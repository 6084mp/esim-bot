from __future__ import annotations

import datetime as dt
import random
import string

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from database.models import SupportAdminMap, SupportMessage, SupportThread


class SupportService:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self.session_factory = session_factory

    @staticmethod
    def _thread_ref() -> str:
        suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
        return f"SUP{dt.datetime.utcnow():%y%m%d%H%M%S}{suffix}"

    async def get_or_create_open_thread(
        self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        language: str,
    ) -> SupportThread:
        async with self.session_factory() as session:
            thread = await session.scalar(
                select(SupportThread)
                .where(SupportThread.user_telegram_id == telegram_id, SupportThread.status == "open")
                .order_by(desc(SupportThread.updated_at))
            )
            if thread:
                thread.username = username
                thread.first_name = first_name
                thread.language = language
                thread.updated_at = dt.datetime.utcnow()
                await session.commit()
                await session.refresh(thread)
                return thread

            thread = SupportThread(
                thread_ref=self._thread_ref(),
                user_telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                language=language,
                status="open",
            )
            session.add(thread)
            await session.commit()
            await session.refresh(thread)
            return thread

    async def add_message(self, thread_ref: str, sender_role: str, text: str) -> None:
        async with self.session_factory() as session:
            message = SupportMessage(
                thread_ref=thread_ref,
                sender_role=sender_role,
                text=text,
            )
            session.add(message)

            thread = await session.scalar(select(SupportThread).where(SupportThread.thread_ref == thread_ref))
            if thread:
                thread.updated_at = dt.datetime.utcnow()

            await session.commit()

    async def bind_admin_message(self, admin_message_id: int, thread_ref: str) -> None:
        async with self.session_factory() as session:
            row = await session.scalar(select(SupportAdminMap).where(SupportAdminMap.admin_message_id == admin_message_id))
            if row:
                row.thread_ref = thread_ref
            else:
                session.add(SupportAdminMap(admin_message_id=admin_message_id, thread_ref=thread_ref))
            await session.commit()

    async def thread_ref_by_admin_message(self, admin_message_id: int) -> str | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(SupportAdminMap.thread_ref).where(SupportAdminMap.admin_message_id == admin_message_id)
            )

    async def user_id_by_thread_ref(self, thread_ref: str) -> int | None:
        async with self.session_factory() as session:
            return await session.scalar(
                select(SupportThread.user_telegram_id).where(SupportThread.thread_ref == thread_ref)
            )

    async def thread_language_by_ref(self, thread_ref: str) -> str:
        async with self.session_factory() as session:
            lang = await session.scalar(
                select(SupportThread.language).where(SupportThread.thread_ref == thread_ref)
            )
            return lang or "en"
