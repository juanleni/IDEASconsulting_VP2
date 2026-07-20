from __future__ import annotations

import json

from core_data import (
    obtener_empresa_detalle,
    obtener_lab_acciones_empresa,
    obtener_lab_auditorias_empresa,
    obtener_lab_calibraciones_empresa,
    obtener_lab_competencias_empresa,
    obtener_lab_control_calidad_empresa,
    obtener_lab_equipos_empresa,
    obtener_lab_incertidumbre_empresa,
    obtener_lab_informes_empresa,
    obtener_lab_metodos_empresa,
    obtener_lab_muestras_empresa,
    obtener_lab_riesgos_empresa,
)


def build_lab_ai_context(company_id: int, alerts: list[dict], extra: dict | None = None) -> dict:
    company = obtener_empresa_detalle(int(company_id)) or {}
    context = {
        "empresa_id": int(company_id),
        "empresa": str(company.get("razon_social") or company.get("nombre") or ""),
        "resumen": {
            "equipos": len(obtener_lab_equipos_empresa(int(company_id))),
            "calibraciones": len(obtener_lab_calibraciones_empresa(int(company_id))),
            "metodos": len(obtener_lab_metodos_empresa(int(company_id))),
            "muestras": len(obtener_lab_muestras_empresa(int(company_id))),
            "competencias": len(obtener_lab_competencias_empresa(int(company_id))),
            "incertidumbre_componentes": len(obtener_lab_incertidumbre_empresa(int(company_id))),
            "control_calidad": len(obtener_lab_control_calidad_empresa(int(company_id))),
            "informes": len(obtener_lab_informes_empresa(int(company_id))),
            "auditorias": len(obtener_lab_auditorias_empresa(int(company_id))),
            "riesgos": len(obtener_lab_riesgos_empresa(int(company_id))),
            "acciones": len(obtener_lab_acciones_empresa(int(company_id))),
        },
        "alertas_disparadas": alerts[:25],
    }
    if extra:
        context["extra"] = extra
    return context


def build_compact_context_text(context: dict) -> str:
    return json.dumps(context, ensure_ascii=False, sort_keys=True, default=str)

