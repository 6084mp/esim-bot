from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Final

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_chat_id: int
    esim_access_code: str
    esim_secret_key: str
    star_to_usd: float


POPULAR_COUNTRIES: Final[list[dict[str, str]]] = [
    {"code": "US", "name_en": "United States", "name_ru": "США", "emoji": "🇺🇸"},
    {"code": "TR", "name_en": "Turkey", "name_ru": "Турция", "emoji": "🇹🇷"},
    {"code": "TH", "name_en": "Thailand", "name_ru": "Таиланд", "emoji": "🇹🇭"},
]

TOP_COUNTRIES: Final[set[str]] = {
    "US",
    "GB",
    "DE",
    "FR",
    "IT",
    "ES",
    "TR",
    "AE",
    "TH",
    "JP",
    "KR",
}

MID_COUNTRIES: Final[set[str]] = {
    "PL",
    "CZ",
    "AT",
    "CH",
    "SE",
    "NO",
    "DK",
    "PT",
    "NL",
    "BE",
    "GR",
    "HU",
    "ID",
    "MY",
    "SG",
    "VN",
}


def get_settings() -> Settings:
    bot_token = os.getenv("BOT_TOKEN", "").strip()
    admin_chat_id_raw = os.getenv("ADMIN_CHAT_ID", "0").strip()
    esim_access_code = os.getenv("ESIM_ACCESS_CODE", "").strip()
    esim_secret_key = os.getenv("ESIM_SECRET_KEY", "").strip()
    star_to_usd = float(os.getenv("STAR_TO_USD", "0.013").strip())

    if not bot_token:
        raise ValueError("BOT_TOKEN is required")
    if not esim_access_code or not esim_secret_key:
        raise ValueError("ESIM_ACCESS_CODE and ESIM_SECRET_KEY are required")

    try:
        admin_chat_id = int(admin_chat_id_raw)
    except ValueError as exc:
        raise ValueError("ADMIN_CHAT_ID must be an integer") from exc

    return Settings(
        bot_token=bot_token,
        admin_chat_id=admin_chat_id,
        esim_access_code=esim_access_code,
        esim_secret_key=esim_secret_key,
        star_to_usd=star_to_usd,
    )
