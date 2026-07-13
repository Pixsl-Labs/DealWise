from __future__ import annotations

import unittest

from dealwise.services.product_classifier import ProductClassifier


class ProductClassifierTests(unittest.TestCase):
    def setUp(self) -> None:
        self.classifier = ProductClassifier()

    def test_r9_290_rejected_for_rx_7700_xt_hunt(self) -> None:
        result = self.classifier.classify(
            "Sapphire Tri-X R9 290 graphics card",
            "RX 7700 XT",
            "GPU",
        )
        self.assertFalse(result.is_deal_candidate)
        self.assertEqual(result.deal_score_cap, 0)
        self.assertIn("Wrong", result.bucket)

    def test_replacement_fan_rejected(self) -> None:
        result = self.classifier.classify(
            "XFX QICK 319 replacement fan assembly",
            "RX 7700 XT",
            "GPU",
        )
        self.assertFalse(result.is_deal_candidate)
        self.assertEqual(result.bucket, "Replacement Part")
        self.assertEqual(result.deal_score_cap, 0)

    def test_valid_rx_7700_xt_accepted(self) -> None:
        result = self.classifier.classify(
            "Sapphire Pulse RX 7700 XT 12GB graphics card tested working",
            "RX 7700 XT",
            "GPU",
        )
        self.assertTrue(result.is_deal_candidate)
        self.assertGreaterEqual(result.identity_confidence, 60)

    def test_ddr4_rejected(self) -> None:
        result = self.classifier.classify(
            "Corsair Vengeance 32GB DDR4 3600",
            "32GB DDR5 6000 CL30",
            "RAM",
        )
        self.assertFalse(result.is_deal_candidate)
        self.assertEqual(result.deal_score_cap, 0)

    def test_sodimm_rejected(self) -> None:
        result = self.classifier.classify(
            "Crucial 32GB DDR5 SO-DIMM laptop RAM",
            "32GB DDR5",
            "RAM",
        )
        self.assertFalse(result.is_deal_candidate)
        self.assertEqual(result.deal_score_cap, 0)

    def test_valid_ddr5_kit_accepted(self) -> None:
        result = self.classifier.classify(
            "G.Skill Flare X5 32GB 2x16GB DDR5 6000 CL30 EXPO",
            "32GB DDR5 6000 CL30",
            "RAM",
        )
        self.assertTrue(result.is_deal_candidate)

    def test_external_ssd_rejected(self) -> None:
        result = self.classifier.classify(
            "Samsung T7 2TB portable external SSD",
            "2TB NVMe Gen4",
            "Storage",
        )
        self.assertFalse(result.is_deal_candidate)
        self.assertEqual(result.deal_score_cap, 0)

    def test_valid_2tb_nvme_accepted(self) -> None:
        result = self.classifier.classify(
            "WD Black SN850X 2TB M.2 NVMe Gen4 SSD",
            "2TB NVMe Gen4",
            "Storage",
        )
        self.assertTrue(result.is_deal_candidate)


if __name__ == "__main__":
    unittest.main()
