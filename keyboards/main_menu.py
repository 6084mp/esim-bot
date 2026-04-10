from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import t


def language_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="English", callback_data="lang:en"),
        InlineKeyboardButton(text="Русский", callback_data="lang:ru"),
    )
    return builder.as_markup()


def main_menu_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "buy_esim"), callback_data="menu:buy"))
    builder.row(InlineKeyboardButton(text=t(lang, "my_orders"), callback_data="menu:orders"))
    builder.row(InlineKeyboardButton(text=t(lang, "check_device"), callback_data="menu:device"))
    builder.row(InlineKeyboardButton(text=t(lang, "faq"), callback_data="menu:faq"))
    builder.row(InlineKeyboardButton(text=t(lang, "support"), callback_data="menu:support"))
    return builder.as_markup()


def countries_keyboard(countries: list[dict[str, str]], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries[:3]:
        title = country["name_ru"] if lang == "ru" else country["name_en"]
        builder.row(
            InlineKeyboardButton(
                text=f"{country['emoji']} {title}",
                callback_data=f"country:{country['code']}",
            )
        )
    builder.row(InlineKeyboardButton(text=t(lang, "search_country"), callback_data="country:search"))
    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:back"))
    return builder.as_markup()


def search_results_keyboard(countries: list[dict[str, str]], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for country in countries[:4]:
        title = country["name_ru"] if lang == "ru" else country["name_en"]
        builder.row(
            InlineKeyboardButton(
                text=f"{country['emoji']} {title}",
                callback_data=f"country:{country['code']}",
            )
        )
    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:buy"))
    return builder.as_markup()


def packages_keyboard(offers: list[dict], lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    offer_map = {
        "best": t(lang, "offer_best"),
        "cheap": t(lang, "offer_cheap"),
        "max": t(lang, "offer_max"),
        "extra": t(lang, "offer_extra"),
    }
    for offer in offers[:3]:
        label = offer_map.get(offer["offer_type"], t(lang, "offer_extra"))
        text = f"{label} • {offer['data_gb']}GB • {offer['stars_amount']}⭐"
        builder.row(InlineKeyboardButton(text=text, callback_data=f"package:{offer['country']}:{offer['code']}"))

    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:buy"))
    return builder.as_markup()


def package_detail_keyboard(country_code: str, package_code: str, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "pay_stars"), callback_data=f"pay:{country_code}:{package_code}"))
    builder.row(InlineKeyboardButton(text=t(lang, "crypto_disabled"), callback_data="noop:crypto"))
    builder.row(InlineKeyboardButton(text=t(lang, "check_device"), callback_data="menu:device"))
    builder.row(InlineKeyboardButton(text=t(lang, "support"), callback_data="menu:support"))
    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data=f"country:{country_code}"))
    return builder.as_markup()


def confirm_price_keyboard(country_code: str, package_code: str, lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "confirm"), callback_data=f"payconfirm:{country_code}:{package_code}"))
    builder.row(InlineKeyboardButton(text=t(lang, "cancel"), callback_data=f"package:{country_code}:{package_code}"))
    return builder.as_markup()


def troubleshooting_keyboard(lang: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t(lang, "internet_not_working"), callback_data="help:internet"))
    builder.row(InlineKeyboardButton(text=t(lang, "support"), callback_data="menu:support"))
    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:back"))
    return builder.as_markup()
