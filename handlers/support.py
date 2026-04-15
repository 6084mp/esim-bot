from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from services.runtime_context import get_services

router = Router()

SUPPORT_TEXTS = {"Support", "Поддержка"}


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


async def _show_support(target, lang: str) -> None:
    services = get_services()
    localization = services["localization"]
    settings = services["settings"]
    await target.answer(localization.t(lang, "support_text", username=settings.support_username))


@router.message(F.text.in_(SUPPORT_TEXTS))
async def support_message(message: Message) -> None:
    lang = await _lang(message)
    await _show_support(message, lang)


@router.callback_query(F.data == "support:open")
async def support_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _show_support(callback.message, lang)
    await callback.answer()
