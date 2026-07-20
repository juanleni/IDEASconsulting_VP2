from __future__ import annotations

from typing import Any

from .context_builder import build_ai_context


def build_multi_agent_context(
    *,
    company_id: int,
    user_id: int | None,
    user_name: str,
    user_role: str,
    permissions: str,
    module_key: str,
    question: str,
    enabled_modules: list[str] | None,
    working_context: str = "",
    focus_payload: dict | None = None,
) -> dict[str, Any]:
    return build_ai_context(
        user_id=user_id,
        company_id=company_id,
        module=module_key or "general",
        query=question,
        user_name=user_name,
        user_role=user_role,
        permissions=permissions,
        module_whitelist=enabled_modules,
        working_context=working_context,
        focus_payload=focus_payload,
    )
