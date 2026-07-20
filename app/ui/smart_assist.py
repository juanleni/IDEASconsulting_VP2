from __future__ import annotations

import httpx
from nicegui import ui


MODULE_OPTIONS = {
    "general": "General",
    "quality_8d": "Calidad 8D",
    "kpi": "KPIs",
    "risks": "Riesgos",
    "documents": "Documentos",
    "environment": "Ambiente",
}


def render_smart_assist(api_base_url: str, jwt_token: str | None, module_key: str = "general") -> None:
    selected_module = {"value": module_key}
    ingest_status = {"label": None}
    message_container = {"column": None}

    async def ask_assist() -> None:
        question = question_input.value.strip()
        if not question or not jwt_token:
            return

        if message_container["column"]:
            with message_container["column"]:
                ui.chat_message(text=question, name="Tu", sent=True).classes("w-full")
        question_input.value = ""

        try:
            async with httpx.AsyncClient(timeout=45.0) as client:
                response = await client.post(
                    f"{api_base_url}/rag/chat",
                    headers={"Authorization": f"Bearer {jwt_token}"},
                    json={
                        "question": question,
                        "module_key": selected_module["value"],
                        "k": 6,
                    },
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            if message_container["column"]:
                with message_container["column"]:
                    ui.chat_message(text=f"No pude consultar el asistente: {exc}", name="Smart Assist").classes("w-full")
            return

        answer = payload.get("answer") or "Sin respuesta disponible."
        sources = payload.get("sources") or []
        source_names = sorted({str(item.get("source")) for item in sources if item.get("source")})
        if source_names:
            answer = f"{answer}\n\nFuentes: {', '.join(source_names[:3])}"
        if message_container["column"]:
            with message_container["column"]:
                ui.chat_message(text=answer, name="Smart Assist").classes("w-full")

    async def ingest_document(event) -> None:
        if not jwt_token:
            return

        data = event.content.read()
        if ingest_status["label"]:
            ingest_status["label"].text = "Procesando documento..."
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(
                    f"{api_base_url}/rag/ingest",
                    headers={"Authorization": f"Bearer {jwt_token}"},
                    data={
                        "source_name": event.name,
                        "module_key": selected_module["value"],
                    },
                    files={"file": (event.name, data, "application/pdf")},
                )
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:
            if ingest_status["label"]:
                ingest_status["label"].text = f"No se pudo procesar: {exc}"
            return

        if ingest_status["label"]:
            ingest_status["label"].text = f"Documento incorporado: {payload.get('chunks', 0)} fragmentos"

    with ui.column().classes("w-full h-full gap-4"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Smart Assist").classes("text-lg font-bold text-slate-900")
            ui.icon("auto_awesome").classes("text-slate-500")

        ui.select(
            MODULE_OPTIONS,
            value=module_key if module_key in MODULE_OPTIONS else "general",
            on_change=lambda event: selected_module.update(value=event.value),
        ).props("outlined dense").classes("w-full")

        upload = ui.upload(
            label="PDF",
            auto_upload=True,
            on_upload=ingest_document,
        ).props("accept=.pdf flat bordered").classes("w-full")
        ingest_status["label"] = ui.label("").classes("text-xs text-slate-500")

        with ui.scroll_area().classes("w-full grow min-h-[360px] pr-2"):
            message_container["column"] = ui.column().classes("w-full gap-3")
            with message_container["column"]:
                ui.chat_message(text="Listo para ayudarte con este modulo.", name="Smart Assist").classes("w-full")

        question_input = ui.input(placeholder="Pregunta").props("outlined dense").classes("w-full")
        question_input.on("keydown.enter", ask_assist)
        ui.button("Preguntar", icon="send", on_click=ask_assist).props("unelevated").classes("w-full")

        if not jwt_token:
            question_input.disable()
            upload.disable()
            ui.label("Sesion requerida").classes("text-xs text-slate-500")
