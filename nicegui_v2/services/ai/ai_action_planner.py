from __future__ import annotations

import re
from typing import Any

from .ai_action_schema import validate_action_plan


def _infer_intent(text: str) -> str:
    t = str(text or "").strip().lower()
    if any(k in t for k in ("accion correctiva", "acción correctiva", "no conformidad")):
        return "create_corrective_action"
    if any(k in t for k in ("auditoria", "auditoría")) and any(k in t for k in ("checklist", "lista")):
        return "create_audit_checklist"
    if any(k in t for k in ("auditoria", "auditoría")):
        return "create_audit_plan"
    if any(k in t for k in ("reporte", "informe ejecutivo", "minuta")):
        return "create_report_draft"
    if any(k in t for k in ("alerta", "vencer", "vencimiento")):
        return "create_alert"
    if any(k in t for k in ("actualiza", "actualizar", "cambia estado", "estado de esta accion", "estado de esta acción")):
        return "update_action_status"
    if any(k in t for k in ("vincula", "relaciona", "link")):
        return "link_records"
    if any(k in t for k in ("tarea", "task", "plan de accion", "plan de acción")):
        return "create_task"
    return ""


def _default_module(intent: str, module_key: str) -> str:
    mapping = {
        "create_corrective_action": "quality.corrective_actions",
        "create_task": "lab.tasks",
        "create_audit_plan": "quality.audits",
        "create_audit_checklist": "quality.audits",
        "create_report_draft": "reports.executive",
        "create_alert": "alerts.company",
        "update_action_status": "quality.corrective_actions",
        "update_task_status": "lab.tasks",
        "link_records": "records.links",
    }
    return mapping.get(intent, f"{module_key or 'general'}.workflow")


def build_action_plan(
    *,
    user_text: str,
    module_key: str,
    company_id: int,
    related_context: dict[str, Any] | None = None,
) -> tuple[bool, str, dict[str, Any]]:
    _ = company_id
    intent = _infer_intent(user_text)
    if not intent:
        return False, "No se detecto una accion ejecutable en esta consulta.", {}
    due_date = ""
    m_date = re.search(r"\b(\d{4}-\d{2}-\d{2}|\d{2}/\d{2}/\d{4})\b", str(user_text))
    if m_date:
        due_date = m_date.group(1)
    proposed = {
        "intent": intent,
        "title": f"Smart IDEAS: {intent.replace('_', ' ')}",
        "summary": str(user_text or "").strip()[:220],
        "requires_confirmation": True,
        "risk_level": "medium",
        "target_module": _default_module(intent, module_key),
        "related_records": (related_context or {}).get("records") if isinstance((related_context or {}).get("records"), list) else [],
        "proposed_data": {
            "description": str(user_text or "").strip(),
            "responsible": None,
            "due_date": due_date or None,
            "priority": "high" if any(k in str(user_text).lower() for k in ("critico", "crítico", "urgente", "vencid")) else "medium",
            "status": "draft",
        },
        "missing_fields": ["responsible"] + ([] if due_date else ["due_date"]),
        "user_message": "Preparé una propuesta. Revisa, completa faltantes y confirma para ejecutar.",
    }
    return validate_action_plan(proposed)
