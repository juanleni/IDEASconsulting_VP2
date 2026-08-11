"""Revisión por la Dirección — acta liviana (Fase 2, 2026-08-10).

Cierra la cláusula 9.3 de ISO 9001/14001/45001: entradas obligatorias
(9.3.2) precargadas desde un snapshot de Auditorías, Calidad/8D, Riesgos,
KPIs y Matriz Legal Ambiental, y salidas/decisiones (9.3.3) editables.
"""
from __future__ import annotations

from nicegui import app, ui
from company_context import empresa_id_from_query_for_admin, with_empresa_id


def go_to_management_review_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/revision-direccion', company_id))


_ESTADO_COLOR = {'Borrador': '#B45309', 'Cerrada': '#15803D'}

_ENTRADAS_FIELDS = [
    ('estado_acciones_previas', 'Estado de las acciones de revisiones anteriores'),
    ('cambios_contexto', 'Cambios en cuestiones externas e internas pertinentes'),
    ('resultados_auditorias', 'Resultados de auditorías internas'),
    ('no_conformidades_acciones_correctivas', 'No conformidades y acciones correctivas (8D)'),
    ('resultados_seguimiento_kpis', 'Resultados de seguimiento y medición (KPIs)'),
    ('cumplimiento_legal', 'Cumplimiento de requisitos legales y otros'),
    ('riesgos_oportunidades', 'Riesgos y oportunidades identificados'),
    ('adecuacion_recursos', 'Adecuación de los recursos'),
    ('retroalimentacion_partes_interesadas', 'Retroalimentación de las partes interesadas'),
]

_SALIDAS_FIELDS = [
    ('decisiones_mejora', 'Decisiones sobre oportunidades de mejora'),
    ('decisiones_recursos', 'Decisiones sobre necesidades de recursos'),
    ('decisiones_cambios_sgi', 'Decisiones sobre cambios en el sistema de gestión'),
    ('objetivos_nuevos', 'Objetivos nuevos o revisados'),
]


def register_management_review_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    fix_text = deps.get('fix_text', lambda v: '' if v is None else str(v))

    obtener_revisiones_empresa = deps['obtener_revisiones_empresa']
    obtener_revision_detalle = deps['obtener_revision_detalle']
    crear_revision_direccion = deps['crear_revision_direccion']
    actualizar_revision_direccion = deps['actualizar_revision_direccion']
    eliminar_revision_direccion = deps['eliminar_revision_direccion']
    obtener_snapshot_revision_direccion = deps['obtener_snapshot_revision_direccion']
    ESTADOS_REVISION_DIRECCION = deps['ESTADOS_REVISION_DIRECCION']

    @ui.page('/sistema-gestion/revision-direccion')
    def management_review_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Revisión por la Dirección', back_route='/sistema-gestion', module_key='management_review')
        company_map = company_options()
        query_empresa_id = empresa_id_from_query_for_admin()
        selected_company_id = query_empresa_id or app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        if query_empresa_id and selected_company_id:
            app.storage.user['management_company_id'] = selected_company_id
            set_selection(selected_company_id, None)
        if not selected_company_id and company_map:
            selected_company_id = next(iter(company_map.keys()))
            app.storage.user['management_company_id'] = selected_company_id
            set_selection(selected_company_id, None)

        with shell_container:
            if not selected_company_id:
                ui.label('No hay empresa seleccionada.').classes('ideas-section-title')
                return

            ui.label('Actas de revisión por la dirección').classes('ideas-kicker')
            ui.label(
                'Cada acta junta lo que pide la cláusula 9.3: estado de auditorías, no conformidades, '
                'KPIs, riesgos y cumplimiento legal como entradas — y decisiones y objetivos como salida.'
            ).classes('ideas-section-note mb-3')

            def _snapshot_summary_text() -> str:
                snap = obtener_snapshot_revision_direccion(selected_company_id)
                return (
                    f"Auditorías internas: {snap.get('auditorias_total', 0)} "
                    f"(hallazgos abiertos: {snap.get('hallazgos_abiertos', 0)}) · "
                    f"8D: {snap.get('ocho_d_total', 0)} (abiertos: {snap.get('ocho_d_abiertos', 0)}) · "
                    f"Matrices de riesgo: {snap.get('matrices_riesgos', 0)} · "
                    f"KPIs cargados: {snap.get('kpis_total', 0)} · "
                    f"Requisitos legales ambientales pendientes: {snap.get('legal_ambiental_pendiente', 0)}"
                )

            with ui.card().classes('w-full p-4 mb-3').style('box-shadow:none;border:1px solid #E5E7EB;background:#F8FAFC;'):
                with ui.row().classes('w-full items-center gap-2'):
                    ui.icon('insights', size='1.2rem').classes('text-slate-500')
                    ui.label('Snapshot actual (se recalcula al abrir esta página)').classes('text-sm font-semibold text-slate-700')
                ui.label(_snapshot_summary_text()).classes('text-xs text-slate-500 mt-1')

            def _abrir_form_revision(revision_id: int | None) -> None:
                existente = obtener_revision_detalle(revision_id) if revision_id else None
                snap = obtener_snapshot_revision_direccion(selected_company_id)
                sugerencias = {
                    'resultados_auditorias': (
                        f"{snap.get('auditorias_total', 0)} auditorías registradas, "
                        f"{snap.get('hallazgos_abiertos', 0)} hallazgo(s) abierto(s)."
                    ),
                    'no_conformidades_acciones_correctivas': (
                        f"{snap.get('ocho_d_total', 0)} casos 8D registrados, "
                        f"{snap.get('ocho_d_abiertos', 0)} abierto(s)."
                    ),
                    'resultados_seguimiento_kpis': f"{snap.get('kpis_total', 0)} KPI(s) cargados en el sistema.",
                    'riesgos_oportunidades': f"{snap.get('matrices_riesgos', 0)} matriz(ces) de riesgo por proceso.",
                    'cumplimiento_legal': f"{snap.get('legal_ambiental_pendiente', 0)} requisito(s) legal-ambiental pendiente(s) de cumplimiento.",
                }

                with ui.dialog() as r_dialog, ui.card().classes('w-full max-w-3xl').style('max-height:90vh;'):
                    with ui.scroll_area().classes('w-full').style('max-height:82vh;'):
                        ui.label('Editar acta' if existente else 'Nueva acta de revisión').classes('text-lg font-semibold')
                        with ui.row().classes('w-full gap-2'):
                            fecha = ui.input('Fecha de la reunión', value=(existente or {}).get('fecha', '')).classes('flex-1').props('outlined dense type=date')
                            periodo = ui.input('Período analizado (ej: Q3 2026)', value=(existente or {}).get('periodo_analizado', '')).classes('flex-1').props('outlined dense')
                        participantes = ui.input('Participantes', value=(existente or {}).get('participantes', '')).classes('w-full').props('outlined dense')

                        ui.separator().classes('my-2')
                        ui.label('Entradas (cláusula 9.3.2)').classes('text-sm font-semibold text-slate-700')
                        entrada_inputs = {}
                        for field, label in _ENTRADAS_FIELDS:
                            value = (existente or {}).get(field, '') or sugerencias.get(field, '')
                            entrada_inputs[field] = ui.textarea(label, value=value).classes('w-full').props('outlined dense')

                        ui.separator().classes('my-2')
                        ui.label('Salidas y decisiones (cláusula 9.3.3)').classes('text-sm font-semibold text-slate-700')
                        salida_inputs = {}
                        for field, label in _SALIDAS_FIELDS:
                            salida_inputs[field] = ui.textarea(label, value=(existente or {}).get(field, '')).classes('w-full').props('outlined dense')

                        conclusion = ui.textarea('Conclusión general', value=(existente or {}).get('conclusion_general', '')).classes('w-full').props('outlined dense')
                        estado_sel = ui.select(ESTADOS_REVISION_DIRECCION, label='Estado', value=(existente or {}).get('estado', 'Borrador')).classes('w-full').props('outlined dense')

                        with ui.row().classes('w-full justify-end gap-2 mt-3'):
                            ui.button('Cancelar', on_click=r_dialog.close).props('flat no-caps')

                            def _guardar() -> None:
                                payload = {
                                    'fecha': fecha.value, 'periodo_analizado': periodo.value,
                                    'participantes': participantes.value,
                                    'conclusion_general': conclusion.value, 'estado': estado_sel.value,
                                }
                                for field, _label in _ENTRADAS_FIELDS:
                                    payload[field] = entrada_inputs[field].value
                                for field, _label in _SALIDAS_FIELDS:
                                    payload[field] = salida_inputs[field].value
                                if existente:
                                    ok, msg = actualizar_revision_direccion(revision_id, payload, empresa_id=selected_company_id)
                                else:
                                    ok, msg, _new_id = crear_revision_direccion(selected_company_id, payload)
                                ui.notify(msg, type='positive' if ok else 'negative')
                                if ok:
                                    r_dialog.close()
                                    tabla_revisiones.refresh()

                            ui.button('Guardar acta', on_click=_guardar).props('unelevated no-caps color=primary')
                r_dialog.open()

            def _ver_revision(revision_id: int) -> None:
                existente = obtener_revision_detalle(revision_id)
                if not existente:
                    ui.notify('El acta ya no existe.', type='warning')
                    tabla_revisiones.refresh()
                    return
                with ui.dialog() as v_dialog, ui.card().classes('w-full max-w-3xl').style('max-height:90vh;'):
                    with ui.scroll_area().classes('w-full').style('max-height:82vh;'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('gap-0'):
                                ui.label(f"Acta — {fix_text(existente.get('periodo_analizado'))}").classes('text-lg font-semibold')
                                ui.label(f"Fecha: {existente.get('fecha') or '—'} · Participantes: {fix_text(existente.get('participantes')) or '—'}").classes('text-xs text-gray-500')
                            color = _ESTADO_COLOR.get(existente.get('estado'), '#6B7480')
                            ui.label(existente.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(f'color:{color}; background:{color}22;')
                        ui.separator().classes('my-2')
                        ui.label('Entradas').classes('text-sm font-semibold text-slate-700')
                        for field, label in _ENTRADAS_FIELDS:
                            val = fix_text(existente.get(field))
                            if val:
                                ui.label(label).classes('text-xs font-semibold text-slate-500 mt-2')
                                ui.label(val).classes('text-sm')
                        ui.separator().classes('my-2')
                        ui.label('Salidas y decisiones').classes('text-sm font-semibold text-slate-700')
                        for field, label in _SALIDAS_FIELDS:
                            val = fix_text(existente.get(field))
                            if val:
                                ui.label(label).classes('text-xs font-semibold text-slate-500 mt-2')
                                ui.label(val).classes('text-sm')
                        if existente.get('conclusion_general'):
                            ui.separator().classes('my-2')
                            ui.label('Conclusión general').classes('text-xs font-semibold text-slate-500')
                            ui.label(fix_text(existente.get('conclusion_general'))).classes('text-sm')
                        with ui.row().classes('w-full justify-end gap-2 mt-3'):
                            ui.button('Cerrar', on_click=v_dialog.close).props('flat no-caps')
                            ui.button('Editar', icon='edit', on_click=lambda: (v_dialog.close(), _abrir_form_revision(revision_id))).props('unelevated no-caps color=primary')
                v_dialog.open()

            def _eliminar_revision(revision_id: int) -> None:
                ok, msg = eliminar_revision_direccion(revision_id, empresa_id=selected_company_id)
                ui.notify(msg, type='positive' if ok else 'negative')
                tabla_revisiones.refresh()

            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Actas registradas').classes('text-sm font-semibold text-gray-600')
                ui.button('Nueva acta', icon='add', on_click=lambda: _abrir_form_revision(None)).props('unelevated no-caps color=primary')

            @ui.refreshable
            def tabla_revisiones() -> None:
                revisiones = obtener_revisiones_empresa(selected_company_id)
                if not revisiones:
                    with ui.card().classes('w-full p-6 items-center').style('box-shadow:none;border:1px dashed #CBD5E1;'):
                        ui.icon('reviews', size='2rem').classes('text-gray-300')
                        ui.label('Todavía no hay actas de revisión por la dirección para esta empresa.').classes('text-sm text-gray-400')
                    return
                for r in revisiones:
                    color = _ESTADO_COLOR.get(r.get('estado'), '#6B7480')
                    with ui.card().classes('w-full p-3 mb-2').style('box-shadow:none;border:1px solid #E5E7EB;'):
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('gap-0 flex-1 cursor-pointer').on('click', lambda rid=r['id']: _ver_revision(rid)):
                                ui.label(fix_text(r.get('periodo_analizado'))).classes('text-sm font-semibold')
                                ui.label(f"Fecha: {r.get('fecha') or '—'} · {fix_text(r.get('participantes')) or 'Sin participantes registrados'}").classes('text-xs text-gray-500')
                            with ui.row().classes('items-center gap-2'):
                                ui.label(r.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(f'color:{color}; background:{color}22;')
                                ui.button(icon='visibility', on_click=lambda rid=r['id']: _ver_revision(rid)).props('flat round dense size=sm')
                                ui.button(icon='delete', on_click=lambda rid=r['id']: _eliminar_revision(rid)).props('flat round dense size=sm color=negative')

            tabla_revisiones()
