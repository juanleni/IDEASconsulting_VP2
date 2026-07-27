"""Login real del prototipo mobile, reutilizando la tabla `usuarios` que ya
usa la plataforma principal (misma función `verificar_usuario`, mismo hash
pbkdf2_sha256 — ver nicegui_v2/core_data.py y el fallback local de
nicegui_v2/pages_platform.py:/plataforma).

No se crea un sistema de usuarios paralelo. Se replican las mismas claves de
`app.storage.user` que usa la plataforma principal (`platform_auth`, `role`,
`logged_empresa_id`, `local_user_role`, `local_user_id`, `session_user_key`,
`session_user_name`) para que las funciones reutilizadas de
modules_legal_matrix (`_log`, que lee `session_user_name`) sigan andando
igual, sin parches.

Modelo de cuentas (ver SPEC_mobile_legal_matrix_v2.md §1.2):
- Cliente, ligado a una sola empresa (`empresa_id` obligatorio): roles
  EMPRESA_ADMIN (editor) / EMPRESA_USER (lector, solo lectura en mobile).
- IDEAS staff (`rol == 'IDEAS_ADMIN'`), acceso transversal: fuera de alcance
  para esta versión del mobile (spec §1.2) — si loguea, se le muestra un
  aviso en vez de armarle una vista propia.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from nicegui import app

_ROOT = Path(__file__).resolve().parents[1]
_NICEGUI_V2_DIR = _ROOT / 'nicegui_v2'
os.chdir(_ROOT)  # core_data usa rutas relativas ("ideas.db"); idempotente si data.py ya corrió esto
for _p in (_ROOT, _NICEGUI_V2_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from core_data import obtener_empresas, verificar_usuario  # noqa: E402  (reutilizado, mismo login local que la plataforma)

SESSION_KEYS = (
    'platform_auth', 'role', 'logged_empresa_id', 'logged_empresa_nombre',
    'local_user_role', 'local_user_id', 'session_user_key', 'session_user_name',
)


def login(usuario: str, password: str) -> tuple[bool, str]:
    usuario = (usuario or '').strip()
    password = (password or '').strip()
    if not usuario or not password:
        return False, 'Ingresá usuario y contraseña.'

    match = verificar_usuario(usuario, password)
    if not match and '@' in usuario:
        match = verificar_usuario(usuario.split('@', 1)[0], password)
    if not match:
        return False, 'Usuario o contraseña incorrectos.'

    rol = str(match.get('rol') or '').strip().upper()
    if rol == 'IDEAS_ADMIN':
        return False, (
            'Tu usuario es de staff IDEAS (acceso a todas las empresas). '
            'Por ahora esta app mobile es solo para usuarios de una empresa cliente — '
            'usá la plataforma de escritorio.'
        )

    empresa_id = match.get('empresa_id')
    try:
        empresa_id = int(empresa_id) if empresa_id else None
    except (TypeError, ValueError):
        empresa_id = None
    if not empresa_id:
        return False, 'Tu usuario no tiene una empresa asignada. Contactá a IDEAS.'

    nombre_empresa = dict(
        (int(eid), str(nombre or '').strip()) for eid, nombre in obtener_empresas()
    ).get(empresa_id, '')

    app.storage.user['platform_auth'] = True
    app.storage.user['role'] = 'empresa'
    app.storage.user['logged_empresa_id'] = empresa_id
    app.storage.user['logged_empresa_nombre'] = nombre_empresa
    app.storage.user['local_user_role'] = rol
    app.storage.user['local_user_id'] = int(match.get('id'))
    app.storage.user['session_user_key'] = str(match.get('username') or usuario).strip().lower()
    app.storage.user['session_user_name'] = str(match.get('username') or usuario).strip()
    return True, 'Acceso concedido.'


def logout() -> None:
    for key in SESSION_KEYS:
        app.storage.user.pop(key, None)


def esta_autenticado() -> bool:
    return bool(app.storage.user.get('platform_auth')) and bool(app.storage.user.get('logged_empresa_id'))


def empresa_id_sesion() -> int | None:
    value = app.storage.user.get('logged_empresa_id')
    try:
        return int(value) if value else None
    except (TypeError, ValueError):
        return None


def nombre_usuario_sesion() -> str:
    return str(app.storage.user.get('session_user_name') or '')


def rol_sesion() -> str:
    return str(app.storage.user.get('local_user_role') or '').strip().upper()


def puede_editar() -> bool:
    """EMPRESA_ADMIN = editor. EMPRESA_USER = lector, solo lectura en mobile (spec §1.2)."""
    return rol_sesion() == 'EMPRESA_ADMIN'
