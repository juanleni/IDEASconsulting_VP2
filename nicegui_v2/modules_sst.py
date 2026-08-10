from __future__ import annotations

from nicegui import app, ui

from dashboard_customizer import render_dashboard_customizer
from company_context import empresa_id_from_query_for_admin, with_empresa_id


def go_to_sst_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user["management_company_id"] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id("/sistema-gestion/salud-ocupacional", company_id))


def register_sst_module(ui, deps: dict) -> None:
    ensure_platform_access = deps["ensure_platform_access"]
    shell = deps["shell"]
    current_selection = deps["current_selection"]
    set_selection = deps["set_selection"]
    company_options = deps["company_options"]
    obtener_empresa_detalle = deps["obtener_empresa_detalle"]
    obtener_mapa_procesos_empresa = deps["obtener_mapa_procesos_empresa"]
    fix_text = deps["fix_text"]
    obtener_sst_capacitaciones_empresa = deps["obtener_sst_capacitaciones_empresa"]
    crear_sst_capacitacion = deps["crear_sst_capacitacion"]
    actualizar_sst_capacitacion = deps["actualizar_sst_capacitacion"]
    eliminar_sst_capacitacion = deps["eliminar_sst_capacitacion"]

    @ui.page("/sistema-gestion/salud-ocupacional")
    def sst_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell("Salud ocupacional", back_route="/sistema-gestion", module_key="sst")
        company_map = company_options()
        query_empresa_id = empresa_id_from_query_for_admin()
        selected_company_id = query_empresa_id or app.storage.user.get("management_company_id") or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        if query_empresa_id and selected_company_id:
            app.storage.user["management_company_id"] = selected_company_id
            set_selection(selected_company_id, None)
        if not selected_company_id and company_map:
            selected_company_id = next(iter(company_map.keys()))
            app.storage.user["management_company_id"] = selected_company_id
            set_selection(selected_company_id, None)

        with shell_container:
            ui.label("Salud ocupacional").classes("ideas-kicker")
            ui.label("Modulo SST por empresa").classes("text-3xl font-bold text-slate-900")
            ui.label("Estructura basada en Panel SST, con navegación por tabs.").classes("ideas-subtitle mb-3")

            if not company_map:
                ui.label("Primero necesitas registrar una empresa para habilitar este modulo.").classes("text-slate-500")
                return

            if str(app.storage.user.get("role") or "") == "admin":
                company_select = ui.select(company_map, value=selected_company_id, label="Empresa-cliente").classes("w-full").props("outlined")
                company_select.on_value_change(
                    lambda _e: (
                        app.storage.user.__setitem__("management_company_id", int(company_select.value) if company_select.value else None),
                        set_selection(int(company_select.value), None) if company_select.value else None,
                        ui.navigate.to(with_empresa_id("/sistema-gestion/salud-ocupacional", company_select.value)),
                    )
                )

            if not selected_company_id:
                return

            empresa = obtener_empresa_detalle(int(selected_company_id)) or {}
            _ = fix_text(empresa.get("razon_social", company_map.get(selected_company_id, "")))
            process_rows = obtener_mapa_procesos_empresa(int(selected_company_id))
            sst_processes = [
                row
                for row in process_rows
                if "salud" in str(row.get("proceso_nombre") or "").lower()
                or "seguridad" in str(row.get("proceso_nombre") or "").lower()
            ]

            panel_structure = [
                {"id": "riesgos", "label": "Riesgos", "icon": "warning", "items": ["Matriz de riesgos"]},
                {"id": "cumplimiento_legal", "label": "Cumplimiento legal", "icon": "gavel", "items": ["Matriz legal", "Documentos - Certificaciones"]},
                {"id": "incidentes_accidentes", "label": "Incidentes / Accidentes", "icon": "report", "items": ["Registro de incidentes", "Registro de accidentes"]},
                {"id": "salud_ocupacional", "label": "Salud Ocupacional", "icon": "health_and_safety", "items": ["Enfermedades profesionales", "Restricciones laborales"]},
                {"id": "prevencion", "label": "Prevención", "icon": "verified_user", "items": ["Trabajos de riesgo", "Controles y mediciones", "Ergonomía", "Prevención de emergencias"]},
                {"id": "equipos_qcos", "label": "Equipos/Productos químicos", "icon": "science", "items": ["Inventario", "Registros - Hojas de seguridad"]},
                {"id": "capacitaciones", "label": "Capacitaciones", "icon": "school", "items": ["Plan de capacitaciones anual", "Registros"]},
                {"id": "epp", "label": "EPP", "icon": "construction", "items": ["Listado de EPP utilizados - certificaciones", "Formulario 299"]},
                {"id": "plan_accion_sst", "label": "Plan de Acción de gestión de Seguridad y Salud en el Trabajo", "icon": "task_alt", "items": []},
                {"id": "kpis", "label": "KPI's", "icon": "insights", "items": []},
            ]

            def _open_submodule(_target: str | None = None) -> None:
                ui.notify("Submódulo en preparación.", type="warning")

            total_submodulos = sum(len(block.get("items", [])) for block in panel_structure)
            total_bloques = len(panel_structure)
            score = int((total_submodulos / max(1, total_bloques * 3)) * 100)

            panel_tab_map: dict[str, any] = {}
            with ui.tabs().classes("w-full mt-4 ideas-panel p-2 rounded-[24px]") as panel_tabs:
                tab_dashboard = ui.tab("Dashboard", icon="insights").props("no-caps").classes("text-slate-700")
                for block in panel_structure:
                    panel_tab_map[block["id"]] = ui.tab(block["label"], icon=block["icon"]).props("no-caps").classes("text-slate-700")

            with ui.tab_panels(panel_tabs, value=tab_dashboard).classes("w-full bg-transparent"):
                with ui.tab_panel(tab_dashboard).classes("px-0"):
                    with ui.grid(columns=3).classes("w-full gap-3 mt-4"):
                        with ui.card().classes("ideas-panel"):
                            ui.label("Cobertura estructural").classes("ideas-section-title")
                            ui.label(f"{score}%").classes("text-3xl font-bold text-slate-900 mt-2")
                            ui.label(f"{total_bloques} bloques y {total_submodulos} submódulos definidos.").classes("text-sm text-slate-500 mt-1")
                        with ui.card().classes("ideas-panel"):
                            ui.label("Bloques principales").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "xAxis": {"type": "category", "data": [str(x.get("label") or "")[:18] for x in panel_structure]},
                                    "yAxis": {"type": "value"},
                                    "series": [{"type": "bar", "data": [len(x.get("items") or []) for x in panel_structure], "barWidth": "42%"}],
                                    "grid": {"left": 28, "right": 12, "top": 24, "bottom": 56},
                                }
                            ).classes("w-full h-64")
                        with ui.card().classes("ideas-panel"):
                            ui.label("Resumen panel").classes("ideas-section-title")
                            ui.echart(
                                {
                                    "tooltip": {"trigger": "item"},
                                    "series": [{"type": "pie", "radius": ["40%", "70%"], "data": [{"name": "Bloques", "value": total_bloques}, {"name": "Submódulos", "value": total_submodulos}]}],
                                }
                            ).classes("w-full h-64")

                    render_dashboard_customizer(
                        module_key="sst",
                        company_id=int(selected_company_id),
                        metric_catalog=[
                            ("procesos_sst_mapeados", "Procesos SST mapeados", len(sst_processes)),
                            ("bloques_panel_sst", "Bloques Panel SST", total_bloques),
                            ("submodulos_panel_sst", "Submodulos Panel SST", total_submodulos),
                            ("cobertura_estructura_sst", "Cobertura estructura SST", score),
                        ],
                    )

                for block in panel_structure:
                    with ui.tab_panel(panel_tab_map[block["id"]]).classes("px-0"):
                        with ui.card().classes("ideas-panel w-full mt-4"):
                            ui.label(str(block.get("label") or "")).classes("ideas-section-title")
                            ui.label("Submódulos del bloque seleccionado.").classes("ideas-section-note")

                            if str(block.get("id")) == "capacitaciones":
                                table_host = ui.column().classes("w-full gap-3 mt-3")
                                proceso_emisor_opts = {
                                    "Seguridad y Salud en el trabajo": "Seguridad y Salud en el trabajo",
                                    "Medio Ambiente": "Medio Ambiente",
                                    "Calidad": "Calidad",
                                    "Otro": "Otro",
                                }
                                modalidad_opts = {
                                    "Presencial": "Presencial",
                                    "Hibrida": "Hibrida",
                                    "Virtual Sincronica": "Virtual Sincronica",
                                    "Virtual Asincronica": "Virtual Asincronica",
                                }
                                responsable_opts = {"Interna": "Interna", "Externa": "Externa"}

                                def _payload(c: dict) -> dict:
                                    return {
                                        "tema": str(c["tema"].value or "").strip(),
                                        "proceso_emisor": str(c["proceso_emisor"].value or "").strip(),
                                        "proceso_receptor": str(c["proceso_receptor"].value or "").strip(),
                                        "personal_involucrado": int(c["personal_involucrado"].value or 0),
                                        "duracion_minutos": int(c["duracion_minutos"].value or 0),
                                        "fecha_maxima_ejecucion_planificada": str(c["fecha_plan"].value or "").strip(),
                                        "fecha_realizacion": str(c["fecha_real"].value or "").strip(),
                                        "estado": str(c["estado"].value or "").strip(),
                                        "porcentaje_personal_capacitado": float(c["porcentaje"].value or 0),
                                        "modalidad": str(c["modalidad"].value or "").strip(),
                                        "responsable_coordinacion": str(c["responsable_coord"].value or "").strip(),
                                        "entrenador": str(c["entrenador"].value or "").strip(),
                                        "requerimiento_legal": str(c["req_legal"].value or "").strip(),
                                        "detalle_requerimiento": str(c["detalle_req"].value or "").strip(),
                                    }

                                def _open_form(row: dict | None = None) -> None:
                                    emisor_val = str((row or {}).get("proceso_emisor") or "").strip()
                                    modalidad_val = str((row or {}).get("modalidad") or "").strip()
                                    responsable_val = str((row or {}).get("responsable_coordinacion") or "").strip()
                                    if emisor_val not in proceso_emisor_opts:
                                        emisor_val = None
                                    if modalidad_val not in modalidad_opts:
                                        modalidad_val = None
                                    if responsable_val not in responsable_opts:
                                        responsable_val = None
                                    with ui.dialog() as dlg, ui.card().classes("w-[980px] max-w-[96vw] ideas-panel p-4"):
                                        ui.label("Carga de capacitación SST").classes("text-lg font-semibold text-slate-900")
                                        with ui.grid(columns=4).classes("w-full gap-2 mt-2"):
                                            tema = ui.input("Tema", value=str((row or {}).get("tema") or "")).props("outlined")
                                            proceso_emisor = ui.select(proceso_emisor_opts, value=emisor_val, label="Proceso emisor").props("outlined")
                                            proceso_receptor = ui.input("Proceso receptor", value=str((row or {}).get("proceso_receptor") or "")).props("outlined")
                                            personal_involucrado = ui.number("Personal involucrado", value=int((row or {}).get("personal_involucrado") or 0)).props("outlined")
                                            duracion_minutos = ui.number("Duración (minutos)", value=int((row or {}).get("duracion_minutos") or 0)).props("outlined")
                                            fecha_plan = ui.input("Fecha máxima de ejecución planificada", value=str((row or {}).get("fecha_maxima_ejecucion_planificada") or ""), placeholder="YYYY-MM-DD").props("outlined")
                                            fecha_real = ui.input("Fecha de realización", value=str((row or {}).get("fecha_realizacion") or ""), placeholder="YYYY-MM-DD").props("outlined")
                                            estado = ui.input("Estado", value=str((row or {}).get("estado") or "")).props("outlined")
                                            porcentaje = ui.number("% Personal capacitado", value=float((row or {}).get("porcentaje_personal_capacitado") or 0)).props("outlined")
                                            modalidad = ui.select(modalidad_opts, value=modalidad_val, label="Modalidad").props("outlined")
                                            responsable_coord = ui.select(responsable_opts, value=responsable_val, label="Responsable coordinación").props("outlined")
                                            entrenador = ui.input("Entrenador", value=str((row or {}).get("entrenador") or "")).props("outlined")
                                            req_legal = ui.input("Requerimiento legal", value=str((row or {}).get("requerimiento_legal") or "")).props("outlined")
                                        detalle_req = ui.textarea("Detalle del requerimiento", value=str((row or {}).get("detalle_requerimiento") or "")).props("outlined autogrow").classes("w-full")

                                        controls = {
                                            "tema": tema,
                                            "proceso_emisor": proceso_emisor,
                                            "proceso_receptor": proceso_receptor,
                                            "personal_involucrado": personal_involucrado,
                                            "duracion_minutos": duracion_minutos,
                                            "fecha_plan": fecha_plan,
                                            "fecha_real": fecha_real,
                                            "estado": estado,
                                            "porcentaje": porcentaje,
                                            "modalidad": modalidad,
                                            "responsable_coord": responsable_coord,
                                            "entrenador": entrenador,
                                            "req_legal": req_legal,
                                            "detalle_req": detalle_req,
                                        }

                                        def _save() -> None:
                                            payload = _payload(controls)
                                            if row and row.get("id"):
                                                ok, msg = actualizar_sst_capacitacion(int(row["id"]), payload)
                                            else:
                                                ok, msg, _new_id = crear_sst_capacitacion(int(selected_company_id), payload)
                                            ui.notify(msg, type="positive" if ok else "warning")
                                            if ok:
                                                dlg.close()
                                                _refresh_table()

                                        with ui.row().classes("w-full justify-end gap-2 mt-2"):
                                            ui.button("Cancelar", on_click=dlg.close).props("flat")
                                            ui.button("Guardar", icon="save", on_click=_save).props("unelevated color=primary")
                                    dlg.open()

                                def _refresh_table() -> None:
                                    rows = obtener_sst_capacitaciones_empresa(int(selected_company_id)) or []
                                    table_host.clear()
                                    with table_host:
                                        with ui.row().classes("w-full justify-between items-center"):
                                            ui.label("Listado de capacitaciones").classes("text-sm font-semibold text-slate-800")
                                            ui.button("Nueva capacitación", icon="add", on_click=lambda: _open_form(None)).props("unelevated color=primary")

                                        table_rows = []
                                        for r in rows:
                                            table_rows.append(
                                                {
                                                    "id": int(r.get("id") or 0),
                                                    "tema": str(r.get("tema") or ""),
                                                    "proceso_emisor": str(r.get("proceso_emisor") or ""),
                                                    "proceso_receptor": str(r.get("proceso_receptor") or ""),
                                                    "personal_involucrado": int(r.get("personal_involucrado") or 0),
                                                    "duracion_minutos": int(r.get("duracion_minutos") or 0),
                                                    "fecha_plan": str(r.get("fecha_maxima_ejecucion_planificada") or ""),
                                                    "fecha_real": str(r.get("fecha_realizacion") or ""),
                                                    "estado": str(r.get("estado") or ""),
                                                    "porcentaje": float(r.get("porcentaje_personal_capacitado") or 0),
                                                    "modalidad": str(r.get("modalidad") or ""),
                                                    "responsable_coord": str(r.get("responsable_coordinacion") or ""),
                                                    "entrenador": str(r.get("entrenador") or ""),
                                                    "req_legal": str(r.get("requerimiento_legal") or ""),
                                                    "detalle_req": str(r.get("detalle_requerimiento") or ""),
                                                    "acciones": "",
                                                }
                                            )

                                        columns = [
                                            {"name": "tema", "label": "Tema", "field": "tema", "align": "left"},
                                            {"name": "proceso_emisor", "label": "Proceso emisor", "field": "proceso_emisor", "align": "left"},
                                            {"name": "proceso_receptor", "label": "Proceso receptor", "field": "proceso_receptor", "align": "left"},
                                            {"name": "personal_involucrado", "label": "Personal", "field": "personal_involucrado", "align": "left"},
                                            {"name": "duracion_minutos", "label": "Duración", "field": "duracion_minutos", "align": "left"},
                                            {"name": "fecha_plan", "label": "Fecha planificada", "field": "fecha_plan", "align": "left"},
                                            {"name": "fecha_real", "label": "Fecha realización", "field": "fecha_real", "align": "left"},
                                            {"name": "estado", "label": "Estado", "field": "estado", "align": "left"},
                                            {"name": "porcentaje", "label": "% Personal", "field": "porcentaje", "align": "left"},
                                            {"name": "modalidad", "label": "Modalidad", "field": "modalidad", "align": "left"},
                                            {"name": "responsable_coord", "label": "Resp. coordinación", "field": "responsable_coord", "align": "left"},
                                            {"name": "entrenador", "label": "Entrenador", "field": "entrenador", "align": "left"},
                                            {"name": "req_legal", "label": "Req. legal", "field": "req_legal", "align": "left"},
                                            {"name": "detalle_req", "label": "Detalle", "field": "detalle_req", "align": "left"},
                                            {"name": "acciones", "label": "Acciones", "field": "acciones", "align": "center"},
                                        ]
                                        table = ui.table(columns=columns, rows=table_rows, row_key="id", pagination=8).classes("w-full ideas-table")
                                        table.add_slot(
                                            "body-cell-acciones",
                                            """
                                            <q-td :props="props">
                                                <q-btn flat dense round icon="edit" color="primary" @click="$parent.$emit('edit_row', props.row.id)" />
                                                <q-btn flat dense round icon="delete" color="negative" @click="$parent.$emit('delete_row', props.row.id)" />
                                            </q-td>
                                            """,
                                        )

                                        def _on_edit(evt) -> None:
                                            rid = int(evt.args or 0)
                                            source = next((x for x in rows if int(x.get("id") or 0) == rid), None)
                                            if source:
                                                _open_form(source)

                                        def _on_delete(evt) -> None:
                                            rid = int(evt.args or 0)
                                            ok, msg = eliminar_sst_capacitacion(rid)
                                            ui.notify(msg, type="positive" if ok else "warning")
                                            if ok:
                                                _refresh_table()

                                        table.on("edit_row", _on_edit)
                                        table.on("delete_row", _on_delete)

                                _refresh_table()
                            else:
                                with ui.grid(columns=2).classes("w-full gap-3 mt-3"):
                                    items = block.get("items") or []
                                    if not items:
                                        with ui.card().classes("ideas-module-card"):
                                            ui.label("Sin submódulos en esta etapa").classes("font-semibold text-slate-700")
                                    for item in items:
                                        with ui.card().classes("ideas-module-card cursor-pointer").on("click", lambda _e, t=None: _open_submodule(t)):
                                            ui.label(str(item)).classes("font-semibold text-slate-900")
                                            ui.label("Abrir submódulo").classes("text-sm text-slate-500")
