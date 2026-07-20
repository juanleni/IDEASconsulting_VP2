from __future__ import annotations

import csv
import io
import sqlite3
from datetime import date, datetime
from pathlib import Path

from nicegui import app, events, ui


DB_PATH = 'ideas.db'
UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'uploads' / 'matriz_legal'


def _inject_legal_design() -> None:
    ui.add_css('''
        :root { --legal-bg:#f2f5f9; --legal-card:#fff; --legal-border:#e3e8ef;
            --legal-text:#1b2433; --legal-muted:#6b7480; --legal-primary:#0e3a53;
            --legal-primary-light:#eaf1f5; --legal-ok:#15803d; --legal-warn:#b45309;
            --legal-danger:#b91c1c; }
        .legal-page { background:var(--legal-bg); border-radius:24px; padding:20px; color:var(--legal-text); }
        .legal-header { background:#fff; border:1px solid var(--legal-border); border-radius:20px;
            padding:22px 24px; box-shadow:0 2px 10px rgba(16,24,40,.05); }
        .legal-kicker { font-size:12px; font-weight:700; letter-spacing:.10em; color:#5a7b8c; }
        .legal-title { font-size:28px; line-height:1.15; font-weight:750; color:var(--legal-primary); }
        .legal-subtitle { color:var(--legal-muted); font-size:14px; }
        .legal-update { background:var(--legal-primary-light); color:var(--legal-primary); border-radius:999px;
            padding:7px 12px; font-size:12px; font-weight:600; }
        .legal-kpi { background:#fff; border:1px solid var(--legal-border); border-radius:20px;
            padding:18px; box-shadow:0 2px 10px rgba(16,24,40,.05); min-height:132px; }
        .legal-kpi-icon { width:38px; height:38px; border-radius:11px; background:var(--legal-primary-light);
            color:var(--legal-primary); display:flex; align-items:center; justify-content:center; }
        .legal-kpi-value { font-size:27px; font-weight:750; color:var(--legal-text); }
        .legal-kpi-label { font-size:12px; color:#8a93a0; }
        .legal-tabs { background:transparent; border-bottom:1px solid var(--legal-border); }
        .legal-tabs .q-tab { color:var(--legal-muted); min-height:52px; }
        .legal-tabs .q-tab--active { color:var(--legal-primary); }
        .legal-panel { background:#fff; border:1px solid var(--legal-border); border-radius:20px;
            padding:20px; box-shadow:0 2px 10px rgba(16,24,40,.05); }
        .legal-section-title { font-size:16px; font-weight:700; color:var(--legal-text); }
        .legal-table { border:1px solid var(--legal-border); border-radius:14px; overflow:hidden; }
        .legal-table thead tr { background:#f8fafc; color:#7b8491; }
        .legal-alert { background:#fff; border:1px solid var(--legal-border); border-left:4px solid var(--legal-warn);
            border-radius:16px; padding:16px 18px; }
        .legal-site { background:#fff; border:1px solid var(--legal-border); border-radius:18px; padding:18px;
            box-shadow:0 2px 10px rgba(16,24,40,.04); }
        .legal-rolebar { background:var(--legal-primary); color:#eaf1f5; border-radius:14px; padding:9px 14px; }
        @media(max-width:900px) { .legal-page { padding:10px; } .legal-header { padding:16px; } }
    ''')


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _ensure_tables() -> None:
    with _connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS legal_sites (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL,
                nombre TEXT NOT NULL, ubicacion TEXT DEFAULT '', jurisdiccion TEXT DEFAULT '',
                actividad TEXT DEFAULT '', activo INTEGER DEFAULT 1, created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS legal_requirements (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, site_id INTEGER,
                ambito TEXT DEFAULT 'Medio Ambiente', jurisdiccion TEXT DEFAULT 'Nacional',
                organismo TEXT DEFAULT '', tipo_norma TEXT DEFAULT 'Ley', numero TEXT DEFAULT '',
                titulo TEXT NOT NULL, articulo TEXT DEFAULT '', obligacion TEXT DEFAULT '',
                proceso TEXT DEFAULT '', responsable TEXT DEFAULT '', frecuencia TEXT DEFAULT '',
                estado TEXT DEFAULT 'Pendiente', criticidad TEXT DEFAULT 'Media',
                fecha_publicacion TEXT DEFAULT '', fecha_revision TEXT DEFAULT '', proxima_revision TEXT DEFAULT '',
                evidencia_requerida TEXT DEFAULT '', observaciones TEXT DEFAULT '', vigente INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP, updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS legal_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, requirement_id INTEGER NOT NULL,
                nombre TEXT NOT NULL, archivo_path TEXT DEFAULT '', comentario TEXT DEFAULT '',
                estado_aprobacion TEXT DEFAULT 'Pendiente', cargado_por TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS legal_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, site_id INTEGER,
                fecha TEXT NOT NULL, tipo TEXT DEFAULT 'Anual', auditor TEXT DEFAULT '',
                alcance TEXT DEFAULT '', resultado TEXT DEFAULT 'Planificada', hallazgos TEXT DEFAULT '',
                plan_accion TEXT DEFAULT '', fecha_cierre TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS legal_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, requirement_id INTEGER,
                tipo TEXT DEFAULT 'Actualización normativa', prioridad TEXT DEFAULT 'Media',
                titulo TEXT NOT NULL, detalle TEXT DEFAULT '', estado TEXT DEFAULT 'Nueva',
                fecha TEXT DEFAULT CURRENT_TIMESTAMP, atendida_por TEXT DEFAULT ''
            );
            CREATE TABLE IF NOT EXISTS legal_audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT, empresa_id INTEGER NOT NULL, usuario TEXT DEFAULT '',
                accion TEXT NOT NULL, entidad TEXT NOT NULL, entidad_id INTEGER,
                detalle TEXT DEFAULT '', created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_legal_req_empresa ON legal_requirements(empresa_id);
            CREATE INDEX IF NOT EXISTS idx_legal_log_empresa ON legal_audit_log(empresa_id);
        ''')


def _user_name() -> str:
    return str(app.storage.user.get('session_user_name') or app.storage.user.get('session_user_key') or 'sistema')


def _log(company_id: int, action: str, entity: str, entity_id: int | None, detail: str = '') -> None:
    with _connect() as conn:
        conn.execute(
            'INSERT INTO legal_audit_log (empresa_id, usuario, accion, entidad, entidad_id, detalle) VALUES (?, ?, ?, ?, ?, ?)',
            (company_id, _user_name(), action, entity, entity_id, detail),
        )


def _rows(query: str, params=()) -> list[dict]:
    with _connect() as conn:
        return [dict(row) for row in conn.execute(query, params).fetchall()]


def _insert(table: str, payload: dict) -> int:
    fields = ', '.join(payload)
    marks = ', '.join('?' for _ in payload)
    with _connect() as conn:
        cur = conn.execute(f'INSERT INTO {table} ({fields}) VALUES ({marks})', tuple(payload.values()))
        return int(cur.lastrowid)


def _update(table: str, row_id: int, payload: dict) -> None:
    assignments = ', '.join(f'{field} = ?' for field in payload)
    with _connect() as conn:
        conn.execute(f'UPDATE {table} SET {assignments} WHERE id = ?', (*payload.values(), row_id))


def go_to_legal_matrix_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/matriz-legal')


def register_legal_matrix_module(ui, deps: dict) -> None:
    _ensure_tables()
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']

    @ui.page('/sistema-gestion/matriz-legal')
    def legal_matrix_page() -> None:
        if not ensure_platform_access():
            return
        _inject_legal_design()
        company_map = company_options()
        company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        company_id = int(company_id) if company_id else (next(iter(company_map)) if company_map else None)
        container = shell('Matriz Legal Digital', back_route='/sistema-gestion', module_key='legal_matrix')
        with container:
            with ui.column().classes('legal-page w-full gap-4'):
                if not company_id:
                    ui.label('Seleccioná una empresa para comenzar.').classes('text-slate-500')
                    return

                empresa = obtener_empresa_detalle(company_id) or {}
                company_name = str(empresa.get('razon_social') or company_map.get(company_id) or '')
                local_role = str(app.storage.user.get('local_user_role') or '').strip().upper()
                role_label = 'Administrador' if local_role in {'IDEAS_ADMIN', 'EMPRESA_ADMIN'} else 'Editor'
                can_manage = local_role in {'IDEAS_ADMIN', 'EMPRESA_ADMIN'}

                with ui.row().classes('legal-header w-full justify-between items-start gap-4'):
                    with ui.column().classes('gap-1'):
                        ui.label('CUMPLIMIENTO Y TRAZABILIDAD').classes('legal-kicker')
                        ui.label('Matriz Legal Digital').classes('legal-title')
                        ui.label(f'{company_name} · Marco normativo, auditorías, evidencias y alertas.').classes('legal-subtitle')
                    with ui.column().classes('items-end gap-2'):
                        ui.label('Actualización normativa · hoy').classes('legal-update')
                        if str(app.storage.user.get('role') or '') == 'admin':
                            selector = ui.select(company_map, value=company_id, label='Empresa').classes('min-w-[280px]').props('outlined dense')
                            def change_company(_e=None):
                                if selector.value:
                                    app.storage.user['management_company_id'] = int(selector.value)
                                    set_selection(int(selector.value), None)
                                    ui.navigate.to('/sistema-gestion/matriz-legal')
                            selector.on_value_change(change_company)

                with ui.row().classes('legal-rolebar w-full items-center justify-between'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('verified_user').classes('text-lg')
                        ui.label(f'Perfil activo: {role_label}').classes('text-sm font-semibold')
                    ui.label('Información confidencial · acceso registrado en bitácora').classes('text-xs opacity-80')

                reqs = _rows('SELECT * FROM legal_requirements WHERE empresa_id = ? ORDER BY criticidad DESC, titulo', (company_id,))
                sites = _rows('SELECT * FROM legal_sites WHERE empresa_id = ? AND activo = 1 ORDER BY nombre', (company_id,))
                evidences = _rows('SELECT * FROM legal_evidence WHERE empresa_id = ? ORDER BY created_at DESC', (company_id,))
                audits = _rows('SELECT * FROM legal_audits WHERE empresa_id = ? ORDER BY fecha DESC', (company_id,))
                alerts = _rows("SELECT * FROM legal_alerts WHERE empresa_id = ? AND estado != 'Cerrada' ORDER BY fecha DESC", (company_id,))
                compliant = sum(1 for row in reqs if row['estado'] == 'Cumple')
                percentage = round(compliant * 100 / len(reqs)) if reqs else 0

                with ui.grid(columns=4).classes('w-full gap-3'):
                    for label, value, icon, color in (
                        ('Cumplimiento', f'{percentage}%', 'verified', 'text-emerald-700'),
                        ('Requisitos vigentes', len(reqs), 'gavel', 'text-blue-700'),
                        ('Alertas abiertas', len(alerts), 'notifications_active', 'text-amber-700'),
                        ('Evidencias', len(evidences), 'folder_copy', 'text-violet-700'),
                    ):
                        with ui.card().classes('legal-kpi'):
                            with ui.row().classes('w-full justify-between items-start'):
                                ui.icon(icon).classes(f'legal-kpi-icon text-xl {color}')
                                ui.label('ACTIVO').classes('text-[10px] text-slate-400 tracking-wider')
                            ui.label(str(value)).classes('legal-kpi-value')
                            ui.label(label).classes('legal-kpi-label')

                with ui.tabs().classes('legal-tabs w-full') as tabs:
                    dashboard_tab = ui.tab('Resumen', icon='dashboard').props('no-caps')
                    matrix_tab = ui.tab('Matriz legal', icon='gavel').props('no-caps')
                    sites_tab = ui.tab('Sedes', icon='location_on').props('no-caps')
                    audits_tab = ui.tab('Auditorías', icon='fact_check').props('no-caps')
                    evidence_tab = ui.tab('Evidencias', icon='folder_copy').props('no-caps')
                    alerts_tab = ui.tab('Alertas', icon='notifications_active').props('no-caps')
                    trace_tab = ui.tab('Bitácora', icon='history').props('no-caps')

            with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full bg-transparent'):
                with ui.tab_panel(dashboard_tab).classes('px-0'):
                    with ui.grid(columns=2).classes('w-full gap-3 mt-3'):
                        with ui.card().classes('legal-panel'):
                            ui.label(f'Estado legal · {company_name}').classes('legal-section-title')
                            ui.echart({'tooltip': {'trigger': 'item'}, 'series': [{'type': 'pie', 'radius': ['48%', '72%'], 'data': [
                                {'name': status, 'value': sum(1 for row in reqs if row['estado'] == status)}
                                for status in ('Cumple', 'En proceso', 'No cumple', 'Pendiente')
                            ]}]}).classes('w-full h-72')
                        with ui.card().classes('legal-panel'):
                            ui.label('Cobertura por ámbito').classes('legal-section-title')
                            scopes = ('Seguridad', 'Salud Ocupacional', 'Medio Ambiente', 'Otras')
                            ui.echart({'xAxis': {'type': 'category', 'data': list(scopes)}, 'yAxis': {'type': 'value'},
                                       'series': [{'type': 'bar', 'data': [sum(1 for row in reqs if row['ambito'] == scope) for scope in scopes]}]}).classes('w-full h-72')

                with ui.tab_panel(matrix_tab).classes('px-0'):
                    host = ui.column().classes('w-full')
                    def matrix_form(row=None):
                        row = row or {}
                        with ui.dialog() as dlg, ui.card().classes('w-[1050px] max-w-[97vw] ideas-panel p-5'):
                            ui.label('Editar requisito' if row else 'Nuevo requisito legal').classes('text-xl font-bold')
                            with ui.grid(columns=3).classes('w-full gap-3'):
                                scope = ui.select(['Seguridad', 'Salud Ocupacional', 'Medio Ambiente', 'Otras'], value=row.get('ambito') or 'Medio Ambiente', label='Ámbito').props('outlined')
                                jurisdiction = ui.select(['Nacional', 'Provincial', 'Municipal'], value=row.get('jurisdiccion') or 'Nacional', label='Jurisdicción').props('outlined')
                                agency = ui.input('Organismo', value=row.get('organismo') or '').props('outlined')
                                norm_type = ui.select(['Ley', 'Decreto', 'Resolución', 'Disposición', 'Ordenanza', 'Otra'], value=row.get('tipo_norma') or 'Ley', label='Tipo').props('outlined')
                                number = ui.input('Número', value=row.get('numero') or '').props('outlined')
                                title = ui.input('Título de la norma', value=row.get('titulo') or '').props('outlined')
                                article = ui.input('Artículo aplicable', value=row.get('articulo') or '').props('outlined')
                                owner = ui.input('Responsable', value=row.get('responsable') or '').props('outlined')
                                status = ui.select(['Pendiente', 'En proceso', 'Cumple', 'No cumple'], value=row.get('estado') or 'Pendiente', label='Estado').props('outlined')
                                criticality = ui.select(['Baja', 'Media', 'Alta', 'Crítica'], value=row.get('criticidad') or 'Media', label='Criticidad').props('outlined')
                                review = ui.input('Próxima revisión', value=row.get('proxima_revision') or '', placeholder='AAAA-MM-DD').props('outlined')
                                frequency = ui.input('Frecuencia de control', value=row.get('frecuencia') or '').props('outlined')
                            obligation = ui.textarea('Obligación / requisito verificable', value=row.get('obligacion') or '').classes('w-full').props('outlined autogrow')
                            evidence = ui.textarea('Evidencia requerida', value=row.get('evidencia_requerida') or '').classes('w-full').props('outlined autogrow')
                            def save():
                                if not str(title.value or '').strip():
                                    ui.notify('El título de la norma es obligatorio.', type='warning'); return
                                payload = {'empresa_id': company_id, 'ambito': scope.value, 'jurisdiccion': jurisdiction.value,
                                    'organismo': agency.value or '', 'tipo_norma': norm_type.value, 'numero': number.value or '',
                                    'titulo': title.value, 'articulo': article.value or '', 'responsable': owner.value or '',
                                    'estado': status.value, 'criticidad': criticality.value, 'proxima_revision': review.value or '',
                                    'frecuencia': frequency.value or '', 'obligacion': obligation.value or '', 'evidencia_requerida': evidence.value or ''}
                                if row.get('id'):
                                    payload.pop('empresa_id'); payload['updated_at'] = datetime.now().isoformat(timespec='seconds')
                                    _update('legal_requirements', int(row['id']), payload); rid = int(row['id']); action = 'MODIFICACIÓN'
                                else:
                                    rid = _insert('legal_requirements', payload); action = 'ALTA'
                                _log(company_id, action, 'requisito legal', rid, str(title.value)); dlg.close(); ui.navigate.to('/sistema-gestion/matriz-legal')
                            with ui.row().classes('w-full justify-end gap-2'):
                                ui.button('Cancelar', on_click=dlg.close).props('flat')
                                ui.button('Guardar', icon='save', on_click=save).props('unelevated color=primary')
                        dlg.open()
                    def export_matrix():
                        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=['ambito','jurisdiccion','organismo','tipo_norma','numero','titulo','articulo','obligacion','responsable','estado','criticidad','proxima_revision']); writer.writeheader()
                        for row in reqs: writer.writerow({key: row.get(key, '') for key in writer.fieldnames})
                        ui.download(output.getvalue().encode('utf-8-sig'), f'matriz_legal_{company_id}.csv')
                        _log(company_id, 'EXPORTACIÓN', 'matriz legal', None, 'CSV')
                    with host:
                        with ui.row().classes('w-full justify-between items-center'):
                            ui.label('Requisitos aplicables').classes('legal-section-title')
                            with ui.row().classes('gap-2'):
                                ui.button('Exportar Excel/CSV', icon='download', on_click=export_matrix).props('outline color=primary')
                                ui.button('Nueva norma', icon='add', on_click=lambda: matrix_form()).props('unelevated color=primary')
                        columns = [{'name': k, 'label': label, 'field': k, 'align': 'left'} for k, label in [('ambito','Ámbito'),('jurisdiccion','Jurisdicción'),('norma','Norma'),('titulo','Requisito'),('estado','Estado'),('criticidad','Criticidad'),('responsable','Responsable'),('revision','Próxima revisión'),('acciones','Acciones')]]
                        data = [{**row, 'norma': f"{row['tipo_norma']} {row['numero']}", 'revision': row['proxima_revision'], 'acciones': ''} for row in reqs]
                        table = ui.table(columns=columns, rows=data, row_key='id', pagination=12).classes('w-full legal-table')
                        table.add_slot('body-cell-acciones', '<q-td :props="props"><q-btn flat dense round icon="edit" color="primary" @click="$parent.$emit(\'edit\', props.row.id)" /></q-td>')
                        table.on('edit', lambda e: matrix_form(next((r for r in reqs if r['id'] == int(e.args)), None)))

                with ui.tab_panel(sites_tab).classes('px-0'):
                    def site_form():
                        with ui.dialog() as dlg, ui.card().classes('w-[720px] max-w-[95vw] ideas-panel'):
                            ui.label('Nueva sede operativa').classes('text-xl font-bold'); name = ui.input('Nombre').classes('w-full').props('outlined'); location = ui.input('Ubicación').classes('w-full').props('outlined'); jurisdiction = ui.input('Jurisdicción').classes('w-full').props('outlined'); activity = ui.input('Actividad / procesos').classes('w-full').props('outlined')
                            def save():
                                rid = _insert('legal_sites', {'empresa_id': company_id, 'nombre': name.value or '', 'ubicacion': location.value or '', 'jurisdiccion': jurisdiction.value or '', 'actividad': activity.value or ''}); _log(company_id, 'ALTA', 'sede', rid, name.value or ''); dlg.close(); ui.navigate.to('/sistema-gestion/matriz-legal')
                            ui.button('Guardar sede', icon='save', on_click=save).props('unelevated color=primary')
                        dlg.open()
                    ui.button('Nueva sede', icon='add_location', on_click=site_form).props('unelevated color=primary').classes('mb-3')
                    ui.table(columns=[{'name':k,'label':l,'field':k,'align':'left'} for k,l in [('nombre','Sede'),('ubicacion','Ubicación'),('jurisdiccion','Jurisdicción'),('actividad','Actividad')]], rows=sites, row_key='id').classes('w-full legal-table')

                with ui.tab_panel(audits_tab).classes('px-0'):
                    def audit_form():
                        with ui.dialog() as dlg, ui.card().classes('w-[850px] max-w-[96vw] ideas-panel'):
                            ui.label('Auditoría de cumplimiento').classes('text-xl font-bold'); audit_date = ui.input('Fecha', value=date.today().isoformat()).props('outlined'); auditor = ui.input('Auditor').props('outlined'); scope = ui.textarea('Alcance').classes('w-full').props('outlined'); result = ui.select(['Planificada','En curso','Conforme','Con hallazgos','Cerrada'], value='Planificada', label='Resultado').props('outlined'); findings = ui.textarea('Hallazgos').classes('w-full').props('outlined'); plan = ui.textarea('Plan de acción').classes('w-full').props('outlined')
                            def save():
                                rid = _insert('legal_audits', {'empresa_id': company_id, 'fecha': audit_date.value, 'auditor': auditor.value or '', 'alcance': scope.value or '', 'resultado': result.value, 'hallazgos': findings.value or '', 'plan_accion': plan.value or ''}); _log(company_id, 'ALTA', 'auditoría', rid, audit_date.value); dlg.close(); ui.navigate.to('/sistema-gestion/matriz-legal')
                            ui.button('Guardar auditoría', icon='save', on_click=save).props('unelevated color=primary')
                        dlg.open()
                    ui.button('Programar auditoría', icon='event', on_click=audit_form).props('unelevated color=primary').classes('mb-3')
                    ui.table(columns=[{'name':k,'label':l,'field':k,'align':'left'} for k,l in [('fecha','Fecha'),('auditor','Auditor'),('alcance','Alcance'),('resultado','Resultado'),('hallazgos','Hallazgos'),('plan_accion','Plan de acción')]], rows=audits, row_key='id').classes('w-full legal-table')

                with ui.tab_panel(evidence_tab).classes('px-0'):
                    req_options = {row['id']: row['titulo'] for row in reqs}
                    selected_req = ui.select(req_options, label='Requisito asociado').classes('w-full').props('outlined')
                    comment = ui.input('Descripción de la evidencia').classes('w-full').props('outlined')
                    def upload_file(e: events.UploadEventArguments):
                        if not selected_req.value:
                            ui.notify('Seleccioná primero un requisito.', type='warning'); return
                        folder = UPLOAD_DIR / f'empresa_{company_id}'; folder.mkdir(parents=True, exist_ok=True); target = folder / Path(e.name).name; target.write_bytes(e.content.read())
                        rid = _insert('legal_evidence', {'empresa_id': company_id, 'requirement_id': int(selected_req.value), 'nombre': Path(e.name).name, 'archivo_path': str(target), 'comentario': comment.value or '', 'cargado_por': _user_name()}); _log(company_id, 'ALTA', 'evidencia', rid, Path(e.name).name); ui.notify('Evidencia cargada.', type='positive'); ui.navigate.to('/sistema-gestion/matriz-legal')
                    ui.upload(on_upload=upload_file, auto_upload=True, label='Cargar documento o evidencia').classes('w-full mt-3')
                    ui.table(columns=[{'name':k,'label':l,'field':k,'align':'left'} for k,l in [('nombre','Documento'),('comentario','Descripción'),('estado_aprobacion','Aprobación'),('cargado_por','Usuario'),('created_at','Fecha')]], rows=evidences, row_key='id').classes('w-full legal-table mt-3')

                with ui.tab_panel(alerts_tab).classes('px-0'):
                    def alert_form():
                        with ui.dialog() as dlg, ui.card().classes('w-[760px] max-w-[95vw] ideas-panel'):
                            ui.label('Nueva alerta normativa').classes('text-xl font-bold'); title = ui.input('Título').classes('w-full').props('outlined'); detail = ui.textarea('Detalle del cambio o vencimiento').classes('w-full').props('outlined'); priority = ui.select(['Baja','Media','Alta','Crítica'], value='Media', label='Prioridad').props('outlined')
                            def save():
                                rid = _insert('legal_alerts', {'empresa_id': company_id, 'titulo': title.value or '', 'detalle': detail.value or '', 'prioridad': priority.value}); _log(company_id, 'ALTA', 'alerta', rid, title.value or ''); dlg.close(); ui.navigate.to('/sistema-gestion/matriz-legal')
                            ui.button('Publicar alerta', icon='notifications', on_click=save).props('unelevated color=primary')
                        dlg.open()
                    ui.button('Nueva alerta', icon='add_alert', on_click=alert_form).props('unelevated color=primary').classes('mb-3')
                    ui.table(columns=[{'name':k,'label':l,'field':k,'align':'left'} for k,l in [('prioridad','Prioridad'),('titulo','Alerta'),('detalle','Detalle'),('estado','Estado'),('fecha','Fecha')]], rows=alerts, row_key='id').classes('w-full legal-table')

                with ui.tab_panel(trace_tab).classes('px-0'):
                    logs = _rows('SELECT * FROM legal_audit_log WHERE empresa_id = ? ORDER BY id DESC LIMIT 500', (company_id,))
                    def export_log():
                        output = io.StringIO(); writer = csv.DictWriter(output, fieldnames=['created_at','usuario','accion','entidad','entidad_id','detalle']); writer.writeheader()
                        for row in logs: writer.writerow({key: row.get(key, '') for key in writer.fieldnames})
                        ui.download(output.getvalue().encode('utf-8-sig'), f'bitacora_legal_{company_id}.csv')
                    ui.button('Exportar bitácora', icon='download', on_click=export_log).props('outline color=primary').classes('mb-3')
                    ui.table(columns=[{'name':k,'label':l,'field':k,'align':'left'} for k,l in [('created_at','Fecha y hora'),('usuario','Usuario'),('accion','Acción'),('entidad','Entidad'),('detalle','Detalle')]], rows=logs, row_key='id', pagination=15).classes('w-full legal-table')
