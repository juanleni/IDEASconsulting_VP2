from __future__ import annotations


def register_public_pages(ui, deps: dict) -> None:
    public_shell = deps['public_shell']
    get_banner_url = deps['get_banner_url']

    @ui.page('/')
    def website_home_page() -> None:
        shell_container = public_shell('Sitio institucional')
        banner = get_banner_url()
        media_html = (
            f'<img src="{banner}" style="width:100%;height:100%;min-height:460px;object-fit:cover;border-radius:26px;" />'
            if banner
            else '<div class="ideas-service-card" style="height:100%;display:flex;align-items:center;justify-content:center;">Agregá ideas_home_banner.png para reforzar la identidad visual.</div>'
        )
        with shell_container:
            ui.html(
                f'''
                <div class="ideas-public-hero">
                    <div class="ideas-public-card ideas-public-hero-copy">
                        <div class="ideas-kicker">Gestión, procesos y resultados reales</div>
                        <div class="ideas-public-title">Transformamos la gestión y los procesos en resultados operativos y económicos reales.</div>
                        <div class="ideas-public-lead">
                            Acompañamos a empresas en la implementación y mejora de sistemas de gestión, auditorías y optimización de procesos,
                            con un enfoque práctico orientado a mejorar la eficiencia operativa y generar resultados sostenibles.
                        </div>
                        <div style="margin-top:16px;">
                            <span class="ideas-chip">Sistemas de gestión</span>
                            <span class="ideas-chip">Auditorías y diagnóstico</span>
                            <span class="ideas-chip">Mejora de procesos</span>
                            <span class="ideas-chip">Capacitación</span>
                        </div>
                        <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:24px;">
                            <a href="/servicios" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--unelevated q-btn--rectangle bg-primary text-white" style="padding:12px 18px;border-radius:16px;">Ver servicios</button></a>
                            <a href="/plataforma" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--outline q-btn--rectangle text-primary" style="padding:12px 18px;border-radius:16px;border:1px solid rgba(31,126,214,.24);">Ingresar a la plataforma</button></a>
                        </div>
                    </div>
                    <div class="ideas-public-card ideas-public-hero-media">
                        {media_html}
                    </div>
                </div>
                '''
            )
            ui.html(
                '''
                <div class="ideas-grid-3 ideas-public-section">
                    <div class="ideas-public-stat"><div class="label">Enfoque</div><div class="value">Gestión aplicada</div><div class="detail">Integramos metodología, experiencia industrial y trabajo cercano con los equipos.</div></div>
                    <div class="ideas-public-stat"><div class="label">Objetivo</div><div class="value">Eficiencia real</div><div class="detail">Ordenar la gestión, mejorar el control operativo y fortalecer la capacidad de ejecución.</div></div>
                    <div class="ideas-public-stat"><div class="label">Resultado</div><div class="value">Impacto sostenible</div><div class="detail">Mejoras que funcionan en la operación diaria y sostienen resultados en el negocio.</div></div>
                </div>
                '''
            )
            with ui.column().classes('ideas-public-section w-full'):
                ui.html('<h2>Sobre nosotros</h2><p>En IDEAS Consulting ayudamos a las organizaciones a transformar sus sistemas de gestión y procesos en herramientas reales de mejora operativa. Trabajamos junto a los equipos, integrándonos a la operación diaria, para ordenar la gestión, mejorar el control operativo y fortalecer la capacidad de la organización para gestionar sus procesos de manera eficiente.</p>')
                ui.html(
                    '''
                    <div class="ideas-grid-3" style="margin-top:18px;">
                        <div class="ideas-service-card"><div class="icon">Cercanía</div><h3>Trabajo cercano</h3><p>Nos integramos a la realidad operativa de cada empresa para implementar mejoras que sí se sostienen.</p></div>
                        <div class="ideas-service-card"><div class="icon">Industria</div><h3>Experiencia industrial</h3><p>Aportamos criterio práctico para intervenir sobre sistemas, procesos y control operativo.</p></div>
                        <div class="ideas-service-card"><div class="icon">Impacto</div><h3>Resultados concretos</h3><p>Transformamos gestión en eficiencia, control y mejoras con impacto operativo y económico.</p></div>
                    </div>
                    '''
                )
                ui.html(
                    '''
                    <div class="ideas-editorial-band">
                        <div class="block">
                            <h3>Propuesta de valor</h3>
                            <p>Convertimos sistemas de gestión y procesos en herramientas concretas para mejorar la operación, fortalecer el control y generar resultados sostenibles.</p>
                        </div>
                        <div class="block">
                            <h3>Lo que generamos</h3>
                            <p>Resultados económicos, eficiencia operativa, mejor gestión y reducción de riesgos, con una lógica aplicable a la realidad diaria de cada organización.</p>
                        </div>
                    </div>
                    '''
                )
            ui.html(
                '''
                <div class="ideas-cta-band ideas-public-section">
                    <h3>Transformamos la gestión en resultados reales.</h3>
                    <p>Nuestro enfoque combina análisis, metodología y trabajo cercano con los equipos, permitiendo implementar mejoras que realmente funcionan en la operación diaria.</p>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;margin-top:20px;">
                        <a href="/metodologia" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--unelevated q-btn--rectangle bg-white text-primary" style="padding:12px 18px;border-radius:16px;">Conocer metodología</button></a>
                        <a href="/contacto" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--outline q-btn--rectangle text-white" style="padding:12px 18px;border-radius:16px;border:1px solid rgba(255,255,255,.28);">Contactar a IDEAS</button></a>
                    </div>
                </div>
                '''
            )

    @ui.page('/servicios')
    def website_services_page() -> None:
        shell_container = public_shell('Servicios')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Nuestros servicios</div><h2>Soluciones orientadas a fortalecer gestión, control y desempeño.</h2><p>Implementamos, desarrollamos y mejoramos sistemas de gestión, auditorías, diagnósticos y procesos con foco en eficiencia operativa y resultados sostenibles.</p></div>')
            ui.html(
                '''
                <div class="ideas-grid-3" style="margin-top:18px;">
                    <div class="ideas-service-card"><div class="icon">Sistemas de gestión</div><h3>Sistemas de gestión</h3><p>Implementación, desarrollo y mejora de sistemas orientados a fortalecer la organización y mejorar el control de los procesos.</p><div class="ideas-feature-list"><div class="ideas-feature-item"><div class="glyph">✓</div><div class="content"><div class="title">ISO 9001</div><div class="detail">Gestión de calidad con foco en consistencia y mejora continua.</div></div></div><div class="ideas-feature-item"><div class="glyph">🚗</div><div class="content"><div class="title">IATF 16949</div><div class="detail">Buenas prácticas de gestión para entornos automotrices.</div></div></div><div class="ideas-feature-item"><div class="glyph">🌿</div><div class="content"><div class="title">ISO 14001</div><div class="detail">Gestión ambiental con criterio preventivo y sostenible.</div></div></div><div class="ideas-feature-item"><div class="glyph">⛑</div><div class="content"><div class="title">ISO 45001</div><div class="detail">Seguridad y salud en el trabajo con control operativo.</div></div></div><div class="ideas-feature-item"><div class="glyph">🔐</div><div class="content"><div class="title">ISO 27001</div><div class="detail">Protección de la información y robustez de gestión.</div></div></div><div class="ideas-feature-item"><div class="glyph">🧩</div><div class="content"><div class="title">Sistemas integrados</div><div class="detail">Integración de normas para una gestión más eficiente.</div></div></div></div></div>
                    <div class="ideas-service-card"><div class="icon">Auditorías y diagnóstico</div><h3>Auditorías y diagnóstico</h3><p>Evaluación estructurada de procesos y sistemas de gestión para identificar oportunidades de mejora y fortalecer el control operativo.</p><div class="ideas-feature-list"><div class="ideas-feature-item"><div class="glyph">📋</div><div class="content"><div class="title">Auditorías internas</div><div class="detail">Revisión ordenada del grado de cumplimiento y madurez.</div></div></div><div class="ideas-feature-item"><div class="glyph">🏭</div><div class="content"><div class="title">VDA 6.3</div><div class="detail">Auditorías de proceso para entornos industriales exigentes.</div></div></div><div class="ideas-feature-item"><div class="glyph">🧭</div><div class="content"><div class="title">Diagnósticos de gestión</div><div class="detail">Identificación de brechas y prioridades de mejora.</div></div></div><div class="ideas-feature-item"><div class="glyph">✅</div><div class="content"><div class="title">Preparación externa</div><div class="detail">Mayor solidez frente a auditorías de terceros.</div></div></div></div></div>
                    <div class="ideas-service-card"><div class="icon">Mejora de procesos</div><h3>Mejora de procesos</h3><p>Optimización de procesos operativos y administrativos para mejorar eficiencia, reducir desvíos y fortalecer el control de la operación.</p><div class="ideas-feature-list"><div class="ideas-feature-item"><div class="glyph">🔬</div><div class="content"><div class="title">Análisis de procesos</div><div class="detail">Comprensión detallada de flujos, fallas y oportunidades.</div></div></div><div class="ideas-feature-item"><div class="glyph">📊</div><div class="content"><div class="title">Implementación de KPIs</div><div class="detail">Indicadores claros para seguimiento y decisión.</div></div></div><div class="ideas-feature-item"><div class="glyph">⚡</div><div class="content"><div class="title">Eficiencia operativa</div><div class="detail">Menos desvíos y mayor productividad en la operación.</div></div></div><div class="ideas-feature-item"><div class="glyph">📐</div><div class="content"><div class="title">Estandarización</div><div class="detail">Procesos más consistentes y fáciles de sostener.</div></div></div></div></div>
                </div>
                '''
            )
            ui.html(
                '''
                <div class="ideas-grid-2 ideas-public-section">
                    <div class="ideas-service-card">
                        <div class="icon">Capacitación</div>
                        <h3>Capacitación</h3>
                        <p>Desarrollo de competencias en los equipos para fortalecer la gestión y sostener las mejoras implementadas.</p>
                        <div class="ideas-feature-list"><div class="ideas-feature-item"><div class="glyph">📝</div><div class="content"><div class="title">Auditores internos</div><div class="detail">Formación para sostener auditorías y control de gestión.</div></div></div><div class="ideas-feature-item"><div class="glyph">🛠</div><div class="content"><div class="title">Herramientas de calidad</div><div class="detail">Recursos prácticos aplicados a la operación diaria.</div></div></div><div class="ideas-feature-item"><div class="glyph">🔁</div><div class="content"><div class="title">Mejora de procesos</div><div class="detail">Capacidad de intervención continua sobre procesos clave.</div></div></div><div class="ideas-feature-item"><div class="glyph">🧠</div><div class="content"><div class="title">Capacidades de gestión</div><div class="detail">Equipos más sólidos para sostener el cambio.</div></div></div></div>
                    </div>
                    <div class="ideas-service-card">
                        <div class="icon">Respaldo</div>
                        <h3>Experiencia y respaldo técnico</h3>
                        <p>Las auditorías de proceso VDA 6.3 son realizadas por auditores calificados con experiencia en entornos industriales.</p>
                    </div>
                </div>
                '''
            )

    @ui.page('/metodologia')
    def website_method_page() -> None:
        shell_container = public_shell('Metodología')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Cómo trabajamos</div><h2>Una metodología estructurada con impacto real en la operación.</h2><p>En IDEAS Consulting aplicamos una metodología que permite comprender la realidad de cada organización, identificar oportunidades de mejora y desarrollar soluciones prácticas con impacto en la operación y en los resultados del negocio.</p></div>')
            ui.html(
                '''
                <div class="ideas-grid-3" style="margin-top:18px;">
                    <div class="ideas-public-stat"><div class="label">1</div><div class="value">Diagnóstico</div><div class="detail">Evaluación de la situación actual para identificar oportunidades de mejora en procesos y sistemas de gestión.</div></div>
                    <div class="ideas-public-stat"><div class="label">2</div><div class="value">Plan de mejora</div><div class="detail">Definición de prioridades, alcance del proyecto y planificación de las acciones de mejora.</div></div>
                    <div class="ideas-public-stat"><div class="label">3</div><div class="value">Implementación</div><div class="detail">Trabajo conjunto con los equipos para aplicar mejoras en la operación y fortalecer procesos.</div></div>
                </div>
                '''
            )
            ui.html(
                '''
                <div class="ideas-grid-2 ideas-public-section">
                    <div class="ideas-service-card">
                        <div class="icon">Resultados</div>
                        <h3>Resultados</h3>
                        <p>Procesos más eficientes, mayor control operativo y mejoras sostenibles en la gestión.</p>
                    </div>
                    <div class="ideas-service-card">
                        <div class="icon">Impacto</div>
                        <h3>Impacto en el negocio</h3>
                        <div class="ideas-feature-list">
                            <div class="ideas-feature-item"><div class="glyph">💰</div><div class="content"><div class="title">Resultados económicos</div><div class="detail">Impacto real en eficiencia, costos y rentabilidad.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">⚙</div><div class="content"><div class="title">Eficiencia operativa</div><div class="detail">Procesos más claros, fluidos y consistentes.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">📊</div><div class="content"><div class="title">Mejor gestión</div><div class="detail">Mayor control y mejor capacidad de decisión.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">🛡</div><div class="content"><div class="title">Reducción de riesgos</div><div class="detail">Menor exposición a desvíos y fallas operativas.</div></div></div>
                        </div>
                    </div>
                </div>
                <div class="ideas-public-card ideas-panel ideas-public-section">
                    <h2 style="margin-top:0;">Resultados que buscamos generar</h2>
                    <div class="ideas-feature-list">
                        <div class="ideas-feature-item"><div class="glyph">💰</div><div class="content"><div class="title">Reducción de costos</div><div class="detail">Menos desperdicios, retrabajos y desvíos operativos.</div></div></div>
                        <div class="ideas-feature-item"><div class="glyph">📈</div><div class="content"><div class="title">Productividad</div><div class="detail">Procesos más claros, estandarizados y eficientes.</div></div></div>
                        <div class="ideas-feature-item"><div class="glyph">📊</div><div class="content"><div class="title">Indicadores claros</div><div class="detail">Mayor visibilidad y mejor base para decidir.</div></div></div>
                        <div class="ideas-feature-item"><div class="glyph">🛡</div><div class="content"><div class="title">Cumplimiento</div><div class="detail">Mayor preparación para auditorías y exigencias normativas.</div></div></div>
                    </div>
                </div>
                '''
            )

    @ui.page('/contacto')
    def website_contact_page() -> None:
        shell_container = public_shell('Contacto')
        with shell_container:
            ui.html('<div class="ideas-public-section"><div class="ideas-kicker">Contacto</div><h2>Conversemos sobre tu organización.</h2><p>En IDEAS Consulting ayudamos a convertir sistemas de gestión y procesos en herramientas concretas para mejorar la operación, fortalecer el control y generar resultados sostenibles.</p></div>')
            ui.html(
                '''
                <div class="ideas-grid-2" style="margin-top:18px;">
                    <div class="ideas-service-card">
                        <div class="icon">Contacto</div>
                        <h3>IDEAS Consulting</h3>
                        <p>Gestión · Procesos · Resultados reales</p>
                        <ul class="ideas-list-clean">
                            <li>Email: ideasconsultingargentina@gmail.com</li>
                            <li>Teléfono: (+54) 11 7006 8904</li>
                            <li>LinkedIn: IDEAS Consulting</li>
                        </ul>
                        <a class="ideas-whatsapp-link" href="https://wa.me/541170068904" target="_blank" rel="noopener noreferrer">
                            <span class="ideas-whatsapp-icon">
                                <svg viewBox="0 0 32 32" aria-hidden="true">
                                    <circle cx="16" cy="16" r="16" fill="#25D366"></circle>
                                    <path fill="#ffffff" d="M23.2 8.7A9.2 9.2 0 0 0 7.6 18.1L6 26l8.1-1.6a9.2 9.2 0 0 0 4.4 1.1h0A9.2 9.2 0 0 0 23.2 8.7zm-4.7 14.6h0a7.7 7.7 0 0 1-3.9-1.1l-.3-.2-4.8.9.9-4.7-.2-.3a7.7 7.7 0 1 1 8.3 5.4zm4.2-5.8c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1s-.7.8-.8 1c-.1.1-.3.2-.5.1a6.3 6.3 0 0 1-1.9-1.2 7.1 7.1 0 0 1-1.3-1.7c-.1-.2 0-.4.1-.5l.4-.4.2-.3c.1-.1.1-.3 0-.4l-.6-1.5c-.2-.4-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3s-.8.8-.8 2 .8 2.4.9 2.5c.1.2 1.6 2.5 3.9 3.5.5.2 1 .4 1.3.6.6.2 1.1.2 1.5.1.5-.1 1.4-.6 1.6-1.1.2-.5.2-1 .2-1.1s-.2-.2-.4-.3z"></path>
                                </svg>
                            </span>
                            <span>Escribir por WhatsApp</span>
                        </a>
                    </div>
                    <div class="ideas-service-card">
                        <div class="icon">Conversemos</div>
                        <h3>Estamos disponibles para ayudarte</h3>
                        <p>Si quieres optimizar tu organización, fortalecer la gestión o mejorar el control operativo, podemos acompañarte con un enfoque práctico, cercano y orientado a resultados reales.</p>
                        <div class="ideas-feature-list">
                            <div class="ideas-feature-item"><div class="glyph">💬</div><div class="content"><div class="title">Asesoramiento cercano</div><div class="detail">Acompañamiento práctico y alineado a tu realidad operativa.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">⚙</div><div class="content"><div class="title">Optimización</div><div class="detail">Procesos más claros, consistentes y eficientes.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">📊</div><div class="content"><div class="title">Mejor control</div><div class="detail">Más visibilidad para gestionar y decidir.</div></div></div>
                            <div class="ideas-feature-item"><div class="glyph">🧭</div><div class="content"><div class="title">Acompañamiento</div><div class="detail">Soporte consultivo para avanzar con método y criterio.</div></div></div>
                        </div>
                    </div>
                </div>
                <div class="ideas-editorial-band ideas-public-section">
                    <div class="block">
                        <h3>Respuesta rápida</h3>
                        <p>Podemos ayudarte a definir el mejor punto de partida según tus objetivos, tu realidad operativa y el nivel de madurez actual de tu organización.</p>
                    </div>
                    <div class="block">
                        <h3>Acceso a plataforma</h3>
                        <p>Si ya trabajas con IDEAS, puedes ingresar directamente a la plataforma operativa para cargar empresas, diagnósticos y reportes.</p>
                    </div>
                </div>
                '''
            )
