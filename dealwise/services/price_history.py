from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone

from dealwise.data.database import DatabaseManager
from dealwise.models import MarketplaceListing


@dataclass(slots=True)
class PriceHistoryStats:
    product_key: str
    sample_count: int
    lowest_price: float
    highest_price: float
    average_price: float
    latest_price: float
    last_seen_at: str

    def range_label(self) -> str:
        return f"£{self.lowest_price:.0f} - £{self.highest_price:.0f}"

    def average_label(self) -> str:
        return f"£{self.average_price:.0f}"


def normalise_product_key(title: str) -> str:
    lower = title.lower()

    patterns = [
        (r"rx\s*7900\s*xtx", "rx 7900 xtx"),
        (r"rx\s*7900\s*xt", "rx 7900 xt"),
        (r"rx\s*7800\s*xt", "rx 7800 xt"),
        (r"rx\s*7700\s*xt", "rx 7700 xt"),
        (r"rx\s*6800\s*xt", "rx 6800 xt"),
        (r"rx\s*6800", "rx 6800"),
        (r"rx\s*6700\s*xt", "rx 6700 xt"),
        (r"rx\s*6600", "rx 6600"),
        (r"rtx\s*4080", "rtx 4080"),
        (r"rtx\s*4070\s*ti", "rtx 4070 ti"),
        (r"rtx\s*4070", "rtx 4070"),
        (r"rtx\s*3060\s*ti", "rtx 3060 ti"),
        (r"rtx\s*3060", "rtx 3060"),
        (r"ryzen\s*9\s*7950x", "ryzen 9 7950x"),
        (r"ryzen\s*9\s*7900x", "ryzen 9 7900x"),
        (r"ryzen\s*9\s*7900", "ryzen 9 7900"),
        (r"ryzen\s*7\s*7800x3d", "ryzen 7 7800x3d"),
        (r"ryzen\s*7\s*7700x", "ryzen 7 7700x"),
        (r"ryzen\s*7\s*7700", "ryzen 7 7700"),
        (r"ryzen\s*5\s*7600x", "ryzen 5 7600x"),
        (r"ryzen\s*5\s*7600", "ryzen 5 7600"),
        (r"i7\s*-?\s*13700k", "intel i7 13700k"),
        (r"i5\s*-?\s*13600k", "intel i5 13600k"),
        (r"i5\s*-?\s*12600k", "intel i5 12600k"),
        (r"b650", "b650 motherboard"),
        (r"x670e", "x670e motherboard"),
        (r"x670", "x670 motherboard"),
        (r"b550", "b550 motherboard"),
        (r"32\s*gb.*ddr5|ddr5.*32\s*gb", "32gb ddr5"),
        (r"64\s*gb.*ddr5|ddr5.*64\s*gb", "64gb ddr5"),
        (r"32\s*gb.*ddr4|ddr4.*32\s*gb", "32gb ddr4"),
        (r"2\s*tb.*nvme|nvme.*2\s*tb", "2tb nvme"),
        (r"1\s*tb.*nvme|nvme.*1\s*tb", "1tb nvme"),
        (r"650\s*w.*gold|650w.*gold", "650w gold psu"),
        (r"750\s*w.*gold|750w.*gold", "750w gold psu"),
        (r"gaming\s*pc|desktop\s*pc|complete\s*pc|full\s*pc|prebuilt", "full pc"),
    ]

    for pattern, key in patterns:
        if re.search(pattern, lower):
            return key

    cleaned = re.sub(r"[^a-z0-9]+", " ", lower)
    words = [word for word in cleaned.split() if len(word) > 2]
    return " ".join(words[:4]) or "unknown"


class PriceHistoryService:
    """Stores and reads observed listing prices.

    Phase 6 starts with prices DealWise has actually seen during searches.
    Later this can be expanded with completed listings and external history.
    """

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def record_listing(self, listing: MarketplaceListing) -> None:
        if listing.price is None:
            return

        captured_at = datetime.now(timezone.utc).isoformat()
        product_key = normalise_product_key(listing.title)

        with self.database.connect() as connection:
            connection.execute(
                """
                INSERT INTO price_snapshots (
                    dedupe_key,
                    product_key,
                    marketplace,
                    listing_id,
                    title,
                    price,
                    currency,
                    url,
                    captured_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    listing.dedupe_key,
                    product_key,
                    listing.marketplace,
                    listing.id,
                    listing.title,
                    listing.price,
                    listing.currency,
                    listing.url,
                    captured_at,
                ),
            )
            connection.commit()

    def stats_for_title(self, title: str) -> PriceHistoryStats | None:
        return self.stats_for_product_key(normalise_product_key(title))

    def stats_for_product_key(self, product_key: str) -> PriceHistoryStats | None:
        with self.database.connect() as connection:
            row = connection.execute(
                """
                SELECT
                    product_key,
                    COUNT(*) AS sample_count,
                    MIN(price) AS lowest_price,
                    MAX(price) AS highest_price,
                    AVG(price) AS average_price,
                    (
                        SELECT price
                        FROM price_snapshots latest
                        WHERE latest.product_key = price_snapshots.product_key
                        ORDER BY latest.captured_at DESC
                        LIMIT 1
                    ) AS latest_price,
                    MAX(captured_at) AS last_seen_at
                FROM price_snapshots
                WHERE product_key = ?
                GROUP BY product_key
                """,
                (product_key,),
            ).fetchone()

        if row is None:
            return None

        return PriceHistoryStats(
            product_key=str(row["product_key"]),
            sample_count=int(row["sample_count"] or 0),
            lowest_price=float(row["lowest_price"] or 0),
            highest_price=float(row["highest_price"] or 0),
            average_price=float(row["average_price"] or 0),
            latest_price=float(row["latest_price"] or 0),
            last_seen_at=str(row["last_seen_at"] or ""),
        )
