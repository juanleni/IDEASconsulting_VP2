import json
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont
from st_aggrid import AgGrid, DataReturnMode, GridOptionsBuilder, GridUpdateMode, JsCode

from database import crear_base
from ideas_data import (
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
from ideas_utils import (
    construir_evidencia_numerica,
    html_safe,
    imagen_a_data_uri,
    limpiar_nombre_archivo,
    obtener_acciones_nivel,
    obtener_clase_badge,
    obtener_color_nivel,
    obtener_conclusion,
    obtener_delta_texto,
    obtener_imagen_inicio_path,
    obtener_logo_path,
    obtener_mensaje_direccion,
    obtener_nivel,
    obtener_prioridad_recomendada,
    obtener_plazo_sugerido,
    obtener_responsable_sugerido,
    obtener_impacto_sugerido,
    pdf_safe,
    valor_afirmativo,
)


# ---------------- CONFIG ----------------


LOGO_PATH = obtener_logo_path()
HOME_IMAGE_PATH = obtener_imagen_inicio_path()
LOGO_URI = imagen_a_data_uri(LOGO_PATH)
HOME_IMAGE_URI = imagen_a_data_uri(HOME_IMAGE_PATH)

st.set_page_config(
    page_title="IDEAS Consulting",
    page_icon=LOGO_PATH if LOGO_PATH else None,
    layout="wide",
)
crear_base()

st.markdown(
    """
    <style>
    :root {
        --ideas-ink: #0f172a;
        --ideas-text: #334155;
        --ideas-green: #0f8f61;
        --ideas-green-deep: #0a6b52;
        --ideas-blue: #1f7ed6;
        --ideas-amber: #e8a126;
        --ideas-surface: rgba(255, 255, 255, 0.82);
        --ideas-border: rgba(15, 23, 42, 0.08);
    }
    .stApp {
        background:
            radial-gradient(circle at top left, rgba(15, 143, 97, 0.08), transparent 24%),
            radial-gradient(circle at top right, rgba(232, 161, 38, 0.08), transparent 18%),
            linear-gradient(180deg, #f7fbf9 0%, #eef5f2 48%, #f6f8fb 100%);
    }
    html, body, [class*="css"] {
        font-family: Aptos, "Segoe UI Variable", "Segoe UI", "Helvetica Neue", sans-serif;
        color: var(--ideas-text);
    }
    h1, h2, h3 {
        color: var(--ideas-ink);
        letter-spacing: -0.02em;
    }
    [data-testid="stSidebar"] {
        background:
            radial-gradient(circle at top left, rgba(15, 143, 97, 0.10), transparent 28%),
            linear-gradient(180deg, rgba(249, 252, 251, 0.98) 0%, rgba(239, 246, 243, 0.98) 100%);
        border-right: 1px solid rgba(15, 23, 42, 0.06);
    }
    [data-testid="stSidebar"] > div:first-child {
        padding-top: 1.2rem;
    }
    .ideas-sidebar-brand {
        margin: 0 0 1.15rem -0.55rem;
        padding: 0;
    }
    .ideas-sidebar-brand img {
        display: block;
        width: 100%;
        max-width: 180px;
        height: auto;
    }
    .ideas-sidebar-caption {
        margin: 0.3rem 0 1.15rem 0;
        color: #4b5563;
        font-size: 0.85rem;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    [data-testid="stSidebar"] [data-testid="stRadio"] > div {
        gap: 0.5rem;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label {
        position: relative;
        border-radius: 18px;
        padding: 0.72rem 0.9rem 0.72rem 1rem;
        transition: background-color 140ms ease, border-color 140ms ease, box-shadow 140ms ease, transform 140ms ease;
        border: 1px solid transparent;
        background: rgba(255, 255, 255, 0.42);
        box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.45);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:hover {
        background: rgba(255, 255, 255, 0.8);
        border-color: rgba(15, 143, 97, 0.14);
        transform: translateX(1px);
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] > div:last-child {
        font-weight: 600;
        color: #1f2937;
        letter-spacing: -0.01em;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label[data-baseweb="radio"] > div:first-child {
        display: none !important;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label::before {
        content: "";
        position: absolute;
        left: 0.35rem;
        top: 0.5rem;
        bottom: 0.5rem;
        width: 4px;
        border-radius: 999px;
        background: transparent;
        transition: background-color 140ms ease;
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
        background: linear-gradient(135deg, rgba(15, 143, 97, 0.16) 0%, rgba(31, 126, 214, 0.10) 100%);
        border-color: rgba(15, 143, 97, 0.18);
        box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked)::before {
        background: linear-gradient(180deg, #0f8f61 0%, #1f7ed6 100%);
    }
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] p,
    [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) > div:last-child {
        color: #0f172a !important;
        font-weight: 700 !important;
    }
    .ideas-sidebar-divider {
        height: 1px;
        margin: 0.9rem 0 1rem 0;
        background: linear-gradient(90deg, rgba(15, 143, 97, 0.18), rgba(15, 23, 42, 0.03));
    }
    .ideas-sidebar-foot {
        margin-top: 1rem;
        padding: 0.95rem 1rem;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.62);
        border: 1px solid rgba(15, 23, 42, 0.06);
        box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
    }
    .ideas-sidebar-foot strong {
        display: block;
        color: #0f172a;
        margin-bottom: 0.2rem;
        font-size: 0.94rem;
    }
    .ideas-sidebar-foot span {
        color: #64748b;
        font-size: 0.84rem;
        line-height: 1.55;
    }
    [data-testid="stTextInputRootElement"] > div,
    [data-baseweb="select"] > div,
    .stTextArea textarea {
        border-radius: 16px !important;
        border: 1px solid rgba(15, 23, 42, 0.1) !important;
        background: rgba(255, 255, 255, 0.86) !important;
        box-shadow: 0 10px 22px rgba(15, 23, 42, 0.04) !important;
    }
    .stButton > button,
    .stDownloadButton > button {
        border-radius: 16px !important;
        border: 1px solid rgba(15, 143, 97, 0.18) !important;
        background: linear-gradient(135deg, #0f8f61 0%, #0c7659 100%) !important;
        color: #ffffff !important;
        font-weight: 700 !important;
        letter-spacing: 0.01em;
        box-shadow: 0 14px 28px rgba(15, 143, 97, 0.2) !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #1f7ed6 0%, #1663ab 100%) !important;
        border-color: rgba(31, 126, 214, 0.2) !important;
        box-shadow: 0 14px 28px rgba(31, 126, 214, 0.18) !important;
    }
    [data-testid="stMetric"] {
        background: rgba(255, 255, 255, 0.78);
        border: 1px solid rgba(15, 23, 42, 0.07);
        border-radius: 22px;
        padding: 1rem 1.15rem;
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stMetricLabel"] {
        color: #475569;
        font-weight: 600;
    }
    [data-testid="stMetricValue"] {
        color: #0f172a;
        letter-spacing: -0.03em;
    }
    .stAlert {
        border-radius: 18px;
    }
    .ideas-page-intro,
    .ideas-soft-panel,
    .ideas-mini-note,
    .ideas-score-card,
    .ideas-history-card,
    .ideas-question-card,
    .ideas-dashboard-hero,
    .ideas-visual-panel,
    .ideas-kpi-band {
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid rgba(15, 23, 42, 0.07);
        box-shadow: 0 18px 36px rgba(15, 23, 42, 0.06);
        backdrop-filter: blur(10px);
    }
    .ideas-page-intro {
        border-radius: 28px;
        padding: 1.6rem 1.75rem;
        margin-bottom: 1.35rem;
    }
    .ideas-page-intro span {
        display: inline-block;
        margin-bottom: 0.45rem;
        color: #0f8f61;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-size: 0.82rem;
    }
    .ideas-page-intro h1 {
        margin: 0;
        font-size: clamp(2rem, 3vw, 2.9rem);
        line-height: 1.05;
        letter-spacing: -0.03em;
    }
    .ideas-page-intro p {
        margin: 0.8rem 0 0 0;
        max-width: 52rem;
        color: #475569;
        line-height: 1.75;
        font-size: 1rem;
    }
    .ideas-soft-panel {
        border-radius: 24px;
        padding: 1.3rem 1.4rem;
        margin-bottom: 1rem;
    }
    .ideas-soft-panel h3,
    .ideas-soft-panel h4 {
        margin: 0 0 0.4rem 0;
        color: #0f172a;
        letter-spacing: -0.02em;
    }
    .ideas-soft-panel p {
        margin: 0;
        color: #475569;
        line-height: 1.7;
    }
    .ideas-mini-note {
        border-radius: 20px;
        padding: 1rem 1.1rem;
        margin: 0.35rem 0 1rem 0;
    }
    .ideas-mini-note strong {
        display: block;
        margin-bottom: 0.2rem;
        color: #0f172a;
    }
    .ideas-score-card {
        border-radius: 24px;
        padding: 1.35rem 1.4rem;
        margin-bottom: 1rem;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.92) 0%, rgba(245, 248, 252, 0.94) 100%);
        border: 1px solid rgba(148, 163, 184, 0.18);
    }
    .ideas-score-card .label {
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-size: 0.78rem;
        font-weight: 700;
    }
    .ideas-score-card .value {
        display: block;
        margin-top: 0.4rem;
        color: #0f172a;
        font-size: 2.3rem;
        line-height: 1;
        letter-spacing: -0.05em;
        font-weight: 800;
    }
    .ideas-score-card .detail {
        display: block;
        margin-top: 0.55rem;
        color: #475569;
        line-height: 1.6;
    }
    .ideas-dashboard-hero {
        border-radius: 30px;
        padding: 1.5rem 1.6rem;
        margin-bottom: 1rem;
        background:
            radial-gradient(circle at top right, rgba(96, 165, 250, 0.20), transparent 28%),
            linear-gradient(135deg, #0f172a 0%, #132238 52%, #1f3b61 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 26px 60px rgba(15, 23, 42, 0.18);
        color: #e2e8f0;
    }
    .ideas-dashboard-hero .eyebrow {
        display: inline-block;
        padding: 0.4rem 0.75rem;
        border-radius: 999px;
        background: rgba(255, 255, 255, 0.10);
        color: #bfdbfe;
        font-size: 0.78rem;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        font-weight: 700;
    }
    .ideas-dashboard-hero h2 {
        margin: 0.9rem 0 0.5rem 0;
        color: #f8fafc;
        font-size: clamp(1.8rem, 2.7vw, 2.8rem);
        line-height: 1.05;
        letter-spacing: -0.03em;
    }
    .ideas-dashboard-hero p {
        margin: 0;
        max-width: 48rem;
        color: rgba(226, 232, 240, 0.86);
        line-height: 1.7;
    }
    .ideas-kpi-band {
        border-radius: 24px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
        background:
            linear-gradient(135deg, rgba(255, 255, 255, 0.96) 0%, rgba(241, 245, 249, 0.98) 100%);
    }
    .ideas-kpi-band strong {
        display: block;
        color: #0f172a;
        margin-bottom: 0.2rem;
    }
    .ideas-kpi-band span {
        color: #64748b;
        line-height: 1.6;
        font-size: 0.94rem;
    }
    .ideas-visual-panel {
        border-radius: 28px;
        padding: 1.2rem 1.3rem;
        margin-bottom: 1rem;
        background:
            linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(244, 247, 251, 0.98) 100%);
    }
    .ideas-visual-panel h3 {
        margin: 0 0 0.25rem 0;
        color: #0f172a;
        font-size: 1.1rem;
        letter-spacing: -0.02em;
    }
    .ideas-visual-panel p {
        margin: 0 0 0.85rem 0;
        color: #64748b;
        line-height: 1.6;
        font-size: 0.94rem;
    }
    [data-testid="stTabs"] {
        margin-bottom: 1rem;
    }
    [data-testid="stTabs"] [role="tablist"] {
        gap: 0.65rem;
        background: rgba(255, 255, 255, 0.48);
        border: 1px solid rgba(148, 163, 184, 0.12);
        border-radius: 22px;
        padding: 0.45rem;
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
    }
    [data-testid="stTabs"] [role="tab"] {
        height: auto;
        border-radius: 16px;
        padding: 0.75rem 1rem;
        background: rgba(255, 255, 255, 0.72);
        border: 1px solid transparent;
        transition: transform 140ms ease, box-shadow 140ms ease, background-color 140ms ease;
    }
    [data-testid="stTabs"] [role="tab"]:hover {
        transform: translateY(-1px);
        box-shadow: 0 10px 22px rgba(15, 23, 42, 0.05);
        background: rgba(255, 255, 255, 0.95);
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, rgba(15, 143, 97, 0.14) 0%, rgba(31, 126, 214, 0.12) 100%);
        border-color: rgba(15, 143, 97, 0.18);
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
    }
    [data-testid="stTabs"] [role="tab"] p {
        color: #334155;
        font-weight: 700;
        letter-spacing: -0.01em;
    }
    [data-testid="stTabs"] [role="tab"][aria-selected="true"] p {
        color: #0f172a;
    }
    .ideas-subsection-title {
        margin: 0.4rem 0 0.75rem 0;
        color: #0f172a;
        font-size: 1.02rem;
        font-weight: 800;
        letter-spacing: -0.02em;
    }
    .ideas-quick-card {
        border-radius: 22px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.9rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.95) 0%, rgba(244,247,251,0.98) 100%);
        border: 1px solid rgba(148, 163, 184, 0.14);
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
    }
    .ideas-quick-card strong {
        display: block;
        margin-bottom: 0.25rem;
        color: #0f172a;
    }
    .ideas-quick-card span {
        color: #64748b;
        line-height: 1.6;
        font-size: 0.94rem;
    }
    .ideas-status-band {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1.15rem 1.25rem;
        margin-bottom: 1rem;
        border-radius: 24px;
        border: 1px solid rgba(148, 163, 184, 0.14);
        box-shadow: 0 16px 34px rgba(15, 23, 42, 0.06);
        background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(244,247,251,0.98) 100%);
    }
    .ideas-status-band.low {
        background: linear-gradient(135deg, rgba(255,244,242,0.98) 0%, rgba(254,226,226,0.9) 100%);
        border-color: rgba(220, 38, 38, 0.14);
    }
    .ideas-status-band.medium {
        background: linear-gradient(135deg, rgba(255,251,235,0.98) 0%, rgba(254,240,138,0.45) 100%);
        border-color: rgba(217, 119, 6, 0.16);
    }
    .ideas-status-band.high {
        background: linear-gradient(135deg, rgba(240,253,244,0.98) 0%, rgba(220,252,231,0.92) 100%);
        border-color: rgba(15, 143, 97, 0.16);
    }
    .ideas-status-band .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        color: #64748b;
        font-size: 0.78rem;
        font-weight: 800;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .ideas-status-band .eyebrow::before {
        content: "";
        width: 0.7rem;
        height: 0.7rem;
        border-radius: 999px;
        background: #94a3b8;
        box-shadow: 0 0 0 6px rgba(148, 163, 184, 0.16);
        flex: 0 0 auto;
    }
    .ideas-status-band.low .eyebrow::before {
        background: #dc2626;
        box-shadow: 0 0 0 6px rgba(220, 38, 38, 0.12);
    }
    .ideas-status-band.medium .eyebrow::before {
        background: #d97706;
        box-shadow: 0 0 0 6px rgba(217, 119, 6, 0.12);
    }
    .ideas-status-band.high .eyebrow::before {
        background: #0f8f61;
        box-shadow: 0 0 0 6px rgba(15, 143, 97, 0.12);
    }
    .ideas-status-band strong {
        display: block;
        margin-top: 0.28rem;
        color: #0f172a;
        font-size: clamp(1.15rem, 2vw, 1.45rem);
        font-weight: 800;
        letter-spacing: -0.03em;
    }
    .ideas-status-band p {
        margin: 0.32rem 0 0 0;
        color: #475569;
        line-height: 1.58;
        font-size: 0.95rem;
        max-width: 44rem;
    }
    .ideas-status-metric {
        flex: 0 0 auto;
        min-width: 150px;
        padding: 0.9rem 1rem;
        border-radius: 18px;
        background: rgba(255, 255, 255, 0.68);
        border: 1px solid rgba(255, 255, 255, 0.4);
        text-align: right;
    }
    .ideas-status-metric span {
        display: block;
        color: #64748b;
        font-size: 0.74rem;
        font-weight: 700;
        letter-spacing: 0.08em;
        text-transform: uppercase;
    }
    .ideas-status-metric strong {
        margin-top: 0.22rem;
        font-size: 2rem;
        line-height: 1;
    }
    .ideas-semaforo-head {
        margin: 0.3rem 0 0.55rem 0;
        padding: 0 0.35rem;
        color: #64748b;
        font-size: 0.76rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        font-weight: 700;
    }
    .ideas-semaforo-row {
        border-radius: 20px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.7rem;
        background: rgba(255, 255, 255, 0.88);
        border: 1px solid rgba(148, 163, 184, 0.12);
        box-shadow: 0 12px 24px rgba(15, 23, 42, 0.05);
    }
    .ideas-semaforo-row strong {
        color: #0f172a;
        font-size: 1rem;
    }
    .ideas-semaforo-row .muted {
        color: #64748b;
        font-size: 0.92rem;
    }
    .ideas-badge {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 108px;
        padding: 0.42rem 0.75rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
        letter-spacing: 0.01em;
    }
    .ideas-badge.alto {
        background: rgba(15, 143, 97, 0.12);
        color: #0f8f61;
    }
    .ideas-badge.medio {
        background: rgba(245, 158, 11, 0.14);
        color: #b45309;
    }
    .ideas-badge.bajo {
        background: rgba(220, 38, 38, 0.12);
        color: #b91c1c;
    }
    .ideas-delta {
        font-weight: 700;
    }
    .ideas-delta.up {
        color: #0f8f61;
    }
    .ideas-delta.down {
        color: #b91c1c;
    }
    .ideas-delta.flat {
        color: #64748b;
    }
    .ideas-history-card {
        border-radius: 22px;
        padding: 1rem 1.1rem;
        margin-bottom: 0.85rem;
    }
    .ideas-history-card .title {
        color: #0f172a;
        font-size: 1.02rem;
        font-weight: 700;
    }
    .ideas-history-card .meta {
        color: #64748b;
        font-size: 0.92rem;
    }
    .ideas-question-card {
        border-radius: 22px;
        padding: 1rem 1.1rem 0.7rem 1.1rem;
        margin-bottom: 0.9rem;
    }
    .ideas-question-card h4 {
        margin: 0 0 0.75rem 0;
        color: #0f172a;
        font-size: 1rem;
        letter-spacing: -0.01em;
        word-break: normal;
        overflow-wrap: normal;
        hyphens: none;
    }
    .ideas-score-guide {
        border-radius: 24px;
        padding: 1rem 1.1rem;
        margin-bottom: 1rem;
        background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(244,247,251,0.98) 100%);
        border: 1px solid rgba(148, 163, 184, 0.14);
        box-shadow: 0 14px 28px rgba(15, 23, 42, 0.05);
    }
    .ideas-score-guide-head {
        margin-bottom: 0.8rem;
    }
    .ideas-score-guide-head strong {
        display: block;
        color: #0f172a;
        font-size: 1rem;
        margin-bottom: 0.18rem;
    }
    .ideas-score-guide-head span {
        color: #64748b;
        font-size: 0.92rem;
        line-height: 1.55;
    }
    .ideas-score-grid {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 0.7rem;
    }
    .ideas-score-item {
        border-radius: 18px;
        padding: 0.9rem 0.95rem;
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.14);
    }
    .ideas-score-item .value {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 2rem;
        height: 2rem;
        margin-bottom: 0.5rem;
        border-radius: 999px;
        background: rgba(31, 126, 214, 0.10);
        color: #1f7ed6;
        font-weight: 800;
    }
    .ideas-score-item strong {
        display: block;
        color: #0f172a;
        font-size: 0.96rem;
        margin-bottom: 0.18rem;
    }
    .ideas-score-item span {
        color: #64748b;
        font-size: 0.86rem;
        line-height: 1.45;
    }
    .ideas-score-rule {
        margin-top: 0.75rem;
        color: #475569;
        font-size: 0.9rem;
        line-height: 1.55;
    }
    .ideas-score-inline {
        margin-top: 0.4rem;
        color: #64748b;
        font-size: 0.84rem;
        line-height: 1.45;
    }
    .ideas-edit-banner {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 1rem;
        padding: 1rem 1.15rem;
        margin-bottom: 1rem;
        border-radius: 24px;
        background: linear-gradient(135deg, rgba(15, 23, 42, 0.96) 0%, rgba(31, 126, 214, 0.90) 100%);
        border: 1px solid rgba(31, 126, 214, 0.16);
        box-shadow: 0 20px 40px rgba(15, 23, 42, 0.12);
        color: #eff6ff;
    }
    .ideas-edit-banner .eyebrow {
        display: inline-flex;
        align-items: center;
        gap: 0.45rem;
        font-size: 0.78rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #bfdbfe;
    }
    .ideas-edit-banner .eyebrow::before {
        content: "";
        width: 0.72rem;
        height: 0.72rem;
        border-radius: 999px;
        background: #f8fafc;
        box-shadow: 0 0 0 6px rgba(248, 250, 252, 0.12);
    }
    .ideas-edit-banner strong {
        display: block;
        margin-top: 0.18rem;
        color: #ffffff;
        font-size: 1.12rem;
        letter-spacing: -0.02em;
    }
    .ideas-edit-banner p {
        margin: 0.22rem 0 0 0;
        max-width: 48rem;
        color: rgba(239, 246, 255, 0.86);
        line-height: 1.58;
        font-size: 0.94rem;
    }
    .ideas-edit-banner .meta {
        flex: 0 0 auto;
        text-align: right;
        color: #dbeafe;
        font-size: 0.86rem;
        line-height: 1.5;
    }
    @media (max-width: 1100px) {
        .ideas-score-grid {
            grid-template-columns: repeat(2, minmax(0, 1fr));
        }
    }
    .block-container {
        padding-top: 2rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# ---------------- FUNCIONES ----------------

def _legacy_obtener_mensaje_direccion(nivel: str) -> str:
    if nivel == "Bajo":
        return "La prioridad de direccion debe centrarse en estabilizar la operacion, definir responsables y establecer un plan de accion de corto plazo."
    if nivel == "Medio":
        return "La direccion cuenta con una base sobre la cual consolidar procesos, cerrar brechas y acelerar mejoras con seguimiento ejecutivo."
    return "La direccion puede orientar el esfuerzo hacia optimizacion, escalabilidad y captura de eficiencias adicionales sin perder disciplina de gestion."


def _legacy_obtener_prioridad_recomendada(nivel: str) -> str:
    if nivel == "Bajo":
        return "Intervencion prioritaria"
    if nivel == "Medio":
        return "Consolidacion y mejora"
    return "Optimizacion y escalado"


def _legacy_obtener_acciones_nivel(nivel: str) -> list[str]:
    if nivel == "Bajo":
        return [
            "Definir un plan de choque con responsables y plazos de ejecucion.",
            "Formalizar controles minimos y evidencia de seguimiento.",
            "Revisar procesos criticos con foco en continuidad operativa.",
        ]
    if nivel == "Medio":
        return [
            "Consolidar estandares operativos y rituales de seguimiento.",
            "Priorizar las brechas con mayor impacto en eficiencia y control.",
            "Monitorear avances con indicadores de gestion simples y frecuentes.",
        ]
    return [
        "Profundizar automatizacion, analitica y consistencia de gestion.",
        "Escalar buenas practicas entre areas y equipos clave.",
        "Alinear las mejoras con objetivos de crecimiento y rentabilidad.",
    ]


@st.cache_data(show_spinner=False)
def _legacy_leer_diagnostico_excel() -> pd.DataFrame:
    ruta = "Data/diagnostico.xlsx"

    if not os.path.exists(ruta):
        raise FileNotFoundError(
            "No se encontró el archivo Data/diagnostico.xlsx"
        )

    # Intenta hoja DIAGNOSTICO; si no existe, toma la primera
    xls = pd.ExcelFile(ruta)
    sheet_name = "DIAGNOSTICO" if "DIAGNOSTICO" in xls.sheet_names else xls.sheet_names[0]

    df = pd.read_excel(ruta, sheet_name=sheet_name)

    # Normalizar nombres de columnas
    df.columns = [str(col).strip().upper() for col in df.columns]

    if "EJE" not in df.columns or "PREGUNTA" not in df.columns:
        raise ValueError(
            f"El Excel debe tener columnas EJE y PREGUNTA. Columnas detectadas: {list(df.columns)}"
        )

    df["EJE"] = df["EJE"].astype(str).str.strip()
    df["PREGUNTA"] = df["PREGUNTA"].astype(str).str.strip()

    df = df[(df["EJE"] != "") & (df["PREGUNTA"] != "")]
    df = df.dropna(subset=["EJE", "PREGUNTA"])

    return df


def _legacy_pdf_safe(texto: str | None) -> str:
    if texto is None:
        return ""

    reemplazos = {
        "â€¢": "-",
        "âš ï¸": "-",
        "âš ": "-",
        "ðŸ”´": "",
        "ðŸŸ¡": "",
        "ðŸŸ¢": "",
        "â€œ": '"',
        "â€": '"',
        "â€™": "'",
        "â€“": "-",
        "â€”": "-",
        "\xa0": " ",
    }
    limpio = str(texto)
    for origen, destino in reemplazos.items():
        limpio = limpio.replace(origen, destino)
    return limpio.encode("latin-1", "replace").decode("latin-1")


def _legacy_valor_afirmativo(valor) -> bool:
    if valor is None:
        return False
    normalizado = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii").strip().lower()
    return normalizado in {"si", "s", "yes", "y", "true", "1"}


def _legacy_html_safe(texto) -> str:
    return html.escape("" if texto is None else str(texto))


def _legacy_limpiar_nombre_archivo(nombre: str) -> str:
    permitido = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in nombre.strip())
    while "__" in permitido:
        permitido = permitido.replace("__", "_")
    return permitido.strip("_") or "reporte"


def _legacy_obtener_color_nivel(nivel: str) -> tuple[int, int, int]:
    if nivel == "Bajo":
        return (193, 39, 45)
    if nivel == "Medio":
        return (232, 161, 38)
    return (15, 143, 97)


def cargar_fuente_pil(size: int, bold: bool = False):
    candidatos = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"] if bold else ["arial.ttf", "segoeui.ttf", "calibri.ttf"]
    for fuente in candidatos:
        try:
            return ImageFont.truetype(fuente, size)
        except OSError:
            continue
    return ImageFont.load_default()


def partir_texto_pil(draw: ImageDraw.ImageDraw, texto: str, fuente, ancho_max: int) -> list[str]:
    palabras = texto.split()
    if not palabras:
        return [""]

    lineas = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        intento = f"{actual} {palabra}"
        if draw.textlength(intento, font=fuente) <= ancho_max:
            actual = intento
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def crear_grafico_score(score: float, nivel: str, empresa: str, ruta_salida: str) -> str:
    ancho, alto = 980, 620
    img = Image.new("RGB", (ancho, alto), (245, 248, 250))
    draw = ImageDraw.Draw(img)

    verde = (15, 143, 97)
    azul = (31, 126, 214)
    ambar = (232, 161, 38)
    gris = (226, 232, 240)
    tinta = (15, 23, 42)
    suave = (71, 85, 105)
    color_nivel = obtener_color_nivel(nivel)

    draw.rounded_rectangle((20, 20, ancho - 20, alto - 20), radius=36, fill=(255, 255, 255), outline=(227, 233, 239), width=2)
    draw.rounded_rectangle((46, 44, ancho - 46, 120), radius=24, fill=(244, 250, 247))
    draw.text((74, 66), "Resumen de Madurez", font=cargar_fuente_pil(36, bold=True), fill=verde)
    draw.text((74, 104), empresa[:42], font=cargar_fuente_pil(22), fill=suave)

    centro = (285, 335)
    radio = 138
    grosor = 32
    bbox = (centro[0] - radio, centro[1] - radio, centro[0] + radio, centro[1] + radio)
    draw.arc(bbox, start=135, end=405, fill=gris, width=grosor)
    avance = 135 + int((max(1, min(score, 4)) - 1) / 3 * 270)
    draw.arc(bbox, start=135, end=avance, fill=color_nivel, width=grosor)
    draw.text((215, 292), f"{score:.2f}", font=cargar_fuente_pil(58, bold=True), fill=tinta)
    draw.text((229, 355), "sobre 4.00", font=cargar_fuente_pil(22), fill=suave)

    draw.text((510, 180), "Nivel ejecutivo", font=cargar_fuente_pil(22, bold=True), fill=suave)
    draw.text((510, 216), nivel, font=cargar_fuente_pil(42, bold=True), fill=color_nivel)
    draw.text((510, 288), "Lectura", font=cargar_fuente_pil(22, bold=True), fill=suave)

    descripcion = obtener_mensaje_direccion(nivel)
    y = 324
    for linea in partir_texto_pil(draw, descripcion, cargar_fuente_pil(24), 360):
        draw.text((510, y), linea, font=cargar_fuente_pil(24), fill=tinta)
        y += 34

    draw.rounded_rectangle((510, 430, 882, 500), radius=20, fill=(245, 248, 250))
    draw.text((538, 452), obtener_prioridad_recomendada(nivel), font=cargar_fuente_pil(22, bold=True), fill=azul)
    draw.rounded_rectangle((74, 486, 290, 534), radius=18, fill=(240, 249, 244))
    draw.text((96, 500), "Escala: 1 = inicial | 4 = maduro", font=cargar_fuente_pil(20), fill=verde)

    img.save(ruta_salida)
    return ruta_salida


def crear_grafico_barras_ejes(eje_scores: dict, ruta_salida: str) -> str:
    items = sorted(eje_scores.items(), key=lambda item: item[1], reverse=True)[:8]
    filas = max(len(items), 1)
    ancho = 1400
    alto = max(760, 250 + filas * 76)

    img = Image.new("RGB", (ancho, alto), (245, 248, 250))
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle((20, 20, ancho - 20, alto - 20), radius=36, fill=(255, 255, 255), outline=(227, 233, 239), width=2)

    tinta = (15, 23, 42)
    suave = (71, 85, 105)
    verde = (15, 143, 97)
    azul = (31, 126, 214)
    gris = (226, 232, 240)

    draw.text((60, 48), "Performance por Area", font=cargar_fuente_pil(36, bold=True), fill=tinta)
    draw.text((60, 94), "Promedio de respuesta por eje sobre una escala de 1 a 4.", font=cargar_fuente_pil(22), fill=suave)

    base_y = 180
    barra_x = 420
    barra_ancho = 840
    row_gap = max(70, min(84, int((alto - 260) / filas)))
    for idx, (eje, valor) in enumerate(items):
        y = base_y + idx * row_gap
        draw.text((60, y + 6), eje[:28], font=cargar_fuente_pil(22, bold=True), fill=tinta)
        draw.rounded_rectangle((barra_x, y, barra_x + barra_ancho, y + 28), radius=14, fill=gris)
        avance = int(barra_ancho * (max(1, min(valor, 4)) / 4))
        fill = verde if valor >= 3 else azul if valor >= 2 else (232, 161, 38)
        draw.rounded_rectangle((barra_x, y, barra_x + avance, y + 28), radius=14, fill=fill)
        draw.text((barra_x + barra_ancho + 22, y + 1), f"{valor:.2f}", font=cargar_fuente_pil(22, bold=True), fill=tinta)

    img.save(ruta_salida)
    return ruta_salida


def pdf_wrap_lines(pdf: FPDF, texto: str, ancho: float) -> list[str]:
    palabras = pdf_safe(texto).split()
    if not palabras:
        return [""]

    lineas = []
    actual = palabras[0]
    for palabra in palabras[1:]:
        intento = f"{actual} {palabra}"
        if pdf.get_string_width(intento) <= ancho:
            actual = intento
        else:
            lineas.append(actual)
            actual = palabra
    lineas.append(actual)
    return lineas


def pdf_image_height(ruta: str, ancho_pdf: float) -> float:
    with Image.open(ruta) as img:
        ancho_px, alto_px = img.size
    return ancho_pdf * (alto_px / ancho_px)


def pdf_text_block_height(pdf: FPDF, texto: str, ancho: float, line_h: float = 5.2) -> float:
    return len(pdf_wrap_lines(pdf, texto, ancho)) * line_h


def pdf_clip_lines(pdf: FPDF, texto: str, ancho: float, max_lines: int) -> list[str]:
    lineas = pdf_wrap_lines(pdf, texto, ancho)
    if len(lineas) <= max_lines:
        return lineas
    recortadas = lineas[:max_lines]
    ultima = recortadas[-1]
    while pdf.get_string_width(f"{ultima}...") > ancho and len(ultima) > 3:
        ultima = ultima[:-1]
    recortadas[-1] = f"{ultima}..."
    return recortadas


def pdf_draw_clipped_text(pdf: FPDF, x: float, y: float, ancho: float, texto: str, max_lines: int, line_h: float = 4.8, font_style: str = "", font_size: int = 10, color: tuple[int, int, int] = (71, 85, 105), bullet: bool = False) -> float:
    pdf.set_font("Arial", font_style, font_size)
    pdf.set_text_color(*color)
    lineas = pdf_clip_lines(pdf, f"- {texto}" if bullet else texto, ancho, max_lines)
    y_actual = y
    for linea in lineas:
        pdf.set_xy(x, y_actual)
        pdf.cell(ancho, line_h, pdf_safe(linea), ln=False)
        y_actual += line_h
    return y_actual


def pdf_metric_card(pdf: FPDF, x: float, y: float, w: float, h: float, etiqueta: str, valor: str, detalle: str, color: tuple[int, int, int]):
    pdf.set_xy(x, y)
    pdf.set_fill_color(250, 252, 251)
    pdf.set_draw_color(228, 233, 239)
    pdf.rect(x, y, w, h, style="FD")
    pdf.set_xy(x + 5, y + 5)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(w - 10, 4, pdf_safe(etiqueta.upper()), ln=True)
    pdf.set_x(x + 5)
    pdf.set_font("Arial", "B", 22)
    pdf.set_text_color(*color)
    pdf.cell(w - 10, 11, pdf_safe(valor), ln=True)
    pdf.set_x(x + 5)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(w - 10, 4.5, pdf_safe(detalle))


def pdf_footer(pdf: FPDF, pagina: int):
    pdf.set_draw_color(226, 232, 240)
    pdf.line(14, 286, 196, 286)
    pdf.set_xy(14, 288)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(120, 4, pdf_safe("IDEAS Consulting | Reporte Ejecutivo"), ln=0)
    pdf.cell(62, 4, pdf_safe(f"Pagina {pagina}"), ln=1, align="R")


def generar_pdf_ejecutivo(nombre_empresa, fecha, score, nivel, conclusion, eje_scores, criticas, empresa_info=None):
    os.makedirs("reportes", exist_ok=True)
    tmp_dir = os.path.join("reportes", "tmp")
    os.makedirs(tmp_dir, exist_ok=True)

    slug = limpiar_nombre_archivo(nombre_empresa)
    score_chart_path = os.path.join(tmp_dir, f"{slug}_score.png")
    bars_chart_path = os.path.join(tmp_dir, f"{slug}_areas.png")
    crear_grafico_score(score, nivel, nombre_empresa, score_chart_path)
    crear_grafico_barras_ejes(eje_scores, bars_chart_path)

    color_nivel = obtener_color_nivel(nivel)
    mensaje_direccion = obtener_mensaje_direccion(nivel)
    acciones_recomendadas = obtener_acciones_nivel(nivel)
    prioridad_recomendada = obtener_prioridad_recomendada(nivel)
    nombre_archivo = os.path.join("reportes", f"Reporte_Ejecutivo_{slug}.pdf")
    empresa_info = empresa_info or {}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    def draw_page_header(page_title: str, page_subtitle: str = ""):
        pdf.set_fill_color(15, 23, 42)
        pdf.rect(0, 0, 210, 16, "F")
        pdf.set_fill_color(31, 126, 214)
        pdf.rect(148, 0, 62, 16, "F")
        if LOGO_PATH and LOGO_PATH.lower().endswith((".png", ".jpg", ".jpeg")):
            pdf.image(LOGO_PATH, x=14, y=22, w=28)
        pdf.set_xy(46, 22)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(15, 143, 97)
        pdf.cell(120, 5, "IDEAS CONSULTING", ln=True)
        pdf.set_x(46)
        pdf.set_font("Arial", "B", 19)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(145, 8, pdf_safe(page_title), ln=True)
        if page_subtitle:
            pdf.set_x(46)
            pdf.set_font("Arial", "", 9)
            pdf.set_text_color(100, 116, 139)
            pdf.multi_cell(140, 4.6, pdf_safe(page_subtitle))

    def draw_box(x: float, y: float, w: float, h: float, title: str, fill=(245, 248, 252)):
        pdf.set_fill_color(*fill)
        pdf.set_draw_color(228, 233, 239)
        pdf.rect(x, y, w, h, "FD")
        pdf.set_xy(x + 5, y + 5)
        pdf.set_font("Arial", "B", 11)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(w - 10, 5, pdf_safe(title), ln=True)

    certificaciones = []
    if valor_afirmativo(empresa_info.get("cert_iso_9001")):
        certificaciones.append("ISO 9001")
    if valor_afirmativo(empresa_info.get("cert_iso_14001")):
        certificaciones.append("ISO 14001")
    if valor_afirmativo(empresa_info.get("cert_iso_45001")):
        certificaciones.append("ISO 45001")
    if valor_afirmativo(empresa_info.get("cert_iatf")):
        certificaciones.append("IATF")

    ficha_items = []
    if empresa_info.get("ubicacion"):
        ficha_items.append(f"Ubicacion: {empresa_info['ubicacion']}")
    if empresa_info.get("rubro"):
        ficha_items.append(f"Rubro: {empresa_info['rubro']}")
    if empresa_info.get("cantidad_empleados") not in (None, ""):
        ficha_items.append(f"Empleados: {empresa_info['cantidad_empleados']}")
    contacto_resumen = " | ".join(
        [valor for valor in [
            empresa_info.get("contacto_nombre"),
            empresa_info.get("contacto_posicion"),
            empresa_info.get("contacto_correo"),
            empresa_info.get("contacto_telefono"),
        ] if valor]
    )
    if contacto_resumen:
        ficha_items.append(f"Contacto: {contacto_resumen}")
    if certificaciones:
        ficha_items.append(f"Certificaciones: {', '.join(certificaciones)}")

    mensajes = [
        f"Nivel general observado: {nivel}.",
        f"Score consolidado: {score:.2f} sobre 4.00.",
        f"Cantidad de ejes evaluados: {len(eje_scores)}.",
        mensaje_direccion,
    ]
    criticas_textos = criticas[:4] if criticas else ["No se detectaron desviaciones criticas para este corte."]
    rows = sorted(eje_scores.items(), key=lambda item: item[1])[:10]

    pdf.add_page()
    draw_page_header("Reporte Ejecutivo de Diagnostico", "Resumen de direccion en formato compacto de 3 paginas.")
    info_y = 52
    pdf.set_fill_color(243, 247, 251)
    pdf.set_draw_color(228, 233, 239)
    pdf.rect(14, info_y, 182, 22, "FD")
    col_x = [20, 90, 146]
    col_w = [64, 48, 34]
    pdf.set_xy(col_x[0], info_y + 4)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(col_w[0], 5, pdf_safe("Empresa"))
    pdf.set_xy(col_x[1], info_y + 4)
    pdf.cell(col_w[1], 5, pdf_safe("Fecha"))
    pdf.set_xy(col_x[2], info_y + 4)
    pdf.cell(col_w[2], 5, pdf_safe("Nivel"))
    pdf_draw_clipped_text(pdf, col_x[0], info_y + 10, col_w[0], nombre_empresa, 2, line_h=4.8, font_style="B", font_size=10, color=(15, 23, 42))
    pdf_draw_clipped_text(pdf, col_x[1], info_y + 10, col_w[1], fecha, 2, line_h=4.8, font_size=9, color=(15, 23, 42))
    pdf.set_xy(col_x[2], info_y + 10)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(*color_nivel)
    pdf.cell(col_w[2], 5, pdf_safe(nivel))

    draw_box(14, 80, 182, 34, "Resumen ejecutivo")
    pdf_draw_clipped_text(pdf, 20, 91, 170, conclusion, 4, line_h=5.4, font_size=10, color=(51, 65, 85))
    pdf.set_xy(20, 108)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*color_nivel)
    pdf.cell(100, 4, pdf_safe(prioridad_recomendada), ln=False)

    pdf_metric_card(pdf, 14, 120, 56, 26, "Score global", f"{score:.2f}", "Promedio consolidado.", (15, 23, 42))
    pdf_metric_card(pdf, 77, 120, 56, 26, "Nivel", nivel, "Lectura de madurez.", color_nivel)
    pdf_metric_card(pdf, 140, 120, 56, 26, "Oportunidades", str(len(criticas)), "Puntos prioritarios.", (31, 126, 214))

    draw_box(14, 152, 182, 38, "Ficha corporativa")
    y_ficha = 163
    for item in ficha_items[:5]:
        y_ficha = pdf_draw_clipped_text(pdf, 20, y_ficha, 170, item, 1, line_h=4.8, font_size=9) + 1.2

    pdf.image(score_chart_path, x=49, y=194, w=112)
    pdf_footer(pdf, 1)

    pdf.add_page()
    draw_page_header("Lecturas para direccion", "Mensajes clave y comparativo visual para una lectura de liderazgo.")
    draw_box(14, 50, 88, 52, "Mensajes clave")
    y_msg = 61
    for mensaje in mensajes[:4]:
        y_msg = pdf_draw_clipped_text(pdf, 20, y_msg, 76, mensaje, 2, line_h=4.4, font_size=9, bullet=True) + 1

    draw_box(108, 50, 88, 52, "Oportunidades clave")
    y_op = 61
    for item in criticas_textos[:4]:
        y_op = pdf_draw_clipped_text(pdf, 114, y_op, 76, item, 2, line_h=4.4, font_size=9, bullet=True) + 1

    draw_box(14, 108, 182, 10, "Performance por area")
    pdf.set_xy(20, 118)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(100, 116, 139)
    pdf.cell(160, 4, pdf_safe("Comparativo visual de madurez por eje para detectar fortalezas y prioridades."), ln=True)
    bars_h = pdf_image_height(bars_chart_path, 182)
    image_y = 126 + max(0, (134 - bars_h) / 2)
    pdf.image(bars_chart_path, x=14, y=image_y, w=182)
    pdf_footer(pdf, 2)

    pdf.add_page()
    draw_page_header("Detalle ejecutivo por area", "Resumen compacto de madurez, prioridad y acciones recomendadas.")
    pdf.set_xy(14, 50)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(92, 8, pdf_safe("Area"), border=0, ln=0, fill=True)
    pdf.cell(28, 8, pdf_safe("Score"), border=0, ln=0, align="C", fill=True)
    pdf.cell(34, 8, pdf_safe("Nivel"), border=0, ln=0, align="C", fill=True)
    pdf.cell(32, 8, pdf_safe("Prioridad"), border=0, ln=1, align="C", fill=True)
    pdf.set_font("Arial", "", 10)
    row_h = max(8, min(14, round(88 / max(len(rows), 1), 1)))
    for eje, valor in rows:
        nivel_eje = obtener_nivel(valor)
        prioridad = "Alta" if valor < 2 else "Media" if valor < 3 else "Control"
        color_fila = (250, 252, 251) if prioridad == "Control" else (255, 249, 235) if prioridad == "Media" else (254, 242, 242)
        pdf.set_fill_color(*color_fila)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(92, row_h, pdf_safe(eje), border=0, ln=0, fill=True)
        pdf.cell(28, row_h, pdf_safe(f"{valor:.2f}"), border=0, ln=0, align="C", fill=True)
        pdf.cell(34, row_h, pdf_safe(nivel_eje), border=0, ln=0, align="C", fill=True)
        pdf.cell(32, row_h, pdf_safe(prioridad), border=0, ln=1, align="C", fill=True)

    recomendaciones_y = 58 + row_h * len(rows) + 12
    draw_box(14, recomendaciones_y, 182, 54, "Recomendaciones para direccion")
    y_acc = recomendaciones_y + 11
    for accion in acciones_recomendadas[:3]:
        y_acc = pdf_draw_clipped_text(pdf, 20, y_acc, 170, accion, 2, line_h=4.8, font_size=10, bullet=True) + 1

    cierre_y = recomendaciones_y + 60
    draw_box(14, cierre_y, 182, 24, "Cierre ejecutivo")
    pdf_draw_clipped_text(pdf, 20, cierre_y + 11, 170, "Este documento resume la situacion actual de la organizacion para direccion. El detalle operativo y evidencial puede desarrollarse en un informe complementario.", 2, line_h=4.8, font_size=9)
    pdf_footer(pdf, 3)

    pdf.output(nombre_archivo)
    return nombre_archivo


def construir_dataframe_ejes(respuestas: list[tuple]) -> pd.DataFrame:
    df_resp = pd.DataFrame(
        respuestas,
        columns=["EJE", "PREGUNTA", "RESPUESTA", "EVIDENCIA", "OBSERVACION"]
    )
    eje_scores_df = df_resp.groupby("EJE", dropna=True)["RESPUESTA"].mean().reset_index()
    return df_resp, eje_scores_df


@st.cache_data(show_spinner=False)
def leer_criterios_puntaje() -> tuple[list[dict], str]:
    ruta = "Data/diagnostico.xlsx"
    criterios_default = [
        {"escala": 1, "nivel": "Inicial", "resumen": "Existe de forma informal o depende de personas."},
        {"escala": 2, "nivel": "Parcial", "resumen": "Está definido, pero se aplica con inconsistencias."},
        {"escala": 3, "nivel": "Implementado", "resumen": "Se aplica regularmente con evidencia disponible."},
        {"escala": 4, "nivel": "Estandarizado", "resumen": "Está sistematizado, controlado y en mejora continua."},
    ]
    regla_default = "Si la empresa dice que lo hace pero no muestra evidencia, no debería superar 2 puntos."

    if not os.path.exists(ruta):
        return criterios_default, regla_default

    try:
        criterios_df = pd.read_excel(ruta, sheet_name="CRITERIOS DE EVALUACION")
        criterios_df.columns = [str(col).strip().upper() for col in criterios_df.columns]
        criterios_df = criterios_df[criterios_df["ESCALA"].isin([1, 2, 3, 4])].copy()
        criterios_df["ESCALA"] = criterios_df["ESCALA"].astype(int)

        criterios = []
        for _, row in criterios_df.iterrows():
            criterios.append(
                {
                    "escala": int(row["ESCALA"]),
                    "nivel": str(row.get("NIVEL", "")).strip(),
                    "resumen": str(row.get("DESCRIPCION GENERAL", "")).strip(),
                }
            )

        instrucciones_df = pd.read_excel(ruta, sheet_name="INSTRUCCIONES", header=None)
        regla = regla_default
        for _, row in instrucciones_df.iterrows():
            if len(row) > 1 and str(row.iloc[0]).strip().lower() == "regla de evidencia":
                valor = str(row.iloc[1]).strip()
                if valor and valor.lower() != "nan":
                    regla = valor
                break

        if criterios:
            return criterios, regla
    except Exception:
        pass

    return criterios_default, regla_default


def resumen_puntaje_corto(escala: int, criterios: list[dict]) -> str:
    resumenes_breves = {
        1: "Inicial, sin sistemática",
        2: "Parcial, con brechas",
        3: "Implementado y controlado",
        4: "Estandarizado, sin desvíos",
    }
    mapa = {
        item["escala"]: f'{item["escala"]} - {resumenes_breves.get(item["escala"], item["nivel"])}'
        for item in criterios
    }
    return mapa.get(escala, str(escala))


def firma_borrador_diagnostico(empresa_id: int | None, respuestas_guardar: list[dict]) -> str:
    payload = {
        "empresa_id": empresa_id,
        "respuestas": [
            {
                "eje": str(item.get("eje", "")).strip(),
                "pregunta": str(item.get("pregunta", "")).strip(),
                "respuesta": int(item.get("respuesta", 0)),
                "evidencia": str(item.get("evidencia", "")).strip(),
                "observacion": str(item.get("observacion", "")).strip(),
            }
            for item in respuestas_guardar
        ],
    }
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def limpiar_borrador_diagnostico() -> None:
    prefijos = ("resp_", "cant_evid_", "evid_", "obs_")
    claves_borrar = [
        key for key in list(st.session_state.keys())
        if key.startswith(prefijos) or key == "diag_empresa"
    ]
    for key in claves_borrar:
        del st.session_state[key]
    st.session_state["diag_draft_dirty"] = False
    st.session_state["diag_draft_empresa_nombre"] = ""
    st.session_state["diag_left_unsaved_notice"] = False
    st.session_state["diag_last_saved_signature"] = None
    st.session_state["diag_editing_id"] = None
    st.session_state["diag_edit_pref_id"] = None
    st.session_state["diag_edit_pref_empresa"] = None
    st.session_state["diag_duplicate_pref_id"] = None
    st.session_state["diag_duplicate_pref_empresa"] = None
    st.session_state["diag_edit_loaded_id"] = None


def descomponer_evidencia_numerica(evidencia: str) -> list[str]:
    texto = str(evidencia or "").strip()
    if not texto:
        return []
    return [item.strip() for item in texto.split(",") if item.strip()]


def precargar_diagnostico_en_formulario(df: pd.DataFrame, diagnostico_id: int, empresa_nombre: str) -> None:
    respuestas = obtener_respuestas_diagnostico(diagnostico_id)
    respuestas_guardar = []
    mapa_respuestas = {
        (str(eje).strip(), str(pregunta).strip()): {
            "respuesta": int(respuesta),
            "evidencia": str(evidencia or "").strip(),
            "observacion": str(observacion or "").strip(),
        }
        for eje, pregunta, respuesta, evidencia, observacion in respuestas
    }
    for i, row in df.iterrows():
        eje = str(row["EJE"]).strip()
        pregunta = str(row["PREGUNTA"]).strip()
        valores = mapa_respuestas.get((eje, pregunta), {})
        evidencia_items = descomponer_evidencia_numerica(valores.get("evidencia", ""))
        if not evidencia_items:
            evidencia_items = [""]
        st.session_state[f"resp_{eje}_{i}"] = int(valores.get("respuesta", 1))
        st.session_state[f"cant_evid_{eje}_{i}"] = max(1, min(5, len(evidencia_items)))
        for nro in range(1, 6):
            st.session_state[f"evid_{eje}_{i}_{nro}"] = evidencia_items[nro - 1] if nro <= len(evidencia_items) else ""
        st.session_state[f"obs_{eje}_{i}"] = valores.get("observacion", "")
        respuestas_guardar.append(
            {
                "eje": eje,
                "pregunta": pregunta,
                "respuesta": int(valores.get("respuesta", 1)),
                "evidencia": valores.get("evidencia", ""),
                "observacion": valores.get("observacion", ""),
            }
        )
    empresa_id = None
    empresas = obtener_empresas()
    empresa_dict = {nombre: eid for eid, nombre in empresas}
    if empresa_nombre in empresa_dict:
        empresa_id = empresa_dict[empresa_nombre]
    st.session_state["diag_last_saved_signature"] = firma_borrador_diagnostico(empresa_id, respuestas_guardar)
    st.session_state["diag_draft_dirty"] = False
    st.session_state["diag_draft_empresa_nombre"] = ""
    st.session_state["diag_edit_loaded_id"] = diagnostico_id


def obtener_columna_evento_grid(event_data) -> str | None:
    if not isinstance(event_data, dict):
        return None
    return (
        event_data.get("colId")
        or event_data.get("column")
        or event_data.get("field")
        or event_data.get("columnId")
    )


def obtener_data_evento_grid(event_data):
    if not isinstance(event_data, dict):
        return None
    if isinstance(event_data.get("data"), dict):
        return event_data.get("data")
    if isinstance(event_data.get("rowData"), dict):
        return event_data.get("rowData")
    return None


def construir_comparativo_diagnosticos(df_actual: pd.DataFrame, df_base: pd.DataFrame | None) -> pd.DataFrame:
    comparado = df_actual.copy()
    comparado["NIVEL_EJE"] = comparado["RESPUESTA"].apply(obtener_nivel)
    if df_base is None or df_base.empty:
        comparado["RESPUESTA_BASE"] = None
        comparado["DELTA"] = None
        return comparado

    base = df_base.groupby("EJE", dropna=True)["RESPUESTA"].mean().reset_index()
    base.columns = ["EJE", "RESPUESTA_BASE"]
    comparado = comparado.merge(base, on="EJE", how="left")
    comparado["DELTA"] = (comparado["RESPUESTA"] - comparado["RESPUESTA_BASE"]).round(2)
    return comparado


def construir_plan_accion(df_resp: pd.DataFrame, eje_scores_df: pd.DataFrame) -> pd.DataFrame:
    eje_map = dict(zip(eje_scores_df["EJE"], eje_scores_df["RESPUESTA"]))
    prioridades_df = df_resp[df_resp["RESPUESTA"] <= 2].copy()
    mejoras_df = df_resp[df_resp["RESPUESTA"] == 3].copy()
    oportunidades = pd.concat([prioridades_df, mejoras_df], ignore_index=True)
    if oportunidades.empty:
        oportunidades = df_resp.sort_values("RESPUESTA", ascending=True).copy()

    rows = []
    for _, row in oportunidades.iterrows():
        eje = row["EJE"]
        score_eje = float(eje_map.get(eje, row["RESPUESTA"]))
        if int(row["RESPUESTA"]) <= 2:
            prioridad = "Alta" if score_eje < 2 else "Media"
            categoria = "Accion prioritaria"
            accion = f"Corregir y estandarizar {str(row['PREGUNTA']).strip().lower()}."
        else:
            prioridad = "Oportunidad"
            categoria = "Oportunidad de mejora"
            accion = f"Fortalecer y consolidar {str(row['PREGUNTA']).strip().lower()}."
        rows.append(
            {
                "EJE": eje,
                "CATEGORIA": categoria,
                "HALLAZGO": row["PREGUNTA"],
                "PRIORIDAD": prioridad,
                "RESPONSABLE": obtener_responsable_sugerido(eje),
                "PLAZO": obtener_plazo_sugerido(score_eje),
                "IMPACTO": obtener_impacto_sugerido(score_eje),
                "ACCION": accion[:140].capitalize(),
                "ESTADO": "Pendiente",
                "EVIDENCIA": row["EVIDENCIA"] if str(row["EVIDENCIA"]).strip() else "-",
                "OBSERVACION": row["OBSERVACION"] if str(row["OBSERVACION"]).strip() else "-",
            }
        )
    return pd.DataFrame(rows)


def generar_pdf_operativo(nombre_empresa, fecha, score, nivel, conclusion, df_resp: pd.DataFrame, eje_scores_df: pd.DataFrame, plan_accion_df: pd.DataFrame, empresa_info=None):
    os.makedirs("reportes", exist_ok=True)
    slug = limpiar_nombre_archivo(f"{nombre_empresa}_operativo")
    nombre_archivo = os.path.join("reportes", f"Reporte_Operativo_{slug}.pdf")
    empresa_info = empresa_info or {}

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 16, "F")
    pdf.set_fill_color(31, 126, 214)
    pdf.rect(148, 0, 62, 16, "F")

    if LOGO_PATH and LOGO_PATH.lower().endswith((".png", ".jpg", ".jpeg")):
        pdf.image(LOGO_PATH, x=14, y=21, w=26)

    pdf.set_xy(44, 21)
    pdf.set_font("Arial", "B", 18)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(145, 8, pdf_safe("Reporte Operativo de Diagnostico"), ln=True)
    pdf.set_x(44)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(100, 116, 139)
    pdf.multi_cell(145, 5, pdf_safe("Documento de trabajo con hallazgos, evidencias y plan de accion sugerido por area."))

    pdf.ln(4)
    pdf_metric_card(pdf, 14, 48, 56, 24, "Empresa", nombre_empresa[:18], fecha, (15, 23, 42))
    pdf_metric_card(pdf, 77, 48, 56, 24, "Score", f"{score:.2f}", nivel, obtener_color_nivel(nivel))
    pdf_metric_card(pdf, 140, 48, 56, 24, "Hallazgos", str(len(plan_accion_df)), "Items priorizados y oportunidades.", (31, 126, 214))

    pdf.set_xy(14, 82)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, pdf_safe("Sintesis operativa"), ln=True)
    pdf.set_font("Arial", "", 10)
    pdf.set_text_color(71, 85, 105)
    pdf.multi_cell(182, 5.4, pdf_safe(conclusion))

    pdf.ln(4)
    pdf.set_font("Arial", "B", 12)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, pdf_safe("Plan de accion sugerido"), ln=True)
    pdf.ln(1)
    pdf.set_fill_color(15, 23, 42)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 8)
    headers = [("Area", 28), ("Cat.", 24), ("Prior.", 18), ("Plazo", 18), ("Estado", 22), ("Accion", 72)]
    for label, width in headers:
        pdf.cell(width, 8, pdf_safe(label), border=0, ln=0, fill=True)
    pdf.ln()
    pdf.set_font("Arial", "", 8)
    for _, row in plan_accion_df.iterrows():
        if pdf.get_y() > 260:
            pdf.add_page()
        pdf.set_text_color(15, 23, 42)
        pdf.set_fill_color(248, 250, 252)
        pdf.cell(28, 8, pdf_safe(str(row["EJE"])[:16]), border=0, ln=0, fill=True)
        pdf.cell(24, 8, pdf_safe(str(row["CATEGORIA"])[:16]), border=0, ln=0, fill=True)
        pdf.cell(18, 8, pdf_safe(str(row["PRIORIDAD"])[:10]), border=0, ln=0, fill=True)
        pdf.cell(18, 8, pdf_safe(str(row["PLAZO"])), border=0, ln=0, fill=True)
        pdf.cell(22, 8, pdf_safe(str(row["ESTADO"])[:14]), border=0, ln=0, fill=True)
        pdf.cell(72, 8, pdf_safe(str(row["ACCION"])[:58]), border=0, ln=1, fill=True)

    pdf.add_page()
    pdf.set_fill_color(15, 23, 42)
    pdf.rect(0, 0, 210, 16, "F")
    pdf.set_xy(14, 22)
    pdf.set_font("Arial", "B", 13)
    pdf.set_text_color(15, 23, 42)
    pdf.cell(0, 6, pdf_safe("Detalle de hallazgos y evidencias"), ln=True)
    pdf.ln(2)

    for _, row in plan_accion_df.iterrows():
        if pdf.get_y() > 250:
            pdf.add_page()
        pdf.set_fill_color(245, 248, 252)
        pdf.set_draw_color(228, 233, 239)
        y = pdf.get_y()
        pdf.rect(14, y, 182, 28, "FD")
        pdf.set_xy(20, y + 4)
        pdf.set_font("Arial", "B", 10)
        pdf.set_text_color(15, 23, 42)
        pdf.cell(170, 5, pdf_safe(f"{row['EJE']} | {row['CATEGORIA']} | {row['PRIORIDAD']} | {row['PLAZO']} | {row['ESTADO']}"), ln=True)
        pdf.set_x(20)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(71, 85, 105)
        pdf.cell(170, 4.5, pdf_safe(f"Hallazgo: {row['HALLAZGO']}"), ln=True)
        pdf.set_x(20)
        pdf.cell(170, 4.5, pdf_safe(f"Responsable: {row['RESPONSABLE']} | Impacto: {row['IMPACTO']}"), ln=True)
        pdf.set_x(20)
        pdf.cell(170, 4.5, pdf_safe(f"Evidencia: {row['EVIDENCIA']}"), ln=True)
        pdf.set_x(20)
        pdf.cell(170, 4.5, pdf_safe(f"Observacion: {row['OBSERVACION']}"), ln=True)
        pdf.set_y(y + 34)

    pdf_footer(pdf, pdf.page_no())
    pdf.output(nombre_archivo)
    return nombre_archivo


@st.cache_data(show_spinner=False)
def _legacy_obtener_empresas():
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    c.execute("""
        SELECT
            id,
            COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social
        FROM empresas
        ORDER BY COALESCE(NULLIF(razon_social, ''), nombre)
    """)
    empresas = c.fetchall()
    conn.close()
    return empresas


@st.cache_data(show_spinner=False)
def _legacy_obtener_empresa_detalle(empresa_id):
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    c.execute("""
        SELECT
            id,
            COALESCE(NULLIF(razon_social, ''), nombre) AS razon_social,
            ubicacion,
            contacto_nombre,
            contacto_correo,
            contacto_telefono,
            contacto_posicion,
            rubro,
            cantidad_empleados,
            cert_iso_9001,
            cert_iso_14001,
            cert_iso_45001,
            cert_iatf
        FROM empresas
        WHERE id = ?
    """, (empresa_id,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None

    keys = [
        "id",
        "razon_social",
        "ubicacion",
        "contacto_nombre",
        "contacto_correo",
        "contacto_telefono",
        "contacto_posicion",
        "rubro",
        "cantidad_empleados",
        "cert_iso_9001",
        "cert_iso_14001",
        "cert_iso_45001",
        "cert_iatf",
    ]
    return dict(zip(keys, row))


@st.cache_data(show_spinner=False)
def _legacy_obtener_diagnosticos_empresa(empresa_id):
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    c.execute("""
        SELECT id, fecha, score, nivel, conclusion
        FROM diagnosticos
        WHERE empresa_id = ?
        ORDER BY fecha DESC
    """, (empresa_id,))
    rows = c.fetchall()
    conn.close()
    return rows


@st.cache_data(show_spinner=False)
def _legacy_obtener_respuestas_diagnostico(diagnostico_id):
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    c.execute("""
        SELECT eje, pregunta, respuesta, evidencia, observacion
        FROM respuestas
        WHERE diagnostico_id = ?
        ORDER BY id
    """, (diagnostico_id,))
    rows = c.fetchall()
    conn.close()
    return rows


@st.cache_data(show_spinner=False)
def _legacy_obtener_historial_diagnosticos():
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    c.execute("""
        SELECT
            d.id,
            d.empresa_id,
            COALESCE(NULLIF(e.razon_social, ''), e.nombre) AS empresa,
            d.fecha,
            d.score,
            d.nivel,
            d.conclusion
        FROM diagnosticos d
        JOIN empresas e ON e.id = d.empresa_id
        ORDER BY empresa, d.fecha DESC
    """)
    rows = c.fetchall()
    conn.close()
    return rows


def _legacy_guardar_empresa(empresa_data):
    razon_social = empresa_data["razon_social"].strip()
    if not razon_social:
        return False, "La razón social no puede estar vacía."

    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO empresas (
                nombre,
                razon_social,
                ubicacion,
                contacto_nombre,
                contacto_correo,
                contacto_telefono,
                contacto_posicion,
                rubro,
                cantidad_empleados,
                cert_iso_9001,
                cert_iso_14001,
                cert_iso_45001,
                cert_iatf
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            razon_social,
            razon_social,
            empresa_data["ubicacion"].strip(),
            empresa_data["contacto_nombre"].strip(),
            empresa_data["contacto_correo"].strip(),
            empresa_data["contacto_telefono"].strip(),
            empresa_data["contacto_posicion"].strip(),
            empresa_data["rubro"].strip(),
            empresa_data["cantidad_empleados"],
            empresa_data["cert_iso_9001"],
            empresa_data["cert_iso_14001"],
            empresa_data["cert_iso_45001"],
            empresa_data["cert_iatf"],
        ))
        conn.commit()
        st.cache_data.clear()
        return True, "Empresa guardada correctamente."
    except sqlite3.IntegrityError:
        return False, "Esa empresa ya existe."
    finally:
        conn.close()


def _legacy_guardar_diagnostico(empresa_id, score, nivel, conclusion, respuestas_guardar):
    conn = sqlite3.connect("ideas.db")
    c = conn.cursor()

    fecha = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute("""
        INSERT INTO diagnosticos (empresa_id, fecha, score, nivel, conclusion)
        VALUES (?, ?, ?, ?, ?)
    """, (empresa_id, fecha, score, nivel, conclusion))

    diagnostico_id = c.lastrowid

    for item in respuestas_guardar:
        c.execute("""
            INSERT INTO respuestas (diagnostico_id, eje, pregunta, respuesta, evidencia, observacion)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            diagnostico_id,
            item["eje"],
            item["pregunta"],
            item["respuesta"],
            item["evidencia"],
            item["observacion"]
        ))

    conn.commit()
    conn.close()
    st.cache_data.clear()
    return diagnostico_id, fecha


def render_page_intro(etiqueta: str, titulo: str, descripcion: str):
    st.markdown(
        f"""
        <div class="ideas-page-intro">
            <span>{etiqueta}</span>
            <h1>{titulo}</h1>
            <p>{descripcion}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_soft_panel(titulo: str, descripcion: str):
    st.markdown(
        f"""
        <div class="ideas-soft-panel">
            <h3>{titulo}</h3>
            <p>{descripcion}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_aggrid_table(
    df: pd.DataFrame,
    *,
    selection_mode: str = "single",
    use_checkbox: bool = True,
    height: int = 320,
    key: str,
    hidden_columns: list[str] | None = None,
    column_configs: dict[str, dict] | None = None,
    update_on: list[str] | None = None,
) -> dict:
    gb = GridOptionsBuilder.from_dataframe(df)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        wrapText=True,
        autoHeight=True,
    )
    gb.configure_grid_options(
        rowHeight=44,
        headerHeight=42,
        domLayout="normal",
        suppressRowClickSelection=False,
    )
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=8,
    )
    gb.configure_selection(selection_mode=selection_mode, use_checkbox=use_checkbox)
    for col in hidden_columns or []:
        gb.configure_column(col, hide=True)
    for col_name, config in (column_configs or {}).items():
        gb.configure_column(col_name, **config)

    return AgGrid(
        df,
        gridOptions=gb.build(),
        data_return_mode=DataReturnMode.AS_INPUT,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        update_on=update_on or ["selectionChanged", "filterChanged", "sortChanged"],
        fit_columns_on_grid_load=True,
        allow_unsafe_jscode=False,
        theme="streamlit",
        height=height,
        key=key,
        custom_css={
            ".ag-root-wrapper": {
                "border": "1px solid rgba(148, 163, 184, 0.16)",
                "border-radius": "20px",
                "overflow": "hidden",
                "box-shadow": "0 18px 38px rgba(15, 23, 42, 0.06)",
            },
            ".ag-header": {
                "background-color": "#f8fbff",
                "border-bottom": "1px solid rgba(148, 163, 184, 0.12)",
            },
            ".ag-header-cell-text": {
                "font-weight": "700",
                "color": "#0f172a",
            },
            ".ag-row": {
                "border-bottom": "1px solid rgba(148, 163, 184, 0.08)",
            },
            ".ag-row-hover": {
                "background-color": "rgba(31, 126, 214, 0.06) !important",
            },
            ".ag-row-selected": {
                "background-color": "rgba(15, 143, 97, 0.10) !important",
            },
        },
    )


def _legacy_obtener_clase_badge(nivel: str) -> str:
    return nivel.lower()


def _legacy_obtener_delta_texto(delta: float | None) -> tuple[str, str]:
    if delta is None:
        return "Sin base comparativa", "flat"
    if delta > 0.03:
        return f"+{delta:.2f} vs. anterior", "up"
    if delta < -0.03:
        return f"{delta:.2f} vs. anterior", "down"
    return "Sin variacion relevante", "flat"


def _legacy_construir_evidencia_numerica(evidencias: list[str]) -> str:
    limpias = [ev.strip() for ev in evidencias if str(ev).strip()]
    return ", ".join(limpias)


# ---------------- SIDEBAR ----------------

if LOGO_URI:
    st.sidebar.markdown(
        f"""
        <div class="ideas-sidebar-brand">
            <img src="{LOGO_URI}" alt="IDEAS logo">
        </div>
        <div class="ideas-sidebar-caption">Consultoría estratégica</div>
        <div class="ideas-sidebar-divider"></div>
        """,
        unsafe_allow_html=True,
    )
else:
    st.sidebar.title("IDEAS Consulting")

if "force_nav_option" in st.session_state:
    st.session_state["sidebar_nav"] = st.session_state.pop("force_nav_option")

opcion = st.sidebar.radio(
    "Navegación",
    ["Inicio", "Empresa", "Nuevo Diagnóstico", "Resultados", "Historial"],
    key="sidebar_nav",
    label_visibility="collapsed"
)

pagina_anterior = st.session_state.get("ideas_prev_page", opcion)
if (
    pagina_anterior == "Nuevo Diagnóstico"
    and opcion != "Nuevo Diagnóstico"
    and st.session_state.get("diag_draft_dirty", False)
):
    st.session_state["diag_left_unsaved_notice"] = True
st.session_state["ideas_prev_page"] = opcion

st.sidebar.markdown(
    """
    <div class="ideas-sidebar-foot">
        <strong>IDEAS Executive Flow</strong>
        <span>Una experiencia enfocada en claridad, criterio consultivo y seguimiento profesional.</span>
        <span style="display:block;margin-top:0.45rem;color:#0f8f61;font-weight:700;">Diagnóstico, lectura ejecutiva y acción en un solo flujo.</span>
    </div>
    """,
    unsafe_allow_html=True,
)

if opcion != "Nuevo Diagnóstico" and st.session_state.get("diag_left_unsaved_notice", False):
    draft_empresa = st.session_state.get("diag_draft_empresa_nombre", "la empresa seleccionada")
    st.warning(
        f"Tienes un diagnóstico sin guardar para {draft_empresa}. Si no lo guardas, no quedará registrado en la base."
    )
    aviso_col_1, aviso_col_2 = st.columns([1, 1], gap="small")
    with aviso_col_1:
        if st.button("Volver al borrador", key="volver_borrador_diag", use_container_width=True):
            st.session_state["force_nav_option"] = "Nuevo Diagnóstico"
            st.rerun()
    with aviso_col_2:
        if st.button("Descartar borrador", key="descartar_borrador_diag", use_container_width=True):
            limpiar_borrador_diagnostico()
            st.rerun()


# ---------------- INICIO ----------------

if opcion == "Inicio":
    st.markdown(
        """
        <style>
        .ideas-hero {
            position: relative;
            overflow: hidden;
            border-radius: 32px;
            padding: 3rem;
            background:
                radial-gradient(circle at top left, rgba(13, 148, 92, 0.24), transparent 30%),
                radial-gradient(circle at top right, rgba(245, 158, 11, 0.26), transparent 26%),
                linear-gradient(135deg, #f3f8f6 0%, #e7f3ef 44%, #eef6ff 100%);
            border: 1px solid rgba(15, 23, 42, 0.06);
            box-shadow: 0 28px 80px rgba(15, 23, 42, 0.14);
        }
        .ideas-hero-grid {
            display: grid;
            grid-template-columns: minmax(0, 1fr);
            gap: 2rem;
            align-items: start;
        }
        .ideas-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.55rem;
            padding: 0.55rem 1rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.78);
            color: #0f5132;
            font-size: 0.92rem;
            font-weight: 700;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            backdrop-filter: blur(8px);
            box-shadow: 0 14px 30px rgba(15, 23, 42, 0.08);
        }
        .ideas-hero h1 {
            margin: 1.15rem 0 0.9rem 0;
            color: #0f172a;
            font-size: clamp(2.6rem, 5vw, 4.7rem);
            line-height: 1.02;
            letter-spacing: -0.04em;
            font-weight: 800;
            word-break: normal;
            overflow-wrap: normal;
            hyphens: none;
            text-wrap: balance;
        }
        .ideas-hero p {
            margin: 0;
            max-width: 54rem;
            color: #334155;
            font-size: 1.08rem;
            line-height: 1.8;
            word-break: normal;
            overflow-wrap: normal;
            hyphens: none;
            text-wrap: pretty;
        }
        .ideas-points {
            display: flex;
            flex-wrap: wrap;
            gap: 0.85rem;
            margin-top: 1.6rem;
        }
        .ideas-chip {
            padding: 0.78rem 1.05rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.88);
            color: #0f172a;
            font-weight: 600;
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
        }
        .ideas-visual-wrap {
            position: relative;
            margin-top: 0.5rem;
        }
        .ideas-visual-glow {
            position: absolute;
            inset: auto 4% -5% 4%;
            height: 22%;
            background: linear-gradient(90deg, rgba(13, 148, 92, 0.32), rgba(59, 130, 246, 0.22), rgba(245, 158, 11, 0.28));
            filter: blur(34px);
            z-index: 0;
        }
        .ideas-visual-card {
            position: relative;
            z-index: 1;
            overflow: hidden;
            border-radius: 30px;
            min-height: 62vh;
            box-shadow: 0 26px 60px rgba(15, 23, 42, 0.22);
            border: 1px solid rgba(255, 255, 255, 0.55);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0.08));
        }
        .ideas-visual-image {
            display: block;
            width: 100%;
            height: 100%;
            min-height: 62vh;
            object-fit: cover;
            object-position: center;
        }
        .ideas-visual-overlay {
            position: absolute;
            inset: 0;
            background:
                linear-gradient(180deg, rgba(15, 23, 42, 0.04) 0%, rgba(15, 23, 42, 0.12) 40%, rgba(15, 23, 42, 0.36) 100%),
                linear-gradient(135deg, rgba(13, 148, 92, 0.14), transparent 42%, rgba(245, 158, 11, 0.18));
        }
        .ideas-visual-badge {
            position: absolute;
            left: 1.2rem;
            right: 1.2rem;
            bottom: 1.2rem;
            z-index: 2;
            padding: 1rem 1.1rem;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.16);
            color: #ffffff;
            backdrop-filter: blur(18px);
            border: 1px solid rgba(255, 255, 255, 0.18);
        }
        .ideas-visual-badge strong {
            display: block;
            margin-bottom: 0.2rem;
            font-size: 1.05rem;
            letter-spacing: 0.01em;
        }
        .ideas-visual-badge span {
            font-size: 0.95rem;
            line-height: 1.5;
            color: rgba(255, 255, 255, 0.9);
        }
        @media (max-width: 980px) {
            .ideas-hero {
                padding: 1.35rem;
                border-radius: 26px;
            }
            .ideas-hero h1 {
                font-size: clamp(2.3rem, 10vw, 3.2rem);
            }
            .ideas-visual-card {
                min-height: 340px;
                border-radius: 24px;
            }
            .ideas-visual-image {
                min-height: 340px;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if HOME_IMAGE_URI:
        st.markdown(
            f"""
            <div class="ideas-hero">
                <div class="ideas-hero-grid">
                    <div>
                        <div class="ideas-kicker">IDEAS Consulting</div>
                        <h1>Diagnóstico empresarial con visión estratégica.</h1>
                        <p>
                            Centralizá el análisis de tu organización con una experiencia más ejecutiva,
                            clara y profesional, pensada para reflejar compromiso, trabajo en equipo
                            y eficiencia operativa.
                        </p>
                        <div class="ideas-points">
                            <div class="ideas-chip">Compromiso</div>
                            <div class="ideas-chip">Trabajo en equipo</div>
                            <div class="ideas-chip">Eficiencia</div>
                        </div>
                    </div>
                    <div class="ideas-visual-wrap">
                        <div class="ideas-visual-glow"></div>
                        <div class="ideas-visual-card">
                            <img class="ideas-visual-image" src="{HOME_IMAGE_URI}" alt="Portada IDEAS Consulting">
                            <div class="ideas-visual-overlay"></div>
                            <div class="ideas-visual-badge">
                                <strong>Portada ejecutiva IDEAS</strong>
                                <span>Una presencia visual más sólida para iniciar cada diagnóstico con una imagen de alto nivel.</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    else:
        st.title("IDEAS Consulting")
        st.subheader("Sistema de Diagnóstico Empresarial")
        st.write("Seleccioná una opción del menú para comenzar.")


# ---------------- EMPRESA ----------------

elif opcion == "Empresa":
    render_page_intro(
        "Empresas",
        "Gestión de empresas",
        "Centralizá la base de clientes y mantené un registro limpio para iniciar nuevos diagnósticos con una operación más ordenada y profesional.",
    )
    col_info, col_form = st.columns([1, 1.2], gap="large")

    with col_info:
        render_soft_panel(
            "Base comercial organizada",
            "Cada empresa queda disponible para nuevas evaluaciones, reportes ejecutivos e histórico comparativo dentro de un mismo flujo.",
        )
        st.markdown(
            """
            <div class="ideas-mini-note">
                <strong>Recomendación IDEAS</strong>
                Usá nombres consistentes y formales para mantener trazabilidad en reportes y diagnósticos futuros.
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col_form:
        render_soft_panel(
            "Alta de cliente",
            "Cargá la empresa y dejala lista para trabajar en el circuito de diagnóstico estratégico.",
        )
        with st.form("empresa_form"):
            razon_social = st.text_input("Razón social", key="empresa_razon_social")
            ubicacion = st.text_input("Ubicación", key="empresa_ubicacion")
            rubro = st.text_input("Rubro", key="empresa_rubro")
            cantidad_empleados = st.number_input("Cantidad de empleados", min_value=0, step=1, key="empresa_empleados")

            st.markdown("**Persona de contacto**")
            contacto_nombre = st.text_input("Nombre", key="empresa_contacto_nombre")
            contacto_correo = st.text_input("Correo", key="empresa_contacto_correo")
            contacto_telefono = st.text_input("Teléfono", key="empresa_contacto_telefono")
            contacto_posicion = st.text_input("Posición", key="empresa_contacto_posicion")

            st.markdown("**Certificaciones**")
            cert1, cert2 = st.columns(2)
            with cert1:
                cert_iso_9001 = st.selectbox("ISO 9001", ["No", "Sí"], key="cert_iso_9001")
                cert_iso_14001 = st.selectbox("ISO 14001", ["No", "Sí"], key="cert_iso_14001")
            with cert2:
                cert_iso_45001 = st.selectbox("ISO 45001", ["No", "Sí"], key="cert_iso_45001")
                cert_iatf = st.selectbox("IATF", ["No", "Sí"], key="cert_iatf")

            guardar_empresa_submit = st.form_submit_button("Guardar empresa", use_container_width=True)

        if guardar_empresa_submit:
            ok, mensaje = guardar_empresa({
                "razon_social": razon_social,
                "ubicacion": ubicacion,
                "contacto_nombre": contacto_nombre,
                "contacto_correo": contacto_correo,
                "contacto_telefono": contacto_telefono,
                "contacto_posicion": contacto_posicion,
                "rubro": rubro,
                "cantidad_empleados": int(cantidad_empleados),
                "cert_iso_9001": cert_iso_9001,
                "cert_iso_14001": cert_iso_14001,
                "cert_iso_45001": cert_iso_45001,
                "cert_iatf": cert_iatf,
            })
            if ok:
                st.success(mensaje)
            else:
                st.warning(mensaje)


# ---------------- NUEVO DIAGNÓSTICO ----------------

elif opcion == "Nuevo Diagnóstico":
    render_page_intro(
        "Diagnóstico",
        "Nuevo diagnóstico empresarial",
        "Evaluá cada eje con una lectura clara, evidencias concretas y observaciones consultivas para construir un resultado ejecutivo consistente.",
    )
    st.session_state["diag_left_unsaved_notice"] = False
    diag_edit_pref_id = st.session_state.get("diag_edit_pref_id")
    diag_edit_pref_empresa = st.session_state.get("diag_edit_pref_empresa")
    diag_duplicate_pref_id = st.session_state.get("diag_duplicate_pref_id")
    diag_duplicate_pref_empresa = st.session_state.get("diag_duplicate_pref_empresa")
    if diag_edit_pref_empresa:
        st.session_state["diag_empresa"] = diag_edit_pref_empresa
    elif diag_duplicate_pref_empresa:
        st.session_state["diag_empresa"] = diag_duplicate_pref_empresa

    empresas = obtener_empresas()

    if not empresas:
        st.warning("Primero tenés que crear una empresa en la sección Empresa.")
        st.stop()

    empresa_dict = {nombre: empresa_id for empresa_id, nombre in empresas}
    col_selector, col_note = st.columns([1.35, 1], gap="large")
    with col_selector:
        render_soft_panel(
            "Empresa objetivo",
            "Seleccioná la organización sobre la que vas a trabajar este relevamiento.",
        )
        empresa_sel = st.selectbox(
            "Seleccionar empresa",
            list(empresa_dict.keys()),
            key="diag_empresa",
            disabled=bool(st.session_state.get("diag_editing_id") or diag_edit_pref_id),
        )
        empresa_id = empresa_dict[empresa_sel]
        diagnosticos_existentes = obtener_diagnosticos_empresa(empresa_id)
        numero_diagnostico = len(diagnosticos_existentes) + 1
        if st.session_state.get("diag_editing_id") or diag_edit_pref_id:
            diag_edicion_id = st.session_state.get("diag_editing_id") or diag_edit_pref_id
            st.markdown(
                f"""
                <div class="ideas-edit-banner">
                    <div>
                        <span class="eyebrow">Modo edición</span>
                        <strong>Vas a actualizar el diagnóstico existente</strong>
                        <p>Estás trabajando sobre el <strong>Diagnóstico ID {diag_edicion_id}</strong>. Si guardas, se reemplazarán puntajes, evidencias y observaciones de ese mismo corte.</p>
                    </div>
                    <div class="meta">Registro actual<br>ID {diag_edicion_id}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Salir del modo edición", key="diag_salir_modo_edicion", use_container_width=True):
                limpiar_borrador_diagnostico()
                st.session_state["force_nav_option"] = "Nuevo Diagnóstico"
                st.rerun()
        elif diag_duplicate_pref_id:
            st.markdown(
                f"""
                <div class="ideas-edit-banner">
                    <div>
                        <span class="eyebrow">Duplicar como nuevo</span>
                        <strong>Usas un diagnóstico anterior como base</strong>
                        <p>La información del <strong>Diagnóstico ID {diag_duplicate_pref_id}</strong> fue precargada para acelerar la carga, pero al guardar se creará un corte nuevo.</p>
                    </div>
                    <div class="meta">Nuevo registro<br>basado en ID {diag_duplicate_pref_id}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button("Cancelar duplicación", key="diag_cancelar_duplicacion", use_container_width=True):
                limpiar_borrador_diagnostico()
                st.session_state["force_nav_option"] = "Nuevo Diagnóstico"
                st.rerun()
        elif diagnosticos_existentes:
            ultimo_diag = diagnosticos_existentes[0]
            st.markdown(
                f"""
                <div class="ideas-mini-note">
                    <strong>Nuevo corte para empresa existente</strong>
                    Esta empresa ya tiene {len(diagnosticos_existentes)} diagnóstico(s) cargado(s). Vas a registrar el <strong>Diagnóstico {numero_diagnostico}</strong>.
                    Último corte: {ultimo_diag[1]} | Score {float(ultimo_diag[2]):.2f} | Nivel {ultimo_diag[3]}.
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="ideas-mini-note">
                    <strong>Primer diagnóstico</strong>
                    Esta empresa todavía no tiene relevamientos. El corte que cargues ahora quedará como Diagnóstico 1.
                </div>
                """,
                unsafe_allow_html=True,
            )
    with col_note:
        st.markdown(
            """
            <div class="ideas-mini-note">
                <strong>Criterio de carga</strong>
                Priorizá evidencia breve, concreta y verificable. Eso mejora la lectura ejecutiva del resultado final.
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            """
            <div class="ideas-mini-note">
                <strong>Evidencias numeradas</strong>
                Si tenés una sola evidencia, cargás solo su número. Si tenés varias, indicás la cantidad y la app las enumera para vos.
            </div>
            """,
            unsafe_allow_html=True,
        )

    try:
        df = leer_diagnostico_excel()
    except Exception as e:
        st.error(str(e))
        st.stop()

    if diag_edit_pref_id and st.session_state.get("diag_edit_loaded_id") != diag_edit_pref_id:
        precargar_diagnostico_en_formulario(df, int(diag_edit_pref_id), empresa_sel)
        st.session_state["diag_editing_id"] = int(diag_edit_pref_id)
        st.session_state["diag_edit_pref_id"] = None
        st.session_state["diag_edit_pref_empresa"] = None
    elif diag_duplicate_pref_id and st.session_state.get("diag_edit_loaded_id") != diag_duplicate_pref_id:
        precargar_diagnostico_en_formulario(df, int(diag_duplicate_pref_id), empresa_sel)
        st.session_state["diag_editing_id"] = None
        st.session_state["diag_edit_loaded_id"] = None
        st.session_state["diag_duplicate_pref_id"] = None
        st.session_state["diag_duplicate_pref_empresa"] = None
        st.session_state["diag_last_saved_signature"] = None
        st.session_state["diag_draft_dirty"] = True
        st.session_state["diag_draft_empresa_nombre"] = empresa_sel

    criterios_puntaje, regla_evidencia = leer_criterios_puntaje()
    score_items_html = "".join(
        f"""
        <div class="ideas-score-item">
            <div class="value">{criterio['escala']}</div>
            <strong>{html_safe(criterio['nivel'])}</strong>
            <span>{html_safe(criterio['resumen'])}</span>
        </div>
        """
        for criterio in criterios_puntaje
    )
    st.markdown(
        f"""
        <div class="ideas-score-guide">
            <div class="ideas-score-guide-head">
                <strong>Criterios de puntuación</strong>
                <span>Usá la misma lógica en todo el relevamiento para mantener consistencia entre áreas y cortes.</span>
            </div>
            <div class="ideas-score-grid">{score_items_html}</div>
            <div class="ideas-score-rule"><strong>Regla IDEAS:</strong> {html_safe(regla_evidencia)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    respuestas_guardar = []
    eje_scores = {}

    with st.form("diagnostico_form"):
        for eje in df["EJE"].dropna().unique():
            render_soft_panel(
                eje,
                "Respondé cada punto valorando madurez operativa, soporte documental y criterio consultivo IDEAS.",
            )

            sub = df[df["EJE"] == eje]
            eje_vals = []

            for i, row in sub.iterrows():
                pregunta = str(row["PREGUNTA"]).strip()

                st.markdown(f'<div class="ideas-question-card"><h4>{pregunta}</h4></div>', unsafe_allow_html=True)

                col1, col2, col3 = st.columns([1, 2, 2])

                with col1:
                    respuesta = st.selectbox(
                        "Nivel",
                        [1, 2, 3, 4],
                        key=f"resp_{eje}_{i}",
                        format_func=lambda valor, criterios=criterios_puntaje: resumen_puntaje_corto(valor, criterios),
                    )
                    st.markdown(
                        f'<div class="ideas-score-inline">{html_safe(resumen_puntaje_corto(int(respuesta), criterios_puntaje))}</div>',
                        unsafe_allow_html=True,
                    )

                with col2:
                    cantidad_evidencias = st.selectbox(
                        "Cantidad de evidencias",
                        [1, 2, 3, 4, 5],
                        key=f"cant_evid_{eje}_{i}"
                    )
                    evidencias_numericas = []
                    for nro_evidencia in range(1, int(cantidad_evidencias) + 1):
                        evidencia_item = st.text_input(
                            f"Evidencia {nro_evidencia}",
                            key=f"evid_{eje}_{i}_{nro_evidencia}",
                            placeholder="Ej. 1"
                        )
                        evidencias_numericas.append(evidencia_item)
                    evidencia = construir_evidencia_numerica(evidencias_numericas)

                with col3:
                    observacion = st.text_input(
                        "Observación IDEAS",
                        key=f"obs_{eje}_{i}"
                    )

                respuestas_guardar.append({
                    "eje": eje,
                    "pregunta": pregunta,
                    "respuesta": int(respuesta),
                    "evidencia": evidencia.strip(),
                    "observacion": observacion.strip()
                })

                eje_vals.append(int(respuesta))
                st.divider()

            eje_scores[eje] = sum(eje_vals) / len(eje_vals)

        guardar_diagnostico_submit = st.form_submit_button("Calcular y guardar diagnóstico", use_container_width=True)

    diag_editing_id = st.session_state.get("diag_editing_id")
    tiene_contenido_borrador = any(
        item["respuesta"] != 1 or item["evidencia"] or item["observacion"]
        for item in respuestas_guardar
    )
    firma_actual_borrador = firma_borrador_diagnostico(empresa_id, respuestas_guardar)
    firma_guardada = st.session_state.get("diag_last_saved_signature")
    borrador_sin_guardar = tiene_contenido_borrador and firma_actual_borrador != firma_guardada
    st.session_state["diag_draft_dirty"] = borrador_sin_guardar
    st.session_state["diag_draft_empresa_nombre"] = empresa_sel if borrador_sin_guardar else ""

    if borrador_sin_guardar:
        st.warning("Hay cambios sin guardar. Si sales de esta sección sin guardar, el diagnóstico no quedará registrado.")
    elif tiene_contenido_borrador and firma_actual_borrador == firma_guardada:
        if diag_editing_id:
            st.info("Este diagnóstico ya está actualizado con ese contenido. Si vuelves a guardar sin cambios, no se modificará.")
        else:
            st.info("El contenido actual ya fue guardado. Si vuelves a guardar sin cambios, no se generará otro diagnóstico.")

    if guardar_diagnostico_submit:
        if not respuestas_guardar:
            st.warning("No hay respuestas para guardar.")
            st.stop()

        score = sum(item["respuesta"] for item in respuestas_guardar) / len(respuestas_guardar)
        nivel = obtener_nivel(score)
        conclusion = obtener_conclusion(score)

        if diag_editing_id:
            diagnostico_id, fecha, guardado_duplicado = actualizar_diagnostico(
                diagnostico_id=diag_editing_id,
                empresa_id=empresa_id,
                score=score,
                nivel=nivel,
                conclusion=conclusion,
                respuestas_guardar=respuestas_guardar,
            )
        else:
            diagnostico_id, fecha, guardado_duplicado = guardar_diagnostico(
                empresa_id=empresa_id,
                score=score,
                nivel=nivel,
                conclusion=conclusion,
                respuestas_guardar=respuestas_guardar
            )

        criticas = [item["pregunta"] for item in respuestas_guardar if item["respuesta"] <= 2]

        st.session_state["resultado_actual"] = {
            "diagnostico_id": diagnostico_id,
            "empresa": empresa_sel,
            "fecha": fecha,
            "score": score,
            "nivel": nivel,
            "conclusion": conclusion,
            "eje_scores": eje_scores,
            "criticas": criticas,
            "detalle": respuestas_guardar
        }
        st.session_state["diag_last_saved_signature"] = firma_actual_borrador
        st.session_state["diag_draft_dirty"] = False
        st.session_state["diag_draft_empresa_nombre"] = ""
        st.session_state["diag_left_unsaved_notice"] = False
        st.session_state["diag_editing_id"] = diagnostico_id
        st.session_state["diag_edit_loaded_id"] = diagnostico_id

        if guardado_duplicado:
            if diag_editing_id:
                st.info("Ese diagnóstico ya tenía exactamente ese contenido. No fue necesario volver a actualizarlo.")
            else:
                st.info("Ese diagnóstico ya había sido guardado con el mismo contenido. Se reutilizó el registro existente.")
        else:
            if diag_editing_id:
                st.success("Diagnóstico actualizado correctamente.")
            else:
                st.success("Diagnóstico guardado correctamente. Ya podés verlo en Resultados.")


# ---------------- RESULTADOS ----------------

elif opcion == "Resultados":
    render_page_intro(
        "Resultados",
        "Dashboard ejecutivo",
        "Interpretá el diagnóstico desde una vista de dirección: nivel global, focos críticos y performance por área en una lectura clara y premium.",
    )

    empresas = obtener_empresas()

    if not empresas:
        st.warning("No hay empresas cargadas.")
        st.stop()

    empresa_dict = {nombre: empresa_id for empresa_id, nombre in empresas}
    empresa_labels = list(empresa_dict.keys())
    empresa_pref = st.session_state.pop("res_empresa_pref", None)
    empresa_index = empresa_labels.index(empresa_pref) if empresa_pref in empresa_labels else 0
    filtro_1, filtro_2 = st.columns(2, gap="large")
    with filtro_1:
        render_soft_panel(
            "Empresa",
            "Elegí la organización para revisar su evolución y diagnóstico disponible.",
        )
        empresa_sel = st.selectbox("Seleccionar empresa", empresa_labels, index=empresa_index, key="res_empresa")
        empresa_id = empresa_dict[empresa_sel]
        empresa_info = obtener_empresa_detalle(empresa_id)

    diagnosticos = obtener_diagnosticos_empresa(empresa_id)

    if not diagnosticos:
        st.warning("Esta empresa no tiene diagnósticos.")
        st.stop()

    diag_dict = {
        f"{fecha} | Score {round(score, 2)}": diag_id
        for diag_id, fecha, score, nivel, conclusion in diagnosticos
    }
    diag_labels = list(diag_dict.keys())
    diag_pref = st.session_state.pop("res_diag_pref", None)
    diag_index = next((idx for idx, label in enumerate(diag_labels) if diag_dict[label] == diag_pref), 0)

    with filtro_2:
        render_soft_panel(
            "Corte analítico",
            "Seleccioná la medición exacta que querés presentar o exportar.",
        )
        diag_sel = st.selectbox("Seleccionar diagnóstico", diag_labels, index=diag_index, key="res_diag")
        diagnostico_id = diag_dict[diag_sel]

    respuestas = obtener_respuestas_diagnostico(diagnostico_id)
    if not respuestas:
        st.warning("No se encontraron respuestas para este diagnóstico.")
        st.stop()

    df_resp, eje_scores_df = construir_dataframe_ejes(respuestas)

    score = df_resp["RESPUESTA"].mean()
    nivel = obtener_nivel(score)
    conclusion = obtener_conclusion(score)
    mensaje_direccion = obtener_mensaje_direccion(nivel)
    eje_scores = dict(zip(eje_scores_df["EJE"], eje_scores_df["RESPUESTA"]))

    criticas = df_resp[df_resp["RESPUESTA"] <= 2]["PREGUNTA"].tolist()
    mejor_eje = eje_scores_df.sort_values("RESPUESTA", ascending=False).iloc[0]
    eje_prioritario = eje_scores_df.sort_values("RESPUESTA", ascending=True).iloc[0]
    historico_df = pd.DataFrame(
        diagnosticos,
        columns=["DIAGNOSTICO_ID", "FECHA", "SCORE", "NIVEL", "CONCLUSION"]
    ).sort_values("FECHA")
    score_anterior = None
    if len(historico_df) > 1:
        prev_rows = historico_df[historico_df["DIAGNOSTICO_ID"] != diagnostico_id]
        if not prev_rows.empty:
            score_anterior = prev_rows.iloc[-1]["SCORE"]
    delta_score = round(score - score_anterior, 2) if score_anterior is not None else None
    delta_score_texto, delta_score_clase = obtener_delta_texto(delta_score)

    df_prev = None
    if score_anterior is not None:
        respuestas_prev = obtener_respuestas_diagnostico(int(prev_rows.iloc[-1]["DIAGNOSTICO_ID"]))
        if respuestas_prev:
            df_prev, _ = construir_dataframe_ejes(respuestas_prev)

    eje_scores_comparado = construir_comparativo_diagnosticos(eje_scores_df, df_prev)
    plan_accion_df = construir_plan_accion(df_resp, eje_scores_df)

    st.markdown(
        f"""
        <div class="ideas-dashboard-hero">
            <span class="eyebrow">Executive Dashboard</span>
            <h2>{empresa_sel} · lectura de dirección</h2>
            <p>
                Nivel actual: <strong>{nivel}</strong>. {mensaje_direccion}
                El tablero resume desempeno, prioridades y consistencia operativa en una vista pensada para liderazgo.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    met1, met2, met3 = st.columns(3, gap="large")
    with met1:
        st.markdown(
            f"""
            <div class="ideas-score-card">
                <span class="label">Score global</span>
                <span class="value">{round(score, 2)}</span>
                <span class="detail">Promedio consolidado del diagnóstico seleccionado.</span>
                <span class="detail"><span class="ideas-delta {delta_score_clase}">{delta_score_texto}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with met2:
        st.markdown(
            f"""
            <div class="ideas-score-card">
                <span class="label">Nivel de madurez</span>
                <span class="value">{nivel}</span>
                <span class="detail">Lectura ejecutiva del desempeño actual de la organización.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with met3:
        st.markdown(
            f"""
            <div class="ideas-score-card">
                <span class="label">Hallazgos críticos</span>
                <span class="value">{len(criticas)}</span>
                <span class="detail">Cantidad de puntos que requieren atención prioritaria.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    overview1, overview2, overview3 = st.columns(3, gap="large")
    with overview1:
        st.markdown(
            f"""
            <div class="ideas-quick-card">
                <strong>Corte seleccionado</strong>
                <span>{html_safe(diag_sel)}. Lectura ejecutiva lista para revisión y exportación.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with overview2:
        st.markdown(
            f"""
            <div class="ideas-quick-card">
                <strong>Área prioritaria de mejora</strong>
                <span>{html_safe(eje_prioritario['EJE'])} concentra la mayor oportunidad con score {eje_prioritario['RESPUESTA']:.2f}.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with overview3:
        tendencia_texto = (
            f"Variación frente al corte previo: {delta_score_texto}."
            if score_anterior is not None
            else "Sin base histórica adicional para comparar."
        )
        st.markdown(
            f"""
            <div class="ideas-quick-card">
                <strong>Tendencia ejecutiva</strong>
                <span>{tendencia_texto}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    band1, band2 = st.columns(2, gap="large")
    with band1:
        st.markdown(
            f"""
            <div class="ideas-kpi-band">
                <strong>Mejor desempeño</strong>
                <span>{mejor_eje['EJE']} lidera con un score de {mejor_eje['RESPUESTA']:.2f}, mostrando la mayor solidez relativa del diagnóstico.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with band2:
        st.markdown(
            f"""
            <div class="ideas-kpi-band">
                <strong>Prioridad de gestión</strong>
                <span>{eje_prioritario['EJE']} concentra la mayor oportunidad, con un score de {eje_prioritario['RESPUESTA']:.2f} y foco recomendado de corto plazo.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ideas-subsection-title">Evolucion y comparativos</div>', unsafe_allow_html=True)
    evo1, evo2 = st.columns([1.15, 0.85], gap="large")
    with evo1:
        st.markdown(
            """
            <div class="ideas-visual-panel">
                <h3>Evolución temporal</h3>
                <p>Seguimiento del score global entre diagnósticos para ver tendencia, estabilidad y avance.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=historico_df["FECHA"],
            y=historico_df["SCORE"],
            mode="lines+markers",
            line=dict(color="#1f7ed6", width=3),
            marker=dict(size=10, color="#0f172a"),
            fill="tozeroy",
            fillcolor="rgba(31,126,214,0.10)",
            hovertemplate="%{x}<br>Score: %{y:.2f}<extra></extra>",
        ))
        fig_line.update_layout(
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            margin=dict(l=10, r=10, t=10, b=20),
            xaxis=dict(showgrid=False, title=""),
            yaxis=dict(
                range=[0.8, 4.05],
                showgrid=True,
                gridcolor="rgba(148,163,184,0.18)",
                title=""
            ),
            height=310,
            showlegend=False,
        )
        st.plotly_chart(fig_line, use_container_width=True)

    with evo2:
        st.markdown(
            """
            <div class="ideas-visual-panel">
                <h3>Lectura de tendencia</h3>
                <p>Comparativo del corte actual frente al histórico disponible.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if score_anterior is not None:
            st.markdown(
                f"""
                <div class="ideas-kpi-band">
                    <strong>Comparación contra el diagnóstico anterior</strong>
                    <span>Score previo: {score_anterior:.2f}. Variación actual: <span class="ideas-delta {delta_score_clase}">{delta_score_texto}</span>.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                """
                <div class="ideas-kpi-band">
                    <strong>Comparación contra el diagnóstico anterior</strong>
                    <span>Aún no hay una base histórica adicional para mostrar evolución comparativa.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="ideas-visual-panel">
            <h3>Comparativo entre diagnósticos</h3>
            <p>Elegí un segundo corte para analizar variaciones puntuales por eje y una lectura ejecutiva de avance o deterioro.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    diag_compare_dict = {label: did for label, did in diag_dict.items() if did != diagnostico_id}
    if diag_compare_dict:
        compare_col_1, compare_col_2 = st.columns([1, 2], gap="large")
        with compare_col_1:
            base_label = st.selectbox("Diagnóstico base para comparar", list(diag_compare_dict.keys()), key="res_diag_compare")
            diagnostico_base_id = diag_compare_dict[base_label]
            respuestas_base = obtener_respuestas_diagnostico(diagnostico_base_id)
            df_base, eje_base_df = construir_dataframe_ejes(respuestas_base)
            comparativo_manual = construir_comparativo_diagnosticos(eje_scores_df, df_base)
            delta_global = round(score - df_base["RESPUESTA"].mean(), 2) if not df_base.empty else None
            delta_manual_txt, delta_manual_cls = obtener_delta_texto(delta_global)
        with compare_col_2:
            mejoras = int((comparativo_manual["DELTA"].fillna(0) > 0.03).sum())
            retrocesos = int((comparativo_manual["DELTA"].fillna(0) < -0.03).sum())
            st.markdown(
                f"""
                <div class="ideas-kpi-band">
                    <strong>Resumen comparativo</strong>
                    <span>Base seleccionada: {html_safe(base_label)}. Variación global: <span class="ideas-delta {delta_manual_cls}">{delta_manual_txt}</span>. Mejoras detectadas: {mejoras}. Retrocesos detectados: {retrocesos}.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
            fig_compare = go.Figure()
            delta_df = comparativo_manual.sort_values("DELTA", ascending=True, na_position="last").fillna({"DELTA": 0})
            fig_compare.add_trace(go.Bar(
                x=delta_df["DELTA"],
                y=delta_df["EJE"],
                orientation="h",
                marker=dict(color=["#0f8f61" if v > 0 else "#dc2626" if v < 0 else "#94a3b8" for v in delta_df["DELTA"]]),
                text=[f"{v:+.2f}" for v in delta_df["DELTA"]],
                textposition="outside",
                hovertemplate="%{y}<br>Delta: %{x:.2f}<extra></extra>",
            ))
            fig_compare.update_layout(
                paper_bgcolor="rgba(255,255,255,0)",
                plot_bgcolor="rgba(255,255,255,0)",
                margin=dict(l=20, r=20, t=10, b=20),
                xaxis=dict(title="", gridcolor="rgba(148,163,184,0.18)", zeroline=True, zerolinecolor="rgba(15,23,42,0.18)"),
                yaxis=dict(title=""),
                height=max(280, 44 * len(delta_df)),
                showlegend=False,
            )
            st.plotly_chart(fig_compare, use_container_width=True)
    else:
        st.markdown(
            """
            <div class="ideas-kpi-band">
                <strong>Comparativo entre diagnósticos</strong>
                <span>Necesitas al menos dos diagnósticos para habilitar la comparación manual entre cortes.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="ideas-subsection-title">Resultado general y lectura por área</div>', unsafe_allow_html=True)
    status_class = {"Bajo": "low", "Medio": "medium", "Alto": "high"}.get(nivel, "medium")
    st.markdown(
        f"""
        <div class="ideas-status-band {status_class}">
            <div>
                <span class="eyebrow">Resultado general</span>
                <strong>Nivel {nivel}</strong>
                <p>{html_safe(conclusion)} {html_safe(mensaje_direccion)}</p>
            </div>
            <div class="ideas-status-metric">
                <span>Score global</span>
                <strong>{round(score, 2):.2f}</strong>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    viz1, viz2 = st.columns([1.05, 0.95], gap="large")
    with viz1:
        st.markdown(
            """
            <div class="ideas-visual-panel">
                <h3>Performance por área</h3>
                <p>Comparativo de madurez por eje para identificar fortalezas y focos de intervención.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        bar_df = eje_scores_df.sort_values("RESPUESTA", ascending=True)
        fig_bar = go.Figure()
        fig_bar.add_trace(go.Bar(
            x=bar_df["RESPUESTA"],
            y=bar_df["EJE"],
            orientation="h",
            marker=dict(
                color=bar_df["RESPUESTA"],
                colorscale=[
                    [0.0, "#f59e0b"],
                    [0.45, "#60a5fa"],
                    [1.0, "#0f8f61"],
                ],
                cmin=1,
                cmax=4,
                line=dict(color="rgba(15,23,42,0.08)", width=1),
            ),
            text=[f"{valor:.2f}" for valor in bar_df["RESPUESTA"]],
            textposition="outside",
            hovertemplate="%{y}<br>Score: %{x:.2f}<extra></extra>",
        ))
        fig_bar.update_layout(
            paper_bgcolor="rgba(255,255,255,0)",
            plot_bgcolor="rgba(255,255,255,0)",
            margin=dict(l=20, r=20, t=10, b=20),
            xaxis=dict(
                range=[0, 4.2],
                showgrid=True,
                gridcolor="rgba(148,163,184,0.18)",
                zeroline=False,
                tickfont=dict(color="#64748b"),
                title="",
            ),
            yaxis=dict(
                tickfont=dict(color="#0f172a"),
                title="",
            ),
            showlegend=False,
            height=360,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

    with viz2:
        st.markdown(
            """
            <div class="ideas-visual-panel">
                <h3>Radar de madurez</h3>
                <p>Vista sintética para evaluar equilibrio entre áreas y amplitud de capacidades.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        fig = go.Figure()
        fig.add_trace(go.Scatterpolar(
            r=eje_scores_df["RESPUESTA"],
            theta=eje_scores_df["EJE"],
            fill="toself",
            line=dict(color="#1f7ed6", width=3),
            fillcolor="rgba(31, 126, 214, 0.22)"
        ))
        fig.update_layout(
            polar=dict(
                bgcolor="rgba(255,255,255,0)",
                radialaxis=dict(
                    visible=True,
                    range=[1, 4],
                    gridcolor="rgba(15, 23, 42, 0.10)",
                    linecolor="rgba(15, 23, 42, 0.10)",
                    tickfont=dict(color="#64748b")
                )
            ),
            paper_bgcolor="rgba(255,255,255,0)",
            showlegend=False,
            margin=dict(l=40, r=40, t=40, b=40)
        )
        st.plotly_chart(fig, use_container_width=True)

    res1, res2 = st.columns([1, 1], gap="large")
    with res1:
        st.markdown('<div class="ideas-subsection-title">Principales oportunidades</div>', unsafe_allow_html=True)
        if criticas:
            for critica in criticas[:5]:
                st.markdown(
                    f"""
                    <div class="ideas-mini-note">
                        <strong>Área prioritaria de mejora</strong>
                        {critica}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        else:
            st.success("No se detectaron desviaciones críticas.")

    with res2:
        st.markdown('<div class="ideas-subsection-title">Conclusion ejecutiva</div>', unsafe_allow_html=True)
        st.subheader("Conclusión Ejecutiva")
        render_soft_panel("Lectura consultiva", conclusion)
        st.markdown(
            f"""
            <div class="ideas-kpi-band">
                <strong>Mensaje para dirección</strong>
                <span>{mensaje_direccion}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        """
        <div class="ideas-visual-panel">
            <h3>Semáforo por eje</h3>
            <p>Mapa resumido para dirección con score, nivel y variación frente al corte previo cuando exista.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        """
        <div class="ideas-semaforo-head">Eje | Score | Nivel | Variación</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ideas-subsection-title">Semaforo ejecutivo por eje</div>', unsafe_allow_html=True)
    for _, fila in eje_scores_comparado.sort_values("RESPUESTA").iterrows():
        delta_txt, delta_cls = obtener_delta_texto(fila["DELTA"] if pd.notna(fila["DELTA"]) else None)
        c1, c2, c3, c4 = st.columns([2.2, 0.8, 1.1, 1.6], gap="small")
        with c1:
            st.markdown(
                f"""
                <div class="ideas-semaforo-row">
                    <strong>{fila['EJE']}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c2:
            st.markdown(
                f"""
                <div class="ideas-semaforo-row">
                    <strong>{fila['RESPUESTA']:.2f}</strong>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c3:
            st.markdown(
                f"""
                <div class="ideas-semaforo-row">
                    <span class="ideas-badge {obtener_clase_badge(fila['NIVEL_EJE'])}">{fila['NIVEL_EJE']}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with c4:
            st.markdown(
                f"""
                <div class="ideas-semaforo-row">
                    <span class="ideas-delta {delta_cls}">{delta_txt}</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

    st.markdown(
        """
        <div class="ideas-visual-panel">
            <h3>Plan de acción sugerido</h3>
            <p>Propuesta consultiva para convertir el diagnóstico en una hoja de ruta accionable, con prioridad, responsable y plazo.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="ideas-subsection-title">Plan de accion y seguimiento</div>', unsafe_allow_html=True)
    plan_state_key = f"plan_accion_editable_{diagnostico_id}"
    if plan_state_key not in st.session_state:
        st.session_state[plan_state_key] = plan_accion_df.copy()
    plan_accion_editable = st.session_state[plan_state_key]

    if not plan_accion_editable.empty:
        plan_info_1, plan_info_2, plan_info_3 = st.columns(3, gap="large")
        with plan_info_1:
            st.markdown(
                f"""
                <div class="ideas-quick-card">
                    <strong>Items del plan</strong>
                    <span>{len(plan_accion_editable)} acciones activas en este corte.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with plan_info_2:
            st.markdown(
                f"""
                <div class="ideas-quick-card">
                    <strong>Prioridad alta</strong>
                    <span>{int((plan_accion_editable['PRIORIDAD'] == 'Alta').sum())} acciones requieren foco inmediato.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with plan_info_3:
            st.markdown(
                f"""
                <div class="ideas-quick-card">
                    <strong>Oportunidades</strong>
                    <span>{int((plan_accion_editable['CATEGORIA'] == 'Oportunidad de mejora').sum())} items quedaron como mejora evolutiva.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

        plan_grid_df = plan_accion_editable[["EJE", "CATEGORIA", "PRIORIDAD", "RESPONSABLE", "PLAZO", "IMPACTO", "ESTADO", "ACCION"]].rename(
            columns={"EJE": "Area", "CATEGORIA": "Categoria", "ACCION": "Accion"}
        )
        st.caption("Vista ejecutiva del plan antes de entrar al editor detallado.")
        render_aggrid_table(
            plan_grid_df,
            key=f"plan_grid_{diagnostico_id}",
            height=320,
            selection_mode="single",
        )
        st.caption("El plan se autogenera en base al diagnóstico, pero puedes editar responsable, plazo, impacto, acción y estado antes de exportar.")
        plan_tab_vista, plan_tab_editor = st.tabs(["Vista ejecutiva", "Editor detallado"])
        with plan_tab_vista:
            st.markdown(
                """
                <div class="ideas-kpi-band">
                    <strong>Lectura de gestion</strong>
                    <span>La grilla resume prioridades, responsables, plazos y estado general para una lectura rapida antes de intervenir el detalle.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with plan_tab_editor:
            st.markdown(
                """
                <div class="ideas-kpi-band">
                    <strong>Edicion del plan</strong>
                    <span>Debajo se mantiene el editor completo para ajustar responsables, impacto, accion y estado.</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        plan_accion_editable = st.data_editor(
            plan_accion_editable,
            use_container_width=True,
            hide_index=True,
            num_rows="fixed",
            key=f"editor_plan_accion_{diagnostico_id}",
            column_config={
                "EJE": st.column_config.TextColumn("Área", disabled=True),
                "CATEGORIA": st.column_config.TextColumn("Categoría", disabled=True),
                "HALLAZGO": st.column_config.TextColumn("Hallazgo", disabled=True, width="large"),
                "PRIORIDAD": st.column_config.SelectboxColumn("Prioridad", options=["Alta", "Media", "Oportunidad", "Control"]),
                "RESPONSABLE": st.column_config.TextColumn("Responsable", width="medium"),
                "PLAZO": st.column_config.TextColumn("Plazo", width="small"),
                "IMPACTO": st.column_config.SelectboxColumn("Impacto", options=["Alto", "Medio", "Bajo", "Sostener"]),
                "ACCION": st.column_config.TextColumn("Acción sugerida", width="large"),
                "ESTADO": st.column_config.SelectboxColumn("Estado", options=["Pendiente", "En curso", "Definido", "Completado"]),
                "EVIDENCIA": st.column_config.TextColumn("Evidencia", disabled=True),
                "OBSERVACION": st.column_config.TextColumn("Observación", disabled=True, width="large"),
            },
            column_order=["EJE", "CATEGORIA", "PRIORIDAD", "RESPONSABLE", "PLAZO", "IMPACTO", "ACCION", "ESTADO", "EVIDENCIA", "OBSERVACION", "HALLAZGO"],
        )
        st.session_state[plan_state_key] = plan_accion_editable
    else:
        st.info("No hay elementos suficientes para construir un plan de acción.")

    st.markdown('<div class="ideas-subsection-title">Reportes y entregables</div>', unsafe_allow_html=True)
    pdf_col_1, pdf_col_2 = st.columns(2, gap="large")
    fecha_diag = next((f for did, f, s, n, c in diagnosticos if did == diagnostico_id), "")
    with pdf_col_1:
        if st.button("Preparar Reporte Ejecutivo PDF", key="btn_pdf_ejecutivo", use_container_width=True):
            archivo_pdf = generar_pdf_ejecutivo(
                nombre_empresa=empresa_sel,
                fecha=fecha_diag,
                score=score,
                nivel=nivel,
                conclusion=conclusion,
                eje_scores=eje_scores,
                criticas=criticas,
                empresa_info=empresa_info,
            )
            st.session_state["pdf_ejecutivo_path"] = archivo_pdf
    with pdf_col_2:
        if st.button("Preparar Reporte Operativo PDF", key="btn_pdf_operativo", use_container_width=True):
            archivo_pdf_operativo = generar_pdf_operativo(
                nombre_empresa=empresa_sel,
                fecha=fecha_diag,
                score=score,
                nivel=nivel,
                conclusion=conclusion,
                df_resp=df_resp,
                eje_scores_df=eje_scores_df,
                plan_accion_df=st.session_state.get(plan_state_key, plan_accion_df),
                empresa_info=empresa_info,
            )
            st.session_state["pdf_operativo_path"] = archivo_pdf_operativo

    if st.session_state.get("pdf_ejecutivo_path") and os.path.exists(st.session_state["pdf_ejecutivo_path"]):
        with open(st.session_state["pdf_ejecutivo_path"], "rb") as f:
            st.download_button(
                label="Descargar Reporte Ejecutivo",
                data=f,
                file_name=os.path.basename(st.session_state["pdf_ejecutivo_path"]),
                mime="application/pdf",
                key="download_pdf_ejecutivo"
            )
    if st.session_state.get("pdf_operativo_path") and os.path.exists(st.session_state["pdf_operativo_path"]):
        with open(st.session_state["pdf_operativo_path"], "rb") as f:
            st.download_button(
                label="Descargar Reporte Operativo",
                data=f,
                file_name=os.path.basename(st.session_state["pdf_operativo_path"]),
                mime="application/pdf",
                key="download_pdf_operativo"
            )


# ---------------- HISTORIAL ----------------

elif opcion == "Historial":
    render_page_intro(
        "Historial",
        "Historial de diagnósticos",
        "Consultá la base de diagnósticos desde una vista más liviana: empresa, corte, resultado final y contexto corporativo relevante.",
    )
    st.markdown(
        """
        <style>
        .ideas-history-hero {
            border-radius: 30px;
            padding: 1.6rem 1.7rem;
            margin-bottom: 1rem;
            background:
                radial-gradient(circle at top right, rgba(59, 130, 246, 0.22), transparent 26%),
                linear-gradient(135deg, #0f172a 0%, #13263f 50%, #1e3a5f 100%);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 24px 64px rgba(15, 23, 42, 0.18);
            color: #e2e8f0;
        }
        .ideas-history-hero .eyebrow {
            display: inline-flex;
            padding: 0.42rem 0.8rem;
            border-radius: 999px;
            background: rgba(255, 255, 255, 0.1);
            color: #bfdbfe;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.08em;
            text-transform: uppercase;
        }
        .ideas-history-hero h2 {
            margin: 0.8rem 0 0.4rem 0;
            color: #f8fafc;
            font-size: clamp(1.8rem, 2.8vw, 3rem);
            letter-spacing: -0.03em;
            line-height: 1.03;
        }
        .ideas-history-hero p {
            margin: 0;
            max-width: 54rem;
            color: rgba(226, 232, 240, 0.86);
            line-height: 1.7;
        }
        .ideas-history-grid-card {
            border-radius: 24px;
            padding: 1rem 1.1rem;
            margin-bottom: 0.85rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(244,247,251,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.16);
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.06);
        }
        .ideas-history-grid-card .kicker {
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.72rem;
            font-weight: 700;
        }
        .ideas-history-grid-card .title {
            margin-top: 0.45rem;
            color: #0f172a;
            font-size: 1.12rem;
            font-weight: 800;
            letter-spacing: -0.02em;
            line-height: 1.2;
        }
        .ideas-history-grid-card .meta {
            margin-top: 0.45rem;
            color: #64748b;
            font-size: 0.92rem;
            line-height: 1.6;
        }
        .ideas-history-chip {
            display: inline-flex;
            align-items: center;
            padding: 0.38rem 0.72rem;
            margin: 0 0.45rem 0.45rem 0;
            border-radius: 999px;
            background: rgba(241, 245, 249, 0.95);
            border: 1px solid rgba(148, 163, 184, 0.16);
            color: #334155;
            font-size: 0.82rem;
            font-weight: 600;
        }
        .ideas-history-summary {
            border-radius: 28px;
            padding: 1.15rem 1.25rem;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(245,248,252,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.15);
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.06);
        }
        .ideas-history-summary h3 {
            margin: 0 0 0.25rem 0;
            color: #0f172a;
            font-size: 1.12rem;
        }
        .ideas-history-summary p {
            margin: 0;
            color: #64748b;
            line-height: 1.65;
        }
        .ideas-history-kpi {
            border-radius: 24px;
            padding: 1.15rem 1.2rem;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.97) 0%, rgba(244,247,251,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.15);
            min-height: 136px;
        }
        .ideas-history-kpi .label {
            color: #64748b;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-size: 0.76rem;
            font-weight: 700;
        }
        .ideas-history-kpi .value {
            display: block;
            margin-top: 0.45rem;
            color: #0f172a;
            font-size: 2.2rem;
            font-weight: 800;
            letter-spacing: -0.04em;
            line-height: 1;
        }
        .ideas-history-kpi .detail {
            display: block;
            margin-top: 0.55rem;
            color: #475569;
            line-height: 1.6;
            font-size: 0.94rem;
        }
        .ideas-history-detail-card {
            border-radius: 22px;
            padding: 1rem 1.05rem;
            margin-bottom: 0.8rem;
            background: rgba(255, 255, 255, 0.92);
            border: 1px solid rgba(148, 163, 184, 0.14);
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.05);
        }
        .ideas-history-detail-card h4 {
            margin: 0 0 0.55rem 0;
            color: #0f172a;
            font-size: 1rem;
            line-height: 1.45;
            letter-spacing: -0.01em;
            word-break: normal;
            overflow-wrap: normal;
            hyphens: none;
        }
        .ideas-history-detail-card p {
            margin: 0.15rem 0;
            color: #475569;
            line-height: 1.55;
        }
        .ideas-history-list-wrap {
            border-radius: 28px;
            padding: 1rem 1.1rem 0.8rem 1.1rem;
            margin-bottom: 1rem;
            background: linear-gradient(180deg, rgba(255,255,255,0.96) 0%, rgba(244,247,251,0.98) 100%);
            border: 1px solid rgba(148, 163, 184, 0.14);
            box-shadow: 0 18px 38px rgba(15, 23, 42, 0.05);
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    historial_rows = obtener_historial_diagnosticos()
    if not historial_rows:
        st.warning("No hay diagnósticos cargados.")
        st.stop()

    historial_df = pd.DataFrame(
        historial_rows,
        columns=["DIAGNOSTICO_ID", "EMPRESA_ID", "EMPRESA", "FECHA", "SCORE", "NIVEL", "CONCLUSION"]
    )
    historial_df["FECHA_ORDEN"] = pd.to_datetime(historial_df["FECHA"], errors="coerce")
    historial_df = historial_df.sort_values(["EMPRESA_ID", "FECHA_ORDEN"], ascending=[True, True]).reset_index(drop=True)
    historial_df["DIAGNOSTICO_NRO"] = historial_df.groupby("EMPRESA_ID").cumcount() + 1
    historial_df = historial_df.sort_values(["EMPRESA", "FECHA_ORDEN"], ascending=[True, False]).reset_index(drop=True)
    historial_df["DIAGNOSTICO_LABEL"] = historial_df["DIAGNOSTICO_NRO"].apply(lambda x: f"Diagnóstico {x}")
    historial_df["SCORE_FMT"] = historial_df["SCORE"].map(lambda x: f"{float(x):.2f}")

    filtro_a, filtro_b, filtro_c = st.columns(3, gap="large")
    with filtro_a:
        empresa_busqueda = st.text_input("Buscar empresa", key="hist_busqueda", placeholder="Ej. Metalurgica")
    with filtro_b:
        nivel_filtro = st.selectbox("Filtrar por nivel", ["Todos", "Bajo", "Medio", "Alto"], key="hist_nivel_filtro")
    with filtro_c:
        solo_multi = st.selectbox("Diagnósticos por empresa", ["Todos", "Solo empresas con múltiples cortes"], key="hist_multi_filtro")

    historial_filtrado = historial_df.copy()
    if empresa_busqueda.strip():
        historial_filtrado = historial_filtrado[historial_filtrado["EMPRESA"].str.contains(empresa_busqueda.strip(), case=False, na=False)]
    if nivel_filtro != "Todos":
        historial_filtrado = historial_filtrado[historial_filtrado["NIVEL"] == nivel_filtro]
    if solo_multi == "Solo empresas con múltiples cortes":
        empresas_multi = historial_filtrado.groupby("EMPRESA_ID")["DIAGNOSTICO_ID"].transform("count") > 1
        historial_filtrado = historial_filtrado[empresas_multi]

    if historial_filtrado.empty:
        st.warning("No hay diagnósticos para los filtros seleccionados.")
        st.stop()

    st.markdown(
        """
        <div class="ideas-history-list-wrap">
            <div class="ideas-history-grid-card" style="margin-bottom: 0.9rem;">
                <div class="kicker">Base de diagnósticos</div>
                <div class="meta">Selecciona una fila para abrir, editar o duplicar el corte sin pasar por filtros redundantes.</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    historial_grid_df = historial_filtrado[["DIAGNOSTICO_ID", "EMPRESA_ID", "EMPRESA", "DIAGNOSTICO_LABEL", "FECHA", "SCORE_FMT", "NIVEL"]].rename(
        columns={
            "EMPRESA": "Empresa",
            "DIAGNOSTICO_LABEL": "Diagnostico",
            "FECHA": "Fecha",
            "SCORE_FMT": "Score",
            "NIVEL": "Nivel",
        }
    )
    historial_grid_df.insert(0, "Acción", "🗑")
    gb = GridOptionsBuilder.from_dataframe(historial_grid_df)
    gb.configure_default_column(
        sortable=True,
        filter=True,
        resizable=True,
        wrapText=True,
        autoHeight=True,
    )
    gb.configure_grid_options(
        rowHeight=44,
        headerHeight=42,
        domLayout="normal",
        suppressRowClickSelection=False,
    )
    gb.configure_pagination(
        enabled=True,
        paginationAutoPageSize=False,
        paginationPageSize=8,
    )
    gb.configure_selection(selection_mode="single", use_checkbox=False)
    gb.configure_column("DIAGNOSTICO_ID", hide=True)
    gb.configure_column("EMPRESA_ID", hide=True)
    gb.configure_column(
        "Acción",
        headerName="",
        width=70,
        maxWidth=70,
        minWidth=64,
        sortable=False,
        filter=False,
        resizable=False,
        suppressMenu=True,
        pinned="left",
        cellStyle={"textAlign": "center", "fontSize": "1rem", "cursor": "pointer"},
    )
    history_grid_return = JsCode(
        """
        function({eventData}) {
            const api = eventData && eventData.api ? eventData.api : null;
            const selectedRows = api ? api.getSelectedRows() : [];
            let colId = null;
            if (eventData) {
                if (eventData.column && eventData.column.colId) {
                    colId = eventData.column.colId;
                } else if (eventData.colId) {
                    colId = eventData.colId;
                }
            }
            return {
                selected_rows: selectedRows,
                event_data: {
                    colId: colId,
                    data: eventData && eventData.data ? eventData.data : null,
                    type: eventData && eventData.type ? eventData.type : null
                }
            };
        }
        """
    )
    grid_response = AgGrid(
        historial_grid_df,
        gridOptions=gb.build(),
        data_return_mode=DataReturnMode.CUSTOM,
        custom_jscode_for_grid_return=history_grid_return,
        allow_unsafe_jscode=True,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        update_on=["cellClicked", "selectionChanged", "filterChanged", "sortChanged"],
        fit_columns_on_grid_load=True,
        theme="streamlit",
        height=360,
        key="historial_master_grid",
        custom_css={
            ".ag-root-wrapper": {
                "border": "1px solid rgba(148, 163, 184, 0.16)",
                "border-radius": "20px",
                "overflow": "hidden",
                "box-shadow": "0 18px 38px rgba(15, 23, 42, 0.06)",
            },
            ".ag-header": {
                "background-color": "#f8fbff",
                "border-bottom": "1px solid rgba(148, 163, 184, 0.12)",
            },
            ".ag-header-cell-text": {
                "font-weight": "700",
                "color": "#0f172a",
            },
            ".ag-row": {
                "border-bottom": "1px solid rgba(148, 163, 184, 0.08)",
            },
            ".ag-row-hover": {
                "background-color": "rgba(31, 126, 214, 0.06) !important",
            },
            ".ag-row-selected": {
                "background-color": "rgba(15, 143, 97, 0.10) !important",
            },
        },
    )

    event_data = grid_response.get("event_data")
    event_col = obtener_columna_evento_grid(event_data)
    event_row = obtener_data_evento_grid(event_data)
    if event_col == "Acción" and isinstance(event_row, dict):
        try:
            st.session_state["hist_delete_target"] = {
                "diagnostico_id": int(event_row["DIAGNOSTICO_ID"]),
                "empresa": str(event_row["Empresa"]),
                "diagnostico": str(event_row["Diagnostico"]),
            }
        except Exception:
            pass

    crm1, crm2, crm3 = st.columns(3, gap="large")
    with crm1:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Empresas registradas</span>
                <span class="value">{historial_filtrado['EMPRESA_ID'].nunique()}</span>
                <span class="detail">Organizaciones visibles según filtros aplicados.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with crm2:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Diagnósticos visibles</span>
                <span class="value">{len(historial_filtrado)}</span>
                <span class="detail">Cortes disponibles en esta vista consultiva.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with crm3:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Empresas con evolución</span>
                <span class="value">{int((historial_filtrado.groupby('EMPRESA_ID')['DIAGNOSTICO_ID'].count() > 1).sum())}</span>
                <span class="detail">Casos con más de un corte para comparar evolución.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    if historial_filtrado.empty:
        st.warning("No hay diagnósticos para los filtros seleccionados.")
        st.stop()

    selected_rows = grid_response.get("selected_rows", []) or []
    selected_row = selected_rows[0] if selected_rows else historial_grid_df.iloc[0].to_dict()

    delete_target = st.session_state.get("hist_delete_target")
    if delete_target:
        st.warning(
            f"Vas a eliminar {delete_target['diagnostico']} de {delete_target['empresa']}. Esta acción borra también sus respuestas."
        )
        delete_col_1, delete_col_2 = st.columns(2, gap="small")
        with delete_col_1:
            if st.button("Confirmar eliminación", key="hist_confirm_delete", use_container_width=True):
                eliminar_diagnostico(int(delete_target["diagnostico_id"]))
                st.session_state["hist_delete_target"] = None
                st.session_state["hist_last_deleted_msg"] = (
                    f"Se eliminó {delete_target['diagnostico']} de {delete_target['empresa']}."
                )
                st.rerun()
        with delete_col_2:
            if st.button("Cancelar", key="hist_cancel_delete", use_container_width=True):
                st.session_state["hist_delete_target"] = None
                st.rerun()

    deleted_msg = st.session_state.pop("hist_last_deleted_msg", None)
    if deleted_msg:
        st.success(deleted_msg)

    empresa_sel = str(selected_row["Empresa"])
    empresa_id = int(selected_row["EMPRESA_ID"])
    diagnostico_id = int(selected_row["DIAGNOSTICO_ID"])
    empresa_rows = historial_filtrado[historial_filtrado["EMPRESA"] == empresa_sel].copy()
    empresa_info = obtener_empresa_detalle(empresa_id)
    empresa_rows = empresa_rows.sort_values("FECHA", ascending=False).reset_index(drop=True)
    if empresa_rows.empty:
        st.warning("No quedan diagnósticos disponibles para la selección actual.")
        st.stop()
    if diagnostico_id not in empresa_rows["DIAGNOSTICO_ID"].tolist():
        fallback_row = empresa_rows.iloc[0]
        empresa_sel = str(fallback_row["EMPRESA"])
        empresa_id = int(fallback_row["EMPRESA_ID"])
        diagnostico_id = int(fallback_row["DIAGNOSTICO_ID"])
        empresa_info = obtener_empresa_detalle(empresa_id)
    diagnosticos_empresa = obtener_diagnosticos_empresa(empresa_id)
    diag_actual_candidates = empresa_rows[empresa_rows["DIAGNOSTICO_ID"] == diagnostico_id]
    if diag_actual_candidates.empty:
        st.warning("No se encontró el diagnóstico seleccionado. Actualiza la vista e intenta nuevamente.")
        st.stop()
    diag_actual_row = diag_actual_candidates.iloc[0]
    diag_sel = f"{diag_actual_row['DIAGNOSTICO_LABEL']} | {diag_actual_row['FECHA']} | Score {float(diag_actual_row['SCORE']):.2f} | {diag_actual_row['NIVEL']}"
    st.markdown(
        f"""
        <div class="ideas-history-grid-card">
            <div class="kicker">Corte activo</div>
            <div class="meta"><strong>{html_safe(empresa_sel)}</strong> · {html_safe(diag_sel)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown("**Acciones del corte seleccionado**")
    action_col_1, action_col_2, action_col_3 = st.columns(3, gap="large")
    with action_col_1:
        if st.button("Abrir en Resultados", key="hist_to_results", use_container_width=True):
            st.session_state["res_empresa_pref"] = empresa_sel
            st.session_state["res_diag_pref"] = diagnostico_id
            st.info("Ve a Resultados y se cargará este corte automáticamente.")
    with action_col_2:
        if st.button("Editar este diagnóstico", key="hist_to_edit_diag", use_container_width=True):
            st.session_state["diag_edit_pref_id"] = diagnostico_id
            st.session_state["diag_edit_pref_empresa"] = empresa_sel
            st.session_state["force_nav_option"] = "Nuevo Diagnóstico"
            st.rerun()
    with action_col_3:
        if st.button("Duplicar como nuevo diagnóstico", key="hist_to_duplicate_diag", use_container_width=True):
            st.session_state["diag_duplicate_pref_id"] = diagnostico_id
            st.session_state["diag_duplicate_pref_empresa"] = empresa_sel
            st.session_state["force_nav_option"] = "Nuevo Diagnóstico"
            st.rerun()

    chips = []
    if empresa_info:
        if empresa_info.get("ubicacion"):
            chips.append(f"Ubicación: {empresa_info['ubicacion']}")
        if empresa_info.get("rubro"):
            chips.append(f"Rubro: {empresa_info['rubro']}")
        if empresa_info.get("cantidad_empleados") not in (None, ""):
            chips.append(f"Dotación: {empresa_info['cantidad_empleados']}")
    chips.append(f"Cortes: {len(empresa_rows)}")
    if chips:
        st.markdown(
            '<div class="ideas-history-grid-card"><div class="kicker">Ficha rápida</div><div class="meta">'
            + "".join(f'<span class="ideas-history-chip">{html_safe(chip)}</span>' for chip in chips)
            + "</div></div>",
            unsafe_allow_html=True,
        )

    respuestas = obtener_respuestas_diagnostico(diagnostico_id)
    if not respuestas:
        st.warning("No se encontraron respuestas para este diagnóstico.")
        st.stop()

    df_hist = pd.DataFrame(
        respuestas,
        columns=["EJE", "PREGUNTA", "RESPUESTA", "EVIDENCIA", "OBSERVACION"]
    )

    diag_actual = next(item for item in diagnosticos_empresa if item[0] == diagnostico_id)
    fecha_diag = diag_actual[1]
    score = float(diag_actual[2])
    nivel = diag_actual[3]
    conclusion = diag_actual[4]
    mensaje_direccion = obtener_mensaje_direccion(nivel)

    eje_scores_df = df_hist.groupby("EJE", dropna=True)["RESPUESTA"].mean().reset_index()
    eje_scores_df = eje_scores_df.sort_values("RESPUESTA", ascending=False)
    mejor_eje = eje_scores_df.iloc[0]
    eje_prioritario = eje_scores_df.sort_values("RESPUESTA", ascending=True).iloc[0]
    total_ejes = int(eje_scores_df["EJE"].nunique())
    respuestas_criticas = int((df_hist["RESPUESTA"] <= 2).sum())
    evidencias_cargadas = int(df_hist["EVIDENCIA"].fillna("").astype(str).str.strip().ne("").sum())

    historico_df = pd.DataFrame(
        diagnosticos_empresa,
        columns=["DIAGNOSTICO_ID", "FECHA", "SCORE", "NIVEL", "CONCLUSION"]
    ).sort_values("FECHA")
    score_anterior = None
    if len(historico_df) > 1:
        prev_rows = historico_df[historico_df["DIAGNOSTICO_ID"] != diagnostico_id]
        if not prev_rows.empty:
            score_anterior = float(prev_rows.iloc[-1]["SCORE"])
    delta_score = round(score - score_anterior, 2) if score_anterior is not None else None
    delta_score_texto, delta_score_clase = obtener_delta_texto(delta_score)

    fortalezas = eje_scores_df.sort_values("RESPUESTA", ascending=False).head(3)
    debilidades = eje_scores_df.sort_values("RESPUESTA", ascending=True).head(3)

    certificaciones = []
    if empresa_info:
        if valor_afirmativo(empresa_info.get("cert_iso_9001")):
            certificaciones.append("ISO 9001")
        if valor_afirmativo(empresa_info.get("cert_iso_14001")):
            certificaciones.append("ISO 14001")
        if valor_afirmativo(empresa_info.get("cert_iso_45001")):
            certificaciones.append("ISO 45001")
        if valor_afirmativo(empresa_info.get("cert_iatf")):
            certificaciones.append("IATF")

    st.markdown(
        f"""
        <div class="ideas-history-hero">
            <span class="eyebrow">Database Overview</span>
            <h2>{html_safe(empresa_sel)}</h2>
            <p>
                Diagnóstico seleccionado: <strong>{html_safe(diag_sel)}</strong>.
                {html_safe(mensaje_direccion)} Esta vista resume resultado final, puntos fuertes, puntos débiles y datos clave de la empresa.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="ideas-history-summary">
            <h3>Resultado final del diagnóstico</h3>
            <p>{html_safe(conclusion)}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    kpi1, kpi2, kpi3, kpi4 = st.columns(4, gap="large")
    with kpi1:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Score global</span>
                <span class="value">{score:.2f}</span>
                <span class="detail">Lectura consolidada del corte seleccionado.</span>
                <span class="detail"><span class="ideas-delta {delta_score_clase}">{delta_score_texto}</span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi2:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Nivel ejecutivo</span>
                <span class="value">{html_safe(nivel)}</span>
                <span class="detail">{html_safe(obtener_prioridad_recomendada(nivel))}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi3:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Cobertura</span>
                <span class="value">{total_ejes}</span>
                <span class="detail">{evidencias_cargadas} registros con evidencia declarada en este corte.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with kpi4:
        st.markdown(
            f"""
            <div class="ideas-history-kpi">
                <span class="label">Área prioritaria de mejora</span>
                <span class="value">{html_safe(eje_prioritario["EJE"])}</span>
                <span class="detail">{respuestas_criticas} respuestas requieren seguimiento. Mejor performance: {html_safe(mejor_eje["EJE"])}.</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

    col_fortalezas, col_contexto = st.columns([1.15, 1], gap="large")
    with col_fortalezas:
        render_soft_panel(
            "Fortalezas y debilidades",
            "Resumen ejecutivo del diagnóstico seleccionado sin bajar al detalle operativo completo.",
        )
        sub_fort, sub_deb = st.columns(2, gap="large")
        with sub_fort:
            st.markdown(
                """
                <div class="ideas-history-grid-card">
                    <div class="kicker">Puntos fuertes</div>
                    <div class="meta">Ejes con mejor lectura relativa dentro del corte seleccionado.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for _, row in fortalezas.iterrows():
                st.markdown(
                    f"""
                    <div class="ideas-history-detail-card">
                        <h4>{html_safe(row["EJE"])}</h4>
                        <p><strong>Score:</strong> {float(row["RESPUESTA"]):.2f} | <strong>Nivel:</strong> {html_safe(obtener_nivel(float(row["RESPUESTA"])))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        with sub_deb:
            st.markdown(
                """
                <div class="ideas-history-grid-card">
                    <div class="kicker">Puntos débiles</div>
                    <div class="meta">Ejes que concentran la prioridad de mejora y seguimiento.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            for _, row in debilidades.iterrows():
                st.markdown(
                    f"""
                    <div class="ideas-history-detail-card">
                        <h4>{html_safe(row["EJE"])}</h4>
                        <p><strong>Score:</strong> {float(row["RESPUESTA"]):.2f} | <strong>Nivel:</strong> {html_safe(obtener_nivel(float(row["RESPUESTA"])))}</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    with col_contexto:
        render_soft_panel(
            "Contexto corporativo",
            "Ficha completa de la empresa para leer el diagnóstico dentro del contexto correcto.",
        )
        contacto_lineas = []
        if empresa_info:
            if empresa_info.get("contacto_nombre"):
                contacto_lineas.append(empresa_info["contacto_nombre"])
            if empresa_info.get("contacto_posicion"):
                contacto_lineas.append(empresa_info["contacto_posicion"])
            if empresa_info.get("contacto_correo"):
                contacto_lineas.append(empresa_info["contacto_correo"])
            if empresa_info.get("contacto_telefono"):
                contacto_lineas.append(empresa_info["contacto_telefono"])
        resumen_contexto = [
            ("Razón social", empresa_info.get("razon_social") if empresa_info else empresa_sel),
            ("Ubicación", empresa_info.get("ubicacion") if empresa_info else ""),
            ("Rubro", empresa_info.get("rubro") if empresa_info else ""),
            ("Dotación", str(empresa_info.get("cantidad_empleados")) if empresa_info and empresa_info.get("cantidad_empleados") not in (None, "") else ""),
            ("Contacto", " | ".join(contacto_lineas)),
            ("Certificaciones", ", ".join(certificaciones) if certificaciones else "Sin certificaciones declaradas"),
        ]
        for titulo, valor in resumen_contexto:
            if valor:
                st.markdown(
                    f"""
                    <div class="ideas-history-grid-card">
                        <div class="kicker">{html_safe(titulo)}</div>
                        <div class="meta">{html_safe(valor)}</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
    st.markdown(
        """
        <div class="ideas-history-grid-card">
            <div class="kicker">Resumen de base</div>
            <div class="meta">La pantalla prioriza lectura general y navegación entre cortes. El detalle operativo completo queda disponible en Resultados y en el reporte ejecutivo.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
