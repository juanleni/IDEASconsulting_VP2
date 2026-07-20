from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from sqlalchemy import select

from app.ai_agents.rag_engine import RAGEngine
from app.db.session import AsyncSessionLocal
from app.models.empresa import Empresa


async def get_or_create_empresa(razon_social: str) -> Empresa:
    async with AsyncSessionLocal() as session:
        stmt = select(Empresa).where(Empresa.razon_social == razon_social)
        result = await session.execute(stmt)
        empresa = result.scalar_one_or_none()
        if empresa:
            return empresa

        empresa = Empresa(razon_social=razon_social, is_active=True)
        session.add(empresa)
        await session.commit()
        await session.refresh(empresa)
        return empresa


async def run(pdf_path: str, empresa_nombre: str, question: str, k: int, module_key: str) -> None:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"No existe el PDF: {path}")

    empresa = await get_or_create_empresa(empresa_nombre)
    engine = RAGEngine()

    async with AsyncSessionLocal() as session:
        chunks = await engine.ingest_pdf(
            session=session,
            empresa_id=int(empresa.id),
            file_path=str(path),
            source_name=path.name,
            module_key=module_key,
        )
        print(f"[OK] Chunks insertados: {chunks} (empresa_id={empresa.id}, module_key={module_key})")

    async with AsyncSessionLocal() as session:
        retrieved = await engine.retrieve(
            session=session,
            empresa_id=int(empresa.id),
            question=question,
            k=k,
            module_key=module_key,
        )
        print(f"[OK] Chunks recuperados: {len(retrieved)}")
        for idx, item in enumerate(retrieved, start=1):
            preview = item.content.replace("\n", " ").strip()[:140]
            print(f"  {idx}. score={item.score:.4f} source={item.metadata_json.get('source')} :: {preview}")

    async with AsyncSessionLocal() as session:
        answer = await engine.chat(
            session=session,
            empresa_id=int(empresa.id),
            question=question,
            k=k,
            module_key=module_key,
        )
        print("\n[RESPUESTA RAG]\n")
        print(answer.answer)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Smoke test de RAG multi-tenant por empresa_id.")
    parser.add_argument(
        "--pdf",
        default="Biblioteca/ISO 9001 2015.pdf",
        help="Ruta al PDF a ingerir.",
    )
    parser.add_argument(
        "--empresa",
        default="Empresa Demo RAG",
        help="Razon social de empresa para aislar la memoria.",
    )
    parser.add_argument(
        "--pregunta",
        default="Que dice la norma sobre contexto de la organizacion?",
        help="Pregunta a evaluar con RAG.",
    )
    parser.add_argument(
        "--k",
        type=int,
        default=4,
        help="Top-K de fragmentos a recuperar.",
    )
    parser.add_argument(
        "--module-key",
        default="quality_8d",
        help="Modulo al que se asociara la memoria documental.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(run(args.pdf, args.empresa, args.pregunta, args.k, args.module_key))
