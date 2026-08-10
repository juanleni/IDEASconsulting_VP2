"""Tests for services/legal_matrix_alert_scheduler.py.

core_data.obtener_empresa_detalle and ideas_utils.enviar_correo_alertas_legal_matrix
are always monkeypatched here: the former hits the real ideas.db (via an
lru_cache'd connection), the latter would send a real email over SMTP. Neither
should ever run for real inside a test.
"""
from __future__ import annotations

from datetime import date, timedelta

import pytest

import modules_legal_matrix as mlm
import services.legal_matrix_alert_scheduler as scheduler


@pytest.fixture(autouse=True)
def scratch_db(tmp_path, monkeypatch):
    monkeypatch.setattr(mlm, 'DB_PATH', str(tmp_path / 'test.db'))
    mlm._ensure_tables()


@pytest.fixture(autouse=True)
def force_send_time(monkeypatch):
    monkeypatch.setattr(scheduler, '_ya_paso_la_hora_de_envio', lambda: True)


@pytest.fixture
def fake_email(monkeypatch):
    calls = []

    def _fake(correo, nombre_empresa, alertas):
        calls.append({'correo': correo, 'nombre_empresa': nombre_empresa, 'alertas': alertas})
        return {'ok': True, 'to': correo}

    monkeypatch.setattr(scheduler, 'enviar_correo_alertas_legal_matrix', _fake)
    return calls


@pytest.fixture
def fake_empresa(monkeypatch):
    def _fake(empresa_id):
        return {'razon_social': 'Empresa Test', 'contacto_correo': 'contacto@empresa-test.com'}

    monkeypatch.setattr(scheduler, 'obtener_empresa_detalle', _fake)


def _crear_requisito_vencido(empresa_id: int) -> None:
    mlm._insert('legal_requirements', {
        'empresa_id': empresa_id,
        'titulo': 'Norma vencida',
        'proxima_revision': (date.today() - timedelta(days=1)).isoformat(),
        'vigente': 1,
    })


def test_sends_email_when_there_are_open_alerts(fake_email, fake_empresa):
    _crear_requisito_vencido(1)
    result = scheduler.procesar_alertas_empresa(1)
    assert result == {'ok': True, 'to': 'contacto@empresa-test.com'}
    assert len(fake_email) == 1
    assert fake_email[0]['nombre_empresa'] == 'Empresa Test'
    assert len(fake_email[0]['alertas']) == 1


def test_marks_sent_even_with_no_alerts_and_skips_email(fake_email, fake_empresa):
    result = scheduler.procesar_alertas_empresa(1)
    assert result is None
    assert fake_email == []
    assert mlm.obtener_legal_matrix_alert_settings(1)['ultimo_envio'] == date.today().isoformat()


def test_skips_when_alerts_disabled(fake_email, fake_empresa):
    mlm.guardar_legal_matrix_alert_settings(1, activo=False, dias_anticipacion=30)
    _crear_requisito_vencido(1)
    result = scheduler.procesar_alertas_empresa(1)
    assert result is None
    assert fake_email == []


def test_skips_when_already_sent_today(fake_email, fake_empresa):
    mlm.marcar_legal_matrix_alertas_enviadas(1)
    _crear_requisito_vencido(1)
    result = scheduler.procesar_alertas_empresa(1)
    assert result is None
    assert fake_email == []


def test_skips_before_send_hour(monkeypatch, fake_email, fake_empresa):
    monkeypatch.setattr(scheduler, '_ya_paso_la_hora_de_envio', lambda: False)
    _crear_requisito_vencido(1)
    result = scheduler.procesar_alertas_empresa(1)
    assert result is None
    assert fake_email == []


def test_skips_when_company_has_no_contact_email(monkeypatch, fake_email):
    monkeypatch.setattr(
        scheduler, 'obtener_empresa_detalle',
        lambda empresa_id: {'razon_social': 'Empresa Sin Correo', 'contacto_correo': ''},
    )
    _crear_requisito_vencido(1)
    result = scheduler.procesar_alertas_empresa(1)
    assert result is None
    assert fake_email == []
