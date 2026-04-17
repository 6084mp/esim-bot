from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def language_keyboard() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🇬🇧 English", callback_data="lang:en")
    kb.button(text="🇷🇺 Русский", callback_data="lang:ru")
    kb.adjust(1)
    return kb.as_markup()


def back_inline_keyboard(back_data: str, back_text: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=back_text, callback_data=back_data)
    return kb.as_markup()


def post_delivery_keyboard(localization, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=localization.t(lang, "installation_guide"), callback_data="install:open")
    kb.button(text=localization.t(lang, "internet_not_working"), callback_data="trouble:open")
    kb.button(text=localization.t(lang, "support"), callback_data="support:open")
    kb.button(text=localization.t(lang, "buy_another"), callback_data="menu:buy")
    kb.adjust(1)
    return kb.as_markup()


def support_keyboard(localization, lang: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=localization.t(lang, "support_write"), callback_data="support:compose")
    kb.button(text=localization.t(lang, "back"), callback_data="menu:open")
    kb.adjust(1)
    return kb.as_markup()
