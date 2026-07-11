from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from statistics import median

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

    # Full PCs must be detected before CPU/GPU terms, otherwise a gaming PC
    # containing "7800X3D" pollutes the standalone CPU price history.
    full_pc_terms = [
        "gaming pc",
        "desktop pc",
        "complete pc",
        "full pc",
        "custom pc",
        "prebuilt",
        "computer tower",
        "gaming computer",
        "workstation",
        "pc bundle",
        "gaming tower pc",
        "desktop tower",
        "pc specialist",
        "tower pc",
        "gaming tower",
    ]

    if any(term in lower for term in full_pc_terms):
        return "full pc"

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
        (r"7800x3d", "ryzen 7 7800x3d"),
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
    ]

    for pattern, key in patterns:
        if re.search(pattern, lower):
            return key

    cleaned = re.sub(r"[^a-z0-9]+", " ", lower)
    words = [word for word in cleaned.split() if len(word) > 2]
    return " ".join(words[:4]) or "unknown"


class PriceHistoryService:
    """Stores and reads observed listing prices.

    Stats use one latest price per distinct listing, not every repeated refresh.
    That prevents one listing being counted 80+ times.
    """

    def __init__(self, database: DatabaseManager) -> None:
        self.database = database

    def record_listing(self, listing: MarketplaceListing) -> None:
        if listing.price is None:
            return

        captured_at = datetime.now(timezone.utc).isoformat()
        product_key = normalise_product_key(listing.title)

        with self.database.connect() as connection:
            existing = connection.execute(
                """
                SELECT id
                FROM price_snapshots
                WHERE dedupe_key = ?
                  AND price = ?
                  AND captured_at >= datetime('now', '-6 hours')
                LIMIT 1
                """,
                (listing.dedupe_key, listing.price),
            ).fetchone()

            if existing is not None:
                return

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
            rows = connection.execute(
                """
                SELECT
                    dedupe_key,
                    title,
                    price,
                    captured_at
                FROM price_snapshots
                WHERE product_key = ?
                ORDER BY captured_at DESC
                """,
                (product_key,),
            ).fetchall()

        latest_by_listing: dict[str, tuple[float, str]] = {}

        for row in rows:
            dedupe_key = str(row["dedupe_key"])
            price = float(row["price"] or 0)
            captured_at = str(row["captured_at"] or "")

            if price <= 0:
                continue

            if dedupe_key not in latest_by_listing:
                latest_by_listing[dedupe_key] = (price, captured_at)

        prices = [item[0] for item in latest_by_listing.values()]

        if not prices:
            return None

        filtered_prices = self._remove_outliers(prices)

        if not filtered_prices:
            filtered_prices = prices

        last_seen_at = ""
        if latest_by_listing:
            last_seen_at = max(item[1] for item in latest_by_listing.values())

        latest_price = prices[0]

        return PriceHistoryStats(
            product_key=product_key,
            sample_count=len(filtered_prices),
            lowest_price=min(filtered_prices),
            highest_price=max(filtered_prices),
            average_price=sum(filtered_prices) / len(filtered_prices),
            latest_price=latest_price,
            last_seen_at=last_seen_at,
        )

    def _remove_outliers(self, prices: list[float]) -> list[float]:
        if len(prices) < 4:
            return prices

        middle = median(prices)

        if middle <= 0:
            return prices

        low_cutoff = middle * 0.35
        high_cutoff = middle * 2.20

        return [
            price
            for price in prices
            if low_cutoff <= price <= high_cutoff
        ]
