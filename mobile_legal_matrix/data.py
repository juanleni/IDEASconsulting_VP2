"""Capa de datos del prototipo mobile de Matriz Legal.

No duplica el modelo de datos: reutiliza directamente las tablas, el
esquema y las funciones ya probadas de ``nicegui_v2/modules_legal_matrix.py``
y ``nicegui_v2/core_data.py`` (misma base ideas.db). Este módulo sólo agrega
consultas de lectura/escritura simples, sin el guardado de sesión/roles de
la plataforma original (a propósito: esta app todavía no tiene gestión de
usuarios).
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NICEGUI_V2_DIR = ROOT / 'nicegui_v2'
os.chdir(ROOT)  # modules_legal_matrix / core_data usan rutas relativas ("ideas.db")
for _p in (ROOT, NICEGUI_V2_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core_data import obtener_empresas, obtener_empresa_detalle  # noqa: E402  (reutilizado)
from modules_legal_matrix import (  # noqa: E402  (reutilizado, misma base y helpers que la plataforma)
    _connect,
    _ensure_tables,
    _fmt_fecha_es,
    _insert,
    _log,
    _norm_criticality,
    _norm_status,
    _rows,
    _update,
    generar_alertas_vencimientos,
)

EVIDENCE_DIR = Path(__file__).resolve().parent / 'evidence_files'  # fuera de data/: esa carpeta se sirve
                                                                    # públicamente bajo /assets, sin auth
EVIDENCE_ACCEPT = 'image/*,application/pdf'
EVIDENCE_MAX_BYTES = 15 * 1024 * 1024

formatear_fecha = _fmt_fecha_es
normalizar_estado = _norm_status
normalizar_criticidad = _norm_criticality

ESTADOS = ['Cumple', 'Pendiente', 'No cumple', 'No aplica']
CRITICIDADES = ['Alta', 'Media', 'Baja']
AMBITOS = ['Medio Ambiente', 'Salud Ocupacional', 'Seguridad e Higiene', 'Calidad']

ESTADO_STYLE = {
    'cumple': {'color': '#15803D', 'bg': '#DCFCE7', 'label': 'Cumple', 'icon': 'o_check_circle'},
    'pendiente': {'color': '#B45309', 'bg': '#FEF3C7', 'label': 'Pendiente', 'icon': 'o_schedule'},
    'no_cumple': {'color': '#B91C1C', 'bg': '#FEE2E2', 'label': 'No cumple', 'icon': 'o_cancel'},
    'no_aplica': {'color': '#6B7480', 'bg': '#EEF1F5', 'label': 'No aplica', 'icon': 'o_remove_circle'},
}
CRITICIDAD_STYLE = {
    'critica': {'color': '#B91C1C', 'label': 'Crítica'},
    'alta': {'color': '#B45309', 'label': 'Alta'},
    'media': {'color': '#0E3A53', 'label': 'Media'},
    'baja': {'color': '#6B7480', 'label': 'Baja'},
}
PRIORIDAD_STYLE = {
    'critica': {'color': '#B91C1C', 'label': 'Crítica'},
    'alta': {'color': '#B45309', 'label': 'Alta'},
    'media': {'color': '#0E3A53', 'label': 'Media'},
    'baja': {'color': '#6B7480', 'label': 'Baja'},
}

PRIMARY = '#0E3A53'


def _ensure() -> None:
    _ensure_tables()
    _ensure_evidence_source_column()


def _ensure_evidence_source_column() -> None:
    """Agrega legal_evidence.source (camera/gallery/file) de forma aditiva,
    igual patrón que ya usa _ensure_tables en modules_legal_matrix.py para
    columnas nuevas — no requiere tocar ese archivo, la migración vive acá
    porque es la app mobile la que introduce este campo."""
    with _connect() as conn:
        cols = {row[1] for row in conn.execute('PRAGMA table_info(legal_evidence)').fetchall()}
        if 'source' not in cols:
            conn.execute("ALTER TABLE legal_evidence ADD COLUMN source TEXT DEFAULT ''")


def listar_empresas() -> list[tuple[int, str]]:
    _ensure()
    return obtener_empresas()


def empresa_nombre(empresa_id: int) -> str:
    detalle = obtener_empresa_detalle(empresa_id) or {}
    return str(detalle.get('razon_social') or '')


def listar_sedes(empresa_id: int) -> list[dict]:
    return _rows('SELECT * FROM legal_sites WHERE empresa_id = ? ORDER BY nombre', (empresa_id,))


def listar_requisitos(empresa_id: int, estado: str | None = None, texto: str | None = None) -> list[dict]:
    rows = _rows(
        'SELECT * FROM legal_requirements WHERE empresa_id = ? ORDER BY updated_at DESC, id DESC',
        (empresa_id,),
    )
    for row in rows:
        row['estado_norm'] = _norm_status(row.get('estado'))
        row['criticidad_norm'] = _norm_criticality(row.get('criticidad'))
    if estado and estado != 'todas':
        rows = [r for r in rows if r['estado_norm'] == estado]
    if texto:
        needle = texto.strip().lower()
        rows = [
            r for r in rows
            if needle in (r.get('titulo') or '').lower()
            or needle in (r.get('numero') or '').lower()
            or needle in (r.get('organismo') or '').lower()
        ]
    return rows


def obtener_requisito(empresa_id: int, req_id: int) -> dict | None:
    rows = _rows(
        'SELECT * FROM legal_requirements WHERE empresa_id = ? AND id = ?', (empresa_id, req_id)
    )
    return rows[0] if rows else None


def crear_requisito(empresa_id: int, payload: dict) -> int:
    site_id = payload.get('site_id')
    rid = _insert('legal_requirements', {
        'empresa_id': empresa_id,
        'site_id': int(site_id) if site_id else None,
        'ambito': payload.get('ambito') or 'Medio Ambiente',
        'jurisdiccion': payload.get('jurisdiccion') or 'Nacional',
        'organismo': payload.get('organismo') or '',
        'tipo_norma': payload.get('tipo_norma') or 'Ley',
        'numero': payload.get('numero') or '',
        'titulo': payload.get('titulo') or '',
        'obligacion': payload.get('obligacion') or '',
        'responsable': payload.get('responsable') or '',
        'estado': payload.get('estado') or 'Pendiente',
        'criticidad': payload.get('criticidad') or 'Media',
        'proxima_revision': payload.get('proxima_revision') or '',
    })
    _log(empresa_id, 'ALTA', 'requisito legal', rid, str(payload.get('titulo') or ''))
    return rid


def actualizar_estado_requisito(empresa_id: int, req_id: int, nuevo_estado: str) -> None:
    _update('legal_requirements', req_id, {'estado': nuevo_estado})
    _log(empresa_id, 'MODIFICACIÓN', 'requisito legal', req_id, f'Estado -> {nuevo_estado} (app mobile)')


def listar_alertas(empresa_id: int, solo_abiertas: bool = True) -> list[dict]:
    query = 'SELECT * FROM legal_alerts WHERE empresa_id = ?'
    if solo_abiertas:
        query += " AND estado != 'Cerrada'"
    query += " ORDER BY CASE prioridad WHEN 'critica' THEN 0 WHEN 'alta' THEN 1 WHEN 'media' THEN 2 ELSE 3 END, fecha DESC"
    return _rows(query, (empresa_id,))


def resolver_alerta(empresa_id: int, alert_id: int) -> None:
    _update('legal_alerts', alert_id, {'estado': 'Cerrada'})
    _log(empresa_id, 'RESOLUCIÓN', 'alerta', alert_id, '(app mobile)')


def contar_alertas_abiertas(empresa_id: int) -> int:
    return len(listar_alertas(empresa_id, solo_abiertas=True))


def generar_alertas_por_vencer(empresa_id: int, dias: int = 30) -> list[dict]:
    return generar_alertas_vencimientos(empresa_id, dias)


def listar_evidencias(empresa_id: int, requirement_id: int) -> list[dict]:
    return _rows(
        'SELECT * FROM legal_evidence WHERE empresa_id = ? AND requirement_id = ? ORDER BY created_at DESC',
        (empresa_id, requirement_id),
    )


def evidencia_por_id(empresa_id: int, evidence_id: int) -> dict | None:
    rows = _rows(
        'SELECT * FROM legal_evidence WHERE empresa_id = ? AND id = ?', (empresa_id, evidence_id)
    )
    return rows[0] if rows else None


def ruta_evidencia(evidencia: dict) -> Path:
    return EVIDENCE_DIR / str(evidencia['archivo_path'])


def guardar_evidencia(
    empresa_id: int, requirement_id: int, filename: str, contenido: bytes, origen: str, cargado_por: str,
) -> int:
    """Guarda el archivo en mobile_legal_matrix/data/evidence/ (fuera de /assets,
    que se sirve sin control de acceso) y registra la fila en legal_evidence,
    la misma tabla que usa la plataforma principal."""
    _ensure_evidence_source_column()
    ext = Path(filename or '').suffix.lower()
    ext = ext if ext.replace('.', '').isalnum() and len(ext) <= 6 else ''
    unique_name = f'{uuid.uuid4().hex}{ext}'
    rel_path = f'{empresa_id}/{requirement_id}/{unique_name}'
    target = EVIDENCE_DIR / rel_path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(contenido)

    rid = _insert('legal_evidence', {
        'empresa_id': empresa_id,
        'requirement_id': requirement_id,
        'nombre': filename or unique_name,
        'archivo_path': rel_path,
        'cargado_por': cargado_por or 'sistema',
        'source': origen or '',
    })
    _log(empresa_id, 'ALTA', 'evidencia', rid, str(filename or ''))
    return rid


def dashboard(empresa_id: int) -> dict:
    reqs = listar_requisitos(empresa_id)
    total = len(reqs)
    conteos = {'cumple': 0, 'pendiente': 0, 'no_cumple': 0, 'no_aplica': 0}
    for r in reqs:
        conteos[r['estado_norm']] += 1
    base = total - conteos['no_aplica'] or 1
    pct_cumplimiento = round((conteos['cumple'] / base) * 100) if total else 0

    hoy = date.today().isoformat()
    limite_30 = str(date.fromordinal(date.today().toordinal() + 30))
    proximas = [
        r for r in reqs
        if r.get('proxima_revision') and hoy <= r['proxima_revision'] <= limite_30
    ]
    vencidas = [r for r in reqs if r.get('proxima_revision') and r['proxima_revision'] < hoy]

    alertas_abiertas = listar_alertas(empresa_id, solo_abiertas=True)
    sedes = listar_sedes(empresa_id)

    return {
        'total': total,
        'conteos': conteos,
        'pct_cumplimiento': pct_cumplimiento,
        'proximas_30d': len(proximas),
        'vencidas': len(vencidas),
        'alertas_abiertas': len(alertas_abiertas),
        'sedes': len(sedes),
    }
