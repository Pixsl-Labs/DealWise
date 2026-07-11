from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

from dealwise.data.database import DatabaseManager
from dealwise.services.build_catalog import BuildCatalog


@dataclass(slots=True)
class CurrentPC:
    imported_at: str
    raw_inxi: str
    system_model: str
    cpu: str
    gpu: str
    memory: str
    storage: str
    distro: str
    kernel: str
    form_factor_notes: str


@dataclass(slots=True)
class TargetBuild:
    name: str
    total_budget: float
    use_case: str
    platform: str
    notes: str


@dataclass(slots=True)
class BuildPart:
    id: int
    part_type: str
    target: str
    budget: float
    bought_price: float
    status: str
    priority: int
    notes: str


@dataclass(slots=True)
class PCValuation:
    whole_unit_low: int
    whole_unit_high: int
    separate_parts_low: int
    separate_parts_high: int
    confidence: str
    notes: list[str]


class PCBuilderService:
    """Stores and analyses current PC and target build information."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database
        self.catalog = BuildCatalog()

    def import_current_pc(self) -> CurrentPC:
        try:
            process = subprocess.run(
                ["inxi", "-Fx"],
                check=False,
                capture_output=True,
                text=True,
                timeout=12,
            )
            raw_output = process.stdout.strip() or process.stderr.strip()
        except FileNotFoundError:
            raw_output = "inxi is not installed. Install it with: sudo apt install inxi"
        except subprocess.TimeoutExpired:
            raw_output = "inxi timed out while collecting system information."

        current_pc = self.parse_inxi(raw_output)
        self.save_current_pc(current_pc)
        return current_pc

    def import_current_pc_from_text(self, raw_output: str) -> CurrentPC:
        """Import current PC details from pasted inxi output.

        This is safer and more transparent than automatically running commands
        because the user can see exactly what command is used and what output is
        imported into DealWise.
        """

        cleaned_output = raw_output.strip()

        if not cleaned_output:
            cleaned_output = "No system information was pasted."

        current_pc = self.parse_inxi(cleaned_output)
        self.save_current_pc(current_pc)
        return current_pc

    def clear_current_pc(self) -> None:
        """Remove the saved current PC profile."""

        with self.database.connect() as connection:
            connection.execute("DELETE FROM current_pc WHERE id = 1")
            connection.commit()

    def parse_inxi(self, raw_output: str) -> CurrentPC:
        system_model = self._extract_first_match(
            raw_output,
            [
                r"Machine:\s*(?:Type:.*?System:\s*)?(.+)",
                r"System:\s*(.+)",
            ],
        )
        cpu = self._extract_first_match(raw_output, [r"CPU:\s*(.+)", r"model:\s*([^\\n]+)"])
        gpu = self._extract_gpu(raw_output)
        memory = self._extract_first_match(raw_output, [r"Memory:\s*(.+)", r"RAM:\s*(.+)"])
        storage = self._extract_first_match(raw_output, [r"Drives:\s*(.+)", r"Storage:\s*(.+)"])
        distro = self._extract_first_match(raw_output, [r"Distro:\s*(.+)"])
        kernel = self._extract_first_match(raw_output, [r"Kernel:\s*([^\\s]+)"])

        notes = self._infer_form_factor_notes(raw_output, system_model)

        return CurrentPC(
            imported_at=datetime.now(timezone.utc).isoformat(),
            raw_inxi=raw_output,
            system_model=system_model or "Unknown system",
            cpu=cpu or "Unknown CPU",
            gpu=gpu or "Unknown GPU",
            memory=memory or "Unknown memory",
            storage=storage or "Unknown storage",
            distro=distro or "Unknown distro",
            kernel=kernel or "Unknown kernel",
            form_factor_notes=notes,
        )

    def save_current_pc(self, current_pc: CurrentPC) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO current_pc (
                    id,
                    imported_at,
                    raw_inxi,
                    system_model,
                    cpu,
                    gpu,
                    memory,
                    storage,
                    distro,
                    kernel,
                    form_factor_notes
                )
                VALUES (1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    current_pc.imported_at,
                    current_pc.raw_inxi,
                    current_pc.system_model,
                    current_pc.cpu,
                    current_pc.gpu,
                    current_pc.memory,
                    current_pc.storage,
                    current_pc.distro,
                    current_pc.kernel,
                    current_pc.form_factor_notes,
                ),
            )
            connection.commit()

    def get_current_pc(self) -> CurrentPC | None:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM current_pc WHERE id = 1").fetchone()

        if row is None:
            return None

        data = dict(row)
        data.pop("id", None)
        return CurrentPC(**data)

    def get_target_build(self) -> TargetBuild:
        with self.database.connect() as connection:
            row = connection.execute("SELECT * FROM target_build WHERE id = 1").fetchone()

        if row is None:
            return TargetBuild(
                name="Main Target Build",
                total_budget=600,
                use_case="1440p gaming / best performance per pound",
                platform="AM5 / ATX target",
                notes="Prioritise GPU first.",
            )

        data = dict(row)
        data.pop("id", None)
        return TargetBuild(**data)

    def save_target_build(
        self,
        total_budget: float,
        use_case: str,
        platform: str,
        notes: str,
    ) -> None:
        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO target_build (
                    id,
                    name,
                    total_budget,
                    use_case,
                    platform,
                    notes
                )
                VALUES (1, 'Main Target Build', ?, ?, ?, ?)
                """,
                (total_budget, use_case, platform, notes),
            )
            connection.commit()

    def list_build_parts(self) -> list[BuildPart]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM build_parts
                ORDER BY priority ASC, id ASC
                """
            ).fetchall()

        return [BuildPart(**dict(row)) for row in rows]

    def update_part_status(self, part_id: int, status: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE build_parts SET status = ? WHERE id = ?",
                (status, part_id),
            )
            connection.commit()

    def update_part_target(self, part_id: int, target: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE build_parts SET target = ? WHERE id = ?",
                (target, part_id),
            )
            connection.commit()

    def apply_recommended_parts(self, build_path: str, use_case: str) -> None:
        """Apply compatible recommended parts and sensible budgets.

        This keeps CPU, motherboard and RAM aligned to the selected build path.
        It also prevents Storage/Cooling and other parts from staying at £0.
        """

        parts = self.list_build_parts()

        with self.database.connect() as connection:
            for part in parts:
                recommended = self.catalog.default_target_for_part(
                    part.part_type,
                    build_path,
                    use_case,
                )

                low, high = self.catalog.estimate_option_cost(
                    part.part_type,
                    recommended,
                    build_path,
                )

                recommended_budget = high if high > 0 else part.budget

                connection.execute(
                    """
                    UPDATE build_parts
                    SET target = ?, budget = ?
                    WHERE id = ?
                    """,
                    (recommended, recommended_budget, part.id),
                )

            connection.commit()

    def estimate_build_cost(self, build_path: str) -> tuple[int, int]:
        """Return rough low/high cost for the currently selected build parts."""

        low_total = 0
        high_total = 0

        for part in self.list_build_parts():
            low, high = self.catalog.estimate_option_cost(
                part.part_type,
                part.target,
                build_path,
            )

            if low == 0 and high == 0 and part.budget > 0:
                low = int(part.budget)
                high = int(part.budget)

            low_total += low
            high_total += high

        return low_total, high_total

    def compatibility_summary(self, build_path: str, use_case: str) -> list[str]:
        return self.catalog.compatibility_summary(build_path, use_case)

    def part_options(self, part_type: str, build_path: str):
        return self.catalog.options_for_part(part_type, build_path)

    def option_cost(self, part_type: str, target: str, build_path: str) -> tuple[int, int]:
        return self.catalog.estimate_option_cost(part_type, target, build_path)

    def needed_part_search_queries(self, build_path: str) -> list[str]:
        return self.catalog.search_queries_for_build(self.list_build_parts(), build_path)

    def estimate_current_pc_value(self, current_pc: CurrentPC) -> PCValuation:
        """Estimate rough resale value for the current PC.

        This is a local heuristic, not live marketplace pricing. Later DealWise
        phases can replace this with real market data from saved listings and
        marketplace connectors.
        """

        combined = " ".join(
            [
                current_pc.raw_inxi,
                current_pc.system_model,
                current_pc.cpu,
                current_pc.gpu,
                current_pc.memory,
                current_pc.storage,
            ]
        ).lower()

        notes: list[str] = []
        separate_low = 0
        separate_high = 0

        cpu_low, cpu_high, cpu_note = self._estimate_cpu_value(combined)
        gpu_low, gpu_high, gpu_note = self._estimate_gpu_value(combined)
        ram_low, ram_high, ram_note = self._estimate_ram_value(current_pc.memory)
        storage_low, storage_high, storage_note = self._estimate_storage_value(current_pc.storage)
        base_low, base_high, base_note = self._estimate_base_system_value(combined)

        for low, high, note in [
            (cpu_low, cpu_high, cpu_note),
            (gpu_low, gpu_high, gpu_note),
            (ram_low, ram_high, ram_note),
            (storage_low, storage_high, storage_note),
            (base_low, base_high, base_note),
        ]:
            separate_low += low
            separate_high += high
            if note:
                notes.append(note)

        if "sff" in combined or "small form factor" in combined:
            whole_multiplier_low = 0.65
            whole_multiplier_high = 0.80
            notes.append("SFF/OEM systems usually sell for less as a full unit because upgrade options are limited.")
        elif "laptop" in combined or "notebook" in combined:
            whole_multiplier_low = 0.80
            whole_multiplier_high = 0.95
            notes.append("Laptop-style systems are usually sold as one unit rather than parted out.")
        else:
            whole_multiplier_low = 0.72
            whole_multiplier_high = 0.88
            notes.append("Whole PC sale estimate is lower than part-out value for faster sale and buyer convenience.")

        whole_low = self._round_to_nearest_5(int(separate_low * whole_multiplier_low))
        whole_high = self._round_to_nearest_5(int(separate_high * whole_multiplier_high))
        separate_low = self._round_to_nearest_5(separate_low)
        separate_high = self._round_to_nearest_5(separate_high)

        confidence = self._valuation_confidence(combined)

        notes.append("This is a rough offline estimate. Use completed listings later for accurate pricing.")
        notes.append("Separate part value is usually higher but takes longer and carries more selling effort.")

        return PCValuation(
            whole_unit_low=max(0, whole_low),
            whole_unit_high=max(0, whole_high),
            separate_parts_low=max(0, separate_low),
            separate_parts_high=max(0, separate_high),
            confidence=confidence,
            notes=notes,
        )

    def _estimate_cpu_value(self, text: str) -> tuple[int, int, str]:
        if "i7-7700" in text or "i7 7700" in text:
            return 30, 45, "CPU estimate: Intel i7-7700 roughly valued as an older used quad-core."
        if "i7-6700" in text or "i7 6700" in text:
            return 25, 40, "CPU estimate: Intel i7-6700 roughly valued as an older used quad-core."
        if "i5-7500" in text or "i5 7500" in text:
            return 15, 30, "CPU estimate: older Intel i5 detected."
        if "ryzen 7 7700" in text:
            return 140, 180, "CPU estimate: Ryzen 7 7700 class detected."
        if "ryzen 5 7600" in text:
            return 110, 150, "CPU estimate: Ryzen 5 7600 class detected."
        if "ryzen" in text:
            return 60, 130, "CPU estimate: Ryzen CPU detected, exact value needs model confirmation."
        if "intel" in text or "core" in text:
            return 25, 80, "CPU estimate: Intel CPU detected, exact value needs model confirmation."
        return 0, 0, "CPU estimate: no clear CPU model detected."

    def _estimate_gpu_value(self, text: str) -> tuple[int, int, str]:
        if "rx 6400" in text:
            return 70, 95, "GPU estimate: RX 6400 low-profile class detected."
        if "rx 6500" in text or "6500 xt" in text:
            return 75, 105, "GPU estimate: RX 6500 XT class detected."
        if "rx 6600" in text:
            return 120, 155, "GPU estimate: RX 6600 class detected."
        if "6700 xt" in text:
            return 190, 240, "GPU estimate: RX 6700 XT class detected."
        if "rx 6800" in text:
            return 240, 310, "GPU estimate: RX 6800 class detected."
        if "7700 xt" in text:
            return 280, 350, "GPU estimate: RX 7700 XT class detected."
        if "rtx 3050" in text:
            return 100, 145, "GPU estimate: RTX 3050 class detected."
        if "rtx 3060" in text:
            return 170, 230, "GPU estimate: RTX 3060 class detected."
        if "radeon" in text or "geforce" in text or "graphics" in text:
            return 40, 120, "GPU estimate: dedicated graphics likely detected, exact value needs model confirmation."
        if "intel hd" in text or "uhd graphics" in text:
            return 0, 0, "GPU estimate: integrated graphics detected."
        return 0, 0, "GPU estimate: no clear dedicated GPU model detected."

    def _estimate_ram_value(self, text: str) -> tuple[int, int, str]:
        capacity = self._extract_memory_capacity_gb(text)

        if capacity >= 64:
            return 80, 140, "RAM estimate: 64GB or more detected."
        if capacity >= 32:
            if "ddr5" in text:
                return 65, 95, "RAM estimate: 32GB DDR5 class detected."
            return 40, 65, "RAM estimate: 32GB DDR4/unknown class detected."
        if capacity >= 16:
            if "ddr5" in text:
                return 35, 55, "RAM estimate: 16GB DDR5 class detected."
            return 20, 35, "RAM estimate: 16GB DDR4/unknown class detected."
        if capacity >= 8:
            return 10, 20, "RAM estimate: 8GB class detected."
        return 0, 0, "RAM estimate: no clear memory capacity detected."

    def _estimate_storage_value(self, text: str) -> tuple[int, int, str]:
        if "2tb" in text or "2 tb" in text:
            return 65, 100, "Storage estimate: 2TB storage class detected."
        if "1tb" in text or "1 tb" in text:
            return 35, 60, "Storage estimate: 1TB storage class detected."
        if "512gb" in text or "512 gb" in text or "500gb" in text or "500 gb" in text:
            return 20, 35, "Storage estimate: 500GB/512GB storage class detected."
        if "256gb" in text or "256 gb" in text:
            return 10, 20, "Storage estimate: 256GB storage class detected."
        if "nvme" in text or "ssd" in text:
            return 15, 45, "Storage estimate: SSD/NVMe detected but capacity unclear."
        return 0, 0, "Storage estimate: no clear storage capacity detected."

    def _estimate_base_system_value(self, text: str) -> tuple[int, int, str]:
        if "dell precision" in text and ("sff" in text or "small form factor" in text):
            return 35, 60, "Base system estimate: Dell Precision SFF chassis/motherboard/PSU value added."
        if "dell precision" in text:
            return 45, 80, "Base system estimate: Dell Precision chassis/motherboard/PSU value added."
        if "desktop" in text or "tower" in text:
            return 40, 90, "Base system estimate: desktop chassis/motherboard/PSU value added."
        return 20, 50, "Base system estimate: generic case/motherboard/PSU allowance added."

    def _extract_memory_capacity_gb(self, text: str) -> int:
        matches = re.findall(r"(\d+)\s*(?:gib|gb)", text, flags=re.IGNORECASE)

        if not matches:
            return 0

        numbers = [int(match) for match in matches]

        if not numbers:
            return 0

        return max(numbers)

    def _valuation_confidence(self, text: str) -> str:
        signals = 0

        for term in ["i7", "i5", "ryzen", "rx ", "rtx", "gtx", "ram", "memory", "nvme", "ssd", "dell", "precision"]:
            if term in text:
                signals += 1

        if signals >= 5:
            return "Medium"
        if signals >= 3:
            return "Low-Medium"
        return "Low"

    def _round_to_nearest_5(self, value: int) -> int:
        return int(round(value / 5) * 5)

    def _extract_first_match(self, text: str, patterns: list[str]) -> str:
        for pattern in patterns:
            match = re.search(pattern, text, flags=re.IGNORECASE)
            if match:
                return " ".join(match.group(1).strip().split())
        return ""

    def _extract_gpu(self, text: str) -> str:
        graphics_match = re.search(
            r"Graphics:\s*(.+?)(?:\n[A-Z][A-Za-z]+:|\Z)",
            text,
            flags=re.IGNORECASE | re.DOTALL,
        )

        if graphics_match:
            return " ".join(graphics_match.group(1).strip().split())

        return self._extract_first_match(text, [r"Device-\d+:\s*(.+)", r"GPU:\s*(.+)"])

    def _infer_form_factor_notes(self, raw_output: str, system_model: str) -> str:
        combined = f"{raw_output} {system_model}".lower()

        if "sff" in combined or "small form factor" in combined:
            return (
                "Small form factor detected or likely. GPU clearance, PSU options, "
                "and motherboard upgrades may be limited. Consider saving major parts "
                "for a future ATX or mATX build."
            )

        if "laptop" in combined or "notebook" in combined:
            return (
                "Laptop-like system detected. Internal upgrades are likely limited to "
                "storage and memory depending on model."
            )

        if "dell precision" in combined:
            return (
                "Dell Precision system detected. Check case size, OEM motherboard, "
                "PSU connectors, and GPU clearance before buying upgrades."
            )

        return (
            "No strict form factor warning detected. Still confirm case clearance, "
            "PSU wattage, motherboard socket, and RAM compatibility before buying."
        )
