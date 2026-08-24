"""Tests for modules_legal_matrix.py.

Most of these are unit tests: they exercise the parsing/SQL/password helpers
directly against a throwaway SQLite file (never the real ideas.db), and never
start a real server. TestMatrixRoleEndpoints (2026-08-24, audit finding #1 of
the second round) is the exception -- it registers the real FastAPI routes
from register_legal_matrix_module() onto nicegui's app singleton and drives
them with fastapi.testclient.TestClient, to prove the RBAC enforcement added
2026-08-21 (legal_matrix_service._require_matrix_permission) actually runs
on the live route and not just when called directly. Still safe: DB_PATH is
redirected to the scratch_db fixture's throwaway file exactly like every
other test here, and app.storage.user is monkeypatched the same way
TestIsMatrixAdmin already does below, so no real session/cookie machinery
(and no real ideas.db) is involved.
"""
from __future__ import annotations

import io
from datetime import date, timedelta

import openpyxl
import pytest

import modules_legal_matrix as mlm
import legal_matrix_service as lms


@pytest.fixture(autouse=True)
def scratch_db(tmp_path, monkeypatch):
    # DB_PATH y _connect() viven en legal_matrix_service.py desde la extracción de
    # capa de servicios (Fase 4) — parchear mlm.DB_PATH ya no alcanza, porque
    # mlm._connect (re-exportado) sigue leyendo el DB_PATH del módulo donde fue
    # *definido* (legal_matrix_service), no el de modules_legal_matrix.
    monkeypatch.setattr(lms, 'DB_PATH', str(tmp_path / 'test.db'))
    mlm._ensure_tables()


def _build_workbook(headers, rows, header_row=1):
    wb = openpyxl.Workbook()
    ws = wb.active
    for _ in range(header_row - 1):
        ws.append([])
    ws.append(headers)
    for row in rows:
        ws.append(row)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


KATASTER_HEADERS = [
    'Abreviatura', 'Ley', 'De.', 'Tipo', 'Nivel', 'Relevancia', 'Cumplió',
    'Último cambio', 'Información para el usuario', 'Obligaciones',
    'Supervisión', 'Responsabilidades', 'Documentos',
]


class TestParseLegalMatrixExcel:
    def test_parses_valid_rows(self):
        # 'nivel' uses the Kataster codes: B=Nacional, L=Provincial, K=Municipal.
        content = _build_workbook(KATASTER_HEADERS, [
            ['N-1', 'Ley de proteccion ambiental', 'Ministerio de Ambiente', 'Ley', 'B',
             'X', 'Si', None, 'Cumplir con la normativa', 'Observaciones', 'Resp A', 'Resp B', 'Registro X'],
            ['N-2', 'Ley de seguridad e higiene', 'SRT', 'Decreto', 'L',
             '', 'No', None, 'Otra obligacion', '', 'Resp C', '', ''],
        ])
        rows = mlm._parse_legal_matrix_excel(content)
        assert len(rows) == 2
        first, second = rows
        assert first['titulo'] == 'Ley de proteccion ambiental'
        assert first['estado'] == 'Cumple'
        assert first['criticidad'] == 'Alta'
        assert first['jurisdiccion'] == 'Nacional'
        assert first['responsable'] == 'Resp A — Resp B'
        assert second['estado'] == 'Pendiente'
        assert second['criticidad'] == 'Media'
        assert second['jurisdiccion'] == 'Provincial'
        assert second['responsable'] == 'Resp C'

    def test_header_can_be_offset_by_blank_rows(self):
        content = _build_workbook(KATASTER_HEADERS, [
            ['N-1', 'Ley offset', 'Organismo', 'Ley', 'NAC', '', 'Si', None, '', '', '', '', ''],
        ], header_row=5)
        rows = mlm._parse_legal_matrix_excel(content)
        assert len(rows) == 1
        assert rows[0]['titulo'] == 'Ley offset'

    def test_stops_after_15_consecutive_blank_rows(self):
        data_rows = [['', '', '', '', '', '', '', None, '', '', '', '', '']] * 20
        data_rows.append(['N-last', 'Nunca deberia importarse', 'Org', 'Ley', 'NAC', '', 'Si', None, '', '', '', '', ''])
        content = _build_workbook(KATASTER_HEADERS, data_rows)
        with pytest.raises(ValueError):
            mlm._parse_legal_matrix_excel(content)

    def test_missing_required_columns_raises(self):
        content = _build_workbook(['Foo', 'Bar'], [['a', 'b']])
        with pytest.raises(ValueError, match='formato EU4.05.13.00'):
            mlm._parse_legal_matrix_excel(content)

    def test_corrupt_file_raises_friendly_error(self):
        with pytest.raises(ValueError, match='Excel'):
            mlm._parse_legal_matrix_excel(b'not an excel file')


class TestInsertHelpers:
    def test_insert_returns_row_id(self):
        rid = mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'Norma A'})
        assert rid == 1
        rows = mlm._rows('SELECT * FROM legal_requirements WHERE id = ?', (rid,))
        assert rows[0]['titulo'] == 'Norma A'

    def test_insert_many_bulk_round_trip(self):
        payloads = [{'empresa_id': 1, 'titulo': f'Norma {i}'} for i in range(10)]
        inserted = mlm._insert_many('legal_requirements', payloads)
        assert inserted == 10
        rows = mlm._rows('SELECT * FROM legal_requirements WHERE empresa_id = ?', (1,))
        assert len(rows) == 10

    def test_insert_many_empty_list_is_noop(self):
        assert mlm._insert_many('legal_requirements', []) == 0


class TestBulkAndFullDeleteScoping:
    def _seed(self):
        ids_e1 = [mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': f'E1-{i}'}) for i in range(5)]
        ids_e2 = [mlm._insert('legal_requirements', {'empresa_id': 2, 'titulo': f'E2-{i}'}) for i in range(3)]
        return ids_e1, ids_e2

    def test_bulk_delete_only_removes_selected_ids_for_that_company(self):
        ids_e1, ids_e2 = self._seed()
        subset = ids_e1[:2]
        with mlm._connect() as conn:
            marks = ', '.join('?' for _ in subset)
            cur = conn.execute(
                f'DELETE FROM legal_requirements WHERE empresa_id = ? AND id IN ({marks})',
                (1, *subset),
            )
            assert cur.rowcount == 2
        remaining_e1 = mlm._rows('SELECT id FROM legal_requirements WHERE empresa_id = ?', (1,))
        remaining_e2 = mlm._rows('SELECT id FROM legal_requirements WHERE empresa_id = ?', (2,))
        assert {r['id'] for r in remaining_e1} == set(ids_e1[2:])
        assert {r['id'] for r in remaining_e2} == set(ids_e2)

    def test_bulk_delete_ignores_ids_belonging_to_another_company(self):
        ids_e1, ids_e2 = self._seed()
        with mlm._connect() as conn:
            marks = ', '.join('?' for _ in ids_e2)
            cur = conn.execute(
                f'DELETE FROM legal_requirements WHERE empresa_id = ? AND id IN ({marks})',
                (1, *ids_e2),
            )
            assert cur.rowcount == 0
        assert len(mlm._rows('SELECT id FROM legal_requirements WHERE empresa_id = ?', (2,))) == 3

    def test_delete_all_only_affects_target_company(self):
        ids_e1, ids_e2 = self._seed()
        with mlm._connect() as conn:
            cur = conn.execute('DELETE FROM legal_requirements WHERE empresa_id = ?', (1,))
            assert cur.rowcount == 5
        assert mlm._rows('SELECT id FROM legal_requirements WHERE empresa_id = ?', (1,)) == []
        assert len(mlm._rows('SELECT id FROM legal_requirements WHERE empresa_id = ?', (2,))) == 3


class TestDeleteAllPassword:
    def test_default_password_is_ideas(self):
        assert mlm.tiene_legal_matrix_password_personalizada(1) is False
        assert mlm.verificar_legal_matrix_delete_password(1, 'IDEAS') is True
        assert mlm.verificar_legal_matrix_delete_password(1, 'wrong') is False

    def test_custom_password_overrides_default(self):
        mlm.guardar_legal_matrix_delete_password(1, 'MiClaveSegura!')
        assert mlm.tiene_legal_matrix_password_personalizada(1) is True
        assert mlm.verificar_legal_matrix_delete_password(1, 'MiClaveSegura!') is True
        assert mlm.verificar_legal_matrix_delete_password(1, 'IDEAS') is False

    def test_password_is_stored_hashed_not_plaintext(self):
        mlm.guardar_legal_matrix_delete_password(1, 'MiClaveSegura!')
        row = mlm._rows('SELECT * FROM legal_matrix_settings WHERE empresa_id = 1')[0]
        assert row['delete_all_password_hash'] != 'MiClaveSegura!'
        assert row['delete_all_password_hash'].startswith('pbkdf2_sha256$')

    def test_blank_password_does_not_change_existing_one(self):
        mlm.guardar_legal_matrix_delete_password(1, 'MiClaveSegura!')
        mlm.guardar_legal_matrix_delete_password(1, '   ')
        assert mlm.verificar_legal_matrix_delete_password(1, 'MiClaveSegura!') is True

    def test_password_is_scoped_per_company(self):
        mlm.guardar_legal_matrix_delete_password(1, 'ClaveEmpresa1')
        assert mlm.verificar_legal_matrix_delete_password(2, 'IDEAS') is True
        assert mlm.verificar_legal_matrix_delete_password(2, 'ClaveEmpresa1') is False


class TestNormalizationHelpers:
    @pytest.mark.parametrize('value,expected', [
        ('cumple', 'cumple'), ('no_cumple', 'no_cumple'), ('pendiente', 'pendiente'),
        ('no_aplica', 'no_aplica'), ('algo-invalido', 'pendiente'), (None, 'pendiente'),
    ])
    def test_norm_status(self, value, expected):
        assert mlm._norm_status(value) == expected

    @pytest.mark.parametrize('value,expected', [
        ('critica', 'critica'), ('alta', 'alta'), ('media', 'media'),
        ('baja', 'baja'), ('desconocido', 'media'), (None, 'media'),
    ])
    def test_norm_criticality(self, value, expected):
        assert mlm._norm_criticality(value) == expected

    def test_norm_audit_status_accepts_spanish_synonyms(self):
        assert mlm._norm_audit_status('conforme') == 'cerrada'
        assert mlm._norm_audit_status('planificada') == 'programada'
        assert mlm._norm_audit_status(None) == 'programada'

    def test_norm_approval(self):
        assert mlm._norm_approval('aprobado') == 'aprobado'
        assert mlm._norm_approval('rechazado') == 'rechazado'
        assert mlm._norm_approval(None) == 'pendiente'


class TestAlertSettings:
    def test_default_settings(self):
        settings = mlm.obtener_legal_matrix_alert_settings(1)
        assert settings == {'activo': True, 'dias_anticipacion': 30, 'ultimo_envio': None}

    def test_save_and_read_round_trip(self):
        mlm.guardar_legal_matrix_alert_settings(1, activo=False, dias_anticipacion=15)
        settings = mlm.obtener_legal_matrix_alert_settings(1)
        assert settings['activo'] is False
        assert settings['dias_anticipacion'] == 15

    def test_settings_are_scoped_per_company(self):
        mlm.guardar_legal_matrix_alert_settings(1, activo=False, dias_anticipacion=15)
        assert mlm.obtener_legal_matrix_alert_settings(2) == {'activo': True, 'dias_anticipacion': 30, 'ultimo_envio': None}

    def test_marcar_enviadas_sets_today(self):
        mlm.marcar_legal_matrix_alertas_enviadas(1)
        settings = mlm.obtener_legal_matrix_alert_settings(1)
        assert settings['ultimo_envio'] == date.today().isoformat()


class TestGenerarAlertasVencimientos:
    def _crear_requisito(self, empresa_id, titulo, proxima_revision, vigente=1):
        return mlm._insert('legal_requirements', {
            'empresa_id': empresa_id,
            'titulo': titulo,
            'proxima_revision': proxima_revision,
            'vigente': vigente,
        })

    def test_creates_alert_within_window(self):
        proxima = (date.today() + timedelta(days=10)).isoformat()
        self._crear_requisito(1, 'Norma A', proxima)
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert len(creadas) == 1
        assert 'Norma A' in creadas[0]['titulo']

    def test_ignores_requirement_beyond_window(self):
        proxima = (date.today() + timedelta(days=90)).isoformat()
        self._crear_requisito(1, 'Norma lejana', proxima)
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert creadas == []

    def test_ignores_requirement_without_next_review_date(self):
        self._crear_requisito(1, 'Sin fecha', '')
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert creadas == []

    def test_ignores_non_vigente_requirement(self):
        proxima = (date.today() + timedelta(days=5)).isoformat()
        self._crear_requisito(1, 'Norma dada de baja', proxima, vigente=0)
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert creadas == []

    def test_does_not_duplicate_open_alert_on_second_run(self):
        proxima = (date.today() + timedelta(days=10)).isoformat()
        self._crear_requisito(1, 'Norma A', proxima)
        first = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        second = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert len(first) == 1
        assert second == []

    def test_overdue_requirement_is_critica(self):
        proxima = (date.today() - timedelta(days=3)).isoformat()
        self._crear_requisito(1, 'Norma vencida', proxima)
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert creadas[0]['prioridad'] == 'critica'
        assert 'Vencida' in creadas[0]['titulo']

    def test_due_soon_requirement_is_alta(self):
        proxima = (date.today() + timedelta(days=3)).isoformat()
        self._crear_requisito(1, 'Norma urgente', proxima)
        creadas = mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert creadas[0]['prioridad'] == 'alta'

    def test_generated_alert_does_not_leak_to_other_company(self):
        proxima = (date.today() + timedelta(days=10)).isoformat()
        self._crear_requisito(1, 'Norma empresa 1', proxima)
        mlm.generar_alertas_vencimientos(1, dias_anticipacion=30)
        assert mlm.obtener_legal_matrix_alertas_vencimiento_abiertas(2) == []
        assert len(mlm.obtener_legal_matrix_alertas_vencimiento_abiertas(1)) == 1


class TestConstruirContextoReporte:
    def test_empty_company_does_not_crash(self):
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['cumplimiento_pct'] == 0
        assert ctx['no_cumplidos'] == 0
        assert ctx['alertas_abiertas'] == 0
        assert ctx['areas'] == []
        assert ctx['sedes'] == []
        assert ctx['hallazgos'] == []

    def test_cumplimiento_and_estados(self):
        for estado in ('cumple', 'cumple', 'no_cumple', 'pendiente'):
            mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'x', 'estado': estado})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['cumplimiento_pct'] == 50
        assert ctx['no_cumplidos'] == 1
        assert ctx['estados'] == {'cumple': 2, 'no_cumple': 1, 'pendiente': 1, 'no_aplica': 0}
        assert ctx['total_requisitos'] == 4

    def test_alertas_abiertas_excludes_cerradas(self):
        mlm._insert('legal_alerts', {'empresa_id': 1, 'titulo': 'abierta', 'estado': 'Nueva'})
        mlm._insert('legal_alerts', {'empresa_id': 1, 'titulo': 'cerrada', 'estado': 'Cerrada'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['alertas_abiertas'] == 1
        assert len(ctx['alertas']) == 1
        assert ctx['alertas'][0]['titulo'] == 'abierta'

    def test_evidencias_pendientes_counts_only_pendiente(self):
        mlm._insert('legal_evidence', {'empresa_id': 1, 'requirement_id': 1, 'nombre': 'a', 'estado_aprobacion': 'Pendiente'})
        mlm._insert('legal_evidence', {'empresa_id': 1, 'requirement_id': 1, 'nombre': 'b', 'estado_aprobacion': 'Aprobado'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['evidencias_pendientes'] == 1

    def test_areas_group_and_compute_pct(self):
        mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'a', 'ambito': 'Ambiental', 'estado': 'cumple'})
        mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'b', 'ambito': 'Ambiental', 'estado': 'no_cumple'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['areas'] == [{'area': 'Ambiental', 'requisitos': 2, 'pct': 50}]

    def test_sedes_group_with_provincia_and_pct(self):
        site_id = mlm._insert('legal_sites', {'empresa_id': 1, 'nombre': 'Planta A', 'jurisdiccion': 'Cordoba'})
        mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'a', 'site_id': site_id, 'estado': 'cumple'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['sedes'] == [{'nombre': 'Planta A', 'provincia': 'Cordoba', 'requisitos': 1, 'pct': 100}]

    def test_alert_resolves_sede_through_requirement_link(self):
        site_id = mlm._insert('legal_sites', {'empresa_id': 1, 'nombre': 'Planta A'})
        req_id = mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'norma', 'site_id': site_id})
        mlm._insert('legal_alerts', {
            'empresa_id': 1, 'requirement_id': req_id, 'titulo': 'alerta', 'prioridad': 'alta',
            'estado': 'Nueva', 'atendida_por': '',
        })
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['alertas'][0]['sede'] == 'Planta A'
        assert ctx['alertas'][0]['prioridad'] == 'Alta'
        assert ctx['alertas'][0]['prioridad_code'] == 'alta'
        assert ctx['alertas'][0]['responsable'] == 'Sin asignar'

    def test_alert_without_requirement_shows_dash_sede(self):
        mlm._insert('legal_alerts', {'empresa_id': 1, 'requirement_id': None, 'titulo': 'alerta suelta', 'estado': 'Nueva'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['alertas'][0]['sede'] == '-'

    def test_auditorias_exclude_cerrada(self):
        mlm._insert('legal_audits', {'empresa_id': 1, 'fecha': '2026-08-01', 'resultado': 'programada'})
        mlm._insert('legal_audits', {'empresa_id': 1, 'fecha': '2026-01-01', 'resultado': 'cerrada'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert len(ctx['auditorias']) == 1
        assert ctx['auditorias'][0]['estado'] == 'Programada'

    def test_hallazgos_include_no_cumple_and_evidence_issues(self):
        req_id = mlm._insert('legal_requirements', {
            'empresa_id': 1, 'titulo': 'Norma X', 'tipo_norma': 'Ley', 'numero': '123', 'estado': 'no_cumple',
        })
        mlm._insert('legal_evidence', {'empresa_id': 1, 'requirement_id': req_id, 'nombre': 'doc.pdf', 'estado_aprobacion': 'Rechazado'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert any('Norma X' in h for h in ctx['hallazgos'])
        assert any('doc.pdf' in h and 'rechazado' in h for h in ctx['hallazgos'])

    def test_conclusion_tiers(self):
        for estado in ('no_cumple',) * 6 + ('cumple',) * 4:
            mlm._insert('legal_requirements', {'empresa_id': 1, 'titulo': 'x', 'estado': estado})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert 'crítico' in ctx['conclusion']

        mlm._insert('legal_requirements', {'empresa_id': 2, 'titulo': 'x', 'estado': 'cumple'})
        ctx2 = mlm.construir_contexto_reporte_legal_matrix(2)
        assert 'sólido' in ctx2['conclusion']

    def test_data_from_other_company_does_not_leak(self):
        mlm._insert('legal_requirements', {'empresa_id': 2, 'titulo': 'de otra empresa', 'estado': 'no_cumple'})
        ctx = mlm.construir_contexto_reporte_legal_matrix(1)
        assert ctx['total_requisitos'] == 0


class TestIsMatrixAdmin:
    def _patch_storage_user(self, monkeypatch, values: dict):
        monkeypatch.setattr(type(mlm.app.storage), 'user', property(lambda self: values))

    def test_platform_admin_is_matrix_admin(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'admin'})
        assert mlm._is_matrix_admin() is True

    def test_empresa_admin_local_role_is_matrix_admin(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_ADMIN'})
        assert mlm._is_matrix_admin() is True

    def test_plain_empresa_user_is_not_matrix_admin(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER'})
        assert mlm._is_matrix_admin() is False


class TestMatrixRoles:
    """RBAC real de Matriz Legal (audit finding #4): antes del 2026-08-21 el
    selector de rol en la UI (Admin/Editor/Aprobador/Lector) era puro estado
    de JS, sin ningun endpoint que lo verificara -- cualquier usuario
    autenticado de la empresa tenia permiso real de escritura sin importar
    que rol mostrara la pantalla. Estos tests cubren el modelo real que lo
    reemplaza: legal_matrix_user_roles + _require_matrix_permission()."""

    def _patch_storage_user(self, monkeypatch, values: dict):
        monkeypatch.setattr(type(mlm.app.storage), 'user', property(lambda self: values))

    def test_unassigned_user_defaults_to_editor(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER'})
        # nadie asigno un rol todavia -- el default tiene que ser 'editor',
        # no 'reader', para no sacarle de golpe a un usuario existente una
        # capacidad que ya tenia antes de que este control existiera.
        assert mlm.obtener_legal_matrix_role(user_id=99, empresa_id=1) == 'editor'

    def test_assigned_role_is_persisted_and_read_back(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER'})
        ok, _msg = mlm.asignar_legal_matrix_role(99, 1, 'reader', assigned_by='tester')
        assert ok is True
        assert mlm.obtener_legal_matrix_role(user_id=99, empresa_id=1) == 'reader'

    def test_invalid_role_is_rejected(self):
        ok, msg = mlm.asignar_legal_matrix_role(99, 1, 'superuser')
        assert ok is False
        assert 'invalido' in msg.lower()

    def test_empresa_admin_always_resolves_to_admin_regardless_of_stored_role(self, monkeypatch):
        # un EMPRESA_ADMIN no se puede autobloquear via una fila vieja/incorrecta
        # en legal_matrix_user_roles -- _is_matrix_admin() manda siempre.
        mlm.asignar_legal_matrix_role(7, 1, 'reader')
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_ADMIN', 'local_user_id': 7})
        assert mlm.obtener_legal_matrix_role(user_id=7, empresa_id=1) == 'admin'

    def test_reader_cannot_create(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER', 'local_user_id': 5})
        mlm.asignar_legal_matrix_role(5, 1, 'reader')
        with pytest.raises(mlm.HTTPException) as exc:
            mlm._require_matrix_permission(1, 'create')
        assert exc.value.status_code == 403

    def test_editor_can_create_but_not_delete(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER', 'local_user_id': 6})
        mlm.asignar_legal_matrix_role(6, 1, 'editor')
        mlm._require_matrix_permission(1, 'create')  # no debe levantar
        with pytest.raises(mlm.HTTPException) as exc:
            mlm._require_matrix_permission(1, 'delete')
        assert exc.value.status_code == 403

    def test_approver_can_approve_but_not_edit(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'empresa', 'local_user_role': 'EMPRESA_USER', 'local_user_id': 4})
        mlm.asignar_legal_matrix_role(4, 1, 'approver')
        mlm._require_matrix_permission(1, 'approve')  # no debe levantar
        with pytest.raises(mlm.HTTPException) as exc:
            mlm._require_matrix_permission(1, 'edit')
        assert exc.value.status_code == 403

    def test_admin_can_do_everything(self, monkeypatch):
        self._patch_storage_user(monkeypatch, {'role': 'admin'})
        for action in ('create', 'edit', 'delete', 'approve'):
            mlm._require_matrix_permission(1, action)  # no debe levantar ninguna


@pytest.fixture(scope='module')
def legal_matrix_client():
    """Registra las rutas reales de Matriz Legal una sola vez para todo el
    modulo de tests y devuelve un TestClient para pegarles directo -- a
    diferencia de TestMatrixRoles arriba (que llama _require_matrix_permission
    a mano), esto prueba que el endpoint HTTP de verdad la invoca."""
    from fastapi.testclient import TestClient
    from nicegui import app as nicegui_app
    from nicegui import ui as nicegui_ui

    stub_deps = {
        'ensure_platform_access': lambda: True,
        'shell': lambda *a, **k: None,
        'company_options': lambda: {},
        'current_selection': lambda: (None, None),
        'set_selection': lambda *a, **k: None,
        'obtener_empresa_detalle': lambda *a, **k: {},
    }
    mlm.register_legal_matrix_module(nicegui_ui, stub_deps)
    return TestClient(nicegui_app)


class TestMatrixRoleEndpoints:
    """Mismo hallazgo que TestMatrixRoles, pero pegandole al endpoint HTTP
    real en vez de llamar _require_matrix_permission directamente -- es la
    prueba que el segundo informe de auditoria (24/08) pidio explicitamente:
    'un test que llame a cada endpoint autenticado como cada rol real y
    confirme que un rol sin permiso recibe 403, no 200'. Cubre los seis
    endpoints de escritura de Matriz Legal contra los tres roles no-admin."""

    def _session(self, monkeypatch, user_id: int, empresa_id: int = 1):
        monkeypatch.setattr(
            type(mlm.app.storage), 'user',
            property(lambda self: {
                'platform_auth': True, 'role': 'empresa',
                'logged_empresa_id': empresa_id,
                'local_user_id': user_id, 'local_user_role': 'EMPRESA_USER',
            }),
        )

    def test_reader_gets_403_on_every_write_endpoint(self, legal_matrix_client, monkeypatch):
        self._session(monkeypatch, user_id=10)
        mlm.asignar_legal_matrix_role(10, 1, 'reader')
        c = legal_matrix_client
        assert c.post('/api/legal-matrix/1/requirements', json={'title': 'x'}).status_code == 403
        assert c.put('/api/legal-matrix/1/requirements/999', json={'title': 'x'}).status_code == 403
        assert c.delete('/api/legal-matrix/1/requirements/999').status_code == 403
        assert c.post('/api/legal-matrix/1/requirements/delete-bulk', json={'ids': [999]}).status_code == 403
        assert c.post('/api/legal-matrix/1/sites', json={'name': 'x'}).status_code == 403
        assert c.post('/api/legal-matrix/1/audits', json={'date': '2026-01-01'}).status_code == 403
        assert c.post('/api/legal-matrix/1/evidence', json={'requirementId': 1, 'name': 'x'}).status_code == 403
        assert c.post('/api/legal-matrix/1/evidence/999/approve').status_code == 403
        assert c.post('/api/legal-matrix/1/alerts/999/resolve').status_code == 403

    def test_editor_can_create_but_not_delete_or_approve(self, legal_matrix_client, monkeypatch):
        self._session(monkeypatch, user_id=11)
        mlm.asignar_legal_matrix_role(11, 1, 'editor')
        c = legal_matrix_client
        created = c.post('/api/legal-matrix/1/requirements', json={'title': 'norma de test'})
        assert created.status_code == 200
        req_id = created.json()['id']
        assert c.put(f'/api/legal-matrix/1/requirements/{req_id}', json={'title': 'editada'}).status_code == 200
        assert c.delete(f'/api/legal-matrix/1/requirements/{req_id}').status_code == 403
        assert c.post('/api/legal-matrix/1/evidence/999/approve').status_code == 403

    def test_approver_can_approve_but_not_create(self, legal_matrix_client, monkeypatch):
        self._session(monkeypatch, user_id=12)
        mlm.asignar_legal_matrix_role(12, 1, 'approver')
        c = legal_matrix_client
        assert c.post('/api/legal-matrix/1/requirements', json={'title': 'x'}).status_code == 403
        # id inexistente -> el UPDATE no toca filas pero igual pasa el check de permiso (200)
        assert c.post('/api/legal-matrix/1/evidence/999/approve').status_code == 200

    def test_unassigned_user_keeps_editor_behavior_by_default(self, legal_matrix_client, monkeypatch):
        # nadie le asigno rol a este usuario -- tiene que poder seguir
        # creando/editando como podia antes de que este control existiera.
        self._session(monkeypatch, user_id=13)
        c = legal_matrix_client
        assert c.post('/api/legal-matrix/1/requirements', json={'title': 'x'}).status_code == 200
        assert c.delete('/api/legal-matrix/1/requirements/999').status_code == 403
