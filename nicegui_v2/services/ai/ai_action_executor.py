from __future__ import annotations

from datetime import datetime
from typing import Any

from core_data import (
    can_user_access_module,
    crear_lab_accion,
    crear_lab_auditoria,
    crear_lab_informe,
    crear_lab_riesgo,
    crear_requisito_legal_ambiental,
    obtener_lab_acciones_empresa,
)

from .ai_audit_trail import write_ai_action_log


def _module_access_code(target_module: str) -> str:
    t = str(target_module or "").lower()
    if "quality" in t:
        return "quality"
    if "risk" in t:
        return "risks"
    if "env" in t:
        return "environment"
    if "sst" in t:
        return "sst"
    if "lab" in t:
        return "lab_17025"
    if "doc" in t:
        return "documents"
    if "kpi" in t:
        return "kpi"
    return "documents"


def _authorized(*, user_id: int | None, company_id: int, role: str, target_module: str) -> bool:
    if str(role or "").lower() == "admin":
        return True
    if not user_id:
        return False
    code = _module_access_code(target_module)
    try:
        return bool(can_user_access_module(int(user_id), int(company_id), code))
    except Exception:
        return False


def execute_ai_action(
    *,
    plan: dict[str, Any],
    company_id: int,
    user_id: int | None,
    user_key: str,
    role: str,
    prompt_original: str,
    confirmed: bool,
) -> tuple[bool, str, dict[str, Any]]:
    intent = str(plan.get("intent") or "")
    if not confirmed:
        return False, "La accion requiere confirmacion explicita.", {}
    if not _authorized(user_id=user_id, company_id=int(company_id), role=role, target_module=str(plan.get("target_module") or "")):
        return False, "No tienes permisos para ejecutar esta accion.", {}

    pd = plan.get("proposed_data") or {}
    payload_desc = str(pd.get("description") or "").strip()
    responsible = str(pd.get("responsible") or "").strip()
    due_date = str(pd.get("due_date") or "").strip()
    priority = str(pd.get("priority") or "medium").strip()
    if not responsible or not due_date:
        return False, "Faltan campos obligatorios: responsable y fecha objetivo.", {}

    result: dict[str, Any] = {}
    ok = False
    msg = ""
    try:
        if intent in {"create_task", "create_corrective_action"}:
            ok, msg, new_id = crear_lab_accion(
                int(company_id),
                {
                    "origen": "Smart IDEAS",
                    "descripcion": payload_desc,
                    "accion_correctiva": payload_desc,
                    "responsable": responsible,
                    "vencimiento": due_date,
                    "estado": "abierta",
                    "eficacia": priority,
                    "creado_por": user_key or "smart_ideas",
                },
            )
            result = {"record_type": "lab_acciones_correctivas", "record_id": new_id}
        elif intent in {"create_audit_plan", "create_audit_checklist"}:
            ok, msg, new_id = crear_lab_auditoria(
                int(company_id),
                {
                    "clausula": str(plan.get("target_module") or "ISO"),
                    "pregunta": payload_desc or "Checklist de auditoria generado por Smart IDEAS",
                    "responsable": responsible,
                    "fecha": due_date,
                    "estado": "abierta",
                    "creado_por": user_key or "smart_ideas",
                },
            )
            result = {"record_type": "lab_auditorias", "record_id": new_id}
        elif intent == "create_report_draft":
            ok, msg, new_id = crear_lab_informe(
                int(company_id),
                {
                    "numero_informe": f"AI-{datetime.now().strftime('%Y%m%d%H%M')}",
                    "cliente": "Interno",
                    "muestra": "-",
                    "metodo": "Smart IDEAS",
                    "resultado": payload_desc,
                    "responsable_tecnico": responsible,
                    "estado": "borrador",
                    "emision": due_date,
                    "observaciones": payload_desc,
                    "creado_por": user_key or "smart_ideas",
                },
            )
            result = {"record_type": "lab_informes", "record_id": new_id}
        elif intent == "create_alert":
            ok, msg, new_id = crear_lab_accion(
                int(company_id),
                {
                    "origen": "Alerta IA",
                    "descripcion": payload_desc or "Alerta creada por Smart IDEAS",
                    "accion_inmediata": payload_desc or "Revisar condición de alerta",
                    "accion_correctiva": payload_desc or "Definir acción correctiva",
                    "responsable": responsible,
                    "vencimiento": due_date,
                    "estado": "abierta",
                    "eficacia": priority,
                    "creado_por": user_key or "smart_ideas",
                },
            )
            result = {"record_type": "lab_acciones_correctivas", "record_id": new_id}
        elif intent == "update_action_status":
            acciones = obtener_lab_acciones_empresa(int(company_id)) or []
            target = acciones[0] if acciones else None
            if not target:
                ok, msg = False, "No hay acciones disponibles para actualizar."
            else:
                ok, msg, _new_id = crear_requisito_legal_ambiental(  # registro de actualización controlado como nota de trazabilidad
                    int(company_id),
                    "Interno",
                    f"Update IA accion #{int(target.get('id') or 0)}",
                    "estado",
                    "En tratamiento",
                    due_date,
                    responsible,
                )
                result = {"record_type": "action_status_note", "record_id": int(target.get("id") or 0)}
        elif intent == "link_records":
            ok, msg, new_id = crear_lab_riesgo(
                int(company_id),
                {
                    "proceso": "Smart IDEAS Link",
                    "riesgo": payload_desc or "Vinculo de registros",
                    "causa": "Relacion IA",
                    "consecuencia": "Seguimiento unificado",
                    "probabilidad": 1,
                    "severidad": 1,
                    "accion": "Revisar enlace creado por IA",
                    "responsable": responsible,
                    "estado": "abierto",
                    "creado_por": user_key or "smart_ideas",
                },
            )
            result = {"record_type": "link_note", "record_id": new_id}
        else:
            return False, "Intent no permitido para ejecución.", {}
    except Exception:
        ok, msg = False, "No se pudo ejecutar la acción en este momento."

    write_ai_action_log(
        company_id=int(company_id),
        user_id=user_id,
        user_key=user_key,
        intent=intent,
        action_name=intent,
        prompt_original=prompt_original,
        proposal=plan,
        execution=result,
        status="success" if ok else "error",
        error_text="" if ok else msg,
        confirmed_by_user=True,
    )
    return ok, msg, result
