from __future__ import annotations

from datetime import datetime
from typing import Any


def build_traceability(*, company_id: int, user_id: int | None, modules: list[str], sources: list[str], counts: dict[str, int]) -> dict[str, Any]:
    return {
        "company_id": int(company_id),
        "user_id": int(user_id) if user_id else None,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "modules": modules,
        "sources_used": sources,
        "records_analyzed": counts,
    }
