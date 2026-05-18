from __future__ import annotations

from typing import Any

from core_data import guardar_evento_memoria_asistente, obtener_memoria_asistente_empresa


class ChatHistoryRepository:
    """Persistencia de historial por empresa + usuario (sin mezclar contextos)."""

    def save_exchange(
        self,
        *,
        empresa_id: int,
        user_key: str,
        module_context: str,
        question: str,
        answer: str,
        context_snapshot: str = "",
    ) -> None:
        guardar_evento_memoria_asistente(
            int(empresa_id),
            "user",
            str(question or ""),
            module_context=module_context,
            context_snapshot=context_snapshot,
            user_key=user_key,
        )
        guardar_evento_memoria_asistente(
            int(empresa_id),
            "assistant",
            str(answer or ""),
            module_context=module_context,
            context_snapshot=context_snapshot,
            user_key=user_key,
        )

    def list_recent(
        self,
        *,
        empresa_id: int,
        user_key: str | None = None,
        module_context: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        return obtener_memoria_asistente_empresa(
            int(empresa_id),
            limite=max(1, int(limit)),
            user_key=(user_key or None),
            module_context=(module_context or None),
        )

