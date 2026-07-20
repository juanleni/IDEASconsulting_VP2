from __future__ import annotations

import json
from typing import Any

from core_data import (
    get_enabled_modules_for_user,
    obtener_alertas_globales,
    obtener_diagnosticos_empresa,
    obtener_empresa_detalle,
    obtener_fuentes_empresa,
    obtener_kpis_empresa,
    obtener_lab_dashboard_empresa,
    obtener_mapa_procesos_empresa,
    obtener_matrices_riesgos_empresa,
    obtener_problemas_calidad_empresa,
)


def _safe_limit(rows: list[dict], limit: int = 6) -> list[dict]:
    return rows[: max(1, int(limit))]


def build_ai_context(
    user_id: int | None,
    company_id: int,
    module: str | None = None,
    query: str | None = None,
    *,
    user_name: str = "",
    user_role: str = "",
    permissions: str = "ALL",
    module_whitelist: list[str] | None = None,
    working_context: str = "",
    focus_payload: dict | None = None,
) -> dict[str, Any]:
    company = obtener_empresa_detalle(int(company_id)) or {}
    kpis = obtener_kpis_empresa(int(company_id)) or []
    procesos = obtener_mapa_procesos_empresa(int(company_id)) or []
    riesgos = obtener_matrices_riesgos_empresa(int(company_id)) or []
    calidad_8d = obtener_problemas_calidad_empresa(int(company_id)) or []
    diagnosticos = obtener_diagnosticos_empresa(int(company_id)) or []
    fuentes = obtener_fuentes_empresa(int(company_id)) or []
    dashboard_lab = obtener_lab_dashboard_empresa(int(company_id)) or {}
    alertas = obtener_alertas_globales() or []
    alertas_empresa = [a for a in alertas if int(a.get("empresa_id") or 0) == int(company_id)]
    abiertas = [a for a in alertas_empresa if str(a.get("estado") or "").lower() not in {"cerrada", "descartada"}]
    open_actions = len([a for a in abiertas if "accion" in str(a.get("titulo") or "").lower()])

    enabled_modules = []
    if module_whitelist is not None:
        enabled_modules = list(module_whitelist)
    elif user_id:
        try:
            enabled_modules = [str(row.get("code") or "") for row in get_enabled_modules_for_user(int(user_id), int(company_id))]
        except Exception:
            enabled_modules = []

    context = {
        "empresa": {
            "id": int(company_id),
            "razon_social": str(company.get("razon_social") or ""),
            "rubro": str(company.get("rubro") or ""),
            "ubicacion": str(company.get("ubicacion") or ""),
            "certificaciones": {
                "iso_9001": str(company.get("cert_iso_9001") or "No"),
                "iso_14001": str(company.get("cert_iso_14001") or "No"),
                "iso_45001": str(company.get("cert_iso_45001") or "No"),
                "iatf_16949": str(company.get("cert_iatf") or "No"),
            },
        },
        "usuario": {
            "id": int(user_id) if user_id else None,
            "nombre": str(user_name or ""),
            "rol": str(user_role or ""),
            "permisos": str(permissions or "ALL"),
            "modulos_habilitados": enabled_modules,
        },
        "consulta": {
            "modulo": str(module or "general"),
            "pregunta": str(query or ""),
        },
        "resumen_operativo": {
            "diagnosticos": len(diagnosticos),
            "kpis": len(kpis),
            "procesos": len(procesos),
            "matrices_riesgo": len(riesgos),
            "no_conformidades_8d": len(calidad_8d),
            "documentos_base_ia": len(fuentes),
            "alertas_abiertas": len(abiertas),
            "acciones_abiertas_aprox": open_actions,
            "lab_score_general": dashboard_lab.get("score_general_iso_17025"),
            "lab_semaforo": dashboard_lab.get("semaforo_general"),
        },
        "registros_relevantes": {
            "kpis": _safe_limit(kpis, 5),
            "riesgos": _safe_limit(riesgos, 4),
            "procesos": _safe_limit(procesos, 4),
            "diagnosticos": _safe_limit(diagnosticos, 3),
            "acciones_8d": _safe_limit(calidad_8d, 3),
            "fuentes": [
                {
                    "titulo": str(item.get("titulo") or ""),
                    "tipo": str(item.get("tipo") or ""),
                }
                for item in _safe_limit(fuentes, 8)
            ],
        },
        "foco_ui": focus_payload or {},
        "working_context": str(working_context or "").strip(),
    }
    return context


def render_context_as_text(context: dict[str, Any], max_chars: int = 7200) -> str:
    text = json.dumps(context, ensure_ascii=False, indent=2)
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n...[contexto resumido por limite]"
