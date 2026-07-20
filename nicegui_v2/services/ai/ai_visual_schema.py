from __future__ import annotations

from typing import Any


ALLOWED_WIDGET_TYPES = {
    "kpi_card",
    "bar_chart",
    "line_chart",
    "donut_chart",
    "table",
    "semaphore",
    "priority_list",
    "timeline",
    "heatmap_simple",
    "alerts",
}

ALLOWED_FILTER_TYPES = {"select", "date_range", "text"}


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def validate_visual_schema(payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "La IA no devolvio un objeto JSON valido.", {}
    title = str(payload.get("title") or "").strip()
    if not title:
        return False, "Falta el titulo del dashboard.", {}

    filters = _as_list(payload.get("filters"))
    widgets = _as_list(payload.get("widgets"))
    if not widgets:
        return False, "No se recibieron widgets para renderizar.", {}

    clean_filters: list[dict[str, Any]] = []
    for item in filters[:10]:
        if not isinstance(item, dict):
            continue
        ftype = str(item.get("type") or "select").strip().lower()
        if ftype not in ALLOWED_FILTER_TYPES:
            ftype = "select"
        clean_filters.append(
            {
                "field": str(item.get("field") or "").strip(),
                "label": str(item.get("label") or item.get("field") or "").strip(),
                "type": ftype,
                "options": _as_list(item.get("options"))[:100],
            }
        )

    clean_widgets: list[dict[str, Any]] = []
    for item in widgets[:16]:
        if not isinstance(item, dict):
            continue
        wtype = str(item.get("type") or "").strip().lower()
        if wtype not in ALLOWED_WIDGET_TYPES:
            continue
        clean_widgets.append(
            {
                "type": wtype,
                "title": str(item.get("title") or "Widget").strip(),
                "description": str(item.get("description") or "").strip(),
                "data_source": str(item.get("data_source") or "").strip(),
                "x": str(item.get("x") or "").strip(),
                "y": str(item.get("y") or "").strip(),
                "columns": [str(c) for c in _as_list(item.get("columns"))[:16]],
                "limit": int(item.get("limit") or 12),
                "severity": str(item.get("severity") or "").strip(),
            }
        )
    if not clean_widgets:
        return False, "No hay widgets permitidos en el schema generado.", {}

    validated = {
        "title": title,
        "description": str(payload.get("description") or "").strip(),
        "filters": clean_filters,
        "widgets": clean_widgets,
    }
    return True, "ok", validated
