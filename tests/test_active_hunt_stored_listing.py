from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from dealwise.data.database import DatabaseManager
from dealwise.services.active_build import ActiveBuildService
from dealwise.services.active_hunt_session import ActiveHuntSessionService


class ActiveHuntStoredListingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(Path(self.tmp.name) / "dealwise-test.db")
        self.active_build = ActiveBuildService(self.database)
        self.active_build.seed_current_real_build()
        self.session = ActiveHuntSessionService(self.database, self.active_build)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_stored_listing_without_id_does_not_crash_classifier(self) -> None:
        stored = SimpleNamespace(
            dedupe_key="vinted:abc123",
            marketplace="Vinted",
            title="G.Skill Flare X5 32GB 2x16GB DDR5 6000 CL30 EXPO",
            price=80.0,
            url="https://example.test/item",
            seller_name="seller",
            source_query="32GB DDR5 6000 CL30",
            raw_json='{"source":"stored"}',
        )

        result = self.session.classify_listing(stored, "RAM")
        self.assertTrue(result.is_deal_candidate)
        self.assertEqual(result.category, "RAM")


if __name__ == "__main__":
    unittest.main()
