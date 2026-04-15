from __future__ import annotations

import asyncio

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery

from services.runtime_context import get_services

router = Router()


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery) -> None:
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message) -> None:
    services = get_services()
    order_service = services["order_service"]
    delivery_service = services["delivery_service"]
    localization = services["localization"]

    lang = await _lang(message)

    payload = message.successful_payment.invoice_payload
    order = await order_service.set_order_paid(payload)
    if not order:
        return

    await message.answer(localization.t(lang, "payment_success"))
    await message.answer(localization.t(lang, "delivery_wait"))

    asyncio.create_task(delivery_service.process_paid_order(message.bot, order.order_ref, lang))
