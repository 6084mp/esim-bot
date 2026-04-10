from __future__ import annotations

import asyncio

from aiogram import F, Bot, Router
from aiogram.types import CallbackQuery
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from api.esimaccess import EsimAccessClient
from database.models import Order
from handlers.start import get_user_language
from keyboards.main_menu import main_menu_keyboard, troubleshooting_keyboard
from utils.i18n import t


router = Router()


@router.callback_query(F.data == "menu:device")
async def device_compatibility(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await callback.message.edit_text(t(lang, "device_text"), reply_markup=troubleshooting_keyboard(lang))
    await callback.answer()


@router.callback_query(F.data == "help:internet")
async def internet_help(callback: CallbackQuery, session_factory: async_sessionmaker) -> None:
    lang = await get_user_language(session_factory, callback.from_user.id)
    await callback.message.edit_text(t(lang, "internet_help"), reply_markup=main_menu_keyboard(lang))
    await callback.answer()


async def _mark_order_failed(
    session_factory: async_sessionmaker,
    order_id: int,
) -> None:
    async with session_factory() as session:
        order = await session.scalar(select(Order).where(Order.id == order_id))
        if order:
            order.payment_status = "failed"
            await session.commit()


async def deliver_paid_order(
    *,
    bot: Bot,
    api_client: EsimAccessClient,
    session_factory: async_sessionmaker,
    admin_chat_id: int,
    order_id: int,
    telegram_id: int,
    package_code: str,
    user_lang: str,
) -> None:
    try:
        async with session_factory() as session:
            order = await session.scalar(select(Order).where(Order.id == order_id))
            if order:
                order.payment_status = "processing"
                await session.commit()

        buy_result = await api_client.purchase_esim(package_code=package_code, external_id=f"tg-{order_id}")
        provider_order_no = buy_result.get("provider_order_no")
        if not provider_order_no:
            raise RuntimeError("Provider order ID is missing")

        ready_detail: dict | None = None
        for _ in range(6):
            detail = await api_client.get_order_detail(provider_order_no)
            status = detail.get("status", "")
            if status in {"active", "completed", "success", "ready", "delivered"} and (
                detail.get("qr_url") or detail.get("activation_code")
            ):
                ready_detail = detail
                break
            await asyncio.sleep(10)

        if not ready_detail:
            raise RuntimeError("Provider did not return ready eSIM in time")

        qr_url = ready_detail.get("qr_url") or "-"
        activation_code = ready_detail.get("activation_code") or "-"
        instructions = ready_detail.get("instructions") or "Install via QR or activation code in device eSIM settings."

        async with session_factory() as session:
            order = await session.scalar(select(Order).where(Order.id == order_id))
            if order:
                order.payment_status = "fulfilled"
                order.esim_qr_url = qr_url
                order.activation_code = activation_code
                await session.commit()

        await bot.send_message(
            chat_id=telegram_id,
            text=t(
                user_lang,
                "delivery_done",
                qr=qr_url,
                code=activation_code,
                instructions=instructions,
            ),
        )

    except Exception:
        await _mark_order_failed(session_factory, order_id)
        await bot.send_message(chat_id=telegram_id, text=t(user_lang, "delivery_failed"))
        await bot.send_message(
            chat_id=admin_chat_id,
            text=t(user_lang, "admin_fail", order_id=order_id, telegram_id=telegram_id),
        )
