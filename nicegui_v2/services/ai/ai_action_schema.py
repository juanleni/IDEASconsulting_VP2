from __future__ import annotations

from typing import Any


ALLOWED_INTENTS = {
    "create_task",
    "create_corrective_action",
    "create_audit_plan",
    "create_audit_checklist",
    "create_report_draft",
    "create_alert",
    "update_action_status",
    "update_task_status",
    "link_records",
}


def validate_action_plan(payload: dict[str, Any]) -> tuple[bool, str, dict[str, Any]]:
    if not isinstance(payload, dict):
        return False, "Plan de accion invalido.", {}
    intent = str(payload.get("intent") or "").strip()
    if intent not in ALLOWED_INTENTS:
        return False, "La accion solicitada no esta permitida en esta etapa.", {}
    title = str(payload.get("title") or "").strip() or "Accion propuesta por Smart IDEAS"
    summary = str(payload.get("summary") or "").strip()
    target_module = str(payload.get("target_module") or "").strip()
    risk_level = str(payload.get("risk_level") or "medium").strip().lower()
    if risk_level not in {"low", "medium", "high"}:
        risk_level = "medium"
    related_records = payload.get("related_records")
    related_records = related_records if isinstance(related_records, list) else []
    proposed_data = payload.get("proposed_data")
    proposed_data = proposed_data if isinstance(proposed_data, dict) else {}
    missing_fields = payload.get("missing_fields")
    missing_fields = [str(x) for x in missing_fields] if isinstance(missing_fields, list) else []
    user_message = str(payload.get("user_message") or "").strip()
    clean = {
        "intent": intent,
        "title": title,
        "summary": summary,
        "requires_confirmation": bool(payload.get("requires_confirmation", True)),
        "risk_level": risk_level,
        "target_module": target_module,
        "related_records": related_records[:20],
        "proposed_data": proposed_data,
        "missing_fields": missing_fields[:12],
        "user_message": user_message,
    }
    return True, "ok", clean
