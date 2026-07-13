from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing
from dealwise.services.active_build import ActiveBuildService
from dealwise.services.active_hunt_session import ActiveHuntSessionService


class ActiveHuntSessionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.database = DatabaseManager(Path(self.tmp.name) / "dealwise-test.db")
        self.active_build = ActiveBuildService(self.database)
        self.active_build.seed_current_real_build()
        self.session_service = ActiveHuntSessionService(self.database, self.active_build)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_session_tables_created(self) -> None:
        stats = self.session_service.start_session()
        self.assertEqual(stats.status, "Searching")
        self.assertIn("GPU", stats.active_parts)
        self.assertIn("RAM", stats.active_parts)
        self.assertIn("Storage", stats.active_parts)

    def test_classification_cache(self) -> None:
        listing = MarketplaceListing(
            id="1",
            marketplace="Vinted",
            title="Sapphire Pulse RX 7700 XT 12GB graphics card",
            price=310,
            currency="GBP",
            url="https://example.test/1",
            source_query="RX 7700 XT",
        )

        first = self.session_service.classify_listing(listing, "GPU")
        second = self.session_service.classify_listing(listing, "GPU")

        self.assertTrue(first.is_deal_candidate)
        self.assertEqual(second.bucket, first.bucket)


if __name__ == "__main__":
    unittest.main()
