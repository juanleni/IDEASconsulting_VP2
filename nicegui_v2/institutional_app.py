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

app.add_static_files('/assets', str(ROOT))


def get_banner_url() -> str:
    for relative in (
        'Data/hero_institucional.png',
        'ideas_home_banner.png',
    ):
        candidate = ROOT / relative
        if candidate.exists():
            return f'/assets/{relative.replace(os.sep, "/")}'
    return '/assets/logo.png'


def public_shell(_page_title: str):
    with ui.header().classes('ideas-public-topbar'):
        ui.html(
            '''
            <div class="ideas-public-nav">
                <div class="ideas-public-brand">
                    <img src="/assets/logo.png" alt="IDEAS logo" />
                    <div>
                        <div class="name">IDEAS Consulting</div>
                        <div class="tag">Inicio</div>
                    </div>
                </div>
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
    },
)

render_port = os.getenv('PORT')
run_port = int(render_port) if render_port else 8502
ui.run(
    title='IDEAS Consulting',
    host='0.0.0.0',
    port=run_port,
    reload=False,
    native=False,
    storage_secret='ideas-consulting-v2-public',
)

