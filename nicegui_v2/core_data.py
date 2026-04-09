from __future__ import annotations

import datetime
import json
import os
import sqlite3
from functools import lru_cache

import pandas as pd

DB_PATH = "ideas.db"
EXCEL_PATH = "Data/diagnostico.xlsx"


def _normalizar_respuestas_para_firma(respuestas_guardar):
    return [
        {
            "eje": str(item.get("eje", "")).strip(),
            "pregunta": str(item.get("pregunta", "")).strip(),
            "respuesta": int(item.get("respuesta", 0)),
            "evidencia": str(item.get("evidencia", "")).strip(),
            "observacion": str(item.get("observacion", "")).strip(),
        }
        for item in respuestas_guardar
    ]


def _firma_respuestas(respuestas_guardar) -> str:
    normalizadas = _normalizar_respuestas_para_firma(respuestas_guardar)
    return json.dumps(normalizadas, ensure_ascii=False, sort_keys=True)


def _clear_caches() -> None:
    leer_diagnostico_excel.cache_clear()
    obtener_empresas.cache_clear()
    obtener_empresa_detalle.cache_clear()
    obtener_diagnosticos_empresa.cache_clear()
    obtener_respuestas_diagnostico.cache_clear()
    obtener_historial_diagnosticos.cache_clear()


@lru_cache(maxsize=1)
def leer_diagnostico_excel() -> pd.DataFrame:
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError("No se encontró el archivo Data/diagnostico.xlsx")

    xls = pd.ExcelFile(EXCEL_PATH)
    sheet_name = "DIAGNOSTICO" if "DIAGNOSTICO" in xls.sheet_names else xls.sheet_names[0]

    df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
    df.columns = [str(col).strip().upper() for col in df.columns]

    if "EJE" not in df.columns or "PREGUNTA" not in df.columns:
        raise ValueError(f"El Excel debe tener columnas EJE y PREGUNTA. Columnas detectadas: {list(df.columns)}")

    df["EJE"] = df["EJE"].astype(str).str.strip()
    df["PREGUNTA"] = df["PREGUNTA"].astype(str).str.strip()
    df = df[(df["EJE"] != "") & (df["PREGUNTA"] != "")]
    df = df.dropna(subset=["EJE", "PREGUNTA"])
    return df


@lru_cache(maxsize=1)
def obtener_empresas():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social
        FROM empresas
        ORDER BY COALESCE(NULLIF(razon_social, ''), nombre)
        """
    )
    empresas = c.fetchall()
    conn.close()
    return empresas


@lru_cache(maxsize=128)
def obtener_empresa_detalle(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social,
            ubicacion,
            contacto_nombre,
            contacto_correo,
            contacto_telefono,
            contacto_posicion,
            rubro,
            cantidad_empleados,
            cert_iso_9001,
            cert_iso_14001,
            cert_iso_45001,
            cert_iatf
        FROM empresas
        WHERE id = ?
        """,
        (empresa_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    keys = [
        "id",
        "razon_social",
        "ubicacion",
        "contacto_nombre",
        "contacto_correo",
        "contacto_telefono",
        "contacto_posicion",
        "rubro",
        "cantidad_empleados",
        "cert_iso_9001",
        "cert_iso_14001",
        "cert_iso_45001",
        "cert_iatf",
    ]
    return dict(zip(keys, row))


@lru_cache(maxsize=128)
def obtener_diagnosticos_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, fecha, score, nivel, conclusion
        FROM diagnosticos
        WHERE empresa_id = ?
        ORDER BY fecha DESC
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


@lru_cache(maxsize=256)
def obtener_respuestas_diagnostico(diagnostico_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT eje, pregunta, respuesta, evidencia, observacion
        FROM respuestas
        WHERE diagnostico_id = ?
        ORDER BY id
        """,
        (diagnostico_id,),
    )
    rows = c.fetchall()
    conn.close()
    return rows


@lru_cache(maxsize=1)
def obtener_historial_diagnosticos():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            d.id,
            d.empresa_id,
            COALESCE(NULLIF(e.razon_social, ''), e.nombre) AS empresa,
            d.fecha,
            d.score,
            d.nivel,
            d.conclusion
        FROM diagnosticos d
        JOIN empresas e ON e.id = d.empresa_id
        ORDER BY empresa, d.fecha DESC
        """
    )
    rows = c.fetchall()
    conn.close()
    return rows


def guardar_empresa(empresa_data):
    razon_social = str(empresa_data["razon_social"]).strip()
    if not razon_social:
        return False, "La razón social no puede estar vacía."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO empresas (
                nombre,
                razon_social,
                ubicacion,
                contacto_nombre,
                contacto_correo,
                contacto_telefono,
                contacto_posicion,
                rubro,
                cantidad_empleados,
                cert_iso_9001,
                cert_iso_14001,
                cert_iso_45001,
                cert_iatf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                razon_social,
                razon_social,
                str(empresa_data["ubicacion"]).strip(),
                str(empresa_data["contacto_nombre"]).strip(),
                str(empresa_data["contacto_correo"]).strip(),
                str(empresa_data["contacto_telefono"]).strip(),
                str(empresa_data["contacto_posicion"]).strip(),
                str(empresa_data["rubro"]).strip(),
                empresa_data["cantidad_empleados"],
                empresa_data["cert_iso_9001"],
                empresa_data["cert_iso_14001"],
                empresa_data["cert_iso_45001"],
                empresa_data["cert_iatf"],
            ),
        )
        conn.commit()
        _clear_caches()
        return True, "Empresa guardada correctamente."
    except sqlite3.IntegrityError:
        return False, "Esa empresa ya existe."
    finally:
        conn.close()


def guardar_diagnostico(empresa_id, score, nivel, conclusion, respuestas_guardar):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    firma_actual = _firma_respuestas(respuestas_guardar)

    c.execute(
        """
        SELECT id, fecha, score, nivel, conclusion
        FROM diagnosticos
        WHERE empresa_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (empresa_id,),
    )
    ultimo_diag = c.fetchone()

    if ultimo_diag:
        ultimo_diag_id, ultima_fecha, ultimo_score, ultimo_nivel, _ultima_conclusion = ultimo_diag
        c.execute(
            """
            SELECT eje, pregunta, respuesta, evidencia, observacion
            FROM respuestas
            WHERE diagnostico_id = ?
            ORDER BY id
            """,
            (ultimo_diag_id,),
        )
        respuestas_ultimo = c.fetchall()
        respuestas_ultimo_norm = [
            {
                "eje": row[0],
                "pregunta": row[1],
                "respuesta": row[2],
                "evidencia": row[3] or "",
                "observacion": row[4] or "",
            }
            for row in respuestas_ultimo
        ]
        misma_firma = _firma_respuestas(respuestas_ultimo_norm) == firma_actual
        mismo_contexto = (
            float(ultimo_score) == float(score)
            and str(ultimo_nivel) == str(nivel)
            and str(ultima_fecha) == str(fecha)
        )
        if misma_firma and mismo_contexto:
            conn.close()
            return ultimo_diag_id, ultima_fecha, True

    c.execute(
        """
        INSERT INTO diagnosticos (empresa_id, fecha, score, nivel, conclusion)
        VALUES (?, ?, ?, ?, ?)
        """,
        (empresa_id, fecha, score, nivel, conclusion),
    )
    diagnostico_id = c.lastrowid

    for item in respuestas_guardar:
        c.execute(
            """
            INSERT INTO respuestas (diagnostico_id, eje, pregunta, respuesta, evidencia, observacion)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                diagnostico_id,
                item["eje"],
                item["pregunta"],
                item["respuesta"],
                item["evidencia"],
                item["observacion"],
            ),
        )

    conn.commit()
    conn.close()
    _clear_caches()
    return diagnostico_id, fecha, False


def actualizar_diagnostico(diagnostico_id, empresa_id, score, nivel, conclusion, respuestas_guardar):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()

    c.execute(
        """
        SELECT fecha, score, nivel, conclusion
        FROM diagnosticos
        WHERE id = ?
        """,
        (diagnostico_id,),
    )
    row = c.fetchone()
    if not row:
        conn.close()
        raise ValueError("El diagnóstico que intentas editar no existe.")

    fecha_existente, score_existente, nivel_existente, _conclusion_existente = row
    firma_actual = _firma_respuestas(respuestas_guardar)

    c.execute(
        """
        SELECT eje, pregunta, respuesta, evidencia, observacion
        FROM respuestas
        WHERE diagnostico_id = ?
        ORDER BY id
        """,
        (diagnostico_id,),
    )
    respuestas_existentes = c.fetchall()
    respuestas_existentes_norm = [
        {
            "eje": item[0],
            "pregunta": item[1],
            "respuesta": item[2],
            "evidencia": item[3] or "",
            "observacion": item[4] or "",
        }
        for item in respuestas_existentes
    ]
    sin_cambios = (
        float(score_existente) == float(score)
        and str(nivel_existente) == str(nivel)
        and _firma_respuestas(respuestas_existentes_norm) == firma_actual
    )
    if sin_cambios:
        conn.close()
        return diagnostico_id, fecha_existente, True

    c.execute(
        """
        UPDATE diagnosticos
        SET empresa_id = ?, score = ?, nivel = ?, conclusion = ?
        WHERE id = ?
        """,
        (empresa_id, score, nivel, conclusion, diagnostico_id),
    )
    c.execute("DELETE FROM respuestas WHERE diagnostico_id = ?", (diagnostico_id,))
    for item in respuestas_guardar:
        c.execute(
            """
            INSERT INTO respuestas (diagnostico_id, eje, pregunta, respuesta, evidencia, observacion)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                diagnostico_id,
                item["eje"],
                item["pregunta"],
                item["respuesta"],
                item["evidencia"],
                item["observacion"],
            ),
        )

    conn.commit()
    conn.close()
    _clear_caches()
    return diagnostico_id, fecha_existente, False


def eliminar_diagnostico(diagnostico_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM respuestas WHERE diagnostico_id = ?", (diagnostico_id,))
    c.execute("DELETE FROM diagnosticos WHERE id = ?", (diagnostico_id,))
    conn.commit()
    conn.close()
    _clear_caches()
