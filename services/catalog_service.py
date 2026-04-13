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

RU_COUNTRY_NAMES: dict[str, str] = {
    "AE": "ОАЭ",
    "AL": "Албания",
    "AR": "Аргентина",
    "AT": "Австрия",
    "AU": "Австралия",
    "BE": "Бельгия",
    "BG": "Болгария",
    "BH": "Бахрейн",
    "BR": "Бразилия",
    "CA": "Канада",
    "CH": "Швейцария",
    "CL": "Чили",
    "CN": "Китай",
    "CO": "Колумбия",
    "CY": "Кипр",
    "CZ": "Чехия",
    "DE": "Германия",
    "DK": "Дания",
    "EE": "Эстония",
    "EG": "Египет",
    "ES": "Испания",
    "FI": "Финляндия",
    "FR": "Франция",
    "GB": "Великобритания",
    "GR": "Греция",
    "HK": "Гонконг",
    "HR": "Хорватия",
    "HU": "Венгрия",
    "ID": "Индонезия",
    "IE": "Ирландия",
    "IL": "Израиль",
    "IN": "Индия",
    "IS": "Исландия",
    "IT": "Италия",
    "JO": "Иордания",
    "JP": "Япония",
    "KE": "Кения",
    "KH": "Камбоджа",
    "KR": "Южная Корея",
    "KW": "Кувейт",
    "LK": "Шри-Ланка",
    "LT": "Литва",
    "LU": "Люксембург",
    "LV": "Латвия",
    "MA": "Марокко",
    "MT": "Мальта",
    "MX": "Мексика",
    "MY": "Малайзия",
    "NG": "Нигерия",
    "NL": "Нидерланды",
    "NO": "Норвегия",
    "NP": "Непал",
    "NZ": "Новая Зеландия",
    "OM": "Оман",
    "PE": "Перу",
    "PH": "Филиппины",
    "PL": "Польша",
    "PT": "Португалия",
    "QA": "Катар",
    "RO": "Румыния",
    "SA": "Саудовская Аравия",
    "SE": "Швеция",
    "SG": "Сингапур",
    "SI": "Словения",
    "SK": "Словакия",
    "TH": "Таиланд",
    "TN": "Тунис",
    "TR": "Турция",
    "TW": "Тайвань",
    "US": "США",
    "VN": "Вьетнам",
    "ZA": "ЮАР",
}

ALPHA3_TO_ALPHA2 = {
    "ARE": "AE",
    "AUS": "AU",
    "AUT": "AT",
    "BEL": "BE",
    "BGR": "BG",
    "BHR": "BH",
    "BRA": "BR",
    "CAN": "CA",
    "CHE": "CH",
    "CHN": "CN",
    "CYP": "CY",
    "CZE": "CZ",
    "DEU": "DE",
    "DNK": "DK",
    "EGY": "EG",
    "ESP": "ES",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "GBR": "GB",
    "GRC": "GR",
    "HKG": "HK",
    "HRV": "HR",
    "HUN": "HU",
    "IDN": "ID",
    "IND": "IN",
    "IRL": "IE",
    "ISL": "IS",
    "ISR": "IL",
    "ITA": "IT",
    "JPN": "JP",
    "KOR": "KR",
    "KWT": "KW",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MEX": "MX",
    "MYS": "MY",
    "NLD": "NL",
    "NOR": "NO",
    "NZL": "NZ",
    "OMN": "OM",
    "PHL": "PH",
    "POL": "PL",
    "PRT": "PT",
    "QAT": "QA",
    "ROU": "RO",
    "SAU": "SA",
    "SGP": "SG",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
    "THA": "TH",
    "TUN": "TN",
    "TUR": "TR",
    "TWN": "TW",
    "USA": "US",
    "VNM": "VN",
    "ZAF": "ZA",
}

COUNTRY_NAME_BY_CODE: dict[str, str] = {
    "AE": "UAE",
    "AU": "Australia",
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CN": "China",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HR": "Croatia",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IS": "Iceland",
    "IT": "Italy",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KH": "Cambodia",
    "KR": "South Korea",
    "KW": "Kuwait",
    "LK": "Sri Lanka",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Morocco",
    "MT": "Malta",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PE": "Peru",
    "PH": "Philippines",
    "PL": "Poland",
    "PT": "Portugal",
    "QA": "Qatar",
    "RO": "Romania",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TH": "Thailand",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TW": "Taiwan",
    "US": "United States",
    "VN": "Vietnam",
    "ZA": "South Africa",
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

    @staticmethod
    def _local_name_ru(name_en: str, code: str) -> str:
        return RU_COUNTRY_NAMES.get(code.upper(), name_en)

    @staticmethod
    def _normalize_country_code(code: str) -> str:
        code_up = (code or "").upper().strip()
        if len(code_up) == 3:
            return ALPHA3_TO_ALPHA2.get(code_up, code_up)
        return code_up

    @staticmethod
    def _fallback_region_map() -> dict[str, str]:
        return {item["code"].upper(): item["region"] for item in FALLBACK_COUNTRIES}

    @staticmethod
    def _fallback_name_map() -> dict[str, str]:
        return {item["code"].upper(): item["name"] for item in FALLBACK_COUNTRIES}

    async def get_all_countries(self, use_cache: bool = True) -> list[dict[str, Any]]:
        cache_key = "__countries__"
        if use_cache:
            cached = self.cache_service.get(cache_key)
            if cached is not None:
                return cached

        fallback_regions = self._fallback_region_map()
        fallback_names = self._fallback_name_map()
        country_map: dict[str, dict[str, Any]] = {}

        # 1) Try official countries endpoint first.
        try:
            countries = await self.api_client.get_countries()
        except Exception:
            countries = []

        for c in countries:
            if not c.get("code"):
                continue
            code = self._normalize_country_code(c["code"])
            if len(code) != 2:
                continue
            name_en = c.get("name") or c.get("name_en") or fallback_names.get(code) or code
            region = c.get("region") or fallback_regions.get(code) or "Other"
            country_map[code] = {
                "code": code,
                "name_en": name_en,
                "name_ru": self._local_name_ru(name_en, code),
                "region": self._normalize_region(region),
                "popularity_score": float(c.get("popularity_score") or 0),
            }

        # 2) Enrich with package list (stable path from your older working version).
        try:
            all_packages = await self.api_client.get_all_packages()
        except Exception:
            all_packages = []

        for pkg in all_packages:
            raw = pkg.get("raw", {})
            raw_code = (
                raw.get("countryCode")
                or raw.get("country")
                or raw.get("locationCode")
                or pkg.get("country")
                or pkg.get("location_code")
                or ""
            )
            code = self._normalize_country_code(str(raw_code))
            if len(code) != 2:
                continue

            net_list = raw.get("locationNetworkList")
            location_name = ""
            if isinstance(net_list, list) and net_list and isinstance(net_list[0], dict):
                location_name = str(net_list[0].get("locationName") or "").strip()

            name_en = (
                country_map.get(code, {}).get("name_en")
                or location_name
                or raw.get("countryName")
                or fallback_names.get(code)
                or COUNTRY_NAME_BY_CODE.get(code)
                or code
            )
            region = country_map.get(code, {}).get("region") or fallback_regions.get(code) or "Other"
            popularity = max(
                float(country_map.get(code, {}).get("popularity_score") or 0),
                float(pkg.get("popularity_score") or 0),
            )
            country_map[code] = {
                "code": code,
                "name_en": str(name_en),
                "name_ru": self._local_name_ru(str(name_en), code),
                "region": self._normalize_region(str(region)),
                "popularity_score": popularity,
            }

        # 3) Safety fallback list.
        if not country_map:
            for c in FALLBACK_COUNTRIES:
                code = self._normalize_country_code(c["code"])
                if len(code) != 2:
                    continue
                name_en = c["name"]
                country_map[code] = {
                    "code": code,
                    "name_en": name_en,
                    "name_ru": self._local_name_ru(name_en, code),
                    "region": self._normalize_region(c["region"]),
                    "popularity_score": 0.0,
                }

        normalized = list(country_map.values())

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

        try:
            packages = await self.api_client.get_packages(country_code=key)
        except RuntimeError as exc:
            error_text = str(exc).lower()
            if "error 400" in error_text or "error 404" in error_text:
                packages = []
            else:
                raise

        # Fallback strategy from previously working flow: fetch all packages and filter locally.
        if not packages:
            try:
                all_packages = await self.api_client.get_all_packages()
            except Exception:
                all_packages = []

            if all_packages:
                filtered: list[dict[str, Any]] = []
                for pkg in all_packages:
                    raw = pkg.get("raw", {})
                    candidates = [
                        self._normalize_country_code(str(pkg.get("country") or "")),
                        self._normalize_country_code(str(pkg.get("location_code") or "")),
                        self._normalize_country_code(str(raw.get("countryCode") or "")),
                        self._normalize_country_code(str(raw.get("country") or "")),
                        self._normalize_country_code(str(raw.get("locationCode") or "")),
                    ]
                    if key in candidates:
                        filtered.append(pkg)
                packages = filtered

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
