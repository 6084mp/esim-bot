from __future__ import annotations

from locales.en import TEXTS as EN_TEXTS
from locales.ru import TEXTS as RU_TEXTS


class LocalizationService:
    def __init__(self, default_language: str = "en") -> None:
        self.default_language = default_language if default_language in {"en", "ru"} else "en"
        self._texts = {
            "en": EN_TEXTS,
            "ru": RU_TEXTS,
        }

    def t(self, lang: str | None, key: str, **kwargs: object) -> str:
        lang_code = lang if lang in {"en", "ru"} else self.default_language
        text = self._texts.get(lang_code, {}).get(key)
        if text is None:
            text = self._texts["en"].get(key, key)
        if kwargs:
            return text.format(**kwargs)
        return text
