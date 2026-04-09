import sqlite3


def _columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas = [row[1] for row in cursor.fetchall()]
    return columna in columnas


def crear_base():
    import sqlite3

    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS empresas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        nombre TEXT
    )
    """)

    nuevas_columnas_empresas = {
        "razon_social": "TEXT",
        "ubicacion": "TEXT",
        "contacto_nombre": "TEXT",
        "contacto_correo": "TEXT",
        "contacto_telefono": "TEXT",
        "contacto_posicion": "TEXT",
        "rubro": "TEXT",
        "cantidad_empleados": "INTEGER",
        "cert_iso_9001": "TEXT",
        "cert_iso_14001": "TEXT",
        "cert_iso_45001": "TEXT",
        "cert_iatf": "TEXT",
    }

    for columna, tipo in nuevas_columnas_empresas.items():
        if not _columna_existe(c, "empresas", columna):
            c.execute(f"ALTER TABLE empresas ADD COLUMN {columna} {tipo}")

    if _columna_existe(c, "empresas", "nombre") and _columna_existe(c, "empresas", "razon_social"):
        c.execute("""
            UPDATE empresas
            SET razon_social = COALESCE(NULLIF(razon_social, ''), nombre)
            WHERE COALESCE(NULLIF(razon_social, ''), '') = ''
        """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS diagnosticos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER,
        fecha TEXT,
        score REAL,
        nivel TEXT,
        conclusion TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS respuestas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        diagnostico_id INTEGER,
        eje TEXT,
        pregunta TEXT,
        respuesta INTEGER,
        evidencia TEXT,
        observacion TEXT
    )
    """)

    conn.commit()
    conn.close()
