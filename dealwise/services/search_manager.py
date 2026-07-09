from __future__ import annotations

import logging
from datetime import datetime, timezone

from gi.repository import GLib

from dealwise.config import ConfigManager
from dealwise.models import RuntimeStats, SavedSearch


class SearchManager:
    """Coordinates saved-search refresh scheduling.

    Phase 1 intentionally does not scrape marketplaces yet. This class gives
    the app a proper production-ready place to add marketplace connectors later.
    """

    def __init__(self, config_manager: ConfigManager, logger: logging.Logger) -> None:
        self.config_manager = config_manager
        self.logger = logger

        self.is_running = False
        self.running_since: datetime | None = None
        self.last_refresh_at: datetime | None = None

        self._timer_id: int | None = None
        self._last_refresh_by_search_id: dict[str, datetime] = {}

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

        for search in searches:
            self.refresh_search(search)

        return len(searches)

    def refresh_search(self, search: SavedSearch) -> None:
        """Refresh a saved search.

        Marketplace integration will be added here in the next phase.
        """

        now = datetime.now(timezone.utc)
        self._last_refresh_by_search_id[search.id] = now
        self.last_refresh_at = now
        self.refreshes_completed += 1

        self.logger.info(
            "Refresh requested | marketplace=%s | query=%s | interval=%sm",
            search.marketplace,
            search.query,
            search.refresh_interval_minutes,
        )

    def get_stats(self) -> RuntimeStats:
        saved_searches = self.config_manager.load_saved_searches()

        return RuntimeStats(
            is_running=self.is_running,
            saved_searches=len(saved_searches),
            searches_running=len(saved_searches) if self.is_running else 0,
            listings_analysed=self.listings_analysed,
            refreshes_completed=self.refreshes_completed,
            running_since=self.running_since,
            last_refresh_at=self.last_refresh_at,
        )

    def _tick(self) -> bool:
        if not self.is_running:
            return False

        now = datetime.now(timezone.utc)
        searches = self.config_manager.load_saved_searches()

        for search in searches:
            last_refresh = self._last_refresh_by_search_id.get(search.id)

            if last_refresh is None:
                self.refresh_search(search)
                continue

            seconds_since_refresh = (now - last_refresh).total_seconds()
            refresh_interval_seconds = search.refresh_interval_minutes * 60

            if seconds_since_refresh >= refresh_interval_seconds:
                self.refresh_search(search)

        return True
