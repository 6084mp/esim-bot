from __future__ import annotations

import asyncio
import json

from aiogram import F, Bot, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.esimaccess import EsimAccessClient
from config import Settings
from database.models import Order
from handlers.delivery import deliver_paid_order
from handlers.start import get_user_language
from keyboards.main_menu import confirm_price_keyboard, main_menu_keyboard
from services.catalog_service import CatalogService
from utils.i18n import t


router = Router()


async def _send_invoice(
    bot: Bot,
    chat_id: int,
    lang: str,
    package: dict,
) -> None:
    payload = {
        "country": package["country"],
        "package_code": package["code"],
        "data_gb": package["data_gb"],
        "days": package["days"],
        "wholesale_price": package["wholesale_price"],
        "retail_price": package["retail_price"],
        "stars_amount": package["stars_amount"],
    }
    await bot.send_invoice(
        chat_id=chat_id,
        title=t(lang, "invoice_title"),
        description=t(lang, "invoice_desc"),
        payload=json.dumps(payload, separators=(",", ":")),
        currency="XTR",
        prices=[LabeledPrice(label=t(lang, "invoice_title"), amount=package["stars_amount"])],
        provider_token="",
    )


@router.callback_query(F.data.startswith("pay:"))
async def pay_now(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
    catalog_service: CatalogService,
    bot: Bot,
) -> None:
    _, country_code, package_code = callback.data.split(":", 2)
    lang = await get_user_language(session_factory, callback.from_user.id)
    data = await state.get_data()
    selected = data.get("selected_package")

    try:
        fresh_packages = await catalog_service.get_country_packages(country_code, use_cache=False)
    except Exception:
        await callback.message.edit_text(t(lang, "pay_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    fresh_package = catalog_service.find_by_code(fresh_packages, package_code)
    if not fresh_package:
        await callback.message.edit_text(t(lang, "no_packages"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    if selected and (
        selected.get("retail_price") != fresh_package["retail_price"]
        or selected.get("stars_amount") != fresh_package["stars_amount"]
    ):
        await state.update_data(confirm_package=fresh_package)
        await callback.message.edit_text(
            t(
                lang,
                "updated_price",
                old_usd=selected["retail_price"],
                new_usd=fresh_package["retail_price"],
                old_stars=selected["stars_amount"],
                new_stars=fresh_package["stars_amount"],
            ),
            reply_markup=confirm_price_keyboard(country_code, package_code, lang),
        )
        await callback.answer()
        return

    try:
        await _send_invoice(bot, callback.from_user.id, lang, fresh_package)
        await callback.answer()
    except Exception:
        await callback.message.edit_text(t(lang, "pay_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()


@router.callback_query(F.data.startswith("payconfirm:"))
async def pay_confirm(
    callback: CallbackQuery,
    state: FSMContext,
    session_factory: async_sessionmaker,
    bot: Bot,
) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    data = await state.get_data()
    package = data.get("confirm_package")

    if not package:
        await callback.message.edit_text(t(lang, "pay_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()
        return

    try:
        await _send_invoice(bot, callback.from_user.id, lang, package)
        await callback.answer()
    except Exception:
        await callback.message.edit_text(t(lang, "pay_error"), reply_markup=main_menu_keyboard(lang))
        await callback.answer()


@router.pre_checkout_query()
async def pre_checkout(pre_checkout_query: PreCheckoutQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, pre_checkout_query.from_user.id)
    try:
        json.loads(pre_checkout_query.invoice_payload)
        await pre_checkout_query.answer(ok=True)
    except Exception:
        await pre_checkout_query.answer(ok=False, error_message=t(lang, "precheckout_error"))


@router.message(F.successful_payment)
async def successful_payment(
    message: Message,
    session_factory: async_sessionmaker,
    api_client: EsimAccessClient,
    settings: Settings,
    bot: Bot,
) -> None:
    lang = await get_user_language(session_factory, message.from_user.id)
    payload = json.loads(message.successful_payment.invoice_payload)

    async with session_factory() as session:
        order = Order(
            telegram_id=message.from_user.id,
            package_code=payload["package_code"],
            country=payload["country"],
            data_amount=float(payload["data_gb"]),
            days=int(payload["days"]),
            wholesale_price=float(payload["wholesale_price"]),
            retail_price=float(payload["retail_price"]),
            stars_amount=int(payload["stars_amount"]),
            payment_status="paid",
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)

    await message.answer(t(lang, "payment_success"))

    asyncio.create_task(
        deliver_paid_order(
            bot=bot,
            api_client=api_client,
            session_factory=session_factory,
            admin_chat_id=settings.admin_chat_id,
            order_id=order.id,
            telegram_id=message.from_user.id,
            package_code=payload["package_code"],
            user_lang=lang,
        )
    )
