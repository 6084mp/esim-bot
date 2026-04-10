from __future__ import annotations

from config import MID_COUNTRIES, TOP_COUNTRIES


class PricingService:
    def __init__(self, star_to_usd: float) -> None:
        self.star_to_usd = star_to_usd

    def country_multiplier(self, country_code: str) -> float:
        code = country_code.upper()
        if code in TOP_COUNTRIES:
            return 1.30
        if code in MID_COUNTRIES:
            return 1.40
        return 1.55

    def retail_price_usd(self, wholesale_price: float, country_code: str) -> float:
        multiplier = self.country_multiplier(country_code)
        retail = max(wholesale_price * multiplier, wholesale_price + 1)
        return round(retail, 2)

    def usd_to_stars(self, usd: float) -> int:
        stars = round((usd / self.star_to_usd) / 10) * 10
        return max(stars, 10)
