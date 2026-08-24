from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from nicegui import app, ui

from services.ai.ai_dashboard_generator import generate_dashboard_schema
from services.dashboard.dashboard_service import (
    delete_dashboard,
    get_data_sources_for_company,
    load_saved_dashboards,
    save_dashboard,
)


_STORE_PATH = Path(__file__).resolve().parent / "data" / "dashboard_widgets_by_module.json"


def _load_store() -> dict:
    if not _STORE_PATH.exists():
        return {}
    try:
        data = json.loads(_STORE_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_store(payload: dict) -> None:
    _STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    _STORE_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _key(module_key: str, company_id: int) -> str:
    return f"{module_key}:{int(company_id)}"


def load_widgets(module_key: str, company_id: int) -> list[dict]:
    data = _load_store()
    rows = data.get(_key(module_key, company_id)) or []
    return rows if isinstance(rows, list) else []


def save_widgets(module_key: str, company_id: int, widgets: list[dict]) -> None:
    data = _load_store()
    data[_key(module_key, company_id)] = widgets
    _save_store(data)


def _can_use_module(module_key: str) -> bool:
    role = str(app.storage.user.get("role") or "").strip().lower()
    if role == "admin":
        return True
    permisos = str(app.storage.user.get("permisos") or "ALL").strip()
    if permisos == "ALL":
        return True
    tokens = {item.strip() for item in permisos.split(",") if item.strip()}
    mapping = {
        "documents": "cert_iso_9001",
        "process_maps": "cert_iso_9001",
        "kpi": "cert_iso_9001",
        "risks": "cert_iso_9001",
        "quality": "cert_iso_9001",
        "environment": "cert_iso_14001",
        "sst": "cert_iso_45001",
        "lab_17025": "cert_iso_17025",
    }
    needed = mapping.get(str(module_key or "").strip().lower(), "")
    return needed in tokens if needed else True


def _normalize_for_widget(source_key: str, data: dict[str, Any], widget: dict[str, Any]) -> list[dict]:
    if source_key == "quality.corrective_actions":
        if widget["type"] in {"bar_chart", "line_chart", "donut_chart"}:
            return data.get("by_phase") or data.get("by_status") or []
        return data.get("overdue") or []
    if source_key == "risks.matrix":
        if widget["type"] in {"bar_chart", "line_chart", "donut_chart"}:
            return data.get("by_process") or []
        return data.get("critical_items") or []
    if source_key == "kpis.company":
        if widget["type"] in {"bar_chart", "line_chart", "donut_chart"}:
            return data.get("by_process") or []
        return data.get("rows") or []
    if source_key == "lab.calibrations":
        if widget["type"] in {"bar_chart", "line_chart", "donut_chart"}:
            status = data.get("status") or {}
            return [{"label": k, "count": int(v)} for k, v in status.items()]
        return data.get("rows") or []
    if source_key == "alerts.company":
        if widget["type"] in {"bar_chart", "line_chart", "donut_chart"}:
            return data.get("by_criticality") or []
        return data.get("open") or []
    if source_key == "documents.expiring":
        return data.get("rows") or []
    if source_key == "environmental.indicators":
        return data.get("rows") or []
    if source_key == "lab.iso17025":
        return [data]
    return []


def _render_visual_dashboard(*, container, schema: dict[str, Any], sources: dict[str, Any]) -> None:
    container.clear()
    with container:
        ui.label(str(schema.get("title") or "Dashboard IA")).classes("ideas-section-title")
        if str(schema.get("description") or "").strip():
            ui.label(str(schema.get("description") or "")).classes("ideas-section-note")
        with ui.grid(columns=2).classes("w-full gap-3 mt-3"):
            for widget in schema.get("widgets") or []:
                src = str(widget.get("data_source") or "").strip()
                src_data = sources.get(src) if isinstance(sources, dict) else None
                rows = _normalize_for_widget(src, src_data or {}, widget)
                with ui.card().classes("ideas-panel p-3"):
                    ui.label(str(widget.get("title") or "Widget")).classes("text-sm font-semibold text-slate-800")
                    wtype = str(widget.get("type") or "")
                    if not rows:
                        ui.label("Sin datos para este bloque. Cargá registros y volvé a intentar.").classes("ideas-section-note mt-2")
                        continue
                    if wtype == "kpi_card":
                        first = rows[0] if isinstance(rows[0], dict) else {}
                        value = first.get("open_count") or first.get("score_general") or first.get("total") or len(rows)
                        ui.label(str(value)).classes("text-3xl font-bold text-slate-900 mt-3")
                    elif wtype in {"bar_chart", "line_chart", "donut_chart"}:
                        x_key = str(widget.get("x") or "label")
                        y_key = str(widget.get("y") or "count")
                        labels = [str(r.get(x_key) or r.get("label") or r.get("process") or "N/D") for r in rows[:16]]
                        values = [float(r.get(y_key) or r.get("count") or 0) for r in rows[:16]]
                        chart = "pie" if wtype == "donut_chart" else ("line" if wtype == "line_chart" else "bar")
                        if chart == "pie":
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "item"},
                                    "series": [
                                        {
                                            "type": "pie",
                                            "radius": ["40%", "70%"],
                                            "data": [{"name": labels[i], "value": values[i]} for i in range(len(labels))],
                                        }
                                    ],
                                }
                            ).classes("w-full h-56")
                        else:
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "axis"},
                                    "xAxis": {"type": "category", "data": labels},
                                    "yAxis": {"type": "value"},
                                    "series": [{"type": chart, "data": values, "smooth": chart == "line"}],
                                }
                            ).classes("w-full h-56")
                    else:
                        columns = [str(c) for c in (widget.get("columns") or []) if str(c).strip()]
                        if not columns:
                            columns = list((rows[0] or {}).keys())[:6]
                        table_columns = [{"name": c, "label": c.replace("_", " ").title(), "field": c, "align": "left"} for c in columns]
                        ui.table(columns=table_columns, rows=rows[: int(widget.get("limit") or 10)], pagination=6).classes("w-full ideas-table mt-2")


def render_dashboard_customizer(*, module_key: str, company_id: int, metric_catalog: list[tuple[str, str, int]]) -> None:
    _ = metric_catalog
    user_permissions = str(app.storage.user.get("permisos") or "ALL").strip()
    sources_cache = get_data_sources_for_company(int(company_id), module_key=str(module_key or ""), user_permissions=user_permissions)

    with ui.card().classes("ideas-panel w-full mt-4"):
        ui.label("Generación visual con IA").classes("ideas-section-title")
        ui.label("Escribí qué querés ver. Smart IDEAS arma el dashboard automáticamente.").classes("ideas-section-note")

        with ui.row().classes("w-full gap-2 mt-2"):
            ai_prompt = ui.input("Ej: Dashboard ejecutivo de acciones abiertas").props("outlined").classes("w-full")
            ai_generate = ui.button("Generar", icon="auto_awesome").props("unelevated color=primary")

        ai_loading = ui.row().classes("items-center gap-2 text-slate-500 mt-2")
        ai_loading.visible = False
        with ai_loading:
            ui.spinner(size="sm")
            ui.label("Smart IDEAS está armando la vista...")

        with ui.row().classes("w-full gap-1 mt-1"):
            async def _run_quick_prompt(text: str) -> None:
                ai_prompt.set_value(text)
                await _generate_ai_dashboard()

            def _quick_click(text: str):
                async def _handler() -> None:
                    await _run_quick_prompt(text)
                return _handler

            for txt in [
                "Dashboard ejecutivo",
                "Riesgos criticos",
                "Acciones vencidas",
                "Auditorias abiertas",
                "Indicadores por proceso",
                "Mantenimiento vencido",
                "Documentos por vencer",
                "Estado ISO 17025",
                "Resumen gerencial",
            ]:
                ui.button(
                    txt,
                    on_click=_quick_click(txt),
                ).props("flat dense").classes("text-[11px] border border-slate-300 rounded px-2")

        ai_panel = ui.column().classes("w-full mt-3 gap-3")
        saved_ai_panel = ui.column().classes("w-full mt-3 gap-2")
        runtime = {"schema": None}

        def refresh_saved_ai() -> None:
            rows = load_saved_dashboards(str(module_key or "general"), int(company_id))
            saved_ai_panel.clear()
            with saved_ai_panel:
                if not rows:
                    ui.label("No hay dashboards IA guardados para este módulo.").classes("ideas-section-note")
                    return
                ui.label("Guardados recientes").classes("text-sm font-semibold text-slate-700")
                for idx, item in enumerate(rows[-6:]):
                    with ui.row().classes("w-full items-center justify-between border border-slate-200 rounded px-3 py-2"):
                        ui.label(str(item.get("title") or "Dashboard IA")).classes("text-sm text-slate-800")
                        with ui.row().classes("gap-1"):
                            ui.button(
                                icon="visibility",
                                on_click=lambda _=None, i=item: _render_visual_dashboard(
                                    container=ai_panel,
                                    schema=i.get("schema") or {},
                                    sources=sources_cache,
                                ),
                            ).props("flat round dense")
                            ui.button(icon="delete", on_click=lambda _=None, i=idx: _delete_saved_ai(i)).props("flat round dense color=negative").tooltip("Eliminar")

        def _delete_saved_ai(index: int) -> None:
            delete_dashboard(str(module_key or "general"), int(company_id), index)
            refresh_saved_ai()
            ui.notify("Dashboard IA eliminado.", type="warning")

        def save_current_ai_dashboard() -> None:
            schema = runtime.get("schema")
            if not isinstance(schema, dict):
                ui.notify("No hay dashboard IA generado para guardar.", type="warning")
                return
            save_dashboard(
                str(module_key or "general"),
                int(company_id),
                {"title": str(schema.get("title") or "Dashboard IA"), "created_at": datetime.now().isoformat(timespec="seconds"), "schema": schema},
            )
            refresh_saved_ai()
            ui.notify("Dashboard IA guardado.", type="positive")

        async def _generate_ai_dashboard() -> None:
            if not _can_use_module(module_key):
                ui.notify("No tenés permisos para generar dashboards en este módulo.", type="negative")
                return
            prompt_text = str(ai_prompt.value or "").strip()
            if not prompt_text:
                ui.notify("Escribí una consulta para generar el dashboard.", type="warning")
                return
            ai_loading.visible = True
            ai_loading.update()
            try:
                available_sources = list(sources_cache.keys())
                context_summary = f"empresa_id={int(company_id)} modulo={module_key} fuentes={available_sources}"
                ok, msg, schema = await generate_dashboard_schema(
                    user_prompt=prompt_text,
                    module_key=str(module_key or "general"),
                    available_sources=available_sources,
                    context_summary=context_summary,
                )
                if not ok:
                    ai_panel.clear()
                    with ai_panel:
                        ui.label(f"No se pudo generar el dashboard: {msg}").classes("text-red-600")
                    return
                runtime["schema"] = schema
                _render_visual_dashboard(container=ai_panel, schema=schema, sources=sources_cache)
            except Exception:
                ai_panel.clear()
                with ai_panel:
                    ui.label("No se pudo generar la vista en este momento. Reintentá en unos segundos.").classes("text-red-600")
            finally:
                ai_loading.visible = False
                ai_loading.update()

        with ui.row().classes("w-full gap-2 mt-2"):
            ai_generate.on_click(_generate_ai_dashboard)
            ui.button("Guardar", icon="bookmark_add", on_click=save_current_ai_dashboard).props("outline color=primary")
            ui.button("Limpiar", icon="ink_eraser", on_click=lambda: (ai_prompt.set_value(""), ai_panel.clear())).props("flat")

        refresh_saved_ai()
