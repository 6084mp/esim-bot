from __future__ import annotations


def format_data_gb(value: float) -> str:
    if value >= 10:
        return f"{value:.0f}"
    if value >= 1:
        return f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{value:.2f}".rstrip("0").rstrip(".")


def format_data_amount(value_gb: float, lang: str = "en") -> str:
    if value_gb < 1:
        mb = int(round(value_gb * 1024))
        unit = "МБ" if lang == "ru" else "MB"
        return f"{mb} {unit}"
    unit = "ГБ" if lang == "ru" else "GB"
    return f"{format_data_gb(value_gb)} {unit}"


def format_usd(value: float) -> str:
    return f"{value:.2f}"
