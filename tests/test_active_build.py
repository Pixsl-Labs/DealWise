from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing
from dealwise.services.active_build import ActiveBuildService


class ActiveBuildServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(Path(self.tmp.name) / "dealwise-test.db")
        self.service = ActiveBuildService(self.database)
        self.service.seed_current_real_build()

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def listing(self, title: str, query: str = "") -> MarketplaceListing:
        return MarketplaceListing(
            id=title.lower().replace(" ", "-"),
            marketplace="Vinted",
            title=title,
            price=100,
            currency="GBP",
            url="https://example.test",
            source_query=query,
        )

    def test_bought_categories_are_inactive(self) -> None:
        active = self.service.active_categories()
        self.assertNotIn("CPU", active)
        self.assertNotIn("Motherboard", active)
        self.assertNotIn("PSU", active)
        self.assertNotIn("Case", active)
        self.assertNotIn("Cooling", active)

    def test_gpu_temporary_still_active(self) -> None:
        active = self.service.active_categories()
        self.assertIn("GPU", active)

    def test_storage_temporary_still_active(self) -> None:
        active = self.service.active_categories()
        self.assertIn("Storage", active)

    def test_search_plan_only_gpu_ram_storage(self) -> None:
        plan = self.service.active_search_plan()
        self.assertEqual(set(plan.queries_by_part), {"GPU", "RAM", "Storage"})

    def test_fractal_scanner_case_rejected(self) -> None:
        self.assertFalse(
            self.service.is_relevant_for_category(
                "Case",
                "Ion slide scanner carry case",
                "Fractal airflow case",
            )
        )

    def test_real_pc_case_accepted_by_case_rules(self) -> None:
        self.assertTrue(
            self.service.is_relevant_for_category(
                "Case",
                "Fractal Design Meshify ATX PC case",
                "Fractal airflow case",
            )
        )

    def test_ddr4_rejected_for_ram(self) -> None:
        self.assertFalse(
            self.service.is_relevant_for_category(
                "RAM",
                "Corsair Vengeance 32GB DDR4 3600",
                "32GB DDR5 6000 CL30",
            )
        )

    def test_sodimm_rejected_for_ram(self) -> None:
        self.assertFalse(
            self.service.is_relevant_for_category(
                "RAM",
                "Crucial 32GB DDR5 SODIMM laptop RAM",
                "32GB DDR5 6000 CL30",
            )
        )

    def test_valid_ddr5_kit_accepted(self) -> None:
        self.assertTrue(
            self.service.is_relevant_for_category(
                "RAM",
                "G.Skill Flare X5 32GB 2x16GB DDR5 6000 CL30 EXPO",
                "32GB DDR5 6000 CL30",
            )
        )

    def test_external_ssd_rejected(self) -> None:
        self.assertFalse(
            self.service.is_relevant_for_category(
                "Storage",
                "Samsung T7 2TB portable external SSD",
                "2TB NVMe Gen4",
            )
        )

    def test_valid_2tb_nvme_accepted(self) -> None:
        self.assertTrue(
            self.service.is_relevant_for_category(
                "Storage",
                "WD Black SN850X 2TB M.2 NVMe Gen4 SSD",
                "2TB NVMe Gen4",
            )
        )

    def test_gpu_full_pc_rejected(self) -> None:
        self.assertFalse(
            self.service.is_relevant_for_category(
                "GPU",
                "Gaming PC Ryzen 7 with RX 7800 XT",
                "RX 7800 XT",
            )
        )

    def test_standalone_gpu_accepted(self) -> None:
        self.assertTrue(
            self.service.is_relevant_for_category(
                "GPU",
                "Sapphire Pulse RX 7800 XT 16GB graphics card",
                "RX 7800 XT",
            )
        )

    def test_purchased_totals_count_bundle_once(self) -> None:
        retail, personal = self.service.purchased_totals()
        self.assertEqual(retail, 628)
        self.assertEqual(personal, 538)

    def test_cpu_listing_hidden_by_default(self) -> None:
        self.assertFalse(
            self.service.should_show_listing(
                "AMD Ryzen 7 7800X3D",
                "Ryzen 7 7800X3D",
                show_bought_categories=False,
            )
        )

    def test_active_gpu_listing_shown_by_default(self) -> None:
        self.assertTrue(
            self.service.should_show_listing(
                "PowerColor RX 7900 GRE 16GB",
                "RX 7900 GRE",
                show_bought_categories=False,
            )
        )


if __name__ == "__main__":
    unittest.main()
