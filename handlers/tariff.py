from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice
from aiogram.utils.keyboard import InlineKeyboardBuilder

from services.runtime_context import get_services

from keyboards.tariff import tariff_detail_keyboard
from utils.flags import country_flag
from utils.formatters import format_data_amount, format_data_gb, format_usd

router = Router()


async def _lang(obj) -> str:
    services = get_services()
    settings = services["settings"]
    order_service = services["order_service"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


@router.callback_query(F.data.startswith("tariff:"))
async def tariff_detail(callback: CallbackQuery) -> None:
    _, country_code, continent_key, package_code, page_s = callback.data.split(":", 4)

    services = get_services()
    localization = services["localization"]
    catalog = services["catalog_service"]

    lang = await _lang(callback)
    tariff = await catalog.get_tariff_by_code(country_code, package_code, force_fresh=False)
    country = catalog.get_country_by_code(country_code)

    if not tariff or not country:
        await callback.answer(localization.t(lang, "no_tariffs"), show_alert=True)
        return

    country_name = country.name_ru if lang == "ru" else country.name_en
    text = localization.t(
        lang,
        "tariff_detail",
        flag=country_flag(country_code),
        country=country_name,
        data=format_data_amount(tariff["data_amount_gb"], lang),
        days=tariff["validity_days"],
        stars=tariff["retail_price_stars"],
        usd=format_usd(tariff["retail_price_usd"]),
    )

    await callback.message.edit_text(
        text,
        reply_markup=tariff_detail_keyboard(
            localization=localization,
            lang=lang,
            country_code=country_code,
            package_code=package_code,
            continent_key=continent_key,
            page=int(page_s),
        ),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("crypto:"))
async def crypto_disabled(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    localization = get_services()["localization"]
    await callback.answer(localization.t(lang, "crypto_unavailable"), show_alert=True)


@router.callback_query(F.data.startswith("pay:"))
async def pay_stars(callback: CallbackQuery) -> None:
    _, country_code, package_code = callback.data.split(":", 2)
    services = get_services()
    localization = services["localization"]
    catalog = services["catalog_service"]
    order_service = services["order_service"]
    settings = services["settings"]

    lang = await _lang(callback)

    if not settings.stars_payment_enabled:
        await callback.answer(localization.t(lang, "payment_disabled"), show_alert=True)
        return

    shown_tariff = await catalog.get_tariff_by_code(country_code, package_code, force_fresh=False)
    fresh_tariff = await catalog.get_tariff_by_code(country_code, package_code, force_fresh=True)

    if not fresh_tariff:
        await callback.answer(localization.t(lang, "no_tariffs"), show_alert=True)
        return

    shown_stars = shown_tariff["retail_price_stars"] if shown_tariff else None
    fresh_stars = fresh_tariff["retail_price_stars"]

    if shown_stars is not None and shown_stars != fresh_stars:
        kb = InlineKeyboardBuilder()
        kb.button(text=localization.t(lang, "confirm_price"), callback_data=f"payconfirm:{country_code}:{package_code}")
        kb.button(text=localization.t(lang, "back"), callback_data="menu:buy")
        kb.adjust(1)
        await callback.message.answer(
            localization.t(
                lang,
                "price_updated",
                stars=fresh_tariff["retail_price_stars"],
                usd=format_usd(fresh_tariff["retail_price_usd"]),
            ),
            reply_markup=kb.as_markup(),
        )
        await callback.answer()
        return

    await _send_invoice(callback, fresh_tariff)


@router.callback_query(F.data.startswith("payconfirm:"))
async def pay_confirm(callback: CallbackQuery) -> None:
    _, country_code, package_code = callback.data.split(":", 2)
    catalog = get_services()["catalog_service"]
    lang = await _lang(callback)
    localization = get_services()["localization"]

    fresh_tariff = await catalog.get_tariff_by_code(country_code, package_code, force_fresh=True)
    if not fresh_tariff:
        await callback.answer(localization.t(lang, "no_tariffs"), show_alert=True)
        return

    await _send_invoice(callback, fresh_tariff)


async def _send_invoice(callback: CallbackQuery, tariff: dict) -> None:
    services = get_services()
    localization = services["localization"]
    order_service = services["order_service"]
    catalog = services["catalog_service"]

    lang = await _lang(callback)
    country = catalog.get_country_by_code(tariff["country_code"])
    country_name = country.name_ru if (country and lang == "ru") else (country.name_en if country else tariff["country_code"])

    order = await order_service.create_pending_order(callback.from_user.id, tariff)

    await callback.message.answer_invoice(
        title=localization.t(lang, "invoice_title"),
        description=localization.t(
            lang,
            "invoice_description",
            country=country_name,
            gb=format_data_gb(tariff["data_amount_gb"]),
            days=tariff["validity_days"],
        ),
        payload=order.order_ref,
        currency="XTR",
        prices=[LabeledPrice(label="eSIM", amount=tariff["retail_price_stars"])],
    )
    await callback.answer()
