from __future__ import annotations

import json
import os
from typing import Any

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - dependencia opcional
    OpenAI = None


def _get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if OpenAI is None:
        raise RuntimeError("La libreria openai no esta instalada en el entorno.")
    if not api_key:
        raise RuntimeError("Falta definir la variable de entorno OPENAI_API_KEY.")
    return OpenAI(api_key=api_key)


def _chat_text(*, system_prompt: str, user_prompt: str, model: str = "gpt-4o-mini") -> str:
    client = _get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.4,
        max_tokens=700,
    )
    return (response.choices[0].message.content or "").strip()


def explicar_requisito_iso(norma, requisito, resumen, observacion_consultiva) -> str:
    system_prompt = (
        "Actua como un auditor experto ISO/IATF de IDEAS Consulting. "
        "Explica este requisito a un operario basandote UNICAMENTE en la guia proporcionada."
    )
    user_prompt = (
        f"Norma: {str(norma or '').strip()}\n"
        f"Requisito: {str(requisito or '').strip()}\n"
        f"Resumen: {str(resumen or '').strip()}\n"
        f"Guia consultiva: {str(observacion_consultiva or '').strip()}\n\n"
        "Devuelve una explicacion breve, clara y practica en espanol. "
        "Estructura sugerida:\n"
        "1. Que pide realmente el requisito\n"
        "2. Que deberia mirar un operario en la practica\n"
        "3. Que evidencia o documento suele ayudar a demostrarlo"
    )
    return _chat_text(system_prompt=system_prompt, user_prompt=user_prompt)


def sugerir_causas_ishikawa(problema, factores_retenidos) -> str:
    factores = factores_retenidos if isinstance(factores_retenidos, str) else ", ".join(str(item or "").strip() for item in (factores_retenidos or []) if str(item or "").strip())
    system_prompt = (
        "Actua como especialista 8D/Ishikawa automotriz. "
        "Sugiere 3 causas raiz breves para el problema descrito, enfocandote en las categorias 6M aplicables."
    )
    user_prompt = (
        f"Problema: {str(problema or '').strip()}\n"
        f"Factores retenidos: {factores}\n\n"
        "Responde en espanol con 3 sugerencias concretas. "
        "Para cada una indica:\n"
        "- categoria 6M probable\n"
        "- causa raiz sugerida\n"
        "- que validacion corta conviene hacer"
    )
    return _chat_text(system_prompt=system_prompt, user_prompt=user_prompt)


def _normalize_aspects(aspectos_lista: list[Any]) -> list[str]:
    normalized: list[str] = []
    for item in aspectos_lista or []:
        text = str(item or "").strip()
        if text and text not in normalized:
            normalized.append(text)
    return normalized


def _prompt_matriz_legal(rubro: str, ubicacion: str, aspectos_str: str) -> str:
    return (
        f"Actúa como un auditor experto en ISO 14001 y legislación ambiental de {ubicacion}. "
        f"Para una empresa del rubro '{rubro}' con estos aspectos ambientales: '{aspectos_str}', "
        "realiza un barrido exhaustivo de toda la normativa aplicable. "
        "Piensa paso a paso y busca regulaciones en tres niveles: "
        "1. Nivel Nacional (Leyes, Decretos, Resoluciones). "
        f"2. Nivel Provincial (Leyes y normativas específicas de la provincia/estado en {ubicacion}). "
        "3. Nivel Municipal (Ordenanzas típicas para ese rubro en esa ciudad). "
        "Debes ser exhaustivo e incluir normativa sobre residuos peligrosos, efluentes, emisiones, "
        "seguridad, habilitaciones, etc. "
        'Devuelve ÚNICAMENTE un JSON con esta estructura exacta: '
        '{ "leyes": [ { "jurisdiccion": "Nacional" | "Provincial" | "Municipal", '
        '"norma_legal": "Nombre exacto y nro", "articulo_aplicable": "Resumen de la exigencia" } ] }'
    )


def _mock_matriz_legal(rubro: str, ubicacion: str, aspectos_str: str) -> list[dict]:
    rubro_text = str(rubro or "industrial").strip()
    ubicacion_text = str(ubicacion or "Argentina").strip()
    aspectos = aspectos_str or "residuos, efluentes, emisiones y emergencias ambientales"
    return [
        {
            "jurisdiccion": "Nacional",
            "norma_legal": "Ley General del Ambiente 25.675",
            "articulo_aplicable": (
                f"Marco general de política ambiental, prevención y mejora continua aplicable al rubro {rubro_text} "
                f"con aspectos {aspectos}."
            ),
        },
        {
            "jurisdiccion": "Nacional",
            "norma_legal": "Ley 24.051 de Residuos Peligrosos",
            "articulo_aplicable": "Identificación, almacenamiento, transporte, manifiestos y disposición final de residuos peligrosos.",
        },
        {
            "jurisdiccion": "Nacional",
            "norma_legal": "Ley 25.612 de Gestión Integral de Residuos Industriales y de Actividades de Servicios",
            "articulo_aplicable": "Gestión integral, minimización, tratamiento y control documental de residuos industriales y especiales.",
        },
        {
            "jurisdiccion": "Nacional",
            "norma_legal": "Ley 19.587 de Higiene y Seguridad en el Trabajo y decreto reglamentario",
            "articulo_aplicable": "Condiciones de seguridad operativa, prevención de incidentes y control de riesgos con impacto ambiental asociado.",
        },
        {
            "jurisdiccion": "Provincial",
            "norma_legal": f"Normativa provincial ambiental aplicable en {ubicacion_text}",
            "articulo_aplicable": (
                f"Revisión de permisos, declaraciones, control de efluentes, residuos especiales y emisiones para empresas del rubro {rubro_text}."
            ),
        },
        {
            "jurisdiccion": "Provincial",
            "norma_legal": f"Registro provincial de generadores, operadores o establecimientos industriales en {ubicacion_text}",
            "articulo_aplicable": "Inscripción, renovación, monitoreos y presentación de información ambiental ante autoridad provincial competente.",
        },
        {
            "jurisdiccion": "Municipal",
            "norma_legal": f"Ordenanzas municipales de habilitación, uso de suelo y gestión ambiental en {ubicacion_text}",
            "articulo_aplicable": "Compatibilidad de actividad, habilitación comercial/industrial, gestión de residuos, ruidos y condiciones operativas locales.",
        },
        {
            "jurisdiccion": "Municipal",
            "norma_legal": f"Ordenanzas locales de contingencias, derrames y emergencias ambientales en {ubicacion_text}",
            "articulo_aplicable": "Planes de contingencia, comunicación a autoridades y preparación ante incidentes ambientales.",
        },
    ]


def sugerir_matriz_legal_ia(rubro: str, ubicacion: str, aspectos_lista: list) -> list[dict]:
    rubro_text = str(rubro or "industrial/general").strip()
    ubicacion_text = str(ubicacion or "Argentina").strip()
    aspectos_normalizados = _normalize_aspects(aspectos_lista)
    aspectos_str = ", ".join(aspectos_normalizados) or "residuos, efluentes, emisiones, consumos y emergencias ambientales"
    prompt = _prompt_matriz_legal(rubro_text, ubicacion_text, aspectos_str)

    if OpenAI is not None and os.getenv("OPENAI_API_KEY"):
        try:
            client = OpenAI()
            response = client.chat.completions.create(
                model=os.getenv("OPENAI_MODEL", "gpt-4.1-mini"),
                messages=[
                    {"role": "system", "content": "Responde solo con JSON válido."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                max_tokens=2500,
            )
            content = response.choices[0].message.content or "{}"
            payload = json.loads(content)
            leyes = payload.get("leyes", [])
            normalized_rows: list[dict] = []
            for item in leyes:
                if not isinstance(item, dict):
                    continue
                norma_legal = str(item.get("norma_legal") or "").strip()
                articulo_aplicable = str(item.get("articulo_aplicable") or "").strip()
                jurisdiccion = str(item.get("jurisdiccion") or "").strip().title()
                if not norma_legal:
                    continue
                normalized_rows.append(
                    {
                        "jurisdiccion": jurisdiccion or "Nacional",
                        "norma_legal": norma_legal,
                        "articulo_aplicable": articulo_aplicable,
                    }
                )
            if normalized_rows:
                return normalized_rows
        except Exception:
            pass

    return _mock_matriz_legal(rubro_text, ubicacion_text, aspectos_str)
