from __future__ import annotations

from dealwise.marketplaces.base import MarketplaceConnector
from dealwise.marketplaces.vinted import VintedPublicConnector


class MarketplaceRegistry:
    """Small connector registry used by SearchManager."""

    def __init__(self) -> None:
        self._connectors: dict[str, MarketplaceConnector] = {}
        self.register(VintedPublicConnector())

    def register(self, connector: MarketplaceConnector) -> None:
        self._connectors[connector.name.lower()] = connector

    def get(self, marketplace_name: str) -> MarketplaceConnector | None:
        return self._connectors.get(marketplace_name.lower())

    def names(self) -> list[str]:
        return sorted(connector.name for connector in self._connectors.values())
