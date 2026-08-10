#!/usr/bin/env python3
"""
sync_normativa_srt_boletin.py

Conector de la fuente "SRT - Boletin Oficial" hacia normas_raw.

A diferencia de sync_normativa_saij.py (que consume un dataset abierto ya
estructurado), esta fuente sí requiere leer páginas del Boletín Oficial de
la República Argentina y extraer los campos con expresiones regulares sobre
el texto de cada aviso. Es el patrón a repetir para cualquier fuente que no
tenga dataset abierto (próximo candidato: Boletín Oficial PBA, con su propia
URL base).

IMPORTANTE antes de correr esto en producción:
  1. Verificar el robots.txt vigente de boletinoficial.gob.ar en el momento
     de desplegar (las políticas de los sitios pueden cambiar).
  2. Este script solo cubre resoluciones publicadas bajo el organismo
     "SUPERINTENDENCIA DE RIESGOS DEL TRABAJO" en la Primera Sección
     (Legislación y Avisos Oficiales), rubro Resoluciones.
  3. Corré primero con --dry-run sobre pocos días para confirmar que el
     parseo de campos da bien antes de cargarlo en la base real.
  4. Respetar un delay entre requests (ya incluido) para no sobrecargar
     el sitio del organismo.

Requisitos:
    pip install requests beautifulsoup4

Uso:
    python sync_normativa_srt_boletin.py --db /ruta/a/ideas.db \
        --desde 2026-06-01 --hasta 2026-07-27 --dry-run

    # Sin --dry-run, escribe de verdad en normas_raw:
    python sync_normativa_srt_boletin.py --db /ruta/a/ideas.db \
        --desde 2026-06-01 --hasta 2026-07-27
"""

import argparse
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.boletinoficial.gob.ar"
ORGANISMO_OBJETIVO = "SUPERINTENDENCIA DE RIESGOS DEL TRABAJO"
RUBRO_RESOLUCIONES = "1715"  # visto en la URL de listado; verificar que no cambie
NOMBRE_FUENTE = "SRT - Boletin Oficial"
DELAY_ENTRE_REQUESTS_SEG = 1.5

HEADERS = {
    "User-Agent": "IDEASConsulting-MatrizLegalDigital/1.0 (uso interno, contacto: legal@ideasconsulting.com.ar)"
}

DDL_LEGAL_SOURCES_WATCH = """
CREATE TABLE IF NOT EXISTS legal_sources_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_fuente TEXT NOT NULL UNIQUE,
    tipo_conector TEXT,
    url_base TEXT,
    frecuencia_recomendada TEXT,
    ultima_corrida TEXT,
    activo INTEGER DEFAULT 1
);
"""

DDL_NORMAS_RAW = """
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
    fecha_scraping TEXT,
    revisado_por TEXT,
    fecha_aprobacion TEXT,
    publicado_a_empresa INTEGER DEFAULT 0,
    UNIQUE(fuente_id, provincia, tipo_norma, numero, fecha_sancion)
);
"""


def listar_avisos_del_dia(fecha: datetime) -> list[str]:
    """Devuelve las URLs de detalle de los avisos de Resoluciones publicados ese día."""
    fecha_str = fecha.strftime("%Y%m%d")
    url = f"{BASE_URL}/seccion/primera/{fecha_str}?rubro={RUBRO_RESOLUCIONES}"
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return []
    soup = BeautifulSoup(resp.text, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        if "/detalleAviso/primera/" in a["href"]:
            href = a["href"]
            if href.startswith("/"):
                href = BASE_URL + href
            links.add(href)
    return sorted(links)


def parsear_aviso(url: str) -> dict | None:
    """Descarga un aviso puntual y extrae los campos relevantes por regex sobre el texto."""
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        return None
    soup = BeautifulSoup(resp.text, "html.parser")
    texto = soup.get_text("\n", strip=True)

    if ORGANISMO_OBJETIVO not in texto.upper():
        return None  # no es de SRT, se descarta (este listado trae todos los organismos)

    # Ej: "Resolución 8/2026"
    m_numero = re.search(r"Resoluci[oó]n\s+(\d+/\d{4})", texto, re.IGNORECASE)
    numero = m_numero.group(1) if m_numero else None

    # Ej: "Ciudad de Buenos Aires, 28/01/2026"
    m_fecha_sancion = re.search(r"Buenos Aires,\s*(\d{2}/\d{2}/\d{4})", texto)
    fecha_sancion = m_fecha_sancion.group(1) if m_fecha_sancion else None

    # Ej: "Fecha de publicación 30/01/2026"
    m_fecha_pub = re.search(r"Fecha de publicaci[oó]n\s*(\d{2}/\d{2}/\d{4})", texto)
    fecha_publicacion = m_fecha_pub.group(1) if m_fecha_pub else None

    # Título: primera línea significativa tras el nombre del organismo
    m_titulo = re.search(
        rf"{re.escape(ORGANISMO_OBJETIVO)}\s*\n?\s*(Resoluci[oó]n\s+\d+/\d{{4}})", texto, re.IGNORECASE
    )
    titulo = m_titulo.group(0).replace("\n", " ").strip() if m_titulo else f"Resolución SRT {numero}"

    # Resumen: primer considerando o primer artículo relevante, recortado.
    m_resumen = re.search(r"CONSIDERANDO:\s*\n(.{0,400})", texto, re.DOTALL)
    resumen = (m_resumen.group(1).strip() + "…") if m_resumen else None

    # Estado: se marca "vigente" salvo que el propio texto diga "derogase esta resolución"
    # referida a sí misma (heurística simple; requiere revisión humana igual).
    estado = "vigente"

    if not numero:
        return None  # no se pudo parsear de forma confiable; se descarta y se revisa a mano

    return {
        "jurisdiccion": "nacional",
        "provincia": None,
        "organismo_emisor": "SRT",
        "tipo_norma": "resolucion",
        "numero": numero,
        "fecha_sancion": fecha_sancion,
        "fecha_publicacion": fecha_publicacion,
        "titulo": titulo,
        "resumen": resumen,
        "tema": "sst",
        "estado": estado,
        "norma_relacionada": None,
        "link_fuente": url,
    }


def obtener_o_crear_fuente(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT id FROM legal_sources_watch WHERE nombre_fuente = ?", (NOMBRE_FUENTE,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO legal_sources_watch (nombre_fuente, tipo_conector, url_base, frecuencia_recomendada) "
        "VALUES (?, 'scraper', ?, 'semanal')",
        (NOMBRE_FUENTE, BASE_URL),
    )
    return cur.lastrowid


def cargar_en_sqlite(db_path: str, normas: list[dict]) -> dict:
    conn = sqlite3.connect(db_path)
    conn.execute(DDL_LEGAL_SOURCES_WATCH)
    conn.execute(DDL_NORMAS_RAW)
    ahora = datetime.now(timezone.utc).isoformat()
    fuente_id = obtener_o_crear_fuente(conn)

    nuevas, sin_cambios, actualizadas = 0, 0, 0
    for n in normas:
        cur = conn.execute(
            """
            SELECT id, estado FROM normas_raw
            WHERE fuente_id = ? AND tipo_norma = ? AND numero = ? AND fecha_sancion = ?
            """,
            (fuente_id, n["tipo_norma"], n["numero"], n["fecha_sancion"]),
        )
        existente = cur.fetchone()

        if existente is None:
            conn.execute(
                """
                INSERT INTO normas_raw (
                    jurisdiccion, provincia, organismo_emisor, tipo_norma, numero,
                    fecha_sancion, fecha_publicacion, titulo, resumen, tema, estado,
                    norma_relacionada, link_fuente, fuente_id, primera_vez_detectada,
                    ultima_corrida_detectada, es_nuevo, fecha_scraping
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?)
                """,
                (
                    n["jurisdiccion"], n["provincia"], n["organismo_emisor"],
                    n["tipo_norma"], n["numero"], n["fecha_sancion"],
                    n["fecha_publicacion"], n["titulo"], n["resumen"], n["tema"],
                    n["estado"], n["norma_relacionada"], n["link_fuente"],
                    fuente_id, ahora, ahora, ahora,
                ),
            )
            nuevas += 1
        else:
            existente_id, estado_previo = existente
            if estado_previo != n["estado"]:
                conn.execute(
                    "UPDATE normas_raw SET estado = ?, ultima_corrida_detectada = ?, es_nuevo = 1, "
                    "cambio_detectado = ? WHERE id = ?",
                    (n["estado"], ahora, f"Estado cambió de '{estado_previo}' a '{n['estado']}'", existente_id),
                )
                actualizadas += 1
            else:
                conn.execute(
                    "UPDATE normas_raw SET ultima_corrida_detectada = ? WHERE id = ?", (ahora, existente_id)
                )
                sin_cambios += 1

    conn.execute("UPDATE legal_sources_watch SET ultima_corrida = ? WHERE id = ?", (ahora, fuente_id))
    conn.commit()
    conn.close()
    return {"nuevas": nuevas, "actualizadas": actualizadas, "sin_cambios": sin_cambios}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True)
    parser.add_argument("--desde", required=True, help="AAAA-MM-DD")
    parser.add_argument("--hasta", required=True, help="AAAA-MM-DD")
    parser.add_argument("--dry-run", action="store_true", help="No escribe en la base, solo imprime lo que encontró")
    args = parser.parse_args()

    desde = datetime.strptime(args.desde, "%Y-%m-%d")
    hasta = datetime.strptime(args.hasta, "%Y-%m-%d")

    encontradas = []
    dia = desde
    while dia <= hasta:
        print(f"Revisando {dia.strftime('%Y-%m-%d')}...", file=sys.stderr)
        try:
            urls = listar_avisos_del_dia(dia)
        except requests.RequestException as e:
            print(f"  error de red, se salta el día: {e}", file=sys.stderr)
            urls = []

        for url in urls:
            time.sleep(DELAY_ENTRE_REQUESTS_SEG)
            try:
                norma = parsear_aviso(url)
            except requests.RequestException as e:
                print(f"  error al leer {url}: {e}", file=sys.stderr)
                continue
            if norma:
                print(f"  encontrado: {norma['titulo']}", file=sys.stderr)
                encontradas.append(norma)

        dia += timedelta(days=1)
        time.sleep(DELAY_ENTRE_REQUESTS_SEG)

    print(f"\nTotal de resoluciones SRT encontradas en el rango: {len(encontradas)}")

    if args.dry_run:
        for n in encontradas:
            print(f"  - {n['numero']} · sanción {n['fecha_sancion']} · pub {n['fecha_publicacion']} · {n['link_fuente']}")
        print("\n(dry-run: nada se escribió en la base)")
        return

    resultado = cargar_en_sqlite(args.db, encontradas)
    print(
        f"Nuevas: {resultado['nuevas']} · Actualizadas: {resultado['actualizadas']} · "
        f"Sin cambios: {resultado['sin_cambios']}."
    )


if __name__ == "__main__":
    main()
