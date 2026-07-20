from __future__ import annotations

from typing import Any

from .service import SmartIdeasAIService


async def synthesize_multi_agent_response(
    *,
    question: str,
    agent_outputs: list[dict[str, Any]],
    company_id: int,
    user_id: int | None,
    user_name: str,
    user_role: str,
    permissions: str,
    module_key: str,
    enabled_modules: list[str] | None,
    working_context: str,
    focus_payload: dict | None,
) -> str:
    bullets: list[str] = []
    for item in agent_outputs:
        bullets.append(
            f"- {item.get('title', 'Agente')}: {item.get('summary', 'Sin resumen')} (fuentes: {', '.join(item.get('sources') or ['N/D'])})"
        )
    pre_context = (
        "Sintetiza este analisis multiagente en formato ejecutivo:\n"
        f"Consulta: {question}\n"
        f"Hallazgos:\n{chr(10).join(bullets)}\n"
        "Incluye: estado general, riesgos, prioridades y siguientes pasos."
    )
    return await SmartIdeasAIService().answer(
        question=pre_context,
        company_id=company_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        permissions=permissions,
        module_key=module_key,
        enabled_modules=enabled_modules,
        working_context=working_context,
        focus_payload=focus_payload,
        include_sources=True,
    )
