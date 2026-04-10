from __future__ import annotations

import asyncio
import logging

import aiohttp
from aiogram import Bot, Dispatcher

from api.esimaccess import EsimAccessClient
from config import get_settings
from database.db import SessionLocal, init_db
from handlers import catalog, delivery, faq, payment, start, support
from services.cache_service import InMemoryTTLCache
from services.catalog_service import CatalogService
from services.pricing_service import PricingService


async def main() -> None:
    logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()

    dp.include_router(start.router)
    dp.include_router(catalog.router)
    dp.include_router(payment.router)
    dp.include_router(delivery.router)
    dp.include_router(faq.router)
    dp.include_router(support.router)

    await init_db()

    cache_service = InMemoryTTLCache(ttl_seconds=600)
    pricing_service = PricingService(star_to_usd=settings.star_to_usd)

    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as http_session:
        async with EsimAccessClient(
            access_code=settings.esim_access_code,
            secret_key=settings.esim_secret_key,
            session=http_session,
        ) as api_client:
            catalog_service = CatalogService(
                api_client=api_client,
                pricing_service=pricing_service,
                cache_service=cache_service,
            )
            await dp.start_polling(
                bot,
                settings=settings,
                session_factory=SessionLocal,
                api_client=api_client,
                pricing_service=pricing_service,
                catalog_service=catalog_service,
                cache_service=cache_service,
            )


if __name__ == "__main__":
    asyncio.run(main())
