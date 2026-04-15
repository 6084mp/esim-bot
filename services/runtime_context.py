from __future__ import annotations

from typing import Any

_SERVICES: dict[str, Any] | None = None


def set_services(services: dict[str, Any]) -> None:
    global _SERVICES
    _SERVICES = services


def get_services() -> dict[str, Any]:
    if _SERVICES is None:
        raise RuntimeError("Services container is not initialized")
    return _SERVICES
