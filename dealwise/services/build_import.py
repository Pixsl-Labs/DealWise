from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from dealwise.services.pc_builder_service import PCBuilderService


PART_ORDER = {
    "GPU": 1,
    "CPU": 2,
    "Motherboard": 3,
    "RAM": 4,
    "PSU": 5,
    "Case": 6,
    "Storage": 7,
    "Cooling": 8,
    "Unknown": 99,
}


DEFAULT_NEGATIVE_KEYWORDS = [
    "broken",
    "faulty",
    "spares",
    "repair",
    "wanted",
    "laptop",
    "notebook",
    "zenbook",
    "macbook",
    "ipad",
    "tablet",
]


@dataclass(slots=True)
class ParsedBuildItem:
    part_type: str
    name: str
    price: float | None
    status: str
    reused: bool
    raw_line: str
    search_terms: list[str]


@dataclass(slots=True)
class BuildImportResult:
    items: list[ParsedBuildItem]
    total: float
    reused_count: int
    priced_count: int
    unknown_count: int
    warnings: list[str]

    def to_markdown(self) -> str:
        lines = [
            "# Imported Build",
            "",
            f"Total priced cost: £{self.total:.0f}",
            f"Priced items: {self.priced_count}",
            f"Reused items: {self.reused_count}",
            f"Unknown items: {self.unknown_count}",
            "",
            "| Part | Item | Price | Status |",
            "|---|---|---:|---|",
        ]

        for item in self.items:
            price = "Reuse" if item.reused else ("-" if item.price is None else f"£{item.price:.0f}")
            lines.append(f"| {item.part_type} | {item.name} | {price} | {item.status} |")

        if self.warnings:
            lines.extend(["", "## Warnings"])
            lines.extend(f"- {warning}" for warning in self.warnings)

        return "\n".join(lines)

    def to_text(self) -> str:
        lines = [
            "Imported Build",
            f"Total priced cost: £{self.total:.0f}",
            f"Priced items: {self.priced_count}",
            f"Reused items: {self.reused_count}",
            f"Unknown items: {self.unknown_count}",
            "",
        ]

        for item in self.items:
            price = "Reuse" if item.reused else ("-" if item.price is None else f"£{item.price:.0f}")
            lines.append(f"{item.part_type}: {item.name} | {price} | {item.status}")

        if self.warnings:
            lines.append("")
            lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in self.warnings)

        return "\n".join(lines)

    def to_json(self) -> str:
        return json.dumps(
            {
                "total": self.total,
                "reused_count": self.reused_count,
                "priced_count": self.priced_count,
                "unknown_count": self.unknown_count,
                "warnings": self.warnings,
                "items": [asdict(item) for item in self.items],
            },
            indent=2,
            sort_keys=True,
        )


class BuildImportService:
    """Natural-language build import and export helper.

    This intentionally accepts messy copied text from ChatGPT, Reddit, Discord,
    PCPartPicker-style lists, notes apps and marketplace planning chats.
    """

    def __init__(self, pc_builder_service: PCBuilderService) -> None:
        self.pc_builder_service = pc_builder_service

    def parse(self, text: str) -> BuildImportResult:
        section_reuse = False
        items: list[ParsedBuildItem] = []
        warnings: list[str] = []

        for raw_line in text.splitlines():
            original_line = raw_line.strip()

            if not original_line:
                continue

            cleaned_line = self._clean_line(original_line)
            lower = cleaned_line.lower()

            if self._is_heading(lower):
                if "reuse" in lower or "existing" in lower:
                    section_reuse = True
                continue

            if "reuse" in lower or "existing" in lower:
                section_reuse = True

            part_type = self.detect_part_type(cleaned_line)

            if part_type == "Unknown" and not self._looks_like_component_line(cleaned_line):
                continue

            price = self.extract_price(cleaned_line)
            reused = section_reuse or self._line_marks_reuse(cleaned_line)
            name = self.extract_name(cleaned_line)

            if not name:
                continue

            if reused:
                status = "Bought"
                price = 0 if price is None else price
            elif price is not None:
                status = "Buying Candidate"
            else:
                status = "Needed"

            items.append(
                ParsedBuildItem(
                    part_type=part_type,
                    name=name,
                    price=price,
                    status=status,
                    reused=reused,
                    raw_line=original_line,
                    search_terms=self.search_terms_for(name, part_type),
                )
            )

        if not items:
            warnings.append("No build components were detected. Try pasting a fuller list with part names.")

        if any(item.part_type == "Unknown" for item in items):
            warnings.append("Some items could not be categorised. Review them before applying.")

        total = sum(item.price or 0 for item in items if not item.reused)
        reused_count = sum(1 for item in items if item.reused)
        priced_count = sum(1 for item in items if item.price is not None and not item.reused)
        unknown_count = sum(1 for item in items if item.part_type == "Unknown")

        return BuildImportResult(
            items=items,
            total=total,
            reused_count=reused_count,
            priced_count=priced_count,
            unknown_count=unknown_count,
            warnings=warnings,
        )

    def apply_to_pc_builder(self, result: BuildImportResult) -> None:
        existing_parts = {
            part.part_type: part
            for part in self.pc_builder_service.list_build_parts()
        }

        with self.pc_builder_service.database.connect() as connection:
            for item in result.items:
                if item.part_type == "Unknown":
                    continue

                budget = float(item.price or 0)
                bought_price = float(item.price or 0) if item.status == "Bought" else 0.0
                notes = (
                    f"Imported from build list on {datetime.now(timezone.utc).date().isoformat()}. "
                    f"Raw: {item.raw_line}"
                )

                existing = existing_parts.get(item.part_type)

                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO build_parts (
                            part_type,
                            target,
                            budget,
                            bought_price,
                            status,
                            priority,
                            notes
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            item.part_type,
                            item.name,
                            budget,
                            bought_price,
                            item.status,
                            PART_ORDER.get(item.part_type, 99),
                            notes,
                        ),
                    )
                    continue

                connection.execute(
                    """
                    UPDATE build_parts
                    SET
                        target = ?,
                        budget = CASE WHEN ? > 0 THEN ? ELSE budget END,
                        bought_price = ?,
                        status = ?,
                        notes = ?
                    WHERE id = ?
                    """,
                    (
                        item.name,
                        budget,
                        budget,
                        bought_price,
                        item.status,
                        notes,
                        existing.id,
                    ),
                )

            connection.commit()

    def build_export(self, format_name: str = "markdown") -> str:
        target = self.pc_builder_service.get_target_build()
        parts = self.pc_builder_service.list_build_parts()
        cost_low, cost_high = self.pc_builder_service.estimate_build_cost(target.platform)

        payload = {
            "target_build": {
                "budget": target.total_budget,
                "use_case": target.use_case,
                "platform": target.platform,
                "notes": target.notes,
                "estimated_low": cost_low,
                "estimated_high": cost_high,
            },
            "parts": [
                {
                    "part_type": part.part_type,
                    "target": part.target,
                    "budget": part.budget,
                    "bought_price": part.bought_price,
                    "status": part.status,
                    "priority": part.priority,
                    "notes": part.notes,
                }
                for part in parts
            ],
        }

        if format_name == "json":
            return json.dumps(payload, indent=2, sort_keys=True)

        if format_name == "txt":
            lines = [
                "DealWise Build Summary",
                f"Budget: £{target.total_budget:.0f}",
                f"Use Case: {target.use_case}",
                f"Build Path: {target.platform}",
                f"Estimated Parts Cost: £{cost_low} - £{cost_high}",
                "",
                "Parts:",
            ]

            for part in parts:
                marker = "✓" if part.status == "Bought" else "□"
                lines.append(f"{marker} {part.part_type}: {part.target} | £{part.budget:.0f} | {part.status}")

            return "\n".join(lines)

        lines = [
            "# DealWise Build Summary",
            "",
            f"- Budget: £{target.total_budget:.0f}",
            f"- Use Case: {target.use_case}",
            f"- Build Path: {target.platform}",
            f"- Estimated Parts Cost: £{cost_low} - £{cost_high}",
            "",
            "## Parts",
            "",
            "| Done | Part | Target | Budget | Status |",
            "|---|---|---|---:|---|",
        ]

        for part in parts:
            marker = "✓" if part.status == "Bought" else "□"
            lines.append(f"| {marker} | {part.part_type} | {part.target} | £{part.budget:.0f} | {part.status} |")

        return "\n".join(lines)

    def search_terms_for(self, name: str, part_type: str) -> list[str]:
        base = name.strip()
        lower = base.lower()
        terms = [base]

        replacements = [
            ("ryzen 7 ", ""),
            ("ryzen 9 ", ""),
            ("ryzen 5 ", ""),
            ("amd ", ""),
            ("intel ", ""),
            ("nvidia ", ""),
            ("radeon ", ""),
        ]

        simplified = lower

        for old, new in replacements:
            simplified = simplified.replace(old, new)

        simplified = " ".join(simplified.split()).upper()

        if simplified and simplified.lower() != lower:
            terms.append(simplified)

        if "7800x3d" in lower:
            terms.extend(["Ryzen 7800X3D", "7800 X3D"])
        elif "7900x" in lower:
            terms.extend(["Ryzen 7900X", "7900 X"])
        elif "7900" in lower and "rx" not in lower:
            terms.extend(["Ryzen 7900", "7900 CPU"])
        elif "b650" in lower:
            terms.extend(["B650 motherboard", "AM5 B650"])
        elif "2tb" in lower and "ssd" in lower:
            terms.extend(["2TB NVMe", "2TB SSD"])

        unique: list[str] = []

        for term in terms:
            clean = term.strip()
            if clean and clean.lower() not in {existing.lower() for existing in unique}:
                unique.append(clean)

        return unique[:4]

    def detect_part_type(self, text: str) -> str:
        lower = text.lower()

        if any(term in lower for term in ["rtx", "gtx", "rx ", "radeon", "geforce", "gpu", "graphics card"]):
            return "GPU"
        if any(term in lower for term in ["7800x3d", "7900x", "7900", "7700", "7600", "ryzen", "intel core", "i5", "i7", "i9", "processor", "cpu"]):
            return "CPU"
        if any(term in lower for term in ["b650", "b650e", "x670", "x670e", "a620", "b550", "x570", "z790", "b760", "motherboard", "mobo"]):
            return "Motherboard"
        if any(term in lower for term in ["ddr5", "ddr4", "ram", "memory"]):
            return "RAM"
        if any(term in lower for term in ["nvme", "ssd", "hdd", "hard drive", "sn850", "990 pro", "nm790", "storage"]):
            return "Storage"
        if any(term in lower for term in ["psu", "power supply", "650w", "750w", "850w", "1000w"]):
            return "PSU"
        if any(term in lower for term in ["case", "chassis", "corsair 4000d", "fractal", "nzxt"]):
            return "Case"
        if any(term in lower for term in ["cooler", "cooling", "aio", "heatsink", "thermalright", "noctua"]):
            return "Cooling"

        return "Unknown"

    def extract_price(self, text: str) -> float | None:
        patterns = [
            r"£\s*([\d,.]+)",
            r"([\d,.]+)\s*£",
        ]

        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                try:
                    return float(match.group(1).replace(",", ""))
                except ValueError:
                    return None

        return None

    def extract_name(self, text: str) -> str:
        cleaned = re.sub(r"^[✓✔☑✅□\-*\s]+", "", text).strip()
        cleaned = re.sub(r"£\s*[\d,.]+", "", cleaned)
        cleaned = re.sub(r"[\d,.]+\s*£", "", cleaned)
        cleaned = re.sub(r"\b(reuse|reused|existing|already got|owned)\b[:\-]?", "", cleaned, flags=re.IGNORECASE)
        cleaned = cleaned.replace(":", " ")
        cleaned = " ".join(cleaned.split())
        return cleaned.strip(" -|")

    def _line_marks_reuse(self, text: str) -> bool:
        lower = text.lower()
        return (
            text.strip().startswith(("✓", "✔", "☑", "✅"))
            or "reuse" in lower
            or "existing" in lower
            or "already got" in lower
            or "owned" in lower
        )

    def _is_heading(self, lower: str) -> bool:
        headings = [
            "final build cost",
            "build cost",
            "reuse",
            "existing",
            "parts list",
            "pcpartpicker",
            "total",
        ]

        if lower in headings:
            return True

        if lower.endswith(":") and not re.search(r"£\s*\d", lower):
            return True

        return False

    def _looks_like_component_line(self, line: str) -> bool:
        if self.extract_price(line) is not None:
            return True

        return self._line_marks_reuse(line)
