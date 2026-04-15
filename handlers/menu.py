from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from services.runtime_context import get_services

from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.callback_query(F.data == "menu:open")
async def menu_open_cb(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    order_service = services["order_service"]
    settings = services["settings"]

    lang = await order_service.get_user_language(callback.from_user.id, settings.default_language)
    await callback.message.answer(localization.t(lang, "menu_title"), reply_markup=main_menu_keyboard(localization, lang))
    await callback.answer()
