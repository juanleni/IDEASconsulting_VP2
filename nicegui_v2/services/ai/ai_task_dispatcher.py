from __future__ import annotations

from typing import Any

from .ai_agent_models import AIAgentResponse


def dispatch_task_to_agent(*, agent: Any, context: dict[str, Any], data_sources: dict[str, Any], question: str) -> AIAgentResponse:
    result = agent.run(context=context, data_sources=data_sources, question=question)
    return AIAgentResponse(
        agent_key=str(result.agent_key),
        title=str(result.title),
        summary=str(result.summary),
        highlights=[str(x) for x in (result.highlights or [])][:6],
        sources=[str(x) for x in (result.sources or [])][:8],
        payload=result.payload if isinstance(result.payload, dict) else {},
    )
