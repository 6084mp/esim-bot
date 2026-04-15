from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from services.runtime_context import get_services

router = Router()

ABOUT_TEXTS = {"About", "О сервисе"}


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


@router.message(F.text.in_(ABOUT_TEXTS))
async def about_message(message: Message) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(message)
    await message.answer(localization.t(lang, "about_text"))


@router.callback_query(F.data == "about:open")
async def about_callback(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(callback)
    await callback.message.answer(localization.t(lang, "about_text"))
    await callback.answer()
