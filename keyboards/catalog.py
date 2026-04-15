from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def continents_keyboard(continents: list[dict[str, str]], back_text: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for continent in continents:
        kb.button(
            text=f"{continent['emoji']} {continent['name']}",
            callback_data=f"cont:{continent['key']}",
        )
    kb.button(text=back_text, callback_data="menu:open")
    kb.adjust(1)
    return kb.as_markup()


def countries_keyboard(
    countries: list[dict[str, str]],
    continent_key: str,
    page: int,
    total_pages: int,
    prev_text: str,
    next_text: str,
    back_text: str,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for country in countries:
        kb.button(
            text=f"{country['flag']} {country['name']}",
            callback_data=f"country:{country['code']}:{continent_key}:{page}",
        )

    if total_pages > 1:
        if page > 1:
            kb.button(text=f"◀️ {prev_text}", callback_data=f"country_page:{continent_key}:{page - 1}")
        if page < total_pages:
            kb.button(text=f"{next_text} ▶️", callback_data=f"country_page:{continent_key}:{page + 1}")

    kb.button(text=back_text, callback_data="menu:buy")
    kb.adjust(2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1)
    return kb.as_markup()
