from __future__ import annotations

import unittest

from dealwise.services.ram_hunt import RAMHuntProfile, RAMHuntService


class RAMHuntServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = RAMHuntService()

    def test_parse_corsair_sku(self) -> None:
        spec = self.service.parse("Corsair Vengeance CMH32GX5M2D6000C36 32GB DDR5 6000 CL36")
        self.assertEqual(spec.brand, "Corsair")
        self.assertEqual(spec.total_capacity_gb, 32)
        self.assertEqual(spec.speed, 6000)
        self.assertEqual(spec.cas_latency, 36)

    def test_detect_2x16gb(self) -> None:
        spec = self.service.parse("G.Skill Flare X5 2x16GB DDR5 6000 CL30 EXPO")
        self.assertEqual(spec.module_count, 2)
        self.assertEqual(spec.module_capacity_gb, 16)
        self.assertEqual(spec.total_capacity_gb, 32)
        self.assertTrue(spec.expo)

    def test_single_stick_final_warns(self) -> None:
        profile = RAMHuntProfile.final_default()
        spec = self.service.parse("Kingston Fury 1x16GB DDR5 6000 CL36")
        score = self.service.score(spec, profile, item_price=40)
        self.assertTrue(any("Single-stick" in warning or "Single stick" in warning for warning in score.warnings + [note for *_rest, note in score.factors]))

    def test_ddr4_rejected(self) -> None:
        profile = RAMHuntProfile.final_default()
        spec = self.service.parse("Corsair Vengeance 32GB DDR4 3600")
        score = self.service.score(spec, profile, item_price=50)
        self.assertTrue(any("DDR4" in warning for warning in score.warnings))

    def test_sodimm_rejected(self) -> None:
        profile = RAMHuntProfile.final_default()
        spec = self.service.parse("Crucial 32GB DDR5 SODIMM laptop RAM 5600")
        score = self.service.score(spec, profile, item_price=60)
        self.assertTrue(any("SO-DIMM" in warning for warning in score.warnings))

    def test_expo_xmp_detection(self) -> None:
        expo = self.service.parse("32GB DDR5 6000 CL30 AMD EXPO")
        xmp = self.service.parse("32GB DDR5 6000 CL36 XMP")
        self.assertTrue(expo.expo)
        self.assertTrue(xmp.xmp)

    def test_speed_and_latency_parse(self) -> None:
        spec = self.service.parse("TeamGroup T-Create Expert DDR5 6000MHz CL30 32GB")
        self.assertEqual(spec.speed, 6000)
        self.assertEqual(spec.cas_latency, 30)

    def test_temporary_profile_accepts_single_stick(self) -> None:
        profile = RAMHuntProfile.temporary_default()
        spec = self.service.parse("16GB DDR5 4800 desktop RAM")
        score = self.service.score(spec, profile, item_price=25)
        self.assertIn("testing", score.recommendation.lower())

    def test_all_in_price(self) -> None:
        price = self.service.all_in_price(35, delivery_price=3, buyer_fee_estimate=2, travel_cost=0)
        self.assertEqual(price, 40)

    def test_browser_handoff_url_generation(self) -> None:
        profile = RAMHuntProfile.final_default()
        urls = self.service.browser_urls(profile)
        names = {name for name, _label, _url in urls}
        self.assertIn("Facebook Marketplace", names)
        self.assertIn("eBay", names)


if __name__ == "__main__":
    unittest.main()
