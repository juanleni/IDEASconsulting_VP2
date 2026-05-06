from __future__ import annotations

from nicegui import app, ui


def go_to_sst_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/salud-ocupacional')


def register_sst_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    obtener_mapa_procesos_empresa = deps['obtener_mapa_procesos_empresa']
    fix_text = deps['fix_text']

    @ui.page('/sistema-gestion/salud-ocupacional')
    def sst_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Salud ocupacional', back_route='/sistema-gestion')
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
            ui.label('Salud ocupacional').classes('ideas-kicker')
            ui.label('Módulo SST por empresa').classes('text-3xl font-bold text-slate-900')
            ui.label('Gestiona controles preventivos, accidentes, capacitación y recursos críticos en un único panel operativo.').classes('ideas-subtitle mb-3')

            if not company_map:
                ui.label('Primero necesitas registrar una empresa para habilitar este módulo.').classes('text-slate-500')
                return

            if str(app.storage.user.get('role') or '') == 'admin':
                company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                company_select.on_value_change(
                    lambda _e: (
                        app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                        set_selection(int(company_select.value), None) if company_select.value else None,
                        ui.navigate.to('/sistema-gestion/salud-ocupacional'),
                    )
                )

            if not selected_company_id:
                return

            empresa = obtener_empresa_detalle(int(selected_company_id)) or {}
            process_rows = obtener_mapa_procesos_empresa(int(selected_company_id))
            sst_processes = [row for row in process_rows if 'salud' in str(row.get('proceso_nombre') or '').lower() or 'seguridad' in str(row.get('proceso_nombre') or '').lower()]
            company_name = fix_text(empresa.get('razon_social', company_map.get(selected_company_id, '')))

            ui.html(
                f'''
                <div class="ideas-grid-3" style="margin-top:14px;">
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Empresa</div>
                        <div class="value" style="font-size:1.45rem; margin-top:6px;">{company_name}</div>
                        <div class="detail" style="margin-top:6px;">Contexto operativo de seguridad y salud.</div>
                    </div>
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Procesos SST mapeados</div>
                        <div class="value" style="font-size:1.9rem; margin-top:6px;">{len(sst_processes)}</div>
                        <div class="detail" style="margin-top:6px;">Procesos asociados a seguridad y salud ocupacional.</div>
                    </div>
                    <div class="ideas-quick-card" style="padding:16px 18px; border-radius:18px; box-shadow:none; border-color:rgba(148,163,184,.18);">
                        <div class="label">Plan anual SST</div>
                        <div class="value" style="font-size:1.45rem; margin-top:6px;">En seguimiento</div>
                        <div class="detail" style="margin-top:6px;">Control ejecutivo de acciones preventivas.</div>
                    </div>
                </div>
                '''
            )

            panel_structure = [
                {
                    'id': 'epp',
                    'label': 'EPP',
                    'icon': 'construction',
                    'items': [
                        {'label': 'Inventario y entrega de EPP', 'target': None},
                        {'label': 'Matriz de reposición', 'target': None},
                    ],
                },
                {
                    'id': 'accidentes',
                    'label': 'Gestión de Accidentes',
                    'icon': 'report',
                    'items': [
                        {'label': 'Registro de incidentes', 'target': None},
                        {'label': 'Investigación de causa raíz', 'target': None},
                        {'label': 'Plan de acciones correctivas', 'target': None},
                    ],
                },
                {
                    'id': 'emergencias',
                    'label': 'Emergencias',
                    'icon': 'local_hospital',
                    'items': [
                        {'label': 'Plan de respuesta', 'target': None},
                        {'label': 'Simulacros y evidencias', 'target': None},
                        {'label': 'Botiquines y brigadas', 'target': None},
                    ],
                },
                {
                    'id': 'equipos',
                    'label': 'Equipos',
                    'icon': 'engineering',
                    'items': [
                        {'label': 'Inspecciones de seguridad', 'target': None},
                        {'label': 'Mantenimiento preventivo', 'target': None},
                    ],
                },
                {
                    'id': 'quimicos',
                    'label': 'Productos Químicos',
                    'icon': 'science',
                    'items': [
                        {'label': 'Inventario', 'target': None},
                        {'label': 'Hojas de seguridad', 'target': None},
                        {'label': 'Almacenamiento y compatibilidad', 'target': None},
                    ],
                },
                {
                    'id': 'capacitaciones',
                    'label': 'Capacitaciones',
                    'icon': 'school',
                    'items': [
                        {'label': 'Plan anual de formación', 'target': None},
                        {'label': 'Registros y asistencia', 'target': None},
                    ],
                },
                {
                    'id': 'recursos',
                    'label': 'Recursos',
                    'icon': 'inventory_2',
                    'items': [
                        {'label': 'Señalización y cartelería', 'target': None},
                        {'label': 'Matriz de recursos críticos', 'target': None},
                    ],
                },
                {
                    'id': 'plan_accion',
                    'label': 'Plan de Acción SST',
                    'icon': 'task_alt',
                    'items': [
                        {'label': 'Backlog de acciones', 'target': None},
                        {'label': 'Cumplimiento por responsable', 'target': None},
                    ],
                },
            ]

            def _open_submodule(_target: str | None) -> None:
                ui.notify('Submódulo en preparación.', type='warning')

            panel_tab_map = {}
            with ui.tabs().classes('w-full mt-4 ideas-panel p-2 rounded-[24px]') as panel_tabs:
                for block in panel_structure:
                    panel_tab_map[block['id']] = ui.tab(block['label'], icon=block['icon']).props('no-caps').classes('text-slate-700')

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
