from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from dealwise.models import SavedSearch


class ConfigManager:
    """Manages DealWise local configuration and storage files.

    Sensitive credentials must never be stored here. Future credential support
    should use Linux Secret Service / Keyring or Windows Credential Manager.
    """

    def __init__(self) -> None:
        self.app_dir = Path.home() / ".config" / "Pixsl-Labs" / "DealWise"
        self.cache_dir = self.app_dir / "cache"
        self.images_dir = self.app_dir / "images"
        self.logs_dir = self.app_dir / "logs"
        self.database_dir = self.app_dir / "database"

        self.config_file = self.app_dir / "config.json"
        self.searches_file = self.app_dir / "searches.json"
        self.database_file = self.database_dir / "dealwise.db"

        self.ensure_directories()
        self.ensure_default_files()

    def ensure_directories(self) -> None:
        self.app_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.database_dir.mkdir(parents=True, exist_ok=True)

    def ensure_default_files(self) -> None:
        if not self.config_file.exists():
            self.write_json(
                self.config_file,
                {
                    "theme": "dark",
                    "default_refresh_interval_minutes": 5,
                    "notifications_enabled": True,
                    "start_minimised": False,
                    "marketplaces_enabled": ["Vinted"],
                    "live_hide_high_scam_risk": True,
                },
            )

        if not self.searches_file.exists():
            self.write_json(self.searches_file, {"saved_searches": []})

    def read_json(self, path: Path, fallback: dict[str, Any]) -> dict[str, Any]:
        try:
            with path.open("r", encoding="utf-8") as file:
                data = json.load(file)

            if isinstance(data, dict):
                return data

            return fallback
        except FileNotFoundError:
            return fallback
        except json.JSONDecodeError:
            broken_file = path.with_suffix(path.suffix + ".broken")
            path.rename(broken_file)
            self.write_json(path, fallback)
            return fallback

    def write_json(self, path: Path, data: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, indent=2, sort_keys=True)

    def load_config(self) -> dict[str, Any]:
        return self.read_json(self.config_file, fallback={})

    def save_config(self, config: dict[str, Any]) -> None:
        self.write_json(self.config_file, config)

    def load_saved_searches(self) -> list[SavedSearch]:
        data = self.read_json(self.searches_file, fallback={"saved_searches": []})
        raw_searches = data.get("saved_searches", [])

        if not isinstance(raw_searches, list):
            return []

        searches: list[SavedSearch] = []

        for raw_search in raw_searches:
            if not isinstance(raw_search, dict):
                continue

            if raw_search.get("paused_by_dealwise"):
                continue

            searches.append(SavedSearch.from_dict(raw_search))

        return searches

    def save_saved_searches(self, searches: list[SavedSearch]) -> None:
        self.write_json(
            self.searches_file,
            {"saved_searches": [search.to_dict() for search in searches]},
        )

    def add_saved_search(self, search: SavedSearch) -> None:
        searches = self.load_saved_searches()
        searches.append(search)
        self.save_saved_searches(searches)

    def delete_saved_search(self, search_id: str) -> None:
        searches = [
            search
            for search in self.load_saved_searches()
            if search.id != search_id
        ]

        self.save_saved_searches(searches)
