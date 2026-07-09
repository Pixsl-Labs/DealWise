from __future__ import annotations

import gi

gi.require_version("Gtk", "4.0")

from gi.repository import Gio, Gtk

from dealwise import APP_ID
from dealwise.config import ConfigManager
from dealwise.logging_setup import setup_logging
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
        self.search_manager = SearchManager(self.config_manager, self.logger)
        self.window: MainWindow | None = None

    def do_activate(self) -> None:
        if self.window is None:
            self.window = MainWindow(
                application=self,
                config_manager=self.config_manager,
                search_manager=self.search_manager,
                logger=self.logger,
            )

        self.search_manager.start()
        self.window.present()

    def do_shutdown(self) -> None:
        self.search_manager.stop()
        self.logger.info("DealWise application shutdown")
        super().do_shutdown()
