"""IDEAS Consulting - Matriz Legal (prototipo mobile).

Proyecto paralelo e independiente de nicegui_v2/. No modifica ni depende del
código de la plataforma principal para arrancar: reutiliza sus funciones de
datos (ver data.py) contra la misma base ideas.db, pero corre en su propio
proceso NiceGUI y en un puerto distinto. Pensado para abrirse desde el
navegador del celular, como la vería el cliente final (una empresa), con
look & feel de app nativa iOS. Sin login / gestión de usuarios todavía.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from nicegui import app, ui

import auth
import data as dm

FAVICON = str(dm.ROOT / 'favicon.ico')
ASSETS_DIR = Path(__file__).resolve().parent / 'data'
MARK_URL = '/assets/ideas_mark.png'

# Se registra en scope de módulo (no en una página): no crea elementos de UI,
# solo agrega rutas estáticas al servidor, así que no dispara el modo
# "script" de NiceGUI (ver _inject_theme).
app.add_static_files('/assets', str(ASSETS_DIR))
app.add_static_file(local_file=ASSETS_DIR / 'manifest.json', url_path='/manifest.json')

# Safari pide el ícono de "Agregar a pantalla de inicio" en estas rutas fijas
# en la raíz del sitio (no alcanza con el <link rel="apple-touch-icon">).
for _url_path in (
    '/apple-touch-icon.png',
    '/apple-touch-icon-precomposed.png',
    '/apple-touch-icon-180x180.png',
    '/apple-touch-icon-180x180-precomposed.png',
):
    app.add_static_file(local_file=ASSETS_DIR / 'apple_touch_icon_180.png', url_path=_url_path)
for _url_path in ('/apple-touch-icon-120x120.png', '/apple-touch-icon-120x120-precomposed.png'):
    app.add_static_file(local_file=ASSETS_DIR / 'apple_touch_icon_120.png', url_path=_url_path)


@app.get('/evidence-file/{empresa_id}/{evidence_id}')
def evidence_file(empresa_id: int, evidence_id: int):
    """Sirve un archivo de evidencia solo a la sesión logueada de esa misma
    empresa — a diferencia de /assets, esta carpeta no es de acceso público."""
    if not auth.esta_autenticado() or auth.empresa_id_sesion() != empresa_id:
        raise HTTPException(status_code=403)
    evidencia = dm.evidencia_por_id(empresa_id, evidence_id)
    if not evidencia:
        raise HTTPException(status_code=404)
    ruta = dm.ruta_evidencia(evidencia)
    if not ruta.exists():
        raise HTTPException(status_code=404)
    return FileResponse(str(ruta), filename=str(evidencia.get('nombre') or ruta.name))


def _inject_theme() -> None:
    """Debe llamarse dentro de una página (no en scope global): NiceGUI 3.x
    trata cualquier llamada de UI en scope global como una "script app" de
    una sola página implícita, lo que choca con el uso explícito de @ui.page."""
    ui.colors(
        primary=dm.PRIMARY,
        secondary='#14577E',
        accent='#0E3A53',
        positive='#15803D',
        negative='#B91C1C',
        warning='#B45309',
    )
    ui.add_head_html('''
    <link rel="manifest" href="/manifest.json">
    <link rel="apple-touch-icon" sizes="180x180" href="/assets/apple_touch_icon_180.png">
    <link rel="apple-touch-icon" sizes="167x167" href="/assets/apple_touch_icon_167.png">
    <link rel="apple-touch-icon" sizes="120x120" href="/assets/apple_touch_icon_120.png">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-title" content="Matriz Legal">
    <meta name="apple-mobile-web-app-status-bar-style" content="default">
    <meta name="theme-color" content="#0E3A53">
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700;800&display=swap" rel="stylesheet">
    <style>
      body, .nicegui-content { font-family: "Poppins", -apple-system, "Segoe UI", sans-serif !important; }
      body { background:#F2F2F7 !important; }
      .lm-card { border-radius:14px !important; box-shadow:0 1px 3px rgba(16,24,40,.05) !important; }
      .lm-tight .q-field__control { border-radius:12px !important; }
      .q-tab-panel { padding:0 !important; }

      /* Barras translúcidas con blur, como una navigation/tab bar de iOS */
      .q-header, .q-footer {
        background:rgba(255,255,255,.86) !important;
        backdrop-filter:saturate(180%) blur(20px);
        -webkit-backdrop-filter:saturate(180%) blur(20px);
        box-shadow:none !important;
      }
      .q-header { border-bottom:1px solid rgba(0,0,0,.08); }
      .q-footer { border-top:1px solid rgba(0,0,0,.08); }

      /* iOS no usa la barra indicadora de Material bajo el tab activo */
      .q-tabs .q-tab__indicator { display:none !important; }
      .q-footer .q-tab { min-height:58px; padding-top:6px; }
      .q-footer .q-tab__icon { font-size:23px; }
      .q-footer .q-tab__label { font-size:10.5px; font-weight:600; margin-top:2px; }
      /* Quasar's QTab no tiene prop "text-color" llana; los tabs inactivos
         quedan blanco-sobre-blanco por defecto si no se fuerza un color. */
      .q-footer .q-tab--inactive { color:#98A2AF !important; }

      .lm-icon-btn { border-radius:10px !important; }
      .lm-large-title { font-size:25px; font-weight:800; letter-spacing:-.01em; color:#1B2433; }

      /* Login v2: franja de 4 colores (los del isotipo), campos simples con
         etiqueta arriba (sin el label flotante de Quasar), botón Face ID. */
      .lm-stripe { height:4px; width:100%; display:flex !important; flex-shrink:0; align-items:stretch !important; gap:0 !important; }
      .lm-stripe > div { flex:1; height:100%; }
      .lm-field-label { font-size:12px; color:#8A93A1; font-weight:500; margin-bottom:4px; display:block; }
      .lm-login-input .q-field__control { border-radius:10px !important; background:#F7F8FA; }
      .lm-login-input .q-field__control:before { border-color:#E3E8EF !important; }
      .lm-login-input.q-field--focused .q-field__control:before { border-color:#0E3A53 !important; border-width:1.5px !important; }
      .lm-divider-o { display:flex; align-items:center; gap:10px; width:100%; }
      .lm-divider-o .lm-line { flex:1; height:1px; background:#E3E8EF; }
      .lm-faceid-btn { border-radius:10px !important; border:1px solid #1D9E75 !important; color:#0F6E56 !important; }

      #lm-splash {
        position:fixed; inset:0; z-index:9999; background:#fff;
        display:flex; flex-direction:column; align-items:center; justify-content:center; gap:18px;
        transition:opacity .35s ease;
      }
      #lm-splash img { width:84px; height:84px; }
      #lm-splash .lm-ring {
        width:34px; height:34px; border-radius:50%;
        border:3px solid #E3E8EF; border-top-color:#0E3A53;
        animation:lm-spin .8s linear infinite;
      }
      @keyframes lm-spin { to { transform:rotate(360deg); } }
      #lm-splash.lm-splash-hide { opacity:0; pointer-events:none; }
    </style>
    ''')


def _inject_splash() -> None:
    """Pantalla de marca al abrir la app (spec §1.5): fondo blanco, logo
    centrado, anillo de carga. Se oculta sola por JS del lado cliente, sin
    ida y vuelta al servidor — el contenido real ya se renderizó debajo."""
    ui.add_body_html(f'''
    <div id="lm-splash">
      <img src="{MARK_URL}" alt="IDEAS Consulting">
      <div class="lm-ring"></div>
    </div>
    <script>
      setTimeout(() => {{
        const el = document.getElementById('lm-splash');
        if (el) {{
          el.classList.add('lm-splash-hide');
          setTimeout(() => el.remove(), 400);
        }}
      }}, 1500);
    </script>
    ''')


# ---------------------------------------------------------------------------
# Pequeños widgets reutilizables
# ---------------------------------------------------------------------------

def estado_pill(estado_norm: str) -> None:
    st = dm.ESTADO_STYLE.get(estado_norm, dm.ESTADO_STYLE['pendiente'])
    with ui.row().classes('items-center gap-1 px-2 py-1 rounded-full').style(
        f'background:{st["bg"]}; color:{st["color"]};'
    ):
        ui.icon(st['icon']).classes('text-sm')
        ui.label(st['label']).classes('text-xs font-semibold')


def criticidad_pill(crit_norm: str) -> None:
    st = dm.CRITICIDAD_STYLE.get(crit_norm, dm.CRITICIDAD_STYLE['media'])
    ui.label(st['label']).classes('text-[11px] font-semibold px-2 py-0.5 rounded-full border').style(
        f'color:{st["color"]}; border-color:{st["color"]}55;'
    )


def kpi_card(icon: str, value, label: str, color: str) -> None:
    with ui.card().classes('lm-card flex-1 min-w-[150px] p-4 items-start gap-1'):
        with ui.row().classes('items-center gap-2'):
            with ui.element('div').classes('rounded-full p-2').style(f'background:{color}22;'):
                ui.icon(icon).style(f'color:{color};').classes('text-xl')
            ui.label(str(value)).classes('text-2xl font-bold').style(f'color:{dm.PRIMARY};')
        ui.label(label).classes('text-xs text-gray-500')


def empty_state(icon: str, title: str, subtitle: str) -> None:
    with ui.column().classes('w-full items-center justify-center py-14 gap-2 text-center'):
        ui.icon(icon).classes('text-5xl text-gray-300')
        ui.label(title).classes('text-gray-500 font-medium')
        ui.label(subtitle).classes('text-gray-400 text-sm px-8')


TAB_TITLES = {'dashboard': 'Inicio', 'normas': 'Normas', 'alertas': 'Alertas', 'sedes': 'Sedes'}


# ---------------------------------------------------------------------------
# Login (spec §1): mismos usuarios que la plataforma principal, sin selector
# de empresa — empresa_id sale directo del usuario logueado.
# ---------------------------------------------------------------------------

STRIPE_COLORS = ('#378ADD', '#EF9F27', '#639922', '#1D9E75')


@ui.page('/login')
def login_page() -> None:
    _inject_theme()
    if auth.esta_autenticado():
        ui.navigate.to('/')
        return

    with ui.column().classes('w-full min-h-screen').style('background:#fff;'):
        with ui.row().classes('lm-stripe'):
            for color in STRIPE_COLORS:
                ui.element('div').style(f'background:{color};')

        with ui.column().classes('w-full flex-1 items-center px-6').style('padding-top:48px;'):
            ui.image(MARK_URL).classes('rounded-2xl').style('width:76px; height:76px; margin-bottom:14px;')
            ui.label('IDEUS').classes('text-lg').style('color:#1B2433; font-weight:500; letter-spacing:.1em;')
            ui.label('BY IDEAS CONSULTING').classes('text-[9px] font-bold').style('color:#8A93A1; letter-spacing:.12em; margin-top:2px;')
            ui.label('Matriz Legal').classes('text-xs mb-6 mt-1').style('color:#8A93A1;')

            with ui.column().classes('w-full max-w-sm gap-1'):
                ui.label('Usuario').classes('lm-field-label')
                usuario = ui.input(placeholder='nombre@empresa.com').classes(
                    'w-full lm-login-input'
                ).props('outlined dense autofocus')

                ui.label('Contraseña').classes('lm-field-label mt-2')
                password = ui.input(placeholder='••••••••', password=True, password_toggle_button=True).classes(
                    'w-full lm-login-input'
                ).props('outlined dense')

                with ui.row().classes('w-full justify-end mt-1'):
                    def _forgot() -> None:
                        ui.notify(
                            'Pedile a tu administrador de IDEAS que te reinicie la contraseña desde la plataforma.',
                            type='info', timeout=5000,
                        )
                    ui.label('¿Olvidaste tu contraseña?').classes('text-xs cursor-pointer').style(
                        'color:#378ADD;'
                    ).on('click', _forgot)

                error_label = ui.label('').classes('text-xs text-red-600')
                error_label.set_visibility(False)

                def _submit() -> None:
                    ok, mensaje = auth.login(usuario.value or '', password.value or '')
                    if not ok:
                        error_label.text = mensaje
                        error_label.set_visibility(True)
                        return
                    ui.navigate.to('/')

                password.on('keydown.enter', _submit)
                ui.button('Ingresar', on_click=_submit).props('unelevated no-caps').classes(
                    'w-full mt-2'
                ).style(f'background:{dm.PRIMARY}; border-radius:10px;')

                with ui.row().classes('lm-divider-o my-3'):
                    ui.element('div').classes('lm-line')
                    ui.label('o').classes('text-[11px]').style('color:#98A2AF;')
                    ui.element('div').classes('lm-line')

                def _face_id() -> None:
                    ui.notify(
                        'Face ID todavía no está activado en esta versión — por ahora ingresá con '
                        'usuario y contraseña.',
                        type='warning', timeout=5000,
                    )
                ui.button('Ingresar con Face ID', icon='o_fingerprint', on_click=_face_id).props(
                    'outline no-caps'
                ).classes('w-full lm-faceid-btn')

                with ui.row().classes('w-full items-center justify-center gap-1 mt-6'):
                    ui.icon('o_lock').classes('text-xs').style('color:#98A2AF;')
                    ui.label('Conexión segura · tu empresa se identifica automáticamente con tu usuario').classes(
                        'text-[10.5px] text-center'
                    ).style('color:#98A2AF;')


# ---------------------------------------------------------------------------
# Página principal
# ---------------------------------------------------------------------------

@ui.page('/')
def main_page() -> None:
    _inject_theme()
    if not auth.esta_autenticado():
        ui.navigate.to('/login')
        return
    _inject_splash()

    empresa_id = auth.empresa_id_sesion()
    state = {'estado_filtro': 'todas', 'texto': ''}

    @ui.refreshable
    def alert_badge() -> None:
        count = dm.contar_alertas_abiertas(empresa_id)
        if count:
            ui.badge(str(count) if count < 100 else '99+').props('color=red floating')

    # -- Header: barra compacta (marca + acciones) + título grande estilo iOS --
    with ui.header().classes('px-4 pt-2 pb-1'):
        with ui.column().classes('w-full max-w-xl mx-auto gap-1'):
            with ui.row().classes('w-full items-center justify-between'):
                with ui.row().classes('items-center gap-2'):
                    ui.image(MARK_URL).classes('w-7 h-7 rounded-md')
                    ui.label('IDEUS').classes(
                        'text-[11px] font-semibold text-gray-500 tracking-wide uppercase'
                    )
                with ui.row().classes('items-center gap-1'):
                    plus_button = ui.button(icon='o_add', on_click=lambda: open_add()).props(
                        'flat round dense'
                    ).classes('lm-icon-btn').style(f'color:{dm.PRIMARY};')
                    ui.button(icon='o_refresh', on_click=lambda: refrescar_todo()).props(
                        'flat round dense'
                    ).classes('lm-icon-btn').style(f'color:{dm.PRIMARY};')
                    with ui.element('div').classes('relative'):
                        ui.button(icon='o_notifications', on_click=lambda: tabs.set_value('alertas')).props(
                            'flat round dense'
                        ).classes('lm-icon-btn').style(f'color:{dm.PRIMARY};')
                        alert_badge()

                    def _logout() -> None:
                        auth.logout()
                        ui.navigate.to('/login')

                    ui.button(icon='o_logout', on_click=_logout).props(
                        'flat round dense'
                    ).classes('lm-icon-btn').style('color:#98A2AF;')
            with ui.row().classes('w-full items-baseline justify-between'):
                title_label = ui.label(TAB_TITLES['dashboard']).classes('lm-large-title')
                with ui.column().classes('gap-0 items-end'):
                    ui.label(dm.empresa_nombre(empresa_id) or '—').classes('text-xs text-gray-400 font-medium')
                    ui.label(auth.nombre_usuario_sesion()).classes('text-[10px] text-gray-300')
    plus_button.set_visibility(False)
    puede_editar = auth.puede_editar()

    # -- Detalle / cambio de estado -------------------------------------
    detail_dialog = ui.dialog()

    def open_detail(req: dict) -> None:
        detail_dialog.clear()
        with detail_dialog, ui.card().classes('lm-card w-full max-w-md p-0 overflow-hidden'):
            with ui.column().classes('w-full p-5 gap-3'):
                with ui.row().classes('w-full items-start justify-between'):
                    ui.label(req.get('titulo') or 'Sin título').classes('text-lg font-bold flex-1').style(
                        f'color:{dm.PRIMARY};'
                    )
                    ui.button(icon='o_close', on_click=detail_dialog.close).props('flat round dense')
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    estado_pill(req['estado_norm'])
                    criticidad_pill(req['criticidad_norm'])
                    ui.label(f"{req.get('tipo_norma') or ''} {req.get('numero') or ''}".strip()).classes(
                        'text-xs text-gray-500 border rounded-full px-2 py-0.5'
                    )
                ui.separator()
                for icon, label, value in (
                    ('o_category', 'Ámbito', req.get('ambito')),
                    ('o_account_balance', 'Organismo', req.get('organismo')),
                    ('o_gavel', 'Jurisdicción', req.get('jurisdiccion')),
                    ('o_description', 'Obligación', req.get('obligacion')),
                    ('o_person', 'Responsable', req.get('responsable')),
                    ('o_event', 'Próxima revisión',
                        dm.formatear_fecha(req.get('proxima_revision')) if req.get('proxima_revision') else ''),
                ):
                    if not value:
                        continue
                    with ui.row().classes('items-start gap-2'):
                        ui.icon(icon).classes('text-gray-400 text-base mt-0.5')
                        ui.label(str(value)).classes('text-sm text-gray-700')
                if puede_editar:
                    ui.separator()
                    ui.label('Cambiar estado').classes('text-xs font-semibold text-gray-500')
                    with ui.row().classes('w-full gap-2 flex-wrap'):
                        for estado in dm.ESTADOS:
                            def _set(estado=estado, req_id=req['id']):
                                if not puede_editar:
                                    return
                                dm.actualizar_estado_requisito(empresa_id, req_id, estado)
                                detail_dialog.close()
                                requirements_view.refresh()
                                dashboard_view.refresh()
                                ui.notify(f'Estado actualizado a "{estado}"', color='positive')
                            active = req['estado'] == estado
                            ui.button(estado, on_click=_set).props(
                                f'{"unelevated" if active else "outline"} dense no-caps'
                            ).classes('text-xs')

                ui.separator()
                ui.label('Evidencia').classes('text-xs font-semibold text-gray-500')

                @ui.refreshable
                def evidencias_section() -> None:
                    items = dm.listar_evidencias(empresa_id, req['id'])
                    if not items:
                        ui.label('Sin evidencia cargada.').classes('text-xs text-gray-400')
                    for ev in items:
                        nombre = str(ev.get('nombre') or '')
                        es_imagen = nombre.lower().endswith(('.png', '.jpg', '.jpeg', '.heic', '.webp', '.gif'))
                        with ui.row().classes('w-full items-center gap-2'):
                            ui.icon('o_image' if es_imagen else 'o_description').classes('text-gray-400 text-lg')
                            with ui.column().classes('gap-0 flex-1 min-w-0'):
                                ui.label(nombre).classes('text-xs text-gray-700 truncate')
                                subinfo = f"{(ev.get('created_at') or '')[:10]} · {ev.get('cargado_por') or 'sistema'}"
                                ui.label(subinfo).classes('text-[11px] text-gray-400')
                            ui.link('Ver', f'/evidence-file/{empresa_id}/{ev["id"]}', new_tab=True).classes(
                                'text-xs font-semibold'
                            ).style(f'color:{dm.PRIMARY};')

                    if puede_editar:
                        async def _on_evidencia(e) -> None:
                            contenido = await e.file.read()
                            if len(contenido) > dm.EVIDENCE_MAX_BYTES:
                                ui.notify('El archivo supera el tamaño máximo (15 MB).', color='negative')
                                return
                            dm.guardar_evidencia(
                                empresa_id, req['id'], e.file.name, contenido,
                                origen='mobile', cargado_por=auth.nombre_usuario_sesion(),
                            )
                            evidencias_section.refresh()
                            ui.notify('Evidencia cargada', color='positive')

                        ui.upload(on_upload=_on_evidencia, auto_upload=True, max_file_size=dm.EVIDENCE_MAX_BYTES).props(
                            f'accept="{dm.EVIDENCE_ACCEPT}" flat bordered label="Adjuntar evidencia (cámara, galería o archivo)"'
                        ).classes('w-full mt-1')

                evidencias_section()
        detail_dialog.open()

    # -- Alta rápida de norma --------------------------------------------
    add_dialog = ui.dialog()

    def open_add() -> None:
        if not puede_editar:
            return
        add_dialog.clear()
        with add_dialog, ui.card().classes('lm-card w-full max-w-md p-5 gap-2'):
            ui.label('Nueva norma').classes('text-lg font-bold').style(f'color:{dm.PRIMARY};')
            titulo = ui.input('Título *').classes('w-full lm-tight').props('outlined dense')
            with ui.row().classes('w-full gap-2'):
                tipo = ui.select(['Ley', 'Decreto', 'Resolución', 'Ordenanza', 'Disposición'],
                                  value='Ley', label='Tipo').classes('flex-1 lm-tight').props('outlined dense')
                numero = ui.input('Número').classes('flex-1 lm-tight').props('outlined dense')
            ambito = ui.select(dm.AMBITOS, value='Medio Ambiente', label='Ámbito').classes(
                'w-full lm-tight'
            ).props('outlined dense')
            organismo = ui.input('Organismo').classes('w-full lm-tight').props('outlined dense')
            obligacion = ui.textarea('Obligación').classes('w-full lm-tight').props('outlined dense rows=2')
            responsable = ui.input('Responsable').classes('w-full lm-tight').props('outlined dense')
            with ui.row().classes('w-full gap-2'):
                criticidad = ui.select(dm.CRITICIDADES, value='Media', label='Criticidad').classes(
                    'flex-1 lm-tight'
                ).props('outlined dense')
                estado = ui.select(dm.ESTADOS, value='Pendiente', label='Estado').classes(
                    'flex-1 lm-tight'
                ).props('outlined dense')
            revision = ui.input('Próxima revisión').props('outlined dense type=date').classes('w-full lm-tight')

            def _save() -> None:
                if not puede_editar:
                    return
                if not titulo.value or not titulo.value.strip():
                    ui.notify('El título es obligatorio', color='negative')
                    return
                dm.crear_requisito(empresa_id, {
                    'titulo': titulo.value,
                    'tipo_norma': tipo.value,
                    'numero': numero.value,
                    'ambito': ambito.value,
                    'organismo': organismo.value,
                    'obligacion': obligacion.value,
                    'responsable': responsable.value,
                    'criticidad': criticidad.value,
                    'estado': estado.value,
                    'proxima_revision': revision.value or '',
                })
                add_dialog.close()
                requirements_view.refresh()
                dashboard_view.refresh()
                ui.notify('Norma agregada', color='positive')

            with ui.row().classes('w-full justify-end gap-2 pt-2'):
                ui.button('Cancelar', on_click=add_dialog.close).props('flat no-caps')
                ui.button('Guardar', on_click=_save).props('unelevated no-caps').style(
                    f'background:{dm.PRIMARY};'
                )
        add_dialog.open()

    # -- Contenido con tabs ----------------------------------------------
    with ui.column().classes('w-full max-w-xl mx-auto px-3 pt-3 pb-6 gap-3'):

        @ui.refreshable
        def dashboard_view() -> None:
            stats = dm.dashboard(empresa_id)
            with ui.row().classes('w-full gap-3 flex-wrap'):
                kpi_card('o_verified', f"{stats['pct_cumplimiento']}%", 'Cumplimiento', dm.ESTADO_STYLE['cumple']['color'])
                kpi_card('o_library_books', stats['total'], 'Normas totales', dm.PRIMARY)
                kpi_card('o_notifications_active', stats['alertas_abiertas'], 'Alertas abiertas', dm.ESTADO_STYLE['no_cumple']['color'])
                kpi_card('o_update', stats['proximas_30d'], 'Vencen en 30 días', dm.ESTADO_STYLE['pendiente']['color'])

            if stats['total']:
                with ui.card().classes('lm-card w-full p-4 gap-2'):
                    ui.label('Estado de las normas').classes('text-sm font-semibold text-gray-600')
                    for key in ('cumple', 'pendiente', 'no_cumple', 'no_aplica'):
                        st = dm.ESTADO_STYLE[key]
                        n = stats['conteos'][key]
                        pct = round((n / stats['total']) * 100) if stats['total'] else 0
                        with ui.row().classes('items-center gap-2 w-full'):
                            ui.label(st['label']).classes('text-xs w-20 text-gray-500')
                            with ui.element('div').classes('flex-1 rounded-full overflow-hidden').style(
                                'background:#EEF1F5; height:8px;'
                            ):
                                ui.element('div').style(
                                    f'background:{st["color"]}; width:{pct}%; height:100%; border-radius:9999px;'
                                )
                            ui.label(str(n)).classes('text-xs w-6 text-right text-gray-600')
            else:
                empty_state('o_library_books', 'Todavía no hay normas cargadas',
                            'Tocá "Normas" y usá el botón + para agregar la primera.')

            if stats['vencidas']:
                with ui.card().classes('lm-card w-full p-3 flex-row items-center gap-2').style(
                    f'background:{dm.ESTADO_STYLE["no_cumple"]["bg"]};'
                ):
                    ui.icon('o_warning').style(f'color:{dm.ESTADO_STYLE["no_cumple"]["color"]};')
                    ui.label(f"{stats['vencidas']} norma(s) con revisión vencida").classes('text-sm').style(
                        f'color:{dm.ESTADO_STYLE["no_cumple"]["color"]};'
                    )

        def requirement_card(req: dict) -> None:
            with ui.card().classes('lm-card w-full p-3 gap-1 cursor-pointer').on('click', lambda req=req: open_detail(req)):
                with ui.row().classes('w-full items-start justify-between gap-2'):
                    ui.label(req.get('titulo') or 'Sin título').classes('text-sm font-semibold flex-1').style(
                        f'color:{dm.PRIMARY};'
                    )
                    estado_pill(req['estado_norm'])
                with ui.row().classes('items-center gap-2 flex-wrap'):
                    ui.label(f"{req.get('tipo_norma') or ''} {req.get('numero') or ''}".strip()).classes(
                        'text-xs text-gray-500'
                    )
                    ui.label('•').classes('text-gray-300')
                    ui.label(req.get('ambito') or '').classes('text-xs text-gray-500')
                    criticidad_pill(req['criticidad_norm'])
                if req.get('proxima_revision'):
                    with ui.row().classes('items-center gap-1'):
                        ui.icon('o_event').classes('text-xs text-gray-400')
                        ui.label(f"Próxima revisión: {dm.formatear_fecha(req['proxima_revision'])}").classes(
                            'text-xs text-gray-400'
                        )

        @ui.refreshable
        def requirements_view() -> None:
            with ui.row().classes('w-full items-center gap-2'):
                search = ui.input(placeholder='Buscar norma...', value=state['texto']).props(
                    'outlined dense clearable prepend-icon=o_search'
                ).classes('flex-1 lm-tight')

                def _search(e) -> None:
                    state['texto'] = e.value or ''
                    requirements_view.refresh()

                search.on_value_change(_search)

            with ui.row().classes('w-full gap-2 flex-wrap'):
                chip_options = [('todas', 'Todas')] + [
                    (dm.normalizar_estado(e), e) for e in dm.ESTADOS
                ]
                for key, label in chip_options:
                    active = state['estado_filtro'] == key

                    def _pick(key=key) -> None:
                        state['estado_filtro'] = key
                        requirements_view.refresh()

                    ui.button(label, on_click=_pick).props('dense no-caps unelevated' if active else 'dense no-caps outline').classes(
                        'text-xs rounded-full'
                    ).style(f'background:{dm.PRIMARY};' if active else '')

            rows = dm.listar_requisitos(empresa_id, state['estado_filtro'], state['texto'])
            if not rows:
                empty_state('o_search_off', 'Sin resultados', 'Probá otro filtro o agregá una norma nueva con el botón +.')
            else:
                for req in rows:
                    requirement_card(req)

        @ui.refreshable
        def alerts_view() -> None:
            rows = dm.listar_alertas(empresa_id, solo_abiertas=True)
            if not rows:
                empty_state('o_notifications_off', 'Sin alertas abiertas',
                             'Tocá "Actualizar" arriba para buscar vencimientos nuevos.')
                return
            for alerta in rows:
                prioridad = dm.normalizar_criticidad(alerta.get('prioridad'))
                st = dm.PRIORIDAD_STYLE.get(prioridad, dm.PRIORIDAD_STYLE['media'])
                with ui.card().classes('lm-card w-full p-3 gap-1').style(f'border-left:4px solid {st["color"]};'):
                    with ui.row().classes('w-full items-start justify-between gap-2'):
                        ui.label(alerta.get('titulo') or '').classes('text-sm font-semibold flex-1').style(
                            f'color:{dm.PRIMARY};'
                        )
                        ui.label(st['label']).classes('text-[11px] font-semibold px-2 py-0.5 rounded-full').style(
                            f'color:{st["color"]}; background:{st["color"]}18;'
                        )
                    if alerta.get('detalle'):
                        ui.label(alerta['detalle']).classes('text-xs text-gray-500')
                    with ui.row().classes('w-full items-center justify-between pt-1'):
                        ui.label((alerta.get('fecha') or '')[:10]).classes('text-xs text-gray-400')

                        if puede_editar:
                            def _resolver(alert_id=alerta['id']) -> None:
                                if not puede_editar:
                                    return
                                dm.resolver_alerta(empresa_id, alert_id)
                                alerts_view.refresh()
                                dashboard_view.refresh()
                                alert_badge.refresh()
                                ui.notify('Alerta resuelta', color='positive')

                            ui.button('Resolver', on_click=_resolver).props('flat dense no-caps').classes('text-xs')

        @ui.refreshable
        def sites_view() -> None:
            rows = dm.listar_sedes(empresa_id)
            if not rows:
                empty_state('o_apartment', 'Sin sedes cargadas', 'Las sedes se administran desde la plataforma principal.')
                return
            for site in rows:
                with ui.card().classes('lm-card w-full p-3 gap-1'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('o_apartment').style(f'color:{dm.PRIMARY};')
                        ui.label(site.get('nombre') or '').classes('text-sm font-semibold').style(
                            f'color:{dm.PRIMARY};'
                        )
                        if not site.get('activo', 1):
                            ui.label('Inactiva').classes('text-[11px] text-gray-400 border rounded-full px-2')
                    for icon, value in (
                        ('o_place', site.get('ubicacion')),
                        ('o_map', site.get('jurisdiccion')),
                        ('o_factory', site.get('actividad')),
                    ):
                        if not value:
                            continue
                        with ui.row().classes('items-center gap-1'):
                            ui.icon(icon).classes('text-xs text-gray-400')
                            ui.label(value).classes('text-xs text-gray-500')

        with ui.tab_panels(value='dashboard').classes('w-full bg-transparent') as panels:
            with ui.tab_panel('dashboard'):
                dashboard_view()
            with ui.tab_panel('normas'):
                requirements_view()
            with ui.tab_panel('alertas'):
                alerts_view()
            with ui.tab_panel('sedes'):
                sites_view()

    def refrescar_todo() -> None:
        creadas = dm.generar_alertas_por_vencer(empresa_id, 30)
        dashboard_view.refresh()
        requirements_view.refresh()
        alerts_view.refresh()
        sites_view.refresh()
        alert_badge.refresh()
        ui.notify(
            f'Actualizado — {len(creadas)} alerta(s) nueva(s)' if creadas else 'Actualizado',
            color='positive',
        )

    # -- Bottom navigation (estilo tab bar de iOS) --------------------------
    with ui.footer().classes('px-2'):
        with ui.tabs(value='dashboard').classes('w-full max-w-xl mx-auto') as tabs:
            ui.tab('dashboard', label='Inicio', icon='o_home')
            ui.tab('normas', label='Normas', icon='o_gavel')
            with ui.tab('alertas', label='Alertas', icon='o_notifications'):
                alert_badge()
            ui.tab('sedes', label='Sedes', icon='o_apartment')

        def _sync(e) -> None:
            panels.value = e.value
            plus_button.set_visibility(e.value == 'normas' and puede_editar)
            title_label.set_text(TAB_TITLES.get(e.value, ''))

        tabs.on_value_change(_sync)
        tabs.props('active-color=primary')


render_port = os.getenv('PORT')
port = int(render_port) if render_port else int(os.getenv('MOBILE_LEGAL_MATRIX_PORT', '8600'))
# Ver nota equivalente en nicegui_v2/app.py: solo forzar `Secure`/HSTS cuando
# corre en Render (HTTPS real) -- en local rompería el login sobre http://.
running_on_render = bool(render_port)


@app.middleware('http')
async def _hsts_header(request, call_next):
    response = await call_next(request)
    if running_on_render:
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response


ui.run(
    title='IDEUS | Matriz Legal — by IDEAS Consulting',
    favicon=FAVICON,
    host='0.0.0.0',
    port=port,
    reload=False,
    native=False,
    storage_secret=os.getenv('MOBILE_LEGAL_MATRIX_STORAGE_SECRET', 'ideas-mobile-legal-matrix-poc'),
    session_middleware_kwargs={'https_only': running_on_render},
)
