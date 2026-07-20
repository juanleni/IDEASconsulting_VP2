from __future__ import annotations

import datetime
import json
import sqlite3

from core_data import DB_PATH, obtener_lab_dashboard_empresa
from services.lab_alert_service import list_lab_alerts
from services.lab_ai_context_builder import build_lab_ai_context
from services.lab_ai_engine import analyze_with_lab_ai


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def generate_pre_assessment_report(company_id: int, generated_by: str = "sistema") -> dict:
    dashboard = obtener_lab_dashboard_empresa(int(company_id))
    alerts = list_lab_alerts(int(company_id), status="abierta")
    crit = [a for a in alerts if str(a.get("criticidad") or "").lower() == "critica"]
    high = [a for a in alerts if str(a.get("criticidad") or "").lower() == "alta"]
    incomplete = [a for a in alerts if str(a.get("tipo") or "").lower() == "incompleto"]
    incoherence = [a for a in alerts if str(a.get("tipo") or "").lower() == "incoherencia"]
    risk = [a for a in alerts if str(a.get("tipo") or "").lower() in {"riesgo", "ia"}]
    context = build_lab_ai_context(int(company_id), alerts[:20], {"kind": "pre_assessment"})
    ai = analyze_with_lab_ai(context)
    payload = {
        "score_general": float(dashboard.get("score_general") or 0),
        "resumen_ejecutivo": str(ai.get("diagnostico") or ""),
        "riesgos_criticos": len(crit),
        "brechas_principales": [str(item.get("titulo") or "") for item in (crit + high)[:10]],
        "vencimientos_criticos": len([a for a in alerts if str(a.get("tipo") or "").lower() == "vencimiento"]),
        "registros_incompletos": len(incomplete),
        "incoherencias_tecnicas": len(incoherence),
        "impacto_potencial": str(ai.get("impacto_potencial") or ""),
        "acciones_prioritarias": [str(a.get("accion_sugerida") or a.get("titulo") or "") for a in alerts[:8]],
        "proximos_pasos": [str(ai.get("accion_inmediata") or ""), str(ai.get("accion_correctiva_sugerida") or "")],
        "riesgo_acreditacion": str(ai.get("riesgo_acreditacion") or "medio"),
        "fecha_generacion": _now(),
    }
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO lab_ai_reportes (empresa_id, tipo, score_general, resumen_ejecutivo, payload_json, generado_por)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (int(company_id), "pre_acreditacion", float(payload["score_general"]), payload["resumen_ejecutivo"], json.dumps(payload, ensure_ascii=False), str(generated_by or "sistema")),
    )
    conn.commit()
    conn.close()
    return payload


def list_reports(company_id: int, report_type: str = "") -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if report_type:
        c.execute(
            "SELECT id, tipo, score_general, resumen_ejecutivo, payload_json, generado_por, created_at FROM lab_ai_reportes WHERE empresa_id = ? AND tipo = ? ORDER BY id DESC",
            (int(company_id), str(report_type)),
        )
    else:
        c.execute(
            "SELECT id, tipo, score_general, resumen_ejecutivo, payload_json, generado_por, created_at FROM lab_ai_reportes WHERE empresa_id = ? ORDER BY id DESC",
            (int(company_id),),
        )
    keys = ["id", "tipo", "score_general", "resumen_ejecutivo", "payload_json", "generado_por", "created_at"]
    rows = [dict(zip(keys, row)) for row in c.fetchall()]
    conn.close()
    return rows


def generate_daily_ai_summary(company_id: int) -> dict:
    return generate_pre_assessment_report(int(company_id), generated_by="scheduler")

