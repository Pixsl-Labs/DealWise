from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from urllib.parse import quote_plus


RAM_NEGATIVE_KEYWORDS = [
    "ddr4",
    "ddr3",
    "sodimm",
    "so-dimm",
    "laptop",
    "notebook",
    "macbook",
    "server",
    "ecc",
    "registered",
    "rdimm",
    "broken",
    "faulty",
    "spares",
    "repair",
    "wanted",
]


@dataclass(slots=True)
class RAMHuntProfile:
    mode: str = "Final 32GB Kit"
    capacity_gb: int = 32
    module_config: str = "2x16GB"
    memory_type: str = "DDR5"
    min_speed: int = 6000
    max_speed: int = 7200
    max_cas_latency: int = 36
    expo_preferred: bool = True
    allow_xmp: bool = True
    rgb: str = "Any"
    condition: str = "Either"
    delivery_mode: str = "Delivery or collection"
    collection_distance_miles: int = 25
    item_price_max: float = 180
    all_in_price_max: float = 200
    deadline: str = "2026-07-14"
    marketplaces: list[str] = field(
        default_factory=lambda: [
            "Vinted",
            "eBay",
            "Gumtree",
            "CeX",
            "Facebook Marketplace",
            "Scan",
            "Amazon UK",
            "Overclockers UK",
            "AWD-IT",
            "Ebuyer",
            "Currys",
        ]
    )
    excluded_keywords: list[str] = field(default_factory=lambda: list(RAM_NEGATIVE_KEYWORDS))
    urgent: bool = True

    def deadline_label(self) -> str:
        try:
            parsed = date.fromisoformat(self.deadline)
        except ValueError:
            return "No valid deadline"

        days_left = (parsed - date.today()).days

        if days_left < 0:
            return f"Deadline passed: {parsed.isoformat()}"

        if days_left == 0:
            return "Deadline is today"

        return f"{days_left} day(s) remaining until {parsed.isoformat()}"

    @classmethod
    def final_default(cls) -> "RAMHuntProfile":
        return cls()

    @classmethod
    def temporary_default(cls) -> "RAMHuntProfile":
        return cls(
            mode="Temporary Test Stick",
            capacity_gb=16,
            module_config="1x16GB",
            memory_type="DDR5",
            min_speed=4800,
            max_speed=5600,
            max_cas_latency=46,
            expo_preferred=False,
            allow_xmp=True,
            rgb="Any",
            condition="Either",
            item_price_max=35,
            all_in_price_max=40,
            excluded_keywords=[
                "ddr4",
                "ddr3",
                "sodimm",
                "so-dimm",
                "laptop",
                "notebook",
                "macbook",
                "server",
                "ecc",
                "registered",
                "rdimm",
                "broken",
                "faulty",
                "spares",
                "repair",
                "wanted",
            ],
            urgent=True,
        )


@dataclass(slots=True)
class RAMSpec:
    raw_title: str
    ddr_generation: str | None = None
    total_capacity_gb: int | None = None
    module_count: int | None = None
    module_capacity_gb: int | None = None
    speed: int | None = None
    cas_latency: int | None = None
    expo: bool = False
    xmp: bool = False
    desktop_udimm: bool | None = None
    sodimm: bool = False
    ecc_or_rdimm: bool = False
    brand: str | None = None
    sku: str | None = None
    rgb: bool | None = None
    factory_matched_kit: bool | None = None
    requires_manual_confirmation: bool = False

    def short_label(self) -> str:
        parts: list[str] = []

        if self.total_capacity_gb:
            parts.append(f"{self.total_capacity_gb}GB")

        if self.module_count and self.module_capacity_gb:
            parts.append(f"{self.module_count}x{self.module_capacity_gb}GB")

        if self.ddr_generation:
            parts.append(self.ddr_generation)

        if self.speed:
            parts.append(str(self.speed))

        if self.cas_latency:
            parts.append(f"CL{self.cas_latency}")

        if self.expo:
            parts.append("EXPO")
        elif self.xmp:
            parts.append("XMP")

        if self.sodimm:
            parts.append("SO-DIMM")
        elif self.desktop_udimm:
            parts.append("Desktop UDIMM")

        return " ".join(parts) if parts else "Specification requires manual confirmation"


@dataclass(slots=True)
class RAMDealScore:
    score: int
    confidence: str
    recommendation: str
    factors: list[tuple[str, int, int, str]]
    warnings: list[str]
    all_in_price: float | None

    def lines(self) -> list[str]:
        output = [
            f"RAM Deal Score: {self.score}/100",
            f"Confidence: {self.confidence}",
            f"Recommendation: {self.recommendation}",
            "",
        ]

        for label, points, maximum, note in self.factors:
            output.append(f"{label}: {points}/{maximum} — {note}")

        if self.warnings:
            output.append("")
            output.append("Warnings:")
            output.extend(f"- {warning}" for warning in self.warnings)

        return output


class RAMHuntService:
    """RAM-specific parsing, query generation, scoring and browser handoff."""

    RETAIL_URLS = {
        "Scan": "https://www.scan.co.uk/search?q={query}",
        "Amazon UK": "https://www.amazon.co.uk/s?k={query}",
        "Overclockers UK": "https://www.overclockers.co.uk/search?sSearch={query}",
        "AWD-IT": "https://www.awd-it.co.uk/catalogsearch/result/?q={query}",
        "Ebuyer": "https://www.ebuyer.com/search?q={query}",
        "Currys": "https://www.currys.co.uk/search?q={query}",
    }

    HANDOFF_URLS = {
        "eBay": "https://www.ebay.co.uk/sch/i.html?_nkw={query}",
        "Gumtree": "https://www.gumtree.com/search?search_category=all&q={query}",
        "CeX": "https://uk.webuy.com/search?stext={query}",
        "Facebook Marketplace": "https://www.facebook.com/marketplace/search/?query={query}",
    }

    BRANDS = {
        "corsair": "Corsair",
        "kingston": "Kingston",
        "fury": "Kingston Fury",
        "g.skill": "G.Skill",
        "gskill": "G.Skill",
        "trident": "G.Skill",
        "flare": "G.Skill",
        "crucial": "Crucial",
        "teamgroup": "TeamGroup",
        "team group": "TeamGroup",
        "lexar": "Lexar",
        "patriot": "Patriot",
        "adata": "ADATA",
        "xpg": "ADATA XPG",
        "samsung": "Samsung",
        "crucial": "Crucial",
    }

    def parse(self, title: str, description: str = "") -> RAMSpec:
        text = f"{title} {description}".strip()
        lower = text.lower()

        spec = RAMSpec(raw_title=title)

        if "ddr5" in lower:
            spec.ddr_generation = "DDR5"
        elif "ddr4" in lower:
            spec.ddr_generation = "DDR4"

        module_match = re.search(
            r"(?P<count>[124])\s*[x×]\s*(?P<size>8|16|24|32|48|64)\s*gb",
            lower,
            flags=re.IGNORECASE,
        )

        if module_match:
            spec.module_count = int(module_match.group("count"))
            spec.module_capacity_gb = int(module_match.group("size"))
            spec.total_capacity_gb = spec.module_count * spec.module_capacity_gb
            spec.factory_matched_kit = spec.module_count >= 2
        else:
            total_match = re.search(r"\b(8|16|24|32|48|64|96|128)\s*gb\b", lower)

            if total_match:
                spec.total_capacity_gb = int(total_match.group(1))

        speed_match = re.search(r"\b(4800|5200|5600|6000|6200|6400|6600|6800|7000|7200)\s*(?:mhz|mt/s|mt|mts)?\b", lower)

        if speed_match:
            spec.speed = int(speed_match.group(1))

        cl_match = re.search(r"\bcl\s*([0-9]{2})\b|c([0-9]{2})\b", lower)

        if cl_match:
            spec.cas_latency = int(cl_match.group(1) or cl_match.group(2))

        spec.expo = "expo" in lower or "amd expo" in lower
        spec.xmp = "xmp" in lower

        spec.sodimm = any(term in lower for term in ["sodimm", "so-dimm", "laptop ram", "notebook ram"])

        spec.ecc_or_rdimm = any(
            term in lower
            for term in [
                "ecc",
                "rdimm",
                "registered",
                "server ram",
                "server memory",
            ]
        )

        if spec.sodimm:
            spec.desktop_udimm = False
        elif any(term in lower for term in ["udimm", "desktop", "dimm"]):
            spec.desktop_udimm = True
        else:
            spec.desktop_udimm = None

        spec.rgb = True if "rgb" in lower else None

        for key, brand in self.BRANDS.items():
            if key in lower:
                spec.brand = brand
                break

        sku_match = re.search(r"\b([A-Z]{2,}[A-Z0-9]{4,}[A-Z0-9-]*)\b", text)

        if sku_match:
            spec.sku = sku_match.group(1)

        if not spec.ddr_generation or not spec.total_capacity_gb or not spec.speed:
            spec.requires_manual_confirmation = True

        return spec

    def query_variants(self, profile: RAMHuntProfile) -> list[str]:
        if profile.mode == "Temporary Test Stick":
            base = [
                "8GB DDR5 desktop RAM",
                "16GB DDR5 desktop RAM",
                "DDR5 4800 UDIMM",
                "DDR5 5200 UDIMM",
                "DDR5 5600 desktop RAM",
                "single DDR5 stick",
            ]
        elif profile.mode == "Final 32GB Kit":
            base = [
                "32GB DDR5 6000 CL30",
                "2x16GB DDR5 6000",
                "DDR5 6000 EXPO 32GB",
                "32GB AM5 RAM",
                "Corsair Vengeance DDR5 6000",
                "Kingston Fury Beast DDR5 6000",
                "G.Skill Flare X5 6000",
                "G.Skill Trident Z5 Neo",
                "TeamGroup T-Create Expert DDR5",
                "Lexar Ares DDR5 6000",
            ]
        else:
            base = [
                f"{profile.capacity_gb}GB {profile.memory_type} {profile.min_speed}",
                f"{profile.module_config} {profile.memory_type}",
                f"{profile.memory_type} {profile.min_speed} RAM",
            ]

        unique: list[str] = []

        for query in base:
            clean = " ".join(query.split())

            if clean.lower() not in {existing.lower() for existing in unique}:
                unique.append(clean)

        return unique

    def browser_urls(self, profile: RAMHuntProfile) -> list[tuple[str, str, str]]:
        primary_query = self.query_variants(profile)[0]
        encoded = quote_plus(primary_query)
        urls: list[tuple[str, str, str]] = []

        for marketplace in profile.marketplaces:
            if marketplace in self.HANDOFF_URLS:
                label = "Browser handoff"
                urls.append((marketplace, label, self.HANDOFF_URLS[marketplace].format(query=encoded)))
            elif marketplace in self.RETAIL_URLS:
                label = "New retail / warranty reference"
                urls.append((marketplace, label, self.RETAIL_URLS[marketplace].format(query=encoded)))

        return urls

    def all_in_price(
        self,
        item_price: float | None,
        delivery_price: float | None = None,
        buyer_fee_estimate: float | None = None,
        travel_cost: float | None = None,
    ) -> float | None:
        if item_price is None:
            return None

        return (
            item_price
            + (delivery_price or 0)
            + (buyer_fee_estimate or 0)
            + (travel_cost or 0)
        )

    def score(
        self,
        spec: RAMSpec,
        profile: RAMHuntProfile,
        item_price: float | None = None,
        delivery_price: float | None = None,
        buyer_fee_estimate: float | None = None,
        travel_cost: float | None = None,
        evidence_notes: str = "",
        condition: str = "Either",
    ) -> RAMDealScore:
        warnings: list[str] = []
        factors: list[tuple[str, int, int, str]] = []
        total = 0
        max_total = 100
        all_in = self.all_in_price(item_price, delivery_price, buyer_fee_estimate, travel_cost)

        price_points = 0

        if all_in is None:
            warnings.append("Price requires manual confirmation.")
            price_note = "Missing all-in price."
        elif all_in <= profile.all_in_price_max * 0.70:
            price_points = 35
            price_note = "Excellent price against configured all-in limit."
        elif all_in <= profile.all_in_price_max * 0.85:
            price_points = 30
            price_note = "Good price against configured all-in limit."
        elif all_in <= profile.all_in_price_max:
            price_points = 24
            price_note = "Within configured all-in limit."
        else:
            price_points = 8
            price_note = "Over configured all-in limit."
            warnings.append("All-in price is above the configured maximum.")

        factors.append(("Price value", price_points, 35, price_note))
        total += price_points

        spec_points = 0

        if spec.ddr_generation == "DDR5":
            spec_points += 5
        elif spec.ddr_generation:
            warnings.append(f"{spec.ddr_generation} is not suitable for this AM5 DDR5 build.")
        else:
            warnings.append("DDR generation requires manual confirmation.")

        if profile.mode == "Final 32GB Kit":
            if spec.total_capacity_gb == 32:
                spec_points += 4
            elif spec.total_capacity_gb:
                warnings.append(f"Capacity is {spec.total_capacity_gb}GB, not the target 32GB.")
            else:
                warnings.append("Capacity requires manual confirmation.")

            if spec.module_count == 2 and spec.module_capacity_gb == 16:
                spec_points += 4
            elif spec.module_count == 1:
                warnings.append("Single-stick RAM is not recommended as the final gaming configuration.")
            elif spec.module_count:
                warnings.append("Module configuration is not the preferred 2x16GB final kit.")
            else:
                warnings.append("Module count requires manual confirmation.")

            if spec.speed and spec.speed >= profile.min_speed:
                spec_points += 4
            elif spec.speed:
                warnings.append(f"Speed {spec.speed} is below target {profile.min_speed}.")
            else:
                warnings.append("Speed requires manual confirmation.")

            if spec.cas_latency and spec.cas_latency <= profile.max_cas_latency:
                spec_points += 3
            elif spec.cas_latency:
                warnings.append(f"CAS latency CL{spec.cas_latency} is above configured maximum CL{profile.max_cas_latency}.")
            else:
                warnings.append("CAS latency requires manual confirmation.")
        else:
            if spec.ddr_generation == "DDR5":
                spec_points += 5
            if spec.total_capacity_gb in {8, 16, 32}:
                spec_points += 5
            if spec.module_count in {None, 1}:
                spec_points += 5
            if spec.speed and 4800 <= spec.speed <= 5600:
                spec_points += 5

        spec_points = min(20, spec_points)
        factors.append(("Specification", spec_points, 20, spec.short_label()))
        total += spec_points

        am5_points = 0

        if spec.ddr_generation == "DDR5" and not spec.sodimm and not spec.ecc_or_rdimm:
            am5_points += 7

        if spec.speed == 6000:
            am5_points += 4
        elif spec.speed and 5600 <= spec.speed <= 6400:
            am5_points += 2

        if spec.expo:
            am5_points += 4
        elif spec.xmp and profile.allow_xmp:
            am5_points += 2

        if spec.sodimm:
            warnings.append("SO-DIMM/laptop memory is not compatible with the target desktop AM5 build.")

        if spec.ecc_or_rdimm:
            warnings.append("ECC/RDIMM/server memory should be rejected for this build.")

        factors.append(("AM5 suitability", min(15, am5_points), 15, "Desktop DDR5 / AM5 preference checks."))
        total += min(15, am5_points)

        kit_points = 0

        if profile.mode == "Temporary Test Stick":
            if spec.module_count in {None, 1}:
                kit_points = 10
                kit_note = "Single desktop DDR5 stick is acceptable for temporary testing."
            else:
                kit_points = 7
                kit_note = "Multiple modules are fine, but this profile only needs temporary POST RAM."
        else:
            if spec.module_count == 2 and spec.module_capacity_gb == 16:
                kit_points = 10
                kit_note = "Looks like a proper 2x16GB kit."
            elif spec.module_count == 1:
                kit_points = 2
                kit_note = "Single stick is not ideal for final gaming configuration."
            else:
                kit_points = 4
                kit_note = "Matched kit confidence requires manual confirmation."

        factors.append(("Matched kit confidence", kit_points, 10, kit_note))
        total += kit_points

        evidence_lower = evidence_notes.lower()
        evidence_points = 0

        if spec.sku:
            evidence_points += 3

        if "bios" in evidence_lower or "cpu-z" in evidence_lower or "cpuz" in evidence_lower or "hwinfo" in evidence_lower:
            evidence_points += 4

        if "both sticks" in evidence_lower or "2x16" in evidence_lower:
            evidence_points += 2

        if "date" in evidence_lower or "username" in evidence_lower:
            evidence_points += 1

        factors.append(("Seller evidence", min(10, evidence_points), 10, "SKU/proof of detection/current ownership."))
        total += min(10, evidence_points)

        warranty_points = 0

        if condition.lower() == "new":
            warranty_points += 3

        if "warranty" in evidence_lower or "receipt" in evidence_lower or "return" in evidence_lower:
            warranty_points += 2

        factors.append(("Warranty / returns", min(5, warranty_points), 5, "Retail/private-sale confidence."))
        total += min(5, warranty_points)

        score = max(0, min(max_total, total))

        if spec.requires_manual_confirmation:
            confidence = "Low"
        elif evidence_points >= 6 and spec.sku:
            confidence = "High"
        elif evidence_points >= 3 or spec.sku:
            confidence = "Medium"
        else:
            confidence = "Low"

        if profile.mode == "Temporary Test Stick":
            recommendation = "Suitable for testing — not recommended as the final gaming configuration."
        elif score >= 82 and not warnings:
            recommendation = "Excellent final RAM candidate."
        elif score >= 70:
            recommendation = "Good candidate if missing specifications are confirmed."
        elif score >= 55:
            recommendation = "Worth watching, but not a clean buy yet."
        else:
            recommendation = "Reject or only consider if evidence/price improves."

        return RAMDealScore(
            score=score,
            confidence=confidence,
            recommendation=recommendation,
            factors=factors,
            warnings=warnings,
            all_in_price=all_in,
        )

    def seller_message(self, profile: RAMHuntProfile, offer_price: float | None = None) -> str:
        if profile.mode == "Temporary Test Stick":
            return (
                "Hi, I’m looking for a cheap desktop DDR5 stick just to test/post an AM5 build. "
                "Could you confirm it is desktop UDIMM DDR5, not laptop SO-DIMM or server ECC/RDIMM? "
                "If possible, could you send a photo of the label/model number? Thanks."
            )

        offer_line = ""

        if offer_price is not None and offer_price > 0:
            offer_line = (
                f"\n\nMy maximum all-in budget is around £{profile.all_in_price_max:.0f}, "
                f"so would you consider £{offer_price:.0f}?"
            )

        return (
            "Hi, I’m interested in the RAM for an AM5 build. Could you confirm the exact model number/SKU "
            "and whether this is a matched 2x16GB desktop DDR5 kit?\n\n"
            "Could you also send a BIOS/CPU-Z/HWiNFO screenshot showing both modules detected, the total 32GB capacity, "
            "and the speed they are currently running at?\n\n"
            "Also just to check, is it desktop UDIMM RAM rather than laptop SO-DIMM or server ECC/RDIMM?"
            f"{offer_line}\n\nThanks."
        )
