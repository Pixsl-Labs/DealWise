from __future__ import annotations

import logging
from datetime import datetime

from gi.repository import Gdk, GLib, Gtk

from dealwise import APP_NAME, APP_VERSION
from dealwise.config import ConfigManager
from dealwise.models import SavedSearch
from dealwise.services.search_manager import SearchManager


class MainWindow(Gtk.ApplicationWindow):
    """Main DealWise desktop window."""

    def __init__(
        self,
        application: Gtk.Application,
        config_manager: ConfigManager,
        search_manager: SearchManager,
        logger: logging.Logger,
    ) -> None:
        super().__init__(application=application)

        self.config_manager = config_manager
        self.search_manager = search_manager
        self.logger = logger

        self.set_title(APP_NAME)
        self.set_default_size(1180, 740)

        self.stat_labels: dict[str, Gtk.Label] = {}

        self._load_css()
        self._build_window()
        self._refresh_saved_searches()
        self._refresh_runtime_stats()

        GLib.timeout_add_seconds(1, self._refresh_runtime_stats)

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
            ("live_deals", "Live Deals", self._placeholder_page("Live Deals")),
            ("saved_searches", "Saved Searches", self._build_saved_searches_page()),
            ("watchlist", "Watchlist", self._placeholder_page("Watchlist")),
            ("price_history", "Price History", self._placeholder_page("Price History")),
            (
                "reverse_image_search",
                "Reverse Image Search",
                self._placeholder_page("Reverse Image Search"),
            ),
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

        heading = self._heading("Dashboard")
        page.append(heading)

        description = self._muted_label(
            "DealWise is running locally. Marketplace connectors will be added "
            "after the GUI, saved-search storage, logging, and refresh scheduler "
            "are stable."
        )
        page.append(description)

        card_grid = Gtk.Grid()
        card_grid.set_row_spacing(14)
        card_grid.set_column_spacing(14)
        card_grid.set_margin_top(18)
        page.append(card_grid)

        stats = [
            ("saved_searches", "Saved Searches"),
            ("searches_running", "Searches Running"),
            ("listings_analysed", "Listings Analysed"),
            ("refreshes_completed", "Refreshes Completed"),
            ("running_since", "Running Since"),
            ("last_refresh", "Last Refresh"),
        ]

        for index, (key, title) in enumerate(stats):
            card = self._stat_card(key, title)
            card_grid.attach(card, index % 3, index // 3, 1, 1)

        section = self._section_card(
            "Phase 1 Status",
            [
                "GTK4 desktop shell is active.",
                "Sidebar navigation is wired.",
                "Saved searches persist under ~/.config/Pixsl-Labs/DealWise/.",
                "Background refresh scheduler is running.",
                "Marketplace scraping is intentionally not implemented yet.",
            ],
        )
        section.set_margin_top(18)
        page.append(section)

        return self._scroll(page)

    def _build_saved_searches_page(self) -> Gtk.Widget:
        page = self._page_container()

        page.append(self._heading("Saved Searches"))
        page.append(
            self._muted_label(
                "Create searches now. Phase 2 will connect these saved searches "
                "to marketplace plugins such as Vinted."
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
        self.min_price_input.set_value(0)

        self.max_price_input = Gtk.SpinButton.new_with_range(0, 100000, 1)
        self.max_price_input.set_value(0)

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

        settings_card = self._section_card(
            "Current Local Settings",
            [
                f"Theme: {config.get('theme', 'dark')}",
                f"Default refresh: {config.get('default_refresh_interval_minutes', 5)} minutes",
                f"Notifications enabled: {config.get('notifications_enabled', True)}",
                f"Config path: {self.config_manager.app_dir}",
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
                    "Logs are stored outside the Git repository.",
                    "Future UI work can add a live log viewer here.",
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
                    "Built for hardware deal tracking, price analysis, and scam detection.",
                    "Designed as a flagship Pixsl-Labs desktop application.",
                    "Current version focuses on clean foundations before marketplace scraping.",
                ],
            )
        )

        return self._scroll(page)

    def _placeholder_page(self, title: str) -> Gtk.Widget:
        page = self._page_container()
        page.append(self._heading(title))

        page.append(
            self._muted_label(
                "This page is reserved for the planned feature. It is included "
                "now so the app architecture can grow without reshuffling the GUI later."
            )
        )

        return self._scroll(page)

    def _on_sidebar_row_selected(
        self,
        _list_box: Gtk.ListBox,
        row: Gtk.ListBoxRow | None,
    ) -> None:
        if row is None:
            return

        page_id = getattr(row, "page_id", None)

        if page_id is None:
            return

        self.stack.set_visible_child_name(page_id)

    def _on_save_search_clicked(self, _button: Gtk.Button) -> None:
        query = self.query_entry.get_text().strip()

        if not query:
            self.query_entry.add_css_class("error")
            return

        self.query_entry.remove_css_class("error")

        min_price = self._price_or_none(self.min_price_input.get_value())
        max_price = self._price_or_none(self.max_price_input.get_value())

        excluded_keywords = [
            keyword.strip()
            for keyword in self.excluded_keywords_entry.get_text().split(",")
            if keyword.strip()
        ]

        search = SavedSearch.create(
            query=query,
            marketplace=self._dropdown_text(self.marketplace_dropdown),
            min_price=min_price,
            max_price=max_price,
            condition=self._dropdown_text(self.condition_dropdown),
            excluded_keywords=excluded_keywords,
            refresh_interval_minutes=int(
                self._dropdown_text(self.refresh_interval_dropdown)
            ),
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

    def _on_manual_refresh_clicked(self, _button: Gtk.Button) -> None:
        refreshed_count = self.search_manager.refresh_all_saved_searches()
        self.logger.info("Manual refresh completed | searches=%s", refreshed_count)
        self._refresh_runtime_stats()

    def _refresh_saved_searches(self) -> None:
        if not hasattr(self, "saved_search_list"):
            return

        child = self.saved_search_list.get_first_child()

        while child is not None:
            next_child = child.get_next_sibling()
            self.saved_search_list.remove(child)
            child = next_child

        searches = self.config_manager.load_saved_searches()

        if not searches:
            empty_row = Gtk.ListBoxRow()
            empty_row.set_selectable(False)
            empty_row.set_child(
                self._muted_label("No saved searches yet. Add one above.")
            )
            self.saved_search_list.append(empty_row)
            return

        for search in searches:
            self.saved_search_list.append(self._saved_search_row(search))

    def _refresh_runtime_stats(self) -> bool:
        stats = self.search_manager.get_stats()

        values = {
            "saved_searches": str(stats.saved_searches),
            "searches_running": str(stats.searches_running),
            "listings_analysed": str(stats.listings_analysed),
            "refreshes_completed": str(stats.refreshes_completed),
            "running_since": self._format_datetime(stats.running_since),
            "last_refresh": self._format_datetime(stats.last_refresh_at),
        }

        for key, value in values.items():
            label = self.stat_labels.get(key)

            if label is not None:
                label.set_text(value)

        return True

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
            label=(
                f"{search.marketplace} • {search.price_range_label()} • "
                f"{search.condition} • every {search.refresh_interval_minutes}m"
            ),
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
            label = self._muted_label(f"• {line}")
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
            font-size: 26px;
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
