from __future__ import annotations

from dataclasses import dataclass


USE_CASE_OPTIONS = [
    "1440p gaming / best performance per pound",
    "1080p budget gaming",
    "1440p high refresh gaming",
    "Gaming + university work",
    "Cybersecurity labs / VMs",
    "Quiet daily desktop",
    "Streaming / content creation",
]

BUILD_PATH_OPTIONS = [
    "AM5 / ATX target",
    "AM5 / mATX value build",
    "AM4 / used value build",
    "Intel LGA1700 / DDR5",
    "Intel LGA1700 / DDR4 value",
    "Current Dell SFF only",
]


@dataclass(slots=True)
class PartOption:
    part_type: str
    name: str
    tier: int
    search_query: str
    compatibility_note: str


class BuildCatalog:
    """Static Phase 4/5 build intelligence foundation.

    Later versions can replace this with a real compatibility database, but this
    gives DealWise useful local recommendations immediately.
    """

    def use_case_options(self) -> list[str]:
        return list(USE_CASE_OPTIONS)

    def build_path_options(self) -> list[str]:
        return list(BUILD_PATH_OPTIONS)

    def options_for_part(self, part_type: str, build_path: str) -> list[PartOption]:
        path = build_path.lower()
        part = part_type.lower()

        options: dict[str, list[PartOption]] = {
            "gpu": [
                PartOption("GPU", "RX 6600", 1, "RX 6600", "Good budget 1080p/entry 1440p option."),
                PartOption("GPU", "RX 6700 XT", 2, "RX 6700 XT", "Strong used 1440p value."),
                PartOption("GPU", "RX 6800", 3, "RX 6800", "Excellent used 1440p target."),
                PartOption("GPU", "RX 7700 XT", 4, "RX 7700 XT", "Newer 1440p option if priced well."),
                PartOption("GPU", "RX 7800 XT", 5, "RX 7800 XT", "Higher-end 1440p option."),
            ],
            "cpu": [
                PartOption("CPU", "Ryzen 5 5600", 1, "Ryzen 5 5600", "AM4 value CPU."),
                PartOption("CPU", "Ryzen 7 5700X", 2, "Ryzen 7 5700X", "AM4 value 8-core CPU."),
                PartOption("CPU", "Ryzen 5 7600", 3, "Ryzen 5 7600", "AM5 value gaming CPU."),
                PartOption("CPU", "Ryzen 7 7700", 4, "Ryzen 7 7700", "AM5 8-core target."),
                PartOption("CPU", "Intel i5-12600K", 3, "i5 12600K", "LGA1700 value option."),
                PartOption("CPU", "Intel i5-13600K", 4, "i5 13600K", "LGA1700 stronger option."),
            ],
            "motherboard": [
                PartOption("Motherboard", "B550", 1, "B550 motherboard", "AM4 DDR4 motherboard."),
                PartOption("Motherboard", "B650", 3, "B650 motherboard", "AM5 DDR5 value motherboard."),
                PartOption("Motherboard", "B650M", 3, "B650M motherboard", "AM5 DDR5 mATX value motherboard."),
                PartOption("Motherboard", "X670", 4, "X670 motherboard", "Higher-end AM5 motherboard."),
                PartOption("Motherboard", "B660 DDR4", 2, "B660 DDR4 motherboard", "Intel LGA1700 DDR4 value board."),
                PartOption("Motherboard", "B760 DDR5", 3, "B760 DDR5 motherboard", "Intel LGA1700 DDR5 board."),
            ],
            "ram": [
                PartOption("RAM", "16GB DDR4", 1, "16GB DDR4 RAM", "Budget DDR4 option."),
                PartOption("RAM", "32GB DDR4", 2, "32GB DDR4 RAM", "Good AM4/DDR4 value."),
                PartOption("RAM", "16GB DDR5", 3, "16GB DDR5 RAM", "Entry DDR5 option."),
                PartOption("RAM", "32GB DDR5", 4, "32GB DDR5 RAM", "Recommended AM5/DDR5 target."),
                PartOption("RAM", "64GB DDR5", 5, "64GB DDR5 RAM", "Useful for VMs/labs/content work."),
            ],
            "storage": [
                PartOption("Storage", "1TB NVMe", 1, "1TB NVMe SSD", "Good starting point."),
                PartOption("Storage", "2TB NVMe", 2, "2TB NVMe SSD", "Recommended main target."),
                PartOption("Storage", "4TB NVMe", 3, "4TB NVMe SSD", "High-capacity option."),
            ],
            "psu": [
                PartOption("PSU", "550W Bronze", 1, "550W PSU", "Only for lower-power builds."),
                PartOption("PSU", "650W Gold", 2, "650W Gold PSU", "Recommended minimum for RX 6800 class."),
                PartOption("PSU", "750W Gold", 3, "750W Gold PSU", "Better headroom."),
                PartOption("PSU", "850W Gold", 4, "850W Gold PSU", "High headroom for future GPU upgrades."),
            ],
            "case": [
                PartOption("Case", "mATX airflow case", 1, "mATX airflow case", "Compact value option."),
                PartOption("Case", "ATX airflow case", 2, "ATX airflow case", "Best general upgrade path."),
                PartOption("Case", "Fractal airflow case", 3, "Fractal airflow case", "Premium airflow option."),
                PartOption("Case", "Corsair 4000D", 3, "Corsair 4000D", "Popular airflow case."),
            ],
            "cooling": [
                PartOption("Cooling", "Stock cooler initially", 1, "AM5 stock cooler", "Fine for early budget stage."),
                PartOption("Cooling", "Thermalright air cooler", 2, "Thermalright CPU cooler", "Excellent value air cooler."),
                PartOption("Cooling", "240mm AIO", 3, "240mm AIO cooler", "Higher-risk used purchase."),
            ],
        }

        raw_options = options.get(part, [PartOption(part_type, "Manual choice", 1, part_type, "Manual compatibility check needed.")])
        return [option for option in raw_options if self.is_compatible(option, path)]

    def is_compatible(self, option: PartOption, build_path_lower: str) -> bool:
        name = option.name.lower()
        part = option.part_type.lower()

        if "current dell sff" in build_path_lower:
            if part == "gpu":
                return "rx 6400" in name or "low profile" in name
            if part in {"case", "motherboard", "psu"}:
                return False
            return True

        if "am5" in build_path_lower:
            if part == "cpu":
                return "ryzen 5 7600" in name or "ryzen 7 7700" in name
            if part == "motherboard":
                return "b650" in name or "x670" in name
            if part == "ram":
                return "ddr5" in name
            return True

        if "am4" in build_path_lower:
            if part == "cpu":
                return "5600" in name or "5700x" in name
            if part == "motherboard":
                return "b550" in name
            if part == "ram":
                return "ddr4" in name
            return True

        if "lga1700" in build_path_lower and "ddr4" in build_path_lower:
            if part == "cpu":
                return "12600k" in name or "13600k" in name
            if part == "motherboard":
                return "b660 ddr4" in name
            if part == "ram":
                return "ddr4" in name
            return True

        if "lga1700" in build_path_lower and "ddr5" in build_path_lower:
            if part == "cpu":
                return "12600k" in name or "13600k" in name
            if part == "motherboard":
                return "b760 ddr5" in name
            if part == "ram":
                return "ddr5" in name
            return True

        return True

    def default_target_for_part(self, part_type: str, build_path: str) -> str:
        options = self.options_for_part(part_type, build_path)
        if not options:
            return part_type

        # Pick a strong middle/top value, not the cheapest absolute option.
        index = min(len(options) - 1, max(0, len(options) - 2))
        return options[index].name

    def search_queries_for_build(self, parts: list, build_path: str) -> list[str]:
        queries: list[str] = []

        for part in parts:
            if getattr(part, "status", "") == "Bought":
                continue

            target = getattr(part, "target", "").strip()
            part_type = getattr(part, "part_type", "").strip()

            if target:
                queries.append(self.clean_query(target))
            else:
                queries.append(self.default_target_for_part(part_type, build_path))

        seen: set[str] = set()
        unique: list[str] = []

        for query in queries:
            if query.lower() in seen:
                continue
            seen.add(query.lower())
            unique.append(query)

        return unique

    def clean_query(self, target: str) -> str:
        # For "RX 6800 / RX 7700 XT / RX 7800 XT", use the first target as the
        # actual marketplace search to avoid huge noisy queries.
        first = target.split("/")[0].strip()
        return first or target.strip()

    def compatibility_summary(self, build_path: str, use_case: str) -> list[str]:
        path = build_path.lower()
        lines: list[str] = []

        if "am5" in path:
            lines.extend(
                [
                    "AM5 selected: only Ryzen 7000/9000-style CPUs, B650/X670 boards, and DDR5 RAM should be shown.",
                    "Good long-term upgrade path. Avoid DDR4 motherboards and AM4 CPUs.",
                ]
            )
        elif "am4" in path:
            lines.extend(
                [
                    "AM4 selected: good used-value path, but weaker future upgrade path than AM5.",
                    "Only B550/AM4 CPUs and DDR4 RAM should be shown.",
                ]
            )
        elif "lga1700" in path:
            lines.append("Intel LGA1700 selected: motherboard RAM type matters, so DDR4 and DDR5 paths must not be mixed.")
        elif "current dell sff" in path:
            lines.extend(
                [
                    "Current Dell SFF selected: only low-profile GPU upgrades should be considered.",
                    "Major GPU, PSU, motherboard, and case upgrades are better saved for a new ATX/mATX build.",
                ]
            )

        if "cybersecurity" in use_case.lower() or "vm" in use_case.lower():
            lines.append("VM/lab use case detected: prioritise 32GB or 64GB RAM and enough NVMe storage.")

        if not lines:
            lines.append("Compatibility rules are active. Pick a build path to narrow the parts shown.")

        return lines
