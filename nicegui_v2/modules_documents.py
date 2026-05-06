from __future__ import annotations

import csv
from pathlib import Path

from nicegui import app, run, ui
from knowledge_helpers import summarize_sources_for_context


DOCUMENT_STANDARDS = {
    'ISO 9001': {
        'tag': 'Calidad',
        'summary': 'Base documental esperada para sostener un sistema de gestion de calidad orientado a procesos, control y mejora continua.',
        'records': [
            'Listado maestro de documentos vigentes',
            'Registros de capacitacion y competencias',
            'Registros de seguimiento de objetivos e indicadores',
            'Resultados de auditorias internas',
            'Registros de evaluacion de proveedores',
            'No conformidades, acciones correctivas y verificacion de eficacia',
            'Registros de satisfaccion del cliente o reclamos',
            'Actas de revision por la direccion',
        ],
    },
    'ISO 14001': {
        'tag': 'Ambiental',
        'summary': 'Estructura documental esperada para gestionar aspectos ambientales, cumplimiento legal y mejora del desempeno ambiental.',
        'records': [
            'Registros de seguimiento de aspectos significativos',
            'Registros de cumplimiento legal ambiental',
            'Resultados de monitoreos y mediciones',
            'Registros de residuos, emisiones o consumos relevantes',
            'Registros de simulacros o respuesta a emergencias',
            'Hallazgos de auditoria interna',
            'No conformidades y acciones correctivas ambientales',
            'Actas de revision por la direccion',
        ],
    },
    'ISO 45001': {
        'tag': 'Salud y seguridad',
        'summary': 'Documentacion tipica esperada para ordenar controles preventivos, riesgos laborales y cumplimiento de salud y seguridad ocupacional.',
        'records': [
            'Registros de entrega y control de EPP',
            'Registros de capacitaciones de SST',
            'Registros de inspecciones y observaciones de seguridad',
            'Registros de incidentes, accidentes y acciones correctivas',
            'Registros de seguimiento de objetivos de SST',
            'Resultados de auditorias internas',
            'Simulacros y pruebas de emergencia',
            'Actas de revision por la direccion',
        ],
    },
    'IATF 16949': {
        'tag': 'Automotriz',
        'summary': 'Biblioteca documental esperada para organizaciones automotrices con foco en prevencion, robustez del proceso y satisfaccion del cliente.',
        'records': [
            'PPAP y evidencia de aprobacion de partes',
            'Resultados de SPC y seguimiento de capacidad',
            'Resultados de MSA y estudios de medicion',
            'Auditorias de proceso tipo layered process audit',
            'Registros de cambios aprobados',
            'No conformidades internas y externas',
            'Analisis de reclamos, garantias y devoluciones',
            'Revision por la direccion con foco en performance automotriz',
        ],
    },
}

CHAPTER_SUMMARIES = {
    'ISO 9001': {
        '4': 'Define el contexto, las partes interesadas, el alcance y la arquitectura de procesos del sistema de calidad.',
        '5': 'Establece liderazgo, politica y responsabilidades para sostener el sistema.',
        '6': 'Ordena riesgos, objetivos y planificacion de cambios para que la gestion tenga direccion.',
        '7': 'Asegura recursos, competencias, comunicacion y control de la informacion documentada.',
        '8': 'Baja el sistema a la operacion: control, proveedores, produccion, trazabilidad y producto no conforme.',
        '9': 'Pide seguimiento, medicion, auditoria interna y revision por la direccion.',
        '10': 'Exige tratamiento de no conformidades y mejora continua.',
    },
    'ISO 14001': {
        '4': 'Define el marco del sistema ambiental, su alcance y el contexto en el que opera.',
        '5': 'Fija liderazgo, politica ambiental y responsabilidades del sistema.',
        '6': 'Ordena aspectos e impactos, obligaciones de cumplimiento, riesgos y objetivos ambientales.',
        '7': 'Asegura recursos, competencias, comunicaciones y control documental.',
        '8': 'Lleva el sistema a la operacion con controles ambientales y preparacion ante emergencias.',
        '9': 'Exige monitoreo, evaluacion de cumplimiento, auditoria interna y revision por la direccion.',
        '10': 'Pide reaccion ante no conformidades y mejora continua del desempeno ambiental.',
    },
    'ISO 45001': {
        '4': 'Define contexto, partes interesadas, alcance y estructura del sistema de SST.',
        '5': 'Refuerza liderazgo, politica, roles y participacion de los trabajadores.',
        '6': 'Ordena identificacion de peligros, evaluacion de riesgos, requisitos legales y objetivos de SST.',
        '7': 'Asegura recursos, competencias, toma de conciencia, comunicacion y documentacion.',
        '8': 'Baja el sistema a controles operacionales, cambios, contratistas y emergencias.',
        '9': 'Exige seguimiento, evaluacion de cumplimiento, auditoria interna y revision por la direccion.',
        '10': 'Pide investigacion de incidentes, acciones correctivas y mejora continua.',
    },
    'IATF 16949': {
        '4': 'Define el sistema automotriz, la interaccion de procesos y temas criticos como seguridad del producto.',
        '5': 'Refuerza liderazgo orientado a desempeno, eficacia y foco cliente.',
        '6': 'Ordena riesgos de negocio, contingencias, objetivos y cambios de proceso.',
        '7': 'Asegura recursos, medicion, competencias y documentacion propia del sector automotriz.',
        '8': 'Es el corazon operativo: APQP, AMFE, plan de control, proveedores, trazabilidad y no conformidades.',
        '9': 'Exige metricas, analisis, auditorias de sistema, proceso y producto, y revision por la direccion.',
        '10': 'Pide resolucion estructurada de problemas y mejora continua del sistema.',
    },
}

DATA_DIR = Path(__file__).resolve().parent / 'data'
REQUIREMENTS_FILE = DATA_DIR / 'document_requirements.csv'
EXAMPLES_DIR = DATA_DIR / 'document_examples'


def enabled_standards_for_company(company: dict | None, valor_afirmativo_fn) -> list[str]:
    if not company:
        return []
    mapping = [
        ('cert_iso_9001', 'ISO 9001'),
        ('cert_iso_14001', 'ISO 14001'),
        ('cert_iso_45001', 'ISO 45001'),
        ('cert_iatf', 'IATF 16949'),
    ]
    return [label for key, label in mapping if valor_afirmativo_fn(company.get(key))]


def go_to_documents_library() -> None:
    ui.navigate.to('/sistema-gestion/documentos')


def go_to_company_documents_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/documentos/empresa')


def load_requirement_rows() -> list[dict]:
    if not REQUIREMENTS_FILE.exists():
        return []
    with REQUIREMENTS_FILE.open('r', encoding='utf-8', newline='') as fh:
        return list(csv.DictReader(fh))


def requirements_for_standard(standard: str) -> list[dict]:
    return [row for row in load_requirement_rows() if row.get('norma') == standard]


def split_expected_documents(value: str | None) -> list[str]:
    raw = (value or '').replace(';', '|')
    return [item.strip() for item in raw.split('|') if item.strip()]


def chapter_sort_key(chapter: str) -> tuple:
    parts: list[int] = []
    for token in str(chapter).split('.'):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(999)
    return tuple(parts)


def requirement_sort_key(requirement: str) -> tuple:
    parts: list[int] = []
    for token in str(requirement).split('.'):
        try:
            parts.append(int(token))
        except ValueError:
            parts.append(999)
    return tuple(parts)


def expected_documents_for_standard(standard: str) -> list[str]:
    seen: list[str] = []
    for row in requirements_for_standard(standard):
        for document in split_expected_documents(row.get('documento_esperado')):
            if document not in seen:
                seen.append(document)
    return seen


def grouped_requirements_by_chapter(standard: str) -> list[tuple[str, list[dict]]]:
    chapters: dict[str, list[dict]] = {}
    for row in requirements_for_standard(standard):
        chapter = (row.get('capitulo') or '').strip() or '-'
        chapters.setdefault(chapter, []).append(row)
    ordered = sorted(chapters.items(), key=lambda item: chapter_sort_key(item[0]))
    return [(chapter, sorted(rows, key=lambda row: requirement_sort_key(row.get('requisito', '')))) for chapter, rows in ordered]


def _obligatory_badge_html(value: str, fix_text_fn) -> str:
    normalized = fix_text_fn(value).lower()
    bg = '#dcfce7' if normalized == 'si' else '#f1f5f9'
    color = '#166534' if normalized == 'si' else '#475569'
    return f'<span style="display:inline-flex;padding:4px 10px;border-radius:999px;background:{bg};color:{color};font-weight:700;">{fix_text_fn(value)}</span>'


def _example_reference(row: dict) -> tuple[str, Path]:
    standard = (row.get('norma') or 'norma').lower().replace(' ', '_')
    requirement = (row.get('requisito') or 'requisito').replace('.', '_')
    example_key = f'{standard}__{requirement}'
    return example_key, EXAMPLES_DIR / f'{example_key}.pdf'


def _render_example_button(*, row: dict) -> None:
    example_key, example_path = _example_reference(row)

    def show_example_placeholder() -> None:
        if example_path.exists():
            ui.notify(f'Ejemplo disponible: {example_path.name}', color='positive')
            return
        ui.notify(
            f'Ejemplo pendiente de carga para {row.get("requisito", "")}. Clave preparada: {example_key}',
            color='secondary',
            multi_line=True,
        )

    ui.button('Ver ejemplo', icon='article', on_click=show_example_placeholder).props('outline color=secondary')


def _render_requirement_dialog(*, row: dict, fix_text_fn, explain_requisito_fn=None) -> None:
    documents = split_expected_documents(row.get('documento_esperado'))
    example_key, example_path = _example_reference(row)
    with ui.dialog() as dialog, ui.card().classes('w-[780px] max-w-[96vw] p-6 rounded-[26px]'):
        with ui.row().classes('w-full items-start justify-between gap-4'):
            with ui.column().classes('gap-1'):
                ui.label(fix_text_fn(row['requisito'])).classes('text-2xl font-bold text-slate-900')
                ui.label(fix_text_fn(row['resumen'])).classes('text-slate-600 leading-7')
            ui.button(icon='close', on_click=dialog.close).props('flat round dense')
        with ui.row().classes('w-full gap-2 mt-3'):
            ui.badge(f'Capitulo {fix_text_fn(row["capitulo"])}').props('color=primary outline')
            ui.badge(fix_text_fn(row['tipo_documento'])).props('color=blue outline')
            ui.html(_obligatory_badge_html(row['obligatorio'], fix_text_fn))
            ui.badge(f'{len(documents)} documento(s)').props('color=grey outline')
        with ui.card().classes('w-full mt-4 p-4 border border-slate-200 shadow-none rounded-[20px]'):
            ui.label('Documentos base esperados').classes('text-lg font-semibold text-slate-900')
            ui.label('Aqui se muestra el paquete documental base sugerido para cubrir el requisito sin perder trazabilidad ni soporte auditor.').classes('text-slate-500 text-sm')
            with ui.column().classes('w-full gap-2 mt-3'):
                for idx, document in enumerate(documents, start=1):
                    ui.html(
                        f'''
                        <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.04);">
                            <div style="min-width:28px;height:28px;border-radius:999px;background:#dbeafe;color:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:800;">{idx}</div>
                            <div style="color:#0f172a;line-height:1.65;">{fix_text_fn(document)}</div>
                        </div>
                        '''
                    )
        with ui.card().classes('w-full mt-4 p-4 border border-slate-200 shadow-none rounded-[20px]'):
            ui.label('Guia practica del requisito').classes('text-lg font-semibold text-slate-900')
            ui.label(fix_text_fn(row['observacion_consultiva'])).classes('text-slate-600 leading-7')
            if explain_requisito_fn:
                async def mostrar_explicacion_ia() -> None:
                    with ui.dialog() as ia_dialog, ui.card().classes('w-[760px] max-w-[96vw] p-6 rounded-[26px]'):
                        with ui.row().classes('w-full items-start justify-between gap-4'):
                            with ui.column().classes('gap-1'):
                                ui.label('Explicacion con IA').classes('text-2xl font-bold text-slate-900')
                                ui.label('Traduccion operativa del requisito con lenguaje simple y enfoque practico.').classes('text-slate-600')
                            ui.button(icon='close', on_click=ia_dialog.close).props('flat round dense')
                        content = ui.column().classes('w-full gap-3 mt-4')
                        with content:
                            with ui.row().classes('w-full items-center gap-3'):
                                ui.spinner(size='lg')
                                ui.label('Generando explicacion...').classes('text-slate-500')
                        ia_dialog.open()
                        try:
                            respuesta = await run.io_bound(
                                explain_requisito_fn,
                                row.get('norma'),
                                row.get('requisito'),
                                row.get('resumen'),
                                row.get('observacion_consultiva'),
                            )
                            content.clear()
                            with content:
                                ui.html(
                                    f'<div style="padding:16px 18px;border-radius:18px;background:rgba(15,23,42,.04);color:#0f172a;line-height:1.8;white-space:pre-wrap;">{fix_text_fn(respuesta)}</div>'
                                )
                        except Exception as exc:
                            content.clear()
                            with content:
                                ui.label(f'No se pudo generar la explicacion con IA: {exc}').classes('text-red-600')

                with ui.row().classes('w-full justify-end mt-3'):
                    ui.button('Explicar con IA', icon='auto_awesome', on_click=mostrar_explicacion_ia).props('unelevated color=primary')
        with ui.card().classes('w-full mt-4 p-4 border border-slate-200 shadow-none rounded-[20px]'):
            ui.label('Ejemplo de referencia').classes('text-lg font-semibold text-slate-900')
            ui.label('Esta funcion ya esta preparada para vincular un ejemplo real por requisito desde la carpeta de ejemplos de la consultora.').classes('text-slate-500 text-sm')
            ui.html(
                f'''
                <div style="margin-top:12px;padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.04);color:#334155;line-height:1.7;">
                    <div><strong>Clave de ejemplo:</strong> {example_key}</div>
                    <div><strong>Ruta esperada:</strong> {example_path.name}</div>
                </div>
                '''
            )
            with ui.row().classes('w-full justify-end mt-4'):
                _render_example_button(row=row)
    ui.button('Ver detalle', icon='visibility', on_click=dialog.open).props('outline color=primary')


def _render_compact_requirement_row(*, row: dict, fix_text_fn, explain_requisito_fn=None) -> None:
    documents = split_expected_documents(row.get('documento_esperado'))
    first_document = documents[0] if documents else '-'
    with ui.card().classes('w-full p-4 border border-slate-200 shadow-none rounded-[20px]'):
        with ui.row().classes('w-full items-start justify-between gap-4 no-wrap'):
            with ui.column().classes('gap-1 col'):
                ui.label(fix_text_fn(row['requisito'])).classes('text-base font-bold text-slate-900')
                ui.label(fix_text_fn(row['resumen'])).classes('text-slate-600')
            with ui.column().classes('items-end gap-2 shrink-0'):
                ui.html(_obligatory_badge_html(row['obligatorio'], fix_text_fn))
                ui.badge(f'{len(documents)} doc.').props('color=grey outline')
        with ui.row().classes('w-full items-center justify-between gap-3 mt-3'):
            ui.html(
                f'''
                <div style="display:flex;gap:8px;flex-wrap:wrap;">
                    <span style="display:inline-flex;padding:4px 10px;border-radius:999px;background:rgba(31,126,214,.08);color:#1d4ed8;font-weight:700;">{fix_text_fn(row["tipo_documento"])}</span>
                    <span style="display:inline-flex;padding:4px 10px;border-radius:999px;background:rgba(15,23,42,.05);color:#0f172a;font-weight:700;">Documento base: {fix_text_fn(first_document)}</span>
                </div>
                '''
            )
            with ui.row().classes('items-center gap-2'):
                _render_example_button(row=row)
                _render_requirement_dialog(row=row, fix_text_fn=fix_text_fn, explain_requisito_fn=explain_requisito_fn)


def _render_requirement_results(*, rows: list[dict], fix_text_fn, explain_requisito_fn=None) -> None:
    with ui.column().classes('w-full gap-3'):
        for row in rows:
            _render_compact_requirement_row(row=row, fix_text_fn=fix_text_fn, explain_requisito_fn=explain_requisito_fn)


def _render_reference_collection_card(*, title: str, subtitle: str, items: list[str], accent: str, icon: str, fix_text_fn) -> None:
    with ui.card().classes('ideas-panel col'):
        ui.label(title).classes('ideas-section-title')
        ui.label(subtitle).classes('ideas-section-note')
        ui.html(
            f'''
            <div style="margin-top:10px;display:flex;align-items:center;justify-content:space-between;gap:12px;padding:14px 16px;border-radius:18px;background:{accent};">
                <div>
                    <div style="font-weight:800;color:#0f172a;">{len(items)} elementos disponibles</div>
                    <div style="color:#475569;margin-top:4px;">Explora esta referencia solo cuando la necesites, sin cargar la pantalla principal.</div>
                </div>
                <div style="min-width:42px;height:42px;border-radius:14px;background:rgba(255,255,255,.75);display:flex;align-items:center;justify-content:center;color:#0f172a;font-weight:800;">{icon}</div>
            </div>
            '''
        )
        with ui.dialog() as dialog, ui.card().classes('w-[820px] max-w-[96vw] p-6 rounded-[26px]'):
            with ui.row().classes('w-full items-start justify-between gap-4'):
                with ui.column().classes('gap-1'):
                    ui.label(title).classes('text-2xl font-bold text-slate-900')
                    ui.label(subtitle).classes('text-slate-600')
                ui.button(icon='close', on_click=dialog.close).props('flat round dense')
            with ui.column().classes('w-full gap-2 mt-4'):
                for idx, item in enumerate(items, start=1):
                    ui.html(
                        f'''
                        <div style="display:flex;gap:12px;align-items:flex-start;padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.04);">
                            <div style="min-width:28px;height:28px;border-radius:999px;background:#dbeafe;color:#1d4ed8;display:flex;align-items:center;justify-content:center;font-weight:800;">{idx}</div>
                            <div style="color:#0f172a;line-height:1.65;">{fix_text_fn(item)}</div>
                        </div>
                        '''
                    )
        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('Explorar', icon='visibility', on_click=dialog.open).props('outline color=primary')


def _render_search_explorer(*, requirement_rows: list[dict], fix_text_fn, explain_requisito_fn=None) -> None:
    ui.html(
        '''
        <div style="margin-top:16px;padding:24px;border-radius:22px;border:1px dashed rgba(15,23,42,.18);background:rgba(255,255,255,.7);">
            <div style="font-size:1.1rem;font-weight:800;color:#0f172a;">Buscador de capitulos y requisitos</div>
            <div style="margin-top:8px;color:#475569;line-height:1.7;">
                Escribe un numero de capitulo o requisito, por ejemplo <strong>4</strong>, <strong>6.1</strong> o <strong>8.5.6</strong>, y veras debajo solo los resultados relevantes para abrir en detalle.
            </div>
        </div>
        '''
    )
    search_input = ui.input(
        label='Buscar capitulo o requisito',
        placeholder='Ejemplo: 4, 6.1, 8.5.6',
    ).classes('w-full mt-4').props('outlined clearable')
    search_feedback = ui.label('La busqueda se mantiene vacia hasta que escribas un capitulo o requisito.').classes('text-slate-500 mt-2')
    search_results = ui.column().classes('w-full gap-3 mt-4')

    def trigger_search(*_args) -> None:
        term = (search_input.value or '').strip().lower()
        search_results.clear()
        if not term:
            search_feedback.set_text('La busqueda se mantiene vacia hasta que escribas un capitulo o requisito.')
            return
        matches = [
            row for row in requirement_rows
            if (row.get('capitulo') or '').strip().lower().startswith(term)
            or (row.get('requisito') or '').strip().lower().startswith(term)
        ]
        if not matches:
            search_feedback.set_text('No se encontraron requisitos para ese criterio. Prueba con un numero de capitulo o un requisito mas especifico.')
            with search_results:
                ui.html(
                    '''
                    <div style="margin-top:6px;padding:14px 16px;border-radius:18px;background:rgba(15,23,42,.04);color:#64748b;">
                        No hay coincidencias para la busqueda ingresada.
                    </div>
                    '''
                )
            return
        search_feedback.set_text(f'Se encontraron {len(matches)} requisito(s) para "{term}".')
        with search_results:
            _render_requirement_results(rows=matches, fix_text_fn=fix_text_fn, explain_requisito_fn=explain_requisito_fn)

    def on_search_input_change(_event) -> None:
        if not (search_input.value or '').strip():
            trigger_search()

    search_input.on('update:model-value', on_search_input_change)
    with ui.row().classes('w-full justify-end gap-3 mt-2'):
        ui.button('Buscar', icon='search', on_click=trigger_search).props('outline color=primary')


def _render_standard_tabs(*, fix_text_fn, standard_names: list[str], explain_requisito_fn=None) -> None:
    if not standard_names:
        ui.label('No hay normas seleccionadas para mostrar.').classes('text-slate-500')
        return
    with ui.tabs().classes('w-full mt-6') as tabs:
        tab_map = {name: ui.tab(name, icon='fact_check') for name in standard_names}
    with ui.tab_panels(tabs, value=next(iter(tab_map.values()))).classes('w-full bg-transparent'):
        for standard in standard_names:
            meta = DOCUMENT_STANDARDS[standard]
            requirement_rows = requirements_for_standard(standard)
            expected_documents = expected_documents_for_standard(standard)
            chapter_groups = grouped_requirements_by_chapter(standard)
            with ui.tab_panel(tab_map[standard]).classes('px-0'):
                ui.html(
                    f'''<div class="ideas-grid-2">
                    <div class="ideas-service-card">
                        <div class="icon">{meta["tag"]}</div>
                        <h3>{standard}</h3>
                        <p>{meta["summary"]}</p>
                    </div>
                    <div class="ideas-service-card">
                        <div class="icon">Uso recomendado</div>
                        <h3>Como usar esta biblioteca</h3>
                        <p>Utiliza los capitulos como filtro natural de la norma. Luego abre solo el requisito que quieras analizar en detalle y evita ruido visual innecesario.</p>
                    </div>
                    </div>'''
                )
                with ui.card().classes('ideas-panel w-full mt-4'):
                    ui.label('Biblioteca estructurada por capitulo').classes('ideas-section-title')
                    ui.label('Cada capitulo resume lo que espera la norma y cada requisito abre un detalle puntual con documentos base y guia practica.').classes('ideas-section-note')
                    if requirement_rows:
                        ui.html(
                            '''
                            <div style="margin-top:10px;padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.04);color:#475569;line-height:1.6;">
                                <strong style="color:#0f172a;">Criterio de la columna obligatoria:</strong>
                                <span><strong>SI</strong> indica que la norma exige informacion documentada o evidencia documental explicita.</span>
                                <span style="margin-left:8px;"><strong>NO</strong> indica documento recomendable o de buena practica para asegurar cumplimiento, control y trazabilidad.</span>
                            </div>
                            '''
                        )
                        with ui.tabs().classes('w-full mt-4') as chapter_tabs:
                            intro_tab = ui.tab('Explorar', icon='filter_alt')
                            chapter_tab_map = {
                                chapter: ui.tab(f'Cap. {fix_text_fn(chapter)}', icon='folder_open')
                                for chapter, _rows in chapter_groups
                            }
                        with ui.tab_panels(chapter_tabs, value=intro_tab).classes('w-full bg-transparent px-0'):
                            with ui.tab_panel(intro_tab).classes('px-0'):
                                _render_search_explorer(requirement_rows=requirement_rows, fix_text_fn=fix_text_fn, explain_requisito_fn=explain_requisito_fn)
                            for chapter, rows in chapter_groups:
                                chapter_summary = CHAPTER_SUMMARIES.get(standard, {}).get(chapter, 'Este capitulo ordena requisitos relevantes para estructurar el sistema y su soporte documental.')
                                with ui.tab_panel(chapter_tab_map[chapter]).classes('px-0'):
                                    with ui.card().classes('w-full mt-3 p-4 border border-slate-200 shadow-none rounded-[22px]'):
                                        ui.label(f'Capitulo {fix_text_fn(chapter)}').classes('text-xl font-bold text-slate-900')
                                        ui.label(fix_text_fn(chapter_summary)).classes('text-slate-600 leading-7')
                                    with ui.column().classes('w-full gap-3 mt-3'):
                                        for row in rows:
                                            _render_compact_requirement_row(row=row, fix_text_fn=fix_text_fn, explain_requisito_fn=explain_requisito_fn)
                    else:
                        ui.label('No hay requisitos cargados para esta norma.').classes('text-slate-500 mt-3')
                with ui.row().classes('w-full gap-4 mt-4'):
                    _render_reference_collection_card(
                        title='Documentos esperados',
                        subtitle='Documentacion base esperada para estructurar el sistema de gestion de la norma.',
                        items=expected_documents,
                        accent='rgba(31,126,214,.08)',
                        icon='DOC',
                        fix_text_fn=fix_text_fn,
                    )
                    _render_reference_collection_card(
                        title='Registros y evidencias esperadas',
                        subtitle='Registros tipicos que suelen requerirse para demostrar aplicacion y trazabilidad.',
                        items=meta['records'],
                        accent='rgba(16,185,129,.10)',
                        icon='REG',
                        fix_text_fn=fix_text_fn,
                    )


def register_documents_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    fix_text = deps['fix_text']
    certifications_summary = deps['certifications_summary']
    valor_afirmativo = deps['valor_afirmativo']
    set_selection = deps['set_selection']
    obtener_fuentes_empresa = deps['obtener_fuentes_empresa']
    explicar_requisito_iso = deps['explicar_requisito_iso']

    @ui.page('/sistema-gestion/documentos')
    def documents_library_page() -> None:
        if not ensure_platform_access():
            return
        with shell('Gestion de documentos', back_route='/sistema-gestion') as shell_container:
            with shell_container:
                ui.label('Gestion de documentos').classes('ideas-kicker')
                ui.label('Biblioteca general de la consultora').classes('text-3xl font-bold text-slate-900')
                ui.label('Esta biblioteca centraliza el estandar documental de IDEAS Consulting. Aqui se encuentran las normas, los documentos esperados y los registros de referencia para estructurar implementaciones, auditorias y planes de certificacion.').classes('ideas-subtitle mb-4')
                ui.html(
                    '''
                    <div class="ideas-workspace-banner w-full mt-4">
                        <div class="eyebrow">Biblioteca general</div>
                        <div class="headline">Estandarizacion y requerimientos por norma</div>
                        <div class="support">
                            Esta vista no depende de ninguna empresa en particular. Sirve como biblioteca maestra de la consultora para consultar el estandar y los documentos esperados por ISO 9001, ISO 14001, ISO 45001 e IATF 16949.
                        </div>
                    </div>
                    '''
                )
                ui.html(
                    f'''<div class="ideas-grid-2" style="margin-top:18px;">
                    <div class="ideas-quick-card"><div class="label">Uso</div><div class="value">Biblioteca general</div><div class="detail">Referencia transversal para consultoria, diagnostico, auditoria e implementacion.</div></div>
                    <div class="ideas-quick-card"><div class="label">Normas disponibles</div><div class="value">{len(DOCUMENT_STANDARDS)}</div><div class="detail">{", ".join(DOCUMENT_STANDARDS.keys())}</div></div>
                    </div>'''
                )
                _render_standard_tabs(fix_text_fn=fix_text, standard_names=list(DOCUMENT_STANDARDS.keys()), explain_requisito_fn=explicar_requisito_iso)
                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ui.button('Ir a biblioteca por empresa', icon='business', on_click=lambda: ui.navigate.to('/sistema-gestion/documentos/empresa')).props('outline')
                    ui.button('Volver al sistema de gestion', icon='arrow_back', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('outline')

    @ui.page('/sistema-gestion/documentos/empresa')
    def company_documents_page() -> None:
        if not ensure_platform_access():
            return
        company_map = company_options()
        selected_company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        if not selected_company_id and company_map:
            selected_company_id = next(iter(company_map.keys()))
            app.storage.user['management_company_id'] = selected_company_id
        selected_company = obtener_empresa_detalle(selected_company_id) if selected_company_id else None
        enabled = enabled_standards_for_company(selected_company, valor_afirmativo)
        visible_standards = enabled or list(DOCUMENT_STANDARDS.keys())

        with shell('Gestion documental por empresa', back_route='/sistema-gestion') as shell_container:
            with shell_container:
                ui.label('Gestion de documentos').classes('ideas-kicker')
                ui.label('Biblioteca particular por empresa').classes('text-3xl font-bold text-slate-900')
                ui.label('Esta vista conecta la biblioteca general con la empresa activa, para mostrar las normas y checklist que le resultan mas relevantes segun su estado de certificacion.').classes('ideas-subtitle mb-4')
                if company_map and str(app.storage.user.get('role') or '') == 'admin':
                    company_select = ui.select(company_map, value=selected_company_id, label='Empresa de referencia').classes('w-full').props('outlined')
                    company_select.on_value_change(
                        lambda _e: (
                            app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                            set_selection(int(company_select.value), None) if company_select.value else None,
                            ui.navigate.to('/sistema-gestion/documentos/empresa'),
                        )
                    )
                if selected_company:
                    company_name = fix_text(selected_company.get('razon_social', ''))
                    enabled_text = ', '.join(enabled) if enabled else 'Sin certificaciones registradas'
                    detail_text = 'Se muestran primero las normas asociadas a las certificaciones registradas.' if enabled else 'Como no hay certificaciones cargadas, se muestra la biblioteca completa como base de preparacion.'
                    ia_activa = valor_afirmativo(selected_company.get('agente_ia_activo'))

                    def open_document_copilot() -> None:
                        fuentes = obtener_fuentes_empresa(int(selected_company_id)) or []
                        context_values = [
                            company_name,
                            enabled_text,
                            certifications_summary(selected_company),
                            *visible_standards,
                            'documentos procedimientos registros auditoria requisitos',
                        ]
                        matched_sources = summarize_sources_for_context(fuentes, context_values, limit=6)
                        with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[96vw] p-6 rounded-[26px]'):
                            with ui.row().classes('w-full items-start justify-between gap-4'):
                                with ui.column().classes('gap-1'):
                                    ui.label('Copiloto IA documental').classes('text-2xl font-bold text-slate-900')
                                    ui.label('Resumen contextual preparado a partir de la base de conocimiento de esta empresa.').classes('text-slate-600')
                                ui.button(icon='close', on_click=dialog.close).props('flat round dense')

                            ui.html(
                                f'''<div class="ideas-grid-3" style="margin-top:16px;">
                                <div class="ideas-quick-card"><div class="label">EMPRESA</div><div class="value">{company_name}</div><div class="detail">Contexto documental activo.</div></div>
                                <div class="ideas-quick-card"><div class="label">FUENTES</div><div class="value">{len(fuentes)}</div><div class="detail">Fuentes cargadas en la base de conocimiento.</div></div>
                                <div class="ideas-quick-card"><div class="label">COINCIDENCIAS</div><div class="value">{len(matched_sources)}</div><div class="detail">Bloques relevantes para normas, procedimientos y registros.</div></div>
                                </div>'''
                            )

                            if not fuentes:
                                with ui.card().classes('w-full mt-4 p-4 border border-amber-200 bg-amber-50 shadow-none rounded-[20px]'):
                                    ui.label('Todavia no hay fuentes cargadas para esta empresa.').classes('text-lg font-bold text-amber-700')
                                    ui.label('Carga manuales, procedimientos, instructivos o texto libre desde Empresas > Base de Conocimiento IA para habilitar ayuda contextual.').classes('text-amber-700')
                            else:
                                with ui.card().classes('w-full mt-4 p-4 border border-slate-200 shadow-none rounded-[20px]'):
                                    ui.label('Enfoque sugerido').classes('text-lg font-bold text-slate-900')
                                    ui.label('Usa primero estas fuentes para validar si la documentacion cubre los requisitos y registros criticos de las normas visibles.').classes('text-slate-600')

                                with ui.column().classes('w-full gap-3 mt-4'):
                                    for item in matched_sources:
                                        with ui.card().classes('w-full p-4 border border-slate-200 shadow-none rounded-[20px]'):
                                            with ui.row().classes('w-full items-center justify-between gap-3'):
                                                with ui.column().classes('gap-1'):
                                                    ui.label(fix_text(item.get('titulo', 'Fuente'))).classes('text-base font-bold text-slate-900')
                                                    ui.label(f'Tipo: {fix_text(item.get("tipo", "texto"))}').classes('text-sm text-slate-500')
                                                ui.badge(
                                                    f'{len(item.get("matched_keywords", []))} coincidencias' if item.get('matched_keywords') else 'Fuente general'
                                                ).props('color=primary outline')
                                            if item.get('matched_keywords'):
                                                ui.label(
                                                    f'Palabras clave detectadas: {fix_text(", ".join(item["matched_keywords"]))}'
                                                ).classes('text-sm text-slate-500 mt-2')
                                            ui.label(fix_text(item.get('snippet', ''))).classes('text-slate-700 leading-7 mt-2')

                            with ui.row().classes('w-full justify-end mt-5'):
                                ui.button('Cerrar', on_click=dialog.close).props('flat')
                        dialog.open()
                    ui.html(
                        f'''<div class="ideas-grid-2" style="margin-top:18px;">
                        <div class="ideas-quick-card"><div class="label">Empresa activa</div><div class="value">{company_name}</div><div class="detail">Certificaciones registradas: {certifications_summary(selected_company)}</div></div>
                        <div class="ideas-quick-card"><div class="label">Normas visibles</div><div class="value">{enabled_text}</div><div class="detail">{detail_text}</div></div>
                        </div>'''
                    )
                    if ia_activa:
                        with ui.row().classes('w-full justify-end mt-3'):
                            ui.button(
                                'Copiloto IA documental',
                                icon='auto_awesome',
                                on_click=open_document_copilot,
                            ).props('unelevated color=primary')
                _render_standard_tabs(fix_text_fn=fix_text, standard_names=visible_standards, explain_requisito_fn=explicar_requisito_iso)
                with ui.row().classes('w-full justify-end gap-3 mt-6'):
                    ui.button('Abrir biblioteca general', icon='library_books', on_click=go_to_documents_library).props('outline')
                    ui.button('Volver al sistema de gestion', icon='arrow_back', on_click=lambda: ui.navigate.to('/sistema-gestion')).props('outline')
