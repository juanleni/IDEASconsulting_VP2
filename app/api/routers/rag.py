from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, UploadFile
from openai import APIConnectionError, APIError, AuthenticationError, RateLimitError
from pydantic import BaseModel, Field, model_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai_agents.rag_engine import RAGEngine
from app.api.deps.auth import get_current_tenant
from app.db.session import get_db_session

router = APIRouter(prefix="/rag", tags=["rag"])


class RAGChatRequest(BaseModel):
    question: str | None = Field(default=None, min_length=2)
    message: str | None = Field(default=None, min_length=2)
    module_key: str = Field(default="general", min_length=2, max_length=80)
    k: int = Field(default=6, ge=1, le=20)
    allow_external: bool = Field(default=True)

    @model_validator(mode="after")
    def require_question_or_message(self) -> "RAGChatRequest":
        if not (self.question or self.message):
            raise ValueError("question o message es requerido.")
        return self

    @property
    def prompt(self) -> str:
        return str(self.question or self.message or "").strip()


class RAGChatResponse(BaseModel):
    answer: str
    sources: list[dict] = Field(default_factory=list)


class RAGIngestResponse(BaseModel):
    chunks: int


@router.post("/ingest", response_model=RAGIngestResponse)
async def ingest_pdf(
    file: UploadFile = File(...),
    source_name: str | None = Form(default=None),
    module_key: str = Form(default="general"),
    empresa_id: int = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> RAGIngestResponse:
    suffix = Path(file.filename or "doc.pdf").suffix or ".pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        engine = RAGEngine()
        count = await engine.ingest_pdf(
            session=session,
            empresa_id=empresa_id,
            file_path=tmp_path,
            source_name=source_name or file.filename,
            module_key=module_key,
        )
        return RAGIngestResponse(chunks=count)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@router.post("/chat", response_model=RAGChatResponse)
async def rag_chat(
    payload: RAGChatRequest,
    empresa_id: int = Depends(get_current_tenant),
    session: AsyncSession = Depends(get_db_session),
) -> RAGChatResponse:
    engine = RAGEngine()
    try:
        result = await engine.chat(
            session=session,
            empresa_id=empresa_id,
            question=payload.prompt,
            k=payload.k,
            module_key=payload.module_key,
            allow_external=payload.allow_external,
        )
    except AuthenticationError:
        return RAGChatResponse(
            answer=(
                "Smart Assist no pudo validar la clave de OpenAI configurada. "
                "Revisa OPENAI_API_KEY y vuelve a intentar."
            ),
            sources=[],
        )
    except RateLimitError:
        return RAGChatResponse(
            answer=(
                "Smart Assist esta temporalmente limitado por cuota o rate limit del proveedor IA. "
                "Reintenta en unos minutos."
            ),
            sources=[],
        )
    except APIConnectionError:
        return RAGChatResponse(
            answer=(
                "Smart Assist no pudo conectarse al motor IA para consultar embeddings y documentos. "
                "La sesion esta activa, pero falta conectividad saliente hacia OpenAI o el servicio esta bloqueado."
            ),
            sources=[],
        )
    except APIError:
        return RAGChatResponse(
            answer="Smart Assist recibio un error temporal del proveedor IA. Reintenta en unos minutos.",
            sources=[],
        )
    return RAGChatResponse(answer=result.answer, sources=result.sources)
