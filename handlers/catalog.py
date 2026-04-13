from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardMarkup
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Order
from handlers.start import get_user_language
from keyboards.main_menu import (
    countries_keyboard,
    main_menu_keyboard,
    package_detail_keyboard,
    package_list_keyboard,
    regions_keyboard,
)
from services.catalog_service import CatalogService
from utils.i18n import t


router = Router()


async def _safe_edit_or_send(
    callback: CallbackQuery,
    text: str,
    reply_markup: InlineKeyboardMarkup | None = None,
) -> None:
    try:
        await callback.message.edit_text(text, reply_markup=reply_markup)
    except TelegramBadRequest:
        await callback.message.answer(text, reply_markup=reply_markup)


def _safe_page(total_items: int, page_size: int, requested_page: int) -> int:
    if total_items <= 0:
        return 0
    max_page = (total_items - 1) // page_size
    return max(0, min(requested_page, max_page))


def _region_label(region: str, lang: str) -> str:
    key = f"region_{region.lower().replace(' ', '_')}"
    value = t(lang, key)
    return value if value != key else region


@router.callback_query(F.data == "menu:buy")
async def buy_esim(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    try:
        regions = await catalog_service.get_regions()
    except Exception:
        await _safe_edit_or_send(callback, t(lang, "country_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    if not regions:
        await _safe_edit_or_send(callback, t(lang, "no_regions"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    await state.update_data(regions=regions)
    await _safe_edit_or_send(
        callback,
        t(lang, "choose_region"),
        reply_markup=regions_keyboard(regions, page=0, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("region_page:"))
async def region_page(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    requested_page = int(callback.data.split(":", 1)[1])

    data = await state.get_data()
    regions = data.get("regions") or await catalog_service.get_regions()
    if not regions:
        await _safe_edit_or_send(callback, t(lang, "no_regions"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    page = _safe_page(len(regions), 8, requested_page)
    await state.update_data(regions=regions)
    await _safe_edit_or_send(
        callback,
        t(lang, "choose_region"),
        reply_markup=regions_keyboard(regions, page=page, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("region:"))
async def region_pick(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    region_idx = int(callback.data.split(":", 1)[1])

    data = await state.get_data()
    regions = data.get("regions") or await catalog_service.get_regions()

    if region_idx < 0 or region_idx >= len(regions):
        await callback.answer()
        return

    region_name = regions[region_idx]
    countries = await catalog_service.get_countries_by_region(region_name)
    if not countries:
        await _safe_edit_or_send(callback, t(lang, "no_country_found"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    countries_map = data.get("countries_by_region") or {}
    countries_map[str(region_idx)] = countries
    await state.update_data(
        regions=regions,
        selected_region_idx=region_idx,
        selected_region=region_name,
        countries_by_region=countries_map,
    )

    await _safe_edit_or_send(
        callback,
        t(lang, "choose_country", region=_region_label(region_name, lang)),
        reply_markup=countries_keyboard(countries, region_idx=region_idx, page=0, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("countries_page:"))
async def countries_page(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    _, region_idx_raw, page_raw = callback.data.split(":", 2)
    region_idx = int(region_idx_raw)
    requested_page = int(page_raw)

    lang = await get_user_language(session_factory, callback.from_user.id)
    data = await state.get_data()

    countries_map = data.get("countries_by_region") or {}
    countries = countries_map.get(str(region_idx))
    regions = data.get("regions") or await catalog_service.get_regions()

    if countries is None:
        if region_idx < 0 or region_idx >= len(regions):
            await callback.answer()
            return
        countries = await catalog_service.get_countries_by_region(regions[region_idx])
        countries_map[str(region_idx)] = countries
        await state.update_data(countries_by_region=countries_map)

    if not countries:
        await _safe_edit_or_send(callback, t(lang, "no_country_found"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    page = _safe_page(len(countries), 20, requested_page)
    region_name = regions[region_idx] if region_idx < len(regions) else ""

    await _safe_edit_or_send(
        callback,
        t(lang, "choose_country", region=_region_label(region_name, lang)),
        reply_markup=countries_keyboard(countries, region_idx=region_idx, page=page, lang=lang),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("country:"))
async def show_country_packages(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    _, country_code = callback.data.split(":", 1)
    lang = await get_user_language(session_factory, callback.from_user.id)

    sort_by = "value"
    try:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
    except Exception:
        await _safe_edit_or_send(callback, t(lang, "package_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    if not packages:
        await _safe_edit_or_send(callback, t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    sorted_packages = catalog_service.sort_packages(packages, sort_by=sort_by)
    state_data = await state.get_data()
    country_packages = state_data.get("country_packages") or {}
    country_packages[country_code.upper()] = packages

    await state.update_data(
        country_packages=country_packages,
        package_sort_by=sort_by,
        package_page=0,
        current_country=country_code.upper(),
    )

    await _safe_edit_or_send(
        callback,
        t(lang, "packages_full_title", country=country_code.upper(), sort=t(lang, "sort_mode_value")),
        reply_markup=package_list_keyboard(
            sorted_packages,
            country_code=country_code.upper(),
            sort_by=sort_by,
            page=0,
            lang=lang,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pkgpage:"))
async def package_page(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    _, country_code, sort_by, requested_page_raw = callback.data.split(":", 3)
    requested_page = int(requested_page_raw)
    lang = await get_user_language(session_factory, callback.from_user.id)

    data = await state.get_data()
    country_packages = data.get("country_packages") or {}
    packages = country_packages.get(country_code.upper())

    if packages is None:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
        country_packages[country_code.upper()] = packages

    if not packages:
        await _safe_edit_or_send(callback, t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    sorted_packages = catalog_service.sort_packages(packages, sort_by=sort_by)
    page = _safe_page(len(sorted_packages), 4, requested_page)

    await state.update_data(
        country_packages=country_packages,
        package_sort_by=sort_by,
        package_page=page,
        current_country=country_code.upper(),
    )

    mode_key = "sort_mode_popular" if sort_by == "popular" else "sort_mode_value"
    await _safe_edit_or_send(
        callback,
        t(lang, "packages_full_title", country=country_code.upper(), sort=t(lang, mode_key)),
        reply_markup=package_list_keyboard(
            sorted_packages,
            country_code=country_code.upper(),
            sort_by=sort_by,
            page=page,
            lang=lang,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("pkgsort:"))
async def package_sort(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    _, country_code, sort_by = callback.data.split(":", 2)
    lang = await get_user_language(session_factory, callback.from_user.id)

    data = await state.get_data()
    country_packages = data.get("country_packages") or {}
    packages = country_packages.get(country_code.upper())

    if packages is None:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
        country_packages[country_code.upper()] = packages

    if not packages:
        await _safe_edit_or_send(callback, t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    sorted_packages = catalog_service.sort_packages(packages, sort_by=sort_by)
    mode_key = "sort_mode_popular" if sort_by == "popular" else "sort_mode_value"

    await state.update_data(
        country_packages=country_packages,
        package_sort_by=sort_by,
        package_page=0,
        current_country=country_code.upper(),
    )

    await _safe_edit_or_send(
        callback,
        t(lang, "packages_full_title", country=country_code.upper(), sort=t(lang, mode_key)),
        reply_markup=package_list_keyboard(
            sorted_packages,
            country_code=country_code.upper(),
            sort_by=sort_by,
            page=0,
            lang=lang,
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("package:"))
async def show_package_detail(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
) -> None:
    _, country_code, package_code = callback.data.split(":", 2)
    lang = await get_user_language(session_factory, callback.from_user.id)

    data = await state.get_data()
    country_packages = data.get("country_packages") or {}
    packages = country_packages.get(country_code.upper()) or []

    package = catalog_service.find_by_code(packages, package_code)
    if not package:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
        package = catalog_service.find_by_code(packages, package_code)

    if not package:
        await _safe_edit_or_send(callback, t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    await state.update_data(selected_package=package)

    text = t(
        lang,
        "plan_details",
        title=package["title"],
        data=package["data_gb"],
        days=package["days"],
        usd=package["retail_price"],
        stars=package["stars_amount"],
    )
    await _safe_edit_or_send(
        callback,
        text,
        reply_markup=package_detail_keyboard(country_code.upper(), package_code, lang),
    )
    await callback.answer()


@router.callback_query(F.data == "menu:orders")
async def my_orders(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    async with session_factory() as session:
        rows = (
            await session.scalars(
                select(Order)
                .where(Order.telegram_id == callback.from_user.id)
                .order_by(desc(Order.id))
                .limit(5)
            )
        ).all()

    if not rows:
        await _safe_edit_or_send(callback, t(lang, "orders_empty"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    lines = [t(lang, "orders_title")]
    for row in rows:
        lines.append(
            t(
                lang,
                "orders_item",
                id=row.id,
                country=row.country,
                usd=row.retail_price,
                status=row.payment_status,
            )
        )

    await _safe_edit_or_send(callback, "\n".join(lines), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "noop:crypto")
async def crypto_soon(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await callback.answer(t(lang, "crypto_disabled"), show_alert=False)
