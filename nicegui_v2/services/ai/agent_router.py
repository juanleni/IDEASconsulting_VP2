from __future__ import annotations


ROUTING_RULES: list[tuple[str, tuple[str, ...]]] = [
    ("lab", ("17025", "calibr", "ensayo", "laboratorio", "incertid")),
    ("quality", ("nc", "no conform", "8d", "correctiva", "iatf", "9001", "vda")),
    ("environmental", ("ambient", "emision", "residuo", "14001", "sustent")),
    ("safety", ("seguridad", "incidente", "iper", "45001", "accidente")),
    ("risk", ("riesgo", "criticidad", "matriz")),
    ("maintenance", ("mantenimiento", "mtbf", "mttr", "preventiv", "predictiv")),
    ("audit", ("auditor", "hallazgo", "finding", "compliance")),
    ("kpi", ("kpi", "indicador", "dashboard", "tendencia", "analit")),
    ("workflow", ("alerta", "workflow", "regla", "automatiz", "tarea")),
    ("builder", ("builder", "formulario", "modulo", "automatizacion")),
    ("executive", ("ejecutivo", "direccion", "gerencial", "resumen")),
]


def route_agents(question: str, module_key: str = "general", max_agents: int = 4) -> list[str]:
    text = f"{str(question or '').lower()} {str(module_key or '').lower()}"
    picked: list[str] = []
    for agent_key, tokens in ROUTING_RULES:
        if any(token in text for token in tokens):
            picked.append(agent_key)
    if not picked:
        picked = ["executive", "kpi"]
    if "executive" not in picked:
        picked.append("executive")
    seen: set[str] = set()
    dedup = [a for a in picked if not (a in seen or seen.add(a))]
    return dedup[: max(1, int(max_agents))]
