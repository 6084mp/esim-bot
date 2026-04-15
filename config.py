from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    bot_token: str
    admin_chat_id: int
    supplier_access_code: str
    supplier_secret_key: str
    support_username: str
    stars_payment_enabled: bool
    crypto_payment_enabled: bool
    cache_ttl_seconds: int
    default_language: str
    database_url: str
    supplier_base_url: str
    stars_usd_rate: float


def _get_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _require(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def get_settings() -> Settings:
    default_language = os.getenv("DEFAULT_LANGUAGE", "en").strip().lower() or "en"
    if default_language not in {"en", "ru"}:
        default_language = "en"

    return Settings(
        bot_token=_require("BOT_TOKEN"),
        admin_chat_id=int(_require("ADMIN_CHAT_ID")),
        supplier_access_code=_require("SUPPLIER_ACCESS_CODE"),
        supplier_secret_key=_require("SUPPLIER_SECRET_KEY"),
        support_username=os.getenv("SUPPORT_USERNAME", "@support").strip() or "@support",
        stars_payment_enabled=_get_bool("STARS_PAYMENT_ENABLED", True),
        crypto_payment_enabled=_get_bool("CRYPTO_PAYMENT_ENABLED", False),
        cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "600")),
        default_language=default_language,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///esim_bot.db").strip(),
        supplier_base_url=os.getenv("SUPPLIER_BASE_URL", "https://api.esimaccess.com").strip().rstrip("/"),
        stars_usd_rate=float(os.getenv("STAR_TO_USD", "0.013")),
    )
