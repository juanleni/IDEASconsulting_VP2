import sqlite3


def _columna_existe(cursor, tabla, columna):
    cursor.execute(f"PRAGMA table_info({tabla})")
    columnas = [row[1] for row in cursor.fetchall()]
    return columna in columnas


def crear_base():
    import os
    import sqlite3

    conn = sqlite3.connect(os.getenv("IDEAS_DB_PATH", "ideas.db"))
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
        "cert_iso_17025": "TEXT",
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
        descripcion_actividad TEXT,
        condicion_normal_operacion TEXT,
        condicion_anormal_operacion TEXT,
        condicion_emergencia TEXT,
        aspecto TEXT,
        medio_afectado TEXT,
        ocurrencia TEXT,
        magnitud TEXT,
        reversibilidad TEXT,
        impacto TEXT,
        requisito_legal_asociado TEXT,
        condicion TEXT,
        significancia INTEGER,
        es_significativo BOOLEAN,
        control_operacional TEXT,
        responsable TEXT,
        fecha_realizacion TEXT,
        cumplimiento TEXT,
        registro TEXT
    )
    """)

    nuevas_columnas_aspectos = {
        "descripcion_actividad": "TEXT",
        "condicion_normal_operacion": "TEXT",
        "condicion_anormal_operacion": "TEXT",
        "condicion_emergencia": "TEXT",
        "medio_afectado": "TEXT",
        "ocurrencia": "TEXT",
        "magnitud": "TEXT",
        "reversibilidad": "TEXT",
        "requisito_legal_asociado": "TEXT",
        "responsable": "TEXT",
        "fecha_realizacion": "TEXT",
        "cumplimiento": "TEXT",
        "registro": "TEXT",
    }
    for columna, tipo in nuevas_columnas_aspectos.items():
        if not _columna_existe(c, "aspectos_ambientales", columna):
            c.execute(f"ALTER TABLE aspectos_ambientales ADD COLUMN {columna} {tipo}")

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

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS sst_capacitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tema TEXT,
            proceso_emisor TEXT,
            proceso_receptor TEXT,
            personal_involucrado INTEGER,
            duracion_minutos INTEGER,
            fecha_maxima_ejecucion_planificada TEXT,
            fecha_realizacion TEXT,
            estado TEXT,
            porcentaje_personal_capacitado REAL,
            modalidad TEXT,
            responsable_coordinacion TEXT,
            entrenador TEXT,
            requerimiento_legal TEXT,
            detalle_requerimiento TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    c.execute(
        """
        CREATE TABLE IF NOT EXISTS ambiental_capacitaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            empresa_id INTEGER NOT NULL,
            tema TEXT,
            proceso_emisor TEXT,
            proceso_receptor TEXT,
            personal_involucrado INTEGER,
            duracion_minutos INTEGER,
            fecha_maxima_ejecucion_planificada TEXT,
            fecha_realizacion TEXT,
            estado TEXT,
            porcentaje_personal_capacitado REAL,
            modalidad TEXT,
            responsable_coordinacion TEXT,
            entrenador TEXT,
            requerimiento_legal TEXT,
            detalle_requerimiento TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

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

    c.execute("""
    CREATE TABLE IF NOT EXISTS ai_memoria_empresa (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        user_key TEXT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        module_context TEXT,
        context_snapshot TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_configuracion (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL UNIQUE,
        lab_nombre TEXT,
        mobile_lab_activo INTEGER DEFAULT 0,
        tipos_ensayo TEXT,
        estados_personalizados TEXT,
        criticidades TEXT,
        frecuencias TEXT,
        plantillas TEXT,
        formatos_informe TEXT,
        criterios_aceptacion TEXT,
        actualizado_por TEXT,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_equipos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        codigo_interno TEXT,
        nombre TEXT NOT NULL,
        tipo TEXT,
        marca TEXT,
        modelo TEXT,
        serie TEXT,
        ubicacion TEXT,
        laboratorio TEXT,
        responsable TEXT,
        estado TEXT,
        criticidad TEXT,
        rango_medicion TEXT,
        resolucion TEXT,
        incertidumbre TEXT,
        fecha_ultima_calibracion TEXT,
        fecha_proxima_calibracion TEXT,
        frecuencia TEXT,
        proveedor TEXT,
        certificado TEXT,
        observaciones TEXT,
        historial_json TEXT,
        adjuntos_json TEXT,
        qr_codigo TEXT,
        metodos_relacionados TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_calibraciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        equipo_id INTEGER,
        tipo TEXT,
        fecha TEXT,
        proveedor TEXT,
        resultado TEXT,
        conformidad TEXT,
        certificado TEXT,
        evidencia TEXT,
        impacto_potencial TEXT,
        responsable TEXT,
        proxima_fecha TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_metodos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        codigo TEXT,
        nombre TEXT NOT NULL,
        version TEXT,
        norma TEXT,
        alcance TEXT,
        responsable_tecnico TEXT,
        equipos_requeridos TEXT,
        competencias_requeridas TEXT,
        incertidumbre TEXT,
        criterios_aceptacion TEXT,
        documentos TEXT,
        estado TEXT,
        validacion TEXT,
        verificacion TEXT,
        checklist TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_muestras (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        codigo_unico TEXT,
        cliente TEXT,
        ubicacion TEXT,
        fecha_recepcion TEXT,
        responsable TEXT,
        estado TEXT,
        tipo TEXT,
        ensayos TEXT,
        metodo TEXT,
        condicion_recepcion TEXT,
        cadena_custodia TEXT,
        prioridad TEXT,
        fecha_compromiso TEXT,
        resultado TEXT,
        observaciones TEXT,
        evidencias TEXT,
        fotos TEXT,
        laboratorio TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_competencias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        persona TEXT,
        rol TEXT,
        metodo_autorizado TEXT,
        fecha_autorizacion TEXT,
        vencimiento TEXT,
        evaluador TEXT,
        evidencia TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_incertidumbre_componentes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        metodo TEXT,
        componente TEXT,
        tipo_ab TEXT,
        distribucion TEXT,
        coef_sensibilidad REAL,
        valor REAL,
        incertidumbre_estandar REAL,
        k REAL,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_control_calidad (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        metodo TEXT,
        equipo TEXT,
        fecha TEXT,
        control TEXT,
        resultado REAL,
        limite_inferior REAL,
        limite_superior REAL,
        conformidad TEXT,
        responsable TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_informes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        numero_informe TEXT,
        cliente TEXT,
        muestra TEXT,
        metodo TEXT,
        resultado TEXT,
        incertidumbre TEXT,
        responsable_tecnico TEXT,
        revisor TEXT,
        estado TEXT,
        emision TEXT,
        pdf_path TEXT,
        observaciones TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_auditorias (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        clausula TEXT,
        pregunta TEXT,
        evidencia TEXT,
        resultado TEXT,
        hallazgo TEXT,
        accion TEXT,
        responsable TEXT,
        fecha TEXT,
        estado TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_riesgos (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        proceso TEXT,
        riesgo TEXT,
        causa TEXT,
        consecuencia TEXT,
        probabilidad INTEGER,
        severidad INTEGER,
        nivel INTEGER,
        accion TEXT,
        responsable TEXT,
        estado TEXT,
        relaciones TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_acciones_correctivas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        origen TEXT,
        descripcion TEXT,
        analisis_causa TEXT,
        accion_inmediata TEXT,
        accion_correctiva TEXT,
        responsable TEXT,
        vencimiento TEXT,
        evidencia TEXT,
        eficacia TEXT,
        estado TEXT,
        relaciones TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_mobile_unidades (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        unidad_movil TEXT,
        patente TEXT,
        modelo TEXT,
        estado TEXT,
        responsable TEXT,
        habilitaciones TEXT,
        mantenimiento TEXT,
        calibracion_entorno TEXT,
        limpieza TEXT,
        energia TEXT,
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_mobile_registros (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        unidad_movil TEXT,
        gps TEXT,
        fecha TEXT,
        hora TEXT,
        cliente TEXT,
        tecnico TEXT,
        ensayo TEXT,
        temperatura REAL,
        humedad REAL,
        presion REAL,
        vibracion REAL,
        energia TEXT,
        cadena_custodia_json TEXT,
        checklist_operativo_json TEXT,
        firma_digital TEXT,
        fotos TEXT,
        adjuntos TEXT,
        estado TEXT,
        sync_estado TEXT DEFAULT 'synced',
        creado_por TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_sync_queue (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        entidad TEXT,
        entidad_id INTEGER,
        payload TEXT,
        estado TEXT DEFAULT 'pendiente',
        reintentos INTEGER DEFAULT 0,
        ultimo_error TEXT,
        creado_en TEXT DEFAULT CURRENT_TIMESTAMP,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_ai_alertas (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        titulo TEXT NOT NULL,
        descripcion TEXT,
        modulo_origen TEXT,
        registro_tipo TEXT,
        registro_id INTEGER,
        responsable TEXT,
        criticidad TEXT,
        tipo TEXT,
        estado TEXT DEFAULT 'abierta',
        fecha_deteccion TEXT DEFAULT CURRENT_TIMESTAMP,
        fecha_objetivo TEXT,
        accion_sugerida TEXT,
        requiere_ia INTEGER DEFAULT 0,
        resultado_ia_json TEXT,
        evidencia_esperada TEXT,
        reglas_activadas_json TEXT,
        creado_por TEXT,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_ai_analisis_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        alerta_id INTEGER,
        disparador TEXT,
        contexto_json TEXT,
        respuesta_json TEXT,
        modelo TEXT,
        tokens_estimados INTEGER DEFAULT 0,
        costo_estimado_usd REAL DEFAULT 0,
        creado_por TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_ai_reportes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL,
        tipo TEXT,
        score_general REAL,
        resumen_ejecutivo TEXT,
        payload_json TEXT,
        generado_por TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    c.execute("""
    CREATE TABLE IF NOT EXISTS lab_ai_settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        empresa_id INTEGER NOT NULL UNIQUE,
        ia_automatica_activa INTEGER DEFAULT 1,
        scheduler_activo INTEGER DEFAULT 0,
        frecuencia_diaria TEXT DEFAULT '08:30',
        frecuencia_semanal_dia TEXT DEFAULT 'monday',
        frecuencia_semanal_hora TEXT DEFAULT '09:00',
        notificar_responsables TEXT,
        auto_summary_activo INTEGER DEFAULT 1,
        max_analisis_por_ciclo INTEGER DEFAULT 20,
        actualizado_por TEXT,
        actualizado_en TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)
    if not _columna_existe(c, "ai_memoria_empresa", "user_key"):
        c.execute("ALTER TABLE ai_memoria_empresa ADD COLUMN user_key TEXT")
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_ai_memoria_empresa_fecha
    ON ai_memoria_empresa (empresa_id, id DESC)
    """)
    c.execute("""
    CREATE INDEX IF NOT EXISTS idx_ai_memoria_empresa_user
    ON ai_memoria_empresa (empresa_id, user_key, id DESC)
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
