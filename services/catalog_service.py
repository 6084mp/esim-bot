from __future__ import annotations

from typing import Any

from api.esimaccess import EsimAccessClient
from services.cache_service import InMemoryTTLCache
from services.pricing_service import PricingService

REGION_PRIORITY = [
    "Europe",
    "Asia",
    "North America",
    "South America",
    "Africa",
    "Middle East",
    "Oceania",
    "Global",
    "Other",
]

REGION_ALIASES = {
    "eu": "Europe",
    "europe": "Europe",
    "asia": "Asia",
    "africa": "Africa",
    "middleeast": "Middle East",
    "middle east": "Middle East",
    "mena": "Middle East",
    "northamerica": "North America",
    "north america": "North America",
    "southamerica": "South America",
    "south america": "South America",
    "america": "North America",
    "americas": "North America",
    "oceania": "Oceania",
    "australia": "Oceania",
    "global": "Global",
    "world": "Global",
    "other": "Other",
}


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

    @staticmethod
    def _normalize_region(region_raw: str | None) -> str:
        if not region_raw:
            return "Other"
        key = region_raw.strip().lower()
        return REGION_ALIASES.get(key, region_raw.strip().title())

    async def get_all_countries(self, use_cache: bool = True) -> list[dict[str, Any]]:
        cache_key = "__countries__"
        if use_cache:
            cached = self.cache_service.get(cache_key)
            if cached is not None:
                return cached

        countries = await self.api_client.get_countries()
        normalized = [
            {
                "code": c["code"],
                "name_en": c["name"],
                "name_ru": c["name"],
                "region": self._normalize_region(c.get("region")),
                "popularity_score": float(c.get("popularity_score") or 0),
            }
            for c in countries
            if c.get("code") and c.get("name")
        ]

        normalized.sort(key=lambda x: x["name_en"].lower())
        if use_cache:
            self.cache_service.set(cache_key, normalized)
        return normalized

    async def get_regions(self) -> list[str]:
        countries = await self.get_all_countries(use_cache=True)
        region_set = {country["region"] for country in countries}

        ordered = [region for region in REGION_PRIORITY if region in region_set]
        leftovers = sorted(region_set.difference(set(ordered)))
        return ordered + leftovers

    async def get_countries_by_region(self, region: str) -> list[dict[str, Any]]:
        countries = await self.get_all_countries(use_cache=True)
        filtered = [country for country in countries if country["region"] == region]
        filtered.sort(key=lambda x: x["name_en"].lower())
        return filtered

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
            value_score = package["data_gb"] / retail if retail else 0
            popularity_score = float(package.get("popularity_score") or 0)

            priced_packages.append(
                {
                    **package,
                    "retail_price": retail,
                    "stars_amount": stars,
                    "value_score": round(value_score, 6),
                    "popularity_score": popularity_score,
                }
            )

        if use_cache:
            self.cache_service.set(key, priced_packages)
        return priced_packages

    @staticmethod
    def sort_packages(packages: list[dict[str, Any]], sort_by: str) -> list[dict[str, Any]]:
        if sort_by == "popular":
            return sorted(
                packages,
                key=lambda p: (
                    p.get("popularity_score", 0),
                    p.get("value_score", 0),
                    -p.get("retail_price", 0),
                ),
                reverse=True,
            )

        return sorted(
            packages,
            key=lambda p: (
                p.get("value_score", 0),
                -p.get("retail_price", 0),
                p.get("data_gb", 0),
            ),
            reverse=True,
        )

    @staticmethod
    def find_by_code(packages: list[dict[str, Any]], package_code: str) -> dict[str, Any] | None:
        for item in packages:
            if item["code"] == package_code:
                return item
        return None
