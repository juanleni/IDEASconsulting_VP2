#!/usr/bin/env python3
"""
sync_normativa_saij.py

Descarga la Base SAIJ de Normativa Provincial (dataset abierto del Ministerio
de Justicia, actualizado mensualmente) y carga en la tabla `normas_raw` de
ideas.db las normas de la/s provincia/s y temas configurados.

Uso exclusivo de IDEAS_ADMIN. No expone nada a empresa_id de clientes.

Fuente: https://datos.jus.gob.ar/dataset/base-saij-de-normativa-provincial
Licencia: Creative Commons Attribution 4.0
Actualización de la fuente: mensual.

Requisitos:
    pip install requests

Uso:
    python sync_normativa_saij.py --db /ruta/a/ideas.db --provincia "Buenos Aires"
"""

import argparse
import csv
import io
import sqlite3
import sys
from datetime import datetime, timezone

import requests

SAIJ_CSV_URL = (
    "https://datos.jus.gob.ar/dataset/d59c2d29-d561-4ad2-a032-cc82b40db2d3/"
    "resource/0ebc70cc-0e71-4158-ab75-9759339e4cbd/download/"
    "base-saij-normativa-provincial.csv"
)

# Palabras clave para filtrar temas relevantes (Ambiente y SST).
# Se buscan en titulo_resumido + titulo_sumario. Ajustar/ampliar según haga falta.
KEYWORDS_AMBIENTE = [
    "ambiente", "ambiental", "residuo", "efluente", "atmosfera", "atmósfera",
    "agua", "hidrico", "hídrico", "contaminacion", "contaminación",
    "impacto ambiental", "industrial", "radicacion industrial",
    "radicación industrial", "ruido", "aptitud ambiental",
]
KEYWORDS_SST = [
    "higiene y seguridad", "seguridad e higiene", "riesgos del trabajo",
    "salud ocupacional", "salud y seguridad", "comite mixto", "comité mixto",
    "accidente de trabajo", "enfermedad profesional", "violencia laboral",
    "condiciones de trabajo",
]

DDL_NORMAS_RAW = """
CREATE TABLE IF NOT EXISTS normas_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jurisdiccion TEXT NOT NULL,          -- nacional | provincial | municipal | organismo
    provincia TEXT,
    organismo_emisor TEXT,
    tipo_norma TEXT,
    numero TEXT,
    fecha_sancion TEXT,
    fecha_publicacion TEXT,
    titulo TEXT,
    resumen TEXT,
    tema TEXT,                            -- ambiente | sst | ambos | otro
    estado TEXT,                          -- vigente | derogada | modificatoria | sin_eficacia
    norma_relacionada TEXT,
    link_fuente TEXT,
    fuente_dataset TEXT,                  -- de dónde vino el registro (para trazabilidad)
    fecha_scraping TEXT,
    revisado_por TEXT,
    fecha_aprobacion TEXT,
    publicado_a_empresa INTEGER DEFAULT 0,
    UNIQUE(provincia, tipo_norma, numero, fecha_sancion)
);
"""

ESTADO_MAP = {
    "vigente de alcance general": "vigente",
    "vigente": "vigente",
    "derogada": "derogada",
    "individual": "individual",
    "solo modificatoria": "modificatoria",
    "sin eficacia": "sin_eficacia",
}


def clasificar_tema(texto: str) -> str:
    texto_l = texto.lower()
    es_ambiente = any(k in texto_l for k in KEYWORDS_AMBIENTE)
    es_sst = any(k in texto_l for k in KEYWORDS_SST)
    if es_ambiente and es_sst:
        return "ambos"
    if es_ambiente:
        return "ambiente"
    if es_sst:
        return "sst"
    return ""  # no relevante -> se descarta aguas abajo


def descargar_csv(url: str) -> list[dict]:
    print(f"Descargando dataset SAIJ desde {url} ...", file=sys.stderr)
    resp = requests.get(url, timeout=120)
    resp.raise_for_status()
    # El CSV viene delimitado por coma, UTF-8 (según metadata oficial).
    contenido = resp.content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(contenido))
    filas = list(reader)
    print(f"{len(filas)} filas descargadas del dataset completo.", file=sys.stderr)
    return filas


def filtrar_y_normalizar(filas: list[dict], provincias: list[str]) -> list[dict]:
    provincias_norm = {p.strip().lower() for p in provincias}
    resultado = []
    for fila in filas:
        provincia = (fila.get("provincia_nombre") or "").strip()
        if provincias_norm and provincia.lower() not in provincias_norm:
            continue

        titulo_resumido = (fila.get("titulo_resumido") or "").strip()
        titulo_sumario = (fila.get("titulo_sumario") or "").strip()
        nombre_norma = (fila.get("nombre_norma") or "").strip()
        texto_para_tema = " ".join([titulo_resumido, titulo_sumario, nombre_norma])

        tema = clasificar_tema(texto_para_tema)
        if not tema:
            continue  # descarta normas fuera del alcance ambiente/SST

        estado_raw = (fila.get("estado_vigencia") or "").strip().lower()
        estado = ESTADO_MAP.get(estado_raw, estado_raw or "desconocido")

        resultado.append({
            "jurisdiccion": "provincial",
            "provincia": provincia,
            "organismo_emisor": None,  # el dataset no discrimina organismo emisor
            "tipo_norma": (fila.get("tipo_norma") or "").strip().lower(),
            "numero": (fila.get("numero_norma") or "").strip(),
            "fecha_sancion": (fila.get("fecha") or "").strip(),
            "fecha_publicacion": (fila.get("fecha_publicacion") or "").strip(),
            "titulo": nombre_norma or titulo_resumido,
            "resumen": titulo_sumario or titulo_resumido,
            "tema": tema,
            "estado": estado,
            "norma_relacionada": (fila.get("informacion_digesto") or "").strip() or None,
            "link_fuente": (fila.get("texto_actualizado") or "").strip() or None,
        })
    print(f"{len(resultado)} normas relevantes (ambiente/SST) tras el filtro.", file=sys.stderr)
    return resultado


def cargar_en_sqlite(db_path: str, normas: list[dict]) -> tuple[int, int]:
    conn = sqlite3.connect(db_path)
    conn.execute(DDL_NORMAS_RAW)
    ahora = datetime.now(timezone.utc).isoformat()

    insertados, ya_existian = 0, 0
    for n in normas:
        try:
            conn.execute(
                """
                INSERT INTO normas_raw (
                    jurisdiccion, provincia, organismo_emisor, tipo_norma, numero,
                    fecha_sancion, fecha_publicacion, titulo, resumen, tema, estado,
                    norma_relacionada, link_fuente, fuente_dataset, fecha_scraping,
                    revisado_por, fecha_aprobacion, publicado_a_empresa
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NULL, NULL, 0)
                """,
                (
                    n["jurisdiccion"], n["provincia"], n["organismo_emisor"],
                    n["tipo_norma"], n["numero"], n["fecha_sancion"],
                    n["fecha_publicacion"], n["titulo"], n["resumen"], n["tema"],
                    n["estado"], n["norma_relacionada"], n["link_fuente"],
                    "SAIJ - Base Normativa Provincial", ahora,
                ),
            )
            insertados += 1
        except sqlite3.IntegrityError:
            # Ya existe (mismo provincia+tipo+numero+fecha_sancion) -> se ignora.
            ya_existian += 1
    conn.commit()
    conn.close()
    return insertados, ya_existian


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Ruta a ideas.db")
    parser.add_argument(
        "--provincia", action="append", default=[],
        help="Provincia a filtrar (repetible). Sin este flag, no filtra por provincia.",
    )
    parser.add_argument(
        "--csv-cache", default=None,
        help="Si se pasa, guarda una copia local del CSV descargado en esta ruta.",
    )
    args = parser.parse_args()

    filas = descargar_csv(SAIJ_CSV_URL)

    if args.csv_cache:
        with open(args.csv_cache, "w", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=filas[0].keys())
            writer.writeheader()
            writer.writerows(filas)
        print(f"Copia cruda guardada en {args.csv_cache}", file=sys.stderr)

    normas = filtrar_y_normalizar(filas, args.provincia)
    insertados, ya_existian = cargar_en_sqlite(args.db, normas)

    print(f"\nListo. Nuevas normas insertadas: {insertados}. Ya existentes (omitidas): {ya_existian}.")


if __name__ == "__main__":
    main()
