from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

FAQ_TEXTS = {"FAQ"}
TOPICS = [
    "what_is",
    "speed",
    "start",
    "number",
    "hotspot",
    "install",
    "not_work",
    "refund",
]


async def _lang(obj) -> str:
    services = obj.bot["services"]
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


async def _faq_menu(target, lang: str) -> None:
    services = target.bot["services"]
    localization = services["localization"]

    kb = InlineKeyboardBuilder()
    for topic in TOPICS:
        kb.button(text=localization.t(lang, f"faq_{topic}"), callback_data=f"faq_topic:{topic}")
    kb.button(text=localization.t(lang, "back"), callback_data="menu:open")
    kb.adjust(1)
    await target.answer(localization.t(lang, "faq_title"), reply_markup=kb.as_markup())


@router.message(F.text.in_(FAQ_TEXTS))
async def faq_message(message: Message) -> None:
    lang = await _lang(message)
    await _faq_menu(message, lang)


@router.callback_query(F.data == "faq:open")
async def faq_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _faq_menu(callback.message, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("faq_topic:"))
async def faq_topic(callback: CallbackQuery) -> None:
    _, topic = callback.data.split(":", 1)
    services = callback.message.bot["services"]
    localization = services["localization"]
    lang = await _lang(callback)

    question = localization.t(lang, f"faq_{topic}")
    answer = localization.t(lang, f"faq_{topic}_a")
    await callback.message.answer(f"{question}\n\n{answer}")
    await callback.answer()
