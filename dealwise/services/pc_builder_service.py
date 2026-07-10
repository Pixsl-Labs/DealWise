from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone

from dealwise.data.database import DatabaseManager


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


class PCBuilderService:
    """Stores and analyses current PC and target build information."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

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
