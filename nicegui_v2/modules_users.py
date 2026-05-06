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

    modulos_opciones = {
        'cert_iso_9001': 'Sistema de Gestion de Calidad',
        'cert_iso_14001': 'Sistema de Gestion Ambiental',
        'cert_iso_45001': 'Sistema de Salud Ocupacional',
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
        shell_container = shell('Gestion de Usuarios y Accesos', back_route='/sistema-gestion')

        with shell_container:
            if user_rol == 'empresa':
                with ui.card().classes('ideas-panel w-full'):
                    ui.label('Acceso denegado').classes('ideas-section-title')
                    ui.label('Tu usuario no tiene permisos para administrar accesos de la organizacion.').classes('ideas-section-note')
                    ui.button('Volver al workspace', icon='arrow_back', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('flat color=primary')
                return

            if user_rol != 'admin':
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
