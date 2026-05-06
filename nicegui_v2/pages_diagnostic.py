from __future__ import annotations

import base64
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except Exception:
    PdfReader = None


def register_diagnostic_pages(ui, app, deps: dict) -> None:
    pd, go = deps['pd'], deps['go']
    shell, ensure_platform_access = deps['shell'], deps['ensure_platform_access']
    obtener_empresas, obtener_empresa_detalle, guardar_empresa = deps['obtener_empresas'], deps['obtener_empresa_detalle'], deps['guardar_empresa']
    actualizar_empresa = deps['actualizar_empresa']
    eliminar_empresa = deps['eliminar_empresa']
    go_to_management_workspace, set_selection = deps['go_to_management_workspace'], deps['set_selection']
    leer_diagnostico_excel, grouped_questions, load_criteria = deps['leer_diagnostico_excel'], deps['grouped_questions'], deps['load_criteria']
    company_options, current_selection = deps['company_options'], deps['current_selection']
    diagnosis_record, diagnosis_response_dicts, split_evidence_values = deps['diagnosis_record'], deps['diagnosis_response_dicts'], deps['split_evidence_values']
    fix_text, certifications_summary = deps['fix_text'], deps['certifications_summary']
    actualizar_diagnostico, guardar_diagnostico = deps['actualizar_diagnostico'], deps['guardar_diagnostico']
    obtener_nivel, obtener_conclusion = deps['obtener_nivel'], deps['obtener_conclusion']
    diagnosis_rows, diagnosis_badge_style, diagnosis_options = deps['diagnosis_rows'], deps['diagnosis_badge_style'], deps['diagnosis_options']
    build_eje_scores, build_plan, short_axis_label = deps['build_eje_scores'], deps['build_plan'], deps['short_axis_label']
    obtener_mensaje_direccion, quick_card, obtener_prioridad_recomendada = deps['obtener_mensaje_direccion'], deps['quick_card'], deps['obtener_prioridad_recomendada']
    start_edit, render_metrics, eliminar_diagnostico = deps['start_edit'], deps['render_metrics'], deps['eliminar_diagnostico']
    guardar_fuente_empresa = deps['guardar_fuente_empresa']
    obtener_fuentes_empresa = deps['obtener_fuentes_empresa']
    eliminar_fuente = deps['eliminar_fuente']
    guardar_token_empresa = deps.get('guardar_token_empresa')
    generar_token_seguro = deps.get('generar_token_seguro')
    enviar_correo_acceso = deps.get('enviar_correo_acceso')
    generar_pdf_ejecutivo_v2 = deps['generar_pdf_ejecutivo_v2']

    root_dir = Path(__file__).resolve().parents[1]
    company_logo_dir = root_dir / 'assets' / 'logos_empresas'

    def logo_url_from_path(path: str) -> str:
        clean = str(path or '').strip().replace('\\', '/')
        if not clean:
            return ''
        if clean.startswith('/assets/'):
            return clean
        return f"/assets/{clean}"

    async def save_company_logo(upload_event, prefix: str = 'empresa') -> str:
        company_logo_dir.mkdir(parents=True, exist_ok=True)
        uploaded_file = getattr(upload_event, 'file', None)
        original_name = str(getattr(uploaded_file, 'name', '') or getattr(upload_event, 'name', '') or 'logo.png')
        safe_prefix = re.sub(r'[^A-Za-z0-9_.-]+', '_', str(prefix or 'empresa')).strip('_') or 'empresa'
        safe_name = re.sub(r'[^A-Za-z0-9_.-]+', '_', original_name).strip('_') or 'logo.png'
        target_name = f"{safe_prefix}_{safe_name}"
        target_path = company_logo_dir / target_name
        if uploaded_file and hasattr(uploaded_file, 'save'):
            if hasattr(uploaded_file, 'size') and uploaded_file.size() <= 0:
                raise ValueError('El archivo recibido esta vacio. Intenta cargarlo nuevamente.')
            await uploaded_file.save(target_path)
            if not target_path.exists() or target_path.stat().st_size <= 0:
                raise ValueError('El logo se recibio, pero no se pudo guardar con contenido. Intenta cargarlo nuevamente.')
            return target_path.relative_to(root_dir).as_posix()

        content = getattr(upload_event, 'content', None)
        data = b''
        if hasattr(content, 'read'):
            if hasattr(content, 'seek'):
                content.seek(0)
            data = content.read()
        elif isinstance(content, (bytes, bytearray)):
            data = bytes(content)
        elif isinstance(content, str):
            data = content.encode('utf-8')
        if not data:
            raise ValueError('El archivo recibido esta vacio. Intentá cargarlo nuevamente.')
        target_path.write_bytes(data)
        return target_path.relative_to(root_dir).as_posix()

    async def extract_knowledge_source(event) -> tuple[str, str, str]:
        uploaded_file = getattr(event, 'file', None)
        if not uploaded_file:
            raise ValueError('No se recibió ningún archivo.')
        nombre = str(getattr(uploaded_file, 'name', '') or 'Fuente IA').strip()
        extension = nombre.rsplit('.', 1)[-1].lower() if '.' in nombre else 'txt'
        tipo = 'pdf' if extension == 'pdf' else extension or 'txt'

        if extension in {'txt', 'md', 'csv', 'json', 'log'} and hasattr(uploaded_file, 'text'):
            contenido = await uploaded_file.text()
        elif extension == 'pdf' and hasattr(uploaded_file, 'read'):
            raw = await uploaded_file.read()
            if PdfReader is None:
                contenido = f"[PDF_BASE64::{nombre}]\n" + base64.b64encode(raw).decode('utf-8')
            else:
                try:
                    from io import BytesIO

                    reader = PdfReader(BytesIO(raw))
                    paginas = []
                    for index, page in enumerate(reader.pages, start=1):
                        texto_pagina = (page.extract_text() or '').strip()
                        if texto_pagina:
                            paginas.append(f"[PAGINA {index}]\n{texto_pagina}")
                    contenido = '\n\n'.join(paginas).strip()
                    if not contenido:
                        raise ValueError('El PDF no contiene texto extraible. Puede ser una imagen o escaneo.')
                except Exception as exc:
                    raise ValueError(f'No se pudo extraer texto del PDF. {exc}')
        elif hasattr(uploaded_file, 'read'):
            raw = await uploaded_file.read()
            try:
                contenido = raw.decode('utf-8')
            except Exception:
                contenido = raw.decode('latin-1', errors='ignore')
        else:
            raise ValueError('No fue posible leer el archivo cargado.')

        if not str(contenido or '').strip():
            raise ValueError('La fuente está vacía y no aporta contenido para la IA.')
        return nombre, tipo, contenido

    def render_sources_manager(container, empresa_id: int) -> None:
        container.clear()
        with container:
            ui.label('Base de Conocimiento IA').classes('text-lg font-semibold text-slate-800')
            ui.label('Sube documentos o agrega contexto textual para alimentar el conocimiento específico de esta empresa.').classes('ideas-section-note')
            titulo_fuente = ui.input('Título de la fuente').classes('w-full')
            texto_libre = ui.textarea('Texto libre / contexto operativo').classes('w-full').props('autogrow')

            async def handle_source_upload(event) -> None:
                try:
                    titulo, tipo, contenido = await extract_knowledge_source(event)
                    ok, message, _fuente_id = guardar_fuente_empresa(empresa_id, titulo, tipo, contenido)
                    ui.notify(fix_text(message), type='positive' if ok else 'negative')
                    if ok:
                        render_sources_manager(container, empresa_id)
                except Exception as exc:
                    ui.notify(f'No se pudo cargar la fuente IA: {exc}', type='negative')

            def save_free_text_source() -> None:
                ok, message, _fuente_id = guardar_fuente_empresa(
                    empresa_id,
                    titulo_fuente.value or 'Contexto manual',
                    'texto',
                    texto_libre.value or '',
                )
                ui.notify(fix_text(message), type='positive' if ok else 'negative')
                if ok:
                    render_sources_manager(container, empresa_id)

            with ui.row().classes('w-full gap-4 items-end mt-3'):
                ui.upload(label='Cargar PDF / TXT / archivo de texto', auto_upload=True, on_upload=handle_source_upload).props('accept=".pdf,.txt,.md,.csv,.json,.log"').classes('col')
                ui.button('Guardar texto libre', icon='note_add', on_click=save_free_text_source).props('unelevated color=primary')

            fuentes = obtener_fuentes_empresa(empresa_id)
            if not fuentes:
                ui.label('Todavía no hay fuentes cargadas para esta empresa.').classes('ideas-section-note mt-4')
                return

            rows = [
                {
                    'id': item['id'],
                    'titulo': fix_text(item.get('titulo', '')),
                    'tipo': str(item.get('tipo', '')).upper(),
                    'fecha_carga': fix_text(item.get('fecha_carga', '')),
                    'contenido_resumen': (fix_text(str(item.get('contenido', '')).replace('\n', ' '))[:120] + '...') if len(str(item.get('contenido', ''))) > 120 else fix_text(item.get('contenido', '')),
                    'acciones': '',
                }
                for item in fuentes
            ]
            table = ui.table(
                columns=[
                    {'name': 'titulo', 'label': 'Fuente', 'field': 'titulo', 'align': 'left'},
                    {'name': 'tipo', 'label': 'Tipo', 'field': 'tipo', 'align': 'center'},
                    {'name': 'fecha_carga', 'label': 'Fecha', 'field': 'fecha_carga', 'align': 'center'},
                    {'name': 'contenido_resumen', 'label': 'Resumen', 'field': 'contenido_resumen', 'align': 'left'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                ],
                rows=rows,
                row_key='id',
                pagination=6,
            ).classes('w-full ideas-table mt-4')
            table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_source', props.row.id)" /></div></q-td>''')
            table.on('delete_source', lambda event: (eliminar_fuente(int(event.args)), ui.notify('Fuente eliminada.', type='positive'), render_sources_manager(container, empresa_id)))

    @ui.page('/empresas')
    def companies_page() -> None:
        if not ensure_platform_access(): return
        if app.storage.user.get('role') != 'admin':
            ui.notify('Acceso denegado.', type='negative')
            ui.navigate.to('/sistema-gestion')
            return
        shell_container = shell('Empresas')
        companies = [{'razon_social': fix_text(name), 'id': company_id, **(obtener_empresa_detalle(company_id) or {})} for company_id, name in obtener_empresas()]
        with shell_container:
            ui.label('Base de empresas').classes('ideas-kicker')
            ui.label('Alta y administración del universo consultivo.').classes('text-3xl font-bold text-slate-900')
            ui.label('Registrá la ficha institucional de cada empresa con el nivel de detalle necesario para los reportes ejecutivos.').classes('ideas-subtitle mb-4')
            with ui.dialog() as dialog_empresa, ui.card().classes('w-[980px] max-w-[96vw] p-6 rounded-[26px] ideas-panel overflow-y-auto').style('max-height: 92vh;'):
                ui.label('Nueva empresa').classes('text-2xl font-bold text-slate-900')
                ui.label('Cargá una nueva empresa cliente con branding, certificaciones y datos institucionales completos.').classes('ideas-section-note')
                with ui.tabs().classes('w-full mt-3') as tabs_new:
                    tab_datos_new = ui.tab('Datos y Branding', icon='business')
                    tab_ai_new = ui.tab('Base de Conocimiento IA', icon='psychology')
                with ui.tab_panels(tabs_new, value=tab_datos_new).classes('w-full bg-transparent overflow-y-auto').style('max-height: 68vh;'):
                    with ui.tab_panel(tab_datos_new).classes('w-full px-0'):
                        razon_social = ui.input('Razón social').classes('w-full')
                        with ui.row().classes('w-full gap-4'):
                            ubicacion = ui.input('Ubicación').classes('col'); rubro = ui.input('Rubro').classes('col'); cantidad_empleados = ui.number('Cantidad de empleados', value=0, min=0, precision=0).classes('col')
                        ui.label('Persona de contacto').classes('text-lg font-semibold text-slate-800 mt-2')
                        with ui.row().classes('w-full gap-4'):
                            contacto_nombre = ui.input('Nombre').classes('col'); contacto_correo = ui.input('Correo').classes('col')
                        with ui.row().classes('w-full gap-4'):
                            contacto_telefono = ui.input('Teléfono').classes('col'); contacto_posicion = ui.input('Posición').classes('col')
                        ui.label('Acceso de la empresa').classes('text-lg font-semibold text-slate-800 mt-2')
                        ui.label('Envía un enlace para que la empresa cree su propia contraseña.').classes('ideas-section-note')
                        def enviar_enlace_nueva_empresa() -> None:
                            correo = str(contacto_correo.value or '').strip()
                            nombre = str(razon_social.value or '').strip() or 'Empresa'
                            if not correo:
                                ui.notify('Primero ingresa un correo de contacto.', type='warning')
                                return
                            if not (guardar_token_empresa and generar_token_seguro and enviar_correo_acceso):
                                ui.notify('No se encontró la lógica de envío de acceso.', type='negative')
                                return
                            token = generar_token_seguro()
                            ok = guardar_token_empresa(correo, token, expiracion_minutos=1440)
                            if not ok:
                                ui.notify('Guarda la empresa primero para poder enviar el enlace de acceso.', type='warning')
                                return
                            enviar_correo_acceso(correo, nombre, token)
                            ui.notify('Enlace de acceso enviado correctamente.', type='positive')
                        with ui.row().classes('w-full justify-start'):
                            ui.button('Enviar enlace de acceso', icon='mail', on_click=enviar_enlace_nueva_empresa).props('outline color=primary')
                        ui.label('Certificaciones').classes('text-lg font-semibold text-slate-800 mt-2')
                        with ui.row().classes('w-full gap-4'):
                            cert_9001 = ui.switch('ISO 9001', value=False); cert_14001 = ui.switch('ISO 14001', value=False); cert_45001 = ui.switch('ISO 45001', value=False); cert_iatf = ui.switch('IATF', value=False)
                        logo_temporal = {'path': ''}
                        logo_preview = ui.column().classes('w-full mt-3')
                        with logo_preview:
                            ui.label('Logo de la empresa').classes('text-lg font-semibold text-slate-800')
                            ui.label('Se guardara localmente en assets/logos_empresas.').classes('ideas-section-note')
                        async def handle_logo_upload(event) -> None:
                            try:
                                logo_temporal['path'] = await save_company_logo(event, prefix=fix_text(razon_social.value or 'empresa'))
                                logo_preview.clear()
                                with logo_preview:
                                    ui.label('Logo de la empresa').classes('text-lg font-semibold text-slate-800')
                                    ui.image(logo_url_from_path(logo_temporal['path'])).classes('w-32 max-h-24 object-contain')
                                    ui.label(logo_temporal['path']).classes('text-xs text-slate-500')
                                ui.notify('Logo cargado correctamente.', type='positive')
                            except Exception as exc:
                                ui.notify(f'No se pudo cargar el logo: {exc}', type='negative')
                        ui.upload(label='Cargar logo', auto_upload=True, on_upload=handle_logo_upload).props('accept=".png,.jpg,.jpeg,.svg,.webp"').classes('w-full mt-2')
                        with ui.card().classes('w-full mt-4 p-4 border border-violet-200 bg-violet-50 shadow-none rounded-[20px]'):
                            ui.label('Copiloto IA').classes('text-lg font-semibold text-violet-900')
                            ui.label('Activa o desactiva el acceso al modulo IA para esta empresa.').classes('text-sm text-violet-700')
                            agente_ia_activo = ui.switch('Habilitar Copiloto IA para esta empresa', value=False).classes('mt-3')
                        ui.label('Estilo visual del cliente').classes('text-lg font-semibold text-slate-800 mt-4')
                        with ui.row().classes('w-full gap-4'):
                            color_primario = ui.color_input('Color primario', value='#1f7ed6', preview=True).classes('col')
                            color_secundario = ui.color_input('Color secundario', value='#0f766e', preview=True).classes('col')
                    with ui.tab_panel(tab_ai_new).classes('w-full px-0'):
                        with ui.card().classes('ideas-panel w-full'):
                            ui.label('Base de Conocimiento IA').classes('ideas-section-title')
                            ui.label('Guarda primero la empresa para habilitar la carga de documentos y contexto específico para la IA.').classes('ideas-section-note')
                def save_company() -> None:
                    payload = {'razon_social': razon_social.value or '', 'ubicacion': ubicacion.value or '', 'contacto_nombre': contacto_nombre.value or '', 'contacto_correo': contacto_correo.value or '', 'password': '', 'contacto_telefono': contacto_telefono.value or '', 'contacto_posicion': contacto_posicion.value or '', 'rubro': rubro.value or '', 'cantidad_empleados': int(cantidad_empleados.value or 0), 'cert_iso_9001': 'Sí' if cert_9001.value else 'No', 'cert_iso_14001': 'Sí' if cert_14001.value else 'No', 'cert_iso_45001': 'Sí' if cert_45001.value else 'No', 'cert_iatf': 'Sí' if cert_iatf.value else 'No'}
                    payload['logo_path'] = logo_temporal['path']
                    payload['color_primario'] = color_primario.value or ''
                    payload['color_secundario'] = color_secundario.value or ''
                    payload['agente_ia_activo'] = 1 if agente_ia_activo.value else 0
                    ok, message = guardar_empresa(payload); ui.notify(fix_text(message), type='positive' if ok else 'negative')
                    if ok:
                        dialog_empresa.close()
                        ui.navigate.to('/empresas')
                with ui.row().classes('w-full justify-end gap-2 mt-4'):
                    ui.button('Cancelar', on_click=dialog_empresa.close).props('flat')
                    ui.button('Guardar empresa', icon='save', on_click=save_company).props('unelevated color=primary')
            def open_edit_company(company_id: int) -> None:
                company = next((item for item in companies if int(item['id']) == int(company_id)), None)
                if not company:
                    ui.notify('Esa empresa ya no existe en la base.', type='warning')
                    return
                with ui.dialog() as dialog, ui.card().classes('w-[980px] max-w-[96vw] p-6 rounded-[28px] ideas-panel overflow-y-auto').style('max-height: 92vh;'):
                    ui.label('Editar empresa').classes('text-2xl font-bold text-slate-900')
                    ui.label('Actualizá la ficha institucional sin salir del listado de empresas.').classes('ideas-section-note')
                    with ui.tabs().classes('w-full mt-3') as tabs_edit:
                        tab_datos_edit = ui.tab('Datos y Branding', icon='business')
                        tab_ai_edit = ui.tab('Base de Conocimiento IA', icon='psychology')
                    with ui.tab_panels(tabs_edit, value=tab_datos_edit).classes('w-full bg-transparent overflow-y-auto').style('max-height: 68vh;'):
                        with ui.tab_panel(tab_datos_edit).classes('w-full px-0'):
                            razon_social_edit = ui.input('Razón social', value=fix_text(company.get('razon_social', ''))).classes('w-full mt-2')
                            with ui.row().classes('w-full gap-4'):
                                ubicacion_edit = ui.input('Ubicación', value=fix_text(company.get('ubicacion', ''))).classes('col'); rubro_edit = ui.input('Rubro', value=fix_text(company.get('rubro', ''))).classes('col'); cantidad_empleados_edit = ui.number('Cantidad de empleados', value=int(company.get('cantidad_empleados') or 0), min=0, precision=0).classes('col')
                            ui.label('Persona de contacto').classes('text-lg font-semibold text-slate-800 mt-2')
                            with ui.row().classes('w-full gap-4'):
                                contacto_nombre_edit = ui.input('Nombre', value=fix_text(company.get('contacto_nombre', ''))).classes('col'); contacto_correo_edit = ui.input('Correo', value=fix_text(company.get('contacto_correo', ''))).classes('col')
                            with ui.row().classes('w-full gap-4'):
                                contacto_telefono_edit = ui.input('Teléfono', value=fix_text(company.get('contacto_telefono', ''))).classes('col'); contacto_posicion_edit = ui.input('Posición', value=fix_text(company.get('contacto_posicion', ''))).classes('col')
                            ui.label('Acceso de la empresa').classes('text-lg font-semibold text-slate-800 mt-2')
                            ui.label('La contraseña la define la empresa desde su enlace seguro.').classes('ideas-section-note')
                            def enviar_enlace_empresa_edit() -> None:
                                correo = str(contacto_correo_edit.value or '').strip()
                                nombre = str(razon_social_edit.value or '').strip() or str(company.get('razon_social') or 'Empresa')
                                if not correo:
                                    ui.notify('Ingresa un correo de contacto.', type='warning')
                                    return
                                if not (guardar_token_empresa and generar_token_seguro and enviar_correo_acceso):
                                    ui.notify('No se encontró la lógica de envío de acceso.', type='negative')
                                    return
                                token = generar_token_seguro()
                                ok = guardar_token_empresa(correo, token, expiracion_minutos=1440)
                                if not ok:
                                    ui.notify('No se pudo generar el enlace para este correo.', type='negative')
                                    return
                                enviar_correo_acceso(correo, nombre, token)
                                ui.notify('Enlace de acceso enviado correctamente.', type='positive')
                            with ui.row().classes('w-full justify-start'):
                                ui.button('Enviar enlace de acceso', icon='mail', on_click=enviar_enlace_empresa_edit).props('outline color=primary')
                            ui.label('Certificaciones').classes('text-lg font-semibold text-slate-800 mt-2')
                            with ui.row().classes('w-full gap-4'):
                                cert_9001_edit = ui.switch('ISO 9001', value='sí' in fix_text(company.get('cert_iso_9001', '')).lower()); cert_14001_edit = ui.switch('ISO 14001', value='sí' in fix_text(company.get('cert_iso_14001', '')).lower()); cert_45001_edit = ui.switch('ISO 45001', value='sí' in fix_text(company.get('cert_iso_45001', '')).lower()); cert_iatf_edit = ui.switch('IATF', value='sí' in fix_text(company.get('cert_iatf', '')).lower())
                            logo_temporal_edit = {'path': str(company.get('logo_path') or '')}
                            logo_preview_edit = ui.column().classes('w-full mt-3')
                            with logo_preview_edit:
                                ui.label('Logo de la empresa').classes('text-lg font-semibold text-slate-800')
                                if logo_temporal_edit['path']:
                                    ui.image(logo_url_from_path(logo_temporal_edit['path'])).classes('w-32 max-h-24 object-contain')
                                    ui.label(logo_temporal_edit['path']).classes('text-xs text-slate-500')
                                else:
                                    ui.label('Sin logo cargado.').classes('ideas-section-note')
                            async def handle_logo_upload_edit(event) -> None:
                                try:
                                    logo_temporal_edit['path'] = await save_company_logo(event, prefix=fix_text(razon_social_edit.value or 'empresa'))
                                    logo_preview_edit.clear()
                                    with logo_preview_edit:
                                        ui.label('Logo de la empresa').classes('text-lg font-semibold text-slate-800')
                                        ui.image(logo_url_from_path(logo_temporal_edit['path'])).classes('w-32 max-h-24 object-contain')
                                        ui.label(logo_temporal_edit['path']).classes('text-xs text-slate-500')
                                    ui.notify('Logo actualizado correctamente.', type='positive')
                                except Exception as exc:
                                    ui.notify(f'No se pudo cargar el logo: {exc}', type='negative')
                            ui.upload(label='Cambiar logo', auto_upload=True, on_upload=handle_logo_upload_edit).props('accept=".png,.jpg,.jpeg,.svg,.webp"').classes('w-full mt-2')
                            with ui.card().classes('w-full mt-4 p-4 border border-violet-200 bg-violet-50 shadow-none rounded-[20px]'):
                                ui.label('Copiloto IA').classes('text-lg font-semibold text-violet-900')
                                ui.label('Control comercial del acceso al copiloto IA para esta empresa.').classes('text-sm text-violet-700')
                                agente_ia_activo_edit = ui.switch('Habilitar Copiloto IA para esta empresa', value=bool(company.get('agente_ia_activo'))).classes('mt-3')
                            ui.label('Estilo visual del cliente').classes('text-lg font-semibold text-slate-800 mt-4')
                            with ui.row().classes('w-full gap-4'):
                                color_primario_edit = ui.color_input('Color primario', value=str(company.get('color_primario') or '#1f7ed6'), preview=True).classes('col')
                                color_secundario_edit = ui.color_input('Color secundario', value=str(company.get('color_secundario') or '#0f766e'), preview=True).classes('col')
                        with ui.tab_panel(tab_ai_edit).classes('w-full px-0'):
                            source_container = ui.column().classes('w-full')
                            render_sources_manager(source_container, int(company_id))
                    def save_edit_company() -> None:
                        payload = {'razon_social': razon_social_edit.value or '', 'ubicacion': ubicacion_edit.value or '', 'contacto_nombre': contacto_nombre_edit.value or '', 'contacto_correo': contacto_correo_edit.value or '', 'password': str(company.get('password') or ''), 'contacto_telefono': contacto_telefono_edit.value or '', 'contacto_posicion': contacto_posicion_edit.value or '', 'rubro': rubro_edit.value or '', 'cantidad_empleados': int(cantidad_empleados_edit.value or 0), 'cert_iso_9001': 'Sí' if cert_9001_edit.value else 'No', 'cert_iso_14001': 'Sí' if cert_14001_edit.value else 'No', 'cert_iso_45001': 'Sí' if cert_45001_edit.value else 'No', 'cert_iatf': 'Sí' if cert_iatf_edit.value else 'No'}
                        payload['logo_path'] = logo_temporal_edit['path']
                        payload['color_primario'] = color_primario_edit.value or ''
                        payload['color_secundario'] = color_secundario_edit.value or ''
                        payload['agente_ia_activo'] = 1 if agente_ia_activo_edit.value else 0
                        ok, message = actualizar_empresa(int(company_id), payload)
                        ui.notify(fix_text(message), type='positive' if ok else 'negative')
                        if ok:
                            dialog.close()
                            ui.navigate.to('/empresas')
                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat'); ui.button('Guardar cambios', icon='save', on_click=save_edit_company).props('unelevated color=primary')
                dialog.open()
            with ui.row().classes('w-full items-center justify-between gap-4 mt-4'):
                with ui.column().classes('gap-1'):
                    ui.label('Empresas registradas').classes('ideas-section-title')
                    ui.label('Gestiona clientes, branding y acceso al workspace desde una vista limpia y centralizada.').classes('ideas-section-note')
                ui.button('Nueva empresa', icon='add_business', on_click=dialog_empresa.open).props('unelevated color=primary')
            table_rows = [{'id': item['id'], 'razon_social': item['razon_social'], 'ubicacion': fix_text(item.get('ubicacion', '')), 'rubro': fix_text(item.get('rubro', '')), 'empleados': item.get('cantidad_empleados') or 0, 'contacto': fix_text(item.get('contacto_nombre', '')), 'certificaciones': certifications_summary(item), 'acciones': ''} for item in companies]
            table = ui.table(columns=[{'name': 'razon_social', 'label': 'Razón social', 'field': 'razon_social', 'align': 'left'}, {'name': 'ubicacion', 'label': 'Ubicación', 'field': 'ubicacion', 'align': 'left'}, {'name': 'rubro', 'label': 'Rubro', 'field': 'rubro', 'align': 'left'}, {'name': 'empleados', 'label': 'Empleados', 'field': 'empleados', 'align': 'right'}, {'name': 'contacto', 'label': 'Contacto', 'field': 'contacto', 'align': 'left'}, {'name': 'certificaciones', 'label': 'Certificaciones', 'field': 'certificaciones', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}], rows=table_rows, row_key='id', pagination=8).classes('w-full ideas-panel ideas-table p-3 mt-4')
            table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="edit" color="secondary" @click="$parent.$emit('edit_company', props.row.id)" /><q-btn flat round dense icon="account_tree" color="primary" @click="$parent.$emit('open_workspace', props.row.id)" /><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_company', props.row.id)" /></div></q-td>''')
            table.on('edit_company', lambda event: open_edit_company(int(event.args)))
            table.on('open_workspace', lambda event: go_to_management_workspace(int(event.args), set_selection))
            def confirm_delete_company(company_id: int) -> None:
                company = next((item for item in companies if int(item['id']) == int(company_id)), None)
                if not company:
                    ui.notify('Esa empresa ya no existe en la base.', type='warning')
                    return
                current_company_id, _current_diag_id = current_selection()
                with ui.dialog() as dialog, ui.card().classes('p-5 max-w-[580px]'):
                    ui.label('Eliminar empresa').classes('text-lg font-semibold')
                    ui.label(f"Se eliminara permanentemente {fix_text(company['razon_social'])} junto con todos sus diagnosticos, respuestas y datos del sistema de gestion. Esta accion no se puede deshacer.").classes('text-slate-600')
                    with ui.row().classes('w-full justify-end gap-2 mt-3'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat')
                        def do_delete() -> None:
                            eliminar_empresa(int(company_id))
                            if current_company_id and int(current_company_id) == int(company_id):
                                set_selection(None, None)
                                app.storage.user['history_selected_id'] = None
                            dialog.close()
                            ui.notify('Empresa eliminada permanentemente junto con todos sus datos asociados.', type='positive')
                            ui.navigate.to('/empresas')
                        ui.button('Eliminar permanentemente', color='negative', on_click=do_delete)
                dialog.open()
            table.on('delete_company', lambda event: confirm_delete_company(int(event.args)))

    @ui.page('/diagnostico')
    def diagnostic_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Nuevo Diagnóstico'); df_base = leer_diagnostico_excel().copy(); grouped = grouped_questions(df_base); criteria, regla = load_criteria(); company_map = company_options()
        score_labels = {1: '1 · Inicial', 2: '2 · Parcial', 3: '3 · Implementado', 4: '4 · Estandarizado'}
        edit_id, duplicate_id = app.storage.user.get('edit_diag_id'), app.storage.user.get('duplicate_diag_id')
        preload_id = int(edit_id or duplicate_id) if (edit_id or duplicate_id) else None; preload = diagnosis_record(preload_id); preload_responses = diagnosis_response_dicts(preload_id); preload_map = {(row['eje'], row['pregunta']): row for row in preload_responses}
        with shell_container:
            ui.label('Nuevo diagnóstico').classes('ideas-kicker'); ui.label('Captura estructurada para análisis ejecutivo.').classes('text-3xl font-bold text-slate-900'); ui.label('Registrá cada eje con una evaluación consistente y evidencia asociada para sostener la lectura consultiva posterior.').classes('ideas-subtitle')
            if preload and edit_id: ui.html(f'<div class="ideas-mode-banner">Modo edición<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Estás actualizando un diagnóstico ya registrado.</div>')
            elif preload and duplicate_id: ui.html(f'<div class="ideas-mode-banner">Duplicar como nuevo<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Tomás un corte previo como base para crear una nueva evaluación.</div>')
            with ui.card().classes('ideas-panel w-full mt-4'):
                guide_html = ''.join(f'''<div class="ideas-score-item"><div class="badge">{int(item['escala'])}</div><div style="margin-top:10px;font-weight:800;color:#0f172a;">{fix_text(item['nivel'])}</div><div style="margin-top:8px;color:#475569;line-height:1.55;">{fix_text(item['resumen'])}</div></div>''' for item in criteria)
                ui.label('Criterios de puntuación').classes('text-lg font-semibold text-slate-900'); ui.html(f'<div class="ideas-score-guide mt-3">{guide_html}</div>'); ui.label(f'Regla de evidencia: {fix_text(regla)}').classes('text-sm text-amber-700 mt-3')
            default_company = preload['empresa_id'] if preload else (current_selection()[0] or None); company_select = ui.select(company_map, value=default_company, label='Empresa').classes('w-full mt-5').props('outlined')
            response_inputs, evidence_inputs, evidence_containers, observation_inputs = {}, {}, {}, {}
            def ensure_evidence_fields(key):
                fields = evidence_inputs[key]; values = [fix_text(field.value).strip() for field in fields]
                if values and values[-1] != '':
                    with evidence_containers[key]: new_field = ui.input(f'Evidencia {len(fields) + 1}').classes('w-full').props('outlined')
                    fields.append(new_field); new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key)); return
                for index in reversed([i for i, value in enumerate(values[:-1]) if value == '']): fields.pop(index).delete()
                if not fields:
                    with evidence_containers[key]: new_field = ui.input('Evidencia 1').classes('w-full').props('outlined')
                    fields.append(new_field); new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
            for eje, questions in grouped.items():
                with ui.expansion(fix_text(eje), icon='schema').classes('w-full ideas-card mt-4'):
                    for question in questions:
                        key, existing = (eje, question), preload_map.get((eje, question), {})
                        with ui.card().classes('ideas-soft w-full p-4 mb-3'):
                            ui.label(question).classes('text-base font-semibold text-slate-900')
                            response_inputs[key] = ui.select({value: f"{label} · {fix_text(next((c['resumen'] for c in criteria if int(c['escala']) == value), ''))}" for value, label in score_labels.items()}, value=int(existing.get('respuesta', 3)), label='Puntaje').classes('w-full mt-3').props('outlined')
                            with ui.row().classes('w-full gap-4 mt-2'):
                                evidence_containers[key] = ui.column().classes('col w-full gap-2'); observation_inputs[key] = ui.textarea('Observación').classes('col w-full').props('outlined autogrow')
                            evidence_inputs[key] = []; preload_evidences = split_evidence_values(existing.get('evidencia', ''))
                            with evidence_containers[key]:
                                for idx, evidence_value in enumerate(preload_evidences, start=1):
                                    field = ui.input(f'Evidencia {idx}').classes('w-full').props('outlined'); field.value = evidence_value; evidence_inputs[key].append(field)
                                if not preload_evidences or preload_evidences[-1].strip() != '':
                                    evidence_inputs[key].append(ui.input(f'Evidencia {len(evidence_inputs[key]) + 1}').classes('w-full').props('outlined'))
                            for field in evidence_inputs[key]: field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
                            ensure_evidence_fields(key); observation_inputs[key].value = existing.get('observacion', '')
            def save_diagnosis() -> None:
                if not company_select.value: ui.notify('Seleccioná una empresa antes de guardar.', type='warning'); return
                rows = [{'eje': eje, 'pregunta': question, 'respuesta': int(selector.value or 1), 'evidencia': ', '.join([fix_text(field.value).strip() for field in evidence_inputs[(eje, question)] if fix_text(field.value).strip()]), 'observacion': observation_inputs[(eje, question)].value or ''} for (eje, question), selector in response_inputs.items()]
                score = round(sum(item['respuesta'] for item in rows) / len(rows), 2) if rows else 0; nivel = obtener_nivel(score); conclusion = fix_text(obtener_conclusion(score)); empresa_id = int(company_select.value)
                if edit_id:
                    diag_id, _fecha, unchanged = actualizar_diagnostico(int(edit_id), empresa_id, score, nivel, conclusion, rows); ui.notify('No se detectaron cambios; el diagnóstico ya estaba actualizado.' if unchanged else 'Diagnóstico actualizado correctamente.', type='positive')
                else:
                    diag_id, _fecha, duplicated = guardar_diagnostico(empresa_id, score, nivel, conclusion, rows); ui.notify('Ese diagnóstico ya estaba guardado; se reutilizó el corte existente.' if duplicated else 'Diagnóstico guardado correctamente.', type='positive')
                app.storage.user['edit_diag_id'] = None; app.storage.user['duplicate_diag_id'] = None; set_selection(empresa_id, diag_id); ui.navigate.to('/resultados')
            with ui.row().classes('w-full justify-end gap-3 mt-6'):
                ui.button('Cancelar', icon='close', on_click=lambda: ui.navigate.to('/historial')).props('outline'); ui.button('Guardar diagnóstico', icon='save', on_click=save_diagnosis).props('unelevated color=primary')

    @ui.page('/resultados')
    def results_page() -> None:
        if not ensure_platform_access():
            return
        shell_container = shell('Resultados del Diagnóstico')
        empresa_id, diag_id = current_selection()
        companies = company_options()
        if not empresa_id and companies:
            empresa_id = next(iter(companies.keys()))
        diag_map = diagnosis_options(empresa_id)
        if not diag_id and diag_map:
            diag_id = next(iter(diag_map.keys()))
        if diag_id:
            set_selection(empresa_id, diag_id)

        with shell_container:
            with ui.card().classes('ideas-panel w-full'):
                with ui.row().classes('w-full gap-4'):
                    company_select = ui.select(companies, value=empresa_id, label='Empresa').classes('col').props('outlined')
                    diagnosis_select = ui.select(diag_map, value=diag_id, label='Diagnóstico').classes('col').props('outlined')

            company_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, None), ui.navigate.to('/resultados')))
            diagnosis_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, int(diagnosis_select.value) if diagnosis_select.value else None), ui.navigate.to('/resultados')))

            if not diag_id:
                with ui.card().classes('ideas-panel w-full mt-6'):
                    ui.label('Todavía no hay un diagnóstico seleccionado.').classes('ideas-section-title')
                    ui.label('Selecciona un corte desde historial para abrir el dashboard ejecutivo del diagnóstico.').classes('ideas-section-note')
                    with ui.row().classes('w-full justify-center mt-4'):
                        ui.button('Volver al historial', icon='history', on_click=lambda: ui.navigate.to('/historial')).props('unelevated color=primary')
                return

            diag = diagnosis_record(diag_id)
            if not diag:
                with ui.card().classes('ideas-panel w-full mt-6'):
                    ui.label('No se encontró el diagnóstico seleccionado.').classes('ideas-section-title')
                    ui.label('Puede haber sido eliminado o ya no estar disponible en la base.').classes('ideas-section-note')
                    with ui.row().classes('w-full justify-center mt-4'):
                        ui.button('Volver al historial', icon='history', on_click=lambda: ui.navigate.to('/historial')).props('unelevated color=primary')
                return

            respuestas = diagnosis_response_dicts(diag_id)
            df_resp, eje_scores_df = build_eje_scores(respuestas)
            plan_df = build_plan(df_resp, eje_scores_df)
            prioridad_alta = int((plan_df['prioridad'] == 'Alta').sum()) if not plan_df.empty and 'prioridad' in plan_df.columns else 0
            nivel = fix_text(diag.get('nivel', 'Sin nivel'))
            conclusion = fix_text(diag.get('conclusion', '')) or fix_text(obtener_mensaje_direccion(nivel))

            async def export_results_pdf() -> None:
                try:
                    company_info = obtener_empresa_detalle(int(diag.get('empresa_id') or empresa_id)) or {}
                    eje_scores = {
                        str(row['EJE']): float(row['RESPUESTA'])
                        for row in eje_scores_df.to_dict('records')
                    } if not eje_scores_df.empty else {}
                    criticas = []
                    if not plan_df.empty and 'accion' in plan_df.columns:
                        criticas = [fix_text(item) for item in plan_df['accion'].head(8).tolist()]
                    pdf_path = generar_pdf_ejecutivo_v2(
                        fix_text(diag.get('empresa', company_info.get('razon_social', 'Empresa'))),
                        fix_text(diag.get('fecha', 'Sin fecha')),
                        float(diag.get('score', 0) or 0),
                        nivel,
                        conclusion,
                        eje_scores,
                        criticas,
                        company_info,
                    )
                    ui.download(str(pdf_path))
                except Exception as exc:
                    ui.notify(f'No se pudo generar el PDF: {exc}', type='negative')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button(
                    'Exportar PDF',
                    icon='picture_as_pdf',
                    color='red-8',
                    on_click=export_results_pdf,
                ).props('unelevated')

            ui.html(
                f'''
                <div class="ideas-result-banner mt-6">
                    <div class="eyebrow">RESULTADOS DEL DIAGNÓSTICO</div>
                    <div class="headline">{fix_text(diag.get('empresa', 'Sin empresa'))} - Nivel {nivel}</div>
                    <div class="support">{conclusion}</div>
                </div>
                '''
            )

            ui.html(
                f'''
                <div class="ideas-grid-3" style="margin-top:24px;">
                    {quick_card('SCORE GLOBAL', f"{float(diag.get('score', 0)):.2f}", 'Síntesis cuantitativa del corte seleccionado.')}
                    {quick_card('NIVEL DE MADUREZ', nivel, 'Lectura consolidada del estado de desarrollo actual.')}
                    {quick_card('ACCIONES PRIORITARIAS', str(prioridad_alta), 'Brechas críticas priorizadas para intervención inmediata.')}
                </div>
                '''
            )

            radar_labels = eje_scores_df['EJE'].tolist() if not eje_scores_df.empty else []
            radar_values = [float(value) for value in eje_scores_df['RESPUESTA'].tolist()] if not eje_scores_df.empty else []
            if radar_labels and radar_values:
                radar_theta = radar_labels + [radar_labels[0]]
                radar_radius = radar_values + [radar_values[0]]
            else:
                radar_theta = ['Sin datos']
                radar_radius = [0]

            radar_fig = go.Figure(
                data=go.Scatterpolar(
                    r=radar_radius,
                    theta=radar_theta,
                    fill='toself',
                    line=dict(color='#1f7ed6', width=3),
                    fillcolor='rgba(31,126,214,0.18)',
                    marker=dict(color='#1f7ed6', size=7),
                    hovertemplate='%{theta}<br>Score: %{r:.2f}<extra></extra>',
                    name='Madurez',
                )
            )
            radar_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                showlegend=False,
                polar=dict(
                    bgcolor='rgba(0,0,0,0)',
                    radialaxis=dict(visible=True, range=[0, 4], tickvals=[1, 2, 3, 4], gridcolor='rgba(148,163,184,0.24)'),
                    angularaxis=dict(gridcolor='rgba(148,163,184,0.16)', tickfont=dict(size=11)),
                ),
            )

            críticos_df = eje_scores_df.sort_values('RESPUESTA', ascending=True).head(5).sort_values('RESPUESTA', ascending=True) if not eje_scores_df.empty else pd.DataFrame(columns=['EJE', 'RESPUESTA'])
            critical_fig = go.Figure(
                data=go.Bar(
                    x=críticos_df['RESPUESTA'] if not críticos_df.empty else [],
                    y=críticos_df['EJE'] if not críticos_df.empty else [],
                    orientation='h',
                    marker=dict(color='#f59e0b'),
                    text=[f'{float(value):.2f}' for value in críticos_df['RESPUESTA'].tolist()] if not críticos_df.empty else [],
                    textposition='outside',
                    hovertemplate='%{y}<br>Score: %{x:.2f}<extra></extra>',
                )
            )
            critical_fig.update_layout(
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                margin=dict(l=20, r=20, t=30, b=20),
                xaxis=dict(range=[0, 4], title='Score'),
                yaxis=dict(autorange='reversed'),
            )

            with ui.grid(columns=2).classes('ideas-grid-2 w-full mt-6'):
                with ui.card().classes('ideas-panel'):
                    ui.label('Balance de Madurez por Eje').classes('ideas-section-title')
                    ui.label('Vista integral del equilibrio y desempeño relativo de cada eje del diagnóstico.').classes('ideas-section-note')
                    ui.plotly(radar_fig).classes('w-full h-64')

                with ui.card().classes('ideas-panel'):
                    ui.label('Áreas Críticas de Mejora').classes('ideas-section-title')
                    ui.label('Top 5 de ejes con menor puntaje para orientar la intervención ejecutiva.').classes('ideas-section-note')
                    ui.plotly(critical_fig).classes('w-full h-64')

            with ui.card().classes('ideas-panel w-full mt-6'):
                ui.label('Plan de Acción Ejecutivo').classes('ideas-section-title')
                ui.label('Principales acciones priorizadas según las brechas detectadas.').classes('ideas-section-note')
                columns = [
                    {'name': 'area', 'label': 'Área / Eje', 'field': 'area', 'align': 'left'},
                    {'name': 'accion', 'label': 'Acción Requerida', 'field': 'accion', 'align': 'left'},
                    {'name': 'prioridad', 'label': 'Prioridad', 'field': 'prioridad', 'align': 'center'},
                    {'name': 'plazo', 'label': 'Plazo Sugerido', 'field': 'plazo', 'align': 'left'},
                ]
                rows = plan_df.to_dict('records') if not plan_df.empty else []
                action_table = ui.table(columns=columns, rows=rows, pagination={'rowsPerPage': 5}).classes('w-full ideas-table mt-4')
                action_table.props('flat bordered')
                action_table.add_slot('body-cell-prioridad', '''
                <q-td :props="props">
                    <q-badge :color="props.value === 'Alta' ? 'negative' : (props.value === 'Media' ? 'warning' : 'primary')" rounded>
                        {{ props.value }}
                    </q-badge>
                </q-td>
                ''')

            with ui.row().classes('w-full justify-center mt-6'):
                ui.button(
                    'Descargar Reporte Ejecutivo (PDF)',
                    icon='download',
                    on_click=lambda: ui.notify('La descarga del PDF ejecutivo quedará conectada en el siguiente paso.', type='info'),
                ).props('unelevated color=primary size=lg')

    @ui.page('/historial')
    def history_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Historial'); rows = diagnosis_rows(); app.storage.user['history_selected_id'] = None
        with shell_container:
            ui.label('Historial').classes('ideas-kicker'); ui.label('Overview rápido de la base de diagnósticos.').classes('text-3xl font-bold text-slate-900'); ui.label('Consultá cada corte, actuá sobre el registro y accedé a la información relevante sin ruido visual.').classes('ideas-subtitle mb-4')
            empresas_con_evolucion = len({row['empresa'] for row in rows if sum(1 for item in rows if item['empresa'] == row['empresa']) > 1})
            render_metrics(ui.row().classes('w-full'), [('Empresas registradas', str(len({row['empresa_id'] for row in rows})), 'Universo visible en la base consultiva.'), ('Diagnósticos visibles', str(len(rows)), 'Cortes disponibles para consulta o edición.'), ('Empresas con evolución', str(empresas_con_evolucion), 'Casos con más de un corte registrado.')])
            columns = [{'name': 'empresa', 'label': 'Empresa', 'field': 'empresa', 'align': 'left'}, {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'}, {'name': 'score', 'label': 'Score', 'field': 'score', 'align': 'right'}, {'name': 'nivel', 'label': 'Nivel', 'field': 'nivel', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}]
            table_rows = [{'id': row['id'], 'empresa_id': row['empresa_id'], 'empresa': row['empresa'], 'fecha': row['fecha'], 'score': f"{row['score']:.2f}", 'nivel': row['nivel'], 'acciones': ''} for row in rows]
            table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=10).classes('w-full ideas-card ideas-table p-3 mt-4'); table.props('flat bordered')
            table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="visibility" color="primary" @click="$parent.$emit('open_resultados', props.row.id)" /><q-btn flat round dense icon="edit" color="secondary" @click="$parent.$emit('edit_diag', props.row.id)" /><q-btn flat round dense icon="content_copy" color="amber-8" @click="$parent.$emit('duplicate_diag', props.row.id)" /><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_diag', props.row.id)" /></div></q-td>''')
            detail_card = ui.card().classes('ideas-panel w-full mt-4')
            def extract_diag_id(args):
                if args is None: return None
                if isinstance(args, dict):
                    if 'id' in args:
                        try: return int(args['id'])
                        except Exception: return None
                    if 'row' in args: return extract_diag_id(args['row'])
                    return None
                if isinstance(args, (list, tuple)):
                    for item in args:
                        diag_id = extract_diag_id(item)
                        if diag_id is not None: return diag_id
                    return None
                try: return int(args)
                except Exception: return None
            def render_detail(diag_id):
                detail_card.clear(); diag = diagnosis_record(diag_id) if diag_id else None
                if not diag:
                    with detail_card:
                        ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title'); ui.label('Haz click en una fila de la lista superior para visualizar aquí el resumen del diagnóstico y los datos de la empresa.').classes('text-slate-500'); ui.html('''<div class="ideas-grid-2" style="margin-top:18px;"><div class="ideas-quick-card"><div class="label">Ficha de empresa</div><div class="detail">Razón social: -</div><div class="detail">Ubicación: -</div><div class="detail">Rubro: -</div><div class="detail">Empleados: -</div></div><div class="ideas-quick-card"><div class="label">Resumen consultivo</div><div class="detail">Puntos fuertes: -</div><div class="detail">Áreas débiles: -</div><div class="detail">Contacto: -</div><div class="detail">Certificaciones: -</div></div></div>''')
                    return
                app.storage.user['history_selected_id'] = int(diag['id']); company = obtener_empresa_detalle(diag['empresa_id']); responses = diagnosis_response_dicts(diag['id']); df_resp = pd.DataFrame(responses)
                strengths = ', '.join(df_resp[df_resp['respuesta'] >= 3]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'; weaknesses = ', '.join(df_resp[df_resp['respuesta'] <= 2]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'
                with detail_card:
                    ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title'); ui.label(f"{diag['empresa']} · {diag['fecha']}").classes('text-slate-500'); ui.html(f'<div style="margin-top:12px;display:inline-flex;padding:10px 14px;border-radius:999px;font-weight:800;{diagnosis_badge_style(diag["nivel"])}">Nivel {diag["nivel"]} · Score {diag["score"]:.2f}</div>'); ui.html(f'''<div class="ideas-grid-2" style="margin-top:18px;"><div class="ideas-quick-card"><div class="label">Ficha de empresa</div><div class="detail">Razón social: {fix_text(company.get('razon_social', diag['empresa'])) if company else diag['empresa']}</div><div class="detail">Ubicación: {fix_text(company.get('ubicacion', '')) if company else ''}</div><div class="detail">Rubro: {fix_text(company.get('rubro', '')) if company else ''}</div><div class="detail">Empleados: {company.get('cantidad_empleados', 0) if company else 0}</div></div><div class="ideas-quick-card"><div class="label">Resumen consultivo</div><div class="detail">Puntos fuertes: {fix_text(strengths)}</div><div class="detail">Áreas débiles: {fix_text(weaknesses)}</div><div class="detail">Contacto: {fix_text(company.get('contacto_nombre', '')) if company else ''}</div><div class="detail">Certificaciones: {certifications_summary(company)}</div></div></div>''')
            render_detail(None)
            table.on('rowClick', lambda event: render_detail(extract_diag_id(event.args)))
            table.on('open_resultados', lambda event: (set_selection(diagnosis_record(int(event.args))['empresa_id'], int(event.args)), ui.navigate.to('/resultados')) if diagnosis_record(int(event.args)) else ui.notify('No se encontró ese diagnóstico.', type='warning'))
            table.on('edit_diag', lambda event: (start_edit(int(event.args), duplicate=False), ui.navigate.to('/diagnostico')))
            table.on('duplicate_diag', lambda event: (start_edit(int(event.args), duplicate=True), ui.navigate.to('/diagnostico')))
            def confirm_delete(diag_id: int) -> None:
                diag = diagnosis_record(diag_id)
                if not diag: ui.notify('Ese diagnóstico ya no existe.', type='warning'); return
                with ui.dialog() as dialog, ui.card().classes('p-5'):
                    ui.label('Eliminar diagnóstico').classes('text-lg font-semibold'); ui.label(f"Se eliminará {diag['empresa']} · {diag['fecha']} y también sus respuestas.").classes('text-slate-600')
                    with ui.row().classes('w-full justify-end gap-2 mt-3'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat'); ui.button('Eliminar', color='negative', on_click=lambda: (eliminar_diagnostico(diag_id), dialog.close(), ui.notify('Diagnóstico eliminado correctamente.', type='positive'), ui.navigate.to('/historial')))
                dialog.open()
            table.on('delete_diag', lambda event: confirm_delete(int(event.args)))
