from __future__ import annotations

import re
from typing import Any

import aiohttp

COUNTRY_CODE_TO_NAME = {
    "AE": "UAE",
    "AU": "Australia",
    "AT": "Austria",
    "BE": "Belgium",
    "BG": "Bulgaria",
    "BH": "Bahrain",
    "BR": "Brazil",
    "CA": "Canada",
    "CH": "Switzerland",
    "CN": "China",
    "CY": "Cyprus",
    "CZ": "Czech Republic",
    "DE": "Germany",
    "DK": "Denmark",
    "EE": "Estonia",
    "EG": "Egypt",
    "ES": "Spain",
    "FI": "Finland",
    "FR": "France",
    "GB": "United Kingdom",
    "GR": "Greece",
    "HK": "Hong Kong",
    "HR": "Croatia",
    "HU": "Hungary",
    "ID": "Indonesia",
    "IE": "Ireland",
    "IL": "Israel",
    "IN": "India",
    "IS": "Iceland",
    "IT": "Italy",
    "JO": "Jordan",
    "JP": "Japan",
    "KE": "Kenya",
    "KH": "Cambodia",
    "KR": "South Korea",
    "KW": "Kuwait",
    "LK": "Sri Lanka",
    "LT": "Lithuania",
    "LU": "Luxembourg",
    "LV": "Latvia",
    "MA": "Morocco",
    "MT": "Malta",
    "MX": "Mexico",
    "MY": "Malaysia",
    "NG": "Nigeria",
    "NL": "Netherlands",
    "NO": "Norway",
    "NP": "Nepal",
    "NZ": "New Zealand",
    "OM": "Oman",
    "PE": "Peru",
    "PH": "Philippines",
    "PL": "Poland",
    "PT": "Portugal",
    "QA": "Qatar",
    "RO": "Romania",
    "SA": "Saudi Arabia",
    "SE": "Sweden",
    "SG": "Singapore",
    "SI": "Slovenia",
    "SK": "Slovakia",
    "TH": "Thailand",
    "TN": "Tunisia",
    "TR": "Turkey",
    "TW": "Taiwan",
    "US": "United States",
    "VN": "Vietnam",
    "ZA": "South Africa",
}


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

    @staticmethod
    def _extract_items(payload: dict[str, Any]) -> list[dict[str, Any]]:
        data = payload.get("data") or payload.get("result") or []
        if isinstance(data, dict):
            for key in ("items", "list", "records", "rows", "packages"):
                value = data.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
            return []
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
        return []

    @staticmethod
    def _country_match(raw: dict[str, Any], code: str, country_name: str) -> bool:
        code_up = code.upper()
        country_low = country_name.lower()
        fields = [
            raw.get("countryCode"),
            raw.get("country"),
            raw.get("countryName"),
            raw.get("region"),
            raw.get("destination"),
            raw.get("zone"),
        ]
        for value in fields:
            if value is None:
                continue
            val = str(value).strip()
            if not val:
                continue
            if val.upper() == code_up:
                return True
            low = val.lower()
            if country_low and country_low in low:
                return True

        countries_field = raw.get("countries")
        if isinstance(countries_field, list):
            for item in countries_field:
                if isinstance(item, dict):
                    v_code = str(item.get("code") or item.get("countryCode") or "").upper()
                    v_name = str(item.get("name") or item.get("countryName") or "").lower()
                    if v_code == code_up or (country_low and country_low in v_name):
                        return True
                else:
                    txt = str(item).strip().lower()
                    if txt == code_up.lower() or (country_low and country_low in txt):
                        return True
        return False

    async def get_countries(self, search: str | None = None) -> list[dict[str, Any]]:
        # Primary endpoint from official Postman collection:
        # POST /api/v1/open/location/list
        countries: list[dict[str, Any]] = []
        attempts: list[tuple[str, str, dict[str, Any] | None]] = [
            ("POST", "/location/list", {}),
            ("GET", "/countries", None),  # backward-compatible fallback
        ]

        for method, path, body in attempts:
            try:
                if method == "POST":
                    payload = await self._request("POST", path, json=body or {})
                else:
                    payload = await self._request("GET", path)
            except RuntimeError as exc:
                if "error 404" in str(exc).lower():
                    continue
                raise

            data = self._extract_items(payload)
            if not data:
                # Some responses keep list in payload["data"] directly (already handled by _extract_items),
                # but keep this compatibility branch for unexpected shapes.
                raw_data = payload.get("data") or payload.get("result") or []
                if isinstance(raw_data, list):
                    data = [item for item in raw_data if isinstance(item, dict)]

            if not data:
                continue

            countries = [
                {
                    "code": str(
                        item.get("code")
                        or item.get("countryCode")
                        or item.get("iso2")
                        or item.get("locationCode")
                        or ""
                    ).upper(),
                    "name": str(
                        item.get("name")
                        or item.get("countryName")
                        or item.get("locationName")
                        or item.get("enName")
                        or ""
                    ),
                    "region": str(
                        item.get("region")
                        or item.get("continent")
                        or item.get("zone")
                        or item.get("groupName")
                        or "Other"
                    ),
                    "popularity_score": self._to_float(
                        item.get("soldCount") or item.get("orderCount") or item.get("popularity")
                    ),
                }
                for item in data
            ]
            if countries:
                break

        countries = [c for c in countries if c["code"]]
        if search:
            q = search.strip().lower()
            countries = [c for c in countries if q in c["name"].lower() or q in c["code"].lower()]
        return countries

    async def get_packages(self, country_code: str) -> list[dict[str, Any]]:
        code = country_code.upper()
        country_name = COUNTRY_CODE_TO_NAME.get(code, "")
        # Primary endpoint from official Postman collection:
        # POST /api/v1/open/package/list
        post_attempts: list[dict[str, Any]] = [
            {},
            {"countryCode": code},
            {"country": code},
        ]
        if country_name:
            post_attempts.extend(
                [
                    {"country": country_name},
                    {"countryName": country_name},
                ]
            )

        for body in post_attempts:
            try:
                payload = await self._request("POST", "/package/list", json=body)
            except RuntimeError as exc:
                text = str(exc).lower()
                if "error 400" in text or "error 404" in text:
                    continue
                raise

            items = self._extract_items(payload)
            if not items:
                continue

            filtered = [item for item in items if self._country_match(item, code, country_name)]
            if not filtered:
                # Some providers may already pre-filter by country in backend response.
                filtered = items
            normalized = [self._normalize_package(item, code) for item in filtered]
            if normalized:
                return normalized

        # Backward-compatible fallback for legacy endpoint variants.
        legacy_paths = [
            ("GET", "/packages"),
            ("GET", "/packages/list"),
        ]
        for method, path in legacy_paths:
            try:
                payload = await self._request(method, path)
            except RuntimeError as exc:
                text = str(exc).lower()
                if "error 400" in text or "error 404" in text:
                    continue
                raise
            items = self._extract_items(payload)
            filtered = [item for item in items if self._country_match(item, code, country_name)]
            normalized = [self._normalize_package(item, code) for item in filtered]
            if normalized:
                return normalized

        return []

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
