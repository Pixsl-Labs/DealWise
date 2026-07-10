from __future__ import annotations

import sqlite3
from pathlib import Path


class DatabaseManager:
    """Initialises and migrates SQLite storage for DealWise."""

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

            self._ensure_column(connection, "listings", "image_url", "TEXT")
            self._ensure_column(connection, "listings", "seller_name", "TEXT")
            self._ensure_column(connection, "listings", "condition", "TEXT")
            self._ensure_column(connection, "listings", "location", "TEXT")
            self._ensure_column(connection, "listings", "source_query", "TEXT")
            self._ensure_column(connection, "listings", "search_id", "TEXT")
            self._ensure_column(connection, "listings", "found_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "listings", "first_seen_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "listings", "last_seen_at", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "listings", "status", "TEXT NOT NULL DEFAULT 'Found'")
            self._ensure_column(connection, "listings", "notes", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "listings", "part_type", "TEXT NOT NULL DEFAULT 'Unknown'")
            self._ensure_column(connection, "listings", "raw_json", "TEXT NOT NULL DEFAULT '{}'")

            self._ensure_column(connection, "target_build", "name", "TEXT NOT NULL DEFAULT 'Main Target Build'")
            self._ensure_column(connection, "target_build", "total_budget", "REAL NOT NULL DEFAULT 600")
            self._ensure_column(connection, "target_build", "use_case", "TEXT NOT NULL DEFAULT '1440p gaming / best performance per pound'")
            self._ensure_column(connection, "target_build", "platform", "TEXT NOT NULL DEFAULT 'AM5 / ATX target'")
            self._ensure_column(connection, "target_build", "notes", "TEXT NOT NULL DEFAULT 'Prioritise GPU deal first, then CPU, motherboard and RAM.'")

            self._ensure_column(connection, "build_parts", "target", "TEXT NOT NULL DEFAULT ''")
            self._ensure_column(connection, "build_parts", "budget", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "bought_price", "REAL NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "status", "TEXT NOT NULL DEFAULT 'Needed'")
            self._ensure_column(connection, "build_parts", "priority", "INTEGER NOT NULL DEFAULT 0")
            self._ensure_column(connection, "build_parts", "notes", "TEXT NOT NULL DEFAULT ''")

            self._ensure_default_target_build(connection)
            self._ensure_default_build_parts(connection)
            self._repair_zero_budgets(connection)

            connection.commit()

    def _ensure_column(
        self,
        connection: sqlite3.Connection,
        table: str,
        column: str,
        definition: str,
    ) -> None:
        rows = connection.execute(f"PRAGMA table_info({table})").fetchall()
        existing = {str(row["name"]) for row in rows}

        if column not in existing:
            connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    def _ensure_default_target_build(self, connection: sqlite3.Connection) -> None:
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

    def _ensure_default_build_parts(self, connection: sqlite3.Connection) -> None:
        default_parts = [
            ("GPU", "RX 6800", 310, 1),
            ("CPU", "Ryzen 7 7700", 200, 2),
            ("Motherboard", "B650", 170, 3),
            ("RAM", "32GB DDR5", 110, 4),
            ("PSU", "650W Gold", 90, 5),
            ("Case", "ATX airflow case", 100, 6),
            ("Storage", "2TB NVMe", 115, 7),
            ("Cooling", "Thermalright air cooler", 45, 8),
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

    def _repair_zero_budgets(self, connection: sqlite3.Connection) -> None:
        defaults = {
            "GPU": 310,
            "CPU": 200,
            "Motherboard": 170,
            "RAM": 110,
            "PSU": 90,
            "Case": 100,
            "Storage": 115,
            "Cooling": 45,
        }

        for part_type, budget in defaults.items():
            connection.execute(
                """
                UPDATE build_parts
                SET budget = ?
                WHERE part_type = ? AND budget <= 0
                """,
                (budget, part_type),
            )
