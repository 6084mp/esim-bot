from __future__ import annotations

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from database.models import Order
from handlers.start import get_user_language
from keyboards.main_menu import (
    countries_keyboard,
    main_menu_keyboard,
    package_detail_keyboard,
    packages_keyboard,
    search_results_keyboard,
)
from services.catalog_service import CatalogService
from utils.i18n import t


router = Router()


class CatalogStates(StatesGroup):
    waiting_country_query = State()


@router.callback_query(F.data == "menu:buy")
async def buy_esim(callback: CallbackQuery, session_factory: async_sessionmaker, catalog_service: CatalogService) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    countries = await catalog_service.get_popular_countries()
    await callback.message.edit_text(
        t(lang, "pick_country"),
        reply_markup=countries_keyboard(countries, lang),
    )
    await callback.answer()


@router.callback_query(F.data == "country:search")
async def ask_country_search(callback: CallbackQuery, state: FSMContext, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await state.set_state(CatalogStates.waiting_country_query)
    await callback.message.edit_text(t(lang, "send_country_query"))
    await callback.answer()


@router.message(CatalogStates.waiting_country_query)
async def country_search(
    message: Message,
    state: FSMContext,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
) -> None:
    lang = await get_user_language(session_factory, message.from_user.id)
    query = (message.text or "").strip()
    if not query:
        await message.answer(t(lang, "send_country_query"))
        return

    try:
        countries = await catalog_service.search_countries(query)
    except Exception:
        await message.answer(t(lang, "country_error"), reply_markup=main_menu_keyboard(lang))
        await state.clear()
        return

    if not countries:
        await message.answer(t(lang, "no_country_found"), reply_markup=main_menu_keyboard(lang))
        await state.clear()
        return

    await message.answer(
        t(lang, "pick_country"),
        reply_markup=search_results_keyboard(countries, lang),
    )
    await state.clear()


@router.callback_query(F.data.startswith("country:"))
async def show_country_packages(
    callback: CallbackQuery,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    state: FSMContext,
) -> None:
    _, country_code = callback.data.split(":", 1)
    if country_code == "search":
        return

    lang = await get_user_language(session_factory, callback.from_user.id)

    try:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
    except Exception:
        await callback.message.edit_text(t(lang, "country_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    offers = catalog_service.select_top_three(packages)
    if not offers:
        await callback.message.edit_text(t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    lines: list[str] = [t(lang, "packages_title", country=country_code.upper())]
    for offer in offers:
        offer_label_key = {
            "best": "offer_best",
            "cheap": "offer_cheap",
            "max": "offer_max",
            "extra": "offer_extra",
        }.get(offer["offer_type"], "offer_extra")
        lines.append(
            t(
                lang,
                "plan_line",
                label=t(lang, offer_label_key),
                data=offer["data_gb"],
                days=offer["days"],
                usd=offer["retail_price"],
                stars=offer["stars_amount"],
            )
        )

    await state.update_data(country_packages={country_code.upper(): packages})
    await callback.message.edit_text("\n".join(lines), reply_markup=packages_keyboard(offers, lang))
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
    country_packages = data.get("country_packages", {})
    packages = country_packages.get(country_code.upper()) or []

    package = catalog_service.find_by_code(packages, package_code)
    if not package:
        packages = await catalog_service.get_country_packages(country_code=country_code, use_cache=True)
        package = catalog_service.find_by_code(packages, package_code)

    if not package:
        await callback.message.edit_text(t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
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
    await callback.message.edit_text(
        text,
        reply_markup=package_detail_keyboard(country_code, package_code, lang),
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
        await callback.message.edit_text(t(lang, "orders_empty"), reply_markup=main_menu_keyboard(lang))
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

    await callback.message.edit_text("\n".join(lines), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "noop:crypto")
async def crypto_soon(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await callback.answer(t(lang, "crypto_disabled"), show_alert=False)
