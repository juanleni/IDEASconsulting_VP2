
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
        @media (max-width: 1100px) { .ideas-hero-card, .ideas-score-guide, .ideas-grid-2, .ideas-grid-3, .ideas-public-hero, .ideas-editorial-band, .ideas-feature-list { grid-template-columns:1fr; } .ideas-public-nav { flex-direction:column; align-items:flex-start; } }
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
        for label, route, icon in [('Inicio', '/dashboard', 'home'), ('Empresas', '/empresas', 'business'), ('Diagnóstico', '/diagnostico', 'assignment'), ('Resultados', '/resultados', 'analytics'), ('Historial', '/historial', 'history')]:
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


@ui.page('/')
def website_home_page() -> None:
    shell_container = public_shell('Sitio institucional')
    banner = get_banner_url()
    logo = get_logo_url()
    fallback_logo = f'<img src="{logo}" alt="IDEAS logo" />' if logo else ''
    media_html = (
        f'<img src="{banner}" style="width:100%;min-height:420px;object-fit:cover;border-radius:24px;" />'
        if banner
        else (
            '<div style="padding:28px;height:100%;display:flex;flex-direction:column;justify-content:center;">'
            f'<div class="ideas-hero-brand">{fallback_logo}<div><div class="brand-name">IDEAS Consulting</div>'
            '<div class="brand-tag">Enfoque ejecutivo para diagnosticar, priorizar y avanzar.</div></div></div>'
            '<div class="ideas-public-lead">Una plataforma visual y consultiva para evaluar madurez organizacional, generar reportes ejecutivos y ordenar planes de acción.</div>'
            '</div>'
        )
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
            f'''
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
                        <div class="ideas-feature-item"><div class="glyph">📊</div><div class="content"><div class="title">Mejor control</div><div class="detail">Más visibilidad para gestionar y decidir mejor.</div></div></div>
                        <div class="ideas-feature-item"><div class="glyph">🛡</div><div class="content"><div class="title">Menos riesgos</div><div class="detail">Mayor robustez frente a desvíos y auditorías.</div></div></div>
                    </div>
                </div>
                <div class="ideas-service-card">
                    <div class="icon">Plataforma</div>
                    <h3>Acceso a plataforma</h3>
                    <p>Si ya trabajas con IDEAS, puedes ingresar directamente a la plataforma operativa para cargar empresas, diagnósticos y reportes.</p>
                    <a href="/plataforma" style="text-decoration:none;"><button class="q-btn q-btn-item non-selectable no-outline q-btn--unelevated q-btn--rectangle bg-primary text-white" style="padding:12px 18px;border-radius:16px;">Ingresar a la plataforma</button></a>
                </div>
            </div>
            '''
        )


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
                ui.button('Nuevo diagnóstico', icon='assignment_add', on_click=lambda: ui.navigate.to('/diagnostico')).props('outline color=primary')


@ui.page('/empresas')
def companies_page() -> None:
    if not ensure_platform_access():
        return
    shell_container = shell('Empresas')
    companies = []
    for company_id, name in obtener_empresas():
        detail = obtener_empresa_detalle(company_id) or {}
        companies.append({'razon_social': fix_text(name), 'id': company_id, **detail})
    with shell_container:
        ui.label('Base de empresas').classes('ideas-kicker')
        ui.label('Alta y administración del universo consultivo.').classes('text-3xl font-bold text-slate-900')
        ui.label('Registrá la ficha institucional de cada empresa con el nivel de detalle necesario para los reportes ejecutivos.').classes('ideas-subtitle mb-4')
        with ui.card().classes('ideas-panel w-full'):
            razon_social = ui.input('Razón social').classes('w-full')
            with ui.row().classes('w-full gap-4'):
                ubicacion = ui.input('Ubicación').classes('col')
                rubro = ui.input('Rubro').classes('col')
                cantidad_empleados = ui.number('Cantidad de empleados', value=0, min=0, precision=0).classes('col')
            ui.label('Persona de contacto').classes('text-lg font-semibold text-slate-800 mt-2')
            with ui.row().classes('w-full gap-4'):
                contacto_nombre = ui.input('Nombre').classes('col')
                contacto_correo = ui.input('Correo').classes('col')
            with ui.row().classes('w-full gap-4'):
                contacto_telefono = ui.input('Teléfono').classes('col')
                contacto_posicion = ui.input('Posición').classes('col')
            ui.label('Certificaciones').classes('text-lg font-semibold text-slate-800 mt-2')
            with ui.row().classes('w-full gap-4'):
                cert_9001 = ui.switch('ISO 9001', value=False)
                cert_14001 = ui.switch('ISO 14001', value=False)
                cert_45001 = ui.switch('ISO 45001', value=False)
                cert_iatf = ui.switch('IATF', value=False)
            def save_company() -> None:
                payload = {'razon_social': razon_social.value or '', 'ubicacion': ubicacion.value or '', 'contacto_nombre': contacto_nombre.value or '', 'contacto_correo': contacto_correo.value or '', 'contacto_telefono': contacto_telefono.value or '', 'contacto_posicion': contacto_posicion.value or '', 'rubro': rubro.value or '', 'cantidad_empleados': int(cantidad_empleados.value or 0), 'cert_iso_9001': 'Sí' if cert_9001.value else 'No', 'cert_iso_14001': 'Sí' if cert_14001.value else 'No', 'cert_iso_45001': 'Sí' if cert_45001.value else 'No', 'cert_iatf': 'Sí' if cert_iatf.value else 'No'}
                ok, message = guardar_empresa(payload)
                ui.notify(fix_text(message), type='positive' if ok else 'negative')
                if ok:
                    ui.navigate.to('/empresas')
            with ui.row().classes('w-full justify-end mt-3'):
                ui.button('Guardar empresa', icon='save', on_click=save_company).props('unelevated color=primary')
        table_rows = [{'razon_social': item['razon_social'], 'ubicacion': fix_text(item.get('ubicacion', '')), 'rubro': fix_text(item.get('rubro', '')), 'empleados': item.get('cantidad_empleados') or 0, 'contacto': fix_text(item.get('contacto_nombre', '')), 'certificaciones': certifications_summary(item)} for item in companies]
        ui.table(columns=[{'name': 'razon_social', 'label': 'Razón social', 'field': 'razon_social', 'align': 'left'}, {'name': 'ubicacion', 'label': 'Ubicación', 'field': 'ubicacion', 'align': 'left'}, {'name': 'rubro', 'label': 'Rubro', 'field': 'rubro', 'align': 'left'}, {'name': 'empleados', 'label': 'Empleados', 'field': 'empleados', 'align': 'right'}, {'name': 'contacto', 'label': 'Contacto', 'field': 'contacto', 'align': 'left'}, {'name': 'certificaciones', 'label': 'Certificaciones', 'field': 'certificaciones', 'align': 'left'}], rows=table_rows, pagination=8).classes('w-full ideas-card ideas-table p-3 mt-6')

@ui.page('/diagnostico')
def diagnostic_page() -> None:
    if not ensure_platform_access():
        return
    shell_container = shell('Nuevo Diagnóstico')
    df_base = leer_diagnostico_excel().copy()
    grouped = grouped_questions(df_base)
    criteria, regla = load_criteria()
    company_map = company_options()
    score_labels = {1: '1 · Inicial', 2: '2 · Parcial', 3: '3 · Implementado', 4: '4 · Estandarizado'}
    edit_id = app.storage.user.get('edit_diag_id')
    duplicate_id = app.storage.user.get('duplicate_diag_id')
    preload_id = int(edit_id or duplicate_id) if (edit_id or duplicate_id) else None
    preload = diagnosis_record(preload_id)
    preload_responses = diagnosis_response_dicts(preload_id)
    preload_map = {(row['eje'], row['pregunta']): row for row in preload_responses}
    with shell_container:
        ui.label('Nuevo diagnóstico').classes('ideas-kicker')
        ui.label('Captura estructurada para análisis ejecutivo.').classes('text-3xl font-bold text-slate-900')
        ui.label('Registrá cada eje con una evaluación consistente y evidencia asociada para sostener la lectura consultiva posterior.').classes('ideas-subtitle')
        if preload and edit_id:
            ui.html(f'<div class="ideas-mode-banner">Modo edición<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Estás actualizando un diagnóstico ya registrado.</div>')
        elif preload and duplicate_id:
            ui.html(f'<div class="ideas-mode-banner">Duplicar como nuevo<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Tomás un corte previo como base para crear una nueva evaluación.</div>')
        with ui.card().classes('ideas-panel w-full mt-4'):
            ui.label('Criterios de puntuación').classes('text-lg font-semibold text-slate-900')
            guide_html = ''.join(f'''<div class="ideas-score-item"><div class="badge">{int(item['escala'])}</div><div style="margin-top:10px;font-weight:800;color:#0f172a;">{fix_text(item['nivel'])}</div><div style="margin-top:8px;color:#475569;line-height:1.55;">{fix_text(item['resumen'])}</div></div>''' for item in criteria)
            ui.html(f'<div class="ideas-score-guide mt-3">{guide_html}</div>')
            ui.label(f'Regla de evidencia: {fix_text(regla)}').classes('text-sm text-amber-700 mt-3')
        default_company = preload['empresa_id'] if preload else (current_selection()[0] or None)
        company_select = ui.select(company_map, value=default_company, label='Empresa').classes('w-full mt-5').props('outlined')
        response_inputs: dict[tuple[str, str], object] = {}
        evidence_inputs: dict[tuple[str, str], list[object]] = {}
        evidence_containers: dict[tuple[str, str], object] = {}
        observation_inputs: dict[tuple[str, str], object] = {}

        def ensure_evidence_fields(key: tuple[str, str]) -> None:
            fields = evidence_inputs[key]
            values = [fix_text(field.value).strip() for field in fields]
            if values and values[-1] != '':
                with evidence_containers[key]:
                    new_field = ui.input(f'Evidencia {len(fields) + 1}').classes('w-full').props('outlined')
                fields.append(new_field)
                new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
                return

            removable_indexes = [index for index, value in enumerate(values[:-1]) if value == '']
            for index in reversed(removable_indexes):
                field = fields.pop(index)
                field.delete()

            if not fields:
                with evidence_containers[key]:
                    new_field = ui.input('Evidencia 1').classes('w-full').props('outlined')
                fields.append(new_field)
                new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
        for eje, questions in grouped.items():
            with ui.expansion(fix_text(eje), icon='schema').classes('w-full ideas-card mt-4'):
                for question in questions:
                    key = (eje, question)
                    existing = preload_map.get(key, {})
                    with ui.card().classes('ideas-soft w-full p-4 mb-3'):
                        ui.label(question).classes('text-base font-semibold text-slate-900')
                        response_inputs[key] = ui.select({value: f"{label} · {fix_text(next((c['resumen'] for c in criteria if int(c['escala']) == value), ''))}" for value, label in score_labels.items()}, value=int(existing.get('respuesta', 3)), label='Puntaje').classes('w-full mt-3').props('outlined')
                        with ui.row().classes('w-full gap-4 mt-2'):
                            evidence_containers[key] = ui.column().classes('col w-full gap-2')
                            observation_inputs[key] = ui.textarea('Observación').classes('col w-full').props('outlined autogrow')
                        evidence_inputs[key] = []
                        preload_evidences = split_evidence_values(existing.get('evidencia', ''))
                        with evidence_containers[key]:
                            for idx, evidence_value in enumerate(preload_evidences, start=1):
                                field = ui.input(f'Evidencia {idx}').classes('w-full').props('outlined')
                                field.value = evidence_value
                                evidence_inputs[key].append(field)
                            if not preload_evidences or preload_evidences[-1].strip() != '':
                                extra_field = ui.input(f'Evidencia {len(evidence_inputs[key]) + 1}').classes('w-full').props('outlined')
                                evidence_inputs[key].append(extra_field)
                        for field in evidence_inputs[key]:
                            field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
                        ensure_evidence_fields(key)
                        observation_inputs[key].value = existing.get('observacion', '')
        def save_diagnosis() -> None:
            if not company_select.value:
                ui.notify('Seleccioná una empresa antes de guardar.', type='warning')
                return
            rows = []
            for (eje, question), selector in response_inputs.items():
                evidences = [fix_text(field.value).strip() for field in evidence_inputs[(eje, question)] if fix_text(field.value).strip()]
                rows.append({'eje': eje, 'pregunta': question, 'respuesta': int(selector.value or 1), 'evidencia': ', '.join(evidences), 'observacion': observation_inputs[(eje, question)].value or ''})
            score = round(sum(item['respuesta'] for item in rows) / len(rows), 2) if rows else 0
            nivel = obtener_nivel(score)
            conclusion = fix_text(obtener_conclusion(score))
            empresa_id = int(company_select.value)
            if edit_id:
                diag_id, _fecha, unchanged = actualizar_diagnostico(int(edit_id), empresa_id, score, nivel, conclusion, rows)
                ui.notify('No se detectaron cambios; el diagnóstico ya estaba actualizado.' if unchanged else 'Diagnóstico actualizado correctamente.', type='positive')
            else:
                diag_id, _fecha, duplicated = guardar_diagnostico(empresa_id, score, nivel, conclusion, rows)
                ui.notify('Ese diagnóstico ya estaba guardado; se reutilizó el corte existente.' if duplicated else 'Diagnóstico guardado correctamente.', type='positive')
            app.storage.user['edit_diag_id'] = None
            app.storage.user['duplicate_diag_id'] = None
            set_selection(empresa_id, diag_id)
            ui.navigate.to('/resultados')
        with ui.row().classes('w-full justify-end gap-3 mt-6'):
            ui.button('Cancelar', icon='close', on_click=lambda: ui.navigate.to('/historial')).props('outline')
            ui.button('Guardar diagnóstico', icon='save', on_click=save_diagnosis).props('unelevated color=primary')


@ui.page('/resultados')
def results_page() -> None:
    if not ensure_platform_access():
        return
    shell_container = shell('Resultados')
    empresa_id, diagnostico_id = current_selection()
    companies = company_options()
    if not empresa_id and companies:
        empresa_id = next(iter(companies.values()))
    diag_map = diagnosis_options(empresa_id)
    if not diagnostico_id and diag_map:
        diagnostico_id = next(iter(diag_map.values()))
    if diagnostico_id:
        set_selection(empresa_id, diagnostico_id)
    with shell_container:
        ui.label('Resultados').classes('ideas-kicker')
        ui.label('Lectura ejecutiva del diagnóstico seleccionado.').classes('text-3xl font-bold text-slate-900')
        ui.label('Unificá score global, lectura por eje y oportunidades prioritarias en una vista de decisión rápida.').classes('ideas-subtitle mb-4')
        with ui.card().classes('ideas-panel w-full'):
            with ui.row().classes('w-full gap-4'):
                company_select = ui.select(companies, value=empresa_id, label='Empresa').classes('col').props('outlined')
                diagnosis_select = ui.select(diag_map, value=diagnostico_id, label='Diagnóstico').classes('col').props('outlined')
        company_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, None), ui.navigate.to('/resultados')))
        diagnosis_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, int(diagnosis_select.value) if diagnosis_select.value else None), ui.navigate.to('/resultados')))
        selected = diagnosis_record(diagnostico_id)
        if not selected:
            ui.label('Todavía no hay un diagnóstico seleccionado para mostrar resultados.').classes('text-slate-500 mt-6')
            return
        responses = diagnosis_response_dicts(diagnostico_id)
        df_resp, eje_scores_df = build_eje_scores(responses)
        company = obtener_empresa_detalle(selected['empresa_id'])
        plan_df = build_plan(df_resp, eje_scores_df)
        score = round(float(selected['score']), 2)
        nivel = fix_text(selected['nivel'])
        focus_area = fix_text(eje_scores_df.sort_values('RESPUESTA').iloc[0]['EJE']) if not eje_scores_df.empty else 'Sin datos'
        ui.html(f'''<div class="ideas-result-banner mt-6"><div class="eyebrow">Resultado general</div><div class="headline">{selected['empresa']} · Nivel {nivel}</div><div class="support">{selected['fecha']} · {fix_text(obtener_mensaje_direccion(nivel))}</div></div>''')
        fig = go.Figure(go.Bar(x=eje_scores_df['RESPUESTA'], y=eje_scores_df['EJE'], orientation='h', marker_color='#1f7ed6', text=[f'{value:.2f}' for value in eje_scores_df['RESPUESTA']], textposition='outside'))
        fig.update_layout(height=430, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
        radar_base_labels = eje_scores_df['EJE'].tolist()
        radar_labels = [short_axis_label(label) for label in radar_base_labels]
        radar_values = eje_scores_df['RESPUESTA'].tolist()
        if radar_labels:
            radar_labels = radar_labels + [radar_labels[0]]
            radar_values = radar_values + [radar_values[0]]
        radar = go.Figure()
        radar.add_trace(
            go.Scatterpolar(
                r=radar_values,
                theta=radar_labels,
                fill='toself',
                line=dict(color='#0f8f61', width=3),
                fillcolor='rgba(15, 143, 97, 0.22)',
                name='Madurez por área',
            )
        )
        radar.update_layout(
            height=430,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[1, 4], tickvals=[1, 2, 3, 4], gridcolor='rgba(148,163,184,0.25)'),
                angularaxis=dict(gridcolor='rgba(148,163,184,0.18)', tickfont=dict(size=10)),
            ),
            showlegend=False,
        )
        gap_values = [max(0, 4 - float(value)) for value in eje_scores_df['RESPUESTA'].tolist()]
        gap_chart = go.Figure(
            go.Bar(
                x=gap_values,
                y=eje_scores_df['EJE'],
                orientation='h',
                marker_color='#f59e0b',
                text=[f'{value:.2f}' for value in gap_values],
                textposition='outside',
            )
        )
        gap_chart.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis=dict(range=[0, 4], title='Brecha a estándar 4'),
            yaxis=dict(autorange='reversed'),
        )
        score_distribution = pd.DataFrame({
            'Nivel': ['1', '2', '3', '4'],
            'Cantidad': [
                int((df_resp['RESPUESTA'] == 1).sum()) if not df_resp.empty else 0,
                int((df_resp['RESPUESTA'] == 2).sum()) if not df_resp.empty else 0,
                int((df_resp['RESPUESTA'] == 3).sum()) if not df_resp.empty else 0,
                int((df_resp['RESPUESTA'] == 4).sum()) if not df_resp.empty else 0,
            ],
        })
        distribution_chart = go.Figure(
            go.Bar(
                x=score_distribution['Nivel'],
                y=score_distribution['Cantidad'],
                marker_color=['#dc2626', '#f59e0b', '#38bdf8', '#16a34a'],
                text=score_distribution['Cantidad'],
                textposition='outside',
            )
        )
        distribution_chart.update_layout(
            height=360,
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            xaxis_title='Puntaje',
            yaxis_title='Cantidad de respuestas',
        )
        with ui.tabs().classes('w-full mt-6') as tabs:
            summary_tab = ui.tab('Resumen ejecutivo', icon='dashboard')
            plan_tab = ui.tab('Plan de acción', icon='task_alt')
        with ui.tab_panels(tabs, value=summary_tab).classes('w-full bg-transparent'):
            with ui.tab_panel(summary_tab).classes('px-0'):
                ui.html(f'''<div class="ideas-grid-3">{quick_card('Empresa', selected['empresa'], 'Corte seleccionado para lectura ejecutiva.')}{quick_card('Fecha del corte', selected['fecha'], 'Toma vigente dentro del historial registrado.')}{quick_card('Prioridad recomendada', fix_text(obtener_prioridad_recomendada(nivel)), 'Enfoque sugerido para dirección.')}</div>''')
                with ui.row().classes('w-full gap-4 mt-6'):
                    with ui.card().classes('ideas-panel col'):
                        ui.label('Performance por área').classes('ideas-section-title')
                        ui.label('Comparativo visual de madurez por eje para detectar fortalezas y focos de intervención.').classes('ideas-section-note')
                        ui.plotly(fig).classes('w-full')
                    with ui.card().classes('ideas-panel col'):
                        ui.label('Radar de brechas por área').classes('ideas-section-title')
                        ui.label('Vista sintética para observar equilibrio, amplitud de capacidades y gaps entre ejes.').classes('ideas-section-note')
                        ui.plotly(radar).classes('w-full')
                        legend_rows = [{'sigla': short_axis_label(label), 'area': label} for label in radar_base_labels]
                        ui.table(
                            columns=[
                                {'name': 'sigla', 'label': 'Etiqueta', 'field': 'sigla', 'align': 'left'},
                                {'name': 'area', 'label': 'Área completa', 'field': 'area', 'align': 'left'},
                            ],
                            rows=legend_rows,
                            pagination=6,
                        ).classes('w-full ideas-table mt-3')
                with ui.row().classes('w-full gap-4 mt-4'):
                    with ui.card().classes('ideas-panel col'):
                        ui.label('Brecha a estándar objetivo').classes('ideas-section-title')
                        ui.label('Muestra en formato ejecutivo cuánto le falta a cada eje para alcanzar un nivel 4 estandarizado.').classes('ideas-section-note')
                        ui.plotly(gap_chart).classes('w-full')
                    with ui.card().classes('ideas-panel col'):
                        ui.label('Distribución de respuestas').classes('ideas-section-title')
                        ui.label('Resume la concentración del diagnóstico por nivel de cumplimiento.').classes('ideas-section-note')
                        ui.plotly(distribution_chart).classes('w-full')
                with ui.row().classes('w-full gap-4 mt-4'):
                    with ui.card().classes('ideas-panel w-full'):
                        ui.label('Ficha ejecutiva').classes('ideas-section-title')
                        ui.label(f"Razón social: {fix_text(company.get('razon_social', selected['empresa'])) if company else selected['empresa']}").classes('text-slate-700')
                        ui.label(f"Ubicación: {fix_text(company.get('ubicacion', '')) if company else ''}").classes('text-slate-700')
                        ui.label(f"Rubro: {fix_text(company.get('rubro', '')) if company else ''}").classes('text-slate-700')
                        ui.label(f"Empleados: {company.get('cantidad_empleados', 0) if company else 0}").classes('text-slate-700')
                        ui.label(f"Certificaciones: {certifications_summary(company)}").classes('text-slate-700')
                        ui.separator().classes('my-3')
                        ui.label(fix_text(obtener_prioridad_recomendada(nivel))).classes('text-slate-800 font-medium')
            with ui.tab_panel(plan_tab).classes('px-0'):
                ui.label('Plan de acción sugerido').classes('ideas-section-title')
                ui.label('Incluye acciones prioritarias para respuestas de 2 o menos y oportunidades de mejora para respuestas de 3.').classes('ideas-section-note')
                ui.table(columns=[{'name': 'categoria', 'label': 'Categoría', 'field': 'categoria', 'align': 'left'}, {'name': 'area', 'label': 'Área', 'field': 'area', 'align': 'left'}, {'name': 'prioridad', 'label': 'Prioridad', 'field': 'prioridad', 'align': 'left'}, {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'}, {'name': 'plazo', 'label': 'Plazo', 'field': 'plazo', 'align': 'left'}, {'name': 'impacto', 'label': 'Impacto', 'field': 'impacto', 'align': 'left'}, {'name': 'accion', 'label': 'Acción sugerida', 'field': 'accion', 'align': 'left'}], rows=plan_df.to_dict('records'), pagination=10).classes('w-full ideas-card ideas-table p-3 mt-3')
        with ui.row().classes('w-full justify-end gap-3 mt-6'):
            ui.button('Editar diagnóstico', icon='edit', on_click=lambda: (start_edit(int(diagnostico_id), duplicate=False), ui.navigate.to('/diagnostico'))).props('outline')
            ui.button('Duplicar como nuevo', icon='content_copy', on_click=lambda: (start_edit(int(diagnostico_id), duplicate=True), ui.navigate.to('/diagnostico'))).props('unelevated color=primary')

@ui.page('/historial')
def history_page() -> None:
    if not ensure_platform_access():
        return
    shell_container = shell('Historial')
    rows = diagnosis_rows()
    app.storage.user['history_selected_id'] = None
    with shell_container:
        ui.label('Historial').classes('ideas-kicker')
        ui.label('Overview rápido de la base de diagnósticos.').classes('text-3xl font-bold text-slate-900')
        ui.label('Consultá cada corte, actuá sobre el registro y accedé a la información relevante sin ruido visual.').classes('ideas-subtitle mb-4')
        empresas_con_evolucion = len({row['empresa'] for row in rows if sum(1 for item in rows if item['empresa'] == row['empresa']) > 1})
        render_metrics(ui.row().classes('w-full'), [('Empresas registradas', str(len({row['empresa_id'] for row in rows})), 'Universo visible en la base consultiva.'), ('Diagnósticos visibles', str(len(rows)), 'Cortes disponibles para consulta o edición.'), ('Empresas con evolución', str(empresas_con_evolucion), 'Casos con más de un corte registrado.')])
        columns = [{'name': 'empresa', 'label': 'Empresa', 'field': 'empresa', 'align': 'left'}, {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'}, {'name': 'score', 'label': 'Score', 'field': 'score', 'align': 'right'}, {'name': 'nivel', 'label': 'Nivel', 'field': 'nivel', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}]
        table_rows = [{'id': row['id'], 'empresa_id': row['empresa_id'], 'empresa': row['empresa'], 'fecha': row['fecha'], 'score': f"{row['score']:.2f}", 'nivel': row['nivel'], 'acciones': ''} for row in rows]
        table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=10).classes('w-full ideas-card ideas-table p-3 mt-4')
        table.props('flat bordered')
        table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="visibility" color="primary" @click="$parent.$emit('open_resultados', props.row.id)" /><q-btn flat round dense icon="edit" color="secondary" @click="$parent.$emit('edit_diag', props.row.id)" /><q-btn flat round dense icon="content_copy" color="amber-8" @click="$parent.$emit('duplicate_diag', props.row.id)" /><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_diag', props.row.id)" /></div></q-td>''')
        detail_card = ui.card().classes('ideas-panel w-full mt-4')
        def extract_diag_id(args) -> int | None:
            if args is None:
                return None
            if isinstance(args, dict):
                if 'id' in args:
                    try:
                        return int(args['id'])
                    except Exception:
                        return None
                if 'row' in args:
                    return extract_diag_id(args['row'])
                return None
            if isinstance(args, (list, tuple)):
                for item in args:
                    diag_id = extract_diag_id(item)
                    if diag_id is not None:
                        return diag_id
                return None
            try:
                return int(args)
            except Exception:
                return None
        def render_detail(diag_id: int | None) -> None:
            detail_card.clear()
            diag = diagnosis_record(diag_id) if diag_id else None
            if not diag:
                with detail_card:
                    ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title')
                    ui.label('Haz click en una fila de la lista superior para visualizar aquí el resumen del diagnóstico y los datos de la empresa.').classes('text-slate-500')
                    ui.html(
                        '''<div class="ideas-grid-2" style="margin-top:18px;">
                        <div class="ideas-quick-card">
                            <div class="label">Ficha de empresa</div>
                            <div class="detail">Razón social: -</div>
                            <div class="detail">Ubicación: -</div>
                            <div class="detail">Rubro: -</div>
                            <div class="detail">Empleados: -</div>
                        </div>
                        <div class="ideas-quick-card">
                            <div class="label">Resumen consultivo</div>
                            <div class="detail">Puntos fuertes: -</div>
                            <div class="detail">Áreas débiles: -</div>
                            <div class="detail">Contacto: -</div>
                            <div class="detail">Certificaciones: -</div>
                        </div>
                        </div>'''
                    )
                return
            app.storage.user['history_selected_id'] = int(diag['id'])
            company = obtener_empresa_detalle(diag['empresa_id'])
            responses = diagnosis_response_dicts(diag['id'])
            df_resp = pd.DataFrame(responses)
            strengths = ', '.join(df_resp[df_resp['respuesta'] >= 3]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'
            weaknesses = ', '.join(df_resp[df_resp['respuesta'] <= 2]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'
            with detail_card:
                ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title')
                ui.label(f"{diag['empresa']} · {diag['fecha']}").classes('text-slate-500')
                ui.html(f'<div style="margin-top:12px;display:inline-flex;padding:10px 14px;border-radius:999px;font-weight:800;{diagnosis_badge_style(diag["nivel"])}">Nivel {diag["nivel"]} · Score {diag["score"]:.2f}</div>')
                ui.html(f'''<div class="ideas-grid-2" style="margin-top:18px;"><div class="ideas-quick-card"><div class="label">Ficha de empresa</div><div class="detail">Razón social: {fix_text(company.get('razon_social', diag['empresa'])) if company else diag['empresa']}</div><div class="detail">Ubicación: {fix_text(company.get('ubicacion', '')) if company else ''}</div><div class="detail">Rubro: {fix_text(company.get('rubro', '')) if company else ''}</div><div class="detail">Empleados: {company.get('cantidad_empleados', 0) if company else 0}</div></div><div class="ideas-quick-card"><div class="label">Resumen consultivo</div><div class="detail">Puntos fuertes: {fix_text(strengths)}</div><div class="detail">Áreas débiles: {fix_text(weaknesses)}</div><div class="detail">Contacto: {fix_text(company.get('contacto_nombre', '')) if company else ''}</div><div class="detail">Certificaciones: {certifications_summary(company)}</div></div></div>''')
        render_detail(None)
        table.on('rowClick', lambda event: render_detail(extract_diag_id(event.args)))
        table.on('open_resultados', lambda event: (set_selection(diagnosis_record(int(event.args))['empresa_id'], int(event.args)), ui.navigate.to('/resultados')) if diagnosis_record(int(event.args)) else ui.notify('No se encontró ese diagnóstico.', type='warning'))
        table.on('edit_diag', lambda event: (start_edit(int(event.args), duplicate=False), ui.navigate.to('/diagnostico')))
        table.on('duplicate_diag', lambda event: (start_edit(int(event.args), duplicate=True), ui.navigate.to('/diagnostico')))
        def confirm_delete(diag_id: int) -> None:
            diag = diagnosis_record(diag_id)
            if not diag:
                ui.notify('Ese diagnóstico ya no existe.', type='warning')
                return
            with ui.dialog() as dialog, ui.card().classes('p-5'):
                ui.label('Eliminar diagnóstico').classes('text-lg font-semibold')
                ui.label(f"Se eliminará {diag['empresa']} · {diag['fecha']} y también sus respuestas.").classes('text-slate-600')
                with ui.row().classes('w-full justify-end gap-2 mt-3'):
                    ui.button('Cancelar', on_click=dialog.close).props('flat')
                    ui.button('Eliminar', color='negative', on_click=lambda: (eliminar_diagnostico(diag_id), dialog.close(), ui.notify('Diagnóstico eliminado correctamente.', type='positive'), ui.navigate.to('/historial')))
            dialog.open()
        table.on('delete_diag', lambda event: confirm_delete(int(event.args)))

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
