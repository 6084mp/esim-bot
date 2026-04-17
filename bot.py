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
from services.runtime_context import set_services
from services.support_service import SupportService

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


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
    support_service = SupportService(session_factory=session_factory)
    catalog_service = CatalogService(
        supplier_client=supplier,
        cache=cache,
        pricing=pricing,
        cache_ttl_seconds=settings.cache_ttl_seconds,
        session_factory=session_factory,
        stale_grace_seconds=settings.catalog_stale_grace_seconds,
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
        "support_service": support_service,
        "catalog_service": catalog_service,
        "compatibility_service": compatibility_service,
        "delivery_service": delivery_service,
    }


async def _catalog_refresh_loop(catalog_service: CatalogService, settings: Settings) -> None:
    popular_interval = max(60, settings.catalog_popular_refresh_seconds)
    full_interval = max(popular_interval, settings.catalog_refresh_seconds)

    try:
        logger.info("Catalog prewarm: popular countries")
        await catalog_service.prewarm_popular()
    except Exception:
        logger.exception("Initial popular prewarm failed")

    last_full_refresh = 0.0

    while True:
        try:
            logger.info("Catalog background refresh: popular countries")
            await catalog_service.prewarm_popular()

            now = asyncio.get_running_loop().time()
            if (now - last_full_refresh) >= full_interval:
                logger.info("Catalog background refresh: all countries")
                await catalog_service.prewarm_all()
                last_full_refresh = now
        except Exception:
            logger.exception("Catalog refresh loop iteration failed")

        await asyncio.sleep(popular_interval)


async def main() -> None:
    settings = get_settings()
    services = build_services(settings)
    set_services(services)

    await create_db(services["engine"])

    bot = Bot(token=settings.bot_token)

    dp = Dispatcher()
    register_handlers(dp)
    refresh_task = asyncio.create_task(_catalog_refresh_loop(services["catalog_service"], settings))
    try:
        await dp.start_polling(bot)
    finally:
        refresh_task.cancel()
        await asyncio.gather(refresh_task, return_exceptions=True)


if __name__ == "__main__":
    asyncio.run(main())
