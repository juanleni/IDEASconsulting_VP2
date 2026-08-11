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

    obtener_sst_incidentes_empresa = deps["obtener_sst_incidentes_empresa"]
    crear_sst_incidente = deps["crear_sst_incidente"]
    actualizar_sst_incidente = deps["actualizar_sst_incidente"]
    eliminar_sst_incidente = deps["eliminar_sst_incidente"]
    obtener_sst_peligros_empresa = deps["obtener_sst_peligros_empresa"]
    crear_sst_peligro = deps["crear_sst_peligro"]
    actualizar_sst_peligro = deps["actualizar_sst_peligro"]
    eliminar_sst_peligro = deps["eliminar_sst_peligro"]
    obtener_sst_epp_empresa = deps["obtener_sst_epp_empresa"]
    crear_sst_epp = deps["crear_sst_epp"]
    actualizar_sst_epp = deps["actualizar_sst_epp"]
    eliminar_sst_epp = deps["eliminar_sst_epp"]
    obtener_sst_epp_entregas_empresa = deps["obtener_sst_epp_entregas_empresa"]
    crear_sst_epp_entrega = deps["crear_sst_epp_entrega"]
    eliminar_sst_epp_entrega = deps["eliminar_sst_epp_entrega"]
    obtener_sst_plan_accion_empresa = deps["obtener_sst_plan_accion_empresa"]
    crear_sst_plan_accion = deps["crear_sst_plan_accion"]
    actualizar_sst_plan_accion = deps["actualizar_sst_plan_accion"]
    cerrar_sst_plan_accion = deps["cerrar_sst_plan_accion"]
    eliminar_sst_plan_accion = deps["eliminar_sst_plan_accion"]
    TIPOS_EVENTO_SST = deps["TIPOS_EVENTO_SST"]
    ESTADOS_EVENTO_SST = deps["ESTADOS_EVENTO_SST"]
    TIPOS_PELIGRO_SST = deps["TIPOS_PELIGRO_SST"]
    ESTADOS_PLAN_ACCION_SST = deps["ESTADOS_PLAN_ACCION_SST"]

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
                {"id": "matriz_peligros", "label": "Matriz de Peligros", "icon": "dangerous", "items": []},
                {"id": "cumplimiento_legal", "label": "Cumplimiento legal", "icon": "gavel", "items": ["Matriz legal", "Documentos - Certificaciones"]},
                {"id": "incidentes_accidentes", "label": "Incidentes / Accidentes", "icon": "report", "items": []},
                {"id": "salud_ocupacional", "label": "Salud Ocupacional", "icon": "health_and_safety", "items": ["Enfermedades profesionales", "Restricciones laborales"]},
                {"id": "prevencion", "label": "Prevención", "icon": "verified_user", "items": ["Trabajos de riesgo", "Controles y mediciones", "Ergonomía", "Prevención de emergencias"]},
                {"id": "equipos_qcos", "label": "Equipos/Productos químicos", "icon": "science", "items": ["Inventario", "Registros - Hojas de seguridad"]},
                {"id": "capacitaciones", "label": "Capacitaciones", "icon": "school", "items": ["Plan de capacitaciones anual", "Registros"]},
                {"id": "epp", "label": "EPP", "icon": "construction", "items": []},
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

                            elif str(block.get("id")) == "incidentes_accidentes":
                                _render_incidentes_block(
                                    ui, selected_company_id, fix_text,
                                    obtener_sst_incidentes_empresa, crear_sst_incidente, actualizar_sst_incidente, eliminar_sst_incidente,
                                    TIPOS_EVENTO_SST, ESTADOS_EVENTO_SST,
                                )

                            elif str(block.get("id")) == "matriz_peligros":
                                _render_peligros_block(
                                    ui, selected_company_id, fix_text,
                                    obtener_sst_peligros_empresa, crear_sst_peligro, actualizar_sst_peligro, eliminar_sst_peligro,
                                    TIPOS_PELIGRO_SST,
                                )

                            elif str(block.get("id")) == "epp":
                                _render_epp_block(
                                    ui, selected_company_id, fix_text,
                                    obtener_sst_epp_empresa, crear_sst_epp, actualizar_sst_epp, eliminar_sst_epp,
                                    obtener_sst_epp_entregas_empresa, crear_sst_epp_entrega, eliminar_sst_epp_entrega,
                                )

                            elif str(block.get("id")) == "plan_accion_sst":
                                _render_plan_accion_block(
                                    ui, selected_company_id, fix_text,
                                    obtener_sst_plan_accion_empresa, crear_sst_plan_accion, actualizar_sst_plan_accion,
                                    cerrar_sst_plan_accion, eliminar_sst_plan_accion, ESTADOS_PLAN_ACCION_SST,
                                )

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


# ---------------------------------------------------------------------------
# Fase 2 (2026-08-10): bloques SST completos (reemplazan los placeholders
# "Submódulo en preparación" de Incidentes/Accidentes, Matriz de Peligros,
# EPP y Plan de Acción SST).
# ---------------------------------------------------------------------------

_SST_ESTADO_COLOR = {
    "Abierto": "#B91C1C", "En investigación": "#B45309", "Cerrado": "#15803D",
    "Pendiente": "#B45309", "En curso": "#0369A1", "Cumplido": "#15803D", "Vencido": "#B91C1C",
}


def _render_incidentes_block(ui, empresa_id, fix_text, obtener_fn, crear_fn, actualizar_fn, eliminar_fn, tipos, estados) -> None:
    def _abrir_form(row: dict | None) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-2xl"):
            ui.label("Editar evento" if row else "Nuevo incidente / accidente").classes("text-base font-semibold")
            with ui.row().classes("w-full gap-2"):
                fecha = ui.input("Fecha", value=(row or {}).get("fecha", "")).classes("flex-1").props("outlined dense type=date")
                tipo = ui.select(tipos, label="Tipo de evento", value=(row or {}).get("tipo") or tipos[0]).classes("flex-1").props("outlined dense")
            lugar = ui.input("Lugar", value=(row or {}).get("lugar", "")).classes("w-full").props("outlined dense")
            descripcion = ui.textarea("Descripción de lo ocurrido", value=(row or {}).get("descripcion", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                personas = ui.input("Personas involucradas", value=(row or {}).get("personas_involucradas", "")).classes("flex-1").props("outlined dense")
                lesion = ui.input("Tipo de lesión (si hubo)", value=(row or {}).get("lesion_tipo", "")).classes("flex-1").props("outlined dense")
            dias_perdidos = ui.number("Días perdidos", value=int((row or {}).get("dias_perdidos") or 0)).classes("w-full").props("outlined dense")
            ui.label("Investigación de causa").classes("text-xs font-semibold text-slate-500 mt-1")
            causa_inmediata = ui.textarea("Causa inmediata", value=(row or {}).get("causa_inmediata", "")).classes("w-full").props("outlined dense")
            causa_raiz = ui.textarea("Causa raíz", value=(row or {}).get("causa_raiz", "")).classes("w-full").props("outlined dense")
            investigador = ui.input("Investigador", value=(row or {}).get("investigador", "")).classes("w-full").props("outlined dense")
            acciones = ui.textarea("Acciones correctivas", value=(row or {}).get("acciones_correctivas", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                estado = ui.select(estados, label="Estado", value=(row or {}).get("estado") or "Abierto").classes("flex-1").props("outlined dense")
                fecha_cierre = ui.input("Fecha de cierre", value=(row or {}).get("fecha_cierre", "")).classes("flex-1").props("outlined dense type=date")
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

                def _guardar() -> None:
                    payload = {
                        "fecha": fecha.value, "tipo": tipo.value, "lugar": lugar.value, "descripcion": descripcion.value,
                        "personas_involucradas": personas.value, "lesion_tipo": lesion.value, "dias_perdidos": dias_perdidos.value,
                        "causa_inmediata": causa_inmediata.value, "causa_raiz": causa_raiz.value, "investigador": investigador.value,
                        "acciones_correctivas": acciones.value, "estado": estado.value, "fecha_cierre": fecha_cierre.value,
                    }
                    if row:
                        ok, msg = actualizar_fn(int(row["id"]), payload, empresa_id=empresa_id)
                    else:
                        ok, msg, _new_id = crear_fn(empresa_id, payload)
                    ui.notify(msg, type="positive" if ok else "negative")
                    if ok:
                        dlg.close()
                        tabla.refresh()

                ui.button("Guardar", on_click=_guardar).props("unelevated no-caps color=primary")
        dlg.open()

    def _eliminar(row_id: int) -> None:
        ok, msg = eliminar_fn(row_id, empresa_id=empresa_id)
        ui.notify(msg, type="positive" if ok else "negative")
        tabla.refresh()

    with ui.row().classes("w-full justify-between items-center mt-3"):
        ui.label("Registro de incidentes y accidentes").classes("text-sm font-semibold text-slate-700")
        ui.button("Nuevo evento", icon="add", on_click=lambda: _abrir_form(None)).props("unelevated no-caps color=primary")

    @ui.refreshable
    def tabla() -> None:
        rows = obtener_fn(empresa_id)
        if not rows:
            with ui.card().classes("ideas-panel w-full p-6 items-center mt-2"):
                ui.icon("report", size="2rem").classes("text-gray-300")
                ui.label("Todavía no hay incidentes o accidentes registrados.").classes("text-sm text-gray-400")
            return
        for r in rows:
            color = _SST_ESTADO_COLOR.get(r.get("estado"), "#6B7480")
            with ui.card().classes("ideas-panel w-full p-3 mt-2"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0 flex-1"):
                        ui.label(f"{r.get('tipo')} · {r.get('fecha') or 'sin fecha'}").classes("text-sm font-semibold")
                        ui.label(fix_text(r.get("descripcion"))[:140]).classes("text-xs text-gray-500")
                    with ui.row().classes("items-center gap-2"):
                        ui.label(r.get("estado")).classes("text-xs font-semibold px-2 py-1 rounded-full").style(f"color:{color}; background:{color}22;")
                        ui.button(icon="edit", on_click=lambda row=r: _abrir_form(row)).props("flat round dense size=sm")
                        ui.button(icon="delete", on_click=lambda rid=r["id"]: _eliminar(rid)).props("flat round dense size=sm color=negative")

    tabla()


def _render_peligros_block(ui, empresa_id, fix_text, obtener_fn, crear_fn, actualizar_fn, eliminar_fn, tipos_peligro) -> None:
    def _abrir_form(row: dict | None) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-2xl"):
            ui.label("Editar peligro" if row else "Nuevo peligro identificado").classes("text-base font-semibold")
            with ui.row().classes("w-full gap-2"):
                proceso_area = ui.input("Proceso / Área", value=(row or {}).get("proceso_area", "")).classes("flex-1").props("outlined dense")
                tipo_peligro = ui.select(tipos_peligro, label="Tipo de peligro", value=(row or {}).get("tipo_peligro") or tipos_peligro[0]).classes("flex-1").props("outlined dense")
            peligro = ui.input("Peligro identificado", value=(row or {}).get("peligro", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                probabilidad = ui.select({1: "1 - Rara vez", 2: "2 - Poco probable", 3: "3 - Posible", 4: "4 - Probable", 5: "5 - Casi seguro"}, label="Probabilidad", value=int((row or {}).get("probabilidad") or 1)).classes("flex-1").props("outlined dense")
                severidad = ui.select({1: "1 - Insignificante", 2: "2 - Menor", 3: "3 - Moderada", 4: "4 - Mayor", 5: "5 - Catastrófica"}, label="Severidad", value=int((row or {}).get("severidad") or 1)).classes("flex-1").props("outlined dense")
            medidas = ui.textarea("Medidas de control", value=(row or {}).get("medidas_control", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                responsable = ui.input("Responsable", value=(row or {}).get("responsable", "")).classes("flex-1").props("outlined dense")
                fecha_revision = ui.input("Próxima revisión", value=(row or {}).get("fecha_revision", "")).classes("flex-1").props("outlined dense type=date")
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

                def _guardar() -> None:
                    payload = {
                        "proceso_area": proceso_area.value, "peligro": peligro.value, "tipo_peligro": tipo_peligro.value,
                        "probabilidad": probabilidad.value, "severidad": severidad.value, "medidas_control": medidas.value,
                        "responsable": responsable.value, "fecha_revision": fecha_revision.value,
                    }
                    if row:
                        ok, msg = actualizar_fn(int(row["id"]), payload, empresa_id=empresa_id)
                    else:
                        ok, msg, _new_id = crear_fn(empresa_id, payload)
                    ui.notify(msg, type="positive" if ok else "negative")
                    if ok:
                        dlg.close()
                        tabla.refresh()

                ui.button("Guardar", on_click=_guardar).props("unelevated no-caps color=primary")
        dlg.open()

    def _eliminar(row_id: int) -> None:
        ok, msg = eliminar_fn(row_id, empresa_id=empresa_id)
        ui.notify(msg, type="positive" if ok else "negative")
        tabla.refresh()

    def _nivel_color(nivel: int) -> str:
        if nivel >= 15:
            return "#B91C1C"
        if nivel >= 8:
            return "#B45309"
        return "#15803D"

    with ui.row().classes("w-full justify-between items-center mt-3"):
        ui.label("Matriz de peligros (probabilidad × severidad)").classes("text-sm font-semibold text-slate-700")
        ui.button("Nuevo peligro", icon="add", on_click=lambda: _abrir_form(None)).props("unelevated no-caps color=primary")

    @ui.refreshable
    def tabla() -> None:
        rows = obtener_fn(empresa_id)
        if not rows:
            with ui.card().classes("ideas-panel w-full p-6 items-center mt-2"):
                ui.icon("dangerous", size="2rem").classes("text-gray-300")
                ui.label("Todavía no hay peligros identificados para esta empresa.").classes("text-sm text-gray-400")
            return
        for r in rows:
            color = _nivel_color(int(r.get("nivel_riesgo") or 1))
            with ui.card().classes("ideas-panel w-full p-3 mt-2"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0 flex-1"):
                        ui.label(f"{fix_text(r.get('peligro'))} · {r.get('tipo_peligro')}").classes("text-sm font-semibold")
                        ui.label(f"{fix_text(r.get('proceso_area')) or 'Sin área'} · P{r.get('probabilidad')} × S{r.get('severidad')}").classes("text-xs text-gray-500")
                    with ui.row().classes("items-center gap-2"):
                        ui.label(f"Nivel {r.get('nivel_riesgo')}").classes("text-xs font-semibold px-2 py-1 rounded-full").style(f"color:{color}; background:{color}22;")
                        ui.button(icon="edit", on_click=lambda row=r: _abrir_form(row)).props("flat round dense size=sm")
                        ui.button(icon="delete", on_click=lambda rid=r["id"]: _eliminar(rid)).props("flat round dense size=sm color=negative")

    tabla()


def _render_epp_block(ui, empresa_id, fix_text, obtener_epp_fn, crear_epp_fn, actualizar_epp_fn, eliminar_epp_fn,
                       obtener_entregas_fn, crear_entrega_fn, eliminar_entrega_fn) -> None:
    def _abrir_form_epp(row: dict | None) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-lg"):
            ui.label("Editar EPP" if row else "Nuevo EPP en catálogo").classes("text-base font-semibold")
            nombre = ui.input("Nombre del EPP", value=(row or {}).get("nombre", "")).classes("w-full").props("outlined dense")
            puesto = ui.input("Puesto / tarea aplicable", value=(row or {}).get("puesto_aplicable", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                norma = ui.input("Norma de certificación", value=(row or {}).get("norma_certificacion", "")).classes("flex-1").props("outlined dense")
                vencimiento = ui.input("Vencimiento certificación", value=(row or {}).get("fecha_vencimiento_certificacion", "")).classes("flex-1").props("outlined dense type=date")
            with ui.row().classes("w-full gap-2"):
                stock = ui.number("Stock disponible", value=int((row or {}).get("stock") or 0)).classes("flex-1").props("outlined dense")
                proveedor = ui.input("Proveedor", value=(row or {}).get("proveedor", "")).classes("flex-1").props("outlined dense")
            notas = ui.textarea("Notas", value=(row or {}).get("notas", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

                def _guardar() -> None:
                    payload = {
                        "nombre": nombre.value, "puesto_aplicable": puesto.value, "norma_certificacion": norma.value,
                        "fecha_vencimiento_certificacion": vencimiento.value, "stock": stock.value,
                        "proveedor": proveedor.value, "notas": notas.value,
                    }
                    if row:
                        ok, msg = actualizar_epp_fn(int(row["id"]), payload, empresa_id=empresa_id)
                    else:
                        ok, msg, _new_id = crear_epp_fn(empresa_id, payload)
                    ui.notify(msg, type="positive" if ok else "negative")
                    if ok:
                        dlg.close()
                        tabla_epp.refresh()
                        epp_options_cache.clear()
                        epp_options_cache.update(_epp_options())

                ui.button("Guardar", on_click=_guardar).props("unelevated no-caps color=primary")
        dlg.open()

    def _eliminar_epp(row_id: int) -> None:
        ok, msg = eliminar_epp_fn(row_id, empresa_id=empresa_id)
        ui.notify(msg, type="positive" if ok else "negative")
        tabla_epp.refresh()
        epp_options_cache.clear()
        epp_options_cache.update(_epp_options())

    def _epp_options() -> dict:
        return {int(e["id"]): fix_text(e.get("nombre")) for e in obtener_epp_fn(empresa_id)}

    epp_options_cache: dict = _epp_options()

    ui.label("Catálogo de EPP").classes("text-sm font-semibold text-slate-700 mt-3")
    with ui.row().classes("w-full justify-end"):
        ui.button("Nuevo EPP", icon="add", on_click=lambda: _abrir_form_epp(None)).props("unelevated no-caps color=primary")

    @ui.refreshable
    def tabla_epp() -> None:
        rows = obtener_epp_fn(empresa_id)
        if not rows:
            with ui.card().classes("ideas-panel w-full p-6 items-center mt-2"):
                ui.icon("construction", size="2rem").classes("text-gray-300")
                ui.label("Todavía no hay EPP cargados en el catálogo.").classes("text-sm text-gray-400")
            return
        for r in rows:
            with ui.card().classes("ideas-panel w-full p-3 mt-2"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0 flex-1"):
                        ui.label(fix_text(r.get("nombre"))).classes("text-sm font-semibold")
                        ui.label(f"{fix_text(r.get('puesto_aplicable')) or 'Sin puesto asignado'} · Stock: {r.get('stock')} · Cert: {fix_text(r.get('norma_certificacion')) or '—'}").classes("text-xs text-gray-500")
                    with ui.row().classes("gap-2"):
                        ui.button(icon="edit", on_click=lambda row=r: _abrir_form_epp(row)).props("flat round dense size=sm")
                        ui.button(icon="delete", on_click=lambda rid=r["id"]: _eliminar_epp(rid)).props("flat round dense size=sm color=negative")

    tabla_epp()

    ui.separator().classes("my-3")
    ui.label("Entregas de EPP (equivalente a Formulario 299)").classes("text-sm font-semibold text-slate-700")

    def _abrir_form_entrega() -> None:
        opciones = _epp_options()
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-md"):
            ui.label("Nueva entrega de EPP").classes("text-base font-semibold")
            epp_select = ui.select(opciones, label="EPP entregado").classes("w-full").props("outlined dense")
            empleado = ui.input("Empleado que recibe").classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                fecha_entrega = ui.input("Fecha de entrega").classes("flex-1").props("outlined dense type=date")
                cantidad = ui.number("Cantidad", value=1).classes("flex-1").props("outlined dense")
            firma = ui.input("Firma / confirmación de recibido").classes("w-full").props("outlined dense")
            observaciones = ui.textarea("Observaciones").classes("w-full").props("outlined dense")
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

                def _guardar() -> None:
                    payload = {
                        "epp_id": epp_select.value, "empleado": empleado.value, "fecha_entrega": fecha_entrega.value,
                        "cantidad": cantidad.value, "firma_recibido": firma.value, "observaciones": observaciones.value,
                    }
                    ok, msg, _new_id = crear_entrega_fn(empresa_id, payload)
                    ui.notify(msg, type="positive" if ok else "negative")
                    if ok:
                        dlg.close()
                        tabla_entregas.refresh()

                ui.button("Registrar entrega", on_click=_guardar).props("unelevated no-caps color=primary")
        dlg.open()

    def _eliminar_entrega(row_id: int) -> None:
        ok, msg = eliminar_entrega_fn(row_id, empresa_id=empresa_id)
        ui.notify(msg, type="positive" if ok else "negative")
        tabla_entregas.refresh()

    with ui.row().classes("w-full justify-end"):
        ui.button("Nueva entrega", icon="add", on_click=_abrir_form_entrega).props("flat no-caps color=primary")

    @ui.refreshable
    def tabla_entregas() -> None:
        rows = obtener_entregas_fn(empresa_id)
        if not rows:
            ui.label("Sin entregas registradas todavía.").classes("text-xs text-gray-400 py-2")
            return
        for r in rows:
            with ui.row().classes("w-full items-center gap-2 py-1").style("border-bottom:1px solid #F1F5F9;"):
                ui.label(fix_text(r.get("empleado"))).classes("text-xs font-semibold w-40")
                ui.label(fix_text(r.get("epp_nombre")) or "—").classes("text-xs flex-1")
                ui.label(str(r.get("cantidad"))).classes("text-xs w-10")
                ui.label(r.get("fecha_entrega") or "—").classes("text-xs w-28 text-gray-400")
                ui.button(icon="delete", on_click=lambda rid=r["id"]: _eliminar_entrega(rid)).props("flat round dense size=sm color=negative")

    tabla_entregas()


def _render_plan_accion_block(ui, empresa_id, fix_text, obtener_fn, crear_fn, actualizar_fn, cerrar_fn, eliminar_fn, estados) -> None:
    def _abrir_form(row: dict | None) -> None:
        with ui.dialog() as dlg, ui.card().classes("w-full max-w-lg"):
            ui.label("Editar acción" if row else "Nueva acción SST").classes("text-base font-semibold")
            origen = ui.select(
                ["Incidente/Accidente", "Matriz de peligros", "Auditoría interna", "Inspección", "Otro"],
                label="Origen", value=(row or {}).get("origen") or "Otro",
            ).classes("w-full").props("outlined dense")
            descripcion = ui.textarea("Descripción de la acción", value=(row or {}).get("descripcion", "")).classes("w-full").props("outlined dense")
            with ui.row().classes("w-full gap-2"):
                responsable = ui.input("Responsable", value=(row or {}).get("responsable", "")).classes("flex-1").props("outlined dense")
                fecha_limite = ui.input("Fecha límite", value=(row or {}).get("fecha_limite", "")).classes("flex-1").props("outlined dense type=date")
            estado = ui.select(estados, label="Estado", value=(row or {}).get("estado") or "Pendiente").classes("w-full").props("outlined dense")
            with ui.row().classes("w-full justify-end gap-2 mt-2"):
                ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")

                def _guardar() -> None:
                    payload = {
                        "origen": origen.value, "descripcion": descripcion.value, "responsable": responsable.value,
                        "fecha_limite": fecha_limite.value, "estado": estado.value,
                    }
                    if row:
                        ok, msg = actualizar_fn(int(row["id"]), payload, empresa_id=empresa_id)
                    else:
                        ok, msg, _new_id = crear_fn(empresa_id, payload)
                    ui.notify(msg, type="positive" if ok else "negative")
                    if ok:
                        dlg.close()
                        tabla.refresh()

                ui.button("Guardar", on_click=_guardar).props("unelevated no-caps color=primary")
        dlg.open()

    def _cerrar(row_id: int) -> None:
        with ui.dialog() as ev_dialog, ui.card().classes("w-full max-w-sm"):
            ui.label("Cerrar acción").classes("text-base font-semibold")
            evidencia = ui.textarea("Evidencia de cumplimiento").classes("w-full").props("outlined dense")
            with ui.row().classes("w-full justify-end gap-2"):
                ui.button("Cancelar", on_click=ev_dialog.close).props("flat no-caps")

                def _confirmar() -> None:
                    ok, msg = cerrar_fn(row_id, evidencia.value, empresa_id=empresa_id)
                    ui.notify(msg, type="positive" if ok else "negative")
                    ev_dialog.close()
                    tabla.refresh()

                ui.button("Confirmar cierre", on_click=_confirmar).props("unelevated no-caps color=positive")
        ev_dialog.open()

    def _eliminar(row_id: int) -> None:
        ok, msg = eliminar_fn(row_id, empresa_id=empresa_id)
        ui.notify(msg, type="positive" if ok else "negative")
        tabla.refresh()

    with ui.row().classes("w-full justify-between items-center mt-3"):
        ui.label("Plan de acción de gestión SST").classes("text-sm font-semibold text-slate-700")
        ui.button("Nueva acción", icon="add", on_click=lambda: _abrir_form(None)).props("unelevated no-caps color=primary")

    @ui.refreshable
    def tabla() -> None:
        rows = obtener_fn(empresa_id)
        if not rows:
            with ui.card().classes("ideas-panel w-full p-6 items-center mt-2"):
                ui.icon("task_alt", size="2rem").classes("text-gray-300")
                ui.label("Todavía no hay acciones cargadas en el plan SST.").classes("text-sm text-gray-400")
            return
        for r in rows:
            color = _SST_ESTADO_COLOR.get(r.get("estado"), "#6B7480")
            with ui.card().classes("ideas-panel w-full p-3 mt-2"):
                with ui.row().classes("w-full justify-between items-center"):
                    with ui.column().classes("gap-0 flex-1"):
                        ui.label(fix_text(r.get("descripcion"))[:140]).classes("text-sm font-semibold")
                        ui.label(f"{r.get('origen')} · Resp: {fix_text(r.get('responsable')) or '—'} · Límite: {r.get('fecha_limite') or '—'}").classes("text-xs text-gray-500")
                    with ui.row().classes("items-center gap-2"):
                        ui.label(r.get("estado")).classes("text-xs font-semibold px-2 py-1 rounded-full").style(f"color:{color}; background:{color}22;")
                        ui.button(icon="edit", on_click=lambda row=r: _abrir_form(row)).props("flat round dense size=sm")
                        if r.get("estado") != "Cumplido":
                            ui.button(icon="task_alt", on_click=lambda rid=r["id"]: _cerrar(rid)).props("flat round dense size=sm color=positive")
                        ui.button(icon="delete", on_click=lambda rid=r["id"]: _eliminar(rid)).props("flat round dense size=sm color=negative")

    tabla()
