from __future__ import annotations

import logging

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message

from services.runtime_context import get_services

from keyboards.catalog import continents_keyboard, countries_keyboard
from keyboards.tariff import tariffs_keyboard
from utils.formatters import format_data_gb

router = Router()
logger = logging.getLogger(__name__)

BUY_TEXTS = {"Buy eSIM", "Купить eSIM"}


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


def _tariff_btn(localization, lang: str, tariff: dict) -> str:
    return localization.t(
        lang,
        "tariff_btn",
        gb=format_data_gb(tariff["data_amount_gb"]),
        days=tariff["validity_days"],
        stars=tariff["retail_price_stars"],
    )


async def _show_continents(target, lang: str) -> None:
    services = get_services()
    localization = services["localization"]
    catalog = services["catalog_service"]

    continents = catalog.get_continents(lang, localization.t)
    await target.answer(
        localization.t(lang, "continents_title"),
        reply_markup=continents_keyboard(continents, localization.t(lang, "back")),
    )


@router.message(F.text.in_(BUY_TEXTS))
async def buy_message(message: Message) -> None:
    lang = await _lang(message)
    await _show_continents(message, lang)


@router.callback_query(F.data == "menu:buy")
async def buy_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _show_continents(callback.message, lang)
    await callback.answer()


async def _show_countries(callback: CallbackQuery, continent_key: str, page: int) -> None:
    services = get_services()
    localization = services["localization"]
    catalog = services["catalog_service"]
    lang = await _lang(callback)

    countries, current_page, total_pages = catalog.paginate_countries(continent_key, lang, page=page, page_size=10)
    continent_name = localization.t(lang, continent_key)

    await callback.message.edit_text(
        localization.t(lang, "countries_title", continent=continent_name),
        reply_markup=countries_keyboard(
            countries,
            continent_key=continent_key,
            page=current_page,
            total_pages=total_pages,
            prev_text=localization.t(lang, "prev"),
            next_text=localization.t(lang, "next"),
            back_text=localization.t(lang, "back"),
        ),
    )


@router.callback_query(F.data.startswith("cont:"))
async def continent_selected(callback: CallbackQuery) -> None:
    continent_key = callback.data.split(":", 1)[1]
    await _show_countries(callback, continent_key, page=1)
    await callback.answer()


@router.callback_query(F.data.startswith("country_page:"))
async def countries_page(callback: CallbackQuery) -> None:
    _, continent_key, page_s = callback.data.split(":", 2)
    await _show_countries(callback, continent_key, page=int(page_s))
    await callback.answer()


async def _show_tariffs(callback: CallbackQuery, country_code: str, continent_key: str, page: int) -> None:
    services = get_services()
    localization = services["localization"]
    catalog = services["catalog_service"]
    lang = await _lang(callback)

    country = catalog.get_country_by_code(country_code)
    if not country:
        await callback.message.answer(localization.t(lang, "no_tariffs"))
        return

    tariffs = await catalog.get_tariffs(country_code)
    if not tariffs:
        await callback.message.answer(localization.t(lang, "no_tariffs"))
        return

    page_items, current_page, total_pages = catalog.paginate_tariffs(tariffs, page=page, page_size=8)

    await callback.message.edit_text(
        localization.t(lang, "tariffs_title", country=(country.name_ru if lang == "ru" else country.name_en)),
        reply_markup=tariffs_keyboard(
            tariffs=page_items,
            country_code=country_code,
            continent_key=continent_key,
            page=current_page,
            total_pages=total_pages,
            label_builder=lambda x: _tariff_btn(localization, lang, x),
            prev_text=localization.t(lang, "prev"),
            next_text=localization.t(lang, "next"),
            back_text=localization.t(lang, "back"),
        ),
    )


@router.callback_query(F.data.startswith("country:"))
async def country_selected(callback: CallbackQuery) -> None:
    _, country_code, continent_key, _page = callback.data.split(":", 3)
    await callback.answer()
    try:
        await _show_tariffs(callback, country_code=country_code, continent_key=continent_key, page=1)
    except Exception:
        logger.exception("Failed to show tariffs for country=%s continent=%s", country_code, continent_key)
        services = get_services()
        localization = services["localization"]
        lang = await _lang(callback)
        await callback.message.answer(localization.t(lang, "unknown_error"))


@router.callback_query(F.data.startswith("tariff_page:"))
async def tariff_page(callback: CallbackQuery) -> None:
    _, country_code, continent_key, page_s = callback.data.split(":", 3)
    await callback.answer()
    try:
        await _show_tariffs(callback, country_code=country_code, continent_key=continent_key, page=int(page_s))
    except Exception:
        logger.exception("Failed to show tariff page for country=%s continent=%s page=%s", country_code, continent_key, page_s)
        services = get_services()
        localization = services["localization"]
        lang = await _lang(callback)
        await callback.message.answer(localization.t(lang, "unknown_error"))
