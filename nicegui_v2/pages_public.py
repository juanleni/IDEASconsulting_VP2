from __future__ import annotations

from ideas_utils import enviar_correo_cotizacion


def register_public_pages(ui, deps: dict) -> None:
    public_shell = deps['public_shell']

    whatsapp_html = '''
        <a class="ideas-whatsapp-link ideas-public-whatsapp" href="https://wa.me/541170068904" target="_blank" rel="noopener noreferrer">
            <span class="ideas-whatsapp-icon">
                <svg viewBox="0 0 32 32" aria-hidden="true">
                    <circle cx="16" cy="16" r="16" fill="#25D366"></circle>
                    <path fill="#ffffff" d="M23.2 8.7A9.2 9.2 0 0 0 7.6 18.1L6 26l8.1-1.6a9.2 9.2 0 0 0 4.4 1.1h0A9.2 9.2 0 0 0 23.2 8.7zm-4.7 14.6h0a7.7 7.7 0 0 1-3.9-1.1l-.3-.2-4.8.9.9-4.7-.2-.3a7.7 7.7 0 1 1 8.3 5.4zm4.2-5.8c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1s-.7.8-.8 1c-.1.1-.3.2-.5.1a6.3 6.3 0 0 1-1.9-1.2 7.1 7.1 0 0 1-1.3-1.7c-.1-.2 0-.4.1-.5l.4-.4.2-.3c.1-.1.1-.3 0-.4l-.6-1.5c-.2-.4-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3s-.8.8-.8 2 .8 2.4.9 2.5c.1.2 1.6 2.5 3.9 3.5.5.2 1 .4 1.3.6.6.2 1.1.2 1.5.1.5-.1 1.4-.6 1.6-1.1.2-.5.2-1 .2-1.1s-.2-.2-.4-.3z"></path>
                </svg>
            </span>
            <span>Escribir por WhatsApp</span>
        </a>
    '''

    def public_styles() -> None:
        ui.add_head_html(
            '''
            <style>
            body,
            .nicegui-content,
            .q-page,
            .q-page-container,
            .q-layout {
                background: #191919 !important;
            }
            .ideas-public-shell {
                max-width: none !important;
                padding: 0 !important;
                background: #191919;
            }
            .q-page-container {
                padding-top: 0 !important;
            }
            .ideas-public-topbar {
                background: rgba(18, 18, 18, .92) !important;
                border-bottom: 1px solid rgba(255, 255, 255, .08) !important;
            }
            .ideas-public-topbar .nicegui-html {
                display: block !important;
                width: 100% !important;
            }
            .ideas-public-nav {
                display: grid !important;
                grid-template-columns: minmax(0, 1fr) auto !important;
                align-items: center !important;
                width: 100vw !important;
                max-width: none !important;
                margin: 0 !important;
                padding: 18px 72px !important;
                box-sizing: border-box !important;
                position: relative !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
            }
            .ideas-public-actions {
                margin-left: auto !important;
                justify-content: flex-end !important;
                justify-self: end !important;
                order: 2 !important;
            }
            .ideas-public-brand {
                flex: 0 0 auto !important;
            }
            .ideas-public-brand img {
                width: 62px !important;
                height: 62px !important;
            }
            .ideas-public-brand .name { color: #f8fafc !important; }
            .ideas-public-brand .tag { color: #a3a3a3 !important; }
            .ideas-public-login-link {
                background: #d6df00 !important;
                border-color: #d6df00 !important;
                color: #171717 !important;
            }
            .ideas-quote-dialog {
                background: #1e293b !important;
                color: #f8fafc !important;
            }
            .ideas-quote-dialog .q-field__control {
                background: rgba(15, 23, 42, .96) !important;
                color: #f8fafc !important;
                border: 1px solid rgba(148, 163, 184, .34) !important;
            }
            .ideas-quote-dialog .q-field__native,
            .ideas-quote-dialog .q-field__input,
            .ideas-quote-dialog textarea {
                color: #f8fafc !important;
                -webkit-text-fill-color: #f8fafc !important;
            }
            .ideas-quote-dialog input,
            .ideas-quote-dialog textarea {
                background: transparent !important;
                color: #f8fafc !important;
                caret-color: #93c5fd !important;
            }
            .ideas-quote-dialog input:-webkit-autofill,
            .ideas-quote-dialog input:-webkit-autofill:hover,
            .ideas-quote-dialog input:-webkit-autofill:focus,
            .ideas-quote-dialog textarea:-webkit-autofill {
                -webkit-text-fill-color: #f8fafc !important;
                box-shadow: 0 0 0 1000px #0f172a inset !important;
                transition: background-color 9999s ease-in-out 0s !important;
                caret-color: #93c5fd !important;
            }
            .ideas-quote-dialog .q-field__label,
            .ideas-quote-dialog .q-field__marginal,
            .ideas-quote-dialog .q-placeholder {
                color: rgba(226, 232, 240, .78) !important;
            }
            .ideas-quote-dialog .q-field--focused .q-field__label,
            .ideas-quote-dialog .q-field--float .q-field__label {
                color: #93c5fd !important;
            }
            .ideas-quote-dialog .q-field__control::before,
            .ideas-quote-dialog .q-field__control::after {
                border-color: rgba(147, 197, 253, .58) !important;
            }
            .ideas-quote-dialog .q-menu {
                background: #0f172a !important;
                color: #f8fafc !important;
            }
            .ideas-public-home {
                width: 100%;
                min-height: 100vh;
                background: #191919;
                color: #f8fafc;
                overflow: hidden;
            }
            .ideas-public-inner {
                width: min(1180px, calc(100vw - 40px));
                margin: 0 auto;
            }
            .ideas-stage {
                min-height: auto !important;
                display: grid !important;
                grid-template-columns: minmax(0, .92fr) minmax(360px, .78fr) !important;
                align-items: start !important;
                gap: 42px !important;
                padding: 0 0 46px !important;
                margin-top: 0 !important;
            }
            .ideas-kicker-dark {
                display: inline-flex;
                align-items: center;
                width: max-content;
                padding: 4px 8px;
                background: #d6df00;
                color: #171717;
                font-size: .68rem;
                font-weight: 900;
                letter-spacing: .04em;
                text-transform: uppercase;
                line-height: 1;
            }
            .ideas-stage h1 {
                margin: 18px 0 14px;
                color: #ffffff;
                font-size: clamp(3rem, 6.2vw, 5.55rem);
                line-height: .92;
                font-weight: 900;
                letter-spacing: 0;
                max-width: 680px;
            }
            .ideas-mobile-title-break {
                display: block;
            }
            .ideas-stage-lead {
                max-width: 720px;
                color: rgba(255, 255, 255, .76);
                font-size: clamp(1.05rem, 1.5vw, 1.28rem);
                line-height: 1.62;
            }
            .ideas-stage-actions {
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 12px;
                margin-top: 24px;
            }
            .ideas-primary-action,
            .ideas-secondary-action {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                min-height: 44px;
                padding: 0 18px;
                border-radius: 2px;
                font-weight: 900;
                text-decoration: none;
            }
            .ideas-primary-action {
                background: #d6df00;
                color: #171717;
            }
            .ideas-secondary-action {
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, .24);
            }
            .ideas-hero-visual {
                position: relative;
                min-height: 390px;
                align-self: start;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, .08);
                background:
                    linear-gradient(135deg, rgba(214, 223, 0, .16), transparent 32%),
                    linear-gradient(315deg, rgba(31, 126, 214, .16), transparent 34%),
                    #262626;
            }
            .ideas-hero-visual::after {
                content: "";
                position: absolute;
                inset: 0;
                background:
                    linear-gradient(90deg, rgba(255, 255, 255, .06) 1px, transparent 1px),
                    linear-gradient(180deg, rgba(255, 255, 255, .05) 1px, transparent 1px);
                background-size: 54px 54px;
                opacity: .32;
            }
            .ideas-visual-message {
                position: absolute;
                left: 28px;
                right: 28px;
                top: 28px;
                z-index: 1;
            }
            .ideas-visual-message .label {
                color: #d6df00;
                font-size: .72rem;
                font-weight: 900;
                letter-spacing: .08em;
                text-transform: uppercase;
            }
            .ideas-visual-message .title {
                max-width: 430px;
                margin-top: 12px;
                color: #ffffff;
                font-size: clamp(1.7rem, 2.45vw, 2.55rem);
                line-height: 1.04;
                font-weight: 900;
            }
            .ideas-visual-card {
                position: absolute;
                left: 24px;
                right: 24px;
                bottom: 24px;
                z-index: 1;
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 12px;
            }
            .ideas-visual-stat {
                padding: 16px;
                background: rgba(25, 25, 25, .76);
                border: 1px solid rgba(255, 255, 255, .1);
            }
            .ideas-visual-stat strong {
                display: block;
                color: #ffffff;
                font-size: 1.6rem;
                line-height: 1;
            }
            .ideas-visual-stat span {
                display: block;
                margin-top: 7px;
                color: rgba(255, 255, 255, .64);
                font-size: .82rem;
                line-height: 1.35;
            }
            .ideas-tab-wrap {
                position: sticky;
                top: 68px;
                z-index: 20;
                background: rgba(25, 25, 25, .92);
                backdrop-filter: blur(16px);
                border-top: 1px solid rgba(255, 255, 255, .08);
                border-bottom: 1px solid rgba(255, 255, 255, .08);
            }
            .ideas-tab-wrap .q-tabs {
                min-height: 76px;
                color: rgba(255, 255, 255, .68);
            }
            .ideas-tab-wrap .q-tab {
                border-radius: 0;
                min-height: 76px;
                padding: 8px 18px;
            }
            .ideas-tab-wrap .q-tab--active {
                color: #f7ff18;
                background: rgba(214, 223, 0, .08);
            }
            .ideas-tab-wrap .q-tab__icon {
                font-size: 1.35rem;
                margin-bottom: 6px;
            }
            .ideas-panels {
                background: transparent !important;
                color: #f8fafc;
            }
            .ideas-panels .q-panel {
                overflow: visible;
            }
            .ideas-section {
                padding: 86px 0;
            }
            .ideas-section-grid {
                display: grid;
                grid-template-columns: minmax(0, .86fr) minmax(0, 1.14fr);
                gap: 56px;
                align-items: start;
            }
            .ideas-section h2 {
                margin: 14px 0 16px;
                color: #ffffff;
                font-size: clamp(2rem, 4vw, 4.35rem);
                line-height: .98;
                font-weight: 900;
                letter-spacing: 0;
            }
            .ideas-copy {
                color: rgba(255, 255, 255, .73);
                font-size: 1.02rem;
                line-height: 1.78;
            }
            .ideas-about-visual {
                position: relative;
                width: 100%;
                margin-top: 28px;
                min-height: 260px;
                overflow: hidden;
                border: 1px solid rgba(255, 255, 255, .1);
                background:
                    linear-gradient(135deg, rgba(214, 223, 0, .12), transparent 34%),
                    #252525;
            }
            .ideas-about-visual img {
                width: 100%;
                height: 100%;
                min-height: 260px;
                max-height: 360px;
                object-fit: cover;
                object-position: center;
                display: block;
                filter: saturate(.92) contrast(1.04) brightness(.86);
            }
            .ideas-about-visual::after {
                content: "";
                position: absolute;
                inset: 0;
                pointer-events: none;
                background: linear-gradient(180deg, rgba(25,25,25,.02), rgba(25,25,25,.34));
            }
            .ideas-card-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
            }
            .ideas-dark-card {
                min-height: 180px;
                padding: 22px;
                background: #303030;
                border: 1px solid rgba(255, 255, 255, .08);
            }
            .ideas-dark-card .icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 34px;
                height: 34px;
                color: #d6df00;
                font-size: 1.65rem;
                margin-bottom: 14px;
            }
            .ideas-dark-card h3 {
                margin: 0 0 8px;
                color: #ffffff;
                font-size: 1.18rem;
                font-weight: 850;
            }
            .ideas-dark-card p {
                margin: 0;
                color: rgba(255, 255, 255, .63);
                line-height: 1.62;
            }
            .ideas-process {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 0;
                margin-top: 34px;
                border: 1px solid rgba(255, 255, 255, .1);
            }
            .ideas-step {
                min-height: 210px;
                padding: 24px;
                background: #292929;
                border-right: 1px solid rgba(255, 255, 255, .1);
            }
            .ideas-step:last-child { border-right: 0; }
            .ideas-step .number {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 38px;
                height: 38px;
                margin-bottom: 18px;
                background: #d6df00;
                color: #171717;
                font-weight: 900;
            }
            .ideas-step h3 {
                margin: 0 0 10px;
                color: #fff;
                font-size: 1.12rem;
                font-weight: 850;
            }
            .ideas-step p {
                margin: 0;
                color: rgba(255, 255, 255, .62);
                line-height: 1.58;
            }
            .ideas-wide-image {
                position: relative;
                min-height: 230px;
                margin: 28px 0 0;
                overflow: hidden;
                border-top: 1px solid rgba(255, 255, 255, .08);
                border-bottom: 1px solid rgba(255, 255, 255, .08);
                background:
                    linear-gradient(90deg, rgba(214, 223, 0, .16), transparent 28%, rgba(31, 126, 214, .12)),
                    #232323;
            }
            .ideas-wide-image .overlay {
                position: absolute;
                inset: 0;
                display: grid;
                place-items: center;
                background:
                    linear-gradient(90deg, rgba(25,25,25,.84), rgba(25,25,25,.45), rgba(25,25,25,.84)),
                    linear-gradient(90deg, rgba(255,255,255,.08) 1px, transparent 1px);
                background-size: auto, 70px 70px;
            }
            .ideas-wide-stats {
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                width: min(780px, calc(100vw - 40px));
                gap: 36px;
                text-align: center;
            }
            .ideas-wide-stats strong {
                display: block;
                color: #fff;
                font-size: 2.1rem;
                line-height: 1;
            }
            .ideas-wide-stats span {
                display: block;
                margin-top: 8px;
                color: rgba(255, 255, 255, .7);
                font-size: .86rem;
                line-height: 1.36;
            }
            .ideas-platform-band {
                display: grid;
                grid-template-columns: minmax(0, 1fr) 380px;
                gap: 28px;
                align-items: stretch;
                margin-top: 30px;
            }
            .ideas-platform-panel {
                padding: 28px;
                background: #303030;
                border-left: 6px solid #d6df00;
            }
            .ideas-platform-panel h3 {
                margin: 0 0 12px;
                color: #ffffff;
                font-size: 1.45rem;
                font-weight: 900;
            }
            .ideas-platform-panel p {
                margin: 0;
                color: rgba(255, 255, 255, .68);
                line-height: 1.75;
            }
            .ideas-public-whatsapp {
                color: #f8fafc !important;
                border-radius: 2px !important;
                background: rgba(37, 211, 102, .14) !important;
            }
            @media (max-width: 980px) {
                .ideas-public-nav {
                    grid-template-columns: 1fr !important;
                    gap: 14px !important;
                    padding: 14px 18px !important;
                    left: 0 !important;
                    transform: none !important;
                    width: 100% !important;
                }
                .ideas-public-brand {
                    width: 100% !important;
                    min-width: 0 !important;
                }
                .ideas-public-brand img {
                    width: 42px !important;
                    height: 42px !important;
                }
                .ideas-public-brand .name {
                    font-size: 1rem !important;
                    line-height: 1.05 !important;
                }
                .ideas-public-brand .tag {
                    font-size: .78rem !important;
                }
                .ideas-public-actions {
                    width: 100% !important;
                    margin-left: 0 !important;
                    justify-content: space-between !important;
                    justify-self: stretch !important;
                    gap: 12px !important;
                }
                .ideas-public-login-link {
                    min-height: 40px !important;
                    padding: 0 14px !important;
                    flex: 1 1 auto !important;
                    justify-content: center !important;
                }
                .ideas-whatsapp-link.topbar {
                    flex: 0 0 auto !important;
                    font-size: .92rem !important;
                }
                .ideas-public-inner {
                    width: min(100% - 28px, 1180px) !important;
                }
                .ideas-stage,
                .ideas-section-grid,
                .ideas-platform-band {
                    grid-template-columns: 1fr !important;
                }
                .ideas-process,
                .ideas-card-grid,
                .ideas-visual-card,
                .ideas-wide-stats {
                    grid-template-columns: 1fr !important;
                }
                .ideas-stage {
                    gap: 24px !important;
                    padding: 18px 0 34px !important;
                }
                .ideas-stage h1 {
                    font-size: clamp(3.2rem, 17vw, 5.1rem);
                    line-height: .88;
                    max-width: 100%;
                    overflow-wrap: anywhere;
                }
                .ideas-mobile-title-break {
                    display: block;
                }
                .ideas-mobile-title-consulting {
                    display: block;
                    font-size: .86em;
                    line-height: .9;
                    white-space: nowrap;
                }
                .ideas-stage-lead {
                    font-size: 1rem;
                    line-height: 1.58;
                }
                .ideas-stage-actions {
                    flex-direction: column;
                    align-items: stretch;
                }
                .ideas-primary-action,
                .ideas-secondary-action {
                    width: 100%;
                    justify-content: center;
                }
                .ideas-hero-visual {
                    min-height: 360px;
                }
                .ideas-visual-message {
                    left: 18px;
                    right: 18px;
                    top: 18px;
                }
                .ideas-visual-message .title {
                    font-size: clamp(1.55rem, 8vw, 2.25rem);
                    max-width: 100%;
                }
                .ideas-visual-card {
                    left: 18px;
                    right: 18px;
                    bottom: 18px;
                }
                .ideas-visual-stat {
                    padding: 13px 14px;
                }
                .ideas-visual-stat strong {
                    font-size: 1.4rem;
                }
                .ideas-tab-wrap {
                    position: static;
                    overflow-x: auto;
                }
                .ideas-tab-wrap .q-tabs {
                    min-height: 62px;
                    justify-content: flex-start;
                    width: max-content;
                    min-width: 100%;
                }
                .ideas-tab-wrap .q-tab {
                    min-height: 62px;
                    padding: 7px 12px;
                    font-size: .78rem;
                }
                .ideas-section {
                    padding: 56px 0;
                }
                .ideas-section-grid {
                    gap: 28px;
                }
                .ideas-section h2 {
                    font-size: clamp(2rem, 11vw, 3.1rem);
                }
                .ideas-copy {
                    font-size: .98rem;
                    line-height: 1.68;
                }
                .ideas-about-visual,
                .ideas-about-visual img {
                    min-height: 220px;
                }
                .ideas-dark-card,
                .ideas-step,
                .ideas-platform-panel {
                    padding: 20px;
                    min-height: auto;
                }
                .ideas-process {
                    margin-top: 24px;
                }
                .ideas-wide-image,
                .ideas-wide-image .overlay {
                    min-height: 260px;
                }
                .ideas-wide-stats {
                    gap: 20px;
                }
                .ideas-step {
                    border-right: 0;
                    border-bottom: 1px solid rgba(255, 255, 255, .1);
                }
                .ideas-step:last-child {
                    border-bottom: 0;
                }
            }
            @media (max-width: 520px) {
                .ideas-public-actions {
                    align-items: center !important;
                }
                .ideas-whatsapp-link.topbar span:last-child {
                    display: none;
                }
                .ideas-whatsapp-icon,
                .ideas-whatsapp-icon svg {
                    width: 30px;
                    height: 30px;
                }
                .ideas-kicker-dark {
                    font-size: .62rem;
                }
                .ideas-stage h1 {
                    font-size: clamp(2.7rem, 18vw, 3.9rem);
                }
                .ideas-mobile-title-consulting {
                    font-size: .78em;
                }
                .ideas-hero-visual {
                    min-height: 430px;
                }
            }
            </style>
            '''
        )

    def card(icon: str, title: str, text: str) -> None:
        with ui.element('article').classes('ideas-dark-card'):
            ui.icon(icon).classes('icon')
            ui.html(f'<h3>{title}</h3><p>{text}</p>')

    @ui.page('/')
    def website_home_page() -> None:
        shell_container = public_shell('Inicio')
        public_styles()
        with shell_container:
            with ui.element('main').classes('ideas-public-home'):
                with ui.element('section').classes('ideas-public-inner ideas-stage'):
                    with ui.element('div'):
                        ui.html('<div class="ideas-kicker-dark">Consultoría + SaaS</div>')
                        ui.html('<h1>IDEAS<br class="ideas-mobile-title-break"><span class="ideas-mobile-title-consulting">CONSULTING</span></h1>')
                        ui.html(
                            '''
                            <p class="ideas-stage-lead">
                            Transformamos procesos en resultados sostenibles. Integramos experiencia industrial,
                            metodología de gestión y plataforma digital para que cada decisión tenga trazabilidad,
                            evidencia y foco operativo.
                            </p>
                            '''
                        )
                        with ui.element('div').classes('ideas-stage-actions'):
                            ui.html('<a class="ideas-primary-action" href="/plataforma">Ingresar a plataforma</a>')
                            ui.html('<a class="ideas-secondary-action" href="#contenido">Conocer propuesta</a>')
                    with ui.element('aside').classes('ideas-hero-visual'):
                        ui.html(
                            '''
                            <div class="ideas-visual-message">
                                <div class="label">Sistema de gestión vivo</div>
                                <div class="title">Diagnóstico, acción y seguimiento en un solo flujo.</div>
                            </div>
                            <div class="ideas-visual-card">
                                <div class="ideas-visual-stat"><strong>20+</strong><span>Años de experiencia industrial</span></div>
                                <div class="ideas-visual-stat"><strong>100%</strong><span>Personalización SaaS por cliente</span></div>
                                <div class="ideas-visual-stat"><strong>IA</strong><span>Inteligencia aplicada a gestión</span></div>
                            </div>
                            '''
                        )

                with ui.element('div').classes('ideas-tab-wrap').props('id=contenido'):
                    with ui.element('div').classes('ideas-public-inner'):
                        with ui.tabs().classes('w-full justify-between') as tabs:
                            tab_about = ui.tab('Sobre Nosotros', icon='domain').props('no-caps')
                            tab_proposal = ui.tab('Nuestra Propuesta', icon='tips_and_updates').props('no-caps')
                            tab_services = ui.tab('Soluciones', icon='cases').props('no-caps')
                            tab_method = ui.tab('Metodología', icon='account_tree').props('no-caps')
                            tab_platform = ui.tab('Plataforma', icon='laptop_mac').props('no-caps')
                            tab_contact = ui.tab('Contacto', icon='forum').props('no-caps')

                with ui.tab_panels(tabs, value=tab_about).classes('ideas-panels'):
                    with ui.tab_panel(tab_about).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            with ui.element('div').classes('ideas-section-grid'):
                                with ui.element('div'):
                                    ui.html('<div class="ideas-kicker-dark">Sobre Nosotros</div>')
                                    ui.html('<h2>Cada cliente es un socio estratégico.</h2>')
                                    ui.html(
                                        '''
                                        <div class="ideas-about-visual">
                                            <img src="/assets/Data/kpi_dashboard_industrial.png"
                                                 alt="Tablero industrial de indicadores KPI"
                                                 onerror="this.parentElement.style.display='none';">
                                        </div>
                                        '''
                                    )
                                with ui.element('div'):
                                    ui.html(
                                        '''
                                        <p class="ideas-copy">
                                        En IDEAS queremos ser tu complemento ideal para avanzar al siguiente nivel:
                                        ordenar la gestión, optimizar procesos, reducir costos y tomar mejores decisiones
                                        con información clara. Trabajamos cerca de cada equipo, entendiendo su realidad,
                                        sus ritmos y sus desafíos, para construir mejoras que se puedan sostener en el día a día.
                                        </p>
                                        '''
                                    )
                                    with ui.element('div').classes('ideas-card-grid mt-6'):
                                        card('factory', 'Trayectoria industrial', 'Más de dos décadas acompañando equipos, procesos y sistemas de gestión.')
                                        card('hub', 'Visión integrada', 'Calidad, ambiente, SST, riesgos, procesos, KPIs y documentos conectados.')
                                        card('psychology', 'IA aplicada', 'Asistencia inteligente para analizar requisitos, causas, riesgos y oportunidades.')
                                        card('visibility', 'Gestión visible', 'Información operativa clara para sostener seguimiento y mejora continua.')

                    with ui.tab_panel(tab_proposal).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            with ui.element('div').classes('ideas-section-grid'):
                                with ui.element('div'):
                                    ui.html('<div class="ideas-kicker-dark">Nuestra Propuesta</div>')
                                    ui.html('<h2>De la consultoría al software, en una sola experiencia.</h2>')
                                with ui.element('div'):
                                    ui.html(
                                        '''
                                        <p class="ideas-copy">
                                        No entregamos solamente diagnósticos o reportes. Diseñamos el sistema de gestión,
                                        acompañamos la implementación y dejamos una plataforma SaaS preparada para sostener
                                        el trabajo diario con trazabilidad, responsables, vencimientos e indicadores.
                                        </p>
                                        '''
                                    )
                                    with ui.element('div').classes('ideas-platform-band'):
                                        ui.html(
                                            '''
                                            <div class="ideas-platform-panel">
                                                <h3>Consultoría + SaaS</h3>
                                                <p>
                                                El mismo equipo que entiende la operación configura la herramienta que la
                                                acompaña. Eso reduce fricción, evita plantillas genéricas y convierte cada
                                                avance en una práctica gestionable.
                                                </p>
                                            </div>
                                            '''
                                        )
                                        ui.html(
                                            '''
                                            <div class="ideas-platform-panel">
                                                <h3>Resultados medibles</h3>
                                                <p>
                                                Diagnósticos, planes de acción, mapas de procesos, riesgos, KPIs y reportes
                                                quedan conectados para tomar decisiones con evidencia.
                                                </p>
                                            </div>
                                            '''
                                        )

                    with ui.tab_panel(tab_services).classes('p-0'):
                        dialog_cotizacion = ui.dialog()

                        def procesar_cotizacion() -> None:
                            nombre = str(inp_nombre.value or '').strip()
                            correo = str(inp_correo.value or '').strip()
                            telefono = str(inp_telefono.value or '').strip()
                            if not nombre or (not correo and not telefono):
                                ui.notify('Por favor, completa tus datos de contacto.', type='warning')
                                return
                            contacto = f"Correo: {correo or 'No informado'} | Teléfono: {telefono or 'No informado'}"

                            enviar_correo_cotizacion(
                                nombre,
                                contacto,
                                sel_servicio.value,
                                txt_detalles.value,
                            )
                            ui.notify('¡Gracias! Hemos recibido tu solicitud y te contactaremos a la brevedad.', type='positive')
                            dialog_cotizacion.close()
                            inp_nombre.value = ''
                            inp_correo.value = ''
                            inp_telefono.value = ''
                            sel_servicio.value = None
                            txt_detalles.value = ''

                        with dialog_cotizacion:
                            with ui.card().classes('ideas-quote-dialog bg-slate-800 border border-slate-700 shadow-2xl p-8 rounded-2xl text-white w-[500px] max-w-[95vw]'):
                                ui.label('¡Hola! Contanos qué necesitas.').classes('text-2xl font-bold text-white mb-2')
                                inp_nombre = ui.input('Tu nombre / Empresa').classes('w-full mb-3').props('outlined dark')
                                inp_correo = ui.input('Correo de contacto').classes('w-full mb-3').props('outlined dark type=email')
                                inp_telefono = ui.input('Número de contacto').classes('w-full mb-3').props('outlined dark type=tel')
                                sel_servicio = ui.select(
                                    ['Soporte Operativo y Sorting', 'Consultoría / Auditoría', 'Plataforma SaaS', 'Otro'],
                                    label='¿En qué te podemos ayudar?',
                                ).classes('w-full mb-3').props('outlined dark')
                                txt_detalles = ui.textarea('Detalles (Ej: tipo de trabajo, cantidad de personas, fechas...)').classes('w-full mb-4').props('outlined dark')
                                ui.button(
                                    'Enviar solicitud',
                                    on_click=procesar_cotizacion,
                                ).classes('w-full rounded-xl bg-blue-600 text-white font-bold py-2')
                                ui.button('Cerrar', on_click=dialog_cotizacion.close).props('flat text-color=grey-4 w-full mt-2')

                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            ui.html('<div class="ideas-kicker-dark">Servicios y Soluciones</div>')
                            ui.html('<h2>Consultoría potenciada por tecnología.</h2>')
                            with ui.element('div').classes('ideas-card-grid mt-8'):
                                services = [
                                    ('assignment', 'Sistemas de Gestión', 'Ordenamos y estructuramos sistemas de gestión con foco en requisitos, evidencia y operación real.'),
                                    ('bolt', 'Aceleración de decisiones', 'Convertimos datos dispersos en tableros, prioridades, alertas y planes accionables.'),
                                    ('sync_alt', 'Mejora continua', 'Acompañamos rutinas, acciones correctivas, problemas 8D y seguimiento de compromisos.'),
                                    ('cloud_done', 'Plataforma SaaS', 'Un entorno digital personalizado para cada cliente, con módulos vivos y trazabilidad total.'),
                                    ('engineering', 'Soporte Operativo y Sorting', 'Facilitación de personal calificado para tareas de inspección, sorting y retrabajos en su planta o en instalaciones del cliente. Gestionamos integralmente los requisitos de ingreso, reportes de avance, indicadores de calidad (KPIs) y trazabilidad del trabajo.'),
                                ]
                                for icon, title, text in services:
                                    card(icon, title, text)
                                with ui.element('article').classes('bg-slate-800/80 border-2 border-blue-500/50 shadow-xl p-6 rounded-xl text-white cursor-pointer hover:bg-slate-700 transition-all').on('click', lambda _e: dialog_cotizacion.open()):
                                    ui.icon('request_quote').classes('text-blue-300 text-3xl mb-4')
                                    ui.label('¿Necesitas una cotización a medida?').classes('text-lg font-bold text-white')
                                    ui.label('Escríbenos y contanos qué estás buscando. Somos rápidos, directos y nos adaptamos a tu necesidad operativa.').classes('text-slate-300 mt-3 leading-relaxed')
                                    ui.button('Solicitar ahora', on_click=dialog_cotizacion.open).props('outline color=blue').classes('mt-4 rounded-full')

                    with ui.tab_panel(tab_method).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            ui.html('<div class="ideas-kicker-dark">Metodología</div>')
                            ui.html('<h2>Nuestro proceso en 4 pasos.</h2>')
                            ui.html(
                                '''
                                <p class="ideas-copy">
                                Cada etapa está pensada para generar valor tangible y sostenerlo: entender el estado actual,
                                diseñar el camino, implementar con los equipos y medir la evolución.
                                </p>
                                '''
                            )
                            with ui.element('div').classes('ideas-process'):
                                for number, title, text in [
                                    ('01', 'Diagnóstico', 'Relevamos madurez, brechas, evidencias y riesgos críticos.'),
                                    ('02', 'Diseno', 'Definimos estructura, prioridades, responsables y herramientas.'),
                                    ('03', 'Implementación', 'Acompañamos ejecución en planta, procesos y rutinas de gestión.'),
                                    ('04', 'Seguimiento', 'Medimos avance, ajustamos desvio y sostenemos mejora continua.'),
                                ]:
                                    ui.html(f'<article class="ideas-step"><div class="number">{number}</div><h3>{title}</h3><p>{text}</p></article>')

                            with ui.element('div').classes('ideas-wide-image'):
                                ui.html(
                                    '''
                                    <div class="overlay">
                                        <div class="ideas-wide-stats">
                                            <div><strong>20+</strong><span>Años de experiencia</span></div>
                                            <div><strong>100%</strong><span>Soluciones configurables</span></div>
                                            <div><strong>IA</strong><span>Soporte inteligente</span></div>
                                        </div>
                                    </div>
                                    '''
                                )

                    with ui.tab_panel(tab_platform).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            with ui.element('div').classes('ideas-section-grid'):
                                with ui.element('div'):
                                    ui.html('<div class="ideas-kicker-dark">Plataforma Digital</div>')
                                    ui.html('<h2>Una plataforma viva para cada cliente.</h2>')
                                    ui.html(
                                        '''
                                        <p class="ideas-copy">
                                        La plataforma centraliza procesos, diagnósticos, documentos, indicadores,
                                        riesgos, ambiente, calidad, SST y usuarios en un entorno único.
                                        </p>
                                        '''
                                    )
                                with ui.element('div').classes('ideas-card-grid'):
                                    card('timeline', 'Trazabilidad total', 'Cada acción, decisión y resultado queda registrado y disponible.')
                                    card('psychology', 'IA integrada', 'Asistencia para requisitos, causas, matrices legales y análisis de gestión.')
                                    card('hub', 'Orden operativo', 'Procesos, indicadores, documentos y planes conectados en un solo lugar.')
                                    card('rocket_launch', 'Evolución continua', 'El SaaS crece junto a la organización y sus prioridades reales.')

                    with ui.tab_panel(tab_contact).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            with ui.element('div').classes('ideas-section-grid'):
                                with ui.element('div'):
                                    ui.html('<div class="ideas-kicker-dark">Contacto</div>')
                                    ui.html('<h2>Conversemos sobre tu sistema de gestión.</h2>')
                                with ui.element('div'):
                                    ui.html(
                                        '''
                                        <p class="ideas-copy">
                                        Podemos revisar tu punto de partida, identificar brechas y definir un camino
                                        concreto para ordenar procesos, evidencia y seguimiento.
                                        </p>
                                        '''
                                    )
                                    ui.html(whatsapp_html)

    @ui.page('/servicios')
    def website_services_page() -> None:
        shell_container = public_shell('Servicios')
        public_styles()
        with shell_container:
            with ui.element('main').classes('ideas-public-home'):
                with ui.element('section').classes('ideas-public-inner ideas-section'):
                    ui.html('<div class="ideas-kicker-dark">Servicios</div>')
                    ui.html('<h2>Consultoría potenciada por tecnología.</h2>')

    @ui.page('/metodologia')
    def website_method_page() -> None:
        shell_container = public_shell('Metodología')
        public_styles()
        with shell_container:
            with ui.element('main').classes('ideas-public-home'):
                with ui.element('section').classes('ideas-public-inner ideas-section'):
                    ui.html('<div class="ideas-kicker-dark">Metodología</div>')
                    ui.html('<h2>Nuestro proceso en 4 pasos.</h2>')

    @ui.page('/contacto')
    def website_contact_page() -> None:
        shell_container = public_shell('Contacto')
        public_styles()
        with shell_container:
            with ui.element('main').classes('ideas-public-home'):
                with ui.element('section').classes('ideas-public-inner ideas-section'):
                    ui.html('<div class="ideas-kicker-dark">Contacto</div>')
                    ui.html('<h2>Conversemos sobre tu sistema de gestión.</h2>')
                    ui.html(whatsapp_html)
