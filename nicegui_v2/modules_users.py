from __future__ import annotations

from nicegui import app, ui


def go_to_users_module(_empresa_id: int | None = None, _set_selection_fn=None) -> None:
    ui.navigate.to('/sistema-gestion/usuarios')


def register_users_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    obtener_usuarios = deps['obtener_usuarios']
    crear_usuario = deps['crear_usuario']
    actualizar_usuario = deps['actualizar_usuario']
    eliminar_usuario = deps['eliminar_usuario']
    obtener_empresas = deps['obtener_empresas']
    fix_text = deps.get('fix_text', lambda value: '' if value is None else str(value))
    list_modules_catalog = deps.get('list_modules_catalog')
    get_available_modules_for_company = deps.get('get_available_modules_for_company')
    get_enabled_modules_for_user = deps.get('get_enabled_modules_for_user')
    assign_modules_to_user = deps.get('assign_modules_to_user')
    guardar_legal_matrix_delete_password = deps.get('guardar_legal_matrix_delete_password')
    tiene_legal_matrix_password_personalizada = deps.get('tiene_legal_matrix_password_personalizada')
    obtener_legal_matrix_alert_settings = deps.get('obtener_legal_matrix_alert_settings')
    guardar_legal_matrix_alert_settings = deps.get('guardar_legal_matrix_alert_settings')

    modulos_opciones = {
        'cert_iso_9001': 'Sistema de Gestion de Calidad',
        'cert_iso_14001': 'Sistema de Gestion Ambiental',
        'cert_iso_45001': 'Sistema de Salud Ocupacional',
        'cert_iso_17025': 'LAB ISO/IEC 17025',
    }

    def _empresa_id_sesion() -> int | None:
        value = app.storage.user.get('logged_empresa_id')
        try:
            return int(value) if value else None
        except Exception:
            return None

    def _empresas_options() -> dict[int, str]:
        return {int(empresa_id): fix_text(nombre) for empresa_id, nombre in obtener_empresas()}

    def _empresa_nombre(empresa_id: int | None) -> str:
        if not empresa_id:
            return 'Global IDEAS'
        return _empresas_options().get(int(empresa_id), f'Empresa #{empresa_id}')

    def _permisos_legibles(value: str | None) -> str:
        permisos = str(value or 'ALL').strip()
        if permisos == 'ALL':
            return 'Todos los modulos'
        labels = []
        for key in permisos.split(','):
            key = key.strip()
            if key:
                labels.append(modulos_opciones.get(key, key))
        return ', '.join(labels) if labels else 'Sin modulos asignados'

    @ui.page('/sistema-gestion/usuarios')
    def users_page() -> None:
        if not ensure_platform_access():
            return

        user_rol = str(app.storage.user.get('role') or '')
        shell_container = shell('Gestion de Usuarios y Accesos', back_route='/sistema-gestion', module_key='users')

        with shell_container:
            local_user_role = str(app.storage.user.get('local_user_role') or '').strip().upper()
            if user_rol == 'empresa' and local_user_role not in {'EMPRESA_ADMIN'}:
                with ui.card().classes('ideas-panel w-full'):
                    ui.label('Acceso denegado').classes('ideas-section-title')
                    ui.label('Tu usuario no tiene permisos para administrar accesos de la organizacion.').classes('ideas-section-note')
                    ui.button('Volver al workspace', icon='arrow_back', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('flat color=primary')
                return

            if user_rol not in {'admin', 'empresa'}:
                with ui.card().classes('ideas-panel w-full'):
                    ui.label('Sesion no autorizada').classes('ideas-section-title')
                    ui.label('Inicia sesion nuevamente con una cuenta administradora.').classes('ideas-section-note')
                return

            ui.label('Usuarios y accesos').classes('ideas-kicker')
            ui.label('Gestion multi-tenant de permisos').classes('text-3xl font-bold text-slate-900')
            if user_rol == 'admin':
                ui.label('Administra usuarios globales y usuarios asociados a cada empresa-cliente.').classes('ideas-section-note mb-4')
            else:
                ui.label(f"Administra solo usuarios de {_empresa_nombre(_empresa_id_sesion())}.").classes('ideas-section-note mb-4')

            if (
                user_rol == 'empresa'
                and local_user_role == 'EMPRESA_ADMIN'
                and callable(guardar_legal_matrix_delete_password)
                and callable(tiene_legal_matrix_password_personalizada)
                and _empresa_id_sesion()
            ):
                empresa_actual = _empresa_id_sesion()
                password_personalizada = tiene_legal_matrix_password_personalizada(empresa_actual)
                with ui.card().classes('ideas-panel w-full mb-4'):
                    ui.label('Matriz Legal · Contraseña de borrado total').classes('ideas-section-title')
                    estado_txt = 'Ya configuraste una contraseña personalizada.' if password_personalizada else 'Usando la contraseña por defecto (IDEAS).'
                    ui.label(f'Se pide antes de eliminar TODA la matriz legal de tu empresa. {estado_txt}').classes('ideas-section-note')
                    with ui.row().classes('w-full items-end gap-3 mt-2'):
                        matrix_password_input = ui.input(
                            'Nueva contraseña de borrado total',
                            password=True,
                            password_toggle_button=True,
                        ).classes('flex-1').props('outlined dense hint="Dejá en blanco para conservar la actual"')

                        def _guardar_password_matriz() -> None:
                            nueva = str(matrix_password_input.value or '').strip()
                            if not nueva:
                                ui.notify('Ingresá una contraseña nueva para actualizarla.', type='warning')
                                return
                            guardar_legal_matrix_delete_password(empresa_actual, nueva)
                            ui.notify('Contraseña actualizada.', type='positive')
                            matrix_password_input.value = ''

                        ui.button('Guardar', icon='save', on_click=_guardar_password_matriz).props('color=primary')

            if (
                user_rol == 'empresa'
                and local_user_role == 'EMPRESA_ADMIN'
                and callable(obtener_legal_matrix_alert_settings)
                and callable(guardar_legal_matrix_alert_settings)
                and _empresa_id_sesion()
            ):
                empresa_actual = _empresa_id_sesion()
                alert_settings = obtener_legal_matrix_alert_settings(empresa_actual)
                with ui.card().classes('ideas-panel w-full mb-4'):
                    ui.label('Matriz Legal · Alertas por email').classes('ideas-section-title')
                    ui.label('Aviso diario (08:00) por correo de normas vencidas o próximas a vencer, al contacto registrado de la empresa.').classes('ideas-section-note')
                    with ui.row().classes('w-full items-end gap-3 mt-2'):
                        alertas_switch = ui.switch('Activadas', value=alert_settings['activo'])
                        dias_input = ui.number(
                            'Días de anticipación', value=alert_settings['dias_anticipacion'], min=1, max=365,
                        ).classes('w-48').props('outlined dense')

                        def _guardar_alert_settings() -> None:
                            guardar_legal_matrix_alert_settings(
                                empresa_actual, bool(alertas_switch.value), int(dias_input.value or 30),
                            )
                            ui.notify('Preferencias de alertas actualizadas.', type='positive')

                        ui.button('Guardar', icon='save', on_click=_guardar_alert_settings).props('color=primary')

            def _usuarios_visibles() -> list[dict]:
                if user_rol == 'admin':
                    return obtener_usuarios()
                return obtener_usuarios(_empresa_id_sesion())

            def _usuario_por_id(usuario_id: int) -> dict | None:
                return next((item for item in _usuarios_visibles() if int(item.get('id')) == int(usuario_id)), None)

            def abrir_dialogo_usuario(row: dict | None = None) -> None:
                editando = row is not None
                usuario_actual = row or {}
                roles_disponibles = ['IDEAS_ADMIN', 'EMPRESA_ADMIN', 'EMPRESA_USER'] if user_rol == 'admin' else ['EMPRESA_ADMIN', 'EMPRESA_USER']
                rol_inicial = str(usuario_actual.get('rol') or ('EMPRESA_ADMIN' if user_rol == 'admin' else 'EMPRESA_USER'))
                empresa_inicial = usuario_actual.get('empresa_id') if editando else _empresa_id_sesion()
                permisos_iniciales = []
                if str(usuario_actual.get('permisos') or 'ALL') != 'ALL':
                    permisos_iniciales = [item.strip() for item in str(usuario_actual.get('permisos') or '').split(',') if item.strip()]

                with ui.dialog() as dialog, ui.card().classes('w-[700px] max-w-[95vw] bg-white rounded-[26px] p-6'):
                    with ui.row().classes('w-full items-start justify-between gap-3'):
                        with ui.column().classes('gap-1'):
                            ui.label('Editar acceso' if editando else 'Nuevo usuario').classes('ideas-section-title')
                            ui.label('Define rol, empresa y sistemas permitidos para mantener el aislamiento por cliente.').classes('ideas-section-note')
                        ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                    with ui.grid(columns=2).classes('ideas-grid-2 w-full mt-4'):
                        username_input = ui.input('Nombre de Usuario', value=fix_text(usuario_actual.get('username', ''))).classes('w-full').props('outlined')
                        password_input = ui.input('Contrasena', password=True, password_toggle_button=True).classes('w-full').props('outlined')
                        select_rol = ui.select(roles_disponibles, value=rol_inicial, label='Rol').classes('w-full').props('outlined')
                        empresa_select = ui.select(_empresas_options(), value=int(empresa_inicial) if empresa_inicial else None, label='Empresa').classes('w-full').props('outlined')
                        empresa_select.set_visibility(user_rol == 'admin')

                    if editando:
                        password_input.value = ''
                        password_input.props('hint="Deja en blanco para conservar la contraseña actual"')

                    permisos_box = ui.column().classes('w-full mt-4 p-4 border rounded-xl bg-slate-50')
                    permisos_box.bind_visibility_from(select_rol, 'value', lambda value: value == 'EMPRESA_USER')
                    with permisos_box:
                        ui.label('Selecciona los sistemas permitidos para este usuario operativo').classes('font-semibold text-slate-700')
                        permisos_select = ui.select(
                            modulos_opciones,
                            value=permisos_iniciales,
                            multiple=True,
                            label='Sistemas',
                        ).classes('w-full').props('outlined use-chips')

                    user_modules_box = ui.column().classes('w-full mt-4 p-4 border rounded-xl bg-slate-50')
                    user_modules_box.bind_visibility_from(select_rol, 'value', lambda value: value in {'EMPRESA_ADMIN', 'EMPRESA_USER'})
                    modules_options = {}
                    modules_initial_ids = []
                    if callable(list_modules_catalog) and callable(get_available_modules_for_company):
                        target_company_id = int(empresa_inicial) if empresa_inicial else None
                        if target_company_id:
                            company_modules = get_available_modules_for_company(int(target_company_id)) or []
                            modules_options = {
                                int(item.get('id')): fix_text(item.get('name') or item.get('code') or '')
                                for item in company_modules
                                if int(item.get('enabled') or 0) == 1 and str(item.get('category') or '') != 'admin'
                            }
                    if editando and callable(get_enabled_modules_for_user) and empresa_inicial:
                        try:
                            current_user_modules = get_enabled_modules_for_user(int(usuario_actual.get('id')), int(empresa_inicial)) or []
                            modules_initial_ids = [int(item.get('id')) for item in current_user_modules if int(item.get('user_enabled') or 0) == 1]
                        except Exception:
                            modules_initial_ids = []
                    with user_modules_box:
                        ui.label('Módulos del Usuario').classes('font-semibold text-slate-700')
                        ui.label('Solo puedes asignar módulos habilitados para esta empresa.').classes('text-xs text-slate-500')
                        user_module_state = {int(mid): (int(mid) in {int(x) for x in modules_initial_ids}) for mid in modules_options.keys()}
                        module_pool = ui.column().classes('w-full mt-2 gap-2')

                        def _render_user_module_pool() -> None:
                            module_pool.clear()
                            with module_pool:
                                with ui.grid(columns=2).classes('w-full gap-2'):
                                    for module_id, module_label in modules_options.items():
                                        with ui.card().classes('ideas-panel').style('border:1px solid rgba(148,163,184,.20);box-shadow:none;'):
                                            with ui.row().classes('w-full items-center justify-between'):
                                                ui.label(module_label).classes('text-sm text-slate-800')
                                                sw = ui.switch(value=bool(user_module_state.get(int(module_id)))).props('dense')
                                                sw.on_value_change(lambda e, mid=int(module_id): user_module_state.__setitem__(mid, bool(e.value)))
                        _render_user_module_pool()
                        with ui.row().classes('w-full justify-between mt-2'):
                            ui.button('Asignar todos', icon='select_all', on_click=lambda: (user_module_state.update({int(k): True for k in user_module_state}), _render_user_module_pool())).props('flat')
                            ui.button('Quitar todos', icon='deselect', on_click=lambda: (user_module_state.update({int(k): False for k in user_module_state}), _render_user_module_pool())).props('flat color=warning')

                    def guardar() -> None:
                        rol = str(select_rol.value or '').strip()
                        empresa_id = None
                        if user_rol == 'admin':
                            empresa_id = None if rol == 'IDEAS_ADMIN' else empresa_select.value
                        else:
                            empresa_id = _empresa_id_sesion()
                        permisos = 'ALL' if rol in {'IDEAS_ADMIN', 'EMPRESA_ADMIN'} else ','.join(list(permisos_select.value or []))
                        if editando:
                            nuevo_username = username_input.value or ''
                            nuevo_password = str(password_input.value or '').strip()
                            ok, mensaje = actualizar_usuario(
                                int(usuario_actual['id']),
                                rol,
                                empresa_id,
                                permisos,
                                username=nuevo_username,
                                password=nuevo_password if nuevo_password else None,
                            )
                        else:
                            ok, mensaje = crear_usuario(username_input.value or '', password_input.value or '', rol, empresa_id, permisos)
                        if not ok:
                            ui.notify(fix_text(mensaje), type='negative')
                            return
                        if (
                            callable(assign_modules_to_user)
                            and rol in {'EMPRESA_ADMIN', 'EMPRESA_USER'}
                            and empresa_id
                        ):
                            target_user_id = int(usuario_actual['id']) if editando else None
                            if not target_user_id:
                                # recuperar por username luego de crear
                                target = next((u for u in _usuarios_visibles() if str(u.get('username') or '').strip().lower() == str(username_input.value or '').strip().lower()), None)
                                target_user_id = int(target.get('id')) if target else None
                            if target_user_id:
                                assign_modules_to_user(
                                    int(target_user_id),
                                    int(empresa_id),
                                    [int(mid) for mid, enabled in user_module_state.items() if bool(enabled)],
                                    actor=str(app.storage.user.get('session_user_key') or app.storage.user.get('username') or ''),
                                )
                        ui.notify(fix_text(mensaje), type='positive')
                        dialog.close()
                        cargar_tabla_usuarios.refresh()

                    with ui.row().classes('w-full justify-end gap-2 mt-6'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat')
                        ui.button('Guardar', icon='save', on_click=guardar).props('color=primary')

                dialog.open()

            def confirmar_eliminacion(usuario_id: int) -> None:
                usuario = _usuario_por_id(usuario_id)
                if not usuario:
                    ui.notify('Ese usuario ya no existe.', type='warning')
                    cargar_tabla_usuarios.refresh()
                    return
                if str(usuario.get('username') or '').strip().lower() in {'admin', 'ideas'}:
                    ui.notify('No se puede eliminar el administrador base.', type='warning')
                    return

                with ui.dialog() as confirm, ui.card().classes('ideas-panel w-[520px] max-w-[95vw]'):
                    ui.label('Eliminar usuario').classes('ideas-section-title')
                    ui.label(f"Se eliminara permanentemente el acceso de {fix_text(usuario.get('username', ''))}.").classes('ideas-section-note')

                    def eliminar() -> None:
                        ok, mensaje = eliminar_usuario(int(usuario_id))
                        if not ok:
                            ui.notify(fix_text(mensaje), type='negative')
                            return
                        confirm.close()
                        ui.notify(fix_text(mensaje), type='positive')
                        cargar_tabla_usuarios.refresh()

                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancelar', on_click=confirm.close).props('flat')
                        ui.button('Eliminar', icon='delete', on_click=eliminar).props('color=negative')
                confirm.open()

            @ui.refreshable
            def cargar_tabla_usuarios() -> None:
                usuarios = _usuarios_visibles()
                columnas = [
                    {'name': 'username', 'label': 'Usuario', 'field': 'username', 'align': 'left'},
                    {'name': 'rol', 'label': 'Rol', 'field': 'rol', 'align': 'center'},
                    {'name': 'permisos', 'label': 'Permisos', 'field': 'permisos', 'align': 'left'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                ]
                if user_rol == 'admin':
                    columnas.insert(2, {'name': 'empresa', 'label': 'Empresa', 'field': 'empresa', 'align': 'left'})

                filas = []
                for usuario in usuarios:
                    fila = {
                        'id': int(usuario['id']),
                        'username': fix_text(usuario.get('username', '')),
                        'rol': fix_text(usuario.get('rol', '')),
                        'empresa': _empresa_nombre(usuario.get('empresa_id')) if usuario.get('empresa_id') else 'Global IDEAS',
                        'permisos': _permisos_legibles(usuario.get('permisos')),
                        'acciones': '',
                    }
                    filas.append(fila)

                with ui.card().classes('ideas-panel w-full'):
                    with ui.row().classes('w-full items-center justify-between gap-3'):
                        with ui.column().classes('gap-1'):
                            ui.label('Usuarios Activos').classes('ideas-section-title')
                            ui.label('Listado operativo de credenciales, roles y alcance por sistema.').classes('ideas-section-note')
                        ui.button('Nuevo Usuario', icon='person_add', on_click=lambda: abrir_dialogo_usuario()).props('color=primary')

                    tabla = ui.table(
                        columns=columnas,
                        rows=filas,
                        row_key='id',
                        pagination={'rowsPerPage': 10},
                    ).classes('w-full ideas-table mt-4')
                    tabla.props('flat bordered')
                    tabla.add_slot(
                        'body-cell-acciones',
                        '''
                        <q-td :props="props">
                            <div class="row items-center justify-center no-wrap q-gutter-sm">
                                <q-btn flat round dense icon="edit" color="primary" @click="$parent.$emit('edit_user', props.row.id)" />
                                <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_user', props.row.id)" />
                            </div>
                        </q-td>
                        ''',
                    )
                    tabla.on('edit_user', lambda event: abrir_dialogo_usuario(_usuario_por_id(int(event.args))))
                    tabla.on('delete_user', lambda event: confirmar_eliminacion(int(event.args)))

            cargar_tabla_usuarios()
