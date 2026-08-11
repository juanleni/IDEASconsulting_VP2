from __future__ import annotations

from ideas_utils import enviar_correo_cotizacion, ideus_wordmark_html


def register_public_pages(ui, deps: dict) -> None:
    public_shell = deps['public_shell']
    platform_enabled = bool(deps.get('platform_enabled', True))

    whatsapp_html = '''
        <a href="https://wa.me/541170068904"
           target="_blank"
           rel="noopener noreferrer"
           style="display:inline-flex;align-items:center;gap:8px;margin-top:14px;color:#cbd5e1;text-decoration:none;font-size:.95rem;">
            <svg viewBox="0 0 32 32" width="20" height="20" aria-hidden="true">
                <circle cx="16" cy="16" r="16" fill="#25D366"></circle>
                <path fill="#ffffff" d="M23.2 8.7A9.2 9.2 0 0 0 7.6 18.1L6 26l8.1-1.6a9.2 9.2 0 0 0 4.4 1.1h0A9.2 9.2 0 0 0 23.2 8.7zm-4.7 14.6h0a7.7 7.7 0 0 1-3.9-1.1l-.3-.2-4.8.9.9-4.7-.2-.3a7.7 7.7 0 1 1 8.3 5.4zm4.2-5.8c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1s-.7.8-.8 1c-.1.1-.3.2-.5.1a6.3 6.3 0 0 1-1.9-1.2 7.1 7.1 0 0 1-1.3-1.7c-.1-.2 0-.4.1-.5l.4-.4.2-.3c.1-.1.1-.3 0-.4l-.6-1.5c-.2-.4-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3s-.8.8-.8 2 .8 2.4.9 2.5c.1.2 1.6 2.5 3.9 3.5.5.2 1 .4 1.3.6.6.2 1.1.2 1.5.1.5-.1 1.4-.6 1.6-1.1.2-.5.2-1 .2-1.1s-.2-.2-.4-.3z"></path>
            </svg>
            <span>Conversemos por WhatsApp!</span>
        </a>
    '''

    linkedin_html = '''
        <a href="https://www.linkedin.com/company/ideas-consulting-argentina"
           target="_blank"
           rel="noopener noreferrer"
           style="display:inline-flex;align-items:center;gap:8px;margin-top:14px;color:#cbd5e1;text-decoration:none;font-size:.95rem;">
            <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
                <path fill="#0A66C2" d="M4.98 3.5C4.98 4.88 3.87 6 2.5 6S0 4.88 0 3.5 1.12 1 2.5 1 4.98 2.12 4.98 3.5zM.5 8h4V23h-4V8zm7 0h3.8v2.1h.1c.5-1 1.9-2.1 3.9-2.1 4.2 0 5 2.8 5 6.3V23h-4v-7.6c0-1.8 0-4.2-2.6-4.2s-3 2-3 4V23h-4V8z"/>
            </svg>
            <span>IDEAS Consulting Argentina</span>
        </a>
    '''

    def render_contact_request_form() -> None:
        service_options = [
            'Sistemas de gestión',
            'Consultoría ISO 9001',
            'Consultoría ISO 14001',
            'Consultoría ISO 45001',
            'Consultoría IATF 16949',
            'Auditorías de proceso',
            'Sorting y controles 100%',
            'Soporte operativo en planta',
            'Plataforma SaaS',
            'Otro',
        ]
        with ui.card().classes('ideas-dark-card mt-6'):
            ui.html('<h3>Enviarnos una solicitud</h3>')
            ui.html('<p class="ideas-copy">Completá los datos y te respondemos a la brevedad.</p>')
            with ui.grid(columns=2).classes('w-full gap-3'):
                in_nombre = ui.input('Nombre').props('outlined dark').classes('w-full')
                in_apellido = ui.input('Apellido').props('outlined dark').classes('w-full')
                in_empresa = ui.input('Empresa').props('outlined dark').classes('w-full')
                in_rubro = ui.input('Rubro').props('outlined dark').classes('w-full')
                in_servicio = ui.select(service_options, label='Servicio').props('outlined dark').classes('w-full')
                in_telefono = ui.input('Número de contacto').props('outlined dark type=tel').classes('w-full')
                in_correo = ui.input('Correo de contacto').props('outlined dark type=email').classes('w-full')
            in_solicitud = ui.textarea('Solicitud / Pedido').props('outlined dark autogrow').classes('w-full mt-3')
            success_msg = ui.label('Mensaje enviado con éxito. Gracias por contactarnos.').classes('text-green-300 text-sm mt-2')
            success_msg.visible = False

            def submit_contact_request() -> None:
                nombre = str(in_nombre.value or '').strip()
                apellido = str(in_apellido.value or '').strip()
                empresa = str(in_empresa.value or '').strip()
                rubro = str(in_rubro.value or '').strip()
                servicio = str(in_servicio.value or '').strip() or 'Otro'
                telefono = str(in_telefono.value or '').strip()
                correo = str(in_correo.value or '').strip()
                solicitud = str(in_solicitud.value or '').strip()

                if not nombre or not apellido or not empresa or not servicio or (not telefono and not correo) or not solicitud:
                    success_msg.visible = False
                    ui.notify('Completá nombre, apellido, empresa, servicio, solicitud y al menos un medio de contacto.', type='warning')
                    return

                nombre_empresa = f'{nombre} {apellido} - {empresa}'
                contacto = f'Rubro: {rubro or "No informado"} | Tel: {telefono or "No informado"} | Correo: {correo or "No informado"}'
                detalles = (
                    f'Empresa: {empresa}\n'
                    f'Rubro: {rubro or "No informado"}\n'
                    f'Nombre: {nombre}\n'
                    f'Apellido: {apellido}\n'
                    f'Teléfono: {telefono or "No informado"}\n'
                    f'Correo: {correo or "No informado"}\n\n'
                    f'Solicitud:\n{solicitud}'
                )
                result = enviar_correo_cotizacion(
                    nombre_empresa,
                    contacto,
                    servicio,
                    detalles,
                    destinatario='ideasconsulting@gmail.com',
                )
                if result.get('ok'):
                    ui.notify('Solicitud enviada. Gracias, te contactamos pronto.', type='positive')
                    success_msg.visible = True
                    in_nombre.value = ''
                    in_apellido.value = ''
                    in_empresa.value = ''
                    in_rubro.value = ''
                    in_servicio.value = None
                    in_telefono.value = ''
                    in_correo.value = ''
                    in_solicitud.value = ''
                else:
                    success_msg.visible = False
                    ui.notify('No se pudo enviar por SMTP. Revisá configuración de correo.', type='negative')

            ui.button('Enviar solicitud', on_click=submit_contact_request).props('unelevated color=primary').classes('mt-4')

    def public_styles() -> None:
        ui.add_head_html(
            '''
            <style>
            body,
            .nicegui-content,
            .q-page,
            .q-page-container,
            .q-layout {
                background: #0F172A !important;
                font-family: Aptos, "Segoe UI Variable", "Segoe UI", sans-serif !important;
            }
            .ideas-public-shell {
                max-width: none !important;
                padding: 0 !important;
                background: #0F172A;
            }
            .q-page-container {
                padding-top: 0 !important;
            }
            .ideas-public-topbar {
                background: rgba(15, 23, 42, .92) !important;
                border-bottom: 1px solid rgba(255, 255, 255, .08) !important;
            }
            .ideas-public-topbar .nicegui-html {
                display: block !important;
                width: 100% !important;
            }
            .ideas-public-nav {
                display: grid !important;
                grid-template-columns: auto minmax(0, 1fr) auto !important;
                align-items: center !important;
                gap: 1.4rem !important;
                width: 100vw !important;
                max-width: none !important;
                margin: 0 !important;
                padding: 18px 72px !important;
                box-sizing: border-box !important;
                position: relative !important;
                left: 50% !important;
                transform: translateX(-50%) !important;
            }
            .ideas-public-menu {
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                gap: 1.6rem !important;
                order: 1 !important;
            }
            .ideas-public-menu-link {
                display: inline-flex !important;
                align-items: center !important;
                gap: 6px !important;
                text-decoration: none !important;
                color: rgba(255, 255, 255, .72) !important;
                font-weight: 700 !important;
                font-size: .94rem !important;
                padding: 8px 0 !important;
                white-space: nowrap !important;
            }
            .ideas-public-menu-link .material-icons { font-size: 1.1rem !important; }
            .ideas-public-menu-link:hover, .ideas-public-menu-link.active {
                color: #00D6A6 !important;
            }
            .ideas-public-actions {
                margin-left: auto !important;
                justify-content: flex-end !important;
                justify-self: end !important;
                order: 2 !important;
            }
            .ideas-public-brand {
                flex: 0 0 auto !important;
                order: 0 !important;
            }
            .ideas-public-brand img {
                width: 62px !important;
                height: 62px !important;
            }
            .ideas-public-brand .name { color: #f8fafc !important; }
            .ideas-public-brand .tag { color: #a3a3a3 !important; }
            .ideus-wordmark {
                --brand-font-size-primary: 1.05rem;
                --brand-color: #f8fafc;
                --brand-color-secondary: rgba(255, 255, 255, .56);
                display: flex;
                flex-direction: column;
                line-height: 1.08;
                gap: .22em;
            }
            .ideus-wordmark .ideus-wordmark-name {
                font-weight: 500;
                letter-spacing: .1em;
                color: var(--brand-color) !important;
                font-size: var(--brand-font-size-primary);
                white-space: nowrap;
            }
            .ideus-wordmark .ideus-wordmark-by {
                font-weight: 700;
                letter-spacing: .12em;
                text-transform: uppercase;
                color: var(--brand-color-secondary) !important;
                font-size: max(calc(var(--brand-font-size-primary) * .3), 8px);
                white-space: nowrap;
            }
            .ideus-wordmark--on-dark { --brand-color: #f8fafc; --brand-color-secondary: rgba(255, 255, 255, .56); }
            .ideus-wordmark--topbar { --brand-font-size-primary: 1.08rem; }
            .ideus-wordmark--login { --brand-font-size-primary: 1.55rem; }
            .ideus-wordmark--hero {
                --brand-font-size-primary: clamp(2.4rem, 5.4vw, 3.6rem);
                margin: 6px 0 2px;
            }
            .ideas-public-login-link {
                background: #00D6A6 !important;
                border-color: #00D6A6 !important;
                color: #0F172A !important;
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
                background: #0F172A;
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
                align-items: stretch !important;
                gap: 42px !important;
                padding: 0 0 46px !important;
                margin-top: 0 !important;
            }
            .ideas-kicker-dark {
                display: inline-flex;
                align-items: center;
                width: max-content;
                padding: 4px 8px;
                background: #00D6A6;
                color: #0F172A;
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
            .ideas-secondary-action,
            .ideas-ideus-action {
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
                background: #00D6A6;
                color: #0F172A;
            }
            .ideas-secondary-action {
                color: #f8fafc;
                border: 1px solid rgba(255, 255, 255, .24);
            }
            .ideas-ideus-action {
                color: #00D6A6;
                border: 1px solid rgba(0, 214, 166, .5);
                background: rgba(0, 214, 166, .08);
            }
            .ideas-ideus-action .material-icons { font-size: 1.15rem; }
            .ideas-ideus-action:hover {
                background: rgba(0, 214, 166, .16);
                border-color: #00D6A6;
            }
            .ideas-hero-visual {
                position: relative;
                min-height: 390px;
                align-self: stretch;
                overflow: hidden;
                border-left: 1px solid rgba(255, 255, 255, .06);
                display: flex;
                flex-direction: column;
                padding: 32px;
                box-sizing: border-box;
                background:
                    radial-gradient(120% 90% at 78% 8%, rgba(0, 214, 166, .16), transparent 46%),
                    radial-gradient(110% 100% at 8% 92%, rgba(46, 140, 255, .16), transparent 50%),
                    #0F172A;
            }
            .ideas-hero-visual::after {
                content: "";
                position: absolute;
                inset: 0;
                background:
                    linear-gradient(90deg, rgba(255, 255, 255, .04) 1px, transparent 1px),
                    linear-gradient(180deg, rgba(255, 255, 255, .04) 1px, transparent 1px);
                background-size: 54px 54px;
                opacity: .2;
                mask-image: linear-gradient(180deg, transparent, #000 22%, #000 78%, transparent);
                pointer-events: none;
            }
            .ideas-visual-message {
                position: relative;
                z-index: 1;
            }
            .ideas-visual-message .label {
                display: inline-flex;
                align-items: center;
                width: max-content;
                padding: 4px 8px;
                background: #00D6A6;
                color: #0F172A;
                font-size: .68rem;
                font-weight: 900;
                letter-spacing: .04em;
                text-transform: uppercase;
                line-height: 1;
            }
            .ideas-visual-message .title {
                max-width: 430px;
                margin-top: 18px;
                color: #ffffff;
                font-size: clamp(1.7rem, 2.45vw, 2.55rem);
                line-height: 1.04;
                font-weight: 900;
            }
            .ideas-hero-mockup {
                position: relative;
                z-index: 1;
                margin-top: 30px;
                max-width: 460px;
            }
            .ideas-hero-mockup .ideas-mockup {
                box-shadow: 0 26px 50px rgba(0, 0, 0, .3);
            }
            .ideas-hero-mockup .ideas-mockup-body {
                padding: 18px;
                min-height: 0;
            }
            .ideas-hero-mockup .ideas-mockup-flow {
                margin-bottom: 16px;
            }
            .ideas-hero-mockup .ideas-mockup-node {
                padding: 10px 12px;
                font-size: .72rem;
            }
            .ideas-hero-mockup .ideas-mockup-row {
                margin-bottom: 8px;
            }
            .ideas-hero-mockup .ideas-mockup-row:last-child {
                margin-bottom: 0;
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
                background: rgba(15, 23, 42, .76);
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
                background: rgba(15, 23, 42, .92);
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
            .ideas-tab-wrap .q-tab {
                transition: color 160ms ease, background 160ms ease;
            }
            .ideas-tab-wrap .q-tab:hover {
                color: rgba(255, 255, 255, .9);
            }
            .ideas-tab-wrap .q-tab--active {
                color: #FF8A21;
                background: rgba(255, 138, 33, .1);
            }
            .ideas-tab-wrap .q-tab__indicator {
                background: #FF8A21 !important;
                height: 3px !important;
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
                    linear-gradient(135deg, rgba(0, 214, 166, .12), transparent 34%),
                    #1e293b;
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
                background: linear-gradient(180deg, rgba(15,23,42,.02), rgba(15,23,42,.34));
            }
            .ideas-card-grid {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
            }
            .ideas-dark-card {
                min-height: 180px;
                padding: 22px;
                background: #1e293b;
                border: 1px solid rgba(255, 255, 255, .08);
            }
            .ideas-dark-card .icon {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 34px;
                height: 34px;
                color: #00D6A6;
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
                background: #16233a;
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
                background: #00D6A6;
                color: #0F172A;
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
                background: #1e293b;
                border-left: 6px solid #00D6A6;
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
            .ideas-saas-page {
                padding-bottom: 70px;
            }
            .ideas-saas-hero h1 {
                max-width: 1040px;
                margin: 0 auto;
                color: #ffffff;
                font-size: clamp(2.1rem, 4.2vw, 4rem);
                line-height: 1.08;
                font-weight: 700;
                letter-spacing: 0;
                text-wrap: balance;
            }
            .ideas-saas-hero p {
                max-width: 850px;
                margin: 18px auto 0;
                color: rgba(255, 255, 255, .72);
                font-size: clamp(1.02rem, 1.55vw, 1.25rem);
                line-height: 1.7;
            }
            .ideas-saas-grid {
                grid-template-columns: repeat(3, minmax(0, 1fr)) !important;
            }
            .ideas-saas-card {
                min-height: 245px;
                border-radius: 0;
                transition: transform 180ms ease, border-color 180ms ease, box-shadow 180ms ease, background 180ms ease;
            }
            .ideas-saas-card:hover {
                transform: translateY(-4px);
                border-color: rgba(0, 214, 166, .4);
                box-shadow: 0 22px 42px rgba(0, 0, 0, .22);
                background: #243449;
            }
            .ideas-saas-feature {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 18px;
            }
            .ideas-saas-feature .ideas-dark-card {
                min-height: 280px;
            }
            .ideas-saas-proof {
                display: grid;
                grid-template-columns: minmax(0, .9fr) minmax(0, 1.1fr);
                gap: 22px;
                align-items: stretch;
                margin: 20px auto 0;
            }
            .ideas-saas-proof-copy {
                padding: 28px;
                background: #1e293b;
                border-left: 6px solid #00D6A6;
            }
            .ideas-saas-proof-copy h2 {
                margin: 0 0 14px;
                color: #ffffff;
                font-size: clamp(1.8rem, 2.8vw, 2.8rem);
                line-height: 1.05;
                font-weight: 900;
            }
            .ideas-saas-proof-copy p {
                margin: 0;
                color: rgba(255, 255, 255, .68);
                line-height: 1.72;
            }
            .ideas-saas-bullets {
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 14px;
                grid-auto-rows: 1fr;
            }
            .ideas-saas-bullet {
                height: 100%;
                min-height: 148px;
                padding: 18px;
                background: #1e293b;
                border: 1px solid rgba(255, 255, 255, .08);
                box-sizing: border-box;
            }
            .ideas-saas-bullet strong {
                display: block;
                color: #ffffff;
                font-size: 1rem;
                margin-bottom: 8px;
            }
            .ideas-saas-bullet span {
                display: block;
                color: rgba(255, 255, 255, .64);
                line-height: 1.55;
                font-size: .94rem;
            }
            .ideas-saas-service-card {
                position: relative;
                cursor: pointer;
                border-left: 6px solid #00D6A6;
            }
            .ideas-saas-service-card .tag {
                display: inline-flex;
                width: max-content;
                margin-top: 14px;
                padding: 6px 10px;
                background: #00D6A6;
                color: #0F172A;
                font-size: .72rem;
                font-weight: 900;
                letter-spacing: .04em;
                text-transform: uppercase;
            }
            .ideas-saas-cta {
                margin-top: 28px;
                padding: 38px 28px;
                background: #1e293b;
                border: 1px solid rgba(255, 255, 255, .08);
                border-left: 6px solid #00D6A6;
                text-align: center;
            }
            .ideas-saas-cta h2 {
                margin: 0;
                color: #ffffff;
                font-size: clamp(1.9rem, 3vw, 3rem);
                line-height: 1.05;
                font-weight: 900;
            }
            .ideas-saas-cta-actions {
                display: flex;
                justify-content: center;
                gap: 12px;
                flex-wrap: wrap;
                margin-top: 24px;
            }
            .ideas-public-whatsapp {
                color: #f8fafc !important;
                border-radius: 2px !important;
                background: rgba(37, 211, 102, .14) !important;
            }
            .ideas-saas-stats-row {
                display: grid;
                grid-template-columns: repeat(4, minmax(0, 1fr));
                gap: 20px;
                padding: 36px 0;
                margin-top: 6px;
                border-top: 1px solid rgba(255, 255, 255, .08);
                border-bottom: 1px solid rgba(255, 255, 255, .08);
            }
            .ideas-saas-stat {
                text-align: center;
                padding: 0 8px;
            }
            .ideas-saas-stat strong {
                display: block;
                color: #ffffff;
                font-size: clamp(1.9rem, 2.6vw, 2.4rem);
                font-weight: 900;
                line-height: 1;
            }
            .ideas-saas-stat span {
                display: block;
                margin-top: 9px;
                color: rgba(255, 255, 255, .62);
                font-size: .84rem;
                line-height: 1.45;
            }
            .ideas-module-directory {
                display: flex;
                flex-wrap: wrap;
                justify-content: center;
                gap: 10px;
                padding: 8px 0 4px;
            }
            .ideas-module-chip {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 9px 16px;
                background: #1e293b;
                border: 1px solid rgba(255, 255, 255, .1);
                color: rgba(255, 255, 255, .82);
                font-size: .84rem;
                font-weight: 700;
                text-decoration: none;
            }
            .ideas-module-chip .material-icons {
                font-size: 1.05rem;
                color: #00D6A6;
            }
            .ideas-module-detail {
                display: grid;
                grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
                gap: 52px;
                align-items: center;
                padding: 58px 0;
                border-top: 1px solid rgba(255, 255, 255, .06);
                scroll-margin-top: 100px;
            }
            .ideas-module-detail.reverse .ideas-module-visual {
                order: -1;
            }
            .ideas-module-copy .index {
                display: inline-flex;
                align-items: center;
                gap: 10px;
                color: rgba(255, 255, 255, .48);
                font-size: .8rem;
                font-weight: 900;
                letter-spacing: .06em;
                text-transform: uppercase;
            }
            .ideas-module-copy .index .material-icons {
                font-size: 1.25rem;
                color: #00D6A6;
            }
            .ideas-module-copy h3 {
                margin: 14px 0 12px;
                color: #ffffff;
                font-size: clamp(1.55rem, 2.3vw, 2.15rem);
                font-weight: 900;
                line-height: 1.12;
            }
            .ideas-module-copy p {
                margin: 0 0 20px;
                color: rgba(255, 255, 255, .68);
                line-height: 1.72;
            }
            .ideas-module-features {
                display: flex;
                flex-direction: column;
                gap: 12px;
            }
            .ideas-module-feature {
                display: flex;
                align-items: flex-start;
                gap: 10px;
                color: rgba(255, 255, 255, .8);
                font-size: .94rem;
                line-height: 1.5;
            }
            .ideas-module-feature .check {
                flex: 0 0 auto;
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 20px;
                height: 20px;
                margin-top: 1px;
                background: rgba(0, 214, 166, .16);
                color: #00D6A6;
                font-size: .74rem;
                font-weight: 900;
            }
            .ideas-mockup {
                border: 1px solid rgba(255, 255, 255, .1);
                background: #0d1729;
                overflow: hidden;
            }
            .ideas-mockup-bar {
                display: flex;
                align-items: center;
                gap: 6px;
                padding: 11px 14px;
                background: #16233a;
                border-bottom: 1px solid rgba(255, 255, 255, .08);
            }
            .ideas-mockup-bar i {
                width: 9px;
                height: 9px;
                border-radius: 50%;
                background: rgba(255, 255, 255, .16);
                display: inline-block;
            }
            .ideas-mockup-bar span {
                margin-left: 8px;
                color: rgba(255, 255, 255, .38);
                font-size: .72rem;
                font-weight: 700;
            }
            .ideas-mockup-body {
                padding: 22px;
                min-height: 230px;
            }
            .ideas-mockup-row {
                display: flex;
                align-items: center;
                justify-content: space-between;
                gap: 10px;
                padding: 12px 14px;
                margin-bottom: 9px;
                background: #1e293b;
                border-left: 3px solid var(--accent, #00D6A6);
                font-size: .82rem;
                color: rgba(255, 255, 255, .82);
            }
            .ideas-mockup-row .tag2 {
                padding: 3px 9px;
                font-size: .64rem;
                font-weight: 800;
                letter-spacing: .02em;
                text-transform: uppercase;
            }
            .tag2.ok { background: rgba(74, 222, 128, .16); color: #4ade80; }
            .tag2.warn { background: rgba(250, 204, 21, .16); color: #facc15; }
            .tag2.danger { background: rgba(248, 113, 113, .16); color: #f87171; }
            .ideas-mockup-chart {
                display: flex;
                align-items: flex-end;
                gap: 14px;
                height: 175px;
            }
            .ideas-mockup-chart .col {
                flex: 1;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: flex-end;
                height: 100%;
                gap: 8px;
            }
            .ideas-mockup-chart .col .bar {
                width: 100%;
                background: linear-gradient(180deg, var(--accent, #00D6A6), rgba(0, 214, 166, .22));
            }
            .ideas-mockup-chart .col span {
                font-size: .68rem;
                color: rgba(255, 255, 255, .55);
                text-align: center;
            }
            .ideas-mockup-flow {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 10px;
            }
            .ideas-mockup-node {
                padding: 13px 16px;
                background: #1e293b;
                border: 1px solid rgba(255, 255, 255, .14);
                border-top: 3px solid var(--accent, #00D6A6);
                font-size: .78rem;
                color: #fff;
                font-weight: 700;
            }
            .ideas-mockup-arrow {
                color: rgba(255, 255, 255, .28);
                font-size: 1.2rem;
            }
            .ideas-mockup-check {
                display: flex;
                align-items: center;
                gap: 11px;
                padding: 10px 0;
                border-bottom: 1px solid rgba(255, 255, 255, .06);
                font-size: .85rem;
                color: rgba(255, 255, 255, .82);
            }
            .ideas-mockup-check:last-child { border-bottom: 0; }
            .ideas-mockup-flow-center {
                display: flex;
                align-items: center;
                min-height: 150px;
            }
            .ideas-mockup-caption {
                margin: 20px 0 0;
                text-align: center;
                color: rgba(255, 255, 255, .48);
                font-size: .78rem;
            }
            .ideas-mockup-check .dot {
                flex: 0 0 auto;
                width: 21px;
                height: 21px;
                border-radius: 50%;
                display: flex;
                align-items: center;
                justify-content: center;
                background: rgba(74, 222, 128, .16);
                color: #4ade80;
                font-size: .76rem;
                font-weight: 900;
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
                .ideus-wordmark--topbar {
                    --brand-font-size-primary: .94rem !important;
                }
                .ideus-wordmark--hero {
                    --brand-font-size-primary: clamp(1.9rem, 9vw, 2.6rem) !important;
                }
                .ideas-public-menu {
                    order: 3 !important;
                    width: 100% !important;
                    justify-content: flex-start !important;
                    flex-wrap: wrap !important;
                    gap: 12px 18px !important;
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
                .ideas-platform-band,
                .ideas-saas-feature,
                .ideas-saas-grid,
                .ideas-saas-proof,
                .ideas-saas-bullets,
                .ideas-module-detail {
                    grid-template-columns: 1fr !important;
                }
                .ideas-process,
                .ideas-card-grid,
                .ideas-visual-card,
                .ideas-wide-stats {
                    grid-template-columns: 1fr !important;
                }
                .ideas-saas-stats-row {
                    grid-template-columns: repeat(2, minmax(0, 1fr)) !important;
                    gap: 20px 14px !important;
                }
                .ideas-module-detail.reverse .ideas-module-visual {
                    order: 0 !important;
                }
                .ideas-module-detail {
                    padding: 40px 0 !important;
                    gap: 24px !important;
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
                .ideas-secondary-action,
                .ideas-ideus-action {
                    width: 100%;
                    justify-content: center;
                }
                .ideas-hero-visual {
                    min-height: 360px;
                    padding: 22px;
                }
                .ideas-visual-message .title {
                    font-size: clamp(1.55rem, 8vw, 2.25rem);
                    max-width: 100%;
                }
                .ideas-hero-mockup {
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

    def saas_card(icon: str, title: str, text: str, anchor: str = '') -> None:
        classes = 'ideas-dark-card ideas-saas-card shadow-lg hover:shadow-2xl'
        with ui.card().classes(classes).props(f'id={anchor}' if anchor else ''):
            ui.icon(icon).classes('icon')
            ui.html(f'<h3>{title}</h3><p>{text}</p>')

    def mockup_shell(label: str, body_html: str) -> str:
        return (
            '<div class="ideas-mockup">'
            f'<div class="ideas-mockup-bar"><i></i><i></i><i></i><span>{label}</span></div>'
            f'<div class="ideas-mockup-body">{body_html}</div>'
            '</div>'
        )

    def mockup_flow(nodes: list[str]) -> str:
        parts = []
        for index, node in enumerate(nodes):
            if index:
                parts.append('<span class="ideas-mockup-arrow">&rarr;</span>')
            parts.append(f'<div class="ideas-mockup-node">{node}</div>')
        return f'<div class="ideas-mockup-flow">{"".join(parts)}</div>'

    def mockup_rows(rows: list[tuple[str, str, str]]) -> str:
        parts = [
            f'<div class="ideas-mockup-row"><span>{label}</span><span class="tag2 {tag_class}">{tag_text}</span></div>'
            for label, tag_text, tag_class in rows
        ]
        return ''.join(parts)

    def mockup_chart(bars: list[tuple[int, str]]) -> str:
        parts = [
            f'<div class="col"><div class="bar" style="height:{height}%"></div><span>{label}</span></div>'
            for height, label in bars
        ]
        return f'<div class="ideas-mockup-chart">{"".join(parts)}</div>'

    def mockup_check(items: list[str]) -> str:
        parts = [f'<div class="ideas-mockup-check"><span class="dot">&#10003;</span><span>{item}</span></div>' for item in items]
        return ''.join(parts)

    def render_platform_saas_content() -> None:
        modules = [
            (
                'account_tree',
                'Mapas de Procesos Dinamicos',
                'Modela procesos, responsables, entradas, salidas y controles para visualizar como opera la organizacion y detectar oportunidades de mejora.',
            ),
            (
                'warning',
                'Matrices de Riesgos Inteligentes',
                'Evalua riesgos por proceso, impacto y probabilidad, priorizando acciones con trazabilidad y foco en decisiones preventivas.',
            ),
            (
                'eco',
                'Medio Ambiente y SST',
                'Centraliza aspectos ambientales, requisitos legales, simulacros, incidentes y controles de seguridad y salud ocupacional.',
            ),
            (
                'dashboard',
                'Dashboards y KPIs',
                'Convierte datos operativos en indicadores claros, alertas y tableros ejecutivos para seguir desempeno, tendencias y desvio.',
            ),
            (
                'library_books',
                'Gestion Documental Activa',
                'Organiza normas, procedimientos, registros y evidencias para que cada equipo trabaje con informacion vigente y disponible.',
            ),
            (
                'fact_check',
                'Gestion de Calidad y Resolucion',
                'Gestiona no conformidades, problemas 8D, causas raiz, acciones correctivas y aprendizaje organizacional con seguimiento real.',
            ),
        ]

        stats = [
            ('-70%', 'Menos tiempo buscando información dispersa en planillas y correos'),
            ('100%', 'Trazabilidad de acciones, responsables y vencimientos'),
            ('6', 'Módulos conectados dentro de un mismo workspace'),
            ('24/7', 'Asistencia con Smart Assist entrenado en tu empresa'),
        ]

        module_details = [
            (
                'account_tree',
                'Mapas de Procesos Dinámicos',
                'Modelá cada proceso con sus entradas, salidas, responsables y controles clave, y entendé de un vistazo cómo se conecta con riesgos, documentos e indicadores.',
                [
                    'Diagramas interactivos por proceso y por área',
                    'Responsables, entradas, salidas y controles asociados',
                    'Vinculación directa con riesgos y documentos relacionados',
                ],
                mockup_shell(
                    'Mapa de Procesos · Planta 1',
                    f'<div class="ideas-mockup-flow-center">{mockup_flow(["Compras", "Producción", "Calidad", "Despacho"])}</div>'
                    '<p class="ideas-mockup-caption">4 procesos vinculados con sus riesgos y documentos asociados</p>',
                ),
            ),
            (
                'warning',
                'Matrices de Riesgos Inteligentes',
                'Evaluá riesgos por proceso, probabilidad e impacto, priorizando qué atender primero con trazabilidad completa de cada plan de acción.',
                [
                    'Matriz probabilidad x impacto con priorización automática',
                    'Planes de acción con responsable y fecha límite',
                    'Alertas cuando un riesgo crítico queda sin tratamiento',
                ],
                mockup_shell('Matriz de Riesgos · Vigente', mockup_rows([
                    ('Corte en prensa hidráulica', 'Alto', 'danger'),
                    ('Falta de EPP en línea 2', 'Medio', 'warn'),
                    ('Fuga menor de aceite', 'Bajo', 'ok'),
                    ('Capacitación vencida - Soldadura', 'Medio', 'warn'),
                ])),
            ),
            (
                'eco',
                'Medio Ambiente y SST',
                'Centralizá aspectos ambientales, requisitos legales, simulacros, incidentes y controles de seguridad y salud ocupacional en un mismo lugar.',
                [
                    'Requisitos legales ambientales y de seguridad al día',
                    'Registro de incidentes, hallazgos y simulacros',
                    'Seguimiento de vencimientos normativos con alertas',
                ],
                mockup_shell('Cumplimiento Legal · SST', mockup_check([
                    'Matriz legal ambiental actualizada',
                    'Simulacro de incendio realizado',
                    'Capacitación en alturas vigente',
                    'Elementos de protección auditados',
                ])),
            ),
            (
                'dashboard',
                'Dashboards y KPIs',
                'Convertí datos operativos en indicadores claros, alertas y tableros ejecutivos para seguir desempeño, tendencias y desvíos en tiempo real.',
                [
                    'Indicadores por proceso, área y objetivo estratégico',
                    'Tendencias, desvíos y semáforos automáticos',
                    'Reportes ejecutivos listos para compartir',
                ],
                mockup_shell('Dashboard Ejecutivo · KPIs', mockup_chart([
                    (72, 'OEE'), (91, 'Calidad'), (58, 'Entregas'), (84, 'SST'),
                ])),
            ),
            (
                'library_books',
                'Gestión Documental Activa',
                'Organizá normas, procedimientos, registros y evidencias para que cada equipo trabaje siempre con información vigente y disponible.',
                [
                    'Control de versiones y vigencia de cada documento',
                    'Acceso segmentado por rol y por empresa',
                    'Búsqueda asistida por IA sobre el contenido vigente',
                ],
                mockup_shell('Gestión Documental · Vigencias', mockup_rows([
                    ('Procedimiento de Calidad Rev.4', 'Vigente', 'ok'),
                    ('Instructivo SST Línea 2', 'Vigente', 'ok'),
                    ('Manual Ambiental Rev.2', 'Por revisar', 'warn'),
                    ('Registro de Auditoría Interna', 'Vencido', 'danger'),
                ])),
            ),
            (
                'fact_check',
                'Gestión de Calidad y Resolución',
                'Gestioná no conformidades, problemas 8D, causas raíz, acciones correctivas y aprendizaje organizacional con seguimiento real.',
                [
                    'No conformidades, 8D y causa raíz en un solo flujo',
                    'Acciones correctivas con seguimiento de cierre',
                    'Historial de aprendizaje reutilizable entre equipos',
                ],
                mockup_shell('No Conformidades · Abiertas', mockup_rows([
                    ('NC-014 Desvío dimensional', 'En análisis', 'warn'),
                    ('NC-011 Reclamo de cliente', 'Acción definida', 'warn'),
                    ('NC-009 Falla de proveedor', 'Cerrada', 'ok'),
                    ('NC-016 Retrabajo en línea 3', 'Crítica', 'danger'),
                ])),
            ),
        ]

        with ui.element('main').classes('ideas-public-home ideas-saas-page'):
            with ui.column().classes('w-full items-center text-center py-12 ideas-public-inner ideas-saas-hero'):
                ui.html(
                    '<div class="ideas-kicker-dark">Plataforma SaaS</div>'
                    + ideus_wordmark_html('hero', on_dark=True)
                    + '<h1>El Copiloto Inteligente para la Gestión Integral de tu Organización</h1>'
                    '<p>Transforma la forma en que administras tu empresa con una plataforma SaaS agil, centralizada y potenciada por Inteligencia Artificial.</p>'
                )

            with ui.element('section').classes('ideas-public-inner ideas-saas-stats-row'):
                for value, label in stats:
                    ui.html(f'<div class="ideas-saas-stat"><strong>{value}</strong><span>{label}</span></div>')

            with ui.element('section').classes('w-full max-w-6xl mx-auto ideas-saas-proof'):
                ui.html(
                    '''
                    <div class="ideas-saas-proof-copy">
                        <div class="ideas-kicker-dark">Por que elegirlo</div>
                        <h2>Una plataforma para dejar de perseguir informacion y empezar a dirigir con evidencia.</h2>
                        <p>
                        IDEUS ordena el sistema de gestion completo: procesos, riesgos, documentos,
                        indicadores, calidad, ambiente, SST y acciones. Cada modulo trabaja conectado, con responsables,
                        vencimientos, trazabilidad y asistencia IA entrenada sobre el contexto real de la empresa.
                        </p>
                    </div>
                    '''
                )
                with ui.element('div').classes('ideas-saas-bullets'):
                    for title, text in [
                        ('Centralizacion real', 'Toda la gestion clave vive en un unico workspace, evitando planillas dispersas, versiones duplicadas y perdida de seguimiento.'),
                        ('Implementacion mas rapida', 'La plataforma se configura sobre la realidad operativa del cliente para acelerar adopcion y reducir burocracia.'),
                        ('Decision ejecutiva', 'KPIs, alertas, riesgos y acciones quedan visibles para priorizar lo importante antes de que se convierta en urgencia.'),
                        ('IA con contexto', 'Smart Assist consulta documentos y modulo activo para responder con criterio aplicado, no con informacion generica.'),
                    ]:
                        ui.html(f'<div class="ideas-saas-bullet"><strong>{title}</strong><span>{text}</span></div>')

            with ui.element('div').classes('ideas-public-inner'):
                ui.html(
                    '<div class="ideas-module-directory">' + ''.join(
                        f'<a class="ideas-module-chip" href="#modulo-{index}">'
                        f'<span class="material-icons">{icon}</span>{title}</a>'
                        for index, (icon, title, _text) in enumerate(modules)
                    ) + '</div>'
                )

            with ui.grid(columns=3).classes('w-full max-w-6xl gap-6 py-8 mx-auto ideas-saas-grid'):
                for icon, title, text in modules:
                    saas_card(icon, title, text)

            for index, (icon, title, text, features, mockup_html) in enumerate(module_details):
                reverse_class = ' reverse' if index % 2 == 1 else ''
                with ui.element('section').classes(f'ideas-public-inner ideas-module-detail{reverse_class}').props(f'id=modulo-{index}'):
                    with ui.element('div').classes('ideas-module-copy'):
                        ui.html(
                            f'<div class="index"><span class="material-icons">{icon}</span>Módulo {index + 1:02d}</div>'
                            f'<h3>{title}</h3>'
                            f'<p>{text}</p>'
                            '<div class="ideas-module-features">' + ''.join(
                                f'<div class="ideas-module-feature"><span class="check">&#10003;</span><span>{feature}</span></div>'
                                for feature in features
                            ) + '</div>'
                        )
                    with ui.element('div').classes('ideas-module-visual'):
                        ui.html(mockup_html)

            with ui.row().classes('w-full max-w-6xl justify-between py-12 mx-auto ideas-saas-feature'):
                with ui.card().classes('ideas-dark-card shadow-lg'):
                    ui.icon('psychology').classes('icon')
                    ui.html(
                        '''
                        <h3>🧠 Smart Assist: Tu Consultor IA 24/7</h3>
                        <p>
                        La IA entiende el modulo donde estas trabajando y consulta los documentos propios de tu empresa.
                        Responde con contexto, evidencia y foco practico, evitando respuestas genericas que no reflejan
                        tu sistema de gestion real.
                        </p>
                        '''
                    )
                with ui.card().classes('ideas-dark-card shadow-lg'):
                    ui.icon('shield').classes('icon')
                    ui.html(
                        '''
                        <h3>🔒 Seguridad de Nivel Corporativo</h3>
                        <p>
                        Cada empresa opera en un entorno aislado multi-tenant. La sesion usa tokens seguros, el acceso
                        queda segmentado por rol y la informacion documental se consulta solo dentro del contexto autorizado.
                        </p>
                        '''
                    )

            with ui.element('section').classes('ideas-public-inner ideas-saas-cta'):
                ui.html('<h2>Menos burocracia. Mas vision estrategica. Mejores resultados.</h2>')
                with ui.element('div').classes('ideas-saas-cta-actions'):
                    ui.button('Solicitar una Demo', on_click=lambda: ui.navigate.to('/contacto')).props('unelevated color=primary rounded')
                    ui.button(
                        'Hablar con un Asesor',
                        on_click=lambda: ui.run_javascript("window.open('https://wa.me/541170068904', '_blank')"),
                    ).props('outline color=primary rounded')

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
                            if platform_enabled:
                                ui.html('<a class="ideas-primary-action" href="/plataforma">Ingresar a plataforma</a>')
                            else:
                                ui.html('<a class="ideas-primary-action" href="/contacto">Solicitar asesoramiento</a>')
                            ui.html(
                                '<a class="ideas-ideus-action" href="/soluciones/plataforma-saas">'
                                '<span class="material-icons" aria-hidden="true">laptop_mac</span>'
                                '<span>Conocé la plataforma IDEUS</span></a>'
                            )
                            ui.html('<a class="ideas-secondary-action" href="#contenido">Conocer propuesta</a>')
                    with ui.element('aside').classes('ideas-hero-visual'):
                        ui.html(
                            '''
                            <div class="ideas-visual-message">
                                <div class="label">Sistema de gestión vivo</div>
                                <div class="title">Diagnóstico, acción y seguimiento en un solo flujo.</div>
                            </div>
                            '''
                        )
                        ui.html(
                            '<div class="ideas-hero-mockup">'
                            + mockup_shell(
                                'Workspace · IDEUS',
                                mockup_flow(['Diagnóstico', 'Acción', 'Seguimiento'])
                                + mockup_rows([
                                    ('Auditoría interna · Planta 2', 'En curso', 'warn'),
                                    ('NC-014 Desvío dimensional', 'Acción definida', 'warn'),
                                    ('Cumplimiento SST', '94%', 'ok'),
                                ])
                            )
                            + '</div>'
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
                            ui.html(
                                '''
                                <p class="ideas-copy">
                                Acompañamos sistemas de gestión con foco práctico en operación real, cumplimiento y mejora continua.
                                </p>
                                '''
                            )
                            with ui.element('div').classes('ideas-card-grid mt-8'):
                                services = [
                                    ('assignment', 'Sistemas de Gestión', 'Ordenamos y estructuramos sistemas de gestión con foco en requisitos, evidencia y operación real.'),
                                    ('bolt', 'Aceleración de decisiones', 'Convertimos datos dispersos en tableros, prioridades, alertas y planes accionables.'),
                                    ('sync_alt', 'Mejora continua', 'Acompañamos rutinas, acciones correctivas, problemas 8D y seguimiento de compromisos.'),
                                    ('eco', 'Gestión Ambiental', 'Cumplimiento legal ambiental, control de impactos y criterios de sustentabilidad aplicados a planta.'),
                                    ('health_and_safety', 'Salud Ocupacional', 'Evaluación de riesgos, controles preventivos y fortalecimiento de cultura de trabajo seguro.'),
                                    ('engineering', 'Soporte Operativo y Sorting', 'Facilitación de personal calificado para tareas de inspección, sorting y retrabajos en su planta o en instalaciones del cliente. Gestionamos integralmente los requisitos de ingreso, reportes de avance, indicadores de calidad (KPIs) y trazabilidad del trabajo.'),
                                ]
                                for icon, title, text in services:
                                    card(icon, title, text)
                                with ui.element('article').classes('ideas-dark-card ideas-saas-service-card').on('click', lambda _e: ui.navigate.to('/soluciones/plataforma-saas')):
                                    ui.icon('cloud_done').classes('icon')
                                    ui.html(
                                        '''
                                        <h3>Plataforma SaaS</h3>
                                        <p>
                                        IDEUS es el sistema operativo de gestion para empresas que necesitan ordenar
                                        procesos, documentos, riesgos, KPIs, calidad, ambiente y SST en un solo lugar. Integra
                                        trazabilidad, responsables, vencimientos y Smart Assist para transformar informacion
                                        dispersa en accion concreta.
                                        </p>
                                        <div class="tag">Conocer IDEUS</div>
                                        '''
                                    )
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
                                    ('02', 'Diseño', 'Definimos estructura, prioridades, responsables y herramientas.'),
                                    ('03', 'Implementación', 'Acompañamos ejecución en planta, procesos y rutinas de gestión.'),
                                    ('04', 'Seguimiento', 'Medimos avance, ajustamos desvio y sostenemos mejora continua.'),
                                ]:
                                    ui.html(f'<article class="ideas-step"><div class="number">{number}</div><h3>{title}</h3><p>{text}</p></article>')

                    with ui.tab_panel(tab_platform).classes('p-0'):
                        with ui.element('section').classes('ideas-public-inner ideas-section'):
                            with ui.element('div').classes('ideas-section-grid'):
                                with ui.element('div'):
                                    ui.html('<div class="ideas-kicker-dark">Plataforma Digital · IDEUS</div>')
                                    ui.html('<h2>Una plataforma viva para cada cliente.</h2>')
                                    ui.html(
                                        '''
                                        <p class="ideas-copy">
                                        IDEUS centraliza procesos, diagnósticos, documentos, indicadores,
                                        riesgos, ambiente, calidad, SST y usuarios en un entorno único, con
                                        Smart Assist como IA entrenada sobre el contexto real de tu empresa.
                                        </p>
                                        '''
                                    )
                                    ui.html(
                                        '<a class="ideas-ideus-action" href="/soluciones/plataforma-saas" style="margin-top:18px;">'
                                        '<span class="material-icons" aria-hidden="true">laptop_mac</span>'
                                        '<span>Ver la plataforma IDEUS completa</span></a>'
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
                                    ui.html(linkedin_html)
                                    render_contact_request_form()

    @ui.page('/servicios')
    def website_services_page() -> None:
        shell_container = public_shell('Servicios')
        public_styles()
        with shell_container:
            with ui.element('main').classes('ideas-public-home'):
                with ui.element('section').classes('ideas-public-inner ideas-section'):
                    ui.html('<div class="ideas-kicker-dark">Servicios</div>')
                    ui.html('<h2>Consultoría potenciada por tecnología.</h2>')

    @ui.page('/soluciones/plataforma-saas')
    def website_platform_saas_page() -> None:
        shell_container = public_shell('Plataforma SaaS')
        public_styles()
        with shell_container:
            render_platform_saas_content()

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
                    ui.html(linkedin_html)
                    render_contact_request_form()
