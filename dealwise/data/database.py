from __future__ import annotations

import sqlite3
from pathlib import Path


class DatabaseManager:
    """Initialises and provides SQLite connections for DealWise.

    The database lives outside the Git repository under the user's config
    directory so runtime data is not committed.
    """

    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.initialise()

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialise(self) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS listings (
                    dedupe_key TEXT PRIMARY KEY,
                    marketplace TEXT NOT NULL,
                    listing_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    price REAL,
                    currency TEXT NOT NULL DEFAULT 'GBP',
                    url TEXT NOT NULL,
                    image_url TEXT,
                    seller_name TEXT,
                    condition TEXT,
                    location TEXT,
                    source_query TEXT,
                    search_id TEXT,
                    found_at TEXT NOT NULL,
                    first_seen_at TEXT NOT NULL,
                    last_seen_at TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Found',
                    notes TEXT NOT NULL DEFAULT '',
                    part_type TEXT NOT NULL DEFAULT 'Unknown',
                    raw_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS target_build (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    name TEXT NOT NULL DEFAULT 'Main Target Build',
                    total_budget REAL NOT NULL DEFAULT 0,
                    use_case TEXT NOT NULL DEFAULT '',
                    platform TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS build_parts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    part_type TEXT NOT NULL,
                    target TEXT NOT NULL DEFAULT '',
                    budget REAL NOT NULL DEFAULT 0,
                    bought_price REAL NOT NULL DEFAULT 0,
                    status TEXT NOT NULL DEFAULT 'Needed',
                    priority INTEGER NOT NULL DEFAULT 0,
                    notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS current_pc (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    imported_at TEXT NOT NULL DEFAULT '',
                    raw_inxi TEXT NOT NULL DEFAULT '',
                    system_model TEXT NOT NULL DEFAULT '',
                    cpu TEXT NOT NULL DEFAULT '',
                    gpu TEXT NOT NULL DEFAULT '',
                    memory TEXT NOT NULL DEFAULT '',
                    storage TEXT NOT NULL DEFAULT '',
                    distro TEXT NOT NULL DEFAULT '',
                    kernel TEXT NOT NULL DEFAULT '',
                    form_factor_notes TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS notification_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    title TEXT NOT NULL,
                    body TEXT NOT NULL,
                    related_listing_key TEXT
                );
                """
            )

            connection.execute(
                """
                INSERT OR IGNORE INTO target_build (
                    id,
                    name,
                    total_budget,
                    use_case,
                    platform,
                    notes
                )
                VALUES (
                    1,
                    'Main Target Build',
                    600,
                    '1440p gaming / best performance per pound',
                    'AM5 / ATX target',
                    'Prioritise GPU deal first, then CPU, motherboard and RAM.'
                )
                """
            )

            default_parts = [
                ("GPU", "RX 6800 / RX 7700 XT / RX 7800 XT", 240, 1),
                ("CPU", "Ryzen 5 7600 / Ryzen 7 7700", 150, 2),
                ("Motherboard", "B650", 100, 3),
                ("RAM", "32GB DDR5", 60, 4),
                ("PSU", "650W Gold", 50, 5),
                ("Case", "ATX airflow case", 50, 6),
                ("Storage", "2TB NVMe", 0, 7),
                ("Cooling", "Air cooler / stock initially", 0, 8),
            ]

            for part_type, target, budget, priority in default_parts:
                existing = connection.execute(
                    "SELECT id FROM build_parts WHERE part_type = ?",
                    (part_type,),
                ).fetchone()

                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO build_parts (
                            part_type,
                            target,
                            budget,
                            status,
                            priority,
                            notes
                        )
                        VALUES (?, ?, ?, 'Needed', ?, '')
                        """,
                        (part_type, target, budget, priority),
                    )

            connection.commit()
