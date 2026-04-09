from __future__ import annotations

from pathlib import Path

from fpdf import FPDF
from PIL import Image, ImageDraw, ImageFont

from ideas_utils import (
    limpiar_nombre_archivo,
    obtener_acciones_nivel,
    obtener_color_nivel,
    obtener_logo_path,
    obtener_mensaje_direccion,
    obtener_nivel,
    obtener_prioridad_recomendada,
    pdf_safe,
    valor_afirmativo,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS_DIR = ROOT / "reportes" / "premium"
TMP_DIR = REPORTS_DIR / "tmp"
LOGO_PATH = obtener_logo_path()

NAVY = (15, 23, 42)
BLUE = (37, 99, 235)
SKY = (96, 165, 250)
GREEN = (21, 128, 61)
AMBER = (217, 119, 6)
RED = (220, 38, 38)
SLATE = (71, 85, 105)
MUTED = (100, 116, 139)
LINE = (226, 232, 240)
SOFT = (245, 247, 250)
WHITE = (255, 255, 255)


def _font(size: int, bold: bool = False):
    candidates = ["arialbd.ttf", "segoeuib.ttf", "calibrib.ttf"] if bold else ["arial.ttf", "segoeui.ttf", "calibri.ttf"]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _wrap_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list[str]:
    words = pdf_safe(text).split()
    if not words:
        return [""]
    lines: list[str] = []
    current = words[0]
    for word in words[1:]:
        proposal = f"{current} {word}"
        if draw.textlength(proposal, font=font) <= max_width:
            current = proposal
        else:
            lines.append(current)
            current = word
    lines.append(current)
    return lines


def _pdf_paragraph(
    pdf: FPDF,
    x: float,
    y: float,
    width: float,
    text: str,
    line_h: float = 5.0,
    font_size: int = 10,
    bold: bool = False,
    color: tuple[int, int, int] = SLATE,
) -> float:
    pdf.set_xy(x, y)
    pdf.set_font("Arial", "B" if bold else "", font_size)
    pdf.set_text_color(*color)
    pdf.multi_cell(width, line_h, pdf_safe(text))
    return pdf.get_y()


def _gradient_bar(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, score: float) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=h // 2, fill=(231, 236, 242))
    score = max(1.0, min(score, 4.0))
    progress = int(w * ((score - 1) / 3))
    if progress <= 0:
        progress = 1
    for i in range(progress):
        t = i / max(progress - 1, 1)
        if t < 0.5:
            mix = t / 0.5
            color = (
                int(RED[0] + (AMBER[0] - RED[0]) * mix),
                int(RED[1] + (AMBER[1] - RED[1]) * mix),
                int(RED[2] + (AMBER[2] - RED[2]) * mix),
            )
        else:
            mix = (t - 0.5) / 0.5
            color = (
                int(AMBER[0] + (GREEN[0] - AMBER[0]) * mix),
                int(AMBER[1] + (GREEN[1] - AMBER[1]) * mix),
                int(AMBER[2] + (GREEN[2] - AMBER[2]) * mix),
            )
        draw.line((x + i, y + 3, x + i, y + h - 3), fill=color, width=1)
    draw.line((x + w, y - 8, x + w, y + h + 8), fill=(148, 163, 184), width=2)


def _score_chart(score: float, nivel: str, empresa: str, conclusion: str, path: str) -> str:
    width, height = 1200, 700
    img = Image.new("RGB", (width, height), (243, 247, 250))
    draw = ImageDraw.Draw(img)
    nivel_color = obtener_color_nivel(nivel)

    draw.rounded_rectangle((22, 22, width - 22, height - 22), radius=40, fill=WHITE, outline=LINE, width=2)
    draw.rounded_rectangle((48, 42, width - 48, 146), radius=32, fill=(241, 246, 251))
    draw.text((78, 66), "Resumen ejecutivo premium", font=_font(40, bold=True), fill=NAVY)
    draw.text((78, 112), empresa[:46], font=_font(24), fill=SLATE)

    center = (260, 388)
    radius = 148
    thickness = 34
    bbox = (center[0] - radius, center[1] - radius, center[0] + radius, center[1] + radius)
    draw.arc(bbox, start=135, end=405, fill=(226, 232, 240), width=thickness)
    end_angle = 135 + int(((max(1.0, min(score, 4.0)) - 1.0) / 3.0) * 270)
    draw.arc(bbox, start=135, end=end_angle, fill=nivel_color, width=thickness)
    draw.text((194, 340), f"{score:.2f}", font=_font(62, bold=True), fill=NAVY)
    draw.text((212, 404), "score global", font=_font(22), fill=SLATE)

    draw.text((522, 190), "Lectura de dirección", font=_font(24, bold=True), fill=MUTED)
    for idx, line in enumerate(_wrap_text(draw, obtener_mensaje_direccion(nivel), _font(24), 560)):
        draw.text((522, 232 + idx * 34), line, font=_font(24), fill=NAVY)

    draw.text((522, 382), "Síntesis ejecutiva", font=_font(24, bold=True), fill=MUTED)
    for idx, line in enumerate(_wrap_text(draw, conclusion, _font(22), 560)):
        draw.text((522, 424 + idx * 30), line, font=_font(22), fill=SLATE)

    draw.rounded_rectangle((522, 552, 1080, 616), radius=22, fill=(240, 247, 255))
    draw.text((548, 572), obtener_prioridad_recomendada(nivel), font=_font(21, bold=True), fill=BLUE)
    draw.rounded_rectangle((1088, 68, 1144, 124), radius=18, fill=nivel_color)
    draw.text((1104, 85), nivel[:1], font=_font(28, bold=True), fill=WHITE)

    img.save(path)
    return path


def _area_bars_chart(eje_scores: dict[str, float], path: str) -> str:
    items = sorted(eje_scores.items(), key=lambda item: item[1], reverse=True)
    rows = max(len(items), 1)
    width, height = 1500, max(860, 260 + rows * 88)
    img = Image.new("RGB", (width, height), (243, 247, 250))
    draw = ImageDraw.Draw(img)

    draw.rounded_rectangle((24, 24, width - 24, height - 24), radius=40, fill=WHITE, outline=LINE, width=2)
    draw.text((64, 58), "Performance por área", font=_font(40, bold=True), fill=NAVY)
    draw.text((64, 108), "Madurez ejecutiva comparada contra el estándar objetivo 4.0", font=_font(22), fill=SLATE)

    bar_x = 520
    bar_w = 840
    start_y = 180
    gap = 88
    for idx, (area, score) in enumerate(items[:8]):
        y = start_y + idx * gap
        draw.text((64, y + 4), area[:30], font=_font(24, bold=True), fill=NAVY)
        _gradient_bar(draw, bar_x, y + 2, bar_w, 30, score)
        draw.text((bar_x + bar_w + 22, y + 2), f"{score:.2f}", font=_font(24, bold=True), fill=NAVY)
        draw.text((bar_x, y + 42), "1", font=_font(18), fill=MUTED)
        draw.text((bar_x + bar_w // 3, y + 42), "2", font=_font(18), fill=MUTED)
        draw.text((bar_x + 2 * bar_w // 3, y + 42), "3", font=_font(18), fill=MUTED)
        draw.text((bar_x + bar_w - 10, y + 42), "4", font=_font(18), fill=MUTED)

    img.save(path)
    return path


def _metric_card(pdf: FPDF, x: float, y: float, w: float, h: float, label: str, value: str, detail: str, color: tuple[int, int, int]) -> None:
    pdf.set_fill_color(*SOFT)
    pdf.set_draw_color(*LINE)
    pdf.rect(x, y, w, h, style="FD")
    pdf.set_xy(x + 6, y + 5)
    pdf.set_font("Arial", "B", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(w - 12, 4, pdf_safe(label.upper()), ln=True)
    pdf.set_x(x + 6)
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(*color)
    pdf.cell(w - 12, 10, pdf_safe(value), ln=True)
    pdf.set_x(x + 6)
    pdf.set_font("Arial", "", 9)
    pdf.set_text_color(*SLATE)
    pdf.multi_cell(w - 12, 4.2, pdf_safe(detail))


def _section_box(pdf: FPDF, x: float, y: float, w: float, h: float, title: str, fill: tuple[int, int, int] = SOFT) -> None:
    pdf.set_fill_color(*fill)
    pdf.set_draw_color(*LINE)
    pdf.rect(x, y, w, h, style="FD")
    pdf.set_xy(x + 6, y + 5)
    pdf.set_font("Arial", "B", 11)
    pdf.set_text_color(*NAVY)
    pdf.cell(w - 12, 5, pdf_safe(title), ln=True)


def _header(pdf: FPDF, title: str, subtitle: str = "") -> None:
    pdf.set_fill_color(*NAVY)
    pdf.rect(0, 0, 210, 16, "F")
    pdf.set_fill_color(*BLUE)
    pdf.rect(150, 0, 60, 16, "F")
    if LOGO_PATH and str(LOGO_PATH).lower().endswith((".png", ".jpg", ".jpeg")):
        pdf.image(str(LOGO_PATH), x=14, y=22, w=24)
    pdf.set_xy(42, 21)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(*GREEN)
    pdf.cell(100, 5, "IDEAS CONSULTING", ln=True)
    pdf.set_x(42)
    pdf.set_font("Arial", "B", 20)
    pdf.set_text_color(*NAVY)
    pdf.cell(150, 8, pdf_safe(title), ln=True)
    if subtitle:
        pdf.set_x(42)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(*MUTED)
        pdf.multi_cell(146, 4.8, pdf_safe(subtitle))


def _footer(pdf: FPDF, page_no: int) -> None:
    pdf.set_draw_color(*LINE)
    pdf.line(14, 286, 196, 286)
    pdf.set_xy(14, 288)
    pdf.set_font("Arial", "", 8)
    pdf.set_text_color(*MUTED)
    pdf.cell(120, 4, pdf_safe("IDEAS Consulting | Reporte Ejecutivo Premium"), ln=0)
    pdf.cell(62, 4, pdf_safe(f"Página {page_no}"), ln=1, align="R")


def _company_lines(empresa_info: dict, certificaciones: list[str]) -> list[str]:
    return [
        f"Razón social: {empresa_info.get('razon_social') or empresa_info.get('nombre') or '-'}",
        f"Ubicación: {empresa_info.get('ubicacion') or '-'}",
        f"Rubro: {empresa_info.get('rubro') or '-'}",
        f"Empleados: {empresa_info.get('cantidad_empleados') or '-'}",
        f"Contacto: {empresa_info.get('contacto_nombre') or '-'}",
        f"Correo: {empresa_info.get('contacto_correo') or '-'}",
        f"Teléfono: {empresa_info.get('contacto_telefono') or '-'}",
        f"Cargo: {empresa_info.get('contacto_posicion') or '-'}",
        f"Certificaciones: {', '.join(certificaciones) if certificaciones else 'Sin certificaciones registradas'}",
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
) -> str:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)
    empresa_info = empresa_info or {}

    slug = limpiar_nombre_archivo(nombre_empresa)
    pdf_path = REPORTS_DIR / f"Reporte_Ejecutivo_Premium_{slug}.pdf"
    score_chart_path = str(TMP_DIR / f"{slug}_score.png")
    area_chart_path = str(TMP_DIR / f"{slug}_areas.png")

    _score_chart(score, nivel, nombre_empresa, conclusion, score_chart_path)
    _area_bars_chart(eje_scores, area_chart_path)

    color_nivel = obtener_color_nivel(nivel)
    certificaciones = [
        label
        for key, label in [
            ("cert_iso_9001", "ISO 9001"),
            ("cert_iso_14001", "ISO 14001"),
            ("cert_iso_45001", "ISO 45001"),
            ("cert_iatf", "IATF"),
        ]
        if valor_afirmativo(empresa_info.get(key))
    ]
    opportunities = criticas[:5] if criticas else ["No se identificaron oportunidades críticas en este corte."]
    top_areas = sorted(eje_scores.items(), key=lambda item: item[1])

    pdf = FPDF()
    pdf.set_auto_page_break(auto=False)

    pdf.add_page()
    _header(
        pdf,
        "Reporte Ejecutivo Premium",
        "Síntesis de madurez organizacional para dirección, con foco en prioridades, brechas y lectura institucional.",
    )

    pdf.set_fill_color(241, 246, 251)
    pdf.set_draw_color(*LINE)
    pdf.rect(14, 62, 182, 22, style="FD")
    pdf.set_xy(20, 68)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(48, 4, pdf_safe("Empresa"))
    pdf.cell(52, 4, pdf_safe("Fecha"))
    pdf.cell(32, 4, pdf_safe("Nivel"))
    pdf.cell(24, 4, pdf_safe("Score"), ln=1)
    pdf.set_x(20)
    pdf.set_font("Arial", "B", 10)
    pdf.set_text_color(*NAVY)
    pdf.cell(48, 6, pdf_safe(nombre_empresa[:26]))
    pdf.cell(52, 6, pdf_safe(fecha[:24]))
    pdf.set_text_color(*color_nivel)
    pdf.cell(32, 6, pdf_safe(nivel))
    pdf.cell(24, 6, pdf_safe(f"{score:.2f}"), ln=1)

    pdf.set_fill_color(245, 248, 252)
    pdf.rect(14, 90, 182, 22, style="FD")
    pdf.set_xy(20, 96)
    pdf.set_font("Arial", "B", 9)
    pdf.set_text_color(*MUTED)
    pdf.cell(170, 4, pdf_safe("Lectura de dirección"), ln=True)
    _pdf_paragraph(pdf, 20, 101, 170, obtener_mensaje_direccion(nivel), line_h=4.8, font_size=10, color=NAVY)

    metric_y = 120
    _metric_card(pdf, 14, metric_y, 56, 26, "Score global", f"{score:.2f}", "Promedio consolidado del diagnóstico.", NAVY)
    _metric_card(pdf, 77, metric_y, 56, 26, "Nivel actual", nivel, "Lectura ejecutiva de madurez.", color_nivel)
    _metric_card(pdf, 140, metric_y, 56, 26, "Prioridades", str(len(opportunities)), "Oportunidades clave detectadas.", BLUE)

    _section_box(pdf, 14, 154, 88, 43, "Síntesis consultiva")
    _pdf_paragraph(pdf, 20, 164, 76, conclusion, line_h=4.5, font_size=9)

    _section_box(pdf, 108, 154, 88, 43, "Ficha institucional")
    info_y = 164
    for line in _company_lines(empresa_info, certificaciones)[:5]:
        pdf.set_xy(114, info_y)
        pdf.set_font("Arial", "", 8)
        pdf.set_text_color(*SLATE)
        pdf.cell(76, 4.3, pdf_safe(line[:70]), ln=True)
        info_y += 4.6

    pdf.image(score_chart_path, x=22, y=205, w=166)
    _footer(pdf, 1)

    pdf.add_page()
    _header(
        pdf,
        "Lectura por Área",
        "Comparativo ejecutivo de madurez por eje para identificar fortalezas, gaps y foco de gestión.",
    )
    pdf.image(area_chart_path, x=14, y=48, w=182)

    _section_box(pdf, 14, 210, 88, 54, "Mensajes clave")
    key_y = 220
    for action in obtener_acciones_nivel(nivel):
        key_y = _pdf_paragraph(pdf, 20, key_y, 76, f"- {action}", line_h=4.3, font_size=8.5)
        key_y += 1

    _section_box(pdf, 108, 210, 88, 54, "Top brechas")
    gap_y = 220
    for area, area_score in top_areas[:4]:
        gap_y = _pdf_paragraph(
            pdf,
            114,
            gap_y,
            76,
            f"{area[:24]} | {area_score:.2f} | {obtener_nivel(area_score)}",
            line_h=4.4,
            font_size=8.5,
            color=NAVY,
        )
        gap_y += 1.2

    _footer(pdf, 2)

    pdf.add_page()
    _header(
        pdf,
        "Prioridades Ejecutivas",
        "Resumen de las áreas con mayor necesidad de intervención y oportunidades de mejora inmediata.",
    )

    pdf.set_xy(14, 50)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 10)
    pdf.cell(102, 8, pdf_safe("Área"), ln=0, fill=True)
    pdf.cell(24, 8, pdf_safe("Score"), ln=0, align="C", fill=True)
    pdf.cell(30, 8, pdf_safe("Nivel"), ln=0, align="C", fill=True)
    pdf.cell(40, 8, pdf_safe("Prioridad"), ln=1, align="C", fill=True)

    pdf.set_font("Arial", "", 10)
    y = 58
    for area, area_score in top_areas[:9]:
        area_level = obtener_nivel(area_score)
        priority = "Alta" if area_score < 2 else "Media" if area_score < 3 else "Sostener"
        fill = (254, 242, 242) if area_score < 2 else (255, 247, 237) if area_score < 3 else (240, 253, 244)
        pdf.set_fill_color(*fill)
        pdf.set_text_color(*NAVY)
        pdf.cell(102, 8, pdf_safe(area[:34]), ln=0, fill=True)
        pdf.cell(24, 8, pdf_safe(f"{area_score:.2f}"), ln=0, align="C", fill=True)
        pdf.cell(30, 8, pdf_safe(area_level), ln=0, align="C", fill=True)
        pdf.cell(40, 8, pdf_safe(priority), ln=1, align="C", fill=True)
        y += 8

    _section_box(pdf, 14, 140, 182, 52, "Oportunidades prioritarias")
    item_y = 150
    for item in opportunities:
        item_y = _pdf_paragraph(pdf, 20, item_y, 170, f"- {item[:120]}", line_h=4.8, font_size=9)
        item_y += 1
        if item_y > 184:
            break

    _section_box(pdf, 14, 198, 182, 36, "Ficha institucional ampliada")
    info_y = 208
    for line in _company_lines(empresa_info, certificaciones)[5:]:
        pdf.set_xy(20, info_y)
        pdf.set_font("Arial", "", 9)
        pdf.set_text_color(*SLATE)
        pdf.cell(170, 4.8, pdf_safe(line[:92]), ln=True)
        info_y += 5

    _section_box(pdf, 14, 240, 182, 28, "Cierre ejecutivo")
    _pdf_paragraph(
        pdf,
        20,
        250,
        170,
        "Este documento resume la situación actual para dirección. El siguiente paso sugerido es profundizar el análisis operativo con responsables, plazos y seguimiento de implementación.",
        line_h=4.5,
        font_size=9,
    )
    _footer(pdf, 3)

    pdf.output(str(pdf_path))
    return str(pdf_path)
