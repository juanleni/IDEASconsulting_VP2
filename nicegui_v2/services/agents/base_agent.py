from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class AgentResult:
    agent_key: str
    title: str
    summary: str
    highlights: list[str]
    sources: list[str]
    payload: dict[str, Any]


class BaseDomainAgent:
    agent_key = "generic"
    title = "Agente IA"
    data_domains: tuple[str, ...] = tuple()

    def run(self, *, context: dict[str, Any], data_sources: dict[str, Any], question: str) -> AgentResult:
        _ = context
        _ = question
        snippets: list[str] = []
        sources: list[str] = []
        payload: dict[str, Any] = {}
        for key in self.data_domains:
            if key in data_sources:
                sources.append(key)
                payload[key] = data_sources.get(key)
                item = data_sources.get(key)
                if isinstance(item, dict):
                    snippets.append(f"{key}: {len(item)} indicadores resumidos.")
                elif isinstance(item, list):
                    snippets.append(f"{key}: {len(item)} registros.")
        summary = " | ".join(snippets) if snippets else "Sin datos suficientes para este dominio."
        return AgentResult(
            agent_key=self.agent_key,
            title=self.title,
            summary=summary,
            highlights=snippets[:4],
            sources=sources,
            payload=payload,
        )
