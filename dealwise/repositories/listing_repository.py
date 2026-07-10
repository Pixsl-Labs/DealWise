from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable

from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing


@dataclass(slots=True)
class StoredListing:
    dedupe_key: str
    marketplace: str
    listing_id: str
    title: str
    price: float | None
    currency: str
    url: str
    image_url: str | None
    seller_name: str | None
    condition: str | None
    location: str | None
    source_query: str | None
    search_id: str | None
    found_at: str
    first_seen_at: str
    last_seen_at: str
    status: str
    notes: str
    part_type: str
    raw_json: str

    def price_label(self) -> str:
        if self.price is None:
            return "Price unknown"

        symbol = "£" if self.currency.upper() == "GBP" else f"{self.currency} "
        return f"{symbol}{self.price:.2f}"


class ListingRepository:
    """Persists marketplace listings and saved listing workflow state."""

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def upsert_marketplace_listings(
        self,
        listings: Iterable[MarketplaceListing],
    ) -> tuple[int, int]:
        now = datetime.now(timezone.utc).isoformat()
        inserted = 0
        updated = 0

        with self.database.connect() as connection:
            for listing in listings:
                existing = connection.execute(
                    "SELECT dedupe_key FROM listings WHERE dedupe_key = ?",
                    (listing.dedupe_key,),
                ).fetchone()

                if existing is None:
                    connection.execute(
                        """
                        INSERT INTO listings (
                            dedupe_key,
                            marketplace,
                            listing_id,
                            title,
                            price,
                            currency,
                            url,
                            image_url,
                            seller_name,
                            condition,
                            location,
                            source_query,
                            search_id,
                            found_at,
                            first_seen_at,
                            last_seen_at,
                            status,
                            notes,
                            part_type,
                            raw_json
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Found', '', ?, ?)
                        """,
                        (
                            listing.dedupe_key,
                            listing.marketplace,
                            listing.id,
                            listing.title,
                            listing.price,
                            listing.currency,
                            listing.url,
                            listing.image_url,
                            listing.seller_name,
                            listing.condition,
                            listing.location,
                            listing.source_query,
                            listing.search_id,
                            listing.found_at,
                            now,
                            now,
                            infer_part_type(listing.title),
                            json.dumps(listing.raw, sort_keys=True),
                        ),
                    )
                    inserted += 1
                else:
                    connection.execute(
                        """
                        UPDATE listings
                        SET
                            title = ?,
                            price = ?,
                            currency = ?,
                            url = ?,
                            image_url = ?,
                            seller_name = ?,
                            condition = ?,
                            location = ?,
                            source_query = ?,
                            search_id = ?,
                            found_at = ?,
                            last_seen_at = ?
                        WHERE dedupe_key = ?
                        """,
                        (
                            listing.title,
                            listing.price,
                            listing.currency,
                            listing.url,
                            listing.image_url,
                            listing.seller_name,
                            listing.condition,
                            listing.location,
                            listing.source_query,
                            listing.search_id,
                            listing.found_at,
                            now,
                            listing.dedupe_key,
                        ),
                    )
                    updated += 1

            connection.commit()

        return inserted, updated

    def add_manual_listing(
        self,
        title: str,
        url: str,
        price: float | None,
        marketplace: str,
        part_type: str,
        notes: str,
    ) -> StoredListing:
        now = datetime.now(timezone.utc).isoformat()
        safe_marketplace = marketplace.strip() or "Manual"
        safe_title = title.strip() or "Untitled listing"
        safe_url = url.strip()
        dedupe_key = f"{safe_marketplace.lower()}:{safe_url or safe_title.lower()}"

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT OR REPLACE INTO listings (
                    dedupe_key,
                    marketplace,
                    listing_id,
                    title,
                    price,
                    currency,
                    url,
                    image_url,
                    seller_name,
                    condition,
                    location,
                    source_query,
                    search_id,
                    found_at,
                    first_seen_at,
                    last_seen_at,
                    status,
                    notes,
                    part_type,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?, 'GBP', ?, NULL, NULL, NULL, NULL, 'manual', NULL, ?, ?, ?, 'Watching', ?, ?, '{}')
                """,
                (
                    dedupe_key,
                    safe_marketplace,
                    dedupe_key,
                    safe_title,
                    price,
                    safe_url,
                    now,
                    now,
                    now,
                    notes,
                    part_type or infer_part_type(safe_title),
                ),
            )
            connection.commit()

        return self.get_listing(dedupe_key)

    def get_listing(self, dedupe_key: str) -> StoredListing:
        with self.database.connect() as connection:
            row = connection.execute(
                "SELECT * FROM listings WHERE dedupe_key = ?",
                (dedupe_key,),
            ).fetchone()

        if row is None:
            raise KeyError(f"Listing not found: {dedupe_key}")

        return StoredListing(**dict(row))

    def list_recent(self, limit: int = 100) -> list[StoredListing]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM listings
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [StoredListing(**dict(row)) for row in rows]

    def list_saved(self, limit: int = 100) -> list[StoredListing]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM listings
                WHERE status != 'Found'
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [StoredListing(**dict(row)) for row in rows]

    def list_favourites(self, limit: int = 25) -> list[StoredListing]:
        with self.database.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM listings
                WHERE status IN ('Watching', 'Favourite', 'Bought', 'Negotiating')
                ORDER BY last_seen_at DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()

        return [StoredListing(**dict(row)) for row in rows]

    def update_status(self, dedupe_key: str, status: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE listings SET status = ? WHERE dedupe_key = ?",
                (status, dedupe_key),
            )
            connection.commit()

    def update_notes(self, dedupe_key: str, notes: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "UPDATE listings SET notes = ? WHERE dedupe_key = ?",
                (notes, dedupe_key),
            )
            connection.commit()

    def delete_listing(self, dedupe_key: str) -> None:
        with self.database.connect() as connection:
            connection.execute(
                "DELETE FROM listings WHERE dedupe_key = ?",
                (dedupe_key,),
            )
            connection.commit()

    def count_all(self) -> int:
        with self.database.connect() as connection:
            row = connection.execute("SELECT COUNT(*) AS count FROM listings").fetchone()

        return int(row["count"] if row is not None else 0)


def infer_part_type(title: str) -> str:
    lower = title.lower()

    gpu_terms = ["rtx", "gtx", "rx ", "radeon", "geforce", "graphics card", "gpu"]
    cpu_terms = ["ryzen", "intel core", "i3-", "i5-", "i7-", "i9-", "cpu", "processor"]
    motherboard_terms = ["b650", "x670", "b550", "x570", "z690", "z790", "motherboard"]
    ram_terms = ["ddr4", "ddr5", "ram", "memory"]
    storage_terms = ["nvme", "ssd", "hard drive", "hdd", "sn850", "990 pro", "nm790"]
    psu_terms = ["psu", "power supply", "650w", "750w", "850w"]
    case_terms = ["case", "tower", "fractal", "nzxt", "corsair 4000d"]
    cooling_terms = ["cooler", "aio", "fan", "heatsink"]

    if any(term in lower for term in gpu_terms):
        return "GPU"
    if any(term in lower for term in cpu_terms):
        return "CPU"
    if any(term in lower for term in motherboard_terms):
        return "Motherboard"
    if any(term in lower for term in ram_terms):
        return "RAM"
    if any(term in lower for term in storage_terms):
        return "Storage"
    if any(term in lower for term in psu_terms):
        return "PSU"
    if any(term in lower for term in case_terms):
        return "Case"
    if any(term in lower for term in cooling_terms):
        return "Cooling"

    return "Unknown"
