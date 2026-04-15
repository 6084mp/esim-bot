from __future__ import annotations

import asyncio
import logging

from aiogram import Bot

from api.supplier_client import SupplierAPIClient
from keyboards.common import post_delivery_keyboard
from services.localization_service import LocalizationService
from services.order_service import OrderService
from utils.formatters import format_data_gb

logger = logging.getLogger(__name__)


class DeliveryService:
    def __init__(
        self,
        supplier_client: SupplierAPIClient,
        order_service: OrderService,
        localization: LocalizationService,
        admin_chat_id: int,
    ) -> None:
        self.supplier_client = supplier_client
        self.order_service = order_service
        self.localization = localization
        self.admin_chat_id = admin_chat_id

    async def _notify_admin(self, bot: Bot, text: str) -> None:
        try:
            await bot.send_message(self.admin_chat_id, text)
        except Exception:
            logger.exception("Failed to notify admin")

    async def process_paid_order(self, bot: Bot, order_ref: str, user_lang: str) -> None:
        order = await self.order_service.get_order_by_ref(order_ref)
        if not order:
            return

        try:
            purchase = await self.supplier_client.purchase_esim(order.package_code, quantity=1, order_ref=order_ref)
            supplier_order_no = purchase.get("supplier_order_no") or ""
            if supplier_order_no:
                await self.order_service.set_supplier_order_no(order_ref, supplier_order_no)
            else:
                raise RuntimeError("Supplier did not return order number")

            details = None
            for attempt in range(6):
                details = await self.supplier_client.get_esim_order_details(supplier_order_no)
                if details.get("ready"):
                    break
                if attempt in {2, 4}:
                    await self._notify_admin(
                        bot,
                        f"[eSIM delay] {order_ref} still provisioning (attempt {attempt + 1}/6)",
                    )
                await asyncio.sleep(10)

            if not details or not details.get("ready"):
                raise RuntimeError("eSIM details are not ready after polling")

            saved = await self.order_service.set_order_delivered(order_ref, details)
            if not saved:
                return

            msg = self.localization.t(
                user_lang,
                "delivery_success",
                order_ref=saved.order_ref,
                country=saved.country_name,
                gb=format_data_gb(saved.data_amount_gb),
                days=saved.validity_days,
                iccid=saved.esim_iccid or "-",
                smdp=saved.esim_smdp or "-",
                code=saved.esim_activation_code or "-",
            )

            if saved.esim_qr_url:
                await bot.send_photo(saved.telegram_id, photo=saved.esim_qr_url, caption=msg)
            else:
                await bot.send_message(saved.telegram_id, msg)

            await bot.send_message(
                saved.telegram_id,
                self.localization.t(user_lang, "install_text"),
                reply_markup=post_delivery_keyboard(self.localization, user_lang),
            )
            await self._notify_admin(bot, f"[sale] Delivered order {saved.order_ref} ({saved.country_name})")

        except Exception as exc:
            logger.exception("Delivery failed for %s", order_ref)
            await self.order_service.set_order_fulfillment_failed(order_ref, str(exc))
            await bot.send_message(order.telegram_id, self.localization.t(user_lang, "delivery_failed"))
            await self._notify_admin(bot, f"[eSIM failed] {order_ref}: {exc}")
