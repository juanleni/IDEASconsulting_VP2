"""Curación de normativa para Matriz Legal Digital — uso exclusivo de IDEAS_ADMIN.

Todo lo de acá (scraping, ingesta cruda, clasificación) es una capa interna
de IDEAS Consulting: las empresas cliente nunca la ven ni la disparan. Las
tablas normas_raw / legal_sources_watch / legal_sync_log NO llevan
empresa_id a propósito — no son multi-tenant, son del staff.

Los tres conectores (SAIJ, SRT Boletín Oficial, SRT Digesto) están
adaptados de los prototipos en `Curacion Normas/`, unificados sobre un
mismo schema (antes el de SAIJ no coincidía con los otros dos) y
reescritos para reutilizar los helpers ya existentes de
modules_legal_matrix (_connect, _rows, _is_ideas_staff, _user_name) en vez
de abrir su propia conexión SQLite suelta.
"""
from __future__ import annotations

import csv
import io
import re
import time
from datetime import date, datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup
from nicegui import run, ui

from modules_legal_matrix import _connect, _rows, _insert, _log, _is_ideas_staff, _user_name

# ---------------------------------------------------------------------------
# Fuentes conocidas
# ---------------------------------------------------------------------------

NOMBRE_SAIJ = 'SAIJ - Normativa Provincial'
NOMBRE_SRT_DIGESTO = 'Digesto SRT'
NOMBRE_SRT_BOLETIN = 'SRT - Boletin Oficial'

FUENTES_SEED = [
    (NOMBRE_SAIJ, 'dataset_abierto', 'https://datos.jus.gob.ar/dataset/base-saij-de-normativa-provincial', 'mensual'),
    (NOMBRE_SRT_DIGESTO, 'api', 'https://api.srt.gob.ar/v1/resoluciones/full', 'semanal'),
    (NOMBRE_SRT_BOLETIN, 'scraper', 'https://www.boletinoficial.gob.ar', 'semanal'),
]

PROVINCIAS_SAIJ_DEFAULT = 'Buenos Aires'


# ---------------------------------------------------------------------------
# Schema (aditivo, mismo patrón que _ensure_tables en modules_legal_matrix)
# ---------------------------------------------------------------------------

def _ensure_curation_tables() -> None:
    with _connect() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS legal_sources_watch (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre_fuente TEXT NOT NULL UNIQUE,
                tipo_conector TEXT,
                url_base TEXT,
                frecuencia_recomendada TEXT,
                ultima_corrida TEXT,
                activo INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS normas_raw (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                jurisdiccion TEXT NOT NULL,
                provincia TEXT,
                organismo_emisor TEXT,
                tipo_norma TEXT,
                numero TEXT,
                fecha_sancion TEXT,
                fecha_publicacion TEXT,
                titulo TEXT,
                resumen TEXT,
                tema TEXT,
                estado TEXT,
                norma_relacionada TEXT,
                link_fuente TEXT,
                fuente_id INTEGER REFERENCES legal_sources_watch(id),
                primera_vez_detectada TEXT,
                ultima_corrida_detectada TEXT,
                es_nuevo INTEGER DEFAULT 1,
                cambio_detectado TEXT,
                fecha_scraping TEXT DEFAULT CURRENT_TIMESTAMP,
                revision TEXT DEFAULT 'pendiente',
                revisado_por TEXT,
                fecha_aprobacion TEXT,
                publicado_a_empresa INTEGER DEFAULT 0,
                UNIQUE(fuente_id, provincia, tipo_norma, numero, fecha_sancion)
            );
            CREATE TABLE IF NOT EXISTS legal_sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fuente_id INTEGER REFERENCES legal_sources_watch(id),
                corrida_at TEXT DEFAULT CURRENT_TIMESTAMP,
                ok INTEGER DEFAULT 1,
                nuevas INTEGER DEFAULT 0,
                actualizadas INTEGER DEFAULT 0,
                sin_cambios INTEGER DEFAULT 0,
                error TEXT
            );
            CREATE INDEX IF NOT EXISTS idx_normas_raw_fuente ON normas_raw(fuente_id);
            CREATE INDEX IF NOT EXISTS idx_normas_raw_revision ON normas_raw(revision);
            CREATE TABLE IF NOT EXISTS norma_empresa_publicacion (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                norma_id INTEGER NOT NULL REFERENCES normas_raw(id),
                empresa_id INTEGER NOT NULL,
                requirement_id INTEGER,
                publicado_por TEXT,
                publicado_en TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(norma_id, empresa_id)
            );
            CREATE INDEX IF NOT EXISTS idx_norma_empresa_pub_norma ON norma_empresa_publicacion(norma_id);
            CREATE INDEX IF NOT EXISTS idx_norma_empresa_pub_empresa ON norma_empresa_publicacion(empresa_id);
        ''')
        for nombre, tipo, url, frecuencia in FUENTES_SEED:
            conn.execute(
                'INSERT OR IGNORE INTO legal_sources_watch (nombre_fuente, tipo_conector, url_base, frecuencia_recomendada) '
                'VALUES (?, ?, ?, ?)',
                (nombre, tipo, url, frecuencia),
            )


def _obtener_fuente_id(conn, nombre_fuente: str) -> int:
    row = conn.execute('SELECT id FROM legal_sources_watch WHERE nombre_fuente = ?', (nombre_fuente,)).fetchone()
    return int(row['id'])


def _registrar_normas(fuente_nombre: str, normas: list[dict]) -> dict:
    """Diff + insert común a los tres conectores: mismo criterio que usaban
    los tres prototipos por separado (nuevo / cambio de estado / sin cambios)."""
    _ensure_curation_tables()
    ahora = datetime.now(timezone.utc).isoformat()
    with _connect() as conn:
        fuente_id = _obtener_fuente_id(conn, fuente_nombre)
        nuevas = actualizadas = sin_cambios = 0
        for n in normas:
            existente = conn.execute(
                '''SELECT id, estado FROM normas_raw
                   WHERE fuente_id = ? AND provincia IS ? AND tipo_norma = ? AND numero = ? AND fecha_sancion IS ?''',
                (fuente_id, n.get('provincia'), n.get('tipo_norma'), n.get('numero'), n.get('fecha_sancion')),
            ).fetchone()
            if existente is None:
                conn.execute(
                    '''INSERT INTO normas_raw (
                        jurisdiccion, provincia, organismo_emisor, tipo_norma, numero,
                        fecha_sancion, fecha_publicacion, titulo, resumen, tema, estado,
                        norma_relacionada, link_fuente, fuente_id, primera_vez_detectada,
                        ultima_corrida_detectada, es_nuevo, fecha_scraping
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)''',
                    (
                        n.get('jurisdiccion'), n.get('provincia'), n.get('organismo_emisor'),
                        n.get('tipo_norma'), n.get('numero'), n.get('fecha_sancion'),
                        n.get('fecha_publicacion'), n.get('titulo'), n.get('resumen'), n.get('tema'),
                        n.get('estado'), n.get('norma_relacionada'), n.get('link_fuente'),
                        fuente_id, ahora, ahora, ahora,
                    ),
                )
                nuevas += 1
            else:
                estado_previo = existente['estado']
                if estado_previo != n.get('estado'):
                    conn.execute(
                        '''UPDATE normas_raw SET estado = ?, ultima_corrida_detectada = ?, es_nuevo = 1,
                           cambio_detectado = ? WHERE id = ?''',
                        (n.get('estado'), ahora, f"Estado cambió de '{estado_previo}' a '{n.get('estado')}'", existente['id']),
                    )
                    actualizadas += 1
                else:
                    conn.execute('UPDATE normas_raw SET ultima_corrida_detectada = ? WHERE id = ?', (ahora, existente['id']))
                    sin_cambios += 1
        conn.execute('UPDATE legal_sources_watch SET ultima_corrida = ? WHERE id = ?', (ahora, fuente_id))
        conn.execute(
            'INSERT INTO legal_sync_log (fuente_id, ok, nuevas, actualizadas, sin_cambios) VALUES (?, 1, ?, ?, ?)',
            (fuente_id, nuevas, actualizadas, sin_cambios),
        )
    return {'nuevas': nuevas, 'actualizadas': actualizadas, 'sin_cambios': sin_cambios}


def _registrar_error(fuente_nombre: str, error: str) -> None:
    _ensure_curation_tables()
    with _connect() as conn:
        fuente_id = _obtener_fuente_id(conn, fuente_nombre)
        conn.execute('INSERT INTO legal_sync_log (fuente_id, ok, error) VALUES (?, 0, ?)', (fuente_id, error))


# ---------------------------------------------------------------------------
# Conector 1: SAIJ (dataset abierto, sin auth) — validado con datos reales
# ---------------------------------------------------------------------------

SAIJ_CSV_URL = (
    'https://datos.jus.gob.ar/dataset/d59c2d29-d561-4ad2-a032-cc82b40db2d3/'
    'resource/0ebc70cc-0e71-4158-ab75-9759339e4cbd/download/'
    'base-saij-normativa-provincial.csv'
)

KEYWORDS_AMBIENTE = [
    'ambiente', 'ambiental', 'residuo', 'efluente', 'atmosfera', 'atmósfera',
    'agua', 'hidrico', 'hídrico', 'contaminacion', 'contaminación',
    'impacto ambiental', 'industrial', 'radicacion industrial',
    'radicación industrial', 'ruido', 'aptitud ambiental',
]
KEYWORDS_SST = [
    'higiene y seguridad', 'seguridad e higiene', 'riesgos del trabajo',
    'salud ocupacional', 'salud y seguridad', 'comite mixto', 'comité mixto',
    'accidente de trabajo', 'enfermedad profesional', 'violencia laboral',
    'condiciones de trabajo',
]
ESTADO_MAP_SAIJ = {
    # Valores reales observados en estado_vigencia (confirmados corriendo el
    # conector contra el CSV real, no los que suponía el prototipo original).
    'vigente, de alcance general': 'vigente',
    'vigente': 'vigente',
    'derogada': 'derogada',
    'individual, solo modificatoria o sin eficacia': 'a_verificar',
}


def _clasificar_tema_saij(texto: str) -> str:
    texto_l = texto.lower()
    es_ambiente = any(k in texto_l for k in KEYWORDS_AMBIENTE)
    es_sst = any(k in texto_l for k in KEYWORDS_SST)
    if es_ambiente and es_sst:
        return 'ambos'
    if es_ambiente:
        return 'ambiente'
    if es_sst:
        return 'sst'
    return ''


def conector_saij(provincias: list[str]) -> dict:
    resp = requests.get(SAIJ_CSV_URL, timeout=120)
    resp.raise_for_status()
    contenido = resp.content.decode('utf-8-sig', errors='replace')
    filas = list(csv.DictReader(io.StringIO(contenido)))

    provincias_norm = {p.strip().lower() for p in provincias if p.strip()}
    normas = []
    for fila in filas:
        provincia = (fila.get('provincia_nombre') or '').strip()
        if provincias_norm and provincia.lower() not in provincias_norm:
            continue
        texto = ' '.join([
            fila.get('titulo_resumido') or '', fila.get('titulo_sumario') or '', fila.get('nombre_norma') or '',
        ])
        tema = _clasificar_tema_saij(texto)
        if not tema:
            continue
        estado_raw = (fila.get('estado_vigencia') or '').strip().lower()
        normas.append({
            'jurisdiccion': 'provincial',
            'provincia': provincia,
            'organismo_emisor': None,
            'tipo_norma': (fila.get('tipo_norma') or '').strip().lower(),
            'numero': (fila.get('numero_norma') or '').strip(),
            'fecha_sancion': (fila.get('fecha') or '').strip() or None,
            'fecha_publicacion': (fila.get('fecha_publicacion') or '').strip() or None,
            'titulo': (fila.get('nombre_norma') or '').strip() or (fila.get('titulo_resumido') or '').strip(),
            'resumen': (fila.get('titulo_sumario') or '').strip() or (fila.get('titulo_resumido') or '').strip(),
            'tema': tema,
            'estado': ESTADO_MAP_SAIJ.get(estado_raw, estado_raw or 'desconocido'),
            'norma_relacionada': (fila.get('informacion_digesto') or '').strip() or None,
            'link_fuente': (fila.get('texto_actualizado') or '').strip() or None,
        })
    return _registrar_normas(NOMBRE_SAIJ, normas)


# ---------------------------------------------------------------------------
# Conector 2: SRT - Boletín Oficial (scraper) — robots.txt y rubro validados
# ---------------------------------------------------------------------------

BOLETIN_BASE_URL = 'https://www.boletinoficial.gob.ar'
BOLETIN_ORGANISMO_OBJETIVO = 'SUPERINTENDENCIA DE RIESGOS DEL TRABAJO'
BOLETIN_RUBRO_RESOLUCIONES = '1715'
BOLETIN_DELAY_SEG = 1.5
BOLETIN_HEADERS = {
    'User-Agent': 'IDEASConsulting-MatrizLegalDigital/1.0 (uso interno, contacto: legal@ideasconsulting.com.ar)',
}


def _listar_avisos_boletin(fecha: date) -> list[str]:
    fecha_str = fecha.strftime('%Y%m%d')
    url = f'{BOLETIN_BASE_URL}/seccion/primera/{fecha_str}?rubro={BOLETIN_RUBRO_RESOLUCIONES}'
    resp = requests.get(url, headers=BOLETIN_HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, 'html.parser')
    links = set()
    for a in soup.find_all('a', href=True):
        if '/detalleAviso/primera/' in a['href']:
            href = a['href']
            if href.startswith('/'):
                href = BOLETIN_BASE_URL + href
            links.add(href)
    return sorted(links)


def _parsear_aviso_boletin(url: str) -> dict | None:
    resp = requests.get(url, headers=BOLETIN_HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, 'html.parser')
    texto = soup.get_text('\n', strip=True)
    if BOLETIN_ORGANISMO_OBJETIVO not in texto.upper():
        return None

    m_numero = re.search(r'Resoluci[oó]n\s+(\d+/\d{4})', texto, re.IGNORECASE)
    numero = m_numero.group(1) if m_numero else None
    if not numero:
        return None

    m_fecha_sancion = re.search(r'Buenos Aires,\s*(\d{2}/\d{2}/\d{4})', texto)
    m_fecha_pub = re.search(r'Fecha de publicaci[oó]n\s*(\d{2}/\d{2}/\d{4})', texto)
    m_resumen = re.search(r'CONSIDERANDO:\s*\n(.{0,400})', texto, re.DOTALL)

    return {
        'jurisdiccion': 'nacional',
        'provincia': None,
        'organismo_emisor': 'SRT',
        'tipo_norma': 'resolucion',
        'numero': numero,
        'fecha_sancion': m_fecha_sancion.group(1) if m_fecha_sancion else None,
        'fecha_publicacion': m_fecha_pub.group(1) if m_fecha_pub else None,
        'titulo': f'Resolución SRT {numero}',
        'resumen': (m_resumen.group(1).strip() + '…') if m_resumen else None,
        'tema': 'sst',
        'estado': 'vigente',
        'norma_relacionada': None,
        'link_fuente': url,
    }


def conector_srt_boletin(desde: date, hasta: date) -> dict:
    encontradas = []
    dia = desde
    while dia <= hasta:
        for url in _listar_avisos_boletin(dia):
            time.sleep(BOLETIN_DELAY_SEG)
            norma = _parsear_aviso_boletin(url)
            if norma:
                encontradas.append(norma)
        dia += timedelta(days=1)
        time.sleep(BOLETIN_DELAY_SEG)
    return _registrar_normas(NOMBRE_SRT_BOLETIN, encontradas)


# ---------------------------------------------------------------------------
# Conector 3: SRT - Digesto (API) — token público, se obtiene solo
# ---------------------------------------------------------------------------

SRT_DIGESTO_API_URL = 'https://api.srt.gob.ar/v1/resoluciones/full'

# El frontend de digesto.srt.gob.ar (Angular) pide este token a este mismo
# endpoint público en cada carga de página, sin login — el client_id no es
# secreto, está a la vista en digesto/constantes.app.js. No hace falta
# capturar nada a mano ni guardar un token: se pide uno fresco en cada
# corrida (dura ~24hs según expires_in, pero total, se vuelve a pedir solo).
SRT_DIGESTO_AUTH_URL = 'https://api.srt.gob.ar/auth/digesto.aspx'
SRT_DIGESTO_CLIENT_ID = '5F8B1824-8069-44AB-ADAB-5AA983F313B3'


def _obtener_token_srt_digesto() -> str:
    resp = requests.get(SRT_DIGESTO_AUTH_URL, params={'client_id': SRT_DIGESTO_CLIENT_ID}, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    token_type = data.get('token_type', 'bearer')
    access_token = data['access_token']
    return f'{token_type} {access_token}'


def conector_srt_digesto(desde: date, hasta: date, cantidad: str = '1000') -> dict:
    authorization = _obtener_token_srt_digesto()
    payload = {
        'NroResolucion': None, 'Cantidad': cantidad, 'Asunto': None,
        'OrganismoEmisor': '', 'TipoNorma': '', 'BoletinOficial': None,
        'FechaDesde': f'{desde.isoformat()}T03:00:00.000Z',
        'FechaHasta': f'{hasta.isoformat()}T03:00:00.000Z',
        'NroExpediente': None, 'Voces': [],
    }
    headers = {'Content-Type': 'application/json', 'Authorization': authorization}
    resp = requests.post(SRT_DIGESTO_API_URL, json=payload, headers=headers, timeout=60)
    resp.raise_for_status()
    data = resp.json()

    items = data if isinstance(data, list) else next(
        (data[k] for k in ('Resultados', 'Items', 'Data', 'resultados') if isinstance(data.get(k), list)), None,
    )
    if items is None:
        raise ValueError('No se pudo interpretar la forma de la respuesta de la API de Digesto SRT.')
    if len(items) >= int(cantidad):
        raise ValueError(
            f"La API devolvió {len(items)} normas (>= Cantidad={cantidad}) — probablemente falte paginar. "
            "No se cargó nada para no dejar el rango incompleto sin avisar; ver docstring del prototipo original."
        )

    normas = []
    for it in items:
        tipo = (it.get('Tipo') or '').strip().lower()
        normas.append({
            'jurisdiccion': 'nacional',
            'provincia': None,
            'organismo_emisor': (it.get('Organismo') or '').strip() or 'SRT',
            'tipo_norma': tipo,
            'numero': it.get('NumeroAnio') or str(it.get('Numero', '')),
            'fecha_sancion': (it.get('Fecha') or '')[:10] if it.get('Fecha') else None,
            'fecha_publicacion': None,
            'titulo': f"{it.get('Tipo', '')} {it.get('NumeroAnio', '')}".strip(),
            'resumen': it.get('Asunto'),
            'tema': 'sst',
            'estado': 'desconocido',
            'norma_relacionada': None,
            'link_fuente': it.get('Link'),
        })
    return _registrar_normas(NOMBRE_SRT_DIGESTO, normas)


def ejecutar_conector(nombre_fuente: str) -> dict:
    """Dispara el conector correspondiente. Se llama SOLO desde acá (backend) —
    nunca fetch client-side (ver spec: exponer estas llamadas al navegador
    las saca del control de IDEAS_ADMIN y además esta API en particular
    no habilita CORS para uso client-side)."""
    hoy = date.today()
    try:
        if nombre_fuente == NOMBRE_SAIJ:
            resultado = conector_saij([p.strip() for p in PROVINCIAS_SAIJ_DEFAULT.split(',')])
        elif nombre_fuente == NOMBRE_SRT_BOLETIN:
            resultado = conector_srt_boletin(hoy - timedelta(days=30), hoy)
        elif nombre_fuente == NOMBRE_SRT_DIGESTO:
            resultado = conector_srt_digesto(hoy - timedelta(days=30), hoy)
        else:
            raise ValueError(f'Fuente desconocida: {nombre_fuente}')
        return {'ok': True, **resultado}
    except Exception as exc:
        _registrar_error(nombre_fuente, str(exc))
        return {'ok': False, 'error': str(exc)}


# ---------------------------------------------------------------------------
# Consultas y acciones de curación
# ---------------------------------------------------------------------------

def listar_fuentes() -> list[dict]:
    _ensure_curation_tables()
    return _rows('SELECT * FROM legal_sources_watch ORDER BY nombre_fuente')


def listar_normas_raw(texto: str = '', tema: str = 'todos', revision: str = 'todos', fuente_id: int | None = None) -> list[dict]:
    _ensure_curation_tables()
    query = (
        'SELECT nr.*, ls.nombre_fuente FROM normas_raw nr '
        'JOIN legal_sources_watch ls ON ls.id = nr.fuente_id WHERE 1=1'
    )
    params: list = []
    if texto:
        query += ' AND (nr.titulo LIKE ? OR nr.numero LIKE ? OR nr.resumen LIKE ?)'
        needle = f'%{texto}%'
        params += [needle, needle, needle]
    if tema != 'todos':
        query += ' AND nr.tema = ?'
        params.append(tema)
    if revision != 'todos':
        query += ' AND nr.revision = ?'
        params.append(revision)
    if fuente_id:
        query += ' AND nr.fuente_id = ?'
        params.append(fuente_id)
    query += ' ORDER BY nr.es_nuevo DESC, nr.fecha_scraping DESC, nr.id DESC'
    return _rows(query, tuple(params))


def contar_por_revision() -> dict:
    _ensure_curation_tables()
    rows = _rows('SELECT revision, COUNT(*) AS n FROM normas_raw GROUP BY revision')
    conteos = {'pendiente': 0, 'aprobada': 0, 'rechazada': 0}
    for r in rows:
        conteos[r['revision']] = r['n']
    conteos['total'] = sum(conteos.values())
    nuevas_rows = _rows('SELECT COUNT(*) AS n FROM normas_raw WHERE es_nuevo = 1')
    conteos['nuevas'] = nuevas_rows[0]['n'] if nuevas_rows else 0
    return conteos


def aprobar_norma(norma_id: int) -> None:
    _ensure_curation_tables()
    with _connect() as conn:
        conn.execute(
            "UPDATE normas_raw SET revision = 'aprobada', revisado_por = ?, fecha_aprobacion = ?, es_nuevo = 0 WHERE id = ?",
            (_user_name(), datetime.now(timezone.utc).isoformat(), norma_id),
        )


def rechazar_norma(norma_id: int) -> None:
    _ensure_curation_tables()
    with _connect() as conn:
        conn.execute(
            "UPDATE normas_raw SET revision = 'rechazada', revisado_por = ?, fecha_aprobacion = ?, es_nuevo = 0 WHERE id = ?",
            (_user_name(), datetime.now(timezone.utc).isoformat(), norma_id),
        )


# ---------------------------------------------------------------------------
# Publicación a empresas (Fase 2, 2026-08-10)
#
# Gap que quedaba abierto: "aprobar" una norma en normas_raw no decidía a qué
# empresa(s) se publicaba -- quedaba 100% en manos de que alguien la cargara a
# mano en la Matriz Legal de cada cliente, sin ningún registro de qué normas
# aprobadas todavía no llegaron a ningún cliente. Esto cierra ese circuito:
# aprobar -> elegir empresas -> se crea el requisito en la Matriz Legal de cada
# una y queda trazado en norma_empresa_publicacion + normas_raw.publicado_a_empresa.
# ---------------------------------------------------------------------------

_AMBITO_POR_TEMA = {
    'ambiente': 'Medio Ambiente',
    'sst': 'Seguridad e Higiene',
    'ambos': 'Medio Ambiente / SST',
}


def obtener_norma_raw(norma_id: int) -> dict | None:
    _ensure_curation_tables()
    rows = _rows('SELECT * FROM normas_raw WHERE id = ?', (norma_id,))
    return rows[0] if rows else None


def obtener_empresas_publicadas_norma(norma_id: int) -> list[dict]:
    _ensure_curation_tables()
    return _rows(
        'SELECT * FROM norma_empresa_publicacion WHERE norma_id = ? ORDER BY publicado_en DESC',
        (norma_id,),
    )


def normas_aprobadas_sin_publicar(limit: int = 200) -> list[dict]:
    """Normas ya aprobadas por el staff que todavia no se publicaron a NINGUNA empresa.
    Es la pieza que faltaba para poder responder 'que aprobamos que nadie recibio todavia'."""
    _ensure_curation_tables()
    return _rows(
        '''
        SELECT nr.*, ls.nombre_fuente FROM normas_raw nr
        JOIN legal_sources_watch ls ON ls.id = nr.fuente_id
        WHERE nr.revision = 'aprobada' AND nr.publicado_a_empresa = 0
        ORDER BY nr.fecha_aprobacion DESC
        LIMIT ?
        ''',
        (limit,),
    )


def publicar_norma_a_empresas(norma_id: int, empresa_ids: list[int]) -> tuple[bool, str]:
    """Publica una norma aprobada a una o mas empresas: crea el requisito legal
    correspondiente en la Matriz Legal de cada una (estado 'Pendiente', para que el
    cliente lo revise) y deja trazabilidad de que empresas ya lo recibieron."""
    _ensure_curation_tables()
    norma = obtener_norma_raw(norma_id)
    if not norma:
        return False, 'La norma no existe.'
    if norma.get('revision') != 'aprobada':
        return False, 'Solo se pueden publicar normas ya aprobadas.'
    empresa_ids = sorted({int(e) for e in (empresa_ids or []) if e})
    if not empresa_ids:
        return False, 'Elegi al menos una empresa.'

    ya_publicadas = {int(p['empresa_id']) for p in obtener_empresas_publicadas_norma(norma_id)}
    pendientes = [e for e in empresa_ids if e not in ya_publicadas]
    if not pendientes:
        return False, 'Esta norma ya fue publicada a todas las empresas seleccionadas.'

    ambito = _AMBITO_POR_TEMA.get(str(norma.get('tema') or ''), 'Medio Ambiente')
    actor = _user_name()
    creados = 0
    for empresa_id in pendientes:
        requirement_id = _insert('legal_requirements', {
            'empresa_id': empresa_id,
            'ambito': ambito,
            'jurisdiccion': norma.get('jurisdiccion') or norma.get('provincia') or 'Nacional',
            'organismo': norma.get('organismo_emisor') or '',
            'tipo_norma': norma.get('tipo_norma') or 'Ley',
            'numero': norma.get('numero') or '',
            'titulo': norma.get('titulo') or f"Norma {norma.get('numero') or norma_id}",
            'obligacion': norma.get('resumen') or '',
            'estado': 'Pendiente',
            'criticidad': 'Media',
            'fecha_publicacion': norma.get('fecha_publicacion') or '',
            'observaciones': f"Publicada automaticamente desde curacion normativa (norma_raw id={norma_id}) por {actor}.",
        })
        with _connect() as conn:
            conn.execute(
                'INSERT OR IGNORE INTO norma_empresa_publicacion (norma_id, empresa_id, requirement_id, publicado_por) '
                'VALUES (?, ?, ?, ?)',
                (norma_id, empresa_id, requirement_id, actor),
            )
        _log(empresa_id, 'ALTA', 'requisito legal (curacion normativa)', requirement_id, str(norma.get('titulo') or ''))
        creados += 1

    with _connect() as conn:
        conn.execute('UPDATE normas_raw SET publicado_a_empresa = 1 WHERE id = ?', (norma_id,))

    try:
        from core_data import registrar_auditoria
        registrar_auditoria(
            None, actor=actor, actor_role='IDEAS_ADMIN', entidad='publicar_norma_a_empresas',
            entidad_id=norma_id, accion='write', resultado='ok',
            detalle=f'{creados} empresa(s): {pendientes}',
        )
    except Exception:
        pass

    return True, f'Norma publicada a {creados} empresa(s).'


def go_to_legal_curation_module(_empresa_id: int | None = None, _set_selection_fn=None) -> None:
    ui.navigate.to('/sistema-gestion/curacion-normativa')


# ---------------------------------------------------------------------------
# UI — panel de curación (solo IDEAS_ADMIN)
# ---------------------------------------------------------------------------

TEMA_META = {
    'ambiente': {'label': 'Ambiente', 'icon': 'eco', 'color': '#15803D', 'bg': '#DCFCE7'},
    'sst': {'label': 'SST', 'icon': 'health_and_safety', 'color': '#0369A1', 'bg': '#E0F2FE'},
    'ambos': {'label': 'Ambiente + SST', 'icon': 'shield', 'color': '#6D28D9', 'bg': '#EDE9FE'},
}
ESTADO_META = {
    'vigente': {'label': 'Vigente', 'color': '#15803D'},
    'derogada': {'label': 'Derogada', 'color': '#B91C1C'},
    'modificatoria': {'label': 'Modificatoria', 'color': '#B45309'},
    'sin_eficacia': {'label': 'Sin eficacia', 'color': '#6B7480'},
    'a_verificar': {'label': 'A verificar', 'color': '#B45309'},
    'desconocido': {'label': 'A verificar', 'color': '#6B7480'},
}
REVISION_META = {
    'pendiente': {'label': 'Pendiente', 'color': '#B45309', 'bg': '#FEF3C7'},
    'aprobada': {'label': 'Aprobada', 'color': '#15803D', 'bg': '#DCFCE7'},
    'rechazada': {'label': 'Rechazada', 'color': '#6B7480', 'bg': '#EEF1F5'},
}


def _estado_meta(estado: str) -> dict:
    return ESTADO_META.get(estado, {'label': estado or 'A verificar', 'color': '#6B7480'})


def _tema_meta(tema: str) -> dict:
    return TEMA_META.get(tema, {'label': tema or '—', 'icon': 'label', 'color': '#6B7480', 'bg': '#EEF1F5'})


def register_legal_curation_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    fix_text = deps.get('fix_text', lambda value: '' if value is None else str(value))

    @ui.page('/sistema-gestion/curacion-normativa')
    def curacion_normativa_page() -> None:
        if not ensure_platform_access():
            return
        shell_container = shell('Curación Normativa', back_route='/sistema-gestion', module_key='legal_curation')

        with shell_container:
            if not _is_ideas_staff():
                with ui.card().classes('ideas-panel w-full'):
                    ui.label('Acceso denegado').classes('ideas-section-title')
                    ui.label(
                        'La curación de normativa es una función interna de IDEAS Consulting. '
                        'Tu usuario no tiene ese alcance.'
                    ).classes('ideas-section-note')
                return

            ui.label('Matriz Legal Digital · Curación').classes('ideas-kicker')
            ui.label('Fuentes normativas y revisión').classes('text-3xl font-bold text-slate-900')
            ui.label(
                'Panel interno: acá se revisan las normas detectadas por los conectores antes de '
                'incorporarlas a la Matriz Legal de cualquier empresa. Ninguna empresa cliente ve esta pantalla.'
            ).classes('ideas-section-note mb-4')

            state = {'texto': '', 'tema': 'todos', 'revision': 'todos', 'fuente_id': None, 'pagina': 1}
            NORMAS_POR_PAGINA = 20

            # -- Stats ---------------------------------------------------
            @ui.refreshable
            def stats_row() -> None:
                conteos = contar_por_revision()
                with ui.row().classes('w-full gap-3 flex-wrap mb-4'):
                    for key, label, color in (
                        ('nuevas', 'Nuevas sin revisar', '#B45309'),
                        ('pendiente', 'Pendientes', '#B45309'),
                        ('aprobada', 'Aprobadas', '#15803D'),
                        ('rechazada', 'Rechazadas', '#6B7480'),
                        ('total', 'Total en curación', '#0E3A53'),
                    ):
                        with ui.card().classes('ideas-panel flex-1 min-w-[150px] p-4 gap-1'):
                            ui.label(str(conteos.get(key, 0))).classes('text-2xl font-bold').style(f'color:{color};')
                            ui.label(label).classes('text-xs text-slate-500')

            # -- Fuentes ---------------------------------------------------
            @ui.refreshable
            def fuentes_row() -> None:
                with ui.card().classes('ideas-panel w-full mb-4'):
                    ui.label('Fuentes conectadas').classes('ideas-section-title')
                    with ui.row().classes('w-full gap-3 flex-wrap mt-2'):
                        for fuente in listar_fuentes():
                            with ui.card().classes('flex-1 min-w-[220px] p-3 gap-1').style(
                                'border:1px solid rgba(148,163,184,.20); box-shadow:none;'
                            ):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.element('div').classes('rounded-full').style(
                                            f'width:8px;height:8px;background:{"#15803D" if fuente["activo"] else "#94A3B8"};'
                                        )
                                        ui.label(fix_text(fuente['nombre_fuente'])).classes('text-sm font-semibold text-slate-800')
                                    ui.label(fuente['tipo_conector'] or '').classes(
                                        'text-[10px] uppercase tracking-wide text-slate-400'
                                    )
                                ui.label(f"Frecuencia: {fuente['frecuencia_recomendada'] or '—'}").classes(
                                    'text-xs text-slate-500'
                                )
                                ultima = fuente['ultima_corrida']
                                ui.label(f"Última corrida: {ultima[:19].replace('T', ' ') if ultima else 'todavía no corrió'}").classes(
                                    'text-xs text-slate-400'
                                )

                                async def _actualizar(nombre=fuente['nombre_fuente']) -> None:
                                    boton.set_text('Actualizando...')
                                    boton.disable()
                                    try:
                                        resultado = await run.io_bound(ejecutar_conector, nombre)
                                    finally:
                                        boton.set_text('Actualizar')
                                        boton.enable()
                                    if resultado.get('ok'):
                                        ui.notify(
                                            f"{nombre}: {resultado['nuevas']} nueva(s), "
                                            f"{resultado['actualizadas']} actualizada(s), "
                                            f"{resultado['sin_cambios']} sin cambios.",
                                            type='positive',
                                        )
                                    else:
                                        ui.notify(f"{nombre}: {resultado.get('error')}", type='negative', timeout=8000)
                                    stats_row.refresh()
                                    fuentes_row.refresh()
                                    tabla_normas.refresh()

                                boton = ui.button('Actualizar', icon='refresh', on_click=_actualizar).props(
                                    'flat dense no-caps'
                                ).classes('mt-1 self-start')

            # -- Filtros -----------------------------------------------
            fuentes_options = {None: 'Todas las fuentes'} | {
                f['id']: fix_text(f['nombre_fuente']) for f in listar_fuentes()
            }

            with ui.row().classes('w-full items-center gap-2 flex-wrap mb-2'):
                search = ui.input(placeholder='Buscar por título, número o resumen...').props(
                    'outlined dense clearable prepend-icon=search'
                ).classes('flex-1 min-w-[240px]')
                tema_select = ui.select(
                    {'todos': 'Todos los temas', 'ambiente': 'Ambiente', 'sst': 'SST', 'ambos': 'Ambiente + SST'},
                    value='todos',
                ).props('outlined dense').classes('w-48')
                revision_select = ui.select(
                    {'todos': 'Toda revisión', 'pendiente': 'Pendiente', 'aprobada': 'Aprobada', 'rechazada': 'Rechazada'},
                    value='todos',
                ).props('outlined dense').classes('w-44')
                fuente_select = ui.select(fuentes_options, value=None).props('outlined dense').classes('w-52')

            def _aplicar_filtros() -> None:
                state['texto'] = search.value or ''
                state['tema'] = tema_select.value
                state['revision'] = revision_select.value
                state['fuente_id'] = fuente_select.value
                state['pagina'] = 1  # nuevo filtro -> volver a la primera pagina
                tabla_normas.refresh()

            search.on_value_change(_aplicar_filtros)
            tema_select.on_value_change(_aplicar_filtros)
            revision_select.on_value_change(_aplicar_filtros)
            fuente_select.on_value_change(_aplicar_filtros)

            # -- Detalle / aprobar-rechazar --------------------------------
            detail_dialog = ui.dialog()

            def abrir_detalle(norma: dict) -> None:
                detail_dialog.clear()
                with detail_dialog, ui.card().classes('w-[640px] max-w-[95vw] p-0 overflow-hidden'):
                    with ui.column().classes('w-full p-5 gap-3'):
                        with ui.row().classes('w-full items-start justify-between'):
                            ui.label(fix_text(norma.get('titulo') or 'Sin título')).classes(
                                'text-lg font-bold flex-1'
                            ).style('color:#0E3A53;')
                            ui.button(icon='close', on_click=detail_dialog.close).props('flat round dense').tooltip('Cerrar')

                        tema_m = _tema_meta(norma.get('tema'))
                        estado_m = _estado_meta(norma.get('estado'))
                        revision_m = REVISION_META.get(norma.get('revision'), REVISION_META['pendiente'])
                        with ui.row().classes('items-center gap-2 flex-wrap'):
                            ui.label(tema_m['label']).classes('text-xs font-semibold px-2 py-1 rounded-full').style(
                                f"color:{tema_m['color']}; background:{tema_m['bg']};"
                            )
                            ui.label(estado_m['label']).classes('text-xs font-semibold px-2 py-1 rounded-full border').style(
                                f"color:{estado_m['color']}; border-color:{estado_m['color']}55;"
                            )
                            ui.label(revision_m['label']).classes('text-xs font-semibold px-2 py-1 rounded-full').style(
                                f"color:{revision_m['color']}; background:{revision_m['bg']};"
                            )
                            if norma.get('es_nuevo'):
                                ui.label('Nuevo').classes('text-xs font-semibold px-2 py-1 rounded-full').style(
                                    'color:#B91C1C; background:#FEE2E2;'
                                )
                        ui.separator()

                        for icon, label, value in (
                            ('source', 'Fuente', norma.get('nombre_fuente')),
                            ('gavel', 'Tipo y número', f"{norma.get('tipo_norma') or ''} {norma.get('numero') or ''}".strip()),
                            ('map', 'Jurisdicción', f"{norma.get('jurisdiccion') or ''} {('· ' + norma['provincia']) if norma.get('provincia') else ''}".strip()),
                            ('account_balance', 'Organismo emisor', norma.get('organismo_emisor')),
                            ('event', 'Fecha de sanción', norma.get('fecha_sancion')),
                            ('event_available', 'Fecha de publicación', norma.get('fecha_publicacion')),
                            ('description', 'Resumen', norma.get('resumen')),
                            ('sync_problem', 'Cambio detectado', norma.get('cambio_detectado')),
                            ('history', 'Revisado por', f"{norma.get('revisado_por') or ''} {('· ' + norma['fecha_aprobacion'][:19]) if norma.get('fecha_aprobacion') else ''}".strip()),
                        ):
                            if not value:
                                continue
                            with ui.row().classes('items-start gap-2'):
                                ui.icon(icon).classes('text-gray-400 text-base mt-0.5')
                                ui.label(str(value)).classes('text-sm text-gray-700')

                        if norma.get('link_fuente'):
                            ui.link('Ver fuente original', norma['link_fuente'], new_tab=True).classes('text-sm')

                        ui.separator()
                        with ui.row().classes('w-full justify-end gap-2'):
                            def _rechazar(norma_id=norma['id']) -> None:
                                rechazar_norma(norma_id)
                                detail_dialog.close()
                                stats_row.refresh()
                                tabla_normas.refresh()
                                ui.notify('Norma rechazada', type='warning')

                            def _aprobar(norma_id=norma['id']) -> None:
                                aprobar_norma(norma_id)
                                detail_dialog.close()
                                stats_row.refresh()
                                tabla_normas.refresh()
                                ui.notify('Norma aprobada', type='positive')

                            def _abrir_publicar(norma_id=norma['id']) -> None:
                                from core_data import obtener_empresas

                                empresas = list(obtener_empresas())
                                ya_publicadas = {int(p['empresa_id']) for p in obtener_empresas_publicadas_norma(norma_id)}
                                with ui.dialog() as pub_dialog, ui.card().classes('w-full max-w-md'):
                                    ui.label('Publicar a empresas').classes('text-base font-semibold')
                                    ui.label(
                                        'Crea el requisito legal (estado Pendiente) en la Matriz Legal de cada '
                                        'empresa elegida. Las que ya la recibieron aparecen tildadas y deshabilitadas.'
                                    ).classes('text-xs text-gray-500')
                                    checks: dict[int, object] = {}
                                    with ui.column().classes('w-full gap-1 max-h-64 overflow-auto'):
                                        for empresa_id, nombre in empresas:
                                            ya = int(empresa_id) in ya_publicadas
                                            checks[int(empresa_id)] = ui.checkbox(
                                                f"{nombre}{' (ya publicada)' if ya else ''}", value=ya,
                                            ).props('disable' if ya else '')
                                    with ui.row().classes('w-full justify-end gap-2 mt-2'):
                                        ui.button('Cancelar', on_click=pub_dialog.close).props('flat no-caps')

                                        def _confirmar_publicar() -> None:
                                            seleccionadas = [eid for eid, chk in checks.items() if chk.value and eid not in ya_publicadas]
                                            ok, msg = publicar_norma_a_empresas(norma_id, seleccionadas)
                                            ui.notify(msg, type='positive' if ok else 'warning')
                                            if ok:
                                                pub_dialog.close()
                                                detail_dialog.close()
                                                tabla_normas.refresh()

                                        ui.button('Publicar', icon='send', on_click=_confirmar_publicar).props('unelevated no-caps').style(
                                            'background:#0E3A53;'
                                        )
                                pub_dialog.open()

                            ui.button('Rechazar', icon='close', on_click=_rechazar).props('flat no-caps color=negative')
                            if norma.get('revision') == 'aprobada':
                                ui.button('Publicar a empresas', icon='send', on_click=_abrir_publicar).props('unelevated no-caps color=primary')
                            ui.button('Aprobar', icon='check', on_click=_aprobar).props('unelevated no-caps').style(
                                'background:#0E3A53;'
                            )
                detail_dialog.open()

            # -- Tabla -----------------------------------------------------
            # 2026-08-24 (auditoria consola Super Admin, hallazgo #5): esta lista
            # renderiza tarjetas a mano (no ui.table()), asi que no tenia el
            # paginado que si tienen Empresas/Usuarios/Historial/Resultados --
            # con las ~208 normas actuales carga todo de una sola vez. Recorta a
            # NORMAS_POR_PAGINA por pagina, con controles simples arriba y abajo
            # de la lista.
            @ui.refreshable
            def tabla_normas() -> None:
                filas = listar_normas_raw(state['texto'], state['tema'], state['revision'], state['fuente_id'])
                if not filas:
                    with ui.column().classes('w-full items-center justify-center py-14 gap-2 text-center'):
                        ui.icon('search_off').classes('text-5xl text-gray-300')
                        ui.label('Sin resultados con estos filtros').classes('text-gray-500 font-medium')
                    return
                total = len(filas)
                total_paginas = max(1, -(-total // NORMAS_POR_PAGINA))  # ceil
                pagina_actual = min(max(1, int(state.get('pagina') or 1)), total_paginas)
                state['pagina'] = pagina_actual

                def _ir_a_pagina(nueva: int) -> None:
                    state['pagina'] = nueva
                    tabla_normas.refresh()

                if total_paginas > 1:
                    with ui.row().classes('w-full items-center justify-between mb-1'):
                        ui.label(f'{total} normas · página {pagina_actual} de {total_paginas}').classes('text-xs text-slate-500')
                        ui.pagination(1, total_paginas, value=pagina_actual, direction_links=True, on_change=lambda e: _ir_a_pagina(int(e.value))).props('dense')

                inicio = (pagina_actual - 1) * NORMAS_POR_PAGINA
                for norma in filas[inicio:inicio + NORMAS_POR_PAGINA]:
                    tema_m = _tema_meta(norma.get('tema'))
                    estado_m = _estado_meta(norma.get('estado'))
                    revision_m = REVISION_META.get(norma.get('revision'), REVISION_META['pendiente'])
                    with ui.card().classes('ideas-panel w-full p-3 gap-1 cursor-pointer mb-2').on(
                        'click', lambda norma=norma: abrir_detalle(norma)
                    ):
                        with ui.row().classes('w-full items-start justify-between gap-2'):
                            with ui.column().classes('gap-0 flex-1 min-w-0'):
                                ui.label(fix_text(norma.get('titulo') or 'Sin título')).classes(
                                    'text-sm font-semibold text-slate-800 truncate'
                                )
                                ui.label(
                                    f"{norma.get('tipo_norma') or ''} {norma.get('numero') or ''} · "
                                    f"{fix_text(norma.get('nombre_fuente'))}"
                                ).classes('text-xs text-slate-500')
                            if norma.get('es_nuevo'):
                                ui.label('Nuevo').classes('text-[10px] font-semibold px-2 py-0.5 rounded-full').style(
                                    'color:#B91C1C; background:#FEE2E2;'
                                )
                        with ui.row().classes('items-center gap-2 flex-wrap mt-1'):
                            ui.label(tema_m['label']).classes('text-[11px] font-semibold px-2 py-0.5 rounded-full').style(
                                f"color:{tema_m['color']}; background:{tema_m['bg']};"
                            )
                            ui.label(estado_m['label']).classes('text-[11px] px-2 py-0.5 rounded-full border').style(
                                f"color:{estado_m['color']}; border-color:{estado_m['color']}55;"
                            )
                            ui.label(revision_m['label']).classes('text-[11px] font-semibold px-2 py-0.5 rounded-full').style(
                                f"color:{revision_m['color']}; background:{revision_m['bg']};"
                            )

                if total_paginas > 1:
                    with ui.row().classes('w-full justify-center mt-2'):
                        ui.pagination(1, total_paginas, value=pagina_actual, direction_links=True, on_change=lambda e: _ir_a_pagina(int(e.value))).props('dense')

            stats_row()
            fuentes_row()
            tabla_normas()
