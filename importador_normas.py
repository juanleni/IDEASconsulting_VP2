from __future__ import annotations

import csv
import json
import os
from pathlib import Path

import fitz
from openai import OpenAI


DIRECTORIO_NORMAS = r"C:\Users\RRHH\Documents\IDEAS\Biblioteca"
CSV_REQUISITOS = Path("nicegui_v2") / "data" / "document_requirements.csv"
MODELO_OPENAI = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
MAX_CHARS_POR_BLOQUE = int(os.getenv("IMPORTADOR_NORMAS_MAX_CHARS", "12000"))

COLUMNAS_CSV = [
    "norma",
    "capitulo",
    "requisito",
    "resumen",
    "documento_esperado",
    "tipo_documento",
    "obligatorio",
    "observacion_consultiva",
]

PROMPT_SISTEMA = (
    "Eres un extractor de normas ISO/IATF. Tu objetivo es extraer los capitulos "
    "y requisitos de este texto. Debes devolver el TEXTO LITERAL EXACTO de la "
    "norma. Si el texto original esta en ingles, debes TRADUCIRLO AL ESPANOL "
    "manteniendo el tono tecnico normativo literal, sin resumir ni interpretar. "
    "Devuelve el resultado exclusivamente en formato JSON como una lista de "
    "diccionarios con las claves: 'norma', 'capitulo', 'requisito', "
    "'texto_literal'."
)


def extraer_texto_pdf(ruta_pdf: Path) -> list[str]:
    bloques: list[str] = []
    with fitz.open(ruta_pdf) as documento:
        for numero_pagina, pagina in enumerate(documento, start=1):
            texto = pagina.get_text("text").strip()
            if texto:
                bloques.append(f"\n--- PAGINA {numero_pagina} ---\n{texto}")
    return bloques


def agrupar_bloques(bloques: list[str], max_chars: int = MAX_CHARS_POR_BLOQUE) -> list[str]:
    grupos: list[str] = []
    actual: list[str] = []
    largo_actual = 0

    for bloque in bloques:
        if actual and largo_actual + len(bloque) > max_chars:
            grupos.append("\n".join(actual))
            actual = []
            largo_actual = 0
        actual.append(bloque)
        largo_actual += len(bloque)

    if actual:
        grupos.append("\n".join(actual))

    return grupos


def limpiar_json_respuesta(contenido: str) -> list[dict]:
    texto = contenido.strip()
    if texto.startswith("```"):
        texto = texto.strip("`").strip()
        if texto.lower().startswith("json"):
            texto = texto[4:].strip()

    data = json.loads(texto)
    if isinstance(data, dict):
        for clave in ("items", "requisitos", "resultados", "data"):
            if isinstance(data.get(clave), list):
                data = data[clave]
                break

    if not isinstance(data, list):
        raise ValueError("La respuesta de OpenAI no es una lista JSON.")

    requisitos: list[dict] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        requisitos.append(
            {
                "norma": str(item.get("norma", "")).strip(),
                "capitulo": str(item.get("capitulo", "")).strip(),
                "requisito": str(item.get("requisito", "")).strip(),
                "texto_literal": str(item.get("texto_literal", "")).strip(),
            }
        )
    return [item for item in requisitos if item["norma"] and item["requisito"] and item["texto_literal"]]


def traducir_y_extraer(cliente: OpenAI, nombre_pdf: str, texto: str) -> list[dict]:
    respuesta = cliente.chat.completions.create(
        model=MODELO_OPENAI,
        temperature=0,
        messages=[
            {"role": "system", "content": PROMPT_SISTEMA},
            {
                "role": "user",
                "content": (
                    f"Archivo fuente: {nombre_pdf}\n\n"
                    "Extrae solamente capitulos/requisitos normativos claros del siguiente texto. "
                    "No inventes requisitos ausentes y no agregues comentarios.\n\n"
                    f"{texto}"
                ),
            },
        ],
    )
    contenido = respuesta.choices[0].message.content or "[]"
    return limpiar_json_respuesta(contenido)


def cargar_csv_existente(ruta_csv: Path) -> dict[tuple[str, str, str], dict]:
    if not ruta_csv.exists():
        return {}

    with ruta_csv.open("r", encoding="utf-8-sig", newline="") as archivo:
        lector = csv.DictReader(archivo)
        filas = {}
        for fila in lector:
            clave = (
                (fila.get("norma") or "").strip().lower(),
                (fila.get("capitulo") or "").strip().lower(),
                (fila.get("requisito") or "").strip().lower(),
            )
            filas[clave] = fila
        return filas


def escribir_csv(ruta_csv: Path, requisitos: list[dict]) -> None:
    existentes = cargar_csv_existente(ruta_csv)
    filas_nuevas: list[dict] = []

    for requisito in requisitos:
        clave = (
            requisito["norma"].strip().lower(),
            requisito["capitulo"].strip().lower(),
            requisito["requisito"].strip().lower(),
        )
        fila_previa = existentes.get(clave, {})
        filas_nuevas.append(
            {
                "norma": requisito["norma"],
                "capitulo": requisito["capitulo"],
                "requisito": requisito["requisito"],
                "resumen": requisito["texto_literal"],
                "documento_esperado": fila_previa.get("documento_esperado", ""),
                "tipo_documento": fila_previa.get("tipo_documento", ""),
                "obligatorio": fila_previa.get("obligatorio", ""),
                "observacion_consultiva": fila_previa.get("observacion_consultiva", ""),
            }
        )

    ruta_csv.parent.mkdir(parents=True, exist_ok=True)
    with ruta_csv.open("w", encoding="utf-8-sig", newline="") as archivo:
        escritor = csv.DictWriter(archivo, fieldnames=COLUMNAS_CSV)
        escritor.writeheader()
        escritor.writerows(filas_nuevas)


def main() -> None:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Falta configurar la variable de entorno OPENAI_API_KEY.")

    directorio = Path(DIRECTORIO_NORMAS)
    if not directorio.exists():
        raise FileNotFoundError(f"No existe el directorio de normas: {directorio}")

    pdfs = sorted(directorio.glob("*.pdf"))
    if not pdfs:
        print(f"No se encontraron PDFs en {directorio}")
        return

    cliente = OpenAI(api_key=api_key)
    requisitos_totales: list[dict] = []

    for pdf in pdfs:
        print(f"Leyendo norma {pdf.name}...")
        try:
            bloques = extraer_texto_pdf(pdf)
            grupos = agrupar_bloques(bloques)
            print(f"Texto extraido: {len(bloques)} paginas con texto, {len(grupos)} bloques para IA.")

            for indice, grupo in enumerate(grupos, start=1):
                print(f"Traduciendo con IA {pdf.name} bloque {indice}/{len(grupos)}...")
                requisitos = traducir_y_extraer(cliente, pdf.name, grupo)
                requisitos_totales.extend(requisitos)
                print(f"Requisitos extraidos en este bloque: {len(requisitos)}")
        except Exception as exc:
            print(f"ERROR procesando {pdf.name}: {exc}")

    if not requisitos_totales:
        print("No se obtuvieron requisitos. El CSV no fue modificado.")
        return

    escribir_csv(CSV_REQUISITOS, requisitos_totales)
    print(f"CSV Actualizado: {CSV_REQUISITOS.resolve()}")
    print(f"Total de requisitos cargados: {len(requisitos_totales)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR general: {exc}")
