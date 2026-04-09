from __future__ import annotations

from nicegui import app, ui


def latest_diagnosis_for_company(empresa_id: int | None, diagnosis_rows_fn) -> dict | None:
    if not empresa_id:
        return None
    for row in diagnosis_rows_fn():
        if int(row['empresa_id']) == int(empresa_id):
            return row
    return None


def management_modules() -> list[dict]:
    return [
        {
            'title': 'Gestion de documentos',
            'icon': 'description',
            'summary': 'Centralizacion de documentos, procedimientos, instructivos y registros con control de vigencia y trazabilidad.',
            'items': ['Procedimientos y politicas vigentes', 'Registros y formatos controlados', 'Estructura documental por empresa'],
        },
        {
            'title': 'Indicadores clave de performance (KPI)',
            'icon': 'query_stats',
            'summary': 'Seguimiento ejecutivo y operativo de metricas criticas para controlar desempeno, desvios y evolucion del negocio.',
            'items': ['Dashboard de indicadores por area', 'Metas, tendencias y responsables', 'Alertas de desvios y seguimiento'],
        },
        {
            'title': 'Gestion ambiental',
            'icon': 'eco',
            'summary': 'Base para aspectos ambientales, cumplimiento, objetivos y seguimiento de acciones asociadas al sistema de gestion.',
            'items': ['Aspectos e impactos ambientales', 'Objetivos y programas', 'Seguimiento de cumplimiento y acciones'],
        },
        {
            'title': 'Gestion de salud ocupacional',
            'icon': 'health_and_safety',
            'summary': 'Espacio para ordenar controles, requisitos y seguimiento preventivo vinculados a la salud y seguridad ocupacional.',
            'items': ['Matriz de controles y seguimiento', 'Planes preventivos', 'Trazabilidad de acciones y hallazgos'],
        },
        {
            'title': 'Mapas de proceso',
            'icon': 'alt_route',
            'summary': 'Visualizacion estructurada de procesos clave, interacciones, responsables y puntos criticos de control.',
            'items': ['Mapa general y por macroproceso', 'Responsables e interfaces', 'Vinculacion con riesgos e indicadores'],
        },
        {
            'title': 'Gestion de riesgos y oportunidades',
            'icon': 'shield',
            'summary': 'Estructura de identificacion, evaluacion y priorizacion de riesgos y oportunidades con foco en control y mejora.',
            'items': ['Matrices por proceso o sistema', 'Priorizacion y tratamiento', 'Seguimiento de oportunidades de mejora'],
        },
    ]


def go_to_management_workspace(empresa_id: int | None, set_selection_fn) -> None:
    if empresa_id:
        app.storage.user['management_company_id'] = int(empresa_id)
        set_selection_fn(int(empresa_id), None)
    ui.navigate.to('/sistema-gestion')


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
) -> None:
    shell_container = shell_fn('Sistema de gestion')
    company_map = company_options_fn()
    selected_company_id = app.storage.user.get('management_company_id') or current_selection_fn()[0]
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
        ui.label('Sistema de gestion').classes('ideas-kicker')
        ui.label('Workspace por empresa-cliente').classes('text-3xl font-bold text-slate-900')
        ui.label('Cada empresa contara con un espacio exclusivo para evolucionar sus herramientas de gestion, control y mejora continua.').classes('ideas-subtitle mb-2')
        if company_map:
            company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
            company_select.on_value_change(
                lambda _e: (
                    app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                    set_selection_fn(int(company_select.value), None) if company_select.value else None,
                    ui.navigate.to('/sistema-gestion'),
                )
            )
        else:
            ui.label('Primero necesitas registrar al menos una empresa para habilitar este espacio.').classes('text-slate-500')
            return

        company_name = fix_text_fn(selected_company.get('razon_social', company_map.get(selected_company_id, ''))) if selected_company else fix_text_fn(company_map.get(selected_company_id, ''))
        last_cut = selected_diag['fecha'] if selected_diag else 'Sin diagnostico registrado'
        score_text = f"{selected_diag['score']:.2f}" if selected_diag else 'Sin score'
        level_text = fix_text_fn(selected_diag['nivel']) if selected_diag else 'Pendiente'
        ui.html(
            f'''
            <div class="ideas-workspace-banner w-full mt-4">
                <div class="eyebrow">Etapa 3 · Sistema de gestion por cliente</div>
                <div class="headline">{company_name}</div>
                <div class="support">
                    Este espacio concentrara la arquitectura documental, los indicadores, los mapas, los riesgos y los frentes de gestion especificos de la empresa.
                    La base ya queda preparada para crecer modulo por modulo en proximas etapas.
                </div>
            </div>
            '''
        )
        render_metrics_fn(
            ui.row().classes('w-full mt-4'),
            [
                ('Ultimo corte', last_cut, 'Referencia ejecutiva mas reciente disponible para esta empresa.'),
                ('Nivel del diagnostico', level_text, 'Lectura consolidada del ultimo diagnostico cargado.'),
                ('Score vigente', score_text, 'Puntaje ejecutivo asociado al ultimo corte disponible.'),
            ],
        )
        ui.html(
            f'''<div class="ideas-grid-3" style="margin-top:18px;">
            {quick_card_fn('Rubro', fix_text_fn(selected_company.get('rubro', 'Sin definir')) if selected_company else 'Sin definir', 'Actividad principal registrada en la ficha institucional.')}
            {quick_card_fn('Certificaciones', certifications_summary_fn(selected_company), 'Base util para orientar modulos, controles y exigencias del sistema.')}
            {quick_card_fn('Contacto clave', fix_text_fn(selected_company.get('contacto_nombre', 'Sin asignar')) if selected_company else 'Sin asignar', 'Persona de referencia actual para acompanar el desarrollo del sistema.')}
            </div>'''
        )
        ui.label('Modulos previstos').classes('ideas-section-title mt-6')
        ui.label('Esta primera version arma la estructura de trabajo por empresa y deja definidos los modulos que iremos desarrollando como herramientas independientes.').classes('ideas-section-note')
        modules_html = ''.join(
            f'''
            <div class="ideas-module-card">
                <div class="ideas-module-top">
                    <div class="ideas-module-icon"><span class="material-icons">{module["icon"]}</span></div>
                    <div class="ideas-module-state">Etapa base</div>
                </div>
                <div>
                    <h3>{module["title"]}</h3>
                    <p>{module["summary"]}</p>
                </div>
                <div class="ideas-mini-list">
                    {''.join(f'<div class="item"><span class="dot"></span><span>{fix_text_fn(item)}</span></div>' for item in module['items'])}
                </div>
            </div>
            '''
            for module in management_modules()
        )
        ui.html(f'<div class="ideas-module-grid w-full mt-4">{modules_html}</div>')
        ui.html(
            '''<div class="ideas-cta-band w-full mt-5">
                <h3>Proxima evolucion del proyecto</h3>
                <p>En la siguiente etapa podremos desarrollar cada modulo como herramienta operativa: repositorio documental, gestion de KPI, matrices ambientales, controles de salud ocupacional, mapas interactivos de procesos y gestion de riesgos y oportunidades.</p>
            </div>'''
        )


def register_management_page(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    fix_text = deps['fix_text']
    certifications_summary = deps['certifications_summary']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    go_to_documents_library = deps['go_to_documents_library']
    go_to_company_documents_module = deps['go_to_company_documents_module']

    @ui.page('/sistema-gestion')
    def management_workspace_page() -> None:
        if not ensure_platform_access():
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
        )
        selected_company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        selected_company = obtener_empresa_detalle(selected_company_id) if selected_company_id else None
        company_name = fix_text(selected_company.get('razon_social', company_options().get(selected_company_id, 'Sin empresa activa'))) if selected_company else 'Sin empresa activa'
        ui.html(
            f'''<div class="ideas-grid-2" style="margin-top:18px;">
            <div class="ideas-service-card">
                <div class="icon">Biblioteca general</div>
                <h3>Biblioteca documental de la consultora</h3>
                <p>Accede al estandar general de IDEAS Consulting con normas, documentos esperados y registros de referencia, separado de las empresas clientes.</p>
                <div class="ideas-feature-list">
                    <div class="ideas-feature-item"><div class="glyph">ISO</div><div class="content"><div class="title">Normas disponibles</div><div class="detail">ISO 9001, ISO 14001, ISO 45001 e IATF 16949.</div></div></div>
                    <div class="ideas-feature-item"><div class="glyph">STD</div><div class="content"><div class="title">Uso consultora</div><div class="detail">Biblioteca maestra para diseno, revision y auditoria.</div></div></div>
                </div>
            </div>
            <div class="ideas-service-card">
                <div class="icon">Empresa activa</div>
                <h3>{company_name}</h3>
                <p>Esta empresa puede acceder a una vista particular de la biblioteca segun sus certificaciones registradas o como base de preparacion.</p>
                <div class="ideas-feature-list" style="margin-top:16px;">
                    <div class="ideas-feature-item"><div class="glyph">EMP</div><div class="content"><div class="title">Empresa activa</div><div class="detail">{company_name}</div></div></div>
                    <div class="ideas-feature-item"><div class="glyph">CERT</div><div class="content"><div class="title">Certificaciones</div><div class="detail">{certifications_summary(selected_company)}</div></div></div>
                </div>
            </div>
            </div>'''
        )
        with ui.row().classes('w-full gap-3 mt-4'):
            ui.button('Abrir biblioteca general', icon='library_books', on_click=go_to_documents_library).props('unelevated color=primary')
            ui.button(
                'Abrir biblioteca por empresa',
                icon='business',
                on_click=lambda: go_to_company_documents_module(selected_company_id, deps['set_selection']),
            ).props('unelevated color=secondary')
