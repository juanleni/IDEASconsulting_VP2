"""Capa de servicios de Calidad/8D: acceso a datos y reglas de negocio para
analisis 8D, 5 Porques e Ishikawa (problemas, causas raiz, acciones).

Extraido de core_data.py el 2026-08-28, replicando el patron de
legal_matrix_service.py (Fase 4, 2026-08-10): un archivo <modulo>_service.py
sin ningun `@ui.page`/`ui.xxx` de construccion de interfaz, importable y
testeable sin levantar NiceGUI. La UI (formularios, tabs, PDF) se queda en
modules_quality.py, en register_quality_module.

A diferencia de Matriz Legal, este modulo NO tiene su propia `_connect()` ni
crea sus tablas: `calidad_problemas_8d`, `calidad_5_porque`, `calidad_ishikawa`
y `calidad_8d_acciones` siguen definidas centralmente en `database.py`
(`crear_base()`), junto con el resto del esquema de la plataforma -- no se
fragmento eso porque ya era la fuente unica de verdad del schema antes de
esta extraccion, y moverlo no era parte de lo que pedia el piloto.

Nota sobre cache: estas funciones de lectura usan `@lru_cache` (igual que
antes en core_data.py) y sus escrituras siguen invalidando el cache global
completo (`core_data._clear_caches()`), no solo el de Calidad -- se preservo
la invalidacion amplia tal cual estaba para no cambiar de comportamiento en
esta extraccion mecanica. Se importa `_clear_caches` de forma diferida
(dentro de la funcion, no arriba del archivo) para evitar un import
circular: core_data.py re-exporta estas funciones (`from quality_service
import ...`) para que el resto del codigo (`from core_data import
obtener_problemas_calidad_empresa`, etc.) siga funcionando sin tocar ningun
otro archivo.
"""
from __future__ import annotations

import datetime
import os
import sqlite3
from functools import lru_cache

DB_PATH = os.getenv("IDEAS_DB_PATH", "ideas.db")


def _clear_caches() -> None:
    """Invalida el cache global completo (no solo el de Calidad) -- import
    diferido para evitar el ciclo core_data <-> quality_service. Ver nota
    del modulo."""
    from core_data import _clear_caches as _clear_all_caches
    _clear_all_caches()


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
    empresa_id=None,
):
    titulo_limpio = str(titulo).strip()
    if not titulo_limpio:
        return False, "El titulo del analisis no puede estar vacio."

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False, "El analisis 8D no existe."
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


def eliminar_problema_calidad_8d(problema_id, empresa_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False
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
    empresa_id=None,
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False, "El analisis 8D no existe."
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


def eliminar_5_porque_problema_calidad(problema_id, empresa_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False
    c.execute("DELETE FROM calidad_5_porque WHERE problema_id = ?", (problema_id,))
    conn.commit()
    conn.close()
    _clear_caches()
    return True


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
    empresa_id=None,
):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False, "El analisis 8D no existe."
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


def eliminar_ishikawa_problema_calidad(problema_id, empresa_id=None):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    if empresa_id is not None:
        c.execute("SELECT id FROM calidad_problemas_8d WHERE id = ? AND empresa_id = ?", (problema_id, int(empresa_id)))
        if not c.fetchone():
            conn.close()
            return False
    c.execute("DELETE FROM calidad_ishikawa WHERE problema_id = ?", (problema_id,))
    conn.commit()
    conn.close()
    _clear_caches()
    return True


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

