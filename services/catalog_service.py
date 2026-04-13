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

FALLBACK_COUNTRIES: list[dict[str, Any]] = [
    {"code": "AL", "name": "Albania", "region": "Europe"},
    {"code": "AT", "name": "Austria", "region": "Europe"},
    {"code": "BE", "name": "Belgium", "region": "Europe"},
    {"code": "BG", "name": "Bulgaria", "region": "Europe"},
    {"code": "CH", "name": "Switzerland", "region": "Europe"},
    {"code": "CY", "name": "Cyprus", "region": "Europe"},
    {"code": "CZ", "name": "Czech Republic", "region": "Europe"},
    {"code": "DE", "name": "Germany", "region": "Europe"},
    {"code": "DK", "name": "Denmark", "region": "Europe"},
    {"code": "EE", "name": "Estonia", "region": "Europe"},
    {"code": "ES", "name": "Spain", "region": "Europe"},
    {"code": "FI", "name": "Finland", "region": "Europe"},
    {"code": "FR", "name": "France", "region": "Europe"},
    {"code": "GB", "name": "United Kingdom", "region": "Europe"},
    {"code": "GR", "name": "Greece", "region": "Europe"},
    {"code": "HR", "name": "Croatia", "region": "Europe"},
    {"code": "HU", "name": "Hungary", "region": "Europe"},
    {"code": "IE", "name": "Ireland", "region": "Europe"},
    {"code": "IS", "name": "Iceland", "region": "Europe"},
    {"code": "IT", "name": "Italy", "region": "Europe"},
    {"code": "LT", "name": "Lithuania", "region": "Europe"},
    {"code": "LU", "name": "Luxembourg", "region": "Europe"},
    {"code": "LV", "name": "Latvia", "region": "Europe"},
    {"code": "MT", "name": "Malta", "region": "Europe"},
    {"code": "NL", "name": "Netherlands", "region": "Europe"},
    {"code": "NO", "name": "Norway", "region": "Europe"},
    {"code": "PL", "name": "Poland", "region": "Europe"},
    {"code": "PT", "name": "Portugal", "region": "Europe"},
    {"code": "RO", "name": "Romania", "region": "Europe"},
    {"code": "SE", "name": "Sweden", "region": "Europe"},
    {"code": "SI", "name": "Slovenia", "region": "Europe"},
    {"code": "SK", "name": "Slovakia", "region": "Europe"},
    {"code": "TR", "name": "Turkey", "region": "Europe"},
    {"code": "AE", "name": "UAE", "region": "Middle East"},
    {"code": "BH", "name": "Bahrain", "region": "Middle East"},
    {"code": "IL", "name": "Israel", "region": "Middle East"},
    {"code": "JO", "name": "Jordan", "region": "Middle East"},
    {"code": "KW", "name": "Kuwait", "region": "Middle East"},
    {"code": "OM", "name": "Oman", "region": "Middle East"},
    {"code": "QA", "name": "Qatar", "region": "Middle East"},
    {"code": "SA", "name": "Saudi Arabia", "region": "Middle East"},
    {"code": "CN", "name": "China", "region": "Asia"},
    {"code": "HK", "name": "Hong Kong", "region": "Asia"},
    {"code": "ID", "name": "Indonesia", "region": "Asia"},
    {"code": "IN", "name": "India", "region": "Asia"},
    {"code": "JP", "name": "Japan", "region": "Asia"},
    {"code": "KH", "name": "Cambodia", "region": "Asia"},
    {"code": "KR", "name": "South Korea", "region": "Asia"},
    {"code": "LK", "name": "Sri Lanka", "region": "Asia"},
    {"code": "MY", "name": "Malaysia", "region": "Asia"},
    {"code": "NP", "name": "Nepal", "region": "Asia"},
    {"code": "PH", "name": "Philippines", "region": "Asia"},
    {"code": "SG", "name": "Singapore", "region": "Asia"},
    {"code": "TH", "name": "Thailand", "region": "Asia"},
    {"code": "TW", "name": "Taiwan", "region": "Asia"},
    {"code": "VN", "name": "Vietnam", "region": "Asia"},
    {"code": "AU", "name": "Australia", "region": "Oceania"},
    {"code": "NZ", "name": "New Zealand", "region": "Oceania"},
    {"code": "CA", "name": "Canada", "region": "North America"},
    {"code": "MX", "name": "Mexico", "region": "North America"},
    {"code": "US", "name": "United States", "region": "North America"},
    {"code": "AR", "name": "Argentina", "region": "South America"},
    {"code": "BR", "name": "Brazil", "region": "South America"},
    {"code": "CL", "name": "Chile", "region": "South America"},
    {"code": "CO", "name": "Colombia", "region": "South America"},
    {"code": "PE", "name": "Peru", "region": "South America"},
    {"code": "ZA", "name": "South Africa", "region": "Africa"},
    {"code": "EG", "name": "Egypt", "region": "Africa"},
    {"code": "MA", "name": "Morocco", "region": "Africa"},
    {"code": "TN", "name": "Tunisia", "region": "Africa"},
    {"code": "KE", "name": "Kenya", "region": "Africa"},
    {"code": "NG", "name": "Nigeria", "region": "Africa"},
]


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

        try:
            countries = await self.api_client.get_countries()
        except Exception:
            countries = FALLBACK_COUNTRIES

        if not countries:
            countries = FALLBACK_COUNTRIES

        normalized = [
            {
                "code": c["code"],
                "name_en": c.get("name") or c.get("name_en") or c["code"],
                "name_ru": c.get("name") or c.get("name_ru") or c["code"],
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
