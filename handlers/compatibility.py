from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.runtime_context import get_services

router = Router()

CHECK_TEXTS = {"Check Device", "Проверить устройство"}


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


async def _menu(target, lang: str) -> None:
    services = get_services()
    localization = services["localization"]

    kb = InlineKeyboardBuilder()
    kb.button(text=localization.t(lang, "compat_iphone"), callback_data="compat_device:iphone")
    kb.button(text=localization.t(lang, "compat_android"), callback_data="compat_device:android")
    kb.button(text=localization.t(lang, "compat_not_sure"), callback_data="compat_device:not_sure")
    kb.button(text=localization.t(lang, "support"), callback_data="support:open")
    kb.adjust(1)

    await target.answer(localization.t(lang, "compat_title"), reply_markup=kb.as_markup())


@router.message(F.text.in_(CHECK_TEXTS))
async def compat_message(message: Message) -> None:
    lang = await _lang(message)
    await _menu(message, lang)


@router.callback_query(F.data == "compat:open")
async def compat_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _menu(callback.message, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("compat_device:"))
async def compat_device(callback: CallbackQuery) -> None:
    _, device_type = callback.data.split(":", 1)
    services = get_services()
    localization = services["localization"]
    compatibility = services["compatibility_service"]
    lang = await _lang(callback)

    text_key = compatibility.get_text_key(device_type)
    await callback.message.answer(localization.t(lang, text_key))
    await callback.answer()
