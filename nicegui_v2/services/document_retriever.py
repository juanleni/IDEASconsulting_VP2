from __future__ import annotations

from typing import Any

import httpx


class DocumentRetriever:
    """Wrapper simple para retrieval documental actual via endpoint RAG."""

    def __init__(self, rag_chat_url: str, timeout_seconds: float = 45.0) -> None:
        self.rag_chat_url = rag_chat_url
        self.timeout_seconds = timeout_seconds

    async def ask(self, *, jwt_token: str, question: str, module_key: str) -> dict[str, Any]:
        headers = {"Authorization": f"Bearer {jwt_token}"}
        payload = {"message": question, "module_key": module_key}
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(self.rag_chat_url, headers=headers, json=payload)
            if response.status_code == 422:
                response = await client.post(
                    self.rag_chat_url,
                    headers=headers,
                    json={"question": question, "module_key": module_key},
                )
            response.raise_for_status()
            return response.json()

