from __future__ import annotations

from math import ceil
from typing import Sequence, TypeVar

T = TypeVar("T")


def paginate_items(items: Sequence[T], page: int, page_size: int) -> tuple[list[T], int, int]:
    total = len(items)
    pages = max(1, ceil(total / page_size))
    page = max(1, min(page, pages))
    start = (page - 1) * page_size
    end = start + page_size
    return list(items[start:end]), page, pages
