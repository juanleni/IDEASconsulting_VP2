"""Gestión Documental — repositorio de documentos controlados (Fase 2, 2026-08-10).

Distinto de modules_documents.py (biblioteca de referencia de qué documentos
exige cada norma): esto es el repositorio real de documentos de la empresa,
con código, versión, estado, aprobador y lista maestra exportable.
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from nicegui import app, events, ui
from company_context import empresa_id_from_query_for_admin, with_empresa_id

UPLOAD_DIR = Path(__file__).resolve().parent / 'uploads' / 'documentos_controlados'


def go_to_document_control_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/gestion-documental', company_id))


_ESTADO_COLOR = {'Vigente': '#15803D', 'En revisión': '#B45309', 'Obsoleto': '#6B7480'}


def _save_uploaded_file(company_id: int, document_id: int, event: events.UploadEventArguments) -> tuple[str, str]:
    target_dir = UPLOAD_DIR / f'empresa_{company_id}' / f'doc_{document_id}'
    target_dir.mkdir(parents=True, exist_ok=True)
    upload = getattr(event, 'file', None)
    raw_name = getattr(upload, 'name', None) or getattr(event, 'name', None) or getattr(getattr(event, 'content', None), 'name', None) or 'documento.bin'
    safe_name = Path(str(raw_name)).name
    target_path = target_dir / safe_name
    if upload is not None:
        data = getattr(upload, '_data', None)
        path = getattr(upload, '_path', None)
        if isinstance(data, (bytes, bytearray)):
            target_path.write_bytes(bytes(data))
            return str(target_path), safe_name
        if path:
            source = Path(str(path))
            if source.exists():
                target_path.write_bytes(source.read_bytes())
                return str(target_path), safe_name
    content = getattr(event, 'content', None)
    if content is None:
        raise ValueError('El archivo cargado no contiene contenido legible.')
    if hasattr(content, 'seek'):
        content.seek(0)
    payload = content.read() if hasattr(content, 'read') else content
    target_path.write_bytes(payload)
    return str(target_path), safe_name


def register_document_control_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    fix_text = deps.get('fix_text', lambda v: '' if v is None else str(v))

    obtener_documentos_controlados_empresa = deps['obtener_documentos_controlados_empresa']
    obtener_documento_controlado_detalle = deps['obtener_documento_controlado_detalle']
    obtener_historial_documento_controlado = deps['obtener_historial_documento_controlado']
    crear_documento_controlado = deps['crear_documento_controlado']
    actualizar_documento_controlado = deps['actualizar_documento_controlado']
    registrar_nueva_version_documento = deps['registrar_nueva_version_documento']
    cambiar_estado_documento_controlado = deps['cambiar_estado_documento_controlado']
    eliminar_documento_controlado = deps['eliminar_documento_controlado']
    TIPOS_DOCUMENTO_CONTROLADO = deps['TIPOS_DOCUMENTO_CONTROLADO']
    ESTADOS_DOCUMENTO_CONTROLADO = deps['ESTADOS_DOCUMENTO_CONTROLADO']

    @ui.page('/sistema-gestion/gestion-documental')
    def document_control_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Gestión Documental', back_route='/sistema-gestion', module_key='document_control')
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

            def _actor_name() -> str:
                return str(app.storage.user.get('session_user_name') or app.storage.user.get('session_user_key') or '').strip()

            ui.label('Repositorio de documentos controlados').classes('ideas-kicker')
            ui.label(
                'Lista maestra de la empresa: código, versión vigente, estado y aprobador — con historial '
                'de versiones para cada documento.'
            ).classes('ideas-section-note mb-3')

            estado_filter = {'value': ''}

            def _exportar_lista_maestra() -> None:
                docs = obtener_documentos_controlados_empresa(selected_company_id, estado_filter['value'])
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(['Código', 'Título', 'Tipo', 'Proceso/Área', 'Versión', 'Estado', 'Fecha emisión', 'Fecha vigencia', 'Aprobador', 'Archivo'])
                for d in docs:
                    writer.writerow([
                        d.get('codigo', ''), d.get('titulo', ''), d.get('tipo', ''), d.get('proceso_area', ''),
                        d.get('version_actual', ''), d.get('estado', ''), d.get('fecha_emision', ''),
                        d.get('fecha_vigencia', ''), d.get('aprobador', ''), d.get('archivo_nombre', ''),
                    ])
                payload = buf.getvalue().encode('utf-8-sig')
                ui.download(payload, filename=f'lista_maestra_documentos_empresa_{selected_company_id}.csv', media_type='text/csv')
                ui.notify('Lista maestra exportada.', type='positive')

            def _abrir_form_nuevo() -> None:
                with ui.dialog() as n_dialog, ui.card().classes('w-full max-w-lg'):
                    ui.label('Nuevo documento controlado').classes('text-base font-semibold')
                    with ui.row().classes('w-full gap-2'):
                        codigo = ui.input('Código (ej: PRO-CAL-01)').classes('flex-1').props('outlined dense')
                        tipo = ui.select(TIPOS_DOCUMENTO_CONTROLADO, label='Tipo', value=TIPOS_DOCUMENTO_CONTROLADO[1]).classes('flex-1').props('outlined dense')
                    titulo = ui.input('Título').classes('w-full').props('outlined dense')
                    proceso_area = ui.input('Proceso / Área').classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full gap-2'):
                        fecha_emision = ui.input('Fecha de emisión', value='').classes('flex-1').props('outlined dense type=date')
                        fecha_vigencia = ui.input('Vigente hasta (opcional)', value='').classes('flex-1').props('outlined dense type=date')
                    with ui.row().classes('w-full gap-2'):
                        elaborado_por = ui.input('Elaborado por').classes('flex-1').props('outlined dense')
                        revisado_por = ui.input('Revisado por').classes('flex-1').props('outlined dense')
                    aprobador = ui.input('Aprobador').classes('w-full').props('outlined dense')
                    notas = ui.textarea('Notas (opcional)').classes('w-full').props('outlined dense')

                    uploaded_state = {'path': '', 'name': ''}
                    ui.label('Archivo (versión 1)').classes('text-xs font-semibold text-slate-500 mt-1')

                    def _on_upload(e: events.UploadEventArguments) -> None:
                        try:
                            path, name = _save_uploaded_file(selected_company_id, 0, e)
                            uploaded_state['path'] = path
                            uploaded_state['name'] = name
                            ui.notify(f'Archivo "{name}" listo para guardar.', type='positive')
                        except Exception as exc:
                            ui.notify(f'No se pudo cargar el archivo: {exc}', type='negative')

                    ui.upload(on_upload=_on_upload, auto_upload=True, label='Subir archivo').props(
                        'accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg"'
                    ).classes('w-full')

                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancelar', on_click=n_dialog.close).props('flat no-caps')

                        def _guardar() -> None:
                            payload = {
                                'codigo': codigo.value, 'titulo': titulo.value, 'tipo': tipo.value,
                                'proceso_area': proceso_area.value, 'fecha_emision': fecha_emision.value,
                                'fecha_vigencia': fecha_vigencia.value, 'elaborado_por': elaborado_por.value,
                                'revisado_por': revisado_por.value, 'aprobador': aprobador.value,
                                'notas': notas.value, 'version_actual': '1', 'estado': 'Vigente',
                                'archivo_path': uploaded_state['path'], 'archivo_nombre': uploaded_state['name'],
                                'actor': _actor_name(),
                            }
                            ok, msg, _new_id = crear_documento_controlado(selected_company_id, payload)
                            ui.notify(msg, type='positive' if ok else 'negative')
                            if ok:
                                n_dialog.close()
                                tabla_documentos.refresh()

                        ui.button('Crear documento', on_click=_guardar).props('unelevated no-caps color=primary')
                n_dialog.open()

            def _abrir_detalle(documento_id: int) -> None:
                doc = obtener_documento_controlado_detalle(documento_id)
                if not doc:
                    ui.notify('El documento ya no existe.', type='warning')
                    tabla_documentos.refresh()
                    return

                with ui.dialog() as d_dialog, ui.card().classes('w-full max-w-2xl').style('max-height:90vh;'):
                    with ui.scroll_area().classes('w-full').style('max-height:82vh;'):
                        with ui.row().classes('w-full justify-between items-start'):
                            with ui.column().classes('gap-0'):
                                ui.label(f"{fix_text(doc.get('codigo')) or 's/código'} — {fix_text(doc.get('titulo'))}").classes('text-lg font-semibold')
                                ui.label(f"{doc.get('tipo')} · {fix_text(doc.get('proceso_area')) or 'Sin área asignada'} · Versión {doc.get('version_actual')}").classes('text-xs text-gray-500')
                            color = _ESTADO_COLOR.get(doc.get('estado'), '#6B7480')
                            ui.label(doc.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(f'color:{color}; background:{color}22;')

                        with ui.row().classes('w-full gap-4 flex-wrap mt-2'):
                            ui.label(f"Aprobador: {fix_text(doc.get('aprobador')) or '—'}").classes('text-sm')
                            ui.label(f"Elaborado por: {fix_text(doc.get('elaborado_por')) or '—'}").classes('text-sm')
                            ui.label(f"Revisado por: {fix_text(doc.get('revisado_por')) or '—'}").classes('text-sm')
                        with ui.row().classes('w-full gap-4 flex-wrap'):
                            ui.label(f"Emisión: {doc.get('fecha_emision') or '—'}").classes('text-sm')
                            ui.label(f"Vigente hasta: {doc.get('fecha_vigencia') or '—'}").classes('text-sm')
                        if doc.get('notas'):
                            ui.label(f"Notas: {fix_text(doc.get('notas'))}").classes('text-sm text-gray-700 mt-1')

                        with ui.row().classes('w-full gap-2 mt-3'):
                            if doc.get('archivo_path'):
                                ui.button('Descargar archivo vigente', icon='download', on_click=lambda: ui.download(doc['archivo_path'], filename=doc.get('archivo_nombre') or None)).props('flat no-caps color=primary')
                            for estado_opt in ESTADOS_DOCUMENTO_CONTROLADO:
                                if estado_opt == doc.get('estado'):
                                    continue

                                def _cambiar(e=estado_opt):
                                    ok, msg = cambiar_estado_documento_controlado(documento_id, e, empresa_id=selected_company_id, actor=_actor_name())
                                    ui.notify(msg, type='positive' if ok else 'negative')
                                    if ok:
                                        d_dialog.close()
                                        tabla_documentos.refresh()

                                ui.button(f'Marcar {estado_opt}', on_click=_cambiar).props('flat no-caps dense')

                        ui.separator().classes('my-3')
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label('Nueva versión').classes('text-sm font-semibold')
                        with ui.row().classes('w-full gap-2 items-end'):
                            nueva_version_input = ui.input('Número de versión', value=str(_next_version_guess(doc.get('version_actual')))).classes('w-40').props('outlined dense')
                            cambios_input = ui.input('Qué cambió (obligatorio para trazabilidad)').classes('flex-1').props('outlined dense')
                        version_upload_state = {'path': '', 'name': ''}

                        def _on_version_upload(e: events.UploadEventArguments) -> None:
                            try:
                                path, name = _save_uploaded_file(selected_company_id, documento_id, e)
                                version_upload_state['path'] = path
                                version_upload_state['name'] = name
                                ui.notify(f'Archivo "{name}" listo — hacé click en "Registrar nueva versión".', type='positive')
                            except Exception as exc:
                                ui.notify(f'No se pudo cargar el archivo: {exc}', type='negative')

                        ui.upload(on_upload=_on_version_upload, auto_upload=True, label='Subir archivo de la nueva versión').props(
                            'accept=".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.png,.jpg,.jpeg"'
                        ).classes('w-full')

                        def _registrar_version() -> None:
                            if not version_upload_state['path']:
                                ui.notify('Subí el archivo de la nueva versión antes de registrarla.', type='warning')
                                return
                            if not cambios_input.value.strip():
                                ui.notify('Indicá qué cambió respecto de la versión anterior.', type='warning')
                                return
                            ok, msg = registrar_nueva_version_documento(documento_id, {
                                'version': nueva_version_input.value, 'estado': 'Vigente',
                                'archivo_path': version_upload_state['path'], 'archivo_nombre': version_upload_state['name'],
                                'cambios': cambios_input.value, 'actor': _actor_name(),
                            }, empresa_id=selected_company_id)
                            ui.notify(msg, type='positive' if ok else 'negative')
                            if ok:
                                d_dialog.close()
                                tabla_documentos.refresh()

                        ui.button('Registrar nueva versión', icon='upload_file', on_click=_registrar_version).props('unelevated no-caps color=primary mt-2')

                        ui.separator().classes('my-3')
                        ui.label('Historial de versiones').classes('text-sm font-semibold')
                        historial = obtener_historial_documento_controlado(documento_id)
                        if not historial:
                            ui.label('Sin historial registrado.').classes('text-xs text-gray-400')
                        for h in historial:
                            with ui.row().classes('w-full items-center gap-2 py-1').style('border-bottom:1px solid #F1F5F9;'):
                                ui.label(f"v{h.get('version')}").classes('text-xs font-semibold w-12')
                                ui.label(h.get('estado')).classes('text-xs w-24')
                                ui.label(h.get('fecha')).classes('text-xs text-gray-400 w-36')
                                ui.label(fix_text(h.get('cambios'))).classes('text-xs flex-1')

                        ui.separator().classes('my-3')
                        with ui.row().classes('w-full justify-between'):
                            ui.button('Editar metadatos', icon='edit', on_click=lambda: (d_dialog.close(), _abrir_form_editar(documento_id))).props('flat no-caps')
                            ui.button('Eliminar documento', icon='delete', on_click=lambda: _eliminar(documento_id, d_dialog)).props('flat no-caps color=negative')
                d_dialog.open()

            def _next_version_guess(current: str) -> str:
                try:
                    return str(round(float(current) + 1, 1)) if '.' not in str(current) else str(round(float(current) + 0.1, 1))
                except Exception:
                    return str(current or '') + '.1'

            def _eliminar(documento_id: int, dialog) -> None:
                ok, msg = eliminar_documento_controlado(documento_id, empresa_id=selected_company_id)
                ui.notify(msg, type='positive' if ok else 'negative')
                if ok:
                    dialog.close()
                    tabla_documentos.refresh()

            def _abrir_form_editar(documento_id: int) -> None:
                doc = obtener_documento_controlado_detalle(documento_id)
                if not doc:
                    return
                with ui.dialog() as e_dialog, ui.card().classes('w-full max-w-lg'):
                    ui.label('Editar metadatos').classes('text-base font-semibold')
                    with ui.row().classes('w-full gap-2'):
                        codigo = ui.input('Código', value=doc.get('codigo', '')).classes('flex-1').props('outlined dense')
                        tipo = ui.select(TIPOS_DOCUMENTO_CONTROLADO, label='Tipo', value=doc.get('tipo') or TIPOS_DOCUMENTO_CONTROLADO[1]).classes('flex-1').props('outlined dense')
                    titulo = ui.input('Título', value=doc.get('titulo', '')).classes('w-full').props('outlined dense')
                    proceso_area = ui.input('Proceso / Área', value=doc.get('proceso_area', '')).classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full gap-2'):
                        fecha_emision = ui.input('Fecha de emisión', value=doc.get('fecha_emision', '')).classes('flex-1').props('outlined dense type=date')
                        fecha_vigencia = ui.input('Vigente hasta', value=doc.get('fecha_vigencia', '')).classes('flex-1').props('outlined dense type=date')
                    with ui.row().classes('w-full gap-2'):
                        elaborado_por = ui.input('Elaborado por', value=doc.get('elaborado_por', '')).classes('flex-1').props('outlined dense')
                        revisado_por = ui.input('Revisado por', value=doc.get('revisado_por', '')).classes('flex-1').props('outlined dense')
                    aprobador = ui.input('Aprobador', value=doc.get('aprobador', '')).classes('w-full').props('outlined dense')
                    notas = ui.textarea('Notas', value=doc.get('notas', '')).classes('w-full').props('outlined dense')
                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                        ui.button('Cancelar', on_click=e_dialog.close).props('flat no-caps')

                        def _guardar() -> None:
                            payload = {
                                'codigo': codigo.value, 'titulo': titulo.value, 'tipo': tipo.value,
                                'proceso_area': proceso_area.value, 'fecha_emision': fecha_emision.value,
                                'fecha_vigencia': fecha_vigencia.value, 'elaborado_por': elaborado_por.value,
                                'revisado_por': revisado_por.value, 'aprobador': aprobador.value,
                                'notas': notas.value,
                            }
                            ok, msg = actualizar_documento_controlado(documento_id, payload, empresa_id=selected_company_id)
                            ui.notify(msg, type='positive' if ok else 'negative')
                            if ok:
                                e_dialog.close()
                                tabla_documentos.refresh()

                        ui.button('Guardar', on_click=_guardar).props('unelevated no-caps color=primary')
                e_dialog.open()

            with ui.row().classes('w-full justify-between items-center mb-2 flex-wrap gap-2'):
                filtro_select = ui.select(
                    {'': 'Todos los estados', **{e: e for e in ESTADOS_DOCUMENTO_CONTROLADO}},
                    value='', label='Filtrar por estado',
                ).classes('w-56').props('outlined dense')
                with ui.row().classes('gap-2'):
                    ui.button('Exportar lista maestra', icon='download', on_click=_exportar_lista_maestra).props('flat no-caps')
                    ui.button('Nuevo documento', icon='add', on_click=_abrir_form_nuevo).props('unelevated no-caps color=primary')

            def _on_filter_change() -> None:
                estado_filter['value'] = filtro_select.value or ''
                tabla_documentos.refresh()

            filtro_select.on_value_change(lambda _e: _on_filter_change())

            @ui.refreshable
            def tabla_documentos() -> None:
                docs = obtener_documentos_controlados_empresa(selected_company_id, estado_filter['value'])
                if not docs:
                    with ui.card().classes('w-full p-6 items-center').style('box-shadow:none;border:1px dashed #CBD5E1;'):
                        ui.icon('folder_managed', size='2rem').classes('text-gray-300')
                        ui.label('Todavía no hay documentos controlados cargados para esta empresa.').classes('text-sm text-gray-400')
                    return
                for d in docs:
                    color = _ESTADO_COLOR.get(d.get('estado'), '#6B7480')
                    with ui.card().classes('w-full p-3 mb-2 cursor-pointer').style('box-shadow:none;border:1px solid #E5E7EB;'):
                        with ui.row().classes('w-full justify-between items-center').on('click', lambda did=d['id']: _abrir_detalle(did)):
                            with ui.column().classes('gap-0 flex-1'):
                                ui.label(f"{fix_text(d.get('codigo')) or 's/código'} — {fix_text(d.get('titulo'))}").classes('text-sm font-semibold')
                                ui.label(f"{d.get('tipo')} · v{d.get('version_actual')} · {fix_text(d.get('proceso_area')) or 'Sin área'} · Aprobador: {fix_text(d.get('aprobador')) or '—'}").classes('text-xs text-gray-500')
                            ui.label(d.get('estado')).classes('text-xs font-semibold px-2 py-1 rounded-full').style(f'color:{color}; background:{color}22;')

            tabla_documentos()
