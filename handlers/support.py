from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from handlers.start import get_user_language
from keyboards.main_menu import main_menu_keyboard
from utils.i18n import t


router = Router()


@router.callback_query(F.data == "menu:support")
async def support_menu(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    text = t(lang, "support_text")
    await callback.message.edit_text(text, reply_markup=main_menu_keyboard(lang))
    await callback.answer()
