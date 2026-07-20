from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from core_data import (
    obtener_acciones_8d,
    obtener_aspectos_ambientales_empresa,
    obtener_fuentes_empresa,
    obtener_items_riesgos_matriz,
    obtener_kpis_empresa,
    obtener_lab_alertas_empresa,
    obtener_lab_calibraciones_empresa,
    obtener_lab_dashboard_empresa,
    obtener_lab_informes_empresa,
    obtener_matrices_riesgos_empresa,
    obtener_problemas_calidad_empresa,
)


_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "ai_dashboards.json"


def load_saved_dashboards(module_key: str, company_id: int) -> list[dict]:
    if not _STORE_PATH.exists():
        return []
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return []
    key = f"{module_key}:{int(company_id)}"
    rows = data.get(key) if isinstance(data, dict) else []
    return rows if isinstance(rows, list) else []


def save_dashboard(module_key: str, company_id: int, item: dict) -> None:
    data: dict[str, Any] = {}
    if _STORE_PATH.exists():
        try:
            raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            data = {}
    key = f"{module_key}:{int(company_id)}"
    rows = data.get(key) if isinstance(data.get(key), list) else []
    rows.append(item)
    data[key] = rows[-20:]
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def delete_dashboard(module_key: str, company_id: int, index: int) -> None:
    rows = load_saved_dashboards(module_key, company_id)
    if 0 <= index < len(rows):
        rows.pop(index)
    data: dict[str, Any] = {}
    if _STORE_PATH.exists():
        try:
            raw = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                data = raw
        except Exception:
            data = {}
    data[f"{module_key}:{int(company_id)}"] = rows
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _to_date_lex(value: Any) -> str:
    return str(value or "").strip()


def get_data_sources_for_company(company_id: int, module_key: str, user_permissions: str = "ALL") -> dict[str, Any]:
    _ = module_key
    _ = user_permissions
    kpis = obtener_kpis_empresa(int(company_id)) or []
    riesgos = obtener_matrices_riesgos_empresa(int(company_id)) or []
    riesgo_items = []
    for matrix in riesgos[:8]:
        mid = int(matrix.get("id") or 0)
        if mid:
            riesgo_items.extend(obtener_items_riesgos_matriz(mid) or [])

    casos = obtener_problemas_calidad_empresa(int(company_id)) or []
    acciones_rows = []
    for caso in casos[:12]:
        pid = int(caso.get("id") or 0)
        if pid:
            acciones_rows.extend(obtener_acciones_8d(pid) or [])

    calibraciones = obtener_lab_calibraciones_empresa(int(company_id)) or []
    informes = obtener_lab_informes_empresa(int(company_id)) or []
    alertas = obtener_lab_alertas_empresa(int(company_id)) or []
    aspectos = obtener_aspectos_ambientales_empresa(int(company_id)) or []
    fuentes = obtener_fuentes_empresa(int(company_id)) or []
    lab = obtener_lab_dashboard_empresa(int(company_id)) or {}

    overdue_acciones = [
        item
        for item in acciones_rows
        if str(item.get("fase_8d") or "") in {"D5", "D6", "D3"}
        and _to_date_lex(item.get("fecha_limite")) != ""
    ]
    overdue_acciones = sorted(overdue_acciones, key=lambda i: _to_date_lex(i.get("fecha_limite")))

    by_process: dict[str, int] = {}
    for row in riesgo_items:
        proc = str(row.get("proceso") or "Sin proceso").strip()
        by_process[proc] = by_process.get(proc, 0) + 1

    cal_status = {"vencidas": 0, "proximas": 0, "vigentes": 0}
    for row in calibraciones:
        estado = str(row.get("estado") or "").lower()
        if "venc" in estado:
            cal_status["vencidas"] += 1
        elif "proxim" in estado:
            cal_status["proximas"] += 1
        else:
            cal_status["vigentes"] += 1

    return {
        "quality.corrective_actions": {
            "open_count": len(acciones_rows),
            "overdue_count": len(overdue_acciones),
            "overdue": overdue_acciones[:40],
            "by_status": _count_by_key(acciones_rows, "progreso"),
            "by_phase": _count_by_key(acciones_rows, "fase_8d"),
        },
        "risks.matrix": {
            "total_matrices": len(riesgos),
            "total_items": len(riesgo_items),
            "critical_items": [r for r in riesgo_items if int(r.get("npr") or 0) >= 18][:50],
            "by_process": [{"process": k, "count": v} for k, v in sorted(by_process.items(), key=lambda x: x[1], reverse=True)[:20]],
        },
        "kpis.company": {
            "total": len(kpis),
            "rows": kpis[:60],
            "by_process": _count_by_key(kpis, "proceso"),
        },
        "lab.calibrations": {
            "total": len(calibraciones),
            "status": cal_status,
            "rows": calibraciones[:60],
        },
        "lab.iso17025": {
            "score_general": lab.get("score_general_iso_17025"),
            "semaforo": lab.get("semaforo_general"),
            "alertas_abiertas": len([a for a in alertas if str(a.get("estado") or "").lower() not in {"cerrada", "descartada"}]),
            "informes": len(informes),
        },
        "environmental.indicators": {
            "aspectos": len(aspectos),
            "rows": aspectos[:60],
        },
        "documents.expiring": {
            "total_sources": len(fuentes),
            "rows": [{"titulo": str(x.get("titulo") or ""), "tipo": str(x.get("tipo") or ""), "fecha_carga": str(x.get("fecha_carga") or "")} for x in fuentes[:50]],
        },
        "alerts.company": {
            "open": [a for a in alertas if str(a.get("estado") or "").lower() not in {"cerrada", "descartada"}][:60],
            "by_criticality": _count_by_key(alertas, "criticidad"),
        },
    }


def _count_by_key(rows: list[dict], key: str) -> list[dict]:
    counts: dict[str, int] = {}
    for row in rows:
        value = str(row.get(key) or "Sin dato").strip()
        counts[value] = counts.get(value, 0) + 1
    return [{"label": k, "count": v} for k, v in sorted(counts.items(), key=lambda x: x[1], reverse=True)]
