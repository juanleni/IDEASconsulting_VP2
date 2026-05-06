from __future__ import annotations

from nicegui import app, ui


STANDARD_PROCESSES = [
    ('management', 'Management'),
    ('produccion', 'Produccion'),
    ('ingenieria', 'Ingenieria'),
    ('logistica', 'Logistica'),
    ('calidad', 'Calidad'),
    ('aspectos_ambientales', 'Aspectos Ambientales'),
    ('salud_ocupacional', 'Salud Ocupacional'),
    ('compras', 'Compras'),
    ('finanzas', 'Finanzas'),
    ('comercial', 'Comercial'),
    ('desarrollo', 'Desarrollo'),
    ('it', 'IT'),
    ('recursos_humanos', 'Recursos Humanos'),
    ('compliance', 'Compliance'),
]

PROCESS_CATEGORIES = {
    'management': 'Estratégicos',
    'comercial': 'Estratégicos',
    'finanzas': 'Estratégicos',
    'compliance': 'Estratégicos',
    'produccion': 'Operativos',
    'ingenieria': 'Operativos',
    'logistica': 'Operativos',
    'calidad': 'Operativos',
    'desarrollo': 'Operativos',
    'aspectos_ambientales': 'Soporte',
    'salud_ocupacional': 'Soporte',
    'compras': 'Soporte',
    'it': 'Soporte',
    'recursos_humanos': 'Soporte',
}

PROCESS_TILE_THEMES = [
    ('linear-gradient(135deg, rgba(31,126,214,.10), rgba(31,126,214,.03))', '#1d4ed8'),
    ('linear-gradient(135deg, rgba(15,143,97,.10), rgba(15,143,97,.03))', '#0f8f61'),
    ('linear-gradient(135deg, rgba(245,158,11,.14), rgba(245,158,11,.04))', '#b45309'),
    ('linear-gradient(135deg, rgba(99,102,241,.12), rgba(99,102,241,.04))', '#4f46e5'),
    ('linear-gradient(135deg, rgba(236,72,153,.12), rgba(236,72,153,.04))', '#be185d'),
    ('linear-gradient(135deg, rgba(20,184,166,.12), rgba(20,184,166,.04))', '#0f766e'),
]


def go_to_process_maps_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/mapas-proceso')


def _available_process_options(existing_rows: list[dict]) -> dict[str, str]:
    used = {str(row.get('proceso_codigo', '')) for row in existing_rows}
    return {code: name for code, name in STANDARD_PROCESSES if code not in used}


def _slugify_process_name(name: str) -> str:
    return (
        name.strip()
        .lower()
        .replace('á', 'a')
        .replace('é', 'e')
        .replace('í', 'i')
        .replace('ó', 'o')
        .replace('ú', 'u')
        .replace('ñ', 'n')
        .replace(' ', '_')
    )


def _process_category(row: dict) -> str:
    return PROCESS_CATEGORIES.get(str(row.get('proceso_codigo', '')), 'Personalizados')


def _render_landscape_overview(*, grouped_rows: dict[str, list[dict]], fix_text_fn, open_process_fn) -> None:
    strategic = grouped_rows.get('Estratégicos', [])
    operative = grouped_rows.get('Operativos', [])
    support = grouped_rows.get('Soporte', [])
    custom = grouped_rows.get('Personalizados', [])
    with ui.card().classes('w-full mt-4 p-7 rounded-[32px] border border-slate-200 shadow-none'):
        with ui.row().classes('w-full items-center justify-between gap-4'):
            with ui.column().classes('gap-1'):
                ui.label('Vista jerárquica del mapa de procesos').classes('text-3xl font-bold text-slate-900')
                ui.label('El landscape consolida todos los procesos de la empresa en una sola lectura, ordenados por nivel estratégico, operativo y de soporte para facilitar una mirada ejecutiva del sistema.').classes('text-slate-600 leading-7 max-w-[78ch]')
            with ui.row().classes('items-center gap-2'):
                ui.badge(f'Estratégicos: {len(strategic)}').style('background:rgba(214,167,95,.18);color:#8a5c14;padding:10px 14px;border-radius:16px;font-weight:800;')
                ui.badge(f'Operativos: {len(operative)}').style('background:rgba(203,213,225,.65);color:#334155;padding:10px 14px;border-radius:16px;font-weight:800;')
                ui.badge(f'Soporte: {len(support)}').style('background:rgba(219,234,254,.72);color:#1e3a8a;padding:10px 14px;border-radius:16px;font-weight:800;')

        def render_band(title: str, rows: list[dict], bg: str, title_color: str, chip_bg: str, chip_color: str) -> None:
            with ui.card().classes('w-full mt-5 p-5 rounded-[26px] shadow-none').style(f'background:{bg};border:1px solid rgba(148,163,184,.16);'):
                ui.label(title).classes('text-sm uppercase tracking-[0.18em] font-bold').style(f'color:{title_color};')
                if rows:
                    with ui.row().classes('w-full gap-3 mt-4 justify-center items-stretch'):
                        for row in rows:
                            ui.button(
                                fix_text_fn(row.get('proceso_nombre', '')),
                                on_click=lambda _=None, r=row: open_process_fn(r),
                            ).props('unelevated no-caps').style(
                                f'background:{chip_bg};color:{chip_color};border-radius:18px;padding:12px 16px;font-weight:800;min-width:170px;'
                            )
                else:
                    ui.label(f'Sin procesos en {title.lower()}.').classes('text-slate-500 mt-3')

        render_band(
            'Procesos estratégicos',
            strategic,
            'rgba(214,167,95,.12)',
            '#8a5c14',
            'linear-gradient(135deg, rgba(214,167,95,.24), rgba(196,140,58,.16))',
            '#0f172a',
        )
        render_band(
            'Procesos operativos',
            operative,
            'rgba(203,213,225,.34)',
            '#334155',
            'linear-gradient(135deg, rgba(71,85,105,.94), rgba(30,41,59,.92))',
            '#f8fafc',
        )
        render_band(
            'Procesos de soporte',
            support,
            'rgba(219,234,254,.52)',
            '#1e3a8a',
            'linear-gradient(135deg, rgba(203,213,225,.62), rgba(226,232,240,.86))',
            '#0f172a',
        )
        if custom:
            render_band(
                'Procesos personalizados',
                custom,
                'rgba(219,234,254,.58)',
                '#1d4ed8',
                'linear-gradient(135deg, rgba(191,219,254,.42), rgba(219,234,254,.84))',
                '#0f172a',
            )


def _process_status(row: dict) -> tuple[str, str, int]:
    filled_fields = sum(
        1
        for value in [
            row.get('dueno_proceso'),
            row.get('ultima_revision'),
            row.get('entradas'),
            row.get('salidas'),
            row.get('documentos'),
            row.get('indicadores'),
            row.get('recursos'),
        ]
        if str(value or '').strip()
    )
    if filled_fields >= 6:
        return 'Base completa', 'positive', filled_fields
    if filled_fields >= 3:
        return 'En desarrollo', 'warning', filled_fields
    return 'Pendiente', 'grey', filled_fields


def _render_process_editor(*, row: dict, fix_text_fn, actualizar_proceso_mapa_fn) -> None:
    with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[96vw] p-6 rounded-[26px]'):
        ui.label(f'Tortuga del proceso: {fix_text_fn(row["proceso_nombre"])}').classes('text-2xl font-bold text-slate-900')
        ui.label('Completa la informacion base del proceso para construir un mapa de procesos claro, estandarizado y util para gestion.').classes('text-slate-600')
        def preview_text(value: str, fallback: str = 'Sin definir') -> str:
            text = fix_text_fn(value or '').strip()
            if not text:
                return fallback
            return text[:120] + ('…' if len(text) > 120 else '')

        ui.html(
            f'''
            <div style="margin-top:18px;padding:24px;border-radius:28px;background:linear-gradient(180deg, rgba(244,247,250,.96), rgba(236,242,248,.92));border:1px solid rgba(148,163,184,.18);">
                <div style="display:grid;grid-template-columns:1fr 1.15fr 1fr;gap:16px;align-items:center;">
                    <div style="display:flex;flex-direction:column;gap:14px;">
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿De dónde? / Entradas</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("entradas"))}</div>
                        </div>
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿Con qué? / Recursos</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("recursos"))}</div>
                        </div>
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿Con qué criterios? / Documentos</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("documentos"))}</div>
                        </div>
                    </div>
                    <div style="display:flex;align-items:center;justify-content:center;">
                        <div style="width:100%;max-width:270px;padding:26px 22px;border-radius:26px;background:linear-gradient(135deg, #9a6800 0%, #c58b18 55%, #8c5f04 100%);color:white;box-shadow:0 20px 40px rgba(146, 102, 10, .22);text-align:center;">
                            <div style="font-size:.76rem;letter-spacing:.12em;text-transform:uppercase;color:rgba(255,255,255,.72);font-weight:800;">Proceso</div>
                            <div style="margin-top:10px;font-size:1.55rem;font-weight:800;line-height:1.08;">{fix_text_fn(row["proceso_nombre"])}</div>
                            <div style="margin-top:12px;padding-top:12px;border-top:1px solid rgba(255,255,255,.18);font-size:.92rem;color:rgba(255,255,255,.85);">Dueño: {preview_text(row.get("dueno_proceso"), "Sin asignar")}</div>
                            <div style="margin-top:6px;font-size:.88rem;color:rgba(255,255,255,.78);">Ult. revision: {preview_text(row.get("ultima_revision"), "Pendiente")}</div>
                        </div>
                    </div>
                    <div style="display:flex;flex-direction:column;gap:14px;">
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿Quién? / Responsable</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("dueno_proceso"), "Sin asignar")}</div>
                        </div>
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿Qué? / Salidas</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("salidas"))}</div>
                        </div>
                        <div style="padding:14px 16px;border-radius:20px;background:white;border:1px solid rgba(148,163,184,.18);">
                            <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">¿Cómo se mide? / Indicadores</div>
                            <div style="margin-top:8px;color:#0f172a;line-height:1.55;">{preview_text(row.get("indicadores"))}</div>
                        </div>
                    </div>
                </div>
            </div>
            '''
        )
        ui.label('Edicion de contenidos de la tortuga').classes('ideas-section-title mt-5')
        ui.label('Actualiza cada bloque y vuelve a guardar para mantener el diagrama del proceso alineado con la realidad operativa.').classes('ideas-section-note')
        with ui.row().classes('w-full gap-4 mt-3'):
            with ui.column().classes('col'):
                entradas_input = ui.textarea('Entradas', value=fix_text_fn(row.get('entradas', '')), placeholder='Proveedores, informacion de entrada, requisitos, insumos...').classes('w-full').props('outlined autogrow')
                documentos_input = ui.textarea('Documentos', value=fix_text_fn(row.get('documentos', '')), placeholder='Procedimientos, instructivos, formatos, registros...').classes('w-full').props('outlined autogrow')
                recursos_input = ui.textarea('Recursos', value=fix_text_fn(row.get('recursos', '')), placeholder='Personas, equipos, software, infraestructura...').classes('w-full').props('outlined autogrow')
            with ui.column().classes('col'):
                salidas_input = ui.textarea('Salidas', value=fix_text_fn(row.get('salidas', '')), placeholder='Resultados del proceso, entregables, informacion de salida...').classes('w-full').props('outlined autogrow')
                indicadores_input = ui.textarea('Indicadores', value=fix_text_fn(row.get('indicadores', '')), placeholder='KPI, metas, frecuencia de seguimiento...').classes('w-full').props('outlined autogrow')
        with ui.row().classes('w-full gap-4 mt-2'):
            with ui.column().classes('col'):
                owner_input = ui.input('Dueño del proceso', value=fix_text_fn(row.get('dueno_proceso', ''))).classes('w-full').props('outlined')
            with ui.column().classes('col justify-center'):
                ui.label('La fecha de ultima revision se actualiza automaticamente al guardar.').classes('text-sm text-slate-500 mt-6')

        def save_process() -> None:
            actualizar_proceso_mapa_fn(
                row['id'],
                owner_input.value or '',
                entradas_input.value or '',
                salidas_input.value or '',
                documentos_input.value or '',
                indicadores_input.value or '',
                recursos_input.value or '',
            )
            ui.notify('Proceso actualizado correctamente.', color='positive')
            dialog.close()
            ui.navigate.to('/sistema-gestion/mapas-proceso')

        with ui.row().classes('w-full justify-between mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar tortuga', icon='save', on_click=save_process).props('unelevated color=primary')
    dialog.open()


def _render_process_tile(
    *,
    row: dict,
    index: int,
    fix_text_fn,
    actualizar_proceso_mapa_fn,
    eliminar_proceso_mapa_fn,
) -> None:
    status_text, status_color, filled_fields = _process_status(row)
    tile_bg, accent = PROCESS_TILE_THEMES[index % len(PROCESS_TILE_THEMES)]

    def open_editor() -> None:
        _render_process_editor(
            row=row,
            fix_text_fn=fix_text_fn,
            actualizar_proceso_mapa_fn=actualizar_proceso_mapa_fn,
        )

    def delete_process() -> None:
        eliminar_proceso_mapa_fn(row['id'])
        ui.notify('Proceso eliminado del mapa.', color='warning')
        ui.navigate.to('/sistema-gestion/mapas-proceso')

    documents_ready = 'Sí' if str(row.get('documentos') or '').strip() else 'No'
    indicators_ready = 'Sí' if str(row.get('indicadores') or '').strip() else 'No'

    with ui.card().classes('ideas-panel p-5 rounded-[24px] h-full').style(f'background:{tile_bg};'):
        with ui.column().classes('w-full gap-0'):
            with ui.row().classes('w-full items-start justify-between gap-3'):
                with ui.column().classes('gap-1 col'):
                    ui.label(fix_text_fn(row['proceso_nombre'])).classes('text-xl font-bold text-slate-900')
                    ui.label(f'Dueño: {fix_text_fn(row.get("dueno_proceso") or "Sin asignar")}').classes('text-slate-600')
                ui.badge(status_text).props(f'color={status_color}')
            with ui.row().classes('w-full gap-2 mt-3'):
                ui.badge(f'Ult. revision: {fix_text_fn(row.get("ultima_revision") or "Pendiente")}').props('color=grey outline')
                ui.badge(f'{filled_fields}/7 campos').props('color=blue outline')
            ui.html(
                f'''
                <div style="margin-top:16px;display:grid;grid-template-columns:repeat(3, minmax(0, 1fr));gap:10px;">
                    <div style="padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.68);border:1px solid rgba(255,255,255,.45);">
                        <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">Dueño</div>
                        <div style="margin-top:6px;color:#0f172a;font-weight:700;">{fix_text_fn(row.get("dueno_proceso") or "Pendiente")}</div>
                    </div>
                    <div style="padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.68);border:1px solid rgba(255,255,255,.45);">
                        <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">Documentos</div>
                        <div style="margin-top:6px;color:{accent};font-weight:800;">{documents_ready}</div>
                    </div>
                    <div style="padding:12px 14px;border-radius:16px;background:rgba(255,255,255,.68);border:1px solid rgba(255,255,255,.45);">
                        <div style="font-size:.72rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#64748b;">Indicadores</div>
                        <div style="margin-top:6px;color:{accent};font-weight:800;">{indicators_ready}</div>
                    </div>
                </div>
                '''
            )
            with ui.row().classes('w-full justify-between items-center gap-3 mt-4'):
                ui.label('Haz clic en Abrir tortuga para editar el contenido del proceso.').classes('text-sm text-slate-500')
                with ui.row().classes('items-center gap-2'):
                    ui.button('Abrir tortuga', icon='open_in_full', on_click=open_editor).props('outline color=primary')
                    ui.button(icon='delete', on_click=delete_process).props('flat color=negative round')


def register_process_maps_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    fix_text = deps['fix_text']
    certifications_summary = deps['certifications_summary']
    obtener_mapa_procesos_empresa = deps['obtener_mapa_procesos_empresa']
    agregar_proceso_mapa_empresa = deps['agregar_proceso_mapa_empresa']
    actualizar_proceso_mapa = deps['actualizar_proceso_mapa']
    eliminar_proceso_mapa = deps['eliminar_proceso_mapa']
    generar_pdf_mapa_procesos = deps.get('generar_pdf_mapa_procesos')

    @ui.page('/sistema-gestion/mapas-proceso')
    def process_maps_page() -> None:
        if not ensure_platform_access():
            return

        company_map = company_options()
        selected_company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        if not selected_company_id and company_map:
            selected_company_id = next(iter(company_map.keys()))
            app.storage.user['management_company_id'] = selected_company_id

        selected_company = obtener_empresa_detalle(selected_company_id) if selected_company_id else None
        existing_rows = obtener_mapa_procesos_empresa(selected_company_id) if selected_company_id else []
        available_options = _available_process_options(existing_rows)

        with shell('Mapas de proceso', back_route='/sistema-gestion') as shell_container:
            with shell_container:
                def export_process_map_pdf() -> None:
                    if not generar_pdf_mapa_procesos:
                        ui.notify('Generación de PDF no disponible.', type='warning')
                        return
                    try:
                        company_name = fix_text(selected_company.get('razon_social', company_map.get(selected_company_id, 'Sin empresa activa'))) if selected_company else 'Sin empresa activa'
                        pdf_path = generar_pdf_mapa_procesos(company_name, existing_rows)
                        ui.download(str(pdf_path))
                    except Exception as exc:
                        ui.notify(f'No se pudo generar el PDF del mapa: {exc}', type='negative')

                ui.label('Mapas de proceso').classes('ideas-kicker')
                with ui.row().classes('w-full items-center justify-between gap-4'):
                    ui.label('Landscape visual y tortuga por proceso').classes('text-3xl font-bold text-slate-900')
                    ui.button(
                        'Exportar a PDF',
                        icon='picture_as_pdf',
                        color='red-8',
                        on_click=export_process_map_pdf,
                    ).props('unelevated')
                ui.label('Selecciona procesos estandar, construye el landscape de la empresa y entra a cada proceso solo cuando necesites editar su tortuga.').classes('ideas-subtitle mb-4')

                if company_map and str(app.storage.user.get('role') or '') == 'admin':
                    company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                    company_select.on_value_change(
                        lambda _e: (
                            app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                            set_selection(int(company_select.value), None) if company_select.value else None,
                            ui.navigate.to('/sistema-gestion/mapas-proceso'),
                        )
                    )
                elif not company_map:
                    ui.label('Primero necesitas registrar una empresa para crear su mapa de procesos.').classes('text-slate-500')
                    return

                if selected_company_id:
                    set_selection(int(selected_company_id), None)

                company_name = fix_text(selected_company.get('razon_social', company_map.get(selected_company_id, 'Sin empresa activa'))) if selected_company else 'Sin empresa activa'
                ui.html(
                    f'''<div class="ideas-grid-3" style="margin-top:18px;">
                    <div class="ideas-quick-card"><div class="label">Empresa activa</div><div class="value">{company_name}</div><div class="detail">Mapa de procesos especifico de la empresa seleccionada.</div></div>
                    <div class="ideas-quick-card"><div class="label">Procesos en landscape</div><div class="value">{len(existing_rows)}</div><div class="detail">Cada proceso se visualiza como tarjeta y se edita de forma puntual.</div></div>
                    <div class="ideas-quick-card"><div class="label">Certificaciones</div><div class="value">{certifications_summary(selected_company)}</div><div class="detail">Referencia util para orientar el mapa y la profundidad del diseño.</div></div>
                    </div>'''
                )

                with ui.card().classes('ideas-panel w-full mt-4'):
                    ui.label('Agregar procesos al landscape').classes('ideas-section-title')
                    ui.label('Selecciona procesos estandar de la consultora y sumalos al mapa especifico de la empresa. A medida que los agregas, apareceran abajo como tarjetas editables.').classes('ideas-section-note')
                    process_select = ui.select(available_options, label='Proceso estandar disponible').classes('w-full mt-4').props('outlined')
                    custom_process_input = ui.input('O agregar proceso personalizado', placeholder='Ejemplo: Mantenimiento, Legal, Customer Care...').classes('w-full mt-3').props('outlined clearable')

                    def add_process() -> None:
                        custom_name = (custom_process_input.value or '').strip()
                        if custom_name:
                            code = _slugify_process_name(custom_name)
                            process_name = custom_name
                        else:
                            code = process_select.value
                            if not code:
                                ui.notify('Selecciona un proceso o escribe uno nuevo para agregar.', color='warning')
                                return
                            process_name = available_options[code]
                        ok, message = agregar_proceso_mapa_empresa(selected_company_id, code, process_name)
                        ui.notify(message, color='positive' if ok else 'warning')
                        ui.navigate.to('/sistema-gestion/mapas-proceso')

                    with ui.row().classes('w-full justify-end mt-3'):
                        ui.button('Agregar proceso al landscape', icon='add', on_click=add_process).props('unelevated color=primary')

                ui.label('Procesos del mapa').classes('ideas-section-title mt-6')
                ui.label('Haz clic en cada tarjeta para entrar al proceso y completar su tortuga. El landscape se organiza por bandas para que el mapa se lea como una arquitectura de procesos real.').classes('ideas-section-note')

                if existing_rows:
                    grouped_rows = {
                        'Estratégicos': [],
                        'Operativos': [],
                        'Soporte': [],
                        'Personalizados': [],
                    }
                    for row in existing_rows:
                        grouped_rows[_process_category(row)].append(row)

                    def open_process_from_landscape(row: dict) -> None:
                        _render_process_editor(
                            row=row,
                            fix_text_fn=fix_text,
                            actualizar_proceso_mapa_fn=actualizar_proceso_mapa,
                        )

                    _render_landscape_overview(
                        grouped_rows=grouped_rows,
                        fix_text_fn=fix_text,
                        open_process_fn=open_process_from_landscape,
                    )

                    category_styles = {
                        'Estratégicos': ('rgba(15,23,42,.92)', '#f8fbff'),
                        'Operativos': ('rgba(31,126,214,.10)', '#0f172a'),
                        'Soporte': ('rgba(15,143,97,.10)', '#0f172a'),
                        'Personalizados': ('rgba(245,158,11,.12)', '#0f172a'),
                    }

                    for category in ['Estratégicos', 'Operativos', 'Soporte', 'Personalizados']:
                        rows_in_category = grouped_rows.get(category, [])
                        if not rows_in_category:
                            continue
                        band_bg, band_text = category_styles[category]
                        ui.html(
                            f'''
                            <div style="margin-top:18px;padding:18px 20px;border-radius:24px;background:{band_bg};color:{band_text};">
                                <div style="font-size:.76rem;font-weight:800;letter-spacing:.14em;text-transform:uppercase;opacity:.75;">Landscape</div>
                                <div style="margin-top:6px;font-size:1.45rem;font-weight:800;letter-spacing:-.03em;">{category}</div>
                                <div style="margin-top:6px;line-height:1.65;opacity:.82;">{len(rows_in_category)} proceso(s) dentro de esta banda del mapa.</div>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full gap-4 mt-4 items-stretch'):
                            for local_index, row in enumerate(rows_in_category):
                                with ui.column().classes('col-12 col-md-6 col-lg-4'):
                                    _render_process_tile(
                                        row=row,
                                        index=local_index,
                                        fix_text_fn=fix_text,
                                        actualizar_proceso_mapa_fn=actualizar_proceso_mapa,
                                        eliminar_proceso_mapa_fn=eliminar_proceso_mapa,
                                    )
                else:
                    ui.html(
                        '''
                        <div style="margin-top:16px;padding:24px;border-radius:22px;border:1px dashed rgba(15,23,42,.18);background:rgba(255,255,255,.7);">
                            <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">Aun no hay procesos en el mapa</div>
                            <div style="margin-top:8px;color:#475569;line-height:1.7;">
                                Comienza agregando procesos estandar al landscape de la empresa. Despues podras completar la tortuga de cada uno con la informacion clave del sistema de gestion.
                            </div>
                        </div>
                        '''
                    )
