from __future__ import annotations

import time
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from dealwise.marketplaces.registry import MarketplaceRegistry
from dealwise.models import MarketplaceListing, SavedSearch


@dataclass(slots=True)
class SourceCapabilities:
    supports_search: bool
    supports_price: bool
    supports_postage: bool
    supports_location: bool
    supports_seller: bool
    supports_seller_reputation: bool
    supports_time_posted: bool
    supports_images: bool
    supports_description: bool
    supports_condition: bool
    supports_delivery: bool
    assisted_only: bool = False


@dataclass(slots=True)
class SourceSearchRequest:
    source_name: str
    query: str
    max_pages: int = 2
    max_raw_listings: int = 100
    max_detail_fetches: int = 30
    timeout_seconds: int = 15


@dataclass(slots=True)
class SourceSearchResult:
    source_name: str
    query: str
    listings: list[MarketplaceListing]
    status: str
    raw_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    duplicate_count: int = 0
    elapsed_ms: int = 0
    assisted_url: str = ""
    error: str = ""


class SourceAdapter:
    source_name = "Unknown"
    capabilities = SourceCapabilities(
        supports_search=False,
        supports_price=False,
        supports_postage=False,
        supports_location=False,
        supports_seller=False,
        supports_seller_reputation=False,
        supports_time_posted=False,
        supports_images=False,
        supports_description=False,
        supports_condition=False,
        supports_delivery=False,
    )

    def build_search_url(self, query: str) -> str:
        return ""

    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        return SourceSearchResult(
            source_name=self.source_name,
            query=request.query,
            listings=[],
            status="Unavailable",
            error="Source adapter does not support automatic searching.",
        )


class VintedSourceAdapter(SourceAdapter):
    source_name = "Vinted"

    capabilities = SourceCapabilities(
        supports_search=True,
        supports_price=True,
        supports_postage=False,
        supports_location=True,
        supports_seller=True,
        supports_seller_reputation=False,
        supports_time_posted=False,
        supports_images=True,
        supports_description=False,
        supports_condition=True,
        supports_delivery=False,
    )

    def __init__(self, registry: MarketplaceRegistry | None = None) -> None:
        self.registry = registry or MarketplaceRegistry()

    def build_search_url(self, query: str) -> str:
        return f"https://www.vinted.co.uk/catalog?search_text={quote_plus(query)}"

    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        started = time.perf_counter()
        connector = self.registry.get("Vinted")

        if connector is None:
            return SourceSearchResult(
                source_name=self.source_name,
                query=request.query,
                listings=[],
                status="Parser failed",
                error="Vinted connector missing.",
            )

        saved_search = SavedSearch.create(
            query=request.query,
            marketplace="Vinted",
            min_price=None,
            max_price=None,
            condition="Any",
            excluded_keywords=[],
            refresh_interval_minutes=5,
        )

        result = connector.search(saved_search, limit=min(96, request.max_raw_listings))
        elapsed_ms = int((time.perf_counter() - started) * 1000)

        return SourceSearchResult(
            source_name=self.source_name,
            query=request.query,
            listings=result.listings,
            status="Completed" if result.error is None else "Failed",
            raw_count=len(result.listings),
            accepted_count=len(result.listings),
            elapsed_ms=elapsed_ms,
            error=result.error or "",
        )


class AssistedSearchAdapter(SourceAdapter):
    def __init__(self, source_name: str, url_template: str, status: str = "Assisted only") -> None:
        self.source_name = source_name
        self.url_template = url_template
        self.status = status
        self.capabilities = SourceCapabilities(
            supports_search=False,
            supports_price=False,
            supports_postage=False,
            supports_location=False,
            supports_seller=False,
            supports_seller_reputation=False,
            supports_time_posted=False,
            supports_images=False,
            supports_description=False,
            supports_condition=False,
            supports_delivery=False,
            assisted_only=True,
        )

    def build_search_url(self, query: str) -> str:
        return self.url_template.format(query=quote_plus(query))

    def search(self, request: SourceSearchRequest) -> SourceSearchResult:
        return SourceSearchResult(
            source_name=self.source_name,
            query=request.query,
            listings=[],
            status=self.status,
            assisted_url=self.build_search_url(request.query),
            error="Automatic source searching is not implemented for this source yet.",
        )


class SourceAdapterRegistry:
    """Registry for Active Hunt source adapters.

    Only Vinted is automatic in this patch. Other sources are represented as
    explicit assisted/unavailable adapters so DealWise never pretends they were
    searched successfully.
    """

    def __init__(self) -> None:
        self._sources: dict[str, SourceAdapter] = {}
        self.register(VintedSourceAdapter())
        self.register(AssistedSearchAdapter("eBay UK", "https://www.ebay.co.uk/sch/i.html?_nkw={query}", "Assisted available"))
        self.register(AssistedSearchAdapter("Gumtree UK", "https://www.gumtree.com/search?search_category=all&q={query}", "Assisted available"))
        self.register(AssistedSearchAdapter("CeX", "https://uk.webuy.com/search?stext={query}", "Assisted available"))
        self.register(AssistedSearchAdapter("Facebook Marketplace", "https://www.facebook.com/marketplace/search/?query={query}", "Facebook Assisted Search"))
        self.register(AssistedSearchAdapter("Amazon UK", "https://www.amazon.co.uk/s?k={query}", "Retail assisted/reference"))
        self.register(AssistedSearchAdapter("Scan", "https://www.scan.co.uk/search?q={query}", "Retail assisted/reference"))
        self.register(AssistedSearchAdapter("Overclockers UK", "https://www.overclockers.co.uk/search?sSearch={query}", "Retail assisted/reference"))
        self.register(AssistedSearchAdapter("Ebuyer", "https://www.ebuyer.com/search?q={query}", "Retail assisted/reference"))
        self.register(AssistedSearchAdapter("CCL", "https://www.cclonline.com/search/?q={query}", "Retail assisted/reference"))
        self.register(AssistedSearchAdapter("AWD-IT", "https://www.awd-it.co.uk/catalogsearch/result/?q={query}", "Retail assisted/reference"))

    def register(self, adapter: SourceAdapter) -> None:
        self._sources[adapter.source_name] = adapter

    def get(self, source_name: str) -> SourceAdapter | None:
        return self._sources.get(source_name)

    def all(self) -> list[SourceAdapter]:
        return list(self._sources.values())

    def automatic_sources(self) -> list[SourceAdapter]:
        return [source for source in self._sources.values() if source.capabilities.supports_search]

    def source_names(self) -> list[str]:
        return sorted(self._sources)
