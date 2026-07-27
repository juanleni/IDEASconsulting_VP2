from __future__ import annotations

import html
import math
import os
import platform
from pathlib import Path

if platform.system() == 'Windows':
    msys2_dll_dir = Path('C:/msys64/mingw64/bin')
    if msys2_dll_dir.exists():
        os.environ.setdefault('WEASYPRINT_DLL_DIRECTORIES', str(msys2_dll_dir))

try:
    from weasyprint import HTML
except OSError as exc:
    HTML = None
    WEASYPRINT_IMPORT_ERROR = exc
else:
    WEASYPRINT_IMPORT_ERROR = None

from ideas_utils import limpiar_nombre_archivo, obtener_logo_path

ROOT = Path(__file__).resolve().parents[1]
TMP_DIR = ROOT / 'reportes' / 'legal_matrix'

_COLORS = {
    'critica': '#B91C1C', 'alta': '#B45309', 'media': '#0E3A53', 'baja': '#6B7480',
}


def _esc(value) -> str:
    return html.escape('' if value is None else str(value), quote=True)


def _logo_html() -> str:
    logo_path = obtener_logo_path()
    if not logo_path:
        return ''
    path = Path(logo_path)
    if not path.exists():
        return ''
    return f'<img class="logo" src="{path.resolve().as_uri()}" alt="IDEAS Consulting">'


def _pie_svg(segments: list[tuple[float, str]], size: int = 100) -> str:
    """segments: list of (count, color). Renders a pie (WeasyPrint has no conic-gradient support)."""
    total = sum(count for count, _ in segments) or 1
    cx = cy = size / 2
    r = size / 2
    non_zero = [(count, color) for count, color in segments if count > 0]
    if len(non_zero) == 1:
        return f'<svg width="{size}" height="{size}"><circle cx="{cx}" cy="{cy}" r="{r}" fill="{non_zero[0][1]}"/></svg>'

    acc = 0.0
    paths = []
    for count, color in segments:
        if count <= 0:
            continue
        start_angle = acc / total * 2 * math.pi
        acc += count
        end_angle = acc / total * 2 * math.pi
        x1, y1 = cx + r * math.sin(start_angle), cy - r * math.cos(start_angle)
        x2, y2 = cx + r * math.sin(end_angle), cy - r * math.cos(end_angle)
        large_arc = 1 if (end_angle - start_angle) > math.pi else 0
        paths.append(f'<path d="M{cx},{cy} L{x1:.2f},{y1:.2f} A{r},{r} 0 {large_arc} 1 {x2:.2f},{y2:.2f} Z" fill="{color}"/>')
    return f'<svg width="{size}" height="{size}">{"".join(paths)}</svg>'


def _donut_html(estados: dict) -> str:
    segments_def = [
        ('cumple', 'Cumple', '#15803D'), ('no_cumple', 'No cumple', '#B91C1C'),
        ('pendiente', 'Pendiente', '#B45309'), ('no_aplica', 'No aplica', '#6B7480'),
    ]
    pie = _pie_svg([(estados.get(key, 0), color) for key, _label, color in segments_def])
    legend = ''.join(
        f'<div class="legend-row"><span class="dot" style="background:{color};"></span>'
        f'<span class="legend-label">{label}</span><span class="legend-count">{estados.get(key, 0)}</span></div>'
        for key, label, color in segments_def
    )
    return f'''
    <div class="donut-wrap">
      <div class="donut">{pie}</div>
      <div class="legend">{legend}</div>
    </div>'''


def _stat_card(label: str, value, css_class: str) -> str:
    return f'''
    <div class="stat-card {css_class}">
      <div class="stat-label">{_esc(label)}</div>
      <div class="stat-value">{_esc(value)}</div>
    </div>'''


def _table(headers: list[str], rows: list[list[str]], empty_text: str) -> str:
    if not rows:
        return f'<div class="empty-note">{_esc(empty_text)}</div>'
    head = ''.join(f'<th>{_esc(h)}</th>' for h in headers)
    body = ''.join('<tr>' + ''.join(f'<td>{cell}</td>' for cell in row) + '</tr>' for row in rows)
    return f'<table class="report-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>'


def _base_style() -> str:
    return '''
    <style>
      @page { size: A4; margin: 16mm 14mm; }
      * { box-sizing: border-box; }
      body { font-family: Arial, "Segoe UI", Helvetica, sans-serif; color: #1B2433; font-size: 9.5pt; line-height: 1.45; }
      .masthead { display: flex; justify-content: space-between; align-items: flex-start; gap: 16px; }
      .brand { display: flex; align-items: center; gap: 12px; }
      .logo { height: 40px; width: auto; }
      .brand-text .eyebrow { font-size: 10px; font-weight: 700; letter-spacing: .08em; color: #5A7B8C; }
      .brand-text .title { font-size: 18px; font-weight: 700; color: #0E3A53; margin-top: 2px; }
      .company-block { text-align: right; font-size: 9.5pt; color: #334155; }
      .company-block .name { font-weight: 700; color: #0f172a; font-size: 11pt; }
      .rule { height: 3px; background: #0E3A53; margin: 12px 0 16px 0; border-radius: 2px; }
      .section-title {
        font-size: 12px; font-weight: 700; letter-spacing: .04em; color: #0E3A53;
        text-transform: uppercase; border-bottom: 1px solid #E3E8EF; padding-bottom: 6px; margin: 18px 0 10px 0;
      }
      .stats-row { display: flex; gap: 10px; }
      .stat-card { flex: 1; border-radius: 12px; padding: 12px 14px; }
      .stat-label { font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; color: #64748b; }
      .stat-value { font-size: 20px; font-weight: 700; margin-top: 4px; }
      .stat-ok { background: #DCFCE7; } .stat-ok .stat-value { color: #15803D; }
      .stat-danger { background: #FEE2E2; } .stat-danger .stat-value { color: #B91C1C; }
      .stat-warn { background: #FEF3C7; } .stat-warn .stat-value { color: #B45309; }
      .stat-slate { background: #EEF1F5; } .stat-slate .stat-value { color: #334155; }
      .two-col { display: flex; gap: 20px; }
      .two-col > div { flex: 1; }
      .donut-wrap { display: flex; align-items: center; gap: 18px; }
      .donut { width: 90px; height: 90px; border-radius: 50%; flex-shrink: 0; }
      .legend-row { display: flex; align-items: center; gap: 6px; font-size: 9.5pt; margin-bottom: 5px; }
      .dot { width: 9px; height: 9px; border-radius: 50%; display: inline-block; flex-shrink: 0; }
      .legend-label { flex: 1; }
      .legend-count { color: #64748b; font-weight: 700; }
      .report-table { width: 100%; border-collapse: collapse; font-size: 9pt; }
      .report-table th { text-align: left; color: #8A93A0; font-weight: 700; border-bottom: 1px solid #E3E8EF; padding: 6px 6px; }
      .report-table td { padding: 7px 6px; border-bottom: 1px solid #F0F2F5; }
      .empty-note { font-size: 9.5pt; color: #8A93A0; padding: 6px 0; }
      .pdot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; margin-right: 5px; }
      ul.findings { margin: 0; padding-left: 18px; }
      ul.findings li { margin-bottom: 6px; font-size: 9.5pt; }
      .conclusion-box {
        background: #FEE2E2; border-left: 4px solid #B91C1C; border-radius: 8px;
        padding: 14px 16px; font-size: 9.5pt; color: #334155; margin-top: 8px;
      }
      .report-footer {
        margin-top: 24px; padding-top: 10px; border-top: 1px solid #E3E8EF;
        display: flex; justify-content: space-between; font-size: 8.5pt; color: #8A93A0;
      }
    </style>'''


def generar_html_reporte_legal_matrix(empresa_nombre: str, fecha_emision_larga: str, contexto: dict) -> str:
    areas_rows = [
        [_esc(a['area']), str(a['requisitos']),
         f'<span class="pdot" style="background:{"#15803D" if a["pct"] >= 80 else "#B45309" if a["pct"] >= 50 else "#B91C1C"};"></span>{a["pct"]}%']
        for a in contexto['areas']
    ]
    sedes_rows = [
        [_esc(s['nombre']), _esc(s['provincia']), str(s['requisitos']),
         f'<span class="pdot" style="background:{"#15803D" if s["pct"] >= 80 else "#B45309" if s["pct"] >= 50 else "#B91C1C"};"></span>{s["pct"]}%']
        for s in contexto['sedes']
    ]
    alertas_rows = [
        [f'<span class="pdot" style="background:{_COLORS.get(a["prioridad_code"], "#0E3A53")};"></span>{_esc(a["titulo"])}',
         _esc(a['prioridad']), _esc(a['sede']), _esc(a['fecha']), _esc(a['responsable'])]
        for a in contexto['alertas']
    ]
    auditorias_rows = [
        [_esc(a['fecha']), _esc(a['sede']), _esc(a['alcance']), _esc(a['auditor']), _esc(a['estado'])]
        for a in contexto['auditorias']
    ]
    hallazgos_html = ''.join(f'<li>{h}</li>' for h in contexto['hallazgos']) or '<li>Sin hallazgos registrados.</li>'

    return f'''<!doctype html>
<html lang="es"><head><meta charset="utf-8">{_base_style()}</head>
<body>
  <div class="masthead">
    <div class="brand">
      {_logo_html()}
      <div class="brand-text">
        <div class="eyebrow">IDEAS CONSULTING</div>
        <div class="title">Reporte Ejecutivo — Matriz Legal Digital</div>
      </div>
    </div>
    <div class="company-block">
      <div class="name">{_esc(empresa_nombre)}</div>
      <div>Emitido el {_esc(fecha_emision_larga)}</div>
    </div>
  </div>
  <div class="rule"></div>

  <div class="section-title">Resumen Ejecutivo</div>
  <div class="stats-row">
    {_stat_card('Cumplimiento Global', f"{contexto['cumplimiento_pct']}%", 'stat-ok')}
    {_stat_card('No Cumplidos', contexto['no_cumplidos'], 'stat-danger')}
    {_stat_card('Alertas Abiertas', contexto['alertas_abiertas'], 'stat-warn')}
    {_stat_card('Evidencias Pendientes', contexto['evidencias_pendientes'], 'stat-slate')}
  </div>

  <div class="two-col">
    <div>
      <div class="section-title">Distribución de Estados</div>
      {_donut_html(contexto['estados'])}
    </div>
    <div>
      <div class="section-title">Cumplimiento por Área Normativa</div>
      {_table(['Área', 'Requisitos', 'Cumplimiento'], areas_rows, 'Sin requisitos cargados.')}
    </div>
  </div>

  <div class="section-title">Cumplimiento por Sede</div>
  {_table(['Sede', 'Provincia', 'Requisitos', 'Cumplimiento'], sedes_rows, 'Sin sedes cargadas.')}

  <div class="section-title">Alertas Prioritarias Abiertas</div>
  {_table(['Alerta', 'Prioridad', 'Sede', 'Fecha', 'Responsable'], alertas_rows, 'Sin alertas abiertas.')}

  <div style="page-break-before: always;"></div>

  <div class="section-title" style="margin-top:0;">Próximas Auditorías</div>
  {_table(['Fecha', 'Sede', 'Alcance', 'Auditor', 'Estado'], auditorias_rows, 'Sin auditorías programadas.')}

  <div class="section-title">Hallazgos y Comentarios</div>
  <ul class="findings">{hallazgos_html}</ul>

  <div class="section-title">Conclusión</div>
  <div class="conclusion-box">{_esc(contexto['conclusion'])}</div>

  <div class="report-footer">
    <span>Ideas Consulting · Matriz Legal Digital</span>
    <span>Confidencial — uso interno de {_esc(empresa_nombre)}</span>
  </div>
</body></html>'''


def generar_pdf_reporte_legal_matrix(empresa_id: int, empresa_nombre: str, fecha_emision_larga: str, contexto: dict) -> Path:
    if HTML is None:
        raise RuntimeError(
            'WeasyPrint esta instalado, pero faltan librerias del sistema para renderizar PDFs '
            f'({WEASYPRINT_IMPORT_ERROR}). En Windows instala MSYS2/Pango o configura WEASYPRINT_DLL_DIRECTORIES.'
        )
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    slug = limpiar_nombre_archivo(empresa_nombre or f'empresa-{empresa_id}')
    path = TMP_DIR / f'matriz_legal_{slug}_{empresa_id}.pdf'
    html_content = generar_html_reporte_legal_matrix(empresa_nombre, fecha_emision_larga, contexto)
    HTML(string=html_content, base_url=str(ROOT)).write_pdf(str(path))
    return path.resolve()
