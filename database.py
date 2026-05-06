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
        "password": "TEXT",
        "contacto_telefono": "TEXT",
        "contacto_posicion": "TEXT",
        "rubro": "TEXT",
        "cantidad_empleados": "INTEGER",
        "cert_iso_9001": "TEXT",
        "cert_iso_14001": "TEXT",
        "cert_iso_45001": "TEXT",
        "cert_iatf": "TEXT",
        "logo_path": "TEXT",
        "color_primario": "TEXT",
        "color_secundario": "TEXT",
        "agente_ia_activo": "INTEGER DEFAULT 0",
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

    c.execute("""
    CREATE TABLE IF NOT EXISTS mapa_procesos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proceso_codigo TEXT NOT NULL,
        proceso_nombre TEXT NOT NULL,
        dueno_proceso TEXT,
        ultima_revision TEXT,
        entradas TEXT,
        salidas TEXT,
        documentos TEXT,
        indicadores TEXT,
        recursos TEXT,
        orden INTEGER DEFAULT 0
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS kpis (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proceso_id INTEGER,
        codigo TEXT,
        nombre TEXT NOT NULL,
        objetivo REAL,
        categoria TEXT,
        formula TEXT,
        meta TEXT,
        frecuencia TEXT,
        responsable TEXT,
        fuente TEXT,
        unidad TEXT,
        tipo_grafico TEXT,
        usa_ytd INTEGER,
        tipo_ytd TEXT,
        mostrar_en_dashboard INTEGER DEFAULT 1,
        ytd_manual_val REAL,
        comentarios_desvio TEXT,
        ene REAL,
        feb REAL,
        mar REAL,
        abr REAL,
        may REAL,
        jun REAL,
        jul REAL,
        ago REAL,
        sep REAL,
        oct REAL,
        nov REAL,
        dic REAL,
        diario_json TEXT,
        mensual_manual_val REAL,
        anual_manual_val REAL,
        objetivo_sentido TEXT DEFAULT 'mayor_mejor',
        dashboard_principal INTEGER DEFAULT 0,
        grupos_personalizados TEXT,
        valor_actual TEXT,
        tendencia TEXT,
        observaciones TEXT,
        fecha_actualizacion TEXT,
        orden INTEGER DEFAULT 0
    )
    """)

    nuevas_columnas_kpis = {
        "proceso_id": "INTEGER",
        "objetivo": "REAL",
        "tipo_grafico": "TEXT",
        "usa_ytd": "INTEGER DEFAULT 0",
        "tipo_ytd": "TEXT",
        "mostrar_en_dashboard": "INTEGER DEFAULT 1",
        "ytd_manual_val": "REAL",
        "comentarios_desvio": "TEXT",
        "ene": "REAL",
        "feb": "REAL",
        "mar": "REAL",
        "abr": "REAL",
        "may": "REAL",
        "jun": "REAL",
        "jul": "REAL",
        "ago": "REAL",
        "sep": "REAL",
        "oct": "REAL",
        "nov": "REAL",
        "dic": "REAL",
        "diario_json": "TEXT",
        "mensual_manual_val": "REAL",
        "anual_manual_val": "REAL",
        "objetivo_sentido": "TEXT DEFAULT 'mayor_mejor'",
        "dashboard_principal": "INTEGER DEFAULT 0",
        "grupos_personalizados": "TEXT",
    }

    for columna, tipo in nuevas_columnas_kpis.items():
        if not _columna_existe(c, "kpis", columna):
            c.execute(f"ALTER TABLE kpis ADD COLUMN {columna} {tipo}")

    if _columna_existe(c, "kpis", "mostrar_en_dashboard"):
        c.execute("""
            UPDATE kpis
            SET mostrar_en_dashboard = 1
            WHERE mostrar_en_dashboard IS NULL
        """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS matrices_riesgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proceso_nombre TEXT,
        fecha_actualizacion TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS items_riesgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        matriz_id INTEGER NOT NULL,
        tipo TEXT,
        descripcion TEXT,
        ocurrencia INTEGER,
        severidad INTEGER,
        npr INTEGER,
        accion_obligatoria BOOLEAN,
        acciones_tomadas TEXT,
        fecha_accion TEXT,
        responsable TEXT,
        eficaz BOOLEAN
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS aspectos_ambientales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proceso_nombre TEXT,
        actividad TEXT,
        aspecto TEXT,
        impacto TEXT,
        condicion TEXT,
        significancia INTEGER,
        es_significativo BOOLEAN,
        control_operacional TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS matriz_legal_ambiental (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        jurisdiccion TEXT,
        norma_legal TEXT,
        articulo_aplicable TEXT,
        estado_cumplimiento TEXT,
        fecha_vencimiento TEXT,
        responsable TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS simulacros_ambientales (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        escenario TEXT,
        fecha_simulacro TEXT,
        participantes TEXT,
        respuesta_eficaz BOOLEAN,
        conclusiones_mejora TEXT,
        archivos_path TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS calidad_problemas_8d (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        numero_8d TEXT,
        fecha TEXT,
        titulo TEXT,
        origen TEXT,
        d1_equipo TEXT,
        d2_descripcion TEXT,
        d3_contencion TEXT,
        d4_causa_raiz TEXT,
        d5_accion_correctiva TEXT,
        d6_verificacion TEXT,
        d7_prevencion TEXT,
        d8_cierre TEXT,
        customer_project TEXT,
        fault_type TEXT,
        safety_relevant INTEGER DEFAULT 0,
        repetitive_fault INTEGER DEFAULT 0,
        nok_ok_details TEXT,
        d3_sorting_details TEXT,
        d4_simulation_details TEXT,
        d5_training_details TEXT,
        d7_docs_update TEXT,
        d8_closure_details TEXT,
        estado TEXT,
        archivos_path TEXT
    )
    """)

    nuevas_columnas_8d = {
        "numero_8d": "TEXT",
        "customer_project": "TEXT",
        "fault_type": "TEXT",
        "safety_relevant": "INTEGER DEFAULT 0",
        "repetitive_fault": "INTEGER DEFAULT 0",
        "nok_ok_details": "TEXT",
        "d3_sorting_details": "TEXT",
        "d4_simulation_details": "TEXT",
        "d5_training_details": "TEXT",
        "d7_docs_update": "TEXT",
        "d8_closure_details": "TEXT",
    }

    for columna, tipo in nuevas_columnas_8d.items():
        if not _columna_existe(c, "calidad_problemas_8d", columna):
            c.execute(f"ALTER TABLE calidad_problemas_8d ADD COLUMN {columna} {tipo}")

    c.execute("""
    CREATE TABLE IF NOT EXISTS calidad_5_porque (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problema_id INTEGER NOT NULL,
        problema_inicial TEXT,
        porque_1 TEXT,
        porque_2 TEXT,
        porque_3 TEXT,
        porque_4 TEXT,
        porque_5 TEXT,
        causa_raiz_confirmada TEXT,
        occ_problema TEXT,
        occ_p1 TEXT,
        occ_p2 TEXT,
        occ_p3 TEXT,
        occ_p4 TEXT,
        occ_p5 TEXT,
        occ_causa_raiz TEXT,
        det_problema TEXT,
        det_p1 TEXT,
        det_p2 TEXT,
        det_p3 TEXT,
        det_p4 TEXT,
        det_p5 TEXT,
        det_causa_raiz TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS calidad_ishikawa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problema_id INTEGER NOT NULL,
        efecto TEXT,
        mano_obra TEXT,
        maquina TEXT,
        material TEXT,
        metodo TEXT,
        medicion TEXT,
        medio_ambiente TEXT,
        factores_retenidos TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS calidad_8d_acciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        problema_id INTEGER NOT NULL,
        fase_8d TEXT,
        accion TEXT,
        responsable TEXT,
        fecha TEXT,
        progreso TEXT,
        evidencia_path TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS usuarios (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        rol TEXT,
        empresa_id INTEGER,
        permisos TEXT DEFAULT 'ALL'
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS empresa_fuentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        tipo TEXT,
        contenido TEXT,
        fecha_carga TEXT
    )
    """)

    nuevas_columnas_simulacros = {
        "participantes": "TEXT",
        "conclusiones_mejora": "TEXT",
        "archivos_path": "TEXT",
    }

    for columna, tipo in nuevas_columnas_simulacros.items():
        if not _columna_existe(c, "simulacros_ambientales", columna):
            c.execute(f"ALTER TABLE simulacros_ambientales ADD COLUMN {columna} {tipo}")

    try:
        c.execute("ALTER TABLE matriz_legal_ambiental ADD COLUMN jurisdiccion TEXT")
    except sqlite3.OperationalError:
        pass

    nuevas_columnas_5p = {
        "ocurrencia_1": "TEXT",
        "ocurrencia_2": "TEXT",
        "ocurrencia_3": "TEXT",
        "ocurrencia_4": "TEXT",
        "ocurrencia_5": "TEXT",
        "causa_ocurrencia": "TEXT",
        "no_deteccion_1": "TEXT",
        "no_deteccion_2": "TEXT",
        "no_deteccion_3": "TEXT",
        "no_deteccion_4": "TEXT",
        "no_deteccion_5": "TEXT",
        "causa_no_deteccion": "TEXT",
        "occ_problema": "TEXT",
        "occ_p1": "TEXT",
        "occ_p2": "TEXT",
        "occ_p3": "TEXT",
        "occ_p4": "TEXT",
        "occ_p5": "TEXT",
        "occ_causa_raiz": "TEXT",
        "det_problema": "TEXT",
        "det_p1": "TEXT",
        "det_p2": "TEXT",
        "det_p3": "TEXT",
        "det_p4": "TEXT",
        "det_p5": "TEXT",
        "det_causa_raiz": "TEXT",
    }

    for columna, tipo in nuevas_columnas_5p.items():
        if not _columna_existe(c, "calidad_5_porque", columna):
            c.execute(f"ALTER TABLE calidad_5_porque ADD COLUMN {columna} {tipo}")

    if not _columna_existe(c, "calidad_ishikawa", "factores_retenidos"):
        c.execute("ALTER TABLE calidad_ishikawa ADD COLUMN factores_retenidos TEXT")

    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN permisos TEXT DEFAULT 'ALL'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE usuarios ADD COLUMN empresa_id INTEGER")
    except sqlite3.OperationalError:
        pass

    c.execute("SELECT COUNT(*) FROM usuarios")
    usuarios_count = int(c.fetchone()[0] or 0)
    if usuarios_count == 0:
        c.execute(
            """
            INSERT INTO usuarios (username, password, rol, empresa_id, permisos)
            VALUES (?, ?, ?, ?, ?)
            """,
            ("admin", "ideas2026", "IDEAS_ADMIN", None, "ALL"),
        )

    conn.commit()
    conn.close()
