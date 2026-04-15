from aiogram import Dispatcher

from .about import router as about_router
from .catalog import router as catalog_router
from .compatibility import router as compatibility_router
from .faq import router as faq_router
from .language import router as language_router
from .menu import router as menu_router
from .orders import router as orders_router
from .payment import router as payment_router
from .refund import router as refund_router
from .start import router as start_router
from .support import router as support_router
from .tariff import router as tariff_router
from .troubleshooting import router as troubleshooting_router


def register_handlers(dp: Dispatcher) -> None:
    dp.include_router(start_router)
    dp.include_router(language_router)
    dp.include_router(menu_router)
    dp.include_router(catalog_router)
    dp.include_router(tariff_router)
    dp.include_router(payment_router)
    dp.include_router(orders_router)
    dp.include_router(faq_router)
    dp.include_router(compatibility_router)
    dp.include_router(troubleshooting_router)
    dp.include_router(refund_router)
    dp.include_router(support_router)
    dp.include_router(about_router)
