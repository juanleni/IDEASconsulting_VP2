from __future__ import annotations

import httpx
from pydantic import BaseModel, Field
from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.output_parsers import PydanticOutputParser

from app.core.config import settings
from app.models.auditoria_ia import AuditoriaIA
from app.models.quality_report import QualityReport8D


class AuditoriaResultado(BaseModel):
    score: int = Field(ge=1, le=100)
    hallazgos: list[str] = Field(default_factory=list)
    aprobado: bool


class AuditorService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx.AsyncClient(trust_env=False),
        )
        self.parser = PydanticOutputParser(pydantic_object=AuditoriaResultado)

    async def evaluar_calidad_8d(self, session: AsyncSession, empresa_id: int, reporte_id: int) -> AuditoriaResultado:
        stmt = select(QualityReport8D).where(
            QualityReport8D.id == int(reporte_id),
            QualityReport8D.empresa_id == int(empresa_id),
        )
        result = await session.execute(stmt)
        reporte = result.scalar_one_or_none()
        if not reporte:
            raise ValueError("Reporte 8D no encontrado para este tenant.")

        prompt = (
            "Evalua coherencia tecnica 8D con enfoque industrial IATF/ISO.\n"
            "Debes evaluar si D5 ataca realmente la causa raiz D4 y si D2 esta bien definido.\n"
            f"D2 Problema:\n{reporte.d2_problema}\n\n"
            f"D4 Causa raiz:\n{reporte.d4_causa_raiz}\n\n"
            f"D5 Acciones:\n{reporte.d5_acciones}\n\n"
            f"Devuelve SOLO JSON valido con este formato:\n{self.parser.get_format_instructions()}"
        )
        response = await self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": "Actua como auditor senior automotriz. Minimiza alucinaciones."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=450,
        )
        raw = (response.choices[0].message.content or "").strip()
        parsed = self.parser.parse(raw)

        auditoria = AuditoriaIA(
            empresa_id=int(empresa_id),
            reporte_id=int(reporte_id),
            score=int(parsed.score),
            hallazgos=list(parsed.hallazgos),
            aprobado=bool(parsed.aprobado),
            raw_response=raw,
        )
        session.add(auditoria)
        await session.commit()
        return parsed
