from __future__ import annotations

import datetime
import difflib
import json
import os
import re
import sqlite3
import unicodedata
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


def _strip_accents(texto: str) -> str:
    return "".join(
        char for char in unicodedata.normalize("NFKD", str(texto or "")) if not unicodedata.combining(char)
    )


def _normalize_legal_name(texto: str) -> str:
    text = _strip_accents(texto).lower()
    text = re.sub(r"[^\w\s./-]", " ", text)
    text = re.sub(r"\b(nro|n°|no|numero|num)\b", " ", text)
    text = re.sub(r"\b(de la|de las|de los|del|de|la|las|los|el|y)\b", " ", text)
    text = re.sub(r"\b(ley|decreto|resolucion|res|ordenanza|disposicion|norma)\b", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_legal_numbers(texto: str) -> tuple[str, ...]:
    normalized = _strip_accents(texto).lower().replace(",", ".")
    matches = re.findall(r"\b\d{1,5}(?:[./-]\d{1,5})+\b|\b\d{4,6}\b", normalized)
    cleaned = []
    for item in matches:
        value = item.replace("/", ".").replace("-", ".")
        if value not in cleaned:
            cleaned.append(value)
    return tuple(cleaned)


def _is_almost_duplicate_legal_name(base_name: str, candidate_name: str) -> bool:
    base_normalized = _normalize_legal_name(base_name)
    candidate_normalized = _normalize_legal_name(candidate_name)
    if not base_normalized or not candidate_normalized:
        return False

    base_numbers = set(_extract_legal_numbers(base_name))
    candidate_numbers = set(_extract_legal_numbers(candidate_name))
    if base_numbers and candidate_numbers and base_numbers.intersection(candidate_numbers):
        return True

    ratio = difflib.SequenceMatcher(None, base_normalized, candidate_normalized).ratio()
    if ratio >= 0.9:
        return True

    base_tokens = {token for token in base_normalized.split() if len(token) > 2}
    candidate_tokens = {token for token in candidate_normalized.split() if len(token) > 2}
    if base_tokens and candidate_tokens:
        overlap = len(base_tokens.intersection(candidate_tokens)) / max(1, min(len(base_tokens), len(candidate_tokens)))
        if overlap >= 0.8 and ratio >= 0.8:
            return True
    return False


def _find_legal_duplicate(cursor, empresa_id: int, jurisdiccion: str, norma_legal: str, exclude_id: int | None = None):
    query = """
        SELECT id, norma_legal
        FROM matriz_legal_ambiental
        WHERE empresa_id = ?
          AND lower(trim(jurisdiccion)) = lower(trim(?))
    """
    params: list[object] = [empresa_id, jurisdiccion]
    if exclude_id is not None:
        query += " AND id <> ?"
        params.append(exclude_id)
    cursor.execute(query, tuple(params))
    for existing_id, existing_name in cursor.fetchall():
        existing_text = str(existing_name or "").strip()
        if not existing_text:
            continue
        if existing_text.casefold() == str(norma_legal or "").strip().casefold():
            return existing_id, "exacto"
        if _is_almost_duplicate_legal_name(existing_text, str(norma_legal or "").strip()):
            return existing_id, "similar"
    return None


def _clear_caches() -> None:
    leer_diagnostico_excel.cache_clear()
    obtener_empresas.cache_clear()
    obtener_empresa_detalle.cache_clear()
    obtener_diagnosticos_empresa.cache_clear()
    obtener_respuestas_diagnostico.cache_clear()
    obtener_historial_diagnosticos.cache_clear()
    obtener_mapa_procesos_empresa.cache_clear()
    obtener_kpis_empresa.cache_clear()
    obtener_kpi_detalle.cache_clear()
    obtener_grupos_kpi_empresa.cache_clear()
    obtener_matrices_riesgos_empresa.cache_clear()
    obtener_matriz_riesgos_detalle.cache_clear()
    obtener_items_riesgos_matriz.cache_clear()
    obtener_aspectos_ambientales_empresa.cache_clear()
    obtener_aspecto_ambiental_detalle.cache_clear()
    obtener_requisitos_legales_ambientales_empresa.cache_clear()
    obtener_requisito_legal_ambiental_detalle.cache_clear()
    obtener_simulacros_ambientales_empresa.cache_clear()
    obtener_simulacro_ambiental_detalle.cache_clear()
    obtener_problemas_calidad_empresa.cache_clear()
    obtener_problema_calidad_detalle.cache_clear()
    obtener_5_porque_problema_calidad.cache_clear()
    obtener_ishikawa_problema_calidad.cache_clear()
    obtener_acciones_8d.cache_clear()
    obtener_fuentes_empresa.cache_clear()
    obtener_alertas_globales.cache_clear()
    obtener_usuarios.cache_clear()
    if hasattr(verificar_usuario, "cache_clear"):
        verificar_usuario.cache_clear()


def _kpi_now_str() -> str:
    return datetime.datetime.now().strftime("%d.%m.%Y %H:%M")


def _ensure_kpi_groups_table() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS kpi_grupos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            nombre TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_kpi_grupos_empresa_nombre
        ON kpi_grupos (empresa_id, nombre)
        """
    )
    conn.commit()
    conn.close()


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
            password,
            contacto_telefono,
            contacto_posicion,
            rubro,
            cantidad_empleados,
            cert_iso_9001,
            cert_iso_14001,
            cert_iso_45001,
            cert_iatf,
            logo_path,
            color_primario,
            color_secundario,
            agente_ia_activo
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
        "password",
        "contacto_telefono",
        "contacto_posicion",
        "rubro",
        "cantidad_empleados",
        "cert_iso_9001",
        "cert_iso_14001",
        "cert_iso_45001",
        "cert_iatf",
        "logo_path",
        "color_primario",
        "color_secundario",
        "agente_ia_activo",
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
                password,
                contacto_telefono,
                contacto_posicion,
                rubro,
                cantidad_empleados,
                cert_iso_9001,
                cert_iso_14001,
                cert_iso_45001,
                cert_iatf,
                logo_path,
                color_primario,
                color_secundario,
                agente_ia_activo
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                razon_social,
                razon_social,
                str(empresa_data["ubicacion"]).strip(),
                str(empresa_data["contacto_nombre"]).strip(),
                str(empresa_data["contacto_correo"]).strip(),
                str(empresa_data.get("password") or "").strip(),
                str(empresa_data["contacto_telefono"]).strip(),
                str(empresa_data["contacto_posicion"]).strip(),
                str(empresa_data["rubro"]).strip(),
                empresa_data["cantidad_empleados"],
                empresa_data["cert_iso_9001"],
                empresa_data["cert_iso_14001"],
                empresa_data["cert_iso_45001"],
                empresa_data["cert_iatf"],
                str(empresa_data.get("logo_path") or "").strip(),
                str(empresa_data.get("color_primario") or "").strip(),
                str(empresa_data.get("color_secundario") or "").strip(),
                int(bool(empresa_data.get("agente_ia_activo"))),
            ),
        )
        conn.commit()
        _clear_caches()
        return True, "Empresa guardada correctamente."
    except sqlite3.IntegrityError:
        return False, "Esa empresa ya existe."
    finally:
        conn.close()


def verificar_login_empresa(correo, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social
        FROM empresas
        WHERE lower(trim(contacto_correo)) = lower(trim(?))
          AND password = ?
        LIMIT 1
        """,
        (str(correo).strip(), str(password).strip()),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return row


def _ensure_empresa_reset_columns() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("PRAGMA table_info(empresas)")
    cols = {row[1] for row in c.fetchall()}
    if "reset_token" not in cols:
        c.execute("ALTER TABLE empresas ADD COLUMN reset_token TEXT")
    if "token_expiry" not in cols:
        c.execute("ALTER TABLE empresas ADD COLUMN token_expiry DATETIME")
    conn.commit()
    conn.close()


def guardar_token_empresa(correo, token, expiracion_minutos=1440):
    _ensure_empresa_reset_columns()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    expiry = (datetime.datetime.now() + datetime.timedelta(minutes=int(expiracion_minutos))).strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """
        UPDATE empresas
        SET reset_token = ?, token_expiry = ?
        WHERE lower(trim(contacto_correo)) = lower(trim(?))
        """,
        (str(token).strip(), expiry, str(correo).strip()),
    )
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    _clear_caches()
    return ok


def verificar_token_empresa(token):
    _ensure_empresa_reset_columns()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute(
        """
        SELECT id
        FROM empresas
        WHERE reset_token = ?
          AND token_expiry IS NOT NULL
          AND token_expiry >= ?
        LIMIT 1
        """,
        (str(token).strip(), now_str),
    )
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row else None


def actualizar_password_empresa(empresa_id, nuevo_password):
    _ensure_empresa_reset_columns()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE empresas
        SET password = ?, reset_token = NULL, token_expiry = NULL
        WHERE id = ?
        """,
        (str(nuevo_password or "").strip(), int(empresa_id)),
    )
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    _clear_caches()
    return ok


def actualizar_empresa(empresa_id, empresa_data):
    razon_social = str(empresa_data["razon_social"]).strip()
    if not razon_social:
        return False, "La razón social no puede estar vacía."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            UPDATE empresas
            SET
                nombre = ?,
                razon_social = ?,
                ubicacion = ?,
                contacto_nombre = ?,
                contacto_correo = ?,
                password = ?,
                contacto_telefono = ?,
                contacto_posicion = ?,
                rubro = ?,
                cantidad_empleados = ?,
                cert_iso_9001 = ?,
                cert_iso_14001 = ?,
                cert_iso_45001 = ?,
                cert_iatf = ?,
                logo_path = ?,
                color_primario = ?,
                color_secundario = ?,
                agente_ia_activo = ?
            WHERE id = ?
            """,
            (
                razon_social,
                razon_social,
                str(empresa_data["ubicacion"]).strip(),
                str(empresa_data["contacto_nombre"]).strip(),
                str(empresa_data["contacto_correo"]).strip(),
                str(empresa_data.get("password") or "").strip(),
                str(empresa_data["contacto_telefono"]).strip(),
                str(empresa_data["contacto_posicion"]).strip(),
                str(empresa_data["rubro"]).strip(),
                int(empresa_data["cantidad_empleados"] or 0),
                empresa_data["cert_iso_9001"],
                empresa_data["cert_iso_14001"],
                empresa_data["cert_iso_45001"],
                empresa_data["cert_iatf"],
                str(empresa_data.get("logo_path") or "").strip(),
                str(empresa_data.get("color_primario") or "").strip(),
                str(empresa_data.get("color_secundario") or "").strip(),
                int(bool(empresa_data.get("agente_ia_activo"))),
                int(empresa_id),
            ),
        )
        conn.commit()
        _clear_caches()
        return True, "Empresa actualizada correctamente."
    finally:
        conn.close()


def guardar_fuente_empresa(empresa_id, titulo, tipo, contenido):
    titulo_limpio = str(titulo or "").strip()
    contenido_limpio = str(contenido or "").strip()
    if not titulo_limpio:
        return False, "El titulo de la fuente no puede estar vacio.", None
    if not contenido_limpio:
        return False, "La fuente no tiene contenido util para guardar.", None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    fecha_carga = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    c.execute(
        """
        INSERT INTO empresa_fuentes (
            empresa_id,
            titulo,
            tipo,
            contenido,
            fecha_carga
        ) VALUES (?, ?, ?, ?, ?)
        """,
        (
            int(empresa_id),
            titulo_limpio,
            str(tipo or "").strip(),
            contenido_limpio,
            fecha_carga,
        ),
    )
    fuente_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Fuente guardada correctamente.", fuente_id


@lru_cache(maxsize=256)
def obtener_fuentes_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, empresa_id, titulo, tipo, contenido, fecha_carga
        FROM empresa_fuentes
        WHERE empresa_id = ?
        ORDER BY fecha_carga DESC, id DESC
        """,
        (int(empresa_id),),
    )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "empresa_id", "titulo", "tipo", "contenido", "fecha_carga"]
    return [dict(zip(keys, row)) for row in rows]


def eliminar_fuente(fuente_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM empresa_fuentes WHERE id = ?", (int(fuente_id),))
    conn.commit()
    conn.close()
    _clear_caches()


def _parsear_fecha_alerta(valor):
    texto = str(valor or "").strip()
    if not texto:
        return None
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%d.%m.%Y", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            return datetime.datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


@lru_cache(maxsize=1)
def obtener_alertas_globales():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            e.id,
            COALESCE(NULLIF(e.razon_social, ''), e.nombre) AS empresa,
            p.id AS problema_id,
            p.titulo,
            a.fase_8d,
            a.accion,
            a.responsable,
            a.fecha,
            a.progreso
        FROM calidad_8d_acciones a
        JOIN calidad_problemas_8d p ON p.id = a.problema_id
        JOIN empresas e ON e.id = p.empresa_id
        ORDER BY a.fecha, a.id
        """
    )
    rows = c.fetchall()
    conn.close()

    hoy = datetime.date.today()
    alertas = []
    for row in rows:
        empresa_id, empresa, problema_id, titulo, fase_8d, accion, responsable, fecha, progreso = row
        progreso_texto = str(progreso or "").strip()
        progreso_num = int(re.sub(r"[^0-9]", "", progreso_texto) or 0)
        if progreso_num >= 100:
            continue

        fecha_alerta = _parsear_fecha_alerta(fecha)
        if fecha_alerta is None:
            estado = "Sin fecha"
        else:
            delta = (fecha_alerta - hoy).days
            if delta < 0:
                estado = "Vencida"
            elif delta <= 7:
                estado = "Proxima"
            else:
                continue

        detalle = f"{str(titulo or 'Accion 8D').strip()} · {str(accion or '').strip()}".strip(" ·")
        alertas.append(
            {
                "empresa_id": int(empresa_id),
                "empresa": str(empresa or "").strip(),
                "tipo": f"Accion {str(fase_8d or '8D').strip()}",
                "detalle": detalle,
                "estado": estado,
                "responsable": str(responsable or "").strip(),
                "fecha": str(fecha or "").strip(),
                "problema_id": int(problema_id),
            }
        )

    alertas.sort(
        key=lambda item: (
            0 if item["estado"] == "Vencida" else 1 if item["estado"] == "Proxima" else 2,
            item.get("fecha") or "",
            item.get("empresa") or "",
        )
    )
    return alertas


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


def eliminar_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM diagnosticos WHERE empresa_id = ?", (empresa_id,))
    diagnostico_ids = [row[0] for row in c.fetchall()]
    c.execute("SELECT id FROM matrices_riesgos WHERE empresa_id = ?", (empresa_id,))
    matriz_ids = [row[0] for row in c.fetchall()]
    c.execute("SELECT id FROM calidad_problemas_8d WHERE empresa_id = ?", (empresa_id,))
    problema_ids = [row[0] for row in c.fetchall()]
    for diagnostico_id in diagnostico_ids:
        c.execute("DELETE FROM respuestas WHERE diagnostico_id = ?", (diagnostico_id,))
    for matriz_id in matriz_ids:
        c.execute("DELETE FROM items_riesgos WHERE matriz_id = ?", (matriz_id,))
    for problema_id in problema_ids:
        c.execute("DELETE FROM calidad_5_porque WHERE problema_id = ?", (problema_id,))
        c.execute("DELETE FROM calidad_ishikawa WHERE problema_id = ?", (problema_id,))
        c.execute("DELETE FROM calidad_8d_acciones WHERE problema_id = ?", (problema_id,))
    c.execute("DELETE FROM diagnosticos WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM mapa_procesos WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM kpis WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM simulacros_ambientales WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM matriz_legal_ambiental WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM aspectos_ambientales WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM empresa_fuentes WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM calidad_problemas_8d WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM matrices_riesgos WHERE empresa_id = ?", (empresa_id,))
    c.execute("DELETE FROM empresas WHERE id = ?", (empresa_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=128)
def obtener_mapa_procesos_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            proceso_codigo,
            proceso_nombre,
            dueno_proceso,
            ultima_revision,
            entradas,
            salidas,
            documentos,
            indicadores,
            recursos,
            orden
        FROM mapa_procesos
        WHERE empresa_id = ?
        ORDER BY orden, proceso_nombre
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "proceso_codigo",
        "proceso_nombre",
        "dueno_proceso",
        "ultima_revision",
        "entradas",
        "salidas",
        "documentos",
        "indicadores",
        "recursos",
        "orden",
    ]
    return [dict(zip(keys, row)) for row in rows]


def agregar_proceso_mapa_empresa(empresa_id, proceso_codigo, proceso_nombre):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id
        FROM mapa_procesos
        WHERE empresa_id = ? AND proceso_codigo = ?
        """,
        (empresa_id, proceso_codigo),
    )
    if c.fetchone():
        conn.close()
        return False, "Ese proceso ya existe en el mapa de la empresa."

    c.execute(
        """
        SELECT COALESCE(MAX(orden), 0) + 1
        FROM mapa_procesos
        WHERE empresa_id = ?
        """,
        (empresa_id,),
    )
    next_order = c.fetchone()[0] or 1
    c.execute(
        """
        INSERT INTO mapa_procesos (
            empresa_id,
            proceso_codigo,
            proceso_nombre,
            dueno_proceso,
            ultima_revision,
            entradas,
            salidas,
            documentos,
            indicadores,
            recursos,
            orden
        ) VALUES (?, ?, ?, '', '', '', '', '', '', '', ?)
        """,
        (empresa_id, proceso_codigo, proceso_nombre, next_order),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Proceso agregado al mapa correctamente."


def actualizar_proceso_mapa(
    proceso_id,
    dueno_proceso,
    entradas,
    salidas,
    documentos,
    indicadores,
    recursos,
):
    ultima_revision = datetime.datetime.now().strftime("%d.%m.%Y")
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE mapa_procesos
        SET
            dueno_proceso = ?,
            ultima_revision = ?,
            entradas = ?,
            salidas = ?,
            documentos = ?,
            indicadores = ?,
            recursos = ?
        WHERE id = ?
        """,
        (
            str(dueno_proceso).strip(),
            str(ultima_revision).strip(),
            str(entradas).strip(),
            str(salidas).strip(),
            str(documentos).strip(),
            str(indicadores).strip(),
            str(recursos).strip(),
            proceso_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()


def eliminar_proceso_mapa(proceso_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM mapa_procesos WHERE id = ?", (proceso_id,))
    conn.commit()
    conn.close()
    _clear_caches()


KPI_MONTH_FIELDS = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")


def _to_optional_float(value):
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _to_int_bool(value) -> int:
    if isinstance(value, str):
        return 1 if value.strip().lower() in {"1", "true", "si", "sí", "yes", "y"} else 0
    return 1 if bool(value) else 0


@lru_cache(maxsize=128)
def obtener_kpis_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            proceso_id,
            proceso_nombre,
            codigo,
            nombre,
            objetivo,
            categoria,
            formula,
            meta,
            frecuencia,
            responsable,
            fuente,
            unidad,
            tipo_grafico,
            usa_ytd,
            tipo_ytd,
            mostrar_en_dashboard,
            dashboard_principal,
            grupos_personalizados,
            ytd_manual_val,
            comentarios_desvio,
            ene,
            feb,
            mar,
            abr,
            may,
            jun,
            jul,
            ago,
            sep,
            oct,
            nov,
            dic,
            diario_json,
            mensual_manual_val,
            anual_manual_val,
            objetivo_sentido,
            valor_actual,
            tendencia,
            observaciones,
            fecha_actualizacion,
            orden
        FROM (
            SELECT
                k.id,
                k.empresa_id,
                k.proceso_id,
                p.proceso_nombre,
                k.codigo,
                k.nombre,
                k.objetivo,
                k.categoria,
                k.formula,
                k.meta,
                k.frecuencia,
                k.responsable,
                k.fuente,
                k.unidad,
                k.tipo_grafico,
                COALESCE(k.usa_ytd, 0) AS usa_ytd,
                k.tipo_ytd,
                COALESCE(k.mostrar_en_dashboard, 1) AS mostrar_en_dashboard,
                COALESCE(k.dashboard_principal, 0) AS dashboard_principal,
                COALESCE(k.grupos_personalizados, '') AS grupos_personalizados,
                k.ytd_manual_val,
                k.comentarios_desvio,
                k.ene,
                k.feb,
                k.mar,
                k.abr,
                k.may,
                k.jun,
                k.jul,
                k.ago,
                k.sep,
                k.oct,
                k.nov,
                k.dic,
                k.diario_json,
                k.mensual_manual_val,
                k.anual_manual_val,
                COALESCE(k.objetivo_sentido, 'mayor_mejor') AS objetivo_sentido,
                k.valor_actual,
                k.tendencia,
                k.observaciones,
                k.fecha_actualizacion,
                k.orden
            FROM kpis k
            LEFT JOIN mapa_procesos p ON p.id = k.proceso_id
            WHERE k.empresa_id = ?
        )
        ORDER BY orden, nombre
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "proceso_id",
        "proceso_nombre",
        "codigo",
        "nombre",
        "objetivo",
        "categoria",
        "formula",
        "meta",
        "frecuencia",
        "responsable",
        "fuente",
        "unidad",
        "tipo_grafico",
        "usa_ytd",
        "tipo_ytd",
        "mostrar_en_dashboard",
        "dashboard_principal",
        "grupos_personalizados",
        "ytd_manual_val",
        "comentarios_desvio",
        *KPI_MONTH_FIELDS,
        "diario_json",
        "mensual_manual_val",
        "anual_manual_val",
        "objetivo_sentido",
        "valor_actual",
        "tendencia",
        "observaciones",
        "fecha_actualizacion",
        "orden",
    ]
    return [dict(zip(keys, row)) for row in rows]


@lru_cache(maxsize=256)
def obtener_kpi_detalle(kpi_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            k.id,
            k.empresa_id,
            k.proceso_id,
            p.proceso_nombre,
            k.codigo,
            k.nombre,
            k.objetivo,
            k.categoria,
            k.formula,
            k.meta,
            k.frecuencia,
            k.responsable,
            k.fuente,
            k.unidad,
            k.tipo_grafico,
            COALESCE(k.usa_ytd, 0) AS usa_ytd,
            k.tipo_ytd,
            COALESCE(k.mostrar_en_dashboard, 1) AS mostrar_en_dashboard,
            COALESCE(k.dashboard_principal, 0) AS dashboard_principal,
            COALESCE(k.grupos_personalizados, '') AS grupos_personalizados,
            k.ytd_manual_val,
            k.comentarios_desvio,
            k.ene,
            k.feb,
            k.mar,
            k.abr,
            k.may,
            k.jun,
            k.jul,
            k.ago,
            k.sep,
            k.oct,
            k.nov,
            k.dic,
            k.diario_json,
            k.mensual_manual_val,
            k.anual_manual_val,
            COALESCE(k.objetivo_sentido, 'mayor_mejor') AS objetivo_sentido,
            k.valor_actual,
            k.tendencia,
            k.observaciones,
            k.fecha_actualizacion,
            k.orden
        FROM kpis k
        LEFT JOIN mapa_procesos p ON p.id = k.proceso_id
        WHERE k.id = ?
        """,
        (kpi_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "empresa_id",
        "proceso_id",
        "proceso_nombre",
        "codigo",
        "nombre",
        "objetivo",
        "categoria",
        "formula",
        "meta",
        "frecuencia",
        "responsable",
        "fuente",
        "unidad",
        "tipo_grafico",
        "usa_ytd",
        "tipo_ytd",
        "mostrar_en_dashboard",
        "dashboard_principal",
        "grupos_personalizados",
        "ytd_manual_val",
        "comentarios_desvio",
        *KPI_MONTH_FIELDS,
        "diario_json",
        "mensual_manual_val",
        "anual_manual_val",
        "objetivo_sentido",
        "valor_actual",
        "tendencia",
        "observaciones",
        "fecha_actualizacion",
        "orden",
    ]
    return dict(zip(keys, row))


def guardar_kpi(
    empresa_id,
    proceso_id,
    nombre,
    objetivo,
    unidad,
    tipo_grafico,
    usa_ytd,
    tipo_ytd,
    mostrar_en_dashboard=1,
    responsable="",
    frecuencia="",
    objetivo_sentido="mayor_mejor",
    dashboard_principal=0,
    grupos_personalizados="",
):
    nombre_limpio = str(nombre or "").strip()
    if not nombre_limpio:
        return False, "El nombre del KPI no puede estar vacio.", None

    proceso_id_clean = int(proceso_id) if proceso_id not in (None, "", 0, "0") else None
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id
        FROM kpis
        WHERE empresa_id = ?
          AND LOWER(nombre) = LOWER(?)
          AND COALESCE(proceso_id, 0) = COALESCE(?, 0)
        """,
        (int(empresa_id), nombre_limpio, proceso_id_clean),
    )
    if c.fetchone():
        conn.close()
        return False, "Ese KPI ya existe para el proceso seleccionado.", None

    c.execute(
        """
        SELECT COALESCE(MAX(orden), 0) + 1
        FROM kpis
        WHERE empresa_id = ?
        """,
        (int(empresa_id),),
    )
    next_order = c.fetchone()[0] or 1
    fecha_actualizacion = _kpi_now_str()
    objetivo_val = _to_optional_float(objetivo)
    usa_ytd_val = _to_int_bool(usa_ytd)
    mostrar_dashboard_val = _to_int_bool(mostrar_en_dashboard)
    dashboard_principal_val = _to_int_bool(dashboard_principal)
    grupos_payload = grupos_personalizados
    if isinstance(grupos_personalizados, (list, tuple, dict)):
        grupos_payload = json.dumps(grupos_personalizados, ensure_ascii=False)

    c.execute(
        """
        INSERT INTO kpis (
            empresa_id,
            proceso_id,
            nombre,
            objetivo,
            unidad,
            frecuencia,
            responsable,
            tipo_grafico,
            usa_ytd,
            tipo_ytd,
            objetivo_sentido,
            mostrar_en_dashboard,
            dashboard_principal,
            grupos_personalizados,
            meta,
            fecha_actualizacion,
            orden
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(empresa_id),
            proceso_id_clean,
            nombre_limpio,
            objetivo_val,
            str(unidad or "").strip(),
            str(frecuencia or "").strip(),
            str(responsable or "").strip(),
            str(tipo_grafico or "").strip(),
            usa_ytd_val,
            str(tipo_ytd or "").strip(),
            str(objetivo_sentido or "mayor_mejor").strip(),
            mostrar_dashboard_val,
            dashboard_principal_val,
            str(grupos_payload or "").strip(),
            "" if objetivo_val is None else str(objetivo_val),
            fecha_actualizacion,
            next_order,
        ),
    )
    kpi_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "KPI guardado correctamente.", kpi_id


def actualizar_kpi_meses(kpi_id, meses_dict, ytd_manual_val=None, comentarios_desvio=""):
    meses_dict = meses_dict or {}
    month_values = [_to_optional_float(meses_dict.get(month)) for month in KPI_MONTH_FIELDS]
    fecha_actualizacion = _kpi_now_str()

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM kpis WHERE id = ?", (int(kpi_id),))
    if not c.fetchone():
        conn.close()
        return False, "Ese KPI no existe."

    c.execute(
        """
        UPDATE kpis
        SET
            ene = ?,
            feb = ?,
            mar = ?,
            abr = ?,
            may = ?,
            jun = ?,
            jul = ?,
            ago = ?,
            sep = ?,
            oct = ?,
            nov = ?,
            dic = ?,
            ytd_manual_val = ?,
            comentarios_desvio = ?,
            fecha_actualizacion = ?
        WHERE id = ?
        """,
        (
            *month_values,
            _to_optional_float(ytd_manual_val),
            str(comentarios_desvio or "").strip(),
            fecha_actualizacion,
            int(kpi_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Valores del KPI actualizados correctamente."


def actualizar_kpi_diario_y_periodos(kpi_id, diario_json="", mensual_manual_val=None, anual_manual_val=None):
    fecha_actualizacion = _kpi_now_str()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM kpis WHERE id = ?", (int(kpi_id),))
    if not c.fetchone():
        conn.close()
        return False, "Ese KPI no existe."

    c.execute(
        """
        UPDATE kpis
        SET
            diario_json = ?,
            mensual_manual_val = ?,
            anual_manual_val = ?,
            fecha_actualizacion = ?
        WHERE id = ?
        """,
        (
            str(diario_json or "").strip(),
            _to_optional_float(mensual_manual_val),
            _to_optional_float(anual_manual_val),
            fecha_actualizacion,
            int(kpi_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Carga diaria y periodos manuales guardados correctamente."


@lru_cache(maxsize=128)
def obtener_grupos_kpi_empresa(empresa_id):
    _ensure_kpi_groups_table()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT nombre
        FROM kpi_grupos
        WHERE empresa_id = ?
        ORDER BY lower(nombre)
        """,
        (int(empresa_id),),
    )
    rows_table = c.fetchall()
    c.execute(
        """
        SELECT COALESCE(grupos_personalizados, '')
        FROM kpis
        WHERE empresa_id = ?
        """,
        (int(empresa_id),),
    )
    rows = c.fetchall()
    conn.close()

    grupos = {str(row[0]).strip() for row in rows_table if str(row[0]).strip()}
    for (raw,) in rows:
        text = str(raw or "").strip()
        if not text:
            continue
        try:
            parsed = json.loads(text)
        except Exception:
            continue
        if isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    nombre = str(item.get("grupo") or "").strip()
                    if nombre:
                        grupos.add(nombre)

    return sorted(grupos, key=lambda value: value.lower())


def crear_grupo_kpi_empresa(empresa_id, nombre_grupo):
    _ensure_kpi_groups_table()
    nombre = str(nombre_grupo or "").strip()
    if not nombre:
        return False, "Ingresa un nombre de grupo."
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id
        FROM kpi_grupos
        WHERE empresa_id = ?
          AND lower(trim(nombre)) = lower(trim(?))
        """,
        (int(empresa_id), nombre),
    )
    if c.fetchone():
        conn.close()
        return False, "Ese grupo ya existe."
    c.execute(
        """
        INSERT INTO kpi_grupos (empresa_id, nombre)
        VALUES (?, ?)
        """,
        (int(empresa_id), nombre),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Grupo creado correctamente."


def actualizar_dashboard_principal_kpi(kpi_id, dashboard_principal):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM kpis WHERE id = ?", (int(kpi_id),))
    if not c.fetchone():
        conn.close()
        return False, "Ese KPI no existe."

    c.execute(
        """
        UPDATE kpis
        SET dashboard_principal = ?, fecha_actualizacion = ?
        WHERE id = ?
        """,
        (
            _to_int_bool(dashboard_principal),
            _kpi_now_str(),
            int(kpi_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Dashboard principal actualizado correctamente."


def actualizar_grupos_personalizados_kpi(kpi_id, grupos_personalizados):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM kpis WHERE id = ?", (int(kpi_id),))
    if not c.fetchone():
        conn.close()
        return False, "Ese KPI no existe."

    payload = grupos_personalizados
    if isinstance(grupos_personalizados, (list, tuple, dict)):
        payload = json.dumps(grupos_personalizados, ensure_ascii=False)

    c.execute(
        """
        UPDATE kpis
        SET grupos_personalizados = ?, fecha_actualizacion = ?
        WHERE id = ?
        """,
        (
            str(payload or "").strip(),
            _kpi_now_str(),
            int(kpi_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Grupos personalizados actualizados correctamente."


def agregar_kpi_empresa(
    empresa_id,
    nombre,
    codigo="",
    categoria="",
    formula="",
    meta="",
    frecuencia="",
    responsable="",
    fuente="",
    unidad="",
    valor_actual="",
    tendencia="",
    observaciones="",
):
    nombre_limpio = str(nombre).strip()
    codigo_limpio = str(codigo).strip()
    if not nombre_limpio:
        return False, "El nombre del KPI no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id
        FROM kpis
        WHERE empresa_id = ?
          AND (
              LOWER(nombre) = LOWER(?)
              OR (? != '' AND LOWER(codigo) = LOWER(?))
          )
        """,
        (empresa_id, nombre_limpio, codigo_limpio, codigo_limpio),
    )
    if c.fetchone():
        conn.close()
        return False, "Ese KPI ya existe para la empresa seleccionada."

    c.execute(
        """
        SELECT COALESCE(MAX(orden), 0) + 1
        FROM kpis
        WHERE empresa_id = ?
        """,
        (empresa_id,),
    )
    next_order = c.fetchone()[0] or 1
    fecha_actualizacion = _kpi_now_str()

    c.execute(
        """
        INSERT INTO kpis (
            empresa_id,
            codigo,
            nombre,
            categoria,
            formula,
            meta,
            frecuencia,
            responsable,
            fuente,
            unidad,
            valor_actual,
            tendencia,
            observaciones,
            fecha_actualizacion,
            orden
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            codigo_limpio,
            nombre_limpio,
            str(categoria).strip(),
            str(formula).strip(),
            str(meta).strip(),
            str(frecuencia).strip(),
            str(responsable).strip(),
            str(fuente).strip(),
            str(unidad).strip(),
            str(valor_actual).strip(),
            str(tendencia).strip(),
            str(observaciones).strip(),
            fecha_actualizacion,
            next_order,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "KPI agregado correctamente."


def actualizar_kpi(
    kpi_id,
    codigo="",
    nombre="",
    categoria="",
    formula="",
    meta="",
    frecuencia="",
    responsable="",
    fuente="",
    unidad="",
    valor_actual="",
    tendencia="",
    observaciones="",
    objetivo=None,
    mostrar_en_dashboard=1,
    proceso_id=None,
    tipo_grafico=None,
    usa_ytd=None,
    tipo_ytd=None,
    objetivo_sentido=None,
):
    nombre_limpio = str(nombre).strip()
    if not nombre_limpio:
        return False, "El nombre del KPI no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT empresa_id FROM kpis WHERE id = ?", (kpi_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "Ese KPI no existe."

    empresa_id = row[0]
    codigo_limpio = str(codigo).strip()
    c.execute(
        """
        SELECT id
        FROM kpis
        WHERE empresa_id = ?
          AND id != ?
          AND (
              LOWER(nombre) = LOWER(?)
              OR (? != '' AND LOWER(codigo) = LOWER(?))
          )
        """,
        (empresa_id, kpi_id, nombre_limpio, codigo_limpio, codigo_limpio),
    )
    if c.fetchone():
        conn.close()
        return False, "Ya existe otro KPI con ese nombre o codigo en esta empresa."

    fecha_actualizacion = _kpi_now_str()
    proceso_id_clean = int(proceso_id) if proceso_id not in (None, "", 0, "0") else None
    c.execute(
        """
        UPDATE kpis
        SET
            proceso_id = COALESCE(?, proceso_id),
            codigo = ?,
            nombre = ?,
            objetivo = ?,
            categoria = ?,
            formula = ?,
            meta = ?,
            frecuencia = ?,
            responsable = ?,
            fuente = ?,
            unidad = ?,
            tipo_grafico = COALESCE(?, tipo_grafico),
            usa_ytd = COALESCE(?, usa_ytd),
            tipo_ytd = COALESCE(?, tipo_ytd),
            objetivo_sentido = COALESCE(?, objetivo_sentido),
            mostrar_en_dashboard = ?,
            valor_actual = ?,
            tendencia = ?,
            observaciones = ?,
            fecha_actualizacion = ?
        WHERE id = ?
        """,
        (
            proceso_id_clean,
            codigo_limpio,
            nombre_limpio,
            _to_optional_float(objetivo if objetivo is not None else meta),
            str(categoria).strip(),
            str(formula).strip(),
            str(meta).strip(),
            str(frecuencia).strip(),
            str(responsable).strip(),
            str(fuente).strip(),
            str(unidad).strip(),
            str(tipo_grafico).strip() if tipo_grafico is not None else None,
            _to_int_bool(usa_ytd) if usa_ytd is not None else None,
            str(tipo_ytd).strip() if tipo_ytd is not None else None,
            str(objetivo_sentido).strip() if objetivo_sentido is not None else None,
            _to_int_bool(mostrar_en_dashboard),
            str(valor_actual).strip(),
            str(tendencia).strip(),
            str(observaciones).strip(),
            fecha_actualizacion,
            kpi_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "KPI actualizado correctamente."


def eliminar_kpi(kpi_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM kpis WHERE id = ?", (kpi_id,))
    conn.commit()
    conn.close()
    _clear_caches()


def _normalize_risk_scale(value) -> int:
    try:
        numeric = int(value)
    except Exception:
        numeric = 1
    return numeric if numeric in (1, 3, 6) else 1


def _risk_metrics(ocurrencia, severidad) -> tuple[int, int, bool]:
    ocurrencia_norm = _normalize_risk_scale(ocurrencia)
    severidad_norm = _normalize_risk_scale(severidad)
    npr = ocurrencia_norm * severidad_norm
    accion_obligatoria = severidad_norm == 6 or npr > 9
    return ocurrencia_norm, severidad_norm, accion_obligatoria


@lru_cache(maxsize=128)
def obtener_matrices_riesgos_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, empresa_id, proceso_nombre, fecha_actualizacion
        FROM matrices_riesgos
        WHERE empresa_id = ?
        ORDER BY proceso_nombre
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "empresa_id", "proceso_nombre", "fecha_actualizacion"]
    return [dict(zip(keys, row)) for row in rows]


@lru_cache(maxsize=256)
def obtener_matriz_riesgos_detalle(matriz_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, empresa_id, proceso_nombre, fecha_actualizacion
        FROM matrices_riesgos
        WHERE id = ?
        """,
        (matriz_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id", "empresa_id", "proceso_nombre", "fecha_actualizacion"]
    return dict(zip(keys, row))


@lru_cache(maxsize=256)
def obtener_items_riesgos_matriz(matriz_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            matriz_id,
            tipo,
            descripcion,
            ocurrencia,
            severidad,
            npr,
            accion_obligatoria,
            acciones_tomadas,
            fecha_accion,
            responsable,
            eficaz
        FROM items_riesgos
        WHERE matriz_id = ?
        ORDER BY id DESC
        """,
        (matriz_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "matriz_id",
        "tipo",
        "descripcion",
        "ocurrencia",
        "severidad",
        "npr",
        "accion_obligatoria",
        "acciones_tomadas",
        "fecha_accion",
        "responsable",
        "eficaz",
    ]
    return [dict(zip(keys, row)) for row in rows]


def crear_matriz_riesgos(empresa_id, proceso_nombre):
    proceso = str(proceso_nombre).strip()
    if not proceso:
        return False, "El nombre del proceso no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id
        FROM matrices_riesgos
        WHERE empresa_id = ? AND LOWER(proceso_nombre) = LOWER(?)
        """,
        (empresa_id, proceso),
    )
    if c.fetchone():
        conn.close()
        return False, "Ya existe una matriz para ese proceso."

    fecha_actualizacion = datetime.datetime.now().strftime("%d.%m.%Y")
    c.execute(
        """
        INSERT INTO matrices_riesgos (empresa_id, proceso_nombre, fecha_actualizacion)
        VALUES (?, ?, ?)
        """,
        (empresa_id, proceso, fecha_actualizacion),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Matriz creada correctamente."


def actualizar_matriz_riesgos(matriz_id, proceso_nombre):
    proceso = str(proceso_nombre).strip()
    if not proceso:
        return False, "El nombre del proceso no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT empresa_id FROM matrices_riesgos WHERE id = ?", (matriz_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "La matriz ya no existe."

    empresa_id = row[0]
    c.execute(
        """
        SELECT id
        FROM matrices_riesgos
        WHERE empresa_id = ? AND id != ? AND LOWER(proceso_nombre) = LOWER(?)
        """,
        (empresa_id, matriz_id, proceso),
    )
    if c.fetchone():
        conn.close()
        return False, "Ya existe otra matriz para ese proceso."

    fecha_actualizacion = datetime.datetime.now().strftime("%d.%m.%Y")
    c.execute(
        """
        UPDATE matrices_riesgos
        SET proceso_nombre = ?, fecha_actualizacion = ?
        WHERE id = ?
        """,
        (proceso, fecha_actualizacion, matriz_id),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Matriz actualizada correctamente."


def eliminar_matriz_riesgos(matriz_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM items_riesgos WHERE matriz_id = ?", (matriz_id,))
    c.execute("DELETE FROM matrices_riesgos WHERE id = ?", (matriz_id,))
    conn.commit()
    conn.close()
    _clear_caches()


def crear_item_riesgo(
    matriz_id,
    tipo,
    descripcion,
    ocurrencia,
    severidad,
    acciones_tomadas="",
    fecha_accion="",
    responsable="",
    eficaz=False,
):
    descripcion_limpia = str(descripcion).strip()
    if not descripcion_limpia:
        return False, "La descripcion no puede estar vacia."

    ocurrencia_norm, severidad_norm, accion_obligatoria = _risk_metrics(ocurrencia, severidad)
    npr = ocurrencia_norm * severidad_norm
    eficaz_value = 1 if bool(eficaz) else 0

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO items_riesgos (
            matriz_id,
            tipo,
            descripcion,
            ocurrencia,
            severidad,
            npr,
            accion_obligatoria,
            acciones_tomadas,
            fecha_accion,
            responsable,
            eficaz
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            matriz_id,
            str(tipo).strip() or "Riesgo",
            descripcion_limpia,
            ocurrencia_norm,
            severidad_norm,
            npr,
            1 if accion_obligatoria else 0,
            str(acciones_tomadas).strip(),
            str(fecha_accion).strip(),
            str(responsable).strip(),
            eficaz_value,
        ),
    )
    c.execute(
        """
        UPDATE matrices_riesgos
        SET fecha_actualizacion = ?
        WHERE id = ?
        """,
        (datetime.datetime.now().strftime("%d.%m.%Y"), matriz_id),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Item guardado correctamente."


def actualizar_item_riesgo(
    item_id,
    tipo,
    descripcion,
    ocurrencia,
    severidad,
    acciones_tomadas="",
    fecha_accion="",
    responsable="",
    eficaz=False,
):
    descripcion_limpia = str(descripcion).strip()
    if not descripcion_limpia:
        return False, "La descripcion no puede estar vacia."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT matriz_id FROM items_riesgos WHERE id = ?", (item_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "El item ya no existe."

    matriz_id = row[0]
    ocurrencia_norm, severidad_norm, accion_obligatoria = _risk_metrics(ocurrencia, severidad)
    npr = ocurrencia_norm * severidad_norm
    eficaz_value = 1 if bool(eficaz) else 0
    c.execute(
        """
        UPDATE items_riesgos
        SET
            tipo = ?,
            descripcion = ?,
            ocurrencia = ?,
            severidad = ?,
            npr = ?,
            accion_obligatoria = ?,
            acciones_tomadas = ?,
            fecha_accion = ?,
            responsable = ?,
            eficaz = ?
        WHERE id = ?
        """,
        (
            str(tipo).strip() or "Riesgo",
            descripcion_limpia,
            ocurrencia_norm,
            severidad_norm,
            npr,
            1 if accion_obligatoria else 0,
            str(acciones_tomadas).strip(),
            str(fecha_accion).strip(),
            str(responsable).strip(),
            eficaz_value,
            item_id,
        ),
    )
    c.execute(
        """
        UPDATE matrices_riesgos
        SET fecha_actualizacion = ?
        WHERE id = ?
        """,
        (datetime.datetime.now().strftime("%d.%m.%Y"), matriz_id),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Item actualizado correctamente."


def eliminar_item_riesgo(item_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT matriz_id FROM items_riesgos WHERE id = ?", (item_id,))
    row = c.fetchone()
    matriz_id = row[0] if row else None
    c.execute("DELETE FROM items_riesgos WHERE id = ?", (item_id,))
    if matriz_id:
        c.execute(
            """
            UPDATE matrices_riesgos
            SET fecha_actualizacion = ?
            WHERE id = ?
            """,
            (datetime.datetime.now().strftime("%d.%m.%Y"), matriz_id),
        )
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=128)
def obtener_aspectos_ambientales_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            proceso_nombre,
            actividad,
            aspecto,
            impacto,
            condicion,
            significancia,
            es_significativo,
            control_operacional
        FROM aspectos_ambientales
        WHERE empresa_id = ?
        ORDER BY proceso_nombre, actividad, aspecto
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "proceso_nombre",
        "actividad",
        "aspecto",
        "impacto",
        "condicion",
        "significancia",
        "es_significativo",
        "control_operacional",
    ]
    return [dict(zip(keys, row)) for row in rows]


@lru_cache(maxsize=256)
def obtener_aspecto_ambiental_detalle(aspecto_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            proceso_nombre,
            actividad,
            aspecto,
            impacto,
            condicion,
            significancia,
            es_significativo,
            control_operacional
        FROM aspectos_ambientales
        WHERE id = ?
        """,
        (aspecto_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "empresa_id",
        "proceso_nombre",
        "actividad",
        "aspecto",
        "impacto",
        "condicion",
        "significancia",
        "es_significativo",
        "control_operacional",
    ]
    return dict(zip(keys, row))


def crear_aspecto_ambiental(
    empresa_id,
    proceso_nombre,
    actividad,
    aspecto,
    impacto,
    condicion,
    significancia,
    control_operacional="",
):
    proceso = str(proceso_nombre).strip()
    actividad_limpia = str(actividad).strip()
    aspecto_limpio = str(aspecto).strip()
    if not proceso or not actividad_limpia or not aspecto_limpio:
        return False, "Proceso, actividad y aspecto son obligatorios."

    significancia_val = 1 if int(significancia or 0) else 0
    es_significativo = 1 if significancia_val else 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO aspectos_ambientales (
            empresa_id,
            proceso_nombre,
            actividad,
            aspecto,
            impacto,
            condicion,
            significancia,
            es_significativo,
            control_operacional
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            proceso,
            actividad_limpia,
            aspecto_limpio,
            str(impacto).strip(),
            str(condicion).strip(),
            significancia_val,
            es_significativo,
            str(control_operacional).strip(),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Aspecto ambiental guardado correctamente."


def actualizar_aspecto_ambiental(
    aspecto_id,
    proceso_nombre,
    actividad,
    aspecto,
    impacto,
    condicion,
    significancia,
    control_operacional="",
):
    proceso = str(proceso_nombre).strip()
    actividad_limpia = str(actividad).strip()
    aspecto_limpio = str(aspecto).strip()
    if not proceso or not actividad_limpia or not aspecto_limpio:
        return False, "Proceso, actividad y aspecto son obligatorios."

    significancia_val = 1 if int(significancia or 0) else 0
    es_significativo = 1 if significancia_val else 0
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE aspectos_ambientales
        SET
            proceso_nombre = ?,
            actividad = ?,
            aspecto = ?,
            impacto = ?,
            condicion = ?,
            significancia = ?,
            es_significativo = ?,
            control_operacional = ?
        WHERE id = ?
        """,
        (
            proceso,
            actividad_limpia,
            aspecto_limpio,
            str(impacto).strip(),
            str(condicion).strip(),
            significancia_val,
            es_significativo,
            str(control_operacional).strip(),
            aspecto_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Aspecto ambiental actualizado correctamente."


def eliminar_aspecto_ambiental(aspecto_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM aspectos_ambientales WHERE id = ?", (aspecto_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=128)
def obtener_requisitos_legales_ambientales_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            jurisdiccion,
            norma_legal,
            articulo_aplicable,
            estado_cumplimiento,
            fecha_vencimiento,
            responsable
        FROM matriz_legal_ambiental
        WHERE empresa_id = ?
        ORDER BY fecha_vencimiento, norma_legal
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "jurisdiccion",
        "norma_legal",
        "articulo_aplicable",
        "estado_cumplimiento",
        "fecha_vencimiento",
        "responsable",
    ]
    items = [dict(zip(keys, row)) for row in rows]
    deduplicated: list[dict] = []
    for item in items:
        jurisdiccion = str(item.get("jurisdiccion") or "Nacional").strip().title()
        norma = str(item.get("norma_legal") or "").strip()
        duplicated = False
        for existing in deduplicated:
            existing_jurisdiccion = str(existing.get("jurisdiccion") or "Nacional").strip().title()
            existing_norma = str(existing.get("norma_legal") or "").strip()
            if existing_jurisdiccion != jurisdiccion:
                continue
            if _is_almost_duplicate_legal_name(existing_norma, norma):
                duplicated = True
                break
        if not duplicated:
            deduplicated.append(item)
    return deduplicated


@lru_cache(maxsize=256)
def obtener_requisito_legal_ambiental_detalle(requisito_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            jurisdiccion,
            norma_legal,
            articulo_aplicable,
            estado_cumplimiento,
            fecha_vencimiento,
            responsable
        FROM matriz_legal_ambiental
        WHERE id = ?
        """,
        (requisito_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "empresa_id",
        "jurisdiccion",
        "norma_legal",
        "articulo_aplicable",
        "estado_cumplimiento",
        "fecha_vencimiento",
        "responsable",
    ]
    return dict(zip(keys, row))


def crear_requisito_legal_ambiental(
    empresa_id,
    jurisdiccion,
    norma_legal,
    articulo_aplicable,
    estado_cumplimiento,
    fecha_vencimiento="",
    responsable="",
):
    norma = str(norma_legal).strip()
    jurisdiccion_text = str(jurisdiccion or "Nacional").strip().title()
    if not norma:
        return False, "La norma legal no puede estar vacia."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    duplicate = _find_legal_duplicate(c, empresa_id, jurisdiccion_text, norma)
    if duplicate:
        conn.close()
        kind = duplicate[1]
        if kind == "exacto":
            return False, "Ese requisito legal ya existe en la misma jurisdiccion. Si corresponde, editalo como actualizacion."
        return False, "Se detecto una norma muy similar en la misma jurisdiccion. Revisala antes de crear un duplicado."
    c.execute(
        """
        INSERT INTO matriz_legal_ambiental (
            empresa_id,
            jurisdiccion,
            norma_legal,
            articulo_aplicable,
            estado_cumplimiento,
            fecha_vencimiento,
            responsable
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            jurisdiccion_text,
            norma,
            str(articulo_aplicable).strip(),
            str(estado_cumplimiento).strip(),
            str(fecha_vencimiento).strip(),
            str(responsable).strip(),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Requisito legal guardado correctamente."


def actualizar_requisito_legal_ambiental(
    requisito_id,
    jurisdiccion,
    norma_legal,
    articulo_aplicable,
    estado_cumplimiento,
    fecha_vencimiento="",
    responsable="",
):
    norma = str(norma_legal).strip()
    jurisdiccion_text = str(jurisdiccion or "Nacional").strip().title()
    if not norma:
        return False, "La norma legal no puede estar vacia."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT empresa_id FROM matriz_legal_ambiental WHERE id = ?", (requisito_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return False, "No se encontro el requisito legal a actualizar."
    empresa_id = int(row[0])
    duplicate = _find_legal_duplicate(c, empresa_id, jurisdiccion_text, norma, exclude_id=requisito_id)
    if duplicate:
        conn.close()
        kind = duplicate[1]
        if kind == "exacto":
            return False, "Ya existe otro requisito con la misma norma y jurisdiccion para esta empresa."
        return False, "Ya existe otro requisito muy similar en la misma jurisdiccion para esta empresa."
    c.execute(
        """
        UPDATE matriz_legal_ambiental
        SET
            jurisdiccion = ?,
            norma_legal = ?,
            articulo_aplicable = ?,
            estado_cumplimiento = ?,
            fecha_vencimiento = ?,
            responsable = ?
        WHERE id = ?
        """,
        (
            jurisdiccion_text,
            norma,
            str(articulo_aplicable).strip(),
            str(estado_cumplimiento).strip(),
            str(fecha_vencimiento).strip(),
            str(responsable).strip(),
            requisito_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Requisito legal actualizado correctamente."


def eliminar_requisito_legal_ambiental(requisito_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM matriz_legal_ambiental WHERE id = ?", (requisito_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=128)
def obtener_simulacros_ambientales_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            escenario,
            fecha_simulacro,
            participantes,
            respuesta_eficaz,
            conclusiones_mejora,
            archivos_path
        FROM simulacros_ambientales
        WHERE empresa_id = ?
        ORDER BY fecha_simulacro DESC, escenario
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "escenario",
        "fecha_simulacro",
        "participantes",
        "respuesta_eficaz",
        "conclusiones_mejora",
        "archivos_path",
    ]
    return [dict(zip(keys, row)) for row in rows]


@lru_cache(maxsize=256)
def obtener_simulacro_ambiental_detalle(simulacro_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            escenario,
            fecha_simulacro,
            participantes,
            respuesta_eficaz,
            conclusiones_mejora,
            archivos_path
        FROM simulacros_ambientales
        WHERE id = ?
        """,
        (simulacro_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "empresa_id",
        "escenario",
        "fecha_simulacro",
        "participantes",
        "respuesta_eficaz",
        "conclusiones_mejora",
        "archivos_path",
    ]
    return dict(zip(keys, row))


def crear_simulacro_ambiental(
    empresa_id,
    escenario,
    fecha_simulacro="",
    participantes="",
    respuesta_eficaz=False,
    conclusiones_mejora="",
    archivos_path="",
):
    escenario_limpio = str(escenario).strip()
    if not escenario_limpio:
        return False, "El escenario no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO simulacros_ambientales (
            empresa_id,
            escenario,
            fecha_simulacro,
            participantes,
            respuesta_eficaz,
            conclusiones_mejora,
            archivos_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            escenario_limpio,
            str(fecha_simulacro).strip(),
            str(participantes).strip(),
            1 if bool(respuesta_eficaz) else 0,
            str(conclusiones_mejora).strip(),
            str(archivos_path).strip(),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Simulacro guardado correctamente."


def actualizar_simulacro_ambiental(
    simulacro_id,
    escenario,
    fecha_simulacro="",
    participantes="",
    respuesta_eficaz=False,
    conclusiones_mejora="",
    archivos_path="",
):
    escenario_limpio = str(escenario).strip()
    if not escenario_limpio:
        return False, "El escenario no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE simulacros_ambientales
        SET
            escenario = ?,
            fecha_simulacro = ?,
            participantes = ?,
            respuesta_eficaz = ?,
            conclusiones_mejora = ?,
            archivos_path = ?
        WHERE id = ?
        """,
        (
            escenario_limpio,
            str(fecha_simulacro).strip(),
            str(participantes).strip(),
            1 if bool(respuesta_eficaz) else 0,
            str(conclusiones_mejora).strip(),
            str(archivos_path).strip(),
            simulacro_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Simulacro actualizado correctamente."


def eliminar_simulacro_ambiental(simulacro_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM simulacros_ambientales WHERE id = ?", (simulacro_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=128)
def obtener_problemas_calidad_empresa(empresa_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            numero_8d,
            fecha,
            titulo,
            origen,
            d1_equipo,
            d2_descripcion,
            d3_contencion,
            d4_causa_raiz,
            d5_accion_correctiva,
            d6_verificacion,
            d7_prevencion,
            d8_cierre,
            customer_project,
            fault_type,
            COALESCE(safety_relevant, 0) AS safety_relevant,
            COALESCE(repetitive_fault, 0) AS repetitive_fault,
            nok_ok_details,
            d3_sorting_details,
            d4_simulation_details,
            d5_training_details,
            d7_docs_update,
            d8_closure_details,
            estado,
            archivos_path
        FROM calidad_problemas_8d
        WHERE empresa_id = ?
        ORDER BY fecha DESC, id DESC
        """,
        (empresa_id,),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "numero_8d",
        "fecha",
        "titulo",
        "origen",
        "d1_equipo",
        "d2_descripcion",
        "d3_contencion",
        "d4_causa_raiz",
        "d5_accion_correctiva",
        "d6_verificacion",
        "d7_prevencion",
        "d8_cierre",
        "customer_project",
        "fault_type",
        "safety_relevant",
        "repetitive_fault",
        "nok_ok_details",
        "d3_sorting_details",
        "d4_simulation_details",
        "d5_training_details",
        "d7_docs_update",
        "d8_closure_details",
        "estado",
        "archivos_path",
    ]
    return [dict(zip(keys, row)) for row in rows]


@lru_cache(maxsize=256)
def obtener_problema_calidad_detalle(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            empresa_id,
            numero_8d,
            fecha,
            titulo,
            origen,
            d1_equipo,
            d2_descripcion,
            d3_contencion,
            d4_causa_raiz,
            d5_accion_correctiva,
            d6_verificacion,
            d7_prevencion,
            d8_cierre,
            customer_project,
            fault_type,
            COALESCE(safety_relevant, 0) AS safety_relevant,
            COALESCE(repetitive_fault, 0) AS repetitive_fault,
            nok_ok_details,
            d3_sorting_details,
            d4_simulation_details,
            d5_training_details,
            d7_docs_update,
            d8_closure_details,
            estado,
            archivos_path
        FROM calidad_problemas_8d
        WHERE id = ?
        """,
        (problema_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "empresa_id",
        "numero_8d",
        "fecha",
        "titulo",
        "origen",
        "d1_equipo",
        "d2_descripcion",
        "d3_contencion",
        "d4_causa_raiz",
        "d5_accion_correctiva",
        "d6_verificacion",
        "d7_prevencion",
        "d8_cierre",
        "customer_project",
        "fault_type",
        "safety_relevant",
        "repetitive_fault",
        "nok_ok_details",
        "d3_sorting_details",
        "d4_simulation_details",
        "d5_training_details",
        "d7_docs_update",
        "d8_closure_details",
        "estado",
        "archivos_path",
    ]
    return dict(zip(keys, row))


def crear_problema_calidad_8d(
    empresa_id,
    fecha,
    titulo,
    numero_8d="",
    origen="",
    d1_equipo="",
    d2_descripcion="",
    d3_contencion="",
    d4_causa_raiz="",
    d5_accion_correctiva="",
    d6_verificacion="",
    d7_prevencion="",
    d8_cierre="",
    customer_project="",
    fault_type="",
    safety_relevant=0,
    repetitive_fault=0,
    nok_ok_details="",
    d3_sorting_details="",
    d4_simulation_details="",
    d5_training_details="",
    d7_docs_update="",
    d8_closure_details="",
    estado="Abierto",
    archivos_path="",
):
    titulo_limpio = str(titulo).strip()
    if not titulo_limpio:
        return False, "El titulo del analisis no puede estar vacio.", None

    fecha_limpia = str(fecha).strip() or datetime.datetime.now().strftime("%d.%m.%Y")
    numero_limpio = str(numero_8d).strip()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if not numero_limpio:
        c.execute("SELECT COUNT(*) FROM calidad_problemas_8d WHERE empresa_id = ?", (empresa_id,))
        siguiente = int(c.fetchone()[0] or 0) + 1
        numero_limpio = f"8D-{int(empresa_id):03d}-{siguiente:04d}"
    c.execute(
        """
        INSERT INTO calidad_problemas_8d (
            empresa_id,
            numero_8d,
            fecha,
            titulo,
            origen,
            d1_equipo,
            d2_descripcion,
            d3_contencion,
            d4_causa_raiz,
            d5_accion_correctiva,
            d6_verificacion,
            d7_prevencion,
            d8_cierre,
            customer_project,
            fault_type,
            safety_relevant,
            repetitive_fault,
            nok_ok_details,
            d3_sorting_details,
            d4_simulation_details,
            d5_training_details,
            d7_docs_update,
            d8_closure_details,
            estado,
            archivos_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            numero_limpio,
            fecha_limpia,
            titulo_limpio,
            str(origen).strip(),
            str(d1_equipo).strip(),
            str(d2_descripcion).strip(),
            str(d3_contencion).strip(),
            str(d4_causa_raiz).strip(),
            str(d5_accion_correctiva).strip(),
            str(d6_verificacion).strip(),
            str(d7_prevencion).strip(),
            str(d8_cierre).strip(),
            str(customer_project).strip(),
            str(fault_type).strip(),
            int(bool(safety_relevant)),
            int(bool(repetitive_fault)),
            str(nok_ok_details).strip(),
            str(d3_sorting_details).strip(),
            str(d4_simulation_details).strip(),
            str(d5_training_details).strip(),
            str(d7_docs_update).strip(),
            str(d8_closure_details).strip(),
            str(estado).strip() or "Abierto",
            str(archivos_path).strip(),
        ),
    )
    problema_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Analisis 8D guardado correctamente.", problema_id


def actualizar_problema_calidad_8d(
    problema_id,
    fecha,
    titulo,
    numero_8d="",
    origen="",
    d1_equipo="",
    d2_descripcion="",
    d3_contencion="",
    d4_causa_raiz="",
    d5_accion_correctiva="",
    d6_verificacion="",
    d7_prevencion="",
    d8_cierre="",
    customer_project="",
    fault_type="",
    safety_relevant=0,
    repetitive_fault=0,
    nok_ok_details="",
    d3_sorting_details="",
    d4_simulation_details="",
    d5_training_details="",
    d7_docs_update="",
    d8_closure_details="",
    estado="Abierto",
    archivos_path="",
):
    titulo_limpio = str(titulo).strip()
    if not titulo_limpio:
        return False, "El titulo del analisis no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE calidad_problemas_8d
        SET
            numero_8d = ?,
            fecha = ?,
            titulo = ?,
            origen = ?,
            d1_equipo = ?,
            d2_descripcion = ?,
            d3_contencion = ?,
            d4_causa_raiz = ?,
            d5_accion_correctiva = ?,
            d6_verificacion = ?,
            d7_prevencion = ?,
            d8_cierre = ?,
            customer_project = ?,
            fault_type = ?,
            safety_relevant = ?,
            repetitive_fault = ?,
            nok_ok_details = ?,
            d3_sorting_details = ?,
            d4_simulation_details = ?,
            d5_training_details = ?,
            d7_docs_update = ?,
            d8_closure_details = ?,
            estado = ?,
            archivos_path = ?
        WHERE id = ?
        """,
        (
            str(numero_8d).strip(),
            str(fecha).strip() or datetime.datetime.now().strftime("%d.%m.%Y"),
            titulo_limpio,
            str(origen).strip(),
            str(d1_equipo).strip(),
            str(d2_descripcion).strip(),
            str(d3_contencion).strip(),
            str(d4_causa_raiz).strip(),
            str(d5_accion_correctiva).strip(),
            str(d6_verificacion).strip(),
            str(d7_prevencion).strip(),
            str(d8_cierre).strip(),
            str(customer_project).strip(),
            str(fault_type).strip(),
            int(bool(safety_relevant)),
            int(bool(repetitive_fault)),
            str(nok_ok_details).strip(),
            str(d3_sorting_details).strip(),
            str(d4_simulation_details).strip(),
            str(d5_training_details).strip(),
            str(d7_docs_update).strip(),
            str(d8_closure_details).strip(),
            str(estado).strip() or "Abierto",
            str(archivos_path).strip(),
            problema_id,
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Analisis 8D actualizado correctamente."


def eliminar_problema_calidad_8d(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM calidad_5_porque WHERE problema_id = ?", (problema_id,))
    c.execute("DELETE FROM calidad_ishikawa WHERE problema_id = ?", (problema_id,))
    c.execute("DELETE FROM calidad_8d_acciones WHERE problema_id = ?", (problema_id,))
    c.execute("DELETE FROM calidad_problemas_8d WHERE id = ?", (problema_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=256)
def obtener_5_porque_problema_calidad(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            problema_id,
            problema_inicial,
            porque_1,
            porque_2,
            porque_3,
            porque_4,
            porque_5,
            causa_raiz_confirmada,
            ocurrencia_1,
            ocurrencia_2,
            ocurrencia_3,
            ocurrencia_4,
            ocurrencia_5,
            causa_ocurrencia,
            no_deteccion_1,
            no_deteccion_2,
            no_deteccion_3,
            no_deteccion_4,
            no_deteccion_5,
            causa_no_deteccion,
            occ_problema,
            occ_p1,
            occ_p2,
            occ_p3,
            occ_p4,
            occ_p5,
            occ_causa_raiz,
            det_problema,
            det_p1,
            det_p2,
            det_p3,
            det_p4,
            det_p5,
            det_causa_raiz
        FROM calidad_5_porque
        WHERE problema_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (problema_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "problema_id",
        "problema_inicial",
        "porque_1",
        "porque_2",
        "porque_3",
        "porque_4",
        "porque_5",
        "causa_raiz_confirmada",
        "ocurrencia_1",
        "ocurrencia_2",
        "ocurrencia_3",
        "ocurrencia_4",
        "ocurrencia_5",
        "causa_ocurrencia",
        "no_deteccion_1",
        "no_deteccion_2",
        "no_deteccion_3",
        "no_deteccion_4",
        "no_deteccion_5",
        "causa_no_deteccion",
        "occ_problema",
        "occ_p1",
        "occ_p2",
        "occ_p3",
        "occ_p4",
        "occ_p5",
        "occ_causa_raiz",
        "det_problema",
        "det_p1",
        "det_p2",
        "det_p3",
        "det_p4",
        "det_p5",
        "det_causa_raiz",
    ]
    return dict(zip(keys, row))


def guardar_5_porque_problema_calidad(
    problema_id,
    problema_inicial="",
    porque_1="",
    porque_2="",
    porque_3="",
    porque_4="",
    porque_5="",
    causa_raiz_confirmada="",
    ocurrencia_1="",
    ocurrencia_2="",
    ocurrencia_3="",
    ocurrencia_4="",
    ocurrencia_5="",
    causa_ocurrencia="",
    no_deteccion_1="",
    no_deteccion_2="",
    no_deteccion_3="",
    no_deteccion_4="",
    no_deteccion_5="",
    causa_no_deteccion="",
    occ_problema="",
    occ_p1="",
    occ_p2="",
    occ_p3="",
    occ_p4="",
    occ_p5="",
    occ_causa_raiz="",
    det_problema="",
    det_p1="",
    det_p2="",
    det_p3="",
    det_p4="",
    det_p5="",
    det_causa_raiz="",
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM calidad_5_porque WHERE problema_id = ? ORDER BY id DESC LIMIT 1", (problema_id,))
    row = c.fetchone()
    values = (
        str(problema_inicial).strip(),
        str(porque_1).strip(),
        str(porque_2).strip(),
        str(porque_3).strip(),
        str(porque_4).strip(),
        str(porque_5).strip(),
        str(causa_raiz_confirmada).strip(),
        str(ocurrencia_1).strip(),
        str(ocurrencia_2).strip(),
        str(ocurrencia_3).strip(),
        str(ocurrencia_4).strip(),
        str(ocurrencia_5).strip(),
        str(causa_ocurrencia).strip(),
        str(no_deteccion_1).strip(),
        str(no_deteccion_2).strip(),
        str(no_deteccion_3).strip(),
        str(no_deteccion_4).strip(),
        str(no_deteccion_5).strip(),
        str(causa_no_deteccion).strip(),
        str(occ_problema).strip(),
        str(occ_p1).strip(),
        str(occ_p2).strip(),
        str(occ_p3).strip(),
        str(occ_p4).strip(),
        str(occ_p5).strip(),
        str(occ_causa_raiz).strip(),
        str(det_problema).strip(),
        str(det_p1).strip(),
        str(det_p2).strip(),
        str(det_p3).strip(),
        str(det_p4).strip(),
        str(det_p5).strip(),
        str(det_causa_raiz).strip(),
    )
    if row:
        c.execute(
            """
            UPDATE calidad_5_porque
            SET
                problema_inicial = ?,
                porque_1 = ?,
                porque_2 = ?,
                porque_3 = ?,
                porque_4 = ?,
                porque_5 = ?,
                causa_raiz_confirmada = ?,
                ocurrencia_1 = ?,
                ocurrencia_2 = ?,
                ocurrencia_3 = ?,
                ocurrencia_4 = ?,
                ocurrencia_5 = ?,
                causa_ocurrencia = ?,
                no_deteccion_1 = ?,
                no_deteccion_2 = ?,
                no_deteccion_3 = ?,
                no_deteccion_4 = ?,
                no_deteccion_5 = ?,
                causa_no_deteccion = ?,
                occ_problema = ?,
                occ_p1 = ?,
                occ_p2 = ?,
                occ_p3 = ?,
                occ_p4 = ?,
                occ_p5 = ?,
                occ_causa_raiz = ?,
                det_problema = ?,
                det_p1 = ?,
                det_p2 = ?,
                det_p3 = ?,
                det_p4 = ?,
                det_p5 = ?,
                det_causa_raiz = ?
            WHERE problema_id = ?
            """,
            (*values, problema_id),
        )
    else:
        c.execute(
            """
            INSERT INTO calidad_5_porque (
                problema_id,
                problema_inicial,
                porque_1,
                porque_2,
                porque_3,
                porque_4,
                porque_5,
                causa_raiz_confirmada,
                ocurrencia_1,
                ocurrencia_2,
                ocurrencia_3,
                ocurrencia_4,
                ocurrencia_5,
                causa_ocurrencia,
                no_deteccion_1,
                no_deteccion_2,
                no_deteccion_3,
                no_deteccion_4,
                no_deteccion_5,
                causa_no_deteccion,
                occ_problema,
                occ_p1,
                occ_p2,
                occ_p3,
                occ_p4,
                occ_p5,
                occ_causa_raiz,
                det_problema,
                det_p1,
                det_p2,
                det_p3,
                det_p4,
                det_p5,
                det_causa_raiz
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (problema_id, *values),
        )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Analisis de 5 porques guardado correctamente."


def eliminar_5_porque_problema_calidad(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM calidad_5_porque WHERE problema_id = ?", (problema_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=256)
def obtener_ishikawa_problema_calidad(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id,
            problema_id,
            efecto,
            mano_obra,
            maquina,
            material,
            metodo,
            medicion,
            medio_ambiente,
            factores_retenidos
        FROM calidad_ishikawa
        WHERE problema_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (problema_id,),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = [
        "id",
        "problema_id",
        "efecto",
        "mano_obra",
        "maquina",
        "material",
        "metodo",
        "medicion",
        "medio_ambiente",
        "factores_retenidos",
    ]
    return dict(zip(keys, row))


def guardar_ishikawa_problema_calidad(
    problema_id,
    efecto="",
    mano_obra="",
    maquina="",
    material="",
    metodo="",
    medicion="",
    medio_ambiente="",
    factores_retenidos="",
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM calidad_ishikawa WHERE problema_id = ? ORDER BY id DESC LIMIT 1", (problema_id,))
    row = c.fetchone()
    values = (
        str(efecto).strip(),
        str(mano_obra).strip(),
        str(maquina).strip(),
        str(material).strip(),
        str(metodo).strip(),
        str(medicion).strip(),
        str(medio_ambiente).strip(),
        str(factores_retenidos).strip(),
    )
    if row:
        c.execute(
            """
            UPDATE calidad_ishikawa
            SET
                efecto = ?,
                mano_obra = ?,
                maquina = ?,
                material = ?,
                metodo = ?,
                medicion = ?,
                medio_ambiente = ?,
                factores_retenidos = ?
            WHERE problema_id = ?
            """,
            (*values, problema_id),
        )
    else:
        c.execute(
            """
            INSERT INTO calidad_ishikawa (
                problema_id,
                efecto,
                mano_obra,
                maquina,
                material,
                metodo,
                medicion,
                medio_ambiente,
                factores_retenidos
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (problema_id, *values),
        )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Diagrama de Ishikawa guardado correctamente."


def eliminar_ishikawa_problema_calidad(problema_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM calidad_ishikawa WHERE problema_id = ?", (problema_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=512)
def obtener_acciones_8d(problema_id, fase_8d=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    query = """
        SELECT
            id,
            problema_id,
            fase_8d,
            accion,
            responsable,
            fecha,
            progreso,
            evidencia_path
        FROM calidad_8d_acciones
        WHERE problema_id = ?
    """
    params = [problema_id]
    if fase_8d:
        query += " AND fase_8d = ?"
        params.append(str(fase_8d).strip())
    query += " ORDER BY fecha, id"
    c.execute(query, tuple(params))
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "problema_id",
        "fase_8d",
        "accion",
        "responsable",
        "fecha",
        "progreso",
        "evidencia_path",
    ]
    return [dict(zip(keys, row)) for row in rows]


def guardar_accion_8d(
    problema_id,
    fase_8d,
    accion,
    responsable="",
    fecha="",
    progreso="0%",
    evidencia_path="",
):
    accion_limpia = str(accion).strip()
    if not accion_limpia:
        return False, "La acción no puede estar vacía.", None

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO calidad_8d_acciones (
            problema_id,
            fase_8d,
            accion,
            responsable,
            fecha,
            progreso,
            evidencia_path
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(problema_id),
            str(fase_8d).strip(),
            accion_limpia,
            str(responsable).strip(),
            str(fecha).strip(),
            str(progreso).strip() or "0%",
            str(evidencia_path).strip(),
        ),
    )
    accion_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Acción guardada correctamente.", accion_id


def eliminar_accion_8d(accion_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM calidad_8d_acciones WHERE id = ?", (accion_id,))
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=64)
def obtener_usuarios(empresa_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is None:
        c.execute(
            """
            SELECT id, username, password, rol, empresa_id, COALESCE(permisos, 'ALL')
            FROM usuarios
            ORDER BY username
            """
        )
    else:
        c.execute(
            """
            SELECT id, username, password, rol, empresa_id, COALESCE(permisos, 'ALL')
            FROM usuarios
            WHERE empresa_id = ?
            ORDER BY username
            """,
            (int(empresa_id),),
        )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "username", "password", "rol", "empresa_id", "permisos"]
    return [dict(zip(keys, row)) for row in rows]


def verificar_usuario(username, password):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, username, rol, empresa_id, COALESCE(permisos, 'ALL')
        FROM usuarios
        WHERE lower(trim(username)) = lower(trim(?))
          AND password = ?
        LIMIT 1
        """,
        (str(username).strip(), str(password).strip()),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    keys = ["id", "username", "rol", "empresa_id", "permisos"]
    return dict(zip(keys, row))


def crear_usuario(username, password, rol, empresa_id=None, permisos="ALL"):
    username_clean = str(username).strip()
    password_clean = str(password).strip()
    rol_clean = str(rol).strip() or "EMPRESA_USER"
    permisos_clean = "ALL" if rol_clean in {"IDEAS_ADMIN", "EMPRESA_ADMIN"} else str(permisos).strip() or ""
    empresa_id_clean = int(empresa_id) if empresa_id not in (None, "", 0, "0") else None
    if rol_clean != "IDEAS_ADMIN" and not empresa_id_clean:
        return False, "Debes asignar una empresa al usuario."
    if not username_clean:
        return False, "El usuario no puede estar vacío."
    if not password_clean:
        return False, "La contraseña no puede estar vacía."
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO usuarios (username, password, rol, empresa_id, permisos)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username_clean, password_clean, rol_clean, empresa_id_clean, permisos_clean or "ALL"),
        )
        conn.commit()
        _clear_caches()
        return True, "Usuario creado correctamente."
    except sqlite3.IntegrityError:
        return False, "Ese usuario ya existe."
    finally:
        conn.close()


def actualizar_usuario(usuario_id, rol, empresa_id=None, permisos="ALL", username=None, password=None):
    rol_clean = str(rol).strip() or "EMPRESA_USER"
    permisos_clean = "ALL" if rol_clean in {"IDEAS_ADMIN", "EMPRESA_ADMIN"} else str(permisos).strip() or ""
    empresa_id_clean = int(empresa_id) if empresa_id not in (None, "", 0, "0") else None
    if rol_clean != "IDEAS_ADMIN" and not empresa_id_clean:
        return False, "Debes asignar una empresa al usuario."
    username_clean = str(username).strip() if username is not None else None
    password_clean = str(password).strip() if password is not None else None
    if username is not None and not username_clean:
        return False, "El usuario no puede estar vacío."
    if password is not None and not password_clean:
        return False, "La contraseña no puede estar vacía."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        fields = ["rol = ?", "empresa_id = ?", "permisos = ?"]
        params = [rol_clean, empresa_id_clean, permisos_clean or "ALL"]
        if username is not None:
            fields.append("username = ?")
            params.append(username_clean)
        if password is not None:
            fields.append("password = ?")
            params.append(password_clean)
        params.append(int(usuario_id))
        c.execute(
            f"""
            UPDATE usuarios
            SET {", ".join(fields)}
            WHERE id = ?
            """,
            tuple(params),
        )
        conn.commit()
        _clear_caches()
        return True, "Usuario actualizado correctamente."
    except sqlite3.IntegrityError:
        return False, "Ese usuario ya existe."
    finally:
        conn.close()


def eliminar_usuario(usuario_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM usuarios WHERE id = ?", (int(usuario_id),))
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Usuario eliminado correctamente."
