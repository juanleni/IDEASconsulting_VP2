
from __future__ import annotations

import os
import socket
import sys
import asyncio
import html
import json
import re
import tempfile
import datetime as dt
from datetime import datetime
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from nicegui import app, ui

ROOT = Path(__file__).resolve().parents[1]
THIS_DIR = Path(__file__).resolve().parent
IDEAS_STANDARD_PATH = THIS_DIR / 'data' / 'ideas_ai_standard.md'
IDEAS_STANDARD_CHANGELOG_PATH = THIS_DIR / 'data' / 'ideas_ai_versions.jsonl'
IDEAS_WELCOME_TEMPLATE_PATH = THIS_DIR / 'data' / 'ideas_ai_welcome_template.txt'
IDEAS_ASSISTANT_SETTINGS_PATH = THIS_DIR / 'data' / 'ideas_ai_settings.json'
IDEAS_ASSISTANT_CLIENT_RULES_PATH = THIS_DIR / 'data' / 'ideas_ai_client_rules.json'
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(THIS_DIR) not in sys.path:
    sys.path.append(str(THIS_DIR))

from database import crear_base  # noqa: E402
from core_data import (  # noqa: E402
    actualizar_kpi,
    actualizar_dashboard_principal_kpi,
    actualizar_grupos_personalizados_kpi,
    actualizar_kpi_meses,
    actualizar_kpi_diario_y_periodos,
    actualizar_problema_calidad_8d,
    actualizar_usuario,
    actualizar_empresa,
    actualizar_aspecto_ambiental,
    actualizar_item_riesgo,
    actualizar_matriz_riesgos,
    actualizar_proceso_mapa,
    actualizar_requisito_legal_ambiental,
    actualizar_simulacro_ambiental,
    actualizar_diagnostico,
    actualizar_password_empresa,
    agregar_kpi_empresa,
    crear_aspecto_ambiental,
    crear_item_riesgo,
    crear_matriz_riesgos,
    crear_problema_calidad_8d,
    crear_requisito_legal_ambiental,
    crear_simulacro_ambiental,
    agregar_proceso_mapa_empresa,
    eliminar_aspecto_ambiental,
    eliminar_empresa,
    eliminar_diagnostico,
    eliminar_kpi,
    eliminar_item_riesgo,
    eliminar_matriz_riesgos,
    eliminar_accion_8d,
    eliminar_problema_calidad_8d,
    eliminar_usuario,
    eliminar_proceso_mapa,
    eliminar_requisito_legal_ambiental,
    eliminar_simulacro_ambiental,
    guardar_diagnostico,
    guardar_fuente_empresa,
    guardar_5_porque_problema_calidad,
    guardar_accion_8d,
    guardar_ishikawa_problema_calidad,
    guardar_kpi,
    guardar_empresa,
    guardar_token_empresa,
    crear_usuario,
    crear_grupo_kpi_empresa,
    leer_diagnostico_excel,
    obtener_aspectos_ambientales_empresa,
    obtener_5_porque_problema_calidad,
    obtener_diagnosticos_empresa,
    obtener_empresa_detalle,
    obtener_empresas,
    obtener_historial_diagnosticos,
    obtener_fuentes_empresa,
    obtener_ishikawa_problema_calidad,
    obtener_acciones_8d,
    obtener_items_riesgos_matriz,
    obtener_kpi_detalle,
    obtener_kpis_empresa,
    obtener_grupos_kpi_empresa,
    obtener_matrices_riesgos_empresa,
    obtener_matriz_riesgos_detalle,
    obtener_mapa_procesos_empresa,
    obtener_problema_calidad_detalle,
    obtener_problemas_calidad_empresa,
    obtener_usuarios,
    obtener_requisitos_legales_ambientales_empresa,
    obtener_respuestas_diagnostico,
    obtener_simulacros_ambientales_empresa,
    obtener_alertas_globales,
    verificar_login_empresa,
    verificar_token_empresa,
    verificar_usuario,
    eliminar_fuente,
)
try:
    from core_data import provisionar_acceso_empresa  # noqa: E402
except Exception:  # pragma: no cover - compatibilidad con despliegues intermedios
    def provisionar_acceso_empresa(*_args, **_kwargs):
        return False, 'Provisionamiento no disponible en esta version.'
try:
    from core_data import (  # noqa: E402
        obtener_memoria_asistente_empresa,
        limpiar_memoria_asistente_empresa,
        guardar_evento_memoria_asistente,
    )
except Exception:  # pragma: no cover - compatibilidad con despliegues intermedios
    def obtener_memoria_asistente_empresa(*_args, **_kwargs):
        return []

    def limpiar_memoria_asistente_empresa(*_args, **_kwargs):
        return 0

    def guardar_evento_memoria_asistente(*_args, **_kwargs):
        return None
try:
    from core_data import crear_backup_db, listar_backups_db, restaurar_backup_db  # noqa: E402
except Exception:  # pragma: no cover - compatibilidad con despliegues intermedios
    def crear_backup_db(*_args, **_kwargs):
        return False, 'Backups no disponibles en esta version.'

    def listar_backups_db(*_args, **_kwargs):
        return []

    def restaurar_backup_db(*_args, **_kwargs):
        return False, 'Restauracion no disponible en esta version.'
from ideas_utils import (  # noqa: E402
    obtener_conclusion,
    obtener_impacto_sugerido,
    obtener_mensaje_direccion,
    obtener_nivel,
    obtener_plazo_sugerido,
    obtener_prioridad_recomendada,
    obtener_responsable_sugerido,
    enviar_correo_acceso,
    generar_token_seguro,
    obtener_color_contraste,
    valor_afirmativo,
)
from pages_management import (  # noqa: E402
    go_to_management_workspace,
    register_management_page,
    render_management_workspace_page,
)
from pages_public import register_public_pages  # noqa: E402
from pages_platform import register_platform_pages  # noqa: E402
from pages_diagnostic import register_diagnostic_pages  # noqa: E402
from modules_documents import (  # noqa: E402
    go_to_company_documents_module,
    go_to_documents_library,
    register_documents_module,
)
from modules_process_maps import (  # noqa: E402
    go_to_process_maps_module,
    register_process_maps_module,
)
from modules_kpi import (  # noqa: E402
    go_to_kpi_module,
    register_kpi_module,
)
from modules_risks import (  # noqa: E402
    go_to_risks_module,
    register_risks_module,
)
from modules_environment import (  # noqa: E402
    go_to_environment_module,
    register_environment_module,
)
from modules_quality import (  # noqa: E402
    go_to_quality_module,
    register_quality_module,
)
from modules_sst import (  # noqa: E402
    go_to_sst_module,
    register_sst_module,
)
from modules_users import go_to_users_module, register_users_module  # noqa: E402
try:
    from ai_services import consultar_asistente_iso, explicar_requisito_iso, sugerir_causas_ishikawa, sugerir_matriz_legal_ia  # noqa: E402
except Exception:  # pragma: no cover - compatibilidad con despliegues intermedios
    async def consultar_asistente_iso(*_args, **_kwargs):
        return 'Smart Assist no disponible temporalmente en esta version desplegada.'

    def explicar_requisito_iso(*_args, **_kwargs):
        return 'Explicacion IA no disponible temporalmente.'

    def sugerir_causas_ishikawa(*_args, **_kwargs):
        return 'Sugerencia IA no disponible temporalmente.'

    def sugerir_matriz_legal_ia(*_args, **_kwargs):
        return []
from pdf_reports import (  # noqa: E402
    generar_pdf_8d,
    generar_pdf_ejecutivo_v2,
    generar_pdf_kpis,
    generar_pdf_mapa_procesos,
    generar_reporte_8d,
    generar_reporte_simulacro,
)

crear_base()
app.add_static_files('/assets', str(ROOT))
FAVICON_ICO_PATH = ROOT / 'favicon.ico'
app.add_static_file(local_file=FAVICON_ICO_PATH, url_path='/favicon.ico')

PLATFORM_USER = 'IDEAS'
PLATFORM_PASSWORD = '2026'
SESSION_TIMEOUT_MINUTES = int(os.getenv('IDEAS_SESSION_TIMEOUT_MINUTES', '90'))
INSTITUTIONAL_ONLY = str(os.getenv('IDEAS_INSTITUTIONAL_ONLY', '0')).strip().lower() in {'1', 'true', 'yes', 'on'}


def inject_global_styles() -> None:
    ui.add_head_html(
        '''
        <style>
        :root {
            --ideas-navy: #0f172a;
            --ideas-blue: #1f7ed6;
            --ideas-green: #0f8f61;
            --ideas-line: rgba(148, 163, 184, 0.16);
            --ideas-text: #334155;
            --ideas-shadow: 0 22px 48px rgba(15, 23, 42, 0.08);
        }
        body, .nicegui-content {
            background:
                radial-gradient(circle at top left, rgba(15, 143, 97, 0.12), transparent 22%),
                radial-gradient(circle at top right, rgba(31, 126, 214, 0.14), transparent 18%),
                linear-gradient(180deg, #f6fafc 0%, #edf3f8 38%, #f7fbfd 100%);
            color: var(--ideas-text);
            font-family: Aptos, "Segoe UI Variable", "Segoe UI", sans-serif;
        }
        .ideas-shell { width: 100%; max-width: 1520px; margin: 0 auto; padding: 8px 34px 40px 34px; }
        .ideas-card, .ideas-soft, .ideas-panel, .ideas-hero-card {
            border-radius: 30px; background: rgba(255,255,255,0.9); border: 1px solid var(--ideas-line);
            box-shadow: var(--ideas-shadow); backdrop-filter: blur(14px);
        }
        .ideas-panel { padding: 24px; }
        .ideas-hero-card {
            padding: 34px; display: grid; grid-template-columns: 1.15fr 0.85fr; gap: 28px; position: relative; overflow: hidden;
        }
        .ideas-hero-card::before {
            content: ""; position: absolute; inset: 0;
            background: radial-gradient(circle at top left, rgba(15, 143, 97, 0.10), transparent 28%), radial-gradient(circle at bottom right, rgba(31, 126, 214, 0.12), transparent 26%);
            pointer-events: none;
        }
        .ideas-kicker { color: var(--ideas-green); font-size: 0.82rem; font-weight: 800; letter-spacing: 0.12em; text-transform: uppercase; }
        .ideas-title { font-size: clamp(2.3rem, 4vw, 4rem); font-weight: 800; color: var(--ideas-navy); line-height: 0.98; letter-spacing: -0.05em; margin: 12px 0; }
        .ideas-subtitle { color: #516174; font-size: 1.02rem; line-height: 1.75; }
        .ideas-chip { display:inline-flex; align-items:center; padding:.55rem .95rem; border-radius:999px; background:rgba(255,255,255,.96); border:1px solid var(--ideas-line); color:var(--ideas-navy); font-weight:700; margin-right:.55rem; margin-top:.7rem; }
        .ideas-brand-card { padding:18px 16px 20px 16px; border-radius:28px; background:linear-gradient(180deg, rgba(255,255,255,.92), rgba(248,251,253,.88)); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); margin-bottom:14px; }
        .ideas-nav-btn { width:100%; justify-content:flex-start; border-radius:18px; padding:.45rem .35rem; margin-bottom:.45rem; color:var(--ideas-navy); background:rgba(255,255,255,.8); border:1px solid rgba(255,255,255,.35); transition:all 180ms ease; }
        .ideas-nav-btn:hover { background:rgba(255,255,255,.98); transform:translateX(2px); box-shadow:0 10px 24px rgba(15,23,42,.06); }
        .ideas-nav-btn .q-btn__content { justify-content:flex-start; align-items:center; gap:.7rem; width:100%; }
        .ideas-nav-btn .q-icon { width: 20px; min-width: 20px; text-align: center; font-size: 1.1rem; display:inline-flex; align-items:center; justify-content:center; line-height:1; }
        .ideas-topbar { background:rgba(255,255,255,.72); backdrop-filter:blur(16px); border-bottom:1px solid var(--ideas-line); }
        .ideas-topbar-brand { display:flex; align-items:center; gap:.85rem; }
        .ideas-topbar-brand img { width:36px; height:36px; object-fit:contain; }
        .ideas-topbar-brand .brand-title { color:var(--ideas-navy); font-weight:800; line-height:1; }
        .ideas-topbar-brand .brand-subtitle { color:#64748b; font-size:.82rem; margin-top:.18rem; }
        .ideas-hero-brand { display:flex; align-items:center; gap:1rem; margin-bottom:1rem; }
        .ideas-hero-brand img { width:68px; height:68px; object-fit:contain; filter:drop-shadow(0 12px 22px rgba(15,23,42,.10)); }
        .ideas-hero-brand .brand-name { color:var(--ideas-navy); font-size:1.05rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }
        .ideas-hero-brand .brand-tag { color:#64748b; font-size:.9rem; margin-top:.18rem; letter-spacing:.02em; }
        .ideas-metric { padding:22px 24px; border-radius:26px; background:linear-gradient(180deg, rgba(255,255,255,.96), rgba(250,252,255,.9)); border:1px solid var(--ideas-line); box-shadow:0 18px 32px rgba(15,23,42,.06); }
        .ideas-metric .label { color:#64748b; font-size:.76rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
        .ideas-metric .value { margin-top:10px; font-size:2.2rem; font-weight:800; color:var(--ideas-navy); line-height:1; letter-spacing:-.04em; }
        .ideas-metric .detail { margin-top:10px; color:#475569; line-height:1.55; }
        .ideas-grid-2 { display:grid; grid-template-columns:1.1fr .9fr; gap:22px; }
        .ideas-grid-3 { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:18px; }
        .ideas-score-guide { display:grid; grid-template-columns:repeat(4, minmax(0, 1fr)); gap:14px; }
        .ideas-score-item { padding:18px; border-radius:20px; background:rgba(255,255,255,.94); border:1px solid var(--ideas-line); }
        .ideas-score-item .badge { width:36px; height:36px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:rgba(31,126,214,.10); color:#1f7ed6; font-weight:800; }
        .ideas-section-title { font-size:1.5rem; font-weight:800; color:var(--ideas-navy); letter-spacing:-.03em; }
        .ideas-section-note { color:#64748b; line-height:1.7; margin-top:4px; }
        .ideas-workspace-banner { padding:28px 30px; border-radius:30px; background:linear-gradient(135deg, #0f172a 0%, #12314d 52%, #0f8f61 100%); color:#f8fbff; box-shadow:0 24px 50px rgba(15,23,42,.18); }
        .ideas-workspace-banner .eyebrow { color:rgba(255,255,255,.72); font-size:.78rem; text-transform:uppercase; letter-spacing:.14em; font-weight:800; }
        .ideas-workspace-banner .headline { margin-top:10px; font-size:2rem; font-weight:800; line-height:1.02; letter-spacing:-.04em; }
        .ideas-workspace-banner .support { margin-top:10px; color:rgba(255,255,255,.84); line-height:1.7; max-width:72ch; }
        .ideas-module-grid { display:grid; grid-template-columns:repeat(3, minmax(0, 1fr)); gap:18px; }
        .ideas-module-card { padding:24px; border-radius:28px; background:rgba(255,255,255,.95); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); min-height:100%; display:flex; flex-direction:column; gap:14px; }
        .ideas-module-top { display:flex; align-items:flex-start; justify-content:space-between; gap:12px; }
        .ideas-module-icon { width:48px; height:48px; border-radius:16px; display:inline-flex; align-items:center; justify-content:center; background:linear-gradient(180deg, rgba(31,126,214,.12), rgba(15,143,97,.10)); color:#1d3f5c; font-size:1.2rem; }
        .ideas-module-state { display:inline-flex; align-items:center; padding:.35rem .75rem; border-radius:999px; background:rgba(15,143,97,.10); color:#0f8f61; font-size:.72rem; font-weight:800; letter-spacing:.08em; text-transform:uppercase; }
        .ideas-module-card h3 { margin:0; color:var(--ideas-navy); font-size:1.16rem; font-weight:800; letter-spacing:-.02em; word-break:normal; overflow-wrap:normal; hyphens:none; text-wrap:pretty; }
        .ideas-module-card p { margin:0; color:#526172; line-height:1.72; word-break:normal; overflow-wrap:normal; hyphens:none; }
        .ideas-mini-list { display:flex; flex-direction:column; gap:8px; margin-top:2px; }
        .ideas-mini-list .item { display:flex; align-items:flex-start; gap:10px; color:#475569; line-height:1.55; }
        .ideas-mini-list .dot { width:9px; height:9px; border-radius:999px; margin-top:7px; background:linear-gradient(180deg, #1f7ed6, #0f8f61); flex:0 0 auto; }
        .ideas-result-banner { padding:24px 26px; border-radius:28px; background:linear-gradient(135deg, #0f172a 0%, #15324f 52%, #1f7ed6 100%); color:#f8fbff; box-shadow:0 22px 48px rgba(17,24,39,.22); }
        .ideas-result-banner .eyebrow { color:rgba(255,255,255,.7); font-size:.78rem; text-transform:uppercase; letter-spacing:.12em; font-weight:800; }
        .ideas-result-banner .headline { margin-top:10px; font-size:2rem; font-weight:800; line-height:1; letter-spacing:-.04em; }
        .ideas-result-banner .support { margin-top:10px; color:rgba(255,255,255,.82); line-height:1.65; }
        .ideas-quick-card { padding:20px 22px; border-radius:24px; background:rgba(255,255,255,.94); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); }
        .ideas-quick-card .label { color:#64748b; text-transform:uppercase; letter-spacing:.1em; font-size:.75rem; font-weight:800; }
        .ideas-quick-card .value { color:var(--ideas-navy); font-size:1.2rem; font-weight:800; margin-top:8px; }
        .ideas-quick-card .detail { color:#516174; line-height:1.65; margin-top:8px; }
        .ideas-table table { border-radius:24px; overflow:hidden; }
        .ideas-table thead tr { background:rgba(15,23,42,.03); }
        .ideas-table tbody tr:hover { background:rgba(31,126,214,.04); }
        .ideas-mode-banner { padding:18px 22px; border-radius:24px; background:linear-gradient(135deg, #0f172a 0%, #1f7ed6 100%); color:#eff6ff; margin-bottom:18px; }
        .ideas-mode-banner strong { display:block; font-size:1.1rem; margin-top:.2rem; }
        .ideas-public-shell { width:100%; max-width:1320px; margin:0 auto; padding:0 28px 48px 28px; }
        .ideas-public-topbar { position:sticky; top:0; z-index:50; background:rgba(25,25,25,.92); backdrop-filter:blur(18px); border-bottom:1px solid rgba(255,255,255,.08); }
        .ideas-public-nav { display:grid; grid-template-columns:minmax(0, 1fr) auto; align-items:center; gap:1rem; width:100vw; max-width:none; margin:0; padding:18px 72px; box-sizing:border-box; position:relative; left:50%; transform:translateX(-50%); }
        .ideas-public-brand { display:flex; align-items:center; gap:1rem; }
        .ideas-public-brand img { width:58px; height:58px; object-fit:contain; }
        .ideas-public-brand .name { color:#f8fafc; font-weight:900; font-size:1.15rem; letter-spacing:.01em; }
        .ideas-public-brand .tag { color:rgba(255,255,255,.58); font-size:.86rem; margin-top:.16rem; }
        .ideas-public-links { display:flex; align-items:center; gap:.4rem; flex-wrap:wrap; }
        .ideas-public-links a { color:#334155; text-decoration:none; font-weight:700; padding:.7rem .9rem; border-radius:999px; }
        .ideas-public-links a:hover { background:rgba(255,255,255,.9); }
        .ideas-public-actions { display:flex; align-items:center; justify-content:flex-end; justify-self:end; gap:1.1rem; flex-wrap:wrap; }
        .ideas-public-home-link { text-decoration:none; color:rgba(255,255,255,.72); font-weight:850; padding:8px 0; }
        .ideas-public-home-link:hover { color:#d6df00; }
        .ideas-public-return-link { display:inline-flex; align-items:center; gap:8px; min-height:42px; padding:0 14px; border-radius:2px; text-decoration:none; color:#f8fafc; font-weight:900; border:1px solid rgba(255,255,255,.18); }
        .ideas-public-return-link:hover { color:#171717; background:#d6df00; border-color:#d6df00; }
        .ideas-public-return-link .material-icons { font-size:1.2rem; line-height:1; }
        .ideas-public-login-link { display:inline-flex; align-items:center; gap:8px; min-height:42px; padding:0 18px; border-radius:2px; text-decoration:none; background:#d6df00; color:#171717; font-weight:900; border:1px solid #d6df00; }
        .ideas-public-login-link .material-icons { font-size:1.2rem; line-height:1; }
        .ideas-public-login-link:hover { background:#f0f715; color:#171717; }
        .ideas-public-hero { display:grid; grid-template-columns:1.08fr .92fr; gap:20px; align-items:stretch; margin-top:0; }
        .ideas-public-card { border-radius:32px; background:rgba(255,255,255,.94); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); }
        .ideas-public-hero-copy { padding:34px 38px; position:relative; overflow:hidden; }
        .ideas-public-hero-copy::before { content:""; position:absolute; inset:0; background:radial-gradient(circle at top left, rgba(15,143,97,.10), transparent 28%), radial-gradient(circle at bottom right, rgba(31,126,214,.12), transparent 24%); pointer-events:none; }
        .ideas-public-hero-copy > * { position:relative; z-index:1; }
        .ideas-public-hero-media { padding:18px; }
        .ideas-public-title { font-size:clamp(2.35rem, 4.4vw, 4rem); line-height:1.02; letter-spacing:-.045em; color:var(--ideas-navy); font-weight:700; margin:10px 0 14px; max-width:13ch; text-wrap:balance; word-break:normal; overflow-wrap:normal; hyphens:none; }
        .ideas-public-lead { color:#526172; font-size:1rem; line-height:1.78; max-width:60ch; }
        .ideas-public-stat { padding:24px; border-radius:28px; background:linear-gradient(180deg, rgba(255,255,255,.98), rgba(248,251,254,.92)); border:1px solid var(--ideas-line); box-shadow:0 16px 30px rgba(15,23,42,.05); }
        .ideas-public-stat .value { color:var(--ideas-navy); font-size:2rem; font-weight:800; letter-spacing:-.04em; }
        .ideas-public-stat .label { color:#64748b; font-size:.78rem; font-weight:800; letter-spacing:.12em; text-transform:uppercase; }
        .ideas-public-section { margin-top:0; }
        .ideas-public-section h2 { color:var(--ideas-navy); font-size:2.2rem; font-weight:800; letter-spacing:-.04em; margin-bottom:10px; }
        .ideas-public-section p { color:#526172; line-height:1.8; }
        .ideas-service-card { padding:28px; border-radius:28px; background:rgba(255,255,255,.96); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); min-height:100%; overflow:hidden; }
        .ideas-service-card .icon { width:max-content; min-width:52px; max-width:100%; min-height:30px; padding:6px 12px; border-radius:999px; display:inline-flex; align-items:center; justify-content:center; background:linear-gradient(180deg, rgba(31,126,214,.10), rgba(15,143,97,.08)); color:#35506c; font-size:.72rem; font-weight:700; letter-spacing:.05em; text-transform:none; margin-bottom:16px; line-height:1.15; flex-wrap:wrap; }
        .ideas-service-card h3 { color:var(--ideas-navy); font-size:1.28rem; font-weight:800; margin:0 0 10px; word-break:normal; overflow-wrap:normal; hyphens:none; text-wrap:pretty; }
        .ideas-service-card p { color:#526172; line-height:1.75; margin:0; word-break:normal; overflow-wrap:normal; hyphens:none; }
        .ideas-list-clean { margin:0; padding-left:1.05rem; color:#526172; line-height:1.9; }
        .ideas-cta-band { padding:34px; border-radius:32px; background:linear-gradient(135deg, #0f172a 0%, #13314b 55%, #1f7ed6 100%); color:#f8fbff; box-shadow:0 24px 48px rgba(15,23,42,.18); }
        .ideas-cta-band h3 { font-size:2rem; font-weight:800; letter-spacing:-.04em; margin:0 0 12px; }
        .ideas-cta-band p { color:rgba(255,255,255,.82); line-height:1.8; margin:0; }
        .ideas-editorial-band { display:grid; grid-template-columns:1fr 1fr; gap:22px; margin-top:24px; }
        .ideas-editorial-band .block { padding:26px 28px; border-radius:28px; background:rgba(255,255,255,.95); border:1px solid var(--ideas-line); box-shadow:var(--ideas-shadow); }
        .ideas-editorial-band .block h3 { margin:0 0 12px; color:var(--ideas-navy); font-size:1.34rem; font-weight:800; letter-spacing:-.03em; }
        .ideas-editorial-band .block p { margin:0; color:#526172; line-height:1.8; }
        .ideas-whatsapp-link { display:inline-flex; align-items:center; gap:.7rem; margin-top:16px; padding:.85rem 1.1rem; border-radius:16px; text-decoration:none; background:linear-gradient(180deg, rgba(37,211,102,.14), rgba(37,211,102,.08)); border:1px solid rgba(37,211,102,.22); color:#166534; font-weight:800; }
        .ideas-whatsapp-link:hover { transform:translateY(-1px); box-shadow:0 12px 24px rgba(22,101,52,.12); }
        .ideas-whatsapp-link.topbar { margin-top:0; padding:0; border-radius:0; font-size:1rem; background:transparent; border:0; color:#25D366; box-shadow:none; }
        .ideas-whatsapp-link.topbar:hover { box-shadow:none; color:#46f184; }
        .ideas-whatsapp-icon { width:28px; height:28px; display:inline-flex; align-items:center; justify-content:center; }
        .ideas-whatsapp-icon svg { width:28px; height:28px; display:block; }
        .ideas-feature-list { display:grid; grid-template-columns:repeat(2, minmax(0, 1fr)); gap:12px; margin-top:16px; }
        .ideas-feature-item { display:flex; align-items:flex-start; gap:12px; padding:13px 14px; border-radius:18px; background:rgba(248,250,252,.84); border:1px solid rgba(148,163,184,.12); min-width:0; }
        .ideas-feature-item .glyph { width:34px; height:34px; border-radius:12px; display:inline-flex; align-items:center; justify-content:center; background:linear-gradient(180deg, rgba(31,126,214,.10), rgba(15,143,97,.08)); color:#31506d; font-size:.9rem; font-weight:700; flex:0 0 auto; }
        .ideas-feature-item .content { display:flex; flex-direction:column; gap:2px; }
        .ideas-feature-item .title { color:var(--ideas-navy); font-weight:700; line-height:1.24; word-break:normal; overflow-wrap:normal; hyphens:none; text-wrap:pretty; }
        .ideas-feature-item .detail { color:#64748b; line-height:1.48; font-size:.89rem; word-break:normal; overflow-wrap:normal; hyphens:none; }
        .ideas-public-section h2, .ideas-public-section p, .ideas-login-title, .ideas-login-note, .ideas-kicker, .ideas-chip, .ideas-quick-card .value, .ideas-quick-card .detail { word-break:normal; overflow-wrap:normal; hyphens:none; }
        .ideas-login-card { max-width:560px; margin-top:8px; padding:30px 32px; }
        .ideas-login-title { color:var(--ideas-navy); font-size:1.9rem; font-weight:700; letter-spacing:-.03em; margin:0 0 10px; }
        .ideas-login-note { color:#5b6878; line-height:1.8; margin-bottom:18px; }
        .nicegui-content, .q-page { padding:0 !important; }
        .q-drawer { background:radial-gradient(circle at top left, rgba(15,143,97,.09), transparent 28%), linear-gradient(180deg, rgba(249,252,251,.99) 0%, rgba(239,246,243,.99) 100%); border-right:1px solid var(--ideas-line); }
        .q-field__control, .q-field--outlined .q-field__control { border-radius:18px !important; background:rgba(255,255,255,.92); }
        .q-btn { text-transform:none; letter-spacing:0; font-weight:700; }
        .q-tab { border-radius:16px; min-height:44px; }
        .q-tab--active { background:rgba(31,126,214,.08); }
        .ideas-ai-drawer { background: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 100%); border-left: 1px solid rgba(15, 23, 42, 0.1); }
        .ideas-ai-drawer.q-drawer {
            z-index: 12000 !important;
        }
        .ideas-ai-drawer .q-drawer__content {
            position: relative;
            z-index: 12001;
        }
        .ideas-ai-chip { display:inline-flex; align-items:center; gap:6px; width:max-content; padding:4px 10px; border-radius:999px; border:1px solid rgba(15, 23, 42, 0.12); background:#d6df00; color:#171717; font-size:.72rem; font-weight:800; letter-spacing:.04em; text-transform:uppercase; }
        .ideas-ai-chat-panel { border:1px solid rgba(15, 23, 42, 0.1); background:#ffffff; border-radius:20px; }
        .ideas-ai-drawer .q-message-text { border-radius:14px; padding:10px 12px; line-height:1.5; }
        .ideas-ai-drawer .q-message-text--sent { background:#d6df00; color:#171717; }
        .ideas-ai-drawer .q-message-text--received { background:#1e3a5f; color:#f8fafc; }
        .ideas-ai-drawer .q-message-text--received,
        .ideas-ai-drawer .q-message-text--received * { color:#f8fafc !important; }
        .ideas-ai-drawer .q-message-text--sent,
        .ideas-ai-drawer .q-message-text--sent * { color:#171717 !important; }
        .ideas-ai-drawer .q-message-name { color:#475569; font-weight:700; }
        .ideas-ai-input .q-field__control { border-radius:12px; background:#ffffff; border:1px solid rgba(15, 23, 42, 0.14); }
        .ideas-ai-send { background:#0f172a; color:#f8fafc; }
        .ideas-ai-send:hover { background:#1e293b; }
        .ideas-8d-dialog .q-dialog__inner {
            padding-right: 420px;
            align-items: center;
        }
        .ideas-ai-avatar {
            width: 28px;
            height: 28px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(180deg, #d6df00, #ecf25d);
            color: #1f2937;
            box-shadow: 0 0 0 1px rgba(15,23,42,.08), 0 6px 14px rgba(15,23,42,.16);
            animation: ideas-ai-bob 2.8s ease-in-out infinite;
            transform-origin: center;
        }
        @keyframes ideas-ai-bob {
            0% { transform: translateY(0) scale(1); }
            50% { transform: translateY(-2px) scale(1.03); }
            100% { transform: translateY(0) scale(1); }
        }
        @media (max-width: 1400px) {
            .ideas-8d-dialog .q-dialog__inner { padding-right: 360px; }
        }
        @media (max-width: 1200px) {
            .ideas-8d-dialog .q-dialog__inner { padding-right: 0; }
        }
        @media (max-width: 1100px) { .ideas-hero-card, .ideas-score-guide, .ideas-grid-2, .ideas-grid-3, .ideas-public-hero, .ideas-editorial-band, .ideas-feature-list, .ideas-module-grid { grid-template-columns:1fr; } .ideas-public-nav { grid-template-columns:1fr; align-items:flex-start; padding:16px 24px; left:0; transform:none; width:100%; } .ideas-public-actions { justify-self:start; justify-content:flex-start; } }
        @media (max-width: 520px) { .ideas-public-shell { padding:0 16px 36px 16px; } .ideas-public-nav { padding:14px 18px; gap:14px; } .ideas-public-brand img { width:42px; height:42px; } .ideas-public-brand .name { font-size:1rem; } .ideas-public-brand .tag { font-size:.78rem; } .ideas-public-actions { width:100%; justify-content:space-between; gap:12px; } .ideas-public-login-link, .ideas-public-return-link { min-height:40px; padding:0 14px; } .ideas-whatsapp-link.topbar span:last-child { display:none; } .ideas-login-card { max-width:100%; padding:24px 20px; } .ideas-public-section h2 { font-size:1.8rem; } }
        </style>
        '''
    )


def fix_text(value) -> str:
    if value is None:
        return ''
    text = str(value)
    if any(token in text for token in ['\u00c3', '\u00c2', '\u00f0', '\ufffd']):
        try:
            return text.encode('latin-1').decode('utf-8')
        except Exception:
            return text
    return text


def load_criteria() -> tuple[list[dict], str]:
    path = ROOT / 'Data' / 'diagnostico.xlsx'
    criterios_default = [
        {'escala': 1, 'nivel': 'Inicial', 'resumen': 'Existe de forma informal o depende de personas.'},
        {'escala': 2, 'nivel': 'Parcial', 'resumen': 'Está definido, pero se aplica con inconsistencias.'},
        {'escala': 3, 'nivel': 'Implementado', 'resumen': 'Se aplica regularmente con evidencia disponible.'},
        {'escala': 4, 'nivel': 'Estandarizado', 'resumen': 'Está sistematizado, controlado y en mejora continua.'},
    ]
    regla = 'Si la empresa dice que lo hace pero no muestra evidencia, no debería superar 2 puntos.'
    if not path.exists():
        return criterios_default, regla
    try:
        criterios_df = pd.read_excel(path, sheet_name='CRITERIOS DE EVALUACION')
        criterios_df.columns = [str(col).strip().upper() for col in criterios_df.columns]
        criterios_df = criterios_df[criterios_df['ESCALA'].isin([1, 2, 3, 4])].copy()
        criterios = [
            {'escala': int(row['ESCALA']), 'nivel': fix_text(str(row.get('NIVEL', '')).strip()), 'resumen': fix_text(str(row.get('DESCRIPCION GENERAL', '')).strip())}
            for _, row in criterios_df.iterrows()
        ]
        instrucciones_df = pd.read_excel(path, sheet_name='INSTRUCCIONES', header=None)
        for _, row in instrucciones_df.iterrows():
            if len(row) > 1 and str(row.iloc[0]).strip().lower() == 'regla de evidencia':
                valor = str(row.iloc[1]).strip()
                if valor and valor.lower() != 'nan':
                    regla = fix_text(valor)
                break
        return criterios or criterios_default, regla
    except Exception:
        return criterios_default, regla


def build_eje_scores(respuestas: list[dict]) -> tuple[pd.DataFrame, pd.DataFrame]:
    df = pd.DataFrame(respuestas)
    if df.empty:
        return pd.DataFrame(columns=['EJE', 'PREGUNTA', 'RESPUESTA', 'EVIDENCIA', 'OBSERVACION']), pd.DataFrame(columns=['EJE', 'RESPUESTA'])
    df = df.rename(columns={'eje': 'EJE', 'pregunta': 'PREGUNTA', 'respuesta': 'RESPUESTA', 'evidencia': 'EVIDENCIA', 'observacion': 'OBSERVACION'})
    eje_scores_df = df.groupby('EJE', dropna=True)['RESPUESTA'].mean().reset_index()
    return df, eje_scores_df


def build_plan(df_resp: pd.DataFrame, eje_scores_df: pd.DataFrame) -> pd.DataFrame:
    eje_map = dict(zip(eje_scores_df['EJE'], eje_scores_df['RESPUESTA']))
    prioridades_df = df_resp[df_resp['RESPUESTA'] <= 2].copy()
    mejoras_df = df_resp[df_resp['RESPUESTA'] == 3].copy()
    oportunidades = pd.concat([prioridades_df, mejoras_df], ignore_index=True)
    if oportunidades.empty:
        oportunidades = df_resp.sort_values('RESPUESTA', ascending=True).copy()
    rows = []
    for _, row in oportunidades.iterrows():
        eje = row['EJE']
        score_eje = float(eje_map.get(eje, row['RESPUESTA']))
        accion = f"Corregir y estandarizar {str(row['PREGUNTA']).strip().lower()}." if int(row['RESPUESTA']) <= 2 else f"Fortalecer y consolidar {str(row['PREGUNTA']).strip().lower()}."
        rows.append({'area': eje, 'categoria': 'Acción prioritaria' if int(row['RESPUESTA']) <= 2 else 'Oportunidad de mejora', 'prioridad': 'Alta' if score_eje < 2 else 'Media' if int(row['RESPUESTA']) <= 2 else 'Oportunidad', 'responsable': obtener_responsable_sugerido(eje), 'plazo': obtener_plazo_sugerido(score_eje), 'impacto': obtener_impacto_sugerido(score_eje), 'accion': accion[:140].capitalize(), 'estado': 'Pendiente'})
    return pd.DataFrame(rows)


def get_logo_url() -> str:
    return '/assets/logo.png' if (ROOT / 'logo.png').exists() else ''


def get_banner_url() -> str:
    return '/assets/ideas_home_banner.png' if (ROOT / 'ideas_home_banner.png').exists() else ''


def is_platform_authenticated() -> bool:
    if not app.storage.user.get('platform_auth'):
        return False
    if str(app.storage.user.get('auth_source') or '').strip().lower() == 'api':
        return bool(app.storage.user.get('jwt_token'))
    return True


def _touch_session_activity() -> None:
    app.storage.user['last_activity_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def _session_is_expired() -> bool:
    last = str(app.storage.user.get('last_activity_at') or '').strip()
    if not last:
        return False
    try:
        then = dt.datetime.strptime(last, '%Y-%m-%d %H:%M:%S')
    except Exception:
        return False
    return (dt.datetime.now() - then).total_seconds() > max(10, SESSION_TIMEOUT_MINUTES * 60)


def _required_systems_for_page(page_title: str) -> set[str]:
    title = str(page_title or '').strip().lower()
    if 'calidad' in title:
        return {'cert_iso_9001', 'cert_iatf'}
    if 'ambient' in title:
        return {'cert_iso_14001'}
    if 'salud' in title or 'sst' in title:
        return {'cert_iso_45001'}
    if any(key in title for key in ('kpi', 'indicador', 'riesgo', 'document', 'proceso', 'mapa')):
        return {'cert_iso_9001', 'cert_iso_14001', 'cert_iso_45001', 'cert_iatf'}
    return set()


def _can_access_page_by_role_and_scope(page_title: str) -> bool:
    role = str(app.storage.user.get('role') or '').strip().lower()
    if role == 'admin' and _is_admin_session():
        return True
    if role != 'empresa':
        return False
    empresa_id = current_company_id_for_ai()
    if not empresa_id:
        return False
    try:
        detalle = obtener_empresa_detalle(int(empresa_id)) or {}
    except Exception:
        return False
    required = _required_systems_for_page(page_title)
    if required:
        has_cert = any(valor_afirmativo(detalle.get(key)) for key in required)
        if not has_cert:
            return False
    permisos = str(app.storage.user.get('permisos') or 'ALL').strip()
    if permisos == 'ALL':
        return True
    tokens = {item.strip() for item in permisos.split(',') if item.strip()}
    # Mapa modulo->token de permiso (misma base que sistemas_activos en workspace)
    title = str(page_title or '').strip().lower()
    if 'ambient' in title:
        needed_token = 'cert_iso_14001'
    elif 'salud' in title or 'sst' in title:
        needed_token = 'cert_iso_45001'
    elif 'calidad' in title:
        needed_token = 'cert_iso_9001'
    else:
        needed_token = 'cert_iso_9001'
    return needed_token in tokens or ('cert_iatf' in tokens and needed_token == 'cert_iso_9001')


def current_company_id_for_ai() -> int | None:
    role = str(app.storage.user.get('role') or '')
    empresa_id = app.storage.user.get('logged_empresa_id') if role == 'empresa' else None
    if not empresa_id:
        empresa_id = app.storage.user.get('management_company_id') or app.storage.user.get('current_empresa_id')
    try:
        return int(empresa_id) if empresa_id else None
    except Exception:
        return None


def current_user_key_for_ai() -> str:
    role = str(app.storage.user.get('role') or '').strip().lower()
    raw = str(app.storage.user.get('session_user_key') or '').strip().lower()
    if raw:
        return raw
    if role == 'admin':
        return 'admin'
    empresa_id = app.storage.user.get('logged_empresa_id')
    if empresa_id:
        return f'empresa_{empresa_id}'
    return 'anon'


def is_ai_enabled_for_current_context() -> bool:
    empresa_id = current_company_id_for_ai()
    if not empresa_id:
        return True
    try:
        detalle = obtener_empresa_detalle(int(empresa_id)) or {}
    except Exception:
        return False
    return valor_afirmativo(detalle.get('agente_ia_activo'))


def set_ai_focus_context(module: str, payload: dict | None) -> None:
    app.storage.user['ai_focus_context'] = {
        'module': str(module or '').strip(),
        'payload': payload or {},
    }


def assistant_display_name_for_page(page_title: str) -> str:
    title = str(page_title or '').strip().lower()
    if 'ambient' in title:
        return 'Smart IdeAs Sustentable'
    if 'salud' in title or 'sst' in title:
        return 'Smart IdeAs Seguro'
    if 'calidad' in title or '8d' in title:
        return 'Smart IdeAs Analitico'
    if 'document' in title:
        return 'Smart IdeAs Documental'
    if 'kpi' in title:
        return 'Smart IdeAs Performance'
    if 'riesgo' in title:
        return 'Smart IdeAs Riesgos'
    if 'mapa' in title or 'proceso' in title:
        return 'Smart IdeAs Procesos'
    return 'Smart IdeAs'


def assistant_icon_for_page(page_title: str) -> tuple[str, str]:
    title = str(page_title or '').strip().lower()
    if 'ambient' in title:
        return 'eco', 'text-emerald-600'
    if 'salud' in title or 'sst' in title:
        return 'health_and_safety', 'text-rose-600'
    if 'calidad' in title or '8d' in title:
        return 'precision_manufacturing', 'text-indigo-600'
    if 'document' in title:
        return 'description', 'text-sky-600'
    if 'kpi' in title:
        return 'query_stats', 'text-violet-600'
    if 'riesgo' in title:
        return 'shield', 'text-amber-600'
    if 'mapa' in title or 'proceso' in title:
        return 'alt_route', 'text-cyan-600'
    return 'auto_awesome', 'text-blue-700'


def assistant_module_key_for_page(page_title: str) -> str:
    title = str(page_title or '').strip().lower()
    if 'ambient' in title:
        return 'ambiental'
    if 'salud' in title or 'sst' in title:
        return 'sst'
    if 'calidad' in title or '8d' in title:
        return 'calidad'
    if 'document' in title:
        return 'documents'
    if 'kpi' in title:
        return 'kpi'
    if 'riesgo' in title:
        return 'riesgos'
    if 'mapa' in title or 'proceso' in title:
        return 'procesos'
    return 'general'


def assistant_route_hints_for_query(user_text: str) -> list[tuple[str, str]]:
    text = str(user_text or '').strip().lower()
    hints: list[tuple[str, str]] = []

    def add(label: str, route: str) -> None:
        if (label, route) not in hints:
            hints.append((label, route))

    if any(token in text for token in ('iso 9001', 'iso 14001', 'iso 45001', 'iatf', 'clausula', 'cláusula', 'requisito', 'norma', 'procedimiento', 'documento')):
        add('Abrir Documentos', '/sistema-gestion/documentos')
    if any(token in text for token in ('kpi', 'indicador', 'ppm', 'scrap', 'tendencia', 'objetivo')):
        add('Abrir KPI', '/sistema-gestion/kpis')
    if any(token in text for token in ('riesgo', 'npr', 'matriz de riesgos', 'oportunidad')):
        add('Abrir Riesgos', '/sistema-gestion/riesgos')
    if any(token in text for token in ('8d', 'ishikawa', '5 porques', 'causa raiz', 'causa raíz', 'no conformidad')):
        add('Abrir Calidad (8D)', '/sistema-gestion/calidad')
    if any(token in text for token in ('aspecto ambiental', 'impacto ambiental', 'legal ambiental', 'simulacro ambiental', 'iso 14001')):
        add('Abrir Ambiental', '/sistema-gestion/ambiental')
    if any(token in text for token in ('sst', 'salud ocupacional', 'seguridad', 'incidente', 'accidente', 'iso 45001')):
        add('Abrir Salud Ocupacional', '/sistema-gestion/salud-ocupacional')
    if any(token in text for token in ('proceso', 'mapa de proceso', 'flujo de proceso')):
        add('Abrir Mapas de Proceso', '/sistema-gestion/mapas')

    return hints[:2]


def is_navigation_style_query(user_text: str) -> bool:
    text = str(user_text or '').strip().lower()
    triggers = (
        'donde', 'dónde', 'donde encuentro', 'dónde encuentro',
        'como accedo', 'cómo accedo', 'en que modulo', 'en qué módulo',
        'donde esta', 'dónde está', 'donde veo', 'dónde veo',
    )
    return any(token in text for token in triggers)


def detect_ai_task_type(user_text: str, page_title: str) -> str:
    text = str(user_text or '').strip().lower()
    page = str(page_title or '').strip().lower()
    if any(token in text for token in ('plantilla', 'generar procedimiento', 'generar checklist', 'generar plan de accion', 'generar plan de acción', 'borrador')):
        return 'generacion_automatica'
    if any(token in text for token in ('kpi', 'indicador', 'ppm', 'scrap', 'tendencia', 'objetivo', 'desvio', 'desvío')) or 'kpi' in page:
        return 'interpretacion_kpi'
    if any(token in text for token in ('auditoria', 'auditoría', 'hallazgo', 'checklist auditoria', 'cumplimiento', 'evidencia faltante')):
        return 'auditor_ia'
    if any(token in text for token in ('iso', 'iatf', 'clausula', 'cláusula', 'documento', 'procedimiento', 'registro', 'norma')):
        return 'chat_documental'
    return 'general'


def build_ai_working_context(page_title: str) -> str:
    empresa_id = current_company_id_for_ai()
    if not empresa_id:
        return 'No hay empresa activa seleccionada.'
    parts: list[str] = [f'Pantalla actual: {page_title}', f'Empresa activa ID: {empresa_id}']
    try:
        empresa = obtener_empresa_detalle(int(empresa_id)) or {}
        razon = fix_text(str(empresa.get('razon_social') or '')).strip()
        if razon:
            parts.append(f'Empresa: {razon}')
        rubro = fix_text(str(empresa.get('rubro') or '')).strip()
        if rubro:
            parts.append(f'Rubro principal: {rubro}')
        certs = certifications_summary(empresa)
        if certs:
            parts.append(f'Certificaciones: {certs}')
    except Exception:
        pass

    try:
        diag_options = obtener_diagnosticos_empresa(int(empresa_id)) or []
        if diag_options:
            diag_id, fecha, score, nivel, _conclusion = diag_options[0]
            parts.append(
                f'Diagnostico mas reciente: id={diag_id}, fecha={fecha}, score={float(score):.2f}, nivel={fix_text(str(nivel))}'
            )
        else:
            parts.append('Diagnostico: sin registros para la empresa.')
    except Exception:
        parts.append('No se pudo leer diagnostico reciente.')

    try:
        kpis = obtener_kpis_empresa(int(empresa_id)) or []
        activos = []
        for row in kpis[:6]:
            nombre = fix_text(str(row.get('nombre') or '')).strip()
            objetivo = str(row.get('objetivo') or row.get('meta') or '').strip()
            tendencia = fix_text(str(row.get('tendencia') or '')).strip()
            if nombre:
                activos.append(f'{nombre} (objetivo={objetivo or "n/d"}, tendencia={tendencia or "n/d"})')
        parts.append(f'KPIs ({len(kpis)}): ' + ('; '.join(activos) if activos else 'sin detalle'))
    except Exception:
        parts.append('No se pudo leer KPIs.')

    try:
        matrices = obtener_matrices_riesgos_empresa(int(empresa_id)) or []
        parts.append(f'Riesgos: matrices activas={len(matrices)}')
        if matrices:
            matriz_id = int(matrices[0].get('id') or 0)
            if matriz_id:
                items = obtener_items_riesgos_matriz(matriz_id) or []
                altos = [it for it in items if int(it.get('npr') or 0) >= 12]
                parts.append(f'Riesgos historicos relevantes (NPR>=12): {len(altos)}')
    except Exception:
        parts.append('No se pudo leer riesgos.')

    try:
        procesos = obtener_mapa_procesos_empresa(int(empresa_id)) or []
        process_names = [fix_text(str(p.get('proceso_nombre') or '')).strip() for p in procesos[:4] if fix_text(str(p.get('proceso_nombre') or '')).strip()]
        parts.append(f'Mapas de proceso ({len(procesos)}): ' + (', '.join(process_names) if process_names else 'sin detalle'))
    except Exception:
        parts.append('No se pudo leer mapas de proceso.')

    try:
        problemas = obtener_problemas_calidad_empresa(int(empresa_id)) or []
        if problemas:
            p = problemas[0]
            numero = fix_text(str(p.get('numero_8d') or '')).strip()
            titulo = fix_text(str(p.get('titulo') or '')).strip()
            estado = fix_text(str(p.get('estado') or '')).strip()
            parts.append(f'Calidad 8D reciente: numero={numero or "n/d"}, titulo={titulo or "n/d"}, estado={estado or "n/d"}')
        else:
            parts.append('Calidad 8D: sin reportes cargados.')
    except Exception:
        parts.append('No se pudo leer calidad 8D.')

    try:
        aspects = obtener_aspectos_ambientales_empresa(int(empresa_id)) or []
        legal = obtener_requisitos_legales_ambientales_empresa(int(empresa_id)) or []
        drills = obtener_simulacros_ambientales_empresa(int(empresa_id)) or []
        parts.append(f'Ambiental: aspectos={len(aspects)}, legales={len(legal)}, simulacros={len(drills)}')
    except Exception:
        parts.append('No se pudo leer gestion ambiental.')

    try:
        fuentes = obtener_fuentes_empresa(int(empresa_id)) or []
        parts.append(f'Base documental IA: fuentes cargadas={len(fuentes)}')
        if fuentes:
            titulos = [fix_text(str(item.get('titulo') or '')).strip() for item in fuentes[:3]]
            titulos = [t for t in titulos if t]
            if titulos:
                parts.append('Documentos clave recientes: ' + ', '.join(titulos))
    except Exception:
        parts.append('No se pudo leer base documental IA.')

    focus = app.storage.user.get('ai_focus_context')
    if isinstance(focus, dict):
        module = str(focus.get('module') or '').strip()
        payload = focus.get('payload') if isinstance(focus.get('payload'), dict) else {}
        if module or payload:
            try:
                payload_text = json.dumps(payload, ensure_ascii=False)
            except Exception:
                payload_text = str(payload)
            parts.append(f'Foco activo del modulo ({module or "general"}): {payload_text}')

    return '\n'.join(parts)


def ensure_platform_access() -> bool:
    if is_platform_authenticated():
        if _session_is_expired():
            # Evitamos clear() en Windows para no forzar unlink del archivo .nicegui en uso.
            for key in [
                'platform_auth', 'jwt_token', 'auth_source', 'role', 'api_role',
                'logged_empresa_id', 'logged_empresa_nombre', 'management_company_id',
                'current_empresa_id', 'session_user_key', 'permisos', 'last_activity_at',
            ]:
                app.storage.user.pop(key, None)
            app.storage.user['platform_auth'] = False
            ui.notify('Tu sesion expiro por inactividad. Vuelve a iniciar sesion.', type='warning')
            ui.navigate.to('/plataforma')
            return False
        _touch_session_activity()
        return True
    ui.navigate.to('/plataforma')
    return False


def _is_admin_session() -> bool:
    if str(app.storage.user.get('role') or '').strip().lower() != 'admin':
        return False
    api_role = str(app.storage.user.get('api_role') or '').strip().lower()
    if api_role:
        return api_role in {'ideas_admin', 'ideas_superadmin', 'superadmin'}
    return True


def _session_company_id() -> int | None:
    try:
        value = app.storage.user.get('logged_empresa_id')
        return int(value) if value else None
    except Exception:
        return None


def _can_write_company(empresa_id: int | None) -> bool:
    if _is_admin_session():
        return True
    role = str(app.storage.user.get('role') or '').strip().lower()
    if role != 'empresa':
        return False
    session_company = _session_company_id()
    try:
        target_company = int(empresa_id) if empresa_id else None
    except Exception:
        target_company = None
    return bool(session_company and target_company and int(session_company) == int(target_company))


def _deny_write(message: str = 'No tienes permisos para ejecutar esta accion.') -> None:
    ui.notify(message, type='negative')


def guarded_guardar_empresa(payload: dict):
    if not _is_admin_session():
        return False, 'No autorizado: solo IDEAS admin puede crear empresas.'
    return guardar_empresa(payload)


def guarded_actualizar_empresa(empresa_id: int, payload: dict):
    if not _is_admin_session():
        return False, 'No autorizado: solo IDEAS admin puede actualizar empresas.'
    return actualizar_empresa(empresa_id, payload)


def guarded_eliminar_empresa(empresa_id: int):
    if not _is_admin_session():
        _deny_write('No autorizado: solo IDEAS admin puede eliminar empresas.')
        return False
    eliminar_empresa(empresa_id)
    return True


def guarded_crear_usuario(username, password, rol, empresa_id=None, permisos='ALL'):
    if not _is_admin_session():
        return False, 'No autorizado: solo IDEAS admin puede crear usuarios.'
    return crear_usuario(username, password, rol, empresa_id, permisos)


def guarded_actualizar_usuario(usuario_id, rol, empresa_id=None, permisos='ALL', username=None, password=None):
    if not _is_admin_session():
        return False, 'No autorizado: solo IDEAS admin puede actualizar usuarios.'
    return actualizar_usuario(usuario_id, rol, empresa_id, permisos, username=username, password=password)


def guarded_eliminar_usuario(usuario_id: int):
    if not _is_admin_session():
        return False, 'No autorizado: solo IDEAS admin puede eliminar usuarios.'
    return eliminar_usuario(usuario_id)


def guarded_guardar_fuente_empresa(empresa_id, titulo, tipo, contenido):
    if not _can_write_company(int(empresa_id) if empresa_id else None):
        return False, 'No autorizado para cargar fuentes en esta empresa.', None
    return guardar_fuente_empresa(empresa_id, titulo, tipo, contenido)


def guarded_eliminar_fuente(fuente_id):
    if not _is_admin_session():
        return False
    eliminar_fuente(fuente_id)
    return True


def guarded_guardar_diagnostico(empresa_id, score, nivel, conclusion, respuestas_guardar):
    if not _can_write_company(int(empresa_id) if empresa_id else None):
        raise PermissionError('No autorizado para guardar diagnosticos en esta empresa.')
    return guardar_diagnostico(empresa_id, score, nivel, conclusion, respuestas_guardar)


def guarded_actualizar_diagnostico(diagnostico_id, empresa_id, score, nivel, conclusion, respuestas_guardar):
    if not _can_write_company(int(empresa_id) if empresa_id else None):
        raise PermissionError('No autorizado para actualizar diagnosticos en esta empresa.')
    return actualizar_diagnostico(diagnostico_id, empresa_id, score, nivel, conclusion, respuestas_guardar)


def guarded_eliminar_diagnostico(diagnostico_id):
    if _is_admin_session():
        eliminar_diagnostico(diagnostico_id)
        return True
    role = str(app.storage.user.get('role') or '').strip().lower()
    if role != 'empresa':
        return False
    session_company = _session_company_id()
    diag_company = None
    try:
        for diag_id, empresa_id, _empresa, _fecha, _score, _nivel, _conclusion in obtener_historial_diagnosticos():
            if int(diag_id) == int(diagnostico_id):
                diag_company = int(empresa_id)
                break
    except Exception:
        diag_company = None
    if not session_company or not diag_company or int(session_company) != int(diag_company):
        return False
    eliminar_diagnostico(diagnostico_id)
    return True


def logout_platform() -> None:
    app.storage.user['platform_auth'] = False
    ui.navigate.to('/')


def shell(page_title: str, back_route: str = None, module_key: str = 'general'):
    inject_global_styles()
    if not ensure_platform_access():
        return ui.column().classes('ideas-shell')
    if not _can_access_page_by_role_and_scope(page_title):
        ui.notify('No tienes permisos para acceder a este modulo.', type='negative')
        ui.navigate.to('/sistema-gestion')
        return ui.column().classes('ideas-shell')
    logo = get_logo_url()
    user_role = str(app.storage.user.get('role') or '')
    user_empresa_id = app.storage.user.get('logged_empresa_id')
    empresa_sesion = app.storage.user.get('logged_empresa_nombre')
    if not empresa_sesion and user_role != 'admin' and user_empresa_id:
        try:
            empresa_detalle = obtener_empresa_detalle(int(user_empresa_id))
            empresa_sesion = fix_text(empresa_detalle.get('razon_social', '')) if empresa_detalle else ''
            if empresa_sesion:
                app.storage.user['logged_empresa_nombre'] = empresa_sesion
        except Exception:
            empresa_sesion = ''

    if user_role == 'admin':
        nav_items = [
            ('Dashboard', '/dashboard', 'home'),
            ('Empresas', '/empresas', 'business'),
            ('Workspace Ejecutivo', '/sistema-gestion', 'account_tree'),
            ('Diagnóstico', '/diagnostico', 'assignment'),
            ('Resultados', '/resultados', 'analytics'),
            ('Historial', '/historial', 'history'),
            ('Usuarios', '/sistema-gestion/usuarios', 'manage_accounts'),
            ('Smart IdeAs Admin', '/sistema-gestion/smart-ideas-admin', 'tune'),
        ]
        drawer_title = 'Panel IDEAS'
        drawer_note = 'Vista interna de consultoría'
        drawer_support = 'Gestiona clientes, diagnósticos, usuarios y módulos desde una consola ejecutiva.'
    else:
        nav_items = [
            ('Mi Workspace', '/sistema-gestion', 'dashboard_customize'),
        ]
        drawer_title = empresa_sesion or 'Workspace cliente'
        drawer_note = 'Sistema de gestión'
        drawer_support = 'Acceso simple a tus módulos habilitados, sin información de otros clientes.'

    if user_role == 'admin':
        with ui.left_drawer(value=True, bordered=False).classes('p-4'):
            with ui.column().classes('ideas-brand-card w-full'):
                if logo:
                    ui.image(logo).classes('w-28 mb-3')
                ui.label('IDEAS Consulting').classes('text-slate-900 text-lg font-bold')
                ui.label(drawer_note).classes('text-xs uppercase tracking-widest text-slate-500')
                ui.separator().classes('my-3')
                ui.label('Navegación').classes('text-[11px] uppercase tracking-[0.22em] text-slate-400')
            for label, route, icon in nav_items:
                ui.button(label, icon=icon, on_click=lambda r=route: ui.navigate.to(r)).props('flat align=left').classes('ideas-nav-btn')
            with ui.column().classes('ideas-brand-card w-full mt-4'):
                ui.label('Board-ready').classes('text-[11px] uppercase tracking-[0.18em] text-slate-400')
                ui.label(drawer_title).classes('text-slate-900 font-semibold mt-1')
                ui.label(drawer_support).classes('text-sm text-slate-500 mt-1')
            ui.button('Web institucional', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat align=left').classes('ideas-nav-btn mt-2')
            if is_platform_authenticated():
                ui.button('Salir', icon='logout', on_click=logout_platform).props('flat align=left color=negative').classes('ideas-nav-btn')

    def resolve_company_name_for_assistant() -> str:
        if empresa_sesion:
            return fix_text(str(empresa_sesion))
        current_empresa_id = app.storage.user.get('current_empresa_id')
        try:
            current_empresa_id = int(current_empresa_id) if current_empresa_id else None
        except Exception:
            current_empresa_id = None
        if current_empresa_id:
            try:
                detalle = obtener_empresa_detalle(int(current_empresa_id))
                nombre = fix_text(str((detalle or {}).get('razon_social') or '')).strip()
                if nombre:
                    return nombre
            except Exception:
                pass
        return 'tu empresa'

    company_name_for_welcome = resolve_company_name_for_assistant()
    user_name_for_welcome = fix_text(str(app.storage.user.get('session_user_name') or '')).strip() or 'equipo'
    ai_enabled_session = is_ai_enabled_for_current_context()
    assistant_name = assistant_display_name_for_page(page_title)
    assistant_icon, assistant_icon_color = assistant_icon_for_page(page_title)
    welcome_template = _read_ideas_welcome_template()
    try:
        welcome_text = welcome_template.format(
            empresa=company_name_for_welcome,
            usuario=user_name_for_welcome,
            agente=assistant_name,
        )
    except Exception:
        welcome_text = (
            f'Hola {user_name_for_welcome}, soy {assistant_name}. '
            f'Estoy para ayudarte en {company_name_for_welcome} con foco practico y concreto.'
        )

    ai_drawer_open = False
    with ui.right_drawer(value=ai_drawer_open).props('persistent').classes('ideas-ai-drawer p-4 w-[460px] max-w-[92vw]') as ai_drawer:
        def _force_open_drawer() -> None:
            ai_drawer.value = True
            app.storage.user['ai_drawer_open'] = True
            ai_drawer.update()
        
        def _remember_drawer_state(event) -> None:
            app.storage.user['ai_drawer_open'] = bool(getattr(event, 'value', False))

        ai_drawer.on_value_change(_remember_drawer_state)
        company_ai_id = current_company_id_for_ai()
        user_ai_key = current_user_key_for_ai()
        module_ai_key = str(module_key or '').strip() or assistant_module_key_for_page(page_title)
        chat_storage_key = f'ai_chat_messages::{company_ai_id or "none"}::{user_ai_key}::{module_ai_key}'
        persisted_messages = app.storage.user.get(chat_storage_key)
        if not isinstance(persisted_messages, list):
            persisted_messages = []
        chat_history: list[dict[str, str]] = [
            {'role': str(item.get('role') or ''), 'content': str(item.get('text') or '')}
            for item in persisted_messages
            if isinstance(item, dict) and str(item.get('role') or '') in {'user', 'assistant'} and str(item.get('text') or '').strip()
        ]
        def _build_user_preference_profile() -> str:
            if not company_ai_id:
                return ''
            try:
                rows = obtener_memoria_asistente_empresa(
                    int(company_ai_id),
                    limite=40,
                    user_key=user_ai_key,
                )
            except Exception:
                return ''
            if not rows:
                return ''
            user_lines = [
                fix_text(str(item.get('content') or '')).strip().lower()
                for item in rows
                if str(item.get('role') or '').strip() == 'user'
            ]
            if not user_lines:
                return ''
            brief_pref = sum(
                1 for line in user_lines
                if any(token in line for token in ('breve', 'corto', 'resumen', 'puntual', 'rapido'))
            )
            detail_pref = sum(
                1 for line in user_lines
                if any(token in line for token in ('detalle', 'profundo', 'paso a paso', 'completo', 'extenso'))
            )
            report_pref = sum(
                1 for line in user_lines
                if any(token in line for token in ('reporte', 'informe', 'pdf', 'entregable', 'auditoria'))
            )
            style = 'breve y directo' if brief_pref >= detail_pref else 'detallado y paso a paso'
            report_hint = 'frecuente' if report_pref >= 2 else 'ocasional'
            return (
                'Perfil del usuario basado en interacciones previas: '
                f'estilo preferido={style}; interes en reportes={report_hint}. '
                'Adapta tono y nivel de detalle sin repetir esta nota.'
            )

        with ui.column().classes('w-full h-full gap-2'):
            with ui.row().classes('items-center gap-2'):
                with ui.row().classes('ideas-ai-avatar'):
                    ui.icon('sentiment_satisfied').classes('text-[0.95rem]')
                ui.icon(assistant_icon).classes(f'text-[1.35rem] {assistant_icon_color}')
                ui.label(assistant_name).classes('text-lg font-bold text-slate-900')
            focus_payload = ((app.storage.user.get('ai_focus_context') or {}).get('payload') or {})
            normas_consideradas = focus_payload.get('normas_visibles') or focus_payload.get('certificaciones_activas') or []
            normas_text = ', '.join(str(n) for n in normas_consideradas[:6]) if normas_consideradas else 'Normas segun certificaciones activas'
            ui.label(f'Empresa activa: {company_name_for_welcome}').classes('text-xs text-slate-600')
            ui.label(f'Normas consideradas: {normas_text}').classes('text-xs text-slate-500')
            ui.label('Las respuestas de IA deben ser revisadas por un profesional antes de su implementacion.').classes('text-[11px] text-amber-700')
            quick_mode = {'value': 'general'}
            quick_prompt_map = [
                ('Explicar requisito', 'explicar_requisito', 'Explica este requisito y como implementarlo en la empresa activa.'),
                ('Evidencias esperadas', 'evidencias_esperadas', 'Indica evidencias objetivas esperadas para este requisito.'),
                ('Checklist de auditoria', 'checklist_auditoria', 'Genera checklist de auditoria para este requisito.'),
                ('Plan de accion', 'plan_accion', 'Convertir en plan de accion aplicable a esta empresa.'),
                ('Riesgos asociados', 'riesgos_asociados', 'Identifica riesgos de incumplimiento y controles recomendados.'),
                ('Redactar procedimiento', 'redactar_procedimiento', 'Redacta un procedimiento base listo para adaptar.'),
                ('Preguntas de auditoria', 'preguntas_auditoria', 'Genera preguntas de auditoria interna y externa.'),
                ('Brecha tipica en PyMEs', 'brecha_pyme', 'Indica brechas tipicas de PyMEs para este requisito.'),
            ]
            with ui.row().classes('w-full gap-1'):
                for label, mode, text in quick_prompt_map:
                    ui.button(
                        label,
                        on_click=lambda _=None, m=mode, t=text: (quick_mode.__setitem__('value', m), _set_quick_prompt(t)),
                    ).props('flat dense').classes('text-[11px] border border-slate-300 rounded px-2 py-1')
            chat_panel = ui.scroll_area().classes('ideas-ai-chat-panel w-full flex-1 min-h-[56vh] p-2')
            with chat_panel:
                chat_messages = ui.column().classes('w-full gap-2')
                with chat_messages:
                    if persisted_messages:
                        for item in persisted_messages[-40:]:
                            if not isinstance(item, dict):
                                continue
                            ui.chat_message(
                                text=_format_chat_text_for_display(str(item.get('text') or '')),
                                name=str(item.get('name') or assistant_name),
                                sent=bool(item.get('sent', False)),
                                text_html=True,
                            )
                    else:
                        ui.chat_message(
                            text=_format_chat_text_for_display(welcome_text),
                            name=assistant_name,
                            sent=False,
                            text_html=True,
                        )
            loading_row = ui.row().classes('items-center gap-2 text-slate-500')
            loading_row.visible = False
            with loading_row:
                ui.spinner(size='sm')
                loading_label = ui.label('Smart IdeAs esta analizando tu consulta...')
            with ui.row().classes('w-full items-end gap-2'):
                ai_input = ui.input('Escribe tu consulta').props('outlined dense').classes('ideas-ai-input w-full')
                ai_send = ui.button(icon='send').props('flat round dense').classes('ideas-ai-send')
            sending_lock = {'active': False}

            def _set_quick_prompt(text: str) -> None:
                ai_input.value = text
                ai_input.update()

            def append_message(text: str, name: str, sent: bool) -> None:
                with chat_messages:
                    ui.chat_message(
                        text=_format_chat_text_for_display(text),
                        name=name,
                        sent=sent,
                        text_html=True,
                    )
                role = 'user' if sent else 'assistant'
                persisted_messages.append(
                    {'role': role, 'name': name, 'text': str(text or ''), 'sent': bool(sent)}
                )
                if len(persisted_messages) > 80:
                    del persisted_messages[:-80]
                app.storage.user[chat_storage_key] = persisted_messages

            def append_route_buttons(hints: list[tuple[str, str]]) -> None:
                if not hints:
                    return
                with chat_messages:
                    with ui.row().classes('w-full justify-start gap-2 mt-1'):
                        for label, route in hints:
                            ui.button(
                                label,
                                icon='open_in_new',
                                on_click=lambda r=route: ui.navigate.to(r),
                            ).props('flat dense').classes('text-[12px] font-semibold text-blue-700 border border-slate-300 rounded-full px-2')

            def generate_report_from_chat() -> None:
                if not persisted_messages:
                    ui.notify('No hay conversacion para reportar.', type='warning')
                    return
                user_msgs = [str(item.get('text') or '').strip() for item in persisted_messages if str(item.get('role') or '') == 'user']
                ai_msgs = [str(item.get('text') or '').strip() for item in persisted_messages if str(item.get('role') or '') == 'assistant']
                report_lines = [
                    '# Reporte Smart Assist',
                    f'- Fecha: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
                    f'- Empresa: {company_name_for_welcome}',
                    f'- Usuario: {user_name_for_welcome}',
                    f'- Modulo: {module_ai_key}',
                    '',
                    '## Resumen Ejecutivo',
                    (ai_msgs[-1] if ai_msgs else 'Sin respuesta del asistente.'),
                    '',
                    '## Conversacion Reciente',
                ]
                for idx, text in enumerate(user_msgs[-5:], start=1):
                    report_lines.append(f'{idx}. Consulta: {text}')
                report_body = '\n'.join(report_lines).strip() + '\n'
                with tempfile.NamedTemporaryFile('w', delete=False, suffix='.md', encoding='utf-8') as tmp:
                    tmp.write(report_body)
                    report_path = tmp.name
                ui.download(report_path)
                ui.notify('Reporte generado.', type='positive')

            def copy_last_answer() -> None:
                last = ''
                for item in reversed(persisted_messages):
                    if str(item.get('role') or '') == 'assistant':
                        last = str(item.get('text') or '').strip()
                        break
                if not last:
                    ui.notify('No hay respuesta para copiar.', type='warning')
                    return
                safe = json.dumps(last)
                ui.run_javascript(f'navigator.clipboard.writeText({safe});')
                ui.notify('Respuesta copiada.', type='positive')

            def transform_last_answer(mode: str, prompt: str) -> None:
                last = ''
                for item in reversed(persisted_messages):
                    if str(item.get('role') or '') == 'assistant':
                        last = str(item.get('text') or '').strip()
                        break
                if not last:
                    ui.notify('No hay respuesta previa para transformar.', type='warning')
                    return
                quick_mode['value'] = mode
                ai_input.value = f'{prompt}\n\nTexto base:\n{last}'
                ai_input.update()

            async def process_assistant_message() -> None:
                if sending_lock['active']:
                    return
                user_text = str(ai_input.value or '').strip()
                if not user_text:
                    return
                sending_lock['active'] = True
                _force_open_drawer()
                ai_send.disable()
                ai_input.disable()

                respuesta = ''
                working_context = ''
                try:
                    if not ai_enabled_session:
                        append_message(
                            'La IA esta deshabilitada para esta empresa. Solicita a IDEAS Superadmin activar "Copiloto IA".',
                            assistant_name,
                            False,
                        )
                        return

                    ai_input.value = ''
                    ai_input.update()
                    append_message(user_text, 'Tu', True)
                    chat_history.append({'role': 'user', 'content': user_text})
                    loading_row.visible = True
                    loading_label.text = 'Smart IdeAs esta analizando tu consulta...'
                    loading_row.update()

                    working_context = build_ai_working_context(page_title)
                    preference_profile = _build_user_preference_profile()
                    if preference_profile:
                        working_context = f'{working_context}\n{preference_profile}'
                    client_rules = _rules_for_company(company_ai_id)
                    memory_context = []
                    company_sources = []

                    if company_ai_id:
                        try:
                            memory_rows = obtener_memoria_asistente_empresa(
                                int(company_ai_id),
                                limite=20,
                                user_key=user_ai_key,
                            )
                            memory_context = [
                                {'role': str(item.get('role') or ''), 'content': str(item.get('content') or '')}
                                for item in memory_rows
                                if str(item.get('role') or '') in {'user', 'assistant'} and str(item.get('content') or '').strip()
                            ]
                        except Exception:
                            memory_context = []
                        try:
                            source_rows = obtener_fuentes_empresa(int(company_ai_id)) or []
                            company_sources = [
                                {
                                    'titulo': str(item.get('titulo') or ''),
                                    'tipo': str(item.get('tipo') or ''),
                                    'contenido': str(item.get('contenido') or ''),
                                }
                                for item in source_rows[:10]
                            ]
                            if module_ai_key == 'documents' and company_sources:
                                source_hint = str((company_sources[0] or {}).get('titulo') or '').strip()
                                if source_hint:
                                    loading_label.text = f'Buscando en fuente: {source_hint}'
                                    loading_label.update()
                        except Exception:
                            company_sources = []

                    company_industry = ''
                    if company_ai_id:
                        try:
                            empresa_detalle_ai = obtener_empresa_detalle(int(company_ai_id)) or {}
                            company_industry = fix_text(str(empresa_detalle_ai.get('rubro') or '')).strip()
                        except Exception:
                            company_industry = ''

                    framed_user_text = f"[modo_respuesta:{quick_mode['value']}] {user_text}"
                    respuesta = await consultar_asistente_iso(
                        framed_user_text,
                        chat_history,
                        module_context=page_title,
                        module_key=module_ai_key,
                        working_context=working_context,
                        client_rules=client_rules,
                        company_industry=company_industry,
                        memory_context=memory_context,
                        company_sources=company_sources,
                        task_type=detect_ai_task_type(user_text, page_title),
                    )
                except Exception as exc:
                    respuesta = (
                        'Explicacion simple: Ocurrio un error al consultar Smart Assist.\n'
                        'Requisito relacionado: No disponible por el momento.\n'
                        f'Detalle tecnico: {exc}'
                    )
                finally:
                    loading_row.visible = False
                    loading_row.update()
                    ai_send.enable()
                    ai_input.enable()
                    _force_open_drawer()
                    sending_lock['active'] = False

                if not respuesta.strip():
                    respuesta = 'No pude generar respuesta en este intento. Reintenta en unos segundos.'

                hints = assistant_route_hints_for_query(user_text)
                if hints and is_navigation_style_query(user_text):
                    respuesta = 'Claro, puedo ayudarte con eso. Te dejo el acceso directo:'
                append_message(respuesta, assistant_name, False)
                if hints:
                    append_route_buttons(hints)
                chat_history.append({'role': 'assistant', 'content': respuesta})
                if company_ai_id:
                    try:
                        guardar_evento_memoria_asistente(
                            int(company_ai_id),
                            'user',
                            user_text,
                            module_context=page_title,
                            context_snapshot=working_context,
                            user_key=user_ai_key,
                        )
                        guardar_evento_memoria_asistente(
                            int(company_ai_id),
                            'assistant',
                            respuesta,
                            module_context=page_title,
                            context_snapshot=working_context,
                            user_key=user_ai_key,
                        )
                    except Exception:
                        pass

            def trigger_send(_event=None) -> None:
                asyncio.create_task(process_assistant_message())

            def close_drawer() -> None:
                ai_drawer.value = False
                app.storage.user['ai_drawer_open'] = False
                ai_drawer.update()

            ai_input.on('keydown.enter', trigger_send)
            ai_send.on_click(trigger_send)
            with ui.row().classes('w-full items-center justify-between gap-2'):
                ui.button('Copiar respuesta', icon='content_copy', on_click=copy_last_answer).props('flat dense').classes('text-slate-600')
                ui.button('Convertir en plan de accion', icon='table_chart', on_click=lambda: transform_last_answer('plan_accion', 'Convertir en plan de accion')).props('flat dense').classes('text-slate-600')
                ui.button('Generar checklist', icon='fact_check', on_click=lambda: transform_last_answer('checklist_auditoria', 'Generar checklist de auditoria')).props('flat dense').classes('text-slate-600')
                ui.button('Reporte', icon='description', on_click=generate_report_from_chat).props('flat dense').classes('text-slate-600')
                ui.button('Cerrar', icon='close', on_click=close_drawer).props('flat dense').classes('text-slate-500')
    with ui.header().classes('ideas-topbar'):
        with ui.row().classes('w-full items-center justify-between px-4'):
            with ui.row().classes('items-center gap-3'):
                if back_route:
                    ui.button(
                        icon='arrow_back',
                        on_click=lambda route=back_route: ui.navigate.to(route),
                    ).props('flat round dense').classes('text-slate-600')
                if logo:
                    ui.html(
                        f'''
                        <div class="ideas-topbar-brand">
                            <img src="{logo}" alt="IDEAS logo" />
                            <div>
                                <div class="brand-title">IDEAS Consulting</div>
                                <div class="brand-subtitle">{page_title}</div>
                            </div>
                        </div>
                        '''
                    )
                else:
                    with ui.column().classes('gap-0'):
                        ui.label('IDEAS Consulting V2').classes('text-slate-900 font-bold')
                        ui.label(page_title).classes('text-sm text-slate-500')
            with ui.row().classes('items-center gap-2'):
                smart_button = ui.button(assistant_name, icon='auto_awesome', on_click=_force_open_drawer).props('flat dense').classes('text-blue-700 font-bold')
                if not ai_enabled_session:
                    smart_button.disable()
                    smart_button.tooltip('IA deshabilitada para la empresa seleccionada')
                ui.button('Web institucional', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat dense')
                if is_platform_authenticated():
                    ui.button('Salir', icon='logout', on_click=logout_platform).props('flat dense color=negative')
    return ui.column().classes('ideas-shell')


def render_metrics(container, metrics: list[tuple[str, str, str]]) -> None:
    with container:
        with ui.row().classes('w-full gap-4'):
            for label, value, detail in metrics:
                with ui.column().classes('ideas-metric col flex-1'):
                    ui.html(f'<div class="label">{label}</div><div class="value">{value}</div><div class="detail">{detail}</div>')


def quick_card(label: str, value: str, detail: str) -> str:
    return f'<div class="ideas-quick-card"><div class="label">{label}</div><div class="value">{value}</div><div class="detail">{detail}</div></div>'


def public_shell(page_title: str):
    inject_global_styles()
    logo = get_logo_url()
    if page_title == 'Acceso':
        actions_html = '''
            <a class="ideas-public-return-link" href="/">
                <span class="material-icons" aria-hidden="true">public</span>
                <span>Volver al sitio web</span>
            </a>
        '''
    else:
        home_link_html = (
            '<a class="ideas-public-home-link" href="/">Inicio</a>'
            if page_title != 'Inicio'
            else ''
        )
        whatsapp_html = '''
            <a class="ideas-whatsapp-link topbar" href="https://wa.me/541170068904" target="_blank" rel="noopener noreferrer">
                <span class="ideas-whatsapp-icon">
                    <svg viewBox="0 0 32 32" aria-hidden="true">
                        <circle cx="16" cy="16" r="16" fill="#25D366"></circle>
                        <path fill="#ffffff" d="M23.2 8.7A9.2 9.2 0 0 0 7.6 18.1L6 26l8.1-1.6a9.2 9.2 0 0 0 4.4 1.1h0A9.2 9.2 0 0 0 23.2 8.7zm-4.7 14.6h0a7.7 7.7 0 0 1-3.9-1.1l-.3-.2-4.8.9.9-4.7-.2-.3a7.7 7.7 0 1 1 8.3 5.4zm4.2-5.8c-.2-.1-1.4-.7-1.6-.8-.2-.1-.4-.1-.6.1s-.7.8-.8 1c-.1.1-.3.2-.5.1a6.3 6.3 0 0 1-1.9-1.2 7.1 7.1 0 0 1-1.3-1.7c-.1-.2 0-.4.1-.5l.4-.4.2-.3c.1-.1.1-.3 0-.4l-.6-1.5c-.2-.4-.4-.4-.6-.4h-.5c-.2 0-.4.1-.6.3s-.8.8-.8 2 .8 2.4.9 2.5c.1.2 1.6 2.5 3.9 3.5.5.2 1 .4 1.3.6.6.2 1.1.2 1.5.1.5-.1 1.4-.6 1.6-1.1.2-.5.2-1 .2-1.1s-.2-.2-.4-.3z"></path>
                    </svg>
                </span>
                <span>WhatsApp</span>
            </a>
        '''
        actions_html = f'''
            {home_link_html}
            <a class="ideas-public-login-link" href="/plataforma">
                <span class="material-icons" aria-hidden="true">login</span>
                <span>Ingresa</span>
            </a>
            {whatsapp_html}
        '''
    with ui.header().classes('ideas-public-topbar'):
        ui.html(
            f'''
            <div class="ideas-public-nav">
                <div class="ideas-public-brand">
                    {f'<img src="{logo}" alt="IDEAS logo" />' if logo else ''}
                    <div>
                        <div class="name">IDEAS Consulting</div>
                        <div class="tag">{page_title}</div>
                    </div>
                </div>
                <div class="ideas-public-actions">
                    {actions_html}
                </div>
            </div>
            '''
        )
    return ui.column().classes('ideas-public-shell')


def wrap_axis_label(text: str, words_per_line: int = 2) -> str:
    words = fix_text(text).split()
    if len(words) <= words_per_line:
        return fix_text(text)
    lines = [" ".join(words[i:i + words_per_line]) for i in range(0, len(words), words_per_line)]
    return "<br>".join(lines)


def short_axis_label(text: str, max_len: int = 14) -> str:
    clean = fix_text(text)
    if len(clean) <= max_len:
        return clean
    words = clean.split()
    if len(words) >= 2:
        candidate = f"{words[0]} {words[1]}"
        if len(candidate) <= max_len:
            return candidate
    return clean[: max_len - 1].rstrip() + "…"

def certifications_summary(company: dict | None) -> str:
    if not company:
        return 'Sin datos'
    labels = []
    for key, label in [('cert_iso_9001', 'ISO 9001'), ('cert_iso_14001', 'ISO 14001'), ('cert_iso_45001', 'ISO 45001'), ('cert_iatf', 'IATF')]:
        if valor_afirmativo(company.get(key)):
            labels.append(label)
    return ', '.join(labels) if labels else 'Sin certificaciones registradas'


def company_options() -> dict[int, str]:
    session_role = str(app.storage.user.get('role') or '')
    if session_role == 'empresa':
        empresa_id = app.storage.user.get('logged_empresa_id')
        empresa_nombre = str(app.storage.user.get('logged_empresa_nombre') or '').strip()
        try:
            empresa_id = int(empresa_id) if empresa_id else None
        except Exception:
            empresa_id = None
        if not empresa_id or not empresa_nombre:
            return {}
        return {int(empresa_id): fix_text(empresa_nombre)}
    return {int(company_id): fix_text(name) for company_id, name in obtener_empresas()}


def diagnosis_rows() -> list[dict]:
    rows = []
    for diag_id, empresa_id, empresa, fecha, score, nivel, conclusion in obtener_historial_diagnosticos():
        rows.append({'id': int(diag_id), 'empresa_id': int(empresa_id), 'empresa': fix_text(empresa), 'fecha': str(fecha), 'score': float(score), 'nivel': fix_text(nivel), 'conclusion': fix_text(conclusion)})
    return rows


def diagnosis_options(empresa_id: int | None) -> dict[int, str]:
    if not empresa_id:
        return {}
    options = {}
    for idx, (diag_id, fecha, score, nivel, _conclusion) in enumerate(obtener_diagnosticos_empresa(empresa_id), start=1):
        options[int(diag_id)] = f'Diagnóstico {idx} · {fecha} · {float(score):.2f} · {fix_text(nivel)}'
    return options


def diagnosis_record(diagnostico_id: int | None) -> dict | None:
    if not diagnostico_id:
        return None
    for row in diagnosis_rows():
        if row['id'] == int(diagnostico_id):
            return row
    return None


def diagnosis_response_dicts(diagnostico_id: int | None) -> list[dict]:
    if not diagnostico_id:
        return []
    responses = []
    for eje, pregunta, respuesta, evidencia, observacion in obtener_respuestas_diagnostico(int(diagnostico_id)):
        responses.append({'eje': fix_text(eje), 'pregunta': fix_text(pregunta), 'respuesta': int(respuesta), 'evidencia': fix_text(evidencia), 'observacion': fix_text(observacion)})
    return responses


def grouped_questions(df_base: pd.DataFrame) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for eje, group in df_base.groupby('EJE', dropna=False):
        grouped[fix_text(eje)] = [fix_text(question) for question in group['PREGUNTA'].tolist()]
    return grouped


def current_selection() -> tuple[int | None, int | None]:
    session_role = str(app.storage.user.get('role') or '')
    forced_empresa_id = app.storage.user.get('logged_empresa_id') if session_role != 'admin' else None
    empresa_id = forced_empresa_id or app.storage.user.get('current_empresa_id')
    diagnostico_id = app.storage.user.get('current_diag_id')
    try:
        empresa_id = int(empresa_id) if empresa_id else None
    except Exception:
        empresa_id = None
    try:
        diagnostico_id = int(diagnostico_id) if diagnostico_id else None
    except Exception:
        diagnostico_id = None
    return empresa_id, diagnostico_id


def set_selection(empresa_id: int | None, diagnostico_id: int | None = None) -> None:
    session_role = str(app.storage.user.get('role') or '')
    if session_role != 'admin':
        empresa_id = app.storage.user.get('logged_empresa_id')
    try:
        empresa_id = int(empresa_id) if empresa_id else None
    except Exception:
        empresa_id = None

    diag_id = None
    try:
        diag_id = int(diagnostico_id) if diagnostico_id else None
    except Exception:
        diag_id = None

    if diag_id and empresa_id:
        diag = diagnosis_record(diag_id)
        if not diag or int(diag.get('empresa_id') or 0) != int(empresa_id):
            diag_id = None
    else:
        diag_id = None

    app.storage.user['current_empresa_id'] = empresa_id
    app.storage.user['current_diag_id'] = diag_id


def start_edit(diagnostico_id: int, duplicate: bool = False) -> None:
    diag = diagnosis_record(diagnostico_id)
    if not diag:
        return
    app.storage.user['edit_diag_id'] = None if duplicate else int(diagnostico_id)
    app.storage.user['duplicate_diag_id'] = int(diagnostico_id) if duplicate else None
    set_selection(diag['empresa_id'], int(diagnostico_id))


def diagnosis_badge_style(nivel: str) -> str:
    if nivel == 'Alto':
        return 'background:#dcfce7;color:#166534;'
    if nivel == 'Medio':
        return 'background:#fef3c7;color:#92400e;'
    return 'background:#fee2e2;color:#991b1b;'


def result_summary(score: float) -> str:
    if score < 2:
        return 'Se recomienda una intervención prioritaria para estabilizar prácticas, formalizar controles y recuperar consistencia operativa.'
    if score < 3:
        return 'La organización cuenta con bases aprovechables, pero todavía necesita consolidar estándares y seguimiento para mejorar su desempeño.'
    return 'La organización presenta una madurez sólida y está en condiciones de profundizar excelencia, escalabilidad y mejora continua.'


def get_free_port(preferred: int = 8502, attempts: int = 20) -> int:
    for port in range(preferred, preferred + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                sock.bind(('0.0.0.0', port))
                return port
            except OSError:
                continue
    return preferred


def first_evidence_only(value: str) -> str:
    text = fix_text(value).strip()
    if not text:
        return ''
    for separator in [',', ';', '|', '\n']:
        if separator in text:
            return text.split(separator)[0].strip()
    return text


def split_evidence_values(value: str) -> list[str]:
    text = fix_text(value)
    if not text.strip():
        return ['']
    normalized = text.replace(';', ',').replace('|', ',').replace('\n', ',')
    parts = [part.strip() for part in normalized.split(',') if part.strip()]
    return parts or ['']


def _format_chat_text_for_display(text: str) -> str:
    raw = str(text or '')
    raw = re.sub(r'(?i)<br\s*/?>', '\n', raw)
    raw = re.sub(r'(?i)&lt;br\s*/?&gt;', '\n', raw)
    escaped = html.escape(raw)
    with_bold = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", escaped, flags=re.DOTALL)
    return with_bold.replace('\n', '<br>')


def _raise_ai_disabled() -> None:
    raise RuntimeError(
        'La IA esta deshabilitada para esta empresa. '
        'Solicita a IDEAS Superadmin activar "Copiloto IA" en la ficha de la empresa.'
    )


def explicar_requisito_iso_guarded(norma, requisito, resumen, observacion_consultiva) -> str:
    if not is_ai_enabled_for_current_context():
        _raise_ai_disabled()
    return explicar_requisito_iso(norma, requisito, resumen, observacion_consultiva)


def sugerir_causas_ishikawa_guarded(problema, factores_retenidos) -> str:
    if not is_ai_enabled_for_current_context():
        _raise_ai_disabled()
    return sugerir_causas_ishikawa(problema, factores_retenidos)


def sugerir_matriz_legal_ia_guarded(rubro: str, ubicacion: str, aspectos_lista: list) -> list[dict]:
    if not is_ai_enabled_for_current_context():
        _raise_ai_disabled()
    return sugerir_matriz_legal_ia(rubro, ubicacion, aspectos_lista)


def _ideas_standard_default() -> str:
    return (
        "# Estandar Smart IdeAs (Superadmin)\n\n"
        "## Rol\n"
        "Actuar como Consultor Inteligente IDEAS en sistemas de gestion industrial B2B.\n\n"
        "## Tono\n"
        "- Claro, profesional, directo y aplicable a planta.\n"
        "- Evitar ambiguedad y frases vacias.\n"
        "- Priorizar acciones concretas.\n\n"
        "## Formato de respuesta obligatorio\n"
        "Explicacion simple: ...\n"
        "Requisito relacionado: ...\n"
        "Ejemplo industrial: ...\n"
        "Evidencia esperada: ...\n"
        "Recomendaciones practicas: ...\n\n"
        "## Reglas de calidad\n"
        "- Si no hay coincidencia exacta de norma/requisito, usar el mas cercano y explicarlo.\n"
        "- Incluir siempre una accion inmediata en recomendaciones.\n"
        "- No inventar leyes, clausulas ni numeros de norma.\n"
        "- Si faltan datos, pedir maximo 2 datos concretos.\n\n"
        "## Lenguaje IDEAS\n"
        "- Usar vocabulario de consultoria operativa: proceso, evidencia, control, accion, responsable, plazo.\n"
        "- Evitar tecnicismos innecesarios cuando el usuario no los pide.\n"
    )


def _ideas_welcome_template_default() -> str:
    return (
        "Hola {usuario}, soy {agente}. "
        "Estoy para ayudarte en {empresa} con foco practico y concreto."
    )


def _read_ideas_welcome_template() -> str:
    try:
        if IDEAS_WELCOME_TEMPLATE_PATH.exists():
            content = IDEAS_WELCOME_TEMPLATE_PATH.read_text(encoding='utf-8').strip()
            if content:
                return content
    except Exception:
        pass
    return _ideas_welcome_template_default()


def _write_ideas_welcome_template(content: str) -> None:
    IDEAS_WELCOME_TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDEAS_WELCOME_TEMPLATE_PATH.write_text(content, encoding='utf-8')


def _read_ideas_assistant_settings() -> dict:
    default = {'response_mode': 'adaptive'}
    if not IDEAS_ASSISTANT_SETTINGS_PATH.exists():
        return default
    try:
        data = json.loads(IDEAS_ASSISTANT_SETTINGS_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict):
            mode = str(data.get('response_mode') or '').strip().lower()
            if mode in {'adaptive', 'always_structured'}:
                return {'response_mode': mode}
    except Exception:
        pass
    return default


def _write_ideas_assistant_settings(settings: dict) -> None:
    IDEAS_ASSISTANT_SETTINGS_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDEAS_ASSISTANT_SETTINGS_PATH.write_text(json.dumps(settings, ensure_ascii=True, indent=2), encoding='utf-8')


def _read_ideas_client_rules() -> dict:
    default = {'by_company': {}}
    if not IDEAS_ASSISTANT_CLIENT_RULES_PATH.exists():
        return default
    try:
        data = json.loads(IDEAS_ASSISTANT_CLIENT_RULES_PATH.read_text(encoding='utf-8'))
        if isinstance(data, dict) and isinstance(data.get('by_company'), dict):
            return {'by_company': data.get('by_company') or {}}
    except Exception:
        pass
    return default


def _write_ideas_client_rules(settings: dict) -> None:
    payload = {'by_company': (settings or {}).get('by_company') or {}}
    IDEAS_ASSISTANT_CLIENT_RULES_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDEAS_ASSISTANT_CLIENT_RULES_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')


def _rules_for_company(company_id: int | None) -> dict:
    if not company_id:
        return {}
    rules = _read_ideas_client_rules().get('by_company') or {}
    item = rules.get(str(int(company_id)))
    return item if isinstance(item, dict) else {}


def _read_ideas_standard() -> str:
    try:
        if IDEAS_STANDARD_PATH.exists():
            return IDEAS_STANDARD_PATH.read_text(encoding='utf-8')
    except Exception:
        pass
    return _ideas_standard_default()


def _write_ideas_standard(content: str) -> None:
    IDEAS_STANDARD_PATH.parent.mkdir(parents=True, exist_ok=True)
    IDEAS_STANDARD_PATH.write_text(content, encoding='utf-8')


def _read_ideas_changelog() -> list[dict]:
    if not IDEAS_STANDARD_CHANGELOG_PATH.exists():
        return []
    rows: list[dict] = []
    try:
        for line in IDEAS_STANDARD_CHANGELOG_PATH.read_text(encoding='utf-8').splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
                if isinstance(item, dict):
                    rows.append(item)
            except Exception:
                continue
    except Exception:
        return []
    return rows


def _append_ideas_changelog(version: str, note: str, size: int) -> None:
    IDEAS_STANDARD_CHANGELOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'version': version.strip(),
        'note': note.strip(),
        'size_chars': int(size),
    }
    with IDEAS_STANDARD_CHANGELOG_PATH.open('a', encoding='utf-8', newline='') as fh:
        fh.write(json.dumps(payload, ensure_ascii=True) + '\n')


def _next_ideas_version() -> str:
    rows = _read_ideas_changelog()
    if not rows:
        return 'v1.0'
    last = str(rows[-1].get('version') or '').strip().lower()
    if last.startswith('v'):
        last = last[1:]
    try:
        parts = last.split('.')
        major = int(parts[0]) if parts and parts[0] else 1
        minor = int(parts[1]) if len(parts) > 1 else 0
        return f'v{major}.{minor + 1}'
    except Exception:
        return 'v1.0'


@ui.page('/sistema-gestion/smart-ideas-admin')
def smart_ideas_admin_page():
    if not ensure_platform_access():
        return
    role = str(app.storage.user.get('role') or '')
    if role != 'admin':
        ui.notify('Acceso solo para IDEAS (superadmin).', type='negative')
        ui.navigate.to('/sistema-gestion')
        return

    with shell('Smart IdeAs Admin', back_route='/sistema-gestion') as container:
        with container:
            with ui.column().classes('ideas-panel w-full gap-4'):
                ui.label('Gestion del estandar de respuestas Smart IdeAs').classes('ideas-section-title')
                ui.label(
                    'Este contenido se aplica a todos los clientes. Edita, guarda y el asistente usara el nuevo estandar en las proximas consultas.'
                ).classes('ideas-section-note')

                ui.label('Mensaje inicial visible para cliente').classes('text-sm font-semibold text-slate-700')
                ui.label(
                    'Usa {usuario}, {agente} y {empresa} para personalizar el saludo inicial.'
                ).classes('text-xs text-slate-500')
                welcome_editor = ui.textarea(
                    label='Plantilla de bienvenida Smart IdeAs',
                    value=_read_ideas_welcome_template(),
                ).props('outlined autogrow').classes('w-full')
                welcome_editor.style('min-height: 120px;')

                with ui.row().classes('w-full items-center gap-2'):
                    def save_welcome_template() -> None:
                        text = str(welcome_editor.value or '').strip()
                        if not text:
                            ui.notify('La plantilla de bienvenida no puede quedar vacia.', type='warning')
                            return
                        if '{empresa}' not in text:
                            ui.notify('Recomendacion: inclui {empresa} para personalizar por cliente.', type='warning')
                        _write_ideas_welcome_template(text + '\n')
                        ui.notify('Plantilla de bienvenida guardada.', type='positive')

                    def restore_welcome_template() -> None:
                        welcome_editor.value = _ideas_welcome_template_default()
                        welcome_editor.update()
                        ui.notify('Plantilla base cargada en el editor. Guarda para aplicar.', type='warning')

                    ui.button('Guardar bienvenida', icon='save', on_click=save_welcome_template).props('flat color=primary')
                    ui.button('Restaurar bienvenida base', icon='restart_alt', on_click=restore_welcome_template).props('flat color=warning')

                ui.label('Modo de respuesta del asistente').classes('text-sm font-semibold text-slate-700')
                settings = _read_ideas_assistant_settings()
                mode_selector = ui.select(
                    {
                        'adaptive': 'Adaptativo (recomendado)',
                        'always_structured': 'Siempre estructurado',
                    },
                    value=str(settings.get('response_mode') or 'adaptive'),
                    label='Comportamiento de formato',
                ).props('outlined dense').classes('w-full')
                ui.label(
                    'Adaptativo: estructura completa para consultas normativas y estilo natural para consultas operativas generales.'
                ).classes('text-xs text-slate-500')
                with ui.row().classes('w-full items-center gap-2'):
                    def save_mode() -> None:
                        selected = str(mode_selector.value or 'adaptive').strip().lower()
                        if selected not in {'adaptive', 'always_structured'}:
                            selected = 'adaptive'
                        _write_ideas_assistant_settings({'response_mode': selected})
                        ui.notify('Modo de respuesta guardado.', type='positive')

                    ui.button('Guardar modo', icon='tune', on_click=save_mode).props('flat color=primary')

                ui.separator().classes('my-2')
                ui.label('Copiloto por cliente (reglas dedicadas)').classes('text-sm font-semibold text-slate-700')
                ui.label(
                    'Define tono, nivel de detalle y limites por empresa. Estas reglas se inyectan en cada consulta de Smart IdeAs.'
                ).classes('text-xs text-slate-500')

                companies = obtener_empresas() or []
                company_rule_options = {str(emp_id): fix_text(str(name)) for emp_id, name in companies}
                company_rule_select = ui.select(
                    company_rule_options,
                    value=next(iter(company_rule_options.keys()), None),
                    label='Empresa objetivo',
                ).props('outlined dense').classes('w-full')
                tone_select = ui.select(
                    {
                        'directo': 'Directo',
                        'consultivo': 'Consultivo',
                        'ejecutivo': 'Ejecutivo',
                        'coach_operativo': 'Coach operativo',
                    },
                    value='directo',
                    label='Tono',
                ).props('outlined dense').classes('w-full')
                detail_select = ui.select(
                    {
                        'breve': 'Breve',
                        'medio': 'Medio',
                        'profundo': 'Profundo',
                    },
                    value='breve',
                    label='Nivel de detalle',
                ).props('outlined dense').classes('w-full')
                limits_input = ui.input('Limites y foco').props('outlined dense').classes('w-full')
                limits_input.value = 'No mas de 8 lineas salvo pedido explicito; priorizar accion inmediata de planta.'
                glossary_input = ui.input('Glosario preferido del cliente').props('outlined dense').classes('w-full')
                glossary_input.value = 'APQP, Run@Rate, GP12, CS1, PSCR, VDA, OEM'
                extra_rules_editor = ui.textarea(
                    label='Instrucciones adicionales del copiloto',
                    value='',
                ).props('outlined autogrow').classes('w-full')
                extra_rules_editor.style('min-height: 100px;')

                def load_client_rules_into_form() -> None:
                    cid = str(company_rule_select.value or '').strip()
                    by_company = _read_ideas_client_rules().get('by_company') or {}
                    current = by_company.get(cid) if isinstance(by_company.get(cid), dict) else {}
                    tone_select.value = str(current.get('tone') or 'directo')
                    detail_select.value = str(current.get('detail_level') or 'breve')
                    limits_input.value = str(current.get('limits') or '')
                    glossary_input.value = str(current.get('glossary') or '')
                    extra_rules_editor.value = str(current.get('extra_instructions') or '')
                    tone_select.update()
                    detail_select.update()
                    limits_input.update()
                    glossary_input.update()
                    extra_rules_editor.update()

                def save_client_rules() -> None:
                    cid = str(company_rule_select.value or '').strip()
                    if not cid:
                        ui.notify('Selecciona una empresa para guardar reglas.', type='warning')
                        return
                    payload = _read_ideas_client_rules()
                    by_company = payload.get('by_company') or {}
                    by_company[cid] = {
                        'tone': str(tone_select.value or 'directo').strip(),
                        'detail_level': str(detail_select.value or 'breve').strip(),
                        'limits': str(limits_input.value or '').strip(),
                        'glossary': str(glossary_input.value or '').strip(),
                        'extra_instructions': str(extra_rules_editor.value or '').strip(),
                        'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    }
                    _write_ideas_client_rules({'by_company': by_company})
                    ui.notify('Reglas del copiloto guardadas para la empresa seleccionada.', type='positive')

                def clear_client_rules() -> None:
                    cid = str(company_rule_select.value or '').strip()
                    if not cid:
                        ui.notify('Selecciona una empresa.', type='warning')
                        return
                    payload = _read_ideas_client_rules()
                    by_company = payload.get('by_company') or {}
                    if cid in by_company:
                        by_company.pop(cid, None)
                        _write_ideas_client_rules({'by_company': by_company})
                    load_client_rules_into_form()
                    ui.notify('Reglas especificas eliminadas. Esa empresa vuelve al estandar global.', type='warning')

                company_rule_select.on('update:model-value', lambda _e: load_client_rules_into_form())
                load_client_rules_into_form()
                with ui.row().classes('w-full items-center gap-2'):
                    ui.button('Guardar reglas cliente', icon='save', on_click=save_client_rules).props('flat color=primary')
                    ui.button('Quitar reglas cliente', icon='delete', on_click=clear_client_rules).props('flat color=negative')

                ui.separator().classes('my-2')
                ui.label('Memoria por empresa (historial de copiloto)').classes('text-sm font-semibold text-slate-700')
                ui.label(
                    'Permite auditar conversaciones recientes y limpiar memoria para mantener foco operativo.'
                ).classes('text-xs text-slate-500')
                memory_company_select = ui.select(
                    company_rule_options,
                    value=next(iter(company_rule_options.keys()), None),
                    label='Empresa memoria',
                ).props('outlined dense').classes('w-full')
                memory_table = ui.table(
                    columns=[
                        {'name': 'created_at', 'label': 'Fecha', 'field': 'created_at', 'align': 'left'},
                        {'name': 'user_key', 'label': 'Usuario', 'field': 'user_key', 'align': 'left'},
                        {'name': 'role', 'label': 'Rol', 'field': 'role', 'align': 'left'},
                        {'name': 'module_context', 'label': 'Modulo', 'field': 'module_context', 'align': 'left'},
                        {'name': 'content', 'label': 'Contenido', 'field': 'content', 'align': 'left'},
                    ],
                    rows=[],
                    row_key='created_at',
                    pagination={'rowsPerPage': 8},
                ).classes('w-full ideas-table')
                memory_table.props('dense flat bordered')

                def refresh_memory_table() -> None:
                    cid = str(memory_company_select.value or '').strip()
                    if not cid:
                        memory_table.rows = []
                        memory_table.update()
                        return
                    rows = obtener_memoria_asistente_empresa(int(cid), limite=80)
                    memory_table.rows = [
                        {
                            'created_at': str(item.get('created_at') or ''),
                            'user_key': fix_text(str(item.get('user_key') or '')),
                            'role': 'Cliente' if str(item.get('role') or '') == 'user' else 'Smart IdeAs',
                            'module_context': fix_text(str(item.get('module_context') or '')),
                            'content': (fix_text(str(item.get('content') or ''))[:220] + '...') if len(str(item.get('content') or '')) > 220 else fix_text(str(item.get('content') or '')),
                        }
                        for item in rows
                    ]
                    memory_table.update()

                def clear_memory_keep_recent() -> None:
                    cid = str(memory_company_select.value or '').strip()
                    if not cid:
                        ui.notify('Selecciona una empresa.', type='warning')
                        return
                    removed = limpiar_memoria_asistente_empresa(int(cid), conservar_recientes=12)
                    refresh_memory_table()
                    ui.notify(f'Se limpiaron {removed} registros, conservando los 12 mas recientes.', type='positive')

                def clear_memory_all() -> None:
                    cid = str(memory_company_select.value or '').strip()
                    if not cid:
                        ui.notify('Selecciona una empresa.', type='warning')
                        return
                    removed = limpiar_memoria_asistente_empresa(int(cid), conservar_recientes=0)
                    refresh_memory_table()
                    ui.notify(f'Se limpiaron {removed} registros de memoria.', type='warning')

                memory_company_select.on('update:model-value', lambda _e: refresh_memory_table())
                with ui.row().classes('w-full items-center gap-2'):
                    ui.button('Refrescar memoria', icon='refresh', on_click=refresh_memory_table).props('flat')
                    ui.button('Limpiar y conservar 12', icon='cleaning_services', on_click=clear_memory_keep_recent).props('flat color=primary')
                    ui.button('Limpiar todo', icon='delete_forever', on_click=clear_memory_all).props('flat color=negative')
                refresh_memory_table()

                ui.separator().classes('my-2')
                ui.label('Backups de base de datos').classes('text-sm font-semibold text-slate-700')
                ui.label(
                    'Crea respaldos operativos y restaura versiones de la base en caso de contingencia.'
                ).classes('text-xs text-slate-500')
                backup_table = ui.table(
                    columns=[
                        {'name': 'name', 'label': 'Archivo', 'field': 'name', 'align': 'left'},
                        {'name': 'updated_at', 'label': 'Fecha', 'field': 'updated_at', 'align': 'left'},
                        {'name': 'size_kb', 'label': 'KB', 'field': 'size_kb', 'align': 'right'},
                    ],
                    rows=[],
                    row_key='name',
                    pagination={'rowsPerPage': 6},
                ).classes('w-full ideas-table')
                backup_table.props('dense flat bordered')
                backup_select = ui.select({}, label='Backup para restaurar').props('outlined dense').classes('w-full')

                def refresh_backups_table() -> None:
                    rows = listar_backups_db(limit=40)
                    backup_table.rows = rows
                    backup_table.update()
                    backup_select.options = {item['name']: f"{item['name']} ({item['updated_at']})" for item in rows}
                    backup_select.value = rows[0]['name'] if rows else None
                    backup_select.update()

                def create_backup_now() -> None:
                    ok, msg = crear_backup_db()
                    ui.notify('Backup creado.' if ok else msg, type='positive' if ok else 'negative')
                    refresh_backups_table()

                def restore_selected_backup() -> None:
                    name = str(backup_select.value or '').strip()
                    if not name:
                        ui.notify('Selecciona un backup para restaurar.', type='warning')
                        return
                    ok, msg = restaurar_backup_db(name)
                    ui.notify(msg, type='positive' if ok else 'negative')
                    refresh_backups_table()

                with ui.row().classes('w-full items-center gap-2'):
                    ui.button('Crear backup ahora', icon='save', on_click=create_backup_now).props('flat color=primary')
                    ui.button('Refrescar lista', icon='refresh', on_click=refresh_backups_table).props('flat')
                    ui.button('Restaurar backup', icon='restore', on_click=restore_selected_backup).props('flat color=warning')
                refresh_backups_table()

                editor = ui.textarea(
                    label='Estandar IDEAS (Markdown)',
                    value=_read_ideas_standard(),
                ).props('outlined autogrow').classes('w-full')
                editor.style('min-height: 420px;')
                with ui.row().classes('w-full items-end gap-3'):
                    version_input = ui.input('Version').props('outlined dense').classes('w-40')
                    version_input.value = _next_ideas_version()
                    note_input = ui.input('Nota de cambio').props('outlined dense').classes('w-full')
                    note_input.value = 'Ajuste de estandar Smart IdeAs'

                changelog_table = ui.table(
                    columns=[
                        {'name': 'timestamp', 'label': 'Fecha', 'field': 'timestamp', 'align': 'left'},
                        {'name': 'version', 'label': 'Version', 'field': 'version', 'align': 'left'},
                        {'name': 'note', 'label': 'Nota', 'field': 'note', 'align': 'left'},
                    ],
                    rows=[],
                    row_key='timestamp',
                ).classes('w-full ideas-table')
                changelog_table.props('dense flat bordered')

                def refresh_changelog_table() -> None:
                    rows = _read_ideas_changelog()
                    recent = list(reversed(rows[-12:]))
                    changelog_table.rows = [
                        {
                            'timestamp': str(item.get('timestamp') or ''),
                            'version': str(item.get('version') or ''),
                            'note': str(item.get('note') or ''),
                        }
                        for item in recent
                    ]
                    changelog_table.update()

                with ui.row().classes('w-full items-center gap-2'):
                    def save_standard() -> None:
                        text = str(editor.value or '').strip()
                        if not text:
                            ui.notify('El estandar no puede quedar vacio.', type='warning')
                            return
                        version = str(version_input.value or '').strip() or _next_ideas_version()
                        note = str(note_input.value or '').strip() or 'Actualizacion sin nota'
                        _write_ideas_standard(text + '\n')
                        _append_ideas_changelog(version=version, note=note, size=len(text))
                        version_input.value = _next_ideas_version()
                        version_input.update()
                        refresh_changelog_table()
                        ui.notify('Estandar guardado. Smart IdeAs ya usa esta version.', type='positive')

                    def reload_standard() -> None:
                        editor.value = _read_ideas_standard()
                        editor.update()
                        version_input.value = _next_ideas_version()
                        version_input.update()
                        refresh_changelog_table()
                        ui.notify('Contenido recargado desde archivo.', type='info')

                    def restore_default() -> None:
                        editor.value = _ideas_standard_default()
                        editor.update()
                        ui.notify('Plantilla base cargada en el editor. Guarda para aplicar.', type='warning')

                    ui.button('Guardar estandar', icon='save', on_click=save_standard).props('color=primary')
                    ui.button('Recargar archivo', icon='refresh', on_click=reload_standard).props('flat')
                    ui.button('Restaurar base', icon='restart_alt', on_click=restore_default).props('flat color=warning')
                refresh_changelog_table()

                with ui.column().classes('w-full'):
                    ui.label('Checklist minimo recomendado').classes('text-sm font-semibold text-slate-700')
                    ui.markdown(
                        '- Definir rol y tono\n'
                        '- Mantener formato de 5 bloques\n'
                        '- Incluir reglas de calidad\n'
                        '- Definir palabras o estilo IDEAS\n'
                        '- Limitar ambiguedad y pedir datos faltantes'
                    ).classes('text-slate-600')


register_public_pages(ui, {'public_shell': public_shell, 'get_banner_url': get_banner_url})

if not INSTITUTIONAL_ONLY:
    register_management_page(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'diagnosis_rows': diagnosis_rows, 'fix_text': fix_text, 'quick_card': quick_card, 'render_metrics': render_metrics, 'certifications_summary': certifications_summary, 'set_selection': set_selection, 'obtener_color_contraste': obtener_color_contraste, 'go_to_documents_library': go_to_documents_library, 'go_to_company_documents_module': go_to_company_documents_module, 'go_to_process_maps_module': go_to_process_maps_module, 'go_to_kpi_module': go_to_kpi_module, 'go_to_risks_module': go_to_risks_module, 'go_to_environment_module': go_to_environment_module, 'go_to_quality_module': go_to_quality_module, 'go_to_sst_module': go_to_sst_module, 'go_to_users_module': go_to_users_module})
    register_documents_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'certifications_summary': certifications_summary, 'valor_afirmativo': valor_afirmativo, 'set_selection': set_selection, 'obtener_fuentes_empresa': obtener_fuentes_empresa, 'explicar_requisito_iso': explicar_requisito_iso_guarded, 'set_ai_focus_context': set_ai_focus_context})
    register_process_maps_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'set_selection': set_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'certifications_summary': certifications_summary, 'obtener_mapa_procesos_empresa': obtener_mapa_procesos_empresa, 'agregar_proceso_mapa_empresa': agregar_proceso_mapa_empresa, 'actualizar_proceso_mapa': actualizar_proceso_mapa, 'eliminar_proceso_mapa': eliminar_proceso_mapa, 'generar_pdf_mapa_procesos': generar_pdf_mapa_procesos, 'set_ai_focus_context': set_ai_focus_context})
    register_kpi_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'set_selection': set_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'render_metrics': render_metrics, 'quick_card': quick_card, 'certifications_summary': certifications_summary, 'obtener_kpis_empresa': obtener_kpis_empresa, 'obtener_kpi_detalle': obtener_kpi_detalle, 'obtener_grupos_kpi_empresa': obtener_grupos_kpi_empresa, 'crear_grupo_kpi_empresa': crear_grupo_kpi_empresa, 'guardar_kpi': guardar_kpi, 'actualizar_kpi_meses': actualizar_kpi_meses, 'actualizar_kpi_diario_y_periodos': actualizar_kpi_diario_y_periodos, 'agregar_kpi_empresa': agregar_kpi_empresa, 'actualizar_kpi': actualizar_kpi, 'actualizar_dashboard_principal_kpi': actualizar_dashboard_principal_kpi, 'actualizar_grupos_personalizados_kpi': actualizar_grupos_personalizados_kpi, 'eliminar_kpi': eliminar_kpi, 'obtener_mapa_procesos_empresa': obtener_mapa_procesos_empresa, 'generar_pdf_kpis': generar_pdf_kpis, 'go': go, 'set_ai_focus_context': set_ai_focus_context})
    register_risks_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'current_selection': current_selection, 'set_selection': set_selection, 'company_options': company_options, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'render_metrics': render_metrics, 'quick_card': quick_card, 'certifications_summary': certifications_summary, 'obtener_mapa_procesos_empresa': obtener_mapa_procesos_empresa, 'obtener_matrices_riesgos_empresa': obtener_matrices_riesgos_empresa, 'obtener_matriz_riesgos_detalle': obtener_matriz_riesgos_detalle, 'obtener_items_riesgos_matriz': obtener_items_riesgos_matriz, 'crear_matriz_riesgos': crear_matriz_riesgos, 'actualizar_matriz_riesgos': actualizar_matriz_riesgos, 'eliminar_matriz_riesgos': eliminar_matriz_riesgos, 'crear_item_riesgo': crear_item_riesgo, 'actualizar_item_riesgo': actualizar_item_riesgo, 'eliminar_item_riesgo': eliminar_item_riesgo, 'set_ai_focus_context': set_ai_focus_context})
    register_environment_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'current_selection': current_selection, 'set_selection': set_selection, 'company_options': company_options, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'render_metrics': render_metrics, 'quick_card': quick_card, 'certifications_summary': certifications_summary, 'obtener_mapa_procesos_empresa': obtener_mapa_procesos_empresa, 'obtener_aspectos_ambientales_empresa': obtener_aspectos_ambientales_empresa, 'crear_aspecto_ambiental': crear_aspecto_ambiental, 'actualizar_aspecto_ambiental': actualizar_aspecto_ambiental, 'eliminar_aspecto_ambiental': eliminar_aspecto_ambiental, 'obtener_requisitos_legales_ambientales_empresa': obtener_requisitos_legales_ambientales_empresa, 'crear_requisito_legal_ambiental': crear_requisito_legal_ambiental, 'actualizar_requisito_legal_ambiental': actualizar_requisito_legal_ambiental, 'eliminar_requisito_legal_ambiental': eliminar_requisito_legal_ambiental, 'obtener_simulacros_ambientales_empresa': obtener_simulacros_ambientales_empresa, 'crear_simulacro_ambiental': crear_simulacro_ambiental, 'actualizar_simulacro_ambiental': actualizar_simulacro_ambiental, 'eliminar_simulacro_ambiental': eliminar_simulacro_ambiental, 'sugerir_matriz_legal_ia': sugerir_matriz_legal_ia_guarded, 'generar_reporte_simulacro': generar_reporte_simulacro, 'set_ai_focus_context': set_ai_focus_context})
    register_sst_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'current_selection': current_selection, 'set_selection': set_selection, 'company_options': company_options, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'obtener_mapa_procesos_empresa': obtener_mapa_procesos_empresa})
    register_quality_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'current_selection': current_selection, 'set_selection': set_selection, 'company_options': company_options, 'obtener_empresa_detalle': obtener_empresa_detalle, 'valor_afirmativo': valor_afirmativo, 'fix_text': fix_text, 'obtener_problemas_calidad_empresa': obtener_problemas_calidad_empresa, 'obtener_problema_calidad_detalle': obtener_problema_calidad_detalle, 'crear_problema_calidad_8d': crear_problema_calidad_8d, 'actualizar_problema_calidad_8d': actualizar_problema_calidad_8d, 'eliminar_problema_calidad_8d': eliminar_problema_calidad_8d, 'obtener_5_porque_problema_calidad': obtener_5_porque_problema_calidad, 'guardar_5_porque_problema_calidad': guardar_5_porque_problema_calidad, 'obtener_ishikawa_problema_calidad': obtener_ishikawa_problema_calidad, 'guardar_ishikawa_problema_calidad': guardar_ishikawa_problema_calidad, 'obtener_acciones_8d': obtener_acciones_8d, 'guardar_accion_8d': guardar_accion_8d, 'eliminar_accion_8d': eliminar_accion_8d, 'generar_reporte_8d': generar_reporte_8d, 'generar_pdf_8d': generar_pdf_8d, 'obtener_fuentes_empresa': obtener_fuentes_empresa, 'sugerir_causas_ishikawa': sugerir_causas_ishikawa_guarded, 'set_ai_focus_context': set_ai_focus_context})
    register_users_module(ui, {'app': app, 'ensure_platform_access': ensure_platform_access, 'shell': shell, 'fix_text': fix_text, 'obtener_usuarios': obtener_usuarios, 'crear_usuario': guarded_crear_usuario, 'actualizar_usuario': guarded_actualizar_usuario, 'eliminar_usuario': guarded_eliminar_usuario, 'obtener_empresas': obtener_empresas})
    register_platform_pages(ui, app, {'public_shell': public_shell, 'shell': shell, 'ensure_platform_access': ensure_platform_access, 'get_banner_url': get_banner_url, 'get_logo_url': get_logo_url, 'quick_card': quick_card, 'obtener_empresas': obtener_empresas, 'obtener_empresa_detalle': obtener_empresa_detalle, 'diagnosis_rows': diagnosis_rows, 'obtener_alertas_globales': obtener_alertas_globales, 'verificar_usuario': verificar_usuario, 'verificar_login_empresa': verificar_login_empresa, 'guardar_token_empresa': guardar_token_empresa, 'verificar_token_empresa': verificar_token_empresa, 'actualizar_password_empresa': actualizar_password_empresa, 'provisionar_acceso_empresa': provisionar_acceso_empresa, 'generar_token_seguro': generar_token_seguro, 'enviar_correo_acceso': enviar_correo_acceso, 'set_selection': set_selection, 'PLATFORM_USER': PLATFORM_USER, 'PLATFORM_PASSWORD': PLATFORM_PASSWORD})
    register_diagnostic_pages(ui, app, {'pd': pd, 'go': go, 'shell': shell, 'ensure_platform_access': ensure_platform_access, 'obtener_empresas': obtener_empresas, 'obtener_empresa_detalle': obtener_empresa_detalle, 'guardar_empresa': guarded_guardar_empresa, 'actualizar_empresa': guarded_actualizar_empresa, 'eliminar_empresa': guarded_eliminar_empresa, 'guardar_fuente_empresa': guarded_guardar_fuente_empresa, 'obtener_fuentes_empresa': obtener_fuentes_empresa, 'eliminar_fuente': guarded_eliminar_fuente, 'guardar_token_empresa': guardar_token_empresa, 'generar_token_seguro': generar_token_seguro, 'enviar_correo_acceso': enviar_correo_acceso, 'go_to_management_workspace': go_to_management_workspace, 'set_selection': set_selection, 'leer_diagnostico_excel': leer_diagnostico_excel, 'grouped_questions': grouped_questions, 'load_criteria': load_criteria, 'company_options': company_options, 'current_selection': current_selection, 'diagnosis_record': diagnosis_record, 'diagnosis_response_dicts': diagnosis_response_dicts, 'split_evidence_values': split_evidence_values, 'fix_text': fix_text, 'certifications_summary': certifications_summary, 'actualizar_diagnostico': guarded_actualizar_diagnostico, 'guardar_diagnostico': guarded_guardar_diagnostico, 'obtener_nivel': obtener_nivel, 'obtener_conclusion': obtener_conclusion, 'diagnosis_rows': diagnosis_rows, 'diagnosis_badge_style': diagnosis_badge_style, 'diagnosis_options': diagnosis_options, 'build_eje_scores': build_eje_scores, 'build_plan': build_plan, 'short_axis_label': short_axis_label, 'obtener_mensaje_direccion': obtener_mensaje_direccion, 'quick_card': quick_card, 'obtener_prioridad_recomendada': obtener_prioridad_recomendada, 'start_edit': start_edit, 'render_metrics': render_metrics, 'eliminar_diagnostico': guarded_eliminar_diagnostico, 'generar_pdf_ejecutivo_v2': generar_pdf_ejecutivo_v2})
render_port = os.getenv('PORT')
run_port = int(render_port) if render_port else 8502
run_host = '0.0.0.0'

ui.run(
    title='IDEAS Consulting V2',
    favicon=FAVICON_ICO_PATH,
    host=run_host,
    port=run_port,
    reload=False,
    native=False,
    storage_secret='ideas-consulting-v2',
)


