from __future__ import annotations

import httpx
from nicegui import ui


async def render_quality8d_panel(api_base_url: str, jwt_token: str) -> None:
    headers = {"Authorization": f"Bearer {jwt_token}"}
    async with httpx.AsyncClient(timeout=20.0) as client:
        response = await client.get(f"{api_base_url}/quality/8d", headers=headers)
        response.raise_for_status()
        rows = response.json()

    with ui.card().classes("ideas-panel w-full"):
        ui.label("Calidad 8D").classes("ideas-section-title")
        ui.label("Datos consumidos asíncronamente desde FastAPI").classes("ideas-section-note")
        table_rows = [
            {
                "id": row["id"],
                "titulo": row["titulo"],
                "problema": row["d2_problema"][:120],
                "causa": row["d4_causa_raiz"][:120],
            }
            for row in rows
        ]
        ui.table(
            columns=[
                {"name": "id", "label": "ID", "field": "id", "align": "left"},
                {"name": "titulo", "label": "Título", "field": "titulo", "align": "left"},
                {"name": "problema", "label": "D2 Problema", "field": "problema", "align": "left"},
                {"name": "causa", "label": "D4 Causa", "field": "causa", "align": "left"},
            ],
            rows=table_rows,
            pagination={"rowsPerPage": 10},
        ).classes("w-full ideas-table")

