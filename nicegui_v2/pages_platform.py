from __future__ import annotations


def register_platform_pages(ui, app, deps: dict) -> None:
    public_shell = deps['public_shell']
    shell = deps['shell']
    ensure_platform_access = deps['ensure_platform_access']
    quick_card = deps['quick_card']
    obtener_empresas = deps['obtener_empresas']
    diagnosis_rows = deps['diagnosis_rows']
    obtener_alertas_globales = deps['obtener_alertas_globales']
    verificar_usuario = deps['verificar_usuario']
    verificar_login_empresa = deps.get('verificar_login_empresa')
    guardar_token_empresa = deps.get('guardar_token_empresa')
    verificar_token_empresa = deps.get('verificar_token_empresa')
    actualizar_password_empresa = deps.get('actualizar_password_empresa')
    generar_token_seguro = deps.get('generar_token_seguro')
    enviar_correo_acceso = deps.get('enviar_correo_acceso')
    PLATFORM_USER = deps['PLATFORM_USER']
    PLATFORM_PASSWORD = deps['PLATFORM_PASSWORD']

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
                ui.html('<div class="ideas-login-title">Crear nueva contraseña</div><div class="ideas-login-note">Define tu nueva contraseña para ingresar a la plataforma.</div>')
                password_input = ui.input('Nueva contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined')
                confirm_input = ui.input('Confirmar contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined')

                def guardar_password() -> None:
                    p1 = str(password_input.value or '').strip()
                    p2 = str(confirm_input.value or '').strip()
                    if not p1:
                        ui.notify('La contraseña no puede estar vacía.', type='warning')
                        return
                    if p1 != p2:
                        ui.notify('Las contraseñas no coinciden.', type='negative')
                        return
                    ok = actualizar_password_empresa(int(empresa_id), p1) if callable(actualizar_password_empresa) else False
                    if not ok:
                        ui.notify('No se pudo actualizar la contraseña.', type='negative')
                        return
                    ui.notify('Contraseña actualizada correctamente.', type='positive')
                    ui.navigate.to('/plataforma')

                with ui.row().classes('w-full justify-end mt-2'):
                    ui.button('Guardar contraseña', icon='save', on_click=guardar_password).props('unelevated color=primary')

    @ui.page('/plataforma')
    def platform_login_page() -> None:
        app.storage.user.clear()
        app.storage.user['platform_auth'] = False
        shell_container = public_shell('Acceso')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Acceso seguro</div><h2>Portal de gestión</h2><p>Ingresa con tu usuario y contraseña para continuar a tu espacio de trabajo.</p></div>')
            with ui.card().classes('ideas-public-card ideas-login-card'):
                ui.html('<div class="ideas-login-title">Iniciar sesión</div><div class="ideas-login-note">Acceso para usuarios autorizados. Una vez autenticado, podrás operar según tus permisos.</div>')
                usuario = ui.input('Usuario').classes('w-full').props('outlined')
                password = ui.input('Contrasena', password=True, password_toggle_button=True).classes('w-full').props('outlined')

                def do_login() -> None:
                    user = (usuario.value or '').strip()
                    pwd = (password.value or '').strip()
                    company_name_by_id = {int(company_id): str(name or '').strip() for company_id, name in obtener_empresas()}

                    if user == PLATFORM_USER and pwd == PLATFORM_PASSWORD:
                        app.storage.user['platform_auth'] = True
                        app.storage.user['role'] = 'admin'
                        app.storage.user['logged_empresa_id'] = None
                        app.storage.user['logged_empresa_nombre'] = ''
                        app.storage.user['permisos'] = 'ALL'
                        ui.notify('Acceso concedido.', type='positive')
                        ui.navigate.to('/dashboard')
                        return

                    set_selection = deps.get('set_selection')
                    found_user = verificar_usuario(user, pwd)
                    if found_user:
                        db_rol = str(found_user.get('rol') or '').strip()
                        empresa_id = found_user.get('empresa_id')
                        app.storage.user['platform_auth'] = True
                        app.storage.user['permisos'] = found_user.get('permisos', 'ALL')
                        if db_rol == 'IDEAS_ADMIN':
                            app.storage.user['role'] = 'admin'
                            app.storage.user['logged_empresa_id'] = None
                            app.storage.user['logged_empresa_nombre'] = ''
                            ui.notify('Acceso concedido.', type='positive')
                            ui.navigate.to('/dashboard')
                            return
                        empresa_id_int = int(empresa_id) if empresa_id else None
                        app.storage.user['role'] = 'empresa'
                        app.storage.user['logged_empresa_id'] = empresa_id_int
                        app.storage.user['logged_empresa_nombre'] = company_name_by_id.get(empresa_id_int, '')
                        if callable(set_selection) and empresa_id:
                            set_selection(int(empresa_id))
                        ui.notify('Acceso concedido.', type='positive')
                        ui.navigate.to('/sistema-gestion')
                        return

                    if callable(verificar_login_empresa):
                        found_empresa = verificar_login_empresa(user, pwd)
                        if found_empresa:
                            empresa_id_int = int(found_empresa[0])
                            empresa_nombre = str(found_empresa[1] or '').strip()
                            app.storage.user['platform_auth'] = True
                            app.storage.user['permisos'] = 'ALL'
                            app.storage.user['role'] = 'empresa'
                            app.storage.user['logged_empresa_id'] = empresa_id_int
                            app.storage.user['logged_empresa_nombre'] = empresa_nombre
                            if callable(set_selection):
                                set_selection(empresa_id_int)
                            ui.notify('Acceso concedido.', type='positive')
                            ui.navigate.to('/sistema-gestion')
                            return

                    ui.notify('Credenciales inválidas', type='negative')

                with ui.row().classes('w-full justify-between items-center mt-2'):
                    ui.button('Volver al sitio', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat')
                    ui.button('Ingresar', icon='login', on_click=do_login).props('unelevated color=primary')
                with ui.row().classes('w-full justify-end'):
                    ui.link('¿Olvidaste tu contraseña?', '/olvide-password').classes('text-sm text-slate-500 hover:text-primary')

    @ui.page('/dashboard')
    def home_page() -> None:
        if not ensure_platform_access():
            return
        if app.storage.user.get('role') != 'admin':
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

                with ui.grid(columns=4).classes('ideas-grid-3 w-full').style('margin-top:8px;'):
                    shortcut_1 = ui.card().classes('ideas-module-card cursor-pointer')
                    shortcut_1.on('click', lambda _e: ui.navigate.to('/empresas'))
                    with shortcut_1:
                        ui.html(
                            '''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">business</span></div>
                            </div>
                            <div>
                                <h3>Empresas</h3>
                                <p>Administra el portfolio de clientes, logos, branding y datos institucionales.</p>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-3'):
                            ui.button('Ingresar', icon='open_in_new', on_click=lambda: ui.navigate.to('/empresas')).props('flat color=primary')

                    shortcut_2 = ui.card().classes('ideas-module-card cursor-pointer')
                    shortcut_2.on('click', lambda _e: ui.navigate.to('/diagnostico'))
                    with shortcut_2:
                        ui.html(
                            '''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">assignment_add</span></div>
                            </div>
                            <div>
                                <h3>Diagnóstico</h3>
                                <p>Inicia relevamientos, consolida respuestas y construye el corte ejecutivo.</p>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-3'):
                            ui.button('Ingresar', icon='open_in_new', on_click=lambda: ui.navigate.to('/diagnostico')).props('flat color=primary')

                    shortcut_3 = ui.card().classes('ideas-module-card cursor-pointer')
                    shortcut_3.on('click', lambda _e: ui.navigate.to('/sistema-gestion'))
                    with shortcut_3:
                        ui.html(
                            '''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">dashboard_customize</span></div>
                            </div>
                            <div>
                                <h3>Workspace Ejecutivo</h3>
                                <p>Accede a los sistemas activos y módulos operativos de cada cliente.</p>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-3'):
                            ui.button('Ingresar', icon='open_in_new', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('flat color=primary')

                    shortcut_4 = ui.card().classes('ideas-module-card cursor-pointer')
                    shortcut_4.on('click', lambda _e: ui.navigate.to('/sistema-gestion/usuarios'))
                    with shortcut_4:
                        ui.html(
                            '''
                            <div class="ideas-module-top">
                                <div class="ideas-module-icon"><span class="material-icons">manage_accounts</span></div>
                            </div>
                            <div>
                                <h3>Usuarios y Permisos</h3>
                                <p>Gestioná perfiles, roles y accesos granulares del entorno multiempresa.</p>
                            </div>
                            '''
                        )
                        with ui.row().classes('w-full justify-end mt-3'):
                            ui.button('Ingresar', icon='open_in_new', on_click=lambda: ui.navigate.to('/sistema-gestion/usuarios')).props('flat color=primary')

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
