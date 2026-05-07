import base64
import html
import mimetypes
import os
import secrets
import smtplib
import unicodedata
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

SMTP_USER = "ideasconsultingargentina@gmail.com"
SMTP_PASSWORD = "ohvsamrfmbpumnbz"


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
        "â¢": "-",
        "âš ï¸": "-",
        "âš ": "-",
        "ðŸ´": "",
        "ðŸŸ¡": "",
        "ðŸŸ¢": "",
        "â": '"',
        "â": '"',
        "â": "'",
        "â": "-",
        "â": "-",
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


def generar_token_seguro() -> str:
    return secrets.token_urlsafe(32)


def enviar_correo_acceso(correo_destino, nombre_empresa, token, base_url="https://ideas-consulting-v2.onrender.com"):
    correo = str(correo_destino or "").strip()
    empresa = str(nombre_empresa or "").strip()
    token_val = str(token or "").strip()
    base = str(base_url or "").rstrip("/")
    enlace = f"{base}/crear-password/{token_val}"

    asunto = "Bienvenido a IDEAS Consulting - Crea tu contrasea"
    if not token_val:
        asunto = "Recuperacin de contrasea"

    html_body = f"""
    <div style="margin:0;padding:24px;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
      <div style="max-width:640px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:14px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1f7ed6 100%);padding:22px 28px;">
          <img src="{base}/assets/logo.png" alt="IDEAS Consulting" width="150" style="display:block;border:0;outline:none;text-decoration:none;" />
          <h1 style="margin:16px 0 0 0;color:#ffffff;font-size:24px;line-height:1.3;font-weight:700;">
            Acceso seguro a tu plataforma
          </h1>
        </div>
        <div style="padding:26px 28px;">
          <p style="margin:0 0 12px 0;font-size:16px;line-height:1.6;color:#0f172a;">
            Hola {empresa or 'equipo'},
          </p>
          <p style="margin:0 0 18px 0;font-size:15px;line-height:1.7;color:#334155;">
            Para crear o restablecer tu contrasea, utiliza el siguiente enlace seguro:
          </p>
          <a href="{enlace}" style="display:inline-block;background:#1f7ed6;color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:700;font-size:15px;">
            Crear mi contrasea
          </a>
          <p style="margin:18px 0 0 0;font-size:13px;line-height:1.6;color:#64748b;">
            Este enlace vence en 24 horas.<br/>
            Si no solicitaste este acceso, puedes ignorar este correo.
          </p>
        </div>
        <div style="padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;">
          IDEAS Consulting
        </div>
      </div>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = SMTP_USER
        msg["To"] = correo
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [correo], msg.as_string())
        server.quit()
        return {"ok": True, "to": correo, "subject": asunto, "link": enlace, "html": html_body}
    except Exception as exc:
        print("=== ENVIO DE CORREO (SIMULADO / FALLBACK) ===")
        print(f"Error SMTP: {exc}")
        print(f"Para: {correo}")
        print(f"Asunto: {asunto}")
        print("HTML:")
        print(html_body)
        print(f"Enlace directo: {enlace}")
        print("=== FIN CORREO (SIMULADO / FALLBACK) ===")
        return {"ok": False, "to": correo, "subject": asunto, "link": enlace, "html": html_body, "error": str(exc)}


def enviar_correo_cotizacion(nombre, contacto, servicio, detalles):
    nombre_text = str(nombre or "").strip()
    contacto_text = str(contacto or "").strip()
    servicio_text = str(servicio or "Otro").strip() or "Otro"
    detalles_text = str(detalles or "").strip()
    asunto = f"Nuevo Lead: Solicitud de {servicio_text}"

    html_body = f"""
    <div style="margin:0;padding:24px;background:#f3f6fb;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
      <div style="max-width:680px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
        <div style="background:linear-gradient(135deg,#0f172a 0%,#1f7ed6 55%,#0f8f61 100%);padding:24px 30px;">
          <h1 style="margin:0;color:#ffffff;font-size:24px;line-height:1.3;font-weight:800;">
            Nueva solicitud de cotización
          </h1>
          <p style="margin:10px 0 0 0;color:rgba(255,255,255,.84);font-size:15px;line-height:1.6;">
            Tienes una nueva solicitud de cotización desde la plataforma web.
          </p>
        </div>
        <div style="padding:28px 30px;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="border-collapse:collapse;">
            <tr>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;width:170px;">
                Nombre/Empresa
              </td>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#0f172a;font-size:15px;line-height:1.6;">
                {html_safe(nombre_text)}
              </td>
            </tr>
            <tr>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;">
                Contacto
              </td>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#0f172a;font-size:15px;line-height:1.6;">
                {html_safe(contacto_text)}
              </td>
            </tr>
            <tr>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;">
                Servicio
              </td>
              <td style="padding:14px 0;border-bottom:1px solid #e2e8f0;color:#0f172a;font-size:15px;line-height:1.6;">
                {html_safe(servicio_text)}
              </td>
            </tr>
            <tr>
              <td style="padding:14px 0;color:#64748b;font-size:13px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;vertical-align:top;">
                Detalles
              </td>
              <td style="padding:14px 0;color:#0f172a;font-size:15px;line-height:1.7;white-space:pre-wrap;">
                {html_safe(detalles_text) or 'Sin detalles adicionales.'}
              </td>
            </tr>
          </table>
        </div>
        <div style="padding:15px 30px;background:#f8fafc;border-top:1px solid #e2e8f0;color:#64748b;font-size:12px;">
          IDEAS Consulting · Lead generado desde la web institucional
        </div>
      </div>
    </div>
    """

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = SMTP_USER
        msg["To"] = SMTP_USER
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, [SMTP_USER], msg.as_string())
        server.quit()
        return {"ok": True, "to": SMTP_USER, "subject": asunto, "html": html_body}
    except Exception as exc:
        print("=== ENVIO DE COTIZACION (SIMULADO / FALLBACK) ===")
        print(f"Error SMTP: {exc}")
        print(f"Para: {SMTP_USER}")
        print(f"Asunto: {asunto}")
        print("HTML:")
        print(html_body)
        print("=== FIN COTIZACION (SIMULADO / FALLBACK) ===")
        return {"ok": False, "to": SMTP_USER, "subject": asunto, "html": html_body, "error": str(exc)}


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


def obtener_color_contraste(color_hex: str | None) -> str:
    """Devuelve blanco o azul marino segun la luminosidad perceptiva del color."""
    color = str(color_hex or "").strip().lstrip("#")
    if len(color) == 3:
        color = "".join(ch * 2 for ch in color)
    if len(color) != 6:
        return "#0f172a"

    try:
        red = int(color[0:2], 16)
        green = int(color[2:4], 16)
        blue = int(color[4:6], 16)
    except ValueError:
        return "#0f172a"

    luminosidad = (0.299 * red + 0.587 * green + 0.114 * blue) / 255
    return "#ffffff" if luminosidad < 0.58 else "#0f172a"

