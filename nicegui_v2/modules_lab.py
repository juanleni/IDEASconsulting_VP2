from __future__ import annotations

import json
import re
from io import BytesIO
from datetime import datetime
from pathlib import Path
from collections import Counter

import pandas as pd

from nicegui import app, ui
from dashboard_customizer import render_dashboard_customizer
from company_context import empresa_id_from_query_for_admin, with_empresa_id


LAB_SUBMODULES = [
    ("Dashboard LAB", "dashboard"),
    ("Equipos", "precision_manufacturing"),
    ("Calibraciones", "event_repeat"),
    ("Metodos", "science"),
    ("Muestras", "biotech"),
    ("Competencias", "groups"),
    ("Incertidumbre", "functions"),
    ("Control de Calidad", "monitoring"),
    ("Informes", "description"),
    ("Auditorias", "fact_check"),
    ("Riesgos", "warning"),
    ("Acciones Correctivas", "task_alt"),
    ("IA LAB", "auto_awesome"),
    ("Configuracion LAB", "tune"),
    ("Mobile Lab", "local_shipping"),
]


def go_to_lab_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user["management_company_id"] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id("/sistema-gestion/lab-iso-17025", company_id))


def _actor_name() -> str:
    return str(app.storage.user.get("session_user_name") or app.storage.user.get("username") or "usuario")


def _semaforo_badge(semaforo: str) -> tuple[str, str]:
    token = str(semaforo or "").lower()
    if token == "verde":
        return "Verde", "positive"
    if token == "amarillo":
        return "Amarillo", "warning"
    return "Rojo", "negative"


def _read_upload_payload(event) -> bytes:
    upload = getattr(event, "file", None)
    if upload is not None:
        data = getattr(upload, "_data", None)
        if isinstance(data, (bytes, bytearray)):
            return bytes(data)
    content = getattr(event, "content", None)
    if content is None:
        return b""
    if hasattr(content, "seek"):
        content.seek(0)
    if hasattr(content, "read"):
        payload = content.read()
        return payload if isinstance(payload, (bytes, bytearray)) else b""
    return bytes(content) if isinstance(content, (bytes, bytearray)) else b""


_LAB_WIDGETS_PATH = Path(__file__).resolve().parent / "data" / "lab_dashboard_widgets.json"


def _load_lab_widgets() -> dict:
    if not _LAB_WIDGETS_PATH.exists():
        return {}
    try:
        data = json.loads(_LAB_WIDGETS_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_lab_widgets(payload: dict) -> None:
    _LAB_WIDGETS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _LAB_WIDGETS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_company_widgets(company_id: int) -> list[dict]:
    data = _load_lab_widgets()
    rows = data.get(str(int(company_id))) or []
    return rows if isinstance(rows, list) else []


def _set_company_widgets(company_id: int, widgets: list[dict]) -> None:
    data = _load_lab_widgets()
    data[str(int(company_id))] = widgets
    _save_lab_widgets(data)


def _available_lab_metrics(dashboard: dict) -> list[tuple[str, str, int]]:
    return [
        ("score_general", "Score general ISO 17025", int(dashboard.get("score_general", 0) or 0)),
        ("equipos_criticos", "Equipos criticos", int(dashboard.get("equipos_criticos", 0) or 0)),
        ("calibraciones_vencidas", "Calibraciones vencidas", int(dashboard.get("calibraciones_vencidas", 0) or 0)),
        ("calibraciones_proximas", "Calibraciones proximas", int(dashboard.get("calibraciones_proximas", 0) or 0)),
        ("muestras_abiertas", "Muestras abiertas", int(dashboard.get("muestras_abiertas", 0) or 0)),
        ("metodos_vigentes", "Metodos vigentes", int(dashboard.get("metodos_vigentes", 0) or 0)),
        ("competencias_vencidas", "Competencias vencidas", int(dashboard.get("competencias_vencidas", 0) or 0)),
        ("auditorias_abiertas", "Auditorias abiertas", int(dashboard.get("auditorias_abiertas", 0) or 0)),
        ("riesgos_criticos", "Riesgos criticos", int(dashboard.get("riesgos_criticos", 0) or 0)),
        ("acciones_pendientes", "Acciones pendientes", int(dashboard.get("acciones_pendientes", 0) or 0)),
    ]


def _build_widget_option(widget: dict, label_by_code: dict[str, str], value_by_code: dict[str, int]) -> dict:
    chart_type = str(widget.get("chart_type") or "bar")
    metric_codes = [str(x) for x in (widget.get("metrics") or []) if str(x).strip()]
    metric_labels = [label_by_code.get(code, code) for code in metric_codes] or ["Sin datos"]
    values = [int(value_by_code.get(code, 0)) for code in metric_codes] or [0]
    title = str(widget.get("title") or "Grafico personalizado")

    if chart_type == "pie":
        return {
            "tooltip": {"trigger": "item"},
            "series": [{"type": "pie", "radius": ["40%", "70%"], "data": [{"name": metric_labels[i], "value": values[i]} for i in range(len(values))]}],
        }
    if chart_type == "line":
        return {
            "tooltip": {"trigger": "axis"},
            "xAxis": {"type": "category", "data": metric_labels},
            "yAxis": {"type": "value"},
            "series": [{"type": "line", "smooth": True, "areaStyle": {}, "data": values}],
        }
    if chart_type == "radar":
        max_value = max(values) + 2 if values else 3
        return {
            "radar": {"indicator": [{"name": metric_labels[i], "max": max(3, max_value)} for i in range(len(metric_labels))]},
            "series": [{"type": "radar", "data": [{"value": values, "name": title}]}],
        }
    return {
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": metric_labels},
        "yAxis": {"type": "value"},
        "series": [{"type": "bar", "data": values}],
    }


def _agent_suggest_widget(prompt: str, metric_catalog: list[tuple[str, str, int]]) -> dict:
    text = str(prompt or "").strip().lower()
    if not text:
        return {"title": "Grafico sugerido", "chart_type": "bar", "metrics": [metric_catalog[0][0]] if metric_catalog else []}
    chart_type = "bar"
    if any(token in text for token in ("torta", "pie", "composicion", "composición", "distribucion", "distribución")):
        chart_type = "pie"
    elif any(token in text for token in ("linea", "línea", "tendencia", "evolucion", "evolución")):
        chart_type = "line"
    elif any(token in text for token in ("radar", "araña", "arana")):
        chart_type = "radar"

    matches = []
    for code, label, _val in metric_catalog:
        code_tokens = set(re.split(r"[_\s]+", code.lower()))
        label_text = label.lower()
        if any(token and token in text for token in code_tokens) or any(token in label_text for token in text.split()):
            matches.append(code)

    if not matches:
        priority = ["calibraciones_vencidas", "riesgos_criticos", "acciones_pendientes", "auditorias_abiertas", "muestras_abiertas"]
        matches = [code for code in priority if any(code == c for c, _l, _v in metric_catalog)][:4]
    return {"title": "Grafico sugerido por agente", "chart_type": chart_type, "metrics": matches[:6]}


def register_lab_module(ui, deps: dict) -> None:
    ensure_platform_access = deps["ensure_platform_access"]
    shell = deps["shell"]
    current_selection = deps["current_selection"]
    set_selection = deps["set_selection"]
    company_options = deps["company_options"]
    obtener_empresa_detalle = deps["obtener_empresa_detalle"]
    fix_text = deps["fix_text"]
    obtener_lab_configuracion = deps["obtener_lab_configuracion"]
    guardar_lab_configuracion = deps["guardar_lab_configuracion"]
    obtener_lab_dashboard_empresa = deps["obtener_lab_dashboard_empresa"]
    seed_lab_demo_data = deps["seed_lab_demo_data"]
    calcular_incertidumbre_metodo = deps["calcular_incertidumbre_metodo"]
    validar_competencia_para_metodo = deps["validar_competencia_para_metodo"]

    obtener_lab_equipos_empresa = deps["obtener_lab_equipos_empresa"]
    crear_lab_equipo = deps["crear_lab_equipo"]
    eliminar_lab_equipo = deps["eliminar_lab_equipo"]
    obtener_lab_calibraciones_empresa = deps["obtener_lab_calibraciones_empresa"]
    crear_lab_calibracion = deps["crear_lab_calibracion"]
    eliminar_lab_calibracion = deps["eliminar_lab_calibracion"]
    obtener_lab_metodos_empresa = deps["obtener_lab_metodos_empresa"]
    crear_lab_metodo = deps["crear_lab_metodo"]
    eliminar_lab_metodo = deps["eliminar_lab_metodo"]
    obtener_lab_muestras_empresa = deps["obtener_lab_muestras_empresa"]
    crear_lab_muestra = deps["crear_lab_muestra"]
    eliminar_lab_muestra = deps["eliminar_lab_muestra"]
    obtener_lab_competencias_empresa = deps["obtener_lab_competencias_empresa"]
    crear_lab_competencia = deps["crear_lab_competencia"]
    eliminar_lab_competencia = deps["eliminar_lab_competencia"]
    obtener_lab_incertidumbre_empresa = deps["obtener_lab_incertidumbre_empresa"]
    crear_lab_incertidumbre_componente = deps["crear_lab_incertidumbre_componente"]
    eliminar_lab_incertidumbre_componente = deps["eliminar_lab_incertidumbre_componente"]
    obtener_lab_control_calidad_empresa = deps["obtener_lab_control_calidad_empresa"]
    crear_lab_control_calidad = deps["crear_lab_control_calidad"]
    eliminar_lab_control_calidad = deps["eliminar_lab_control_calidad"]
    obtener_lab_informes_empresa = deps["obtener_lab_informes_empresa"]
    crear_lab_informe = deps["crear_lab_informe"]
    eliminar_lab_informe = deps["eliminar_lab_informe"]
    obtener_lab_auditorias_empresa = deps["obtener_lab_auditorias_empresa"]
    crear_lab_auditoria = deps["crear_lab_auditoria"]
    eliminar_lab_auditoria = deps["eliminar_lab_auditoria"]
    obtener_lab_riesgos_empresa = deps["obtener_lab_riesgos_empresa"]
    crear_lab_riesgo = deps["crear_lab_riesgo"]
    eliminar_lab_riesgo = deps["eliminar_lab_riesgo"]
    obtener_lab_acciones_empresa = deps["obtener_lab_acciones_empresa"]
    crear_lab_accion = deps["crear_lab_accion"]
    eliminar_lab_accion = deps["eliminar_lab_accion"]
    obtener_lab_mobile_unidades_empresa = deps["obtener_lab_mobile_unidades_empresa"]
    crear_lab_mobile_unidad = deps["crear_lab_mobile_unidad"]
    obtener_lab_mobile_registros_empresa = deps["obtener_lab_mobile_registros_empresa"]
    crear_lab_mobile_registro = deps["crear_lab_mobile_registro"]
    obtener_lab_ai_settings = deps["obtener_lab_ai_settings"]
    guardar_lab_ai_settings = deps["guardar_lab_ai_settings"]
    obtener_lab_alertas_empresa = deps["obtener_lab_alertas_empresa"]
    actualizar_lab_alerta_estado = deps["actualizar_lab_alerta_estado"]
    ejecutar_chequeo_lab_empresa = deps["ejecutar_chequeo_lab_empresa"]
    generar_reporte_pre_acreditacion_lab = deps["generar_reporte_pre_acreditacion_lab"]
    obtener_reportes_lab_ai = deps["obtener_reportes_lab_ai"]
    convertir_alerta_en_accion_lab = deps["convertir_alerta_en_accion_lab"]

    @ui.page("/sistema-gestion/lab-iso-17025")
    def lab_page() -> None:
        if not ensure_platform_access():
            return
        shell_container = shell("LAB ISO/IEC 17025", back_route="/sistema-gestion", module_key="lab_17025")
        empresa_id, _diag = current_selection()
        query_empresa_id = empresa_id_from_query_for_admin()
        if query_empresa_id and query_empresa_id != empresa_id:
            empresa_id = query_empresa_id
            set_selection(int(empresa_id), None)
        if not empresa_id:
            options = company_options()
            if options:
                empresa_id = next(iter(options.keys()))
                set_selection(int(empresa_id), None)
        if not empresa_id:
            with shell_container:
                ui.label("No hay empresa seleccionada.").classes("ideas-section-title")
            return

        empresa = obtener_empresa_detalle(int(empresa_id)) or {}
        config = obtener_lab_configuracion(int(empresa_id))
        mobile_enabled = bool(int(config.get("mobile_lab_activo") or 0))
        dashboard = obtener_lab_dashboard_empresa(int(empresa_id))
        alertas_abiertas = obtener_lab_alertas_empresa(int(empresa_id), estado="abierta")
        semaforo_label, semaforo_color = _semaforo_badge(dashboard.get("semaforo", "rojo"))

        with shell_container:
            ui.label("LAB ISO 17025").classes("ideas-kicker")
            ui.label(f"{fix_text(str(empresa.get('razon_social') or 'Empresa'))} · LIMS + SG + IA").classes("text-3xl font-bold text-slate-900")
            ui.label("Arquitectura modular para laboratorios fijos y móviles, con trazabilidad y foco de auditoría.").classes("ideas-subtitle mb-4")

            with ui.row().classes("w-full items-center gap-3 mb-4"):
                ui.badge(f"Estado general: {semaforo_label}").props(f"color={semaforo_color}")
                ui.badge(f"Score ISO 17025: {dashboard.get('score_general', 0)}").props("color=primary")
                ui.button("Generar datos demo", icon="dataset", on_click=lambda: ui.notify(seed_lab_demo_data(int(empresa_id), _actor_name())[1], type="positive")).props("outline color=primary")

            with ui.tabs().classes("w-full ideas-panel p-2 rounded-[24px]") as tabs:
                tab_map = {}
                for label, icon in LAB_SUBMODULES:
                    if label == "Mobile Lab" and not mobile_enabled:
                        continue
                    tab_map[label] = ui.tab(label, icon=icon).props("no-caps")

            with ui.tab_panels(tabs, value=next(iter(tab_map.values()))).classes("w-full mt-4"):
                with ui.tab_panel(tab_map["Dashboard LAB"]).classes("w-full"):
                    all_alerts = obtener_lab_alertas_empresa(int(empresa_id))
                    criticality_counts = Counter(str(item.get("criticidad") or "media").lower() for item in all_alerts)
                    module_counts = Counter(str(item.get("modulo_origen") or "general") for item in all_alerts)
                    status_counts = Counter(str(item.get("estado") or "abierta").lower() for item in all_alerts)
                    today = datetime.now().date()
                    alerts_by_day = []
                    day_labels = []
                    for offset in range(13, -1, -1):
                        day = today.fromordinal(today.toordinal() - offset)
                        day_labels.append(day.strftime("%d/%m"))
                        count = 0
                        for item in all_alerts:
                            raw = str(item.get("fecha_deteccion") or "")[:10]
                            try:
                                parsed = datetime.strptime(raw, "%Y-%m-%d").date()
                            except Exception:
                                parsed = None
                            if parsed == day:
                                count += 1
                        alerts_by_day.append(count)

                    crit_alerts = int(criticality_counts.get("critica", 0) + criticality_counts.get("crítica", 0))
                    high_alerts = int(criticality_counts.get("alta", 0))
                    open_alerts = int(status_counts.get("abierta", 0) + status_counts.get("en análisis", 0) + status_counts.get("en analisis", 0))
                    compliance_index = max(0, min(100, int(dashboard.get("score_general", 0))))

                    with ui.grid(columns=3).classes("w-full gap-3 mb-3"):
                        with ui.card().classes("ideas-panel").style("background:rgba(255,255,255,0.58);border:1px solid rgba(148,163,184,.18);box-shadow:none;backdrop-filter:blur(10px);"):
                            ui.label("Compliance Index ISO/IEC 17025").classes("text-[0.82rem] font-normal text-slate-500 tracking-[0.08em] uppercase")
                            ui.echart(
                                {
                                    "series": [
                                        {
                                            "type": "gauge",
                                            "min": 0,
                                            "max": 100,
                                            "startAngle": 210,
                                            "endAngle": -30,
                                            "radius": "88%",
                                            "progress": {"show": True, "width": 8, "roundCap": True},
                                            "axisLine": {"lineStyle": {"width": 8, "color": [[1, "rgba(148,163,184,.22)"]]}},
                                            "axisTick": {"show": False},
                                            "splitLine": {"show": False},
                                            "axisLabel": {"show": False},
                                            "pointer": {"show": False},
                                            "anchor": {"show": False},
                                            "title": {
                                                "show": True,
                                                "offsetCenter": [0, "18%"],
                                                "fontSize": 11,
                                                "fontWeight": "normal",
                                                "color": "rgba(71,85,105,.78)",
                                            },
                                            "detail": {
                                                "formatter": "{value}%",
                                                "offsetCenter": [0, "-8%"],
                                                "fontSize": 20,
                                                "fontWeight": "normal",
                                                "color": "rgba(15,23,42,.86)",
                                            },
                                            "data": [{"value": compliance_index, "name": "score"}],
                                        }
                                    ]
                                }
                            ).classes("w-full h-56")
                        with ui.card().classes("ideas-panel"):
                            ui.label("Riesgo Operacional (Composición)").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "item"},
                                    "series": [
                                        {
                                            "type": "pie",
                                            "radius": ["40%", "70%"],
                                            "data": [
                                                {"name": "Alertas abiertas", "value": open_alerts},
                                                {"name": "Críticas", "value": crit_alerts},
                                                {"name": "Altas", "value": high_alerts},
                                                {"name": "Riesgos críticos", "value": int(dashboard.get("riesgos_criticos", 0))},
                                                {"name": "Calibraciones vencidas", "value": int(dashboard.get("calibraciones_vencidas", 0))},
                                            ],
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")
                        with ui.card().classes("ideas-panel"):
                            ui.label("KPI Operacional LAB").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "radar": {
                                        "indicator": [
                                            {"name": "Muestras abiertas", "max": max(3, int(dashboard.get("muestras_abiertas", 0)) + 2)},
                                            {"name": "Auditorías abiertas", "max": max(3, int(dashboard.get("auditorias_abiertas", 0)) + 2)},
                                            {"name": "Acciones pendientes", "max": max(3, int(dashboard.get("acciones_pendientes", 0)) + 2)},
                                            {"name": "Calib. vencidas", "max": max(3, int(dashboard.get("calibraciones_vencidas", 0)) + 2)},
                                            {"name": "Competencias vencidas", "max": max(3, int(dashboard.get("competencias_vencidas", 0)) + 2)},
                                            {"name": "Equipos críticos", "max": max(3, int(dashboard.get("equipos_criticos", 0)) + 2)},
                                        ]
                                    },
                                    "series": [
                                        {
                                            "type": "radar",
                                            "data": [
                                                {
                                                    "value": [
                                                        int(dashboard.get("muestras_abiertas", 0)),
                                                        int(dashboard.get("auditorias_abiertas", 0)),
                                                        int(dashboard.get("acciones_pendientes", 0)),
                                                        int(dashboard.get("calibraciones_vencidas", 0)),
                                                        int(dashboard.get("competencias_vencidas", 0)),
                                                        int(dashboard.get("equipos_criticos", 0)),
                                                    ],
                                                    "name": "Estado actual",
                                                }
                                            ],
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")

                    with ui.grid(columns=2).classes("w-full gap-3 mt-4"):
                        with ui.card().classes("ideas-panel"):
                            ui.label("Tendencia de Alertas (14 días)").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "axis"},
                                    "xAxis": {"type": "category", "data": day_labels},
                                    "yAxis": {"type": "value"},
                                    "series": [
                                        {
                                            "type": "line",
                                            "data": alerts_by_day,
                                            "smooth": True,
                                            "areaStyle": {},
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")

                        with ui.card().classes("ideas-panel"):
                            ui.label("Distribución por Criticidad").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "item"},
                                    "series": [
                                        {
                                            "type": "pie",
                                            "radius": ["42%", "70%"],
                                            "data": [
                                                {"value": int(criticality_counts.get("baja", 0)), "name": "Baja"},
                                                {"value": int(criticality_counts.get("media", 0)), "name": "Media"},
                                                {"value": int(criticality_counts.get("alta", 0)), "name": "Alta"},
                                                {"value": int(criticality_counts.get("critica", 0) + criticality_counts.get("crítica", 0)), "name": "Crítica"},
                                            ],
                                        }
                                    ],
                                }
                            ).classes("w-full h-64")

                    with ui.grid(columns=2).classes("w-full gap-3 mt-3"):
                        with ui.card().classes("ideas-panel"):
                            ui.label("Módulos Más Impactados").classes("ideas-section-title")
                            mod_labels = [item[0] for item in module_counts.most_common(8)] or ["sin datos"]
                            mod_values = [item[1] for item in module_counts.most_common(8)] or [0]
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "axis"},
                                    "xAxis": {"type": "value"},
                                    "yAxis": {"type": "category", "data": mod_labels},
                                    "series": [{"type": "bar", "data": mod_values}],
                                }
                            ).classes("w-full h-64")

                        with ui.card().classes("ideas-panel"):
                            ui.label("Backlog por Estado").classes("ideas-section-title")
                            st_labels = [item[0] for item in status_counts.most_common(6)] or ["sin datos"]
                            st_values = [item[1] for item in status_counts.most_common(6)] or [0]
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "axis"},
                                    "xAxis": {"type": "category", "data": st_labels},
                                    "yAxis": {"type": "value"},
                                    "series": [{"type": "bar", "data": st_values}],
                                }
                            ).classes("w-full h-64")

                    render_dashboard_customizer(
                        module_key="lab_17025",
                        company_id=int(empresa_id),
                        metric_catalog=_available_lab_metrics(dashboard),
                    )

                    with ui.card().classes("ideas-panel w-full mt-4"):
                        ui.label("Alertas IA ISO 17025").classes("ideas-section-title")
                        crit = len([a for a in alertas_abiertas if str(a.get("criticidad") or "").lower() == "critica"])
                        high = len([a for a in alertas_abiertas if str(a.get("criticidad") or "").lower() == "alta"])
                        venc = len([a for a in alertas_abiertas if str(a.get("tipo") or "").lower() == "vencimiento"])
                        incomplete = len([a for a in alertas_abiertas if str(a.get("tipo") or "").lower() == "incompleto"])
                        incoh = len([a for a in alertas_abiertas if str(a.get("tipo") or "").lower() == "incoherencia"])
                        risk = len([a for a in alertas_abiertas if str(a.get("tipo") or "").lower() in {"riesgo", "ia"}])
                        with ui.grid(columns=6).classes("w-full gap-3 mt-2"):
                            ui.html(f'<div class="ideas-quick-card"><div class="label">ABIERTAS</div><div class="value">{len(alertas_abiertas)}</div></div>')
                            ui.html(f'<div class="ideas-quick-card"><div class="label">CRÍTICAS</div><div class="value">{crit}</div></div>')
                            ui.html(f'<div class="ideas-quick-card"><div class="label">ALTAS</div><div class="value">{high}</div></div>')
                            ui.html(f'<div class="ideas-quick-card"><div class="label">VENCIMIENTOS</div><div class="value">{venc}</div></div>')
                            ui.html(f'<div class="ideas-quick-card"><div class="label">INCOMPLETOS</div><div class="value">{incomplete}</div></div>')
                            ui.html(f'<div class="ideas-quick-card"><div class="label">INCOHERENCIAS/RIESGO</div><div class="value">{incoh + risk}</div></div>')

                def render_simple_crud(
                    *,
                    panel,
                    title: str,
                    columns: list[dict],
                    rows_fn,
                    create_fn,
                    delete_fn,
                    form_fields: list[tuple[str, str, str]],
                ) -> None:
                    with ui.tab_panel(panel).classes("w-full"):
                        with ui.card().classes("ideas-panel w-full"):
                            with ui.row().classes("w-full items-center justify-between"):
                                ui.label(title).classes("ideas-section-title")
                                ui.button("Nuevo", icon="add", on_click=lambda: open_form()).props("unelevated color=primary")
                            table = ui.table(columns=columns + [{"name": "acciones", "label": "Acciones", "field": "acciones"}], rows=[], row_key="id").classes("w-full mt-3 ideas-card p-3")
                            table.add_slot(
                                "body-cell-acciones",
                                """<q-td :props="props"><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('del', props.row.id)" /></q-td>""",
                            )

                            def refresh_table() -> None:
                                table.rows[:] = [{**item, "acciones": ""} for item in rows_fn(int(empresa_id))]
                                table.update()

                            def open_form() -> None:
                                with ui.dialog() as dialog, ui.card().classes("ideas-panel w-[760px] max-w-[95vw]"):
                                    ui.label(f"Nuevo registro · {title}").classes("ideas-section-title")
                                    controls = {}
                                    with ui.grid(columns=2).classes("w-full gap-3 mt-3"):
                                        for key, label, ctype in form_fields:
                                            if ctype == "textarea":
                                                controls[key] = ui.textarea(label).classes("col-span-2").props("outlined autogrow")
                                            else:
                                                controls[key] = ui.input(label).props("outlined")

                                    def save() -> None:
                                        payload = {k: (controls[k].value or "") for k in controls}
                                        payload["creado_por"] = _actor_name()
                                        payload["estado"] = payload.get("estado") or "activo"
                                        ok, msg, _id = create_fn(int(empresa_id), payload)
                                        ui.notify(fix_text(msg), type="positive" if ok else "negative")
                                        if ok:
                                            dialog.close()
                                            refresh_table()

                                    with ui.row().classes("w-full justify-end mt-4"):
                                        ui.button("Cancelar", on_click=dialog.close).props("flat")
                                        ui.button("Guardar", icon="save", on_click=save).props("unelevated color=primary")
                                dialog.open()

                            table.on("del", lambda e: (delete_fn(int(e.args)), refresh_table(), ui.notify("Registro eliminado.", type="warning")))
                            refresh_table()

                with ui.tab_panel(tab_map["Equipos"]).classes("w-full"):
                    with ui.card().classes("ideas-panel w-full"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("Gestión de Equipos").classes("ideas-section-title")
                            ui.button("Nuevo", icon="add", on_click=lambda: open_equipo_form()).props("unelevated color=primary")
                        with ui.row().classes("w-full items-center justify-between mt-2"):
                            ui.label("Importación masiva desde Excel habilitada.").classes("ideas-section-note")
                            excel_upload = ui.upload(label="Importar Excel", auto_upload=True, on_upload=lambda e: import_equipos_excel(e)).props('accept=".xlsx,.xls"')

                        equipos_table = ui.table(
                            columns=[
                                {"name": "codigo_interno", "label": "Código", "field": "codigo_interno"},
                                {"name": "nombre", "label": "Nombre", "field": "nombre"},
                                {"name": "estado", "label": "Estado", "field": "estado"},
                                {"name": "criticidad", "label": "Criticidad", "field": "criticidad"},
                                {"name": "fecha_proxima_calibracion", "label": "Próx. calibración", "field": "fecha_proxima_calibracion"},
                                {"name": "acciones", "label": "Acciones", "field": "acciones"},
                            ],
                            rows=[],
                            row_key="id",
                        ).classes("w-full mt-3 ideas-card p-3")
                        equipos_table.add_slot(
                            "body-cell-acciones",
                            """<q-td :props="props"><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('del', props.row.id)" /></q-td>""",
                        )

                        def refresh_equipos() -> None:
                            equipos_table.rows[:] = [{**item, "acciones": ""} for item in obtener_lab_equipos_empresa(int(empresa_id))]
                            equipos_table.update()

                        def open_equipo_form() -> None:
                            with ui.dialog() as dialog, ui.card().classes("ideas-panel w-[760px] max-w-[95vw]"):
                                ui.label("Nuevo equipo").classes("ideas-section-title")
                                codigo = ui.input("Código interno").props("outlined").classes("w-full")
                                nombre = ui.input("Nombre").props("outlined").classes("w-full mt-2")
                                tipo = ui.input("Tipo").props("outlined").classes("w-full mt-2")
                                laboratorio = ui.input("Laboratorio").props("outlined").classes("w-full mt-2")
                                responsable = ui.input("Responsable").props("outlined").classes("w-full mt-2")
                                estado = ui.input("Estado").props("outlined").classes("w-full mt-2")
                                criticidad = ui.input("Criticidad").props("outlined").classes("w-full mt-2")
                                prox = ui.input("Fecha próxima calibración (YYYY-MM-DD)").props("outlined").classes("w-full mt-2")
                                observ = ui.textarea("Observaciones").props("outlined autogrow").classes("w-full mt-2")

                                def save_equipo() -> None:
                                    ok, msg, _eid = crear_lab_equipo(
                                        int(empresa_id),
                                        {
                                            "codigo_interno": codigo.value or "",
                                            "nombre": nombre.value or "",
                                            "tipo": tipo.value or "",
                                            "laboratorio": laboratorio.value or "",
                                            "responsable": responsable.value or "",
                                            "estado": estado.value or "activo",
                                            "criticidad": criticidad.value or "",
                                            "fecha_proxima_calibracion": prox.value or "",
                                            "observaciones": observ.value or "",
                                            "creado_por": _actor_name(),
                                        },
                                    )
                                    ui.notify(msg, type="positive" if ok else "negative")
                                    if ok:
                                        dialog.close()
                                        refresh_equipos()

                                with ui.row().classes("w-full justify-end mt-4"):
                                    ui.button("Cancelar", on_click=dialog.close).props("flat")
                                    ui.button("Guardar", icon="save", on_click=save_equipo).props("unelevated color=primary")
                            dialog.open()

                        def import_equipos_excel(event) -> None:
                            payload = _read_upload_payload(event)
                            if not payload:
                                ui.notify("No se pudo leer el archivo Excel.", type="negative")
                                return
                            try:
                                df = pd.read_excel(BytesIO(payload))
                            except Exception as exc:
                                ui.notify(f"Error leyendo Excel: {exc}", type="negative")
                                return
                            if df.empty:
                                ui.notify("El Excel está vacío.", type="warning")
                                return
                            normalized = {str(col).strip().lower(): col for col in df.columns}
                            def col(name: str) -> str:
                                return normalized.get(name, "")
                            created = 0
                            for _, row in df.fillna("").iterrows():
                                nombre_col = col("nombre")
                                nombre_val = str(row.get(nombre_col, "")).strip() if nombre_col else ""
                                if not nombre_val:
                                    continue
                                ok, _msg, _eid = crear_lab_equipo(
                                    int(empresa_id),
                                    {
                                        "codigo_interno": str(row.get(col("codigo_interno"), "")).strip() if col("codigo_interno") else "",
                                        "nombre": nombre_val,
                                        "tipo": str(row.get(col("tipo"), "")).strip() if col("tipo") else "",
                                        "marca": str(row.get(col("marca"), "")).strip() if col("marca") else "",
                                        "modelo": str(row.get(col("modelo"), "")).strip() if col("modelo") else "",
                                        "serie": str(row.get(col("serie"), "")).strip() if col("serie") else "",
                                        "ubicacion": str(row.get(col("ubicacion"), "")).strip() if col("ubicacion") else "",
                                        "laboratorio": str(row.get(col("laboratorio"), "")).strip() if col("laboratorio") else "",
                                        "responsable": str(row.get(col("responsable"), "")).strip() if col("responsable") else "",
                                        "estado": str(row.get(col("estado"), "")).strip() if col("estado") else "activo",
                                        "criticidad": str(row.get(col("criticidad"), "")).strip() if col("criticidad") else "",
                                        "fecha_proxima_calibracion": str(row.get(col("fecha_proxima_calibracion"), "")).strip() if col("fecha_proxima_calibracion") else "",
                                        "creado_por": _actor_name(),
                                    },
                                )
                                if ok:
                                    created += 1
                            refresh_equipos()
                            ui.notify(f"Importación completada: {created} equipos cargados.", type="positive")

                        equipos_table.on("del", lambda e: (eliminar_lab_equipo(int(e.args)), refresh_equipos(), ui.notify("Equipo eliminado.", type="warning")))
                        refresh_equipos()

                render_simple_crud(
                    panel=tab_map["Calibraciones"],
                    title="Calibraciones y Mantenimiento",
                    columns=[
                        {"name": "tipo", "label": "Tipo", "field": "tipo"},
                        {"name": "fecha", "label": "Fecha", "field": "fecha"},
                        {"name": "proveedor", "label": "Proveedor", "field": "proveedor"},
                        {"name": "conformidad", "label": "Conformidad", "field": "conformidad"},
                        {"name": "proxima_fecha", "label": "Próxima", "field": "proxima_fecha"},
                    ],
                    rows_fn=obtener_lab_calibraciones_empresa,
                    create_fn=crear_lab_calibracion,
                    delete_fn=eliminar_lab_calibracion,
                    form_fields=[
                        ("equipo_id", "ID Equipo", "text"),
                        ("tipo", "Tipo (calibración/verificación/...)", "text"),
                        ("fecha", "Fecha (YYYY-MM-DD)", "text"),
                        ("proveedor", "Proveedor", "text"),
                        ("resultado", "Resultado", "text"),
                        ("conformidad", "Conformidad", "text"),
                        ("proxima_fecha", "Próxima fecha", "text"),
                        ("impacto_potencial", "Impacto potencial", "textarea"),
                    ],
                )

                with ui.tab_panel(tab_map["Metodos"]).classes("w-full"):
                    with ui.card().classes("ideas-panel w-full"):
                        with ui.row().classes("w-full items-center justify-between"):
                            ui.label("Métodos de Ensayo / Calibración").classes("ideas-section-title")
                            ui.button("Nuevo método", icon="add", on_click=lambda: open_metodo_form()).props("unelevated color=primary")

                        metodos_table = ui.table(
                            columns=[
                                {"name": "codigo", "label": "Código", "field": "codigo"},
                                {"name": "nombre", "label": "Nombre", "field": "nombre"},
                                {"name": "version", "label": "Versión", "field": "version"},
                                {"name": "estado", "label": "Estado", "field": "estado"},
                                {"name": "documentos_count", "label": "Docs", "field": "documentos_count"},
                                {"name": "acciones", "label": "Acciones", "field": "acciones"},
                            ],
                            rows=[],
                            row_key="id",
                        ).classes("w-full mt-3 ideas-card p-3")
                        metodos_table.add_slot(
                            "body-cell-acciones",
                            """<q-td :props="props"><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('del', props.row.id)" /></q-td>""",
                        )

                        def refresh_metodos() -> None:
                            rows = []
                            for item in obtener_lab_metodos_empresa(int(empresa_id)):
                                raw_docs = str(item.get("documentos") or "")
                                docs_count = 0
                                if raw_docs:
                                    try:
                                        docs_count = len(json.loads(raw_docs))
                                    except Exception:
                                        docs_count = len([x for x in raw_docs.split(",") if x.strip()])
                                rows.append({**item, "documentos_count": docs_count, "acciones": ""})
                            metodos_table.rows[:] = rows
                            metodos_table.update()

                        def open_metodo_form() -> None:
                            with ui.dialog() as dialog, ui.card().classes("ideas-panel w-[800px] max-w-[95vw]"):
                                ui.label("Nuevo método").classes("ideas-section-title")
                                codigo = ui.input("Código").props("outlined").classes("w-full")
                                nombre = ui.input("Nombre").props("outlined").classes("w-full mt-2")
                                version = ui.input("Versión").props("outlined").classes("w-full mt-2")
                                norma = ui.input("Norma").props("outlined").classes("w-full mt-2")
                                responsable = ui.input("Responsable técnico").props("outlined").classes("w-full mt-2")
                                estado = ui.input("Estado").props("outlined").classes("w-full mt-2")
                                criterios = ui.textarea("Criterios de aceptación").props("outlined autogrow").classes("w-full mt-2")
                                docs_paths: list[str] = []
                                docs_preview = ui.column().classes("w-full mt-3")
                                upload_root = Path(__file__).resolve().parents[1] / "uploads" / "lab_metodos" / f"empresa_{int(empresa_id)}"
                                upload_root.mkdir(parents=True, exist_ok=True)

                                def refresh_docs_preview() -> None:
                                    docs_preview.clear()
                                    with docs_preview:
                                        if not docs_paths:
                                            ui.label("Sin documentos adjuntos.").classes("ideas-section-note")
                                        else:
                                            for path in docs_paths:
                                                ui.label(Path(path).name).classes("text-sm text-slate-600")

                                def handle_doc_upload(event) -> None:
                                    payload = _read_upload_payload(event)
                                    if not payload:
                                        ui.notify("No se pudo leer el documento.", type="negative")
                                        return
                                    raw_name = str(getattr(getattr(event, "file", None), "name", None) or getattr(event, "name", None) or "documento.bin")
                                    safe_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{Path(raw_name).name}"
                                    target = upload_root / safe_name
                                    target.write_bytes(payload)
                                    docs_paths.append(str(target))
                                    refresh_docs_preview()
                                    ui.notify("Documento cargado.", type="positive")

                                ui.upload(label="Adjuntar documento del método", auto_upload=True, on_upload=handle_doc_upload).props('accept=".pdf,.doc,.docx,.xls,.xlsx,.png,.jpg,.jpeg,.txt"').classes("w-full mt-2")
                                refresh_docs_preview()

                                def save_metodo() -> None:
                                    ok, msg, _mid = crear_lab_metodo(
                                        int(empresa_id),
                                        {
                                            "codigo": codigo.value or "",
                                            "nombre": nombre.value or "",
                                            "version": version.value or "",
                                            "norma": norma.value or "",
                                            "responsable_tecnico": responsable.value or "",
                                            "estado": estado.value or "borrador",
                                            "criterios_aceptacion": criterios.value or "",
                                            "documentos": json.dumps(docs_paths, ensure_ascii=False),
                                            "creado_por": _actor_name(),
                                        },
                                    )
                                    ui.notify(msg, type="positive" if ok else "negative")
                                    if ok:
                                        dialog.close()
                                        refresh_metodos()

                                with ui.row().classes("w-full justify-end mt-4"):
                                    ui.button("Cancelar", on_click=dialog.close).props("flat")
                                    ui.button("Guardar", icon="save", on_click=save_metodo).props("unelevated color=primary")
                            dialog.open()

                        metodos_table.on("del", lambda e: (eliminar_lab_metodo(int(e.args)), refresh_metodos(), ui.notify("Método eliminado.", type="warning")))
                        refresh_metodos()

                render_simple_crud(
                    panel=tab_map["Muestras"],
                    title="Gestión de Muestras",
                    columns=[
                        {"name": "codigo_unico", "label": "Código", "field": "codigo_unico"},
                        {"name": "cliente", "label": "Cliente", "field": "cliente"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                        {"name": "metodo", "label": "Método", "field": "metodo"},
                        {"name": "prioridad", "label": "Prioridad", "field": "prioridad"},
                    ],
                    rows_fn=obtener_lab_muestras_empresa,
                    create_fn=crear_lab_muestra,
                    delete_fn=eliminar_lab_muestra,
                    form_fields=[
                        ("codigo_unico", "Código único", "text"),
                        ("cliente", "Cliente", "text"),
                        ("fecha_recepcion", "Fecha recepción", "text"),
                        ("responsable", "Responsable", "text"),
                        ("estado", "Estado", "text"),
                        ("metodo", "Método", "text"),
                        ("prioridad", "Prioridad", "text"),
                        ("observaciones", "Observaciones", "textarea"),
                    ],
                )

                render_simple_crud(
                    panel=tab_map["Competencias"],
                    title="Competencia del Personal",
                    columns=[
                        {"name": "persona", "label": "Persona", "field": "persona"},
                        {"name": "rol", "label": "Rol", "field": "rol"},
                        {"name": "metodo_autorizado", "label": "Método", "field": "metodo_autorizado"},
                        {"name": "vencimiento", "label": "Vencimiento", "field": "vencimiento"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                    ],
                    rows_fn=obtener_lab_competencias_empresa,
                    create_fn=crear_lab_competencia,
                    delete_fn=eliminar_lab_competencia,
                    form_fields=[
                        ("persona", "Persona", "text"),
                        ("rol", "Rol", "text"),
                        ("metodo_autorizado", "Método autorizado", "text"),
                        ("fecha_autorizacion", "Fecha autorización", "text"),
                        ("vencimiento", "Vencimiento", "text"),
                        ("evaluador", "Evaluador", "text"),
                        ("estado", "Estado", "text"),
                    ],
                )

                with ui.tab_panel(tab_map["Incertidumbre"]).classes("w-full"):
                    with ui.card().classes("ideas-panel"):
                        ui.label("Incertidumbre de Medición").classes("ideas-section-title")
                        ui.label("Estructura base con cálculo uc = sqrt(sum(ui²)) y U = k * uc.").classes("ideas-section-note")
                        method_input = ui.input("Método para calcular").props("outlined").classes("w-full mt-3")
                        result_box = ui.column().classes("w-full mt-3")

                        def do_calc() -> None:
                            result_box.clear()
                            res = calcular_incertidumbre_metodo(int(empresa_id), method_input.value or "")
                            with result_box:
                                ui.html(f'<div class="ideas-quick-card"><div class="label">COMPONENTES</div><div class="value">{res["componentes"]}</div></div>')
                                ui.html(f'<div class="ideas-quick-card"><div class="label">uc</div><div class="value">{res["uc"]:.6f}</div></div>')
                                ui.html(f'<div class="ideas-quick-card"><div class="label">U (k={res["k"]})</div><div class="value">{res["U"]:.6f}</div></div>')

                        ui.button("Calcular incertidumbre", icon="calculate", on_click=do_calc).props("unelevated color=primary").classes("mt-3")
                        comp_table = ui.table(
                            columns=[
                                {"name": "metodo", "label": "Método", "field": "metodo"},
                                {"name": "componente", "label": "Componente", "field": "componente"},
                                {"name": "incertidumbre_estandar", "label": "ui", "field": "incertidumbre_estandar"},
                                {"name": "k", "label": "k", "field": "k"},
                                {"name": "acciones", "label": "Acciones", "field": "acciones"},
                            ],
                            rows=[],
                            row_key="id",
                        ).classes("w-full mt-4 ideas-card p-3")
                        comp_table.add_slot(
                            "body-cell-acciones",
                            """<q-td :props="props"><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('del', props.row.id)" /></q-td>""",
                        )

                        def refresh_components() -> None:
                            comp_table.rows[:] = [{**item, "acciones": ""} for item in obtener_lab_incertidumbre_empresa(int(empresa_id))]
                            comp_table.update()

                        def open_component_form() -> None:
                            with ui.dialog() as dialog, ui.card().classes("ideas-panel w-[760px] max-w-[95vw]"):
                                ui.label("Nuevo componente de incertidumbre").classes("ideas-section-title")
                                metodo_i = ui.input("Método").props("outlined").classes("w-full")
                                componente_i = ui.input("Componente").props("outlined").classes("w-full mt-2")
                                tipo_i = ui.input("Tipo A/B").props("outlined").classes("w-full mt-2")
                                dist_i = ui.input("Distribución").props("outlined").classes("w-full mt-2")
                                cs_i = ui.input("Coef. sensibilidad").props("outlined").classes("w-full mt-2")
                                valor_i = ui.input("Valor").props("outlined").classes("w-full mt-2")
                                ui_i = ui.input("Incertidumbre estándar").props("outlined").classes("w-full mt-2")
                                k_i = ui.input("k").props("outlined").classes("w-full mt-2")

                                def save_comp() -> None:
                                    ok, msg, _nid = crear_lab_incertidumbre_componente(
                                        int(empresa_id),
                                        {
                                            "metodo": metodo_i.value or "",
                                            "componente": componente_i.value or "",
                                            "tipo_ab": tipo_i.value or "",
                                            "distribucion": dist_i.value or "",
                                            "coef_sensibilidad": cs_i.value or 0,
                                            "valor": valor_i.value or 0,
                                            "incertidumbre_estandar": ui_i.value or 0,
                                            "k": k_i.value or 2,
                                            "creado_por": _actor_name(),
                                        },
                                    )
                                    ui.notify(msg, type="positive" if ok else "negative")
                                    if ok:
                                        dialog.close()
                                        refresh_components()

                                with ui.row().classes("w-full justify-end mt-4"):
                                    ui.button("Cancelar", on_click=dialog.close).props("flat")
                                    ui.button("Guardar", icon="save", on_click=save_comp).props("unelevated color=primary")
                            dialog.open()

                        comp_table.on("del", lambda e: (eliminar_lab_incertidumbre_componente(int(e.args)), refresh_components(), ui.notify("Componente eliminado.", type="warning")))
                        ui.button("Nuevo componente", icon="add", on_click=open_component_form).props("outline color=primary").classes("mt-3")
                        refresh_components()

                render_simple_crud(
                    panel=tab_map["Control de Calidad"],
                    title="Control de Calidad Interno",
                    columns=[
                        {"name": "metodo", "label": "Método", "field": "metodo"},
                        {"name": "equipo", "label": "Equipo", "field": "equipo"},
                        {"name": "fecha", "label": "Fecha", "field": "fecha"},
                        {"name": "resultado", "label": "Resultado", "field": "resultado"},
                        {"name": "conformidad", "label": "Conformidad", "field": "conformidad"},
                    ],
                    rows_fn=obtener_lab_control_calidad_empresa,
                    create_fn=crear_lab_control_calidad,
                    delete_fn=eliminar_lab_control_calidad,
                    form_fields=[
                        ("metodo", "Método", "text"),
                        ("equipo", "Equipo", "text"),
                        ("fecha", "Fecha", "text"),
                        ("control", "Control", "text"),
                        ("resultado", "Resultado", "text"),
                        ("limite_inferior", "Límite inferior", "text"),
                        ("limite_superior", "Límite superior", "text"),
                        ("conformidad", "Conformidad", "text"),
                    ],
                )

                render_simple_crud(
                    panel=tab_map["Informes"],
                    title="Informes / Certificados",
                    columns=[
                        {"name": "numero_informe", "label": "Nro informe", "field": "numero_informe"},
                        {"name": "cliente", "label": "Cliente", "field": "cliente"},
                        {"name": "muestra", "label": "Muestra", "field": "muestra"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                        {"name": "emision", "label": "Emisión", "field": "emision"},
                    ],
                    rows_fn=obtener_lab_informes_empresa,
                    create_fn=crear_lab_informe,
                    delete_fn=eliminar_lab_informe,
                    form_fields=[
                        ("numero_informe", "Número informe", "text"),
                        ("cliente", "Cliente", "text"),
                        ("muestra", "Muestra", "text"),
                        ("metodo", "Método", "text"),
                        ("resultado", "Resultado", "textarea"),
                        ("incertidumbre", "Incertidumbre", "text"),
                        ("responsable_tecnico", "Responsable técnico", "text"),
                        ("revisor", "Revisor", "text"),
                        ("estado", "Estado", "text"),
                        ("emision", "Emisión", "text"),
                    ],
                )

                render_simple_crud(
                    panel=tab_map["Auditorias"],
                    title="Auditorías ISO 17025",
                    columns=[
                        {"name": "clausula", "label": "Cláusula", "field": "clausula"},
                        {"name": "pregunta", "label": "Pregunta", "field": "pregunta"},
                        {"name": "resultado", "label": "Resultado", "field": "resultado"},
                        {"name": "responsable", "label": "Responsable", "field": "responsable"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                    ],
                    rows_fn=obtener_lab_auditorias_empresa,
                    create_fn=crear_lab_auditoria,
                    delete_fn=eliminar_lab_auditoria,
                    form_fields=[
                        ("clausula", "Cláusula (4/5/6/7/8)", "text"),
                        ("pregunta", "Pregunta", "textarea"),
                        ("evidencia", "Evidencia", "textarea"),
                        ("resultado", "Resultado", "text"),
                        ("hallazgo", "Hallazgo", "textarea"),
                        ("accion", "Acción", "textarea"),
                        ("responsable", "Responsable", "text"),
                        ("fecha", "Fecha", "text"),
                        ("estado", "Estado", "text"),
                    ],
                )

                render_simple_crud(
                    panel=tab_map["Riesgos"],
                    title="Riesgos y Oportunidades",
                    columns=[
                        {"name": "proceso", "label": "Proceso", "field": "proceso"},
                        {"name": "riesgo", "label": "Riesgo", "field": "riesgo"},
                        {"name": "nivel", "label": "Nivel", "field": "nivel"},
                        {"name": "responsable", "label": "Responsable", "field": "responsable"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                    ],
                    rows_fn=obtener_lab_riesgos_empresa,
                    create_fn=crear_lab_riesgo,
                    delete_fn=eliminar_lab_riesgo,
                    form_fields=[
                        ("proceso", "Proceso", "text"),
                        ("riesgo", "Riesgo", "textarea"),
                        ("causa", "Causa", "textarea"),
                        ("consecuencia", "Consecuencia", "textarea"),
                        ("probabilidad", "Probabilidad", "text"),
                        ("severidad", "Severidad", "text"),
                        ("accion", "Acción", "textarea"),
                        ("responsable", "Responsable", "text"),
                        ("estado", "Estado", "text"),
                    ],
                )

                render_simple_crud(
                    panel=tab_map["Acciones Correctivas"],
                    title="Acciones Correctivas",
                    columns=[
                        {"name": "origen", "label": "Origen", "field": "origen"},
                        {"name": "descripcion", "label": "Descripción", "field": "descripcion"},
                        {"name": "responsable", "label": "Responsable", "field": "responsable"},
                        {"name": "vencimiento", "label": "Vencimiento", "field": "vencimiento"},
                        {"name": "estado", "label": "Estado", "field": "estado"},
                    ],
                    rows_fn=obtener_lab_acciones_empresa,
                    create_fn=crear_lab_accion,
                    delete_fn=eliminar_lab_accion,
                    form_fields=[
                        ("origen", "Origen", "text"),
                        ("descripcion", "Descripción", "textarea"),
                        ("analisis_causa", "Análisis causa", "textarea"),
                        ("accion_inmediata", "Acción inmediata", "textarea"),
                        ("accion_correctiva", "Acción correctiva", "textarea"),
                        ("responsable", "Responsable", "text"),
                        ("vencimiento", "Vencimiento", "text"),
                        ("eficacia", "Eficacia", "text"),
                        ("estado", "Estado", "text"),
                    ],
                )

                with ui.tab_panel(tab_map["IA LAB"]).classes("w-full"):
                    with ui.card().classes("ideas-panel"):
                        ui.label("IA Técnica LAB").classes("ideas-section-title")
                        ui.label("Rules Engine + IA contextual + alertas + reportes pre-acreditación.").classes("ideas-section-note")
                        persona = ui.input("Persona").props("outlined").classes("w-full mt-3")
                        metodo = ui.input("Método a validar").props("outlined").classes("w-full mt-2")
                        result = ui.column().classes("w-full mt-3")

                        def run_quick_check() -> None:
                            result.clear()
                            ok, msg = validar_competencia_para_metodo(int(empresa_id), persona.value or "", metodo.value or "")
                            with result:
                                ui.notify(msg, type="positive" if ok else "warning")
                                ui.label(msg).classes("ideas-section-note")

                        ui.button("Validar competencia para método", icon="verified_user", on_click=run_quick_check).props("unelevated color=primary").classes("mt-3")
                        with ui.row().classes("w-full gap-2 mt-4"):
                            ui.button(
                                "Ejecutar chequeo automático",
                                icon="play_circle",
                                on_click=lambda: ui.notify(
                                    f"Alertas: {ejecutar_chequeo_lab_empresa(int(empresa_id), actor='manual').get('alerts_created', 0)}",
                                    type="positive",
                                ),
                            ).props("unelevated color=primary")
                            def generate_and_download_report() -> None:
                                report = generar_reporte_pre_acreditacion_lab(int(empresa_id), actor="manual")
                                payload = json.dumps(report, ensure_ascii=False, indent=2).encode("utf-8")
                                filename = f"reporte_pre_acreditacion_iso17025_empresa_{int(empresa_id)}.json"
                                ui.download(payload, filename=filename, media_type="application/json")
                                ui.notify(
                                    f"Reporte generado y descargado (score {report.get('score_general', 0)}).",
                                    type="positive",
                                )

                            ui.button(
                                "Generar reporte pre-acreditación",
                                icon="summarize",
                                on_click=generate_and_download_report,
                            ).props("outline color=primary")

                        settings = obtener_lab_ai_settings(int(empresa_id))
                        with ui.card().classes("w-full mt-4 border border-slate-200 p-4"):
                            ui.label("Automatización IA").classes("ideas-section-title")
                            auto_ia = ui.switch("IA automática activa", value=bool(int(settings.get("ia_automatica_activa") or 1)))
                            scheduler_active = ui.switch("Scheduler activo", value=bool(int(settings.get("scheduler_activo") or 0)))
                            daily_time = ui.input("Horario diario (HH:MM)", value=str(settings.get("frecuencia_diaria") or "08:30")).props("outlined").classes("w-full mt-2")
                            week_day = ui.input("Día semanal", value=str(settings.get("frecuencia_semanal_dia") or "monday")).props("outlined").classes("w-full mt-2")
                            week_time = ui.input("Hora semanal (HH:MM)", value=str(settings.get("frecuencia_semanal_hora") or "09:00")).props("outlined").classes("w-full mt-2")
                            max_cycle = ui.input("Máx análisis por ciclo", value=str(settings.get("max_analisis_por_ciclo") or 20)).props("outlined").classes("w-full mt-2")

                            def save_ai_settings() -> None:
                                ok, msg = guardar_lab_ai_settings(
                                    int(empresa_id),
                                    {
                                        "ia_automatica_activa": bool(auto_ia.value),
                                        "scheduler_activo": bool(scheduler_active.value),
                                        "frecuencia_diaria": daily_time.value or "08:30",
                                        "frecuencia_semanal_dia": week_day.value or "monday",
                                        "frecuencia_semanal_hora": week_time.value or "09:00",
                                        "max_analisis_por_ciclo": int(max_cycle.value or 20),
                                        "actualizado_por": _actor_name(),
                                    },
                                )
                                ui.notify(msg, type="positive" if ok else "negative")

                            ui.button("Guardar automatización", icon="save", on_click=save_ai_settings).props("unelevated color=primary").classes("mt-3")

                        with ui.card().classes("w-full mt-4 border border-slate-200 p-4"):
                            ui.label("Alertas generadas").classes("ideas-section-title")
                            filt_mod = ui.input("Filtro módulo").props("outlined").classes("w-full")
                            filt_crit = ui.input("Filtro criticidad").props("outlined").classes("w-full mt-2")
                            filt_estado = ui.input("Filtro estado").props("outlined").classes("w-full mt-2")
                            alerts_table = ui.table(
                                columns=[
                                    {"name": "id", "label": "ID", "field": "id"},
                                    {"name": "titulo", "label": "Título", "field": "titulo"},
                                    {"name": "modulo_origen", "label": "Módulo", "field": "modulo_origen"},
                                    {"name": "criticidad", "label": "Criticidad", "field": "criticidad"},
                                    {"name": "estado", "label": "Estado", "field": "estado"},
                                    {"name": "tipo", "label": "Tipo", "field": "tipo"},
                                    {"name": "acciones", "label": "Acciones", "field": "acciones"},
                                ],
                                rows=[],
                                row_key="id",
                            ).classes("w-full mt-3 ideas-card p-3")
                            alerts_table.add_slot(
                                "body-cell-acciones",
                                """<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="task_alt" color="positive" @click="$parent.$emit('close_alert', props.row.id)" /><q-btn flat round dense icon="build" color="primary" @click="$parent.$emit('to_action', props.row.id)" /><q-btn flat round dense icon="block" color="negative" @click="$parent.$emit('discard_alert', props.row.id)" /></div></q-td>""",
                            )

                            def refresh_alerts() -> None:
                                rows = obtener_lab_alertas_empresa(
                                    int(empresa_id),
                                    estado=str(filt_estado.value or ""),
                                    criticidad=str(filt_crit.value or ""),
                                    modulo=str(filt_mod.value or ""),
                                )
                                alerts_table.rows[:] = [{**r, "acciones": ""} for r in rows]
                                alerts_table.update()

                            alerts_table.on("close_alert", lambda e: (actualizar_lab_alerta_estado(int(e.args), "cerrada", "Cierre manual"), refresh_alerts(), ui.notify("Alerta cerrada.", type="positive")))
                            alerts_table.on("discard_alert", lambda e: (actualizar_lab_alerta_estado(int(e.args), "descartada", "Descartada por usuario"), refresh_alerts(), ui.notify("Alerta descartada.", type="warning")))
                            alerts_table.on("to_action", lambda e: (convertir_alerta_en_accion_lab(int(e.args), int(empresa_id), responsable=_actor_name()), refresh_alerts(), ui.notify("Alerta convertida en acción.", type="positive")))
                            ui.button("Aplicar filtros", icon="filter_alt", on_click=refresh_alerts).props("outline color=primary").classes("mt-2")
                            refresh_alerts()

                        with ui.card().classes("w-full mt-4 border border-slate-200 p-4"):
                            ui.label("Reportes generados").classes("ideas-section-title")
                            reports = obtener_reportes_lab_ai(int(empresa_id))
                            if not reports:
                                ui.label("Sin reportes aún.").classes("ideas-section-note")
                            else:
                                for rep in reports[:8]:
                                    ui.label(f"#{rep.get('id')} · {rep.get('tipo')} · score {rep.get('score_general')} · {rep.get('created_at')}").classes("text-sm text-slate-600")

                with ui.tab_panel(tab_map["Configuracion LAB"]).classes("w-full"):
                    with ui.card().classes("ideas-panel"):
                        ui.label("Configuración LAB").classes("ideas-section-title")
                        lab_nombre = ui.input("Nombre del laboratorio", value=str(config.get("lab_nombre") or "")).props("outlined").classes("w-full")
                        mobile_switch = ui.switch("Activar Mobile Lab", value=mobile_enabled).classes("mt-2")
                        tipos_ensayo = ui.input("Tipos de ensayo (csv)", value=str(config.get("tipos_ensayo") or "")).props("outlined").classes("w-full mt-2")
                        estados = ui.input("Estados (csv)", value=str(config.get("estados_personalizados") or "")).props("outlined").classes("w-full mt-2")
                        criticidades = ui.input("Criticidades (csv)", value=str(config.get("criticidades") or "")).props("outlined").classes("w-full mt-2")
                        frecuencias = ui.input("Frecuencias (csv)", value=str(config.get("frecuencias") or "")).props("outlined").classes("w-full mt-2")
                        formatos = ui.input("Formatos de informe", value=str(config.get("formatos_informe") or "")).props("outlined").classes("w-full mt-2")

                        def save_config() -> None:
                            ok, msg = guardar_lab_configuracion(
                                int(empresa_id),
                                {
                                    "lab_nombre": lab_nombre.value or "",
                                    "mobile_lab_activo": bool(mobile_switch.value),
                                    "tipos_ensayo": tipos_ensayo.value or "",
                                    "estados_personalizados": estados.value or "",
                                    "criticidades": criticidades.value or "",
                                    "frecuencias": frecuencias.value or "",
                                    "formatos_informe": formatos.value or "",
                                    "actualizado_por": _actor_name(),
                                },
                            )
                            ui.notify(msg, type="positive" if ok else "negative")
                            if ok:
                                ui.navigate.to("/sistema-gestion/lab-iso-17025")

                        ui.button("Guardar configuración", icon="save", on_click=save_config).props("unelevated color=primary").classes("mt-3")

                if "Mobile Lab" in tab_map:
                    with ui.tab_panel(tab_map["Mobile Lab"]).classes("w-full"):
                        with ui.grid(columns=2).classes("w-full gap-3"):
                            with ui.card().classes("ideas-panel"):
                                ui.label("15A · Vehículos").classes("ideas-section-title")
                                unidad = ui.input("Unidad móvil").props("outlined").classes("w-full")
                                patente = ui.input("Patente").props("outlined").classes("w-full mt-2")
                                modelo = ui.input("Modelo").props("outlined").classes("w-full mt-2")
                                responsable = ui.input("Responsable").props("outlined").classes("w-full mt-2")

                                def save_unidad() -> None:
                                    ok, msg, _nid = crear_lab_mobile_unidad(
                                        int(empresa_id),
                                        {
                                            "unidad_movil": unidad.value or "",
                                            "patente": patente.value or "",
                                            "modelo": modelo.value or "",
                                            "responsable": responsable.value or "",
                                            "estado": "activo",
                                            "creado_por": _actor_name(),
                                        },
                                    )
                                    ui.notify(msg, type="positive" if ok else "negative")
                                    if ok:
                                        ui.navigate.to("/sistema-gestion/lab-iso-17025")

                                ui.button("Guardar unidad", icon="save", on_click=save_unidad).props("unelevated color=primary").classes("mt-3")

                            with ui.card().classes("ideas-panel"):
                                ui.label("15B-15H · Operación Mobile").classes("ideas-section-title")
                                gps = ui.input("GPS").props("outlined").classes("w-full")
                                cliente = ui.input("Cliente").props("outlined").classes("w-full mt-2")
                                tecnico = ui.input("Técnico").props("outlined").classes("w-full mt-2")
                                ensayo = ui.input("Ensayo").props("outlined").classes("w-full mt-2")
                                temp = ui.input("Temperatura").props("outlined").classes("w-full mt-2")
                                hum = ui.input("Humedad").props("outlined").classes("w-full mt-2")
                                pres = ui.input("Presión").props("outlined").classes("w-full mt-2")
                                vib = ui.input("Vibración").props("outlined").classes("w-full mt-2")
                                firma = ui.textarea("Firma digital (base64/texto)").props("outlined autogrow").classes("w-full mt-2")

                                def save_mobile_registro() -> None:
                                    now = datetime.now()
                                    checklist = {
                                        "equipo_calibrado": True,
                                        "operador_habilitado": True,
                                        "metodo_vigente": True,
                                        "condiciones_ok": True,
                                        "epp": True,
                                        "bateria": True,
                                        "vehiculo": True,
                                    }
                                    custodia = [{"evento": "toma_muestra", "responsable": tecnico.value or "", "timestamp": now.strftime("%Y-%m-%d %H:%M:%S")}]
                                    ok, msg, _nid = crear_lab_mobile_registro(
                                        int(empresa_id),
                                        {
                                            "unidad_movil": "",
                                            "gps": gps.value or "",
                                            "fecha": now.strftime("%Y-%m-%d"),
                                            "hora": now.strftime("%H:%M:%S"),
                                            "cliente": cliente.value or "",
                                            "tecnico": tecnico.value or "",
                                            "ensayo": ensayo.value or "",
                                            "temperatura": temp.value or 0,
                                            "humedad": hum.value or 0,
                                            "presion": pres.value or 0,
                                            "vibracion": vib.value or 0,
                                            "energia": "OK",
                                            "cadena_custodia_json": json.dumps(custodia, ensure_ascii=False),
                                            "checklist_operativo_json": json.dumps(checklist, ensure_ascii=False),
                                            "firma_digital": firma.value or "",
                                            "sync_estado": "pendiente",
                                            "creado_por": _actor_name(),
                                        },
                                    )
                                    ui.notify(msg, type="positive" if ok else "negative")
                                    if ok:
                                        ui.navigate.to("/sistema-gestion/lab-iso-17025")

                                ui.button("Registrar operación mobile", icon="cloud_upload", on_click=save_mobile_registro).props("unelevated color=primary").classes("mt-3")

                        with ui.card().classes("ideas-panel mt-4"):
                            ui.label("Unidades registradas").classes("ideas-section-title")
                            unidades = obtener_lab_mobile_unidades_empresa(int(empresa_id))
                            registros = obtener_lab_mobile_registros_empresa(int(empresa_id))
                            ui.label(f"Unidades: {len(unidades)} · Operaciones: {len(registros)} · Cola offline: {len([r for r in registros if str(r.get('sync_estado') or '') == 'pendiente'])}").classes("ideas-section-note")
