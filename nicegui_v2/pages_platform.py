from __future__ import annotations


def register_platform_pages(ui, app, deps: dict) -> None:
    public_shell = deps['public_shell']
    shell = deps['shell']
    ensure_platform_access = deps['ensure_platform_access']
    get_banner_url = deps['get_banner_url']
    get_logo_url = deps['get_logo_url']
    quick_card = deps['quick_card']
    PLATFORM_USER = deps['PLATFORM_USER']
    PLATFORM_PASSWORD = deps['PLATFORM_PASSWORD']

    @ui.page('/plataforma')
    def platform_login_page() -> None:
        app.storage.user['platform_auth'] = False
        shell_container = public_shell('Acceso plataforma')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Acceso interno</div><h2>Plataforma IDEAS</h2><p>Ingresá con tus credenciales para acceder a la carga de empresas, diagnósticos, resultados e historial.</p></div>')
            with ui.card().classes('ideas-public-card ideas-login-card'):
                ui.html('<div class="ideas-login-title">Ingreso del equipo IDEAS</div><div class="ideas-login-note">Este acceso está reservado para el equipo interno. Una vez autenticado, podrás administrar empresas, diagnósticos, resultados e historial desde la plataforma.</div>')
                usuario = ui.input('Usuario').classes('w-full').props('outlined')
                password = ui.input('Contraseña', password=True, password_toggle_button=True).classes('w-full').props('outlined')

                def do_login() -> None:
                    if (usuario.value or '').strip() == PLATFORM_USER and (password.value or '').strip() == PLATFORM_PASSWORD:
                        app.storage.user['platform_auth'] = True
                        ui.notify('Acceso concedido.', type='positive')
                        ui.navigate.to('/dashboard')
                    else:
                        ui.notify('Usuario o contraseña incorrectos.', type='negative')

                with ui.row().classes('w-full justify-between items-center mt-2'):
                    ui.button('Volver al sitio', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat')
                    ui.button('Ingresar', icon='login', on_click=do_login).props('unelevated color=primary')

    @ui.page('/dashboard')
    def home_page() -> None:
        if not ensure_platform_access():
            return
        shell_container = shell('Inicio')
        banner = get_banner_url()
        logo = get_logo_url()
        with shell_container:
            with ui.column().classes('w-full gap-6'):
                ui.html(
                    f'''<div class="ideas-hero-card w-full"><div style="position:relative;z-index:1;"><div class="ideas-hero-brand">{f'<img src="{logo}" alt="IDEAS logo" />' if logo else ''}<div><div class="brand-name">IDEAS Consulting</div><div class="brand-tag">Consultoría estratégica para dirección, eficiencia y evolución organizacional.</div></div></div><div class="ideas-kicker">IDEAS Executive Flow</div><div class="ideas-title">Diagnóstico empresarial con visión estratégica.</div><div class="ideas-subtitle">Centralizá el análisis de tu organización con una experiencia más ejecutiva, visual y dinámica, pensada para dirección, consultoría y toma de decisiones rápida.</div><div style="margin-top:10px;"><span class="ideas-chip">Compromiso</span><span class="ideas-chip">Trabajo en equipo</span><span class="ideas-chip">Eficiencia</span><span class="ideas-chip">Dirección</span></div></div><div style="position:relative;z-index:1;">{f'<img src="{banner}" style="width:100%;border-radius:24px;box-shadow:0 20px 40px rgba(15,23,42,0.14);object-fit:cover;min-height:320px;" />' if banner else quick_card('Portada institucional', 'Imagen principal', 'Agregá ideas_home_banner.png en la raíz o en Data para reforzar la identidad visual.')}</div></div>'''
                )
                ui.html(f'''<div class="ideas-grid-3">{quick_card('Flujo', 'Carga simple', 'Empresas, diagnósticos y resultados conectados en un mismo entorno.')}{quick_card('Enfoque', 'Visión ejecutiva', 'Lectura de madurez, focos prioritarios y plan de acción sugerido.')}{quick_card('Estado', 'V2 en NiceGUI', 'Base desacoplada de Streamlit y preparada para seguir creciendo.')}</div>''')
                with ui.row().classes('w-full gap-3 justify-end'):
                    ui.button('Cargar empresa', icon='apartment', on_click=lambda: ui.navigate.to('/empresas')).props('unelevated color=primary')
                    ui.button('Sistema de gestión', icon='account_tree', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('outline color=primary')
                    ui.button('Nuevo diagnóstico', icon='assignment_add', on_click=lambda: ui.navigate.to('/diagnostico')).props('outline color=primary')
