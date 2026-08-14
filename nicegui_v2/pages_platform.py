from __future__ import annotations
import time
from datetime import datetime

import httpx
from sqlalchemy import select

from ideas_utils import ideus_wordmark_html


AUTH_API_BASE_URL = 'http://127.0.0.1:8000/api'

# Fase 1 (2026-08-10): rate limiting basico de login por usuario, en memoria del proceso.
# No sustituye un rate limit por IP a nivel infraestructura, pero frena fuerza bruta contra
# un usuario conocido (p.ej. el admin de /plataforma) sin requerir nada externo.
_LOGIN_MAX_INTENTOS = 5
_LOGIN_VENTANA_SEG = 15 * 60
_LOGIN_BLOQUEO_SEG = 15 * 60
_login_failures: dict[str, list[float]] = {}


def _login_key(username: str) -> str:
    return (username or '').strip().lower()


def _login_locked(username: str) -> int:
    """Devuelve segundos restantes de bloqueo (0 si no esta bloqueado)."""
    key = _login_key(username)
    attempts = _login_failures.get(key) or []
    now = time.time()
    attempts = [t for t in attempts if now - t < _LOGIN_VENTANA_SEG]
    _login_failures[key] = attempts
    if len(attempts) < _LOGIN_MAX_INTENTOS:
        return 0
    remaining = _LOGIN_BLOQUEO_SEG - (now - attempts[-1])
    return max(0, int(remaining))


def _login_register_failure(username: str) -> None:
    key = _login_key(username)
    _login_failures.setdefault(key, []).append(time.time())


def _login_register_success(username: str) -> None:
    _login_failures.pop(_login_key(username), None)


def register_platform_pages(ui, app, deps: dict) -> None:
    public_shell = deps['public_shell']
    shell = deps['shell']
    ensure_platform_access = deps['ensure_platform_access']
    quick_card = deps['quick_card']
    obtener_empresas = deps['obtener_empresas']
    obtener_empresa_detalle = deps.get('obtener_empresa_detalle')
    diagnosis_rows = deps['diagnosis_rows']
    obtener_alertas_globales = deps['obtener_alertas_globales']
    verificar_usuario = deps['verificar_usuario']
    verificar_login_empresa = deps.get('verificar_login_empresa')
    guardar_token_empresa = deps.get('guardar_token_empresa')
    verificar_token_empresa = deps.get('verificar_token_empresa')
    actualizar_password_empresa = deps.get('actualizar_password_empresa')
    provisionar_acceso_empresa = deps.get('provisionar_acceso_empresa')
    generar_token_seguro = deps.get('generar_token_seguro')
    enviar_correo_acceso = deps.get('enviar_correo_acceso')
    PLATFORM_USER = deps['PLATFORM_USER']
    PLATFORM_PASSWORD = deps['PLATFORM_PASSWORD']

    async def _provisionar_usuario_api(empresa_nombre: str, username: str, password: str) -> tuple[bool, str]:
        try:
            from app.db.session import AsyncSessionLocal
            from app.models.empresa import Empresa
            from app.models.usuario import Usuario
            from app.services.auth_service import hash_password, normalize_login_identifier
        except Exception:
            return False, 'No se pudo cargar el servicio de autenticacion.'

        email = normalize_login_identifier(username)
        empresa_nombre_clean = str(empresa_nombre or '').strip() or 'Empresa Demo'
        rol_empresa = 'empresa_admin'
        try:
            async with AsyncSessionLocal() as session:
                empresa_result = await session.execute(select(Empresa).where(Empresa.razon_social == empresa_nombre_clean))
                empresa = empresa_result.scalar_one_or_none()
                if not empresa:
                    empresa = Empresa(razon_social=empresa_nombre_clean, is_active=True)
                    session.add(empresa)
                    await session.flush()

                user_result = await session.execute(select(Usuario).where(Usuario.email == email))
                api_user = user_result.scalar_one_or_none()
                if api_user:
                    api_user.empresa_id = int(empresa.id)
                    api_user.password_hash = hash_password(password)
                    api_user.rol = rol_empresa
                else:
                    api_user = Usuario(
                        empresa_id=int(empresa.id),
                        email=email,
                        password_hash=hash_password(password),
                        rol=rol_empresa,
                    )
                    session.add(api_user)
                await session.commit()
                return True, email
        except Exception:
            return False, 'No se pudo guardar el usuario en la API.'

    def _emitir_link_acceso(correo: str, nombre_empresa: str) -> bool:
        if not (guardar_token_empresa and generar_token_seguro and enviar_correo_acceso):
            return False
        token = generar_token_seguro()
        ok = guardar_token_empresa(correo, token, expiracion_minutos=1440)
        if not ok:
            return False
        enviar_correo_acceso(correo, nombre_empresa, token)
        return True

    @ui.page('/olvide-password')
    def forgot_password_page() -> None:
        shell_container = public_shell('Recuperación')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Acceso seguro</div><h2>Recuperar contraseña</h2><p>Ingresa tu correo de contacto y te enviaremos un enlace para crear o recuperar tu contraseña.</p></div>')
            with ui.card().classes('ideas-public-card ideas-login-card'):
                ui.html(ideus_wordmark_html('login', extra_class='ideus-login-wordmark'))
                ui.html('<div class="ideas-login-title">Recuperación de acceso</div><div class="ideas-login-note">Si el correo existe, recibirás un enlace válido por 24 horas.</div>')
                correo_input = ui.input('Correo electrónico').classes('w-full').props('outlined type=email')

                def enviar_link() -> None:
                    correo = str(correo_input.value or '').strip()
                    if not correo:
                        ui.notify('Ingresa un correo válido.', type='warning')
                        return
                    ok = _emitir_link_acceso(correo, 'Empresa')
                    if ok:
                        ui.notify('Te enviamos un enlace de acceso a tu correo.', type='positive')
                    else:
                        ui.notify('Si el correo está registrado, recibirá el enlace en breve.', type='positive')

                with ui.row().classes('w-full justify-between items-center mt-2'):
                    ui.button('Volver al login', icon='arrow_back', on_click=lambda: ui.navigate.to('/plataforma')).props('flat')
                    ui.button('Enviar enlace', icon='mail', on_click=enviar_link).props('unelevated color=primary')

    @ui.page('/crear-password/{token}')
    def create_password_page(token: str) -> None:
        shell_container = public_shell('Crear contraseña')
        with shell_container:
            empresa_id = verificar_token_empresa(token) if callable(verificar_token_empresa) else None
            if not empresa_id:
                with ui.card().classes('ideas-public-card ideas-login-card'):
                    ui.html('<div class="ideas-login-title">Enlace inválido</div><div class="ideas-login-note">El enlace no existe o ya expiró. Solicita uno nuevo desde "¿Olvidaste tu contraseña?"</div>')
                    ui.button('Ir al login', icon='login', on_click=lambda: ui.navigate.to('/plataforma')).props('unelevated color=primary')
                return

            with ui.card().classes('ideas-public-card ideas-login-card'):
                ui.html(ideus_wordmark_html('login', extra_class='ideus-login-wordmark'))
                ui.html('<div class="ideas-login-title">Crear acceso</div><div class="ideas-login-note">Define usuario y contraseña para ingresar a la plataforma.</div>')
                username_input = ui.input('Usuario').classes('w-full').props('outlined')
                password_input = ui.input('Nueva contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined')
                confirm_input = ui.input('Confirmar contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined')

                async def guardar_password() -> None:
                    user_name = str(username_input.value or '').strip()
                    p1 = str(password_input.value or '').strip()
                    p2 = str(confirm_input.value or '').strip()
                    if not user_name:
                        ui.notify('El usuario no puede estar vacío.', type='warning')
                        return
                    if not p1:
                        ui.notify('La contraseña no puede estar vacía.', type='warning')
                        return
                    if p1 != p2:
                        ui.notify('Las contraseñas no coinciden.', type='negative')
                        return
                    ok_local = False
                    mensaje = 'No se pudo actualizar el acceso.'
                    if callable(provisionar_acceso_empresa):
                        ok_local, mensaje = provisionar_acceso_empresa(int(empresa_id), user_name, p1)
                    elif callable(actualizar_password_empresa):
                        ok_local = actualizar_password_empresa(int(empresa_id), p1)
                    if not ok_local:
                        ui.notify(mensaje, type='negative')
                        return

                    empresa_nombre = f'Empresa {int(empresa_id)}'
                    if callable(obtener_empresa_detalle):
                        detalle = obtener_empresa_detalle(int(empresa_id))
                        if isinstance(detalle, dict):
                            empresa_nombre = str(detalle.get('razon_social') or empresa_nombre).strip()

                    ok_api, user_email = await _provisionar_usuario_api(empresa_nombre, user_name, p1)
                    if not ok_api:
                        ui.notify('Se guardo acceso local, pero fallo alta en API. Contacta a soporte.', type='negative')
                        return

                    ui.notify(f'Usuario y contraseña creados correctamente. Ingresa con {user_email}.', type='positive')
                    ui.navigate.to('/plataforma')

                with ui.row().classes('w-full justify-end mt-2'):
                    ui.button('Guardar acceso', icon='save', on_click=guardar_password).props('unelevated color=primary')

    @ui.page('/plataforma')
    def platform_login_page() -> None:
        # Evitar clear(): en Windows puede fallar con WinError 32 por lock del archivo de storage.
        for key in [
            'jwt_token', 'auth_source', 'role', 'api_role', 'logged_empresa_id',
            'logged_empresa_nombre', 'management_company_id', 'current_empresa_id',
            'session_user_key', 'permisos', 'last_activity_at', 'local_user_id', 'local_user_role',
        ]:
            app.storage.user.pop(key, None)
        app.storage.user['platform_auth'] = False
        shell_container = public_shell('Acceso')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Acceso seguro</div><h2>Portal de gestión</h2><p>Ingresa con tu usuario y contraseña para continuar a tu espacio de trabajo.</p></div>')
            with ui.card().classes('ideas-public-card ideas-login-card'):
                ui.html(ideus_wordmark_html('login', extra_class='ideus-login-wordmark'))
                ui.html('<div class="ideas-login-title">Iniciar sesión</div><div class="ideas-login-note">Acceso para usuarios autorizados. Una vez autenticado, podrás operar según tus permisos.</div>')
                usuario = ui.input('Usuario').classes('w-full').props('outlined')
                password = ui.input('Contrasena', password=True, password_toggle_button=True).classes('w-full').props('outlined')

                async def do_login() -> None:
                    login_button.props('loading disable')
                    try:
                        await _do_login_body()
                    finally:
                        login_button.props(remove='loading disable')

                async def _do_login_body() -> None:
                    user = (usuario.value or '').strip()
                    pwd = (password.value or '').strip()
                    if not user or not pwd:
                        ui.notify('Ingresa usuario y contrasena.', type='warning')
                        return

                    bloqueo_seg = _login_locked(user)
                    if bloqueo_seg > 0:
                        minutos = max(1, bloqueo_seg // 60)
                        ui.notify(f'Demasiados intentos fallidos. Intenta de nuevo en {minutos} minuto(s).', type='negative')
                        return

                    set_selection = deps.get('set_selection')
                    company_name_by_id = {int(company_id): str(name or '').strip() for company_id, name in obtener_empresas()}
                    local_user_match = None
                    if callable(verificar_usuario):
                        local_user_match = verificar_usuario(user, pwd)
                        if not local_user_match and '@' in user:
                            local_user_match = verificar_usuario(user.split('@', 1)[0], pwd)
                    if not isinstance(local_user_match, dict):
                        _login_register_failure(user)
                    else:
                        _login_register_success(user)

                    def login_local() -> bool:
                        if not isinstance(local_user_match, dict):
                            return False
                        # 2026-08-14: dispara el splash de marca (~3s) que consume
                        # shell() una sola vez, en la primera pagina que se renderiza
                        # despues de un login exitoso -- no en cada navegacion.
                        app.storage.user['show_splash'] = True
                        local_role = str(local_user_match.get('rol') or '').strip().upper()
                        local_company_id = local_user_match.get('empresa_id')
                        try:
                            local_company_id = int(local_company_id) if local_company_id else None
                        except Exception:
                            local_company_id = None
                        role = 'admin' if local_role == 'IDEAS_ADMIN' else 'empresa'
                        app.storage.user['platform_auth'] = True
                        app.storage.user['jwt_token'] = ''
                        app.storage.user['auth_source'] = 'local'
                        app.storage.user['last_activity_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        app.storage.user['api_user_id'] = None
                        app.storage.user['api_role'] = ''
                        app.storage.user['permisos'] = str(local_user_match.get('permisos') or 'ALL').strip()
                        app.storage.user['role'] = role
                        app.storage.user['session_user_key'] = str(local_user_match.get('username') or user).strip().lower()
                        app.storage.user['session_user_name'] = str(local_user_match.get('username') or user).strip()
                        app.storage.user['local_user_id'] = int(local_user_match.get('id')) if local_user_match.get('id') else None
                        app.storage.user['local_user_role'] = local_role

                        if role == 'admin':
                            app.storage.user['logged_empresa_id'] = None
                            app.storage.user['logged_empresa_nombre'] = ''
                            ui.notify('Acceso concedido (local).', type='positive')
                            ui.navigate.to('/dashboard')
                            return True

                        resolved_empresa_id = local_company_id if local_company_id in company_name_by_id else None
                        if not resolved_empresa_id and len(company_name_by_id) == 1:
                            resolved_empresa_id = next(iter(company_name_by_id.keys()))
                        app.storage.user['logged_empresa_id'] = resolved_empresa_id
                        app.storage.user['logged_empresa_nombre'] = company_name_by_id.get(resolved_empresa_id, '')
                        if callable(set_selection) and resolved_empresa_id:
                            set_selection(resolved_empresa_id)
                        ui.notify('Acceso concedido (local).', type='positive')
                        ui.navigate.to('/sistema-gestion')
                        return True

                    try:
                        async with httpx.AsyncClient(timeout=12.0) as client:
                            login_response = await client.post(
                                f'{AUTH_API_BASE_URL}/auth/login',
                                data={'username': user, 'password': pwd},
                                headers={'Content-Type': 'application/x-www-form-urlencoded'},
                            )
                            if login_response.status_code == 422:
                                login_response = await client.post(
                                    f'{AUTH_API_BASE_URL}/auth/login',
                                    json={'email': user, 'password': pwd},
                            )
                            if login_response.status_code == 401:
                                if login_local():
                                    return
                                ui.notify('Credenciales invalidas', type='negative')
                                return
                            login_response.raise_for_status()
                            token_payload = login_response.json()
                            access_token = str(token_payload.get('access_token') or '').strip()
                            if not access_token:
                                ui.notify('La API no devolvio un token de acceso.', type='negative')
                                return

                            me_response = await client.get(
                                f'{AUTH_API_BASE_URL}/auth/me',
                                headers={'Authorization': f'Bearer {access_token}'},
                            )
                            me_response.raise_for_status()
                            session_payload = me_response.json()
                    except httpx.HTTPStatusError:
                        ui.notify('Credenciales invalidas', type='negative')
                        return
                    except httpx.RequestError:
                        if login_local():
                            return
                        ui.notify('No se pudo conectar con el servicio de autenticacion.', type='negative')
                        return
                    except Exception:
                        ui.notify('No se pudo iniciar sesion.', type='negative')
                        return

                    _login_register_success(user)
                    app.storage.user['show_splash'] = True
                    empresa_id = session_payload.get('empresa_id')
                    try:
                        empresa_id_int = int(empresa_id) if empresa_id else None
                    except Exception:
                        empresa_id_int = None

                    api_rol = str(session_payload.get('rol') or '').strip()
                    internal_roles = {'ideas_admin', 'ideas_superadmin', 'superadmin'}
                    role = 'admin' if api_rol.lower() in internal_roles else 'empresa'
                    email = str(session_payload.get('email') or user).strip()

                    app.storage.user['platform_auth'] = True
                    app.storage.user['jwt_token'] = access_token
                    app.storage.user['auth_source'] = 'api'
                    app.storage.user['last_activity_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    app.storage.user['api_user_id'] = session_payload.get('user_id')
                    app.storage.user['api_role'] = api_rol
                    app.storage.user['permisos'] = 'ALL'
                    app.storage.user['role'] = role
                    app.storage.user['session_user_key'] = email.lower()
                    app.storage.user['session_user_name'] = email
                    app.storage.user['local_user_id'] = int(local_user_match.get('id')) if isinstance(local_user_match, dict) and local_user_match.get('id') else None
                    app.storage.user['local_user_role'] = str(local_user_match.get('rol') or '') if isinstance(local_user_match, dict) else ''
                    if isinstance(local_user_match, dict) and str(local_user_match.get('permisos') or '').strip():
                        app.storage.user['permisos'] = str(local_user_match.get('permisos') or 'ALL').strip()

                    if role == 'admin':
                        app.storage.user['logged_empresa_id'] = None
                        app.storage.user['logged_empresa_nombre'] = ''
                        ui.notify('Acceso concedido.', type='positive')
                        ui.navigate.to('/dashboard')
                        return

                    resolved_empresa_id = empresa_id_int if empresa_id_int in company_name_by_id else None
                    if not resolved_empresa_id and isinstance(local_user_match, dict):
                        local_empresa_id = local_user_match.get('empresa_id')
                        try:
                            local_empresa_id = int(local_empresa_id) if local_empresa_id else None
                        except Exception:
                            local_empresa_id = None
                        if local_empresa_id in company_name_by_id:
                            resolved_empresa_id = local_empresa_id
                    if not resolved_empresa_id and len(company_name_by_id) == 1:
                        resolved_empresa_id = next(iter(company_name_by_id.keys()))

                    app.storage.user['logged_empresa_id'] = resolved_empresa_id
                    app.storage.user['logged_empresa_nombre'] = company_name_by_id.get(resolved_empresa_id, '')
                    if callable(set_selection) and resolved_empresa_id:
                        set_selection(resolved_empresa_id)
                    ui.notify('Acceso concedido.', type='positive')
                    ui.navigate.to('/sistema-gestion')
                    return

                with ui.row().classes('w-full justify-between items-center mt-2'):
                    ui.button('Volver al sitio', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat')
                    login_button = ui.button('Ingresar', icon='login', on_click=do_login).props('unelevated color=primary')
                with ui.row().classes('w-full justify-end'):
                    ui.link('¿Olvidaste tu contraseña?', '/olvide-password').classes('text-sm text-slate-500 hover:text-primary')

    @ui.page('/dashboard')
    def home_page() -> None:
        if not ensure_platform_access():
            return
        api_role = str(app.storage.user.get('api_role') or '').strip().lower()
        local_role = str(app.storage.user.get('local_user_role') or '').strip().upper()
        is_api_admin = api_role in {'ideas_admin', 'ideas_superadmin', 'superadmin'}
        is_local_admin = (
            str(app.storage.user.get('auth_source') or '').strip().lower() == 'local'
            and local_role == 'IDEAS_ADMIN'
        )
        if app.storage.user.get('role') != 'admin' or not (is_api_admin or is_local_admin):
            ui.notify('Acceso denegado.', type='negative')
            ui.navigate.to('/sistema-gestion')
            return

        shell_container = shell('Dashboard General')
        empresas = obtener_empresas()
        alertas = obtener_alertas_globales()
        rol_actual = str(app.storage.user.get('role') or '')
        total_empresas = len(empresas)
        total_alertas = len(alertas)
        alertas_vencidas = len([item for item in alertas if item.get('estado') == 'Vencida'])
        alertas_proximas = len([item for item in alertas if item.get('estado') == 'Proxima'])
        alertas_rows = alertas[:12]

        with shell_container:
            with ui.column().classes('w-full gap-6'):
                ui.html(
                    f'''
                    <div class="ideas-workspace-banner w-full" style="position:relative;overflow:hidden;">
                        <div style="position:absolute;inset:auto -120px -120px auto;width:320px;height:320px;border-radius:999px;background:radial-gradient(circle, rgba(255,255,255,.16), rgba(255,255,255,0) 68%);"></div>
                        <div style="display:flex;justify-content:space-between;gap:24px;align-items:flex-start;position:relative;">
                            <div>
                                <div class="eyebrow">CENTRO DE COMANDO IDEAS</div>
                                <div class="headline">Dashboard General Interno</div>
                                <div class="support">
                                    Vista tactica para operar el SaaS con foco en pendientes reales de clientes, accesos clave y seguimiento de alertas.
                                    Menos ruido, más acción consultiva.
                                </div>
                            </div>
                            <div style="min-width:220px;padding:18px 20px;border-radius:22px;background:rgba(255,255,255,.10);border:1px solid rgba(255,255,255,.14);backdrop-filter:blur(10px);">
                                <div style="font-size:.75rem;letter-spacing:.14em;text-transform:uppercase;color:rgba(255,255,255,.68);font-weight:800;">Sesion activa</div>
                                <div style="margin-top:8px;font-size:1.05rem;font-weight:800;color:#ffffff;">{rol_actual or 'IDEAS_ADMIN'}</div>
                                <div style="margin-top:10px;color:rgba(255,255,255,.82);line-height:1.6;">Alertas abiertas: {total_alertas}</div>
                            </div>
                        </div>
                    </div>
                    '''
                )

                ui.html(
                    f'''
                    <div class="ideas-grid-3" style="margin-top:24px;">
                        {quick_card('TOTAL EMPRESAS', str(total_empresas), 'Clientes registrados en la base maestra de la consultora.')}
                        {quick_card('ALERTAS ABIERTAS', str(total_alertas), 'Pendientes consolidados en toda la cartera visible.')}
                        {quick_card('VENCIDAS / PROXIMAS', f'{alertas_vencidas} / {alertas_proximas}', 'Prioriza primero lo vencido y luego lo proximo a vencer.')}
                    </div>
                    '''
                )

                with ui.row().classes('w-full items-center justify-between gap-4').style('margin-top:8px;'):
                    with ui.column().classes('gap-1'):
                        ui.label('Accesos estratégicos').classes('ideas-section-title')
                        ui.label('Entradas rápidas para la operación diaria del equipo IDEAS.').classes('ideas-section-note')
                    ui.badge('Modo interno', color='primary').classes('px-3 py-2')

                home_shortcuts = [
                    ('Empresas', 'business', '/empresas'),
                    ('Diagnóstico', 'assignment_add', '/diagnostico'),
                    ('Workspace Ejecutivo', 'dashboard_customize', '/sistema-gestion'),
                    ('Usuarios y Permisos', 'manage_accounts', '/sistema-gestion/usuarios'),
                ]
                with ui.tabs().classes('w-full mt-1 ideas-panel p-2 rounded-[24px]'):
                    home_shortcut_tabs = {
                        title: ui.tab(title, icon=icon).props('no-caps').classes('text-slate-700')
                        for title, icon, _route in home_shortcuts
                    }

                def _open_home_shortcut(title: str) -> None:
                    for item_title, _icon, route in home_shortcuts:
                        if item_title == title:
                            ui.navigate.to(route)
                            return

                for title, tab_obj in home_shortcut_tabs.items():
                    tab_obj.on('click', lambda _e, t=title: _open_home_shortcut(t))

                with ui.card().classes('ideas-panel w-full').style('margin-top:24px;'):
                    ui.label('Alertas y Actividades Pendientes').classes('ideas-section-title')
                    ui.label('Panel tactico consolidado para priorizar vencimientos, seguimiento 8D y proximos compromisos de clientes.').classes('ideas-section-note')
                    if not alertas_rows:
                        with ui.column().classes('w-full items-center justify-center').style('padding:28px 0;'):
                            ui.icon('task_alt').classes('text-4xl text-emerald-600')
                            ui.label('No hay alertas abiertas por el momento.').classes('text-lg font-semibold text-slate-800 mt-2')
                            ui.label('Cuando existan acciones pendientes o vencidas en la cartera, aparecerán aquí.').classes('ideas-section-note')
                    else:
                        columns = [
                            {'name': 'empresa', 'label': 'Empresa', 'field': 'empresa', 'align': 'left'},
                            {'name': 'tipo', 'label': 'Tipo', 'field': 'tipo', 'align': 'left'},
                            {'name': 'detalle', 'label': 'Detalle', 'field': 'detalle', 'align': 'left'},
                            {'name': 'estado', 'label': 'Estado', 'field': 'estado', 'align': 'center'},
                            {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'center'},
                        ]
                        table = ui.table(columns=columns, rows=alertas_rows, row_key='detalle', pagination={'rowsPerPage': 10}).classes('w-full ideas-table mt-4')
                        table.add_slot('body-cell-estado', '''<q-td :props="props"><q-badge :color="props.value === 'Vencida' ? 'negative' : (props.value === 'Proxima' ? 'warning' : 'grey-7')" rounded>{{ props.value }}</q-badge></q-td>''')
