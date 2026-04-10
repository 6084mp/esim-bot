from __future__ import annotations

from typing import Any

from api.esimaccess import EsimAccessClient
from config import POPULAR_COUNTRIES
from services.cache_service import InMemoryTTLCache
from services.pricing_service import PricingService


class CatalogService:
    def __init__(
        self,
        api_client: EsimAccessClient,
        pricing_service: PricingService,
        cache_service: InMemoryTTLCache,
    ) -> None:
        self.api_client = api_client
        self.pricing_service = pricing_service
        self.cache_service = cache_service

    async def get_popular_countries(self) -> list[dict[str, str]]:
        return POPULAR_COUNTRIES

    async def search_countries(self, query: str) -> list[dict[str, str]]:
        countries = await self.api_client.get_countries(search=query)
        return [{"code": c["code"], "name_en": c["name"], "name_ru": c["name"], "emoji": "🌍"} for c in countries[:4]]

    async def get_country_packages(self, country_code: str, use_cache: bool = True) -> list[dict[str, Any]]:
        key = country_code.upper()
        if use_cache:
            cached = self.cache_service.get(key)
            if cached is not None:
                return cached

        packages = await self.api_client.get_packages(country_code=key)
        priced_packages: list[dict[str, Any]] = []

        for package in packages:
            if package["wholesale_price"] <= 0 or package["data_gb"] <= 0:
                continue
            retail = self.pricing_service.retail_price_usd(package["wholesale_price"], key)
            stars = self.pricing_service.usd_to_stars(retail)
            priced_packages.append(
                {
                    **package,
                    "retail_price": retail,
                    "stars_amount": stars,
                }
            )

        if use_cache:
            self.cache_service.set(key, priced_packages)
        return priced_packages

    @staticmethod
    def select_top_three(packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if not packages:
            return []

        cheapest = min(packages, key=lambda x: x["retail_price"])

        def value_score(item: dict[str, Any]) -> float:
            return item["data_gb"] / item["retail_price"] if item["retail_price"] else 0

        best_value = max(packages, key=value_score)
        maximum = max(packages, key=lambda x: x["data_gb"])

        seen_codes: set[str] = set()
        selected: list[dict[str, Any]] = []

        for label, pack in [("best", best_value), ("cheap", cheapest), ("max", maximum)]:
            code = pack["code"]
            if code in seen_codes:
                continue
            item = {**pack, "offer_type": label}
            selected.append(item)
            seen_codes.add(code)

        if len(selected) < 3:
            for item in sorted(packages, key=lambda x: x["retail_price"]):
                if item["code"] in seen_codes:
                    continue
                selected.append({**item, "offer_type": "extra"})
                seen_codes.add(item["code"])
                if len(selected) == 3:
                    break

        return selected[:3]

    @staticmethod
    def find_by_code(packages: list[dict[str, Any]], package_code: str) -> dict[str, Any] | None:
        for item in packages:
            if item["code"] == package_code:
                return item
        return None
