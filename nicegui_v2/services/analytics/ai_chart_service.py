from __future__ import annotations

from typing import Any


def bar_chart_widget(*, title: str, rows: list[dict], x: str = "label", y: str = "count") -> dict[str, Any]:
    return {"type": "bar_chart", "title": title, "data": rows[:16], "x": x, "y": y}


def table_widget(*, title: str, rows: list[dict], columns: list[str], limit: int = 12) -> dict[str, Any]:
    return {"type": "table", "title": title, "rows": rows[: max(1, int(limit))], "columns": columns}
