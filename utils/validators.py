from __future__ import annotations


def normalize_lang(lang: str | None, default: str = "en") -> str:
    if not lang:
        return default
    lang = lang.lower().strip()
    return lang if lang in {"en", "ru"} else default
