from __future__ import annotations

import html
import json
import os
import platform
from pathlib import Path

if platform.system() == "Windows":
    msys2_dll_dir = Path("C:/msys64/mingw64/bin")
    if msys2_dll_dir.exists():
        os.environ.setdefault("WEASYPRINT_DLL_DIRECTORIES", str(msys2_dll_dir))

try:
    from weasyprint import HTML
except OSError as exc:
    HTML = None
    WEASYPRINT_IMPORT_ERROR = exc
else:
    WEASYPRINT_IMPORT_ERROR = None

from ideas_utils import (
    limpiar_nombre_archivo,
    obtener_acciones_nivel,
    obtener_logo_path,
    obtener_mensaje_direccion,
    obtener_nivel,
    obtener_prioridad_recomendada,
    valor_afirmativo,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reportes" / "premium"
TMP_DIR = REPORTS_DIR / "tmp"
LOGO_PATH = obtener_logo_path()


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _pct(score: float, minimum: float = 1.0, maximum: float = 4.0) -> float:
    score = max(minimum, min(float(score or 0), maximum))
    return ((score - minimum) / (maximum - minimum)) * 100


def _logo_html() -> str:
    if not LOGO_PATH:
        return ""
    path = Path(LOGO_PATH)
    if not path.exists():
        return ""
    return f'<img class="logo" src="{path.resolve().as_uri()}" alt="IDEAS logo">'


def _file_uri(path_like: str | None) -> str:
    if not path_like:
        return ""
    path = Path(str(path_like).strip())
    if not path.exists():
        return ""
    return path.resolve().as_uri()


def _brand_logo_html(custom_logo: str | None = None) -> str:
    custom_uri = _file_uri(custom_logo)
    if custom_uri:
        return f'<img class="logo" src="{custom_uri}" alt="Logo empresa">'
    return _logo_html()


def _sanitize_color(value: str | None, fallback: str) -> str:
    text = str(value or "").strip()
    if text.startswith("#") and len(text) in {4, 7}:
        return text
    return fallback


def _base_style() -> str:
    return """
    <style>
        @page { size: A4; margin: 18mm 16mm; }
        :root {
            --ideas-navy: #0f172a;
            --ideas-blue: #1f7ed6;
            --ideas-green: #0f8f61;
            --ideas-line: #dbe3ec;
            --ideas-soft: #f5f8fb;
            --ideas-red: #ef4444;
            --ideas-amber: #d97706;
            --ideas-slate: #475569;
        }
        body {
            font-family: "Segoe UI", Arial, sans-serif;
            color: var(--ideas-slate);
            font-size: 10.5pt;
            line-height: 1.48;
        }
        .topbar {
            height: 10px;
            background: linear-gradient(90deg, var(--ideas-navy), var(--ideas-blue), var(--ideas-green));
            border-radius: 999px;
            margin-bottom: 22px;
        }
        header { display: flex; align-items: center; gap: 16px; margin-bottom: 20px; }
        .logo { width: 58px; height: 58px; object-fit: contain; }
        .brand { color: var(--ideas-green); font-weight: 800; letter-spacing: .12em; font-size: 9pt; text-transform: uppercase; }
        h1 { color: var(--ideas-navy); font-size: 25pt; line-height: 1.05; margin: 3px 0 5px; }
        h2 { color: var(--ideas-navy); font-size: 15pt; margin: 22px 0 10px; }
        h3 { color: var(--ideas-navy); font-size: 11.5pt; margin: 0 0 7px; }
        .subtitle { color: #64748b; max-width: 660px; }
        .hero {
            background: linear-gradient(135deg, #f8fbff, #eef7f3);
            border: 1px solid var(--ideas-line);
            border-radius: 18px;
            padding: 18px;
            margin: 14px 0;
        }
        .metrics { display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; margin: 14px 0; }
        .card {
            border: 1px solid var(--ideas-line);
            border-radius: 14px;
            padding: 13px;
            background: white;
        }
        .label { color: #64748b; font-size: 8pt; font-weight: 800; letter-spacing: .08em; text-transform: uppercase; }
        .value { color: var(--ideas-navy); font-size: 22pt; font-weight: 800; margin-top: 5px; }
        .green { color: var(--ideas-green); }
        .blue { color: var(--ideas-blue); }
        .red { color: var(--ideas-red); }
        .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
        .pill {
            display: inline-block;
            padding: 5px 10px;
            border-radius: 999px;
            background: #e8f3ff;
            color: #135c9f;
            font-weight: 700;
            font-size: 8.5pt;
            margin: 3px 4px 3px 0;
        }
        .bar-row { margin: 9px 0; }
        .bar-head { display: flex; justify-content: space-between; color: var(--ideas-navy); font-weight: 700; }
        .bar-track { background: #e5eaf0; border-radius: 999px; height: 12px; overflow: hidden; margin-top: 5px; }
        .bar-fill { height: 12px; border-radius: 999px; background: linear-gradient(90deg, var(--ideas-red), var(--ideas-amber), var(--ideas-green)); }
        table { width: 100%; border-collapse: collapse; margin-top: 8px; }
        th { background: var(--ideas-navy); color: white; text-align: left; padding: 8px; font-size: 8.5pt; }
        td { border-bottom: 1px solid var(--ideas-line); padding: 8px; vertical-align: top; }
        .alert { background: #fef2f2; color: #7f1d1d; border: 1px solid #fecaca; border-radius: 12px; padding: 12px; }
        .section { page-break-inside: avoid; }
        footer { margin-top: 26px; padding-top: 10px; border-top: 1px solid var(--ideas-line); color: #94a3b8; font-size: 8pt; }
    </style>
    """


def _base_style_custom(primary: str | None = None, secondary: str | None = None) -> str:
    return _base_style().replace("--ideas-blue: #1f7ed6;", f"--ideas-blue: {_sanitize_color(primary, '#1f7ed6')};").replace(
        "--ideas-green: #0f8f61;",
        f"--ideas-green: {_sanitize_color(secondary, '#0f8f61')};",
    )


def _write_pdf(html_content: str, path: Path) -> Path:
    if HTML is None:
        raise RuntimeError(
            "WeasyPrint esta instalado, pero faltan librerias del sistema para renderizar PDFs "
            f"({WEASYPRINT_IMPORT_ERROR}). En Windows instala MSYS2/Pango o configura WEASYPRINT_DLL_DIRECTORIES."
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=html_content, base_url=str(ROOT)).write_pdf(str(path))
    return path.resolve()


def _certificaciones(empresa_info: dict) -> list[str]:
    return [
        label
        for key, label in [
            ("cert_iso_9001", "ISO 9001"),
            ("cert_iso_14001", "ISO 14001"),
            ("cert_iso_45001", "ISO 45001"),
            ("cert_iatf", "IATF 16949"),
        ]
        if valor_afirmativo(empresa_info.get(key))
    ]


def generar_pdf_ejecutivo_v2(
    nombre_empresa: str,
    fecha: str,
    score: float,
    nivel: str,
    conclusion: str,
    eje_scores: dict[str, float],
    criticas: list[str],
    empresa_info: dict | None = None,
) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    empresa_info = empresa_info or {}
    slug = limpiar_nombre_archivo(nombre_empresa or "empresa")
    fecha_slug = limpiar_nombre_archivo(str(fecha or "sin_fecha").replace("/", "-").replace(":", "-"))
    pdf_path = TMP_DIR / f"reporte_{slug}_{fecha_slug}.pdf"

    certificaciones = _certificaciones(empresa_info)
    oportunidades = criticas[:6] if criticas else ["No se identificaron oportunidades criticas en este corte."]
    top_areas = sorted((eje_scores or {}).items(), key=lambda item: item[1])

    area_rows = "\n".join(
        f"""
        <tr>
            <td>{_esc(area)}</td>
            <td>{float(area_score):.2f}</td>
            <td>{_esc(obtener_nivel(area_score))}</td>
            <td>{_esc('Alta' if area_score < 2 else 'Media' if area_score < 3 else 'Sostener')}</td>
        </tr>
        """
        for area, area_score in top_areas
    )
    bars = "\n".join(
        f"""
        <div class="bar-row">
            <div class="bar-head"><span>{_esc(area)}</span><span>{float(area_score):.2f}</span></div>
            <div class="bar-track"><div class="bar-fill" style="width:{_pct(area_score):.1f}%"></div></div>
        </div>
        """
        for area, area_score in sorted((eje_scores or {}).items(), key=lambda item: item[1], reverse=True)
    )
    opportunities_html = "".join(f"<li>{_esc(item)}</li>" for item in oportunidades)
    actions_html = "".join(f"<li>{_esc(item)}</li>" for item in obtener_acciones_nivel(nivel))
    certs_html = "".join(f'<span class="pill">{_esc(item)}</span>' for item in certificaciones) or '<span class="pill">Sin certificaciones registradas</span>'

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {_logo_html()}
            <div>
                <div class="brand">IDEAS Consulting</div>
                <h1>Reporte Ejecutivo Premium</h1>
                <div class="subtitle">Sintesis de madurez organizacional para direccion, prioridades de gestion y lectura institucional.</div>
            </div>
        </header>

        <section class="hero">
            <div class="label">Empresa</div>
            <h2>{_esc(nombre_empresa)}</h2>
            <div>{_esc(fecha)} · {_esc(empresa_info.get("rubro") or "Rubro sin definir")} · {_esc(empresa_info.get("ubicacion") or "Ubicacion sin definir")}</div>
            <div style="margin-top:10px">{certs_html}</div>
        </section>

        <section class="metrics">
            <div class="card"><div class="label">Score global</div><div class="value blue">{float(score):.2f}</div></div>
            <div class="card"><div class="label">Nivel actual</div><div class="value green">{_esc(nivel)}</div></div>
            <div class="card"><div class="label">Prioridad</div><div class="value red">{_esc(obtener_prioridad_recomendada(nivel))}</div></div>
        </section>

        <section class="grid-2 section">
            <div class="card" style="border-color:#fecaca;background:#fef2f2;">
                <h3>Lectura de direccion</h3>
                <p>{_esc(obtener_mensaje_direccion(nivel))}</p>
            </div>
            <div class="card" style="border-color:#bbf7d0;background:#f0fdf4;">
                <h3>Sintesis consultiva</h3>
                <p>{_esc(conclusion)}</p>
            </div>
        </section>

        <section class="section">
            <h2>Performance por area</h2>
            <div class="card">{bars}</div>
        </section>

        <section class="section">
            <h2>Prioridades ejecutivas</h2>
            <table>
                <thead><tr><th>Area</th><th>Score</th><th>Nivel</th><th>Prioridad</th></tr></thead>
                <tbody>{area_rows}</tbody>
            </table>
        </section>

        <section class="grid-2 section">
            <div class="card">
                <h3>Oportunidades prioritarias</h3>
                <ul>{opportunities_html}</ul>
            </div>
            <div class="card">
                <h3>Acciones recomendadas</h3>
                <ul>{actions_html}</ul>
            </div>
        </section>

        <footer>IDEAS Consulting · Reporte generado automaticamente desde la plataforma</footer>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_pdf_8d(problema_data: dict, acciones_data: list[dict] | None = None) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    acciones_data = acciones_data or []
    empresa = problema_data.get("empresa") or problema_data.get("razon_social") or "Empresa"
    titulo = problema_data.get("titulo") or "Analisis 8D"
    fecha = problema_data.get("fecha") or "sin_fecha"
    slug = limpiar_nombre_archivo(f"{empresa}_{titulo}_{fecha}".replace("/", "-").replace(":", "-"))
    pdf_path = TMP_DIR / f"reporte_8d_{slug}.pdf"

    acciones_d5_d6 = [
        accion for accion in acciones_data if str(accion.get("fase_8d") or "").strip().upper() in {"D5", "D6"}
    ] or acciones_data
    acciones_rows = "\n".join(
        f"""
        <tr>
            <td>{_esc(accion.get("fase_8d") or "-")}</td>
            <td>{_esc(accion.get("accion") or "-")}</td>
            <td>{_esc(accion.get("responsable") or "-")}</td>
            <td>{_esc(accion.get("fecha") or "-")}</td>
            <td>{_esc(accion.get("progreso") or "-")}</td>
        </tr>
        """
        for accion in acciones_d5_d6
    ) or '<tr><td colspan="5">Sin acciones D5/D6 registradas.</td></tr>'

    ishikawa_fields = [
        ("Efecto", problema_data.get("efecto")),
        ("Mano de obra", problema_data.get("mano_obra")),
        ("Maquina", problema_data.get("maquina")),
        ("Material", problema_data.get("material")),
        ("Metodo", problema_data.get("metodo")),
        ("Medicion", problema_data.get("medicion")),
        ("Medio ambiente", problema_data.get("medio_ambiente")),
        ("Factores retenidos", problema_data.get("factores_retenidos")),
    ]
    ishikawa_html = "".join(f"<li><strong>{_esc(label)}:</strong> {_esc(value or 'Sin dato')}</li>" for label, value in ishikawa_fields)

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {_logo_html()}
            <div>
                <div class="brand">IDEAS Consulting</div>
                <h1>Reporte Ejecutivo 8D</h1>
                <div class="subtitle">Analisis estructurado del problema, causa raiz y acciones correctivas D5/D6.</div>
            </div>
        </header>

        <section class="hero">
            <div class="label">Problema</div>
            <h2>{_esc(titulo)}</h2>
            <div>{_esc(empresa)} · {_esc(fecha)} · Estado: {_esc(problema_data.get("estado") or "Abierto")}</div>
        </section>

        <section class="grid-2 section">
            <div class="card"><h3>Origen</h3><p>{_esc(problema_data.get("origen") or "Sin origen informado")}</p></div>
            <div class="card"><h3>D2 · Descripcion</h3><p>{_esc(problema_data.get("d2_descripcion") or "Sin descripcion registrada")}</p></div>
        </section>

        <section class="grid-2 section">
            <div class="card"><h3>D3 · Contencion</h3><p>{_esc(problema_data.get("d3_contencion") or "Sin contencion registrada")}</p></div>
            <div class="card"><h3>D4 · Causa raiz</h3><p>{_esc(problema_data.get("d4_causa_raiz") or "Sin causa raiz registrada")}</p></div>
        </section>

        <section class="section">
            <h2>Ishikawa</h2>
            <div class="card"><ul>{ishikawa_html}</ul></div>
        </section>

        <section class="section">
            <h2>Acciones D5/D6</h2>
            <table>
                <thead><tr><th>Fase</th><th>Accion</th><th>Responsable</th><th>Fecha limite</th><th>Progreso</th></tr></thead>
                <tbody>{acciones_rows}</tbody>
            </table>
        </section>

        <section class="grid-2 section">
            <div class="card"><h3>D7 · Prevencion</h3><p>{_esc(problema_data.get("d7_prevencion") or "Sin prevencion registrada")}</p></div>
            <div class="card"><h3>D8 · Cierre</h3><p>{_esc(problema_data.get("d8_cierre") or "Sin cierre registrado")}</p></div>
        </section>

        <footer>IDEAS Consulting · Reporte 8D generado automaticamente desde la plataforma</footer>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_pdf_8d(problema_data: dict, acciones_data: list[dict] | None = None) -> Path:
    import json

    TMP_DIR.mkdir(parents=True, exist_ok=True)
    acciones_data = acciones_data or []
    empresa = problema_data.get("razon_social") or problema_data.get("empresa") or "Empresa"
    titulo = problema_data.get("titulo") or "Analisis 8D"
    fecha = problema_data.get("fecha") or "sin_fecha"
    slug = limpiar_nombre_archivo(f"{empresa}_{titulo}_{fecha}".replace("/", "-").replace(":", "-"))
    pdf_path = TMP_DIR / f"reporte_8d_{slug}.pdf"

    style = _base_style_custom(problema_data.get("color_primario"), problema_data.get("color_secundario"))
    brand_logo = _brand_logo_html(problema_data.get("logo_path"))
    numero_8d = problema_data.get("numero_8d") or "-"
    estado = problema_data.get("estado") or "Abierto"
    nok_ok = problema_data.get("nok_ok_details") if isinstance(problema_data.get("nok_ok_details"), dict) else json.loads(str(problema_data.get("nok_ok_details") or "{}"))
    d3_details = problema_data.get("d3_sorting_details") if isinstance(problema_data.get("d3_sorting_details"), dict) else json.loads(str(problema_data.get("d3_sorting_details") or "{}"))
    d4_details = problema_data.get("d4_simulation_details") if isinstance(problema_data.get("d4_simulation_details"), dict) else json.loads(str(problema_data.get("d4_simulation_details") or "{}"))
    d5_training = problema_data.get("d5_training_details") if isinstance(problema_data.get("d5_training_details"), dict) else json.loads(str(problema_data.get("d5_training_details") or "{}"))
    d7_docs = problema_data.get("d7_docs_update") if isinstance(problema_data.get("d7_docs_update"), dict) else json.loads(str(problema_data.get("d7_docs_update") or "{}"))
    d8_closure = problema_data.get("d8_closure_details") if isinstance(problema_data.get("d8_closure_details"), dict) else json.loads(str(problema_data.get("d8_closure_details") or "{}"))

    def build_actions_rows(fase: str) -> str:
        rows = [accion for accion in acciones_data if str(accion.get("fase_8d") or "").strip().upper() == fase]
        return "\n".join(
            f"""
            <tr>
                <td>{_esc(accion.get("accion") or "-")}</td>
                <td>{_esc(accion.get("responsable") or "-")}</td>
                <td>{_esc(accion.get("fecha") or "-")}</td>
                <td>{_esc(accion.get("progreso") or "-")}</td>
            </tr>
            """
            for accion in rows
        ) or '<tr><td colspan="4">Sin acciones registradas.</td></tr>'

    docs_rows = "\n".join(
        f"""
        <tr>
            <td>{_esc(doc_name)}</td>
            <td>{'Si' if bool(values.get('checked')) else 'No'}</td>
            <td>{_esc(values.get('reviewed_at') or '-')}</td>
            <td>{_esc(values.get('updated_at') or '-')}</td>
            <td>{_esc(values.get('comments') or '-')}</td>
        </tr>
        """
        for doc_name, values in (d7_docs.get("documents") or {}).items()
    ) or '<tr><td colspan="5">Sin revisiones documentales registradas.</td></tr>'

    closure_rows = "\n".join(
        f"""
        <tr>
            <td>{_esc(label)}</td>
            <td>{_esc((d8_closure.get(key) or {}).get('nombre') or '-')}</td>
            <td>{_esc((d8_closure.get(key) or {}).get('fecha') or '-')}</td>
        </tr>
        """
        for key, label in [
            ("problem_coordinator", "Problem Coordinator"),
            ("responsible_q", "Responsible Q"),
            ("ap_team_leader", "AP-team leader"),
        ]
    )

    ishikawa_fields = [
        ("Efecto", problema_data.get("efecto")),
        ("Mano de obra", problema_data.get("mano_obra")),
        ("Maquina", problema_data.get("maquina")),
        ("Material", problema_data.get("material")),
        ("Metodo", problema_data.get("metodo")),
        ("Medicion", problema_data.get("medicion")),
        ("Medio ambiente", problema_data.get("medio_ambiente")),
        ("Factores retenidos", problema_data.get("factores_retenidos")),
    ]
    ishikawa_html = "".join(f"<li><strong>{_esc(label)}:</strong> {_esc(value or 'Sin dato')}</li>" for label, value in ishikawa_fields)

    nok_image = _file_uri(nok_ok.get("nok_part_image"))
    ok_image = _file_uri(nok_ok.get("ok_part_image"))
    image_cards = ""
    if nok_image or ok_image:
        image_cards = f"""
        <section class="grid-2 section">
            <div class="card">
                <h3>Pieza NOK</h3>
                <p>{_esc(nok_ok.get('nok_part') or 'Sin descripcion')}</p>
                {'<img style="width:100%;max-height:260px;object-fit:contain;border-radius:12px;border:1px solid #fecaca;background:#fff" src="' + nok_image + '">' if nok_image else '<p>Sin imagen NOK.</p>'}
            </div>
            <div class="card">
                <h3>Pieza OK</h3>
                <p>{_esc(nok_ok.get('ok_part') or 'Sin descripcion')}</p>
                {'<img style="width:100%;max-height:260px;object-fit:contain;border-radius:12px;border:1px solid #bbf7d0;background:#fff" src="' + ok_image + '">' if ok_image else '<p>Sin imagen OK.</p>'}
            </div>
        </section>
        """

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{style}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {brand_logo}
            <div>
                <div class="brand">{_esc(empresa)}</div>
                <h1>Reporte 8D</h1>
                <div class="subtitle">Visual management del analisis 8D, con evidencia, causa raiz, acciones y cierre.</div>
            </div>
        </header>

        <section class="hero">
            <div class="label">Caso</div>
            <h2>{_esc(titulo)}</h2>
            <div>{_esc(empresa)} · 8D: {_esc(numero_8d)} · {_esc(fecha)} · Estado: {_esc(estado)}</div>
            <div style="margin-top:10px;">Origen: {_esc(problema_data.get("origen") or "-")} · Proyecto: {_esc(problema_data.get("customer_project") or "-")} · Fault type: {_esc(problema_data.get("fault_type") or "-")}</div>
        </section>

        <section class="metrics">
            <div class="card"><div class="label">Safety Relevant</div><div class="value {'red' if problema_data.get('safety_relevant') else 'blue'}">{'Si' if problema_data.get('safety_relevant') else 'No'}</div></div>
            <div class="card"><div class="label">Repetitive Fault</div><div class="value {'red' if problema_data.get('repetitive_fault') else 'blue'}">{'Si' if problema_data.get('repetitive_fault') else 'No'}</div></div>
            <div class="card"><div class="label">Equipo D1</div><div class="value blue">{len([line for line in str(problema_data.get('d1_equipo') or '').splitlines() if line.strip()])}</div></div>
        </section>

        <section class="grid-2 section">
            <div class="card"><h3>D1 · Equipo multifuncional</h3><p>{_esc(problema_data.get("d1_equipo") or "Sin equipo registrado")}</p></div>
            <div class="card"><h3>D2 · Descripcion del problema</h3><p>{_esc(problema_data.get("d2_descripcion") or "Sin descripcion registrada")}</p></div>
        </section>

        {image_cards}

        <section class="grid-2 section">
            <div class="card">
                <h3>D3 · Contencion</h3>
                <p>{_esc(problema_data.get("d3_contencion") or "Sin contencion registrada")}</p>
                <p><strong>Sorting required:</strong> {'Si' if d3_details.get('sorting_required') else 'No'}</p>
                <p><strong>Empleados informados:</strong> {'Si' if d3_details.get('employees_informed') else 'No'}</p>
            </div>
            <div class="card">
                <h3>D4 · Causa raiz</h3>
                <p>{_esc(problema_data.get("d4_causa_raiz") or "Sin causa raiz registrada")}</p>
                <p><strong>Ocurrencia:</strong> {_esc(d4_details.get('occ_root') or '-')}</p>
                <p><strong>No deteccion:</strong> {_esc(d4_details.get('det_root') or '-')}</p>
                <p><strong>Simulacion posible:</strong> {'Si' if d4_details.get('simulation_possible') else 'No'}</p>
                <p><strong>Match fault:</strong> {'Si' if d4_details.get('match_fault') else 'No'}</p>
            </div>
        </section>

        <section class="section">
            <h2>D3 · Plan de acciones</h2>
            <table>
                <thead><tr><th>Accion</th><th>Responsable</th><th>Fecha</th><th>Status</th></tr></thead>
                <tbody>{build_actions_rows('D3')}</tbody>
            </table>
        </section>

        <section class="section">
            <h2>Ishikawa y 5 Porques</h2>
            <div class="card"><ul>{ishikawa_html}</ul></div>
        </section>

        <section class="section">
            <h2>D5 · Acciones correctivas</h2>
            <div class="card"><p><strong>Capacitacion:</strong> {'Si' if d5_training.get('trained') else 'No'} · {_esc(d5_training.get('responsable') or '-')} · {_esc(d5_training.get('fecha') or '-')}</p></div>
            <table>
                <thead><tr><th>Accion</th><th>Responsable</th><th>Fecha</th><th>Status</th></tr></thead>
                <tbody>{build_actions_rows('D5')}</tbody>
            </table>
        </section>

        <section class="section">
            <h2>D6 · Verificacion de eficacia</h2>
            <table>
                <thead><tr><th>Accion</th><th>Responsable</th><th>Fecha</th><th>Status</th></tr></thead>
                <tbody>{build_actions_rows('D6')}</tbody>
            </table>
        </section>

        <section class="section">
            <h2>D7 · Actualizacion documental</h2>
            <table>
                <thead><tr><th>Documento</th><th>Revisado</th><th>Cuando</th><th>Actualizado</th><th>Comentarios</th></tr></thead>
                <tbody>{docs_rows}</tbody>
            </table>
            <div class="card"><h3>Prevencion e implementacion</h3><p>{_esc(problema_data.get("d7_prevencion") or "Sin prevencion registrada")}</p></div>
        </section>

        <section class="section">
            <h2>D8 · Cierre</h2>
            <div class="card"><p>{_esc(problema_data.get("d8_cierre") or "Sin cierre registrado")}</p></div>
            <table>
                <thead><tr><th>Rol</th><th>Nombre</th><th>Verificado / Informado el</th></tr></thead>
                <tbody>{closure_rows}</tbody>
            </table>
        </section>

        <footer>{_esc(empresa)} · Reporte 8D generado automaticamente desde la plataforma</footer>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_reporte_8d(datos_8d: dict, datos_5p: dict | None = None, datos_ishikawa: dict | None = None) -> Path:
    datos_5p = datos_5p or {}
    datos_ishikawa = datos_ishikawa or {}
    problema_data = {**datos_8d, **datos_5p, **datos_ishikawa}
    acciones = []
    if datos_8d.get("d5_accion_correctiva"):
        acciones.append({"fase_8d": "D5", "accion": datos_8d.get("d5_accion_correctiva"), "progreso": "-"})
    if datos_8d.get("d6_verificacion"):
        acciones.append({"fase_8d": "D6", "accion": datos_8d.get("d6_verificacion"), "progreso": "-"})
    return generar_pdf_8d(problema_data, acciones)


def generar_reporte_simulacro(datos_simulacro: dict) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    empresa = datos_simulacro.get("empresa") or "Empresa"
    escenario = datos_simulacro.get("escenario") or "Simulacro"
    fecha = datos_simulacro.get("fecha_simulacro") or "sin_fecha"
    slug = limpiar_nombre_archivo(f"{empresa}_{escenario}_{fecha}".replace("/", "-").replace(":", "-"))
    pdf_path = TMP_DIR / f"reporte_simulacro_{slug}.pdf"
    eficaz = "Si" if bool(datos_simulacro.get("respuesta_eficaz")) else "No"

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>{_logo_html()}<div><div class="brand">IDEAS Consulting</div><h1>Reporte de Simulacro Ambiental</h1></div></header>
        <section class="metrics">
            <div class="card"><div class="label">Empresa</div><div class="value blue">{_esc(empresa)}</div></div>
            <div class="card"><div class="label">Fecha</div><div class="value">{_esc(fecha)}</div></div>
            <div class="card"><div class="label">Respuesta eficaz</div><div class="value {'green' if eficaz == 'Si' else 'red'}">{eficaz}</div></div>
        </section>
        <section class="card"><h3>Escenario</h3><p>{_esc(escenario)}</p></section>
        <section class="card"><h3>Participantes</h3><p>{_esc(datos_simulacro.get("participantes") or "Sin participantes registrados")}</p></section>
        <section class="card"><h3>Conclusiones y mejoras</h3><p>{_esc(datos_simulacro.get("conclusiones_mejora") or "Sin conclusiones registradas")}</p></section>
        <footer>IDEAS Consulting · Reporte generado automaticamente desde la plataforma</footer>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_pdf_kpis(nombre_empresa: str, kpis: list[dict]) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    slug = limpiar_nombre_archivo(nombre_empresa or "empresa")
    pdf_path = TMP_DIR / f"reporte_kpis_{slug}.pdf"

    rows_html = "".join(
        f"""
        <tr>
            <td>{_esc(item.get("codigo") or "")}</td>
            <td>{_esc(item.get("nombre") or "")}</td>
            <td>{_esc(item.get("categoria") or "")}</td>
            <td>{_esc(item.get("meta") or "")}</td>
            <td>{_esc(item.get("valor_actual") or "")}</td>
            <td>{_esc(item.get("tendencia") or "")}</td>
            <td>{_esc(item.get("responsable") or "")}</td>
        </tr>
        """
        for item in (kpis or [])
    ) or '<tr><td colspan="7">Sin KPI registrados.</td></tr>'

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {_logo_html()}
            <div>
                <div class="brand">IDEAS Consulting</div>
                <h1>Reporte KPI</h1>
                <div class="subtitle">Empresa: {_esc(nombre_empresa)} · Total KPI: {len(kpis or [])}</div>
            </div>
        </header>
        <section class="section">
            <h2>Listado de indicadores</h2>
            <table>
                <thead>
                    <tr>
                        <th>Código</th>
                        <th>Nombre</th>
                        <th>Categoría</th>
                        <th>Meta</th>
                        <th>Valor actual</th>
                        <th>Tendencia</th>
                        <th>Responsable</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </section>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_pdf_mapa_procesos(nombre_empresa: str, procesos: list[dict]) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    slug = limpiar_nombre_archivo(nombre_empresa or "empresa")
    pdf_path = TMP_DIR / f"reporte_mapa_procesos_{slug}.pdf"

    rows_html = "".join(
        f"""
        <tr>
            <td>{_esc(item.get("proceso_nombre") or "")}</td>
            <td>{_esc(item.get("proceso_codigo") or "")}</td>
            <td>{_esc(item.get("dueno_proceso") or "")}</td>
            <td>{_esc(item.get("ultima_revision") or "")}</td>
            <td>{_esc(item.get("indicadores") or "")}</td>
        </tr>
        """
        for item in (procesos or [])
    ) or '<tr><td colspan="5">Sin procesos cargados.</td></tr>'

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {_logo_html()}
            <div>
                <div class="brand">IDEAS Consulting</div>
                <h1>Mapa de Procesos</h1>
                <div class="subtitle">Empresa: {_esc(nombre_empresa)} · Total procesos: {len(procesos or [])}</div>
            </div>
        </header>
        <section class="section">
            <h2>Listado de procesos</h2>
            <table>
                <thead>
                    <tr>
                        <th>Proceso</th>
                        <th>Código</th>
                        <th>Dueño</th>
                        <th>Última revisión</th>
                        <th>Indicadores</th>
                    </tr>
                </thead>
                <tbody>{rows_html}</tbody>
            </table>
        </section>
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)


def generar_pdf_kpis(nombre_empresa: str, kpis: list[dict], options: dict | None = None) -> Path:
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    slug = limpiar_nombre_archivo(nombre_empresa or "empresa")
    pdf_path = TMP_DIR / f"reporte_kpis_{slug}.pdf"
    options = options or {}

    include_summary = bool(options.get("include_summary", True))
    include_charts = bool(options.get("include_charts", True))
    include_comments = bool(options.get("include_comments", True))
    include_codigo = bool(options.get("include_codigo", True))
    include_categoria = bool(options.get("include_categoria", True))
    include_meta = bool(options.get("include_meta", True))
    include_valor = bool(options.get("include_valor", True))
    include_tendencia = bool(options.get("include_tendencia", True))
    include_responsable = bool(options.get("include_responsable", True))
    include_mensual = bool(options.get("include_mensual", False))
    custom_logo_path = str(options.get("custom_logo_path") or "").strip()

    columns = []
    if include_codigo:
        columns.append(("codigo", "Codigo"))
    columns.append(("nombre", "Nombre"))
    if include_categoria:
        columns.append(("categoria", "Categoria"))
    if include_meta:
        columns.append(("meta", "Meta"))
    if include_valor:
        columns.append(("valor_actual", "Valor actual"))
    if include_tendencia:
        columns.append(("tendencia", "Tendencia"))
    if include_responsable:
        columns.append(("responsable", "Responsable"))
    if not columns:
        columns = [("nombre", "Nombre")]

    headers_html = "".join(f"<th>{_esc(label)}</th>" for _key, label in columns)
    grouped: dict[str, list[dict]] = {}
    for item in (kpis or []):
        process_name = str(item.get("proceso_nombre") or "Sin proceso").strip() or "Sin proceso"
        grouped.setdefault(process_name, []).append(item)

    months = [
        ("ene", "Ene"), ("feb", "Feb"), ("mar", "Mar"), ("abr", "Abr"),
        ("may", "May"), ("jun", "Jun"), ("jul", "Jul"), ("ago", "Ago"),
        ("sep", "Sep"), ("oct", "Oct"), ("nov", "Nov"), ("dic", "Dic"),
    ]

    def _to_float(value):
        if value in (None, ""):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _current_value(item: dict):
        usa_ytd = int(item.get("usa_ytd") or 0) == 1
        tipo_ytd = str(item.get("tipo_ytd") or "").strip().lower()
        if usa_ytd:
            if tipo_ytd.startswith("manual"):
                manual_val = _to_float(item.get("ytd_manual_val"))
                if manual_val is not None:
                    return manual_val
            values = [_to_float(item.get(key)) for key, _ in months]
            valid = [v for v in values if v is not None]
            if valid:
                return sum(valid) / len(valid)
        explicit_val = _to_float(item.get("valor_actual"))
        if explicit_val is not None:
            return explicit_val
        latest = next((_to_float(item.get(key)) for key, _ in reversed(months) if _to_float(item.get(key)) is not None), None)
        return latest

    def _display_cell(item: dict, key: str):
        if key == "valor_actual":
            current = _current_value(item)
            return "-" if current is None else f"{current:.2f}"
        if key == "categoria":
            return str(item.get(key) or "Sin categoria")
        if key == "tendencia":
            return str(item.get(key) or "Sin tendencia")
        if key == "responsable":
            return str(item.get(key) or "Sin responsable")
        return str(item.get(key) or "")

    rows_blocks = []
    for process_name, items in grouped.items():
        rows_blocks.append(f'<tr><td colspan="{len(columns)}" style="background:#eef4fb;font-weight:800;">Proceso: {_esc(process_name)}</td></tr>')
        for item in items:
            rows_blocks.append("<tr>" + "".join(f"<td>{_esc(_display_cell(item, key))}</td>" for key, _label in columns) + "</tr>")
    rows_html = "".join(rows_blocks) or f'<tr><td colspan="{len(columns)}">Sin KPI registrados.</td></tr>'

    def _mini_chart(item: dict) -> str:
        values = [_to_float(item.get(key)) for key, _ in months]
        vista = str(item.get("_export_vista") or "Mensual").strip().lower()
        month_key = str(item.get("_export_month_key") or "ene").strip().lower()
        year_key = str(item.get("_export_year_key") or "2026").strip()
        month_labels = [label for _key, label in months]
        if vista.startswith("dia"):
            daily = []
            raw_daily = str(item.get("diario_json") or "").strip()
            if raw_daily:
                try:
                    parsed = json.loads(raw_daily)
                    if isinstance(parsed, dict):
                        period_key = f"{year_key}-{month_key}"
                        day_values = parsed.get(period_key)
                        if day_values is None:
                            day_values = parsed.get(month_key)
                        if isinstance(day_values, list):
                            daily = [_to_float(v) for v in day_values]
                except Exception:
                    daily = []
            if daily:
                values = daily
                month_labels = [str(i) for i in range(1, len(daily) + 1)]
        elif vista.startswith("an"):
            ytd = _current_value(item)
            values = [ytd]
            month_labels = ["Anual"]
        elif vista.startswith("men"):
            if all(v is None for v in values):
                manual_m = _to_float(item.get("mensual_manual_val"))
                if manual_m is not None:
                    values = [manual_m]
                    month_labels = ["Mensual"]

        max_val = max([v for v in values if v is not None], default=0.0)
        scale = max(max_val, 1.0)
        tipo = str(item.get("_export_chart_type") or item.get("tipo_grafico") or "Barra").strip().lower()
        objetivo = _to_float(item.get("objetivo")) or 0.0
        current_value = _current_value(item) or next((v for v in reversed(values) if v is not None), 0.0) or 0.0

        bars = []
        for idx, value in enumerate(values):
            height = 8 if value is None else max(8, int((value / scale) * 56))
            label = month_labels[idx] if idx < len(month_labels) else str(idx + 1)
            val_text = "-" if value is None else f"{value:.2f}"
            bars.append(
                f"""
                <div style="display:flex;flex-direction:column;align-items:center;gap:3px;">
                    <div style="width:10px;height:{height}px;border-radius:6px;background:{'#cbd5e1' if value is None else '#1f7ed6'};"></div>
                    <div style="font-size:7pt;color:#64748b;">{label}</div>
                    <div style="font-size:7pt;color:#0f172a;">{val_text}</div>
                </div>
                """
            )
        month_labels_html = "".join(f'<div style="font-size:7pt;color:#64748b;">{label}</div>' for label in month_labels)
        month_values = "".join(
            f'<div style="font-size:7pt;color:#0f172a;">{"-" if value is None else f"{value:.2f}"}</div>'
            for value in values
        )
        if "linea" in tipo or "línea" in tipo:
            points = []
            total = max(1, len(values) - 1)
            for idx, value in enumerate(values):
                x = int(20 + (idx * (960 / total)))
                y = 66 if value is None else int(66 - ((value / scale) * 56))
                points.append(f"{x},{y}")
            line_svg = f'<svg viewBox="0 0 1000 78" preserveAspectRatio="none" style="width:100%;height:92px;"><polyline fill="none" stroke="#1f7ed6" stroke-width="3" points="{" ".join(points)}" /></svg>'
            chart_markup = (
                line_svg
                + f'<div style="display:grid;grid-template-columns:repeat({max(1, len(month_labels))},minmax(0,1fr));gap:2px;align-items:center;text-align:center;margin-top:4px;">{month_labels_html}</div>'
                + f'<div style="display:grid;grid-template-columns:repeat({max(1, len(values))},minmax(0,1fr));gap:2px;align-items:center;text-align:center;">{month_values}</div>'
            )
        elif "gauge" in tipo:
            max_ref = max(current_value, objetivo, 1.0)
            pct = int((current_value / max_ref) * 100)
            sweep = max(0, min(100, pct))
            chart_markup = f'''
                <div style="padding:8px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:8.5pt;color:#334155;"><span>Actual: {current_value:.2f}</span><span>Objetivo: {objetivo:.2f}</span></div>
                    <svg viewBox="0 0 220 130" style="width:100%;height:120px;margin-top:4px;">
                        <path d="M20 110 A90 90 0 0 1 200 110" fill="none" stroke="#e2e8f0" stroke-width="18" stroke-linecap="round"/>
                        <path d="M20 110 A90 90 0 0 1 200 110" fill="none" stroke="#1f7ed6" stroke-width="18" stroke-linecap="round" stroke-dasharray="{sweep * 2.83} 999"/>
                        <circle cx="110" cy="110" r="5" fill="#0f172a"/>
                        <text x="110" y="84" text-anchor="middle" style="font-size:11px;fill:#334155;">{current_value:.2f}</text>
                    </svg>
                </div>
            '''
        elif "bullet" in tipo:
            max_ref = max(current_value, objetivo, 1.0)
            pct = int((current_value / max_ref) * 100)
            chart_markup = f'''
                <div style="padding:8px 0;">
                    <div style="display:flex;justify-content:space-between;font-size:8.5pt;color:#334155;"><span>Actual: {current_value:.2f}</span><span>Objetivo: {objetivo:.2f}</span></div>
                    <div style="margin-top:6px;height:14px;border-radius:999px;background:#e2e8f0;overflow:hidden;">
                        <div style="height:14px;width:{pct}%;background:#1f7ed6;"></div>
                    </div>
                </div>
            '''
        elif "radar" in tipo:
            chart_markup = f'<div style="font-size:8.5pt;color:#475569;">Radar (resumen mensual): {" | ".join("-" if v is None else f"{v:.1f}" for v in values)}</div>'
        else:
            chart_markup = f'<div style="display:flex;gap:6px;align-items:flex-end;justify-content:space-between;">{"".join(bars)}</div>'
        return f"""
        <div class="card" style="margin-top:8px;">
            <h3 style="margin-bottom:6px;">{_esc(item.get('nombre') or 'KPI')}</h3>
            <div style="font-size:8pt;color:#64748b;margin-bottom:6px;">Tipo: {_esc(item.get('_export_chart_type') or item.get('tipo_grafico') or 'Barra')}</div>
            {chart_markup}
        </div>
        """

    charts_html = ""
    if include_charts:
        for process_name, items in grouped.items():
            charts_html += f'<h3 style="margin-top:10px;">Proceso: {_esc(process_name)}</h3>'
            charts_html += "".join(_mini_chart(item) for item in items)

    comments_rows = []
    if include_comments:
        for item in (kpis or []):
            comment = str(item.get("comentarios_desvio") or "").strip()
            if comment:
                comments_rows.append(
                    f"<tr><td>{_esc(item.get('nombre') or '')}</td><td>{_esc(comment)}</td></tr>"
                )
    comments_html = "".join(comments_rows)

    summary_html = ""
    if include_summary:
        with_target = sum(1 for item in (kpis or []) if str(item.get("meta") or "").strip())
        with_owner = sum(1 for item in (kpis or []) if str(item.get("responsable") or "").strip())
        negative = sum(1 for item in (kpis or []) if str(item.get("tendencia") or "").strip().lower() == "negativa")
        summary_html = f"""
        <section class="metrics">
            <div class="card"><div class="label">KPI</div><div class="value blue">{len(kpis or [])}</div></div>
            <div class="card"><div class="label">Con meta</div><div class="value">{with_target}</div></div>
            <div class="card"><div class="label">Tendencia negativa</div><div class="value red">{negative}</div></div>
            <div class="card"><div class="label">Con responsable</div><div class="value">{with_owner}</div></div>
        </section>
        """

    monthly_table_html = ""
    if include_mensual:
        month_headers = "".join(f"<th>{label}</th>" for _key, label in months)
        month_rows = []
        for item in (kpis or []):
            cells = "".join(f"<td>{_esc(item.get(key) or '')}</td>" for key, _ in months)
            month_rows.append(f"<tr><td>{_esc(item.get('nombre') or '')}</td>{cells}</tr>")
        monthly_table_html = f"""
        <section class="section">
            <h2>Detalle mensual</h2>
            <table>
                <thead><tr><th>KPI</th>{month_headers}</tr></thead>
                <tbody>{''.join(month_rows) or '<tr><td colspan="13">Sin valores mensuales cargados.</td></tr>'}</tbody>
            </table>
        </section>
        """

    html_content = f"""
    <!doctype html>
    <html>
    <head><meta charset="utf-8">{_base_style()}</head>
    <body>
        <div class="topbar"></div>
        <header>
            {_brand_logo_html(custom_logo_path)}
            <div>
                <div class="brand">IDEAS Consulting</div>
                <h1>Reporte KPI</h1>
                <div class="subtitle">Empresa: {_esc(nombre_empresa)} · Total KPI: {len(kpis or [])}</div>
            </div>
        </header>
        {summary_html}
        <section class="section">
            <h2>Listado de indicadores</h2>
            <table>
                <thead><tr>{headers_html}</tr></thead>
                <tbody>{rows_html}</tbody>
            </table>
        </section>
        {monthly_table_html}
        {f'<section style="page-break-inside:auto;"><h2>Graficos de tendencia mensual</h2>{charts_html}</section>' if include_charts else ''}
        {f'<section class="section"><h2>Comentarios y desvios</h2><table><thead><tr><th>KPI</th><th>Comentario</th></tr></thead><tbody>{comments_html}</tbody></table></section>' if comments_html else ''}
    </body>
    </html>
    """
    return _write_pdf(html_content, pdf_path)
