from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.main_menu import main_menu_keyboard

router = Router()


@router.callback_query(F.data.startswith("lang:"))
async def language_selected(callback: CallbackQuery) -> None:
    services = callback.message.bot["services"]
    order_service = services["order_service"]
    localization = services["localization"]

    lang = callback.data.split(":", 1)[1]
    if lang not in {"en", "ru"}:
        lang = "en"

    await order_service.set_user_language(callback.from_user.id, lang)

    await callback.message.answer(
        localization.t(lang, "menu_title"),
        reply_markup=main_menu_keyboard(localization, lang),
    )
    await callback.answer(localization.t(lang, "language_saved"))
