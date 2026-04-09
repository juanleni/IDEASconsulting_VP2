
from __future__ import annotations

import os
import socket
import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from nicegui import app, ui

ROOT = Path(__file__).resolve().parents[1]
THIS_DIR = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))
if str(THIS_DIR) not in sys.path:
    sys.path.append(str(THIS_DIR))

from database import crear_base  # noqa: E402
from core_data import (  # noqa: E402
    actualizar_diagnostico,
    eliminar_diagnostico,
    guardar_diagnostico,
    guardar_empresa,
    leer_diagnostico_excel,
    obtener_diagnosticos_empresa,
    obtener_empresa_detalle,
    obtener_empresas,
    obtener_historial_diagnosticos,
    obtener_respuestas_diagnostico,
)
from ideas_utils import (  # noqa: E402
    obtener_conclusion,
    obtener_impacto_sugerido,
    obtener_mensaje_direccion,
    obtener_nivel,
    obtener_plazo_sugerido,
    obtener_prioridad_recomendada,
    obtener_responsable_sugerido,
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

crear_base()
app.add_static_files('/assets', str(ROOT))

PLATFORM_USER = 'IDEAS'
PLATFORM_PASSWORD = '2026'


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
        .ideas-public-shell { width:100%; max-width:1320px; margin:0 auto; padding:2px 28px 48px 28px; }
        .ideas-public-topbar { position:sticky; top:0; z-index:50; background:rgba(247,250,252,.84); backdrop-filter:blur(18px); border-bottom:1px solid var(--ideas-line); }
        .ideas-public-nav { display:flex; align-items:center; justify-content:space-between; gap:1rem; width:100%; max-width:1320px; margin:0 auto; padding:12px 28px; }
        .ideas-public-brand { display:flex; align-items:center; gap:.9rem; }
        .ideas-public-brand img { width:44px; height:44px; object-fit:contain; }
        .ideas-public-brand .name { color:var(--ideas-navy); font-weight:800; font-size:1rem; letter-spacing:.02em; }
        .ideas-public-brand .tag { color:#64748b; font-size:.82rem; margin-top:.12rem; }
        .ideas-public-links { display:flex; align-items:center; gap:.4rem; flex-wrap:wrap; }
        .ideas-public-links a { color:#334155; text-decoration:none; font-weight:700; padding:.7rem .9rem; border-radius:999px; }
        .ideas-public-links a:hover { background:rgba(255,255,255,.9); }
        .ideas-public-actions { display:flex; align-items:center; gap:.7rem; flex-wrap:wrap; }
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
        .ideas-public-section { margin-top:14px; }
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
        .ideas-whatsapp-link.topbar { margin-top:0; padding:.72rem 1rem; border-radius:999px; font-size:.92rem; }
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
        .q-drawer { background:radial-gradient(circle at top left, rgba(15,143,97,.09), transparent 28%), linear-gradient(180deg, rgba(249,252,251,.99) 0%, rgba(239,246,243,.99) 100%); border-right:1px solid var(--ideas-line); }
        .q-field__control, .q-field--outlined .q-field__control { border-radius:18px !important; background:rgba(255,255,255,.92); }
        .q-btn { text-transform:none; letter-spacing:0; font-weight:700; }
        .q-tab { border-radius:16px; min-height:44px; }
        .q-tab--active { background:rgba(31,126,214,.08); }
        @media (max-width: 1100px) { .ideas-hero-card, .ideas-score-guide, .ideas-grid-2, .ideas-grid-3, .ideas-public-hero, .ideas-editorial-band, .ideas-feature-list, .ideas-module-grid { grid-template-columns:1fr; } .ideas-public-nav { flex-direction:column; align-items:flex-start; } }
        </style>
        '''
    )


def fix_text(value) -> str:
    if value is None:
        return ''
    text = str(value)
    if any(token in text for token in ['Ã', 'Â', 'ð', '�']):
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
    return bool(app.storage.user.get('platform_auth'))


def ensure_platform_access() -> bool:
    if is_platform_authenticated():
        return True
    ui.navigate.to('/plataforma')
    return False


def logout_platform() -> None:
    app.storage.user['platform_auth'] = False
    ui.navigate.to('/')


def shell(page_title: str):
    inject_global_styles()
    logo = get_logo_url()
    with ui.left_drawer(value=True, bordered=False).classes('p-4'):
        with ui.column().classes('ideas-brand-card w-full'):
            if logo:
                ui.image(logo).classes('w-28 mb-3')
            ui.label('IDEAS Consulting').classes('text-slate-900 text-lg font-bold')
            ui.label('Consultoría estratégica').classes('text-xs uppercase tracking-widest text-slate-500')
            ui.separator().classes('my-3')
            ui.label('Navegación').classes('text-[11px] uppercase tracking-[0.22em] text-slate-400')
        for label, route, icon in [('Inicio', '/dashboard', 'home'), ('Empresas', '/empresas', 'business'), ('Sistema de gestión', '/sistema-gestion', 'account_tree'), ('Diagnóstico', '/diagnostico', 'assignment'), ('Resultados', '/resultados', 'analytics'), ('Historial', '/historial', 'history')]:
            ui.button(label, icon=icon, on_click=lambda r=route: ui.navigate.to(r)).props('flat align=left').classes('ideas-nav-btn')
        with ui.column().classes('ideas-brand-card w-full mt-4'):
            ui.label('Board-ready').classes('text-[11px] uppercase tracking-[0.18em] text-slate-400')
            ui.label('Workspace ejecutivo').classes('text-slate-900 font-semibold mt-1')
            ui.label('Más visual, más modular y preparada para evolucionar sin tocar la app actual.').classes('text-sm text-slate-500 mt-1')
        ui.button('Volver al sitio', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat align=left').classes('ideas-nav-btn mt-2')
    with ui.header().classes('ideas-topbar'):
        with ui.row().classes('w-full items-center justify-between px-4'):
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
                ui.label('Executive diagnostic workspace').classes('text-sm text-slate-500')
                ui.button('Sitio', icon='public', on_click=lambda: ui.navigate.to('/')).props('flat dense')
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
                <div class="ideas-public-links">
                    <a href="/">Inicio</a>
                    <a href="/servicios">Servicios</a>
                    <a href="/metodologia">Metodología</a>
                    <a href="/contacto">Contacto</a>
                </div>
                <div class="ideas-public-actions">
                    {whatsapp_html}
                    <a href="/plataforma" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--unelevated q-btn--rectangle bg-primary text-white" style="padding:11px 16px;border-radius:999px;">Ingresar</button></a>
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
    empresa_id = app.storage.user.get('current_empresa_id')
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
    app.storage.user['current_empresa_id'] = int(empresa_id) if empresa_id else None
    app.storage.user['current_diag_id'] = int(diagnostico_id) if diagnostico_id else None


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


register_public_pages(ui, {'public_shell': public_shell, 'get_banner_url': get_banner_url})
register_management_page(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'diagnosis_rows': diagnosis_rows, 'fix_text': fix_text, 'quick_card': quick_card, 'render_metrics': render_metrics, 'certifications_summary': certifications_summary, 'set_selection': set_selection, 'go_to_documents_library': go_to_documents_library, 'go_to_company_documents_module': go_to_company_documents_module})
register_documents_module(ui, {'ensure_platform_access': ensure_platform_access, 'shell': shell, 'company_options': company_options, 'current_selection': current_selection, 'obtener_empresa_detalle': obtener_empresa_detalle, 'fix_text': fix_text, 'certifications_summary': certifications_summary, 'valor_afirmativo': valor_afirmativo, 'set_selection': set_selection})

register_platform_pages(ui, app, {'public_shell': public_shell, 'shell': shell, 'ensure_platform_access': ensure_platform_access, 'get_banner_url': get_banner_url, 'get_logo_url': get_logo_url, 'quick_card': quick_card, 'PLATFORM_USER': PLATFORM_USER, 'PLATFORM_PASSWORD': PLATFORM_PASSWORD})
register_diagnostic_pages(ui, app, {'pd': pd, 'go': go, 'shell': shell, 'ensure_platform_access': ensure_platform_access, 'obtener_empresas': obtener_empresas, 'obtener_empresa_detalle': obtener_empresa_detalle, 'guardar_empresa': guardar_empresa, 'go_to_management_workspace': go_to_management_workspace, 'set_selection': set_selection, 'leer_diagnostico_excel': leer_diagnostico_excel, 'grouped_questions': grouped_questions, 'load_criteria': load_criteria, 'company_options': company_options, 'current_selection': current_selection, 'diagnosis_record': diagnosis_record, 'diagnosis_response_dicts': diagnosis_response_dicts, 'split_evidence_values': split_evidence_values, 'fix_text': fix_text, 'certifications_summary': certifications_summary, 'actualizar_diagnostico': actualizar_diagnostico, 'guardar_diagnostico': guardar_diagnostico, 'obtener_nivel': obtener_nivel, 'obtener_conclusion': obtener_conclusion, 'diagnosis_rows': diagnosis_rows, 'diagnosis_badge_style': diagnosis_badge_style, 'diagnosis_options': diagnosis_options, 'build_eje_scores': build_eje_scores, 'build_plan': build_plan, 'short_axis_label': short_axis_label, 'obtener_mensaje_direccion': obtener_mensaje_direccion, 'quick_card': quick_card, 'obtener_prioridad_recomendada': obtener_prioridad_recomendada, 'start_edit': start_edit, 'render_metrics': render_metrics, 'eliminar_diagnostico': eliminar_diagnostico})
render_port = os.getenv('PORT')
run_port = int(render_port) if render_port else get_free_port(8502)
run_host = '0.0.0.0' if render_port else '127.0.0.1'

ui.run(
    title='IDEAS Consulting V2',
    host=run_host,
    port=run_port,
    reload=False,
    native=False,
    storage_secret='ideas-consulting-v2',
)


