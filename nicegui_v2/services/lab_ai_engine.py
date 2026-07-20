from __future__ import annotations

import json
from services.lab_ai_context_builder import build_compact_context_text
from services.ai.openai_client import get_openai_client


LAB_BASE_PROMPT = (
    "Actuás como una IA técnica experta en ISO/IEC 17025, acreditación de laboratorios, metrología, "
    "incertidumbre de medición, trazabilidad, auditorías, gestión de riesgos y acciones correctivas.\n\n"
    "Tu función es analizar información estructurada del módulo LAB ISO 17025 y detectar riesgos de acreditación, "
    "incoherencias técnicas, impacto potencial sobre resultados, evidencias faltantes y acciones recomendadas.\n\n"
    "No inventes datos.\n"
    "No asumas evidencia no cargada.\n"
    "Si falta información, indicá exactamente qué dato o documento falta.\n"
    "Diferenciá claramente entre una validación objetiva del sistema y una recomendación técnica.\n"
    "Clasificá el riesgo como bajo, medio, alto o crítico.\n"
    "Indicá impacto potencial sobre acreditación, ensayos, informes, clientes o trazabilidad.\n"
    "Proponé acción inmediata, acción correctiva, evidencia esperada y criterio de eficacia.\n"
    "Respondé JSON puro con este esquema exacto:\n"
    "{"
    "\"diagnostico\":\"\","
    "\"riesgo_acreditacion\":\"bajo|medio|alto|critico\","
    "\"impacto_potencial\":\"\","
    "\"evidencia_faltante\":[],"
    "\"accion_inmediata\":\"\","
    "\"accion_correctiva_sugerida\":\"\","
    "\"evidencia_esperada_cierre\":[],"
    "\"criterio_eficacia\":\"\","
    "\"modulos_afectados\":[],"
    "\"requiere_bloqueo\":false,"
    "\"requiere_no_conformidad\":false,"
    "\"prioridad\":\"baja|media|alta|urgente\""
    "}"
)


def _openai_client():
    try:
        return get_openai_client()
    except Exception:
        return None


def _empty_response(reason: str) -> dict:
    return {
        "diagnostico": reason,
        "riesgo_acreditacion": "medio",
        "impacto_potencial": "",
        "evidencia_faltante": [],
        "accion_inmediata": "",
        "accion_correctiva_sugerida": "",
        "evidencia_esperada_cierre": [],
        "criterio_eficacia": "",
        "modulos_afectados": [],
        "requiere_bloqueo": False,
        "requiere_no_conformidad": False,
        "prioridad": "media",
    }


def analyze_with_lab_ai(context: dict, model: str = "gpt-4o-mini") -> dict:
    client = _openai_client()
    if client is None:
        return _empty_response("IA no disponible en este entorno.")
    prompt = build_compact_context_text(context)
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=0.1,
            max_tokens=900,
            messages=[
                {"role": "system", "content": LAB_BASE_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        content = str(response.choices[0].message.content or "").strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            return parsed
    except Exception as exc:
        return _empty_response(f"Error IA: {exc}")
    return _empty_response("Respuesta IA no parseable.")


def analyze_accreditation_risks(company_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)


def validate_technical_consistency(company_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)


def review_uncertainty_records(company_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)


def detect_incomplete_records(company_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)


def analyze_quality_trends(company_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)


def suggest_corrective_actions(alert_id: int, context: dict) -> dict:
    return analyze_with_lab_ai(context)
