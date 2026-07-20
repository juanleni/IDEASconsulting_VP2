from __future__ import annotations

from collections import deque
from typing import Any


_MEMORY: dict[str, deque] = {}


def _memory_key(company_id: int, user_id: int | None) -> str:
    return f"{int(company_id)}:{int(user_id or 0)}"


def push_memory(*, company_id: int, user_id: int | None, item: dict[str, Any], limit: int = 40) -> None:
    key = _memory_key(company_id, user_id)
    queue = _MEMORY.setdefault(key, deque(maxlen=max(10, int(limit))))
    queue.append(item)


def read_memory(*, company_id: int, user_id: int | None, limit: int = 10) -> list[dict[str, Any]]:
    key = _memory_key(company_id, user_id)
    queue = _MEMORY.get(key)
    if not queue:
        return []
    return list(queue)[-max(1, int(limit)) :]
