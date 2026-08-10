from __future__ import annotations

import datetime
from pathlib import Path

from nicegui import app, events, ui
from dashboard_customizer import render_dashboard_customizer
from company_context import empresa_id_from_query_for_admin, with_empresa_id


UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'uploads' / 'ambiental'
LEGAL_STATUS_COLORS = {
    'cumple': 'positive',
    'en proceso': 'warning',
    'no cumple': 'negative',
}
LEGAL_JURISDICTION_COLORS = {
    'nacional': 'primary',
    'provincial': 'positive',
    'municipal': 'grey-7',
}


def go_to_environment_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/ambiental', company_id))


def _extract_int(value) -> int | None:
    try:
        return int(value)
    except Exception:
        pass
    if isinstance(value, dict):
        for key in ('id', 'row'):
            found = _extract_int(value.get(key))
            if found is not None:
                return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_int(item)
            if found is not None:
                return found
    return None


def _parse_date(value: str) -> datetime.date | None:
    text = str(value or '').strip()
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(text, fmt).date()
        except Exception:
            continue
    return None


def _process_options(rows: list[dict], fix_text_fn) -> dict[str, str]:
    return {
        fix_text_fn(row.get('proceso_nombre') or '').strip(): fix_text_fn(row.get('proceso_nombre') or '').strip()
        for row in rows
        if fix_text_fn(row.get('proceso_nombre') or '').strip()
    }


def _save_uploaded_file(company_id: int, event: events.UploadEventArguments) -> str:
    target_dir = UPLOAD_DIR / f'empresa_{company_id}'
    target_dir.mkdir(parents=True, exist_ok=True)
    file_name = Path(event.name).name
    target_path = target_dir / file_name
    target_path.write_bytes(event.content.read())
    return str(target_path)


def _show_aspect_dialog(ui, *, row, company_id: int, process_options: dict[str, str], fix_text_fn, crear_fn, actualizar_fn) -> None:
    is_edit = bool(row)
    current_process = fix_text_fn(row.get('proceso_nombre', '')) if row else ''
    options = dict(process_options)
    if current_process and current_process not in options:
        options[current_process] = current_process

    with ui.dialog() as dialog, ui.card().classes('w-[980px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
        ui.label('Editar aspecto ambiental' if is_edit else 'Nuevo aspecto ambiental').classes('text-2xl font-bold text-slate-900')
        ui.label('El proceso se selecciona desde el mapa real de la empresa para asegurar coherencia entre operación e identificación ambiental.').classes('ideas-section-note')
        if not options:
            ui.label('No hay procesos mapeados para esta empresa. Primero debes cargarlos en Mapas de proceso.').classes('text-amber-700 mt-3')
            ui.button('Cerrar', on_click=dialog.close).props('unelevated color=primary').classes('mt-3')
            dialog.open()
            return

        with ui.row().classes('w-full gap-4 mt-4'):
            process_input = ui.select(options, value=current_process or None, label='Proceso').classes('col').props('outlined use-input fill-input')
            condition_input = ui.select(['Normal', 'Anormal', 'Emergencia'], value=fix_text_fn(row.get('condicion', '')) if row else 'Normal', label='Condición').classes('col').props('outlined')
            significance_input = ui.select({0: 'No significativo', 1: 'Significativo'}, value=int(row.get('significancia') or 0) if row else 0, label='Significancia').classes('col').props('outlined')
        activity_input = ui.input('Actividad', value=fix_text_fn(row.get('actividad', '')) if row else '').classes('w-full mt-3').props('outlined')
        aspect_input = ui.input('Aspecto', value=fix_text_fn(row.get('aspecto', '')) if row else '').classes('w-full mt-3').props('outlined')
        impact_input = ui.textarea('Impacto', value=fix_text_fn(row.get('impacto', '')) if row else '').classes('w-full mt-3').props('outlined autogrow')
        control_input = ui.textarea('Control operacional', value=fix_text_fn(row.get('control_operacional', '')) if row else '').classes('w-full mt-3').props('outlined autogrow')

        def save() -> None:
            args = (
                process_input.value or '',
                activity_input.value or '',
                aspect_input.value or '',
                impact_input.value or '',
                condition_input.value or '',
                int(significance_input.value or 0),
                control_input.value or '',
            )
            ok, message = actualizar_fn(int(row['id']), *args) if is_edit else crear_fn(int(company_id), *args)
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                dialog.close()
                ui.navigate.to('/sistema-gestion/ambiental')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', icon='save', on_click=save).props('unelevated color=primary')
    dialog.open()


def _show_legal_dialog(ui, *, row, company_id: int, fix_text_fn, crear_fn, actualizar_fn) -> None:
    is_edit = bool(row)
    with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
        ui.label('Editar requisito legal' if is_edit else 'Nuevo requisito legal').classes('text-2xl font-bold text-slate-900')
        jurisdiction_input = ui.select(
            ['Nacional', 'Provincial', 'Municipal'],
            value=fix_text_fn(row.get('jurisdiccion', '')) if row else 'Nacional',
            label='Jurisdicción',
        ).classes('w-full mt-4').props('outlined')
        norm_input = ui.input('Norma legal', value=fix_text_fn(row.get('norma_legal', '')) if row else '').classes('w-full mt-3').props('outlined')
        article_input = ui.input('Artículo aplicable', value=fix_text_fn(row.get('articulo_aplicable', '')) if row else '').classes('w-full mt-3').props('outlined')
        with ui.row().classes('w-full gap-4 mt-3'):
            status_input = ui.select(['Cumple', 'En Proceso', 'No Cumple'], value=fix_text_fn(row.get('estado_cumplimiento', '')) if row else 'En Proceso', label='Estado').classes('col').props('outlined')
            due_input = ui.input('Fecha de vencimiento', value=fix_text_fn(row.get('fecha_vencimiento', '')) if row else '', placeholder='dd.mm.aaaa').classes('col').props('outlined')
            owner_input = ui.input('Responsable', value=fix_text_fn(row.get('responsable', '')) if row else '').classes('col').props('outlined')

        def save() -> None:
            args = (
                jurisdiction_input.value or 'Nacional',
                norm_input.value or '',
                article_input.value or '',
                status_input.value or '',
                due_input.value or '',
                owner_input.value or '',
            )
            ok, message = actualizar_fn(int(row['id']), *args) if is_edit else crear_fn(int(company_id), *args)
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                dialog.close()
                ui.navigate.to('/sistema-gestion/ambiental')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar', icon='save', on_click=save).props('unelevated color=primary')
    dialog.open()


def _show_ia_suggestions_dialog(ui, *, suggestions: list[dict], guardar_fn, company_id: int, fix_text_fn) -> None:
    selected = {str(index): True for index, _ in enumerate(suggestions)}
    grouped: dict[str, list[tuple[int, dict]]] = {'Nacional': [], 'Provincial': [], 'Municipal': []}
    for index, item in enumerate(suggestions):
        jurisdiccion = fix_text_fn(item.get('jurisdiccion') or 'Nacional').title()
        grouped.setdefault(jurisdiccion, []).append((index, item))
    with ui.dialog() as dialog, ui.card().classes('w-[980px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
        ui.label('Sugerencias de legislación ambiental').classes('text-2xl font-bold text-slate-900')
        ui.label('Selecciona las normas pertinentes para incorporarlas a la matriz legal de la empresa.').classes('ideas-section-note')
        for jurisdiccion in ('Nacional', 'Provincial', 'Municipal'):
            items = grouped.get(jurisdiccion, [])
            if not items:
                continue
            with ui.column().classes('w-full gap-2 mt-4'):
                with ui.row().classes('items-center gap-3'):
                    ui.label(jurisdiccion).classes('text-lg font-bold text-slate-900')
                    ui.badge(jurisdiccion).props(f"color={LEGAL_JURISDICTION_COLORS.get(jurisdiccion.lower(), 'primary')}")
                for index, item in items:
                    with ui.card().classes('w-full p-4 rounded-[22px] border border-slate-200 shadow-none'):
                        with ui.row().classes('w-full items-start gap-3 no-wrap'):
                            check = ui.checkbox(value=True)
                            check.bind_value(selected, str(index))
                            with ui.column().classes('gap-1'):
                                with ui.row().classes('items-center gap-2'):
                                    ui.label(fix_text_fn(item.get('norma_legal') or '')).classes('font-bold text-slate-900')
                                    ui.badge(jurisdiccion).props(f"color={LEGAL_JURISDICTION_COLORS.get(jurisdiccion.lower(), 'primary')}")
                                ui.label(fix_text_fn(item.get('articulo_aplicable') or '')).classes('text-slate-600')

        def save_selected() -> None:
            saved = 0
            skipped = 0
            for index, item in enumerate(suggestions):
                if not selected.get(str(index)):
                    continue
                ok, _message = guardar_fn(
                    int(company_id),
                    item.get('jurisdiccion') or 'Nacional',
                    item.get('norma_legal') or '',
                    item.get('articulo_aplicable') or '',
                    'En Proceso',
                    '',
                    '',
                )
                if ok:
                    saved += 1
                else:
                    skipped += 1
            if saved and skipped:
                ui.notify(
                    f'Se guardaron {saved} requisitos legales y se omitieron {skipped} duplicados.',
                    type='positive',
                )
            elif saved:
                ui.notify(f'Se guardaron {saved} requisitos legales.', type='positive')
            elif skipped:
                ui.notify(
                    f'No se agregaron nuevas normas. Se omitieron {skipped} duplicados existentes.',
                    type='warning',
                )
            else:
                ui.notify('No se seleccionaron normas para guardar.', type='warning')
            dialog.close()
            ui.navigate.to('/sistema-gestion/ambiental')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar seleccionadas', icon='save', on_click=save_selected).props('unelevated color=primary')
    dialog.open()


def _show_simulacro_dialog(ui, *, row, company_id: int, fix_text_fn, crear_fn, actualizar_fn) -> None:
    is_edit = bool(row)
    uploaded_paths = [part.strip() for part in str((row or {}).get('archivos_path') or '').split(',') if part.strip()]

    with ui.dialog() as dialog, ui.card().classes('w-[1000px] max-w-[97vw] p-6 rounded-[28px] ideas-panel'):
        ui.label('Editar simulacro' if is_edit else 'Nuevo simulacro').classes('text-2xl font-bold text-slate-900')
        ui.label('Documenta el escenario, participantes, conclusiones y evidencias visuales del ejercicio ambiental.').classes('ideas-section-note')
        scenario_input = ui.input('Escenario', value=fix_text_fn((row or {}).get('escenario', ''))).classes('w-full mt-4').props('outlined')
        with ui.row().classes('w-full gap-4 mt-3'):
            date_input = ui.input('Fecha del simulacro', value=fix_text_fn((row or {}).get('fecha_simulacro', '')), placeholder='dd.mm.aaaa').classes('col').props('outlined')
            participants_input = ui.input('Participantes', value=fix_text_fn((row or {}).get('participantes', ''))).classes('col').props('outlined')
            effective_input = ui.switch('Respuesta eficaz', value=bool((row or {}).get('respuesta_eficaz'))).classes('col mt-4')
        conclusions_input = ui.textarea('Conclusiones y mejora', value=fix_text_fn((row or {}).get('conclusiones_mejora', ''))).classes('w-full mt-3').props('outlined autogrow')
        files_preview = ui.column().classes('w-full gap-2 mt-3')

        def refresh_files() -> None:
            files_preview.clear()
            with files_preview:
                if uploaded_paths:
                    for path in uploaded_paths:
                        ui.label(path).classes('text-sm text-slate-600')
                else:
                    ui.label('Sin archivos cargados.').classes('text-sm text-slate-500')

        def on_upload(event: events.UploadEventArguments) -> None:
            path = _save_uploaded_file(company_id, event)
            uploaded_paths.append(path)
            refresh_files()
            ui.notify(f'Archivo cargado: {Path(path).name}', type='positive')

        ui.upload(
            on_upload=on_upload,
            multiple=True,
            auto_upload=True,
            label='Adjuntar imágenes del simulacro',
        ).props('accept=.png,.jpg,.jpeg').classes('w-full mt-3')
        refresh_files()

        def save() -> None:
            args = (
                scenario_input.value or '',
                date_input.value or '',
                participants_input.value or '',
                bool(effective_input.value),
                conclusions_input.value or '',
                ','.join(uploaded_paths),
            )
            ok, message = actualizar_fn(int(row['id']), *args) if is_edit else crear_fn(int(company_id), *args)
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                dialog.close()
                ui.navigate.to('/sistema-gestion/ambiental')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar simulacro', icon='save', on_click=save).props('unelevated color=primary')
    dialog.open()


def register_environment_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    obtener_mapa_procesos_empresa = deps['obtener_mapa_procesos_empresa']
    fix_text = deps['fix_text']
    render_metrics = deps['render_metrics']
    quick_card = deps['quick_card']
    obtener_aspectos_ambientales_empresa = deps['obtener_aspectos_ambientales_empresa']
    crear_aspecto_ambiental = deps['crear_aspecto_ambiental']
    actualizar_aspecto_ambiental = deps['actualizar_aspecto_ambiental']
    eliminar_aspecto_ambiental = deps['eliminar_aspecto_ambiental']
    obtener_requisitos_legales_ambientales_empresa = deps['obtener_requisitos_legales_ambientales_empresa']
    crear_requisito_legal_ambiental = deps['crear_requisito_legal_ambiental']
    actualizar_requisito_legal_ambiental = deps['actualizar_requisito_legal_ambiental']
    eliminar_requisito_legal_ambiental = deps['eliminar_requisito_legal_ambiental']
    obtener_simulacros_ambientales_empresa = deps['obtener_simulacros_ambientales_empresa']
    crear_simulacro_ambiental = deps['crear_simulacro_ambiental']
    actualizar_simulacro_ambiental = deps['actualizar_simulacro_ambiental']
    eliminar_simulacro_ambiental = deps['eliminar_simulacro_ambiental']
    obtener_ambiental_capacitaciones_empresa = deps['obtener_ambiental_capacitaciones_empresa']
    crear_ambiental_capacitacion = deps['crear_ambiental_capacitacion']
    actualizar_ambiental_capacitacion = deps['actualizar_ambiental_capacitacion']
    eliminar_ambiental_capacitacion = deps['eliminar_ambiental_capacitacion']
    sugerir_matriz_legal_ia = deps['sugerir_matriz_legal_ia']
    generar_reporte_simulacro = deps['generar_reporte_simulacro']
    set_ai_focus_context = deps.get('set_ai_focus_context')

    @ui.page('/sistema-gestion/ambiental')
    def environment_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Gestión ambiental', back_route='/sistema-gestion', module_key='environment')
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
            ui.label('Gestión ambiental').classes('ideas-kicker')
            ui.label('Módulo ambiental por empresa').classes('text-3xl font-bold text-slate-900')
            ui.label('Cruza procesos reales, aspectos ambientales, legislación y simulacros en un único frente de gestión.').classes('ideas-subtitle mb-3')

            if not company_map:
                ui.label('Primero necesitas registrar una empresa para habilitar este módulo.').classes('text-slate-500')
                return

            if str(app.storage.user.get('role') or '') == 'admin':
                company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                company_select.on_value_change(lambda _e: (app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None), set_selection(int(company_select.value), None) if company_select.value else None, ui.navigate.to(with_empresa_id('/sistema-gestion/ambiental', company_select.value))))

            if not selected_company_id:
                return

            empresa = obtener_empresa_detalle(int(selected_company_id)) or {}
            company_name = fix_text(empresa.get('razon_social', company_map.get(selected_company_id, '')))
            process_rows = obtener_mapa_procesos_empresa(int(selected_company_id))
            process_options = _process_options(process_rows, fix_text)
            aspects = obtener_aspectos_ambientales_empresa(int(selected_company_id))
            legal_rows = obtener_requisitos_legales_ambientales_empresa(int(selected_company_id))
            drills = obtener_simulacros_ambientales_empresa(int(selected_company_id))
            if callable(set_ai_focus_context):
                set_ai_focus_context(
                    'ambiental',
                    {
                        'empresa_id': int(selected_company_id),
                        'aspectos_total': len(aspects or []),
                        'legales_total': len(legal_rows or []),
                        'simulacros_total': len(drills or []),
                        'proceso_referencia': next(iter(process_options.values()), '') if process_options else '',
                    },
                )

            today = datetime.date.today()
            significant_aspects = sum(1 for row in aspects if bool(row.get('es_significativo')))
            legal_due = sum(1 for row in legal_rows if (due := _parse_date(row.get('fecha_vencimiento'))) and due >= today and (due - today).days <= 60)
            drill_dates = [date for date in (_parse_date(row.get('fecha_simulacro')) for row in drills) if date]
            latest_drill = max(drill_dates).strftime('%d.%m.%Y') if drill_dates else 'Sin registro'
            aspects_pending = any(
                bool(row.get('es_significativo')) and not str(row.get('control_operacional') or '').strip()
                for row in aspects
            )
            legal_alert = any(
                str(row.get('estado_cumplimiento') or '').strip().lower() in {'no cumple', 'en proceso'}
                or ((due := _parse_date(row.get('fecha_vencimiento'))) is not None and due < today)
                for row in legal_rows
            )
            drills_alert = (not drills) or any(not bool(row.get('respuesta_eficaz')) for row in drills)
            tab_alerts = {
                'aspectos_impactos': aspects_pending,
                'cumplimiento_legal': legal_alert,
                'emergencias': drills_alert,
                'residuos': False,
                'productos_quimicos': False,
                'capacitaciones': False,
                'recursos': False,
                'huella_co2': False,
            }

            def _tab_label(base_label: str, block_id: str) -> str:
                if not tab_alerts.get(block_id):
                    return base_label
                return f'{base_label} \u2022'

            if False:
                ui.html(
                f'''
                <div class="ideas-grid-3" style="margin-top:14px;">
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Aspectos significativos</div>
                        <div class="value" style="font-size:1.9rem; margin-top:6px;">{significant_aspects}</div>
                        <div class="detail" style="margin-top:6px;">Aspectos marcados como significativos.</div>
                    </div>
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Próximos vencimientos legales</div>
                        <div class="value" style="font-size:1.9rem; margin-top:6px;">{legal_due}</div>
                        <div class="detail" style="margin-top:6px;">Requisitos legales con vencimiento en 60 días.</div>
                    </div>
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Último simulacro realizado</div>
                        <div class="value" style="font-size:1.9rem; margin-top:6px;">{latest_drill}</div>
                        <div class="detail" style="margin-top:6px;">Fecha del simulacro ambiental más reciente.</div>
                    </div>
                </div>
                '''
            )

            panel_structure = [
                {
                    'id': 'aspectos_impactos',
                    'label': 'Aspectos e Impactos',
                    'icon': 'eco',
                    'items': [
                        {'label': 'Matriz de aspectos e impactos', 'target': 'aspects'},
                    ],
                },
                {
                    'id': 'cumplimiento_legal',
                    'label': 'Cumplimiento Legal',
                    'icon': 'gavel',
                    'items': [
                        {'label': 'Matriz legal', 'target': 'legal'},
                        {'label': 'Certificaciones', 'target': None},
                    ],
                },
                {
                    'id': 'emergencias',
                    'label': 'Emergencias',
                    'icon': 'local_fire_department',
                    'items': [
                        {'label': 'Prevención de emergencias', 'target': None},
                        {'label': 'Simulacros', 'target': 'drills'},
                        {'label': 'Registro de emergencias', 'target': None},
                        {'label': 'Documentos', 'target': None},
                    ],
                },
                {
                    'id': 'residuos',
                    'label': 'Residuos',
                    'icon': 'delete_outline',
                    'items': [
                        {'label': 'Residuos peligrosos/especiales', 'target': None},
                        {'label': 'Residuos industriales asimilables a domiciliarios', 'target': None},
                        {'label': 'Residuos reciclables', 'target': None},
                    ],
                },
                {
                    'id': 'productos_quimicos',
                    'label': 'Productos químicos',
                    'icon': 'science',
                    'items': [
                        {'label': 'Inventario', 'target': None},
                        {'label': 'Registros - Hojas de seguridad', 'target': None},
                    ],
                },
                {
                    'id': 'capacitaciones',
                    'label': 'Capacitaciones',
                    'icon': 'school',
                    'items': [
                        {'label': 'Plan de capacitaciones anual', 'target': None},
                        {'label': 'Registros', 'target': None},
                    ],
                },
                {
                    'id': 'recursos',
                    'label': 'Recursos',
                    'icon': 'bolt',
                    'items': [
                        {'label': 'Energía eléctrica', 'target': None},
                        {'label': 'Gas', 'target': None},
                        {'label': 'Agua', 'target': None},
                        {'label': 'Emisiones gaseosas', 'target': None},
                    ],
                },
                {
                    'id': 'huella_co2',
                    'label': 'Huella de CO2',
                    'icon': 'co2',
                    'items': [
                        {'label': 'Scope 1', 'target': None},
                        {'label': 'Scope 2', 'target': None},
                        {'label': 'Scope 3', 'target': None},
                    ],
                },
            ]
            def _open_submodule(target: str | None) -> None:
                if target in {'aspects', 'legal', 'drills'}:
                    ui.notify('Submódulo seleccionado.', type='info')
                else:
                    ui.notify('Submódulo en preparación.', type='warning')

            panel_tab_map = {}
            with ui.tabs().classes('w-full mt-4 ideas-panel p-2 rounded-[24px]') as panel_tabs:
                tab_dashboard = ui.tab('Dashboard', icon='insights').props('no-caps').classes('text-slate-700')
                for block in panel_structure:
                    tab_classes = 'text-slate-700'
                    if tab_alerts.get(block['id']):
                        tab_classes += ' text-red-500'
                    panel_tab_map[block['id']] = (
                        ui.tab(_tab_label(block['label'], block['id']), icon=block['icon'])
                        .props('no-caps')
                        .classes(tab_classes)
                    )

            with ui.tab_panels(panel_tabs, value=tab_dashboard).classes('w-full bg-transparent'):
                with ui.tab_panel(tab_dashboard).classes('px-0'):
                    aspects_count = len(aspects or [])
                    legal_count = len(legal_rows or [])
                    drills_count = len(drills or [])
                    total_submodulos = sum(len(block.get('items', [])) for block in panel_structure)
                    total_alertas = sum(1 for v in tab_alerts.values() if v)
                    score = int((aspects_count / max(1, aspects_count + legal_count + drills_count)) * 100) if (aspects_count or legal_count or drills_count) else 0
                    with ui.grid(columns=3).classes('w-full gap-3 mt-4'):
                        with ui.card().classes('ideas-panel').style('background:rgba(255,255,255,0.58);border:1px solid rgba(148,163,184,.18);box-shadow:none;backdrop-filter:blur(10px);'):
                            ui.label('Cobertura ambiental').classes('text-[0.82rem] font-normal text-slate-500 tracking-[0.08em] uppercase')
                            ui.echart({'series': [{
                                'type': 'gauge', 'min': 0, 'max': 100, 'startAngle': 210, 'endAngle': -30, 'radius': '88%',
                                'progress': {'show': True, 'width': 8, 'roundCap': True},
                                'axisLine': {'lineStyle': {'width': 8, 'color': [[1, 'rgba(148,163,184,.22)']]}},
                                'axisTick': {'show': False}, 'splitLine': {'show': False}, 'axisLabel': {'show': False},
                                'pointer': {'show': False}, 'anchor': {'show': False},
                                'title': {'show': True, 'offsetCenter': [0, '18%'], 'fontSize': 11, 'fontWeight': 'normal', 'color': 'rgba(71,85,105,.78)'},
                                'detail': {'formatter': '{value}%', 'offsetCenter': [0, '-8%'], 'fontSize': 20, 'fontWeight': 'normal', 'color': 'rgba(15,23,42,.86)'},
                                'data': [{'value': score, 'name': 'score'}],
                            }]}).classes('w-full h-56')
                        with ui.card().classes('ideas-panel'):
                            ui.label('Registros clave').classes('ideas-section-title')
                            ui.echart({
                                'xAxis': {'type': 'category', 'data': ['Aspectos', 'Legales', 'Simulacros']},
                                'yAxis': {'type': 'value'},
                                'series': [{'type': 'bar', 'barWidth': '42%', 'data': [aspects_count, legal_count, drills_count]}],
                                'grid': {'left': 28, 'right': 12, 'top': 24, 'bottom': 26},
                            }).classes('w-full h-64')
                        with ui.card().classes('ideas-panel'):
                            ui.label('Submodulos y alertas').classes('ideas-section-title')
                            ui.echart({
                                'tooltip': {'trigger': 'item'},
                                'series': [{'type': 'pie', 'radius': ['40%', '70%'], 'data': [
                                    {'name': 'Submodulos', 'value': total_submodulos},
                                    {'name': 'Alertas', 'value': total_alertas},
                                ]}]
                            }).classes('w-full h-64')
                    render_dashboard_customizer(
                        module_key='environment',
                        company_id=int(selected_company_id),
                        metric_catalog=[
                            ('aspectos_total', 'Aspectos ambientales', aspects_count),
                            ('aspectos_significativos', 'Aspectos significativos', significant_aspects),
                            ('requisitos_legales', 'Requisitos legales', legal_count),
                            ('vencimientos_60d', 'Vencimientos legales 60d', legal_due),
                            ('simulacros_total', 'Simulacros', drills_count),
                            ('submodulos', 'Submodulos', total_submodulos),
                            ('alertas_tab', 'Alertas de tabs', total_alertas),
                            ('cobertura_ambiental', 'Cobertura ambiental', score),
                        ],
                    )
                for block in panel_structure:
                    with ui.tab_panel(panel_tab_map[block['id']]).classes('px-0'):
                        with ui.card().classes('ideas-panel w-full mt-4'):
                            ui.label(block['label']).classes('ideas-section-title')
                            ui.label('Submódulos del subproceso seleccionado.').classes('ideas-section-note')
                            if str(block.get('id')) == 'cumplimiento_legal':
                                legal_table_host = ui.column().classes('w-full gap-3 mt-3')

                                def _open_legal_form(row: dict | None = None) -> None:
                                    _show_legal_dialog(
                                        ui, row=row, company_id=int(selected_company_id), fix_text_fn=fix_text,
                                        crear_fn=crear_requisito_legal_ambiental,
                                        actualizar_fn=actualizar_requisito_legal_ambiental,
                                    )

                                def _suggest_legal_requirements() -> None:
                                    rubro = fix_text(empresa.get('rubro') or empresa.get('actividad') or company_name)
                                    ubicacion = ', '.join(part for part in (
                                        fix_text(empresa.get('localidad') or ''),
                                        fix_text(empresa.get('provincia') or ''),
                                        fix_text(empresa.get('pais') or ''),
                                    ) if part)
                                    aspectos_lista = [
                                        fix_text(row.get('aspecto') or row.get('impacto') or '')
                                        for row in aspects
                                        if fix_text(row.get('aspecto') or row.get('impacto') or '')
                                    ]
                                    try:
                                        suggestions = sugerir_matriz_legal_ia(rubro, ubicacion, aspectos_lista) or []
                                    except Exception:
                                        ui.notify('No se pudieron generar sugerencias en este momento.', type='negative')
                                        return
                                    if not suggestions:
                                        ui.notify('La IA no devolvió requisitos legales para revisar.', type='warning')
                                        return
                                    _show_ia_suggestions_dialog(
                                        ui, suggestions=suggestions, guardar_fn=crear_requisito_legal_ambiental,
                                        company_id=int(selected_company_id), fix_text_fn=fix_text,
                                    )

                                def _refresh_legal_table() -> None:
                                    rows = obtener_requisitos_legales_ambientales_empresa(int(selected_company_id)) or []
                                    legal_table_host.clear()
                                    with legal_table_host:
                                        with ui.row().classes('w-full justify-between items-center gap-2'):
                                            ui.label('Matriz legal ambiental').classes('text-sm font-semibold text-slate-800')
                                            with ui.row().classes('gap-2'):
                                                ui.button('Sugerir con IA', icon='auto_awesome', on_click=_suggest_legal_requirements).props('outline color=primary')
                                                ui.button('Nuevo requisito', icon='add', on_click=lambda: _open_legal_form(None)).props('unelevated color=primary')

                                        table_rows = [{
                                            'id': int(row.get('id') or 0),
                                            'jurisdiccion': fix_text(row.get('jurisdiccion') or 'Nacional'),
                                            'norma': fix_text(row.get('norma_legal') or ''),
                                            'articulo': fix_text(row.get('articulo_aplicable') or ''),
                                            'estado': fix_text(row.get('estado_cumplimiento') or ''),
                                            'vencimiento': fix_text(row.get('fecha_vencimiento') or ''),
                                            'responsable': fix_text(row.get('responsable') or ''),
                                            'acciones': '',
                                        } for row in rows]
                                        columns = [
                                            {'name': 'jurisdiccion', 'label': 'Jurisdicción', 'field': 'jurisdiccion', 'align': 'left'},
                                            {'name': 'norma', 'label': 'Norma legal', 'field': 'norma', 'align': 'left'},
                                            {'name': 'articulo', 'label': 'Artículo aplicable', 'field': 'articulo', 'align': 'left'},
                                            {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'left'},
                                            {'name': 'vencimiento', 'label': 'Vencimiento', 'field': 'vencimiento', 'align': 'left'},
                                            {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                                            {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                                        ]
                                        table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=10).classes('w-full ideas-table')
                                        table.add_slot('body-cell-estado', """
                                            <q-td :props="props"><q-badge :color="props.value.toLowerCase() === 'cumple' ? 'positive' : (props.value.toLowerCase() === 'no cumple' ? 'negative' : 'warning')">{{ props.value }}</q-badge></q-td>
                                        """)
                                        table.add_slot('body-cell-acciones', """
                                            <q-td :props="props">
                                                <q-btn flat dense round icon="edit" color="primary" @click="$parent.$emit('edit_row', props.row.id)" />
                                                <q-btn flat dense round icon="delete" color="negative" @click="$parent.$emit('delete_row', props.row.id)" />
                                            </q-td>
                                        """)

                                        def _on_edit_legal(evt) -> None:
                                            rid = _extract_int(evt.args)
                                            source = next((row for row in rows if int(row.get('id') or 0) == rid), None)
                                            if source:
                                                _open_legal_form(source)

                                        def _on_delete_legal(evt) -> None:
                                            rid = _extract_int(evt.args)
                                            if rid is not None:
                                                eliminar_requisito_legal_ambiental(rid)
                                                ui.notify('Requisito legal eliminado.', type='positive')
                                                _refresh_legal_table()

                                        table.on('edit_row', _on_edit_legal)
                                        table.on('delete_row', _on_delete_legal)

                                _refresh_legal_table()

                            if str(block.get('id')) == 'aspectos_impactos':
                                table_host = ui.column().classes('w-full gap-3 mt-3')
                                medio_afectado_opts = {'Suelo': 'Suelo', 'Agua': 'Agua', 'Aire': 'Aire', 'Flora y Fauna': 'Flora y Fauna', 'Medio Humano': 'Medio Humano'}
                                ocurrencia_opts = {'No ha ocurrido': 'No ha ocurrido', 'Eventual': 'Eventual', 'Frecuente': 'Frecuente', 'Permanente': 'Permanente'}
                                magnitud_opts = {'Baja': 'Baja', 'Media': 'Media', 'Alta': 'Alta'}
                                reversibilidad_opts = {'Reversible': 'Reversible', 'Recuperable': 'Recuperable', 'Mitigable': 'Mitigable', 'Irreversible': 'Irreversible'}
                                cumplimiento_opts = {'OK': 'OK', 'NOK': 'NOK', 'N/A': 'N/A'}

                                def _open_aspect_form(row: dict | None = None) -> None:
                                    proceso_val = str((row or {}).get('proceso_nombre') or '').strip()
                                    medio_val = str((row or {}).get('medio_afectado') or '').strip()
                                    ocurrencia_val = str((row or {}).get('ocurrencia') or '').strip()
                                    magnitud_val = str((row or {}).get('magnitud') or '').strip()
                                    reversibilidad_val = str((row or {}).get('reversibilidad') or '').strip()
                                    cumplimiento_val = str((row or {}).get('cumplimiento') or '').strip()
                                    if proceso_val not in process_options:
                                        proceso_val = None
                                    if medio_val not in medio_afectado_opts:
                                        medio_val = None
                                    if ocurrencia_val not in ocurrencia_opts:
                                        ocurrencia_val = None
                                    if magnitud_val not in magnitud_opts:
                                        magnitud_val = None
                                    if reversibilidad_val not in reversibilidad_opts:
                                        reversibilidad_val = None
                                    if cumplimiento_val not in cumplimiento_opts:
                                        cumplimiento_val = None

                                    with ui.dialog() as dlg, ui.card().classes('w-[1180px] max-w-[98vw] ideas-panel p-5'):
                                        ui.label('Carga de Matriz de Aspectos e Impactos').classes('text-lg font-semibold text-slate-900')
                                        ui.label('Completá de izquierda a derecha. Enter avanza al siguiente campo.').classes('text-sm text-slate-500')

                                        with ui.row().classes('w-full items-center gap-2 mt-3'):
                                            ui.badge('DATOS BASE').props('color=grey-7')
                                        with ui.grid(columns=3).classes('w-full gap-2'):
                                            proceso = ui.select(process_options, value=proceso_val, label='Proceso').props('outlined use-input fill-input')
                                            actividad = ui.input('Actividad', value=str((row or {}).get('actividad') or '')).props('outlined')
                                            descripcion_actividad = ui.input('Descripción de la actividad', value=str((row or {}).get('descripcion_actividad') or '')).props('outlined')

                                        with ui.row().classes('w-full items-center gap-2 mt-3'):
                                            ui.badge('ASPECTO AMBIENTAL').props('color=primary')
                                        with ui.grid(columns=4).classes('w-full gap-2'):
                                            condicion_normal = ui.input('Condición normal de operación', value=str((row or {}).get('condicion_normal_operacion') or '')).props('outlined')
                                            condicion_anormal = ui.input('Condición anormal de operación', value=str((row or {}).get('condicion_anormal_operacion') or '')).props('outlined')
                                            condicion_emergencia = ui.input('Condición de emergencia', value=str((row or {}).get('condicion_emergencia') or '')).props('outlined')
                                            aspecto = ui.input('Descripción', value=str((row or {}).get('aspecto') or '')).props('outlined')

                                        with ui.row().classes('w-full items-center gap-2 mt-3'):
                                            ui.badge('IMPACTO AMBIENTAL').props('color=teal')
                                        with ui.grid(columns=4).classes('w-full gap-2'):
                                            impacto = ui.input('Descripción', value=str((row or {}).get('impacto') or '')).props('outlined')
                                            medio_afectado = ui.select(medio_afectado_opts, value=medio_val, label='Medio afectado').props('outlined')
                                            ocurrencia = ui.select(ocurrencia_opts, value=ocurrencia_val, label='Ocurrencia').props('outlined')
                                            magnitud = ui.select(magnitud_opts, value=magnitud_val, label='Magnitud').props('outlined')
                                            reversibilidad = ui.select(reversibilidad_opts, value=reversibilidad_val, label='Reversibilidad').props('outlined')

                                        with ui.row().classes('w-full items-center gap-2 mt-3'):
                                            ui.badge('EVALUACIÓN').props('color=indigo')
                                        with ui.grid(columns=4).classes('w-full gap-2'):
                                            requisito_legal = ui.input('Requisito legal asociado', value=str((row or {}).get('requisito_legal_asociado') or '')).props('outlined')
                                            significancia = ui.select({0: 'No significativo', 1: 'Significativo'}, value=int((row or {}).get('significancia') or 0), label='Significancia ambiental').props('outlined')

                                        with ui.row().classes('w-full items-center gap-2 mt-3'):
                                            ui.badge('GESTIÓN').props('color=orange')
                                        with ui.grid(columns=4).classes('w-full gap-2'):
                                            mitigacion = ui.input('Medidas de mitigación', value=str((row or {}).get('control_operacional') or '')).props('outlined')
                                            responsable = ui.input('Responsable', value=str((row or {}).get('responsable') or '')).props('outlined')
                                            fecha_realizacion = ui.input('Fecha de realización', value=str((row or {}).get('fecha_realizacion') or ''), placeholder='YYYY-MM-DD').props('outlined')
                                            cumplimiento = ui.select(cumplimiento_opts, value=cumplimiento_val, label='Cumplimiento').props('outlined')
                                            registro = ui.input('Registro', value=str((row or {}).get('registro') or '')).props('outlined')

                                        focus_order = [
                                            actividad, descripcion_actividad,
                                            condicion_normal, condicion_anormal, condicion_emergencia, aspecto,
                                            impacto, requisito_legal, mitigacion, responsable, fecha_realizacion, registro,
                                        ]
                                        for idx, control in enumerate(focus_order[:-1]):
                                            nxt = focus_order[idx + 1]
                                            control.on('keydown.enter', lambda _e, n=nxt: n.run_method('focus'))

                                        def _save_aspect() -> None:
                                            payload = {
                                                'proceso_nombre': str(proceso.value or '').strip(),
                                                'actividad': str(actividad.value or '').strip(),
                                                'aspecto': str(aspecto.value or '').strip(),
                                                'impacto': str(impacto.value or '').strip(),
                                                'condicion': str((condicion_normal.value or '') or (condicion_anormal.value or '') or (condicion_emergencia.value or '')).strip(),
                                                'significancia': int(significancia.value or 0),
                                                'control_operacional': str(mitigacion.value or '').strip(),
                                                'descripcion_actividad': str(descripcion_actividad.value or '').strip(),
                                                'condicion_normal_operacion': str(condicion_normal.value or '').strip(),
                                                'condicion_anormal_operacion': str(condicion_anormal.value or '').strip(),
                                                'condicion_emergencia': str(condicion_emergencia.value or '').strip(),
                                                'medio_afectado': str(medio_afectado.value or '').strip(),
                                                'ocurrencia': str(ocurrencia.value or '').strip(),
                                                'magnitud': str(magnitud.value or '').strip(),
                                                'reversibilidad': str(reversibilidad.value or '').strip(),
                                                'requisito_legal_asociado': str(requisito_legal.value or '').strip(),
                                                'responsable': str(responsable.value or '').strip(),
                                                'fecha_realizacion': str(fecha_realizacion.value or '').strip(),
                                                'cumplimiento': str(cumplimiento.value or '').strip(),
                                                'registro': str(registro.value or '').strip(),
                                            }
                                            if row and row.get('id'):
                                                ok, msg = actualizar_aspecto_ambiental(int(row['id']), **payload)
                                            else:
                                                ok, msg = crear_aspecto_ambiental(int(selected_company_id), **payload)
                                            ui.notify(fix_text(msg), type='positive' if ok else 'warning')
                                            if ok:
                                                dlg.close()
                                                _refresh_aspects_table()

                                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                            ui.button('Cancelar', on_click=dlg.close).props('flat')
                                            ui.button('Guardar', icon='save', on_click=_save_aspect).props('unelevated color=primary')
                                    dlg.open()

                                def _refresh_aspects_table() -> None:
                                    rows = obtener_aspectos_ambientales_empresa(int(selected_company_id)) or []
                                    table_host.clear()
                                    with table_host:
                                        with ui.row().classes('w-full justify-between items-center'):
                                            ui.label('Listado de aspectos e impactos').classes('text-sm font-semibold text-slate-800')
                                            ui.button('Nuevo registro', icon='add', on_click=lambda: _open_aspect_form(None)).props('unelevated color=primary')
                                        table_rows = [{
                                            'id': int(r.get('id') or 0),
                                            'proceso': str(r.get('proceso_nombre') or ''),
                                            'actividad': str(r.get('actividad') or ''),
                                            'descripcion_actividad': str(r.get('descripcion_actividad') or ''),
                                            'c_normal': str(r.get('condicion_normal_operacion') or ''),
                                            'c_anormal': str(r.get('condicion_anormal_operacion') or ''),
                                            'c_emergencia': str(r.get('condicion_emergencia') or ''),
                                            'impacto_desc': str(r.get('impacto') or ''),
                                            'medio_afectado': str(r.get('medio_afectado') or ''),
                                            'ocurrencia': str(r.get('ocurrencia') or ''),
                                            'magnitud': str(r.get('magnitud') or ''),
                                            'reversibilidad': str(r.get('reversibilidad') or ''),
                                            'req_legal': str(r.get('requisito_legal_asociado') or ''),
                                            'significancia': 'Significativo' if int(r.get('significancia') or 0) else 'No significativo',
                                            'mitigacion': str(r.get('control_operacional') or ''),
                                            'responsable': str(r.get('responsable') or ''),
                                            'fecha_realizacion': str(r.get('fecha_realizacion') or ''),
                                            'cumplimiento': str(r.get('cumplimiento') or ''),
                                            'registro': str(r.get('registro') or ''),
                                            'acciones': '',
                                        } for r in rows]
                                        columns = [
                                            {'name': 'proceso', 'label': 'Proceso', 'field': 'proceso', 'align': 'left'},
                                            {'name': 'actividad', 'label': 'Actividad', 'field': 'actividad', 'align': 'left'},
                                            {'name': 'descripcion_actividad', 'label': 'Descripción actividad', 'field': 'descripcion_actividad', 'align': 'left'},
                                            {'name': 'c_normal', 'label': 'Condición normal', 'field': 'c_normal', 'align': 'left'},
                                            {'name': 'c_anormal', 'label': 'Condición anormal', 'field': 'c_anormal', 'align': 'left'},
                                            {'name': 'c_emergencia', 'label': 'Condición emergencia', 'field': 'c_emergencia', 'align': 'left'},
                                            {'name': 'impacto_desc', 'label': 'Descripción', 'field': 'impacto_desc', 'align': 'left'},
                                            {'name': 'medio_afectado', 'label': 'Medio afectado', 'field': 'medio_afectado', 'align': 'left'},
                                            {'name': 'ocurrencia', 'label': 'Ocurrencia', 'field': 'ocurrencia', 'align': 'left'},
                                            {'name': 'magnitud', 'label': 'Magnitud', 'field': 'magnitud', 'align': 'left'},
                                            {'name': 'reversibilidad', 'label': 'Reversibilidad', 'field': 'reversibilidad', 'align': 'left'},
                                            {'name': 'req_legal', 'label': 'Req. legal', 'field': 'req_legal', 'align': 'left'},
                                            {'name': 'significancia', 'label': 'Significancia', 'field': 'significancia', 'align': 'left'},
                                            {'name': 'mitigacion', 'label': 'Medidas mitigación', 'field': 'mitigacion', 'align': 'left'},
                                            {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                                            {'name': 'fecha_realizacion', 'label': 'Fecha', 'field': 'fecha_realizacion', 'align': 'left'},
                                            {'name': 'cumplimiento', 'label': 'Cumplimiento', 'field': 'cumplimiento', 'align': 'left'},
                                            {'name': 'registro', 'label': 'Registro', 'field': 'registro', 'align': 'left'},
                                            {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                                        ]
                                        table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=8).classes('w-full ideas-table')
                                        table.add_slot('header', """
                                            <q-tr class="bg-slate-50">
                                                <q-th colspan="3"></q-th>
                                                <q-th colspan="3" class="text-center text-blue-700" style="font-weight:700;border-right:1px solid #cbd5e1;">Aspecto Ambiental</q-th>
                                                <q-th colspan="5" class="text-center text-teal-700" style="font-weight:700;">Impacto Ambiental</q-th>
                                                <q-th colspan="9"></q-th>
                                            </q-tr>
                                            <q-tr :props="props">
                                                <q-th
                                                    v-for="col in props.cols"
                                                    :key="col.name"
                                                    :props="props"
                                                    :style="col.name === 'c_emergencia' ? 'border-right:1px solid #cbd5e1;' : ''"
                                                >{{ col.label }}</q-th>
                                            </q-tr>
                                        """)
                                        table.add_slot('body-cell-acciones', """
                                            <q-td :props=\"props\">
                                                <q-btn flat dense round icon=\"edit\" color=\"primary\" @click=\"$parent.$emit('edit_row', props.row.id)\" />
                                                <q-btn flat dense round icon=\"delete\" color=\"negative\" @click=\"$parent.$emit('delete_row', props.row.id)\" />
                                            </q-td>
                                        """)

                                        def _on_edit_aspect(evt) -> None:
                                            rid = int(evt.args or 0)
                                            source = next((x for x in rows if int(x.get('id') or 0) == rid), None)
                                            if source:
                                                _open_aspect_form(source)

                                        def _on_delete_aspect(evt) -> None:
                                            rid = int(evt.args or 0)
                                            eliminar_aspecto_ambiental(rid)
                                            ui.notify('Registro eliminado.', type='positive')
                                            _refresh_aspects_table()

                                        table.on('edit_row', _on_edit_aspect)
                                        table.on('delete_row', _on_delete_aspect)
                                _refresh_aspects_table()

                            if str(block.get('id')) == 'capacitaciones':
                                table_host = ui.column().classes('w-full gap-3 mt-3')
                                proceso_emisor_opts = {'Seguridad y Salud en el trabajo': 'Seguridad y Salud en el trabajo', 'Medio Ambiente': 'Medio Ambiente', 'Calidad': 'Calidad', 'Otro': 'Otro'}
                                modalidad_opts = {'Presencial': 'Presencial', 'Hibrida': 'Hibrida', 'Virtual Sincronica': 'Virtual Sincronica', 'Virtual Asincronica': 'Virtual Asincronica'}
                                responsable_opts = {'Interna': 'Interna', 'Externa': 'Externa'}

                                def _payload(c: dict) -> dict:
                                    return {
                                        'tema': str(c['tema'].value or '').strip(),
                                        'proceso_emisor': str(c['proceso_emisor'].value or '').strip(),
                                        'proceso_receptor': str(c['proceso_receptor'].value or '').strip(),
                                        'personal_involucrado': int(c['personal_involucrado'].value or 0),
                                        'duracion_minutos': int(c['duracion_minutos'].value or 0),
                                        'fecha_maxima_ejecucion_planificada': str(c['fecha_plan'].value or '').strip(),
                                        'fecha_realizacion': str(c['fecha_real'].value or '').strip(),
                                        'estado': str(c['estado'].value or '').strip(),
                                        'porcentaje_personal_capacitado': float(c['porcentaje'].value or 0),
                                        'modalidad': str(c['modalidad'].value or '').strip(),
                                        'responsable_coordinacion': str(c['responsable_coord'].value or '').strip(),
                                        'entrenador': str(c['entrenador'].value or '').strip(),
                                        'requerimiento_legal': str(c['req_legal'].value or '').strip(),
                                        'detalle_requerimiento': str(c['detalle_req'].value or '').strip(),
                                    }

                                def _open_form(row: dict | None = None) -> None:
                                    emisor_val = str((row or {}).get('proceso_emisor') or '').strip()
                                    modalidad_val = str((row or {}).get('modalidad') or '').strip()
                                    responsable_val = str((row or {}).get('responsable_coordinacion') or '').strip()
                                    if emisor_val not in proceso_emisor_opts:
                                        emisor_val = None
                                    if modalidad_val not in modalidad_opts:
                                        modalidad_val = None
                                    if responsable_val not in responsable_opts:
                                        responsable_val = None
                                    with ui.dialog() as dlg, ui.card().classes('w-[980px] max-w-[96vw] ideas-panel p-4'):
                                        ui.label('Carga de capacitación Ambiental').classes('text-lg font-semibold text-slate-900')
                                        with ui.grid(columns=4).classes('w-full gap-2 mt-2'):
                                            tema = ui.input('Tema', value=str((row or {}).get('tema') or '')).props('outlined')
                                            proceso_emisor = ui.select(proceso_emisor_opts, value=emisor_val, label='Proceso emisor').props('outlined')
                                            proceso_receptor = ui.input('Proceso receptor', value=str((row or {}).get('proceso_receptor') or '')).props('outlined')
                                            personal_involucrado = ui.number('Personal involucrado', value=int((row or {}).get('personal_involucrado') or 0)).props('outlined')
                                            duracion_minutos = ui.number('Duración (minutos)', value=int((row or {}).get('duracion_minutos') or 0)).props('outlined')
                                            fecha_plan = ui.input('Fecha máxima de ejecución planificada', value=str((row or {}).get('fecha_maxima_ejecucion_planificada') or ''), placeholder='YYYY-MM-DD').props('outlined')
                                            fecha_real = ui.input('Fecha de realización', value=str((row or {}).get('fecha_realizacion') or ''), placeholder='YYYY-MM-DD').props('outlined')
                                            estado = ui.input('Estado', value=str((row or {}).get('estado') or '')).props('outlined')
                                            porcentaje = ui.number('% Personal capacitado', value=float((row or {}).get('porcentaje_personal_capacitado') or 0)).props('outlined')
                                            modalidad = ui.select(modalidad_opts, value=modalidad_val, label='Modalidad').props('outlined')
                                            responsable_coord = ui.select(responsable_opts, value=responsable_val, label='Responsable coordinación').props('outlined')
                                            entrenador = ui.input('Entrenador', value=str((row or {}).get('entrenador') or '')).props('outlined')
                                            req_legal = ui.input('Requerimiento legal', value=str((row or {}).get('requerimiento_legal') or '')).props('outlined')
                                        detalle_req = ui.textarea('Detalle del requerimiento', value=str((row or {}).get('detalle_requerimiento') or '')).props('outlined autogrow').classes('w-full')
                                        controls = {'tema': tema, 'proceso_emisor': proceso_emisor, 'proceso_receptor': proceso_receptor, 'personal_involucrado': personal_involucrado, 'duracion_minutos': duracion_minutos, 'fecha_plan': fecha_plan, 'fecha_real': fecha_real, 'estado': estado, 'porcentaje': porcentaje, 'modalidad': modalidad, 'responsable_coord': responsable_coord, 'entrenador': entrenador, 'req_legal': req_legal, 'detalle_req': detalle_req}

                                        def _save() -> None:
                                            payload = _payload(controls)
                                            if row and row.get('id'):
                                                ok, msg = actualizar_ambiental_capacitacion(int(row['id']), payload)
                                            else:
                                                ok, msg, _new_id = crear_ambiental_capacitacion(int(selected_company_id), payload)
                                            ui.notify(msg, type='positive' if ok else 'warning')
                                            if ok:
                                                dlg.close()
                                                _refresh_table()

                                        with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                            ui.button('Cancelar', on_click=dlg.close).props('flat')
                                            ui.button('Guardar', icon='save', on_click=_save).props('unelevated color=primary')
                                    dlg.open()

                                def _refresh_table() -> None:
                                    rows = obtener_ambiental_capacitaciones_empresa(int(selected_company_id)) or []
                                    table_host.clear()
                                    with table_host:
                                        with ui.row().classes('w-full justify-between items-center'):
                                            ui.label('Listado de capacitaciones').classes('text-sm font-semibold text-slate-800')
                                            ui.button('Nueva capacitación', icon='add', on_click=lambda: _open_form(None)).props('unelevated color=primary')
                                        table_rows = [{
                                            'id': int(r.get('id') or 0), 'tema': str(r.get('tema') or ''), 'proceso_emisor': str(r.get('proceso_emisor') or ''), 'proceso_receptor': str(r.get('proceso_receptor') or ''), 'personal_involucrado': int(r.get('personal_involucrado') or 0), 'duracion_minutos': int(r.get('duracion_minutos') or 0), 'fecha_plan': str(r.get('fecha_maxima_ejecucion_planificada') or ''), 'fecha_real': str(r.get('fecha_realizacion') or ''), 'estado': str(r.get('estado') or ''), 'porcentaje': float(r.get('porcentaje_personal_capacitado') or 0), 'modalidad': str(r.get('modalidad') or ''), 'responsable_coord': str(r.get('responsable_coordinacion') or ''), 'entrenador': str(r.get('entrenador') or ''), 'req_legal': str(r.get('requerimiento_legal') or ''), 'detalle_req': str(r.get('detalle_requerimiento') or ''), 'acciones': '',
                                        } for r in rows]
                                        columns = [{'name': 'tema', 'label': 'Tema', 'field': 'tema', 'align': 'left'}, {'name': 'proceso_emisor', 'label': 'Proceso emisor', 'field': 'proceso_emisor', 'align': 'left'}, {'name': 'proceso_receptor', 'label': 'Proceso receptor', 'field': 'proceso_receptor', 'align': 'left'}, {'name': 'personal_involucrado', 'label': 'Personal', 'field': 'personal_involucrado', 'align': 'left'}, {'name': 'duracion_minutos', 'label': 'Duración', 'field': 'duracion_minutos', 'align': 'left'}, {'name': 'fecha_plan', 'label': 'Fecha planificada', 'field': 'fecha_plan', 'align': 'left'}, {'name': 'fecha_real', 'label': 'Fecha realización', 'field': 'fecha_real', 'align': 'left'}, {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'left'}, {'name': 'porcentaje', 'label': '% Personal', 'field': 'porcentaje', 'align': 'left'}, {'name': 'modalidad', 'label': 'Modalidad', 'field': 'modalidad', 'align': 'left'}, {'name': 'responsable_coord', 'label': 'Resp. coordinación', 'field': 'responsable_coord', 'align': 'left'}, {'name': 'entrenador', 'label': 'Entrenador', 'field': 'entrenador', 'align': 'left'}, {'name': 'req_legal', 'label': 'Req. legal', 'field': 'req_legal', 'align': 'left'}, {'name': 'detalle_req', 'label': 'Detalle', 'field': 'detalle_req', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}]
                                        table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=8).classes('w-full ideas-table')
                                        table.add_slot('body-cell-acciones', """
                                            <q-td :props=\"props\">
                                                <q-btn flat dense round icon=\"edit\" color=\"primary\" @click=\"$parent.$emit('edit_row', props.row.id)\" />
                                                <q-btn flat dense round icon=\"delete\" color=\"negative\" @click=\"$parent.$emit('delete_row', props.row.id)\" />
                                            </q-td>
                                        """)

                                        def _on_edit(evt) -> None:
                                            rid = int(evt.args or 0)
                                            source = next((x for x in rows if int(x.get('id') or 0) == rid), None)
                                            if source:
                                                _open_form(source)

                                        def _on_delete(evt) -> None:
                                            rid = int(evt.args or 0)
                                            ok, msg = eliminar_ambiental_capacitacion(rid)
                                            ui.notify(msg, type='positive' if ok else 'warning')
                                            if ok:
                                                _refresh_table()

                                        table.on('edit_row', _on_edit)
                                        table.on('delete_row', _on_delete)
                                _refresh_table()

                            with ui.grid(columns=2).classes('w-full gap-3 mt-3'):
                                for item in block['items']:
                                    with ui.card().classes('ideas-module-card cursor-pointer').on(
                                        'click',
                                        lambda _e, t=item.get('target'): _open_submodule(t),
                                    ):
                                        ui.label(item['label']).classes('font-semibold text-slate-900')
                                        ui.label('Abrir módulo').classes('text-sm text-slate-500')

            return
