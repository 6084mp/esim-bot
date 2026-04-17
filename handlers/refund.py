from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from services.runtime_context import get_services

router = Router()

def _is_refund_text(value: str | None) -> bool:
    if not value:
        return False
    return ("Refund Policy" in value) or ("Политика возвратов" in value)


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


@router.message(F.text.func(_is_refund_text))
async def refund_message(message: Message) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(message)
    await message.answer(localization.t(lang, "refund_text"))


@router.callback_query(F.data == "refund:open")
async def refund_callback(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(callback)
    await callback.message.answer(localization.t(lang, "refund_text"))
    await callback.answer()
