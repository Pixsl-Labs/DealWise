from __future__ import annotations

import json
import logging
from http.cookiejar import CookieJar
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

from dealwise.marketplaces.base import MarketplaceConnector
from dealwise.models import MarketplaceListing, MarketplaceSearchResult, SavedSearch


class VintedPublicConnector(MarketplaceConnector):
    """Best-effort public Vinted search connector.

    This connector intentionally does not log in, does not buy, does not message
    sellers, and does not store credentials. It performs a low-volume public
    catalog search and normalises whatever listing data is returned.

    Vinted may change or block internal public endpoints at any time. Failures
    are returned as safe status messages rather than crashing the app.
    """

    name = "Vinted"

    def __init__(
        self,
        base_url: str = "https://www.vinted.co.uk",
        logger: logging.Logger | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.logger = logger or logging.getLogger("dealwise.marketplaces.vinted")
        self.cookie_jar = CookieJar()
        self.opener = build_opener(HTTPCookieProcessor(self.cookie_jar))

    def search(self, saved_search: SavedSearch, limit: int = 20) -> MarketplaceSearchResult:
        query = saved_search.query.strip()

        if not query:
            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=[],
                status_message="Skipped empty Vinted search.",
            )

        url = self._build_search_url(saved_search, limit=limit)

        try:
            self._warm_cookies(query)
            response_data = self._request_json(url)
            listings = self._parse_listings(response_data, saved_search)

            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=listings,
                status_message=f"Vinted returned {len(listings)} listing(s) for '{query}'.",
            )
        except HTTPError as error:
            message = (
                f"Vinted search failed with HTTP {error.code}. "
                "This can happen if the public endpoint changes or rate-limits requests."
            )
            self.logger.warning("%s | query=%s", message, query)

            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=[],
                status_message=message,
                error=message,
            )
        except URLError as error:
            message = f"Vinted network error: {error.reason}"
            self.logger.warning("%s | query=%s", message, query)

            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=[],
                status_message=message,
                error=message,
            )
        except json.JSONDecodeError:
            message = "Vinted returned a non-JSON response."
            self.logger.warning("%s | query=%s", message, query)

            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=[],
                status_message=message,
                error=message,
            )
        except Exception as error:
            message = f"Unexpected Vinted connector error: {error}"
            self.logger.exception("%s | query=%s", message, query)

            return MarketplaceSearchResult(
                marketplace=self.name,
                query=query,
                listings=[],
                status_message=message,
                error=message,
            )

    def _build_search_url(self, saved_search: SavedSearch, limit: int) -> str:
        params: dict[str, str | int] = {
            "search_text": saved_search.query,
            "page": 1,
            "per_page": max(1, min(limit, 96)),
            "order": "newest_first",
            "currency": "GBP",
        }

        if saved_search.min_price is not None:
            params["price_from"] = f"{saved_search.min_price:.0f}"

        if saved_search.max_price is not None:
            params["price_to"] = f"{saved_search.max_price:.0f}"

        return f"{self.base_url}/api/v2/catalog/items?{urlencode(params)}"

    def _warm_cookies(self, query: str) -> None:
        search_url = f"{self.base_url}/catalog?{urlencode({'search_text': query})}"
        request = self._request(search_url, accept="text/html,application/xhtml+xml")
        self.opener.open(request, timeout=12).read(1024)

    def _request_json(self, url: str) -> dict:
        request = self._request(url, accept="application/json")
        with self.opener.open(request, timeout=20) as response:
            raw = response.read().decode("utf-8", errors="replace")

        data = json.loads(raw)

        if isinstance(data, dict):
            return data

        return {}

    def _request(self, url: str, accept: str) -> Request:
        return Request(
            url,
            headers={
                "Accept": accept,
                "Accept-Language": "en-GB,en;q=0.9",
                "Connection": "keep-alive",
                "Referer": f"{self.base_url}/",
                "User-Agent": (
                    "Mozilla/5.0 (X11; Linux x86_64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0 Safari/537.36 DealWise/0.2"
                ),
            },
        )

    def _parse_listings(
        self,
        data: dict,
        saved_search: SavedSearch,
    ) -> list[MarketplaceListing]:
        raw_items = data.get("items", [])

        if not isinstance(raw_items, list):
            return []

        listings: list[MarketplaceListing] = []

        for item in raw_items:
            if not isinstance(item, dict):
                continue

            listing = self._parse_listing(item, saved_search)

            if listing is not None:
                listings.append(listing)

        return listings

    def _parse_listing(
        self,
        item: dict,
        saved_search: SavedSearch,
    ) -> MarketplaceListing | None:
        item_id = str(item.get("id") or "").strip()
        title = str(item.get("title") or item.get("name") or "").strip()

        if not item_id or not title:
            return None

        url = self._extract_url(item)
        price, currency = self._extract_price(item)
        image_url = self._extract_image_url(item)
        seller_name = self._extract_seller_name(item)

        return MarketplaceListing(
            id=item_id,
            marketplace=self.name,
            title=title,
            price=price,
            currency=currency,
            url=url,
            image_url=image_url,
            seller_name=seller_name,
            condition=self._safe_string(item.get("status")),
            location=self._safe_string(item.get("city")),
            source_query=saved_search.query,
            search_id=saved_search.id,
            raw={
                "favourite_count": item.get("favourite_count"),
                "view_count": item.get("view_count"),
                "service_fee": item.get("service_fee"),
            },
        )

    def _extract_url(self, item: dict) -> str:
        url = item.get("url")

        if isinstance(url, str) and url.startswith("http"):
            return url

        path = item.get("path")

        if isinstance(path, str) and path:
            if path.startswith("http"):
                return path

            return f"{self.base_url}{path}"

        item_id = str(item.get("id") or "")
        return f"{self.base_url}/items/{item_id}"

    def _extract_price(self, item: dict) -> tuple[float | None, str]:
        currency = "GBP"
        price_value = item.get("price")

        if isinstance(price_value, dict):
            currency = str(
                price_value.get("currency_code")
                or price_value.get("currency")
                or currency
            ).upper()
            price_value = price_value.get("amount")

        if price_value is None:
            total_price = item.get("total_item_price")

            if isinstance(total_price, dict):
                currency = str(
                    total_price.get("currency_code")
                    or total_price.get("currency")
                    or currency
                ).upper()
                price_value = total_price.get("amount")

        try:
            if price_value is None:
                return None, currency

            return float(str(price_value).replace(",", ".")), currency
        except ValueError:
            return None, currency

    def _extract_image_url(self, item: dict) -> str | None:
        photo = item.get("photo")

        if isinstance(photo, dict):
            for key in ("url", "full_size_url", "high_resolution_url"):
                value = photo.get(key)

                if isinstance(value, str) and value.startswith("http"):
                    return value

        photos = item.get("photos")

        if isinstance(photos, list):
            for photo_item in photos:
                if not isinstance(photo_item, dict):
                    continue

                value = photo_item.get("url")

                if isinstance(value, str) and value.startswith("http"):
                    return value

        return None

    def _extract_seller_name(self, item: dict) -> str | None:
        user = item.get("user")

        if isinstance(user, dict):
            for key in ("login", "username", "name"):
                value = user.get(key)

                if isinstance(value, str) and value.strip():
                    return value.strip()

        return None

    def _safe_string(self, value: object) -> str | None:
        if value is None:
            return None

        text = str(value).strip()
        return text or None
