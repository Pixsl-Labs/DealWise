from __future__ import annotations

import json
import logging
from pathlib import Path
import webbrowser
from urllib.parse import quote_plus
from datetime import datetime

from gi.repository import Gdk, GLib, Gtk

from dealwise import APP_NAME, APP_VERSION
from dealwise.config import ConfigManager
from dealwise.models import MarketplaceListing, SavedSearch
from dealwise.repositories.listing_repository import ListingRepository, StoredListing, infer_part_type
from dealwise.services.listing_intelligence import ListingIntelligenceService
from dealwise.services.pc_builder_service import PCBuilderService
from dealwise.services.search_manager import SearchManager
from dealwise.services.active_build import ActiveBuildService
from dealwise.services.ram_hunt import RAMHuntProfile, RAMHuntService
from dealwise.services.build_catalog import BUILD_PATH_OPTIONS, USE_CASE_OPTIONS
from dealwise.services.image_cache import ImageCacheService
from dealwise.services.price_history import PriceHistoryService
from dealwise.services.compatibility_service import CompatibilityService
from dealwise.services.build_import import BuildImportService, BuildImportResult


HARDWARE_PREFERENCE_OPTIONS = [
    "Best value / mixed",
    "Linux Mint friendly AMD-first",
    "AMD CPU + AMD GPU",
    "AMD CPU + Nvidia GPU",
    "Intel CPU + AMD GPU",
    "Intel CPU + Nvidia GPU",
]

LIVE_PRIORITY_OPTIONS = [
    "Best overall first",
    "PC parts first",
    "Full PCs first",
]

LIVE_PRODUCT_FILTERS = {
    "All Parts": [
        "Any Product",
    ],
    "CPU": [
        "Any CPU",
        "Ryzen 5 7600",
        "Ryzen 7 7700",
        "Ryzen 7 7800X3D",
        "Ryzen 9 7900",
        "Ryzen 9 7900X",
        "Intel i5-12600K",
        "Intel i5-13600K",
        "Intel i7-13700K",
    ],
    "GPU": [
        "Any GPU",
        "RX 6600",
        "RX 6700 XT",
        "RX 6800",
        "RX 7700 XT",
        "RX 7800 XT",
        "RX 7900 XT",
        "RTX 3060",
        "RTX 4070",
        "RTX 4070 Ti",
        "RTX 4080",
    ],
    "Motherboard": [
        "Any Motherboard",
        "B650",
        "B650M",
        "B650E",
        "X670",
        "X670E",
        "B550",
        "B760 DDR5",
        "Z790 DDR5",
    ],
    "RAM": [
        "Any RAM",
        "32GB DDR5",
        "64GB DDR5",
        "32GB DDR4",
        "16GB DDR5",
    ],
    "Storage": [
        "Any Storage",
        "1TB NVMe",
        "2TB NVMe",
        "4TB NVMe",
        "Samsung 990 Pro",
        "Lexar NM790",
        "WD SN850X",
    ],
    "PSU": [
        "Any PSU",
        "650W Gold",
        "750W Gold",
        "850W Gold",
        "1000W Gold",
    ],
    "Case": [
        "Any Case",
        "ATX airflow case",
        "mATX airflow case",
        "Corsair 4000D",
        "Fractal airflow case",
    ],
    "Cooling": [
        "Any Cooling",
        "Thermalright air cooler",
        "Noctua air cooler",
        "240mm AIO",
        "360mm AIO",
    ],
    "Full PC": [
        "Any Full PC",
        "AM5 full PC",
        "Gaming PC",
        "Workstation PC",
        "Ryzen full PC",
    ],
    "Unknown": [
        "Any Product",
    ],
}

LIVE_PRODUCT_RULES = {
    "Ryzen 5 7600": {"all": ["ryzen", "7600"], "exclude": ["laptop", "notebook"]},
    "Ryzen 7 7700": {"all": ["ryzen", "7700"], "exclude": ["laptop", "notebook"]},
    "Ryzen 7 7800X3D": {"any": ["7800x3d", "7800 x3d"], "exclude": ["laptop", "notebook"]},
    "Ryzen 9 7900": {"all": ["ryzen", "7900"], "exclude": ["7900x", "laptop", "notebook"]},
    "Ryzen 9 7900X": {"all": ["ryzen", "7900x"], "exclude": ["laptop", "notebook"]},
    "Intel i5-12600K": {"all": ["12600k"], "exclude": ["laptop", "notebook"]},
    "Intel i5-13600K": {"all": ["13600k"], "exclude": ["laptop", "notebook"]},
    "Intel i7-13700K": {"all": ["13700k"], "exclude": ["laptop", "notebook"]},

    "RX 6600": {"all": ["rx", "6600"], "exclude": ["laptop", "notebook"]},
    "RX 6700 XT": {"all": ["6700", "xt"], "exclude": ["laptop", "notebook"]},
    "RX 6800": {"all": ["rx", "6800"], "exclude": ["laptop", "notebook"]},
    "RX 7700 XT": {"all": ["7700", "xt"], "exclude": ["laptop", "notebook"]},
    "RX 7800 XT": {"all": ["7800", "xt"], "exclude": ["laptop", "notebook"]},
    "RX 7900 XT": {"all": ["7900", "xt"], "exclude": ["laptop", "notebook"]},
    "RTX 3060": {"all": ["rtx", "3060"], "exclude": ["laptop", "notebook"]},
    "RTX 4070": {"all": ["rtx", "4070"], "exclude": ["4070 ti", "laptop", "notebook"]},
    "RTX 4070 Ti": {"all": ["4070", "ti"], "exclude": ["laptop", "notebook"]},
    "RTX 4080": {"all": ["rtx", "4080"], "exclude": ["laptop", "notebook"]},

    "B650": {"any": ["b650"], "exclude": ["b550", "laptop", "notebook"]},
    "B650M": {"all": ["b650m"], "exclude": ["laptop", "notebook"]},
    "B650E": {"all": ["b650e"], "exclude": ["laptop", "notebook"]},
    "X670": {"any": ["x670"], "exclude": ["x670e", "laptop", "notebook"]},
    "X670E": {"all": ["x670e"], "exclude": ["laptop", "notebook"]},
    "B550": {"any": ["b550"], "exclude": ["laptop", "notebook"]},
    "B760 DDR5": {"all": ["b760", "ddr5"], "exclude": ["laptop", "notebook"]},
    "Z790 DDR5": {"all": ["z790", "ddr5"], "exclude": ["laptop", "notebook"]},

    "32GB DDR5": {"all": ["32", "ddr5"], "exclude": ["laptop", "sodimm", "notebook"]},
    "64GB DDR5": {"all": ["64", "ddr5"], "exclude": ["laptop", "sodimm", "notebook"]},
    "32GB DDR4": {"all": ["32", "ddr4"], "exclude": ["laptop", "sodimm", "notebook"]},
    "16GB DDR5": {"all": ["16", "ddr5"], "exclude": ["laptop", "sodimm", "notebook"]},

    "1TB NVMe": {"all": ["1tb", "nvme"], "exclude": ["enclosure", "caddy", "external", "sata", "2.5", "hdd", "laptop"]},
    "2TB NVMe": {"all": ["2tb", "nvme"], "exclude": ["enclosure", "caddy", "external", "sata", "2.5", "hdd", "laptop"]},
    "4TB NVMe": {"all": ["4tb", "nvme"], "exclude": ["enclosure", "caddy", "external", "sata", "2.5", "hdd", "laptop"]},
    "Samsung 990 Pro": {"all": ["990", "pro"], "exclude": ["enclosure", "external", "sata", "2.5", "laptop"]},
    "Lexar NM790": {"all": ["nm790"], "exclude": ["enclosure", "external", "sata", "2.5", "laptop"]},
    "WD SN850X": {"any": ["sn850x", "sn850"], "exclude": ["enclosure", "external", "sata", "2.5", "laptop"]},

    "650W Gold": {"all": ["650w"], "any": ["gold", "80+"], "exclude": ["laptop"]},
    "750W Gold": {"all": ["750w"], "any": ["gold", "80+"], "exclude": ["laptop"]},
    "850W Gold": {"all": ["850w"], "any": ["gold", "80+"], "exclude": ["laptop"]},
    "1000W Gold": {"all": ["1000w"], "any": ["gold", "80+"], "exclude": ["laptop"]},

    "ATX airflow case": {"all": ["case"], "any": ["atx", "airflow"], "exclude": ["laptop"]},
    "mATX airflow case": {"all": ["case"], "any": ["matx", "m-atx", "micro atx", "airflow"], "exclude": ["laptop"]},
    "Corsair 4000D": {"all": ["4000d"], "exclude": ["laptop"]},
    "Fractal airflow case": {"all": ["fractal"], "any": ["case", "airflow"], "exclude": ["laptop"]},

    "Thermalright air cooler": {"all": ["thermalright"], "any": ["cooler", "heatsink"], "exclude": ["laptop"]},
    "Noctua air cooler": {"all": ["noctua"], "any": ["cooler", "heatsink"], "exclude": ["laptop"]},
    "240mm AIO": {"all": ["240"], "any": ["aio", "liquid"], "exclude": ["laptop"]},
    "360mm AIO": {"all": ["360"], "any": ["aio", "liquid"], "exclude": ["laptop"]},

    "AM5 full PC": {"all": ["pc"], "any": ["am5", "ryzen 7000", "b650"], "exclude": ["laptop", "notebook"]},
    "Gaming PC": {"all": ["gaming", "pc"], "exclude": ["laptop", "notebook"]},
    "Workstation PC": {"any": ["workstation", "precision"], "exclude": ["laptop", "notebook"]},
    "Ryzen full PC": {"all": ["ryzen"], "any": ["pc", "tower", "desktop"], "exclude": ["laptop", "notebook"]},
}


class MainWindow(Gtk.ApplicationWindow):
    """Main DealWise desktop window."""

    def __init__(
        self,
        application: Gtk.Application,
        config_manager: ConfigManager,
        search_manager: SearchManager,
        logger: logging.Logger,
        listing_repository: ListingRepository,
        pc_builder_service: PCBuilderService,
        listing_intelligence_service: ListingIntelligenceService,
    ) -> None:
        super().__init__(application=application)

        self.config_manager = config_manager
        self.search_manager = search_manager
        self.logger = logger
        self.listing_repository = listing_repository
        self.pc_builder_service = pc_builder_service
        self.active_build_service = ActiveBuildService(self.pc_builder_service.database)
        self.active_build_service.seed_current_real_build()
        self.active_build_service.pause_obsolete_saved_searches(self.config_manager)
        self.active_build_service.clear_stale_live_results(self.search_manager)
        self.listing_intelligence_service = listing_intelligence_service

        self.set_title(APP_NAME)
        self._configure_app_icon()
        self.set_default_size(1280, 780)

        self.stat_labels: dict[str, Gtk.Label] = {}
        self.image_cache = ImageCacheService(self.config_manager.cache_dir / "listing-images")
        self.price_history_service = PriceHistoryService(self.pc_builder_service.database)
        self.compatibility_service = CompatibilityService()
        self.build_import_service = BuildImportService(self.pc_builder_service)
        self.ram_hunt_service = RAMHuntService()
        self._live_render_signature = ""
        self._pc_builder_refresh_timer_id: int | None = None

        self._load_css()
        self._build_window()

        GLib.idle_add(self._safe_initial_refresh)
        GLib.timeout_add_seconds(1, self._safe_refresh_runtime_stats)
        GLib.timeout_add_seconds(4, self._safe_refresh_live_results)
        GLib.timeout_add_seconds(5, self._safe_refresh_persistent_listings)

    def _safe_initial_refresh(self) -> bool:
        """Run startup refreshes after the window has been created.

        This prevents one broken refresh, old database schema, or marketplace
        issue from stopping the main window from appearing.
        """

        refresh_steps = [
            ("saved searches", self._refresh_saved_searches),
            ("live results", lambda: self._refresh_live_results(force=True)),
            ("persistent listings", self._refresh_persistent_listings),
            ("pc builder", self._refresh_pc_builder),
            ("runtime stats", self._refresh_runtime_stats),
        ]

        for name, callback in refresh_steps:
            try:
                callback()
            except Exception as error:
                self.logger.exception("Startup refresh failed | step=%s", name)
                self._write_fatal_log(f"Startup refresh failed during {name}: {error}")

        return False

    def _safe_refresh_runtime_stats(self) -> bool:
        try:
            return self._refresh_runtime_stats()
        except Exception as error:
            self.logger.exception("Runtime stats refresh failed")
            self._write_fatal_log(f"Runtime stats refresh failed: {error}")
            return True

    def _safe_refresh_live_results(self) -> bool:
        try:
            return self._refresh_live_results()
        except Exception as error:
            self.logger.exception("Live results refresh failed")
            self._write_fatal_log(f"Live results refresh failed: {error}")
            return True

    def _safe_refresh_persistent_listings(self) -> bool:
        try:
            return self._refresh_persistent_listings()
        except Exception as error:
            self.logger.exception("Persistent listings refresh failed")
            self._write_fatal_log(f"Persistent listings refresh failed: {error}")
            return True

    def _write_fatal_log(self, message: str) -> None:
        try:
            with open("/tmp/dealwise_fatal.log", "a", encoding="utf-8") as file:
                file.write(message + "\n")
        except OSError:
            pass

    def _configure_app_icon(self) -> None:
        icon_dir = Path(__file__).resolve().parents[2] / "assets" / "icon"
        display = Gdk.Display.get_default()

        if display is not None and icon_dir.exists():
            icon_theme = Gtk.IconTheme.get_for_display(display)
            icon_theme.add_search_path(str(icon_dir))

        self.set_icon_name("dealwise")

    def _build_window(self) -> None:
        header = Gtk.HeaderBar()
        header.set_title_widget(self._title_label(APP_NAME, f"v{APP_VERSION}"))
        self.set_titlebar(header)

        manual_refresh_button = Gtk.Button(label="Refresh")
        manual_refresh_button.set_tooltip_text("Manually refresh all saved searches")
        manual_refresh_button.connect("clicked", self._on_manual_refresh_clicked)
        header.pack_end(manual_refresh_button)

        root = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        root.add_css_class("app-root")
        self.set_child(root)

        self.sidebar = Gtk.ListBox()
        self.sidebar.add_css_class("sidebar")
        self.sidebar.set_selection_mode(Gtk.SelectionMode.SINGLE)
        self.sidebar.connect("row-selected", self._on_sidebar_row_selected)
        root.append(self.sidebar)

        self.stack = Gtk.Stack()
        self.stack.set_hexpand(True)
        self.stack.set_vexpand(True)
        root.append(self.stack)

        pages = [
            ("dashboard", "Dashboard", self._build_dashboard_page()),
            ("pc_builder", "PC Builder", self._build_pc_builder_page()),
            ("ram_hunt", "RAM Hunt", self._build_ram_hunt_page()),
            ("live_deals", "Live Deals", self._build_live_deals_page()),
            ("saved_listings", "Saved Listings", self._build_saved_listings_page()),
            ("listing_checker", "Listing Checker", self._build_listing_checker_page()),
            ("saved_searches", "Saved Searches", self._build_saved_searches_page()),
            ("watchlist", "Watchlist", self._placeholder_page("Watchlist")),
            ("price_history", "Price History", self._placeholder_page("Price History")),
            ("reverse_image_search", "Reverse Image Search", self._placeholder_page("Reverse Image Search")),
            ("scam_detection", "Scam Detection", self._placeholder_page("Scam Detection")),
            ("notifications", "Notifications", self._placeholder_page("Notifications")),
            ("statistics", "Statistics", self._placeholder_page("Statistics")),
            ("market_trends", "Market Trends", self._placeholder_page("Market Trends")),
            ("build_planner", "Build Planner", self._placeholder_page("Build Planner")),
            ("settings", "Settings", self._build_settings_page()),
            ("logs", "Logs", self._build_logs_page()),
            ("about", "About", self._build_about_page()),
        ]

        for page_id, title, widget in pages:
            self.stack.add_named(widget, page_id)
            self.sidebar.append(self._sidebar_row(page_id, title))

        first_row = self.sidebar.get_row_at_index(0)
        if first_row is not None:
            self.sidebar.select_row(first_row)

    def _build_dashboard_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Dashboard"))
        page.append(
            self._muted_label(
                "Polish + Build Import phase is active: real-time PC Builder updates, hidden deals, build import, build export, price history scoring and compatibility checks."
            )
        )

        card_grid = Gtk.Grid()
        card_grid.set_row_spacing(14)
        card_grid.set_column_spacing(14)
        card_grid.set_margin_top(18)
        page.append(card_grid)

        stats = [
            ("saved_searches", "Saved Searches"),
            ("searches_running", "Searches Running"),
            ("live_results", "Live Results"),
            ("db_listings", "Database Listings"),
            ("listings_analysed", "Listings Analysed"),
            ("refreshes_completed", "Refreshes Completed"),
            ("running_since", "Running Since"),
            ("last_refresh", "Last Refresh"),
            ("connector_status", "Connector Status"),
        ]

        for index, (key, title) in enumerate(stats):
            card = self._stat_card(key, title)
            card_grid.attach(card, index % 3, index // 3, 1, 1)

        section = self._section_card(
            "DealWise Status",
            [
                "SQLite database is active under ~/.config/Pixsl-Labs/DealWise/database/dealwise.db.",
                "Marketplace results are now persisted and deduplicated.",
                "PC Builder can import current PC information with inxi -Fx.",
                "Listing Checker can create manual listings and generate seller messages.",
                "Deal scoring now combines rough market ranges, local price history, compatibility notes and buyer-evidence checks.",
                "Phase 7 is paused until this polish pass feels smooth enough for daily use.",
            ],
        )
        section.set_margin_top(18)
        page.append(section)

        return self._scroll(page)

    def _build_pc_builder_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("PC Builder"))
        page.append(
            self._muted_label(
                "Clear upgrade planner with live compatibility, budget estimates, hardware preference, and checklist-driven marketplace searches."
            )
        )

        top_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        import_button = Gtk.Button(label="Import Current PC")
        import_button.connect("clicked", self._on_import_pc_clicked)

        import_build_button = Gtk.Button(label="Import Build List")
        import_build_button.connect("clicked", self._on_import_build_clicked)

        clear_pc_button = Gtk.Button(label="Clear Saved PC")
        clear_pc_button.connect("clicked", self._on_clear_current_pc_clicked)

        apply_button = Gtk.Button(label="Apply Recommendations")
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", self._on_apply_recommendations_clicked)

        search_parts_button = Gtk.Button(label="Search Needed Parts")
        search_parts_button.connect("clicked", self._on_search_needed_parts_clicked)

        save_target_button = Gtk.Button(label="Save Target Build")
        save_target_button.connect("clicked", self._on_save_target_build_clicked)

        copy_summary_button = Gtk.Button(label="Copy Summary")
        copy_summary_button.connect("clicked", self._on_copy_build_summary_clicked)

        export_md_button = Gtk.Button(label="Export MD")
        export_md_button.connect("clicked", self._on_export_build_markdown_clicked)

        export_json_button = Gtk.Button(label="Export JSON")
        export_json_button.connect("clicked", self._on_export_build_json_clicked)

        top_actions.append(import_button)
        top_actions.append(import_build_button)
        top_actions.append(clear_pc_button)
        top_actions.append(apply_button)
        top_actions.append(search_parts_button)
        top_actions.append(save_target_button)
        top_actions.append(copy_summary_button)
        top_actions.append(export_md_button)
        top_actions.append(export_json_button)
        page.append(top_actions)

        self.pc_summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.pc_summary_box.set_margin_top(18)
        page.append(self.pc_summary_box)

        target = self.pc_builder_service.get_target_build()

        target_expander = Gtk.Expander(label="Target Build Controls")
        target_expander.set_expanded(True)
        target_expander.set_margin_top(18)

        target_card = Gtk.Frame()
        target_card.add_css_class("card")
        target_form = Gtk.Grid()
        target_form.set_row_spacing(12)
        target_form.set_column_spacing(12)
        target_form.set_margin_top(14)
        target_form.set_margin_bottom(14)
        target_form.set_margin_start(14)
        target_form.set_margin_end(14)

        self.target_budget_input = Gtk.SpinButton.new_with_range(0, 100000, 10)
        self.target_budget_input.set_value(target.total_budget)
        self.target_budget_input.connect("value-changed", self._on_target_input_changed)

        self.target_use_case_dropdown = Gtk.DropDown.new_from_strings(USE_CASE_OPTIONS)
        self._set_dropdown_by_value(self.target_use_case_dropdown, target.use_case)
        self.target_use_case_dropdown.connect("notify::selected", self._on_target_input_changed)

        self.target_platform_dropdown = Gtk.DropDown.new_from_strings(BUILD_PATH_OPTIONS)
        self._set_dropdown_by_value(self.target_platform_dropdown, target.platform)
        self.target_platform_dropdown.connect("notify::selected", self._on_target_input_changed)

        self.hardware_preference_dropdown = Gtk.DropDown.new_from_strings(HARDWARE_PREFERENCE_OPTIONS)
        self.hardware_preference_dropdown.set_selected(1)
        self.hardware_preference_dropdown.connect("notify::selected", self._on_hardware_preference_changed)

        self.target_notes_view = Gtk.TextView()
        self.target_notes_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.target_notes_view.set_vexpand(False)
        self.target_notes_view.set_size_request(-1, 130)
        self.target_notes_buffer = self.target_notes_view.get_buffer()
        self.target_notes_buffer.set_text(target.notes)
        self.target_notes_buffer.connect("changed", self._on_target_input_changed)

        notes_scroll = Gtk.ScrolledWindow()
        notes_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        notes_scroll.set_child(self.target_notes_view)
        notes_scroll.set_min_content_height(130)

        notes_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        notes_box.append(
            self._muted_label(
                "Add build rules, buying priorities, compatibility warnings, or anything you want DealWise to remember."
            )
        )
        notes_box.append(notes_scroll)

        notes_expander = Gtk.Expander(label="Build Notes")
        notes_expander.set_expanded(True)
        notes_expander.set_child(notes_box)

        target_form.attach(self._form_label("Total Budget"), 0, 0, 1, 1)
        target_form.attach(self.target_budget_input, 1, 0, 1, 1)
        target_form.attach(self._form_label("Use Case"), 0, 1, 1, 1)
        target_form.attach(self.target_use_case_dropdown, 1, 1, 1, 1)
        target_form.attach(self._form_label("Build Path"), 0, 2, 1, 1)
        target_form.attach(self.target_platform_dropdown, 1, 2, 1, 1)
        target_form.attach(self._form_label("Hardware Preference"), 0, 3, 1, 1)
        target_form.attach(self.hardware_preference_dropdown, 1, 3, 1, 1)
        target_form.attach(self._form_label("Notes"), 0, 4, 1, 1)
        target_form.attach(notes_expander, 1, 4, 1, 1)

        target_card.set_child(target_form)
        target_expander.set_child(target_card)
        page.append(target_expander)

        self.compatibility_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.compatibility_box.set_margin_top(14)
        page.append(self.compatibility_box)

        page.append(self._subheading("Parts Checklist"))
        page.append(
            self._muted_label(
                "Dropdowns are filtered by build path and hardware preference. Use Stop Searching when you have found a part and do not want DealWise to keep searching that category."
            )
        )

        self.parts_list = Gtk.ListBox()
        self.parts_list.add_css_class("saved-search-list")
        self.parts_list.set_margin_top(10)
        page.append(self.parts_list)

        return self._scroll(page)


    def _build_ram_hunt_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("RAM Hunt"))
        page.append(
            self._muted_label(
                "Urgent RAM workflow for AM5: final 32GB DDR5 kit or temporary POST/test stick. Facebook is browser handoff/manual import only."
            )
        )

        banner = Gtk.Frame()
        banner.add_css_class("card")
        banner.set_margin_top(12)

        banner_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        banner_box.set_margin_top(12)
        banner_box.set_margin_bottom(12)
        banner_box.set_margin_start(12)
        banner_box.set_margin_end(12)

        self.ram_hunt_banner_label = self._muted_label("Deadline and best-match summary will appear here.")
        banner_box.append(self.ram_hunt_banner_label)
        banner.set_child(banner_box)
        page.append(banner)

        controls = Gtk.Frame()
        controls.add_css_class("card")
        controls.set_margin_top(16)

        grid = Gtk.Grid()
        grid.set_row_spacing(10)
        grid.set_column_spacing(12)
        grid.set_margin_top(14)
        grid.set_margin_bottom(14)
        grid.set_margin_start(14)
        grid.set_margin_end(14)

        self.ram_mode_dropdown = Gtk.DropDown.new_from_strings(["Final 32GB Kit", "Temporary Test Stick", "Custom"])
        self.ram_capacity_dropdown = Gtk.DropDown.new_from_strings(["8", "16", "32", "64"])
        self.ram_module_dropdown = Gtk.DropDown.new_from_strings(["1x8GB", "1x16GB", "1x32GB", "2x8GB", "2x16GB", "2x32GB"])
        self.ram_memory_type_dropdown = Gtk.DropDown.new_from_strings(["DDR5"])
        self.ram_min_speed_dropdown = Gtk.DropDown.new_from_strings(["4800", "5200", "5600", "6000", "6200", "6400"])
        self.ram_max_speed_dropdown = Gtk.DropDown.new_from_strings(["5600", "6000", "6400", "7200"])
        self.ram_max_cl_dropdown = Gtk.DropDown.new_from_strings(["30", "32", "36", "40", "46"])
        self.ram_rgb_dropdown = Gtk.DropDown.new_from_strings(["Any", "RGB", "Non-RGB"])
        self.ram_condition_dropdown = Gtk.DropDown.new_from_strings(["Either", "New", "Used"])
        self.ram_delivery_dropdown = Gtk.DropDown.new_from_strings(["Delivery or collection", "Delivery only", "Collection only"])

        self.ram_expo_check = Gtk.CheckButton(label="AMD EXPO preferred")
        self.ram_expo_check.set_active(True)
        self.ram_xmp_check = Gtk.CheckButton(label="Allow XMP")
        self.ram_xmp_check.set_active(True)
        self.ram_urgent_check = Gtk.CheckButton(label="Urgent hunt mode")
        self.ram_urgent_check.set_active(True)

        self.ram_distance_input = Gtk.SpinButton.new_with_range(0, 200, 5)
        self.ram_distance_input.set_value(25)
        self.ram_item_max_input = Gtk.SpinButton.new_with_range(0, 1000, 5)
        self.ram_item_max_input.set_value(180)
        self.ram_all_in_max_input = Gtk.SpinButton.new_with_range(0, 1000, 5)
        self.ram_all_in_max_input.set_value(200)
        self.ram_deadline_entry = Gtk.Entry()
        self.ram_deadline_entry.set_text("2026-07-14")

        self.ram_excluded_entry = Gtk.Entry()
        self.ram_excluded_entry.set_text("ddr4,sodimm,so-dimm,laptop,server,ecc,registered,rdimm,broken,faulty,spares,repair,wanted")

        controls_to_refresh = [
            self.ram_mode_dropdown,
            self.ram_capacity_dropdown,
            self.ram_module_dropdown,
            self.ram_min_speed_dropdown,
            self.ram_max_speed_dropdown,
            self.ram_max_cl_dropdown,
            self.ram_rgb_dropdown,
            self.ram_condition_dropdown,
            self.ram_delivery_dropdown,
        ]

        for dropdown in controls_to_refresh:
            dropdown.connect("notify::selected", self._on_ram_hunt_controls_changed)

        for widget in [
            self.ram_expo_check,
            self.ram_xmp_check,
            self.ram_urgent_check,
        ]:
            widget.connect("toggled", self._on_ram_hunt_controls_changed)

        for widget in [
            self.ram_distance_input,
            self.ram_item_max_input,
            self.ram_all_in_max_input,
        ]:
            widget.connect("value-changed", self._on_ram_hunt_controls_changed)

        self.ram_deadline_entry.connect("changed", self._on_ram_hunt_controls_changed)
        self.ram_excluded_entry.connect("changed", self._on_ram_hunt_controls_changed)

        self._set_dropdown_by_value(self.ram_capacity_dropdown, "32")
        self._set_dropdown_by_value(self.ram_module_dropdown, "2x16GB")
        self._set_dropdown_by_value(self.ram_min_speed_dropdown, "6000")
        self._set_dropdown_by_value(self.ram_max_speed_dropdown, "7200")
        self._set_dropdown_by_value(self.ram_max_cl_dropdown, "36")

        row = 0
        grid.attach(self._form_label("Hunt Mode"), 0, row, 1, 1)
        grid.attach(self.ram_mode_dropdown, 1, row, 1, 1)
        grid.attach(self._form_label("Capacity"), 2, row, 1, 1)
        grid.attach(self.ram_capacity_dropdown, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Module Config"), 0, row, 1, 1)
        grid.attach(self.ram_module_dropdown, 1, row, 1, 1)
        grid.attach(self._form_label("Memory Type"), 2, row, 1, 1)
        grid.attach(self.ram_memory_type_dropdown, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Min Speed"), 0, row, 1, 1)
        grid.attach(self.ram_min_speed_dropdown, 1, row, 1, 1)
        grid.attach(self._form_label("Max Speed"), 2, row, 1, 1)
        grid.attach(self.ram_max_speed_dropdown, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Max CL"), 0, row, 1, 1)
        grid.attach(self.ram_max_cl_dropdown, 1, row, 1, 1)
        grid.attach(self._form_label("RGB"), 2, row, 1, 1)
        grid.attach(self.ram_rgb_dropdown, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Condition"), 0, row, 1, 1)
        grid.attach(self.ram_condition_dropdown, 1, row, 1, 1)
        grid.attach(self._form_label("Delivery"), 2, row, 1, 1)
        grid.attach(self.ram_delivery_dropdown, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Collection Distance"), 0, row, 1, 1)
        grid.attach(self.ram_distance_input, 1, row, 1, 1)
        grid.attach(self._form_label("Item Max"), 2, row, 1, 1)
        grid.attach(self.ram_item_max_input, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("All-In Max"), 0, row, 1, 1)
        grid.attach(self.ram_all_in_max_input, 1, row, 1, 1)
        grid.attach(self._form_label("Deadline"), 2, row, 1, 1)
        grid.attach(self.ram_deadline_entry, 3, row, 1, 1)

        row += 1
        grid.attach(self.ram_expo_check, 1, row, 1, 1)
        grid.attach(self.ram_xmp_check, 2, row, 1, 1)
        grid.attach(self.ram_urgent_check, 3, row, 1, 1)

        row += 1
        grid.attach(self._form_label("Excluded Keywords"), 0, row, 1, 1)
        grid.attach(self.ram_excluded_entry, 1, row, 3, 1)

        controls.set_child(grid)
        page.append(controls)

        actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        actions.set_margin_top(12)

        final_button = Gtk.Button(label="Use Final Kit Profile")
        final_button.connect("clicked", self._on_ram_hunt_final_profile_clicked)

        temporary_button = Gtk.Button(label="Use Temporary Test Profile")
        temporary_button.connect("clicked", self._on_ram_hunt_temporary_profile_clicked)

        search_vinted_button = Gtk.Button(label="Search Vinted Batch")
        search_vinted_button.add_css_class("suggested-action")
        search_vinted_button.connect("clicked", self._on_ram_hunt_search_vinted_clicked)

        open_all_button = Gtk.Button(label="Open All Marketplace Searches")
        open_all_button.connect("clicked", self._on_ram_hunt_open_all_clicked)

        copy_message_button = Gtk.Button(label="Copy Seller Message")
        copy_message_button.connect("clicked", self._on_ram_hunt_copy_message_clicked)

        apply_builder_button = Gtk.Button(label="Apply To PC Builder RAM")
        apply_builder_button.connect("clicked", self._on_ram_hunt_apply_builder_clicked)

        mark_bought_button = Gtk.Button(label="Mark RAM Bought")
        mark_bought_button.connect("clicked", self._on_ram_hunt_mark_bought_clicked)

        for button in [
            final_button,
            temporary_button,
            search_vinted_button,
            open_all_button,
            copy_message_button,
            apply_builder_button,
            mark_bought_button,
        ]:
            actions.append(button)

        page.append(actions)

        self.ram_hunt_output_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.ram_hunt_output_box.set_margin_top(16)
        page.append(self.ram_hunt_output_box)

        self._refresh_ram_hunt_page()
        return self._scroll(page)

    def _current_ram_hunt_profile(self) -> RAMHuntProfile:
        excluded = [
            item.strip()
            for item in self.ram_excluded_entry.get_text().split(",")
            if item.strip()
        ] if hasattr(self, "ram_excluded_entry") else []

        return RAMHuntProfile(
            mode=self._dropdown_text(self.ram_mode_dropdown) if hasattr(self, "ram_mode_dropdown") else "Final 32GB Kit",
            capacity_gb=int(self._dropdown_text(self.ram_capacity_dropdown)) if hasattr(self, "ram_capacity_dropdown") else 32,
            module_config=self._dropdown_text(self.ram_module_dropdown) if hasattr(self, "ram_module_dropdown") else "2x16GB",
            memory_type="DDR5",
            min_speed=int(self._dropdown_text(self.ram_min_speed_dropdown)) if hasattr(self, "ram_min_speed_dropdown") else 6000,
            max_speed=int(self._dropdown_text(self.ram_max_speed_dropdown)) if hasattr(self, "ram_max_speed_dropdown") else 7200,
            max_cas_latency=int(self._dropdown_text(self.ram_max_cl_dropdown)) if hasattr(self, "ram_max_cl_dropdown") else 36,
            expo_preferred=self.ram_expo_check.get_active() if hasattr(self, "ram_expo_check") else True,
            allow_xmp=self.ram_xmp_check.get_active() if hasattr(self, "ram_xmp_check") else True,
            rgb=self._dropdown_text(self.ram_rgb_dropdown) if hasattr(self, "ram_rgb_dropdown") else "Any",
            condition=self._dropdown_text(self.ram_condition_dropdown) if hasattr(self, "ram_condition_dropdown") else "Either",
            delivery_mode=self._dropdown_text(self.ram_delivery_dropdown) if hasattr(self, "ram_delivery_dropdown") else "Delivery or collection",
            collection_distance_miles=int(self.ram_distance_input.get_value()) if hasattr(self, "ram_distance_input") else 25,
            item_price_max=float(self.ram_item_max_input.get_value()) if hasattr(self, "ram_item_max_input") else 180,
            all_in_price_max=float(self.ram_all_in_max_input.get_value()) if hasattr(self, "ram_all_in_max_input") else 200,
            deadline=self.ram_deadline_entry.get_text().strip() if hasattr(self, "ram_deadline_entry") else "2026-07-14",
            excluded_keywords=excluded,
            urgent=self.ram_urgent_check.get_active() if hasattr(self, "ram_urgent_check") else True,
        )

    def _on_ram_hunt_controls_changed(self, *_args) -> None:
        self._refresh_ram_hunt_page()

    def _refresh_ram_hunt_page(self) -> None:
        if not hasattr(self, "ram_hunt_output_box"):
            return

        self._clear_box(self.ram_hunt_output_box)
        profile = self._current_ram_hunt_profile()
        queries = self.ram_hunt_service.query_variants(profile)
        urls = self.ram_hunt_service.browser_urls(profile)

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text(
                f"{profile.mode} | {profile.capacity_gb}GB {profile.module_config} {profile.memory_type} | "
                f"{profile.min_speed}-{profile.max_speed}MT/s | max CL{profile.max_cas_latency} | "
                f"All-in max £{profile.all_in_price_max:.0f} | {profile.deadline_label()}"
            )

        self.ram_hunt_output_box.append(
            self._section_card(
                "RAM Hunt Summary",
                [
                    f"Mode: {profile.mode}",
                    f"Target: {profile.capacity_gb}GB {profile.module_config} {profile.memory_type}",
                    f"Speed: {profile.min_speed} to {profile.max_speed} MT/s",
                    f"Maximum CAS latency: CL{profile.max_cas_latency}",
                    f"AMD EXPO preferred: {profile.expo_preferred}",
                    f"XMP allowed: {profile.allow_xmp}",
                    f"All-in price maximum: £{profile.all_in_price_max:.0f}",
                    f"Urgent mode: {profile.urgent}",
                    f"Deadline: {profile.deadline_label()}",
                    "Temporary mode note: Suitable for testing — not recommended as the final gaming configuration."
                    if profile.mode == "Temporary Test Stick"
                    else "Final mode note: prioritise 2x16GB desktop DDR5-6000 CL30/32/36 kits with EXPO or likely AM5 compatibility.",
                ],
            )
        )

        self.ram_hunt_output_box.append(
            self._section_card(
                "Generated Search Terms",
                [f"- {query}" for query in queries],
            )
        )

        self.ram_hunt_output_box.append(
            self._section_card(
                "Negative Keywords",
                [f"- {keyword}" for keyword in profile.excluded_keywords],
            )
        )

        self.ram_hunt_output_box.append(
            self._section_card(
                "Marketplace Handoff",
                [
                    f"{marketplace}: {label}"
                    for marketplace, label, _url in urls
                ],
            )
        )

        self.ram_hunt_output_box.append(
            self._section_card(
                "Seller Message Preview",
                self.ram_hunt_service.seller_message(profile).splitlines(),
            )
        )

    def _apply_ram_profile_to_controls(self, profile: RAMHuntProfile) -> None:
        self._set_dropdown_by_value(self.ram_mode_dropdown, profile.mode)
        self._set_dropdown_by_value(self.ram_capacity_dropdown, str(profile.capacity_gb))
        self._set_dropdown_by_value(self.ram_module_dropdown, profile.module_config)
        self._set_dropdown_by_value(self.ram_min_speed_dropdown, str(profile.min_speed))
        self._set_dropdown_by_value(self.ram_max_speed_dropdown, str(profile.max_speed))
        self._set_dropdown_by_value(self.ram_max_cl_dropdown, str(profile.max_cas_latency))
        self._set_dropdown_by_value(self.ram_rgb_dropdown, profile.rgb)
        self._set_dropdown_by_value(self.ram_condition_dropdown, profile.condition)
        self._set_dropdown_by_value(self.ram_delivery_dropdown, profile.delivery_mode)
        self.ram_expo_check.set_active(profile.expo_preferred)
        self.ram_xmp_check.set_active(profile.allow_xmp)
        self.ram_urgent_check.set_active(profile.urgent)
        self.ram_distance_input.set_value(profile.collection_distance_miles)
        self.ram_item_max_input.set_value(profile.item_price_max)
        self.ram_all_in_max_input.set_value(profile.all_in_price_max)
        self.ram_deadline_entry.set_text(profile.deadline)
        self.ram_excluded_entry.set_text(",".join(profile.excluded_keywords))
        self._refresh_ram_hunt_page()

    def _on_ram_hunt_final_profile_clicked(self, _button: Gtk.Button) -> None:
        self._apply_ram_profile_to_controls(RAMHuntProfile.final_default())

    def _on_ram_hunt_temporary_profile_clicked(self, _button: Gtk.Button) -> None:
        self._apply_ram_profile_to_controls(RAMHuntProfile.temporary_default())

    def _on_ram_hunt_search_vinted_clicked(self, _button: Gtk.Button) -> None:
        profile = self._current_ram_hunt_profile()
        queries = self.ram_hunt_service.query_variants(profile)[:4]
        started = 0

        for query in queries:
            search = SavedSearch.create(
                query=query,
                marketplace="Vinted",
                min_price=None,
                max_price=profile.all_in_price_max,
                condition="Any",
                excluded_keywords=profile.excluded_keywords,
                refresh_interval_minutes=5,
            )

            self.config_manager.add_saved_search(search)

            if self.search_manager.refresh_search(search, manual=True):
                started += 1

        self._refresh_saved_searches()
        self._refresh_runtime_stats()

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text(
                f"Started {started} Vinted RAM search(es). Queries are batched to avoid rate limits."
            )

    def _on_ram_hunt_open_all_clicked(self, _button: Gtk.Button) -> None:
        profile = self._current_ram_hunt_profile()
        urls = self.ram_hunt_service.browser_urls(profile)

        for _marketplace, _label, url in urls:
            webbrowser.open(url)

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text(
                f"Opened {len(urls)} marketplace/reference searches in browser. Facebook is handoff only."
            )

    def _on_ram_hunt_copy_message_clicked(self, _button: Gtk.Button) -> None:
        profile = self._current_ram_hunt_profile()
        copied = self._copy_text_to_clipboard(self.ram_hunt_service.seller_message(profile))

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text(
                "RAM seller message copied to clipboard." if copied else "Could not copy seller message."
            )

    def _on_ram_hunt_apply_builder_clicked(self, _button: Gtk.Button) -> None:
        profile = self._current_ram_hunt_profile()
        target = (
            "Temporary desktop DDR5 test stick"
            if profile.mode == "Temporary Test Stick"
            else f"{profile.capacity_gb}GB {profile.module_config} DDR5-{profile.min_speed} CL{profile.max_cas_latency} EXPO"
        )

        with self.pc_builder_service.database.connect() as connection:
            connection.execute(
                """
                UPDATE build_parts
                SET target = ?, budget = ?, status = 'Needed', notes = ?
                WHERE part_type = 'RAM'
                """,
                (
                    target,
                    profile.all_in_price_max,
                    f"RAM Hunt profile: {profile.mode}. Deadline: {profile.deadline}.",
                ),
            )
            connection.commit()

        self._refresh_pc_builder()

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text("PC Builder RAM row updated from RAM Hunt profile.")

    def _on_ram_hunt_mark_bought_clicked(self, _button: Gtk.Button) -> None:
        profile = self._current_ram_hunt_profile()

        with self.pc_builder_service.database.connect() as connection:
            connection.execute(
                """
                UPDATE build_parts
                SET status = 'Bought', bought_price = budget, notes = ?
                WHERE part_type = 'RAM'
                """,
                (
                    f"Marked bought from RAM Hunt. Urgent notifications should stop for final RAM. Profile: {profile.mode}.",
                ),
            )
            connection.commit()

        self._refresh_pc_builder()

        if hasattr(self, "ram_hunt_banner_label"):
            self.ram_hunt_banner_label.set_text("RAM marked as bought in PC Builder. Pause urgent RAM searches manually if needed.")


    def _build_live_deals_page(self) -> Gtk.Widget:
        page = self._page_container()

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_row.set_hexpand(True)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_box.set_hexpand(True)
        title_box.append(self._heading("Live Deals"))
        title_box.append(
            self._muted_label(
                "Search, filter, sort and compare live marketplace results. Results now appear above saved deals."
            )
        )

        search_parts_button = Gtk.Button(label="Search Needed Parts")
        search_parts_button.connect("clicked", self._on_search_needed_parts_clicked)

        refresh_button = Gtk.Button(label="Search Now")
        refresh_button.connect("clicked", self._on_manual_refresh_clicked)

        view_results_button = Gtk.Button(label="View Results")
        view_results_button.connect("clicked", self._on_view_live_results_clicked)

        top_row.append(title_box)
        top_row.append(search_parts_button)
        top_row.append(refresh_button)
        top_row.append(view_results_button)
        page.append(top_row)

        status_card = Gtk.Frame()
        status_card.add_css_class("card")
        status_card.set_margin_top(18)

        status_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        status_box.set_margin_top(12)
        status_box.set_margin_bottom(12)
        status_box.set_margin_start(12)
        status_box.set_margin_end(12)

        self.live_status_label = self._muted_label("Waiting for saved searches...")
        status_box.append(self.live_status_label)

        self.live_results_hint_label = self._muted_label("Tip: choose Part/Product or use Search Selected Filter for focused results.")
        status_box.append(self.live_results_hint_label)

        status_card.set_child(status_box)
        page.append(status_card)

        filter_expander = Gtk.Expander(label="Search, Filters and Sorting")
        filter_expander.set_expanded(True)
        filter_expander.set_margin_top(14)

        filter_card = Gtk.Frame()
        filter_card.add_css_class("card")

        filter_grid = Gtk.Grid()
        filter_grid.set_row_spacing(10)
        filter_grid.set_column_spacing(10)
        filter_grid.set_margin_top(14)
        filter_grid.set_margin_bottom(14)
        filter_grid.set_margin_start(14)
        filter_grid.set_margin_end(14)

        self.live_search_entry = Gtk.Entry()
        self.live_search_entry.set_placeholder_text("Optional: search shown deals, e.g. RX 6800, Ryzen 7700, full PC")
        self.live_search_entry.connect("changed", self._on_live_filter_debounced)

        self.live_focus_dropdown = Gtk.DropDown.new_from_strings(
            ["Active Build Hunt", "All Live Deals", "Checklist Matches Only"]
        )
        self.live_focus_dropdown.connect("notify::selected", self._on_live_filter_debounced)

        self.live_part_dropdown = Gtk.DropDown.new_from_strings(
            ["All Parts", "Full PC", "CPU", "GPU", "Motherboard", "RAM", "Storage", "PSU", "Case", "Cooling", "Unknown"]
        )
        self.live_part_dropdown.connect("notify::selected", self._on_live_part_filter_changed)

        self.live_product_dropdown = Gtk.DropDown.new_from_strings(LIVE_PRODUCT_FILTERS["All Parts"])
        self.live_product_dropdown.connect("notify::selected", self._on_live_filter_debounced)

        self.live_priority_dropdown = Gtk.DropDown.new_from_strings(LIVE_PRIORITY_OPTIONS)
        self.live_priority_dropdown.connect("notify::selected", self._on_live_filter_debounced)
        self.live_priority_dropdown.set_selected(1)

        self.live_sort_dropdown = Gtk.DropDown.new_from_strings(
            [
                "Newest First",
                "Lowest Price",
                "Highest Price",
                "Highest Deal Score",
                "Lowest Scam Risk",
                "Highest Build Fit",
                "Highest Evidence Confidence",
                "Lowest Historical Price",
            ]
        )
        self.live_sort_dropdown.connect("notify::selected", self._on_live_filter_debounced)

        self.live_max_price_input = Gtk.SpinButton.new_with_range(0, 100000, 5)
        self.live_max_price_input.set_tooltip_text("0 means no max price filter")
        self.live_max_price_input.connect("value-changed", self._on_live_filter_debounced)

        self.live_hide_high_scam_check = Gtk.CheckButton(label="Hide high scam risk")
        self.live_show_bought_categories_check = Gtk.CheckButton(label="Show Bought Categories")
        self.live_hide_high_scam_check.connect("toggled", self._on_live_filter_debounced)

        apply_filters_button = Gtk.Button(label="Apply Filters")
        apply_filters_button.add_css_class("suggested-action")
        apply_filters_button.connect("clicked", self._on_apply_live_filters_clicked)

        clear_filters_button = Gtk.Button(label="Clear Filters")
        clear_filters_button.connect("clicked", self._on_clear_live_filters_clicked)

        clear_stale_button = Gtk.Button(label="Clear Stale Live Results")
        clear_stale_button.connect("clicked", self._on_clear_stale_live_results_clicked)

        search_text_button = Gtk.Button(label="Search Selected Filter")
        search_text_button.connect("clicked", self._on_search_live_text_clicked)

        filter_grid.attach(self._form_label("Search"), 0, 0, 1, 1)
        filter_grid.attach(self.live_search_entry, 1, 0, 3, 1)
        filter_grid.attach(self._form_label("Focus"), 0, 1, 1, 1)
        filter_grid.attach(self.live_focus_dropdown, 1, 1, 1, 1)
        filter_grid.attach(self._form_label("Part"), 2, 1, 1, 1)
        filter_grid.attach(self.live_part_dropdown, 3, 1, 1, 1)
        filter_grid.attach(self._form_label("Product"), 0, 2, 1, 1)
        filter_grid.attach(self.live_product_dropdown, 1, 2, 1, 1)
        filter_grid.attach(self._form_label("Show First"), 2, 2, 1, 1)
        filter_grid.attach(self.live_priority_dropdown, 3, 2, 1, 1)
        filter_grid.attach(self._form_label("Sort"), 0, 3, 1, 1)
        filter_grid.attach(self.live_sort_dropdown, 1, 3, 1, 1)
        filter_grid.attach(self._form_label("Max Price"), 2, 3, 1, 1)
        filter_grid.attach(self.live_max_price_input, 3, 3, 1, 1)
        filter_grid.attach(self.live_hide_high_scam_check, 1, 4, 1, 1)
        filter_grid.attach(self.live_show_bought_categories_check, 2, 4, 1, 1)
        filter_grid.attach(apply_filters_button, 3, 4, 1, 1)
        filter_grid.attach(clear_filters_button, 2, 5, 1, 1)
        filter_grid.attach(clear_stale_button, 3, 5, 1, 1)
        filter_grid.attach(search_text_button, 1, 5, 3, 1)

        filter_card.set_child(filter_grid)
        filter_expander.set_child(filter_card)
        page.append(filter_expander)

        self._saved_live_expanded = False
        self._worth_live_expanded = True

        # Results first. Saved deals underneath.
        self.worth_live_expander = Gtk.Expander(label="New / Worth Checking")
        self.worth_live_expander.set_expanded(True)
        self.worth_live_expander.set_margin_top(16)
        self.worth_live_expander.connect("notify::expanded", self._on_worth_live_expanded_changed)

        self.worth_live_list = Gtk.ListBox()
        self.worth_live_list.add_css_class("saved-search-list")
        self.worth_live_expander.set_child(self.worth_live_list)
        page.append(self.worth_live_expander)

        self.saved_live_expander = Gtk.Expander(label="Saved / Favourited Deals")
        self.saved_live_expander.set_expanded(False)
        self.saved_live_expander.set_margin_top(16)
        self.saved_live_expander.connect("notify::expanded", self._on_saved_live_expanded_changed)

        self.saved_live_list = Gtk.ListBox()
        self.saved_live_list.add_css_class("saved-search-list")
        self.saved_live_expander.set_child(self.saved_live_list)
        page.append(self.saved_live_expander)

        self.hidden_live_expander = Gtk.Expander(label="Hidden Deals")
        self.hidden_live_expander.set_expanded(False)
        self.hidden_live_expander.set_margin_top(16)

        self.hidden_live_list = Gtk.ListBox()
        self.hidden_live_list.add_css_class("saved-search-list")
        self.hidden_live_expander.set_child(self.hidden_live_list)
        page.append(self.hidden_live_expander)

        return self._scroll(page)

    def _build_saved_listings_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Saved Listings"))
        page.append(
            self._muted_label(
                "Persistent listing database. Marketplace results, manual listings, and saved buying statuses will appear here."
            )
        )

        self.persistent_listings_list = Gtk.ListBox()
        self.persistent_listings_list.add_css_class("saved-search-list")
        self.persistent_listings_list.set_margin_top(16)
        page.append(self.persistent_listings_list)

        return self._scroll(page)

    def _build_listing_checker_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Listing Checker"))
        page.append(
            self._muted_label(
                "Paste a listing, price, and any seller chat notes. DealWise will flag evidence/risk issues and generate a safer seller message."
            )
        )

        form_card = Gtk.Frame()
        form_card.add_css_class("card")
        form = Gtk.Grid()
        form.set_row_spacing(12)
        form.set_column_spacing(12)
        form.set_margin_top(14)
        form.set_margin_bottom(14)
        form.set_margin_start(14)
        form.set_margin_end(14)

        self.checker_title_entry = Gtk.Entry()
        self.checker_title_entry.set_placeholder_text("Example: RX 6800 Sapphire Pulse")

        self.checker_url_entry = Gtk.Entry()
        self.checker_url_entry.set_placeholder_text("Paste listing URL")

        self.checker_marketplace_entry = Gtk.Entry()
        self.checker_marketplace_entry.set_text("Manual")

        self.checker_price_input = Gtk.SpinButton.new_with_range(0, 100000, 1)

        self.checker_part_dropdown = Gtk.DropDown.new_from_strings(
            ["Unknown", "GPU", "CPU", "Motherboard", "RAM", "Storage", "PSU", "Case", "Cooling"]
        )

        self.checker_notes_entry = Gtk.Entry()
        self.checker_notes_entry.set_placeholder_text("Notes / concerns")

        analyse_button = Gtk.Button(label="Analyse and Save")
        analyse_button.add_css_class("suggested-action")
        analyse_button.connect("clicked", self._on_analyse_listing_clicked)

        form.attach(self._form_label("Title"), 0, 0, 1, 1)
        form.attach(self.checker_title_entry, 1, 0, 2, 1)
        form.attach(self._form_label("URL"), 0, 1, 1, 1)
        form.attach(self.checker_url_entry, 1, 1, 2, 1)
        form.attach(self._form_label("Marketplace"), 0, 2, 1, 1)
        form.attach(self.checker_marketplace_entry, 1, 2, 1, 1)
        form.attach(self._form_label("Price"), 0, 3, 1, 1)
        form.attach(self.checker_price_input, 1, 3, 1, 1)
        form.attach(self._form_label("Part Type"), 0, 4, 1, 1)
        form.attach(self.checker_part_dropdown, 1, 4, 1, 1)
        form.attach(self._form_label("Notes"), 0, 5, 1, 1)
        form.attach(self.checker_notes_entry, 1, 5, 2, 1)
        form.attach(analyse_button, 1, 6, 1, 1)

        form_card.set_child(form)
        form_card.set_margin_top(18)
        page.append(form_card)

        self.checker_result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.checker_result_box.set_margin_top(18)
        page.append(self.checker_result_box)

        return self._scroll(page)

    def _build_saved_searches_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Saved Searches"))
        page.append(
            self._muted_label(
                "Create marketplace searches. Vinted searches can run through the public connector."
            )
        )

        form_card = Gtk.Frame()
        form_card.add_css_class("card")
        form_card.set_margin_top(18)

        form = Gtk.Grid()
        form.set_row_spacing(12)
        form.set_column_spacing(12)
        form.set_margin_top(14)
        form.set_margin_bottom(14)
        form.set_margin_start(14)
        form.set_margin_end(14)
        form_card.set_child(form)

        self.query_entry = Gtk.Entry()
        self.query_entry.set_placeholder_text("Example: Ryzen 7700")
        self.excluded_keywords_entry = Gtk.Entry()
        self.excluded_keywords_entry.set_placeholder_text("Example: broken, faulty, wanted")

        self.min_price_input = Gtk.SpinButton.new_with_range(0, 100000, 1)
        self.max_price_input = Gtk.SpinButton.new_with_range(0, 100000, 1)

        self.marketplace_dropdown = Gtk.DropDown.new_from_strings(
            ["Vinted", "eBay", "Facebook Marketplace", "Gumtree", "CeX"]
        )
        self.condition_dropdown = Gtk.DropDown.new_from_strings(
            ["Any", "New", "Like New", "Good", "Used", "For parts"]
        )
        self.refresh_interval_dropdown = Gtk.DropDown.new_from_strings(
            ["1", "2", "5", "10", "15", "30", "60"]
        )
        self.refresh_interval_dropdown.set_selected(2)

        save_button = Gtk.Button(label="Save Search")
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_search_clicked)

        form.attach(self._form_label("Search"), 0, 0, 1, 1)
        form.attach(self.query_entry, 1, 0, 2, 1)
        form.attach(self._form_label("Marketplace"), 0, 1, 1, 1)
        form.attach(self.marketplace_dropdown, 1, 1, 1, 1)
        form.attach(self._form_label("Condition"), 0, 2, 1, 1)
        form.attach(self.condition_dropdown, 1, 2, 1, 1)
        form.attach(self._form_label("Min Price"), 0, 3, 1, 1)
        form.attach(self.min_price_input, 1, 3, 1, 1)
        form.attach(self._form_label("Max Price"), 0, 4, 1, 1)
        form.attach(self.max_price_input, 1, 4, 1, 1)
        form.attach(self._form_label("Excluded Keywords"), 0, 5, 1, 1)
        form.attach(self.excluded_keywords_entry, 1, 5, 2, 1)
        form.attach(self._form_label("Refresh Minutes"), 0, 6, 1, 1)
        form.attach(self.refresh_interval_dropdown, 1, 6, 1, 1)
        form.attach(save_button, 1, 7, 1, 1)

        page.append(form_card)

        list_heading = self._subheading("Current Searches")
        list_heading.set_margin_top(22)
        page.append(list_heading)

        self.saved_search_list = Gtk.ListBox()
        self.saved_search_list.add_css_class("saved-search-list")
        self.saved_search_list.set_margin_top(10)
        page.append(self.saved_search_list)

        return self._scroll(page)

    def _build_settings_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Settings"))

        config = self.config_manager.load_config()
        connector_names = ", ".join(self.search_manager.marketplace_registry.names())

        settings_card = self._section_card(
            "Current Local Settings",
            [
                f"Theme: {config.get('theme', 'dark')}",
                f"Default refresh: {config.get('default_refresh_interval_minutes', 5)} minutes",
                f"Notifications enabled: {config.get('notifications_enabled', True)}",
                f"Available connectors: {connector_names}",
                f"Config path: {self.config_manager.app_dir}",
                f"Database path: {self.config_manager.database_file}",
            ],
        )
        page.append(settings_card)
        return self._scroll(page)

    def _build_logs_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("Logs"))
        page.append(
            self._section_card(
                "Runtime Logs",
                [
                    f"Log file: {self.config_manager.logs_dir / 'dealwise.log'}",
                    "Connector and database failures are logged here instead of crashing the app.",
                ],
            )
        )
        return self._scroll(page)

    def _build_about_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("About DealWise"))
        page.append(
            self._section_card(
                "Project Vision",
                [
                    "Linux-first marketplace intelligence desktop app.",
                    "Built for PC hardware deal tracking, price analysis, scam detection, and upgrade planning.",
                    "Current version activates Phase 6 foundations.",
                ],
            )
        )
        return self._scroll(page)

    def _placeholder_page(self, title: str) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading(title))
        page.append(
            self._muted_label(
                "This page is reserved for a planned feature. Current focus is Phase 6 quality, price history, compatibility, buyer evidence checks, and Phase 7 connector readiness."
            )
        )
        return self._scroll(page)

    def _on_sidebar_row_selected(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        page_id = getattr(row, "page_id", None)
        if page_id is not None:
            self.stack.set_visible_child_name(page_id)

    def _on_view_live_results_clicked(self, _button: Gtk.Button) -> None:
        self._worth_live_expanded = True
        self._saved_live_expanded = False

        if hasattr(self, "worth_live_expander"):
            self.worth_live_expander.set_expanded(True)

        if hasattr(self, "saved_live_expander"):
            self.saved_live_expander.set_expanded(False)

    def _on_saved_live_expanded_changed(self, *_args) -> None:
        if hasattr(self, "saved_live_expander"):
            self._saved_live_expanded = self.saved_live_expander.get_expanded()

    def _on_worth_live_expanded_changed(self, *_args) -> None:
        if hasattr(self, "worth_live_expander"):
            self._worth_live_expanded = self.worth_live_expander.get_expanded()

    def _on_remove_live_listing_clicked(self, _button: Gtk.Button, listing: MarketplaceListing) -> None:
        self.search_manager.hide_live_listing(listing.dedupe_key)
        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        self._refresh_runtime_stats()

    def _on_delete_stored_listing_clicked(self, _button: Gtk.Button, dedupe_key: str) -> None:
        self.listing_repository.delete_listing(dedupe_key)
        self.search_manager.hide_live_listing(dedupe_key)
        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        self._refresh_persistent_listings()
        self._refresh_runtime_stats()

    def _on_manual_refresh_clicked(self, _button: Gtk.Button) -> None:
        started_count = self.search_manager.refresh_all_saved_searches()
        self.logger.info("Manual refresh requested | started=%s", started_count)
        self._refresh_runtime_stats()

    def _on_save_search_clicked(self, _button: Gtk.Button) -> None:
        query = self.query_entry.get_text().strip()

        if not query:
            self.query_entry.add_css_class("error")
            return

        self.query_entry.remove_css_class("error")

        excluded_keywords = [
            keyword.strip()
            for keyword in self.excluded_keywords_entry.get_text().split(",")
            if keyword.strip()
        ]

        search = SavedSearch.create(
            query=query,
            marketplace=self._dropdown_text(self.marketplace_dropdown),
            min_price=self._price_or_none(self.min_price_input.get_value()),
            max_price=self._price_or_none(self.max_price_input.get_value()),
            condition=self._dropdown_text(self.condition_dropdown),
            excluded_keywords=excluded_keywords,
            refresh_interval_minutes=int(self._dropdown_text(self.refresh_interval_dropdown)),
        )

        self.config_manager.add_saved_search(search)
        self.logger.info("Saved search created | query=%s", search.query)

        self.query_entry.set_text("")
        self.excluded_keywords_entry.set_text("")
        self.min_price_input.set_value(0)
        self.max_price_input.set_value(0)

        self._refresh_saved_searches()
        self._refresh_runtime_stats()

    def _on_delete_search_clicked(self, _button: Gtk.Button, search_id: str) -> None:
        self.config_manager.delete_saved_search(search_id)
        self.logger.info("Saved search deleted | id=%s", search_id)
        self._refresh_saved_searches()
        self._refresh_runtime_stats()

    def _on_open_listing_clicked(self, _button: Gtk.Button, url: str) -> None:
        if url:
            webbrowser.open(url)

    def _on_save_live_listing_clicked(self, _button: Gtk.Button, listing: MarketplaceListing) -> None:
        self.listing_repository.upsert_marketplace_listings([listing])
        self.listing_repository.update_status(listing.dedupe_key, "Watching")
        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        self._refresh_persistent_listings()
        self._refresh_runtime_stats()

    def _on_status_clicked(self, _button: Gtk.Button, dedupe_key: str, status: str) -> None:
        self.listing_repository.update_status(dedupe_key, status)
        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        self._refresh_persistent_listings()
        self._refresh_runtime_stats()

    def _on_import_pc_clicked(self, _button: Gtk.Button) -> None:
        self._open_pc_import_window()

    def _open_pc_import_window(self) -> None:
        existing_window = getattr(self, "pc_import_window", None)

        if existing_window is not None:
            existing_window.present()
            return

        command = "inxi -Fx"

        window = Gtk.Window()
        window.set_title("Import Current PC Specs")
        window.set_transient_for(self)
        window.set_modal(True)
        window.set_default_size(900, 700)
        window.connect("close-request", self._on_pc_import_window_closed)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)
        window.set_child(root)

        root.append(self._heading("Import Current PC Specs"))
        root.append(
            self._muted_label(
                "Linux-first import. Copy the command below, run it in your terminal, then paste the full output back into DealWise."
            )
        )

        command_card = Gtk.Frame()
        command_card.add_css_class("card")

        command_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        command_box.set_margin_top(14)
        command_box.set_margin_bottom(14)
        command_box.set_margin_start(14)
        command_box.set_margin_end(14)

        command_box.append(self._subheading("Step 1 — Copy this command"))

        command_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        command_entry = Gtk.Entry()
        command_entry.set_text(command)
        command_entry.set_editable(False)
        command_entry.set_hexpand(True)

        copy_button = Gtk.Button(label="Copy Command")
        copy_button.connect("clicked", self._on_copy_pc_import_command_clicked, command)

        command_row.append(command_entry)
        command_row.append(copy_button)
        command_box.append(command_row)

        install_hint = self._muted_label(
            "If inxi is missing, install it with: sudo apt install inxi"
        )
        command_box.append(install_hint)

        command_card.set_child(command_box)
        root.append(command_card)

        paste_card = Gtk.Frame()
        paste_card.add_css_class("card")
        paste_card.set_vexpand(True)

        paste_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        paste_box.set_margin_top(14)
        paste_box.set_margin_bottom(14)
        paste_box.set_margin_start(14)
        paste_box.set_margin_end(14)

        paste_box.append(self._subheading("Step 2 — Paste terminal output here"))

        self.pc_import_text_view = Gtk.TextView()
        self.pc_import_text_view.set_monospace(True)
        self.pc_import_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.pc_import_text_view.set_vexpand(True)
        self.pc_import_text_buffer = self.pc_import_text_view.get_buffer()

        paste_scroll = Gtk.ScrolledWindow()
        paste_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        paste_scroll.set_vexpand(True)
        paste_scroll.set_child(self.pc_import_text_view)
        paste_box.append(paste_scroll)

        paste_card.set_child(paste_box)
        root.append(paste_card)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        import_button = Gtk.Button(label="Import Pasted Specs")
        import_button.add_css_class("suggested-action")
        import_button.connect("clicked", self._on_import_pc_pasted_output_clicked)

        clear_paste_button = Gtk.Button(label="Clear Pasted Text")
        clear_paste_button.connect("clicked", self._on_clear_pc_import_paste_clicked)

        clear_saved_button = Gtk.Button(label="Clear Saved PC")
        clear_saved_button.connect("clicked", self._on_clear_current_pc_clicked)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _button: window.close())

        button_row.append(import_button)
        button_row.append(clear_paste_button)
        button_row.append(clear_saved_button)
        button_row.append(close_button)
        root.append(button_row)

        self.pc_import_status_label = self._muted_label(
            "Ready. Paste the output from inxi -Fx, then click Import Pasted Specs."
        )
        root.append(self.pc_import_status_label)

        self.pc_import_window = window
        window.present()

    def _on_pc_import_window_closed(self, _window: Gtk.Window) -> bool:
        self.pc_import_window = None
        return False

    def _on_copy_pc_import_command_clicked(self, _button: Gtk.Button, command: str) -> None:
        copied = self._copy_text_to_clipboard(command)

        if copied:
            self._set_pc_import_status("Command copied. Run it in terminal, then paste the output below.")
        else:
            self._set_pc_import_status("Could not copy automatically. Select the command text and copy it manually.")

    def _on_import_pc_pasted_output_clicked(self, _button: Gtk.Button) -> None:
        if not hasattr(self, "pc_import_text_buffer"):
            return

        start_iter, end_iter = self.pc_import_text_buffer.get_bounds()
        raw_output = self.pc_import_text_buffer.get_text(start_iter, end_iter, False).strip()

        if not raw_output:
            self._set_pc_import_status("Paste the inxi -Fx output before importing.")
            return

        current_pc = self.pc_builder_service.import_current_pc_from_text(raw_output)
        self._refresh_pc_builder()

        self._set_pc_import_status(
            f"Imported current PC specs. Detected: {current_pc.system_model}"
        )

    def _on_clear_pc_import_paste_clicked(self, _button: Gtk.Button) -> None:
        if hasattr(self, "pc_import_text_buffer"):
            self.pc_import_text_buffer.set_text("")

        self._set_pc_import_status("Pasted text cleared.")

    def _on_clear_current_pc_clicked(self, _button: Gtk.Button) -> None:
        self.pc_builder_service.clear_current_pc()
        self._refresh_pc_builder()
        self._set_pc_import_status("Saved current PC profile cleared.")

    def _set_pc_import_status(self, message: str) -> None:
        status_label = getattr(self, "pc_import_status_label", None)

        if status_label is not None:
            status_label.set_text(message)

    def _copy_text_to_clipboard(self, text: str) -> bool:
        display = Gdk.Display.get_default()

        if display is None:
            return False

        clipboard = display.get_clipboard()

        try:
            clipboard.set_text(text)
            return True
        except AttributeError:
            pass

        try:
            clipboard.set(text)
            return True
        except Exception:
            return False

    def _on_save_target_build_clicked(self, _button: Gtk.Button) -> None:
        self.pc_builder_service.save_target_build(
            total_budget=self._current_budget(),
            use_case=self._effective_use_case(),
            platform=self._current_build_path(),
            notes=self._get_target_notes(),
        )
        self._refresh_pc_builder()

    def _on_part_status_clicked(self, _button: Gtk.Button, part_id: int, status: str) -> None:
        self.pc_builder_service.update_part_status(part_id, status)
        self.active_build_service.set_part_status(self.pc_builder_service.get_part(part_id).part_type, status) if hasattr(self.pc_builder_service, "get_part") else None
        self.active_build_service.pause_obsolete_saved_searches(self.config_manager)
        self.active_build_service.clear_stale_live_results(self.search_manager)
        self._refresh_pc_builder()
        self._refresh_live_results(force=True)
        self._refresh_saved_searches()

    def _on_analyse_listing_clicked(self, _button: Gtk.Button) -> None:
        title = self.checker_title_entry.get_text().strip()
        url = self.checker_url_entry.get_text().strip()
        marketplace = self.checker_marketplace_entry.get_text().strip() or "Manual"
        price = self._price_or_none(self.checker_price_input.get_value())
        part_type = self._dropdown_text(self.checker_part_dropdown)
        notes = self.checker_notes_entry.get_text().strip()

        if not title and not url:
            self._show_checker_result(["Add at least a title or URL first."])
            return

        stored = self.listing_repository.add_manual_listing(
            title=title or url,
            url=url,
            price=price,
            marketplace=marketplace,
            part_type=part_type,
            notes=notes,
        )

        target = self.pc_builder_service.get_target_build()
        decision = self.listing_intelligence_service.analyse_stored_listing(
            stored,
            budget=target.total_budget,
        )

        lines = [
            f"Saved listing: {stored.title}",
            f"Decision: {decision.decision}",
            f"Deal Score: {decision.deal_score}/100",
            f"Scam Risk: {decision.scam_risk}/10",
            f"Build Fit: {decision.build_fit}/100",
            f"Budget Fit: {decision.budget_fit}/100",
            f"Evidence Confidence: {decision.evidence_confidence}/100",
            "Reasoning / Risk Flags:",
            *[f"- {reason}" for reason in decision.reasoning],
            "",
            "Seller Message / Evidence Request:",
            decision.seller_message,
        ]

        self._show_checker_result(lines)
        self._refresh_persistent_listings()

    def _refresh_runtime_stats(self) -> bool:
        stats = self.search_manager.get_stats()
        db_count = self.listing_repository.count_all()

        values = {
            "saved_searches": str(stats.saved_searches),
            "searches_running": str(stats.searches_running),
            "live_results": str(stats.live_results),
            "db_listings": str(db_count),
            "listings_analysed": str(stats.listings_analysed),
            "refreshes_completed": str(stats.refreshes_completed),
            "connector_status": stats.connector_status,
            "running_since": self._format_datetime(stats.running_since),
            "last_refresh": self._format_datetime(stats.last_refresh_at),
        }

        for key, value in values.items():
            label = self.stat_labels.get(key)
            if label is not None:
                label.set_text(value)

        return True

    def _refresh_saved_searches(self) -> None:
        if not hasattr(self, "saved_search_list"):
            return

        self._clear_listbox(self.saved_search_list)
        searches = self.config_manager.load_saved_searches()

        if not searches:
            self.saved_search_list.append(self._simple_row("No saved searches yet. Add one above."))
            return

        for search in searches:
            self.saved_search_list.append(self._saved_search_row(search))

    def _refresh_live_results(self, force: bool = False) -> bool:
        if not hasattr(self, "worth_live_list"):
            return True

        stats = self.search_manager.get_stats()

        favourites = self._filter_stored_live_results(
            self.listing_repository.list_favourites(limit=25)
        )

        live_results = self.search_manager.get_live_results(limit=250)
        filtered_live_results = self._filter_and_sort_live_results(live_results)

        hidden_results = []
        hidden_keys: set[str] = set()

        if hasattr(self.search_manager, "get_hidden_results"):
            hidden_results = self.search_manager.get_hidden_results(limit=100)
            hidden_keys = {listing.dedupe_key for listing in hidden_results}

        live_keys = {listing.dedupe_key for listing in filtered_live_results}

        database_results = self._filter_and_sort_stored_results(
            self.listing_repository.list_recent(limit=300),
            excluded_keys=live_keys | hidden_keys,
        )

        total_visible = len(filtered_live_results) + len(database_results)
        max_cards = 60
        visible_live_results = filtered_live_results[:max_cards]
        remaining_slots = max(0, max_cards - len(visible_live_results))
        visible_database_results = database_results[:remaining_slots]
        rendered_count = len(visible_live_results) + len(visible_database_results)

        # Hard UX rule: if there are search results, results section is open and saved is closed.
        if total_visible > 0:
            self._worth_live_expanded = True
            self._saved_live_expanded = False
        else:
            if hasattr(self, "saved_live_expander"):
                self._saved_live_expanded = self.saved_live_expander.get_expanded()

            if hasattr(self, "worth_live_expander"):
                self._worth_live_expanded = self.worth_live_expander.get_expanded()

        if hasattr(self, "saved_live_expander"):
            self.saved_live_expander.set_label(f"Saved / Favourited Deals ({len(favourites)})")

        if hasattr(self, "worth_live_expander"):
            self.worth_live_expander.set_label(f"New / Worth Checking ({total_visible})")

        if hasattr(self, "hidden_live_expander"):
            self.hidden_live_expander.set_label(f"Hidden Deals ({len(hidden_results)})")

        if hasattr(self, "live_results_hint_label"):
            if total_visible > 0:
                self.live_results_hint_label.set_text(
                    "Results are shown below filters. Saved deals are collapsed underneath so they do not hide fresh matches."
                )
            else:
                self.live_results_hint_label.set_text(
                    "No visible matches yet. Choose Part/Product, use Search Selected Filter, or Clear Filters."
                )

        if hasattr(self, "live_status_label"):
            if total_visible > max_cards:
                shown_text = f"Showing first {max_cards} of {total_visible}"
            else:
                shown_text = f"Showing {total_visible}"

            self.live_status_label.set_text(
                f"{stats.connector_status} {shown_text} result(s): "
                f"{len(filtered_live_results)} live, {len(database_results)} from database. "
                f"Hidden: {len(hidden_results)}."
            )

        signature = "|".join(
            [
                self._live_signature("", favourites, visible_live_results),
                "db=" + ",".join(f"{listing.dedupe_key}:{listing.status}:{listing.price}" for listing in visible_database_results),
                "hidden=" + ",".join(listing.dedupe_key for listing in hidden_results),
                f"counts={total_visible}:{len(favourites)}:{len(hidden_results)}",
            ]
        )

        if not force and signature == self._live_render_signature:
            if hasattr(self, "worth_live_expander") and total_visible > 0:
                self.worth_live_expander.set_expanded(True)
            if hasattr(self, "saved_live_expander") and total_visible > 0:
                self.saved_live_expander.set_expanded(False)
            return True

        self._live_render_signature = signature

        self._clear_listbox(self.worth_live_list)
        self._clear_listbox(self.saved_live_list)

        if hasattr(self, "hidden_live_list"):
            self._clear_listbox(self.hidden_live_list)

            if hidden_results:
                for listing in hidden_results:
                    self.hidden_live_list.append(self._hidden_listing_row(listing))
            else:
                self.hidden_live_list.append(
                    self._simple_row("No hidden deals. Removed live deals will appear here so they can be restored.")
                )

        if not visible_live_results and not visible_database_results:
            self.worth_live_list.append(
                self._simple_row(
                    "No results match the current filters. Pick Part/Product, click Search Selected Filter, or clear filters."
                )
            )
        else:
            if total_visible > max_cards:
                self.worth_live_list.append(
                    self._simple_row(
                        f"Showing first {rendered_count} of {total_visible} matching results. Narrow by Part, Product, Search, Max Price or Sort to reduce lag."
                    )
                )

            for listing in visible_live_results:
                self.worth_live_list.append(self._listing_row(listing))

            for listing in visible_database_results:
                self.worth_live_list.append(self._stored_listing_row(listing))

        if not favourites:
            self.saved_live_list.append(
                self._simple_row("No saved deals match the current filters. Clear filters to see all saved deals.")
            )
        else:
            for listing in favourites:
                self.saved_live_list.append(self._stored_listing_row(listing))

        if hasattr(self, "worth_live_expander"):
            self.worth_live_expander.set_expanded(self._worth_live_expanded)

        if hasattr(self, "saved_live_expander"):
            self.saved_live_expander.set_expanded(self._saved_live_expanded)

        return True

    def _refresh_persistent_listings(self) -> bool:
        if not hasattr(self, "persistent_listings_list"):
            return True

        self._clear_listbox(self.persistent_listings_list)
        listings = self.listing_repository.list_recent(limit=100)

        if not listings:
            self.persistent_listings_list.append(
                self._simple_row("No stored listings yet. Run a search or use Listing Checker.")
            )
            return True

        for listing in listings:
            self.persistent_listings_list.append(self._stored_listing_row(listing))

        return True

    def _refresh_pc_builder(self) -> None:
        if not hasattr(self, "pc_summary_box"):
            return

        self._clear_box(self.pc_summary_box)


        if hasattr(self, "pc_summary_box"):
            self.pc_summary_box.append(
                self._section_card(
                    "Active Build Hunt Summary",
                    self.active_build_service.active_hunt_lines(),
                )
            )
            self.pc_summary_box.append(
                self._section_card(
                    "Bought Parts + Remaining Budget",
                    self.active_build_service.cost_overview_lines(),
                )
            )
            self.pc_summary_box.append(
                self._section_card(
                    "Active Search Plan",
                    self.active_build_service.search_plan_lines(),
                )
            )

        if hasattr(self, "compatibility_box"):
            self._clear_box(self.compatibility_box)

        current_pc = self.pc_builder_service.get_current_pc()
        target = self.pc_builder_service.get_target_build()
        parts = self.pc_builder_service.list_build_parts()

        selected_use_case = self._current_use_case()
        selected_build_path = self._current_build_path()
        selected_budget = self._current_budget()
        selected_notes = self._get_target_notes()
        selected_hardware_preference = self._current_hardware_preference()

        bought_count = sum(1 for part in parts if part.status == "Bought")
        needed_count = sum(1 for part in parts if part.status == "Needed")
        candidate_count = sum(1 for part in parts if part.status in {"Buying Candidate", "Evidence Requested"})
        paused_count = sum(1 for part in parts if part.status in {"Stop Searching", "Upgrade Later", "Not Looking"})
        cost_low, cost_high = self.pc_builder_service.estimate_build_cost(selected_build_path)
        remaining_low = selected_budget - cost_high
        remaining_high = selected_budget - cost_low

        if current_pc is None:
            self.pc_summary_box.append(
                self._key_value_card(
                    "Current PC Snapshot",
                    [
                        ("Status", "No current PC imported yet."),
                        ("Action", "Click Import Current PC to copy the Linux command and paste the response back."),
                        ("Result", "DealWise will then show upgrade limits and resale estimate."),
                    ],
                )
            )
        else:
            self.pc_summary_box.append(
                self._key_value_card(
                    "Current PC Snapshot",
                    [
                        ("System", current_pc.system_model),
                        ("CPU", self._shorten_text(current_pc.cpu, 130)),
                        ("GPU", self._shorten_text(current_pc.gpu, 160)),
                        ("Memory", current_pc.memory),
                        ("Storage", current_pc.storage),
                        ("Distro", current_pc.distro),
                        ("Upgrade Notes", current_pc.form_factor_notes),
                    ],
                )
            )

            valuation = self.pc_builder_service.estimate_current_pc_value(current_pc)
            self.pc_summary_box.append(
                self._key_value_card(
                    "Estimated Resale Value",
                    [
                        ("Whole PC Estimate", f"£{valuation.whole_unit_low} - £{valuation.whole_unit_high}"),
                        ("Separate Parts Estimate", f"£{valuation.separate_parts_low} - £{valuation.separate_parts_high}"),
                        ("Confidence", valuation.confidence),
                        ("Best Practical Read", "Separate parts may earn more, but selling the full PC is easier and faster."),
                        ("Notes", " ".join(valuation.notes)),
                    ],
                    emphasise_values=True,
                )
            )

        self.pc_summary_box.append(
            self._key_value_card(
                "Target Build Summary",
                [
                    ("Budget", f"£{selected_budget:.0f}"),
                    ("Selected Use Case", selected_use_case),
                    ("Selected Build Path", selected_build_path),
                    ("Hardware Preference", selected_hardware_preference),
                    ("Live Notes", selected_notes or "No notes added yet."),
                ],
            )
        )

        self.pc_summary_box.append(
            self._key_value_card(
                "Build Cost Overview",
                [
                    ("Estimated Parts Cost", f"£{cost_low} - £{cost_high}"),
                    ("Budget Remaining After Low Estimate", f"£{remaining_high:.0f}"),
                    ("Budget Remaining After High Estimate", f"£{remaining_low:.0f}"),
                    ("Bought Parts", str(bought_count)),
                    ("Buying Candidates", str(candidate_count)),
                    ("Search Paused", str(paused_count)),
                    ("Still Needed", str(needed_count)),
                    ("Budget Warning", "High estimate is above budget." if remaining_low < 0 else "Current selected parts fit within budget range."),
                ],
                emphasise_values=True,
            )
        )

        progress_lines = []
        for part in parts:
            marker = "✓" if part.status == "Bought" else ("◐" if part.status in {"Buying Candidate", "Evidence Requested"} else "□")
            progress_lines.append(f"{marker} {part.part_type}: {part.target} — {part.status}")

        if progress_lines:
            self.pc_summary_box.append(
                self._section_card(
                    "Wishlist Progress",
                    progress_lines,
                )
            )

        if hasattr(self, "compatibility_box"):
            self.compatibility_box.append(
                self._section_card(
                    "Compatibility Filter",
                    self.pc_builder_service.compatibility_summary(selected_build_path, self._effective_use_case()),
                )
            )

            self.compatibility_box.append(
                self._section_card(
                    "Selected Parts Compatibility",
                    self.compatibility_service.analyse_build(
                        parts,
                        selected_build_path,
                        selected_hardware_preference,
                    ),
                )
            )

            search_queries = self.pc_builder_service.needed_part_search_queries(selected_build_path)

            self.compatibility_box.append(
                self._section_card(
                    "Search Plan",
                    [
                        "Search Needed Parts will create or refresh Vinted searches for:",
                        *[f"- {query}" for query in search_queries],
                    ],
                )
            )

            self.compatibility_box.append(
                self._section_card(
                    "Search Builder",
                    [
                        "Search Terms:",
                        *[f"- {query}" for query in search_queries],
                        "",
                        "Negative Keywords:",
                        "- broken",
                        "- faulty",
                        "- spares",
                        "- repair",
                        "- wanted",
                        "- laptop / notebook",
                        "",
                        "Selected Marketplaces:",
                        "- Vinted enabled now",
                        "- eBay / CeX / Gumtree planned for Phase 7",
                    ],
                )
            )

        if hasattr(self, "parts_list"):
            self._clear_listbox(self.parts_list)
            for part in parts:
                self.parts_list.append(self._build_part_row(part))

    def _show_checker_result(self, lines: list[str]) -> None:
        self._clear_box(self.checker_result_box)
        self.checker_result_box.append(self._section_card("Analysis Result", lines))

    def _saved_search_row(self, search: SavedSearch) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        wrapper.set_margin_top(12)
        wrapper.set_margin_bottom(12)
        wrapper.set_margin_start(12)
        wrapper.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=search.query, xalign=0)
        title.add_css_class("row-title")

        meta = Gtk.Label(
            label=f"{search.marketplace} • {search.price_range_label()} • {search.condition} • every {search.refresh_interval_minutes}m",
            xalign=0,
        )
        meta.add_css_class("muted")

        details.append(title)
        details.append(meta)

        delete_button = Gtk.Button(label="Delete")
        delete_button.connect("clicked", self._on_delete_search_clicked, search.id)

        wrapper.append(details)
        wrapper.append(delete_button)
        row.set_child(wrapper)
        return row

    def _listing_row(self, listing: MarketplaceListing) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        decision = self._analyse_marketplace_listing(listing)

        frame = Gtk.Frame()
        frame.add_css_class("deal-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(14)
        outer.set_margin_bottom(14)
        outer.set_margin_start(14)
        outer.set_margin_end(14)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        decision_label = Gtk.Label(label=decision.decision)
        decision_label.add_css_class("decision-badge")

        title = Gtk.Label(label=listing.title, xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)
        title.set_hexpand(True)

        header.append(decision_label)
        header.append(title)
        outer.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        image_box = self._listing_image_widget(listing.image_url)
        body.append(image_box)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        details.set_hexpand(True)

        part_type = infer_part_type(listing.title)

        meta_parts = [listing.marketplace, listing.price_label(), f"Type: {part_type}"]
        if listing.seller_name:
            meta_parts.append(f"Seller: {listing.seller_name}")
        if listing.source_query:
            meta_parts.append(f"Search: {listing.source_query}")

        meta = Gtk.Label(label=" • ".join(meta_parts), xalign=0)
        meta.add_css_class("muted")
        meta.set_wrap(True)

        scores = Gtk.Label(
            label=(
                f"Deal {decision.deal_score}/100  •  Scam {decision.scam_risk}/10  •  "
                f"Build fit {decision.build_fit}/100  •  Evidence {decision.evidence_confidence}/100"
            ),
            xalign=0,
        )
        scores.add_css_class("score-line")
        scores.set_wrap(True)

        history = Gtk.Label(label=" | ".join(self._price_history_lines_for_title(listing.title)), xalign=0)
        history.add_css_class("muted")
        history.set_wrap(True)

        compatibility = Gtk.Label(label=" | ".join(self._compatibility_lines_for_title(listing.title)), xalign=0)
        compatibility.add_css_class("muted")
        compatibility.set_wrap(True)

        reasoning_text = " | ".join(decision.reasoning[:3])
        reasoning = Gtk.Label(label=reasoning_text, xalign=0)
        reasoning.add_css_class("muted")
        reasoning.set_wrap(True)

        url_label = Gtk.Label(label=listing.url, xalign=0)
        url_label.add_css_class("muted")
        url_label.set_wrap(True)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self._on_save_live_listing_clicked, listing)

        remove_button = Gtk.Button(label="Remove")
        remove_button.connect("clicked", self._on_remove_live_listing_clicked, listing)

        open_button = Gtk.Button(label="Open")
        open_button.connect("clicked", self._on_open_listing_clicked, listing.url)

        image_button = Gtk.Button(label="Image Check")
        image_button.connect("clicked", self._on_image_check_clicked, listing.image_url)

        score_button = Gtk.Button(label="Score Details")
        score_button.connect("clicked", self._on_score_details_clicked, listing.title, listing.price, decision)

        button_row.append(save_button)
        button_row.append(remove_button)
        button_row.append(open_button)
        button_row.append(image_button)
        button_row.append(score_button)

        details.append(meta)
        details.append(scores)
        details.append(history)
        details.append(compatibility)
        details.append(reasoning)
        details.append(url_label)
        details.append(button_row)

        body.append(details)
        outer.append(body)

        frame.set_child(outer)
        row.set_child(frame)
        return row

    def _stored_listing_row(self, listing: StoredListing) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        decision = self._analyse_stored_listing_with_history(listing)

        frame = Gtk.Frame()
        frame.add_css_class("deal-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        outer.set_margin_top(14)
        outer.set_margin_bottom(14)
        outer.set_margin_start(14)
        outer.set_margin_end(14)

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        status_label = Gtk.Label(label=listing.status)
        status_label.add_css_class("decision-badge")

        title = Gtk.Label(label=listing.title, xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)
        title.set_hexpand(True)

        header.append(status_label)
        header.append(title)
        outer.append(header)

        body = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=14)

        image_box = self._listing_image_widget(listing.image_url)
        body.append(image_box)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6)
        details.set_hexpand(True)

        meta = Gtk.Label(
            label=f"{listing.marketplace} • {listing.price_label()} • {listing.part_type} • Decision: {decision.decision}",
            xalign=0,
        )
        meta.add_css_class("muted")
        meta.set_wrap(True)

        scores = Gtk.Label(
            label=(
                f"Deal {decision.deal_score}/100  •  Scam {decision.scam_risk}/10  •  "
                f"Build fit {decision.build_fit}/100  •  Evidence {decision.evidence_confidence}/100"
            ),
            xalign=0,
        )
        scores.add_css_class("score-line")
        scores.set_wrap(True)

        history = Gtk.Label(label=" | ".join(self._price_history_lines_for_title(listing.title)), xalign=0)
        history.add_css_class("muted")
        history.set_wrap(True)

        compatibility = Gtk.Label(label=" | ".join(self._compatibility_lines_for_title(listing.title)), xalign=0)
        compatibility.add_css_class("muted")
        compatibility.set_wrap(True)

        url_label = Gtk.Label(label=listing.url, xalign=0)
        url_label.add_css_class("muted")
        url_label.set_wrap(True)

        details.append(meta)
        details.append(scores)
        details.append(history)
        details.append(compatibility)

        if listing.notes:
            details.append(self._muted_label(f"Notes: {listing.notes}"))

        details.append(url_label)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)

        fav_button = Gtk.Button(label="Favourite")
        fav_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Favourite")

        watch_button = Gtk.Button(label="Watching")
        watch_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Watching")

        bought_button = Gtk.Button(label="Bought")
        bought_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Bought")

        evidence_button = Gtk.Button(label="Evidence Requested")
        evidence_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Evidence Requested")

        candidate_button = Gtk.Button(label="Buying Candidate")
        candidate_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Buying Candidate")

        avoid_button = Gtk.Button(label="Avoid")
        avoid_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Avoided")

        remove_button = Gtk.Button(label="Remove")
        remove_button.connect("clicked", self._on_delete_stored_listing_clicked, listing.dedupe_key)

        open_button = Gtk.Button(label="Open")
        open_button.connect("clicked", self._on_open_listing_clicked, listing.url)

        image_button = Gtk.Button(label="Image Check")
        image_button.connect("clicked", self._on_image_check_clicked, listing.image_url)

        stored_score_button = Gtk.Button(label="Score Details")
        stored_score_button.connect("clicked", self._on_score_details_clicked, listing.title, listing.price, decision)

        button_row.append(fav_button)
        button_row.append(watch_button)
        button_row.append(bought_button)
        button_row.append(evidence_button)
        button_row.append(candidate_button)
        button_row.append(avoid_button)
        button_row.append(remove_button)
        button_row.append(open_button)
        button_row.append(image_button)
        button_row.append(stored_score_button)

        details.append(button_row)

        body.append(details)
        outer.append(body)

        frame.set_child(outer)
        row.set_child(frame)
        return row

    def _build_part_row(self, part) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        wrapper.set_margin_top(12)
        wrapper.set_margin_bottom(12)
        wrapper.set_margin_start(12)
        wrapper.set_margin_end(12)

        top = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=f"{part.part_type}: {part.target}", xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)

        low, high = self.pc_builder_service.option_cost(
            part.part_type,
            part.target,
            self._current_build_path(),
        )

        meta = Gtk.Label(
            label=(
                f"Budget: £{part.budget:.0f} • Estimated: £{low} - £{high} • "
                f"Bought: £{part.bought_price:.0f} • Status: {part.status}"
            ),
            xalign=0,
        )
        meta.add_css_class("muted")
        meta.set_wrap(True)

        details.append(title)
        details.append(meta)

        options = self.pc_builder_service.part_options(part.part_type, self._current_build_path())
        option_names = [option.name for option in options] or [part.target or part.part_type]

        target_dropdown = Gtk.DropDown.new_from_strings(option_names)
        self._set_dropdown_by_value(target_dropdown, part.target)

        use_button = Gtk.Button(label="Use Selected")
        use_button.connect("clicked", self._on_part_target_selected_clicked, part.id, target_dropdown)

        needed_button = Gtk.Button(label="Needed")
        needed_button.connect("clicked", self._on_part_status_clicked, part.id, "Needed")

        bought_button = Gtk.Button(label="Bought")
        bought_button.connect("clicked", self._on_part_status_clicked, part.id, "Bought")

        candidate_button = Gtk.Button(label="Candidate")
        candidate_button.connect("clicked", self._on_part_status_clicked, part.id, "Buying Candidate")

        later_button = Gtk.Button(label="Later")
        later_button.connect("clicked", self._on_part_status_clicked, part.id, "Upgrade Later")

        stop_search_button = Gtk.Button(label="Stop Searching")
        stop_search_button.connect("clicked", self._on_part_status_clicked, part.id, "Stop Searching")

        top.append(details)
        top.append(target_dropdown)
        top.append(use_button)
        top.append(needed_button)
        top.append(bought_button)
        top.append(candidate_button)
        top.append(later_button)
        top.append(stop_search_button)

        wrapper.append(top)

        if options:
            selected_index = min(len(options) - 1, target_dropdown.get_selected())
            option = options[selected_index]
            wrapper.append(
                self._muted_label(
                    f"Tier {option.tier}: {option.compatibility_note} Estimated used/new range: £{option.estimated_low} - £{option.estimated_high}."
                )
            )

        row.set_child(wrapper)
        return row

    def _on_apply_recommendations_clicked(self, _button: Gtk.Button) -> None:
        self.pc_builder_service.apply_recommended_parts(
            build_path=self._current_build_path(),
            use_case=self._effective_use_case(),
        )
        self._refresh_pc_builder()

    def _on_search_needed_parts_clicked(self, _button: Gtk.Button) -> None:
        self.active_build_service.seed_current_real_build()
        created = self.active_build_service.create_or_refresh_active_searches(
            self.config_manager,
            self.search_manager,
        )
        removed = self.active_build_service.clear_stale_live_results(self.search_manager)

        if hasattr(self, "live_status_label"):
            self.live_status_label.set_text(
                f"Active Build Hunt refreshed. Created {created} active search(es), cleared {removed} stale live result(s)."
            )

        self._refresh_saved_searches()
        self._refresh_pc_builder()
        self._refresh_live_results(force=True)
        self._refresh_runtime_stats()

    def _on_part_target_selected_clicked(self, _button: Gtk.Button, part_id: int, dropdown: Gtk.DropDown) -> None:
        target = self._dropdown_text(dropdown)
        self.pc_builder_service.update_part_target(part_id, target)
        self._refresh_pc_builder()

    def _on_target_selection_changed(self, *_args) -> None:
        self._refresh_pc_builder()

    def _on_image_check_clicked(self, _button: Gtk.Button, image_url: str | None) -> None:
        if not image_url:
            return

        # Phase 5 foundation: open the raw image URL for manual inspection.
        # Later this can hand off to a reverse-image provider.
        webbrowser.open(image_url)

    def _listing_matches_needed_parts(self, listing: MarketplaceListing) -> bool:
        title = listing.title.lower()
        queries = self.pc_builder_service.needed_part_search_queries(self._current_build_path())

        if not queries:
            return True

        for query in queries:
            important_terms = [
                term.lower()
                for term in query.replace("/", " ").replace("-", " ").split()
                if len(term) >= 3
            ]

            if important_terms and all(term in title for term in important_terms[:2]):
                return True

            if query.lower() in title:
                return True

        return False

    def _listing_image_widget(self, image_url: str | None) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.add_css_class("image-card")
        frame.set_size_request(120, 100)

        placeholder = Gtk.Label(label="No image")
        placeholder.add_css_class("muted")
        frame.set_child(placeholder)

        if not image_url:
            return frame

        loading = Gtk.Label(label="Loading image...")
        loading.add_css_class("muted")
        frame.set_child(loading)

        def make_picture(path) -> Gtk.Picture | None:
            if path is None:
                return None

            picture = Gtk.Picture()
            picture.set_size_request(120, 100)

            try:
                picture.set_content_fit(Gtk.ContentFit.COVER)
            except AttributeError:
                pass

            try:
                texture = Gdk.Texture.new_from_filename(str(path))
                picture.set_paintable(texture)
                return picture
            except Exception:
                try:
                    picture.set_filename(str(path))
                    return picture
                except Exception:
                    return None

        cached_path = None

        if hasattr(self.image_cache, "cached_path_for_url"):
            cached_path = self.image_cache.cached_path_for_url(image_url)

        cached_picture = make_picture(cached_path)

        if cached_picture is not None:
            frame.set_child(cached_picture)
            return frame

        def apply_image(path):
            picture = make_picture(path)

            if picture is not None:
                current_child = frame.get_child()

                if current_child is loading:
                    frame.set_child(picture)

            return False

        self.image_cache.fetch_async(image_url, apply_image)
        return frame

    def _on_live_part_filter_changed(self, *_args) -> None:
        if not hasattr(self, "live_product_dropdown"):
            return

        part = self._dropdown_text(self.live_part_dropdown)
        options = LIVE_PRODUCT_FILTERS.get(part, LIVE_PRODUCT_FILTERS["All Parts"])

        self.live_product_dropdown.set_model(Gtk.StringList.new(options))
        self.live_product_dropdown.set_selected(0)

    def _current_live_search_query(self) -> str:
        typed_query = self.live_search_entry.get_text().strip() if hasattr(self, "live_search_entry") else ""

        if typed_query:
            return typed_query

        product = self._current_product_filter() if hasattr(self, "live_product_dropdown") else "Any Product"
        part = self._dropdown_text(self.live_part_dropdown) if hasattr(self, "live_part_dropdown") else "All Parts"

        if product and not product.startswith("Any "):
            if part == "PSU" and "psu" not in product.lower():
                return f"{product} PSU"
            if part == "Motherboard" and "motherboard" not in product.lower():
                return f"{product} motherboard"
            if part == "Storage" and "ssd" not in product.lower() and "nvme" not in product.lower():
                return f"{product} SSD"
            return product

        selected_targets = {
            build_part.part_type: build_part.target
            for build_part in self.pc_builder_service.list_build_parts()
        }

        fallback_by_part = {
            "PSU": selected_targets.get("PSU") or "750W Gold PSU",
            "Motherboard": selected_targets.get("Motherboard") or "B650 motherboard",
            "GPU": selected_targets.get("GPU") or "RX 6800",
            "CPU": selected_targets.get("CPU") or "Ryzen 7 7800X3D",
            "RAM": selected_targets.get("RAM") or "32GB DDR5",
            "Storage": selected_targets.get("Storage") or "2TB NVMe SSD",
            "Case": selected_targets.get("Case") or "ATX airflow case",
            "Cooling": selected_targets.get("Cooling") or "Thermalright CPU cooler",
            "Full PC": "AM5 gaming PC",
        }

        query = fallback_by_part.get(part, "")

        if part == "PSU" and query and "psu" not in query.lower() and "power supply" not in query.lower():
            query = f"{query} PSU"

        if part == "Motherboard" and query and "motherboard" not in query.lower():
            query = f"{query} motherboard"

        if part == "Storage" and query and "ssd" not in query.lower() and "nvme" not in query.lower():
            query = f"{query} SSD"

        return query.strip()

    def _on_search_live_text_clicked(self, _button: Gtk.Button) -> None:
        query = self._current_live_search_query()

        if not query:
            if hasattr(self, "live_status_label"):
                self.live_status_label.set_text("Choose a Part/Product or type a search first.")
            return

        search = SavedSearch.create(
            query=query,
            marketplace="Vinted",
            min_price=None,
            max_price=self._price_or_none(self.live_max_price_input.get_value()) if hasattr(self, "live_max_price_input") else None,
            condition="Any",
            excluded_keywords=[
                "broken",
                "faulty",
                "spares",
                "repair",
                "wanted",
                "laptop",
                "notebook",
                "zenbook",
                "macbook",
                "ipad",
                "tablet",
                "camera",
                "airpods",
                "enclosure",
                "external",
            ],
            refresh_interval_minutes=5,
        )

        started = self.search_manager.refresh_search(search, manual=True)

        if hasattr(self, "live_status_label"):
            if started:
                self.live_status_label.set_text(f"Searching Vinted once for: {query}")
            else:
                self.live_status_label.set_text("Search could not start. Check cooldown or connector status.")

        self._refresh_runtime_stats()

    def _on_clear_stale_live_results_clicked(self, _button: Gtk.Button) -> None:
        removed = self.active_build_service.clear_stale_live_results(self.search_manager)

        if hasattr(self, "live_status_label"):
            self.live_status_label.set_text(
                f"Cleared {removed} stale live result(s). Database listings and price history were preserved."
            )

        self._refresh_live_results(force=True)
        self._refresh_runtime_stats()

    def _on_apply_live_filters_clicked(self, _button: Gtk.Button) -> None:
        self._saved_live_expanded = False
        self._worth_live_expanded = True
        self._live_render_signature = ""
        self._refresh_live_results(force=True)

    def _on_clear_live_filters_clicked(self, _button: Gtk.Button) -> None:
        if hasattr(self, "live_search_entry"):
            self.live_search_entry.set_text("")

        if hasattr(self, "live_focus_dropdown"):
            self.live_focus_dropdown.set_selected(0)

        if hasattr(self, "live_part_dropdown"):
            self.live_part_dropdown.set_selected(0)

        if hasattr(self, "live_product_dropdown"):
            self.live_product_dropdown.set_model(Gtk.StringList.new(LIVE_PRODUCT_FILTERS["All Parts"]))
            self.live_product_dropdown.set_selected(0)

        if hasattr(self, "live_priority_dropdown"):
            self.live_priority_dropdown.set_selected(1)

        if hasattr(self, "live_sort_dropdown"):
            self.live_sort_dropdown.connect("notify::selected", self._on_live_filter_debounced)
        self.live_sort_dropdown.set_selected(0)

        if hasattr(self, "live_max_price_input"):
            self.live_max_price_input.set_value(0)

        if hasattr(self, "live_hide_high_scam_check"):
            self.live_hide_high_scam_check.set_active(False)

        self._live_render_signature = ""
        self._refresh_live_results(force=True)

    def _current_hardware_preference(self) -> str:
        if hasattr(self, "hardware_preference_dropdown"):
            return self._dropdown_text(self.hardware_preference_dropdown)

        return "Best value / mixed"

    def _effective_use_case(self) -> str:
        return f"{self._current_use_case()} | {self._current_hardware_preference()}"

    def _on_hardware_preference_changed(self, *_args) -> None:
        preference = self._current_hardware_preference().lower()

        if "intel cpu" in preference and hasattr(self, "target_platform_dropdown"):
            self._set_dropdown_by_value(self.target_platform_dropdown, "Intel LGA1700 / DDR5")
        elif ("amd cpu" in preference or "linux mint" in preference) and hasattr(self, "target_platform_dropdown"):
            self._set_dropdown_by_value(self.target_platform_dropdown, "AM5 / ATX target")

        self._on_target_input_changed()

    def _analyse_marketplace_listing(self, listing: MarketplaceListing):
        decision = self.listing_intelligence_service.analyse(
            title=listing.title,
            price=listing.price,
            url=listing.url,
            marketplace=listing.marketplace,
            part_type=infer_part_type(listing.title),
            budget=self.pc_builder_service.get_target_build().total_budget,
        )
        self._apply_price_history_to_decision(decision, listing.title, listing.price)
        return decision

    def _analyse_stored_listing_with_history(self, listing: StoredListing):
        decision = self.listing_intelligence_service.analyse_stored_listing(
            listing,
            budget=self.pc_builder_service.get_target_build().total_budget,
        )
        self._apply_price_history_to_decision(decision, listing.title, listing.price)
        return decision

    def _apply_price_history_to_decision(self, decision, title: str, price: float | None) -> None:
        if price is None:
            return

        stats = self.price_history_service.stats_for_title(title)

        if stats is None or stats.sample_count < 2 or stats.average_price <= 0:
            return

        if price <= stats.lowest_price:
            decision.deal_score = min(100, decision.deal_score + 12)
            decision.urgency_score = min(100, decision.urgency_score + 10)
            decision.reasoning.insert(0, "Phase 6 history: this is at or below the lowest observed DealWise price.")
        elif price <= stats.average_price * 0.90:
            decision.deal_score = min(100, decision.deal_score + 8)
            decision.reasoning.insert(0, "Phase 6 history: this is below the observed average price.")
        elif price >= stats.average_price * 1.15:
            decision.deal_score = max(0, decision.deal_score - 10)
            decision.reasoning.insert(0, "Phase 6 history: this is above the observed average price.")

        decision.decision = self.listing_intelligence_service._choose_decision(
            deal_score=decision.deal_score,
            scam_risk=decision.scam_risk,
            budget_fit=decision.budget_fit,
            evidence_confidence=decision.evidence_confidence,
        )

    def _price_history_lines_for_title(self, title: str) -> list[str]:
        stats = self.price_history_service.stats_for_title(title)

        if stats is None or stats.sample_count < 2:
            return ["Price History: learning from distinct seen listings. More clean samples needed."]

        return [
            f"Price History: {stats.sample_count} sample(s)",
            f"Observed Range: {stats.range_label()}",
            f"Observed Average: {stats.average_label()}",
        ]

    def _historical_price_rank(self, title: str, price: float | None) -> float:
        if price is None:
            return 0

        stats = self.price_history_service.stats_for_title(title)

        if stats is None or stats.average_price <= 0:
            return 0

        return max(0, stats.average_price - price)

    def _compatibility_lines_for_title(self, title: str) -> list[str]:
        return self.compatibility_service.listing_notes(
            title,
            self._current_build_path(),
            self._current_hardware_preference(),
        )

    def _current_use_case(self) -> str:
        if hasattr(self, "target_use_case_dropdown"):
            return self._dropdown_text(self.target_use_case_dropdown)

        return self.pc_builder_service.get_target_build().use_case

    def _current_hardware_preference(self) -> str:
        if hasattr(self, "hardware_preference_dropdown"):
            return self._dropdown_text(self.hardware_preference_dropdown)

        return "Best value / mixed"

    def _effective_use_case(self) -> str:
        return f"{self._current_use_case()} | {self._current_hardware_preference()}"

    def _on_hardware_preference_changed(self, *_args) -> None:
        preference = self._current_hardware_preference().lower()

        if "intel cpu" in preference and hasattr(self, "target_platform_dropdown"):
            self._set_dropdown_by_value(self.target_platform_dropdown, "Intel LGA1700 / DDR5")
        elif ("amd cpu" in preference or "linux mint" in preference) and hasattr(self, "target_platform_dropdown"):
            self._set_dropdown_by_value(self.target_platform_dropdown, "AM5 / ATX target")

        self._on_target_input_changed()

    def _current_build_path(self) -> str:
        if hasattr(self, "target_platform_dropdown"):
            return self._dropdown_text(self.target_platform_dropdown)

        return self.pc_builder_service.get_target_build().platform

    def _get_target_notes(self) -> str:
        if not hasattr(self, "target_notes_buffer"):
            return self.pc_builder_service.get_target_build().notes

        start_iter, end_iter = self.target_notes_buffer.get_bounds()
        return self.target_notes_buffer.get_text(start_iter, end_iter, False)

    def _set_dropdown_by_value(self, dropdown: Gtk.DropDown, value: str) -> None:
        model = dropdown.get_model()

        if model is None:
            return

        for index in range(model.get_n_items()):
            item = model.get_item(index)

            if item is not None and item.get_string() == value:
                dropdown.set_selected(index)
                return

        dropdown.set_selected(0)

    def _shorten_text(self, text: str, limit: int) -> str:
        if len(text) <= limit:
            return text

        return text[: limit - 3] + "..."

    def _on_target_input_changed(self, *_args) -> None:
        if self._pc_builder_refresh_timer_id is not None:
            return

        self._pc_builder_refresh_timer_id = GLib.timeout_add(
            250,
            self._run_scheduled_pc_builder_refresh,
        )

    def _run_scheduled_pc_builder_refresh(self) -> bool:
        self._pc_builder_refresh_timer_id = None
        self._refresh_pc_builder()
        return False

    def _on_live_filter_changed(self, *_args) -> None:
        # Kept for backward compatibility. Filters are now applied manually
        # through the Apply Filters button to reduce janky rebuilds.
        return

    def _on_live_part_filter_changed(self, *_args) -> None:
        if not hasattr(self, "live_product_dropdown"):
            return

        part = self._dropdown_text(self.live_part_dropdown)
        options = LIVE_PRODUCT_FILTERS.get(part, LIVE_PRODUCT_FILTERS["All Parts"])

        self.live_product_dropdown.set_model(Gtk.StringList.new(options))
        self.live_product_dropdown.set_selected(0)

    def _current_live_search_query(self) -> str:
        typed_query = self.live_search_entry.get_text().strip() if hasattr(self, "live_search_entry") else ""

        if typed_query:
            return typed_query

        product = self._current_product_filter() if hasattr(self, "live_product_dropdown") else "Any Product"
        part = self._dropdown_text(self.live_part_dropdown) if hasattr(self, "live_part_dropdown") else "All Parts"

        if product and not product.startswith("Any "):
            if part == "PSU" and "psu" not in product.lower():
                return f"{product} PSU"
            if part == "Motherboard" and "motherboard" not in product.lower():
                return f"{product} motherboard"
            if part == "Storage" and "ssd" not in product.lower() and "nvme" not in product.lower():
                return f"{product} SSD"
            return product

        selected_targets = {
            build_part.part_type: build_part.target
            for build_part in self.pc_builder_service.list_build_parts()
        }

        fallback_by_part = {
            "PSU": selected_targets.get("PSU") or "750W Gold PSU",
            "Motherboard": selected_targets.get("Motherboard") or "B650 motherboard",
            "GPU": selected_targets.get("GPU") or "RX 6800",
            "CPU": selected_targets.get("CPU") or "Ryzen 7 7800X3D",
            "RAM": selected_targets.get("RAM") or "32GB DDR5",
            "Storage": selected_targets.get("Storage") or "2TB NVMe SSD",
            "Case": selected_targets.get("Case") or "ATX airflow case",
            "Cooling": selected_targets.get("Cooling") or "Thermalright CPU cooler",
            "Full PC": "AM5 gaming PC",
        }

        query = fallback_by_part.get(part, "")

        if part == "PSU" and query and "psu" not in query.lower() and "power supply" not in query.lower():
            query = f"{query} PSU"

        if part == "Motherboard" and query and "motherboard" not in query.lower():
            query = f"{query} motherboard"

        if part == "Storage" and query and "ssd" not in query.lower() and "nvme" not in query.lower():
            query = f"{query} SSD"

        return query.strip()

    def _on_search_live_text_clicked(self, _button: Gtk.Button) -> None:
        if not hasattr(self, "live_search_entry"):
            return

        query = self.live_search_entry.get_text().strip()

        if not query:
            if hasattr(self, "live_status_label"):
                self.live_status_label.set_text("Type something in Live Deals search first.")
            return

        search = SavedSearch.create(
            query=query,
            marketplace="Vinted",
            min_price=None,
            max_price=self._price_or_none(self.live_max_price_input.get_value()) if hasattr(self, "live_max_price_input") else None,
            condition="Any",
            excluded_keywords=[
                "broken",
                "faulty",
                "wanted",
                "laptop",
                "notebook",
                "zenbook",
                "macbook",
                "ipad",
                "tablet",
                "camera",
                "airpods",
            ],
            refresh_interval_minutes=5,
        )

        started = self.search_manager.refresh_search(search, manual=True)

        if hasattr(self, "live_status_label"):
            if started:
                self.live_status_label.set_text(f"Searching Vinted once for: {query}")
            else:
                self.live_status_label.set_text("Search could not start. Check cooldown or connector status.")

        self._refresh_runtime_stats()

    def _on_apply_live_filters_clicked(self, _button: Gtk.Button) -> None:
        self._saved_live_expanded = False
        self._worth_live_expanded = True
        self._live_render_signature = ""
        self._refresh_live_results(force=True)

    def _on_clear_live_filters_clicked(self, _button: Gtk.Button) -> None:
        if hasattr(self, "live_search_entry"):
            self.live_search_entry.set_text("")

        if hasattr(self, "live_focus_dropdown"):
            self.live_focus_dropdown.set_selected(0)

        if hasattr(self, "live_part_dropdown"):
            self.live_part_dropdown.set_selected(0)

        if hasattr(self, "live_product_dropdown"):
            self.live_product_dropdown.set_model(Gtk.StringList.new(LIVE_PRODUCT_FILTERS["All Parts"]))
            self.live_product_dropdown.set_selected(0)

        if hasattr(self, "live_priority_dropdown"):
            self.live_priority_dropdown.set_selected(1)

        if hasattr(self, "live_sort_dropdown"):
            self.live_sort_dropdown.set_selected(0)

        if hasattr(self, "live_max_price_input"):
            self.live_max_price_input.set_value(0)

        if hasattr(self, "live_hide_high_scam_check"):
            self.live_hide_high_scam_check.set_active(False)

        self._live_render_signature = ""
        self._refresh_live_results(force=True)

    def _current_product_filter(self) -> str:
        if hasattr(self, "live_product_dropdown"):
            return self._dropdown_text(self.live_product_dropdown)

        return "Any Product"

    def _listing_matches_product_filter(self, title: str) -> bool:
        product_filter = self._current_product_filter()

        if product_filter.startswith("Any "):
            return True

        rules = LIVE_PRODUCT_RULES.get(product_filter)

        if not rules:
            return True

        lower = title.lower()

        for blocked in rules.get("exclude", []):
            if blocked.lower() in lower:
                return False

        all_terms = [term.lower() for term in rules.get("all", [])]

        if all_terms and not all(term in lower for term in all_terms):
            return False

        any_terms = [term.lower() for term in rules.get("any", [])]

        if any_terms and not any(term in lower for term in any_terms):
            return False

        return True

    def _filter_and_sort_stored_results(
        self,
        listings: list[StoredListing],
        excluded_keys: set[str] | None = None,
    ) -> list[StoredListing]:
        excluded_keys = excluded_keys or set()
        show_bought = self.live_show_bought_categories_check.get_active() if hasattr(self, "live_show_bought_categories_check") else False
        focus_filter = self._dropdown_text(self.live_focus_dropdown) if hasattr(self, "live_focus_dropdown") else "Active Build Hunt"
        part_filter = self._dropdown_text(self.live_part_dropdown) if hasattr(self, "live_part_dropdown") else "All Parts"
        search_text = self.live_search_entry.get_text().lower().strip() if hasattr(self, "live_search_entry") else ""
        max_price = self.live_max_price_input.get_value() if hasattr(self, "live_max_price_input") else 0

        filtered: list[StoredListing] = []

        for listing in listings:
            if listing.dedupe_key in excluded_keys:
                continue

            if listing.status in {"Favourite", "Watching", "Bought", "Evidence Requested", "Buying Candidate"}:
                continue

            source_query = listing.source_query or ""
            category = self.active_build_service.category_for_text(f"{listing.title} {source_query}")

            if focus_filter == "Active Build Hunt":
                if not self.active_build_service.should_show_listing(
                    listing.title,
                    source_query,
                    show_bought_categories=show_bought,
                    default_active_hunt=True,
                ):
                    continue

            if part_filter != "All Parts" and category != part_filter:
                continue

            if not self.active_build_service.is_relevant_for_category(category, listing.title, source_query):
                continue

            if hasattr(self, "_listing_matches_product_filter") and not self._listing_matches_product_filter(listing.title):
                continue

            haystack = " ".join(
                [
                    listing.title,
                    listing.marketplace,
                    listing.seller_name or "",
                    listing.location or "",
                    source_query,
                    category,
                ]
            ).lower()

            if search_text and search_text not in haystack:
                continue

            if max_price > 0 and listing.price is not None and listing.price > max_price:
                continue

            filtered.append(listing)

        sort_mode = self._dropdown_text(self.live_sort_dropdown) if hasattr(self, "live_sort_dropdown") else "Newest First"

        def price_value(listing: StoredListing) -> float:
            return listing.price if listing.price is not None else 999999

        if sort_mode == "Lowest Price":
            filtered.sort(key=price_value)
        elif sort_mode == "Highest Price":
            filtered.sort(key=price_value, reverse=True)
        elif sort_mode == "Highest Deal Score":
            filtered.sort(key=lambda listing: self._analyse_stored_listing_with_history(listing).deal_score, reverse=True)
        elif sort_mode == "Lowest Scam Risk":
            filtered.sort(key=lambda listing: self._analyse_stored_listing_with_history(listing).scam_risk)
        elif sort_mode == "Highest Build Fit":
            filtered.sort(key=lambda listing: self._analyse_stored_listing_with_history(listing).build_fit, reverse=True)
        elif sort_mode == "Highest Evidence Confidence":
            filtered.sort(key=lambda listing: self._analyse_stored_listing_with_history(listing).evidence_confidence, reverse=True)
        elif sort_mode == "Lowest Historical Price":
            filtered.sort(key=lambda listing: self._historical_price_rank(listing.title, listing.price), reverse=True)
        else:
            filtered.sort(key=lambda listing: listing.last_seen_at, reverse=True)

        return filtered

    def _filter_stored_live_results(self, listings: list[StoredListing]) -> list[StoredListing]:
        search_text = self.live_search_entry.get_text().lower().strip() if hasattr(self, "live_search_entry") else ""
        part_filter = self._dropdown_text(self.live_part_dropdown) if hasattr(self, "live_part_dropdown") else "All Parts"
        max_price = self.live_max_price_input.get_value() if hasattr(self, "live_max_price_input") else 0

        filtered: list[StoredListing] = []

        for listing in listings:
            inferred_part = infer_part_type(listing.title)
            haystack = " ".join(
                [
                    listing.title,
                    listing.marketplace,
                    listing.seller_name or "",
                    listing.source_query or "",
                    inferred_part,
                ]
            ).lower()

            if search_text and search_text not in haystack:
                continue

            if part_filter != "All Parts" and inferred_part != part_filter:
                continue

            if not self._listing_matches_product_filter(listing.title):
                continue

            if max_price > 0 and listing.price is not None and listing.price > max_price:
                continue

            filtered.append(listing)

        return filtered

    def _filter_and_sort_live_results(self, results: list[MarketplaceListing]) -> list[MarketplaceListing]:
        search_text = self.live_search_entry.get_text().lower().strip() if hasattr(self, "live_search_entry") else ""
        focus_filter = self._dropdown_text(self.live_focus_dropdown) if hasattr(self, "live_focus_dropdown") else "Active Build Hunt"
        part_filter = self._dropdown_text(self.live_part_dropdown) if hasattr(self, "live_part_dropdown") else "All Parts"
        max_price = self.live_max_price_input.get_value() if hasattr(self, "live_max_price_input") else 0
        show_bought = self.live_show_bought_categories_check.get_active() if hasattr(self, "live_show_bought_categories_check") else False

        filtered: list[MarketplaceListing] = []

        for listing in results:
            source_query = listing.source_query or ""
            category = self.active_build_service.category_for_text(f"{listing.title} {source_query}")

            if focus_filter == "Active Build Hunt":
                if not self.active_build_service.should_show_listing(
                    listing.title,
                    source_query,
                    show_bought_categories=show_bought,
                    default_active_hunt=True,
                ):
                    continue

            if part_filter != "All Parts" and category != part_filter:
                continue

            if not self.active_build_service.is_relevant_for_category(category, listing.title, source_query):
                continue

            if hasattr(self, "_listing_matches_product_filter") and not self._listing_matches_product_filter(listing.title):
                continue

            haystack = " ".join(
                [
                    listing.title,
                    listing.marketplace,
                    listing.seller_name or "",
                    listing.location or "",
                    source_query,
                    category,
                ]
            ).lower()

            if search_text and search_text not in haystack:
                continue

            if max_price > 0 and listing.price is not None and listing.price > max_price:
                continue

            if hasattr(self, "live_hide_high_scam_check") and self.live_hide_high_scam_check.get_active():
                decision = self._analyse_listing_with_history(listing)
                if decision.scam_risk >= 6:
                    continue

            filtered.append(listing)

        sort_mode = self._dropdown_text(self.live_sort_dropdown) if hasattr(self, "live_sort_dropdown") else "Newest First"

        def price_value(listing: MarketplaceListing) -> float:
            return listing.price if listing.price is not None else 999999

        if sort_mode == "Lowest Price":
            filtered.sort(key=price_value)
        elif sort_mode == "Highest Price":
            filtered.sort(key=price_value, reverse=True)
        elif sort_mode == "Highest Deal Score":
            filtered.sort(key=lambda listing: self._analyse_listing_with_history(listing).deal_score, reverse=True)
        elif sort_mode == "Lowest Scam Risk":
            filtered.sort(key=lambda listing: self._analyse_listing_with_history(listing).scam_risk)
        elif sort_mode == "Highest Build Fit":
            filtered.sort(key=lambda listing: self._analyse_listing_with_history(listing).build_fit, reverse=True)
        elif sort_mode == "Highest Evidence Confidence":
            filtered.sort(key=lambda listing: self._analyse_listing_with_history(listing).evidence_confidence, reverse=True)
        elif sort_mode == "Lowest Historical Price":
            filtered.sort(key=lambda listing: self._historical_price_rank(listing.title, listing.price), reverse=True)
        else:
            filtered.sort(key=lambda listing: listing.found_at, reverse=True)

        return filtered

    def _is_full_pc_listing(self, title: str) -> bool:
        lower = title.lower()
        full_pc_terms = [
            "gaming pc",
            "desktop pc",
            "full pc",
            "complete pc",
            "computer tower",
            "gaming computer",
            "custom pc",
            "prebuilt",
            "workstation",
            "dell precision",
            "pc bundle",
        ]

        return any(term in lower for term in full_pc_terms)

    def _live_signature(self, status: str, favourites: list[StoredListing], results: list[MarketplaceListing]) -> str:
        filter_state = []

        for attr in [
            "live_focus_dropdown",
            "live_part_dropdown",
            "live_product_dropdown",
            "live_priority_dropdown",
            "live_sort_dropdown",
        ]:
            if hasattr(self, attr):
                filter_state.append(self._dropdown_text(getattr(self, attr)))

        if hasattr(self, "live_search_entry"):
            filter_state.append(self.live_search_entry.get_text().strip())

        if hasattr(self, "live_max_price_input"):
            filter_state.append(str(self.live_max_price_input.get_value()))

        if hasattr(self, "live_hide_high_scam_check"):
            filter_state.append(str(self.live_hide_high_scam_check.get_active()))

        fav_keys = ",".join(f"{listing.dedupe_key}:{listing.status}" for listing in favourites)
        result_keys = ",".join(f"{listing.dedupe_key}:{listing.price}" for listing in results)

        return "|".join(
            [
                str(getattr(self, "_saved_live_expanded", True)),
                str(getattr(self, "_worth_live_expanded", True)),
                ",".join(filter_state),
                fav_keys,
                result_keys,
            ]
        )

    def _current_budget(self) -> float:
        if hasattr(self, "target_budget_input"):
            return float(self.target_budget_input.get_value())

        return self.pc_builder_service.get_target_build().total_budget

    def _key_value_card(
        self,
        title: str,
        pairs: list[tuple[str, str]],
        emphasise_values: bool = False,
    ) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.add_css_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        box.append(self._subheading(title))

        for key, value in pairs:
            safe_key = GLib.markup_escape_text(str(key))
            safe_value = GLib.markup_escape_text(str(value))

            if emphasise_values:
                markup = f"<b>{safe_key}:</b> <b>{safe_value}</b>"
            else:
                markup = f"<b>{safe_key}:</b> {safe_value}"

            label = Gtk.Label(xalign=0)
            label.set_use_markup(True)
            label.set_markup(markup)
            label.add_css_class("muted")
            label.set_wrap(True)
            box.append(label)

        frame.set_child(box)
        return frame

    def _stat_card(self, key: str, title: str) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.add_css_class("card")
        frame.set_hexpand(True)

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        title_label = Gtk.Label(label=title, xalign=0)
        title_label.add_css_class("muted")

        value_label = Gtk.Label(label="0", xalign=0)
        value_label.add_css_class("stat-value")
        value_label.set_wrap(True)
        self.stat_labels[key] = value_label

        box.append(title_label)
        box.append(value_label)
        frame.set_child(box)
        return frame

    def _section_card(self, title: str, lines: list[str]) -> Gtk.Widget:
        frame = Gtk.Frame()
        frame.add_css_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        box.set_margin_top(14)
        box.set_margin_bottom(14)
        box.set_margin_start(14)
        box.set_margin_end(14)

        box.append(self._subheading(title))

        for line in lines:
            label = self._muted_label(str(line))
            box.append(label)

        frame.set_child(box)
        return frame

    def _sidebar_row(self, page_id: str, title: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.page_id = page_id

        label = Gtk.Label(label=title, xalign=0)
        label.set_margin_top(10)
        label.set_margin_bottom(10)
        label.set_margin_start(14)
        label.set_margin_end(14)

        row.set_child(label)
        return row

    def _simple_row(self, text: str) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)
        row.set_child(self._muted_label(text))
        return row

    def _clear_listbox(self, listbox: Gtk.ListBox) -> None:
        child = listbox.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            listbox.remove(child)
            child = next_child

    def _clear_box(self, box: Gtk.Box) -> None:
        child = box.get_first_child()
        while child is not None:
            next_child = child.get_next_sibling()
            box.remove(child)
            child = next_child

    def _page_container(self) -> Gtk.Box:
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        page.set_margin_top(24)
        page.set_margin_bottom(24)
        page.set_margin_start(28)
        page.set_margin_end(28)
        return page

    def _scroll(self, child: Gtk.Widget) -> Gtk.ScrolledWindow:
        scroll = Gtk.ScrolledWindow()
        scroll.set_child(child)
        scroll.set_hexpand(True)
        scroll.set_vexpand(True)
        return scroll

    def _title_label(self, title: str, subtitle: str) -> Gtk.Widget:
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        title_label = Gtk.Label(label=title)
        title_label.add_css_class("window-title")
        subtitle_label = Gtk.Label(label=subtitle)
        subtitle_label.add_css_class("muted")
        box.append(title_label)
        box.append(subtitle_label)
        return box

    def _heading(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("heading")
        return label

    def _subheading(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("subheading")
        return label

    def _muted_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("muted")
        label.set_wrap(True)
        return label

    def _form_label(self, text: str) -> Gtk.Label:
        label = Gtk.Label(label=text, xalign=0)
        label.add_css_class("form-label")
        return label

    def _dropdown_text(self, dropdown: Gtk.DropDown) -> str:
        selected = dropdown.get_selected_item()
        if selected is None:
            return ""
        return selected.get_string()

    def _price_or_none(self, value: float) -> float | None:
        if value <= 0:
            return None
        return value

    def _format_datetime(self, value: datetime | None) -> str:
        if value is None:
            return "Not yet"
        return value.astimezone().strftime("%H:%M:%S")


    def _on_import_build_clicked(self, _button: Gtk.Button) -> None:
        self._open_build_import_window()

    def _open_build_import_window(self) -> None:
        existing_window = getattr(self, "build_import_window", None)

        if existing_window is not None:
            existing_window.present()
            return

        window = Gtk.Window()
        window.set_title("Import Build List")
        window.set_transient_for(self)
        window.set_modal(True)
        window.set_default_size(900, 720)
        window.connect("close-request", self._on_build_import_window_closed)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)
        window.set_child(root)

        root.append(self._heading("Import Build List"))
        root.append(
            self._muted_label(
                "Paste almost any build list from ChatGPT, Reddit, Discord, notes or PCPartPicker-style text. DealWise will detect parts, prices, reused items and checklist status."
            )
        )

        example = (
            "Final Build Cost\n\n"
            "7800X3D £200\n"
            "ASUS TUF B650-E £85\n"
            "SSD 2TB £80\n"
            "PSU £80\n"
            "Case £70\n"
            "Cooler £35\n\n"
            "Reuse:\n"
            "✓ RX6400\n"
            "✓ Existing RAM"
        )

        self.build_import_text_view = Gtk.TextView()
        self.build_import_text_view.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        self.build_import_text_view.set_vexpand(True)
        self.build_import_buffer = self.build_import_text_view.get_buffer()
        self.build_import_buffer.set_text(example)

        paste_scroll = Gtk.ScrolledWindow()
        paste_scroll.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.AUTOMATIC)
        paste_scroll.set_vexpand(True)
        paste_scroll.set_min_content_height(280)
        paste_scroll.set_child(self.build_import_text_view)
        root.append(paste_scroll)

        button_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)

        parse_button = Gtk.Button(label="Parse Preview")
        parse_button.connect("clicked", self._on_build_import_parse_clicked)

        apply_button = Gtk.Button(label="Apply To PC Builder")
        apply_button.add_css_class("suggested-action")
        apply_button.connect("clicked", self._on_build_import_apply_clicked)

        searches_button = Gtk.Button(label="Create Searches")
        searches_button.connect("clicked", self._on_build_import_create_searches_clicked)

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _button: window.close())

        button_row.append(parse_button)
        button_row.append(apply_button)
        button_row.append(searches_button)
        button_row.append(close_button)
        root.append(button_row)

        self.build_import_result_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        root.append(self.build_import_result_box)

        self.build_import_window = window
        self._show_build_import_result(self._parse_build_import_text())
        window.present()

    def _on_build_import_window_closed(self, _window: Gtk.Window) -> bool:
        self.build_import_window = None
        return False

    def _parse_build_import_text(self) -> BuildImportResult:
        if not hasattr(self, "build_import_buffer"):
            return self.build_import_service.parse("")

        start_iter, end_iter = self.build_import_buffer.get_bounds()
        text = self.build_import_buffer.get_text(start_iter, end_iter, False)
        return self.build_import_service.parse(text)

    def _on_build_import_parse_clicked(self, _button: Gtk.Button) -> None:
        self._show_build_import_result(self._parse_build_import_text())

    def _on_build_import_apply_clicked(self, _button: Gtk.Button) -> None:
        result = self._parse_build_import_text()
        self.build_import_service.apply_to_pc_builder(result)
        self._show_build_import_result(result, extra_message="Applied to PC Builder.")
        self._refresh_pc_builder()
        self._refresh_runtime_stats()

    def _on_build_import_create_searches_clicked(self, _button: Gtk.Button) -> None:
        result = self._parse_build_import_text()
        existing = {search.query.lower().strip() for search in self.config_manager.load_saved_searches()}
        added = 0

        for item in result.items:
            if item.status in {"Bought", "Stop Searching"}:
                continue

            for term in item.search_terms:
                key = term.lower().strip()

                if not key or key in existing:
                    continue

                search = SavedSearch.create(
                    query=term,
                    marketplace="Vinted",
                    min_price=None,
                    max_price=None,
                    condition="Any",
                    excluded_keywords=[
                        "broken",
                        "faulty",
                        "spares",
                        "repair",
                        "wanted",
                        "laptop",
                        "notebook",
                    ],
                    refresh_interval_minutes=5,
                )

                self.config_manager.add_saved_search(search)
                existing.add(key)
                added += 1

        self._refresh_saved_searches()
        self._refresh_runtime_stats()
        self._show_build_import_result(result, extra_message=f"Created {added} saved search(es).")

    def _show_build_import_result(self, result: BuildImportResult, extra_message: str = "") -> None:
        if not hasattr(self, "build_import_result_box"):
            return

        self._clear_box(self.build_import_result_box)

        lines = [
            extra_message,
            f"Detected Items: {len(result.items)}",
            f"Build Total: £{result.total:.0f}",
            f"Priced Items: {result.priced_count}",
            f"Reused Items: {result.reused_count}",
            f"Unknown Items: {result.unknown_count}",
            "",
            "Detected Components:",
        ]

        lines = [line for line in lines if line != ""]

        for item in result.items:
            price = "Reuse" if item.reused else ("-" if item.price is None else f"£{item.price:.0f}")
            terms = ", ".join(item.search_terms)
            lines.append(f"{item.part_type}: {item.name} | {price} | {item.status} | Searches: {terms}")

        if result.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(result.warnings)

        self.build_import_result_box.append(self._section_card("Build Import Preview", lines))

    def _build_summary_text(self, format_name: str = "markdown") -> str:
        return self.build_import_service.build_export(format_name)

    def _on_copy_build_summary_clicked(self, _button: Gtk.Button) -> None:
        copied = self._copy_text_to_clipboard(self._build_summary_text("markdown"))

        if hasattr(self, "live_status_label"):
            self.live_status_label.set_text("Build summary copied to clipboard." if copied else "Could not copy build summary.")

    def _on_export_build_markdown_clicked(self, _button: Gtk.Button) -> None:
        self._export_build_summary("markdown", "md")

    def _on_export_build_json_clicked(self, _button: Gtk.Button) -> None:
        self._export_build_summary("json", "json")

    def _export_build_summary(self, format_name: str, suffix: str) -> None:
        export_dir = self.config_manager.app_dir / "exports"
        export_dir.mkdir(parents=True, exist_ok=True)
        output_path = export_dir / f"dealwise-build-summary.{suffix}"
        output_path.write_text(self._build_summary_text(format_name), encoding="utf-8")

        if hasattr(self, "live_status_label"):
            self.live_status_label.set_text(f"Build summary exported: {output_path}")

    def _on_restore_hidden_listing_clicked(self, _button: Gtk.Button, dedupe_key: str) -> None:
        if hasattr(self.search_manager, "restore_hidden_listing"):
            self.search_manager.restore_hidden_listing(dedupe_key)

        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        self._refresh_runtime_stats()

    def _hidden_listing_row(self, listing: MarketplaceListing) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        frame = Gtk.Frame()
        frame.add_css_class("deal-card")

        outer = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        outer.set_margin_top(12)
        outer.set_margin_bottom(12)
        outer.set_margin_start(12)
        outer.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=listing.title, xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)

        meta = Gtk.Label(
            label=f"{listing.marketplace} • {listing.price_label()} • Hidden from current Live Deals",
            xalign=0,
        )
        meta.add_css_class("muted")
        meta.set_wrap(True)

        details.append(title)
        details.append(meta)

        restore_button = Gtk.Button(label="Restore")
        restore_button.connect("clicked", self._on_restore_hidden_listing_clicked, listing.dedupe_key)

        open_button = Gtk.Button(label="Open")
        open_button.connect("clicked", self._on_open_listing_clicked, listing.url)

        outer.append(details)
        outer.append(restore_button)
        outer.append(open_button)

        frame.set_child(outer)
        row.set_child(frame)
        return row

    def _on_score_details_clicked(self, _button: Gtk.Button, title: str, price: float | None, decision) -> None:
        window = Gtk.Window()
        window.set_title("Deal Score Details")
        window.set_transient_for(self)
        window.set_modal(True)
        window.set_default_size(620, 520)

        root = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        root.set_margin_top(20)
        root.set_margin_bottom(20)
        root.set_margin_start(20)
        root.set_margin_end(20)
        window.set_child(root)

        root.append(self._heading("Deal Score Details"))
        root.append(self._section_card("Score Breakdown", self._deal_score_explanation_lines(title, price, decision)))

        close_button = Gtk.Button(label="Close")
        close_button.connect("clicked", lambda _button: window.close())
        root.append(close_button)

        window.present()

    def _deal_score_explanation_lines(self, title: str, price: float | None, decision) -> list[str]:
        stats = self.price_history_service.stats_for_title(title)
        confidence = "Low"

        if stats is not None:
            if stats.sample_count >= 8:
                confidence = "High"
            elif stats.sample_count >= 4:
                confidence = "Medium"

        price_points = min(40, max(0, int(decision.deal_score * 0.40)))
        condition_points = min(20, max(0, int(decision.evidence_confidence * 0.20)))
        history_points = 0 if stats is None else min(15, max(0, int((100 - self._historical_price_rank(title, price)) * 0.15)))
        demand_points = min(15, max(0, int(decision.urgency_score * 0.15)))
        seller_points = min(10, max(0, int((100 - int(decision.scam_risk * 10)) * 0.10)))

        recommendation = "Excellent deal." if decision.deal_score >= 85 else (
            "Good deal if evidence checks out." if decision.deal_score >= 70 else (
                "Worth watching." if decision.deal_score >= 55 else "Not strong enough yet."
            )
        )

        history_line = "Historical Price: no local history yet."

        if stats is not None:
            history_line = (
                f"Historical Price: {history_points}/15 "
                f"({stats.sample_count} sample(s), range {stats.range_label()}, average {stats.average_label()})"
            )

        return [
            f"Item: {title}",
            f"Final Deal Score: {decision.deal_score}/100",
            f"Confidence: {confidence}",
            "",
            f"Price: {price_points}/40",
            f"Condition / Evidence: {condition_points}/20",
            history_line,
            f"Demand / Urgency: {demand_points}/15",
            f"Seller / Scam Risk: {seller_points}/10",
            "",
            f"Scam Risk: {decision.scam_risk}/10",
            f"Build Fit: {decision.build_fit}/100",
            f"Budget Fit: {decision.budget_fit}/100",
            f"Evidence Confidence: {decision.evidence_confidence}/100",
            "",
            f"Recommendation: {recommendation}",
            "",
            "Reasoning:",
            *[f"- {reason}" for reason in decision.reasoning],
        ]

    def _on_live_filter_debounced(self, *_args) -> None:
        timer_id = getattr(self, "_live_filter_timer_id", None)

        if timer_id is not None:
            GLib.source_remove(timer_id)

        self._live_filter_timer_id = GLib.timeout_add(180, self._run_live_filter_refresh)

    def _run_live_filter_refresh(self) -> bool:
        self._live_filter_timer_id = None
        self._saved_live_expanded = False
        self._worth_live_expanded = True
        self._live_render_signature = ""
        self._refresh_live_results(force=True)
        return False


    def _load_css(self) -> None:
        css = """
        .app-root {
            background: #111318;
        }

        .sidebar {
            background: #171a21;
            border-right: 1px solid #2b303b;
            min-width: 220px;
        }

        .heading {
            font-size: 28px;
            font-weight: 700;
            color: #f4f7fb;
        }

        .subheading {
            font-size: 17px;
            font-weight: 700;
            color: #f4f7fb;
        }

        .window-title {
            font-size: 15px;
            font-weight: 700;
        }

        .muted {
            color: #aab2c0;
        }

        .card {
            background: #1b1f29;
            border: 1px solid #2b303b;
            border-radius: 14px;
        }

        .deal-card {
            background: #1b1f29;
            border: 1px solid #2b303b;
            border-radius: 14px;
            margin-bottom: 10px;
        }

        .decision-badge {
            background: #263241;
            color: #ffffff;
            font-weight: 700;
            border-radius: 999px;
            padding: 6px 10px;
        }

        .score-line {
            color: #d6e2f2;
            font-weight: 700;
        }

        .image-card {
            background: #111318;
            border: 1px solid #2b303b;
            border-radius: 12px;
        }

        .stat-value {
            font-size: 18px;
            font-weight: 700;
            color: #ffffff;
        }

        .form-label {
            font-weight: 700;
            color: #f4f7fb;
        }

        .row-title {
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
        }

        .saved-search-list {
            background: transparent;
        }

        .error {
            border-color: #ff5c5c;
        }
        """

        provider = Gtk.CssProvider()

        try:
            provider.load_from_data(css)
        except TypeError:
            provider.load_from_data(css.encode("utf-8"))

        display = Gdk.Display.get_default()

        if display is not None:
            Gtk.StyleContext.add_provider_for_display(
                display,
                provider,
                Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION,
            )
