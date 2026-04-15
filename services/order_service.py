from __future__ import annotations

import datetime as dt
import random
import string
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import Order, User


class OrderService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _order_ref() -> str:
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"ESM{dt.datetime.utcnow():%y%m%d%H%M%S}{suffix}"

    async def get_or_create_user(self, telegram_id: int, username: str | None, first_name: str | None, default_language: str) -> User:
        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user:
                if username != user.username or first_name != user.first_name:
                    user.username = username
                    user.first_name = first_name
                    await session.commit()
                return user

            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                language=default_language,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def set_user_language(self, telegram_id: int, language: str) -> None:
        async with self.session_factory() as session:
            user = await session.scalar(select(User).where(User.telegram_id == telegram_id))
            if user:
                user.language = language
                await session.commit()

    async def get_user_language(self, telegram_id: int, default_language: str) -> str:
        async with self.session_factory() as session:
            user = await session.scalar(select(User.language).where(User.telegram_id == telegram_id))
            return user or default_language

    async def create_pending_order(self, telegram_id: int, tariff: dict[str, Any]) -> Order:
        async with self.session_factory() as session:
            order = Order(
                order_ref=self._order_ref(),
                telegram_id=telegram_id,
                package_code=tariff["package_code"],
                country_code=tariff["country_code"],
                country_name=tariff["country_name_en"],
                data_amount_gb=float(tariff["data_amount_gb"]),
                validity_days=int(tariff["validity_days"]),
                wholesale_price_usd=float(tariff["wholesale_price_usd"]),
                retail_price_usd=float(tariff["retail_price_usd"]),
                retail_price_stars=int(tariff["retail_price_stars"]),
                payment_system="stars",
                payment_status="pending",
                fulfillment_status="waiting_payment",
            )
            session.add(order)
            await session.commit()
            await session.refresh(order)
            return order

    async def get_order_by_ref(self, order_ref: str) -> Order | None:
        async with self.session_factory() as session:
            return await session.scalar(select(Order).where(Order.order_ref == order_ref))

    async def list_recent_orders(self, telegram_id: int, limit: int = 10) -> list[Order]:
        async with self.session_factory() as session:
            result = await session.scalars(
                select(Order)
                .where(Order.telegram_id == telegram_id)
                .order_by(desc(Order.created_at))
                .limit(limit)
            )
            return list(result)

    async def set_order_paid(self, order_ref: str) -> Order | None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.order_ref == order_ref))
            if not order:
                return None
            order.payment_status = "paid"
            order.paid_at = dt.datetime.utcnow()
            order.fulfillment_status = "provisioning"
            await session.commit()
            await session.refresh(order)
            return order

    async def set_order_payment_failed(self, order_ref: str, error_message: str) -> None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.order_ref == order_ref))
            if not order:
                return
            order.payment_status = "failed"
            order.last_error = error_message
            await session.commit()

    async def set_supplier_order_no(self, order_ref: str, supplier_order_no: str) -> None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.order_ref == order_ref))
            if not order:
                return
            order.supplier_order_no = supplier_order_no
            await session.commit()

    async def set_order_delivered(self, order_ref: str, details: dict[str, Any]) -> Order | None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.order_ref == order_ref))
            if not order:
                return None
            order.fulfillment_status = "delivered"
            order.delivered_at = dt.datetime.utcnow()
            order.esim_iccid = details.get("iccid")
            order.esim_qr_url = details.get("qr_url")
            order.esim_smdp = details.get("smdp")
            order.esim_activation_code = details.get("activation_code")
            await session.commit()
            await session.refresh(order)
            return order

    async def set_order_fulfillment_failed(self, order_ref: str, error_message: str) -> Order | None:
        async with self.session_factory() as session:
            order = await session.scalar(select(Order).where(Order.order_ref == order_ref))
            if not order:
                return None
            order.fulfillment_status = "failed"
            order.last_error = error_message
            await session.commit()
            await session.refresh(order)
            return order
