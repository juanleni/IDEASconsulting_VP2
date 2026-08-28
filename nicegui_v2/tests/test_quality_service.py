"""Tests for quality_service.py (Calidad/8D data layer, extracted from
core_data.py 2026-08-28 -- ver el docstring del modulo).

Cada test usa una base SQLite descartable (nunca ideas.db real), creada con
el esquema real via database.crear_base() -- las tablas de Calidad
(calidad_problemas_8d, calidad_5_porque, calidad_ishikawa,
calidad_8d_acciones) viven ahi, no en quality_service.py.
"""
from __future__ import annotations

import pytest

import database
import quality_service as qs


@pytest.fixture(autouse=True)
def scratch_db(tmp_path, monkeypatch):
    db_path = str(tmp_path / 'test.db')
    monkeypatch.setenv('IDEAS_DB_PATH', db_path)
    monkeypatch.setattr(qs, 'DB_PATH', db_path)
    database.crear_base()
    for fn in (
        qs.obtener_problemas_calidad_empresa,
        qs.obtener_problema_calidad_detalle,
        qs.obtener_5_porque_problema_calidad,
        qs.obtener_ishikawa_problema_calidad,
        qs.obtener_acciones_8d,
    ):
        fn.cache_clear()
    yield
    for fn in (
        qs.obtener_problemas_calidad_empresa,
        qs.obtener_problema_calidad_detalle,
        qs.obtener_5_porque_problema_calidad,
        qs.obtener_ishikawa_problema_calidad,
        qs.obtener_acciones_8d,
    ):
        fn.cache_clear()


def _crear_caso(empresa_id=1, **overrides):
    payload = dict(
        empresa_id=empresa_id,
        fecha='28.08.2026',
        titulo='Falla de torque en linea 3',
        origen='Cliente',
    )
    payload.update(overrides)
    ok, msg, problema_id = qs.crear_problema_calidad_8d(**payload)
    assert ok, msg
    return problema_id


class TestProblema8D:
    def test_crear_y_listar(self):
        problema_id = _crear_caso()
        rows = qs.obtener_problemas_calidad_empresa(1)
        assert len(rows) == 1
        assert rows[0]['id'] == problema_id
        assert rows[0]['titulo'] == 'Falla de torque en linea 3'
        assert rows[0]['estado'] == 'Abierto'

    def test_numero_8d_autogenerado_si_no_se_pasa(self):
        _crear_caso(empresa_id=5)
        rows = qs.obtener_problemas_calidad_empresa(5)
        assert rows[0]['numero_8d'] == '8D-005-0001'

    def test_titulo_vacio_no_guarda(self):
        ok, msg, problema_id = qs.crear_problema_calidad_8d(
            empresa_id=1, fecha='28.08.2026', titulo='   ',
        )
        assert not ok
        assert problema_id is None
        assert qs.obtener_problemas_calidad_empresa(1) == []

    def test_detalle_por_id(self):
        problema_id = _crear_caso()
        detalle = qs.obtener_problema_calidad_detalle(problema_id)
        assert detalle is not None
        assert detalle['titulo'] == 'Falla de torque en linea 3'
        assert qs.obtener_problema_calidad_detalle(999999) is None

    def test_actualizar(self):
        problema_id = _crear_caso()
        ok, msg = qs.actualizar_problema_calidad_8d(
            problema_id=problema_id, fecha='28.08.2026', titulo='Titulo corregido',
            estado='Cerrado',
        )
        assert ok, msg
        detalle = qs.obtener_problema_calidad_detalle(problema_id)
        assert detalle['titulo'] == 'Titulo corregido'
        assert detalle['estado'] == 'Cerrado'

    def test_actualizar_respeta_empresa_id(self):
        problema_id = _crear_caso(empresa_id=1)
        ok, msg = qs.actualizar_problema_calidad_8d(
            problema_id=problema_id, fecha='28.08.2026', titulo='Intento cruzado',
            empresa_id=2,
        )
        assert not ok
        assert qs.obtener_problema_calidad_detalle(problema_id)['titulo'] == 'Falla de torque en linea 3'

    def test_eliminar_cascade(self):
        problema_id = _crear_caso()
        qs.guardar_5_porque_problema_calidad(problema_id=problema_id, problema_inicial='x')
        qs.guardar_ishikawa_problema_calidad(problema_id=problema_id, efecto='x')
        qs.guardar_accion_8d(problema_id=problema_id, fase_8d='D5', accion='Corregir')

        qs.eliminar_problema_calidad_8d(problema_id)

        assert qs.obtener_problemas_calidad_empresa(1) == []
        assert qs.obtener_5_porque_problema_calidad(problema_id) is None
        assert qs.obtener_ishikawa_problema_calidad(problema_id) is None
        assert qs.obtener_acciones_8d(problema_id) == []

    def test_eliminar_respeta_empresa_id(self):
        problema_id = _crear_caso(empresa_id=1)
        result = qs.eliminar_problema_calidad_8d(problema_id, empresa_id=2)
        assert result is False
        assert qs.obtener_problema_calidad_detalle(problema_id) is not None


class Test5Porques:
    def test_guardar_y_leer(self):
        problema_id = _crear_caso()
        ok, msg = qs.guardar_5_porque_problema_calidad(
            problema_id=problema_id, problema_inicial='No arranca', porque_1='Fusible quemado',
        )
        assert ok, msg
        registro = qs.obtener_5_porque_problema_calidad(problema_id)
        assert registro['problema_inicial'] == 'No arranca'
        assert registro['porque_1'] == 'Fusible quemado'

    def test_guardar_dos_veces_actualiza_no_duplica(self):
        problema_id = _crear_caso()
        qs.guardar_5_porque_problema_calidad(problema_id=problema_id, porque_1='v1')
        qs.guardar_5_porque_problema_calidad(problema_id=problema_id, porque_1='v2')
        assert qs.obtener_5_porque_problema_calidad(problema_id)['porque_1'] == 'v2'

    def test_eliminar(self):
        problema_id = _crear_caso()
        qs.guardar_5_porque_problema_calidad(problema_id=problema_id, porque_1='v1')
        assert qs.eliminar_5_porque_problema_calidad(problema_id) is True
        assert qs.obtener_5_porque_problema_calidad(problema_id) is None


class TestIshikawa:
    def test_guardar_y_leer(self):
        problema_id = _crear_caso()
        ok, msg = qs.guardar_ishikawa_problema_calidad(
            problema_id=problema_id, efecto='Pieza fuera de tolerancia', maquina='Torno CNC 3',
        )
        assert ok, msg
        registro = qs.obtener_ishikawa_problema_calidad(problema_id)
        assert registro['efecto'] == 'Pieza fuera de tolerancia'
        assert registro['maquina'] == 'Torno CNC 3'

    def test_guardar_respeta_empresa_id(self):
        problema_id = _crear_caso(empresa_id=1)
        ok, msg = qs.guardar_ishikawa_problema_calidad(problema_id=problema_id, efecto='x', empresa_id=2)
        assert not ok
        assert qs.obtener_ishikawa_problema_calidad(problema_id) is None


class TestAcciones8D:
    def test_guardar_y_listar(self):
        problema_id = _crear_caso()
        ok, msg, accion_id = qs.guardar_accion_8d(
            problema_id=problema_id, fase_8d='D5', accion='Reemplazar sensor', responsable='J. Perez',
        )
        assert ok, msg
        acciones = qs.obtener_acciones_8d(problema_id)
        assert len(acciones) == 1
        assert acciones[0]['id'] == accion_id
        assert acciones[0]['fase_8d'] == 'D5'

    def test_accion_vacia_no_guarda(self):
        problema_id = _crear_caso()
        ok, msg, accion_id = qs.guardar_accion_8d(problema_id=problema_id, fase_8d='D5', accion='   ')
        assert not ok
        assert accion_id is None

    def test_filtrar_por_fase(self):
        problema_id = _crear_caso()
        qs.guardar_accion_8d(problema_id=problema_id, fase_8d='D5', accion='Accion D5')
        qs.guardar_accion_8d(problema_id=problema_id, fase_8d='D6', accion='Accion D6')
        assert len(qs.obtener_acciones_8d(problema_id)) == 2
        assert len(qs.obtener_acciones_8d(problema_id, fase_8d='D5')) == 1

    def test_eliminar(self):
        problema_id = _crear_caso()
        _, _, accion_id = qs.guardar_accion_8d(problema_id=problema_id, fase_8d='D5', accion='Accion')
        qs.eliminar_accion_8d(accion_id)
        assert qs.obtener_acciones_8d(problema_id) == []


class TestReexportDesdeCoreData:
    """core_data.py re-exporta estas funciones para no romper a nadie que
    siga haciendo `from core_data import obtener_problemas_calidad_empresa`
    -- confirma que son literalmente el mismo objeto, no una copia."""

    def test_mismo_objeto_de_funcion(self):
        import core_data
        assert core_data.obtener_problemas_calidad_empresa is qs.obtener_problemas_calidad_empresa
        assert core_data.crear_problema_calidad_8d is qs.crear_problema_calidad_8d
        assert core_data.eliminar_accion_8d is qs.eliminar_accion_8d
