from __future__ import annotations

import asyncio
import datetime as dt
import json
import logging
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from api.supplier_client import SupplierAPIClient
from database.models import CachedTariff
from services.cache_service import CacheService
from services.pricing_service import PricingService
from utils.flags import country_flag
from utils.pagination import paginate_items

logger = logging.getLogger(__name__)


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
        CountryItem("RU", "RU", "europe", "Russia", "Россия", True),
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
        session_factory: async_sessionmaker[AsyncSession],
        stale_grace_seconds: int = 86400,
    ) -> None:
        self.supplier_client = supplier_client
        self.cache = cache
        self.pricing = pricing
        self.cache_ttl_seconds = cache_ttl_seconds
        self.stale_grace_seconds = stale_grace_seconds
        self.session_factory = session_factory
        self._country_map = {country.code: country for country in self.COUNTRIES}
        self._dynamic_country_map: dict[str, CountryItem] = {}
        self._refresh_locks: dict[str, asyncio.Lock] = {}

    def _get_refresh_lock(self, country_code: str) -> asyncio.Lock:
        key = country_code.upper()
        lock = self._refresh_locks.get(key)
        if lock is None:
            lock = asyncio.Lock()
            self._refresh_locks[key] = lock
        return lock

    @staticmethod
    def _utcnow() -> dt.datetime:
        return dt.datetime.utcnow()

    def _cache_key(self, country_code: str) -> str:
        return f"packages:{country_code.upper()}"

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
        code = country_code.upper()
        return self._country_map.get(code) or self._dynamic_country_map.get(code)

    def all_country_codes(self) -> list[str]:
        merged = {country.code for country in self.COUNTRIES}
        merged.update(self._dynamic_country_map.keys())
        return sorted(merged)

    def popular_country_codes(self) -> list[str]:
        base = [country.code for country in self.COUNTRIES if country.popular]
        # Dynamic countries are non-popular by default.
        return base

    @staticmethod
    def _continent_key_from_region(region: str) -> str | None:
        value = (region or "").strip().lower()
        if not value:
            return None
        if "global" in value:
            return "global_plans"
        if "europe" in value:
            return "europe"
        if "middle east" in value or "middle-east" in value or "gulf" in value:
            return "middle_east"
        if "north america" in value or "caribbean" in value or "central america" in value:
            return "north_america"
        if "south america" in value or "latin america" in value:
            return "south_america"
        if "africa" in value:
            return "africa"
        if "asia" in value or "oceania" in value or "pacific" in value:
            return "asia"
        return None

    async def refresh_locations(self) -> None:
        try:
            rows = await self.supplier_client.get_locations()
        except Exception:
            logger.exception("Failed to refresh locations from supplier")
            return

        dynamic: dict[str, CountryItem] = {}
        for row in rows:
            code = str(row.get("country_code", "")).upper().strip()
            if len(code) != 2:
                continue
            if code in self._country_map:
                continue

            continent_key = self._continent_key_from_region(str(row.get("continent", "")))
            if not continent_key:
                continue

            name = str(row.get("country_name", code)).strip() or code
            dynamic[code] = CountryItem(
                code=code,
                supplier_code=code,
                continent=continent_key,
                name_en=name,
                name_ru=name,
                popular=False,
            )

        self._dynamic_country_map = dynamic

    def list_countries(self, continent: str, lang: str) -> list[dict[str, Any]]:
        items = [country for country in self.COUNTRIES if country.continent == continent]
        items.extend(country for country in self._dynamic_country_map.values() if country.continent == continent)

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

    def _build_tariffs_from_packages(self, country: CountryItem, raw_packages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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
        return tariffs

    async def _save_db_cache(self, country_code: str, tariffs: list[dict[str, Any]]) -> None:
        now = self._utcnow()
        expires_at = now + dt.timedelta(seconds=max(1, self.cache_ttl_seconds))
        payload = json.dumps(tariffs, ensure_ascii=False, separators=(",", ":"))
        async with self.session_factory() as session:
            row = await session.scalar(
                select(CachedTariff).where(CachedTariff.country_code == country_code.upper())
            )
            if not row:
                row = CachedTariff(
                    country_code=country_code.upper(),
                    payload_json=payload,
                    source_count=len(tariffs),
                    updated_at=now,
                    expires_at=expires_at,
                )
                session.add(row)
            else:
                row.payload_json = payload
                row.source_count = len(tariffs)
                row.updated_at = now
                row.expires_at = expires_at
            await session.commit()

    async def _get_db_cache(self, country_code: str) -> tuple[list[dict[str, Any]], bool]:
        now = self._utcnow()
        async with self.session_factory() as session:
            row = await session.scalar(
                select(CachedTariff).where(CachedTariff.country_code == country_code.upper())
            )
            if not row:
                return [], False
            try:
                payload = json.loads(row.payload_json)
            except json.JSONDecodeError:
                return [], False
            if not isinstance(payload, list):
                return [], False

            is_fresh = row.expires_at >= now
            grace_deadline = row.expires_at + dt.timedelta(seconds=max(0, self.stale_grace_seconds))
            if not is_fresh and grace_deadline < now:
                return [], False
            return payload, is_fresh

    async def refresh_country_tariffs(self, country_code: str) -> list[dict[str, Any]]:
        country = self.get_country_by_code(country_code)
        if not country:
            return []

        lock = self._get_refresh_lock(country.code)
        async with lock:
            raw_packages = await self.supplier_client.get_packages_by_country(country.supplier_code)
            tariffs = self._build_tariffs_from_packages(country, raw_packages)
            self.cache.set(self._cache_key(country.code), tariffs, self.cache_ttl_seconds)
            await self._save_db_cache(country.code, tariffs)
            return tariffs

    def trigger_background_refresh(self, country_code: str) -> None:
        async def _runner() -> None:
            try:
                await self.refresh_country_tariffs(country_code)
            except Exception:
                logger.exception("Background refresh failed for country=%s", country_code)

        asyncio.create_task(_runner())

    async def get_tariffs(self, country_code: str, force_fresh: bool = False) -> list[dict[str, Any]]:
        country = self.get_country_by_code(country_code)
        if not country:
            return []

        cache_key = self._cache_key(country.code)
        if force_fresh:
            return await self.refresh_country_tariffs(country.code)

        cached = self.cache.get(cache_key)
        if isinstance(cached, list):
            return cached

        db_cached, is_fresh = await self._get_db_cache(country.code)
        if db_cached:
            ttl = self.cache_ttl_seconds if is_fresh else min(120, self.cache_ttl_seconds)
            self.cache.set(cache_key, db_cached, ttl)
            if not is_fresh:
                self.trigger_background_refresh(country.code)
            return db_cached

        # Hard miss (first call without prewarm): fetch synchronously.
        return await self.refresh_country_tariffs(country.code)

    async def prewarm_country_batch(self, country_codes: list[str], concurrency: int = 4) -> None:
        semaphore = asyncio.Semaphore(max(1, concurrency))

        async def _worker(code: str) -> None:
            async with semaphore:
                try:
                    await self.refresh_country_tariffs(code)
                except Exception:
                    logger.exception("Prewarm failed for country=%s", code)

        await asyncio.gather(*(_worker(code) for code in country_codes))

    async def prewarm_popular(self) -> None:
        await self.refresh_locations()
        await self.prewarm_country_batch(self.popular_country_codes(), concurrency=4)

    async def prewarm_all(self) -> None:
        await self.refresh_locations()
        await self.prewarm_country_batch(self.all_country_codes(), concurrency=4)

    async def get_tariff_by_code(self, country_code: str, package_code: str, force_fresh: bool = False) -> dict[str, Any] | None:
        tariffs = await self.get_tariffs(country_code, force_fresh=force_fresh)
        for tariff in tariffs:
            if tariff["package_code"] == package_code:
                return tariff
        return None

    def paginate_tariffs(self, tariffs: list[dict[str, Any]], page: int, page_size: int = 8) -> tuple[list[dict[str, Any]], int, int]:
        return paginate_items(tariffs, page, page_size)
