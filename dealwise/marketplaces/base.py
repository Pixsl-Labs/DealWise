from __future__ import annotations

from abc import ABC, abstractmethod

from dealwise.models import MarketplaceSearchResult, SavedSearch


class MarketplaceConnector(ABC):
    """Base interface for marketplace connectors.

    Connectors should only return normalised data. They should not update GTK
    widgets, write directly to app state, or store credentials.
    """

    name: str

    @abstractmethod
    def search(self, saved_search: SavedSearch, limit: int = 20) -> MarketplaceSearchResult:
        """Run a marketplace search and return normalised listing data."""
        raise NotImplementedError
