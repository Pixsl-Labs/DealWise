from __future__ import annotations

import logging
import random
import threading
from datetime import datetime, timedelta, timezone

from gi.repository import GLib

from dealwise.config import ConfigManager
from dealwise.marketplaces.registry import MarketplaceRegistry
from dealwise.models import MarketplaceListing, RuntimeStats, SavedSearch
from dealwise.repositories.listing_repository import ListingRepository, is_blocked_listing_title


class SearchManager:
    """Coordinates saved-search refresh scheduling and marketplace dispatch."""

    def __init__(
        self,
        config_manager: ConfigManager,
        logger: logging.Logger,
        listing_repository: ListingRepository | None = None,
    ) -> None:
        self.config_manager = config_manager
        self.logger = logger
        self.listing_repository = listing_repository
        self.marketplace_registry = MarketplaceRegistry()

        self.is_running = False
        self.running_since: datetime | None = None
        self.last_refresh_at: datetime | None = None

        self._timer_id: int | None = None
        self._last_refresh_by_search_id: dict[str, datetime] = {}
        self._next_due_by_search_id: dict[str, datetime] = {}
        self._active_refreshes: set[str] = set()

        self._live_results: list[MarketplaceListing] = []
        self._seen_listing_keys: set[str] = set()
        self._hidden_listing_keys: set[str] = set()
        self._hidden_live_results: dict[str, MarketplaceListing] = {}
        self._connector_status = "Connectors idle."
        self._marketplace_backoff_until: dict[str, datetime] = {}
        self._lock = threading.RLock()

        self.listings_analysed = 0
        self.refreshes_completed = 0

    def start(self) -> None:
        if self.is_running:
            return

        self.is_running = True
        self.running_since = datetime.now(timezone.utc)
        self._timer_id = GLib.timeout_add_seconds(1, self._tick)

        self.logger.info("Search manager started")

    def stop(self) -> None:
        if self._timer_id is not None:
            GLib.source_remove(self._timer_id)
            self._timer_id = None

        self.is_running = False
        self.logger.info("Search manager stopped")

    def refresh_all_saved_searches(self) -> int:
        searches = self.config_manager.load_saved_searches()
        started_count = 0

        for search in searches:
            if started_count >= 3:
                with self._lock:
                    self._connector_status = (
                        "Started 3 searches. Pausing the rest to avoid marketplace rate limits."
                    )
                break

            if self.refresh_search(search, manual=True):
                started_count += 1

        return started_count

    def _is_marketplace_backing_off(self, marketplace_name: str) -> bool:
        backoff_until = self._marketplace_backoff_until.get(marketplace_name.lower())

        if backoff_until is None:
            return False

        return datetime.now(timezone.utc) < backoff_until

    def _backoff_label(self, marketplace_name: str) -> str:
        backoff_until = self._marketplace_backoff_until.get(marketplace_name.lower())

        if backoff_until is None:
            return ""

        local_time = backoff_until.astimezone().strftime("%H:%M")
        return f"{marketplace_name} is cooling down until {local_time} after rate limiting."

    def refresh_search(self, search: SavedSearch, manual: bool = False) -> bool:
        connector = self.marketplace_registry.get(search.marketplace)

        if self._is_marketplace_backing_off(search.marketplace):
            with self._lock:
                self._connector_status = self._backoff_label(search.marketplace)

            return False

        if connector is None:
            with self._lock:
                self._connector_status = (
                    f"No connector available for marketplace '{search.marketplace}'."
                )

            self.logger.warning(
                "No connector available | marketplace=%s | query=%s",
                search.marketplace,
                search.query,
            )
            return False

        with self._lock:
            if search.id in self._active_refreshes:
                return False

            self._active_refreshes.add(search.id)
            self._connector_status = f"Searching {connector.name} for '{search.query}'..."

        worker = threading.Thread(
            target=self._refresh_search_worker,
            args=(search, manual),
            daemon=True,
        )
        worker.start()

        return True

    def get_live_results(self, limit: int = 100) -> list[MarketplaceListing]:
        with self._lock:
            return list(self._live_results[:limit])

    def hide_live_listing(self, dedupe_key: str) -> None:
        with self._lock:
            kept_results: list[MarketplaceListing] = []

            for listing in self._live_results:
                if listing.dedupe_key == dedupe_key:
                    self._hidden_listing_keys.add(dedupe_key)
                    self._hidden_live_results[dedupe_key] = listing
                else:
                    kept_results.append(listing)

            self._live_results = kept_results
            self._connector_status = "Listing moved to Hidden Deals."

    def restore_hidden_listing(self, dedupe_key: str) -> None:
        with self._lock:
            listing = self._hidden_live_results.pop(dedupe_key, None)
            self._hidden_listing_keys.discard(dedupe_key)

            if listing is not None and listing.dedupe_key not in {item.dedupe_key for item in self._live_results}:
                self._live_results.insert(0, listing)

            self._connector_status = "Listing restored from Hidden Deals."

    def get_hidden_results(self, limit: int = 100) -> list[MarketplaceListing]:
        with self._lock:
            return list(self._hidden_live_results.values())[:limit]

    def hidden_count(self) -> int:
        with self._lock:
            return len(self._hidden_live_results)

    def get_stats(self) -> RuntimeStats:
        saved_searches = self.config_manager.load_saved_searches()

        with self._lock:
            live_result_count = len(self._live_results)
            connector_status = self._connector_status
            active_count = len(self._active_refreshes)

        return RuntimeStats(
            is_running=self.is_running,
            saved_searches=len(saved_searches),
            searches_running=active_count,
            listings_analysed=self.listings_analysed,
            live_results=live_result_count,
            refreshes_completed=self.refreshes_completed,
            connector_status=connector_status,
            running_since=self.running_since,
            last_refresh_at=self.last_refresh_at,
        )

    def _filter_connector_listings(
        self,
        listings: list[MarketplaceListing],
        search: SavedSearch,
    ) -> list[MarketplaceListing]:
        filtered: list[MarketplaceListing] = []

        excluded_terms = [term.lower().strip() for term in search.excluded_keywords if term.strip()]
        global_excluded_terms = [
            "laptop",
            "notebook",
            "ultrabook",
            "zenbook",
            "vivobook",
            "thinkpad",
            "ideapad",
            "macbook",
            "chromebook",
            "surface laptop",
            "nike",
            "fitness",
            "resistance band",
            "headphones",
            "airpod",
            "camera",
            "tablet",
            "ipad",
        ]

        for listing in listings:
            title = listing.title.lower()

            if is_blocked_listing_title(listing.title):
                continue

            if any(term in title for term in excluded_terms):
                continue

            if any(term in title for term in global_excluded_terms):
                continue

            filtered.append(listing)

        return filtered

    def _refresh_search_worker(self, search: SavedSearch, manual: bool) -> None:
        connector = self.marketplace_registry.get(search.marketplace)
        now = datetime.now(timezone.utc)

        if connector is None:
            with self._lock:
                self._active_refreshes.discard(search.id)
            return

        try:
            result = connector.search(search, limit=20)
            filtered_listings = self._filter_connector_listings(result.listings, search)

            if result.error and "429" in result.error:
                with self._lock:
                    self._marketplace_backoff_until[connector.name.lower()] = datetime.now(timezone.utc) + timedelta(minutes=20)
                    self._connector_status = (
                        f"{connector.name} rate-limited DealWise. Cooling down for 20 minutes."
                    )
            new_count = 0
            inserted_count = 0
            updated_count = 0

            if self.listing_repository is not None and filtered_listings:
                inserted_count, updated_count = self.listing_repository.upsert_marketplace_listings(
                    filtered_listings
                )

            with self._lock:
                for listing in filtered_listings:
                    if listing.dedupe_key in self._hidden_listing_keys:
                        continue

                    if listing.dedupe_key in self._seen_listing_keys:
                        continue

                    self._seen_listing_keys.add(listing.dedupe_key)
                    self._live_results.insert(0, listing)
                    new_count += 1

                self._live_results = self._live_results[:250]
                self.listings_analysed += len(filtered_listings)
                self.refreshes_completed += 1
                self.last_refresh_at = datetime.now(timezone.utc)
                self._last_refresh_by_search_id[search.id] = self.last_refresh_at
                self._next_due_by_search_id[search.id] = self._calculate_next_due(search)
                self._connector_status = (
                    f"{result.status_message} New this session: {new_count}. "
                    f"DB inserted: {inserted_count}, updated: {updated_count}."
                )

            if result.error:
                self.logger.warning(
                    "Connector refresh completed with error | marketplace=%s | query=%s | error=%s",
                    connector.name,
                    search.query,
                    result.error,
                )
            else:
                self.logger.info(
                    "Connector refresh completed | marketplace=%s | query=%s | returned=%s | session_new=%s | db_inserted=%s | db_updated=%s | manual=%s",
                    connector.name,
                    search.query,
                    len(filtered_listings),
                    new_count,
                    inserted_count,
                    updated_count,
                    manual,
                )
        except Exception as error:
            self.logger.exception(
                "Unhandled refresh worker error | marketplace=%s | query=%s",
                connector.name,
                search.query,
            )

            with self._lock:
                self._connector_status = f"Refresh failed for '{search.query}': {error}"
                self._next_due_by_search_id[search.id] = self._calculate_next_due(search)
        finally:
            with self._lock:
                self._active_refreshes.discard(search.id)

            elapsed = (datetime.now(timezone.utc) - now).total_seconds()
            self.logger.info(
                "Refresh worker finished | query=%s | elapsed=%.2fs",
                search.query,
                elapsed,
            )

    def _tick(self) -> bool:
        if not self.is_running:
            return False

        now = datetime.now(timezone.utc)
        searches = self.config_manager.load_saved_searches()

        for search in searches:
            due_at = self._next_due_by_search_id.get(search.id)

            if due_at is None:
                self._next_due_by_search_id[search.id] = self._initial_due_time()
                continue

            if now >= due_at:
                self.refresh_search(search)

        return True

    def _initial_due_time(self) -> datetime:
        jitter_seconds = random.randint(1, 8)
        return datetime.now(timezone.utc) + timedelta(seconds=jitter_seconds)

    def _calculate_next_due(self, search: SavedSearch) -> datetime:
        base_seconds = search.refresh_interval_minutes * 60
        jitter_seconds = random.randint(0, min(30, max(3, base_seconds // 5)))
        return datetime.now(timezone.utc) + timedelta(
            seconds=base_seconds + jitter_seconds
        )
