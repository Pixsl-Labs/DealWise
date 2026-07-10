from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from dealwise import APP_ID
from dealwise.config import ConfigManager
from dealwise.data.database import DatabaseManager
from dealwise.logging_setup import setup_logging
from dealwise.repositories.listing_repository import ListingRepository
from dealwise.services.listing_intelligence import ListingIntelligenceService
from dealwise.services.pc_builder_service import PCBuilderService
from dealwise.services.search_manager import SearchManager
from dealwise.ui.main_window import MainWindow


class DealWiseApplication(Gtk.Application):
    """GTK application entry point."""

    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )

        self.config_manager = ConfigManager()
        self.logger = setup_logging(self.config_manager)
        self.database_manager = DatabaseManager(self.config_manager.database_file)
        self.listing_repository = ListingRepository(self.database_manager)
        self.pc_builder_service = PCBuilderService(self.database_manager)
        self.listing_intelligence_service = ListingIntelligenceService()
        self.search_manager = SearchManager(
            self.config_manager,
            self.logger,
            listing_repository=self.listing_repository,
        )
        self.window: MainWindow | None = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(
                application=self,
                config_manager=self.config_manager,
                search_manager=self.search_manager,
                logger=self.logger,
                listing_repository=self.listing_repository,
                pc_builder_service=self.pc_builder_service,
                listing_intelligence_service=self.listing_intelligence_service,
            )

        self.search_manager.start()
        self.window.present()

    def do_shutdown(self) -> None:
        self.search_manager.stop()
        self.logger.info("DealWise application shutdown")
        super().do_shutdown()
