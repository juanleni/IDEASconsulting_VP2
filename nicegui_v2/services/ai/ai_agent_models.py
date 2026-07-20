from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class AIAgentTask:
    question: str
    company_id: int
    user_id: int | None
    module_key: str
    allowed_agents: list[str] = field(default_factory=list)


@dataclass(slots=True)
class AIAgentResponse:
    agent_key: str
    title: str
    summary: str
    highlights: list[str]
    sources: list[str]
    payload: dict[str, Any]
