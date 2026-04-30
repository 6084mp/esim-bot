from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str) -> AsyncEngine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        # Reduce "database is locked" errors under concurrent async access.
        connect_args = {"timeout": 30}
    return create_async_engine(database_url, future=True, echo=False, connect_args=connect_args)


def get_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_db(engine: AsyncEngine) -> None:
    from database import models  # noqa: F401

    async with engine.begin() as conn:
        if engine.url.get_backend_name().startswith("sqlite"):
            await conn.execute(text("PRAGMA journal_mode=WAL;"))
            await conn.execute(text("PRAGMA synchronous=NORMAL;"))
            await conn.execute(text("PRAGMA busy_timeout=30000;"))
        await conn.run_sync(Base.metadata.create_all)
