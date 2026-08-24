"""Auditorías Internas — módulo transversal (Fase 2, 2026-08-10).

Generaliza a Calidad/Ambiente/SST/Integrado el mismo patrón que ya existía,
aislado, en Laboratorio (lab_auditorias): programa de auditorías, hallazgos
clasificados (NC mayor/menor, observación, oportunidad de mejora), plan de
acción y cierre con evidencia. Cierra el gap crítico de la cláusula 9.2 de
ISO 9001/14001/45001 (auditoría interna) para el resto de los módulos.
"""
from __future__ import annotations

from nicegui import app, ui
from company_context import empresa_id_from_query_for_admin, with_empresa_id


def go_to_audits_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/auditorias-internas', company_id))


_CLASIF_COLOR = {
    'No conformidad mayor': '#B91C1C',
    'No conformidad menor': '#B45309',
    'Observación': '#0369A1',
    'Oportunidad de mejora': '#15803D',
}
_ESTADO_AUD_COLOR = {'Programada': '#0369A1', 'En curso': '#B45309', 'Cerrada': '#15803D'}
_ESTADO_HALLAZGO_COLOR = {'Abierto': '#B91C1C', 'En tratamiento': '#B45309', 'Cerrado': '#15803D'}


def register_audits_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    fix_text = deps.get('fix_text', lambda v: '' if v is None else str(v))

    obtener_auditorias_empresa = deps['obtener_auditorias_empresa']
    obtener_auditoria_detalle = deps['obtener_auditoria_detalle']
    crear_auditoria_interna = deps['crear_auditoria_interna']
    actualizar_auditoria_interna = deps['actualizar_auditoria_interna']
    eliminar_auditoria_interna = deps['eliminar_auditoria_interna']
    obtener_hallazgos_auditoria = deps['obtener_hallazgos_auditoria']
    crear_hallazgo_auditoria = deps['crear_hallazgo_auditoria']
    actualizar_hallazgo_auditoria = deps['actualizar_hallazgo_auditoria']
    cerrar_hallazgo_auditoria = deps['cerrar_hallazgo_auditoria']
    eliminar_hallazgo_auditoria = deps['eliminar_hallazgo_auditoria']
    AREAS_AUDITORIA = deps['AREAS_AUDITORIA']
    NORMAS_AUDITORIA = deps['NORMAS_AUDITORIA']
    ESTADOS_AUDITORIA = deps['ESTADOS_AUDITORIA']
    CLASIFICACIONES_HALLAZGO = deps['CLASIFICACIONES_HALLAZGO']
    ESTADOS_HALLAZGO = deps['ESTADOS_HALLAZGO']

    @ui.page('/sistema-gestion/auditorias-internas')
    def audits_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Auditorías Internas', back_route='/sistema-gestion', module_key='audits')
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

            ui.label('Programa de auditorías internas').classes('ideas-kicker')
            ui.label(
                'Programá auditorías por área y norma, registrá hallazgos clasificados y hacé '
                'seguimiento del plan de acción hasta el cierre — la evidencia que pide la cláusula 9.2.'
            ).classes('ideas-section-note mb-3')

            # ---- detalle de una auditoria (con sus hallazgos) --------------
            def _abrir_detalle(auditoria_id: int) -> None:
                auditoria = obtener_auditoria_detalle(auditoria_id)
                if not auditoria:
                    ui.notify('La auditoría ya no existe.', type='warning')
                    tabla_auditorias.refresh()
                    return

                with ui.dialog() as detail_dialog, ui.card().classes('w-full max-w-3xl'):
                    with ui.row().classes('w-full justify-between items-start'):
                        with ui.column().classes('gap-0'):
                            ui.label(fix_text(auditoria.get('titulo'))).classes('text-lg font-semibold')
                            ui.label(f"{auditoria.get('area')} · {auditoria.get('norma')}").classes('text-xs text-gray-500')
                        color = _ESTADO_AUD_COLOR.get(auditoria.get('estado'), '#6B7480')
                        ui.label(auditoria.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(
                            f'color:{color}; background:{color}22;'
                        )
                    ui.separator()

                    with ui.row().classes('w-full gap-4 flex-wrap'):
                        ui.label(f"Auditor: {fix_text(auditoria.get('auditor')) or '—'}").classes('text-sm')
                        ui.label(f"Programada: {auditoria.get('fecha_programada') or '—'}").classes('text-sm')
                        ui.label(f"Realizada: {auditoria.get('fecha_realizada') or '—'}").classes('text-sm')
                    if auditoria.get('alcance'):
                        ui.label(f"Alcance: {fix_text(auditoria.get('alcance'))}").classes('text-sm text-gray-700')
                    if auditoria.get('conclusion'):
                        ui.label(f"Conclusión: {fix_text(auditoria.get('conclusion'))}").classes('text-sm text-gray-700')

                    ui.separator()
                    with ui.row().classes('w-full justify-between items-center'):
                        ui.label('Hallazgos').classes('text-sm font-semibold')
                        ui.button('Agregar hallazgo', icon='add', on_click=lambda: _abrir_form_hallazgo(auditoria_id, None)).props(
                            'flat no-caps color=primary dense'
                        )

                    @ui.refreshable
                    def tabla_hallazgos() -> None:
                        hallazgos = obtener_hallazgos_auditoria(auditoria_id)
                        if not hallazgos:
                            ui.label('Sin hallazgos registrados todavía.').classes('text-sm text-gray-400 py-2')
                            return
                        for h in hallazgos:
                            with ui.card().classes('w-full p-3 mb-1').style('box-shadow:none;border:1px solid #E5E7EB;'):
                                with ui.row().classes('w-full justify-between items-start'):
                                    with ui.column().classes('gap-0 flex-1'):
                                        clasif_color = _CLASIF_COLOR.get(h.get('clasificacion'), '#6B7480')
                                        with ui.row().classes('items-center gap-2'):
                                            ui.label(h.get('clasificacion')).classes('text-xs font-semibold px-2 py-0.5 rounded-full').style(
                                                f'color:{clasif_color}; background:{clasif_color}22;'
                                            )
                                            if h.get('clausula'):
                                                ui.label(f"Cláusula {h['clausula']}").classes('text-xs text-gray-400')
                                        ui.label(fix_text(h.get('descripcion'))).classes('text-sm mt-1')
                                        if h.get('accion_correctiva'):
                                            ui.label(f"Acción: {fix_text(h.get('accion_correctiva'))}").classes('text-xs text-gray-600')
                                        meta = ' · '.join(
                                            x for x in [
                                                f"Resp: {h.get('responsable')}" if h.get('responsable') else '',
                                                f"Límite: {h.get('fecha_limite')}" if h.get('fecha_limite') else '',
                                            ] if x
                                        )
                                        if meta:
                                            ui.label(meta).classes('text-xs text-gray-400')
                                    with ui.column().classes('items-end gap-1'):
                                        est_color = _ESTADO_HALLAZGO_COLOR.get(h.get('estado'), '#6B7480')
                                        ui.label(h.get('estado')).classes('text-xs font-semibold px-2 py-0.5 rounded-full').style(
                                            f'color:{est_color}; background:{est_color}22;'
                                        )
                                        with ui.row().classes('gap-1'):
                                            ui.button(icon='edit', on_click=lambda hid=h['id']: _abrir_form_hallazgo(auditoria_id, hid)).props(
                                                'flat round dense size=sm'
                                            ).tooltip('Editar hallazgo')
                                            if h.get('estado') != 'Cerrado':
                                                ui.button(icon='task_alt', on_click=lambda hid=h['id']: _cerrar_hallazgo(hid)).props(
                                                    'flat round dense size=sm color=positive'
                                                ).tooltip('Cerrar hallazgo')
                                            ui.button(icon='delete', on_click=lambda hid=h['id']: _eliminar_hallazgo(hid)).props(
                                                'flat round dense size=sm color=negative'
                                            ).tooltip('Eliminar hallazgo')

                    def _cerrar_hallazgo(hallazgo_id: int) -> None:
                        with ui.dialog() as ev_dialog, ui.card().classes('w-full max-w-sm'):
                            ui.label('Cerrar hallazgo').classes('text-base font-semibold')
                            evidencia = ui.textarea('Evidencia de cierre').classes('w-full').props('outlined')
                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Cancelar', on_click=ev_dialog.close).props('flat no-caps')

                                def _confirmar() -> None:
                                    ok, msg = cerrar_hallazgo_auditoria(hallazgo_id, evidencia.value, empresa_id=selected_company_id)
                                    ui.notify(msg, type='positive' if ok else 'negative')
                                    ev_dialog.close()
                                    tabla_hallazgos.refresh()

                                ui.button('Confirmar cierre', on_click=_confirmar).props('unelevated no-caps color=positive')
                        ev_dialog.open()

                    def _eliminar_hallazgo(hallazgo_id: int) -> None:
                        ok, msg = eliminar_hallazgo_auditoria(hallazgo_id, empresa_id=selected_company_id)
                        ui.notify(msg, type='positive' if ok else 'negative')
                        tabla_hallazgos.refresh()

                    def _abrir_form_hallazgo(auditoria_id: int, hallazgo_id: int | None) -> None:
                        existente = None
                        if hallazgo_id:
                            existente = next((h for h in obtener_hallazgos_auditoria(auditoria_id) if h['id'] == hallazgo_id), None)
                        with ui.dialog() as h_dialog, ui.card().classes('w-full max-w-lg'):
                            ui.label('Editar hallazgo' if existente else 'Nuevo hallazgo').classes('text-base font-semibold')
                            clausula = ui.input('Cláusula (opcional)', value=(existente or {}).get('clausula', '')).classes('w-full').props('outlined dense')
                            descripcion = ui.textarea('Descripción', value=(existente or {}).get('descripcion', '')).classes('w-full').props('outlined')
                            clasificacion = ui.select(CLASIFICACIONES_HALLAZGO, label='Clasificación', value=(existente or {}).get('clasificacion', CLASIFICACIONES_HALLAZGO[2])).classes('w-full').props('outlined dense')
                            accion = ui.textarea('Acción correctiva propuesta', value=(existente or {}).get('accion_correctiva', '')).classes('w-full').props('outlined')
                            with ui.row().classes('w-full gap-2'):
                                responsable = ui.input('Responsable', value=(existente or {}).get('responsable', '')).classes('flex-1').props('outlined dense')
                                fecha_limite = ui.input('Fecha límite', value=(existente or {}).get('fecha_limite', '')).classes('flex-1').props('outlined dense type=date')
                            estado_h = ui.select(ESTADOS_HALLAZGO, label='Estado', value=(existente or {}).get('estado', 'Abierto')).classes('w-full').props('outlined dense')
                            with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                ui.button('Cancelar', on_click=h_dialog.close).props('flat no-caps')

                                def _guardar() -> None:
                                    payload = {
                                        'clausula': clausula.value, 'descripcion': descripcion.value,
                                        'clasificacion': clasificacion.value, 'accion_correctiva': accion.value,
                                        'responsable': responsable.value, 'fecha_limite': fecha_limite.value,
                                        'estado': estado_h.value,
                                    }
                                    if existente:
                                        ok, msg = actualizar_hallazgo_auditoria(hallazgo_id, payload, empresa_id=selected_company_id)
                                    else:
                                        ok, msg, _new_id = crear_hallazgo_auditoria(auditoria_id, selected_company_id, payload)
                                    ui.notify(msg, type='positive' if ok else 'negative')
                                    if ok:
                                        h_dialog.close()
                                        tabla_hallazgos.refresh()

                                ui.button('Guardar', on_click=_guardar).props('unelevated no-caps color=primary')
                        h_dialog.open()

                    tabla_hallazgos()
                detail_dialog.open()

            # ---- alta / edicion de auditoria --------------------------------
            def _abrir_form_auditoria(auditoria_id: int | None) -> None:
                existente = obtener_auditoria_detalle(auditoria_id) if auditoria_id else None
                with ui.dialog() as a_dialog, ui.card().classes('w-full max-w-lg'):
                    ui.label('Editar auditoría' if existente else 'Nueva auditoría').classes('text-base font-semibold')
                    titulo = ui.input('Título', value=(existente or {}).get('titulo', '')).classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full gap-2'):
                        area = ui.select(AREAS_AUDITORIA, label='Área', value=(existente or {}).get('area', AREAS_AUDITORIA[0])).classes('flex-1').props('outlined dense')
                        norma = ui.select(NORMAS_AUDITORIA, label='Norma', value=(existente or {}).get('norma', NORMAS_AUDITORIA[0])).classes('flex-1').props('outlined dense')
                    alcance = ui.textarea('Alcance', value=(existente or {}).get('alcance', '')).classes('w-full').props('outlined')
                    auditor = ui.input('Auditor', value=(existente or {}).get('auditor', '')).classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full gap-2'):
                        fecha_prog = ui.input('Fecha programada', value=(existente or {}).get('fecha_programada', '')).classes('flex-1').props('outlined dense type=date')
                        fecha_real = ui.input('Fecha realizada', value=(existente or {}).get('fecha_realizada', '')).classes('flex-1').props('outlined dense type=date')
                    estado_a = ui.select(ESTADOS_AUDITORIA, label='Estado', value=(existente or {}).get('estado', 'Programada')).classes('w-full').props('outlined dense')
                    conclusion = ui.textarea('Conclusión', value=(existente or {}).get('conclusion', '')).classes('w-full').props('outlined')
                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancelar', on_click=a_dialog.close).props('flat no-caps')

                        def _guardar() -> None:
                            payload = {
                                'titulo': titulo.value, 'area': area.value, 'norma': norma.value,
                                'alcance': alcance.value, 'auditor': auditor.value,
                                'fecha_programada': fecha_prog.value, 'fecha_realizada': fecha_real.value,
                                'estado': estado_a.value, 'conclusion': conclusion.value,
                            }
                            if existente:
                                ok, msg = actualizar_auditoria_interna(auditoria_id, payload, empresa_id=selected_company_id)
                            else:
                                ok, msg, _new_id = crear_auditoria_interna(selected_company_id, payload)
                            ui.notify(msg, type='positive' if ok else 'negative')
                            if ok:
                                a_dialog.close()
                                tabla_auditorias.refresh()

                        ui.button('Guardar', on_click=_guardar).props('unelevated no-caps color=primary')
                a_dialog.open()

            def _eliminar_auditoria(auditoria_id: int) -> None:
                ok, msg = eliminar_auditoria_interna(auditoria_id, empresa_id=selected_company_id)
                ui.notify(msg, type='positive' if ok else 'negative')
                tabla_auditorias.refresh()

            with ui.row().classes('w-full justify-between items-center mb-2'):
                ui.label('Programa de auditorías').classes('text-sm font-semibold text-gray-600')
                ui.button('Nueva auditoría', icon='add', on_click=lambda: _abrir_form_auditoria(None)).props('unelevated no-caps color=primary')

            @ui.refreshable
            def tabla_auditorias() -> None:
                auditorias = obtener_auditorias_empresa(selected_company_id)
                if not auditorias:
                    with ui.card().classes('w-full p-6 items-center').style('box-shadow:none;border:1px dashed #CBD5E1;'):
                        ui.icon('fact_check', size='2rem').classes('text-gray-300')
                        ui.label('Todavía no hay auditorías programadas para esta empresa.').classes('text-sm text-gray-400')
                    return
                for a in auditorias:
                    color = _ESTADO_AUD_COLOR.get(a.get('estado'), '#6B7480')
                    with ui.card().classes('w-full p-3 mb-2 cursor-pointer').style('box-shadow:none;border:1px solid #E5E7EB;') as card:
                        with ui.row().classes('w-full justify-between items-center'):
                            with ui.column().classes('gap-0 flex-1').on('click', lambda aid=a['id']: _abrir_detalle(aid)):
                                ui.label(fix_text(a.get('titulo'))).classes('text-sm font-semibold')
                                ui.label(f"{a.get('area')} · {a.get('norma')} · Programada: {a.get('fecha_programada') or '—'}").classes('text-xs text-gray-500')
                            with ui.row().classes('items-center gap-2'):
                                ui.label(a.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(
                                    f'color:{color}; background:{color}22;'
                                )
                                ui.button(icon='visibility', on_click=lambda aid=a['id']: _abrir_detalle(aid)).props('flat round dense size=sm').tooltip('Ver detalle')
                                ui.button(icon='delete', on_click=lambda aid=a['id']: _eliminar_auditoria(aid)).props('flat round dense size=sm color=negative').tooltip('Eliminar auditoría')

            tabla_auditorias()
