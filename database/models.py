from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    language: Mapped[str] = mapped_column(String(2), default="en")
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, index=True)
    package_code: Mapped[str] = mapped_column(String(128))
    country: Mapped[str] = mapped_column(String(8))
    data_amount: Mapped[float] = mapped_column(Float)
    days: Mapped[int] = mapped_column(Integer)
    wholesale_price: Mapped[float] = mapped_column(Float)
    retail_price: Mapped[float] = mapped_column(Float)
    stars_amount: Mapped[int] = mapped_column(Integer)
    payment_status: Mapped[str] = mapped_column(String(32), default="pending")
    esim_qr_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    activation_code: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
