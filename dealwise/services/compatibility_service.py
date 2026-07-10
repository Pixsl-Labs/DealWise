from __future__ import annotations

import re


class CompatibilityService:
    """Rule-based compatibility checks for the current DealWise build plan."""

    def analyse_build(self, parts: list, build_path: str, hardware_preference: str = "") -> list[str]:
        targets = {part.part_type: part.target for part in parts}
        lines: list[str] = []

        cpu = targets.get("CPU", "")
        motherboard = targets.get("Motherboard", "")
        ram = targets.get("RAM", "")
        gpu = targets.get("GPU", "")
        psu = targets.get("PSU", "")
        case = targets.get("Case", "")
        cooling = targets.get("Cooling", "")

        cpu_platform = self.cpu_platform(cpu)
        board_platform = self.motherboard_platform(motherboard)
        ram_type = self.ram_type(ram)
        build_lower = build_path.lower()

        if "am5" in build_lower:
            if cpu_platform != "AM5":
                lines.append("Warning: Selected CPU does not look like an AM5 CPU.")
            if board_platform != "AM5":
                lines.append("Warning: Selected motherboard does not look like an AM5 motherboard.")
            if ram_type != "DDR5":
                lines.append("Warning: AM5 requires DDR5 RAM.")
            if cpu_platform == "AM5" and board_platform == "AM5" and ram_type == "DDR5":
                lines.append("CPU, motherboard and RAM look compatible for AM5.")
        elif "am4" in build_lower:
            if cpu_platform != "AM4":
                lines.append("Warning: Selected CPU does not look like an AM4 CPU.")
            if board_platform != "AM4":
                lines.append("Warning: Selected motherboard does not look like an AM4 motherboard.")
            if ram_type != "DDR4":
                lines.append("Warning: AM4 requires DDR4 RAM.")
            if cpu_platform == "AM4" and board_platform == "AM4" and ram_type == "DDR4":
                lines.append("CPU, motherboard and RAM look compatible for AM4.")
        elif "lga1700" in build_lower:
            if cpu_platform != "LGA1700":
                lines.append("Warning: Selected CPU does not look like an Intel LGA1700 CPU.")
            if board_platform != "LGA1700":
                lines.append("Warning: Selected motherboard does not look like an Intel LGA1700 motherboard.")
            if "ddr4" in build_lower and ram_type != "DDR4":
                lines.append("Warning: Selected Intel DDR4 path requires DDR4 RAM.")
            if "ddr5" in build_lower and ram_type != "DDR5":
                lines.append("Warning: Selected Intel DDR5 path requires DDR5 RAM.")

        recommended_watts = self.recommended_psu_watts(gpu)
        selected_watts = self.extract_watts(psu)

        if recommended_watts and selected_watts:
            if selected_watts < recommended_watts:
                lines.append(f"Warning: {gpu} should ideally have at least a {recommended_watts}W PSU.")
            else:
                lines.append(f"PSU wattage looks okay for {gpu}.")

        if "rx 6800" in gpu.lower() or "rx 7800" in gpu.lower() or "rtx 4070" in gpu.lower():
            if "sff" in case.lower() or "mini" in case.lower():
                lines.append("Warning: Selected GPU may not fit compact/SFF cases. Check length and slot width.")
            else:
                lines.append("GPU/case fit still needs physical length and slot-width check.")

        if "aio" in cooling.lower() and "airflow" not in case.lower():
            lines.append("AIO selected: check radiator support before buying.")

        pref = hardware_preference.lower()
        if "linux mint" in pref or "amd" in pref:
            if "nvidia" in gpu.lower() or "rtx" in gpu.lower():
                lines.append("Linux note: Nvidia can work, but AMD GPUs are usually simpler on Linux Mint with Mesa/amdgpu.")
            elif "rx " in gpu.lower() or "radeon" in gpu.lower():
                lines.append("Linux note: AMD GPU choice is Linux Mint friendly.")

        if not lines:
            lines.append("No obvious compatibility issue detected. Still confirm socket, RAM type, PSU wattage, case clearance and BIOS support before buying.")

        return lines

    def listing_notes(self, title: str, build_path: str, hardware_preference: str = "") -> list[str]:
        lower = title.lower()
        notes: list[str] = []

        if "am5" in build_path.lower():
            if self.cpu_platform(title) == "AM4":
                notes.append("Compatibility warning: this CPU appears AM4, but your build path is AM5.")
            if self.motherboard_platform(title) == "AM4":
                notes.append("Compatibility warning: this motherboard appears AM4, but your build path is AM5.")
            if self.ram_type(title) == "DDR4":
                notes.append("Compatibility warning: DDR4 RAM will not work with AM5.")
        elif "am4" in build_path.lower():
            if self.cpu_platform(title) == "AM5":
                notes.append("Compatibility warning: this CPU appears AM5, but your build path is AM4.")
            if self.ram_type(title) == "DDR5":
                notes.append("Compatibility warning: DDR5 RAM will not work with AM4.")

        if "lga1700" in build_path.lower():
            if self.cpu_platform(title) in {"AM4", "AM5"}:
                notes.append("Compatibility warning: Ryzen CPU does not match Intel LGA1700 build path.")
            if "ddr4" in build_path.lower() and self.ram_type(title) == "DDR5":
                notes.append("Compatibility warning: DDR5 RAM does not match your Intel DDR4 path.")
            if "ddr5" in build_path.lower() and self.ram_type(title) == "DDR4":
                notes.append("Compatibility warning: DDR4 RAM does not match your Intel DDR5 path.")

        if ("linux mint" in hardware_preference.lower() or "amd" in hardware_preference.lower()) and ("rtx" in lower or "nvidia" in lower):
            notes.append("Linux note: Nvidia can work, but AMD GPUs are usually smoother on Linux Mint.")

        if not notes:
            notes.append("Compatibility note: no obvious build-path conflict detected.")

        return notes

    def cpu_platform(self, text: str) -> str:
        lower = text.lower()

        if "ryzen 5 7600" in lower or "ryzen 7 7700" in lower or "7800x3d" in lower or "ryzen 9 7900" in lower or "7950x" in lower:
            return "AM5"
        if "ryzen 5 5600" in lower or "ryzen 7 5700" in lower or "5800x" in lower:
            return "AM4"
        if "12600k" in lower or "13600k" in lower or "13700k" in lower or "lga1700" in lower:
            return "LGA1700"

        return "Unknown"

    def motherboard_platform(self, text: str) -> str:
        lower = text.lower()

        if "a620" in lower or "b650" in lower or "x670" in lower:
            return "AM5"
        if "b550" in lower or "x570" in lower:
            return "AM4"
        if "b660" in lower or "b760" in lower or "z690" in lower or "z790" in lower:
            return "LGA1700"

        return "Unknown"

    def ram_type(self, text: str) -> str:
        lower = text.lower()

        if "ddr5" in lower:
            return "DDR5"
        if "ddr4" in lower:
            return "DDR4"

        return "Unknown"

    def recommended_psu_watts(self, gpu: str) -> int:
        lower = gpu.lower()

        if "rtx 4080" in lower or "rx 7900" in lower:
            return 750
        if "rx 7800" in lower or "rx 6800" in lower or "rtx 4070" in lower:
            return 650
        if "rx 6700" in lower or "rtx 3060" in lower:
            return 550

        return 0

    def extract_watts(self, text: str) -> int:
        match = re.search(r"(\d{3,4})\s*w", text.lower())

        if match:
            return int(match.group(1))

        return 0
