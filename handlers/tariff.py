from __future__ import annotations

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
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


def _is_free_user(user_id: int, settings) -> bool:
    return user_id == settings.admin_chat_id or user_id in settings.free_order_user_ids


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

    if _is_free_user(callback.from_user.id, settings):
        await _process_free_order(callback, fresh_only=True, country_code=country_code, package_code=package_code)
        return

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

    settings = get_services()["settings"]
    if _is_free_user(callback.from_user.id, settings):
        await _process_free_order(callback, fresh_tariff=fresh_tariff)
        return

    await _send_invoice(callback, fresh_tariff)


async def _process_free_order(
    callback: CallbackQuery,
    fresh_only: bool = False,
    country_code: str | None = None,
    package_code: str | None = None,
    fresh_tariff: dict | None = None,
) -> None:
    services = get_services()
    localization = services["localization"]
    order_service = services["order_service"]
    delivery_service = services["delivery_service"]
    catalog = services["catalog_service"]
    settings = services["settings"]

    if not _is_free_user(callback.from_user.id, settings):
        return

    lang = await _lang(callback)

    tariff = fresh_tariff
    if tariff is None:
        if not country_code or not package_code:
            await callback.answer(localization.t(lang, "no_tariffs"), show_alert=True)
            return
        tariff = await catalog.get_tariff_by_code(country_code, package_code, force_fresh=True)
        if not tariff:
            await callback.answer(localization.t(lang, "no_tariffs"), show_alert=True)
            return

    order = await order_service.create_pending_order(callback.from_user.id, tariff)
    paid_order = await order_service.set_order_paid(order.order_ref)
    if not paid_order:
        await callback.answer(localization.t(lang, "unknown_error"), show_alert=True)
        return

    await callback.message.answer(localization.t(lang, "payment_test_mode"))
    await callback.message.answer(localization.t(lang, "delivery_wait"))
    await callback.answer()
    import asyncio
    asyncio.create_task(delivery_service.process_paid_order(callback.bot, paid_order.order_ref, lang))


async def _send_invoice(callback: CallbackQuery, tariff: dict) -> None:
    services = get_services()
    localization = services["localization"]
    order_service = services["order_service"]
    catalog = services["catalog_service"]
    settings = services["settings"]

    lang = await _lang(callback)

    wholesale = float(tariff["wholesale_price_usd"])
    retail = float(tariff["retail_price_usd"])
    if retail <= wholesale:
        await callback.answer(localization.t(lang, "pricing_blocked"), show_alert=True)
        try:
            await callback.bot.send_message(
                settings.admin_chat_id,
                (
                    f"[pricing-hard-stop] user={callback.from_user.id} "
                    f"country={tariff.get('country_code')} package={tariff.get('package_code')} "
                    f"wholesale={wholesale:.4f} retail={retail:.4f}"
                ),
            )
        except Exception:
            pass
        return

    country = catalog.get_country_by_code(tariff["country_code"])
    country_name = country.name_ru if (country and lang == "ru") else (country.name_en if country else tariff["country_code"])

    order = await order_service.create_pending_order(callback.from_user.id, tariff)
    stars_amount = max(1, int(tariff["retail_price_stars"]))

    try:
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
            prices=[LabeledPrice(label="eSIM", amount=stars_amount)],
        )
        await callback.answer()
    except TelegramBadRequest as e:
        await callback.answer(localization.t(lang, "payment_provider_unavailable"), show_alert=True)
        try:
            await callback.bot.send_message(
                settings.admin_chat_id,
                (
                    "[stars-invoice-error] "
                    f"user={callback.from_user.id} "
                    f"order_ref={order.order_ref} "
                    f"country={tariff.get('country_code')} "
                    f"package={tariff.get('package_code')} "
                    f"stars={stars_amount} "
                    f"error={str(e)}"
                ),
            )
        except Exception:
            pass
