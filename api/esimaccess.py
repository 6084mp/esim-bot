from __future__ import annotations

import re
from typing import Any

import aiohttp


class EsimAccessClient:
    BASE_URL = "https://api.esimaccess.com/api/v1/open"

    def __init__(self, access_code: str, secret_key: str, session: aiohttp.ClientSession | None = None) -> None:
        self._access_code = access_code
        self._secret_key = secret_key
        self._external_session = session
        self._session: aiohttp.ClientSession | None = session

    async def __aenter__(self) -> "EsimAccessClient":
        if self._session is None:
            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20))
        return self

    async def __aexit__(self, *_: Any) -> None:
        if self._session and not self._external_session:
            await self._session.close()
        self._session = self._external_session

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self._session is None:
            raise RuntimeError("EsimAccessClient session is not initialized")

        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "RT-AccessCode": self._access_code,
                "RT-SecretKey": self._secret_key,
                "Content-Type": "application/json",
            }
        )

        url = f"{self.BASE_URL}{path}"
        async with self._session.request(method, url, headers=headers, **kwargs) as response:
            payload = await response.json(content_type=None)
            if response.status >= 400:
                raise RuntimeError(f"Provider API error {response.status}: {payload}")
            if isinstance(payload, dict):
                return payload
            return {"data": payload}

    @staticmethod
    def _to_float(value: Any) -> float:
        if value is None:
            return 0.0
        if isinstance(value, (int, float)):
            return float(value)
        text = str(value).strip().replace(",", ".")
        match = re.search(r"-?\d+(?:\.\d+)?", text)
        if not match:
            return 0.0
        try:
            return float(match.group(0))
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _to_int(value: Any, default: int = 0) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _normalize_package(self, raw: dict[str, Any], fallback_country: str) -> dict[str, Any]:
        data_raw = raw.get("dataGb") or raw.get("data") or raw.get("volume") or raw.get("dataMb")
        data_gb = 0.0
        if isinstance(data_raw, str):
            text = data_raw.strip().lower()
            number = self._to_float(text)
            if "mb" in text and "gb" not in text:
                data_gb = number / 1024
            else:
                data_gb = number
        else:
            data_mb = self._to_float(raw.get("data") or raw.get("volume") or raw.get("dataMb"))
            data_gb = self._to_float(raw.get("dataGb") or (data_mb / 1024 if data_mb else 0))

        wholesale = self._to_float(
            raw.get("price")
            or raw.get("wholesalePrice")
            or raw.get("basePrice")
            or raw.get("salePrice")
            or raw.get("amount")
            or raw.get("cost")
        )

        days_raw = raw.get("validity") or raw.get("days") or raw.get("durationDays") or raw.get("duration")
        days = self._to_int(days_raw, default=0)
        if days <= 0 and isinstance(days_raw, str):
            days = self._to_int(self._to_float(days_raw), default=1)
        if days <= 0:
            days = 1

        return {
            "code": str(raw.get("packageCode") or raw.get("code") or raw.get("id") or ""),
            "country": str(raw.get("countryCode") or raw.get("country") or fallback_country).upper(),
            "title": str(raw.get("name") or raw.get("title") or "eSIM plan"),
            "data_gb": round(data_gb, 2),
            "days": days,
            "wholesale_price": wholesale,
            "popularity_score": self._to_float(raw.get("soldCount") or raw.get("orderCount") or raw.get("popularity")),
            "raw": raw,
        }

    async def get_countries(self, search: str | None = None) -> list[dict[str, Any]]:
        payload = await self._request("GET", "/countries")
        data = payload.get("data") or payload.get("result") or []
        countries = [
            {
                "code": str(item.get("code") or item.get("countryCode") or "").upper(),
                "name": str(item.get("name") or item.get("countryName") or ""),
                "region": str(item.get("region") or item.get("continent") or item.get("zone") or "Other"),
                "popularity_score": self._to_float(item.get("soldCount") or item.get("orderCount") or item.get("popularity")),
            }
            for item in data
        ]
        countries = [c for c in countries if c["code"]]
        if search:
            q = search.strip().lower()
            countries = [c for c in countries if q in c["name"].lower() or q in c["code"].lower()]
        return countries

    async def get_packages(self, country_code: str) -> list[dict[str, Any]]:
        payload = await self._request("GET", f"/packages?countryCode={country_code.upper()}")
        data = payload.get("data") or payload.get("result") or []
        return [self._normalize_package(item, country_code.upper()) for item in data]

    async def purchase_esim(self, package_code: str, external_id: str) -> dict[str, Any]:
        payload = {
            "packageCode": package_code,
            "quantity": 1,
            "externalOrderNo": external_id,
        }
        response = await self._request("POST", "/orders", json=payload)
        data = response.get("data") or response.get("result") or response
        return {
            "provider_order_no": str(data.get("orderNo") or data.get("id") or ""),
            "raw": data,
        }

    async def get_order_detail(self, provider_order_no: str) -> dict[str, Any]:
        response = await self._request("GET", f"/orders/{provider_order_no}")
        data = response.get("data") or response.get("result") or response
        return {
            "status": str(data.get("status") or data.get("orderStatus") or "").lower(),
            "qr_url": str(data.get("qrCodeUrl") or data.get("esimQrUrl") or ""),
            "activation_code": str(data.get("activationCode") or data.get("iccid") or ""),
            "instructions": str(data.get("activationManual") or data.get("instructions") or ""),
            "raw": data,
        }
