import base64
import html
import mimetypes
import os
import unicodedata


def obtener_logo_path() -> str | None:
    candidatos = [
        "logo.png",
        "logo.jpg",
        "logo.jpeg",
        "Data/logo.png",
        "Data/logo.jpg",
        "Data/logo.jpeg",
        "Data/IDEAS_logo.png",
        "Data/IDEAS_logo.jpg",
        "Data/IDEAS_logo.jpeg",
    ]

    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return None


def obtener_imagen_inicio_path() -> str | None:
    candidatos = [
        "ideas_home_banner.png",
        "ideas_home_banner.jpg",
        "ideas_home_banner.jpeg",
        "Data/ideas_home_banner.png",
        "Data/ideas_home_banner.jpg",
        "Data/ideas_home_banner.jpeg",
        "Data/inicio_ideas.png",
        "Data/inicio_ideas.jpg",
        "Data/inicio_ideas.jpeg",
    ]

    for ruta in candidatos:
        if os.path.exists(ruta):
            return ruta
    return None


def imagen_a_data_uri(ruta: str | None) -> str | None:
    if not ruta or not os.path.exists(ruta):
        return None

    mime_type = mimetypes.guess_type(ruta)[0] or "image/png"
    with open(ruta, "rb") as archivo:
        contenido = base64.b64encode(archivo.read()).decode("utf-8")
    return f"data:{mime_type};base64,{contenido}"


def obtener_nivel(score: float) -> str:
    if score < 2:
        return "Bajo"
    if score < 3:
        return "Medio"
    return "Alto"


def obtener_conclusion(score: float) -> str:
    if score < 2:
        return "La organización presenta debilidades relevantes en su nivel de gestión y control. Requiere acciones correctivas prioritarias para estabilizar su desempeño."
    if score < 3:
        return "La organización muestra un nivel intermedio de madurez. Existen prácticas valiosas, aunque todavía hay oportunidades claras para consolidar consistencia, control y eficiencia."
    return "La organización evidencia una base sólida de gestión y desempeño. El desafío principal está en sostener, escalar y sofisticar sus capacidades."


def obtener_mensaje_direccion(nivel: str) -> str:
    if nivel == "Bajo":
        return "La lectura de dirección sugiere intervenir con foco inmediato en disciplina de gestión, control y consistencia operativa."
    if nivel == "Medio":
        return "La compañía cuenta con bases aprovechables, pero todavía requiere consolidar prácticas y ritmos de seguimiento para sostener resultados."
    return "La organización se encuentra en una posición favorable para profundizar excelencia operativa, escalabilidad y sofisticación de gestión."


def obtener_prioridad_recomendada(nivel: str) -> str:
    if nivel == "Bajo":
        return "Prioridad recomendada: intervención inmediata sobre los ejes críticos."
    if nivel == "Medio":
        return "Prioridad recomendada: consolidar estándares y acelerar mejoras de impacto."
    return "Prioridad recomendada: sostener fortalezas y avanzar hacia mayor sofisticación."


def obtener_acciones_nivel(nivel: str) -> list[str]:
    if nivel == "Bajo":
        return [
            "Definir un plan de choque con responsables y plazos de ejecución.",
            "Formalizar controles mínimos y evidencia de seguimiento.",
            "Revisar procesos críticos con foco en continuidad operativa.",
        ]
    if nivel == "Medio":
        return [
            "Consolidar estándares operativos y rituales de seguimiento.",
            "Priorizar las brechas con mayor impacto en eficiencia y control.",
            "Monitorear avances con indicadores de gestión simples y frecuentes.",
        ]
    return [
        "Profundizar automatización, analítica y consistencia de gestión.",
        "Escalar buenas prácticas entre áreas y equipos clave.",
        "Alinear las mejoras con objetivos de crecimiento y rentabilidad.",
    ]


def pdf_safe(texto: str | None) -> str:
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


def valor_afirmativo(valor) -> bool:
    if valor is None:
        return False
    normalizado = unicodedata.normalize("NFKD", str(valor)).encode("ascii", "ignore").decode("ascii").strip().lower()
    return normalizado in {"si", "s", "yes", "y", "true", "1"}


def html_safe(texto) -> str:
    return html.escape("" if texto is None else str(texto))


def limpiar_nombre_archivo(nombre: str) -> str:
    permitido = "".join(ch if ch.isalnum() or ch in ("_", "-") else "_" for ch in nombre.strip())
    while "__" in permitido:
        permitido = permitido.replace("__", "_")
    return permitido.strip("_") or "reporte"


def obtener_color_nivel(nivel: str) -> tuple[int, int, int]:
    if nivel == "Bajo":
        return (220, 38, 38)
    if nivel == "Medio":
        return (232, 161, 38)
    return (15, 143, 97)


def obtener_clase_badge(nivel: str) -> str:
    return "alto" if nivel == "Alto" else "medio" if nivel == "Medio" else "bajo"


def obtener_delta_texto(delta: float | None) -> tuple[str, str]:
    if delta is None:
        return "Sin base previa", "flat"
    if delta > 0.03:
        return f"+{delta:.2f} vs. anterior", "up"
    if delta < -0.03:
        return f"{delta:.2f} vs. anterior", "down"
    return "Sin variacion relevante", "flat"


def construir_evidencia_numerica(evidencias: list[str]) -> str:
    limpias = [ev.strip() for ev in evidencias if str(ev).strip()]
    return ", ".join(limpias)


def obtener_responsable_sugerido(eje: str) -> str:
    eje_l = eje.lower()
    if "fin" in eje_l:
        return "Direccion financiera"
    if "talent" in eje_l or "rrhh" in eje_l or "persona" in eje_l:
        return "Lider de talento"
    if "comercial" in eje_l or "venta" in eje_l or "cliente" in eje_l:
        return "Lider comercial"
    if "calidad" in eje_l or "iso" in eje_l:
        return "Responsable de calidad"
    if "tec" in eje_l or "sistema" in eje_l or "digital" in eje_l:
        return "Responsable de tecnologia"
    if "log" in eje_l or "abast" in eje_l:
        return "Lider de supply chain"
    return "Responsable del area"


def obtener_plazo_sugerido(score_eje: float) -> str:
    if score_eje < 2:
        return "30 dias"
    if score_eje < 3:
        return "60 dias"
    return "90 dias"


def obtener_impacto_sugerido(score_eje: float) -> str:
    if score_eje < 2:
        return "Alto"
    if score_eje < 3:
        return "Medio"
    return "Sostener"
