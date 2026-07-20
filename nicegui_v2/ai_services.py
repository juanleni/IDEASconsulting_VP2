from __future__ import annotations

import os
from datetime import datetime
from typing import Any

from nicegui import app

try:
    from services.ai import SmartIdeasAIService, build_ai_context, run_multi_agent_orchestration
except Exception:  # pragma: no cover
    from nicegui_v2.services.ai import SmartIdeasAIService, build_ai_context, run_multi_agent_orchestration


def _current_user_id() -> int | None:
    raw = app.storage.user.get("local_user_id") or app.storage.user.get("session_user_id")
    try:
        return int(raw) if raw else None
    except Exception:
        return None


def _current_user_name() -> str:
    return str(app.storage.user.get("session_user_name") or app.storage.user.get("username") or "").strip()


def _current_user_role() -> str:
    return str(app.storage.user.get("role") or "").strip().lower()


def _current_permissions() -> str:
    return str(app.storage.user.get("permisos") or "ALL").strip()


def _current_company_id_from_working_context(working_context: str | None) -> int | None:
    text = str(working_context or "")
    marker = "Empresa activa ID:"
    if marker not in text:
        return None
    tail = text.split(marker, 1)[-1].strip().splitlines()[0].strip()
    try:
        return int(tail)
    except Exception:
        return None


def _extract_enabled_modules() -> list[str] | None:
    enabled = app.storage.user.get("enabled_module_codes")
    if isinstance(enabled, list):
        return [str(item).strip() for item in enabled if str(item).strip()]
    user_id = _current_user_id()
    company_id = app.storage.user.get("logged_empresa_id") or app.storage.user.get("current_empresa_id")
    try:
        company_id = int(company_id) if company_id else None
    except Exception:
        company_id = None
    if user_id and company_id:
        try:
            from core_data import get_enabled_modules_for_user  # import local para evitar ciclos

            rows = get_enabled_modules_for_user(int(user_id), int(company_id))
            return [str(item.get("code") or "").strip() for item in rows if str(item.get("code") or "").strip()]
        except Exception:
            return None
    return None


def _service() -> SmartIdeasAIService:
    return SmartIdeasAIService(model=str(os.getenv("OPENAI_MODEL", "gpt-4o-mini")))


def _should_use_multi_agent(question: str, task_type: str | None = None) -> bool:
    text = f"{str(question or '').lower()} {str(task_type or '').lower()}"
    tokens = (
        "dashboard", "kpi", "riesgo", "auditor", "17025", "calibr", "mantenimiento",
        "indicador", "tendencia", "analisis", "estado general", "ejecutivo",
    )
    return any(t in text for t in tokens)


def suggest_dashboard_widget_with_ai(
    *,
    user_prompt: str,
    module_name: str,
    metric_catalog: list[tuple[str, str, int]],
    model: str | None = None,
) -> dict:
    _ = model
    return SmartIdeasAIService.suggest_dashboard_widget(
        user_prompt=str(user_prompt or "").strip(),
        module_name=str(module_name or "").strip() or "general",
        metric_catalog=metric_catalog or [],
    )


async def consultar_asistente_iso(
    mensaje_usuario: str,
    historial: list,
    module_context: str | None = None,
    module_key: str = "general",
    working_context: str | None = None,
    client_rules: dict | None = None,
    company_industry: str | None = None,
    memory_context: list | None = None,
    company_sources: list | None = None,
    task_type: str | None = None,
) -> str:
    _ = company_industry
    _ = company_sources
    company_id = _current_company_id_from_working_context(working_context) or app.storage.user.get("logged_empresa_id")
    try:
        company_id = int(company_id) if company_id else None
    except Exception:
        company_id = None
    focus_payload = ((app.storage.user.get("ai_focus_context") or {}).get("payload") or {})
    if isinstance(client_rules, dict) and client_rules:
        focus_payload["client_rules"] = client_rules
    normalized_question = str(mensaje_usuario or "").strip().lower()
    if normalized_question in {"que dia es hoy", "que día es hoy", "fecha de hoy", "hoy"} or "que dia es hoy" in normalized_question or "que día es hoy" in normalized_question:
        return f"Hoy es {datetime.now().strftime('%d/%m/%Y')}."

    if company_id and _should_use_multi_agent(mensaje_usuario, task_type):
        try:
            orchestration = await run_multi_agent_orchestration(
                question=str(mensaje_usuario or "").strip(),
                company_id=int(company_id),
                user_id=_current_user_id(),
                user_name=_current_user_name(),
                user_role=_current_user_role(),
                permissions=_current_permissions(),
                module_key=str(module_key or "general").strip().lower(),
                enabled_modules=_extract_enabled_modules(),
                working_context=str(working_context or ""),
                focus_payload=focus_payload,
            )
            summary = str(orchestration.get("summary") or "").strip()
            if summary:
                agents = ", ".join([str(a) for a in (orchestration.get("agents") or []) if str(a).strip()][:5])
                header = f"Smart IDEAS (multiagente: {agents})\n" if agents else "Smart IDEAS (multiagente)\n"
                return f"{header}{summary}"
        except Exception:
            pass

    return await _service().answer(
        question=str(mensaje_usuario or "").strip(),
        company_id=company_id,
        user_id=_current_user_id(),
        user_name=_current_user_name(),
        user_role=_current_user_role(),
        permissions=_current_permissions(),
        module_key=str(module_key or "general").strip().lower(),
        module_context=str(module_context or ""),
        enabled_modules=_extract_enabled_modules(),
        history=historial or [],
        memory_context=memory_context or [],
        working_context=str(working_context or ""),
        focus_payload=focus_payload,
        task_type=str(task_type or "general"),
        include_sources=True,
    )


def explicar_requisito_iso(norma, requisito, resumen, observacion_consultiva) -> str:
    company_id = app.storage.user.get("logged_empresa_id") or app.storage.user.get("current_empresa_id")
    try:
        company_id = int(company_id) if company_id else None
    except Exception:
        company_id = None
    if not company_id:
        return "No hay empresa activa para contextualizar esta explicacion."
    context = build_ai_context(
        user_id=_current_user_id(),
        company_id=int(company_id),
        module="documents",
        query=str(requisito or ""),
        user_name=_current_user_name(),
        user_role=_current_user_role(),
        permissions=_current_permissions(),
    )
    prompt = (
        "Explica este requisito para la empresa activa sin inventar datos.\n"
        f"Norma: {str(norma or '').strip()}\n"
        f"Requisito: {str(requisito or '').strip()}\n"
        f"Resumen: {str(resumen or '').strip()}\n"
        f"Guia consultiva: {str(observacion_consultiva or '').strip()}\n"
        f"Contexto: {context}"
    )
    try:
        return _service()._chat_text(
            "Eres Smart IDEAS y respondes en espanol profesional, con foco practico y fuente/modulo.",
            prompt,
        )
    except Exception:
        return "No pude generar la explicacion del requisito en este momento."


def sugerir_causas_ishikawa(problema, factores_retenidos) -> str:
    if isinstance(factores_retenidos, list):
        factores = ", ".join(str(item or "").strip() for item in factores_retenidos if str(item or "").strip())
    else:
        factores = str(factores_retenidos or "").strip()
    company_id = app.storage.user.get("logged_empresa_id") or app.storage.user.get("current_empresa_id")
    try:
        company_id = int(company_id) if company_id else None
    except Exception:
        company_id = None
    if not company_id:
        return "No hay empresa activa para generar sugerencias contextualizadas."
    context = build_ai_context(
        user_id=_current_user_id(),
        company_id=int(company_id),
        module="quality",
        query=str(problema or ""),
        user_name=_current_user_name(),
        user_role=_current_user_role(),
        permissions=_current_permissions(),
    )
    prompt = (
        "Genera 3 causas raiz para Ishikawa 6M y una validacion corta por cada una.\n"
        f"Problema: {str(problema or '').strip()}\n"
        f"Factores retenidos: {factores}\n"
        f"Contexto: {context}"
    )
    try:
        return _service()._chat_text(
            "Eres Smart IDEAS experto en calidad, no conformidades y 8D. Responde breve y accionable.",
            prompt,
        )
    except Exception:
        return "No pude generar causas Ishikawa en este momento."


def sugerir_matriz_legal_ia(rubro: str, ubicacion: str, aspectos_lista: list) -> list[dict]:
    aspectos = [str(item or "").strip() for item in (aspectos_lista or []) if str(item or "").strip()]
    company_id = app.storage.user.get("logged_empresa_id") or app.storage.user.get("current_empresa_id")
    try:
        company_id = int(company_id) if company_id else None
    except Exception:
        company_id = None
    if not company_id:
        return []
    import json

    context = build_ai_context(
        user_id=_current_user_id(),
        company_id=int(company_id),
        module="environment",
        query=f"{rubro} {ubicacion}",
        user_name=_current_user_name(),
        user_role=_current_user_role(),
        permissions=_current_permissions(),
    )
    raw = _service()._chat_text(
        "Eres Smart IDEAS ambiental. Devuelves exclusivamente JSON valido.",
        (
            "Genera una matriz legal ambiental inicial orientativa en JSON.\n"
            f"Rubro: {str(rubro or '').strip()}\n"
            f"Ubicacion: {str(ubicacion or '').strip()}\n"
            f"Aspectos ambientales: {', '.join(aspectos) if aspectos else 'No informados'}\n"
            "Devuelve una lista JSON de objetos con: norma_legal,jurisdiccion,articulo_aplicable,obligacion,"
            "responsable,frecuencia_control,evidencia.\n"
            f"Contexto: {context}"
        ),
    )
    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return [item for item in data if isinstance(item, dict)]
    except Exception:
        pass
    return []


__all__ = [
    "build_ai_context",
    "consultar_asistente_iso",
    "explicar_requisito_iso",
    "sugerir_causas_ishikawa",
    "sugerir_matriz_legal_ia",
    "suggest_dashboard_widget_with_ai",
]
