from __future__ import annotations

import re
import unicodedata


def _normalize_text(value: str | None) -> str:
    text = unicodedata.normalize('NFKD', str(value or ''))
    text = text.encode('ascii', 'ignore').decode('ascii').lower()
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def build_context_keywords(values: list[str | None], *, min_len: int = 3, max_keywords: int = 18) -> list[str]:
    keywords: list[str] = []
    for value in values:
        for token in _normalize_text(value).split():
            if len(token) < min_len:
                continue
            if token not in keywords:
                keywords.append(token)
            if len(keywords) >= max_keywords:
                return keywords
    return keywords


def summarize_sources_for_context(
    sources: list[dict] | None,
    context_values: list[str | None],
    *,
    limit: int = 5,
    fallback_limit: int = 3,
    snippet_length: int = 320,
) -> list[dict]:
    items = list(sources or [])
    if not items:
        return []

    keywords = build_context_keywords(context_values)
    ranked: list[dict] = []
    for source in items:
        content = str(source.get('contenido') or '').strip()
        title = str(source.get('titulo') or 'Fuente sin titulo').strip()
        source_type = str(source.get('tipo') or 'texto').strip()
        haystack = _normalize_text(f'{title} {content}')

        matched = [keyword for keyword in keywords if keyword in haystack]
        score = len(matched)
        if keywords and score == 0:
            continue

        snippet = content[:snippet_length].strip() if content else 'Sin contenido textual visible.'
        if len(content) > snippet_length:
            snippet = f'{snippet}...'

        ranked.append(
            {
                'id': source.get('id'),
                'titulo': title,
                'tipo': source_type,
                'snippet': snippet,
                'score': score,
                'matched_keywords': matched[:8],
            }
        )

    if ranked:
        ranked.sort(key=lambda item: (-int(item['score']), item['titulo']))
        return ranked[:limit]

    fallback: list[dict] = []
    for source in items[:fallback_limit]:
        content = str(source.get('contenido') or '').strip()
        snippet = content[:snippet_length].strip() if content else 'Sin contenido textual visible.'
        if len(content) > snippet_length:
            snippet = f'{snippet}...'
        fallback.append(
            {
                'id': source.get('id'),
                'titulo': str(source.get('titulo') or 'Fuente sin titulo').strip(),
                'tipo': str(source.get('tipo') or 'texto').strip(),
                'snippet': snippet,
                'score': 0,
                'matched_keywords': [],
            }
        )
    return fallback


def build_quality_brainstorm_lines(
    retained_factors: list[str] | None,
    effect_text: str | None,
    source_matches: list[dict] | None,
) -> list[str]:
    suggestions: list[str] = []
    effect = str(effect_text or '').strip()
    for factor in list(retained_factors or [])[:5]:
        factor_text = str(factor or '').strip()
        if not factor_text:
            continue
        suggestions.append(f'Revisar si el factor "{factor_text}" esta cubierto por un estandar, instruccion o control vigente.')
        suggestions.append(f'Validar evidencia objetiva para confirmar si "{factor_text}" explica la ocurrencia o la no deteccion.')

    if effect:
        suggestions.append(f'Contrastar el problema central "{effect}" contra la secuencia real del proceso y los controles de deteccion.')

    for match in list(source_matches or [])[:3]:
        title = str(match.get('titulo') or '').strip()
        if title:
            suggestions.append(f'Cruzar el caso con la fuente "{title}" para verificar si el metodo esperado realmente se aplico.')

    unique: list[str] = []
    for suggestion in suggestions:
        clean = suggestion.strip()
        if clean and clean not in unique:
            unique.append(clean)
    return unique[:8]
