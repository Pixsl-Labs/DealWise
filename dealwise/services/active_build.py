from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from dealwise.config import ConfigManager
from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing, SavedSearch
from dealwise.services.product_classifier import ProductClassifier


SEARCH_ACTIVE_STATUSES = {
    "Needed",
    "Buying Candidate",
    "Evidence Requested",
    "Temporary / Upgrade Wanted",
}

SEARCH_INACTIVE_STATUSES = {
    "Bought",
    "Stop Searching",
    "Upgrade Later",
    "Not Looking",
    "Reused",
}

ACTIVE_HUNT_PARTS = ["GPU", "RAM", "Storage"]

BOUGHT_PARTS = {
    "CPU",
    "Motherboard",
    "Cooling",
    "PSU",
    "Case",
}


@dataclass(slots=True)
class ActiveSearchPlan:
    queries_by_part: dict[str, list[str]]
    negative_keywords_by_part: dict[str, list[str]]

    def all_queries(self) -> list[str]:
        output: list[str] = []
        for queries in self.queries_by_part.values():
            output.extend(queries)
        return output


@dataclass(slots=True)
class ActiveBuildSummary:
    active_parts: list[str]
    inactive_parts: list[str]
    temporary_parts: list[str]
    bought_parts: list[str]
    retail_spend: float
    personal_spend: float
    remaining_low: float
    remaining_high: float

    def active_label(self) -> str:
        return f"Active Hunt — {len(self.active_parts)} Parts"


class ActiveBuildService:
    """Central active-build and bought-part filtering service.

    This service owns the logic for:
    - which statuses are searchable;
    - which categories are active;
    - which saved searches should be generated;
    - which old searches should be paused;
    - which live results should be hidden from the active build hunt;
    - how bought bundle costs are counted.
    """

    GENERATED_MARKER = "dealwise_active_build_auto"

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.product_classifier = ProductClassifier()
        self.ensure_schema()

    def ensure_schema(self) -> None:
        with self.database.connect() as connection:
            self._ensure_column(connection, "build_parts", "retail_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "personal_net_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "purchase_group", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "build_parts", "bundle_total", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "included_in_bundle", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "upgrade_target", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "build_parts", "component_role", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "build_parts", "search_active", "INTEGER NOT NULL DEFAULT 1")
            connection.commit()

    def _ensure_column(self, connection, table: str, column: str, definition: str) -> None:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}

        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def seed_current_real_build(self) -> None:
        """Update the checklist to match the user's real purchases.

        Safe/idempotent. It updates known component rows but preserves DB,
        listings, price snapshots, notes and unrelated user data.
        """

        self._upsert_part(
            "CPU",
            "AMD Ryzen 7 7800X3D",
            budget=290,
            bought_price=290,
            status="Bought",
            priority=2,
            notes="Bought new. Retail price £290. Personal/net cost after family contribution: £200.",
            retail_price=290,
            personal_net_price=200,
            component_role="Bought CPU",
            search_active=0,
        )

        bundle_id = "asus_tuf_b850e_lc3_360_bundle"

        self._upsert_part(
            "Motherboard",
            "ASUS TUF Gaming B850-E WiFi",
            budget=174,
            bought_price=174,
            status="Bought",
            priority=3,
            notes="Bought as ASUS motherboard + 360mm cooler bundle. Bundle total £174. Count bundle once.",
            retail_price=174,
            personal_net_price=174,
            purchase_group=bundle_id,
            bundle_total=174,
            included_in_bundle=0,
            component_role="Bundle lead",
            search_active=0,
        )

        self._upsert_part(
            "Cooling",
            "ASUS TUF Gaming LC III 360 ARGB",
            budget=0,
            bought_price=0,
            status="Bought",
            priority=8,
            notes="Included in ASUS motherboard + 360mm cooler bundle. Do not count £174 twice.",
            retail_price=0,
            personal_net_price=0,
            purchase_group=bundle_id,
            bundle_total=174,
            included_in_bundle=1,
            component_role="Included in bundle",
            search_active=0,
        )

        self._upsert_part(
            "PSU",
            "Corsair RM850e 850W",
            budget=80,
            bought_price=80,
            status="Bought",
            priority=5,
            notes="Bought PSU. Stop PSU searches.",
            retail_price=80,
            personal_net_price=80,
            component_role="Bought PSU",
            search_active=0,
        )

        self._upsert_part(
            "Case",
            "Lian Li O11 Dynamic Mini V2 Flow Black",
            budget=84,
            bought_price=84,
            status="Bought",
            priority=6,
            notes="Bought case. Includes five supplied case fans. Stop case searches.",
            retail_price=84,
            personal_net_price=84,
            component_role="Bought case",
            search_active=0,
        )

        self._upsert_part(
            "GPU",
            "Sapphire RX 6400 Low Profile 4GB",
            budget=420,
            bought_price=0,
            status="Temporary / Upgrade Wanted",
            priority=1,
            notes="Current installed GPU. Temporary only. Continue searching for AMD GPU upgrade for 1440p Linux Mint gaming.",
            retail_price=0,
            personal_net_price=0,
            upgrade_target="RX 7700 XT performance or above",
            component_role="Temporary current GPU",
            search_active=1,
        )

        self._upsert_part(
            "RAM",
            "32GB 2x16GB DDR5-6000 CL30 EXPO",
            budget=110,
            bought_price=0,
            status="Needed",
            priority=4,
            notes="Required final RAM target: matched 2x16GB desktop DDR5, 6000MT/s, CL30 preferred, AMD EXPO preferred.",
            retail_price=0,
            personal_net_price=0,
            upgrade_target="32GB 2x16GB DDR5-6000 CL30 EXPO",
            component_role="Active hunt",
            search_active=1,
        )

        self._upsert_part(
            "Storage",
            "2TB M.2 NVMe PCIe Gen4 SSD",
            budget=110,
            bought_price=0,
            status="Temporary / Upgrade Wanted",
            priority=7,
            notes="Current Toshiba KXG50ZNV512G 512GB NVMe is reused temporarily and around 85% full. Continue searching for 2TB NVMe.",
            retail_price=0,
            personal_net_price=0,
            upgrade_target="2TB M.2 2280 NVMe PCIe Gen4 SSD",
            component_role="Temporary storage / active upgrade hunt",
            search_active=1,
        )

    def _upsert_part(
        self,
        part_type: str,
        target: str,
        budget: float,
        bought_price: float,
        status: str,
        priority: int,
        notes: str,
        retail_price: float = 0,
        personal_net_price: float = 0,
        purchase_group: str = "",
        bundle_total: float = 0,
        included_in_bundle: int = 0,
        upgrade_target: str = "",
        component_role: str = "",
        search_active: int = 1,
    ) -> None:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT id FROM build_parts WHERE part_type = ? LIMIT 1",
                (part_type,),
            ).fetchone()

            if row is None:
                connection.execute(
                    """
                    INSERT INTO build_parts (
                        part_type,
                        target,
                        budget,
                        bought_price,
                        status,
                        priority,
                        notes,
                        retail_price,
                        personal_net_price,
                        purchase_group,
                        bundle_total,
                        included_in_bundle,
                        upgrade_target,
                        component_role,
                        search_active
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        part_type,
                        target,
                        budget,
                        bought_price,
                        status,
                        priority,
                        notes,
                        retail_price,
                        personal_net_price,
                        purchase_group,
                        bundle_total,
                        included_in_bundle,
                        upgrade_target,
                        component_role,
                        search_active,
                    ),
                )
            else:
                connection.execute(
                    """
                    UPDATE build_parts
                    SET
                        target = ?,
                        budget = ?,
                        bought_price = ?,
                        status = ?,
                        priority = ?,
                        notes = ?,
                        retail_price = ?,
                        personal_net_price = ?,
                        purchase_group = ?,
                        bundle_total = ?,
                        included_in_bundle = ?,
                        upgrade_target = ?,
                        component_role = ?,
                        search_active = ?
                    WHERE id = ?
                    """,
                    (
                        target,
                        budget,
                        bought_price,
                        status,
                        priority,
                        notes,
                        retail_price,
                        personal_net_price,
                        purchase_group,
                        bundle_total,
                        included_in_bundle,
                        upgrade_target,
                        component_role,
                        search_active,
                        row["id"],
                    ),
                )

            connection.commit()

    def set_part_status(self, part_type: str, status: str) -> None:
        search_active = 1 if status in SEARCH_ACTIVE_STATUSES else 0

        with self.database.connect() as connection:
            connection.execute(
                """
                UPDATE build_parts
                SET status = ?, search_active = ?
                WHERE part_type = ?
                """,
                (status, search_active, part_type),
            )
            connection.commit()

    def part_statuses(self) -> dict[str, str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                "SELECT part_type, status FROM build_parts"
            ).fetchall()

        return {str(row["part_type"]): str(row["status"]) for row in rows}

    def active_categories(self) -> set[str]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT part_type, status, search_active
                FROM build_parts
                """
            ).fetchall()

        active: set[str] = set()

        for row in rows:
            status = str(row["status"])
            part_type = str(row["part_type"])

            if int(row["search_active"] or 0) == 1 or status in SEARCH_ACTIVE_STATUSES:
                active.add(part_type)

        return active

    def inactive_categories(self) -> set[str]:
        statuses = self.part_statuses()
        inactive: set[str] = set()

        for part_type, status in statuses.items():
            if status in SEARCH_INACTIVE_STATUSES or part_type in BOUGHT_PARTS:
                inactive.add(part_type)

        return inactive

    def active_search_plan(self) -> ActiveSearchPlan:
        active = self.active_categories()
        queries: dict[str, list[str]] = {}
        negatives: dict[str, list[str]] = {}

        if "GPU" in active:
            queries["GPU"] = [
                "RX 7700 XT",
                "RX 7800 XT",
                "RX 7900 GRE",
                "RX 7900 XT",
                "RX 9070",
                "RX 9070 XT",
                "RX 9060 XT 16GB",
            ]
            negatives["GPU"] = [
                "laptop",
                "full pc",
                "gaming pc",
                "empty box",
                "box only",
                "water block",
                "waterblock",
                "cooler only",
                "backplate",
                "wanted",
                "broken",
                "faulty",
                "spares",
                "repair",
                "parts only",
                "bracket",
                "egpu",
                "enclosure",
            ]

        if "RAM" in active:
            queries["RAM"] = [
                "32GB DDR5 6000 CL30",
                "2x16GB DDR5 6000 EXPO",
                "Corsair Vengeance 32GB DDR5 6000 CL30",
                "Kingston Fury Beast 32GB DDR5 6000 CL30 EXPO",
                "G.Skill Flare X5 32GB DDR5 6000 CL30",
                "G.Skill Trident Z5 Neo 32GB DDR5 6000 CL30",
                "TeamGroup T-Force 32GB DDR5 6000 CL30",
                "KLEVV Bolt V 32GB DDR5 6000 CL30",
            ]
            negatives["RAM"] = [
                "ddr4",
                "ddr3",
                "sodimm",
                "so-dimm",
                "laptop",
                "notebook",
                "server",
                "ecc",
                "rdimm",
                "registered",
                "single 8gb",
                "1x8gb",
                "1x16gb",
                "mismatched",
                "empty box",
                "box only",
            ]

        if "Storage" in active:
            queries["Storage"] = [
                "2TB NVMe Gen4",
                "2TB M.2 NVMe SSD",
                "WD Black SN850X 2TB",
                "Lexar NM790 2TB",
                "Kingston KC3000 2TB",
                "Samsung 990 Pro 2TB",
                "Solidigm P44 Pro 2TB",
                "Crucial T500 2TB",
                "TeamGroup MP44 2TB",
                "Seagate FireCuda 530 2TB",
            ]
            negatives["Storage"] = [
                "external",
                "portable",
                "enclosure",
                "caddy",
                "sata",
                "2.5",
                "hdd",
                "hard drive",
                "empty box",
                "box only",
                "heatsink only",
                "faulty",
                "locked",
                "untested",
                "128gb",
                "256gb",
                "512gb",
            ]

        return ActiveSearchPlan(queries_by_part=queries, negative_keywords_by_part=negatives)

    def summary(self) -> ActiveBuildSummary:
        active = sorted(self.active_categories())
        inactive = sorted(self.inactive_categories())
        statuses = self.part_statuses()
        temporary = sorted([part for part, status in statuses.items() if status == "Temporary / Upgrade Wanted"])
        bought = sorted([part for part, status in statuses.items() if status == "Bought"])

        retail_spend, personal_spend = self.purchased_totals()
        remaining_low, remaining_high = self.remaining_estimate_range()

        return ActiveBuildSummary(
            active_parts=active,
            inactive_parts=inactive,
            temporary_parts=temporary,
            bought_parts=bought,
            retail_spend=retail_spend,
            personal_spend=personal_spend,
            remaining_low=remaining_low,
            remaining_high=remaining_high,
        )

    def purchased_totals(self) -> tuple[float, float]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT
                    part_type,
                    target,
                    retail_price,
                    personal_net_price,
                    purchase_group,
                    bundle_total,
                    included_in_bundle,
                    status
                FROM build_parts
                WHERE status = 'Bought'
                """
            ).fetchall()

        retail_total = 0.0
        personal_total = 0.0
        counted_groups: set[str] = set()

        for row in rows:
            group = str(row["purchase_group"] or "")
            included = int(row["included_in_bundle"] or 0)
            bundle_total = float(row["bundle_total"] or 0)

            if group and bundle_total > 0:
                if group in counted_groups:
                    continue
                counted_groups.add(group)
                retail_total += bundle_total
                personal_total += bundle_total
                continue

            if included:
                continue

            retail_total += float(row["retail_price"] or 0)
            personal_total += float(row["personal_net_price"] or row["retail_price"] or 0)

        return retail_total, personal_total

    def remaining_estimate_range(self) -> tuple[float, float]:
        active = self.active_categories()
        low = 0.0
        high = 0.0

        if "GPU" in active:
            low += 320
            high += 650

        if "RAM" in active:
            low += 80
            high += 130

        if "Storage" in active:
            low += 85
            high += 150

        return low, high

    def cost_overview_lines(self) -> list[str]:
        retail, personal = self.purchased_totals()
        remaining_low, remaining_high = self.remaining_estimate_range()
        summary = self.summary()

        projected_low = personal + remaining_low
        projected_high = personal + remaining_high

        return [
            "Already Purchased",
            "CPU: AMD Ryzen 7 7800X3D — £290 retail / £200 net personal cost",
            "ASUS Motherboard + 360mm Cooler Bundle — £174",
            "PSU: Corsair RM850e 850W — £80",
            "Case: Lian Li O11 Dynamic Mini V2 Flow Black — £84",
            "",
            f"Retail build spend: £{retail:.0f}",
            f"Personal/net spend: £{personal:.0f}",
            "",
            "Remaining Target Budget",
            f"Active hunt parts: {', '.join(summary.active_parts) if summary.active_parts else 'None'}",
            f"Remaining estimated cost: £{remaining_low:.0f} - £{remaining_high:.0f}",
            f"Projected completed personal total: £{projected_low:.0f} - £{projected_high:.0f}",
            "",
            "Temporary / Upgrade Wanted",
            "GPU: Sapphire RX 6400 Low Profile 4GB — can assemble, but GPU hunt remains active.",
            "Storage: Toshiba KXG50ZNV512G 512GB NVMe — can assemble, but 2TB NVMe hunt remains active.",
        ]

    def active_hunt_lines(self) -> list[str]:
        active = self.active_categories()
        lines = [f"Active Hunt — {len(active)} Parts"]

        if "GPU" in active:
            lines.append("- GPU upgrade")

        if "RAM" in active:
            lines.append("- 32GB DDR5 RAM")

        if "Storage" in active:
            lines.append("- 2TB NVMe SSD")

        return lines

    def search_plan_lines(self) -> list[str]:
        plan = self.active_search_plan()
        lines: list[str] = []

        for part in ["GPU", "RAM", "Storage"]:
            part_queries = plan.queries_by_part.get(part, [])

            if not part_queries:
                continue

            lines.append(part)
            lines.extend([f"- {query}" for query in part_queries])
            lines.append("")

        return lines or ["No active search categories."]

    def create_or_refresh_active_searches(
        self,
        config_manager: ConfigManager,
        search_manager,
    ) -> int:
        self.pause_obsolete_saved_searches(config_manager)
        plan = self.active_search_plan()
        existing = {search.query.lower().strip() for search in config_manager.load_saved_searches()}
        created = 0
        started = 0

        for part, queries in plan.queries_by_part.items():
            negatives = plan.negative_keywords_by_part.get(part, [])

            for query in queries:
                key = query.lower().strip()

                if key not in existing:
                    search = SavedSearch.create(
                        query=query,
                        marketplace="Vinted",
                        min_price=None,
                        max_price=None,
                        condition="Any",
                        excluded_keywords=negatives,
                        refresh_interval_minutes=5,
                    )
                    self._add_generated_search(config_manager, search, part)
                    existing.add(key)
                    created += 1
                else:
                    search = next(
                        item
                        for item in config_manager.load_saved_searches()
                        if item.query.lower().strip() == key
                    )

                if started < 3:
                    try:
                        if search_manager.refresh_search(search, manual=True):
                            started += 1
                    except Exception:
                        pass

        return created

    def _add_generated_search(self, config_manager: ConfigManager, search: SavedSearch, part: str) -> None:
        data = config_manager.read_json(config_manager.searches_file, fallback={"saved_searches": []})
        raw_searches = data.get("saved_searches", [])

        if not isinstance(raw_searches, list):
            raw_searches = []

        raw = search.to_dict()
        raw[self.GENERATED_MARKER] = True
        raw["dealwise_part_type"] = part
        raw["paused_by_dealwise"] = False
        raw_searches.append(raw)
        config_manager.write_json(config_manager.searches_file, {"saved_searches": raw_searches})

    def pause_obsolete_saved_searches(self, config_manager: ConfigManager) -> int:
        data = config_manager.read_json(config_manager.searches_file, fallback={"saved_searches": []})
        raw_searches = data.get("saved_searches", [])

        if not isinstance(raw_searches, list):
            return 0

        inactive = self.inactive_categories()
        paused = 0

        for raw in raw_searches:
            if not isinstance(raw, dict):
                continue

            query = str(raw.get("query") or "")
            part = str(raw.get("dealwise_part_type") or self.category_for_text(query))

            is_generated = bool(raw.get(self.GENERATED_MARKER))
            looks_generated = self._looks_like_old_generated_query(query)

            if part in inactive and (is_generated or looks_generated):
                if not raw.get("paused_by_dealwise"):
                    paused += 1
                raw["paused_by_dealwise"] = True
                raw["pause_reason"] = f"{part} is no longer search-active."

        config_manager.write_json(config_manager.searches_file, {"saved_searches": raw_searches})
        return paused

    def _looks_like_old_generated_query(self, query: str) -> bool:
        known = {item.lower() for item in self._all_known_generated_queries()}
        return query.lower().strip() in known

    def _all_known_generated_queries(self) -> list[str]:
        plan = ActiveSearchPlan(
            queries_by_part={
                "CPU": ["Ryzen 7 7800X3D", "Ryzen 7 7700", "Ryzen 5 7600"],
                "Motherboard": ["B650", "B650M", "X670", "ASUS TUF Gaming B650-E WiFi", "ASUS TUF Gaming B850-E WiFi"],
                "Cooling": ["Thermalright air cooler", "360mm AIO", "ASUS TUF Gaming LC III"],
                "PSU": ["650W Gold", "750W Gold", "850W Gold", "Corsair RM850e"],
                "Case": ["Fractal airflow case", "Lian Li O11", "ATX airflow case"],
                "GPU": [],
                "RAM": [],
                "Storage": [],
            },
            negative_keywords_by_part={},
        )
        output: list[str] = []
        for queries in plan.queries_by_part.values():
            output.extend(queries)
        return output

    def clear_stale_live_results(self, search_manager) -> int:
        def should_remove(listing: MarketplaceListing) -> bool:
            return not self.should_show_listing(
                title=listing.title,
                source_query=listing.source_query or "",
                show_bought_categories=False,
                default_active_hunt=True,
            )

        if hasattr(search_manager, "remove_live_results_by_predicate"):
            return search_manager.remove_live_results_by_predicate(should_remove)

        return 0

    def should_show_listing(
        self,
        title: str,
        source_query: str = "",
        show_bought_categories: bool = False,
        default_active_hunt: bool = True,
    ) -> bool:
        category = self.category_for_text(f"{title} {source_query}")

        if category == "Unknown":
            return False if default_active_hunt else True

        if not self.is_relevant_for_category(category, title, source_query):
            return False

        if show_bought_categories:
            return True

        return category in self.active_categories()

    def category_for_text(self, text: str) -> str:
        lower = f" {text.lower()} "

        if self._is_full_pc(lower):
            return "Full PC"

        if self._looks_like_gpu(lower):
            return "GPU"

        if self._looks_like_ram(lower):
            return "RAM"

        if self._looks_like_storage(lower):
            return "Storage"

        if self._looks_like_cpu(lower):
            return "CPU"

        if self._looks_like_motherboard(lower):
            return "Motherboard"

        if self._looks_like_psu(lower):
            return "PSU"

        if self._looks_like_cooling(lower):
            return "Cooling"

        if self._looks_like_case(lower):
            return "Case"

        return "Unknown"

    def is_relevant_for_category(self, category: str, title: str, source_query: str = "") -> bool:
        if category in {"GPU", "RAM", "Storage"}:
            classification = self.product_classifier.classify(
                title=title,
                source_query=source_query,
                category_hint=category,
            )
            return classification.is_deal_candidate

        lower = f" {title.lower()} {source_query.lower()} "

        if category == "Case":
            return self._case_relevant(lower)

        if category == "CPU":
            return self._cpu_relevant(lower)

        if category == "Motherboard":
            return self._motherboard_relevant(lower)

        if category == "PSU":
            return self._psu_relevant(lower)

        if category == "Cooling":
            return self._cooling_relevant(lower)

        if category == "Full PC":
            return False

        return False

    def _is_full_pc(self, lower: str) -> bool:
        terms = [
            "gaming pc",
            "full pc",
            "desktop pc",
            "tower pc",
            "custom pc",
            "prebuilt",
            "pc specialist",
            "computer tower",
            "complete build",
        ]
        return any(term in lower for term in terms)

    def _looks_like_gpu(self, lower: str) -> bool:
        return any(
            term in lower
            for term in [
                " rx 7700",
                " rx 7800",
                " rx 7900",
                " rx 9070",
                " rx 9060",
                " radeon",
                " graphics card",
                " gpu",
                "rtx ",
            ]
        )

    def _looks_like_ram(self, lower: str) -> bool:
        return any(term in lower for term in ["ddr5", "ddr4", "ram", "memory", "2x16gb", "32gb"])

    def _looks_like_storage(self, lower: str) -> bool:
        return any(term in lower for term in ["nvme", "m.2", "ssd", "sn850x", "nm790", "kc3000", "990 pro", "firecuda"])

    def _looks_like_cpu(self, lower: str) -> bool:
        return any(term in lower for term in ["7800x3d", "ryzen", "processor", " cpu", " i5", " i7", " i9"])

    def _looks_like_motherboard(self, lower: str) -> bool:
        return any(term in lower for term in ["b650", "b850", "x670", "motherboard", "mobo", "am5 board"])

    def _looks_like_psu(self, lower: str) -> bool:
        return any(term in lower for term in ["psu", "power supply", "850w", "750w", "650w", "rm850e"])

    def _looks_like_cooling(self, lower: str) -> bool:
        return any(term in lower for term in ["cooler", "cooling", "aio", "heatsink", "thermalright", "noctua", "360mm"])

    def _looks_like_case(self, lower: str) -> bool:
        return "case" in lower or any(
            term in lower
            for term in [
                "chassis",
                "pc chassis",
                "gaming tower",
                "mid tower",
                "full tower",
                "fractal design",
                "lian li",
                "nzxt",
                "phanteks",
                "montech",
            ]
        )

    def _contains_any(self, lower: str, terms: list[str]) -> bool:
        return any(term in lower for term in terms)

    def _gpu_relevant(self, lower: str) -> bool:
        exclude = [
            "laptop",
            "gaming pc",
            "full pc",
            "desktop pc",
            "tower pc",
            "empty box",
            "box only",
            "water block",
            "waterblock",
            "cooler only",
            "replacement cooler",
            "backplate",
            "wanted",
            "broken",
            "faulty",
            "spares",
            "repair",
            "parts only",
            "bracket",
            "egpu",
            "enclosure",
        ]

        if self._contains_any(lower, exclude):
            return False

        gpu_models = [
            "rx 7700 xt",
            "rx7700xt",
            "rx 7800 xt",
            "rx7800xt",
            "rx 7900 gre",
            "rx7900gre",
            "rx 7900 xt",
            "rx7900xt",
            "rx 9070",
            "rx9070",
            "rx 9070 xt",
            "rx9070xt",
            "rx 9060 xt",
            "rx9060xt",
        ]

        return self._contains_any(lower, gpu_models)

    def _ram_relevant(self, lower: str) -> bool:
        exclude = [
            "ddr4",
            "ddr3",
            "sodimm",
            "so-dimm",
            "laptop",
            "notebook",
            "server",
            "ecc",
            "rdimm",
            "registered",
            "single 8gb",
            "1x8gb",
            "empty box",
            "box only",
        ]

        if self._contains_any(lower, exclude):
            return False

        if "ddr5" not in lower:
            return False

        if "32gb" not in lower and "2x16" not in lower and "2 x 16" not in lower:
            return False

        if "1x16" in lower or "1 x 16" in lower or "1x32" in lower or "1 x 32" in lower:
            return False

        speed_ok = any(term in lower for term in ["6000", "5600", "cl30", "cl32", "cl28", "expo"])
        return speed_ok

    def _storage_relevant(self, lower: str) -> bool:
        exclude = [
            "external",
            "portable",
            "enclosure",
            "caddy",
            "sata",
            "2.5",
            "hdd",
            "hard drive",
            "empty box",
            "box only",
            "heatsink only",
            "faulty",
            "locked",
            "128gb",
            "256gb",
            "512gb",
        ]

        if self._contains_any(lower, exclude):
            return False

        if "2tb" not in lower:
            return False

        if "nvme" not in lower and "m.2" not in lower and "sn850x" not in lower and "nm790" not in lower and "kc3000" not in lower:
            return False

        return True

    def _case_relevant(self, lower: str) -> bool:
        unrelated = [
            "phone case",
            "tablet case",
            "camera case",
            "carry case",
            "flight case",
            "suitcase",
            "slide case",
            "scanner case",
            "cartridge case",
            "jewellery case",
            "watch case",
            "airpods case",
            "tool case",
        ]

        if self._contains_any(lower, unrelated):
            return False

        pc_case_signals = [
            "pc case",
            "computer case",
            "gaming case",
            "atx case",
            "matx case",
            "micro atx case",
            "chassis",
            "pc chassis",
            "gaming tower",
            "mid tower",
            "full tower",
            "fractal design",
            "lian li",
            "corsair case",
            "nzxt case",
            "phanteks",
            "montech",
        ]

        hardware_anchor = [
            "pc",
            "computer",
            "gaming",
            "atx",
            "matx",
            "micro atx",
            "chassis",
            "tower",
            "fractal",
            "lian li",
            "corsair",
            "nzxt",
            "phanteks",
            "montech",
        ]

        return self._contains_any(lower, pc_case_signals) and self._contains_any(lower, hardware_anchor)

    def _cpu_relevant(self, lower: str) -> bool:
        return self._contains_any(lower, ["7800x3d", "ryzen 7 7800"])

    def _motherboard_relevant(self, lower: str) -> bool:
        return self._contains_any(lower, ["b850", "b650", "x670", "am5", "motherboard", "mobo"])

    def _psu_relevant(self, lower: str) -> bool:
        return self._contains_any(lower, ["psu", "power supply", "rm850e", "850w", "750w", "650w"])

    def _cooling_relevant(self, lower: str) -> bool:
        return self._contains_any(lower, ["cooler", "aio", "360mm", "lc iii", "thermalright", "noctua"])
