from __future__ import annotations

from typing import Any

from services.dashboard.dashboard_service import get_data_sources_for_company

from .agent_memory import push_memory, read_memory
from .agent_registry import build_agent_registry
from .agent_router import route_agents
from .ai_task_dispatcher import dispatch_task_to_agent
from .multi_agent_context import build_multi_agent_context
from .response_synthesizer import synthesize_multi_agent_response


async def run_multi_agent_orchestration(
    *,
    question: str,
    company_id: int,
    user_id: int | None,
    user_name: str = "",
    user_role: str = "",
    permissions: str = "ALL",
    module_key: str = "general",
    enabled_modules: list[str] | None = None,
    working_context: str = "",
    focus_payload: dict | None = None,
) -> dict[str, Any]:
    registry = build_agent_registry()
    routed = route_agents(question, module_key=module_key, max_agents=4)
    context = build_multi_agent_context(
        company_id=company_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        permissions=permissions,
        module_key=module_key,
        question=question,
        enabled_modules=enabled_modules,
        working_context=working_context,
        focus_payload=focus_payload,
    )
    data_sources = get_data_sources_for_company(int(company_id), module_key, permissions)
    outputs: list[dict[str, Any]] = []
    for key in routed:
        agent = registry.get(key)
        if not agent:
            continue
        result = dispatch_task_to_agent(
            agent=agent,
            context=context,
            data_sources=data_sources,
            question=question,
        )
        outputs.append(
            {
                "agent_key": result.agent_key,
                "title": result.title,
                "summary": result.summary,
                "highlights": result.highlights,
                "sources": result.sources,
                "payload": result.payload,
            }
        )
    memory = read_memory(company_id=company_id, user_id=user_id, limit=6)
    summary = await synthesize_multi_agent_response(
        question=question,
        agent_outputs=outputs,
        company_id=company_id,
        user_id=user_id,
        user_name=user_name,
        user_role=user_role,
        permissions=permissions,
        module_key=module_key,
        enabled_modules=enabled_modules,
        working_context=working_context,
        focus_payload=focus_payload,
    )
    push_memory(
        company_id=company_id,
        user_id=user_id,
        item={"question": question, "agents": routed, "summary": str(summary or "")[:1200]},
    )
    return {
        "orchestrator": "smart_ideas",
        "agents": routed,
        "agent_outputs": outputs,
        "memory_hits": len(memory),
        "summary": summary,
    }
