from __future__ import annotations

import json
import tempfile
from datetime import datetime

from services.analytics.ai_analysis_service import generate_command_center_analysis


def register_ai_command_center_page(ui, app, deps: dict) -> None:
    shell = deps["shell"]
    ensure_platform_access = deps["ensure_platform_access"]
    get_enabled_modules_for_user = deps["get_enabled_modules_for_user"]
    get_data_sources_for_company = deps["get_data_sources_for_company"]

    @ui.page("/sistema-gestion/smart-ideas")
    def smart_ideas_command_center_page() -> None:
        if not ensure_platform_access():
            return
        with shell("Smart IDEAS Command Center", back_route="/sistema-gestion", module_key="general") as container:
            with container:
                company_id = app.storage.user.get("logged_empresa_id")
                user_id = app.storage.user.get("local_user_id")
                user_name = str(app.storage.user.get("session_user_name") or app.storage.user.get("username") or "").strip()
                user_role = str(app.storage.user.get("role") or "").strip().lower()
                permissions = str(app.storage.user.get("permisos") or "ALL").strip()
                company_name = str(app.storage.user.get("logged_empresa_nombre") or "Empresa activa").strip()
                enabled_modules = []
                try:
                    if company_id and user_id:
                        enabled_modules = [
                            str(item.get("code") or "").strip()
                            for item in (get_enabled_modules_for_user(int(user_id), int(company_id)) or [])
                            if str(item.get("code") or "").strip()
                        ]
                except Exception:
                    enabled_modules = []

                result_state = {"data": None}
                with ui.column().classes("ideas-panel w-full gap-3"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Smart IDEAS Command Center").classes("text-2xl font-bold text-slate-900")
                        with ui.row().classes("items-center gap-2"):
                            ui.label(datetime.now().strftime("%d/%m/%Y")).classes("text-xs text-slate-500")
                            ui.label("IA conectada").classes("text-xs text-emerald-700")
                    ui.label(f"Empresa: {company_name}").classes("text-sm text-slate-700")
                    ui.label(f"Módulos habilitados: {', '.join(enabled_modules[:10]) if enabled_modules else 'No informados'}").classes("text-xs text-slate-500")

                    with ui.row().classes("w-full gap-2 items-center"):
                        query_input = ui.textarea(
                            "Pedile a Smart IDEAS que analice, compare, grafique o genere un reporte..."
                        ).props("outlined autogrow").classes("w-full")
                        run_btn = ui.button("Analizar", icon="auto_awesome").props("unelevated color=primary")
                    with ui.row().classes("w-full gap-2"):
                        for txt in [
                            "Analizar empresa completa",
                            "Dashboard ejecutivo",
                            "Riesgos críticos",
                            "Acciones vencidas",
                            "Reporte ISO 17025",
                            "KPIs y tendencias",
                            "Datos faltantes",
                            "Plan de acción",
                        ]:
                            ui.button(txt, on_click=lambda _=None, t=txt: query_input.set_value(t)).props("flat dense").classes("ideas-ai-chip-modern")

                    with ui.row().classes("w-full justify-end gap-2"):
                        def _new_query() -> None:
                            query_input.value = ""
                            query_input.update()
                            result_state["data"] = None
                            results_panel.clear()

                        def _copy_summary() -> None:
                            data = result_state.get("data") or {}
                            text = str(data.get("summary") or "").strip()
                            if not text:
                                ui.notify("No hay resumen generado.", type="warning")
                                return
                            safe = json.dumps(text)
                            ui.run_javascript(f"navigator.clipboard.writeText({safe});")
                            ui.notify("Resumen copiado.", type="positive")

                        def _export_json() -> None:
                            data = result_state.get("data")
                            if not isinstance(data, dict):
                                ui.notify("No hay análisis para exportar.", type="warning")
                                return
                            with tempfile.NamedTemporaryFile("w", delete=False, suffix=".json", encoding="utf-8") as fh:
                                fh.write(json.dumps(data, ensure_ascii=False, indent=2))
                                path = fh.name
                            ui.download(path)

                        ui.button("Nueva consulta", icon="add", on_click=_new_query).props("outline")
                        ui.button("Copiar resumen", icon="content_copy", on_click=_copy_summary).props("outline")
                        ui.button("Exportar reporte", icon="download", on_click=_export_json).props("outline color=primary")

                    loading = ui.row().classes("items-center gap-2 text-slate-500")
                    loading.visible = False
                    with loading:
                        ui.spinner(size="sm")
                        ui.label("Analizando datos reales de la empresa...")

                    with ui.row().classes("w-full gap-3 items-start"):
                        results_panel = ui.column().classes("w-[76%] gap-3")
                        side_panel = ui.column().classes("w-[24%] gap-3")

                    def _render_results(payload: dict) -> None:
                        results_panel.clear()
                        side_panel.clear()
                        with results_panel:
                            ui.label(str(payload.get("title") or "Resultado IA")).classes("text-xl font-semibold text-slate-900")
                            ui.label(str(payload.get("summary") or "")).classes("text-sm text-slate-700")
                            widgets = payload.get("widgets") or []
                            with ui.grid(columns=2).classes("w-full gap-3"):
                                for w in widgets:
                                    wtype = str(w.get("type") or "")
                                    with ui.card().classes("ideas-panel p-3"):
                                        ui.label(str(w.get("title") or "Widget")).classes("font-semibold text-slate-800")
                                        if wtype in {"kpi_card", "insight_card", "warning_card"}:
                                            value = w.get("value") or w.get("message") or "-"
                                            ui.label(str(value)).classes("text-2xl font-bold text-slate-900 mt-2")
                                        elif wtype in {"bar_chart", "line_chart", "pie_chart", "donut_chart", "radar_chart"}:
                                            rows = w.get("data") or []
                                            x = str(w.get("x") or "label")
                                            y = str(w.get("y") or "count")
                                            labels = [str(r.get(x) or "N/D") for r in rows[:16]]
                                            values = [float(r.get(y) or 0) for r in rows[:16]]
                                            ctype = "pie" if wtype in {"pie_chart", "donut_chart"} else ("line" if wtype == "line_chart" else "bar")
                                            if ctype == "pie":
                                                ui.echart({"series": [{"type": "pie", "radius": ["42%", "70%"], "data": [{"name": labels[i], "value": values[i]} for i in range(len(labels))]}]}).classes("w-full h-52")
                                            else:
                                                ui.echart({"xAxis": {"type": "category", "data": labels}, "yAxis": {"type": "value"}, "series": [{"type": ctype, "data": values, "smooth": ctype == "line"}]}).classes("w-full h-52")
                                        elif wtype == "table":
                                            cols = [str(c) for c in (w.get("columns") or []) if str(c).strip()]
                                            rows = w.get("rows") or []
                                            if not cols and rows:
                                                cols = list((rows[0] or {}).keys())[:8]
                                            table_cols = [{"name": c, "label": c.replace("_", " ").title(), "field": c, "align": "left"} for c in cols]
                                            ui.table(columns=table_cols, rows=rows[:12], pagination=6).classes("w-full ideas-table")
                        with side_panel:
                            trace = payload.get("traceability") or {}
                            ui.label("Fuentes usadas").classes("text-sm font-semibold text-slate-800")
                            for src in payload.get("sources_used") or []:
                                ui.label(f"- {src}").classes("text-xs text-slate-600")
                            ui.separator()
                            ui.label("Trazabilidad").classes("text-sm font-semibold text-slate-800")
                            ui.label(f"Empresa: {trace.get('company_id')}").classes("text-xs text-slate-600")
                            ui.label(f"Usuario: {trace.get('user_id')}").classes("text-xs text-slate-600")
                            ui.label(f"Fecha: {trace.get('generated_at')}").classes("text-xs text-slate-600")
                            counts = trace.get("records_analyzed") or {}
                            for k, v in counts.items():
                                ui.label(f"{k}: {v}").classes("text-xs text-slate-600")
                            recs = payload.get("recommendations") or []
                            if recs:
                                ui.separator()
                                ui.label("Sugerencias").classes("text-sm font-semibold text-slate-800")
                                for rec in recs[:6]:
                                    ui.label(f"- {rec}").classes("text-xs text-slate-600")

                    async def _run_analysis() -> None:
                        query = str(query_input.value or "").strip()
                        if not query:
                            ui.notify("Escribí una consulta.", type="warning")
                            return
                        loading.visible = True
                        loading.update()
                        try:
                            response = await generate_command_center_analysis(
                                query=query,
                                company_id=int(company_id) if company_id else None,
                                user_id=int(user_id) if user_id else None,
                                user_name=user_name,
                                user_role=user_role,
                                permissions=permissions,
                                module_key="general",
                                enabled_modules=enabled_modules,
                            )
                            if not response.get("ok"):
                                ui.notify(str(response.get("message") or "No se pudo generar el análisis."), type="warning")
                                return
                            payload = response.get("result") or {}
                            result_state["data"] = payload
                            _render_results(payload)
                        except Exception:
                            ui.notify("No se pudo completar el análisis en este momento.", type="negative")
                        finally:
                            loading.visible = False
                            loading.update()

                    run_btn.on_click(_run_analysis)
