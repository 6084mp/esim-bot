from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(localization, lang: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=localization.t(lang, "buy_esim"))],
            [KeyboardButton(text=localization.t(lang, "my_orders"))],
            [KeyboardButton(text=localization.t(lang, "check_device"))],
            [KeyboardButton(text=localization.t(lang, "faq"))],
            [KeyboardButton(text=localization.t(lang, "support"))],
            [KeyboardButton(text=localization.t(lang, "refund_policy"))],
            [KeyboardButton(text=localization.t(lang, "about"))],
        ],
        resize_keyboard=True,
    )
