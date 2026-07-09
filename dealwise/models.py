from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


DEFAULT_REFRESH_INTERVAL_MINUTES = 5
MIN_REFRESH_INTERVAL_MINUTES = 1


@dataclass(slots=True)
class SavedSearch:
    """A user-configured marketplace search."""

    id: str
    query: str
    marketplace: str = "Vinted"
    min_price: float | None = None
    max_price: float | None = None
    condition: str = "Any"
    excluded_keywords: list[str] = field(default_factory=list)
    refresh_interval_minutes: int = DEFAULT_REFRESH_INTERVAL_MINUTES
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def create(
        cls,
        query: str,
        marketplace: str,
        min_price: float | None,
        max_price: float | None,
        condition: str,
        excluded_keywords: list[str],
        refresh_interval_minutes: int,
    ) -> "SavedSearch":
        return cls(
            id=str(uuid4()),
            query=query.strip(),
            marketplace=marketplace.strip() or "Vinted",
            min_price=min_price,
            max_price=max_price,
            condition=condition.strip() or "Any",
            excluded_keywords=excluded_keywords,
            refresh_interval_minutes=max(
                MIN_REFRESH_INTERVAL_MINUTES,
                refresh_interval_minutes,
            ),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SavedSearch":
        return cls(
            id=str(data.get("id") or uuid4()),
            query=str(data.get("query") or "").strip(),
            marketplace=str(data.get("marketplace") or "Vinted").strip(),
            min_price=_optional_float(data.get("min_price")),
            max_price=_optional_float(data.get("max_price")),
            condition=str(data.get("condition") or "Any").strip(),
            excluded_keywords=_string_list(data.get("excluded_keywords")),
            refresh_interval_minutes=max(
                MIN_REFRESH_INTERVAL_MINUTES,
                int(data.get("refresh_interval_minutes") or DEFAULT_REFRESH_INTERVAL_MINUTES),
            ),
            created_at=str(
                data.get("created_at") or datetime.now(timezone.utc).isoformat()
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "marketplace": self.marketplace,
            "min_price": self.min_price,
            "max_price": self.max_price,
            "condition": self.condition,
            "excluded_keywords": self.excluded_keywords,
            "refresh_interval_minutes": self.refresh_interval_minutes,
            "created_at": self.created_at,
        }

    def price_range_label(self) -> str:
        if self.min_price is None and self.max_price is None:
            return "Any price"

        if self.min_price is not None and self.max_price is not None:
            return f"£{self.min_price:.0f} - £{self.max_price:.0f}"

        if self.min_price is not None:
            return f"From £{self.min_price:.0f}"

        return f"Up to £{self.max_price:.0f}"


@dataclass(slots=True)
class RuntimeStats:
    """Small snapshot used by the dashboard."""

    is_running: bool
    saved_searches: int
    searches_running: int
    listings_analysed: int
    refreshes_completed: int
    running_since: datetime | None
    last_refresh_at: datetime | None


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None

    if parsed <= 0:
        return None

    return parsed


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []

    return [str(item).strip() for item in value if str(item).strip()]
