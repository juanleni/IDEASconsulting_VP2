#!/usr/bin/env python3
"""
sync_normativa_srt_digesto.py

Conector de la fuente "Digesto SRT" hacia normas_raw, usando la API real
descubierta por inspección de red (DevTools) sobre https://digesto.srt.gob.ar.

Endpoint:
    POST https://api.srt.gob.ar/v1/resoluciones/full
    Content-Type: application/json

Payload de ejemplo (confirmado por captura real del navegador):
    {
        "NroResolucion": null,
        "Cantidad": "100",
        "Asunto": null,
        "OrganismoEmisor": "",
        "TipoNorma": "",
        "BoletinOficial": null,
        "FechaDesde": "1996-05-10T03:00:00.000Z",
        "FechaHasta": "2026-07-27T03:00:00.000Z",
        "NroExpediente": null,
        "Voces": []
    }

Respuesta: array de objetos con Tipo, Organismo, Asunto, Link, Subtipo,
TieneArchvios, Numero, Anio, Fecha, NumeroAnio, NumeroAnioCorto, OID.

PENDIENTE DE CONFIRMAR (no incluido en esta versión, requiere otra captura
de red sobre el detalle de una norma puntual en el sitio):
  - El campo "Estado" (vigente/derogada/actualizada/parcialmente derogada)
    que menciona la FAQ del sitio no viene en este listado. Hasta tenerlo,
    todo se carga con estado="desconocido" para forzar revisión manual.
  - No se confirmó si "Cantidad" pagina resultados o es un tope absoluto.
    Si Cantidad=100 y hay más de 100 normas en el rango de fechas, esta
    versión NO las trae todas. Ver nota en main().

Requisitos:
    pip install requests

Uso:
    python sync_normativa_srt_digesto.py --db /ruta/a/ideas.db \
        --desde 1996-01-01 --hasta 2026-07-27 --dry-run
"""

import argparse
import sqlite3
import sys
from datetime import datetime, timezone

import requests

API_URL = "https://api.srt.gob.ar/v1/resoluciones/full"
NOMBRE_FUENTE = "Digesto SRT"
HEADERS = {"Content-Type": "application/json"}

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


def consultar_digesto(fecha_desde: str, fecha_hasta: str, cantidad: str = "1000") -> list[dict]:
    """
    fecha_desde / fecha_hasta en formato AAAA-MM-DD (se convierten al formato
    ISO con hora que usa la API, tal como se vio en la captura real).
    """
    payload = {
        "NroResolucion": None,
        "Cantidad": cantidad,
        "Asunto": None,
        "OrganismoEmisor": "",
        "TipoNorma": "",
        "BoletinOficial": None,
        "FechaDesde": f"{fecha_desde}T03:00:00.000Z",
        "FechaHasta": f"{fecha_hasta}T03:00:00.000Z",
        "NroExpediente": None,
        "Voces": [],
    }
    resp = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    # La API puede devolver la lista directamente o envuelta en una clave
    # (ej. {"Resultados": [...]})  -- ajustar acá si hace falta tras probar.
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("Resultados", "Items", "Data", "resultados"):
            if key in data and isinstance(data[key], list):
                return data[key]
    raise ValueError(
        "No se pudo interpretar la forma de la respuesta. "
        "Revisar manualmente la estructura del JSON devuelto por la API."
    )


def normalizar(items: list[dict]) -> list[dict]:
    normas = []
    for it in items:
        tipo = (it.get("Tipo") or "").strip().lower()
        organismo = (it.get("Organismo") or "").strip()
        normas.append({
            "jurisdiccion": "nacional",
            "provincia": None,
            "organismo_emisor": organismo or "SRT",
            "tipo_norma": tipo,
            "numero": it.get("NumeroAnio") or str(it.get("Numero", "")),
            "fecha_sancion": (it.get("Fecha") or "")[:10] if it.get("Fecha") else None,
            "fecha_publicacion": None,  # no viene en este endpoint
            "titulo": f"{it.get('Tipo', '')} {it.get('NumeroAnio', '')}".strip(),
            "resumen": it.get("Asunto"),
            "tema": "sst",
            "estado": "desconocido",  # pendiente: no viene en este endpoint, ver docstring
            "norma_relacionada": None,
            "link_fuente": it.get("Link"),
        })
    return normas


def obtener_o_crear_fuente(conn: sqlite3.Connection) -> int:
    cur = conn.execute("SELECT id FROM legal_sources_watch WHERE nombre_fuente = ?", (NOMBRE_FUENTE,))
    row = cur.fetchone()
    if row:
        return row[0]
    cur = conn.execute(
        "INSERT INTO legal_sources_watch (nombre_fuente, tipo_conector, url_base, frecuencia_recomendada) "
        "VALUES (?, 'api', ?, 'semanal')",
        (NOMBRE_FUENTE, API_URL),
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
    parser.add_argument("--cantidad", default="1000", help="Tope de resultados a pedir (ver nota de paginación)")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    items = consultar_digesto(args.desde, args.hasta, args.cantidad)
    print(f"La API devolvió {len(items)} normas en el rango pedido.", file=sys.stderr)

    if len(items) >= int(args.cantidad):
        print(
            f"AVISO: la cantidad devuelta ({len(items)}) es igual o mayor al parámetro "
            f"--cantidad ({args.cantidad}). Es probable que haya más normas de las que "
            f"trajo esta corrida y falte paginar. Revisar si la API acepta un parámetro "
            f"de página/offset antes de asumir que esto es todo el universo.",
            file=sys.stderr,
        )

    normas = normalizar(items)

    if args.dry_run:
        for n in normas[:20]:
            print(f"  - {n['tipo_norma']} {n['numero']} · {n['fecha_sancion']} · {n['resumen'][:60] if n['resumen'] else ''}")
        print(f"\n(dry-run: se muestran hasta 20 de {len(normas)}. Nada se escribió en la base)")
        return

    resultado = cargar_en_sqlite(args.db, normas)
    print(
        f"Nuevas: {resultado['nuevas']} · Actualizadas: {resultado['actualizadas']} · "
        f"Sin cambios: {resultado['sin_cambios']}."
    )
    print(
        "Recordatorio: 'estado' quedó como 'desconocido' para todo lo cargado desde esta "
        "fuente (el campo real de vigencia no vino en este endpoint). Revisar manualmente "
        "antes de aprobar hacia legal_requirements."
    )


if __name__ == "__main__":
    main()
