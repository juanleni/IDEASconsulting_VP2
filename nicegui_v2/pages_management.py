from __future__ import annotations

from nicegui import app, ui


def latest_diagnosis_for_company(empresa_id: int | None, diagnosis_rows_fn) -> dict | None:
    if not empresa_id:
        return None
    for row in diagnosis_rows_fn():
        if int(row['empresa_id']) == int(empresa_id):
            return row
    return None


def valor_afirmativo_local(value) -> bool:
    text = str(value or '').strip().lower()
    return text in {'si', 'sí', 's', 'true', '1', 'yes', 'y', 'certificada', 'certificado', 'en proceso'}


def estructurar_sistemas() -> dict[str, dict]:
    return {
        'cert_iso_9001': {
            'titulo': 'Sistema de Gestion de Calidad',
            'norma': 'ISO 9001 / IATF 16949',
            'icono': 'verified',
            'resumen': 'Herramientas para controlar procesos, indicadores, documentos, riesgos y resolucion estructurada de problemas.',
            'campos_contratacion': ['cert_iso_9001', 'cert_iatf'],
            'herramientas': [
                {'titulo': 'Biblioteca Documental', 'icono': 'description', 'accion': 'documentos'},
                {'titulo': 'Mapas de Proceso', 'icono': 'alt_route', 'accion': 'mapas'},
                {'titulo': 'Indicadores KPI', 'icono': 'query_stats', 'accion': 'kpis'},
                {'titulo': 'Riesgos y Oportunidades', 'icono': 'shield', 'accion': 'riesgos'},
                {'titulo': 'Herramientas de Calidad 8D', 'icono': 'plumbing', 'accion': 'calidad'},
            ],
        },
        'cert_iso_14001': {
            'titulo': 'Sistema de Gestion Ambiental',
            'norma': 'ISO 14001',
            'icono': 'eco',
            'resumen': 'Gestiona aspectos e impactos, cumplimiento legal, simulacros, documentos ambientales y seguimiento ejecutivo.',
            'campos_contratacion': ['cert_iso_14001'],
            'herramientas': [
                {'titulo': 'Gestion Ambiental', 'icono': 'eco', 'accion': 'ambiental'},
                {'titulo': 'Biblioteca Documental', 'icono': 'description', 'accion': 'documentos'},
                {'titulo': 'Mapas de Proceso', 'icono': 'alt_route', 'accion': 'mapas'},
                {'titulo': 'Indicadores KPI', 'icono': 'query_stats', 'accion': 'kpis'},
                {'titulo': 'Riesgos y Oportunidades', 'icono': 'shield', 'accion': 'riesgos'},
            ],
        },
        'cert_iso_45001': {
            'titulo': 'Sistema de Salud Ocupacional',
            'norma': 'ISO 45001',
            'icono': 'health_and_safety',
            'resumen': 'Workspace para controles preventivos, documentos, procesos, indicadores y riesgos vinculados a seguridad y salud.',
            'campos_contratacion': ['cert_iso_45001'],
            'herramientas': [
                {'titulo': 'Salud Ocupacional', 'icono': 'health_and_safety', 'accion': 'salud'},
                {'titulo': 'Biblioteca Documental', 'icono': 'description', 'accion': 'documentos'},
                {'titulo': 'Mapas de Proceso', 'icono': 'alt_route', 'accion': 'mapas'},
                {'titulo': 'Indicadores KPI', 'icono': 'query_stats', 'accion': 'kpis'},
                {'titulo': 'Riesgos y Oportunidades', 'icono': 'shield', 'accion': 'riesgos'},
            ],
        },
    }


def go_to_management_workspace(empresa_id: int | None, set_selection_fn) -> None:
    if empresa_id:
        app.storage.user['management_company_id'] = int(empresa_id)
        set_selection_fn(int(empresa_id), None)
    ui.navigate.to('/sistema-gestion')


def sistemas_activos_para_empresa(selected_company: dict | None, permisos: str) -> dict[str, dict]:
    permisos_habilitados = {item.strip() for item in str(permisos or '').split(',') if item.strip()} if permisos != 'ALL' else set()
    activos = {}
    for sistema_id, sistema in estructurar_sistemas().items():
        contratado = any(valor_afirmativo_local(selected_company.get(campo)) for campo in sistema['campos_contratacion']) if selected_company else False
        permitido = permisos == 'ALL' or sistema_id in permisos_habilitados
        if contratado and permitido:
            activos[sistema_id] = sistema
    return activos


def logo_url_from_path(path: str | None) -> str:
    clean = str(path or '').strip().replace('\\', '/')
    if not clean:
        return ''
    if clean.startswith('/assets/'):
        return clean
    return f'/assets/{clean}'


def normalize_brand_color(value: str | None, default: str) -> str:
    color = str(value or '').strip()
    if len(color) == 7 and color.startswith('#'):
        return color
    if len(color) == 6:
        return f'#{color}'
    return default


def render_management_workspace_page(
    *,
    shell_fn,
    company_options_fn,
    current_selection_fn,
    obtener_empresa_detalle_fn,
    diagnosis_rows_fn,
    fix_text_fn,
    quick_card_fn,
    render_metrics_fn,
    certifications_summary_fn,
    set_selection_fn,
    obtener_color_contraste_fn=None,
    go_to_documents_library_fn=None,
    go_to_company_documents_module_fn=None,
    go_to_risks_module_fn=None,
    go_to_kpi_module_fn=None,
    go_to_process_maps_module_fn=None,
    go_to_environment_module_fn=None,
    go_to_sst_module_fn=None,
    go_to_quality_module_fn=None,
    go_to_users_module_fn=None,
) -> None:
    shell_container = shell_fn('Sistema de gestion')
    company_map = company_options_fn()
    session_role = str(app.storage.user.get('role') or '')
    forced_company_id = app.storage.user.get('logged_empresa_id') if session_role != 'admin' else None
    selected_company_id = forced_company_id or app.storage.user.get('management_company_id') or current_selection_fn()[0]
    try:
        selected_company_id = int(selected_company_id) if selected_company_id else None
    except Exception:
        selected_company_id = None
    if not selected_company_id and company_map:
        selected_company_id = next(iter(company_map.keys()))
        app.storage.user['management_company_id'] = selected_company_id

    selected_company = obtener_empresa_detalle_fn(selected_company_id) if selected_company_id else None
    selected_diag = latest_diagnosis_for_company(selected_company_id, diagnosis_rows_fn)

    with shell_container:
        if company_map and session_role == 'admin':
            company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
            company_select.on_value_change(
                lambda _e: (
                    app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                    set_selection_fn(int(company_select.value), None) if company_select.value else None,
                    ui.navigate.to('/sistema-gestion'),
                )
            )
        elif company_map and selected_company_id:
            set_selection_fn(selected_company_id, None)
        else:
            ui.label('Primero necesitas registrar al menos una empresa para habilitar este espacio.').classes('text-slate-500')
            return

        company_name = fix_text_fn(selected_company.get('razon_social', company_map.get(selected_company_id, ''))) if selected_company else fix_text_fn(company_map.get(selected_company_id, ''))
        logo_path = str(selected_company.get('logo_path') or '').strip() if selected_company else ''
        logo_url = logo_url_from_path(logo_path)
        color_primario = normalize_brand_color(selected_company.get('color_primario') if selected_company else None, '#1f7ed6')
        color_secundario = normalize_brand_color(selected_company.get('color_secundario') if selected_company else None, '#0f766e')
        color_texto_primario = obtener_color_contraste_fn(color_primario) if obtener_color_contraste_fn else '#ffffff'
        ia_empresa_activa = valor_afirmativo_local(selected_company.get('agente_ia_activo')) if selected_company else False
        ui.colors(primary=color_primario, secondary=color_secundario)
        logo_html = (
            f'''
            <div style="display:flex;justify-content:center;align-items:center;margin-bottom:22px;">
                <div style="width:min(520px,90vw);height:230px;display:flex;align-items:center;justify-content:center;background:radial-gradient(circle, rgba(31,126,214,.20) 0%, rgba(31,126,214,.08) 34%, rgba(255,255,255,0) 72%);">
                    <img src="{logo_url}" alt="{company_name}" class="h-48 w-auto bg-transparent drop-shadow-xl" style="max-width:100%;object-fit:contain;" />
                </div>
            </div>
            '''
            if logo_url
            else ''
        )
        last_cut = selected_diag['fecha'] if selected_diag else 'Sin diagnostico registrado'
        score_text = f"{selected_diag['score']:.2f}" if selected_diag else 'Sin score'
        level_text = fix_text_fn(selected_diag['nivel']) if selected_diag else 'Pendiente'

        ui.html(
            f'''
            <div class="w-full mt-2" style="position:relative;left:auto;transform:none;width:100%;max-width:100%;box-sizing:border-box;overflow:visible;border:0;background:transparent;border-radius:0;">
                <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:6px;min-height:clamp(96px,15vh,146px);padding:4px 10px 0 10px;">
                    <div style="display:flex;justify-content:center;align-items:center;margin-bottom:2px;">
                        <div style="width:min(360px,82vw);height:108px;display:flex;align-items:center;justify-content:center;background:transparent;">
                            {f'<img src="{logo_url}" alt="{company_name}" class="h-24 w-auto bg-transparent" style="max-width:100%;object-fit:contain;filter:drop-shadow(0 6px 12px rgba(15,23,42,.10));" />' if logo_url else ''}
                        </div>
                    </div>
                    <div class="eyebrow" style="color:rgba(15,23,42,.62);font-weight:700;letter-spacing:.16em;">SISTEMA DE GESTION INTEGRADO</div>
                    <div class="headline" style="color:#0f172a;font-weight:700;text-shadow:none;">{company_name}</div>
                </div>
            </div>
            '''
        ).classes('w-full').style('display:block;width:100%;margin:0;')
        cert_items = []
        if selected_company and valor_afirmativo_local(selected_company.get('cert_iso_9001')):
            cert_items.append(('ISO 9001', 'verified'))
        if selected_company and valor_afirmativo_local(selected_company.get('cert_iatf')):
            cert_items.append(('IATF 16949', 'precision_manufacturing'))
        if selected_company and valor_afirmativo_local(selected_company.get('cert_iso_14001')):
            cert_items.append(('ISO 14001', 'eco'))
        if selected_company and valor_afirmativo_local(selected_company.get('cert_iso_45001')):
            cert_items.append(('ISO 45001', 'health_and_safety'))

        with ui.column().classes('w-full mt-2 gap-2'):
            ui.label('Certificaciones').classes('ideas-section-title')
            with ui.row().classes('w-full flex-wrap items-center gap-2'):
                if cert_items:
                    for cert_label, cert_icon in cert_items:
                        with ui.row().classes('items-center gap-2 px-3 py-2 rounded-[999px] bg-white/80 border border-slate-200 text-slate-700'):
                            ui.icon(cert_icon).classes('text-[1rem] text-slate-600')
                            ui.label(cert_label).classes('text-sm font-semibold')
                else:
                    ui.label('Sin certificaciones declaradas').classes('ideas-section-note')
        if session_role == 'empresa':
            module_cards = [
                ('Documentos', 'description', 'documentos', go_to_company_documents_module_fn),
                ('Mapas', 'alt_route', 'mapas-proceso', go_to_process_maps_module_fn),
                ('KPIs', 'query_stats', 'kpis', go_to_kpi_module_fn),
                ('Riesgos', 'shield', 'riesgos', go_to_risks_module_fn),
                ('Ambiental', 'eco', 'ambiental', go_to_environment_module_fn),
                ('Salud Ocupacional', 'health_and_safety', 'salud-ocupacional', go_to_sst_module_fn),
                ('Calidad', 'plumbing', 'calidad', go_to_quality_module_fn),
            ]
            with ui.row().classes('w-full items-center justify-between mt-6'):
                ui.label('Módulos Operativos').classes('ideas-section-title')
                ui.label('Acceso directo al workspace corporativo').classes('ideas-section-note')
            ui.add_css(
                '''
                .ideas-ops-tabs .q-tab {
                    min-height: 94px;
                    padding: 0 30px;
                    border-radius: 16px;
                    margin: 3px 6px;
                }
                .ideas-ops-tabs .q-tab__label {
                    font-size: 1.18rem;
                    font-weight: 700;
                    letter-spacing: 0;
                }
                .ideas-ops-tabs .q-tab__icon {
                    font-size: 1.95rem;
                    margin-right: 10px;
                }
                '''
            )
            with ui.tabs().classes('w-full mt-3 ideas-panel p-3 rounded-[24px] ideas-ops-tabs'):
                for title, icon, route, action_fn in module_cards:
                    tab = ui.tab(title, icon=icon).props('inline-label no-caps').classes('text-slate-700 cursor-pointer')
                    if action_fn:
                        tab.on('click', lambda _e, fn=action_fn: fn(selected_company_id, set_selection_fn))
                    else:
                        tab.on('click', lambda _e, path=route: ui.navigate.to(f'/sistema-gestion/{path}'))
            return
            with ui.grid(columns=3).classes('ideas-module-grid w-full mt-3'):
                for title, icon, route, action_fn in module_cards:
                    card = ui.card().classes('ideas-module-card cursor-pointer')
                    if action_fn:
                        card.on('click', lambda _e, fn=action_fn: fn(selected_company_id, set_selection_fn))
                    else:
                        card.on('click', lambda _e, path=route: ui.navigate.to(f'/sistema-gestion/{path}'))
                    with card:
                        ui.html(
                            f'''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">{icon}</span></div>
                            </div>
                            <div>
                                <h3>{title}</h3>
                                <p>Acceso al módulo {title.lower()}.</p>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-2'):
                            if action_fn:
                                ui.button('Abrir', icon='open_in_new', on_click=lambda fn=action_fn: fn(selected_company_id, set_selection_fn)).props('flat color=primary')
                            else:
                                ui.button('Abrir', icon='open_in_new', on_click=lambda path=route: ui.navigate.to(f'/sistema-gestion/{path}')).props('flat color=primary')
            return

        if ia_empresa_activa:
            with ui.card().classes('ideas-panel w-full mt-4 border border-violet-200 bg-violet-50 shadow-none'):
                with ui.row().classes('w-full items-center justify-between gap-4'):
                    with ui.row().classes('items-center gap-4'):
                        ui.html('<div class="ideas-module-icon" style="background:rgba(124,58,237,.12);color:#7c3aed;"><span class="material-icons">auto_awesome</span></div>')
                        with ui.column().classes('gap-1'):
                            ui.label('Copiloto IA activo para esta empresa').classes('ideas-section-title')
                            ui.label('La asistencia IA ya esta habilitada y disponible dentro de Documentos y Herramientas de Calidad.').classes('ideas-section-note')
                    with ui.row().classes('items-center gap-2'):
                        if go_to_company_documents_module_fn:
                            ui.button(
                                'Ir a Documentos',
                                icon='description',
                                on_click=lambda: go_to_company_documents_module_fn(selected_company_id, set_selection_fn),
                            ).props('flat color=primary')
                        if go_to_quality_module_fn:
                            ui.button(
                                'Ir a Calidad',
                                icon='plumbing',
                                on_click=lambda: go_to_quality_module_fn(selected_company_id, set_selection_fn),
                            ).props('unelevated color=primary')

        permisos_session = str(app.storage.user.get('permisos') or 'ALL')
        module_actions = {
            'documentos': (go_to_company_documents_module_fn, selected_company_id),
            'kpis': (go_to_kpi_module_fn, selected_company_id),
            'ambiental': (go_to_environment_module_fn, selected_company_id),
            'salud': (go_to_sst_module_fn, selected_company_id),
            'mapas': (go_to_process_maps_module_fn, selected_company_id),
            'riesgos': (go_to_risks_module_fn, selected_company_id),
            'calidad': (go_to_quality_module_fn, selected_company_id),
        }

        selected_system_state = {'id': None}

        @ui.refreshable
        def render_dashboard_content(selected_company_data: dict | None, permisos: str, sistema_activo_id: str | None = None) -> None:
            sistemas_activos = sistemas_activos_para_empresa(selected_company_data, permisos)

            if not sistema_activo_id:
                ui.label('Sistemas Activos').classes('ideas-section-title mt-6')
                ui.label('Selecciona un sistema para ver sus herramientas operativas.').classes('ideas-section-note')

                if not sistemas_activos:
                    with ui.card().classes('ideas-panel w-full mt-6'):
                        ui.label('No hay sistemas activos disponibles').classes('ideas-section-title')
                        ui.label('La empresa no tiene sistemas activos o tu usuario no tiene permisos asignados para visualizarlos.').classes('ideas-section-note')
                    return

                with ui.grid(columns=2).classes('ideas-module-grid w-full mt-4'):
                    for sistema_id, sistema in sistemas_activos.items():
                        card = ui.card().classes('ideas-module-card cursor-pointer')
                        card.style(f'background:linear-gradient(135deg, {color_primario}, {color_secundario}); color:{color_texto_primario} !important; border:0;')
                        card.on(
                            'click',
                            lambda _e, sid=sistema_id: (
                                selected_system_state.__setitem__('id', sid),
                                render_dashboard_content.refresh(selected_company_data, permisos, sid),
                            ),
                        )
                        with card:
                            ui.html(
                                f'''
                                <div class="ideas-module-top" style="color:{color_texto_primario} !important;">
                                    <div class="ideas-module-icon" style="background:rgba(255,255,255,.18);color:{color_texto_primario};"><span class="material-icons">{sistema["icono"]}</span></div>
                                    <span class="ideas-module-state" style="background:rgba(255,255,255,.18);color:{color_texto_primario};border-color:rgba(255,255,255,.28);">Activo</span>
                                </div>
                                <div style="color:{color_texto_primario} !important;">
                                    <h3 style="color:{color_texto_primario} !important;">{fix_text_fn(sistema["titulo"])}</h3>
                                    <p style="color:{color_texto_primario} !important;opacity:.88;">{fix_text_fn(sistema["norma"])} - {fix_text_fn(sistema["resumen"])}</p>
                                    {'<div style="margin-top:10px;display:inline-flex;padding:6px 12px;border-radius:999px;background:rgba(255,255,255,.18);color:' + color_texto_primario + ';font-weight:700;">Copiloto IA disponible</div>' if ia_empresa_activa else ''}
                                </div>
                                '''
                            )
                            with ui.row().classes('w-full justify-end mt-3'):
                                ui.button(
                                    'Ingresar',
                                    icon='arrow_forward',
                                    on_click=lambda sid=sistema_id: (
                                        selected_system_state.__setitem__('id', sid),
                                        render_dashboard_content.refresh(selected_company_data, permisos, sid),
                                    ),
                                ).props('flat').style(f'color:{color_texto_primario} !important;')
                return

            sistema = sistemas_activos.get(sistema_activo_id)
            if not sistema:
                ui.label('Sistema no disponible').classes('ideas-section-title mt-6')
                ui.label('El sistema seleccionado ya no esta activo o no tienes permisos para verlo.').classes('ideas-section-note')
                ui.button(
                    'Volver a Sistemas Activos',
                    icon='arrow_back',
                    on_click=lambda: (
                        selected_system_state.__setitem__('id', None),
                        render_dashboard_content.refresh(selected_company_data, permisos, None),
                    ),
                ).props('flat color=primary')
                return

            with ui.row().classes('w-full items-center justify-between mt-6 gap-4'):
                with ui.row().classes('items-center gap-4'):
                    ui.button(
                        'Volver',
                        icon='arrow_back',
                        on_click=lambda: (
                            selected_system_state.__setitem__('id', None),
                            render_dashboard_content.refresh(selected_company_data, permisos, None),
                        ),
                    ).props('flat color=primary')
                    with ui.column().classes('gap-1'):
                        ui.label(fix_text_fn(sistema['titulo'])).classes('ideas-section-title')
                        ui.label(f"{fix_text_fn(sistema['norma'])} - Herramientas disponibles").classes('ideas-section-note')
                ui.badge('Operativo', color='positive').classes('px-3 py-2')

            with ui.grid(columns=3).classes('ideas-module-grid w-full mt-4'):
                for herramienta in sistema['herramientas']:
                    action_tuple = module_actions.get(herramienta['accion'])
                    action_fn = action_tuple[0] if action_tuple else None
                    action_company_id = action_tuple[1] if action_tuple else None
                    ia_disponible_herramienta = ia_empresa_activa and herramienta['accion'] in {'documentos', 'calidad'}
                    tool_card = ui.card().classes('ideas-module-card cursor-pointer')
                    if action_fn:
                        tool_card.on('click', lambda _e, fn=action_fn, company_id=action_company_id: fn(company_id, set_selection_fn))
                    with tool_card:
                        ui.html(
                            f'''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">{herramienta["icono"]}</span></div>
                            </div>
                            <div>
                                <h3>{fix_text_fn(herramienta["titulo"])}</h3>
                                <p>Herramienta integrada en {fix_text_fn(sistema["titulo"])}.</p>
                                {'<div style="margin-top:10px;display:inline-flex;padding:6px 12px;border-radius:999px;background:rgba(124,58,237,.10);color:#7c3aed;font-weight:700;">IA disponible aqui</div>' if ia_disponible_herramienta else ''}
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-2'):
                            if action_fn:
                                ui.button('Abrir', icon='open_in_new', on_click=lambda fn=action_fn, company_id=action_company_id: fn(company_id, set_selection_fn)).props('flat color=primary')
                            else:
                                ui.button('Proximamente', icon='schedule').props('flat color=grey-7 disable')

        render_dashboard_content(selected_company, permisos_session, None)

        if session_role == 'admin':
            with ui.card().classes('ideas-panel w-full mt-6'):
                with ui.row().classes('w-full items-center justify-between gap-4'):
                    with ui.row().classes('items-center gap-4'):
                        ui.html('<div class="ideas-module-icon"><span class="material-icons">group</span></div>')
                        with ui.column().classes('gap-1'):
                            ui.label('Gestion de Usuarios').classes('ideas-section-title')
                            ui.label('Administra credenciales, roles y permisos por sistema activo.').classes('ideas-section-note')
                    ui.button(
                        'Administrar usuarios',
                        icon='manage_accounts',
                        on_click=lambda: go_to_users_module_fn(selected_company_id, set_selection_fn) if go_to_users_module_fn else None,
                    ).props('color=primary')


def register_management_page(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    go_to_documents_library = deps['go_to_documents_library']
    go_to_company_documents_module = deps['go_to_company_documents_module']
    go_to_process_maps_module = deps['go_to_process_maps_module']
    go_to_kpi_module = deps['go_to_kpi_module']
    go_to_risks_module = deps['go_to_risks_module']
    go_to_environment_module = deps['go_to_environment_module']
    go_to_sst_module = deps['go_to_sst_module']
    go_to_quality_module = deps['go_to_quality_module']
    go_to_users_module = deps['go_to_users_module']

    @ui.page('/sistema-gestion')
    def management_workspace_page() -> None:
        if not ensure_platform_access():
            return
        if app.storage.user.get('role') == 'admin':
            ui.notify('Acceso denegado: El workspace es exclusivo para cuentas de empresa.', type='negative')
            ui.navigate.to('/dashboard')
            return
        render_management_workspace_page(
            shell_fn=deps['shell'],
            company_options_fn=deps['company_options'],
            current_selection_fn=deps['current_selection'],
            obtener_empresa_detalle_fn=deps['obtener_empresa_detalle'],
            diagnosis_rows_fn=deps['diagnosis_rows'],
            fix_text_fn=deps['fix_text'],
            quick_card_fn=deps['quick_card'],
            render_metrics_fn=deps['render_metrics'],
            certifications_summary_fn=deps['certifications_summary'],
            set_selection_fn=deps['set_selection'],
            obtener_color_contraste_fn=deps.get('obtener_color_contraste'),
            go_to_documents_library_fn=go_to_documents_library,
            go_to_company_documents_module_fn=go_to_company_documents_module,
            go_to_risks_module_fn=go_to_risks_module,
            go_to_kpi_module_fn=go_to_kpi_module,
            go_to_process_maps_module_fn=go_to_process_maps_module,
            go_to_environment_module_fn=go_to_environment_module,
            go_to_sst_module_fn=go_to_sst_module,
            go_to_quality_module_fn=go_to_quality_module,
            go_to_users_module_fn=go_to_users_module,
        )
