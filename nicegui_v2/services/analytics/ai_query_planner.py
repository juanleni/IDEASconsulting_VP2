from __future__ import annotations


def plan_sources_from_query(query: str) -> list[str]:
    text = str(query or "").lower()
    picked: list[str] = []
    mapping = [
        ("quality.corrective_actions", ("accion", "correctiva", "nc", "8d")),
        ("risks.matrix", ("riesgo", "criticidad", "matriz")),
        ("kpis.company", ("kpi", "indicador", "tendencia", "dashboard", "ejecutivo")),
        ("lab.calibrations", ("calibr", "equipo", "mantenimiento")),
        ("lab.iso17025", ("17025", "laboratorio", "iso 17025", "lab")),
        ("environmental.indicators", ("ambient", "emision", "residuo")),
        ("documents.expiring", ("documento", "vencimiento", "procedimiento")),
        ("alerts.company", ("alerta", "vencid", "prioridad")),
    ]
    for source, tokens in mapping:
        if any(t in text for t in tokens):
            picked.append(source)
    if not picked:
        picked = ["kpis.company", "risks.matrix", "quality.corrective_actions", "alerts.company"]
    seen: set[str] = set()
    return [x for x in picked if not (x in seen or seen.add(x))]
