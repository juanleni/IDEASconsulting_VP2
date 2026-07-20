from __future__ import annotations

from typing import Any

from services.ai.service import SmartIdeasAIService

from .ai_chart_service import bar_chart_widget, table_widget
from .ai_data_catalog import DATA_CATALOG
from .ai_query_planner import plan_sources_from_query
from .ai_report_service import build_traceability
from .company_data_index import (
    assert_company_scope,
    filter_by_company_id,
    validate_module_access,
    validate_user_permission,
)


ALLOWED_RESPONSE_TYPES = {
    "executive_summary",
    "analysis_dashboard",
    "chart_report",
    "table_analysis",
    "audit_report",
    "risk_analysis",
    "compliance_report",
    "action_plan",
    "data_quality_report",
    "missing_data_report",
}


def _records_count(rows: Any) -> int:
    if isinstance(rows, list):
        return len(rows)
    if isinstance(rows, dict):
        for key in ("rows", "open", "critical_items", "by_process", "by_status"):
            value = rows.get(key)
            if isinstance(value, list):
                return len(value)
    return 0


async def generate_command_center_analysis(
    *,
    query: str,
    company_id: int | None,
    user_id: int | None,
    user_name: str,
    user_role: str,
    permissions: str,
    module_key: str,
    enabled_modules: list[str] | None,
) -> dict[str, Any]:
    scoped_company = assert_company_scope(company_id)
    if not validate_module_access(module_key, enabled_modules):
        return {"ok": False, "message": "No tenés acceso al módulo activo."}
    if not validate_user_permission(permissions):
        return {"ok": False, "message": "No tenés permisos para este análisis."}

    sources_all = filter_by_company_id(
        company_id=scoped_company,
        module_key=module_key,
        user_permissions=permissions,
    )
    planned = [s for s in plan_sources_from_query(query) if s in sources_all and s in DATA_CATALOG]
    source_payload = {k: sources_all.get(k) for k in planned}

    widgets: list[dict[str, Any]] = []
    recommendations: list[str] = []
    counts: dict[str, int] = {}
    module_names: list[str] = []
    for source in planned:
        data = source_payload.get(source) or {}
        counts[source] = _records_count(data)
        module_names.append(str((DATA_CATALOG.get(source) or {}).get("module") or "general"))
        if source == "quality.corrective_actions":
            widgets.append({"type": "kpi_card", "title": "Acciones abiertas", "value": int(data.get("open_count") or 0), "status": "warning"})
            widgets.append(table_widget(title="Acciones vencidas", rows=data.get("overdue") or [], columns=["accion", "responsable", "fecha_limite", "fase_8d"]))
        elif source == "risks.matrix":
            crit = data.get("critical_items") or []
            widgets.append({"type": "kpi_card", "title": "Riesgos críticos", "value": len(crit), "status": "warning" if crit else "ok"})
            widgets.append(bar_chart_widget(title="Riesgos por proceso", rows=data.get("by_process") or [], x="process", y="count"))
        elif source == "kpis.company":
            widgets.append({"type": "kpi_card", "title": "KPIs cargados", "value": int(data.get("total") or 0), "status": "ok"})
            widgets.append(bar_chart_widget(title="KPIs por proceso", rows=data.get("by_process") or [], x="label", y="count"))
        elif source == "lab.iso17025":
            widgets.append({"type": "kpi_card", "title": "Score ISO 17025", "value": data.get("score_general") or "N/D", "status": "warning"})
        elif source == "lab.calibrations":
            status = data.get("status") or {}
            widgets.append(bar_chart_widget(title="Calibraciones por estado", rows=[{"label": k, "count": int(v)} for k, v in status.items()]))
        elif source == "documents.expiring":
            widgets.append(table_widget(title="Documentos disponibles", rows=data.get("rows") or [], columns=["titulo", "tipo", "fecha_carga"], limit=8))
        elif source == "alerts.company":
            widgets.append(table_widget(title="Alertas abiertas", rows=data.get("open") or [], columns=["titulo", "criticidad", "estado"], limit=8))
        elif source == "environmental.indicators":
            widgets.append({"type": "kpi_card", "title": "Registros ambientales", "value": int(data.get("aspectos") or 0), "status": "ok"})

    missing = [s for s in planned if counts.get(s, 0) == 0]
    if missing:
        recommendations.append(
            "Faltan datos en: " + ", ".join([str((DATA_CATALOG.get(m) or {}).get("label") or m) for m in missing])
        )
    if not widgets:
        return {
            "ok": True,
            "result": {
                "response_type": "missing_data_report",
                "title": "Datos insuficientes",
                "summary": "No hay datos suficientes para generar análisis visual en esta empresa.",
                "sources_used": planned,
                "widgets": [{"type": "warning_card", "title": "Datos faltantes", "message": "Cargá registros en los módulos habilitados para activar análisis visual."}],
                "recommendations": ["Cargá datos en KPIs, riesgos, acciones y documentos."],
                "next_actions": [],
                "traceability": build_traceability(company_id=scoped_company, user_id=user_id, modules=module_names, sources=planned, counts=counts),
            },
        }

    summary_prompt = (
        "Genera un resumen ejecutivo breve en español sobre este análisis empresarial. "
        "No inventes datos. Enfocate en prioridades y siguientes pasos.\n"
        f"Consulta: {query}\n"
        f"Conteos: {counts}\n"
        f"Fuentes: {planned}\n"
    )
    summary = await SmartIdeasAIService().answer(
        question=summary_prompt,
        company_id=scoped_company,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        permissions=permissions,
        module_key=module_key,
        enabled_modules=enabled_modules,
        task_type="analysis_dashboard",
        include_sources=True,
    )

    response_type = "analysis_dashboard"
    if response_type not in ALLOWED_RESPONSE_TYPES:
        response_type = "executive_summary"

    return {
        "ok": True,
        "result": {
            "response_type": response_type,
            "title": "Smart IDEAS Command Center",
            "summary": summary,
            "sources_used": planned,
            "widgets": widgets,
            "recommendations": recommendations,
            "next_actions": [
                "Revisar responsables de vencidas.",
                "Definir plan de acción para riesgos críticos.",
            ],
            "traceability": build_traceability(company_id=scoped_company, user_id=user_id, modules=module_names, sources=planned, counts=counts),
        },
    }
