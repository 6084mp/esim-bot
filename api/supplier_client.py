from __future__ import annotations

import asyncio
import logging
import re
import time
import uuid
from typing import Any

import aiohttp

logger = logging.getLogger(__name__)


class SupplierAPIError(Exception):
    pass


class SupplierAPIClient:
    def __init__(
        self,
        base_url: str,
        access_code: str,
        secret_key: str,
        timeout_seconds: int = 20,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.access_code = access_code
        self.secret_key = secret_key
        self.timeout = aiohttp.ClientTimeout(total=timeout_seconds)

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "RT-AccessCode": self.access_code,
            "RT-SecretKey": self.secret_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.base_url}{path}"
        try:
            async with aiohttp.ClientSession(timeout=self.timeout) as session:
                async with session.request(method, url, headers=self._headers, json=payload or {}) as response:
                    text = await response.text()
                    if response.status >= 400:
                        raise SupplierAPIError(f"HTTP {response.status}: {text[:300]}")
                    try:
                        return await response.json(content_type=None)
                    except Exception as exc:
                        raise SupplierAPIError(f"Invalid JSON from supplier: {text[:300]}") from exc
        except (aiohttp.ClientError, asyncio.TimeoutError) as exc:
            raise SupplierAPIError(f"Supplier request failed: {exc}") from exc

    @staticmethod
    def _extract_obj(data: Any) -> Any:
        if isinstance(data, dict):
            if "success" in data and not data.get("success", True):
                code = data.get("errorCode")
                message = data.get("errorMsg") or data.get("message") or "Supplier error"
                raise SupplierAPIError(f"Supplier error {code}: {message}")
            if "obj" in data:
                return data.get("obj")
            if "data" in data:
                return data.get("data")
            if "result" in data:
                return data.get("result")
        return data

    @staticmethod
    def _extract_list_payload(data: Any) -> list[Any]:
        """Supplier may return list directly or wrap it into various dict keys."""
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in (
                "list",
                "records",
                "rows",
                "packages",
                "packageList",
                "dataList",
                "items",
                "locationList",
                "locations",
                "countryList",
                "resultList",
            ):
                value = data.get(key)
                if isinstance(value, list):
                    return value
            # One more fallback: return first list-typed value from dict.
            for value in data.values():
                if isinstance(value, list):
                    return value
        return []

    @staticmethod
    def _to_float(value: Any, default: float = 0.0) -> float:
        if value is None:
            return default
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            cleaned = value.replace(",", ".")
            cleaned = re.sub(r"[^0-9.\-]", "", cleaned)
            if not cleaned:
                return default
            try:
                return float(cleaned)
            except ValueError:
                return default
        return default

    @staticmethod
    def _normalize_price(value: Any, volume_mb: float | None = None) -> float:
        raw_price = SupplierAPIClient._to_float(value, 0.0)
        if raw_price <= 0:
            return 0.0

        # Supplier payloads may contain mixed scales in the same response set.
        # Common variants:
        # - USD direct (e.g. 4.7)
        # - cents (e.g. 1220 -> 12.20)
        # - x10000 fixed-point (e.g. 13000 -> 1.30, 38000 -> 3.80)
        is_integer_like = False
        has_only_zero_fraction = False
        if isinstance(value, int):
            is_integer_like = True
        elif isinstance(value, str):
            raw = value.strip()
            if raw and "." not in raw and "," not in raw:
                is_integer_like = True
            if "." in raw:
                frac = raw.split(".", 1)[1]
                has_only_zero_fraction = frac.strip("0") == ""
            elif "," in raw:
                frac = raw.split(",", 1)[1]
                has_only_zero_fraction = frac.strip("0") == ""

        candidates: list[float] = []
        if is_integer_like:
            candidates.extend([raw_price / 10000.0, raw_price / 100.0, raw_price])
        elif has_only_zero_fraction:
            candidates.extend([raw_price / 10000.0, raw_price / 100.0, raw_price])
        else:
            candidates.append(raw_price)

        # Deduplicate while preserving order.
        unique_candidates: list[float] = []
        seen: set[float] = set()
        for candidate in candidates:
            rounded = round(candidate, 6)
            if rounded <= 0:
                continue
            if rounded in seen:
                continue
            seen.add(rounded)
            unique_candidates.append(rounded)
        if not unique_candidates:
            return 0.0

        data_gb = (float(volume_mb) / 1024.0) if volume_mb and volume_mb > 0 else 0.0

        def _score(candidate: float) -> tuple[int, float]:
            penalty = 0

            # Global absolute sanity.
            if candidate < 0.1:
                penalty += 6
            elif candidate < 0.3:
                penalty += 3
            if candidate > 200:
                penalty += 6
            elif candidate > 100:
                penalty += 3

            if data_gb > 0:
                per_gb = candidate / data_gb
                if per_gb < 0.1:
                    penalty += 6
                elif per_gb < 0.2:
                    penalty += 3
                if per_gb > 80:
                    penalty += 6
                elif per_gb > 40:
                    penalty += 3

            # Prefer smaller positive candidate when penalties equal.
            return (penalty, candidate)

        price = min(unique_candidates, key=_score)

        # Extra guard: some responses may still be scaled by 100 more.
        while price > 500:
            price = price / 100.0

        return round(price, 4)

    @staticmethod
    def _parse_validity_days(value: Any) -> int:
        if isinstance(value, int):
            return max(1, value)
        if isinstance(value, float):
            return max(1, int(value))
        if isinstance(value, str):
            match = re.search(r"(\d+)", value)
            if match:
                return max(1, int(match.group(1)))
        return 1

    @staticmethod
    def _parse_volume_mb(value: Any) -> float:
        if isinstance(value, (int, float)):
            raw = float(value)
            if raw <= 0:
                return 0.0
            if raw > 1_000_000:
                return raw / (1024 * 1024)
            if raw > 100_000:
                return raw / 1024
            return raw

        if isinstance(value, str):
            cleaned = value.strip().upper().replace(" ", "")
            match = re.match(r"([0-9]+(?:\.[0-9]+)?)([A-Z]+)?", cleaned)
            if not match:
                return 0.0
            amount = float(match.group(1))
            unit = (match.group(2) or "MB").replace("IB", "B")
            if unit in {"B"}:
                return amount / (1024 * 1024)
            if unit in {"KB", "K"}:
                return amount / 1024
            if unit in {"MB", "M"}:
                return amount
            if unit in {"GB", "G"}:
                return amount * 1024
            if unit in {"TB", "T"}:
                return amount * 1024 * 1024
            return amount

        return 0.0

    @staticmethod
    def _pick(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
        for key in keys:
            if key in data and data[key] not in (None, ""):
                return data[key]
        return default

    @staticmethod
    def _extract_order_no_any(data: Any) -> str:
        if isinstance(data, dict):
            for key in ("orderNo", "transactionId", "id"):
                value = data.get(key)
                if value not in (None, ""):
                    return str(value)
            for list_key in ("orderNoList", "orderList", "orders"):
                value = data.get(list_key)
                if isinstance(value, list) and value:
                    first = value[0]
                    if isinstance(first, dict):
                        nested = SupplierAPIClient._extract_order_no_any(first)
                        if nested:
                            return nested
                    if first not in (None, ""):
                        return str(first)
            for value in data.values():
                nested = SupplierAPIClient._extract_order_no_any(value)
                if nested:
                    return nested
        elif isinstance(data, list):
            for item in data:
                nested = SupplierAPIClient._extract_order_no_any(item)
                if nested:
                    return nested
        return ""

    def _extract_safe_wholesale_price(self, raw: dict[str, Any], volume_mb: float) -> float:
        # Safety-first rule:
        # normalize all possible supplier price fields and use the maximum.
        # This prevents accidental underpricing when one field is scaled differently.
        price_fields = ("price", "costPrice", "salePrice", "amount", "orderPrice")
        candidates: list[float] = []
        for field in price_fields:
            value = raw.get(field)
            if value in (None, ""):
                continue
            normalized = self._normalize_price(value, volume_mb=volume_mb)
            if normalized > 0:
                candidates.append(normalized)

        if not candidates:
            return 0.0

        safe_price = max(candidates)
        if len(candidates) >= 2:
            low = min(candidates)
            high = max(candidates)
            # Log large spreads for diagnostics without exposing secrets.
            if low > 0 and (high / low) >= 1.8:
                logger.warning(
                    "Supplier price spread detected package=%s country=%s low=%.4f high=%.4f fields=%s",
                    str(raw.get("packageCode") or raw.get("packageNo") or raw.get("id") or ""),
                    str(raw.get("locationCode") or raw.get("countryCode") or ""),
                    low,
                    high,
                    [field for field in price_fields if raw.get(field) not in (None, "")],
                )
        return safe_price

    def _normalize_package(self, raw: dict[str, Any]) -> dict[str, Any] | None:
        package_code = str(self._pick(raw, "packageCode", "packageNo", "id", "code", default="")).strip()
        if not package_code:
            return None

        volume_raw = self._pick(raw, "volume", "volumeMb", "totalVolume", "data", "dataVolume", "flow", default=0)
        volume_mb = round(self._parse_volume_mb(volume_raw), 4)
        if volume_mb <= 0:
            return None

        price = self._extract_safe_wholesale_price(raw, volume_mb=volume_mb)
        if price <= 0:
            return None

        validity_days = self._parse_validity_days(
            self._pick(raw, "validityDays", "duration", "day", "validity", default=1)
        )

        country_code = str(self._pick(raw, "locationCode", "countryCode", "country", default="")).upper()
        country_name = str(self._pick(raw, "locationName", "countryName", "country", default=country_code))

        is_active = self._pick(raw, "active", "isActive", "status", default=True)
        if isinstance(is_active, str):
            active_value = is_active.lower() in {"1", "true", "active", "on", "yes"}
        elif isinstance(is_active, int):
            active_value = is_active == 1
        else:
            active_value = bool(is_active)

        if not active_value:
            return None

        return {
            "package_code": package_code,
            "country_code": country_code,
            "country_name": country_name,
            "volume_mb": volume_mb,
            "validity_days": validity_days,
            "wholesale_price_usd": price,
        }

    async def get_locations(self) -> list[dict[str, Any]]:
        raw = await self._request("POST", "/api/v1/open/location/list", {})
        obj = self._extract_obj(raw)
        raw_list = self._extract_list_payload(obj)
        if not raw_list and isinstance(obj, list):
            raw_list = obj
        if not raw_list:
            raise SupplierAPIError("Unexpected location response shape")

        normalized: list[dict[str, Any]] = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            code = str(self._pick(item, "locationCode", "countryCode", "code", default="")).upper()
            if not code:
                continue
            normalized.append(
                {
                    "country_code": code,
                    "country_name": str(self._pick(item, "locationName", "countryName", "name", default=code)),
                    "continent": str(self._pick(item, "region", "continent", default="")),
                }
            )
        return normalized

    async def get_packages_by_country(self, country_code: str) -> list[dict[str, Any]]:
        cc = country_code.upper()

        payload_attempts = [
            {"locationCode": cc},
            {"countryCode": cc},
            {"location": cc},
            {"isoCode": cc},
        ]

        last_error: Exception | None = None
        for payload in payload_attempts:
            try:
                raw = await self._request("POST", "/api/v1/open/package/list", payload)
                obj = self._extract_obj(raw)
                raw_list = self._extract_list_payload(obj)
                if not raw_list:
                    continue

                results: list[dict[str, Any]] = []
                for item in raw_list:
                    if not isinstance(item, dict):
                        continue
                    norm = self._normalize_package(item)
                    if not norm:
                        continue

                    if not norm.get("country_code"):
                        norm["country_code"] = cc

                    # Keep exact country, country subcodes (e.g. RU-1), and global entries.
                    ncc = str(norm.get("country_code", "")).upper()
                    if ncc and ncc not in {cc, "GLOBAL", "GL"} and not ncc.startswith(f"{cc}-"):
                        continue
                    results.append(norm)

                if results:
                    return results
            except Exception as exc:  # noqa: BLE001
                msg = str(exc)
                if "200032" in msg and "Not support the location code" in msg:
                    logger.info("Supplier does not support location code %s for package/list; skipping", cc)
                    return []
                last_error = exc
                logger.exception("Package list request failed for payload=%s country=%s", payload, cc)

        # Fallback: request without filters and filter locally.
        try:
            raw = await self._request("POST", "/api/v1/open/package/list", {})
            obj = self._extract_obj(raw)
            raw_list = self._extract_list_payload(obj)
            results: list[dict[str, Any]] = []
            for item in raw_list:
                if not isinstance(item, dict):
                    continue
                norm = self._normalize_package(item)
                if not norm:
                    continue

                ncc = str(norm.get("country_code", "")).upper()
                if ncc in {cc, "GLOBAL", "GL"} or ncc.startswith(f"{cc}-"):
                    results.append(norm)
            if results:
                return results
        except Exception as exc:  # noqa: BLE001
            msg = str(exc)
            if "200032" in msg and "Not support the location code" in msg:
                logger.info("Supplier does not support location code %s in fallback package/list; skipping", cc)
                return []
            last_error = exc
            logger.exception("Unfiltered package list fallback failed for country=%s", cc)

        if last_error:
            raise SupplierAPIError(f"Failed to load packages for {cc}: {last_error}") from last_error
        return []

    async def purchase_esim(self, package_code: str, quantity: int = 1, order_ref: str | None = None) -> dict[str, Any]:
        txid = order_ref or f"TX-{int(time.time())}-{uuid.uuid4().hex[:10].upper()}"
        pkg_info = [{"packageCode": package_code, "count": int(quantity)}]
        payload_attempts: list[dict[str, Any]] = [
            {
                "transactionId": txid,
                "packageInfoList": pkg_info,
            },
            {
                "transactionId": txid,
                "outTradeNo": txid,
                "packageInfoList": pkg_info,
            },
            {
                "transactionId": txid,
                "packageCode": package_code,
                "quantity": int(quantity),
            },
            {
                "outTradeNo": txid,
                "packageCode": package_code,
                "quantity": int(quantity),
            },
        ]

        last_error: Exception | None = None
        for payload in payload_attempts:
            try:
                raw = await self._request("POST", "/api/v1/open/esim/order", payload)
                obj = self._extract_obj(raw)
                order_no = self._extract_order_no_any(obj)
                if not order_no:
                    raise SupplierAPIError("Supplier did not return order number")
                return {"supplier_order_no": order_no, "raw": obj}
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning("Purchase attempt failed for package=%s payload_keys=%s err=%s", package_code, sorted(payload.keys()), exc)

        raise SupplierAPIError(f"All purchase payload formats failed: {last_error}")

    async def get_esim_order_details(self, supplier_order_no: str) -> dict[str, Any]:
        payload_attempts: list[dict[str, Any]] = [
            {
                "orderNo": supplier_order_no,
                "pager": {"pageNum": 1, "pageSize": 20},
            },
            {
                "orderNo": supplier_order_no,
                "pager": {"pageNo": 1, "pageSize": 20},
            },
            {
                "transactionId": supplier_order_no,
                "pager": {"pageNum": 1, "pageSize": 20},
            },
            {
                "transactionId": supplier_order_no,
                "pager": {"pageNo": 1, "pageSize": 20},
            },
            {
                "orderNo": supplier_order_no,
            },
        ]

        last_error: Exception | None = None
        for payload in payload_attempts:
            try:
                raw = await self._request("POST", "/api/v1/open/esim/query", payload)
                obj = self._extract_obj(raw)

                if isinstance(obj, list):
                    obj = obj[0] if obj else {}
                if isinstance(obj, dict):
                    list_payload = self._extract_list_payload(obj)
                    if list_payload and isinstance(list_payload[0], dict):
                        obj = list_payload[0]
                if not isinstance(obj, dict):
                    raise SupplierAPIError("Unexpected query response")

                qr_url = self._pick(obj, "qrCodeUrl", "qrUrl", "esimQrUrl", default=None)
                activation_code = self._pick(obj, "activationCode", "ac", "code", default=None)
                smdp = self._pick(obj, "smdpAddress", "smdp", "smdpAddressCode", default=None)
                iccid = self._pick(obj, "iccid", "esimIccid", default=None)

                ready = bool(qr_url or (activation_code and smdp))
                return {
                    "ready": ready,
                    "iccid": iccid,
                    "qr_url": qr_url,
                    "smdp": smdp,
                    "activation_code": activation_code,
                    "raw": obj,
                }
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "Query attempt failed supplier_order_no=%s payload_keys=%s err=%s",
                    supplier_order_no,
                    sorted(payload.keys()),
                    exc,
                )

        raise SupplierAPIError(f"Failed to query eSIM details: {last_error}")
