from __future__ import annotations


DATA_CATALOG: dict[str, dict] = {
    "quality.corrective_actions": {"module": "quality", "label": "Acciones correctivas"},
    "risks.matrix": {"module": "risks", "label": "Matriz de riesgos"},
    "kpis.company": {"module": "kpi", "label": "KPIs"},
    "lab.calibrations": {"module": "lab_17025", "label": "Calibraciones"},
    "lab.iso17025": {"module": "lab_17025", "label": "Estado ISO 17025"},
    "environmental.indicators": {"module": "environment", "label": "Indicadores ambientales"},
    "documents.expiring": {"module": "documents", "label": "Documentos"},
    "alerts.company": {"module": "general", "label": "Alertas"},
}


def list_catalog_sources() -> list[str]:
    return list(DATA_CATALOG.keys())
