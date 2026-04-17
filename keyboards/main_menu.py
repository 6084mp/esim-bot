from __future__ import annotations

from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def main_menu_keyboard(localization, lang: str) -> ReplyKeyboardMarkup:
    buy = f"🛍 {localization.t(lang, 'buy_esim')}"
    orders = f"📦 {localization.t(lang, 'my_orders')}"
    check = f"📱 {localization.t(lang, 'check_device')}"
    faq = f"❓ {localization.t(lang, 'faq')}"
    support = f"🛟 {localization.t(lang, 'support')}"
    refund = f"💸 {localization.t(lang, 'refund_policy')}"
    about = f"ℹ️ {localization.t(lang, 'about')}"

    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=buy), KeyboardButton(text=orders)],
            [KeyboardButton(text=check), KeyboardButton(text=faq)],
            [KeyboardButton(text=support), KeyboardButton(text=refund)],
            [KeyboardButton(text=about)],
        ],
        resize_keyboard=True,
    )
