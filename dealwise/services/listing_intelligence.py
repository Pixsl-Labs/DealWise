from __future__ import annotations

import re
from dataclasses import dataclass

from dealwise.repositories.listing_repository import StoredListing, infer_part_type


@dataclass(slots=True)
class ListingDecision:
    decision: str
    deal_score: int
    scam_risk: float
    build_fit: int
    budget_fit: int
    evidence_confidence: int
    urgency_score: int
    reasoning: list[str]
    seller_message: str


def buyer_risk_flags(text: str) -> list[str]:
    lower = text.lower()
    flags: list[str] = []

    checks = [
        ("photo is not the actual item", ["not the one", "not the actual", "picture is not", "photo is not"]),
        ("seller says the situation may look suspicious", ["looks scummy", "sounds dodgy", "look dodgy"]),
        ("limited testing window", ["test once", "only once", "thermal paste", "won't be able to put it back"]),
        ("CPU has been swapped/tested multiple times", ["swap out the cpu", "swapped out the cpu", "multiple times"]),
        ("OEM/tray/AliExpress comparison mentioned", ["ali express", "aliexpress", "oem tray", "tray ones"]),
        ("needs proof of current ownership", ["date", "username", "piece of paper"]),
    ]

    for label, terms in checks:
        if any(term in lower for term in terms):
            flags.append(label)

    return flags


def buyer_evidence_checklist(part_type: str) -> list[str]:
    part = part_type.lower()

    if part == "cpu":
        return [
            "Photo of the actual CPU next to today's date and seller username.",
            "Close-up of the front so the model and OPN/serial area are readable.",
            "Clear photo of the back/contact pads.",
            "BIOS, CPU-Z, HWiNFO, lscpu or /proc/cpuinfo showing the exact CPU detected.",
            "Prefer one short video connecting the proof together if the story is complicated.",
        ]

    if part == "gpu":
        return [
            "Photo of the actual GPU next to today's date and seller username.",
            "GPU-Z or system screenshot showing the exact GPU.",
            "Short video/photo showing it running.",
            "Confirmation there is no artifacting, overheating or fan issue.",
            "Ask whether it has been mined on if relevant.",
        ]

    return [
        "Photo of the actual item with today's date and seller username.",
        "Proof the item works.",
        "Clear photos of labels, serial/model details and condition.",
        "Any missing parts or known issues confirmed in writing.",
    ]


class ListingIntelligenceService:
    """Explainable local listing scoring.

    Phase 6 can now adjust these scores further using stored observed prices.
    """

    def analyse(
        self,
        title: str,
        price: float | None,
        url: str,
        marketplace: str,
        part_type: str | None = None,
        budget: float | None = None,
        notes: str = "",
    ) -> ListingDecision:
        safe_part_type = part_type or infer_part_type(title)
        lower_title = title.lower()
        reasoning: list[str] = []
        buyer_flags = buyer_risk_flags(f"{title} {notes}")

        expected_low, expected_high, matched_model = self._expected_price_range(lower_title, safe_part_type)

        deal_score = 58
        scam_risk = 3.0
        build_fit = 62
        budget_fit = 60
        evidence_confidence = 45
        urgency_score = 42

        if matched_model:
            build_fit += 12
            evidence_confidence += 8
            reasoning.append(f"Detected likely model/range: {matched_model}.")
        elif safe_part_type != "Unknown":
            build_fit += 6
            reasoning.append(f"Listing appears to match part type: {safe_part_type}.")

        if price is None:
            deal_score = 50
            evidence_confidence -= 10
            reasoning.append("No price was detected, so deal quality is uncertain.")
        elif expected_high > 0:
            midpoint = (expected_low + expected_high) / 2

            if price <= expected_low * 0.80:
                deal_score = 88
                scam_risk += 1.2
                urgency_score += 20
                reasoning.append("Price is far below the rough expected range, so it may be a strong deal but needs caution.")
            elif price <= expected_low:
                deal_score = 78
                urgency_score += 14
                reasoning.append("Price is below the rough expected range.")
            elif price <= midpoint:
                deal_score = 68
                reasoning.append("Price is around the lower half of the rough expected range.")
            elif price <= expected_high:
                deal_score = 58
                reasoning.append("Price is within the rough expected range.")
            else:
                deal_score = 43
                urgency_score -= 8
                reasoning.append("Price is above the rough expected range.")

        if price is not None and budget and budget > 0:
            if price <= budget:
                budget_fit = 90
                deal_score += 6
                reasoning.append("Price is within the selected budget.")
            elif price <= budget * 1.15:
                budget_fit = 65
                reasoning.append("Price is slightly above the selected budget.")
            else:
                budget_fit = 35
                deal_score -= 8
                reasoning.append("Price is well above the selected budget.")

        high_risk_words = ["broken", "faulty", "spares", "repair", "not working", "untested", "no returns"]
        if any(term in lower_title for term in high_risk_words):
            scam_risk += 2.5
            evidence_confidence -= 18
            deal_score -= 12
            reasoning.append("Risk wording detected in the listing title.")

        if not url:
            scam_risk += 1.5
            evidence_confidence -= 10
            reasoning.append("No URL was provided, so the listing cannot be independently checked.")

        if safe_part_type in {"GPU", "PSU", "Cooling"}:
            scam_risk += 0.8
            evidence_confidence -= 6
            reasoning.append(f"{safe_part_type} is higher risk when buying used.")

        if marketplace.lower() == "manual":
            evidence_confidence -= 5
            reasoning.append("Manual listing input needs extra evidence before buying.")

        if buyer_flags:
            scam_risk += min(3.0, len(buyer_flags) * 0.8)
            evidence_confidence -= min(25, len(buyer_flags) * 6)
            deal_score -= min(12, len(buyer_flags) * 3)
            reasoning.append("Buyer evidence flags: " + ", ".join(buyer_flags[:3]) + ".")

        deal_score = clamp_int(deal_score, 0, 100)
        build_fit = clamp_int(build_fit, 0, 100)
        budget_fit = clamp_int(budget_fit, 0, 100)
        evidence_confidence = clamp_int(evidence_confidence, 0, 100)
        urgency_score = clamp_int(urgency_score, 0, 100)
        scam_risk = max(0.0, min(10.0, scam_risk))

        decision = self._choose_decision(
            deal_score=deal_score,
            scam_risk=scam_risk,
            budget_fit=budget_fit,
            evidence_confidence=evidence_confidence,
        )

        reasoning.append(f"Evidence confidence is currently {evidence_confidence}/100.")
        reasoning.append("Ask for proof before sending money or committing to buy.")

        seller_message = self.generate_seller_message(
            title=title,
            part_type=safe_part_type,
            decision=decision,
        )

        return ListingDecision(
            decision=decision,
            deal_score=deal_score,
            scam_risk=scam_risk,
            build_fit=build_fit,
            budget_fit=budget_fit,
            evidence_confidence=evidence_confidence,
            urgency_score=urgency_score,
            reasoning=reasoning,
            seller_message=seller_message,
        )

    def analyse_stored_listing(self, listing: StoredListing, budget: float | None = None) -> ListingDecision:
        return self.analyse(
            title=listing.title,
            price=listing.price,
            url=listing.url,
            marketplace=listing.marketplace,
            part_type=listing.part_type,
            budget=budget,
            notes=listing.notes,
        )

    def _expected_price_range(self, title: str, part_type: str) -> tuple[int, int, str]:
        ranges = [
            (r"rx\s*6600", 110, 150, "RX 6600"),
            (r"rx\s*6700\s*xt", 180, 240, "RX 6700 XT"),
            (r"rx\s*6800", 230, 310, "RX 6800"),
            (r"rx\s*7700\s*xt", 290, 360, "RX 7700 XT"),
            (r"rx\s*7800\s*xt", 380, 470, "RX 7800 XT"),
            (r"rtx\s*3060", 160, 220, "RTX 3060"),
            (r"rtx\s*4070\s*ti", 520, 680, "RTX 4070 Ti"),
            (r"rtx\s*4070", 390, 500, "RTX 4070"),
            (r"ryzen\s*5\s*7600", 130, 170, "Ryzen 5 7600"),
            (r"ryzen\s*7\s*7700", 150, 200, "Ryzen 7 7700"),
            (r"7800x3d", 230, 300, "Ryzen 7 7800X3D"),
            (r"ryzen\s*9\s*7900x?", 200, 280, "Ryzen 9 7900/7900X"),
            (r"i5\s*-?\s*12600k", 120, 170, "Intel i5-12600K"),
            (r"i5\s*-?\s*13600k", 190, 260, "Intel i5-13600K"),
            (r"i7\s*-?\s*13700k", 240, 330, "Intel i7-13700K"),
            (r"b650", 90, 170, "B650 motherboard"),
            (r"x670", 190, 280, "X670 motherboard"),
            (r"32\s*gb.*ddr5|ddr5.*32\s*gb", 70, 110, "32GB DDR5 RAM"),
            (r"64\s*gb.*ddr5|ddr5.*64\s*gb", 140, 220, "64GB DDR5 RAM"),
            (r"2\s*tb.*nvme|nvme.*2\s*tb", 70, 115, "2TB NVMe"),
            (r"650\s*w.*gold|650w.*gold", 55, 90, "650W Gold PSU"),
            (r"750\s*w.*gold|750w.*gold", 75, 120, "750W Gold PSU"),
            (r"gaming\s*pc|desktop\s*pc|full\s*pc|complete\s*pc|prebuilt", 250, 900, "Full PC"),
        ]

        for pattern, low, high, label in ranges:
            if re.search(pattern, title):
                return low, high, label

        fallback = {
            "GPU": (120, 320, "Generic GPU"),
            "CPU": (80, 220, "Generic CPU"),
            "Motherboard": (70, 180, "Generic motherboard"),
            "RAM": (35, 120, "Generic RAM"),
            "Storage": (30, 120, "Generic storage"),
            "PSU": (40, 120, "Generic PSU"),
            "Case": (35, 110, "Generic case"),
            "Cooling": (20, 90, "Generic cooling"),
            "Full PC": (250, 900, "Generic full PC"),
        }

        low, high, label = fallback.get(part_type, (0, 0, ""))
        return low, high, label

    def generate_seller_message(
        self,
        title: str,
        part_type: str,
        decision: str,
        tone: str = "friendly",
    ) -> str:
        evidence_lines = buyer_evidence_checklist(part_type)
        evidence_text = "\n".join(f"- {line}" for line in evidence_lines)

        if decision == "NEGOTIATE":
            intro = "Hi, I am interested in this item. Before buying, would you be able to send a couple of extra details please?"
            close = "If everything checks out, would you consider a fair offer? Thanks."
        elif decision == "AVOID":
            intro = "Hi, I am interested, but I would need to check a few things first before considering it."
            close = "Thanks, just being careful before buying used PC parts."
        else:
            intro = "Hi, I am interested in this item. Could you help confirm a few details please?"
            close = "Just want to check everything clearly before buying. Thanks."

        return (
            f"{intro}\n\n"
            f"Item: {title}\n\n"
            f"Ideally:\n"
            f"{evidence_text}\n\n"
            f"{close}"
        )

    def _choose_decision(
        self,
        deal_score: int,
        scam_risk: float,
        budget_fit: int,
        evidence_confidence: int,
    ) -> str:
        if scam_risk >= 7:
            return "AVOID"
        if evidence_confidence < 35:
            return "EVIDENCE REQUIRED"
        if deal_score >= 82 and budget_fit >= 70 and scam_risk <= 4:
            return "BUY NOW"
        if deal_score >= 68 and scam_risk <= 5:
            return "WATCH"
        if evidence_confidence < 45:
            return "NEGOTIATE"
        if deal_score < 48:
            return "WAIT"
        return "WATCH"


def evidence_for_part(part_type: str) -> list[str]:
    part = part_type.lower()

    if part == "gpu":
        return [
            "A photo of the GPU with today's date written on paper",
            "A GPU-Z screenshot if possible",
            "A quick photo or video showing it running",
            "Confirmation it has no artifacting, overheating, or fan issues",
            "Whether it has been mined on, if known",
        ]

    if part == "cpu":
        return [
            "A clear photo of the top of the CPU",
            "A clear photo of the pins or pads",
            "Confirmation there are no bent pins or damage",
            "Confirmation it boots and works normally",
        ]

    if part == "motherboard":
        return [
            "A clear photo of the CPU socket",
            "Confirmation the I/O shield is included",
            "BIOS version if known",
            "Confirmation RAM and PCIe slots are not damaged",
        ]

    if part == "psu":
        return [
            "Exact model number",
            "Age of the PSU",
            "Which cables are included",
            "Confirmation it has had no stability issues",
            "Warranty status if available",
        ]

    if part == "storage":
        return [
            "SMART health screenshot if possible",
            "Total writes if available",
            "Exact model and capacity",
            "Confirmation it is not locked or faulty",
        ]

    return [
        "Extra clear photos",
        "Proof the item works",
        "Confirmation of condition",
        "Any known issues or missing parts",
    ]


def clamp_int(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))
