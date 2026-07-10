from __future__ import annotations

import logging
import webbrowser
from datetime import datetime

from gi.repository import Gdk, GLib, Gtk

from dealwise import APP_NAME, APP_VERSION
from dealwise.config import ConfigManager
from dealwise.models import MarketplaceListing, SavedSearch
from dealwise.repositories.listing_repository import ListingRepository, StoredListing
from dealwise.services.listing_intelligence import ListingIntelligenceService
from dealwise.services.pc_builder_service import PCBuilderService
from dealwise.services.search_manager import SearchManager


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
        self.listing_intelligence_service = listing_intelligence_service

        self.set_title(APP_NAME)
        self.set_icon_name("dealwise")
        self.set_default_size(1280, 780)

        self.stat_labels: dict[str, Gtk.Label] = {}

        self._load_css()
        self._build_window()
        self._refresh_saved_searches()
        self._refresh_live_results()
        self._refresh_persistent_listings()
        self._refresh_pc_builder()
        self._refresh_runtime_stats()

        GLib.timeout_add_seconds(1, self._refresh_runtime_stats)
        GLib.timeout_add_seconds(2, self._refresh_live_results)
        GLib.timeout_add_seconds(5, self._refresh_persistent_listings)

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
                "Phase 3 foundation is active: SQLite persistence, saved listings, PC Builder, inxi import, listing checker, and seller message generation."
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
            "Phase 3 Status",
            [
                "SQLite database is active under ~/.config/Pixsl-Labs/DealWise/database/dealwise.db.",
                "Marketplace results are now persisted and deduplicated.",
                "PC Builder can import current PC information with inxi -Fx.",
                "Listing Checker can create manual listings and generate seller messages.",
                "Advanced scoring is intentionally placeholder-level and explainable for now.",
            ],
        )
        section.set_margin_top(18)
        page.append(section)

        return self._scroll(page)

    def _build_pc_builder_page(self) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading("PC Builder"))

        top_actions = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        import_button = Gtk.Button(label="Import Current PC")
        import_button.connect("clicked", self._on_import_pc_clicked)

        clear_pc_button = Gtk.Button(label="Clear Saved PC")
        clear_pc_button.connect("clicked", self._on_clear_current_pc_clicked)

        save_target_button = Gtk.Button(label="Save Target Build")
        save_target_button.connect("clicked", self._on_save_target_build_clicked)

        top_actions.append(import_button)
        top_actions.append(clear_pc_button)
        top_actions.append(save_target_button)
        page.append(top_actions)

        self.pc_summary_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        self.pc_summary_box.set_margin_top(18)
        page.append(self.pc_summary_box)

        target = self.pc_builder_service.get_target_build()

        target_card = Gtk.Frame()
        target_card.add_css_class("card")
        target_form = Gtk.Grid()
        target_form.set_row_spacing(10)
        target_form.set_column_spacing(10)
        target_form.set_margin_top(14)
        target_form.set_margin_bottom(14)
        target_form.set_margin_start(14)
        target_form.set_margin_end(14)

        self.target_budget_input = Gtk.SpinButton.new_with_range(0, 100000, 10)
        self.target_budget_input.set_value(target.total_budget)

        self.target_use_case_entry = Gtk.Entry()
        self.target_use_case_entry.set_text(target.use_case)

        self.target_platform_entry = Gtk.Entry()
        self.target_platform_entry.set_text(target.platform)

        self.target_notes_entry = Gtk.Entry()
        self.target_notes_entry.set_text(target.notes)

        target_form.attach(self._form_label("Total Budget"), 0, 0, 1, 1)
        target_form.attach(self.target_budget_input, 1, 0, 1, 1)
        target_form.attach(self._form_label("Use Case"), 0, 1, 1, 1)
        target_form.attach(self.target_use_case_entry, 1, 1, 1, 1)
        target_form.attach(self._form_label("Build Path"), 0, 2, 1, 1)
        target_form.attach(self.target_platform_entry, 1, 2, 1, 1)
        target_form.attach(self._form_label("Notes"), 0, 3, 1, 1)
        target_form.attach(self.target_notes_entry, 1, 3, 1, 1)

        target_card.set_child(target_form)
        target_card.set_margin_top(18)
        page.append(target_card)

        page.append(self._subheading("Parts Checklist"))
        self.parts_list = Gtk.ListBox()
        self.parts_list.add_css_class("saved-search-list")
        self.parts_list.set_margin_top(10)
        page.append(self.parts_list)

        return self._scroll(page)

    def _build_live_deals_page(self) -> Gtk.Widget:
        page = self._page_container()

        top_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        top_row.set_hexpand(True)

        title_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        title_box.set_hexpand(True)
        title_box.append(self._heading("Live Deals"))
        title_box.append(
            self._muted_label(
                "Results from marketplace connectors appear here and are now also persisted in SQLite for Phase 3."
            )
        )

        refresh_button = Gtk.Button(label="Search Now")
        refresh_button.connect("clicked", self._on_manual_refresh_clicked)

        top_row.append(title_box)
        top_row.append(refresh_button)
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
        status_card.set_child(status_box)
        page.append(status_card)

        self.live_deals_list = Gtk.ListBox()
        self.live_deals_list.add_css_class("saved-search-list")
        self.live_deals_list.set_margin_top(16)
        page.append(self.live_deals_list)

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
                "Paste a listing manually to save it, get placeholder scores, and generate a safer seller message."
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
                    "Current version activates Phase 3 foundations.",
                ],
            )
        )
        return self._scroll(page)

    def _placeholder_page(self, title: str) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading(title))
        page.append(
            self._muted_label(
                "This page is reserved for a planned feature. Phase 3 focuses on SQLite, saved listings, PC Builder, and listing intelligence foundations."
            )
        )
        return self._scroll(page)

    def _on_sidebar_row_selected(self, _list_box: Gtk.ListBox, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        page_id = getattr(row, "page_id", None)
        if page_id is not None:
            self.stack.set_visible_child_name(page_id)

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
        self._refresh_persistent_listings()

    def _on_status_clicked(self, _button: Gtk.Button, dedupe_key: str, status: str) -> None:
        self.listing_repository.update_status(dedupe_key, status)
        self._refresh_persistent_listings()

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
            total_budget=self.target_budget_input.get_value(),
            use_case=self.target_use_case_entry.get_text(),
            platform=self.target_platform_entry.get_text(),
            notes=self.target_notes_entry.get_text(),
        )
        self._refresh_pc_builder()

    def _on_part_status_clicked(self, _button: Gtk.Button, part_id: int, status: str) -> None:
        self.pc_builder_service.update_part_status(part_id, status)
        self._refresh_pc_builder()

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
            "Reasoning:",
            *[f"- {reason}" for reason in decision.reasoning],
            "",
            "Seller Message:",
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

    def _refresh_live_results(self) -> bool:
        if not hasattr(self, "live_deals_list"):
            return True

        self._clear_listbox(self.live_deals_list)

        results = self.search_manager.get_live_results(limit=100)
        stats = self.search_manager.get_stats()

        if hasattr(self, "live_status_label"):
            self.live_status_label.set_text(stats.connector_status)

        if not results:
            self.live_deals_list.append(
                self._simple_row("No live results yet. Add a Vinted saved search, then click Search Now.")
            )
            return True

        for listing in results:
            self.live_deals_list.append(self._listing_row(listing))

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

        current_pc = self.pc_builder_service.get_current_pc()
        target = self.pc_builder_service.get_target_build()
        parts = self.pc_builder_service.list_build_parts()

        if current_pc is None:
            self.pc_summary_box.append(
                self._section_card(
                    "Current PC",
                    [
                        "No current PC imported yet.",
                        "Click Import Current PC to run inxi -Fx.",
                        "Install inxi if needed with: sudo apt install inxi",
                    ],
                )
            )
        else:
            self.pc_summary_box.append(
                self._section_card(
                    "Current PC",
                    [
                        f"System: {current_pc.system_model}",
                        f"CPU: {current_pc.cpu}",
                        f"GPU: {current_pc.gpu}",
                        f"Memory: {current_pc.memory}",
                        f"Storage: {current_pc.storage}",
                        f"Distro: {current_pc.distro}",
                        f"Upgrade notes: {current_pc.form_factor_notes}",
                    ],
                )
            )

        if current_pc is not None:
            valuation = self.pc_builder_service.estimate_current_pc_value(current_pc)
            self.pc_summary_box.append(
                self._section_card(
                    "Estimated Resale Value",
                    [
                        f"Whole PC estimate: £{valuation.whole_unit_low} - £{valuation.whole_unit_high}",
                        f"Separate parts estimate: £{valuation.separate_parts_low} - £{valuation.separate_parts_high}",
                        f"Confidence: {valuation.confidence}",
                        *valuation.notes,
                    ],
                )
            )

        self.pc_summary_box.append(
            self._section_card(
                "Target Build Summary",
                [
                    f"Budget: £{target.total_budget:.0f}",
                    f"Use case: {target.use_case}",
                    f"Build path: {target.platform}",
                    f"Notes: {target.notes}",
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

        wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        wrapper.set_margin_top(12)
        wrapper.set_margin_bottom(12)
        wrapper.set_margin_start(12)
        wrapper.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=listing.title, xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)

        meta_parts = [listing.marketplace, listing.price_label()]
        if listing.seller_name:
            meta_parts.append(f"Seller: {listing.seller_name}")
        if listing.source_query:
            meta_parts.append(f"Search: {listing.source_query}")

        meta = Gtk.Label(label=" • ".join(meta_parts), xalign=0)
        meta.add_css_class("muted")
        meta.set_wrap(True)

        url_label = Gtk.Label(label=listing.url, xalign=0)
        url_label.add_css_class("muted")
        url_label.set_wrap(True)

        details.append(title)
        details.append(meta)
        details.append(url_label)

        save_button = Gtk.Button(label="Save")
        save_button.connect("clicked", self._on_save_live_listing_clicked, listing)

        open_button = Gtk.Button(label="Open")
        open_button.connect("clicked", self._on_open_listing_clicked, listing.url)

        wrapper.append(details)
        wrapper.append(save_button)
        wrapper.append(open_button)
        row.set_child(wrapper)
        return row

    def _stored_listing_row(self, listing: StoredListing) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        wrapper.set_margin_top(12)
        wrapper.set_margin_bottom(12)
        wrapper.set_margin_start(12)
        wrapper.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=listing.title, xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)

        meta = Gtk.Label(
            label=f"{listing.marketplace} • {listing.price_label()} • {listing.part_type} • {listing.status}",
            xalign=0,
        )
        meta.add_css_class("muted")
        meta.set_wrap(True)

        url_label = Gtk.Label(label=listing.url, xalign=0)
        url_label.add_css_class("muted")
        url_label.set_wrap(True)

        details.append(title)
        details.append(meta)
        if listing.notes:
            details.append(self._muted_label(f"Notes: {listing.notes}"))
        details.append(url_label)

        watch_button = Gtk.Button(label="Watching")
        watch_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Watching")

        bought_button = Gtk.Button(label="Bought")
        bought_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Bought")

        avoid_button = Gtk.Button(label="Avoid")
        avoid_button.connect("clicked", self._on_status_clicked, listing.dedupe_key, "Avoided")

        open_button = Gtk.Button(label="Open")
        open_button.connect("clicked", self._on_open_listing_clicked, listing.url)

        wrapper.append(details)
        wrapper.append(watch_button)
        wrapper.append(bought_button)
        wrapper.append(avoid_button)
        wrapper.append(open_button)

        row.set_child(wrapper)
        return row

    def _build_part_row(self, part) -> Gtk.ListBoxRow:
        row = Gtk.ListBoxRow()
        row.set_selectable(False)

        wrapper = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
        wrapper.set_margin_top(10)
        wrapper.set_margin_bottom(10)
        wrapper.set_margin_start(12)
        wrapper.set_margin_end(12)

        details = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        details.set_hexpand(True)

        title = Gtk.Label(label=f"{part.part_type}: {part.target}", xalign=0)
        title.add_css_class("row-title")
        title.set_wrap(True)

        meta = Gtk.Label(
            label=f"Budget: £{part.budget:.0f} • Bought: £{part.bought_price:.0f} • Status: {part.status}",
            xalign=0,
        )
        meta.add_css_class("muted")
        meta.set_wrap(True)

        details.append(title)
        details.append(meta)

        needed_button = Gtk.Button(label="Needed")
        needed_button.connect("clicked", self._on_part_status_clicked, part.id, "Needed")

        bought_button = Gtk.Button(label="Bought")
        bought_button.connect("clicked", self._on_part_status_clicked, part.id, "Bought")

        later_button = Gtk.Button(label="Later")
        later_button.connect("clicked", self._on_part_status_clicked, part.id, "Upgrade Later")

        wrapper.append(details)
        wrapper.append(needed_button)
        wrapper.append(bought_button)
        wrapper.append(later_button)

        row.set_child(wrapper)
        return row

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
