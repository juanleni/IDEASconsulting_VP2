from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from services.document_retriever import DocumentRetriever
from services.prompt_builder import build_documental_system_prompt, build_documental_user_prompt


@dataclass
class AgentContext:
    company_context: str
    history_context: str
    memory_context: str
    sources_context: str
    module_focus: str
    response_mode: str
    extra_rules: dict[str, Any]


class SmartIdeasDocumentalAgent:
    """Orquestador base para evolucionar el asistente sin reescribir la app."""

    def __init__(self, *, retriever: DocumentRetriever) -> None:
        self.retriever = retriever

    def build_prompts(self, question: str, context: AgentContext) -> tuple[str, str]:
        system_prompt = build_documental_system_prompt(
            agent_name="Smart IdeAs Documental",
            module_focus=context.module_focus,
            response_mode=context.response_mode,
        )
        user_prompt = build_documental_user_prompt(
            user_question=question,
            company_context=context.company_context,
            memory_context=context.memory_context,
            history_context=context.history_context,
            internal_sources_context=context.sources_context,
            extra_rules=context.extra_rules,
        )
        return system_prompt, user_prompt

