from __future__ import annotations

import logging
import random
import threading
from datetime import datetime, timedelta, timezone

from gi.repository import GLib

from dealwise.config import ConfigManager
from dealwise.marketplaces.registry import MarketplaceRegistry
from dealwise.models import MarketplaceListing, RuntimeStats, SavedSearch
from dealwise.repositories.listing_repository import ListingRepository


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
        self._connector_status = "Connectors idle."
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
            if self.refresh_search(search, manual=True):
                started_count += 1

        return started_count

    def refresh_search(self, search: SavedSearch, manual: bool = False) -> bool:
        connector = self.marketplace_registry.get(search.marketplace)

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

    def _refresh_search_worker(self, search: SavedSearch, manual: bool) -> None:
        connector = self.marketplace_registry.get(search.marketplace)
        now = datetime.now(timezone.utc)

        if connector is None:
            with self._lock:
                self._active_refreshes.discard(search.id)
            return

        try:
            result = connector.search(search, limit=20)
            new_count = 0
            inserted_count = 0
            updated_count = 0

            if self.listing_repository is not None and result.listings:
                inserted_count, updated_count = self.listing_repository.upsert_marketplace_listings(
                    result.listings
                )

            with self._lock:
                for listing in result.listings:
                    if listing.dedupe_key in self._seen_listing_keys:
                        continue

                    self._seen_listing_keys.add(listing.dedupe_key)
                    self._live_results.insert(0, listing)
                    new_count += 1

                self._live_results = self._live_results[:250]
                self.listings_analysed += len(result.listings)
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
                    len(result.listings),
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
