from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from api.supplier_client import SupplierAPIClient
from config import Settings, get_settings
from database.db import build_engine, create_db, get_session_factory
from handlers import register_handlers
from services.cache_service import CacheService
from services.catalog_service import CatalogService
from services.compatibility_service import CompatibilityService
from services.delivery_service import DeliveryService
from services.localization_service import LocalizationService
from services.order_service import OrderService
from services.pricing_service import PricingService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)


def build_services(settings: Settings) -> dict:
    engine = build_engine(settings.database_url)
    session_factory = get_session_factory(engine)

    localization = LocalizationService(default_language=settings.default_language)
    pricing = PricingService(stars_usd_rate=settings.stars_usd_rate)
    cache = CacheService()

    supplier = SupplierAPIClient(
        base_url=settings.supplier_base_url,
        access_code=settings.supplier_access_code,
        secret_key=settings.supplier_secret_key,
    )

    order_service = OrderService(session_factory=session_factory)
    catalog_service = CatalogService(
        supplier_client=supplier,
        cache=cache,
        pricing=pricing,
        cache_ttl_seconds=settings.cache_ttl_seconds,
    )
    compatibility_service = CompatibilityService()
    delivery_service = DeliveryService(
        supplier_client=supplier,
        order_service=order_service,
        localization=localization,
        admin_chat_id=settings.admin_chat_id,
    )

    return {
        "settings": settings,
        "engine": engine,
        "localization": localization,
        "pricing": pricing,
        "cache": cache,
        "supplier_client": supplier,
        "order_service": order_service,
        "catalog_service": catalog_service,
        "compatibility_service": compatibility_service,
        "delivery_service": delivery_service,
    }


async def main() -> None:
    settings = get_settings()
    services = build_services(settings)

    await create_db(services["engine"])

    bot = Bot(token=settings.bot_token)
    bot["services"] = services

    dp = Dispatcher()
    register_handlers(dp)

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
