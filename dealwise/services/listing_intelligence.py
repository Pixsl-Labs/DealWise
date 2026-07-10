from __future__ import annotations

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


class ListingIntelligenceService:
    """Phase 3 decision/seller-message foundation.

    This is deliberately simple and explainable for now. Later phases can make
    scoring more advanced once price history, seller data, and reverse image
    checks exist.
    """

    def analyse(
        self,
        title: str,
        price: float | None,
        url: str,
        marketplace: str,
        part_type: str | None = None,
        budget: float | None = None,
    ) -> ListingDecision:
        safe_part_type = part_type or infer_part_type(title)
        reasoning: list[str] = []

        deal_score = 55
        scam_risk = 3.5
        build_fit = 65
        budget_fit = 60
        evidence_confidence = 35
        urgency_score = 40

        if price is not None and budget and budget > 0:
            if price <= budget:
                budget_fit = 90
                deal_score += 10
                reasoning.append("Price is within the allocated part budget.")
            else:
                budget_fit = 35
                deal_score -= 10
                reasoning.append("Price is above the allocated part budget.")

        if safe_part_type != "Unknown":
            build_fit += 10
            reasoning.append(f"Listing appears to match part type: {safe_part_type}.")

        if marketplace.lower() == "manual":
            reasoning.append("Manual URL/listing input needs extra evidence before buying.")
            evidence_confidence -= 5

        if not url:
            scam_risk += 1.5
            reasoning.append("No URL was provided, so the listing cannot be independently checked.")

        if safe_part_type in {"GPU", "PSU", "AIO"}:
            scam_risk += 1.0
            evidence_confidence -= 10
            reasoning.append(f"{safe_part_type} is higher risk when buying used.")

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
        )

    def generate_seller_message(
        self,
        title: str,
        part_type: str,
        decision: str,
        tone: str = "friendly",
    ) -> str:
        evidence_lines = evidence_for_part(part_type)

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

        if evidence_confidence < 45:
            return "NEGOTIATE"

        if deal_score >= 80 and budget_fit >= 75 and scam_risk <= 3:
            return "BUY NOW"

        if deal_score >= 65:
            return "WATCH"

        return "WAIT"


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
