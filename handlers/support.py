from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, ForceReply, Message

from services.runtime_context import get_services

from keyboards.common import support_keyboard

router = Router()

def _is_support_text(value: str | None) -> bool:
    if not value:
        return False
    return ("Support" in value) or ("Поддержка" in value)


PROMPT_TTL_SECONDS = 3600


async def _lang(obj) -> str:
    services = get_services()
    order_service = services["order_service"]
    settings = services["settings"]
    return await order_service.get_user_language(obj.from_user.id, settings.default_language)


async def _show_support(target, lang: str) -> None:
    services = get_services()
    localization = services["localization"]
    settings = services["settings"]
    support_username = (settings.support_username or "").strip()
    if support_username and support_username != "@support":
        text = localization.t(lang, "support_text", username=support_username)
    else:
        text = localization.t(lang, "support_text_inbot")
    await target.answer(
        text,
        reply_markup=support_keyboard(localization, lang),
    )


def _extract_text(message: Message) -> str | None:
    text = (message.text or "").strip()
    if text:
        return text
    caption = (message.caption or "").strip()
    if caption:
        return caption
    return None


def _is_support_user_input(message: Message) -> bool:
    if message.from_user is None:
        return False
    if message.chat.type != "private":
        return False
    services = get_services()
    settings = services["settings"]
    cache = services["cache"]
    if message.from_user.id == settings.admin_chat_id:
        return False
    prompt_id = cache.get(f"support_prompt:{message.from_user.id}")
    if not prompt_id:
        return False
    return bool(message.reply_to_message and message.reply_to_message.message_id == int(prompt_id))


def _is_support_admin_input(message: Message) -> bool:
    services = get_services()
    settings = services["settings"]
    if message.chat.id != settings.admin_chat_id:
        return False
    if message.reply_to_message:
        return True
    return bool((message.text or "").startswith("/reply "))


async def _forward_to_admin(user_message: Message, lang: str, text: str) -> None:
    services = get_services()
    localization = services["localization"]
    settings = services["settings"]
    support_service = services["support_service"]

    thread = await support_service.get_or_create_open_thread(
        telegram_id=user_message.from_user.id,
        username=user_message.from_user.username,
        first_name=user_message.from_user.first_name,
        language=lang,
    )
    await support_service.add_message(thread.thread_ref, "user", text)

    admin_msg = await user_message.bot.send_message(
        settings.admin_chat_id,
        localization.t(
            "ru",
            "support_admin_new",
            thread_ref=thread.thread_ref,
            user_id=user_message.from_user.id,
            username=user_message.from_user.username or "—",
            first_name=user_message.from_user.first_name or "—",
            lang=lang,
            text=text,
        ),
    )
    await support_service.bind_admin_message(admin_msg.message_id, thread.thread_ref)

    await user_message.answer(localization.t(lang, "support_sent", thread_ref=thread.thread_ref))


@router.message(F.text.func(_is_support_text))
async def support_message(message: Message) -> None:
    lang = await _lang(message)
    await _show_support(message, lang)


@router.callback_query(F.data == "support:open")
async def support_callback(callback: CallbackQuery) -> None:
    lang = await _lang(callback)
    await _show_support(callback.message, lang)
    await callback.answer()


@router.callback_query(F.data == "support:compose")
async def support_compose(callback: CallbackQuery) -> None:
    services = get_services()
    localization = services["localization"]
    cache = services["cache"]
    lang = await _lang(callback)

    prompt = await callback.message.answer(
        localization.t(lang, "support_prompt"),
        reply_markup=ForceReply(selective=True),
    )
    cache.set(f"support_prompt:{callback.from_user.id}", prompt.message_id, PROMPT_TTL_SECONDS)
    await callback.answer()


@router.message(_is_support_user_input)
async def support_user_message(message: Message) -> None:
    services = get_services()
    cache = services["cache"]

    prompt_id = cache.get(f"support_prompt:{message.from_user.id}")
    if not prompt_id:
        return

    text = _extract_text(message)
    if not text:
        return

    lang = await _lang(message)
    await _forward_to_admin(message, lang, text)
    cache.delete(f"support_prompt:{message.from_user.id}")


@router.message(_is_support_admin_input)
async def support_admin_reply(message: Message) -> None:
    services = get_services()
    localization = services["localization"]
    support_service = services["support_service"]

    text = _extract_text(message)
    if not text:
        return

    admin_lang = "ru"

    thread_ref: str | None = None
    if message.reply_to_message:
        thread_ref = await support_service.thread_ref_by_admin_message(message.reply_to_message.message_id)

    if not thread_ref and text.startswith("/reply "):
        parts = text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer(localization.t(admin_lang, "support_admin_bad_format"))
            return
        thread_ref = parts[1].strip().upper()
        text = parts[2].strip()

    if not thread_ref:
        return

    user_id = await support_service.user_id_by_thread_ref(thread_ref)
    if not user_id:
        await message.answer(localization.t(admin_lang, "support_admin_unknown_thread"))
        return

    user_lang = await support_service.thread_language_by_ref(thread_ref)
    try:
        await message.bot.send_message(
            user_id,
            localization.t(user_lang, "support_user_reply_prefix", thread_ref=thread_ref, text=text),
        )
    except Exception:
        await message.answer(localization.t(admin_lang, "support_delivery_failed"))
        return

    await support_service.add_message(thread_ref, "admin", text)
    admin_echo = await message.answer(localization.t(admin_lang, "support_admin_sent", thread_ref=thread_ref))
    await support_service.bind_admin_message(admin_echo.message_id, thread_ref)
