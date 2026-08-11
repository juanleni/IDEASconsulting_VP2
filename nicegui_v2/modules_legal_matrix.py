"""Módulo de UI/rutas HTTP de Matriz Legal Digital: la página NiceGUI que aloja
el iframe de diseño, y las rutas FastAPI que ese iframe consume (CRUD de
requisitos/sedes/auditorías/evidencias/alertas, export de PDF, importación de
Excel, notificación al cliente).

Toda la lógica de negocio y acceso a datos (conexión a la DB, alertas de
vencimiento, resumen de cambios, contexto del reporte, parsing de Excel,
transformaciones al formato del diseño) vive en legal_matrix_service.py desde
el 2026-08-10 (Fase 4, extracción de capa de servicios). Este archivo
re-importa todo lo que necesita desde ahí para que el resto del código
(app.py, modules_legal_curation.py, mobile_legal_matrix/data.py,
services/legal_matrix_alert_scheduler.py) siga pudiendo hacer
`from modules_legal_matrix import ...` sin cambios.
"""
from __future__ import annotations

import asyncio
from datetime import date, datetime

from fastapi import File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from nicegui import app, ui
from company_context import empresa_id_from_query_for_admin, with_empresa_id

from ideas_utils import enviar_correo_actualizacion_matriz_legal
from legal_matrix_pdf import generar_pdf_reporte_legal_matrix

from legal_matrix_service import (
    DB_PATH,
    DESIGN_HTML_PATH,
    DEFAULT_DELETE_ALL_PASSWORD,
    _connect,
    _ensure_tables,
    _hash_password,
    _verify_password,
    tiene_legal_matrix_password_personalizada,
    verificar_legal_matrix_delete_password,
    guardar_legal_matrix_delete_password,
    obtener_legal_matrix_alert_settings,
    guardar_legal_matrix_alert_settings,
    obtener_legal_matrix_alertas_vencimiento_abiertas,
    marcar_legal_matrix_alertas_enviadas,
    generar_alertas_vencimientos,
    generar_resumen_cambios_pendientes,
    _user_name,
    _log,
    _rows,
    _insert,
    _insert_many,
    _update,
    _fmt_fecha_es,
    _fmt_fecha_larga_es,
    construir_contexto_reporte_legal_matrix,
    _norm_status,
    _norm_criticality,
    _norm_audit_status,
    _norm_approval,
    _requirement_to_design,
    _site_to_design,
    _audit_to_design,
    _evidence_to_design,
    _alert_to_design,
    _log_to_design,
    _is_matrix_admin,
    _is_ideas_staff,
    _build_design_context,
    _render_design_page,
    _xlsx_text,
    _norm_header,
    _find_legal_matrix_header,
    _parse_legal_matrix_excel,
)

__all__ = [
    'DB_PATH', 'DESIGN_HTML_PATH', 'go_to_legal_matrix_module', 'register_legal_matrix_module',
]


def go_to_legal_matrix_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to(with_empresa_id('/sistema-gestion/matriz-legal', company_id))


def register_legal_matrix_module(ui, deps: dict) -> None:
    _ensure_tables()
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']

    def _frame_guard(empresa_id: int) -> bool:
        if not app.storage.user.get('platform_auth'):
            return False
        role = str(app.storage.user.get('role') or '')
        if role == 'empresa':
            logged = app.storage.user.get('logged_empresa_id')
            try:
                return int(logged) == int(empresa_id)
            except (TypeError, ValueError):
                return False
        return True

    @ui.page('/sistema-gestion/matriz-legal')
    def legal_matrix_page() -> None:
        if not ensure_platform_access():
            return
        company_map = company_options()
        query_empresa_id = empresa_id_from_query_for_admin()
        company_id = query_empresa_id or app.storage.user.get('management_company_id') or current_selection()[0]
        company_id = int(company_id) if company_id else (next(iter(company_map)) if company_map else None)
        if query_empresa_id and company_id:
            app.storage.user['management_company_id'] = company_id
            set_selection(company_id, None)
        container = shell('Matriz Legal Digital', back_route='/sistema-gestion', module_key='legal_matrix')
        with container:
            with ui.column().classes('w-full gap-3'):
                if not company_id:
                    ui.label('Seleccioná una empresa para comenzar.').classes('text-slate-500')
                    return

                if str(app.storage.user.get('role') or '') == 'admin':
                    with ui.row().classes('w-full justify-end'):
                        selector = ui.select(company_map, value=company_id, label='Empresa').classes('min-w-[280px]').props('outlined dense')

                        def change_company(_e=None) -> None:
                            if selector.value:
                                app.storage.user['management_company_id'] = int(selector.value)
                                set_selection(int(selector.value), None)
                                ui.navigate.to(with_empresa_id('/sistema-gestion/matriz-legal', selector.value))

                        selector.on_value_change(change_company)

                ui.html(
                    f'<iframe src="/legal-matrix-frame/{company_id}" '
                    'style="width:100%;height:calc(100vh - 190px);border:none;border-radius:20px;'
                    'background:#F2F5F9;display:block;" loading="lazy"></iframe>',
                    sanitize=False,
                ).classes('w-full')

    @app.get('/legal-matrix-frame/{empresa_id}')
    def legal_matrix_frame(empresa_id: int):
        if not _frame_guard(empresa_id):
            return HTMLResponse('<p style="font-family:sans-serif;padding:24px;">Acceso no autorizado.</p>', status_code=403)
        empresa = obtener_empresa_detalle(empresa_id) or {}
        company_name = str(empresa.get('razon_social') or company_options().get(empresa_id) or '')
        contact_email = str(empresa.get('contacto_correo') or '').strip()
        return HTMLResponse(_render_design_page(empresa_id, company_name, contact_email))

    @app.get('/api/legal-matrix/{empresa_id}/export-pdf')
    def export_legal_matrix_pdf(empresa_id: int):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        empresa = obtener_empresa_detalle(empresa_id) or {}
        company_name = str(empresa.get('razon_social') or company_options().get(empresa_id) or '')
        contexto = construir_contexto_reporte_legal_matrix(empresa_id)
        pdf_path = generar_pdf_reporte_legal_matrix(
            empresa_id, company_name, _fmt_fecha_larga_es(date.today()), contexto,
        )
        return FileResponse(
            str(pdf_path), media_type='application/pdf',
            headers={'Content-Disposition': f'inline; filename="{pdf_path.name}"'},
        )

    @app.post('/api/legal-matrix/{empresa_id}/requirements')
    async def create_legal_requirement(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        rid = _insert('legal_requirements', {
            'empresa_id': empresa_id,
            'site_id': int(payload['siteId']) if payload.get('siteId') else None,
            'ambito': payload.get('scope') or 'Medio Ambiente',
            'jurisdiccion': payload.get('jurisdiction') or 'Nacional',
            'organismo': payload.get('agency') or '',
            'tipo_norma': payload.get('normType') or 'Ley',
            'numero': payload.get('normNumber') or '',
            'titulo': payload.get('title') or '',
            'obligacion': payload.get('obligation') or '',
            'responsable': payload.get('responsible') or '',
            'estado': payload.get('status') or 'pendiente',
            'criticidad': payload.get('criticality') or 'media',
            'proxima_revision': payload.get('nextReview') or '',
        })
        _log(empresa_id, 'ALTA', 'requisito legal', rid, str(payload.get('title') or ''))
        return JSONResponse({'id': rid})

    @app.post('/api/legal-matrix/{empresa_id}/requirements/import')
    async def import_legal_requirements(empresa_id: int, file: UploadFile = File(...)):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        content = await file.read()

        def _process() -> int:
            rows = _parse_legal_matrix_excel(content)
            for row in rows:
                row['empresa_id'] = empresa_id
            return _insert_many('legal_requirements', rows)

        try:
            imported = await asyncio.to_thread(_process)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))
        _log(empresa_id, 'IMPORTACIÓN', 'matriz legal', None, f'{imported} normas desde {file.filename}')
        return JSONResponse({'imported': imported})

    @app.put('/api/legal-matrix/{empresa_id}/requirements/{req_id}')
    async def update_legal_requirement(empresa_id: int, req_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        _update('legal_requirements', req_id, {
            'site_id': int(payload['siteId']) if payload.get('siteId') else None,
            'ambito': payload.get('scope') or 'Medio Ambiente',
            'jurisdiccion': payload.get('jurisdiction') or 'Nacional',
            'organismo': payload.get('agency') or '',
            'tipo_norma': payload.get('normType') or 'Ley',
            'numero': payload.get('normNumber') or '',
            'titulo': payload.get('title') or '',
            'obligacion': payload.get('obligation') or '',
            'responsable': payload.get('responsible') or '',
            'estado': payload.get('status') or 'pendiente',
            'criticidad': payload.get('criticality') or 'media',
            'proxima_revision': payload.get('nextReview') or '',
            'updated_at': datetime.now().isoformat(timespec='seconds'),
        })
        _log(empresa_id, 'MODIFICACIÓN', 'requisito legal', req_id, str(payload.get('title') or ''))
        return JSONResponse({'ok': True})

    @app.delete('/api/legal-matrix/{empresa_id}/requirements/{req_id}')
    def delete_legal_requirement(empresa_id: int, req_id: int):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        with _connect() as conn:
            conn.execute('DELETE FROM legal_requirements WHERE id = ? AND empresa_id = ?', (req_id, empresa_id))
        _log(empresa_id, 'BAJA', 'requisito legal', req_id, '')
        return JSONResponse({'ok': True})

    @app.post('/api/legal-matrix/{empresa_id}/requirements/delete-bulk')
    async def delete_legal_requirements_bulk(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        ids = [int(item) for item in (payload.get('ids') or [])]
        if not ids:
            return JSONResponse({'deleted': 0})
        marks = ', '.join('?' for _ in ids)
        with _connect() as conn:
            cur = conn.execute(
                f'DELETE FROM legal_requirements WHERE empresa_id = ? AND id IN ({marks})',
                (empresa_id, *ids),
            )
            deleted = cur.rowcount
        _log(empresa_id, 'BAJA MASIVA', 'requisito legal', None, f'{deleted} norma(s) seleccionada(s)')
        return JSONResponse({'deleted': deleted})

    @app.post('/api/legal-matrix/{empresa_id}/requirements/delete-all')
    async def delete_legal_requirements_all(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        if not _is_matrix_admin():
            raise HTTPException(status_code=403, detail='Solo un administrador puede eliminar toda la matriz legal.')
        payload = await request.json()
        password = str(payload.get('password') or '')
        if not verificar_legal_matrix_delete_password(empresa_id, password):
            raise HTTPException(status_code=401, detail='Contraseña incorrecta.')
        with _connect() as conn:
            cur = conn.execute('DELETE FROM legal_requirements WHERE empresa_id = ?', (empresa_id,))
            deleted = cur.rowcount
        _log(empresa_id, 'BAJA TOTAL', 'requisito legal', None, f'{deleted} norma(s) eliminadas (borrado total)')
        return JSONResponse({'deleted': deleted})

    @app.post('/api/legal-matrix/{empresa_id}/sites')
    async def create_legal_site(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        rid = _insert('legal_sites', {
            'empresa_id': empresa_id,
            'nombre': payload.get('name') or '',
            'ubicacion': payload.get('address') or payload.get('municipality') or '',
            'jurisdiccion': payload.get('province') or '',
            'actividad': payload.get('activity') or payload.get('processes') or '',
        })
        _log(empresa_id, 'ALTA', 'sede', rid, str(payload.get('name') or ''))
        return JSONResponse({'id': rid})

    @app.put('/api/legal-matrix/{empresa_id}/sites/{site_id}')
    async def update_legal_site(empresa_id: int, site_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        _update('legal_sites', site_id, {
            'nombre': payload.get('name') or '',
            'ubicacion': payload.get('address') or payload.get('municipality') or '',
            'jurisdiccion': payload.get('province') or '',
            'actividad': payload.get('activity') or payload.get('processes') or '',
            'activo': 1 if payload.get('active', True) else 0,
        })
        _log(empresa_id, 'MODIFICACIÓN', 'sede', site_id, str(payload.get('name') or ''))
        return JSONResponse({'ok': True})

    @app.post('/api/legal-matrix/{empresa_id}/audits')
    async def create_legal_audit(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        rid = _insert('legal_audits', {
            'empresa_id': empresa_id,
            'site_id': int(payload['siteId']) if payload.get('siteId') else None,
            'fecha': payload.get('date') or date.today().isoformat(),
            'tipo': payload.get('type') or 'Interna',
            'auditor': payload.get('auditor') or '',
            'alcance': payload.get('scope') or '',
            'resultado': 'programada',
        })
        _log(empresa_id, 'ALTA', 'auditoría', rid, str(payload.get('date') or ''))
        return JSONResponse({'id': rid})

    @app.post('/api/legal-matrix/{empresa_id}/evidence')
    async def create_legal_evidence(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        payload = await request.json()
        if not payload.get('requirementId'):
            raise HTTPException(status_code=400, detail='requirementId requerido')
        rid = _insert('legal_evidence', {
            'empresa_id': empresa_id,
            'requirement_id': int(payload['requirementId']),
            'nombre': payload.get('name') or '',
            'cargado_por': payload.get('user') or _user_name(),
        })
        _log(empresa_id, 'ALTA', 'evidencia', rid, str(payload.get('name') or ''))
        return JSONResponse({'id': rid})

    @app.post('/api/legal-matrix/{empresa_id}/evidence/{evidence_id}/approve')
    def approve_legal_evidence(empresa_id: int, evidence_id: int):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        _update('legal_evidence', evidence_id, {'estado_aprobacion': 'aprobado'})
        _log(empresa_id, 'APROBACIÓN', 'evidencia', evidence_id, '')
        return JSONResponse({'ok': True})

    @app.post('/api/legal-matrix/{empresa_id}/alerts/{alert_id}/resolve')
    def resolve_legal_alert(empresa_id: int, alert_id: int):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        _update('legal_alerts', alert_id, {'estado': 'Cerrada'})
        _log(empresa_id, 'RESOLUCIÓN', 'alerta', alert_id, '')
        return JSONResponse({'ok': True})

    @app.get('/api/legal-matrix/{empresa_id}/changes-summary')
    def legal_matrix_changes_summary(empresa_id: int):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        if not _is_ideas_staff():
            raise HTTPException(status_code=403)
        return JSONResponse(generar_resumen_cambios_pendientes(empresa_id))

    @app.post('/api/legal-matrix/{empresa_id}/notify-update')
    async def notify_legal_matrix_update(empresa_id: int, request: Request):
        if not _frame_guard(empresa_id):
            raise HTTPException(status_code=403)
        if not _is_ideas_staff():
            raise HTTPException(status_code=403, detail='Solo el equipo de IDEAS puede publicar actualizaciones al cliente.')
        payload = await request.json()
        resumen = str(payload.get('summary') or '').strip()
        if not resumen:
            raise HTTPException(status_code=400, detail='Ingresá un resumen de la actualización.')
        empresa = obtener_empresa_detalle(empresa_id) or {}
        correo = str(empresa.get('contacto_correo') or '').strip()
        if not correo:
            raise HTTPException(status_code=400, detail='La empresa no tiene un correo de contacto configurado.')
        company_name = str(empresa.get('razon_social') or company_options().get(empresa_id) or '')
        resultado = await asyncio.to_thread(
            enviar_correo_actualizacion_matriz_legal, correo, company_name, resumen, _user_name(),
        )
        _insert('legal_matrix_updates', {
            'empresa_id': empresa_id,
            'resumen': resumen,
            'destinatario': correo,
            'enviado_por': _user_name(),
            'enviado_ok': 1 if resultado.get('ok') else 0,
        })
        _log(empresa_id, 'NOTIFICACIÓN', 'actualización matriz legal', None, resumen)
        return JSONResponse({'ok': bool(resultado.get('ok')), 'to': correo})
