from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from urllib.parse import quote, unquote, urlparse, parse_qs

from langchain_text_splitters import RecursiveCharacterTextSplitter
import httpx
from openai import AsyncOpenAI
from pypdf import PdfReader
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.document_chunk import DocumentChunk


@dataclass
class RetrievedChunk:
    id: int
    content: str
    score: float
    metadata_json: dict


@dataclass
class RAGAnswer:
    answer: str
    sources: list[dict]


class RAGEngine:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            http_client=httpx.AsyncClient(trust_env=False),
        )
        self.splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)

    @staticmethod
    def _strip_html(text: str) -> str:
        value = re.sub(r"(?is)<script.*?>.*?</script>", " ", text or "")
        value = re.sub(r"(?is)<style.*?>.*?</style>", " ", value)
        value = re.sub(r"(?is)<[^>]+>", " ", value)
        value = re.sub(r"\s+", " ", value).strip()
        return value

    @staticmethod
    def _normalize_result_url(url: str) -> str:
        raw = str(url or "").strip()
        if not raw:
            return ""
        parsed = urlparse(raw)
        if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
            target = parse_qs(parsed.query).get("uddg", [""])[0]
            if target:
                return unquote(target)
        return raw

    async def _search_external_sources(self, query: str, max_results: int) -> list[dict]:
        if not query.strip() or max_results <= 0:
            return []
        search_url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
        try:
            async with httpx.AsyncClient(
                timeout=settings.rag_external_timeout_seconds,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (IDEAS-RAG)"},
                trust_env=True,
            ) as client:
                html = (await client.get(search_url)).text
                matches = re.findall(r'<a[^>]*class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, flags=re.I | re.S)
                results: list[dict] = []
                for href, title_html in matches:
                    if len(results) >= max_results:
                        break
                    target_url = self._normalize_result_url(href)
                    if not target_url.startswith("http"):
                        continue
                    title = self._strip_html(title_html)[:180]
                    try:
                        page = await client.get(target_url)
                        snippet = self._strip_html(page.text)[:1400]
                    except Exception:
                        snippet = ""
                    if snippet:
                        results.append(
                            {
                                "source": target_url,
                                "title": title or target_url,
                                "content": snippet,
                                "source_type": "external",
                            }
                        )
                return results
        except Exception:
            return []

    async def ingest_pdf(
        self,
        session: AsyncSession,
        empresa_id: int,
        file_path: str,
        source_name: str | None = None,
        module_key: str = "general",
    ) -> int:
        pdf_path = Path(file_path)
        reader = PdfReader(str(pdf_path))
        raw_text = "\n".join((page.extract_text() or "") for page in reader.pages)
        chunks = self.splitter.split_text(raw_text)
        if not chunks:
            return 0

        embedded = await self.client.embeddings.create(model=settings.openai_embedding_model, input=chunks)
        count = 0
        for idx, (chunk, emb) in enumerate(zip(chunks, embedded.data, strict=False), start=1):
            row = DocumentChunk(
                empresa_id=int(empresa_id),
                content=chunk,
                metadata_json={
                    "empresa_id": str(int(empresa_id)),
                    "module_key": module_key,
                    "source": source_name or pdf_path.name,
                    "chunk_index": idx,
                },
                embedding=list(emb.embedding),
            )
            session.add(row)
            count += 1
        await session.commit()
        return count

    async def retrieve(
        self,
        session: AsyncSession,
        empresa_id: int,
        question: str,
        k: int = 6,
        module_key: str = "general",
    ) -> list[RetrievedChunk]:
        emb = await self.client.embeddings.create(model=settings.openai_embedding_model, input=[question])
        vector = emb.data[0].embedding
        vector_literal = "[" + ",".join(f"{value:.12f}" for value in vector) + "]"
        stmt = text(
            """
            SELECT id, content, metadata_json, (embedding <=> CAST(:embedding AS vector)) AS score
            FROM document_chunks
            WHERE metadata_json->>'empresa_id' = :empresa_id
              AND metadata_json->>'module_key' = :module_key
            ORDER BY embedding <=> CAST(:embedding AS vector)
            LIMIT :k
            """
        )
        result = await session.execute(
            stmt,
            {
                "embedding": vector_literal,
                "empresa_id": str(int(empresa_id)),
                "module_key": module_key,
                "k": int(k),
            },
        )
        rows: list[RetrievedChunk] = []
        for item in result.mappings().all():
            rows.append(
                RetrievedChunk(
                    id=int(item["id"]),
                    content=str(item["content"]),
                    score=float(item["score"]),
                    metadata_json=dict(item["metadata_json"] or {}),
                )
            )
        return rows

    async def chat(
        self,
        session: AsyncSession,
        empresa_id: int,
        question: str,
        k: int = 6,
        module_key: str = "general",
        allow_external: bool = True,
    ) -> RAGAnswer:
        chunks = await self.retrieve(
            session=session,
            empresa_id=empresa_id,
            question=question,
            k=k,
            module_key=module_key,
        )
        context = "\n\n".join([f"[INTERNA:{c.metadata_json.get('source', 'doc')}] {c.content}" for c in chunks])
        external_items: list[dict] = []
        should_use_external = (
            settings.rag_allow_external_fallback
            and allow_external
            and (not chunks or len(chunks) < 3 or min((c.score for c in chunks), default=1.0) > 0.45)
        )
        if should_use_external:
            external_items = await self._search_external_sources(
                query=f"{question} {module_key} ISO IATF",
                max_results=max(1, int(settings.rag_external_max_sources)),
            )
            if external_items:
                ext_context = "\n\n".join([f"[EXTERNA:{item['source']}] {item['content']}" for item in external_items])
                context = f"{context}\n\n{ext_context}".strip()
        system_prompt = (
            "Eres Smart Assist de IDEAS Consulting, un auditor senior industrial. "
            "Responde en espanol natural, conversacional y profesional (sin tablas ni formato rigido). "
            "Primero responde directo a la pregunta en 3-6 lineas claras. "
            "Responde de forma breve, accionable y precisa para el modulo "
            f"{module_key}. Prioriza SIEMPRE fuentes internas de empresa. "
            "Si usas fuentes externas, marcarlas como referencia externa y no reemplazar contenido interno."
        )
        user_prompt = f"Pregunta:\n{question}\n\nDocumentos recuperados:\n{context or 'Sin documentos.'}"
        completion = await self.client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.1,
            max_tokens=400,
        )
        sources = [
            {
                "id": chunk.id,
                "source": chunk.metadata_json.get("source", "doc"),
                "chunk_index": chunk.metadata_json.get("chunk_index"),
                "score": chunk.score,
                "source_type": "internal",
            }
            for chunk in chunks
        ]
        for idx, item in enumerate(external_items, start=1):
            sources.append(
                {
                    "id": f"ext-{idx}",
                    "source": item.get("source", ""),
                    "chunk_index": idx,
                    "score": None,
                    "source_type": "external",
                }
            )
        return RAGAnswer(answer=(completion.choices[0].message.content or "").strip(), sources=sources)
