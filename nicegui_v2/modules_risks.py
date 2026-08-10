from __future__ import annotations

from nicegui import app, ui
from dashboard_customizer import render_dashboard_customizer
from company_context import empresa_id_from_query_for_admin, with_empresa_id


RISK_SCALE_OPTIONS = {
    1: '1 · Bajo / Leve',
    3: '3 · Medio / Moderado',
    6: '6 · Alto / Critico',
}


def go_to_risks_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/riesgos', company_id))


def _risk_status(item: dict, fix_text_fn) -> tuple[str, str]:
    severidad = int(item.get('severidad') or 1)
    npr = int(item.get('npr') or 0)
    if severidad == 6 or npr >= 18:
        return 'Critico', 'negative'
    if npr == 9:
        return 'Moderado', 'warning'
    return 'Aceptable', 'positive'


def _extract_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if 'id' in value:
            return _extract_int(value['id'])
        if 'row' in value:
            return _extract_int(value['row'])
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_int(item)
            if found is not None:
                return found
        return None
    try:
        return int(value)
    except Exception:
        return None


def _show_scale_help(ui) -> None:
    with ui.dialog() as dialog, ui.card().classes('p-5 max-w-[640px] ideas-panel'):
        ui.label('Ayuda de criterios').classes('text-lg font-semibold text-slate-900')
        ui.label('La evaluacion usa una escala discreta de 1, 3 y 6 para simplificar la priorizacion y dejar una lectura clara para la gestion.').classes('ideas-section-note')
        with ui.row().classes('w-full gap-3 mt-3'):
            with ui.card().classes('col p-4 rounded-[22px] border border-slate-200'):
                ui.label('1 · Bajo / Leve').classes('font-bold text-emerald-700')
                ui.label('Impacto acotado y baja probabilidad de ocurrencia.').classes('text-slate-600')
            with ui.card().classes('col p-4 rounded-[22px] border border-slate-200'):
                ui.label('3 · Medio / Moderado').classes('font-bold text-amber-700')
                ui.label('Impacto relevante o frecuencia intermedia que requiere seguimiento.').classes('text-slate-600')
            with ui.card().classes('col p-4 rounded-[22px] border border-slate-200'):
                ui.label('6 · Alto / Critico').classes('font-bold text-rose-700')
                ui.label('Impacto severo o criticidad alta que exige control y accion prioritaria.').classes('text-slate-600')
        ui.separator().classes('my-4')
        ui.label('Reglas de negocio').classes('font-semibold text-slate-900')
        ui.label('NPR = Ocurrencia x Severidad').classes('text-slate-600')
        ui.label('Si la severidad es 6 o el NPR supera 9, la accion es obligatoria.').classes('text-slate-600')
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Cerrar', on_click=dialog.close).props('unelevated color=primary')
    dialog.open()


def _show_matrix_editor(
    *,
    ui,
    fix_text_fn,
    matrix: dict,
    obtener_items_riesgos_matriz_fn,
    crear_item_riesgo_fn,
    actualizar_item_riesgo_fn,
    eliminar_item_riesgo_fn,
    actualizar_matriz_riesgos_fn,
) -> None:
    selected_item = {'id': None}

    def reset_form() -> None:
        selected_item['id'] = None
        process_input.value = fix_text_fn(matrix.get('proceso_nombre', ''))
        type_input.value = 'Riesgo'
        description_input.value = ''
        occurrence_input.value = 1
        severity_input.value = 1
        actions_input.value = ''
        action_date_input.value = ''
        owner_input.value = ''
        effective_input.value = False
        refresh_preview()

    def current_metrics() -> tuple[int, int, int, bool]:
        ocurrencia = int(occurrence_input.value or 1)
        severidad = int(severity_input.value or 1)
        npr = ocurrencia * severidad
        obligatory = severidad == 6 or npr > 9
        return ocurrencia, severidad, npr, obligatory

    def refresh_preview() -> None:
        _ocurrencia, severidad, npr, obligatory = current_metrics()
        preview_container.clear()
        with preview_container:
            with ui.row().classes('w-full gap-3'):
                ui.html(f'<div class="ideas-quick-card"><div class="label">NPR</div><div class="value">{npr}</div><div class="detail">Probabilidad x severidad.</div></div>')
                status_label = 'Critico' if severidad == 6 or npr >= 18 else 'Moderado' if npr == 9 else 'Aceptable'
                status_color = 'negative' if status_label == 'Critico' else 'warning' if status_label == 'Moderado' else 'positive'
                with ui.card().classes('ideas-quick-card flex-1'):
                    ui.label('Estado').classes('label')
                    ui.badge(status_label).props(f'color={status_color}')
                    ui.label('Accion obligatoria' if obligatory else 'Seguimiento recomendado').classes('detail mt-2')

    def build_item_rows() -> list[dict]:
        rows = []
        for item in obtener_items_riesgos_matriz_fn(int(matrix['id'])):
            status_label, _status_color = _risk_status(item, fix_text_fn)
            rows.append(
                {
                    'id': int(item['id']),
                    'tipo': fix_text_fn(item.get('tipo') or 'Riesgo'),
                    'descripcion': fix_text_fn(item.get('descripcion') or ''),
                    'ocurrencia': int(item.get('ocurrencia') or 1),
                    'severidad': int(item.get('severidad') or 1),
                    'npr': int(item.get('npr') or 0),
                    'accion_obligatoria': 'Si' if bool(item.get('accion_obligatoria')) else 'No',
                    'responsable': fix_text_fn(item.get('responsable') or 'Sin responsable'),
                    'eficaz': 'Si' if bool(item.get('eficaz')) else 'No',
                    'estado': status_label,
                    'acciones': '',
                }
            )
        return rows

    with ui.dialog() as dialog, ui.card().classes('w-[1200px] max-w-[97vw] p-6 rounded-[28px] ideas-panel'):
        with ui.row().classes('w-full items-start justify-between'):
            with ui.column().classes('gap-1'):
                ui.label(f"Matriz de riesgos y oportunidades · {fix_text_fn(matrix.get('proceso_nombre', 'Proceso'))}").classes('text-2xl font-bold text-slate-900')
                ui.label('Gestiona riesgos y oportunidades por proceso con una priorizacion simple, visible y accionable.').classes('ideas-section-note')
            ui.button('Ayuda de criterios', icon='help_outline', on_click=lambda: _show_scale_help(ui)).props('outline')

        preview_container = ui.column().classes('w-full mt-4')

        with ui.row().classes('w-full gap-4 mt-4'):
            process_input = ui.input('Proceso / Matriz', value=fix_text_fn(matrix.get('proceso_nombre', ''))).classes('col').props('outlined')
            type_input = ui.select(['Riesgo', 'Oportunidad'], value='Riesgo', label='Tipo').classes('col').props('outlined')
        description_input = ui.textarea('Descripcion').classes('w-full mt-3').props('outlined autogrow')
        with ui.row().classes('w-full gap-4 mt-3'):
            occurrence_input = ui.select(RISK_SCALE_OPTIONS, value=1, label='Probabilidad de ocurrencia').classes('col').props('outlined')
            severity_input = ui.select(RISK_SCALE_OPTIONS, value=1, label='Grado de severidad').classes('col').props('outlined')
            owner_input = ui.input('Responsable').classes('col').props('outlined')
        with ui.row().classes('w-full gap-4 mt-3'):
            actions_input = ui.textarea('Acciones tomadas').classes('col').props('outlined autogrow')
            action_date_input = ui.input('Fecha de accion', placeholder='dd.mm.aaaa').classes('col').props('outlined')
        effective_input = ui.switch('Accion eficaz', value=False).classes('mt-3')

        occurrence_input.on_value_change(lambda _e: refresh_preview())
        severity_input.on_value_change(lambda _e: refresh_preview())
        refresh_preview()

        items_table = ui.table(
            columns=[
                {'name': 'tipo', 'label': 'Tipo', 'field': 'tipo', 'align': 'left'},
                {'name': 'descripcion', 'label': 'Descripcion', 'field': 'descripcion', 'align': 'left'},
                {'name': 'ocurrencia', 'label': 'O', 'field': 'ocurrencia', 'align': 'center'},
                {'name': 'severidad', 'label': 'S', 'field': 'severidad', 'align': 'center'},
                {'name': 'npr', 'label': 'NPR', 'field': 'npr', 'align': 'center'},
                {'name': 'accion_obligatoria', 'label': 'Accion obligatoria', 'field': 'accion_obligatoria', 'align': 'center'},
                {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                {'name': 'eficaz', 'label': 'Eficaz', 'field': 'eficaz', 'align': 'center'},
                {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'center'},
                {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
            ],
            rows=[],
            row_key='id',
            pagination=8,
        ).classes('w-full ideas-card ideas-table p-3 mt-6')
        items_table.props('flat bordered')
        items_table.add_slot(
            'body-cell-acciones',
            '''
            <q-td :props="props">
                <div class="row items-center no-wrap q-gutter-sm">
                    <q-btn flat round dense icon="edit" color="primary" @click="$parent.$emit('edit_item', props.row.id)" />
                    <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_item', props.row.id)" />
                </div>
            </q-td>
            ''',
        )

        def refresh_table() -> None:
            items_table.rows[:] = build_item_rows()
            items_table.update()

        def save_matrix_header() -> None:
            ok, message = actualizar_matriz_riesgos_fn(int(matrix['id']), process_input.value or '')
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                matrix['proceso_nombre'] = process_input.value or ''

        def save_item() -> None:
            ok, message = (
                actualizar_item_riesgo_fn(
                    int(selected_item['id']),
                    type_input.value or 'Riesgo',
                    description_input.value or '',
                    int(occurrence_input.value or 1),
                    int(severity_input.value or 1),
                    actions_input.value or '',
                    action_date_input.value or '',
                    owner_input.value or '',
                    bool(effective_input.value),
                )
                if selected_item['id']
                else crear_item_riesgo_fn(
                    int(matrix['id']),
                    type_input.value or 'Riesgo',
                    description_input.value or '',
                    int(occurrence_input.value or 1),
                    int(severity_input.value or 1),
                    actions_input.value or '',
                    action_date_input.value or '',
                    owner_input.value or '',
                    bool(effective_input.value),
                )
            )
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                refresh_table()
                reset_form()

        def load_item(item_id: int) -> None:
            item = next((row for row in obtener_items_riesgos_matriz_fn(int(matrix['id'])) if int(row['id']) == int(item_id)), None)
            if not item:
                ui.notify('Ese item ya no existe.', type='warning')
                return
            selected_item['id'] = int(item['id'])
            type_input.value = fix_text_fn(item.get('tipo') or 'Riesgo')
            description_input.value = fix_text_fn(item.get('descripcion') or '')
            occurrence_input.value = int(item.get('ocurrencia') or 1)
            severity_input.value = int(item.get('severidad') or 1)
            actions_input.value = fix_text_fn(item.get('acciones_tomadas') or '')
            action_date_input.value = fix_text_fn(item.get('fecha_accion') or '')
            owner_input.value = fix_text_fn(item.get('responsable') or '')
            effective_input.value = bool(item.get('eficaz'))
            refresh_preview()

        def remove_item(item_id: int) -> None:
            eliminar_item_riesgo_fn(int(item_id))
            ui.notify('Item eliminado correctamente.', type='positive')
            refresh_table()
            if selected_item['id'] and int(selected_item['id']) == int(item_id):
                reset_form()

        items_table.on('edit_item', lambda event: load_item(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el item.', type='warning'))
        items_table.on('delete_item', lambda event: remove_item(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el item.', type='warning'))

        refresh_table()
        with ui.row().classes('w-full justify-between gap-3 mt-4'):
            with ui.row().classes('gap-2'):
                ui.button('Guardar encabezado', icon='save', on_click=save_matrix_header).props('outline')
                ui.button('Limpiar formulario', icon='restart_alt', on_click=reset_form).props('flat')
            with ui.row().classes('gap-2'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar item', icon='save', on_click=save_item).props('unelevated color=primary')
    dialog.open()


def register_risks_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    fix_text = deps['fix_text']
    render_metrics = deps['render_metrics']
    quick_card = deps['quick_card']
    certifications_summary = deps['certifications_summary']
    obtener_mapa_procesos_empresa = deps['obtener_mapa_procesos_empresa']
    obtener_matrices_riesgos_empresa = deps['obtener_matrices_riesgos_empresa']
    obtener_matriz_riesgos_detalle = deps['obtener_matriz_riesgos_detalle']
    obtener_items_riesgos_matriz = deps['obtener_items_riesgos_matriz']
    crear_matriz_riesgos = deps['crear_matriz_riesgos']
    actualizar_matriz_riesgos = deps['actualizar_matriz_riesgos']
    eliminar_matriz_riesgos = deps['eliminar_matriz_riesgos']
    crear_item_riesgo = deps['crear_item_riesgo']
    actualizar_item_riesgo = deps['actualizar_item_riesgo']
    eliminar_item_riesgo = deps['eliminar_item_riesgo']
    set_ai_focus_context = deps.get('set_ai_focus_context')

    @ui.page('/sistema-gestion/riesgos')
    def risks_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Riesgos y oportunidades', back_route='/sistema-gestion', module_key='risks')
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
            ui.label('Gestion de riesgos y oportunidades').classes('ideas-kicker')
            ui.label('Matrices por proceso').classes('text-3xl font-bold text-slate-900')
            ui.label('Construye matrices por proceso para identificar, priorizar y seguir riesgos y oportunidades de la empresa activa.').classes('ideas-subtitle mb-3')

            if not company_map:
                ui.label('Primero necesitas registrar una empresa para habilitar este modulo.').classes('text-slate-500')
                return

            if str(app.storage.user.get('role') or '') == 'admin':
                company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                company_select.on_value_change(
                    lambda _e: (
                        app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                        set_selection(int(company_select.value), None) if company_select.value else None,
                        ui.navigate.to(with_empresa_id('/sistema-gestion/riesgos', company_select.value)),
                    )
                )

            if not selected_company_id:
                ui.label('Selecciona una empresa para comenzar.').classes('text-slate-500 mt-4')
                return

            company = obtener_empresa_detalle(selected_company_id)
            company_name = fix_text(company.get('razon_social', company_map.get(selected_company_id, ''))) if company else fix_text(company_map.get(selected_company_id, ''))
            matrices = obtener_matrices_riesgos_empresa(int(selected_company_id))
            if callable(set_ai_focus_context):
                set_ai_focus_context(
                    'riesgos',
                    {
                        'empresa_id': int(selected_company_id),
                        'matrices_total': len(matrices or []),
                        'matriz_reciente': fix_text(str((matrices or [{}])[0].get('proceso_nombre') or '')).strip() if matrices else '',
                    },
                )
            all_items = []
            for matrix in matrices:
                all_items.extend(obtener_items_riesgos_matriz(int(matrix['id'])))

            total_riesgos = sum(1 for item in all_items if fix_text(item.get('tipo') or '').lower() == 'riesgo')
            riesgos_con_accion = sum(
                1
                for item in all_items
                if fix_text(item.get('tipo') or '').lower() == 'riesgo'
                and str(item.get('acciones_tomadas') or '').strip()
            )
            acciones_tomadas = sum(1 for item in all_items if str(item.get('acciones_tomadas') or '').strip())
            acciones_eficaces = sum(1 for item in all_items if bool(item.get('eficaz')))

            if False:
                ui.html(
                f'''
                <div class="ideas-workspace-banner w-full mt-4">
                    <div class="eyebrow">Sistema de gestion · Riesgos</div>
                    <div class="headline">{company_name}</div>
                    <div class="support">
                        Releva matrices por proceso con criterio unificado, NPR automatico y foco visible sobre riesgos criticos y oportunidades prioritarias.
                    </div>
                </div>
                '''
            )

            with ui.tabs().classes('w-full mt-5 ideas-panel p-2 rounded-[24px]') as risk_tabs:
                tab_dashboard = ui.tab('Dashboard', icon='insights').props('no-caps').classes('text-slate-700')
                tab_create = ui.tab('Crear nueva matriz de riesgos & oportunidades', icon='add_chart').props('no-caps').classes('text-slate-700')
                tab_view = ui.tab('Ver matrices de Riesgos & Oportunidades', icon='table_view').props('no-caps').classes('text-slate-700')
                tab_stats = ui.tab('Gestion estadistica', icon='analytics').props('no-caps').classes('text-slate-700')

            with ui.tab_panels(risk_tabs, value=tab_dashboard).classes('w-full bg-transparent'):
                with ui.tab_panel(tab_dashboard).classes('px-0'):
                    criticos = sum(1 for item in all_items if _risk_status(item, fix_text)[0] == 'Critico')
                    moderados = sum(1 for item in all_items if _risk_status(item, fix_text)[0] == 'Moderado')
                    bajos = max(0, len(all_items) - criticos - moderados)
                    cobertura = int((riesgos_con_accion / total_riesgos) * 100) if total_riesgos else 0
                    with ui.grid(columns=3).classes('w-full gap-3 mt-4'):
                        with ui.card().classes('ideas-panel').style('background:rgba(255,255,255,0.58);border:1px solid rgba(148,163,184,.18);box-shadow:none;backdrop-filter:blur(10px);'):
                            ui.label('Coverage de acciones').classes('text-[0.82rem] font-normal text-slate-500 tracking-[0.08em] uppercase')
                            ui.echart({
                                'series': [{
                                    'type': 'gauge', 'min': 0, 'max': 100, 'startAngle': 210, 'endAngle': -30, 'radius': '88%',
                                    'progress': {'show': True, 'width': 8, 'roundCap': True},
                                    'axisLine': {'lineStyle': {'width': 8, 'color': [[1, 'rgba(148,163,184,.22)']]}},
                                    'axisTick': {'show': False}, 'splitLine': {'show': False}, 'axisLabel': {'show': False},
                                    'pointer': {'show': False}, 'anchor': {'show': False},
                                    'title': {'show': True, 'offsetCenter': [0, '18%'], 'fontSize': 11, 'fontWeight': 'normal', 'color': 'rgba(71,85,105,.78)'},
                                    'detail': {'formatter': '{value}%', 'offsetCenter': [0, '-8%'], 'fontSize': 20, 'fontWeight': 'normal', 'color': 'rgba(15,23,42,.86)'},
                                    'data': [{'value': cobertura, 'name': 'cobertura'}],
                                }]
                            }).classes('w-full h-56')
                        with ui.card().classes('ideas-panel'):
                            ui.label('Perfil de criticidad').classes('ideas-section-title')
                            ui.echart({
                                'tooltip': {'trigger': 'item'},
                                'series': [{'type': 'pie', 'radius': ['40%', '70%'], 'data': [
                                    {'name': 'Criticos', 'value': criticos},
                                    {'name': 'Moderados', 'value': moderados},
                                    {'name': 'Bajos', 'value': bajos},
                                ]}]
                            }).classes('w-full h-64')
                        with ui.card().classes('ideas-panel'):
                            ui.label('Matriz ejecutiva').classes('ideas-section-title')
                            ui.echart({
                                'xAxis': {'type': 'category', 'data': ['Matrices', 'Riesgos', 'Con accion', 'Eficaces']},
                                'yAxis': {'type': 'value'},
                                'series': [{'type': 'bar', 'barWidth': '42%', 'data': [len(matrices), total_riesgos, riesgos_con_accion, acciones_eficaces]}],
                                'grid': {'left': 28, 'right': 12, 'top': 24, 'bottom': 26},
                            }).classes('w-full h-64')
                    render_dashboard_customizer(
                        module_key='risks',
                        company_id=int(selected_company_id),
                        metric_catalog=[
                            ('matrices_total', 'Matrices totales', len(matrices)),
                            ('riesgos_totales', 'Riesgos totales', total_riesgos),
                            ('riesgos_con_accion', 'Riesgos con accion', riesgos_con_accion),
                            ('acciones_eficaces', 'Acciones eficaces', acciones_eficaces),
                            ('criticos', 'Riesgos criticos', criticos),
                            ('moderados', 'Riesgos moderados', moderados),
                            ('bajos', 'Riesgos bajos', bajos),
                            ('cobertura', 'Coverage de acciones', cobertura),
                        ],
                    )
                with ui.tab_panel(tab_create).classes('px-0'):
                    with ui.card().classes('ideas-panel w-full mt-4'):
                        ui.label('Crear nueva matriz').classes('ideas-section-title')
                        ui.label('Genera una matriz por proceso para trabajar riesgos y oportunidades de forma ordenada.').classes('ideas-section-note')
                        process_options = {
                            fix_text(item.get('proceso_nombre') or ''): fix_text(item.get('proceso_nombre') or '')
                            for item in obtener_mapa_procesos_empresa(int(selected_company_id))
                            if fix_text(item.get('proceso_nombre') or '').strip()
                        }
                        with ui.row().classes('w-full gap-4 mt-3'):
                            proceso_input = ui.select(process_options, label='Proceso / matriz').classes('col').props('outlined')

                        def save_matrix() -> None:
                            ok, message = crear_matriz_riesgos(int(selected_company_id), proceso_input.value or '')
                            ui.notify(fix_text(message), type='positive' if ok else 'negative')
                            if ok:
                                ui.navigate.to('/sistema-gestion/riesgos')

                        if process_options:
                            with ui.row().classes('w-full justify-end mt-3'):
                                ui.button('Crear matriz', icon='add_chart', on_click=save_matrix).props('unelevated color=primary')
                        else:
                            ui.label('No hay procesos cargados para esta empresa. Primero registra procesos en Mapas de proceso y luego crea la matriz desde aqui.').classes('text-amber-700 mt-3')

                with ui.tab_panel(tab_view).classes('px-0'):
                    ui.label('Ver matrices de Riesgos & Oportunidades').classes('ideas-section-title mt-4')
                    ui.label('Haz click sobre una matriz para abrir su editor detallado y gestionar riesgos u oportunidades del proceso.').classes('ideas-section-note')
                    if matrices:
                        with ui.row().classes('w-full gap-4 mt-4'):
                            for matrix in matrices:
                                items = obtener_items_riesgos_matriz(int(matrix['id']))
                                critical = sum(1 for item in items if _risk_status(item, fix_text)[0] == 'Critico')
                                moderate = sum(1 for item in items if _risk_status(item, fix_text)[0] == 'Moderado')
                                with ui.card().classes('ideas-module-card col cursor-pointer').on(
                                    'click',
                                    lambda _e, current_matrix=matrix: _show_matrix_editor(
                                        ui=ui,
                                        fix_text_fn=fix_text,
                                        matrix=current_matrix,
                                        obtener_items_riesgos_matriz_fn=obtener_items_riesgos_matriz,
                                        crear_item_riesgo_fn=crear_item_riesgo,
                                        actualizar_item_riesgo_fn=actualizar_item_riesgo,
                                        eliminar_item_riesgo_fn=eliminar_item_riesgo,
                                        actualizar_matriz_riesgos_fn=actualizar_matriz_riesgos,
                                    ),
                                ):
                                    with ui.row().classes('items-start justify-between w-full'):
                                        with ui.column().classes('gap-1'):
                                            ui.label(fix_text(matrix.get('proceso_nombre') or 'Proceso sin nombre')).classes('text-lg font-bold text-slate-900')
                                            ui.label(f"Ultima actualizacion: {fix_text(matrix.get('fecha_actualizacion') or 'Pendiente')}").classes('text-slate-500')
                                        ui.icon('warning_amber').classes('text-slate-400')
                                    with ui.row().classes('w-full gap-2 mt-2'):
                                        ui.badge(f'{len(items)} items').props('color=primary outline')
                                        ui.badge(f'{critical} criticos').props('color=negative outline')
                                        ui.badge(f'{moderate} moderados').props('color=warning outline')
                                    ui.label('Abre la matriz para editar proceso, cargar items, revisar NPR y registrar acciones.').classes('text-slate-600 mt-3')
                                    with ui.row().classes('w-full justify-end mt-3'):
                                        ui.button('Abrir matriz', icon='open_in_full', on_click=lambda current_matrix=matrix: _show_matrix_editor(
                                            ui=ui,
                                            fix_text_fn=fix_text,
                                            matrix=current_matrix,
                                            obtener_items_riesgos_matriz_fn=obtener_items_riesgos_matriz,
                                            crear_item_riesgo_fn=crear_item_riesgo,
                                            actualizar_item_riesgo_fn=actualizar_item_riesgo,
                                            eliminar_item_riesgo_fn=eliminar_item_riesgo,
                                            actualizar_matriz_riesgos_fn=actualizar_matriz_riesgos,
                                        )).props('flat color=primary')
                                        ui.button(
                                            '',
                                            icon='delete',
                                            on_click=lambda current_matrix=matrix: (eliminar_matriz_riesgos(int(current_matrix['id'])), ui.notify('Matriz eliminada correctamente.', type='positive'), ui.navigate.to('/sistema-gestion/riesgos')),
                                        ).props('flat color=negative round dense')
                    else:
                        ui.label('Todavia no hay matrices creadas para esta empresa.').classes('text-slate-500 mt-4')

                with ui.tab_panel(tab_stats).classes('px-0'):
                    ui.label('Gestion estadistica').classes('ideas-section-title mt-4')
                    ui.label('Indicadores ejecutivos del modulo para priorizar la gestion de riesgos y oportunidades.').classes('ideas-section-note')
                    render_metrics(
                        ui.row().classes('w-full mt-4'),
                        [
                            ('Riesgos relevados', str(total_riesgos), 'Cantidad total de riesgos registrados en las matrices de la empresa activa.'),
                            ('Riesgos con acciones definidas', str(riesgos_con_accion), 'Cantidad de riesgos relevados que ya tienen una accion definida para su tratamiento.'),
                            ('Tomadas / eficaces', f'{acciones_tomadas} / {acciones_eficaces}', 'Cantidad de acciones registradas y cuantas ya fueron marcadas como eficaces.'),
                        ],
                    )
