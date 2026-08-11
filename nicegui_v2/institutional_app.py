from __future__ import annotations

import os
import sys
from pathlib import Path

from nicegui import app, ui

ROOT = Path(__file__).resolve().parents[1]
THIS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(THIS_DIR) not in sys.path:
    sys.path.append(str(THIS_DIR))

from pages_public import register_public_pages  # noqa: E402
from ideas_utils import ideus_wordmark_html  # noqa: E402

app.add_static_files('/assets', str(ROOT))
FAVICON_ICO_PATH = ROOT / 'favicon.ico'
app.add_static_file(local_file=FAVICON_ICO_PATH, url_path='/favicon.ico')


def get_banner_url() -> str:
    for relative in (
        'Data/hero_institucional.png',
        'ideas_home_banner.png',
    ):
        candidate = ROOT / relative
        if candidate.exists():
            return f'/assets/{relative.replace(os.sep, "/")}'
    return '/assets/logo.png'


def public_shell(page_title: str):
    ui.page_title(f'IDEUS | {page_title}')
    ui.add_head_html(
        f'''
        <meta name="description" content="IDEUS, la plataforma de gestion inteligente desarrollada por IDEAS Consulting: procesos, riesgos, calidad, SST, documentos y KPIs en un solo workspace.">
        <meta property="og:site_name" content="IDEUS">
        <meta property="og:title" content="IDEUS | {page_title} — by IDEAS Consulting">
        <meta property="og:description" content="La plataforma de gestion inteligente desarrollada por IDEAS Consulting.">
        <style>
        body, .nicegui-content {{ font-family: Aptos, "Segoe UI Variable", "Segoe UI", sans-serif; }}
        </style>
        '''
    )
    platform_active = ' active' if page_title == 'Plataforma SaaS' else ''
    home_link_html = (
        '<a class="ideas-public-home-link" href="/">Inicio</a>'
        if page_title != 'Inicio'
        else ''
    )
    with ui.header().classes('ideas-public-topbar'):
        ui.html(
            f'''
            <div class="ideas-public-nav">
                <div class="ideas-public-brand">
                    <img src="/assets/logo.png" alt="Isotipo de IDEAS Consulting" />
                    {ideus_wordmark_html('topbar', on_dark=True)}
                </div>
                <nav class="ideas-public-menu">
                    {home_link_html}
                    <a class="ideas-public-menu-link{platform_active}" href="/soluciones/plataforma-saas">
                        <span class="material-icons" aria-hidden="true">laptop_mac</span>
                        <span>Plataforma IDEUS</span>
                    </a>
                    <a class="ideas-public-menu-link" href="/contacto">Contacto</a>
                </nav>
                <div class="ideas-public-actions">
                    <a class="ideas-whatsapp-link topbar" href="https://wa.me/541170068904" target="_blank" rel="noopener noreferrer">
                        <span class="ideas-whatsapp-icon">🟢</span>
                        <span>WhatsApp</span>
                    </a>
                </div>
            </div>
            '''
        )
    return ui.column().classes('ideas-public-shell')


register_public_pages(
    ui,
    {
        'public_shell': public_shell,
        'get_banner_url': get_banner_url,
        'platform_enabled': False,
        'ideus_wordmark_html': ideus_wordmark_html,
    },
)

render_port = os.getenv('PORT')
run_port = int(render_port) if render_port else 8502
ui.run(
    title='IDEUS | IDEAS Consulting',
    favicon=FAVICON_ICO_PATH,
    host='0.0.0.0',
    port=run_port,
    reload=False,
    native=False,
    storage_secret=os.getenv('NICEGUI_STORAGE_SECRET_PUBLIC', 'ideas-consulting-v2-public'),
)
