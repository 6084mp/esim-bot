from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    language: Mapped[str] = mapped_column(String(2), nullable=False, default="en")
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=False), default=dt.datetime.utcnow, nullable=False)


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    order_ref: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    supplier_order_no: Mapped[str | None] = mapped_column(String(128), nullable=True)

    package_code: Mapped[str] = mapped_column(String(128), nullable=False)
    country_code: Mapped[str] = mapped_column(String(8), nullable=False)
    country_name: Mapped[str] = mapped_column(String(128), nullable=False)

    data_amount_gb: Mapped[float] = mapped_column(Float, nullable=False)
    validity_days: Mapped[int] = mapped_column(Integer, nullable=False)

    wholesale_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    retail_price_usd: Mapped[float] = mapped_column(Float, nullable=False)
    retail_price_stars: Mapped[int] = mapped_column(Integer, nullable=False)

    payment_system: Mapped[str] = mapped_column(String(32), nullable=False)
    payment_status: Mapped[str] = mapped_column(String(32), nullable=False)
    fulfillment_status: Mapped[str] = mapped_column(String(32), nullable=False)

    esim_iccid: Mapped[str | None] = mapped_column(String(128), nullable=True)
    esim_qr_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    esim_smdp: Mapped[str | None] = mapped_column(String(256), nullable=True)
    esim_activation_code: Mapped[str | None] = mapped_column(String(256), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=False), default=dt.datetime.utcnow, nullable=False)
    paid_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


Index("ix_orders_telegram_created", Order.telegram_id, Order.created_at.desc())


class CachedTariff(Base):
    __tablename__ = "cached_tariffs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    country_code: Mapped[str] = mapped_column(String(8), unique=True, index=True, nullable=False)
    payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=False), default=dt.datetime.utcnow, nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=False), nullable=False)
