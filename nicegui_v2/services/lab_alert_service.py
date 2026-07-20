from __future__ import annotations

import datetime
import json
import sqlite3

from core_data import DB_PATH
from services.lab_ai_context_builder import build_lab_ai_context
from services.lab_ai_engine import analyze_with_lab_ai
from services.lab_rules_engine import run_lab_rules_check, run_record_rules_check


def _now() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _save_alert(company_id: int, alert: dict, created_by: str = "rules_engine") -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO lab_ai_alertas (
            empresa_id, titulo, descripcion, modulo_origen, registro_tipo, registro_id, responsable, criticidad,
            tipo, estado, fecha_deteccion, fecha_objetivo, accion_sugerida, requiere_ia, resultado_ia_json,
            evidencia_esperada, reglas_activadas_json, creado_por, actualizado_en
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(company_id),
            str(alert.get("titulo") or "Alerta LAB"),
            str(alert.get("descripcion") or ""),
            str(alert.get("modulo_origen") or ""),
            str(alert.get("registro_tipo") or ""),
            int(alert.get("registro_id") or 0),
            str(alert.get("responsable") or ""),
            str(alert.get("criticidad") or "media"),
            str(alert.get("tipo") or "incompleto"),
            "abierta",
            _now(),
            str(alert.get("fecha_objetivo") or ""),
            str(alert.get("accion_sugerida") or ""),
            int(bool(alert.get("requiere_ia"))),
            str(alert.get("resultado_ia_json") or ""),
            str(alert.get("evidencia_esperada") or ""),
            json.dumps(alert.get("reglas_activadas") or [], ensure_ascii=False),
            created_by,
            _now(),
        ),
    )
    new_id = int(c.lastrowid)
    conn.commit()
    conn.close()
    return new_id


def _save_ai_result(company_id: int, alert_id: int, context: dict, ai_result: dict, actor: str = "scheduler") -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE lab_ai_alertas SET resultado_ia_json = ?, estado = ?, actualizado_en = ? WHERE id = ?",
        (json.dumps(ai_result, ensure_ascii=False), "en análisis", _now(), int(alert_id)),
    )
    c.execute(
        """
        INSERT INTO lab_ai_analisis_log (
            empresa_id, alerta_id, disparador, contexto_json, respuesta_json, modelo, tokens_estimados, costo_estimado_usd, creado_por
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(company_id),
            int(alert_id),
            "auto",
            json.dumps(context, ensure_ascii=False),
            json.dumps(ai_result, ensure_ascii=False),
            "gpt-4o-mini",
            int(len(json.dumps(context, ensure_ascii=False)) / 4),
            0.0,
            actor,
        ),
    )
    conn.commit()
    conn.close()


def list_lab_alerts(company_id: int, *, status: str = "", criticality: str = "", module: str = "") -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """
        SELECT id, empresa_id, titulo, descripcion, modulo_origen, registro_tipo, registro_id, responsable, criticidad,
               tipo, estado, fecha_deteccion, fecha_objetivo, accion_sugerida, requiere_ia, resultado_ia_json, evidencia_esperada
        FROM lab_ai_alertas
        WHERE empresa_id = ?
    """
    params: list[object] = [int(company_id)]
    if status:
        query += " AND lower(estado) = ?"
        params.append(str(status).strip().lower())
    if criticality:
        query += " AND lower(criticidad) = ?"
        params.append(str(criticality).strip().lower())
    if module:
        query += " AND lower(modulo_origen) = ?"
        params.append(str(module).strip().lower())
    query += " ORDER BY id DESC"
    c.execute(query, tuple(params))
    keys = ["id", "empresa_id", "titulo", "descripcion", "modulo_origen", "registro_tipo", "registro_id", "responsable", "criticidad", "tipo", "estado", "fecha_deteccion", "fecha_objetivo", "accion_sugerida", "requiere_ia", "resultado_ia_json", "evidencia_esperada"]
    rows = [dict(zip(keys, row)) for row in c.fetchall()]
    conn.close()
    return rows


def update_alert_status(alert_id: int, status: str, justification: str = "") -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "UPDATE lab_ai_alertas SET estado = ?, evidencia_esperada = COALESCE(NULLIF(evidencia_esperada,''), ?) , actualizado_en = ? WHERE id = ?",
        (str(status or "abierta"), str(justification or ""), _now(), int(alert_id)),
    )
    conn.commit()
    conn.close()
    return True, "Estado de alerta actualizado."


def run_rules_and_alert(company_id: int, *, record_type: str = "", record_id: int = 0, actor: str = "evento") -> dict:
    alerts = run_record_rules_check(record_type, int(record_id), int(company_id)) if record_type and record_id else run_lab_rules_check(int(company_id))
    created = 0
    ai_runs = 0
    for item in alerts:
        alert_id = _save_alert(int(company_id), item, created_by=actor)
        created += 1
        crit = str(item.get("criticidad") or "").lower()
        requires_ai = bool(item.get("requiere_ia")) or crit in {"alta", "critica"}
        if requires_ai:
            context = build_lab_ai_context(int(company_id), [item], {"alerta_id": alert_id})
            ai_result = analyze_with_lab_ai(context)
            _save_ai_result(int(company_id), int(alert_id), context, ai_result, actor=actor)
            ai_runs += 1
    return {"alerts_created": created, "ai_runs": ai_runs}

