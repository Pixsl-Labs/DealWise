from __future__ import annotations

import re
from dataclasses import dataclass


DEAL_CANDIDATE_BUCKETS = {"Exact Product", "Compatible Alternative"}


@dataclass(slots=True)
class ProductClassification:
    category: str
    bucket: str
    identity_confidence: int
    matched_model: str
    extracted_spec: str
    rejection_reason: str
    deal_score_cap: int | None
    evidence_score: int
    scam_risk: float
    why: list[str]

    @property
    def is_deal_candidate(self) -> bool:
        return self.bucket in DEAL_CANDIDATE_BUCKETS and self.identity_confidence >= 60


class ProductClassifier:
    """Two-stage classifier for Active Hunt listings.

    Stage 1 validates product identity before any deal scoring is allowed.
    Stage 2 exposes confidence/caps so unrelated products cannot receive high scores.
    """

    GPU_MODELS = {
        "rx 7700 xt": ["rx 7700 xt", "rx7700xt", "radeon 7700 xt"],
        "rx 7800 xt": ["rx 7800 xt", "rx7800xt", "radeon 7800 xt"],
        "rx 7900 gre": ["rx 7900 gre", "rx7900gre", "radeon 7900 gre"],
        "rx 7900 xt": ["rx 7900 xt", "rx7900xt", "radeon 7900 xt"],
        "rx 9070": ["rx 9070", "rx9070", "radeon 9070"],
        "rx 9070 xt": ["rx 9070 xt", "rx9070xt", "radeon 9070 xt"],
        "rx 9060 xt": ["rx 9060 xt", "rx9060xt", "radeon 9060 xt"],
        "rx 6800 xt": ["rx 6800 xt", "rx6800xt", "radeon 6800 xt"],
        "rx 6900 xt": ["rx 6900 xt", "rx6900xt", "radeon 6900 xt"],
        "rtx 5060 ti": ["rtx 5060 ti", "rtx5060ti"],
        "rtx 4070 super": ["rtx 4070 super", "rtx4070super"],
    }

    GPU_ACCESSORY_TERMS = [
        "fan assembly",
        "fan replacement",
        "replacement fan",
        "cooler only",
        "heatsink only",
        "shroud",
        "backplate",
        "bracket",
        "water block",
        "waterblock",
        "cable",
        "adapter",
        "screw set",
        "thermal pad",
        "paste",
    ]

    GPU_REJECT_TERMS = [
        "empty box",
        "box only",
        "no gpu",
        "parts only",
        "faulty",
        "no display",
        "repair",
        "spares",
        "laptop",
        "gaming pc",
        "full pc",
        "desktop pc",
        "mining rig",
        "wanted",
        "swap",
        "manual",
    ]

    WRONG_OLD_GPU_PATTERNS = [
        r"\br9\s*290\b",
        r"\br9\s*390\b",
        r"\brx\s*570\b",
        r"\brx\s*580\b",
        r"\brx\s*590\b",
        r"\brx\s*5500\b",
        r"\brx\s*5600\b",
        r"\brx\s*5700\b",
        r"\brx\s*5700\s*xt\b",
    ]

    RAM_REJECT_TERMS = [
        "ddr4",
        "ddr3",
        "sodimm",
        "so-dimm",
        "laptop",
        "notebook",
        "rdimm",
        "registered",
        "server ram",
        "server memory",
        "ecc",
        "1x16gb",
        "1 x 16gb",
        "1x8gb",
        "1 x 8gb",
        "2x8gb",
        "2 x 8gb",
        "4x8gb",
        "4 x 8gb",
        "mismatched",
        "empty box",
        "box only",
        "heatspreader only",
    ]

    SSD_REJECT_TERMS = [
        "external",
        "portable",
        "enclosure",
        "caddy",
        "sata",
        "m.2 sata",
        "2.5",
        "hdd",
        "hard drive",
        "heatsink only",
        "laptop",
        "gaming pc",
        "full pc",
        "desktop pc",
        "128gb",
        "256gb",
        "512gb",
        "1tb",
        "faulty",
        "parts only",
        "locked",
        "22110",
    ]

    def classify(
        self,
        title: str,
        source_query: str = "",
        category_hint: str = "",
        description: str = "",
    ) -> ProductClassification:
        category = category_hint or self._guess_category(f"{title} {source_query}")
        text = self._normalise(f"{title} {source_query} {description}")

        if category == "GPU":
            return self._classify_gpu(text)

        if category in {"RAM", "Memory"}:
            return self._classify_ram(text)

        if category in {"Storage", "SSD"}:
            return self._classify_ssd(text)

        if self._contains_any(text, ["gaming pc", "full pc", "desktop pc", "complete pc"]):
            return self._reject(category or "Unknown", "Complete PC", "Complete PC", text)

        return ProductClassification(
            category=category or "Unknown",
            bucket="Needs Classification",
            identity_confidence=35,
            matched_model="",
            extracted_spec="",
            rejection_reason="Unknown or unsupported product category.",
            deal_score_cap=40,
            evidence_score=20,
            scam_risk=5.0,
            why=["Could not confidently classify this listing."],
        )

    def _classify_gpu(self, text: str) -> ProductClassification:
        if self._contains_any(text, self.GPU_ACCESSORY_TERMS):
            return self._reject("GPU", "Replacement Part", "Replacement GPU component/accessory.", text)

        if self._contains_any(text, self.GPU_REJECT_TERMS):
            return self._reject("GPU", "Faulty / Parts Only", "GPU listing contains rejection wording.", text)

        for pattern in self.WRONG_OLD_GPU_PATTERNS:
            if re.search(pattern, text):
                return self._reject("GPU", "Wrong GPU Model", "Old/wrong GPU model does not match the active hunt.", text)

        matched_model = ""

        for model, tokens in self.GPU_MODELS.items():
            if self._contains_any(text, tokens):
                matched_model = model.upper()
                break

        if not matched_model:
            return ProductClassification(
                category="GPU",
                bucket="Needs Classification",
                identity_confidence=35,
                matched_model="",
                extracted_spec="No exact active GPU model token found.",
                rejection_reason="GPU identity below threshold.",
                deal_score_cap=40,
                evidence_score=25,
                scam_risk=4.5,
                why=[
                    "A valid Active Hunt GPU must contain an exact model token.",
                    "Generic terms like AMD, Radeon, Sapphire, XFX, QICK or GPU are not enough.",
                ],
            )

        evidence = 55
        why = [f"Matched exact/allowed GPU model: {matched_model}."]

        if self._contains_any(text, ["12gb", "16gb", "vram"]):
            evidence += 12
            why.append("VRAM/capacity evidence found.")

        if self._contains_any(text, ["sapphire", "powercolor", "xfx", "asus", "gigabyte", "msi", "asrock"]):
            evidence += 8
            why.append("Known GPU board partner detected.")

        if self._contains_any(text, ["gpu-z", "gpuz", "benchmark", "tested", "working", "furmark", "3dmark"]):
            evidence += 10
            why.append("Operation/proof wording detected.")

        return ProductClassification(
            category="GPU",
            bucket="Exact Product",
            identity_confidence=90,
            matched_model=matched_model,
            extracted_spec=matched_model,
            rejection_reason="",
            deal_score_cap=None,
            evidence_score=min(100, evidence),
            scam_risk=2.5,
            why=why,
        )

    def _classify_ram(self, text: str) -> ProductClassification:
        if self._contains_any(text, self.RAM_REJECT_TERMS):
            return self._reject("RAM", "Wrong Specification", "RAM listing fails DDR5 desktop 2x16GB target rules.", text)

        if "ddr5" not in text:
            return self._needs("RAM", "Missing DDR5 evidence.", text)

        has_32gb = "32gb" in text or "32 gb" in text
        has_2x16 = self._contains_any(text, ["2x16", "2 x 16", "2x16gb", "2 x 16gb"])

        if not has_32gb and not has_2x16:
            return self._needs("RAM", "Missing 32GB / 2x16GB evidence.", text)

        if self._contains_any(text, ["1x32", "1 x 32"]):
            return self._reject("RAM", "Wrong Specification", "1x32GB is not the preferred complete 2x16GB kit.", text)

        speed = self._extract_first_int(text, [r"\b(5600|6000|6200|6400|6600|6800|7000|7200)\b"])
        cl = self._extract_first_int(text, [r"\bcl\s*(28|30|32|36|40)\b", r"\bc(28|30|32|36|40)\b"])

        confidence = 72
        evidence = 50
        why = ["DDR5 32GB-class RAM detected."]

        if has_2x16:
            confidence += 15
            evidence += 15
            why.append("Matched 2x16GB kit signal.")

        if speed:
            evidence += 10
            why.append(f"Speed detected: {speed}MT/s.")

        if cl:
            evidence += 8
            why.append(f"CAS latency detected: CL{cl}.")

        if "expo" in text:
            evidence += 10
            why.append("AMD EXPO detected.")
        elif "xmp" in text:
            evidence += 5
            why.append("XMP detected.")

        spec = "32GB DDR5"
        if has_2x16:
            spec += " 2x16GB"
        if speed:
            spec += f" {speed}"
        if cl:
            spec += f" CL{cl}"
        if "expo" in text:
            spec += " EXPO"

        bucket = "Exact Product" if has_2x16 and speed else "Compatible Alternative"

        return ProductClassification(
            category="RAM",
            bucket=bucket,
            identity_confidence=min(100, confidence),
            matched_model=spec,
            extracted_spec=spec,
            rejection_reason="",
            deal_score_cap=None,
            evidence_score=min(100, evidence),
            scam_risk=2.0,
            why=why,
        )

    def _classify_ssd(self, text: str) -> ProductClassification:
        if self._contains_any(text, self.SSD_REJECT_TERMS):
            return self._reject("Storage", "Wrong Specification", "SSD listing fails 2TB internal NVMe rules.", text)

        if "2tb" not in text and "2 tb" not in text:
            return self._needs("Storage", "Missing 2TB evidence.", text)

        if "nvme" not in text and "m.2" not in text:
            return self._needs("Storage", "Missing NVMe/M.2 evidence.", text)

        model = self._ssd_model(text)
        evidence = 55
        why = ["2TB internal NVMe/M.2 storage detected."]

        if model:
            evidence += 15
            why.append(f"Recognised SSD model detected: {model}.")

        if self._contains_any(text, ["gen4", "pcie 4", "pci-e 4", "7000mb", "7300mb", "7450mb"]):
            evidence += 10
            why.append("PCIe Gen4 / high-speed wording detected.")

        if self._contains_any(text, ["smart", "health", "tbw", "host writes", "power on hours"]):
            evidence += 15
            why.append("Used-drive health evidence detected.")

        spec = model or "2TB M.2 NVMe SSD"

        return ProductClassification(
            category="Storage",
            bucket="Exact Product" if model else "Compatible Alternative",
            identity_confidence=88 if model else 74,
            matched_model=spec,
            extracted_spec=spec,
            rejection_reason="",
            deal_score_cap=None,
            evidence_score=min(100, evidence),
            scam_risk=2.5,
            why=why,
        )

    def _reject(self, category: str, bucket: str, reason: str, text: str) -> ProductClassification:
        return ProductClassification(
            category=category,
            bucket=bucket,
            identity_confidence=0,
            matched_model="",
            extracted_spec="",
            rejection_reason=reason,
            deal_score_cap=0,
            evidence_score=0,
            scam_risk=8.5,
            why=[reason],
        )

    def _needs(self, category: str, reason: str, text: str) -> ProductClassification:
        return ProductClassification(
            category=category,
            bucket="Needs Classification",
            identity_confidence=45,
            matched_model="",
            extracted_spec="",
            rejection_reason=reason,
            deal_score_cap=40,
            evidence_score=25,
            scam_risk=4.5,
            why=[reason],
        )

    def _guess_category(self, text: str) -> str:
        lower = self._normalise(text)

        if self._contains_any(lower, ["rx 7700", "rx 7800", "rx 7900", "rx 9070", "rtx 4070", "graphics card", "gpu"]):
            return "GPU"

        if self._contains_any(lower, ["ddr5", "ddr4", "ram", "memory", "2x16"]):
            return "RAM"

        if self._contains_any(lower, ["nvme", "m.2", "ssd", "sn850x", "990 pro", "kc3000", "nm790"]):
            return "Storage"

        return "Unknown"

    def _ssd_model(self, text: str) -> str:
        models = {
            "WD Black SN850X": ["sn850x"],
            "Samsung 990 Pro": ["990 pro", "990pro"],
            "Kingston KC3000": ["kc3000"],
            "Crucial T500": ["t500"],
            "Lexar NM790": ["nm790"],
            "Acer Predator GM7000": ["gm7000"],
            "Corsair MP600": ["mp600"],
            "Solidigm P44 Pro": ["p44 pro", "p44pro"],
            "TeamGroup MP44": ["mp44"],
            "Seagate FireCuda 530": ["firecuda 530"],
        }

        for model, tokens in models.items():
            if self._contains_any(text, tokens):
                return model

        return ""

    def _extract_first_int(self, text: str, patterns: list[str]) -> int | None:
        for pattern in patterns:
            match = re.search(pattern, text)

            if match:
                try:
                    return int(match.group(1))
                except ValueError:
                    return None

        return None

    def _normalise(self, text: str) -> str:
        text = text.lower()
        text = text.replace("-", " ")
        text = re.sub(r"\s+", " ", text)
        return f" {text.strip()} "

    def _contains_any(self, text: str, terms: list[str]) -> bool:
        return any(term in text for term in terms)
