from __future__ import annotations


def country_flag(country_code: str) -> str:
    code = (country_code or "").strip().upper()
    if code == "GL":
        return "🌍"
    if len(code) != 2 or not code.isalpha():
        return "🏳️"
    return "".join(chr(ord(ch) + 127397) for ch in code)
