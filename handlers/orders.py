from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from keyboards.common import post_delivery_keyboard
from utils.formatters import format_data_gb

router = Router()

ORDER_TEXTS = {"My Orders", "Мои заказы"}


async def _lang(obj) -> str:
    services = obj.bot["services"]
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


async def _show_orders(target, user_id: int, lang: str) -> None:
    services = target.bot["services"]
    order_service = services["order_service"]
    localization = services["localization"]

    orders = await order_service.list_recent_orders(user_id, limit=10)
    if not orders:
        await target.answer(localization.t(lang, "orders_empty"))
        return

    await target.answer(localization.t(lang, "orders_title"))
    for order in orders:
        text = localization.t(
            lang,
            "order_line",
            order_ref=order.order_ref,
            country=order.country_name,
            gb=format_data_gb(order.data_amount_gb),
            days=order.validity_days,
            stars=order.retail_price_stars,
            payment=localization.t(lang, f"status_{order.payment_status}"),
            delivery=localization.t(lang, f"ful_{order.fulfillment_status}"),
        )
        kb = InlineKeyboardBuilder()
        kb.button(text=localization.t(lang, "order_view"), callback_data=f"order:{order.order_ref}")
        await target.answer(text, reply_markup=kb.as_markup())


@router.message(F.text.in_(ORDER_TEXTS))
async def orders_message(message: Message) -> None:
    lang = await _lang(message)
    await _show_orders(message, message.from_user.id, lang)


@router.callback_query(F.data == "menu:orders")
async def orders_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _show_orders(callback.message, callback.from_user.id, lang)
    await callback.answer()


@router.callback_query(F.data.startswith("order:"))
async def open_order(callback: CallbackQuery) -> None:
    _, order_ref = callback.data.split(":", 1)
    services = callback.message.bot["services"]
    order_service = services["order_service"]
    localization = services["localization"]

    lang = await _lang(callback)
    order = await order_service.get_order_by_ref(order_ref)
    if not order or order.telegram_id != callback.from_user.id:
        await callback.answer(localization.t(lang, "order_not_found"), show_alert=True)
        return

    if order.fulfillment_status == "delivered":
        details = localization.t(
            lang,
            "delivery_success",
            order_ref=order.order_ref,
            country=order.country_name,
            gb=format_data_gb(order.data_amount_gb),
            days=order.validity_days,
            iccid=order.esim_iccid or "-",
            smdp=order.esim_smdp or "-",
            code=order.esim_activation_code or "-",
        )
        if order.esim_qr_url:
            await callback.message.answer_photo(order.esim_qr_url, caption=details)
        else:
            await callback.message.answer(details)
        await callback.message.answer(
            localization.t(lang, "install_text"),
            reply_markup=post_delivery_keyboard(localization, lang),
        )
    else:
        await callback.answer(localization.t(lang, f"ful_{order.fulfillment_status}"), show_alert=True)
        return

    await callback.answer()
