from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from services.runtime_context import get_services

from keyboards.common import language_keyboard

router = Router()


@router.message(CommandStart())
async def start_handler(message: Message) -> None:
    services = get_services()
    order_service = services["order_service"]
    localization = services["localization"]
    settings = services["settings"]

    await order_service.get_or_create_user(
        telegram_id=message.from_user.id,
        username=message.from_user.username,
        first_name=message.from_user.first_name,
        default_language=settings.default_language,
    )

    await message.answer(localization.t("en", "welcome"), reply_markup=language_keyboard())
