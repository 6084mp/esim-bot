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


def regions_keyboard(regions: list[str], page: int, lang: str, page_size: int = 3) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * page_size
    chunk = regions[start : start + page_size]

    for idx, region in enumerate(chunk, start=start):
        builder.row(InlineKeyboardButton(text=region, callback_data=f"region:{idx}"))

    if start + page_size < len(regions):
        builder.row(InlineKeyboardButton(text=t(lang, "more"), callback_data=f"region_page:{page + 1}"))

    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:back"))
    return builder.as_markup()


def countries_keyboard(
    countries: list[dict[str, str]],
    region_idx: int,
    page: int,
    lang: str,
    page_size: int = 3,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * page_size
    chunk = countries[start : start + page_size]

    for country in chunk:
        title = country["name_ru"] if lang == "ru" else country["name_en"]
        builder.row(
            InlineKeyboardButton(
                text=f"{title}",
                callback_data=f"country:{country['code']}",
            )
        )

    if start + page_size < len(countries):
        builder.row(
            InlineKeyboardButton(
                text=t(lang, "more"),
                callback_data=f"countries_page:{region_idx}:{page + 1}",
            )
        )

    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:buy"))
    return builder.as_markup()


def package_list_keyboard(
    packages: list[dict],
    country_code: str,
    sort_by: str,
    page: int,
    lang: str,
    page_size: int = 2,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * page_size
    chunk = packages[start : start + page_size]

    for package in chunk:
        text = f"{package['data_gb']}GB • {package['days']}d • {package['stars_amount']}⭐"
        builder.row(InlineKeyboardButton(text=text, callback_data=f"package:{country_code}:{package['code']}"))

    if sort_by == "value":
        builder.row(
            InlineKeyboardButton(
                text=t(lang, "sort_popular"),
                callback_data=f"pkgsort:{country_code}:popular",
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=t(lang, "sort_value"),
                callback_data=f"pkgsort:{country_code}:value",
            )
        )

    if start + page_size < len(packages):
        builder.row(
            InlineKeyboardButton(
                text=t(lang, "more"),
                callback_data=f"pkgpage:{country_code}:{sort_by}:{page + 1}",
            )
        )

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
