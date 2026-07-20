from __future__ import annotations

import json
from typing import Any

from .ai_visual_schema import validate_visual_schema
from .service import SmartIdeasAIService


def _schema_prompt() -> str:
    return (
        "Devuelve SOLO JSON valido con este formato:\n"
        "{"
        "\"title\":\"...\","
        "\"description\":\"...\","
        "\"filters\":[{\"field\":\"...\",\"label\":\"...\",\"type\":\"select|date_range|text\"}],"
        "\"widgets\":["
        "{\"type\":\"kpi_card|bar_chart|line_chart|donut_chart|table|semaphore|priority_list|timeline|heatmap_simple|alerts\","
        "\"title\":\"...\",\"data_source\":\"...\",\"x\":\"...\",\"y\":\"...\",\"columns\":[\"...\"],\"limit\":12}"
        "]"
        "}\n"
        "No agregues markdown, ni texto fuera del JSON."
    )


def _fallback_schema(user_prompt: str) -> dict[str, Any]:
    p = str(user_prompt or "").lower()
    if "riesgo" in p:
        return {
            "title": "Riesgos críticos por proceso",
            "description": "Vista ejecutiva de riesgos con foco en criticidad.",
            "filters": [{"field": "process", "label": "Proceso", "type": "select"}],
            "widgets": [
                {"type": "kpi_card", "title": "Riesgos críticos", "data_source": "risks.matrix"},
                {"type": "bar_chart", "title": "Riesgos por proceso", "data_source": "risks.matrix", "x": "process", "y": "count"},
                {"type": "table", "title": "Detalle crítico", "data_source": "risks.matrix", "columns": ["proceso", "riesgo", "npr", "estado"], "limit": 12},
            ],
        }
    if "calibr" in p or "17025" in p:
        return {
            "title": "Estado ISO 17025 y calibraciones",
            "description": "Resumen de calibraciones e indicadores LAB.",
            "filters": [],
            "widgets": [
                {"type": "kpi_card", "title": "Score ISO 17025", "data_source": "lab.iso17025"},
                {"type": "donut_chart", "title": "Calibraciones por estado", "data_source": "lab.calibrations", "x": "label", "y": "count"},
                {"type": "alerts", "title": "Alertas abiertas", "data_source": "alerts.company", "limit": 10},
            ],
        }
    return {
        "title": "Dashboard ejecutivo",
        "description": "Resumen operativo generado por Smart IDEAS.",
        "filters": [{"field": "status", "label": "Estado", "type": "select"}],
        "widgets": [
            {"type": "kpi_card", "title": "Acciones abiertas", "data_source": "quality.corrective_actions"},
            {"type": "bar_chart", "title": "Acciones por fase 8D", "data_source": "quality.corrective_actions", "x": "label", "y": "count"},
            {"type": "table", "title": "Acciones vencidas", "data_source": "quality.corrective_actions", "columns": ["accion", "responsable", "fecha_limite", "fase_8d"], "limit": 10},
        ],
    }


async def generate_dashboard_schema(
    *,
    user_prompt: str,
    module_key: str,
    available_sources: list[str],
    context_summary: str,
) -> tuple[bool, str, dict[str, Any]]:
    if not str(user_prompt or "").strip():
        fallback = _fallback_schema("dashboard ejecutivo")
        ok, msg, validated = validate_visual_schema(fallback)
        return ok, msg, validated

    service = SmartIdeasAIService()
    prompt = (
        f"Pedido de dashboard: {user_prompt}\n"
        f"Modulo actual: {module_key}\n"
        f"Data sources disponibles: {', '.join(available_sources)}\n"
        f"Contexto resumido: {context_summary}\n"
        f"{_schema_prompt()}"
    )
    try:
        import asyncio

        raw = await asyncio.to_thread(
            service._chat_text,
            "Eres Smart IDEAS y solo generas schemas JSON seguros para dashboards empresariales.",
            prompt,
        )
        data = json.loads(raw)
        ok, msg, validated = validate_visual_schema(data)
        if ok:
            return True, "ok", validated
    except Exception:
        pass
    fallback = _fallback_schema(user_prompt)
    ok, msg, validated = validate_visual_schema(fallback)
    return ok, msg, validated
