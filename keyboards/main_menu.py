from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from utils.i18n import t

ALPHA3_TO_ALPHA2 = {
    "ARE": "AE",
    "AUS": "AU",
    "AUT": "AT",
    "BEL": "BE",
    "BGR": "BG",
    "BHR": "BH",
    "BRA": "BR",
    "CAN": "CA",
    "CHE": "CH",
    "CHN": "CN",
    "CYP": "CY",
    "CZE": "CZ",
    "DEU": "DE",
    "DNK": "DK",
    "EGY": "EG",
    "ESP": "ES",
    "EST": "EE",
    "FIN": "FI",
    "FRA": "FR",
    "GBR": "GB",
    "GRC": "GR",
    "HKG": "HK",
    "HRV": "HR",
    "HUN": "HU",
    "IDN": "ID",
    "IND": "IN",
    "IRL": "IE",
    "ISL": "IS",
    "ISR": "IL",
    "ITA": "IT",
    "JPN": "JP",
    "KOR": "KR",
    "KWT": "KW",
    "LTU": "LT",
    "LUX": "LU",
    "LVA": "LV",
    "MEX": "MX",
    "MYS": "MY",
    "NLD": "NL",
    "NOR": "NO",
    "NZL": "NZ",
    "OMN": "OM",
    "PHL": "PH",
    "POL": "PL",
    "PRT": "PT",
    "QAT": "QA",
    "ROU": "RO",
    "SAU": "SA",
    "SGP": "SG",
    "SVK": "SK",
    "SVN": "SI",
    "SWE": "SE",
    "THA": "TH",
    "TUN": "TN",
    "TUR": "TR",
    "TWN": "TW",
    "USA": "US",
    "VNM": "VN",
    "ZAF": "ZA",
}


def _flag_emoji(country_code: str) -> str:
    code = (country_code or "").upper().strip()
    if len(code) == 3:
        code = ALPHA3_TO_ALPHA2.get(code, "")
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return chr(0x1F1E6 + ord(code[0]) - ord("A")) + chr(0x1F1E6 + ord(code[1]) - ord("A"))


def _region_title(region: str, lang: str) -> str:
    key = f"region_{region.lower().replace(' ', '_')}"
    translated = t(lang, key)
    return translated if translated != key else region


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


def regions_keyboard(regions: list[str], page: int, lang: str, page_size: int = 8) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * page_size
    chunk = regions[start : start + page_size]

    for idx, region in enumerate(chunk, start=start):
        builder.row(InlineKeyboardButton(text=_region_title(region, lang), callback_data=f"region:{idx}"))

    if start + page_size < len(regions):
        builder.row(InlineKeyboardButton(text=t(lang, "more"), callback_data=f"region_page:{page + 1}"))

    builder.row(InlineKeyboardButton(text=t(lang, "back"), callback_data="menu:back"))
    return builder.as_markup()


def countries_keyboard(
    countries: list[dict[str, str]],
    region_idx: int,
    page: int,
    lang: str,
    page_size: int = 20,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    start = page * page_size
    chunk = countries[start : start + page_size]
    for i in range(0, len(chunk), 2):
        left = chunk[i]
        left_title = left["name_ru"] if lang == "ru" else left["name_en"]
        left_flag = _flag_emoji(left["code"])
        left_btn = InlineKeyboardButton(
            text=f"{left_flag} {left_title}".strip(),
            callback_data=f"country:{left['code']}",
        )
        right_btn = None
        if i + 1 < len(chunk):
            right = chunk[i + 1]
            right_title = right["name_ru"] if lang == "ru" else right["name_en"]
            right_flag = _flag_emoji(right["code"])
            right_btn = InlineKeyboardButton(
                text=f"{right_flag} {right_title}".strip(),
                callback_data=f"country:{right['code']}",
            )
        if right_btn:
            builder.row(left_btn, right_btn)
        else:
            builder.row(left_btn)

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
    page_size: int = 4,
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
