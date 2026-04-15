from __future__ import annotations


class PricingService:
    TOP_COUNTRIES = {"US", "GB", "DE", "FR", "IT", "ES", "TR", "TH", "JP", "AE"}
    RARE_COUNTRIES = {
        "AO", "BJ", "BF", "BI", "CM", "CF", "TD", "CD", "CG", "ER", "GA", "GM", "GN", "GW",
        "LS", "LR", "MG", "MW", "ML", "MR", "MZ", "NE", "RW", "SL", "SO", "SS", "SD", "TG", "UG", "ZM",
    }

    MULTIPLIERS = {
        "top": 1.30,
        "mid": 1.40,
        "rare": 1.55,
        "global": 1.35,
    }

    def __init__(self, stars_usd_rate: float = 0.013) -> None:
        self.stars_usd_rate = stars_usd_rate

    def country_group(self, country_code: str) -> str:
        code = (country_code or "").upper()
        if code in {"GL", "GLOBAL"}:
            return "global"
        if code in self.TOP_COUNTRIES:
            return "top"
        if code in self.RARE_COUNTRIES:
            return "rare"
        return "mid"

    def calculate_retail_usd(self, wholesale_usd: float, country_code: str) -> float:
        group = self.country_group(country_code)
        multiplier = self.MULTIPLIERS[group]
        retail = max(wholesale_usd * multiplier, wholesale_usd + 1.0)
        return round(retail, 2)

    def usd_to_stars(self, usd_amount: float) -> int:
        raw_stars = usd_amount / self.stars_usd_rate
        stars = round(raw_stars / 10) * 10
        return max(1, int(stars))

    @staticmethod
    def duration_weight(validity_days: int) -> float:
        if validity_days >= 30:
            return 1.0
        if validity_days >= 15:
            return 0.95
        if validity_days >= 7:
            return 0.90
        return 0.80

    def calculate_value_score(self, data_gb: float, retail_price_usd: float, validity_days: int) -> float:
        if retail_price_usd <= 0:
            return 0.0
        weight = self.duration_weight(validity_days)
        return (data_gb / retail_price_usd) * weight
