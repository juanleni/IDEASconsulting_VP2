from __future__ import annotations

from typing import Any

from services.dashboard.dashboard_service import get_data_sources_for_company


def assert_company_scope(company_id: int | None) -> int:
    if not company_id:
        raise ValueError("No hay empresa activa.")
    return int(company_id)


def validate_user_permission(user_permissions: str, required: str = "") -> bool:
    perms = str(user_permissions or "ALL").strip()
    if perms == "ALL":
        return True
    if not required:
        return True
    tokens = {x.strip() for x in perms.split(",") if x.strip()}
    return required in tokens


def validate_module_access(module_key: str, enabled_modules: list[str] | None) -> bool:
    normalized_key = str(module_key or "general").strip().lower()
    if normalized_key in {"", "general", "smart_ideas", "ai_command_center"}:
        return True
    if not enabled_modules:
        return True
    normalized = {str(x).strip().lower() for x in enabled_modules if str(x).strip()}
    return normalized_key in normalized or "general" in normalized


def filter_by_company_id(*, company_id: int, module_key: str, user_permissions: str) -> dict[str, Any]:
    return get_data_sources_for_company(
        int(company_id),
        module_key=str(module_key or "general"),
        user_permissions=str(user_permissions or "ALL"),
    )
