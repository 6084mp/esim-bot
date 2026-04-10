from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.types import CallbackQuery, Message
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import User
from keyboards.main_menu import language_keyboard, main_menu_keyboard
from utils.i18n import t


router = Router()


async def upsert_user(
    session_factory: async_sessionmaker,
    telegram_id: int,
    username: str | None,
    language: str | None = None,
) -> User:
    async with session_factory() as session:
        user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
        if user is None:
            user = User(telegram_id=telegram_id, username=username, language=language or "en")
            session.add(user)
        else:
            user.username = username
            if language:
                user.language = language
        await session.commit()
        await session.refresh(user)
        return user


async def get_user_language(session_factory: async_sessionmaker, telegram_id: int) -> str:
    async with session_factory() as session:
        lang = await session.scalar(select(User.language).where(User.telegram_id == telegram_id))
    return lang or "en"


@router.message(CommandStart())
async def start_cmd(message: Message, session_factory: async_sessionmaker) -> None:
    await upsert_user(
        session_factory=session_factory,
        telegram_id=message.from_user.id,
        username=message.from_user.username,
    )
    await message.answer(t("en", "welcome"), reply_markup=language_keyboard())


@router.callback_query(F.data.startswith("lang:"))
async def set_language(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    language = callback.data.split(":", 1)[1]
    if language not in {"en", "ru"}:
        language = "en"

    await upsert_user(
        session_factory=session_factory,
        telegram_id=callback.from_user.id,
        username=callback.from_user.username,
        language=language,
    )

    await callback.message.edit_text(
        f"{t(language, 'lang_saved')}\n\n{t(language, 'menu')}",
        reply_markup=main_menu_keyboard(language),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:back")
async def back_to_main(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await callback.message.edit_text(t(lang, "menu"), reply_markup=main_menu_keyboard(lang))
    await callback.answer()
