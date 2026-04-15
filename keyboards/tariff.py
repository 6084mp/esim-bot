from __future__ import annotations

from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def tariffs_keyboard(
    tariffs: list[dict],
    country_code: str,
    continent_key: str,
    page: int,
    total_pages: int,
    label_builder,
    prev_text: str,
    next_text: str,
    back_text: str,
) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for tariff in tariffs:
        kb.button(
            text=label_builder(tariff),
            callback_data=f"tariff:{country_code}:{continent_key}:{tariff['package_code']}:{page}",
        )

    if total_pages > 1:
        if page > 1:
            kb.button(text=f"◀️ {prev_text}", callback_data=f"tariff_page:{country_code}:{continent_key}:{page - 1}")
        if page < total_pages:
            kb.button(text=f"{next_text} ▶️", callback_data=f"tariff_page:{country_code}:{continent_key}:{page + 1}")

    kb.button(text=back_text, callback_data=f"cont:{continent_key}")
    kb.adjust(1)
    return kb.as_markup()


def tariff_detail_keyboard(localization, lang: str, country_code: str, package_code: str, continent_key: str, page: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text=localization.t(lang, "pay_stars"), callback_data=f"pay:{country_code}:{package_code}")
    kb.button(text=localization.t(lang, "pay_crypto"), callback_data=f"crypto:{country_code}:{package_code}")
    kb.button(text=localization.t(lang, "check_device"), callback_data="compat:open")
    kb.button(text=localization.t(lang, "installation_guide"), callback_data="install:open")
    kb.button(text=localization.t(lang, "support"), callback_data="support:open")
    kb.button(text=localization.t(lang, "back"), callback_data=f"tariff_page:{country_code}:{continent_key}:{page}")
    kb.adjust(1)
    return kb.as_markup()
