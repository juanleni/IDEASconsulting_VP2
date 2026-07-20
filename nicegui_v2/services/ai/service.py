from __future__ import annotations

import asyncio
import json
from typing import Any

from .context_builder import build_ai_context, render_context_as_text
from .openai_client import get_openai_client
from .prompts import SMART_IDEAS_SYSTEM_PROMPT, build_user_prompt
from .tools import list_future_tools
from .ai_usage_tracker import log_ai_usage


class SmartIdeasAIService:
    def __init__(self, *, model: str = "gpt-4o-mini") -> None:
        self.model = model

    async def answer(
        self,
        *,
        question: str,
        company_id: int | None,
        user_id: int | None,
        user_name: str = "",
        user_role: str = "",
        permissions: str = "ALL",
        module_key: str = "general",
        module_context: str = "",
        enabled_modules: list[str] | None = None,
        history: list[dict] | None = None,
        memory_context: list[dict] | None = None,
        working_context: str = "",
        focus_payload: dict | None = None,
        task_type: str = "general",
        include_sources: bool = False,
    ) -> str:
        if not str(question or "").strip():
            return "Necesito una consulta concreta para ayudarte."
        if not company_id:
            return "No hay empresa activa seleccionada. Selecciona una empresa para usar Smart IDEAS."
        if enabled_modules is not None and module_key not in {"general", ""} and module_key not in set(enabled_modules):
            return "No tienes permisos para consultar este modulo con Smart IDEAS."

        context = build_ai_context(
            user_id=user_id,
            company_id=int(company_id),
            module=module_key or module_context or "general",
            query=question,
            user_name=user_name,
            user_role=user_role,
            permissions=permissions,
            module_whitelist=enabled_modules,
            working_context=working_context,
            focus_payload=focus_payload,
        )
        history_text = self._history_to_text(memory_context or history or [])
        context_text = render_context_as_text(context)
        user_prompt = build_user_prompt(
            question=question,
            context_text=context_text,
            memory_text=history_text,
            module_key=module_key or "general",
            task_type=task_type or "general",
        )
        if include_sources:
            user_prompt += "\nSi usas datos internos, cita modulo o fuente en una linea final."
        try:
            response = await asyncio.to_thread(
                self._chat_text,
                SMART_IDEAS_SYSTEM_PROMPT,
                user_prompt,
                company_id=company_id,
                user_id=user_id,
                prompt_kind=task_type or "general",
            )
            return self._sanitize_answer(response)
        except Exception as exc:
            detail = str(exc).lower()
            if "openai_api_key" in detail or "falta configurar" in detail:
                return (
                    "Smart IDEAS no esta disponible porque falta OPENAI_API_KEY. "
                    "Configura la clave y reinicia la aplicacion."
                )
            if "invalid" in detail and "api" in detail and "key" in detail:
                return "La clave OPENAI_API_KEY no es valida. Actualizala y vuelve a intentar."
            if "quota" in detail or "429" in detail:
                return "La cuenta OpenAI no tiene cuota disponible en este momento. Revisa billing y limites."
            return "No pude completar la consulta en este momento. Reintenta en unos minutos."

    def _chat_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        company_id: int | None = None,
        user_id: int | None = None,
        prompt_kind: str = "general",
    ) -> str:
        client = get_openai_client()
        result = client.chat.completions.create(
            model=self.model,
            temperature=0.25,
            max_tokens=900,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        usage = getattr(result, "usage", None)
        log_ai_usage(
            model=self.model,
            prompt_kind=prompt_kind,
            company_id=company_id,
            user_id=user_id,
            input_tokens=int(getattr(usage, "prompt_tokens", 0) or 0),
            output_tokens=int(getattr(usage, "completion_tokens", 0) or 0),
        )
        return str(result.choices[0].message.content or "").strip()

    @staticmethod
    def _history_to_text(history: list[dict]) -> str:
        lines: list[str] = []
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip()
            content = str(item.get("content") or "").strip()
            if role in {"user", "assistant"} and content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    @staticmethod
    def _sanitize_answer(text: str) -> str:
        cleaned = str(text or "").strip()
        if not cleaned:
            return "No hay datos suficientes para responder con precision. Carga mas informacion y vuelve a intentar."
        return cleaned

    @staticmethod
    def suggest_dashboard_widget(*, user_prompt: str, module_name: str, metric_catalog: list[tuple[str, str, int]]) -> dict[str, Any]:
        metric_lines = "\n".join([f"- {code}: {label} ({value})" for code, label, value in metric_catalog])
        payload = (
            "Devuelve JSON valido con claves: title, chart_type, analysis_mode, metrics.\n"
            "chart_type: bar|line|pie|radar. analysis_mode: raw|trend|outliers.\n"
            "metrics: lista de codigos existentes."
        )
        user_content = (
            f"Modulo: {module_name}\nPedido: {user_prompt}\nMetricas:\n{metric_lines}\n{payload}"
        )
        try:
            raw = SmartIdeasAIService()._chat_text(
                "Eres analista de dashboards SaaS B2B y solo devuelves JSON.",
                user_content,
            )
            data = json.loads(raw)
            if not isinstance(data, dict):
                raise ValueError("JSON invalido")
            valid_codes = {m[0] for m in metric_catalog}
            metrics = [str(item) for item in (data.get("metrics") or []) if str(item) in valid_codes][:6]
            return {
                "title": str(data.get("title") or "Grafico sugerido por Smart IDEAS"),
                "chart_type": str(data.get("chart_type") or "bar"),
                "analysis_mode": str(data.get("analysis_mode") or "raw"),
                "metrics": metrics or [metric_catalog[0][0]] if metric_catalog else [],
            }
        except Exception:
            return {
                "title": "Grafico sugerido por Smart IDEAS",
                "chart_type": "bar",
                "analysis_mode": "raw",
                "metrics": [code for code, _label, _val in metric_catalog[:4]],
            }

    @staticmethod
    def list_tooling_roadmap() -> list[dict[str, Any]]:
        return list_future_tools()
