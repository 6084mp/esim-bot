from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.runtime_context import get_services

router = Router()


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


@router.callback_query(F.data == "trouble:open")
async def trouble_callback(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(callback)

    kb = InlineKeyboardBuilder()
    kb.button(text=localization.t(lang, "support"), callback_data="support:open")
    kb.adjust(1)

    await callback.message.answer(localization.t(lang, "troubleshoot_text"), reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "install:open")
async def install_callback(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    lang = await _lang(callback)
    await callback.message.answer(localization.t(lang, "install_text"))
    await callback.answer()
