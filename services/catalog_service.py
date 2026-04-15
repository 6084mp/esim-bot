from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from api.supplier_client import SupplierAPIClient
from services.cache_service import CacheService
from services.pricing_service import PricingService
from utils.flags import country_flag
from utils.pagination import paginate_items


@dataclass(frozen=True)
class CountryItem:
    code: str
    supplier_code: str
    continent: str
    name_en: str
    name_ru: str
    popular: bool


class CatalogService:
    CONTINENT_ORDER = [
        "europe",
        "asia",
        "north_america",
        "south_america",
        "africa",
        "middle_east",
        "global_plans",
    ]

    CONTINENT_EMOJI = {
        "europe": "🇪🇺",
        "asia": "🌏",
        "north_america": "🌎",
        "south_america": "🌎",
        "africa": "🌍",
        "middle_east": "🕌",
        "global_plans": "🌐",
    }

    COUNTRIES: list[CountryItem] = [
        CountryItem("GB", "GB", "europe", "United Kingdom", "Великобритания", True),
        CountryItem("DE", "DE", "europe", "Germany", "Германия", True),
        CountryItem("FR", "FR", "europe", "France", "Франция", True),
        CountryItem("IT", "IT", "europe", "Italy", "Италия", True),
        CountryItem("ES", "ES", "europe", "Spain", "Испания", True),
        CountryItem("TR", "TR", "europe", "Turkey", "Турция", True),
        CountryItem("AT", "AT", "europe", "Austria", "Австрия", False),
        CountryItem("BE", "BE", "europe", "Belgium", "Бельгия", False),
        CountryItem("BG", "BG", "europe", "Bulgaria", "Болгария", False),
        CountryItem("CH", "CH", "europe", "Switzerland", "Швейцария", False),
        CountryItem("CZ", "CZ", "europe", "Czech Republic", "Чехия", False),
        CountryItem("GR", "GR", "europe", "Greece", "Греция", False),
        CountryItem("HR", "HR", "europe", "Croatia", "Хорватия", False),
        CountryItem("HU", "HU", "europe", "Hungary", "Венгрия", False),
        CountryItem("IE", "IE", "europe", "Ireland", "Ирландия", False),
        CountryItem("NL", "NL", "europe", "Netherlands", "Нидерланды", False),
        CountryItem("NO", "NO", "europe", "Norway", "Норвегия", False),
        CountryItem("PL", "PL", "europe", "Poland", "Польша", False),
        CountryItem("PT", "PT", "europe", "Portugal", "Португалия", False),
        CountryItem("RO", "RO", "europe", "Romania", "Румыния", False),
        CountryItem("SE", "SE", "europe", "Sweden", "Швеция", False),

        CountryItem("TH", "TH", "asia", "Thailand", "Таиланд", True),
        CountryItem("JP", "JP", "asia", "Japan", "Япония", True),
        CountryItem("SG", "SG", "asia", "Singapore", "Сингапур", True),
        CountryItem("ID", "ID", "asia", "Indonesia", "Индонезия", True),
        CountryItem("MY", "MY", "asia", "Malaysia", "Малайзия", True),
        CountryItem("VN", "VN", "asia", "Vietnam", "Вьетнам", True),
        CountryItem("CN", "CN", "asia", "China", "Китай", False),
        CountryItem("HK", "HK", "asia", "Hong Kong", "Гонконг", False),
        CountryItem("IN", "IN", "asia", "India", "Индия", False),
        CountryItem("KR", "KR", "asia", "South Korea", "Южная Корея", False),
        CountryItem("KZ", "KZ", "asia", "Kazakhstan", "Казахстан", False),
        CountryItem("LK", "LK", "asia", "Sri Lanka", "Шри-Ланка", False),
        CountryItem("MN", "MN", "asia", "Mongolia", "Монголия", False),
        CountryItem("PH", "PH", "asia", "Philippines", "Филиппины", False),
        CountryItem("PK", "PK", "asia", "Pakistan", "Пакистан", False),
        CountryItem("TW", "TW", "asia", "Taiwan", "Тайвань", False),
        CountryItem("UZ", "UZ", "asia", "Uzbekistan", "Узбекистан", False),

        CountryItem("US", "US", "north_america", "United States", "США", True),
        CountryItem("CA", "CA", "north_america", "Canada", "Канада", True),
        CountryItem("MX", "MX", "north_america", "Mexico", "Мексика", True),
        CountryItem("CR", "CR", "north_america", "Costa Rica", "Коста-Рика", False),
        CountryItem("DO", "DO", "north_america", "Dominican Republic", "Доминикана", False),
        CountryItem("GT", "GT", "north_america", "Guatemala", "Гватемала", False),
        CountryItem("JM", "JM", "north_america", "Jamaica", "Ямайка", False),
        CountryItem("PA", "PA", "north_america", "Panama", "Панама", False),

        CountryItem("BR", "BR", "south_america", "Brazil", "Бразилия", True),
        CountryItem("AR", "AR", "south_america", "Argentina", "Аргентина", True),
        CountryItem("CL", "CL", "south_america", "Chile", "Чили", True),
        CountryItem("CO", "CO", "south_america", "Colombia", "Колумбия", True),
        CountryItem("PE", "PE", "south_america", "Peru", "Перу", False),
        CountryItem("UY", "UY", "south_america", "Uruguay", "Уругвай", False),
        CountryItem("EC", "EC", "south_america", "Ecuador", "Эквадор", False),

        CountryItem("EG", "EG", "africa", "Egypt", "Египет", True),
        CountryItem("ZA", "ZA", "africa", "South Africa", "ЮАР", True),
        CountryItem("MA", "MA", "africa", "Morocco", "Марокко", True),
        CountryItem("KE", "KE", "africa", "Kenya", "Кения", False),
        CountryItem("NG", "NG", "africa", "Nigeria", "Нигерия", False),
        CountryItem("TN", "TN", "africa", "Tunisia", "Тунис", False),
        CountryItem("GH", "GH", "africa", "Ghana", "Гана", False),
        CountryItem("TZ", "TZ", "africa", "Tanzania", "Танзания", False),
        CountryItem("UG", "UG", "africa", "Uganda", "Уганда", False),

        CountryItem("AE", "AE", "middle_east", "United Arab Emirates", "ОАЭ", True),
        CountryItem("SA", "SA", "middle_east", "Saudi Arabia", "Саудовская Аравия", True),
        CountryItem("QA", "QA", "middle_east", "Qatar", "Катар", False),
        CountryItem("OM", "OM", "middle_east", "Oman", "Оман", False),
        CountryItem("BH", "BH", "middle_east", "Bahrain", "Бахрейн", False),
        CountryItem("IL", "IL", "middle_east", "Israel", "Израиль", False),
        CountryItem("JO", "JO", "middle_east", "Jordan", "Иордания", False),
        CountryItem("KW", "KW", "middle_east", "Kuwait", "Кувейт", False),

        CountryItem("GL", "GLOBAL", "global_plans", "Global Plan", "Глобальный тариф", True),
    ]

    def __init__(
        self,
        supplier_client: SupplierAPIClient,
        cache: CacheService,
        pricing: PricingService,
        cache_ttl_seconds: int,
    ) -> None:
        self.supplier_client = supplier_client
        self.cache = cache
        self.pricing = pricing
        self.cache_ttl_seconds = cache_ttl_seconds
        self._country_map = {country.code: country for country in self.COUNTRIES}

    def get_continents(self, lang: str, t_func) -> list[dict[str, str]]:
        data: list[dict[str, str]] = []
        for key in self.CONTINENT_ORDER:
            data.append(
                {
                    "key": key,
                    "name": t_func(lang, key),
                    "emoji": self.CONTINENT_EMOJI.get(key, "🌐"),
                }
            )
        return data

    def _country_name(self, country: CountryItem, lang: str) -> str:
        return country.name_ru if lang == "ru" else country.name_en

    def get_country_by_code(self, country_code: str) -> CountryItem | None:
        return self._country_map.get(country_code.upper())

    def list_countries(self, continent: str, lang: str) -> list[dict[str, Any]]:
        items = [country for country in self.COUNTRIES if country.continent == continent]

        popular = [item for item in items if item.popular]
        regular = [item for item in items if not item.popular]
        regular.sort(key=lambda item: self._country_name(item, lang).lower())
        ordered = popular + regular

        result: list[dict[str, Any]] = []
        for country in ordered:
            result.append(
                {
                    "code": country.code,
                    "supplier_code": country.supplier_code,
                    "name": self._country_name(country, lang),
                    "flag": country_flag(country.code),
                    "popular": country.popular,
                }
            )
        return result

    def paginate_countries(self, continent: str, lang: str, page: int, page_size: int = 10) -> tuple[list[dict[str, Any]], int, int]:
        countries = self.list_countries(continent, lang)
        return paginate_items(countries, page, page_size)

    async def get_tariffs(self, country_code: str, force_fresh: bool = False) -> list[dict[str, Any]]:
        country = self.get_country_by_code(country_code)
        if not country:
            return []

        cache_key = f"packages:{country.code}"
        if not force_fresh:
            cached = self.cache.get(cache_key)
            if isinstance(cached, list):
                return cached

        raw_packages = await self.supplier_client.get_packages_by_country(country.supplier_code)

        tariffs: list[dict[str, Any]] = []
        for package in raw_packages:
            wholesale = float(package["wholesale_price_usd"])
            retail_usd = self.pricing.calculate_retail_usd(wholesale, country.code)
            stars = self.pricing.usd_to_stars(retail_usd)
            data_gb = round(float(package["volume_mb"]) / 1024, 3)
            validity_days = int(package["validity_days"])
            value_score = self.pricing.calculate_value_score(data_gb, retail_usd, validity_days)

            tariffs.append(
                {
                    "package_code": package["package_code"],
                    "country_code": country.code,
                    "country_name_en": country.name_en,
                    "country_name_ru": country.name_ru,
                    "data_amount_gb": data_gb,
                    "validity_days": validity_days,
                    "wholesale_price_usd": wholesale,
                    "retail_price_usd": retail_usd,
                    "retail_price_stars": stars,
                    "value_score": value_score,
                }
            )

        tariffs.sort(key=lambda x: x["value_score"], reverse=True)
        self.cache.set(cache_key, tariffs, self.cache_ttl_seconds)
        return tariffs

    async def get_tariff_by_code(self, country_code: str, package_code: str, force_fresh: bool = False) -> dict[str, Any] | None:
        tariffs = await self.get_tariffs(country_code, force_fresh=force_fresh)
        for tariff in tariffs:
            if tariff["package_code"] == package_code:
                return tariff
        return None

    def paginate_tariffs(self, tariffs: list[dict[str, Any]], page: int, page_size: int = 8) -> tuple[list[dict[str, Any]], int, int]:
        return paginate_items(tariffs, page, page_size)
