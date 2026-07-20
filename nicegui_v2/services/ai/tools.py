from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ToolPlan:
    name: str
    description: str
    requires_confirmation: bool = True


def list_future_tools() -> list[dict[str, Any]]:
    plans = [
        ToolPlan("crear_accion_correctiva", "Crear accion correctiva en el modulo de calidad."),
        ToolPlan("generar_reporte_pdf", "Generar reporte PDF ejecutivo por modulo."),
        ToolPlan("crear_auditoria", "Crear auditoria interna con checklist base."),
        ToolPlan("crear_tarea", "Crear tarea operativa con responsable y fecha."),
        ToolPlan("generar_dashboard", "Sugerir o crear dashboard por objetivos."),
        ToolPlan("buscar_documentos", "Buscar documentos internos por clausula y tema."),
        ToolPlan("analizar_kpi", "Analizar desvio KPI y proponer plan."),
        ToolPlan("enviar_alerta", "Enviar alerta operativa segun riesgo."),
        ToolPlan("generar_procedimiento", "Generar borrador de procedimiento."),
        ToolPlan("revisar_vencimientos", "Detectar vencimientos y criticidad."),
    ]
    return [plan.__dict__ for plan in plans]
