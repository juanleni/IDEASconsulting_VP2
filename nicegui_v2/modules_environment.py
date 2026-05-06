from __future__ import annotations

import datetime
from pathlib import Path

from nicegui import app, events, ui


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
    ui.navigate.to('/sistema-gestion/ambiental')


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
    sugerir_matriz_legal_ia = deps['sugerir_matriz_legal_ia']
    generar_reporte_simulacro = deps['generar_reporte_simulacro']

    @ui.page('/sistema-gestion/ambiental')
    def environment_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Gestión ambiental', back_route='/sistema-gestion')
        company_map = company_options()
        selected_company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
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
                company_select.on_value_change(lambda _e: (app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None), set_selection(int(company_select.value), None) if company_select.value else None, ui.navigate.to('/sistema-gestion/ambiental')))

            if not selected_company_id:
                return

            empresa = obtener_empresa_detalle(int(selected_company_id)) or {}
            company_name = fix_text(empresa.get('razon_social', company_map.get(selected_company_id, '')))
            process_rows = obtener_mapa_procesos_empresa(int(selected_company_id))
            process_options = _process_options(process_rows, fix_text)
            aspects = obtener_aspectos_ambientales_empresa(int(selected_company_id))
            legal_rows = obtener_requisitos_legales_ambientales_empresa(int(selected_company_id))
            drills = obtener_simulacros_ambientales_empresa(int(selected_company_id))

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
                for block in panel_structure:
                    tab_classes = 'text-slate-700'
                    if tab_alerts.get(block['id']):
                        tab_classes += ' text-red-500'
                    panel_tab_map[block['id']] = (
                        ui.tab(_tab_label(block['label'], block['id']), icon=block['icon'])
                        .props('no-caps')
                        .classes(tab_classes)
                    )

            with ui.tab_panels(panel_tabs, value=panel_tab_map[panel_structure[0]['id']]).classes('w-full bg-transparent'):
                for block in panel_structure:
                    with ui.tab_panel(panel_tab_map[block['id']]).classes('px-0'):
                        with ui.card().classes('ideas-panel w-full mt-4'):
                            ui.label(block['label']).classes('ideas-section-title')
                            ui.label('Submódulos del subproceso seleccionado.').classes('ideas-section-note')
                            with ui.grid(columns=2).classes('w-full gap-3 mt-3'):
                                for item in block['items']:
                                    with ui.card().classes('ideas-module-card cursor-pointer').on(
                                        'click',
                                        lambda _e, t=item.get('target'): _open_submodule(t),
                                    ):
                                        ui.label(item['label']).classes('font-semibold text-slate-900')
                                        ui.label('Abrir módulo').classes('text-sm text-slate-500')

            return
