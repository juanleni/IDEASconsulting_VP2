from __future__ import annotations

import datetime
import difflib
import hashlib
import json
import os
import re
import secrets
import shutil
import sqlite3
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

DB_PATH = "ideas.db"
EXCEL_PATH = "Data/diagnostico.xlsx"
BACKUP_DIR = "backups"

MODULE_CATALOG = [
    {"code": "documents", "name": "Documentos", "category": "core", "icon": "description", "route": "/sistema-gestion/documentos"},
    {"code": "process_maps", "name": "Mapas de Proceso", "category": "core", "icon": "alt_route", "route": "/sistema-gestion/mapas-proceso"},
    {"code": "kpi", "name": "Indicadores KPI", "category": "core", "icon": "query_stats", "route": "/sistema-gestion/kpis"},
    {"code": "risks", "name": "Riesgos", "category": "core", "icon": "shield", "route": "/sistema-gestion/riesgos"},
    {"code": "environment", "name": "Ambiental", "category": "ehs", "icon": "eco", "route": "/sistema-gestion/ambiental"},
    {"code": "legal_matrix", "name": "Matriz Legal Digital", "category": "ehs", "icon": "gavel", "route": "/sistema-gestion/matriz-legal"},
    {"code": "sst", "name": "Salud Ocupacional", "category": "ehs", "icon": "health_and_safety", "route": "/sistema-gestion/salud-ocupacional"},
    {"code": "quality", "name": "Calidad", "category": "quality", "icon": "plumbing", "route": "/sistema-gestion/calidad"},
    {"code": "lab_17025", "name": "LAB ISO 17025", "category": "lab", "icon": "science", "route": "/sistema-gestion/lab-iso-17025"},
    {"code": "users", "name": "Administración Usuarios", "category": "core", "icon": "manage_accounts", "route": "/sistema-gestion/usuarios"},
    {"code": "smart_ideas_admin", "name": "Smart IdeAs Admin", "category": "admin", "icon": "tune", "route": "/sistema-gestion/smart-ideas-admin"},
]


def _is_password_hash(value: str) -> bool:
    return str(value or "").startswith("pbkdf2_sha256$")


def _hash_password(password: str) -> str:
    raw = str(password or "")
    salt = secrets.token_hex(16)
    rounds = 120_000
    digest = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), rounds).hex()
    return f"pbkdf2_sha256${rounds}${salt}${digest}"


def _verify_password(password: str, stored: str) -> bool:
    raw = str(password or "")
    saved = str(stored or "")
    if not saved:
        return False
    if _is_password_hash(saved):
        try:
            _algo, rounds_txt, salt, digest = saved.split("$", 3)
            rounds = int(rounds_txt)
            calc = hashlib.pbkdf2_hmac("sha256", raw.encode("utf-8"), salt.encode("utf-8"), rounds).hex()
            return secrets.compare_digest(calc, digest)
        except Exception:
            return False
    return secrets.compare_digest(raw, saved)


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
    obtener_memoria_asistente_empresa.cache_clear()
    obtener_alertas_globales.cache_clear()
    obtener_usuarios.cache_clear()
    obtener_lab_configuracion.cache_clear()
    obtener_lab_equipos_empresa.cache_clear()
    obtener_lab_calibraciones_empresa.cache_clear()
    obtener_lab_metodos_empresa.cache_clear()
    obtener_lab_muestras_empresa.cache_clear()
    obtener_lab_competencias_empresa.cache_clear()
    obtener_lab_incertidumbre_empresa.cache_clear()
    obtener_lab_control_calidad_empresa.cache_clear()
    obtener_lab_informes_empresa.cache_clear()
    obtener_lab_auditorias_empresa.cache_clear()
    obtener_lab_riesgos_empresa.cache_clear()
    obtener_lab_acciones_empresa.cache_clear()
    obtener_lab_mobile_unidades_empresa.cache_clear()
    obtener_lab_mobile_registros_empresa.cache_clear()
    obtener_lab_dashboard_empresa.cache_clear()
    obtener_lab_ai_settings.cache_clear()
    obtener_lab_alertas_empresa.cache_clear()
    if "obtener_sst_capacitaciones_empresa" in globals():
        obtener_sst_capacitaciones_empresa.cache_clear()
    if "obtener_ambiental_capacitaciones_empresa" in globals():
        obtener_ambiental_capacitaciones_empresa.cache_clear()
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


def _ensure_module_access_tables() -> None:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            description TEXT DEFAULT '',
            category TEXT DEFAULT 'core',
            icon TEXT DEFAULT '',
            route TEXT DEFAULT '',
            is_active INTEGER DEFAULT 1,
            is_core INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS company_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1,
            enabled_by TEXT DEFAULT '',
            enabled_at TEXT DEFAULT CURRENT_TIMESTAMP,
            disabled_at TEXT,
            notes TEXT DEFAULT '',
            UNIQUE(company_id, module_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS user_modules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company_id INTEGER NOT NULL,
            module_id INTEGER NOT NULL,
            enabled INTEGER DEFAULT 1,
            assigned_by TEXT DEFAULT '',
            assigned_at TEXT DEFAULT CURRENT_TIMESTAMP,
            removed_at TEXT,
            existed_before_disable INTEGER DEFAULT 0,
            UNIQUE(user_id, company_id, module_id)
        )
        """
    )
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS module_access_audit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            user_id INTEGER,
            module_code TEXT NOT NULL,
            action TEXT NOT NULL,
            actor TEXT DEFAULT '',
            source TEXT DEFAULT '',
            details_json TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    c.execute("CREATE INDEX IF NOT EXISTS idx_company_modules_company ON company_modules(company_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_user_modules_company_user ON user_modules(company_id, user_id)")
    c.execute("CREATE INDEX IF NOT EXISTS idx_module_access_audit_company ON module_access_audit(company_id)")

    for item in MODULE_CATALOG:
        code = str(item.get("code") or "").strip()
        if not code:
            continue
        c.execute(
            """
            INSERT INTO modules (code, name, description, category, icon, route, is_active, is_core)
            VALUES (?, ?, ?, ?, ?, ?, 1, ?)
            ON CONFLICT(code) DO UPDATE SET
                name = excluded.name,
                description = excluded.description,
                category = excluded.category,
                icon = excluded.icon,
                route = excluded.route,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                code,
                str(item.get("name") or code),
                str(item.get("description") or ""),
                str(item.get("category") or "core"),
                str(item.get("icon") or ""),
                str(item.get("route") or ""),
                1 if str(item.get("category") or "") == "admin" else 0,
            ),
        )
    conn.commit()
    conn.close()


def _audit_module_access(
    *,
    company_id: int | None,
    user_id: int | None,
    module_code: str,
    action: str,
    actor: str = "",
    source: str = "",
    details: dict | None = None,
) -> None:
    _ensure_module_access_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO module_access_audit (company_id, user_id, module_code, action, actor, source, details_json)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(company_id) if company_id else None,
            int(user_id) if user_id else None,
            str(module_code or "").strip(),
            str(action or "").strip(),
            str(actor or "").strip(),
            str(source or "").strip(),
            json.dumps(details or {}, ensure_ascii=False),
        ),
    )
    conn.commit()
    conn.close()


def _bootstrap_company_modules(company_id: int) -> None:
    _ensure_module_access_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(1) FROM company_modules WHERE company_id = ?", (int(company_id),))
    row = c.fetchone()
    if row and int(row[0] or 0) > 0:
        conn.close()
        return
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    c.execute("SELECT id, code, category FROM modules WHERE is_active = 1")
    for mid, code, category in c.fetchall():
        enabled = 0 if str(category or "") == "admin" or str(code or "") in {"smart_ideas_admin"} else 1
        c.execute(
            """
            INSERT INTO company_modules (company_id, module_id, enabled, enabled_by, enabled_at, disabled_at, notes)
            VALUES (?, ?, ?, 'bootstrap', ?, ?, 'bootstrap inicial')
            ON CONFLICT(company_id, module_id) DO NOTHING
            """,
            (int(company_id), int(mid), int(enabled), now, None if enabled else now),
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

    password_raw = str(empresa_data.get("password") or "").strip()
    password_store = _hash_password(password_raw) if password_raw and not _is_password_hash(password_raw) else password_raw
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
                password_store,
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
        SELECT id, COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social, COALESCE(password, '')
        FROM empresas
        WHERE lower(trim(contacto_correo)) = lower(trim(?))
        LIMIT 1
        """,
        (str(correo).strip(),),
    )
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    empresa_id, razon_social, stored_password = row
    raw_password = str(password).strip()
    if not _verify_password(raw_password, str(stored_password or "")):
        conn.close()
        return None
    if stored_password and not _is_password_hash(str(stored_password)):
        try:
            c.execute(
                "UPDATE empresas SET password = ? WHERE id = ?",
                (_hash_password(raw_password), int(empresa_id)),
            )
            conn.commit()
        except Exception:
            pass
    conn.close()
    return int(empresa_id), str(razon_social or "")


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
        (_hash_password(str(nuevo_password or "").strip()), int(empresa_id)),
    )
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    _clear_caches()
    return ok


def provisionar_acceso_empresa(empresa_id, username, nuevo_password):
    _ensure_empresa_reset_columns()
    empresa_id_int = int(empresa_id)
    username_clean = str(username or "").strip()
    password_clean = str(nuevo_password or "").strip()
    if not username_clean:
        return False, "El usuario no puede estar vacio."
    if not password_clean:
        return False, "La contrasena no puede estar vacia."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            SELECT id
            FROM empresas
            WHERE id = ?
            LIMIT 1
            """,
            (empresa_id_int,),
        )
        empresa_row = c.fetchone()
        if not empresa_row:
            return False, "La empresa no existe."

        c.execute(
            """
            SELECT id, empresa_id
            FROM usuarios
            WHERE lower(trim(username)) = lower(trim(?))
            LIMIT 1
            """,
            (username_clean,),
        )
        existing_user = c.fetchone()
        if existing_user:
            existing_user_id = int(existing_user[0])
            existing_empresa_id = existing_user[1]
            if existing_empresa_id is not None and int(existing_empresa_id) != empresa_id_int:
                return False, "Ese usuario ya esta asignado a otra empresa."
            c.execute(
                """
                UPDATE usuarios
                SET password = ?, rol = ?, empresa_id = ?, permisos = ?
                WHERE id = ?
                """,
                (_hash_password(password_clean), "EMPRESA_ADMIN", empresa_id_int, "ALL", existing_user_id),
            )
        else:
            c.execute(
                """
                INSERT INTO usuarios (username, password, rol, empresa_id, permisos)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username_clean, _hash_password(password_clean), "EMPRESA_ADMIN", empresa_id_int, "ALL"),
            )

        c.execute(
            """
            UPDATE empresas
            SET
                password = ?,
                contacto_correo = CASE
                    WHEN COALESCE(trim(contacto_correo), '') = '' THEN ?
                    ELSE contacto_correo
                END,
                reset_token = NULL,
                token_expiry = NULL
            WHERE id = ?
            """,
            (_hash_password(password_clean), username_clean, empresa_id_int),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.rollback()
        return False, "No se pudo guardar el usuario. Verifica que sea unico."
    finally:
        conn.close()
    _clear_caches()
    return True, "Acceso configurado correctamente."


def actualizar_empresa(empresa_id, empresa_data):
    razon_social = str(empresa_data["razon_social"]).strip()
    if not razon_social:
        return False, "La razón social no puede estar vacía."

    password_raw = str(empresa_data.get("password") or "").strip()
    password_store = _hash_password(password_raw) if password_raw and not _is_password_hash(password_raw) else password_raw
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
                password_store,
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


def guardar_evento_memoria_asistente(
    empresa_id: int,
    role: str,
    content: str,
    module_context: str = "",
    context_snapshot: str = "",
    user_key: str = "",
) -> None:
    empresa = int(empresa_id or 0)
    rol = str(role or "").strip().lower()
    texto = str(content or "").strip()
    if empresa <= 0 or rol not in {"user", "assistant"} or not texto:
        return
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO ai_memoria_empresa (
            empresa_id,
            user_key,
            role,
            content,
            module_context,
            context_snapshot
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            empresa,
            str(user_key or "").strip().lower()[:120],
            rol,
            texto[:8000],
            str(module_context or "").strip()[:180],
            str(context_snapshot or "").strip()[:4000],
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()


@lru_cache(maxsize=256)
def obtener_memoria_asistente_empresa(
    empresa_id: int,
    limite: int = 24,
    user_key: str = "",
    module_context: str = "",
) -> list[dict]:
    empresa = int(empresa_id or 0)
    if empresa <= 0:
        return []
    limit_val = max(1, min(int(limite or 24), 120))
    user = str(user_key or "").strip().lower()
    module = str(module_context or "").strip().lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user and module:
        c.execute(
            """
            SELECT id, empresa_id, user_key, role, content, module_context, context_snapshot, created_at
            FROM ai_memoria_empresa
            WHERE empresa_id = ?
              AND lower(trim(COALESCE(user_key, ''))) = ?
              AND lower(trim(COALESCE(module_context, ''))) = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (empresa, user, module, limit_val),
        )
    elif user:
        c.execute(
            """
            SELECT id, empresa_id, user_key, role, content, module_context, context_snapshot, created_at
            FROM ai_memoria_empresa
            WHERE empresa_id = ? AND lower(trim(COALESCE(user_key, ''))) = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (empresa, user, limit_val),
        )
    elif module:
        c.execute(
            """
            SELECT id, empresa_id, user_key, role, content, module_context, context_snapshot, created_at
            FROM ai_memoria_empresa
            WHERE empresa_id = ? AND lower(trim(COALESCE(module_context, ''))) = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (empresa, module, limit_val),
        )
    else:
        c.execute(
            """
            SELECT id, empresa_id, user_key, role, content, module_context, context_snapshot, created_at
            FROM ai_memoria_empresa
            WHERE empresa_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (empresa, limit_val),
        )
    rows = c.fetchall()
    conn.close()
    rows.reverse()
    keys = ["id", "empresa_id", "user_key", "role", "content", "module_context", "context_snapshot", "created_at"]
    return [dict(zip(keys, row)) for row in rows]


def limpiar_memoria_asistente_empresa(empresa_id: int, conservar_recientes: int = 0, user_key: str = "") -> int:
    empresa = int(empresa_id or 0)
    if empresa <= 0:
        return 0
    keep = max(0, int(conservar_recientes or 0))
    user = str(user_key or "").strip().lower()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if user:
        if keep <= 0:
            c.execute(
                "DELETE FROM ai_memoria_empresa WHERE empresa_id = ? AND lower(trim(COALESCE(user_key, ''))) = ?",
                (empresa, user),
            )
            deleted = int(c.rowcount or 0)
        else:
            c.execute(
                """
                DELETE FROM ai_memoria_empresa
                WHERE empresa_id = ?
                  AND lower(trim(COALESCE(user_key, ''))) = ?
                  AND id NOT IN (
                    SELECT id FROM ai_memoria_empresa
                    WHERE empresa_id = ?
                      AND lower(trim(COALESCE(user_key, ''))) = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (empresa, user, empresa, user, keep),
            )
            deleted = int(c.rowcount or 0)
    else:
        if keep <= 0:
            c.execute("DELETE FROM ai_memoria_empresa WHERE empresa_id = ?", (empresa,))
            deleted = int(c.rowcount or 0)
        else:
            c.execute(
                """
                DELETE FROM ai_memoria_empresa
                WHERE empresa_id = ?
                  AND id NOT IN (
                    SELECT id FROM ai_memoria_empresa
                    WHERE empresa_id = ?
                    ORDER BY id DESC
                    LIMIT ?
                  )
                """,
                (empresa, empresa, keep),
            )
            deleted = int(c.rowcount or 0)
    conn.commit()
    conn.close()
    _clear_caches()
    return deleted


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
            descripcion_actividad,
            condicion_normal_operacion,
            condicion_anormal_operacion,
            condicion_emergencia,
            aspecto,
            medio_afectado,
            ocurrencia,
            magnitud,
            reversibilidad,
            impacto,
            requisito_legal_asociado,
            condicion,
            significancia,
            es_significativo,
            control_operacional,
            responsable,
            fecha_realizacion,
            cumplimiento,
            registro
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
        "descripcion_actividad",
        "condicion_normal_operacion",
        "condicion_anormal_operacion",
        "condicion_emergencia",
        "aspecto",
        "medio_afectado",
        "ocurrencia",
        "magnitud",
        "reversibilidad",
        "impacto",
        "requisito_legal_asociado",
        "condicion",
        "significancia",
        "es_significativo",
        "control_operacional",
        "responsable",
        "fecha_realizacion",
        "cumplimiento",
        "registro",
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
            descripcion_actividad,
            condicion_normal_operacion,
            condicion_anormal_operacion,
            condicion_emergencia,
            aspecto,
            medio_afectado,
            ocurrencia,
            magnitud,
            reversibilidad,
            impacto,
            requisito_legal_asociado,
            condicion,
            significancia,
            es_significativo,
            control_operacional,
            responsable,
            fecha_realizacion,
            cumplimiento,
            registro
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
        "descripcion_actividad",
        "condicion_normal_operacion",
        "condicion_anormal_operacion",
        "condicion_emergencia",
        "aspecto",
        "medio_afectado",
        "ocurrencia",
        "magnitud",
        "reversibilidad",
        "impacto",
        "requisito_legal_asociado",
        "condicion",
        "significancia",
        "es_significativo",
        "control_operacional",
        "responsable",
        "fecha_realizacion",
        "cumplimiento",
        "registro",
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
    descripcion_actividad="",
    condicion_normal_operacion="",
    condicion_anormal_operacion="",
    condicion_emergencia="",
    medio_afectado="",
    ocurrencia="",
    magnitud="",
    reversibilidad="",
    requisito_legal_asociado="",
    responsable="",
    fecha_realizacion="",
    cumplimiento="",
    registro="",
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
            descripcion_actividad,
            condicion_normal_operacion,
            condicion_anormal_operacion,
            condicion_emergencia,
            aspecto,
            medio_afectado,
            ocurrencia,
            magnitud,
            reversibilidad,
            impacto,
            requisito_legal_asociado,
            condicion,
            significancia,
            es_significativo,
            control_operacional,
            responsable,
            fecha_realizacion,
            cumplimiento,
            registro
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            empresa_id,
            proceso,
            actividad_limpia,
            str(descripcion_actividad).strip(),
            str(condicion_normal_operacion).strip(),
            str(condicion_anormal_operacion).strip(),
            str(condicion_emergencia).strip(),
            aspecto_limpio,
            str(medio_afectado).strip(),
            str(ocurrencia).strip(),
            str(magnitud).strip(),
            str(reversibilidad).strip(),
            str(impacto).strip(),
            str(requisito_legal_asociado).strip(),
            str(condicion).strip(),
            significancia_val,
            es_significativo,
            str(control_operacional).strip(),
            str(responsable).strip(),
            str(fecha_realizacion).strip(),
            str(cumplimiento).strip(),
            str(registro).strip(),
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
    descripcion_actividad="",
    condicion_normal_operacion="",
    condicion_anormal_operacion="",
    condicion_emergencia="",
    medio_afectado="",
    ocurrencia="",
    magnitud="",
    reversibilidad="",
    requisito_legal_asociado="",
    responsable="",
    fecha_realizacion="",
    cumplimiento="",
    registro="",
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
            descripcion_actividad = ?,
            condicion_normal_operacion = ?,
            condicion_anormal_operacion = ?,
            condicion_emergencia = ?,
            aspecto = ?,
            medio_afectado = ?,
            ocurrencia = ?,
            magnitud = ?,
            reversibilidad = ?,
            impacto = ?,
            requisito_legal_asociado = ?,
            condicion = ?,
            significancia = ?,
            es_significativo = ?,
            control_operacional = ?,
            responsable = ?,
            fecha_realizacion = ?,
            cumplimiento = ?,
            registro = ?
        WHERE id = ?
        """,
        (
            proceso,
            actividad_limpia,
            str(descripcion_actividad).strip(),
            str(condicion_normal_operacion).strip(),
            str(condicion_anormal_operacion).strip(),
            str(condicion_emergencia).strip(),
            aspecto_limpio,
            str(medio_afectado).strip(),
            str(ocurrencia).strip(),
            str(magnitud).strip(),
            str(reversibilidad).strip(),
            str(impacto).strip(),
            str(requisito_legal_asociado).strip(),
            str(condicion).strip(),
            significancia_val,
            es_significativo,
            str(control_operacional).strip(),
            str(responsable).strip(),
            str(fecha_realizacion).strip(),
            str(cumplimiento).strip(),
            str(registro).strip(),
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


def list_modules_catalog() -> list[dict]:
    _ensure_module_access_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT id, code, name, description, category, icon, route, is_active, is_core
        FROM modules
        ORDER BY
            CASE category
                WHEN 'core' THEN 1
                WHEN 'quality' THEN 2
                WHEN 'ehs' THEN 3
                WHEN 'lab' THEN 4
                WHEN 'admin' THEN 5
                ELSE 9
            END,
            name
        """
    )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "code", "name", "description", "category", "icon", "route", "is_active", "is_core"]
    return [dict(zip(keys, row)) for row in rows]


def get_available_modules_for_company(company_id: int) -> list[dict]:
    _ensure_module_access_tables()
    _bootstrap_company_modules(int(company_id))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT m.id, m.code, m.name, m.description, m.category, m.icon, m.route, m.is_active,
               COALESCE(cm.enabled, 0) AS enabled
        FROM modules m
        LEFT JOIN company_modules cm
          ON cm.module_id = m.id
         AND cm.company_id = ?
        ORDER BY m.name
        """,
        (int(company_id),),
    )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "code", "name", "description", "category", "icon", "route", "is_active", "enabled"]
    return [dict(zip(keys, row)) for row in rows]


def get_enabled_modules_for_user(user_id: int, company_id: int) -> list[dict]:
    _ensure_module_access_tables()
    _bootstrap_company_modules(int(company_id))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT m.id, m.code, m.name, m.description, m.category, m.icon, m.route,
               COALESCE(cm.enabled, 0) AS company_enabled,
               COALESCE(um.enabled, 0) AS user_enabled
        FROM modules m
        LEFT JOIN company_modules cm
          ON cm.module_id = m.id
         AND cm.company_id = ?
        LEFT JOIN user_modules um
          ON um.module_id = m.id
         AND um.company_id = ?
         AND um.user_id = ?
        WHERE COALESCE(cm.enabled, 0) = 1
        ORDER BY m.name
        """,
        (int(company_id), int(company_id), int(user_id)),
    )
    rows = c.fetchall()
    conn.close()
    keys = ["id", "code", "name", "description", "category", "icon", "route", "company_enabled", "user_enabled"]
    return [dict(zip(keys, row)) for row in rows]


def can_company_access_module(company_id: int, module_code: str) -> bool:
    _ensure_module_access_tables()
    _bootstrap_company_modules(int(company_id))
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COALESCE(cm.enabled, 0)
        FROM modules m
        LEFT JOIN company_modules cm ON cm.module_id = m.id AND cm.company_id = ?
        WHERE lower(trim(m.code)) = lower(trim(?))
        LIMIT 1
        """,
        (int(company_id), str(module_code or "")),
    )
    row = c.fetchone()
    conn.close()
    return bool(int(row[0])) if row else False


def can_user_access_module(user_id: int, company_id: int, module_code: str) -> bool:
    if not can_company_access_module(company_id, module_code):
        return False
    _ensure_module_access_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT COALESCE(um.enabled, 0)
        FROM modules m
        LEFT JOIN user_modules um
          ON um.module_id = m.id
         AND um.company_id = ?
         AND um.user_id = ?
        WHERE lower(trim(m.code)) = lower(trim(?))
        LIMIT 1
        """,
        (int(company_id), int(user_id), str(module_code or "")),
    )
    row = c.fetchone()
    if row is None:
        c.execute(
            """
            SELECT COALESCE(permisos, 'ALL')
            FROM usuarios
            WHERE id = ? AND empresa_id = ?
            LIMIT 1
            """,
            (int(user_id), int(company_id)),
        )
        legacy = c.fetchone()
        conn.close()
        if not legacy:
            return False
        permisos = str(legacy[0] or "ALL").strip()
        if permisos == "ALL":
            return True
        tokens = {item.strip() for item in permisos.split(",") if item.strip()}
        code_to_legacy = {
            "documents": "cert_iso_9001",
            "process_maps": "cert_iso_9001",
            "kpi": "cert_iso_9001",
            "risks": "cert_iso_9001",
            "quality": "cert_iso_9001",
            "environment": "cert_iso_14001",
            "sst": "cert_iso_45001",
            "lab_17025": "cert_iso_17025",
        }
        needed = code_to_legacy.get(str(module_code or "").strip().lower(), "")
        return needed in tokens if needed else False
    conn.close()
    return bool(int(row[0])) if row else False


def assign_modules_to_company(company_id: int, module_ids: list[int], actor: str = "") -> tuple[bool, str]:
    _ensure_module_access_tables()
    selected = {int(item) for item in (module_ids or [])}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, code FROM modules")
    module_rows = c.fetchall()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_events: list[tuple[str, str, dict]] = []
    for mid, code in module_rows:
        enabled = 1 if int(mid) in selected else 0
        c.execute(
            """
            INSERT INTO company_modules (company_id, module_id, enabled, enabled_by, enabled_at, disabled_at, notes)
            VALUES (?, ?, ?, ?, ?, ?, '')
            ON CONFLICT(company_id, module_id) DO UPDATE SET
                enabled = excluded.enabled,
                enabled_by = excluded.enabled_by,
                enabled_at = CASE WHEN excluded.enabled = 1 THEN excluded.enabled_at ELSE company_modules.enabled_at END,
                disabled_at = CASE WHEN excluded.enabled = 0 THEN excluded.enabled_at ELSE NULL END
            """,
            (int(company_id), int(mid), int(enabled), str(actor or ""), now, now if not enabled else None),
        )
        audit_events.append(
            (
                str(code or ""),
                "enable_company_module" if enabled else "disable_company_module",
                {"module_id": int(mid), "enabled": bool(enabled)},
            )
        )
    conn.commit()
    conn.close()
    for code, action, details in audit_events:
        _audit_module_access(
            company_id=int(company_id),
            user_id=None,
            module_code=code,
            action=action,
            actor=actor,
            source="assign_modules_to_company",
            details=details,
        )
    sync_user_modules_after_company_change(int(company_id), actor=actor)
    _clear_caches()
    return True, "Módulos de empresa actualizados."


def sync_user_modules_after_company_change(company_id: int, actor: str = "") -> tuple[bool, str]:
    _ensure_module_access_tables()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT module_id, enabled FROM company_modules WHERE company_id = ?", (int(company_id),))
    company_rows = c.fetchall()
    c.execute("SELECT id FROM usuarios WHERE empresa_id = ?", (int(company_id),))
    user_rows = [int(row[0]) for row in c.fetchall()]
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    for uid in user_rows:
        for mid, company_enabled in company_rows:
            c.execute(
                """
                INSERT INTO user_modules (user_id, company_id, module_id, enabled, assigned_by, assigned_at, removed_at, existed_before_disable)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0)
                ON CONFLICT(user_id, company_id, module_id) DO NOTHING
                """,
                (
                    int(uid),
                    int(company_id),
                    int(mid),
                    1 if int(company_enabled) else 0,
                    str(actor or "sync"),
                    now,
                    None if int(company_enabled) else now,
                ),
            )
            if int(company_enabled):
                c.execute(
                    """
                    UPDATE user_modules
                    SET enabled = CASE WHEN existed_before_disable = 1 THEN 1 ELSE enabled END,
                        removed_at = CASE WHEN existed_before_disable = 1 THEN NULL ELSE removed_at END,
                        existed_before_disable = 0
                    WHERE user_id = ? AND company_id = ? AND module_id = ?
                    """,
                    (int(uid), int(company_id), int(mid)),
                )
            else:
                c.execute(
                    """
                    UPDATE user_modules
                    SET existed_before_disable = CASE WHEN enabled = 1 THEN 1 ELSE existed_before_disable END,
                        enabled = 0,
                        removed_at = ?
                    WHERE user_id = ? AND company_id = ? AND module_id = ?
                    """,
                    (now, int(uid), int(company_id), int(mid)),
                )
    conn.commit()
    conn.close()
    _audit_module_access(
        company_id=int(company_id),
        user_id=None,
        module_code="*",
        action="sync_user_modules_after_company_change",
        actor=actor,
        source="cascade",
    )
    _clear_caches()
    return True, "Permisos de usuarios sincronizados."


def assign_modules_to_user(user_id: int, company_id: int, module_ids: list[int], actor: str = "") -> tuple[bool, str]:
    _ensure_module_access_tables()
    selected = {int(item) for item in (module_ids or [])}
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT m.id, m.code
        FROM modules m
        JOIN company_modules cm ON cm.module_id = m.id
        WHERE cm.company_id = ? AND cm.enabled = 1
        """,
        (int(company_id),),
    )
    allowed_rows = c.fetchall()
    allowed_ids = {int(mid) for mid, _code in allowed_rows}
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    audit_events: list[tuple[str, str, dict]] = []
    for mid, code in allowed_rows:
        enabled = 1 if int(mid) in selected else 0
        c.execute(
            """
            INSERT INTO user_modules (user_id, company_id, module_id, enabled, assigned_by, assigned_at, removed_at, existed_before_disable)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(user_id, company_id, module_id) DO UPDATE SET
                enabled = excluded.enabled,
                assigned_by = excluded.assigned_by,
                assigned_at = CASE WHEN excluded.enabled = 1 THEN excluded.assigned_at ELSE user_modules.assigned_at END,
                removed_at = CASE WHEN excluded.enabled = 0 THEN excluded.assigned_at ELSE NULL END
            """,
            (int(user_id), int(company_id), int(mid), int(enabled), str(actor or ""), now, now if not enabled else None),
        )
        audit_events.append(
            (
                str(code or ""),
                "enable_user_module" if enabled else "disable_user_module",
                {"module_id": int(mid), "enabled": bool(enabled)},
            )
        )
    conn.commit()
    conn.close()
    for code, action, details in audit_events:
        _audit_module_access(
            company_id=int(company_id),
            user_id=int(user_id),
            module_code=code,
            action=action,
            actor=actor,
            source="assign_modules_to_user",
            details=details,
        )
    invalid = [mid for mid in selected if mid not in allowed_ids]
    _clear_caches()
    if invalid:
        return True, "Permisos guardados (algunos módulos no estaban habilitados para la empresa y se ignoraron)."
    return True, "Módulos de usuario actualizados."


def enable_company_module(company_id: int, module_id: int, actor: str = "") -> tuple[bool, str]:
    return assign_modules_to_company(int(company_id), [int(module_id)] + [
        int(item.get("id"))
        for item in get_available_modules_for_company(int(company_id))
        if int(item.get("enabled") or 0) and int(item.get("id") or 0) != int(module_id)
    ], actor=actor)


def disable_company_module(company_id: int, module_id: int, actor: str = "") -> tuple[bool, str]:
    return assign_modules_to_company(int(company_id), [
        int(item.get("id"))
        for item in get_available_modules_for_company(int(company_id))
        if int(item.get("enabled") or 0) and int(item.get("id") or 0) != int(module_id)
    ], actor=actor)


def enable_user_module(user_id: int, company_id: int, module_id: int, actor: str = "") -> tuple[bool, str]:
    current_ids = [
        int(item.get("id"))
        for item in get_enabled_modules_for_user(int(user_id), int(company_id))
        if int(item.get("user_enabled") or 0)
    ]
    if int(module_id) not in current_ids:
        current_ids.append(int(module_id))
    return assign_modules_to_user(int(user_id), int(company_id), current_ids, actor=actor)


def disable_user_module(user_id: int, company_id: int, module_id: int, actor: str = "") -> tuple[bool, str]:
    current_ids = [
        int(item.get("id"))
        for item in get_enabled_modules_for_user(int(user_id), int(company_id))
        if int(item.get("user_enabled") or 0) and int(item.get("id") or 0) != int(module_id)
    ]
    return assign_modules_to_user(int(user_id), int(company_id), current_ids, actor=actor)


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
        SELECT id, username, COALESCE(password, ''), rol, empresa_id, COALESCE(permisos, 'ALL')
        FROM usuarios
        WHERE lower(trim(username)) = lower(trim(?))
        LIMIT 1
        """,
        (str(username).strip(),),
    )
    row = c.fetchone()
    if not row:
        conn.close()
        return None
    user_id, user_name, stored_password, rol, empresa_id, permisos = row
    raw_password = str(password).strip()
    if not _verify_password(raw_password, str(stored_password or "")):
        conn.close()
        return None
    if stored_password and not _is_password_hash(str(stored_password)):
        try:
            c.execute(
                "UPDATE usuarios SET password = ? WHERE id = ?",
                (_hash_password(raw_password), int(user_id)),
            )
            conn.commit()
        except Exception:
            pass
    conn.close()
    return {
        "id": int(user_id),
        "username": str(user_name or ""),
        "rol": str(rol or ""),
        "empresa_id": empresa_id,
        "permisos": str(permisos or "ALL"),
    }


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
    password_store = _hash_password(password_clean)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            """
            INSERT INTO usuarios (username, password, rol, empresa_id, permisos)
            VALUES (?, ?, ?, ?, ?)
            """,
            (username_clean, password_store, rol_clean, empresa_id_clean, permisos_clean or "ALL"),
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
    password_store = _hash_password(password_clean) if password is not None else None

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
            params.append(password_store)
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


def crear_backup_db() -> tuple[bool, str]:
    source = Path(DB_PATH)
    if not source.exists():
        return False, "No existe la base de datos para respaldar."
    backup_root = Path(BACKUP_DIR)
    backup_root.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    target = backup_root / f"ideas_db_{timestamp}.sqlite3"
    try:
        shutil.copy2(source, target)
        return True, str(target.as_posix())
    except Exception as exc:
        return False, f"No se pudo crear el backup: {exc}"


def listar_backups_db(limit: int = 30) -> list[dict]:
    backup_root = Path(BACKUP_DIR)
    if not backup_root.exists():
        return []
    files = sorted(
        [item for item in backup_root.glob("ideas_db_*.sqlite3") if item.is_file()],
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    rows: list[dict] = []
    for item in files[: max(1, int(limit or 30))]:
        stat = item.stat()
        rows.append(
            {
                "name": item.name,
                "path": item.as_posix(),
                "size_kb": round(stat.st_size / 1024, 1),
                "updated_at": datetime.datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
    return rows


def restaurar_backup_db(backup_name: str) -> tuple[bool, str]:
    backup_root = Path(BACKUP_DIR)
    if not backup_root.exists():
        return False, "No existe carpeta de backups."
    safe_name = Path(str(backup_name or "")).name
    source = backup_root / safe_name
    if not source.exists() or not source.is_file():
        return False, "Backup no encontrado."
    target = Path(DB_PATH)
    try:
        pre_ok, pre_path = crear_backup_db()
        if not pre_ok:
            return False, f"No se pudo crear respaldo previo a restaurar: {pre_path}"
        shutil.copy2(source, target)
        _clear_caches()
        return True, f"Base restaurada desde {safe_name}. Reinicia la app para asegurar consistencia."
    except Exception as exc:
        return False, f"No se pudo restaurar backup: {exc}"


def _now_iso() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _db_rows_to_dicts(cursor, keys: list[str]) -> list[dict]:
    return [dict(zip(keys, row)) for row in cursor.fetchall()]


def _entity_defaults(payload: dict | None, estado_default: str = "activo") -> tuple[str, str]:
    data = payload or {}
    return str(data.get("creado_por") or "sistema"), str(data.get("estado") or estado_default)


@lru_cache(maxsize=256)
def obtener_lab_configuracion(empresa_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            empresa_id, lab_nombre, mobile_lab_activo, tipos_ensayo, estados_personalizados, criticidades,
            frecuencias, plantillas, formatos_informe, criterios_aceptacion, actualizado_por, actualizado_en
        FROM lab_configuracion
        WHERE empresa_id = ?
        """,
        (int(empresa_id),),
    )
    row = c.fetchone()
    conn.close()
    keys = [
        "empresa_id", "lab_nombre", "mobile_lab_activo", "tipos_ensayo", "estados_personalizados", "criticidades",
        "frecuencias", "plantillas", "formatos_informe", "criterios_aceptacion", "actualizado_por", "actualizado_en",
    ]
    if not row:
        return {
            "empresa_id": int(empresa_id),
            "lab_nombre": "Laboratorio principal",
            "mobile_lab_activo": 0,
            "tipos_ensayo": "",
            "estados_personalizados": "",
            "criticidades": "baja,media,alta,critica",
            "frecuencias": "mensual,trimestral,semestral,anual",
            "plantillas": "",
            "formatos_informe": "",
            "criterios_aceptacion": "",
            "actualizado_por": "",
            "actualizado_en": "",
        }
    return dict(zip(keys, row))


def guardar_lab_configuracion(empresa_id: int, payload: dict) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM lab_configuracion WHERE empresa_id = ?", (int(empresa_id),))
    exists = c.fetchone()
    fields = (
        str(payload.get("lab_nombre") or "Laboratorio principal"),
        int(bool(payload.get("mobile_lab_activo"))),
        str(payload.get("tipos_ensayo") or ""),
        str(payload.get("estados_personalizados") or ""),
        str(payload.get("criticidades") or ""),
        str(payload.get("frecuencias") or ""),
        str(payload.get("plantillas") or ""),
        str(payload.get("formatos_informe") or ""),
        str(payload.get("criterios_aceptacion") or ""),
        str(payload.get("actualizado_por") or "sistema"),
        _now_iso(),
    )
    if exists:
        c.execute(
            """
            UPDATE lab_configuracion
            SET lab_nombre = ?, mobile_lab_activo = ?, tipos_ensayo = ?, estados_personalizados = ?, criticidades = ?,
                frecuencias = ?, plantillas = ?, formatos_informe = ?, criterios_aceptacion = ?, actualizado_por = ?, actualizado_en = ?
            WHERE empresa_id = ?
            """,
            fields + (int(empresa_id),),
        )
    else:
        c.execute(
            """
            INSERT INTO lab_configuracion (
                lab_nombre, mobile_lab_activo, tipos_ensayo, estados_personalizados, criticidades,
                frecuencias, plantillas, formatos_informe, criterios_aceptacion, actualizado_por, actualizado_en, empresa_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fields + (int(empresa_id),),
        )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Configuracion LAB guardada."


def _generic_lab_list(table: str, empresa_id: int, keys: list[str]) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT {', '.join(keys)} FROM {table} WHERE empresa_id = ? ORDER BY id DESC", (int(empresa_id),))
    rows = _db_rows_to_dicts(c, keys)
    conn.close()
    return rows


def _generic_lab_insert(table: str, fields: dict) -> int:
    keys = list(fields.keys())
    vals = tuple(fields[key] for key in keys)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        f"INSERT INTO {table} ({', '.join(keys)}) VALUES ({', '.join(['?'] * len(keys))})",
        vals,
    )
    new_id = int(c.lastrowid)
    conn.commit()
    conn.close()
    _clear_caches()
    return new_id


def _generic_lab_update(table: str, row_id: int, fields: dict) -> tuple[bool, str]:
    keys = [key for key in fields.keys() if key != "id"]
    if not keys:
        return False, "No hay campos para actualizar."
    vals = tuple(fields[key] for key in keys) + (int(row_id),)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE {table} SET {', '.join([f'{k} = ?' for k in keys])} WHERE id = ?", vals)
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Registro actualizado."


def _empresa_id_for_table_row(table: str, row_id: int) -> int:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"SELECT empresa_id FROM {table} WHERE id = ?", (int(row_id),))
    row = c.fetchone()
    conn.close()
    return int(row[0]) if row and row[0] else 0


def _generic_lab_delete(table: str, row_id: int) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"DELETE FROM {table} WHERE id = ?", (int(row_id),))
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Registro eliminado."


@lru_cache(maxsize=256)
def obtener_lab_equipos_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "codigo_interno", "nombre", "tipo", "marca", "modelo", "serie", "ubicacion", "laboratorio",
        "responsable", "estado", "criticidad", "rango_medicion", "resolucion", "incertidumbre", "fecha_ultima_calibracion",
        "fecha_proxima_calibracion", "frecuencia", "proveedor", "certificado", "observaciones", "historial_json", "adjuntos_json",
        "qr_codigo", "metodos_relacionados", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_equipos", empresa_id, keys)


def crear_lab_equipo(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "activo")
    new_id = _generic_lab_insert(
        "lab_equipos",
        {
            "empresa_id": int(empresa_id),
            "codigo_interno": str(payload.get("codigo_interno") or ""),
            "nombre": str(payload.get("nombre") or "").strip(),
            "tipo": str(payload.get("tipo") or ""),
            "marca": str(payload.get("marca") or ""),
            "modelo": str(payload.get("modelo") or ""),
            "serie": str(payload.get("serie") or ""),
            "ubicacion": str(payload.get("ubicacion") or ""),
            "laboratorio": str(payload.get("laboratorio") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "estado": estado,
            "criticidad": str(payload.get("criticidad") or ""),
            "rango_medicion": str(payload.get("rango_medicion") or ""),
            "resolucion": str(payload.get("resolucion") or ""),
            "incertidumbre": str(payload.get("incertidumbre") or ""),
            "fecha_ultima_calibracion": str(payload.get("fecha_ultima_calibracion") or ""),
            "fecha_proxima_calibracion": str(payload.get("fecha_proxima_calibracion") or ""),
            "frecuencia": str(payload.get("frecuencia") or ""),
            "proveedor": str(payload.get("proveedor") or ""),
            "certificado": str(payload.get("certificado") or ""),
            "observaciones": str(payload.get("observaciones") or ""),
            "historial_json": str(payload.get("historial_json") or ""),
            "adjuntos_json": str(payload.get("adjuntos_json") or ""),
            "qr_codigo": str(payload.get("qr_codigo") or ""),
            "metodos_relacionados": str(payload.get("metodos_relacionados") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "equipo", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Equipo creado.", new_id


def actualizar_lab_equipo(equipo_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_equipos", equipo_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_equipos", int(equipo_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "equipo", int(equipo_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_equipo(equipo_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_equipos", equipo_id)


@lru_cache(maxsize=256)
def obtener_lab_calibraciones_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "equipo_id", "tipo", "fecha", "proveedor", "resultado", "conformidad", "certificado", "evidencia",
        "impacto_potencial", "responsable", "proxima_fecha", "estado", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_calibraciones", empresa_id, keys)


def crear_lab_calibracion(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "programada")
    new_id = _generic_lab_insert(
        "lab_calibraciones",
        {
            "empresa_id": int(empresa_id),
            "equipo_id": int(payload.get("equipo_id") or 0) or None,
            "tipo": str(payload.get("tipo") or "calibracion"),
            "fecha": str(payload.get("fecha") or ""),
            "proveedor": str(payload.get("proveedor") or ""),
            "resultado": str(payload.get("resultado") or ""),
            "conformidad": str(payload.get("conformidad") or ""),
            "certificado": str(payload.get("certificado") or ""),
            "evidencia": str(payload.get("evidencia") or ""),
            "impacto_potencial": str(payload.get("impacto_potencial") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "proxima_fecha": str(payload.get("proxima_fecha") or ""),
            "estado": estado,
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "calibracion", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Evento de calibracion guardado.", new_id


def actualizar_lab_calibracion(evento_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_calibraciones", evento_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_calibraciones", int(evento_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "calibracion", int(evento_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_calibracion(evento_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_calibraciones", evento_id)


@lru_cache(maxsize=256)
def obtener_lab_metodos_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "codigo", "nombre", "version", "norma", "alcance", "responsable_tecnico", "equipos_requeridos",
        "competencias_requeridas", "incertidumbre", "criterios_aceptacion", "documentos", "estado", "validacion", "verificacion",
        "checklist", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_metodos", empresa_id, keys)


def crear_lab_metodo(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "borrador")
    new_id = _generic_lab_insert(
        "lab_metodos",
        {
            "empresa_id": int(empresa_id),
            "codigo": str(payload.get("codigo") or ""),
            "nombre": str(payload.get("nombre") or ""),
            "version": str(payload.get("version") or "1.0"),
            "norma": str(payload.get("norma") or "ISO/IEC 17025"),
            "alcance": str(payload.get("alcance") or ""),
            "responsable_tecnico": str(payload.get("responsable_tecnico") or ""),
            "equipos_requeridos": str(payload.get("equipos_requeridos") or ""),
            "competencias_requeridas": str(payload.get("competencias_requeridas") or ""),
            "incertidumbre": str(payload.get("incertidumbre") or ""),
            "criterios_aceptacion": str(payload.get("criterios_aceptacion") or ""),
            "documentos": str(payload.get("documentos") or ""),
            "estado": estado,
            "validacion": str(payload.get("validacion") or ""),
            "verificacion": str(payload.get("verificacion") or ""),
            "checklist": str(payload.get("checklist") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "metodo", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Metodo creado.", new_id


def actualizar_lab_metodo(metodo_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_metodos", metodo_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_metodos", int(metodo_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "metodo", int(metodo_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_metodo(metodo_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_metodos", metodo_id)


@lru_cache(maxsize=256)
def obtener_lab_muestras_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "codigo_unico", "cliente", "ubicacion", "fecha_recepcion", "responsable", "estado", "tipo", "ensayos",
        "metodo", "condicion_recepcion", "cadena_custodia", "prioridad", "fecha_compromiso", "resultado", "observaciones",
        "evidencias", "fotos", "laboratorio", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_muestras", empresa_id, keys)


def crear_lab_muestra(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "recepcion")
    new_id = _generic_lab_insert(
        "lab_muestras",
        {
            "empresa_id": int(empresa_id),
            "codigo_unico": str(payload.get("codigo_unico") or ""),
            "cliente": str(payload.get("cliente") or ""),
            "ubicacion": str(payload.get("ubicacion") or ""),
            "fecha_recepcion": str(payload.get("fecha_recepcion") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "estado": estado,
            "tipo": str(payload.get("tipo") or ""),
            "ensayos": str(payload.get("ensayos") or ""),
            "metodo": str(payload.get("metodo") or ""),
            "condicion_recepcion": str(payload.get("condicion_recepcion") or ""),
            "cadena_custodia": str(payload.get("cadena_custodia") or ""),
            "prioridad": str(payload.get("prioridad") or "media"),
            "fecha_compromiso": str(payload.get("fecha_compromiso") or ""),
            "resultado": str(payload.get("resultado") or ""),
            "observaciones": str(payload.get("observaciones") or ""),
            "evidencias": str(payload.get("evidencias") or ""),
            "fotos": str(payload.get("fotos") or ""),
            "laboratorio": str(payload.get("laboratorio") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "muestra", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Muestra creada.", new_id


def actualizar_lab_muestra(muestra_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_muestras", muestra_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_muestras", int(muestra_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "muestra", int(muestra_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_muestra(muestra_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_muestras", muestra_id)


@lru_cache(maxsize=256)
def obtener_lab_competencias_empresa(empresa_id: int) -> list[dict]:
    keys = ["id", "empresa_id", "persona", "rol", "metodo_autorizado", "fecha_autorizacion", "vencimiento", "evaluador", "evidencia", "estado", "creado_por", "creado_en", "actualizado_en"]
    return _generic_lab_list("lab_competencias", empresa_id, keys)


def crear_lab_competencia(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "vigente")
    new_id = _generic_lab_insert(
        "lab_competencias",
        {
            "empresa_id": int(empresa_id),
            "persona": str(payload.get("persona") or ""),
            "rol": str(payload.get("rol") or ""),
            "metodo_autorizado": str(payload.get("metodo_autorizado") or ""),
            "fecha_autorizacion": str(payload.get("fecha_autorizacion") or ""),
            "vencimiento": str(payload.get("vencimiento") or ""),
            "evaluador": str(payload.get("evaluador") or ""),
            "evidencia": str(payload.get("evidencia") or ""),
            "estado": estado,
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "competencia", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Competencia guardada.", new_id


def actualizar_lab_competencia(comp_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_competencias", comp_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_competencias", int(comp_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "competencia", int(comp_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_competencia(comp_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_competencias", comp_id)


@lru_cache(maxsize=256)
def obtener_lab_incertidumbre_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "metodo", "componente", "tipo_ab", "distribucion", "coef_sensibilidad", "valor",
        "incertidumbre_estandar", "k", "estado", "creado_por", "creado_en", "actualizado_en",
    ]
    rows = _generic_lab_list("lab_incertidumbre_componentes", empresa_id, keys)
    return rows


def crear_lab_incertidumbre_componente(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "activo")
    new_id = _generic_lab_insert(
        "lab_incertidumbre_componentes",
        {
            "empresa_id": int(empresa_id),
            "metodo": str(payload.get("metodo") or ""),
            "componente": str(payload.get("componente") or ""),
            "tipo_ab": str(payload.get("tipo_ab") or ""),
            "distribucion": str(payload.get("distribucion") or ""),
            "coef_sensibilidad": float(payload.get("coef_sensibilidad") or 0),
            "valor": float(payload.get("valor") or 0),
            "incertidumbre_estandar": float(payload.get("incertidumbre_estandar") or 0),
            "k": float(payload.get("k") or 2),
            "estado": estado,
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "incertidumbre", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Componente de incertidumbre guardado.", new_id


def eliminar_lab_incertidumbre_componente(comp_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_incertidumbre_componentes", comp_id)


@lru_cache(maxsize=256)
def obtener_lab_control_calidad_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "metodo", "equipo", "fecha", "control", "resultado", "limite_inferior", "limite_superior",
        "conformidad", "responsable", "estado", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_control_calidad", empresa_id, keys)


def crear_lab_control_calidad(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "registrado")
    new_id = _generic_lab_insert(
        "lab_control_calidad",
        {
            "empresa_id": int(empresa_id),
            "metodo": str(payload.get("metodo") or ""),
            "equipo": str(payload.get("equipo") or ""),
            "fecha": str(payload.get("fecha") or ""),
            "control": str(payload.get("control") or ""),
            "resultado": float(payload.get("resultado") or 0),
            "limite_inferior": float(payload.get("limite_inferior") or 0),
            "limite_superior": float(payload.get("limite_superior") or 0),
            "conformidad": str(payload.get("conformidad") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "estado": estado,
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "control_calidad", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Control de calidad guardado.", new_id


def eliminar_lab_control_calidad(control_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_control_calidad", control_id)


@lru_cache(maxsize=256)
def obtener_lab_informes_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "numero_informe", "cliente", "muestra", "metodo", "resultado", "incertidumbre",
        "responsable_tecnico", "revisor", "estado", "emision", "pdf_path", "observaciones", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_informes", empresa_id, keys)


def crear_lab_informe(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "borrador")
    new_id = _generic_lab_insert(
        "lab_informes",
        {
            "empresa_id": int(empresa_id),
            "numero_informe": str(payload.get("numero_informe") or ""),
            "cliente": str(payload.get("cliente") or ""),
            "muestra": str(payload.get("muestra") or ""),
            "metodo": str(payload.get("metodo") or ""),
            "resultado": str(payload.get("resultado") or ""),
            "incertidumbre": str(payload.get("incertidumbre") or ""),
            "responsable_tecnico": str(payload.get("responsable_tecnico") or ""),
            "revisor": str(payload.get("revisor") or ""),
            "estado": estado,
            "emision": str(payload.get("emision") or ""),
            "pdf_path": str(payload.get("pdf_path") or ""),
            "observaciones": str(payload.get("observaciones") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "informe", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Informe LAB creado.", new_id


def actualizar_lab_informe(informe_id: int, payload: dict) -> tuple[bool, str]:
    ok, msg = _generic_lab_update("lab_informes", informe_id, {**payload, "actualizado_en": _now_iso()})
    empresa_id = _empresa_id_for_table_row("lab_informes", int(informe_id))
    if ok and empresa_id:
        _trigger_lab_event_checks(int(empresa_id), "informe", int(informe_id), actor=str(payload.get("creado_por") or "evento"))
    return ok, msg


def eliminar_lab_informe(informe_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_informes", informe_id)


@lru_cache(maxsize=256)
def obtener_lab_auditorias_empresa(empresa_id: int) -> list[dict]:
    keys = ["id", "empresa_id", "clausula", "pregunta", "evidencia", "resultado", "hallazgo", "accion", "responsable", "fecha", "estado", "creado_por", "creado_en", "actualizado_en"]
    return _generic_lab_list("lab_auditorias", empresa_id, keys)


def crear_lab_auditoria(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "abierta")
    new_id = _generic_lab_insert(
        "lab_auditorias",
        {
            "empresa_id": int(empresa_id),
            "clausula": str(payload.get("clausula") or ""),
            "pregunta": str(payload.get("pregunta") or ""),
            "evidencia": str(payload.get("evidencia") or ""),
            "resultado": str(payload.get("resultado") or ""),
            "hallazgo": str(payload.get("hallazgo") or ""),
            "accion": str(payload.get("accion") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "fecha": str(payload.get("fecha") or ""),
            "estado": estado,
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "auditoria", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Auditoria LAB guardada.", new_id


def eliminar_lab_auditoria(auditoria_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_auditorias", auditoria_id)


@lru_cache(maxsize=256)
def obtener_lab_riesgos_empresa(empresa_id: int) -> list[dict]:
    keys = ["id", "empresa_id", "proceso", "riesgo", "causa", "consecuencia", "probabilidad", "severidad", "nivel", "accion", "responsable", "estado", "relaciones", "creado_por", "creado_en", "actualizado_en"]
    return _generic_lab_list("lab_riesgos", empresa_id, keys)


def crear_lab_riesgo(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "abierto")
    prob = int(payload.get("probabilidad") or 1)
    sev = int(payload.get("severidad") or 1)
    level = int(payload.get("nivel") or (prob * sev))
    new_id = _generic_lab_insert(
        "lab_riesgos",
        {
            "empresa_id": int(empresa_id),
            "proceso": str(payload.get("proceso") or ""),
            "riesgo": str(payload.get("riesgo") or ""),
            "causa": str(payload.get("causa") or ""),
            "consecuencia": str(payload.get("consecuencia") or ""),
            "probabilidad": prob,
            "severidad": sev,
            "nivel": level,
            "accion": str(payload.get("accion") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "estado": estado,
            "relaciones": str(payload.get("relaciones") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "riesgo", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Riesgo LAB creado.", new_id


def eliminar_lab_riesgo(riesgo_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_riesgos", riesgo_id)


@lru_cache(maxsize=256)
def obtener_lab_acciones_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "origen", "descripcion", "analisis_causa", "accion_inmediata", "accion_correctiva",
        "responsable", "vencimiento", "evidencia", "eficacia", "estado", "relaciones", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_acciones_correctivas", empresa_id, keys)


def crear_lab_accion(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "abierta")
    new_id = _generic_lab_insert(
        "lab_acciones_correctivas",
        {
            "empresa_id": int(empresa_id),
            "origen": str(payload.get("origen") or ""),
            "descripcion": str(payload.get("descripcion") or ""),
            "analisis_causa": str(payload.get("analisis_causa") or ""),
            "accion_inmediata": str(payload.get("accion_inmediata") or ""),
            "accion_correctiva": str(payload.get("accion_correctiva") or ""),
            "responsable": str(payload.get("responsable") or ""),
            "vencimiento": str(payload.get("vencimiento") or ""),
            "evidencia": str(payload.get("evidencia") or ""),
            "eficacia": str(payload.get("eficacia") or ""),
            "estado": estado,
            "relaciones": str(payload.get("relaciones") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "accion", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Accion correctiva LAB creada.", new_id


def eliminar_lab_accion(accion_id: int) -> tuple[bool, str]:
    return _generic_lab_delete("lab_acciones_correctivas", accion_id)


@lru_cache(maxsize=256)
def obtener_lab_mobile_unidades_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "unidad_movil", "patente", "modelo", "estado", "responsable", "habilitaciones", "mantenimiento",
        "calibracion_entorno", "limpieza", "energia", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_mobile_unidades", empresa_id, keys)


def crear_lab_mobile_unidad(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "activo")
    new_id = _generic_lab_insert(
        "lab_mobile_unidades",
        {
            "empresa_id": int(empresa_id),
            "unidad_movil": str(payload.get("unidad_movil") or ""),
            "patente": str(payload.get("patente") or ""),
            "modelo": str(payload.get("modelo") or ""),
            "estado": estado,
            "responsable": str(payload.get("responsable") or ""),
            "habilitaciones": str(payload.get("habilitaciones") or ""),
            "mantenimiento": str(payload.get("mantenimiento") or ""),
            "calibracion_entorno": str(payload.get("calibracion_entorno") or ""),
            "limpieza": str(payload.get("limpieza") or ""),
            "energia": str(payload.get("energia") or ""),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    _trigger_lab_event_checks(int(empresa_id), "mobile_unidad", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Unidad mobile lab creada.", new_id


@lru_cache(maxsize=256)
def obtener_lab_mobile_registros_empresa(empresa_id: int) -> list[dict]:
    keys = [
        "id", "empresa_id", "unidad_movil", "gps", "fecha", "hora", "cliente", "tecnico", "ensayo", "temperatura", "humedad",
        "presion", "vibracion", "energia", "cadena_custodia_json", "checklist_operativo_json", "firma_digital", "fotos", "adjuntos",
        "estado", "sync_estado", "creado_por", "creado_en", "actualizado_en",
    ]
    return _generic_lab_list("lab_mobile_registros", empresa_id, keys)


def crear_lab_mobile_registro(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    creator, estado = _entity_defaults(payload, "cerrado")
    new_id = _generic_lab_insert(
        "lab_mobile_registros",
        {
            "empresa_id": int(empresa_id),
            "unidad_movil": str(payload.get("unidad_movil") or ""),
            "gps": str(payload.get("gps") or ""),
            "fecha": str(payload.get("fecha") or ""),
            "hora": str(payload.get("hora") or ""),
            "cliente": str(payload.get("cliente") or ""),
            "tecnico": str(payload.get("tecnico") or ""),
            "ensayo": str(payload.get("ensayo") or ""),
            "temperatura": float(payload.get("temperatura") or 0),
            "humedad": float(payload.get("humedad") or 0),
            "presion": float(payload.get("presion") or 0),
            "vibracion": float(payload.get("vibracion") or 0),
            "energia": str(payload.get("energia") or ""),
            "cadena_custodia_json": str(payload.get("cadena_custodia_json") or ""),
            "checklist_operativo_json": str(payload.get("checklist_operativo_json") or ""),
            "firma_digital": str(payload.get("firma_digital") or ""),
            "fotos": str(payload.get("fotos") or ""),
            "adjuntos": str(payload.get("adjuntos") or ""),
            "estado": estado,
            "sync_estado": str(payload.get("sync_estado") or "synced"),
            "creado_por": creator,
            "actualizado_en": _now_iso(),
        },
    )
    if str(payload.get("sync_estado") or "synced") == "pendiente":
        _generic_lab_insert(
            "lab_sync_queue",
            {
                "empresa_id": int(empresa_id),
                "entidad": "lab_mobile_registros",
                "entidad_id": int(new_id),
                "payload": json.dumps(payload, ensure_ascii=False),
                "estado": "pendiente",
                "reintentos": 0,
                "ultimo_error": "",
                "actualizado_en": _now_iso(),
            },
        )
    _trigger_lab_event_checks(int(empresa_id), "mobile_registro", int(new_id), actor=str(payload.get("creado_por") or "evento"))
    return True, "Registro Mobile LAB creado.", new_id


@lru_cache(maxsize=128)
def obtener_lab_dashboard_empresa(empresa_id: int) -> dict:
    equipos = obtener_lab_equipos_empresa(int(empresa_id))
    calibraciones = obtener_lab_calibraciones_empresa(int(empresa_id))
    muestras = obtener_lab_muestras_empresa(int(empresa_id))
    metodos = obtener_lab_metodos_empresa(int(empresa_id))
    competencias = obtener_lab_competencias_empresa(int(empresa_id))
    auditorias = obtener_lab_auditorias_empresa(int(empresa_id))
    riesgos = obtener_lab_riesgos_empresa(int(empresa_id))
    acciones = obtener_lab_acciones_empresa(int(empresa_id))
    hoy = datetime.datetime.now().date()

    vencidas = 0
    proximas = 0
    equipos_criticos = 0
    for eq in equipos:
        if str(eq.get("criticidad") or "").lower() in {"alta", "critica"}:
            equipos_criticos += 1
        due = str(eq.get("fecha_proxima_calibracion") or "").strip()
        try:
            if due:
                due_date = datetime.datetime.strptime(due, "%Y-%m-%d").date()
                if due_date < hoy:
                    vencidas += 1
                elif (due_date - hoy).days <= 30:
                    proximas += 1
        except Exception:
            pass
    score = 100
    score -= min(30, vencidas * 8)
    score -= min(20, max(0, len([m for m in muestras if str(m.get("estado") or "").lower() not in {"cerrada", "final"}])) * 2)
    score -= min(20, len([a for a in auditorias if str(a.get("estado") or "").lower() not in {"cerrada", "completada"}]) * 3)
    score -= min(20, len([r for r in riesgos if int(r.get("nivel") or 0) >= 12]) * 3)
    score = max(0, score)
    semaforo = "verde" if score >= 80 else "amarillo" if score >= 60 else "rojo"

    return {
        "score_general": score,
        "semaforo": semaforo,
        "equipos_criticos": equipos_criticos,
        "calibraciones_vencidas": vencidas,
        "calibraciones_proximas": proximas,
        "muestras_abiertas": len([m for m in muestras if str(m.get("estado") or "").lower() not in {"cerrada", "final"}]),
        "metodos_vigentes": len([m for m in metodos if str(m.get("estado") or "").lower() == "vigente"]),
        "competencias_vencidas": len([c for c in competencias if str(c.get("estado") or "").lower() in {"vencida", "vencido"}]),
        "auditorias_abiertas": len([a for a in auditorias if str(a.get("estado") or "").lower() not in {"cerrada", "completada"}]),
        "riesgos_criticos": len([r for r in riesgos if int(r.get("nivel") or 0) >= 12]),
        "acciones_pendientes": len([a for a in acciones if str(a.get("estado") or "").lower() not in {"cerrada", "eficaz"}]),
    }


def validar_competencia_para_metodo(empresa_id: int, persona: str, metodo: str) -> tuple[bool, str]:
    persona_norm = str(persona or "").strip().lower()
    metodo_norm = str(metodo or "").strip().lower()
    for comp in obtener_lab_competencias_empresa(int(empresa_id)):
        if str(comp.get("persona") or "").strip().lower() == persona_norm and str(comp.get("metodo_autorizado") or "").strip().lower() == metodo_norm:
            if str(comp.get("estado") or "").strip().lower() in {"vigente", "activa", "activo"}:
                return True, "Competencia vigente."
            return False, "La competencia existe pero esta vencida o inactiva."
    return False, "No existe competencia autorizada para ese metodo."


def calcular_incertidumbre_metodo(empresa_id: int, metodo: str, k_default: float = 2.0) -> dict:
    metodo_norm = str(metodo or "").strip().lower()
    componentes = [item for item in obtener_lab_incertidumbre_empresa(int(empresa_id)) if str(item.get("metodo") or "").strip().lower() == metodo_norm]
    if not componentes:
        return {"metodo": metodo, "componentes": 0, "uc": 0.0, "k": float(k_default), "U": 0.0}
    suma = 0.0
    k = float(k_default)
    for comp in componentes:
        ui_val = float(comp.get("incertidumbre_estandar") or 0)
        suma += ui_val ** 2
        if comp.get("k") not in (None, ""):
            k = float(comp.get("k") or k_default)
    uc = suma ** 0.5
    return {"metodo": metodo, "componentes": len(componentes), "uc": uc, "k": k, "U": k * uc}


def seed_lab_demo_data(empresa_id: int, creado_por: str = "demo") -> tuple[bool, str]:
    if obtener_lab_equipos_empresa(int(empresa_id)):
        return True, "La empresa ya tiene datos LAB, se conserva informacion existente."
    guardar_lab_configuracion(
        int(empresa_id),
        {
            "lab_nombre": "Laboratorio Central",
            "mobile_lab_activo": 1,
            "tipos_ensayo": "quimico,metrologico,ambiental",
            "actualizado_por": creado_por,
        },
    )
    _ok, _msg, equipo_id = crear_lab_equipo(
        int(empresa_id),
        {
            "codigo_interno": "EQ-17025-001",
            "nombre": "Balanza analitica 0.1mg",
            "tipo": "metrologia",
            "marca": "Mettler",
            "modelo": "XPR205",
            "serie": "SN001122",
            "laboratorio": "Metrologia",
            "responsable": "Jefe Metrologia",
            "estado": "activo",
            "criticidad": "alta",
            "fecha_ultima_calibracion": "2026-04-10",
            "fecha_proxima_calibracion": "2026-06-10",
            "frecuencia": "trimestral",
            "creado_por": creado_por,
        },
    )
    crear_lab_calibracion(
        int(empresa_id),
        {
            "equipo_id": int(equipo_id or 0),
            "tipo": "calibracion",
            "fecha": "2026-04-10",
            "proveedor": "LabCal SA",
            "resultado": "dentro de tolerancia",
            "conformidad": "conforme",
            "proxima_fecha": "2026-06-10",
            "estado": "cerrada",
            "creado_por": creado_por,
        },
    )
    crear_lab_metodo(
        int(empresa_id),
        {
            "codigo": "MET-001",
            "nombre": "Determinacion de masa por pesada directa",
            "version": "2.1",
            "estado": "vigente",
            "responsable_tecnico": "Responsable Tecnico",
            "creado_por": creado_por,
        },
    )
    crear_lab_muestra(
        int(empresa_id),
        {
            "codigo_unico": "MUE-2026-0001",
            "cliente": "Cliente Demo",
            "fecha_recepcion": "2026-05-19",
            "responsable": "Analista 1",
            "estado": "ensayo",
            "metodo": "MET-001",
            "creado_por": creado_por,
        },
    )
    crear_lab_competencia(
        int(empresa_id),
        {
            "persona": "Analista 1",
            "rol": "Analista Senior",
            "metodo_autorizado": "MET-001",
            "fecha_autorizacion": "2026-01-10",
            "vencimiento": "2027-01-10",
            "estado": "vigente",
            "creado_por": creado_por,
        },
    )
    crear_lab_incertidumbre_componente(
        int(empresa_id),
        {
            "metodo": "MET-001",
            "componente": "Repetibilidad",
            "tipo_ab": "A",
            "distribucion": "normal",
            "coef_sensibilidad": 1.0,
            "valor": 0.002,
            "incertidumbre_estandar": 0.002,
            "k": 2.0,
            "creado_por": creado_por,
        },
    )
    crear_lab_control_calidad(
        int(empresa_id),
        {
            "metodo": "MET-001",
            "equipo": "EQ-17025-001",
            "fecha": "2026-05-19",
            "control": "Patron interno",
            "resultado": 10.01,
            "limite_inferior": 9.95,
            "limite_superior": 10.05,
            "conformidad": "conforme",
            "creado_por": creado_por,
        },
    )
    crear_lab_auditoria(
        int(empresa_id),
        {
            "clausula": "7.2",
            "pregunta": "El personal es competente para las tareas asignadas?",
            "resultado": "parcial",
            "hallazgo": "Matriz de competencias incompleta",
            "accion": "Completar autorizaciones por metodo",
            "responsable": "Coordinador Calidad",
            "fecha": "2026-05-20",
            "estado": "abierta",
            "creado_por": creado_por,
        },
    )
    crear_lab_riesgo(
        int(empresa_id),
        {
            "proceso": "Calibraciones",
            "riesgo": "Vencimiento de calibracion critica",
            "causa": "Sin alerta automatica",
            "consecuencia": "Resultados no validos",
            "probabilidad": 3,
            "severidad": 6,
            "accion": "Configurar alertas + bloqueo",
            "responsable": "Jefe Metrologia",
            "estado": "abierto",
            "creado_por": creado_por,
        },
    )
    crear_lab_accion(
        int(empresa_id),
        {
            "origen": "Auditoria interna",
            "descripcion": "Cerrar brecha de competencia metodo MET-001",
            "analisis_causa": "No habia calendario de reevaluacion",
            "accion_correctiva": "Programar matriz anual de renovacion",
            "responsable": "Coordinador Calidad",
            "vencimiento": "2026-06-30",
            "estado": "abierta",
            "creado_por": creado_por,
        },
    )
    crear_lab_mobile_unidad(
        int(empresa_id),
        {
            "unidad_movil": "LAB-MOVIL-01",
            "patente": "AA123BB",
            "modelo": "Sprinter",
            "estado": "activo",
            "responsable": "Tecnico Mobile",
            "energia": "OK",
            "creado_por": creado_por,
        },
    )
    return True, "Datos demo LAB generados."


def _trigger_lab_event_checks(empresa_id: int, record_type: str, record_id: int, actor: str = "evento") -> None:
    try:
        from services.lab_alert_service import run_rules_and_alert
        run_rules_and_alert(int(empresa_id), record_type=str(record_type or ""), record_id=int(record_id or 0), actor=actor)
    except Exception:
        return


@lru_cache(maxsize=256)
def obtener_lab_ai_settings(empresa_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT empresa_id, ia_automatica_activa, scheduler_activo, frecuencia_diaria, frecuencia_semanal_dia, frecuencia_semanal_hora,
               notificar_responsables, auto_summary_activo, max_analisis_por_ciclo, actualizado_por, actualizado_en
        FROM lab_ai_settings
        WHERE empresa_id = ?
        """,
        (int(empresa_id),),
    )
    row = c.fetchone()
    conn.close()
    keys = ["empresa_id", "ia_automatica_activa", "scheduler_activo", "frecuencia_diaria", "frecuencia_semanal_dia", "frecuencia_semanal_hora", "notificar_responsables", "auto_summary_activo", "max_analisis_por_ciclo", "actualizado_por", "actualizado_en"]
    if not row:
        return {
            "empresa_id": int(empresa_id),
            "ia_automatica_activa": 1,
            "scheduler_activo": 0,
            "frecuencia_diaria": "08:30",
            "frecuencia_semanal_dia": "monday",
            "frecuencia_semanal_hora": "09:00",
            "notificar_responsables": "",
            "auto_summary_activo": 1,
            "max_analisis_por_ciclo": 20,
            "actualizado_por": "",
            "actualizado_en": "",
        }
    return dict(zip(keys, row))


def guardar_lab_ai_settings(empresa_id: int, payload: dict) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id FROM lab_ai_settings WHERE empresa_id = ?", (int(empresa_id),))
    existing = c.fetchone()
    values = (
        int(bool(payload.get("ia_automatica_activa", True))),
        int(bool(payload.get("scheduler_activo", False))),
        str(payload.get("frecuencia_diaria") or "08:30"),
        str(payload.get("frecuencia_semanal_dia") or "monday"),
        str(payload.get("frecuencia_semanal_hora") or "09:00"),
        str(payload.get("notificar_responsables") or ""),
        int(bool(payload.get("auto_summary_activo", True))),
        int(payload.get("max_analisis_por_ciclo") or 20),
        str(payload.get("actualizado_por") or "sistema"),
        _now_iso(),
    )
    if existing:
        c.execute(
            """
            UPDATE lab_ai_settings
            SET ia_automatica_activa = ?, scheduler_activo = ?, frecuencia_diaria = ?, frecuencia_semanal_dia = ?, frecuencia_semanal_hora = ?,
                notificar_responsables = ?, auto_summary_activo = ?, max_analisis_por_ciclo = ?, actualizado_por = ?, actualizado_en = ?
            WHERE empresa_id = ?
            """,
            values + (int(empresa_id),),
        )
    else:
        c.execute(
            """
            INSERT INTO lab_ai_settings (
                ia_automatica_activa, scheduler_activo, frecuencia_diaria, frecuencia_semanal_dia, frecuencia_semanal_hora,
                notificar_responsables, auto_summary_activo, max_analisis_por_ciclo, actualizado_por, actualizado_en, empresa_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values + (int(empresa_id),),
        )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Configuración IA LAB guardada."


@lru_cache(maxsize=256)
def obtener_lab_alertas_empresa(empresa_id: int, estado: str = "", criticidad: str = "", modulo: str = "") -> list[dict]:
    from services.lab_alert_service import list_lab_alerts
    return list_lab_alerts(int(empresa_id), status=estado, criticality=criticidad, module=modulo)


def actualizar_lab_alerta_estado(alerta_id: int, estado: str, justificacion: str = "") -> tuple[bool, str]:
    from services.lab_alert_service import update_alert_status
    ok, msg = update_alert_status(int(alerta_id), estado, justification=justificacion)
    _clear_caches()
    return ok, msg


def ejecutar_chequeo_lab_empresa(empresa_id: int, actor: str = "manual") -> dict:
    from services.lab_alert_service import run_rules_and_alert
    result = run_rules_and_alert(int(empresa_id), actor=actor)
    _clear_caches()
    return result


def generar_reporte_pre_acreditacion_lab(empresa_id: int, actor: str = "manual") -> dict:
    from services.lab_ai_report_service import generate_pre_assessment_report
    return generate_pre_assessment_report(int(empresa_id), generated_by=actor)


def obtener_reportes_lab_ai(empresa_id: int) -> list[dict]:
    from services.lab_ai_report_service import list_reports
    return list_reports(int(empresa_id))


def convertir_alerta_en_accion_lab(alerta_id: int, empresa_id: int, responsable: str = "") -> tuple[bool, str, int | None]:
    alerts = obtener_lab_alertas_empresa(int(empresa_id))
    target = next((a for a in alerts if int(a.get("id") or 0) == int(alerta_id)), None)
    if not target:
        return False, "Alerta no encontrada.", None
    ok, msg, new_id = crear_lab_accion(
        int(empresa_id),
        {
            "origen": f"Alerta IA #{alerta_id}",
            "descripcion": str(target.get("titulo") or ""),
            "analisis_causa": str(target.get("descripcion") or ""),
            "accion_correctiva": str(target.get("accion_sugerida") or ""),
            "responsable": responsable or str(target.get("responsable") or ""),
            "vencimiento": str(target.get("fecha_objetivo") or ""),
            "estado": "abierta",
            "creado_por": "ia_lab",
        },
    )
    if not ok:
        return False, msg, None
    actualizar_lab_alerta_estado(int(alerta_id), "en tratamiento", justificacion=f"Convertida en accion #{new_id}")
    return True, "Alerta convertida en acción correctiva.", new_id


@lru_cache(maxsize=256)
def obtener_sst_capacitaciones_empresa(empresa_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id, empresa_id, tema, proceso_emisor, proceso_receptor, personal_involucrado, duracion_minutos,
            fecha_maxima_ejecucion_planificada, fecha_realizacion, estado, porcentaje_personal_capacitado,
            modalidad, responsable_coordinacion, entrenador, requerimiento_legal, detalle_requerimiento
        FROM sst_capacitaciones
        WHERE empresa_id = ?
        ORDER BY id DESC
        """,
        (int(empresa_id),),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "tema",
        "proceso_emisor",
        "proceso_receptor",
        "personal_involucrado",
        "duracion_minutos",
        "fecha_maxima_ejecucion_planificada",
        "fecha_realizacion",
        "estado",
        "porcentaje_personal_capacitado",
        "modalidad",
        "responsable_coordinacion",
        "entrenador",
        "requerimiento_legal",
        "detalle_requerimiento",
    ]
    return [dict(zip(keys, row)) for row in rows]


def crear_sst_capacitacion(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO sst_capacitaciones (
            empresa_id, tema, proceso_emisor, proceso_receptor, personal_involucrado, duracion_minutos,
            fecha_maxima_ejecucion_planificada, fecha_realizacion, estado, porcentaje_personal_capacitado,
            modalidad, responsable_coordinacion, entrenador, requerimiento_legal, detalle_requerimiento, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(empresa_id),
            str(payload.get("tema") or "").strip(),
            str(payload.get("proceso_emisor") or "").strip(),
            str(payload.get("proceso_receptor") or "").strip(),
            int(payload.get("personal_involucrado") or 0),
            int(payload.get("duracion_minutos") or 0),
            str(payload.get("fecha_maxima_ejecucion_planificada") or "").strip(),
            str(payload.get("fecha_realizacion") or "").strip(),
            str(payload.get("estado") or "").strip(),
            float(payload.get("porcentaje_personal_capacitado") or 0),
            str(payload.get("modalidad") or "").strip(),
            str(payload.get("responsable_coordinacion") or "").strip(),
            str(payload.get("entrenador") or "").strip(),
            str(payload.get("requerimiento_legal") or "").strip(),
            str(payload.get("detalle_requerimiento") or "").strip(),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion creada.", int(new_id or 0)


def actualizar_sst_capacitacion(capacitacion_id: int, payload: dict) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE sst_capacitaciones
        SET
            tema = ?,
            proceso_emisor = ?,
            proceso_receptor = ?,
            personal_involucrado = ?,
            duracion_minutos = ?,
            fecha_maxima_ejecucion_planificada = ?,
            fecha_realizacion = ?,
            estado = ?,
            porcentaje_personal_capacitado = ?,
            modalidad = ?,
            responsable_coordinacion = ?,
            entrenador = ?,
            requerimiento_legal = ?,
            detalle_requerimiento = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            str(payload.get("tema") or "").strip(),
            str(payload.get("proceso_emisor") or "").strip(),
            str(payload.get("proceso_receptor") or "").strip(),
            int(payload.get("personal_involucrado") or 0),
            int(payload.get("duracion_minutos") or 0),
            str(payload.get("fecha_maxima_ejecucion_planificada") or "").strip(),
            str(payload.get("fecha_realizacion") or "").strip(),
            str(payload.get("estado") or "").strip(),
            float(payload.get("porcentaje_personal_capacitado") or 0),
            str(payload.get("modalidad") or "").strip(),
            str(payload.get("responsable_coordinacion") or "").strip(),
            str(payload.get("entrenador") or "").strip(),
            str(payload.get("requerimiento_legal") or "").strip(),
            str(payload.get("detalle_requerimiento") or "").strip(),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            int(capacitacion_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion actualizada."


def eliminar_sst_capacitacion(capacitacion_id: int) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM sst_capacitaciones WHERE id = ?", (int(capacitacion_id),))
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion eliminada."


@lru_cache(maxsize=256)
def obtener_ambiental_capacitaciones_empresa(empresa_id: int) -> list[dict]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT
            id, empresa_id, tema, proceso_emisor, proceso_receptor, personal_involucrado, duracion_minutos,
            fecha_maxima_ejecucion_planificada, fecha_realizacion, estado, porcentaje_personal_capacitado,
            modalidad, responsable_coordinacion, entrenador, requerimiento_legal, detalle_requerimiento
        FROM ambiental_capacitaciones
        WHERE empresa_id = ?
        ORDER BY id DESC
        """,
        (int(empresa_id),),
    )
    rows = c.fetchall()
    conn.close()
    keys = [
        "id",
        "empresa_id",
        "tema",
        "proceso_emisor",
        "proceso_receptor",
        "personal_involucrado",
        "duracion_minutos",
        "fecha_maxima_ejecucion_planificada",
        "fecha_realizacion",
        "estado",
        "porcentaje_personal_capacitado",
        "modalidad",
        "responsable_coordinacion",
        "entrenador",
        "requerimiento_legal",
        "detalle_requerimiento",
    ]
    return [dict(zip(keys, row)) for row in rows]


def crear_ambiental_capacitacion(empresa_id: int, payload: dict) -> tuple[bool, str, int | None]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        INSERT INTO ambiental_capacitaciones (
            empresa_id, tema, proceso_emisor, proceso_receptor, personal_involucrado, duracion_minutos,
            fecha_maxima_ejecucion_planificada, fecha_realizacion, estado, porcentaje_personal_capacitado,
            modalidad, responsable_coordinacion, entrenador, requerimiento_legal, detalle_requerimiento, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            int(empresa_id),
            str(payload.get("tema") or "").strip(),
            str(payload.get("proceso_emisor") or "").strip(),
            str(payload.get("proceso_receptor") or "").strip(),
            int(payload.get("personal_involucrado") or 0),
            int(payload.get("duracion_minutos") or 0),
            str(payload.get("fecha_maxima_ejecucion_planificada") or "").strip(),
            str(payload.get("fecha_realizacion") or "").strip(),
            str(payload.get("estado") or "").strip(),
            float(payload.get("porcentaje_personal_capacitado") or 0),
            str(payload.get("modalidad") or "").strip(),
            str(payload.get("responsable_coordinacion") or "").strip(),
            str(payload.get("entrenador") or "").strip(),
            str(payload.get("requerimiento_legal") or "").strip(),
            str(payload.get("detalle_requerimiento") or "").strip(),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    new_id = c.lastrowid
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion creada.", int(new_id or 0)


def actualizar_ambiental_capacitacion(capacitacion_id: int, payload: dict) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        UPDATE ambiental_capacitaciones
        SET
            tema = ?,
            proceso_emisor = ?,
            proceso_receptor = ?,
            personal_involucrado = ?,
            duracion_minutos = ?,
            fecha_maxima_ejecucion_planificada = ?,
            fecha_realizacion = ?,
            estado = ?,
            porcentaje_personal_capacitado = ?,
            modalidad = ?,
            responsable_coordinacion = ?,
            entrenador = ?,
            requerimiento_legal = ?,
            detalle_requerimiento = ?,
            updated_at = ?
        WHERE id = ?
        """,
        (
            str(payload.get("tema") or "").strip(),
            str(payload.get("proceso_emisor") or "").strip(),
            str(payload.get("proceso_receptor") or "").strip(),
            int(payload.get("personal_involucrado") or 0),
            int(payload.get("duracion_minutos") or 0),
            str(payload.get("fecha_maxima_ejecucion_planificada") or "").strip(),
            str(payload.get("fecha_realizacion") or "").strip(),
            str(payload.get("estado") or "").strip(),
            float(payload.get("porcentaje_personal_capacitado") or 0),
            str(payload.get("modalidad") or "").strip(),
            str(payload.get("responsable_coordinacion") or "").strip(),
            str(payload.get("entrenador") or "").strip(),
            str(payload.get("requerimiento_legal") or "").strip(),
            str(payload.get("detalle_requerimiento") or "").strip(),
            datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            int(capacitacion_id),
        ),
    )
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion actualizada."


def eliminar_ambiental_capacitacion(capacitacion_id: int) -> tuple[bool, str]:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM ambiental_capacitaciones WHERE id = ?", (int(capacitacion_id),))
    conn.commit()
    conn.close()
    _clear_caches()
    return True, "Capacitacion eliminada."
