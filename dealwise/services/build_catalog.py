from __future__ import annotations

from dataclasses import dataclass


USE_CASE_OPTIONS = [
    "1440p gaming / best performance per pound",
    "1080p budget gaming",
    "1440p high refresh gaming",
    "4K gaming / premium build",
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
    estimated_low: int
    estimated_high: int


class BuildCatalog:
    """Static build intelligence foundation.

    Higher tier = stronger and usually more expensive.
    Compatibility is filtered by selected build path.
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
                PartOption("GPU", "RX 6600", 1, "RX 6600", "Budget 1080p / entry 1440p option.", 110, 150),
                PartOption("GPU", "RX 6700 XT", 2, "RX 6700 XT", "Strong used 1440p value.", 180, 240),
                PartOption("GPU", "RX 6800", 3, "RX 6800", "Excellent used 1440p target.", 230, 310),
                PartOption("GPU", "RX 7700 XT", 4, "RX 7700 XT", "Newer 1440p option if priced well.", 290, 360),
                PartOption("GPU", "RX 7800 XT", 5, "RX 7800 XT", "High-end 1440p option.", 380, 470),
                PartOption("GPU", "RX 7900 XT", 6, "RX 7900 XT", "Premium AMD option.", 520, 650),
                PartOption("GPU", "RTX 4070", 5, "RTX 4070", "Efficient Nvidia 1440p option.", 390, 500),
                PartOption("GPU", "RTX 4070 Ti", 6, "RTX 4070 Ti", "Stronger Nvidia 1440p/entry 4K option.", 520, 680),
                PartOption("GPU", "RTX 4080", 7, "RTX 4080", "Premium 4K-capable option.", 750, 950),
            ],
            "cpu": [
                PartOption("CPU", "Ryzen 5 5600", 1, "Ryzen 5 5600", "AM4 value CPU.", 65, 95),
                PartOption("CPU", "Ryzen 7 5700X", 2, "Ryzen 7 5700X", "AM4 value 8-core CPU.", 110, 150),
                PartOption("CPU", "Ryzen 5 7600", 3, "Ryzen 5 7600", "AM5 value gaming CPU.", 130, 170),
                PartOption("CPU", "Ryzen 7 7700", 4, "Ryzen 7 7700", "AM5 8-core target.", 150, 200),
                PartOption("CPU", "Ryzen 7 7800X3D", 5, "Ryzen 7 7800X3D", "Premium AM5 gaming CPU.", 270, 350),
                PartOption("CPU", "Ryzen 9 7900", 6, "Ryzen 9 7900", "AM5 12-core productivity/gaming option.", 250, 340),
                PartOption("CPU", "Ryzen 9 7900X", 7, "Ryzen 9 7900X", "Higher-power AM5 12-core option.", 280, 370),
                PartOption("CPU", "Ryzen 9 7950X", 8, "Ryzen 9 7950X", "High-end AM5 productivity option.", 390, 520),
                PartOption("CPU", "Intel i5-12600K", 3, "i5 12600K", "LGA1700 value option.", 120, 170),
                PartOption("CPU", "Intel i5-13600K", 4, "i5 13600K", "LGA1700 stronger option.", 190, 260),
                PartOption("CPU", "Intel i7-13700K", 5, "i7 13700K", "LGA1700 high-end option.", 240, 330),
            ],
            "motherboard": [
                PartOption("Motherboard", "A620", 1, "A620 motherboard", "Budget AM5 board. Check VRMs/features.", 65, 95),
                PartOption("Motherboard", "B550", 1, "B550 motherboard", "AM4 DDR4 motherboard.", 70, 110),
                PartOption("Motherboard", "B650M", 3, "B650M motherboard", "AM5 DDR5 mATX value motherboard.", 90, 140),
                PartOption("Motherboard", "B650", 4, "B650 motherboard", "AM5 DDR5 value motherboard.", 110, 170),
                PartOption("Motherboard", "B650E", 5, "B650E motherboard", "AM5 board with stronger PCIe feature set.", 150, 230),
                PartOption("Motherboard", "X670", 6, "X670 motherboard", "Higher-end AM5 motherboard.", 190, 280),
                PartOption("Motherboard", "X670E", 7, "X670E motherboard", "Premium AM5 motherboard.", 240, 380),
                PartOption("Motherboard", "B660 DDR4", 2, "B660 DDR4 motherboard", "Intel LGA1700 DDR4 value board.", 70, 120),
                PartOption("Motherboard", "B760 DDR5", 3, "B760 DDR5 motherboard", "Intel LGA1700 DDR5 board.", 110, 170),
                PartOption("Motherboard", "Z790 DDR5", 5, "Z790 DDR5 motherboard", "Higher-end Intel LGA1700 DDR5 board.", 170, 280),
            ],
            "ram": [
                PartOption("RAM", "16GB DDR4", 1, "16GB DDR4 RAM", "Budget DDR4 option.", 20, 35),
                PartOption("RAM", "32GB DDR4", 2, "32GB DDR4 RAM", "Good AM4/DDR4 value.", 40, 65),
                PartOption("RAM", "16GB DDR5", 3, "16GB DDR5 RAM", "Entry DDR5 option.", 35, 55),
                PartOption("RAM", "32GB DDR5", 4, "32GB DDR5 RAM", "Recommended AM5/DDR5 target.", 70, 110),
                PartOption("RAM", "64GB DDR5", 5, "64GB DDR5 RAM", "Useful for VMs/labs/content work.", 140, 220),
                PartOption("RAM", "96GB DDR5", 6, "96GB DDR5 RAM", "Heavy VM/workstation option.", 220, 340),
            ],
            "storage": [
                PartOption("Storage", "1TB NVMe", 1, "1TB NVMe SSD", "Good starting point.", 35, 60),
                PartOption("Storage", "2TB NVMe", 2, "2TB NVMe SSD", "Recommended main target.", 70, 115),
                PartOption("Storage", "4TB NVMe", 3, "4TB NVMe SSD", "High-capacity option.", 160, 260),
            ],
            "psu": [
                PartOption("PSU", "550W Bronze", 1, "550W PSU", "Only for lower-power builds.", 35, 55),
                PartOption("PSU", "650W Gold", 2, "650W Gold PSU", "Recommended minimum for RX 6800 class.", 55, 90),
                PartOption("PSU", "750W Gold", 3, "750W Gold PSU", "Better headroom.", 75, 120),
                PartOption("PSU", "850W Gold", 4, "850W Gold PSU", "High headroom for future GPU upgrades.", 95, 150),
                PartOption("PSU", "1000W Gold", 5, "1000W Gold PSU", "Premium high-power headroom.", 130, 210),
            ],
            "case": [
                PartOption("Case", "mATX airflow case", 1, "mATX airflow case", "Compact value option.", 40, 75),
                PartOption("Case", "ATX airflow case", 2, "ATX airflow case", "Best general upgrade path.", 50, 100),
                PartOption("Case", "Corsair 4000D", 3, "Corsair 4000D", "Popular airflow case.", 65, 115),
                PartOption("Case", "Fractal airflow case", 4, "Fractal airflow case", "Premium airflow option.", 90, 170),
            ],
            "cooling": [
                PartOption("Cooling", "Stock cooler initially", 1, "AM5 stock cooler", "Fine for early budget stage.", 0, 20),
                PartOption("Cooling", "Thermalright air cooler", 2, "Thermalright CPU cooler", "Excellent value air cooler.", 25, 45),
                PartOption("Cooling", "Noctua air cooler", 3, "Noctua CPU cooler", "Premium air cooling.", 55, 95),
                PartOption("Cooling", "240mm AIO", 4, "240mm AIO cooler", "Higher-risk used purchase.", 60, 120),
                PartOption("Cooling", "360mm AIO", 5, "360mm AIO cooler", "Premium cooling, check case fit.", 90, 170),
            ],
        }

        raw_options = options.get(
            part,
            [PartOption(part_type, "Manual choice", 1, part_type, "Manual compatibility check needed.", 0, 0)],
        )
        return [option for option in raw_options if self.is_compatible(option, path)]

    def is_compatible(self, option: PartOption, build_path_lower: str) -> bool:
        name = option.name.lower()
        part = option.part_type.lower()

        if "current dell sff" in build_path_lower:
            if part == "gpu":
                return "low profile" in name or "rx 6400" in name
            if part in {"case", "motherboard", "psu"}:
                return False
            return True

        if "am5" in build_path_lower:
            if part == "cpu":
                return "ryzen 5 7600" in name or "ryzen 7 7700" in name or "7800x3d" in name or "7900" in name or "7950x" in name
            if part == "motherboard":
                return "a620" in name or "b650" in name or "x670" in name
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
                return "12600k" in name or "13600k" in name or "13700k" in name
            if part == "motherboard":
                return "ddr4" in name
            if part == "ram":
                return "ddr4" in name
            return True

        if "lga1700" in build_path_lower and "ddr5" in build_path_lower:
            if part == "cpu":
                return "12600k" in name or "13600k" in name or "13700k" in name
            if part == "motherboard":
                return "ddr5" in name or "z790" in name
            if part == "ram":
                return "ddr5" in name
            return True

        return True

    def default_target_for_part(self, part_type: str, build_path: str, use_case: str = "") -> str:
        options = self.options_for_part(part_type, build_path)

        if not options:
            return part_type

        use = use_case.lower()

        if "4k" in use or "premium" in use:
            index = len(options) - 1
        elif "cybersecurity" in use or "vm" in use:
            if part_type.lower() == "ram":
                index = min(len(options) - 1, 4)
            elif part_type.lower() == "cpu":
                index = min(len(options) - 1, 5)
            else:
                index = min(len(options) - 1, max(0, len(options) - 2))
        elif "budget" in use:
            index = min(len(options) - 1, 1)
        else:
            index = min(len(options) - 1, max(0, len(options) - 2))

        return options[index].name

    def estimate_option_cost(self, part_type: str, target: str, build_path: str) -> tuple[int, int]:
        options = self.options_for_part(part_type, build_path)

        for option in options:
            if option.name.lower() == target.lower():
                return option.estimated_low, option.estimated_high

        if options:
            return options[0].estimated_low, options[-1].estimated_high

        return 0, 0

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
        first = target.split("/")[0].strip()
        return first or target.strip()

    def compatibility_summary(self, build_path: str, use_case: str) -> list[str]:
        path = build_path.lower()
        lines: list[str] = []

        if "am5" in path:
            lines.extend(
                [
                    "AM5 selected: Ryzen 7000/9000-style CPUs, AM5 motherboards, and DDR5 RAM only.",
                    "CPU, motherboard, and RAM options are filtered to avoid AM4/DDR4 mismatches.",
                ]
            )
        elif "am4" in path:
            lines.extend(
                [
                    "AM4 selected: good used-value path, but weaker future upgrade path than AM5.",
                    "Only AM4 CPUs, B550-style motherboards, and DDR4 RAM are shown.",
                ]
            )
        elif "lga1700" in path:
            lines.append("Intel LGA1700 selected: motherboard RAM type is locked to the chosen DDR4 or DDR5 path.")
        elif "current dell sff" in path:
            lines.extend(
                [
                    "Current Dell SFF selected: only low-profile and low-power upgrades should be considered.",
                    "Major GPU, PSU, motherboard, and case upgrades are better saved for a new ATX/mATX build.",
                ]
            )

        if "cybersecurity" in use_case.lower() or "vm" in use_case.lower():
            lines.append("VM/lab use case detected: prioritise RAM, CPU cores, and NVMe capacity.")

        if not lines:
            lines.append("Compatibility rules are active. Pick a build path to narrow the parts shown.")

        return lines
