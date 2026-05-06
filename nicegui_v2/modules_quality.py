from __future__ import annotations

import datetime
import json
from pathlib import Path

from nicegui import app, events, run, ui
from knowledge_helpers import build_quality_brainstorm_lines, summarize_sources_for_context


UPLOAD_DIR = Path(__file__).resolve().parents[1] / 'uploads' / 'quality'


def go_to_quality_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/calidad')


def _extract_int(value) -> int | None:
    try:
        return int(value)
    except Exception:
        pass
    if isinstance(value, dict):
        for key in ('id', 'row'):
            found = _extract_int(value.get(key))
            if found is not None:
                return found
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_int(item)
            if found is not None:
                return found
    return None


def _save_uploaded_file(company_id: int, event: events.UploadEventArguments) -> str:
    target_dir = UPLOAD_DIR / f'empresa_{company_id}'
    target_dir.mkdir(parents=True, exist_ok=True)
    upload = getattr(event, 'file', None)
    raw_name = getattr(upload, 'name', None) or getattr(event, 'name', None) or getattr(getattr(event, 'content', None), 'name', None) or 'upload.bin'
    target_path = target_dir / Path(str(raw_name)).name
    if upload is not None:
        data = getattr(upload, '_data', None)
        path = getattr(upload, '_path', None)
        if isinstance(data, (bytes, bytearray)):
            target_path.write_bytes(bytes(data))
            return str(target_path)
        if path:
            source = Path(str(path))
            if source.exists():
                target_path.write_bytes(source.read_bytes())
                return str(target_path)
    content = getattr(event, 'content', None)
    if content is None:
        raise ValueError('El archivo cargado no contiene contenido legible.')
    if hasattr(content, 'seek'):
        content.seek(0)
    payload = content.read() if hasattr(content, 'read') else content
    target_path.write_bytes(payload)
    return str(target_path)


def _metrics_html(total_cases: int, open_cases: int, with_evidence: int) -> str:
    return f'''
    <div class="ideas-grid-3" style="margin-top:18px;">
        <div class="ideas-quick-card">
            <div class="label">CASOS TOTALES</div>
            <div class="value">{total_cases}</div>
            <div class="detail">Analisis de problemas registrados para la empresa activa.</div>
        </div>
        <div class="ideas-quick-card">
            <div class="label">CASOS ABIERTOS</div>
            <div class="value">{open_cases}</div>
            <div class="detail">Casos que aun requieren seguimiento o cierre formal.</div>
        </div>
        <div class="ideas-quick-card">
            <div class="label">EVIDENCIA VISUAL</div>
            <div class="value">{with_evidence}</div>
            <div class="detail">Registros con evidencia visual general adjunta.</div>
        </div>
    </div>
    '''


def _overview_html(prepared_rows: list[dict]) -> str:
    total = len(prepared_rows)
    advanced = sum(1 for item in prepared_rows if str(item.get('overview_status') or '') == 'Avanzado')
    closed = sum(1 for item in prepared_rows if str(item.get('estado') or '') == 'Cerrado')
    avg_progress = round(sum(int(item.get('progress_pct') or 0) for item in prepared_rows) / max(1, total)) if total else 0
    return f'''
    <div class="ideas-grid-4" style="margin-top:18px;display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:16px;">
        <div class="ideas-quick-card"><div class="label">8D ABIERTOS</div><div class="value">{total - closed}</div><div class="detail">Casos activos o en seguimiento.</div></div>
        <div class="ideas-quick-card"><div class="label">8D AVANZADOS</div><div class="value">{advanced}</div><div class="detail">Casos por encima del 75%.</div></div>
        <div class="ideas-quick-card"><div class="label">8D CERRADOS</div><div class="value">{closed}</div><div class="detail">Casos con cierre final informado.</div></div>
        <div class="ideas-quick-card"><div class="label">AVANCE PROMEDIO</div><div class="value">{avg_progress}%</div><div class="detail">Cumplimiento global de acciones.</div></div>
    </div>
    '''


def _parse_d2_details(text: str) -> dict[str, str]:
    details = {
        'descripcion_libre': '',
        'cliente': '',
        'piezas_defectos': '',
        'quien_detecto': '',
        'como_detecto': '',
        'cuando_detecto': '',
    }
    raw_text = str(text or '').strip()
    if not raw_text:
        return details

    markers = {
        'Descripción general:': 'descripcion_libre',
        'Cliente:': 'cliente',
        'Piezas con defectos:': 'piezas_defectos',
        'Quién detectó el problema:': 'quien_detecto',
        'Cómo lo detectó:': 'como_detecto',
        'Cuándo lo detectó:': 'cuando_detecto',
    }
    found_marker = False
    for line in raw_text.splitlines():
        line_clean = line.strip()
        for marker, key in markers.items():
            if line_clean.startswith(marker):
                details[key] = line_clean.replace(marker, '', 1).strip()
                found_marker = True
                break
        else:
            if not found_marker:
                details['descripcion_libre'] = raw_text
                break
    return details


def _compose_d2_description(
    descripcion_libre: str,
    cliente: str,
    piezas_defectos: str,
    quien_detecto: str,
    como_detecto: str,
    cuando_detecto: str,
) -> str:
    blocks = [
        f"Descripción general: {str(descripcion_libre or '').strip()}",
        f"Cliente: {str(cliente or '').strip()}",
        f"Piezas con defectos: {str(piezas_defectos or '').strip()}",
        f"Quién detectó el problema: {str(quien_detecto or '').strip()}",
        f"Cómo lo detectó: {str(como_detecto or '').strip()}",
        f"Cuándo lo detectó: {str(cuando_detecto or '').strip()}",
    ]
    return '\n'.join(block for block in blocks if block.split(':', 1)[1].strip())


def _csv_to_list(value: str) -> list[str]:
    return [item.strip() for item in str(value or '').split(',') if item.strip()]


def _list_to_csv(values: list[str]) -> str:
    cleaned = []
    for value in values:
        item = str(value or '').strip()
        if item and item not in cleaned:
            cleaned.append(item)
    return ', '.join(cleaned)


def _build_action_summary(actions: list[dict]) -> str:
    if not actions:
        return ''
    parts = []
    for action in actions[:6]:
        accion = str(action.get('accion') or '').strip()
        responsable = str(action.get('responsable') or '').strip()
        progreso = str(action.get('progreso') or '').strip()
        suffix = ' · '.join(item for item in [responsable, progreso] if item)
        if accion:
            parts.append(f'{accion} ({suffix})' if suffix else accion)
    return ' | '.join(parts)


def _action_rows_for_table(rows: list[dict], fix_text_fn) -> list[dict]:
    return [
        {
            'id': item.get('id'),
            'accion': fix_text_fn(item.get('accion', '')),
            'responsable': fix_text_fn(item.get('responsable', '')),
            'fecha': fix_text_fn(item.get('fecha', '')),
            'progreso': fix_text_fn(item.get('progreso', '')),
            'evidencia': ', '.join(Path(path).name for path in str(item.get('evidencia_path', '')).split(',') if path.strip()) or 'Sin archivo',
            'acciones': '',
        }
        for item in rows
    ]


def _split_factor_problem(value: str) -> tuple[str, str]:
    text = str(value or '').strip()
    if ' || ' in text:
        factor, problema = text.split(' || ', 1)
        return factor.strip(), problema.strip()
    return '', text


def _merge_factor_problem(factor: str, problema: str) -> str:
    factor_text = str(factor or '').strip()
    problema_text = str(problema or '').strip()
    if factor_text and problema_text:
        return f'{factor_text} || {problema_text}'
    return problema_text or factor_text


def _parse_team_members(value: str) -> list[dict]:
    members: list[dict] = []
    for line in str(value or '').splitlines():
        text = line.strip()
        if not text:
            continue
        role_type = 'Miembro'
        lowered = text.lower()
        if lowered.startswith('líder:') or lowered.startswith('lider:'):
            role_type = 'Líder'
            text = text.split(':', 1)[1].strip()
        elif lowered.startswith('miembro:'):
            text = text.split(':', 1)[1].strip()
        name = text
        function = ''
        if '|' in text:
            left, right = text.split('|', 1)
            name = left.strip()
            function = right.strip()
        elif ' - ' in text:
            left, right = text.split(' - ', 1)
            name = left.strip()
            function = right.strip()
        members.append({'tipo': role_type, 'nombre': name, 'funcion': function})
    return members


def _compose_team_members(members: list[dict]) -> str:
    rows = []
    for idx, item in enumerate(members):
        nombre = str(item.get('nombre') or '').strip()
        funcion = str(item.get('funcion') or '').strip()
        if not nombre:
            continue
        prefix = 'Líder' if idx == 0 else 'Miembro'
        detail = f'{nombre} | {funcion}' if funcion else nombre
        rows.append(f'{prefix}: {detail}')
    return '\n'.join(rows)


def _load_json_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    raw = str(value or '').strip()
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _bool_from_any(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    return str(value or '').strip().lower() in {'1', 'true', 'si', 'sí', 'yes', 'y', 'on'}


def _safe_action_rows(rows: list[dict] | None) -> list[dict]:
    cleaned: list[dict] = []
    for row in rows or []:
        if not isinstance(row, dict):
            continue
        cleaned.append(
            {
                'accion': str(row.get('accion') or '').strip(),
                'responsable': str(row.get('responsable') or '').strip(),
                'fecha': str(row.get('fecha') or '').strip(),
                'progreso': str(row.get('progreso') or '').strip(),
                'evidencia_path': str(row.get('evidencia_path') or '').strip(),
            }
        )
    return cleaned


def _parse_dot_date(value: str) -> datetime.datetime | None:
    text = str(value or '').strip()
    if not text:
        return None
    for fmt in ('%d.%m.%Y', '%Y-%m-%d', '%d/%m/%Y'):
        try:
            return datetime.datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _max_action_date(rows: list[dict]) -> str:
    parsed = [_parse_dot_date(item.get('fecha', '')) for item in rows if str(item.get('progreso') or '').strip() == '100%']
    parsed = [item for item in parsed if item is not None]
    return max(parsed).strftime('%d.%m.%Y') if parsed else ''


def _calc_completion_pct(rows: list[dict]) -> int:
    valid = [row for row in rows if str(row.get('accion') or '').strip()]
    if not valid:
        return 0
    mapping = {'0%': 0, '25%': 25, '50%': 50, '75%': 75, '100%': 100}
    values = [mapping.get(str(row.get('progreso') or '0%').strip(), 0) for row in valid]
    return round(sum(values) / max(1, len(values)))


def _overview_badge(progress_pct: int, estado: str) -> tuple[str, str]:
    estado_txt = str(estado or '').strip()
    if estado_txt == 'Cerrado':
        return 'Cerrado', 'positive'
    if progress_pct >= 75:
        return 'Avanzado', 'primary'
    if progress_pct >= 25:
        return 'En proceso', 'warning'
    return 'Abierto', 'negative'


def _parse_factor_lines(categoria: str, value: str) -> list[str]:
    items = []
    for raw in str(value or '').replace(';', '\n').splitlines():
        part = raw.strip(' -\t')
        if part:
            items.append(f'{categoria}: {part}')
    return items


def _show_quality_editor(
    ui,
    *,
    company_id: int,
    company_name: str,
    company_info: dict | None = None,
    ia_enabled: bool = False,
    obtener_fuentes_fn=None,
    sugerir_causas_ishikawa_fn=None,
    row: dict | None,
    fix_text_fn,
    crear_problema_fn,
    actualizar_problema_fn,
    guardar_5p_fn,
    guardar_ishikawa_fn,
    obtener_acciones_fn,
    guardar_accion_fn,
    eliminar_accion_fn,
    generar_pdf_8d_fn=None,
    preset_numero_8d: str = '',
) -> None:
    company_info = company_info or {}
    is_edit = bool(row)
    current_row = row or {'numero_8d': str(preset_numero_8d or '').strip()}
    data_5p = current_row.get('data_5p') or {}
    data_ishikawa = current_row.get('data_ishikawa') or {}
    d2_details = _parse_d2_details(current_row.get('d2_descripcion', ''))
    uploaded_paths = [item.strip() for item in str(current_row.get('archivos_path') or '').split(',') if item.strip()]
    initial_retained = _csv_to_list(data_ishikawa.get('factores_retenidos', ''))
    occ_factor_initial, occ_problem_initial = _split_factor_problem(data_5p.get('occ_problema', ''))
    det_factor_initial, det_problem_initial = _split_factor_problem(data_5p.get('det_problema', ''))
    team_members = _parse_team_members(current_row.get('d1_equipo', ''))
    nok_ok_data = _load_json_dict(current_row.get('nok_ok_details'))
    d3_data = _load_json_dict(current_row.get('d3_sorting_details'))
    d4_data = _load_json_dict(current_row.get('d4_simulation_details'))
    d5_training_data = _load_json_dict(current_row.get('d5_training_details'))
    d7_docs_data = _load_json_dict(current_row.get('d7_docs_update'))
    d8_closure_data = _load_json_dict(current_row.get('d8_closure_details'))
    problema_state = {'id': int(current_row['id']) if is_edit and current_row.get('id') else None}
    retained_state = {'values': list(initial_retained)}
    action_state = {
        'D3': _safe_action_rows(d3_data.get('acciones')),
        'D5': [],
        'D6': [],
    }
    d3_draft_files: list[str] = []
    d5_draft_files: list[str] = []
    d6_draft_files: list[str] = []
    nok_part_image_state = {'path': str(nok_ok_data.get('nok_part_image') or '').strip()}
    ok_part_image_state = {'path': str(nok_ok_data.get('ok_part_image') or '').strip()}

    async def open_quality_copilot() -> None:
        fuentes = obtener_fuentes_fn(int(company_id)) if obtener_fuentes_fn else []
        context_values = [
            company_name,
            current_row.get('titulo', ''),
            current_row.get('d2_descripcion', ''),
            getattr(effect_input, 'value', ''),
            *retained_state['values'],
            getattr(occ_factor_select, 'value', ''),
            getattr(det_factor_select, 'value', ''),
        ]
        matched_sources = summarize_sources_for_context(fuentes, context_values, limit=5)
        brainstorm_lines = build_quality_brainstorm_lines(
            retained_state['values'],
            getattr(effect_input, 'value', ''),
            matched_sources,
        )

        with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[96vw] p-6 rounded-[26px]'):
            with ui.row().classes('w-full items-start justify-between gap-4'):
                with ui.column().classes('gap-1'):
                    ui.label('Copiloto IA para Ishikawa').classes('text-2xl font-bold text-slate-900')
                    ui.label('Sugerencias breves basadas en OpenAI y en el contexto del caso actual.').classes('text-slate-600')
                ui.button(icon='close', on_click=dialog.close).props('flat round dense')

            ui.html(
                f'''<div class="ideas-grid-3" style="margin-top:16px;">
                <div class="ideas-quick-card"><div class="label">EMPRESA</div><div class="value">{company_name}</div><div class="detail">Contexto del caso de calidad.</div></div>
                <div class="ideas-quick-card"><div class="label">FUENTES</div><div class="value">{len(fuentes or [])}</div><div class="detail">Fuentes disponibles para este cliente.</div></div>
                <div class="ideas-quick-card"><div class="label">FACTORES</div><div class="value">{len(retained_state["values"])}</div><div class="detail">Factores retenidos listos para profundizar.</div></div>
                </div>'''
            )

            content = ui.column().classes('w-full gap-3 mt-4')
            with content:
                with ui.row().classes('w-full items-center gap-3'):
                    ui.spinner(size='lg')
                    ui.label('Generando sugerencias...').classes('text-slate-500')
            dialog.open()

            try:
                if not sugerir_causas_ishikawa_fn:
                    raise RuntimeError('La funcion sugerir_causas_ishikawa no fue inyectada en el modulo.')
                respuesta = await run.io_bound(
                    sugerir_causas_ishikawa_fn,
                    compose_d2(),
                    retained_state['values'],
                )
                content.clear()
                with content:
                    with ui.card().classes('w-full mt-1 p-4 border border-slate-200 shadow-none rounded-[20px]'):
                        ui.label('Sugerencias IA').classes('text-lg font-bold text-slate-900')
                        ui.html(
                            f'<div style="padding:12px 14px;border-radius:16px;background:rgba(15,23,42,.04);color:#0f172a;line-height:1.8;white-space:pre-wrap;">{fix_text_fn(respuesta)}</div>'
                        )
                    if brainstorm_lines:
                        with ui.card().classes('w-full p-4 border border-slate-200 shadow-none rounded-[20px]'):
                            ui.label('Contexto documental sugerido').classes('text-lg font-bold text-slate-900')
                            with ui.column().classes('w-full gap-2 mt-3'):
                                for line in brainstorm_lines:
                                    ui.html(f'<div class="ideas-mini-list"><div class="item"><div class="dot"></div><div>{fix_text_fn(line)}</div></div></div>')
                    for item in matched_sources:
                        with ui.card().classes('w-full p-4 border border-slate-200 shadow-none rounded-[20px]'):
                            with ui.row().classes('w-full items-center justify-between gap-3'):
                                with ui.column().classes('gap-1'):
                                    ui.label(fix_text_fn(item.get('titulo', 'Fuente'))).classes('text-base font-bold text-slate-900')
                                    ui.label(f'Tipo: {fix_text_fn(item.get("tipo", "texto"))}').classes('text-sm text-slate-500')
                                ui.badge(
                                    f'{len(item.get("matched_keywords", []))} coincidencias' if item.get('matched_keywords') else 'Fuente general'
                                ).props('color=primary outline')
                            ui.label(fix_text_fn(item.get('snippet', ''))).classes('text-slate-700 leading-7 mt-2')
            except Exception as exc:
                content.clear()
                with content:
                    ui.label(f'No se pudieron generar sugerencias con IA: {exc}').classes('text-red-600')

            with ui.row().classes('w-full justify-end mt-5'):
                ui.button('Cerrar', on_click=dialog.close).props('flat')

    action_columns = [
        {'name': 'accion', 'label': 'Acción', 'field': 'accion', 'align': 'left'},
        {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
        {'name': 'fecha', 'label': 'Fecha límite', 'field': 'fecha', 'align': 'left'},
        {'name': 'progreso', 'label': 'Progreso', 'field': 'progreso', 'align': 'center'},
        {'name': 'evidencia', 'label': 'Evidencia', 'field': 'evidencia', 'align': 'left'},
        {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
    ]

    with ui.dialog() as dialog, ui.card().classes('w-[1180px] max-w-[97vw] bg-white rounded-[26px] p-0 overflow-hidden'):
        with ui.column().classes('w-full gap-0'):
            with ui.row().classes('w-full items-center justify-between px-6 pt-5'):
                ui.label('Analisis y Resolución de Problemas').classes('text-2xl font-bold text-slate-900')
                with ui.row().classes('items-center gap-2'):
                    top_save_button = ui.button('Guardar 8D', icon='save', color='primary').props('unelevated')
                    ui.label('Usa este bot³n para guardar').classes('text-sm text-slate-500')
                    export_editor_button = ui.button('Reporte 8D (PDF)', icon='picture_as_pdf', color='red-8').props('unelevated')
                    ui.button(icon='close', on_click=dialog.close).props('flat round')

            with ui.row().classes('w-full items-center justify-between px-6 pt-2'):
                ui.label(f'Empresa activa: {company_name}').classes('ideas-section-note')
                ui.badge('8D + Ishikawa + 5 Porques').props('color=primary')

            with ui.tabs().classes('w-full mt-2 px-6') as tabs:
                tab_8d = ui.tab('Reporte 8D', icon='assignment')
                tab_ishi = ui.tab('Ishikawa (6M)', icon='hub')
                tab_5p = ui.tab('5 Porques', icon='account_tree')
                tab_ev = ui.tab('Evidencia General', icon='photo_camera')

            with ui.tab_panels(tabs, value=tab_8d).classes('w-full bg-transparent h-[68vh] overflow-y-auto px-6 pb-4'):
                with ui.tab_panel(tab_8d).classes('p-0'):
                    with ui.column().classes('gap-4 pt-4'):
                        with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                            numero_8d_input = ui.input('N 8D', value=fix_text_fn(current_row.get('numero_8d', ''))).classes('w-full').props('outlined readonly')
                            fecha_input = ui.input('Fecha', value=fix_text_fn(current_row.get('fecha') or datetime.datetime.now().strftime('%d.%m.%Y'))).classes('w-full').props('outlined')
                            titulo_input = ui.input('Titulo del problema', value=fix_text_fn(current_row.get('titulo', ''))).classes('w-full').props('outlined')
                        origen_input = ui.input('Origen', value=fix_text_fn(current_row.get('origen', ''))).classes('w-full').props('outlined')
                        numero_8d_editable_input = ui.input('Codigo / Numero 8D', value=fix_text_fn(current_row.get('numero_8d', ''))).classes('w-full').props('outlined')

                        estado_input = ui.select(
                            ['Abierto', 'En analisis', 'Implementado', 'Cerrado'],
                            value=fix_text_fn(current_row.get('estado', 'Abierto')) or 'Abierto',
                            label='Estado',
                        ).classes('w-full').props('outlined')

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D1 · Equipo multifuncional').classes('text-lg font-bold text-slate-900')
                            ui.label('Carga el equipo con nombre y función. El primer integrante queda marcado como líder del equipo.').classes('ideas-section-note')
                            with ui.grid(columns=3).classes('w-full mt-3').style('grid-template-columns: 1.25fr 1fr auto; gap: 12px;'):
                                d1_name_input = ui.input('Nombre del participante').classes('w-full').props('outlined')
                                d1_role_input = ui.input('Función / área').classes('w-full').props('outlined')
                                add_member_button = ui.button('Agregar integrante', icon='person_add').props('color=primary').classes('self-end')
                            team_table = ui.table(
                                columns=[
                                    {'name': 'tipo', 'label': 'Rol', 'field': 'tipo', 'align': 'center'},
                                    {'name': 'nombre', 'label': 'Nombre', 'field': 'nombre', 'align': 'left'},
                                    {'name': 'funcion', 'label': 'Función', 'field': 'funcion', 'align': 'left'},
                                ],
                                rows=[],
                                pagination={'rowsPerPage': 6},
                            ).classes('w-full ideas-table mt-4')

                            def refresh_team_table() -> None:
                                team_table.rows = [
                                    {
                                        'tipo': 'Líder' if idx == 0 else 'Miembro',
                                        'nombre': fix_text_fn(item.get('nombre', '')),
                                        'funcion': fix_text_fn(item.get('funcion', '')),
                                    }
                                    for idx, item in enumerate(team_members)
                                ]
                                team_table.update()

                            def add_team_member() -> None:
                                nombre = str(d1_name_input.value or '').strip()
                                funcion = str(d1_role_input.value or '').strip()
                                if not nombre:
                                    ui.notify('Necesitas al menos el nombre del participante para agregarlo al equipo.', type='warning')
                                    return
                                team_members.append({'nombre': nombre, 'funcion': funcion})
                                d1_name_input.value = ''
                                d1_role_input.value = ''
                                refresh_team_table()
                                if len(team_members) == 1:
                                    ui.notify('Integrante agregado como líder del equipo.', type='positive')
                                else:
                                    ui.notify('Integrante agregado al equipo multifuncional.', type='positive')

                            add_member_button.on_click(add_team_member)
                            refresh_team_table()

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D2 · Descripción detallada del caso').classes('text-lg font-bold text-slate-900')
                            with ui.column().classes('w-full gap-3 mt-3'):
                                d2_input = ui.textarea('Descripción general', value=fix_text_fn(d2_details.get('descripcion_libre', ''))).props('outlined autogrow').classes('w-full h-24')
                                with ui.grid(columns=2).classes('w-full ideas-grid-2'):
                                    with ui.card().classes('w-full border border-red-200 shadow-none rounded-[18px] p-4 bg-red-50'):
                                        ui.label('Foto pieza NOK').classes('text-sm font-bold text-red-900')
                                        nok_part_preview = ui.column().classes('w-full mt-3')

                                        def refresh_nok_part_preview() -> None:
                                            nok_part_preview.clear()
                                            with nok_part_preview:
                                                if nok_part_image_state['path']:
                                                    ui.image(nok_part_image_state['path']).classes('w-full h-44 object-contain rounded-[12px] bg-white')
                                                    ui.label(Path(nok_part_image_state['path']).name).classes('text-xs text-red-800 mt-2')
                                                    with ui.row().classes('w-full justify-end mt-2'):
                                                        ui.button('Eliminar foto', icon='delete', on_click=lambda: remove_nok_part_image()).props('flat color=negative')
                                                else:
                                                    ui.label('Sin foto NOK cargada.').classes('text-sm text-red-800')

                                        def on_upload_nok_part(event: events.UploadEventArguments) -> None:
                                            try:
                                                nok_part_image_state['path'] = _save_uploaded_file(company_id, event)
                                                refresh_nok_part_preview()
                                                ui.notify(f'Foto NOK cargada: {Path(nok_part_image_state["path"]).name}', type='positive')
                                            except Exception as exc:
                                                ui.notify(f'No se pudo guardar la foto NOK: {exc}', type='negative')

                                        def remove_nok_part_image() -> None:
                                            nok_part_image_state['path'] = ''
                                            refresh_nok_part_preview()
                                            ui.notify('Foto NOK eliminada del 8D.', type='positive')

                                        ui.upload(on_upload=on_upload_nok_part, multiple=False, auto_upload=True, label='Subir foto NOK').props('accept=.png,.jpg,.jpeg').classes('w-full')
                                        refresh_nok_part_preview()

                                    with ui.card().classes('w-full border border-green-200 shadow-none rounded-[18px] p-4 bg-green-50'):
                                        ui.label('Foto pieza OK').classes('text-sm font-bold text-green-900')
                                        ok_part_preview = ui.column().classes('w-full mt-3')

                                        def refresh_ok_part_preview() -> None:
                                            ok_part_preview.clear()
                                            with ok_part_preview:
                                                if ok_part_image_state['path']:
                                                    ui.image(ok_part_image_state['path']).classes('w-full h-44 object-contain rounded-[12px] bg-white')
                                                    ui.label(Path(ok_part_image_state['path']).name).classes('text-xs text-green-800 mt-2')
                                                    with ui.row().classes('w-full justify-end mt-2'):
                                                        ui.button('Eliminar foto', icon='delete', on_click=lambda: remove_ok_part_image()).props('flat color=negative')
                                                else:
                                                    ui.label('Sin foto OK cargada.').classes('text-sm text-green-800')

                                        def on_upload_ok_part(event: events.UploadEventArguments) -> None:
                                            try:
                                                ok_part_image_state['path'] = _save_uploaded_file(company_id, event)
                                                refresh_ok_part_preview()
                                                ui.notify(f'Foto OK cargada: {Path(ok_part_image_state["path"]).name}', type='positive')
                                            except Exception as exc:
                                                ui.notify(f'No se pudo guardar la foto OK: {exc}', type='negative')

                                        def remove_ok_part_image() -> None:
                                            ok_part_image_state['path'] = ''
                                            refresh_ok_part_preview()
                                            ui.notify('Foto OK eliminada del 8D.', type='positive')

                                        ui.upload(on_upload=on_upload_ok_part, multiple=False, auto_upload=True, label='Subir foto OK').props('accept=.png,.jpg,.jpeg').classes('w-full')
                                        refresh_ok_part_preview()
                                with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                                    customer_project_input = ui.input(
                                        'Cliente / Proyecto',
                                        value=fix_text_fn(current_row.get('customer_project') or d2_details.get('cliente', '')),
                                    ).classes('w-full').props('outlined')
                                    fault_type_input = ui.input('Tipo de falla', value=fix_text_fn(current_row.get('fault_type', ''))).classes('w-full').props('outlined')
                                    cliente_input = ui.input('Cliente', value=fix_text_fn(d2_details.get('cliente', ''))).classes('w-full').props('outlined')
                                with ui.row().classes('w-full items-center gap-6'):
                                    safety_relevant_switch = ui.switch(
                                        'Caracteristica relevante de seguridad',
                                        value=_bool_from_any(current_row.get('safety_relevant', 0)),
                                    )
                                    repetitive_fault_switch = ui.switch(
                                        'Falla repetitiva',
                                        value=_bool_from_any(current_row.get('repetitive_fault', 0)),
                                    )
                                with ui.row().classes('w-full items-stretch gap-4'):
                                    nok_part_input = ui.textarea(
                                        'NOK PART (Condición de falla)',
                                        value=fix_text_fn(nok_ok_data.get('nok_part', '')),
                                    ).props('outlined autogrow').classes('w-full h-28 border border-red-200 rounded-[16px] bg-red-50')
                                    ok_part_input = ui.textarea(
                                        'OK PART (Condición esperada)',
                                        value=fix_text_fn(nok_ok_data.get('ok_part', '')),
                                    ).props('outlined autogrow').classes('w-full h-28 border border-green-200 rounded-[16px] bg-green-50')
                                with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                                    piezas_defectos_input = ui.input('Piezas con defectos', value=fix_text_fn(d2_details.get('piezas_defectos', ''))).classes('w-full').props('outlined')
                                    quien_detecto_input = ui.input('Quin detect el problema?', value=fix_text_fn(d2_details.get('quien_detecto', ''))).classes('w-full').props('outlined')
                                    como_detecto_input = ui.input('Cmo lo detect?', value=fix_text_fn(d2_details.get('como_detecto', ''))).classes('w-full').props('outlined')
                                with ui.grid(columns=2).classes('w-full ideas-grid-2'):
                                    cuando_detecto_input = ui.input('Cundo lo detect?', value=fix_text_fn(d2_details.get('cuando_detecto', ''))).classes('w-full').props('outlined')

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D3 · Contención').classes('text-lg font-bold text-slate-900')
                            ui.label('Define las acciones inmediatas para proteger al cliente y contener el problema.').classes('ideas-section-note')
                            d3_input = ui.textarea('Acciones de contención inmediata', value=fix_text_fn(current_row.get('d3_contencion', ''))).props('outlined autogrow').classes('w-full h-24 mt-3')
                            ui.label('Plan de acciones D3').classes('text-sm font-bold text-slate-900 mt-3')
                            d3_actions_host = ui.column().classes('w-full gap-3 mt-2')
                            d3_files_note = ui.label('Sin evidencia adjunta para esta accion.').classes('text-sm text-slate-500')

                            def on_upload_d3(event: events.UploadEventArguments) -> None:
                                try:
                                    path = _save_uploaded_file(company_id, event)
                                    d3_draft_files.append(path)
                                    d3_files_note.text = ', '.join(Path(item).name for item in d3_draft_files)
                                    _refresh_action_editors()
                                    ui.notify(f'Evidencia D3 cargada: {Path(path).name}', type='positive')
                                except Exception as exc:
                                    ui.notify(f'No se pudo guardar la evidencia D3: {exc}', type='negative')

                            d3_upload = ui.upload(on_upload=on_upload_d3, multiple=True, auto_upload=True, label='Subir evidencia de la accion').props('accept=.png,.jpg,.jpeg,.pdf').classes('w-full mt-3')
                            d3_table = ui.table(columns=action_columns, rows=[], pagination={'rowsPerPage': 5}).classes('w-full ideas-table mt-4')
                            sorting_needed_switch = ui.switch('Sorting action necessary?', value=_bool_from_any(d3_data.get('sorting_required', 0))).classes('mt-3')
                            with ui.column().classes('w-full gap-3') as sorting_panel:
                                with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                                    kroschu_sorted_input = ui.number('Sorted · At Kroschu', value=d3_data.get('kroschu_sorted')).classes('w-full').props('outlined')
                                    transit_sorted_input = ui.number('Sorted · On transit', value=d3_data.get('transit_sorted')).classes('w-full').props('outlined')
                                    customer_sorted_input = ui.number('Sorted · At customer', value=d3_data.get('customer_sorted')).classes('w-full').props('outlined')
                                with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                                    kroschu_nok_input = ui.number('nOk · At Kroschu', value=d3_data.get('kroschu_nok')).classes('w-full').props('outlined')
                                    transit_nok_input = ui.number('nOk · On transit', value=d3_data.get('transit_nok')).classes('w-full').props('outlined')
                                    customer_nok_input = ui.number('nOk · At customer', value=d3_data.get('customer_nok')).classes('w-full').props('outlined')
                            employees_informed_switch = ui.switch(
                                'Fueron informados los empleados relevantes?',
                                value=_bool_from_any(d3_data.get('employees_informed', 0)),
                            ).classes('mt-2')
                            sorting_needed_switch._props['label'] = 'Es necesaria una accion de sorting?'
                            kroschu_sorted_input._props['label'] = 'Sorted · En planta'
                            transit_sorted_input._props['label'] = 'Sorted · En transito'
                            customer_sorted_input._props['label'] = 'Sorted · En cliente'
                            kroschu_nok_input._props['label'] = 'nOk · En planta'
                            transit_nok_input._props['label'] = 'nOk · En transito'
                            customer_nok_input._props['label'] = 'nOk · En cliente'
                            employees_informed_switch._props['label'] = 'Fueron informados los empleados relevantes?'

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D4 · Causa raiz').classes('text-lg font-bold text-slate-900')
                            with ui.card().classes('w-full mt-3 bg-slate-50 border border-slate-200 shadow-none rounded-[20px]'):
                                ui.label('Panel de verificacion').classes('text-base font-bold text-slate-900')
                                simulation_possible_switch = ui.switch(
                                    'Es posible la simulacin?',
                                    value=not bool(str(d4_data.get('simulation_not_possible_reason', '')).strip()) if d4_data else _bool_from_any(d4_data.get('simulation_possible', 0)),
                                ).classes('mt-2')
                                simulation_reason_input = ui.input(
                                    'Motivo por el cual la simulacion no es posible',
                                    value=fix_text_fn(d4_data.get('simulation_not_possible_reason', '')),
                                ).classes('w-full mt-3').props('outlined')
                                simulation_match_switch = ui.switch(
                                    'El defecto reproducido coincide con la falla?',
                                    value=_bool_from_any(d4_data.get('match_fault', 0)),
                                ).classes('mt-3')
                            with ui.grid(columns=2).classes('w-full ideas-grid-2 mt-3'):
                                d4_occ_root_input = ui.textarea(
                                    'Causa raiz de Ocurrencia',
                                    value=fix_text_fn(d4_data.get('occ_root') or data_5p.get('occ_causa_raiz', '')),
                                ).props('outlined autogrow').classes('w-full h-24 bg-amber-50')
                                d4_det_root_input = ui.textarea(
                                    'Causa raiz de No detección',
                                    value=fix_text_fn(d4_data.get('det_root') or data_5p.get('det_causa_raiz', '')),
                                ).props('outlined autogrow').classes('w-full h-24 bg-amber-50')
                            d4_status = ui.label('').classes('ideas-section-note')
                            d4_input = ui.textarea('Describe la causa raiz validada', value=fix_text_fn(current_row.get('d4_causa_raiz', ''))).props('outlined autogrow').classes('w-full h-24 mt-3')

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D5 · Acciones correctivas').classes('text-lg font-bold text-slate-900')
                            d5_status = ui.label('').classes('ideas-section-note')
                            with ui.row().classes('w-full items-end gap-4 mt-3'):
                                d5_training_switch = ui.switch(
                                    'Se capacit a los empleados relevantes?',
                                    value=_bool_from_any(d5_training_data.get('trained', 0)),
                                )
                                d5_training_owner_input = ui.input(
                                    'Responsable',
                                    value=fix_text_fn(d5_training_data.get('responsable', '')),
                                ).classes('w-full').props('outlined')
                                d5_training_date_input = ui.input(
                                    'Fecha de entrenamiento',
                                    value=fix_text_fn(d5_training_data.get('fecha', '')),
                                ).classes('w-full').props('outlined')
                            ui.label('Plan de acciones D5').classes('text-sm font-bold text-slate-900 mt-3')
                            d5_actions_host = ui.column().classes('w-full gap-3 mt-2')
                            d5_files_note = ui.label('Sin evidencia adjunta para esta accion.').classes('text-sm text-slate-500')

                            def on_upload_d5(event: events.UploadEventArguments) -> None:
                                try:
                                    path = _save_uploaded_file(company_id, event)
                                    d5_draft_files.append(path)
                                    d5_files_note.text = ', '.join(Path(item).name for item in d5_draft_files)
                                    _refresh_action_editors()
                                    ui.notify(f'Evidencia D5 cargada: {Path(path).name}', type='positive')
                                except Exception as exc:
                                    ui.notify(f'No se pudo guardar la evidencia D5: {exc}', type='negative')

                            d5_upload = ui.upload(on_upload=on_upload_d5, multiple=True, auto_upload=True, label='Subir evidencia de la accion').props('accept=.png,.jpg,.jpeg,.pdf').classes('w-full mt-3')
                            d5_table = ui.table(columns=action_columns, rows=[], pagination={'rowsPerPage': 5}).classes('w-full ideas-table mt-4')

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D6 · Verificación de eficacia').classes('text-lg font-bold text-slate-900')
                            d6_status = ui.label('').classes('ideas-section-note')
                            ui.label('Plan de acciones D6').classes('text-sm font-bold text-slate-900 mt-3')
                            d6_actions_host = ui.column().classes('w-full gap-3 mt-2')
                            d6_files_note = ui.label('Sin evidencia adjunta para esta verificacion.').classes('text-sm text-slate-500')

                            def on_upload_d6(event: events.UploadEventArguments) -> None:
                                try:
                                    path = _save_uploaded_file(company_id, event)
                                    d6_draft_files.append(path)
                                    d6_files_note.text = ', '.join(Path(item).name for item in d6_draft_files)
                                    _refresh_action_editors()
                                    ui.notify(f'Evidencia D6 cargada: {Path(path).name}', type='positive')
                                except Exception as exc:
                                    ui.notify(f'No se pudo guardar la evidencia D6: {exc}', type='negative')

                            d6_upload = ui.upload(on_upload=on_upload_d6, multiple=True, auto_upload=True, label='Subir evidencia de la accion').props('accept=.png,.jpg,.jpeg,.pdf').classes('w-full mt-3')
                            d6_table = ui.table(columns=action_columns, rows=[], pagination={'rowsPerPage': 5}).classes('w-full ideas-table mt-4')
                            for current_table, current_phase in [(d3_table, 'D3'), (d5_table, 'D5'), (d6_table, 'D6')]:
                                current_table.add_slot(
                                    'body-cell-acciones',
                                    '''
                                    <q-td :props="props">
                                        <div class="row items-center no-wrap q-gutter-sm">
                                            <q-btn flat round dense icon="edit" color="primary" @click="$parent.$emit('edit_action', {phase: 'PHASE_TOKEN', id: props.row.id})" />
                                            <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_action', {phase: 'PHASE_TOKEN', id: props.row.id})" />
                                        </div>
                                    </q-td>
                                    '''.replace('PHASE_TOKEN', current_phase),
                                )

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D7 · Prevencion').classes('text-lg font-bold text-slate-900')
                            ui.label('Documentation · Standard updates').classes('ideas-section-note')
                            d7_doc_controls = {}
                            with ui.column().classes('w-full gap-3 mt-3'):
                                for doc_name in ['FMEA', 'Plan de Control', 'Planos', 'Instrucciones de Trabajo', 'Plan de Mantenimiento', 'Procedimiento', 'Tarjeta de Lecciones Aprendidas']:
                                    doc_data = (d7_docs_data.get('documents') or {}).get(doc_name, {})
                                    with ui.card().classes('w-full border border-slate-200 shadow-none rounded-[18px] p-4'):
                                        with ui.grid(columns=4).classes('w-full ideas-grid-2'):
                                            reviewed = ui.checkbox(doc_name, value=_bool_from_any(doc_data.get('checked', 0)))
                                            reviewed_at = ui.input('Se revisó (cuándo)', value=fix_text_fn(doc_data.get('reviewed_at', ''))).classes('w-full').props('outlined')
                                            updated_at = ui.input('Se actualizó (cuándo)', value=fix_text_fn(doc_data.get('updated_at', ''))).classes('w-full').props('outlined')
                                            comments = ui.input('Comentarios', value=fix_text_fn(doc_data.get('comments', ''))).classes('w-full').props('outlined')
                                        d7_doc_controls[doc_name] = {
                                            'checked': reviewed,
                                            'reviewed_at': reviewed_at,
                                            'updated_at': updated_at,
                                            'comments': comments,
                                        }
                            d7_input = ui.textarea(
                                'Implementación de medidas a procesos/productos similares',
                                value=fix_text_fn(current_row.get('d7_prevencion', '')),
                            ).props('outlined autogrow').classes('w-full h-24 mt-3')

                        with ui.card().classes('w-full ideas-panel shadow-none border border-slate-200'):
                            ui.label('D8 · Cierre y reconocimiento').classes('text-lg font-bold text-slate-900')
                            d8_input = ui.textarea('Cierre formal, lecciones aprendidas y reconocimiento del equipo', value=fix_text_fn(current_row.get('d8_cierre', ''))).props('outlined autogrow').classes('w-full h-24 mt-3')
                            with ui.grid(columns=3).classes('w-full ideas-grid-3 mt-3'):
                                closure_inputs = {}
                                for role_key, role_label in [
                                    ('problem_coordinator', 'Coordinador del problema'),
                                    ('responsible_q', 'Responsable de Calidad'),
                                    ('ap_team_leader', 'Lider del equipo AP'),
                                ]:
                                    role_data = d8_closure_data.get(role_key) or {}
                                    with ui.card().classes('w-full border border-slate-200 shadow-none rounded-[18px] p-4'):
                                        ui.label(role_label).classes('text-sm font-bold text-slate-900')
                                        name_input = ui.input('Nombre', value=fix_text_fn(role_data.get('nombre', ''))).classes('w-full mt-3').props('outlined')
                                        date_input = ui.input('Verificado / Informado el', value=fix_text_fn(role_data.get('fecha', ''))).classes('w-full mt-3').props('outlined')
                                        closure_inputs[role_key] = {'nombre': name_input, 'fecha': date_input}

                with ui.tab_panel(tab_ishi).classes('p-0'):
                    with ui.column().classes('gap-4 pt-4'):
                        ui.label('Usa el Ishikawa para depurar causas y retener únicamente los factores que realmente merecen profundización.').classes('text-slate-500')
                        with ui.grid(columns=2).classes('w-full ideas-grid-2'):
                            with ui.card().classes('ideas-panel shadow-none border border-slate-200'):
                                ui.label('Variables del analisis').classes('text-lg font-bold text-slate-900')
                                with ui.grid(columns=2).classes('w-full ideas-grid-2 mt-3'):
                                    mano_obra_input = ui.textarea('Mano de obra', value=fix_text_fn(data_ishikawa.get('mano_obra', ''))).props('outlined autogrow').classes('w-full h-24')
                                    maquina_input = ui.textarea('Máquina', value=fix_text_fn(data_ishikawa.get('maquina', ''))).props('outlined autogrow').classes('w-full h-24')
                                    material_input = ui.textarea('Material', value=fix_text_fn(data_ishikawa.get('material', ''))).props('outlined autogrow').classes('w-full h-24')
                                    metodo_input = ui.textarea('Método', value=fix_text_fn(data_ishikawa.get('metodo', ''))).props('outlined autogrow').classes('w-full h-24')
                                    medicion_input = ui.textarea('Medición', value=fix_text_fn(data_ishikawa.get('medicion', ''))).props('outlined autogrow').classes('w-full h-24')
                                    medio_ambiente_input = ui.textarea('Medio ambiente', value=fix_text_fn(data_ishikawa.get('medio_ambiente', ''))).props('outlined autogrow').classes('w-full h-24')

                            with ui.column().classes('gap-4'):
                                with ui.card().classes('bg-red-50 border border-red-200 rounded-[24px] p-5'):
                                    ui.label('Efecto / Problema Central').classes('text-sm uppercase tracking-[0.16em] text-red-500 font-bold')
                                    effect_input = ui.textarea('Problema / efecto a analizar', value=fix_text_fn(data_ishikawa.get('efecto', current_row.get('titulo', '')))).props('outlined autogrow').classes('w-full h-36 mt-3')

                                with ui.card().classes('ideas-panel shadow-none border border-slate-200'):
                                    ui.label('Factores retenidos validados').classes('text-lg font-bold text-slate-900')
                                    ui.label('Selecciona o escribe los factores que pasaran al analisis de 5 Porques.').classes('ideas-section-note')
                                    if ia_enabled:
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button(
                                                'Sugerencias IA (Brainstorming)',
                                                icon='auto_awesome',
                                                on_click=open_quality_copilot,
                                            ).props('unelevated color=primary')
                                    retained_input = ui.select(
                                        options=initial_retained,
                                        value=initial_retained,
                                        with_input=True,
                                        label='Factores retenidos',
                                        multiple=True,
                                    ).classes('w-full mt-3').props('use-input use-chips multiple new-value-mode=add-unique outlined')
                                    retained_preview = ui.html('')

                with ui.tab_panel(tab_5p).classes('p-0'):
                    with ui.column().classes('gap-4 pt-4'):
                        ui.label('Selecciona el factor retenido a analizar y desarrolla el razonamiento causal en paralelo para ocurrencia y no detección.').classes('text-slate-500')
                        with ui.row().classes('w-full gap-4 items-center'):
                            retained_chip = ui.html('')
                        with ui.grid(columns=2).classes('w-full ideas-grid-2'):
                            occ_factor_select = ui.select(options=initial_retained, value=occ_factor_initial or None, label='Factor retenido a analizar · Ocurrencia').classes('w-full').props('outlined')
                            det_factor_select = ui.select(options=initial_retained, value=det_factor_initial or None, label='Factor retenido a analizar · No detección').classes('w-full').props('outlined')

                        with ui.card().classes('ideas-panel shadow-none border border-slate-200'):
                            with ui.grid(columns='180px 1fr 1fr').classes('w-full gap-3'):
                                ui.label('Nivel').classes('font-bold text-slate-900')
                                ui.label('Ocurrencia').classes('font-bold text-slate-900')
                                ui.label('No detección').classes('font-bold text-slate-900')

                                ui.label('Problema base').classes('text-slate-600 font-semibold')
                                occ_problem_input = ui.input('Problema de ocurrencia', value=fix_text_fn(occ_problem_initial)).classes('w-full').props('outlined')
                                det_problem_input = ui.input('Problema de no detección', value=fix_text_fn(det_problem_initial)).classes('w-full').props('outlined')

                                occ_inputs = []
                                det_inputs = []
                                for index in range(1, 6):
                                    ui.label(f'Por qu {index}?').classes('text-slate-600 font-semibold')
                                    occ_field = ui.input(f'Porque {index} - ocurrencia', value=fix_text_fn(data_5p.get(f'occ_p{index}', ''))).classes('w-full').props('outlined')
                                    det_field = ui.input(f'Porque {index} - no detección', value=fix_text_fn(data_5p.get(f'det_p{index}', ''))).classes('w-full').props('outlined')
                                    occ_inputs.append(occ_field)
                                    det_inputs.append(det_field)

                                ui.label('Causa raiz').classes('text-slate-600 font-semibold')
                                occ_root_input = ui.textarea('Causa raiz de ocurrencia', value=fix_text_fn(data_5p.get('occ_causa_raiz', ''))).props('outlined autogrow').classes('w-full h-24 bg-amber-50')
                                det_root_input = ui.textarea('Causa raiz de no detección', value=fix_text_fn(data_5p.get('det_causa_raiz', ''))).props('outlined autogrow').classes('w-full h-24 bg-amber-50')

                with ui.tab_panel(tab_ev).classes('p-0'):
                    with ui.column().classes('gap-4 pt-4'):
                        preview = ui.column().classes('w-full gap-2')

                        def refresh_files() -> None:
                            preview.clear()
                            with preview:
                                if not uploaded_paths:
                                    ui.label('Sin imágenes cargadas todavía.').classes('text-slate-500')
                                    return
                                with ui.grid(columns=3).classes('w-full ideas-grid-3'):
                                    for path in uploaded_paths:
                                        with ui.card().classes('rounded-[18px] border border-slate-200 p-3 shadow-none'):
                                            ui.image(path).classes('w-full h-32 object-cover rounded-[12px]')
                                            with ui.row().classes('w-full items-center justify-between mt-2'):
                                                ui.label(Path(path).name).classes('text-xs text-slate-600')
                                                ui.button(icon='delete', on_click=lambda current=path: remove_file(current)).props('flat round dense color=negative')

                        def remove_file(path: str) -> None:
                            if path in uploaded_paths:
                                uploaded_paths.remove(path)
                            refresh_files()

                        def on_upload(event: events.UploadEventArguments) -> None:
                            try:
                                path = _save_uploaded_file(company_id, event)
                                uploaded_paths.append(path)
                                refresh_files()
                                ui.notify(f'Archivo cargado: {Path(path).name}', type='positive')
                            except Exception as exc:
                                ui.notify(f'No se pudo guardar el archivo: {exc}', type='negative')

                        ui.upload(on_upload=on_upload, multiple=True, auto_upload=True, label='Subir evidencia general del caso').props('accept=.png,.jpg,.jpeg,.pdf').classes('w-full')
                        refresh_files()

            def refresh_retained_options() -> None:
                factor_pool = []
                factor_pool.extend(_parse_factor_lines('Mano de obra', getattr(mano_obra_input, 'value', '')))
                factor_pool.extend(_parse_factor_lines('Máquina', getattr(maquina_input, 'value', '')))
                factor_pool.extend(_parse_factor_lines('Material', getattr(material_input, 'value', '')))
                factor_pool.extend(_parse_factor_lines('Método', getattr(metodo_input, 'value', '')))
                factor_pool.extend(_parse_factor_lines('Medición', getattr(medicion_input, 'value', '')))
                factor_pool.extend(_parse_factor_lines('Medio ambiente', getattr(medio_ambiente_input, 'value', '')))
                options = []
                for item in factor_pool + retained_state['values']:
                    clean = str(item or '').strip()
                    if clean and clean not in options:
                        options.append(clean)
                retained_input.options = options
                occ_factor_select.options = options
                det_factor_select.options = options
                retained_input.update()
                occ_factor_select.update()
                det_factor_select.update()

            def sync_retained_visuals() -> None:
                retained_state['values'] = [str(item).strip() for item in list(retained_input.value or []) if str(item).strip()]
                summary_text = ', '.join(retained_state['values']) if retained_state['values'] else 'Sin factores retenidos aun.'
                retained_preview.content = (
                    '<div class="ideas-mini-list">'
                    + ''.join(
                        f'<div class="item"><div class="dot"></div><div>{fix_text_fn(item)}</div></div>'
                        for item in retained_state['values']
                    )
                    + '</div>'
                    if retained_state['values']
                    else '<div class="ideas-section-note">Todavia no seleccionaste factores retenidos.</div>'
                )
                retained_chip.content = (
                    '<div class="ideas-quick-card">'
                    '<div class="label">FACTORES RETENIDOS</div>'
                    f'<div class="detail">{summary_text}</div>'
                    '</div>'
                )
                refresh_retained_options()

            def refresh_action_tables() -> None:
                rows_d3 = obtener_acciones_fn(int(problema_state['id']), 'D3') if problema_state['id'] else []
                rows_d5 = obtener_acciones_fn(int(problema_state['id']), 'D5') if problema_state['id'] else []
                rows_d6 = obtener_acciones_fn(int(problema_state['id']), 'D6') if problema_state['id'] else []
                action_state['D3'] = _safe_action_rows(rows_d3 or [])
                action_state['D5'] = _safe_action_rows(rows_d5 or [])
                action_state['D6'] = _safe_action_rows(rows_d6 or [])
                d3_action_rows.clear()
                d3_action_rows.extend(action_state['D3'])
                d5_action_rows.clear()
                d5_action_rows.extend(action_state['D5'])
                d6_action_rows.clear()
                d6_action_rows.extend(action_state['D6'])
                d3_table.rows = _action_rows_for_table(rows_d3 or [], fix_text_fn)
                d5_table.rows = _action_rows_for_table(rows_d5 or [], fix_text_fn)
                d6_table.rows = _action_rows_for_table(rows_d6 or [], fix_text_fn)
                d3_table.update()
                d5_table.update()
                d6_table.update()
                _refresh_action_editors()

            def update_progressive_states() -> None:
                d3_ready = bool(str(d3_input.value or '').strip())
                d4_ready = bool(str(d4_input.value or '').strip()) or bool(str(d4_occ_root_input.value or '').strip()) or bool(str(d4_det_root_input.value or '').strip())
                d4_status.text = 'Completa D3 para habilitar el analisis de causa raiz.' if not d3_ready else 'D4 ya esta habilitado para profundizar la causa raiz.'
                d5_status.text = 'Completa D4 para habilitar la carga de acciones correctivas.' if not d4_ready else 'D5 habilitado para gestionar acciones correctivas.'
                d6_status.text = 'Completa D4 para habilitar la verificacion de eficacia.' if not d4_ready else 'D6 habilitado para gestionar verificaciones.'
                for control in [d4_input]:
                    control.enabled = d3_ready
                    control.update()
                for control in [d5_upload, d6_upload]:
                    control.enabled = d4_ready
                    control.update()
                d3_upload.enabled = d3_ready
                d3_upload.update()
                d3_table.visible = bool(d3_action_rows)
                d3_table.update()

            d3_action_rows: list[dict] = []
            d5_action_rows: list[dict] = []
            d6_action_rows: list[dict] = []
            action_form_state = {
                'D3': {'accion': '', 'responsable': '', 'fecha': '', 'progreso': '0%'},
                'D5': {'accion': '', 'responsable': '', 'fecha': '', 'progreso': '0%'},
                'D6': {'accion': '', 'responsable': '', 'fecha': '', 'progreso': '0%'},
            }
            action_edit_state = {'D3': None, 'D5': None, 'D6': None}

            def _draft_files_for_phase(phase: str) -> list[str]:
                if phase == 'D3':
                    return d3_draft_files
                if phase == 'D5':
                    return d5_draft_files
                return d6_draft_files

            def _draft_note_for_phase(phase: str):
                if phase == 'D3':
                    return d3_files_note
                if phase == 'D5':
                    return d5_files_note
                return d6_files_note

            def _default_note_for_phase(phase: str) -> str:
                if phase == 'D3':
                    return 'Sin evidencia adjunta para esta accion.'
                if phase == 'D5':
                    return 'Sin evidencia adjunta para esta accion.'
                return 'Sin evidencia adjunta para esta verificacion.'

            def _refresh_draft_files_note(phase: str) -> None:
                files = _draft_files_for_phase(phase)
                note = _draft_note_for_phase(phase)
                note.text = ', '.join(Path(item).name for item in files) if files else _default_note_for_phase(phase)
                note.update()

            def _remove_draft_file(phase: str, current_path: str) -> None:
                files = _draft_files_for_phase(phase)
                if current_path in files:
                    files.remove(current_path)
                _refresh_draft_files_note(phase)
                _refresh_action_editors()

            def _build_action_editor(host, target_rows: list[dict], phase: str, title_prefix: str) -> None:
                host.clear()
                with host:
                    form_state = action_form_state[phase]
                    with ui.card().classes('w-full border border-slate-200 shadow-none rounded-[18px] p-4'):
                        ui.label(title_prefix).classes('text-sm font-bold text-slate-900')
                        with ui.grid(columns=4).classes('w-full ideas-grid-2 mt-3'):
                            action_input = ui.input('Acción requerida', value=fix_text_fn(form_state.get('accion', ''))).classes('w-full').props('outlined')
                            owner_input = ui.input('Responsable', value=fix_text_fn(form_state.get('responsable', ''))).classes('w-full').props('outlined')
                            date_input = ui.input('Fecha', value=fix_text_fn(form_state.get('fecha', ''))).classes('w-full').props('outlined')
                            progress_input = ui.select(['0%', '25%', '50%', '75%', '100%'], value=fix_text_fn(form_state.get('progreso', '0%')) or '0%', label='Progreso').classes('w-full').props('outlined')

                        def sync_form(_event=None) -> None:
                            action_form_state[phase] = {
                                'accion': action_input.value or '',
                                'responsable': owner_input.value or '',
                                'fecha': date_input.value or '',
                                'progreso': progress_input.value or '0%',
                            }

                        action_input.on_value_change(sync_form)
                        owner_input.on_value_change(sync_form)
                        date_input.on_value_change(sync_form)
                        progress_input.on_value_change(sync_form)
                        draft_files = _draft_files_for_phase(phase)
                        if draft_files:
                            with ui.column().classes('w-full gap-2 mt-3'):
                                ui.label('Evidencia adjunta a esta accion').classes('text-sm font-semibold text-slate-700')
                                for current_path in draft_files:
                                    with ui.row().classes('w-full items-center justify-between rounded-[12px] border border-slate-200 bg-slate-50 px-3 py-2'):
                                        ui.label(Path(current_path).name).classes('text-sm text-slate-700')
                                        ui.button(icon='delete', on_click=lambda _, current_phase=phase, item=current_path: _remove_draft_file(current_phase, item)).props('flat round dense color=negative')
                        with ui.row().classes('w-full justify-end gap-2 mt-3'):
                            if action_edit_state[phase]:
                                ui.button('Cancelar edición', on_click=lambda current_phase=phase: cancel_action_edit(current_phase)).props('flat')
                            ui.button('Agregar' if not action_edit_state[phase] else 'Guardar cambios', icon='add_task', on_click=lambda current_phase=phase: save_action_form(current_phase)).props('color=primary')

            def cancel_action_edit(phase: str) -> None:
                action_edit_state[phase] = None
                action_form_state[phase] = {'accion': '', 'responsable': '', 'fecha': '', 'progreso': '0%'}
                _draft_files_for_phase(phase).clear()
                _refresh_draft_files_note(phase)
                _refresh_action_editors()

            def save_action_form(phase: str) -> None:
                if phase in {'D5', 'D6'} and not str(d4_input.value or '').strip():
                    ui.notify('Primero define la causa raiz en D4 para habilitar acciones.', type='warning')
                    return
                payload = action_form_state[phase]
                if not str(payload.get('accion') or '').strip():
                    ui.notify('Completa la accion antes de agregarla.', type='warning')
                    return
                problema_id = ensure_problem_saved()
                if not problema_id:
                    return
                evidence = ','.join(_draft_files_for_phase(phase))
                editing_id = action_edit_state[phase]
                if editing_id:
                    eliminar_accion_fn(int(editing_id))
                ok, message, _accion_id = guardar_accion_fn(
                    problema_id,
                    phase,
                    payload.get('accion') or '',
                    payload.get('responsable') or '',
                    payload.get('fecha') or '',
                    payload.get('progreso') or '0%',
                    evidence,
                )
                if not ok:
                    ui.notify(fix_text_fn(message), type='negative')
                    return
                action_edit_state[phase] = None
                action_form_state[phase] = {'accion': '', 'responsable': '', 'fecha': '', 'progreso': '0%'}
                _draft_files_for_phase(phase).clear()
                _refresh_draft_files_note(phase)
                refresh_action_tables()
                ui.notify(f'Acción {phase} guardada correctamente.', type='positive')

            def start_action_edit(phase: str, action_id: int) -> None:
                if not problema_state['id']:
                    return
                rows = obtener_acciones_fn(int(problema_state['id']), phase) or []
                current = next((row for row in rows if int(row.get('id') or 0) == int(action_id)), None)
                if not current:
                    ui.notify('La accion ya no existe.', type='warning')
                    return
                action_edit_state[phase] = int(action_id)
                action_form_state[phase] = {
                    'accion': str(current.get('accion') or ''),
                    'responsable': str(current.get('responsable') or ''),
                    'fecha': str(current.get('fecha') or ''),
                    'progreso': str(current.get('progreso') or '0%') or '0%',
                }
                _draft_files_for_phase(phase).clear()
                evidencia_actual = [item.strip() for item in str(current.get('evidencia_path') or '').split(',') if item.strip()]
                _draft_files_for_phase(phase).extend(evidencia_actual)
                _refresh_draft_files_note(phase)
                _refresh_action_editors()

            def delete_action(phase: str, action_id: int) -> None:
                eliminar_accion_fn(int(action_id))
                if action_edit_state[phase] == int(action_id):
                    cancel_action_edit(phase)
                refresh_action_tables()
                ui.notify(f'Acción {phase} eliminada.', type='positive')

            def _refresh_action_editors() -> None:
                _build_action_editor(d3_actions_host, d3_action_rows, 'D3', 'Acción D3')
                _build_action_editor(d5_actions_host, d5_action_rows, 'D5', 'Acción D5')
                _build_action_editor(d6_actions_host, d6_action_rows, 'D6', 'Acción D6')

            def compose_d2() -> str:
                return _compose_d2_description(
                    d2_input.value or '',
                    cliente_input.value or '',
                    piezas_defectos_input.value or '',
                    quien_detecto_input.value or '',
                    como_detecto_input.value or '',
                    cuando_detecto_input.value or '',
                )

            def compose_nok_ok_details() -> str:
                return json.dumps(
                    {
                        'nok_part': nok_part_input.value or '',
                        'ok_part': ok_part_input.value or '',
                        'nok_part_image': nok_part_image_state['path'],
                        'ok_part_image': ok_part_image_state['path'],
                    },
                    ensure_ascii=False,
                )

            def compose_d3_sorting_details() -> str:
                return json.dumps(
                    {
                        'sorting_required': bool(sorting_needed_switch.value),
                        'employees_informed': bool(employees_informed_switch.value),
                        'kroschu_sorted': kroschu_sorted_input.value,
                        'transit_sorted': transit_sorted_input.value,
                        'customer_sorted': customer_sorted_input.value,
                        'kroschu_nok': kroschu_nok_input.value,
                        'transit_nok': transit_nok_input.value,
                        'customer_nok': customer_nok_input.value,
                        'acciones': [row for row in d3_action_rows if str(row.get('accion') or '').strip()],
                    },
                    ensure_ascii=False,
                )

            def compose_d4_simulation_details() -> str:
                simulation_possible = bool(simulation_possible_switch.value)
                return json.dumps(
                    {
                        'simulation_possible': simulation_possible,
                        'simulation_not_possible_reason': '' if simulation_possible else (simulation_reason_input.value or ''),
                        'match_fault': bool(simulation_match_switch.value) if simulation_possible else False,
                        'occ_root': d4_occ_root_input.value or '',
                        'det_root': d4_det_root_input.value or '',
                    },
                    ensure_ascii=False,
                )

            def compose_d5_training_details() -> str:
                return json.dumps(
                    {
                        'trained': bool(d5_training_switch.value),
                        'responsable': d5_training_owner_input.value or '',
                        'fecha': d5_training_date_input.value or '',
                    },
                    ensure_ascii=False,
                )

            def compose_d7_docs_update() -> str:
                return json.dumps(
                    {
                        'documents': {
                            label: {
                                'checked': bool(controls['checked'].value),
                                'reviewed_at': controls['reviewed_at'].value or '',
                                'updated_at': controls['updated_at'].value or '',
                                'comments': controls['comments'].value or '',
                            }
                            for label, controls in d7_doc_controls.items()
                        },
                    },
                    ensure_ascii=False,
                )

            def compose_d8_closure_details() -> str:
                return json.dumps(
                    {
                        role_key: {
                            'nombre': controls['nombre'].value or '',
                            'fecha': controls['fecha'].value or '',
                        }
                        for role_key, controls in closure_inputs.items()
                    },
                    ensure_ascii=False,
                )

            def update_sorting_panel() -> None:
                sorting_panel.visible = bool(sorting_needed_switch.value)
                sorting_panel.update()

            def update_simulation_panel() -> None:
                simulation_possible = bool(simulation_possible_switch.value)
                simulation_reason_input.visible = not simulation_possible
                simulation_match_switch.visible = simulation_possible
                simulation_reason_input.update()
                simulation_match_switch.update()

            def sync_d4_root_from_5p() -> None:
                d4_occ_root_input.value = occ_root_input.value or ''
                d4_det_root_input.value = det_root_input.value or ''
                joined = ' | '.join(
                    part for part in [
                        f'Ocurrencia: {str(d4_occ_root_input.value or "").strip()}' if str(d4_occ_root_input.value or '').strip() else '',
                        f'No detección: {str(d4_det_root_input.value or "").strip()}' if str(d4_det_root_input.value or '').strip() else '',
                    ]
                    if part
                )
                if joined:
                    d4_input.value = joined
                d4_occ_root_input.update()
                d4_det_root_input.update()
                d4_input.update()
                update_progressive_states()

            def sync_actions_to_db(problema_id: int, fase: str, rows: list[dict], evidence_path: str = '') -> None:
                existentes = _safe_action_rows(obtener_acciones_fn(problema_id, fase) or [])
                existing_keys = {
                    (
                        item.get('accion', ''),
                        item.get('responsable', ''),
                        item.get('fecha', ''),
                        item.get('progreso', ''),
                    )
                    for item in existentes
                }
                for index, row in enumerate(rows):
                    accion = str(row.get('accion') or '').strip()
                    if not accion:
                        continue
                    key = (
                        accion,
                        str(row.get('responsable') or '').strip(),
                        str(row.get('fecha') or '').strip(),
                        str(row.get('progreso') or '0%').strip() or '0%',
                    )
                    if key in existing_keys:
                        continue
                    evidencia = evidence_path if evidence_path and fase in {'D5', 'D6'} and index == len(rows) - 1 else ''
                    ok, message, _accion_id = guardar_accion_fn(
                        problema_id,
                        fase,
                        key[0],
                        key[1],
                        key[2],
                        key[3],
                        evidencia,
                    )
                    if not ok:
                        raise RuntimeError(message)
                    existing_keys.add(key)

            def ensure_problem_saved() -> int | None:
                team_payload = _compose_team_members(team_members)
                d5_summary = _build_action_summary([row for row in d5_action_rows if str(row.get('accion') or '').strip()])
                d6_summary = _build_action_summary([row for row in d6_action_rows if str(row.get('accion') or '').strip()])
                if problema_state['id']:
                    ok, message = actualizar_problema_fn(
                        int(problema_state['id']),
                        fecha_input.value or '',
                        titulo_input.value or '',
                        numero_8d_editable_input.value or numero_8d_input.value or '',
                        origen_input.value or '',
                        team_payload,
                        compose_d2(),
                        d3_input.value or '',
                        d4_input.value or '',
                        d5_summary,
                        d6_summary,
                        d7_input.value or '',
                        d8_input.value or '',
                        customer_project_input.value or '',
                        fault_type_input.value or '',
                        safety_relevant_switch.value,
                        repetitive_fault_switch.value,
                        compose_nok_ok_details(),
                        compose_d3_sorting_details(),
                        compose_d4_simulation_details(),
                        compose_d5_training_details(),
                        compose_d7_docs_update(),
                        compose_d8_closure_details(),
                        estado_input.value or 'Abierto',
                        ','.join(uploaded_paths),
                    )
                    if not ok:
                        ui.notify(fix_text_fn(message), type='negative')
                        return None
                    return int(problema_state['id'])

                ok, message, problema_id = crear_problema_fn(
                    int(company_id),
                    fecha_input.value or '',
                    titulo_input.value or '',
                    numero_8d_editable_input.value or numero_8d_input.value or '',
                    origen_input.value or '',
                    team_payload,
                    compose_d2(),
                    d3_input.value or '',
                    d4_input.value or '',
                    d5_summary,
                    d6_summary,
                    d7_input.value or '',
                    d8_input.value or '',
                    customer_project_input.value or '',
                    fault_type_input.value or '',
                    safety_relevant_switch.value,
                    repetitive_fault_switch.value,
                    compose_nok_ok_details(),
                    compose_d3_sorting_details(),
                    compose_d4_simulation_details(),
                    compose_d5_training_details(),
                    compose_d7_docs_update(),
                    compose_d8_closure_details(),
                    estado_input.value or 'Abierto',
                    ','.join(uploaded_paths),
                )
                if not ok or not problema_id:
                    ui.notify(fix_text_fn(message), type='negative')
                    return None
                problema_state['id'] = int(problema_id)
                return int(problema_id)

            d3_input.on_value_change(lambda _e: update_progressive_states())
            d4_input.on_value_change(lambda _e: update_progressive_states())
            occ_root_input.on_value_change(lambda _e: sync_d4_root_from_5p())
            det_root_input.on_value_change(lambda _e: sync_d4_root_from_5p())
            d4_occ_root_input.on_value_change(lambda _e: update_progressive_states())
            d4_det_root_input.on_value_change(lambda _e: update_progressive_states())
            sorting_needed_switch.on_value_change(lambda _e: update_sorting_panel())
            simulation_possible_switch.on_value_change(lambda _e: update_simulation_panel())
            for source in [mano_obra_input, maquina_input, material_input, metodo_input, medicion_input, medio_ambiente_input]:
                source.on_value_change(lambda _e: refresh_retained_options())
            retained_input.on_value_change(lambda _e: sync_retained_visuals())

            refresh_retained_options()
            sync_retained_visuals()
            update_sorting_panel()
            update_simulation_panel()
            refresh_action_tables()
            sync_d4_root_from_5p()
            update_progressive_states()
            for current_table in [d3_table, d5_table, d6_table]:
                current_table.on('edit_action', lambda event: start_action_edit(str((event.args or {}).get('phase') or ''), int((event.args or {}).get('id') or 0)) if (event.args or {}).get('id') else None)
                current_table.on('delete_action', lambda event: delete_action(str((event.args or {}).get('phase') or ''), int((event.args or {}).get('id') or 0)) if (event.args or {}).get('id') else None)

            def save_all() -> None:
                try:
                    problema_id = ensure_problem_saved()
                    if not problema_id:
                        return

                    ok_5p, msg_5p = guardar_5p_fn(
                        problema_id,
                        problema_inicial='',
                        porque_1='',
                        porque_2='',
                        porque_3='',
                        porque_4='',
                        porque_5='',
                        causa_raiz_confirmada='',
                        ocurrencia_1='',
                        ocurrencia_2='',
                        ocurrencia_3='',
                        ocurrencia_4='',
                        ocurrencia_5='',
                        causa_ocurrencia='',
                        no_deteccion_1='',
                        no_deteccion_2='',
                        no_deteccion_3='',
                        no_deteccion_4='',
                        no_deteccion_5='',
                        causa_no_deteccion='',
                        occ_problema=_merge_factor_problem(occ_factor_select.value or '', occ_problem_input.value or ''),
                        occ_p1=occ_inputs[0].value or '',
                        occ_p2=occ_inputs[1].value or '',
                        occ_p3=occ_inputs[2].value or '',
                        occ_p4=occ_inputs[3].value or '',
                        occ_p5=occ_inputs[4].value or '',
                        occ_causa_raiz=occ_root_input.value or '',
                        det_problema=_merge_factor_problem(det_factor_select.value or '', det_problem_input.value or ''),
                        det_p1=det_inputs[0].value or '',
                        det_p2=det_inputs[1].value or '',
                        det_p3=det_inputs[2].value or '',
                        det_p4=det_inputs[3].value or '',
                        det_p5=det_inputs[4].value or '',
                        det_causa_raiz=det_root_input.value or '',
                    )
                    if not ok_5p:
                        ui.notify(fix_text_fn(msg_5p), type='negative')
                        return

                    ok_ish, msg_ish = guardar_ishikawa_fn(
                        problema_id,
                        effect_input.value or '',
                        mano_obra_input.value or '',
                        maquina_input.value or '',
                        material_input.value or '',
                        metodo_input.value or '',
                        medicion_input.value or '',
                        medio_ambiente_input.value or '',
                        _list_to_csv(retained_state['values']),
                    )
                    if not ok_ish:
                        ui.notify(fix_text_fn(msg_ish), type='negative')
                        return

                    d5_files_note.text = 'Sin evidencia adjunta para esta accion.'
                    d6_files_note.text = 'Sin evidencia adjunta para esta verificacion.'
                    ensure_problem_saved()
                    refresh_action_tables()
                    ui.notify('Analisis de calidad guardado correctamente.', type='positive')
                    dialog.close()
                    ui.navigate.to('/sistema-gestion/calidad')
                except Exception as exc:
                    ui.notify(f'No se pudo guardar el analisis: {exc}', type='negative')

            def export_editor_pdf() -> None:
                if not generar_pdf_8d_fn:
                    ui.notify('Generacion de PDF no disponible.', type='warning')
                    return
                try:
                    problema_id = ensure_problem_saved()
                    if not problema_id:
                        return
                    acciones_d5_d6 = (obtener_acciones_fn(problema_id, 'D5') or []) + (obtener_acciones_fn(problema_id, 'D6') or [])
                    problema_data = {
                        'empresa': company_name,
                        'razon_social': company_info.get('razon_social') or company_name,
                        'logo_path': company_info.get('logo_path') or '',
                        'color_primario': company_info.get('color_primario') or '',
                        'color_secundario': company_info.get('color_secundario') or '',
                        'fecha': fecha_input.value or '',
                        'titulo': titulo_input.value or '',
                        'numero_8d': numero_8d_editable_input.value or numero_8d_input.value or '',
                        'origen': origen_input.value or '',
                        'estado': estado_input.value or 'Abierto',
                        'd1_equipo': _compose_team_members(team_members),
                        'd2_descripcion': compose_d2(),
                        'd3_contencion': d3_input.value or '',
                        'd4_causa_raiz': d4_input.value or '',
                        'd7_prevencion': d7_input.value or '',
                        'd8_cierre': d8_input.value or '',
                        'customer_project': customer_project_input.value or '',
                        'fault_type': fault_type_input.value or '',
                        'safety_relevant': bool(safety_relevant_switch.value),
                        'repetitive_fault': bool(repetitive_fault_switch.value),
                        'nok_ok_details': compose_nok_ok_details(),
                        'd3_sorting_details': compose_d3_sorting_details(),
                        'd4_simulation_details': compose_d4_simulation_details(),
                        'd5_training_details': compose_d5_training_details(),
                        'd7_docs_update': compose_d7_docs_update(),
                        'd8_closure_details': compose_d8_closure_details(),
                        'efecto': effect_input.value or '',
                        'mano_obra': mano_obra_input.value or '',
                        'maquina': maquina_input.value or '',
                        'material': material_input.value or '',
                        'metodo': metodo_input.value or '',
                        'medicion': medicion_input.value or '',
                        'medio_ambiente': medio_ambiente_input.value or '',
                        'factores_retenidos': _list_to_csv(retained_state['values']),
                    }
                    acciones_d3 = obtener_acciones_fn(problema_id, 'D3') or []
                    pdf_path = generar_pdf_8d_fn(problema_data, acciones_d3 + acciones_d5_d6)
                    ui.download(str(pdf_path))
                except Exception as exc:
                    ui.notify(f'No se pudo generar el reporte 8D: {exc}', type='negative')

            export_editor_button.on_click(export_editor_pdf)
            top_save_button.on_click(save_all)

            ui.separator()
            with ui.row().classes('w-full justify-end items-center px-6 py-4 gap-2'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar Analisis Completo', icon='save', on_click=save_all).props('color=primary')

    dialog.open()


def register_quality_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    company_options = deps['company_options']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    valor_afirmativo = deps['valor_afirmativo']
    fix_text = deps['fix_text']
    obtener_problemas_calidad_empresa = deps['obtener_problemas_calidad_empresa']
    obtener_problema_calidad_detalle = deps['obtener_problema_calidad_detalle']
    crear_problema_calidad_8d = deps['crear_problema_calidad_8d']
    actualizar_problema_calidad_8d = deps['actualizar_problema_calidad_8d']
    eliminar_problema_calidad_8d = deps['eliminar_problema_calidad_8d']
    obtener_5_porque_problema_calidad = deps['obtener_5_porque_problema_calidad']
    guardar_5_porque_problema_calidad = deps['guardar_5_porque_problema_calidad']
    obtener_ishikawa_problema_calidad = deps['obtener_ishikawa_problema_calidad']
    guardar_ishikawa_problema_calidad = deps['guardar_ishikawa_problema_calidad']
    obtener_acciones_8d = deps['obtener_acciones_8d']
    guardar_accion_8d = deps['guardar_accion_8d']
    eliminar_accion_8d = deps['eliminar_accion_8d']
    generar_reporte_8d = deps['generar_reporte_8d']
    generar_pdf_8d = deps.get('generar_pdf_8d')
    obtener_fuentes_empresa = deps['obtener_fuentes_empresa']
    sugerir_causas_ishikawa = deps['sugerir_causas_ishikawa']
    quality_structure = [
        {
            'key': 'gestion_clientes',
            'label': 'Gestion de Clientes',
            'icon': 'support_agent',
            'items': [
                {'label': 'Acceso a portales', 'icon': 'language', 'target': None},
                {'label': 'Satisfaccion', 'icon': 'sentiment_satisfied', 'target': None},
                {'label': 'Reclamos', 'icon': 'report_problem', 'target': None},
                {'label': 'Plan de accion', 'icon': 'assignment_turned_in', 'target': None},
            ],
        },
        {
            'key': 'auditorias',
            'label': 'Auditorias',
            'icon': 'fact_check',
            'items': [
                {'label': 'Auditorias de procesos', 'icon': 'rule', 'target': None},
                {'label': 'Auditorias de sistema interna', 'icon': 'verified_user', 'target': None},
                {'label': 'Auditorias de sistema externa', 'icon': 'travel_explore', 'target': None},
                {'label': 'Auditorias de producto', 'icon': 'inventory_2', 'target': None},
                {'label': 'Plan de accion', 'icon': 'assignment_turned_in', 'target': None},
            ],
        },
        {
            'key': 'plan_accion_general',
            'label': 'Plan de Accion General',
            'icon': 'playlist_add_check_circle',
            'items': [
                {'label': 'Prevencion de emergencias', 'icon': 'health_and_safety', 'target': None},
                {'label': 'Simulacros', 'icon': 'local_fire_department', 'target': None},
                {'label': 'Registro de emergencias', 'icon': 'edit_note', 'target': None},
                {'label': 'Documentos', 'icon': 'description', 'target': None},
            ],
        },
        {
            'key': 'msa',
            'label': 'MSA',
            'icon': 'straighten',
            'items': [
                {'label': 'Calibracion de instrumentos', 'icon': 'tune', 'target': None},
                {'label': 'Listado de instrumentos', 'icon': 'view_list', 'target': None},
            ],
        },
        {
            'key': 'gestion_proveedores',
            'label': 'Gestion de Proveedores',
            'icon': 'handshake',
            'items': [
                {'label': 'Reclamos', 'icon': 'warning_amber', 'target': None},
                {'label': 'Analisis de problemas de proveedores', 'icon': 'manage_search', 'target': None},
                {'label': 'Plan de accion', 'icon': 'assignment_turned_in', 'target': None},
            ],
        },
        {
            'key': 'analisis_problemas',
            'label': 'Analisis de Problemas',
            'icon': 'manage_search',
            'items': [
                {'label': 'Gestion de 8D', 'icon': 'schema', 'target': '8d'},
                {'label': 'Plan de accion', 'icon': 'assignment_turned_in', 'target': None},
            ],
        },
    ]

    @ui.page('/sistema-gestion/calidad')
    def quality_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Gestion de calidad', back_route='/sistema-gestion')
        company_map = company_options()
        selected_company_id = app.storage.user.get('management_company_id') or current_selection()[0]
        try:
            selected_company_id = int(selected_company_id) if selected_company_id else None
        except Exception:
            selected_company_id = None
        if not selected_company_id and company_map:
            selected_company_id = next(iter(company_map.keys()))
            app.storage.user['management_company_id'] = selected_company_id
            set_selection(selected_company_id, None)

        with shell_container:
            ui.label('GESTION DE CALIDAD').classes('ideas-kicker')
            ui.label('Modulo de Gestion de Calidad').classes('text-3xl font-bold text-slate-900')
            ui.label('Centraliza subprocesos, estandares y herramientas de calidad en un unico frente operativo.').classes('ideas-subtitle mb-3')

            if not company_map:
                ui.label('Primero necesitas registrar una empresa para habilitar este modulo.').classes('text-slate-500')
                return

            if str(app.storage.user.get('role') or '') == 'admin':
                company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                company_select.on_value_change(
                    lambda _e: (
                        app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                        set_selection(int(company_select.value), None) if company_select.value else None,
                        ui.navigate.to('/sistema-gestion/calidad'),
                    )
                )

            if not selected_company_id:
                return

            selected_process_key = str(app.storage.user.get('quality_process_key') or 'gestion_clientes')
            process_by_key = {item['key']: item for item in quality_structure}
            if selected_process_key not in process_by_key:
                selected_process_key = 'gestion_clientes'
            selected_process = process_by_key[selected_process_key]

            selected_target = str(app.storage.user.get('quality_submodule_target') or '')

            def _open_submodule(target: str | None, process_key: str) -> None:
                app.storage.user['quality_process_key'] = process_key
                app.storage.user['quality_submodule_target'] = str(target or '')
                if target == '8d':
                    ui.notify('Submodulo seleccionado.', type='info')
                    ui.navigate.to('/sistema-gestion/calidad')
                    return
                ui.notify('Submodulo en preparacion.', type='warning')

            panel_tab_map = {}
            with ui.tabs().classes('w-full mt-4 ideas-panel p-2 rounded-[24px]') as panel_tabs:
                for block in quality_structure:
                    panel_tab_map[block['key']] = ui.tab(block['label'], icon=block['icon']).props('no-caps')

            with ui.tab_panels(panel_tabs, value=panel_tab_map[selected_process_key]).classes('w-full bg-transparent'):
                for block in quality_structure:
                    with ui.tab_panel(panel_tab_map[block['key']]).classes('px-0'):
                        with ui.card().classes('ideas-panel w-full mt-4'):
                            ui.label(block['label']).classes('ideas-section-title')
                            ui.label('Submodulos del subproceso seleccionado.').classes('ideas-section-note')
                            with ui.grid(columns=2).classes('w-full gap-3 mt-3'):
                                for item in block.get('items', []):
                                    with ui.card().classes('ideas-module-card cursor-pointer').on(
                                        'click',
                                        lambda _e, t=item.get('target'), p_key=block['key']: _open_submodule(t, p_key),
                                    ):
                                        with ui.row().classes('items-center gap-2'):
                                            ui.icon(str(item.get('icon') or 'widgets')).classes('text-slate-600')
                                            ui.label(str(item.get('label') or '')).classes('font-semibold text-slate-900')
                                        ui.label('Abrir modulo').classes('text-sm text-slate-500')

            if selected_target != '8d':
                return

            empresa = obtener_empresa_detalle(int(selected_company_id)) or {}
            ia_activa = valor_afirmativo(empresa.get('agente_ia_activo'))
            company_name = fix_text(empresa.get('razon_social', company_map.get(selected_company_id, '')))
            problemas = obtener_problemas_calidad_empresa(int(selected_company_id))

            prepared_rows = []
            for item in problemas:
                detail_5p = obtener_5_porque_problema_calidad(int(item['id'])) or {}
                detail_ish = obtener_ishikawa_problema_calidad(int(item['id'])) or {}
                prepared = dict(item)
                prepared['data_5p'] = detail_5p
                prepared['data_ishikawa'] = detail_ish
                d8_closure = _load_json_dict(item.get('d8_closure_details'))
                d3_rows = obtener_acciones_8d(int(item['id']), 'D3') or []
                d5_rows = obtener_acciones_8d(int(item['id']), 'D5') or []
                d6_rows = obtener_acciones_8d(int(item['id']), 'D6') or []
                all_rows = d3_rows + d5_rows + d6_rows
                progress_pct = _calc_completion_pct(all_rows)
                badge_label, badge_color = _overview_badge(progress_pct, item.get('estado', ''))
                closure_dates = [
                    _parse_dot_date((d8_closure.get(role_key) or {}).get('fecha', ''))
                    for role_key in ['problem_coordinator', 'responsible_q', 'ap_team_leader']
                ]
                closure_dates = [dt for dt in closure_dates if dt is not None]
                prepared['resumen_problema'] = fix_text(item.get('titulo') or item.get('d2_descripcion') or '')
                prepared['fecha_cierre_d3'] = _max_action_date(d3_rows)
                prepared['fecha_cierre_d6'] = _max_action_date(d6_rows)
                prepared['fecha_cierre_final'] = max(closure_dates).strftime('%d.%m.%Y') if closure_dates else ''
                prepared['progress_pct'] = progress_pct
                prepared['overview_status'] = badge_label
                prepared['overview_color'] = badge_color
                prepared_rows.append(prepared)

            total_cases = len(prepared_rows)
            open_cases = sum(1 for item in prepared_rows if str(item.get('estado') or '').strip() != 'Cerrado')
            with_evidence = sum(1 for item in prepared_rows if str(item.get('archivos_path') or '').strip())
            next_8d_number = f"8D-{int(selected_company_id):03d}-{(total_cases + 1):04d}"
            ui.html(_metrics_html(total_cases, open_cases, with_evidence))
            ui.html(_overview_html(prepared_rows))

            with ui.row().classes('w-full items-center justify-between mt-4'):
                with ui.column().classes('gap-1'):
                    ui.label('Casos de analisis activos').classes('ideas-section-title')
                    ui.label('Cada registro consolida 8D, 5 Porques, Ishikawa, acciones y evidencia asociada para exportacion ejecutiva.').classes('ideas-section-note')
                ui.button(
                    'Nuevo analisis',
                    icon='add',
                    on_click=lambda: _show_quality_editor(
                        ui,
                        company_id=int(selected_company_id),
                        company_name=company_name,
                        company_info=empresa,
                        ia_enabled=ia_activa,
                        obtener_fuentes_fn=obtener_fuentes_empresa,
                        sugerir_causas_ishikawa_fn=sugerir_causas_ishikawa,
                        row=None,
                        fix_text_fn=fix_text,
                        crear_problema_fn=crear_problema_calidad_8d,
                        actualizar_problema_fn=actualizar_problema_calidad_8d,
                        guardar_5p_fn=guardar_5_porque_problema_calidad,
                        guardar_ishikawa_fn=guardar_ishikawa_problema_calidad,
                        obtener_acciones_fn=obtener_acciones_8d,
                        guardar_accion_fn=guardar_accion_8d,
                        eliminar_accion_fn=eliminar_accion_8d,
                        generar_pdf_8d_fn=generar_pdf_8d,
                        preset_numero_8d=next_8d_number,
                    ),
                ).props('unelevated color=primary')

            table = ui.table(
                columns=[
                    {'name': 'numero_8d', 'label': 'N 8D', 'field': 'numero_8d', 'align': 'center'},
                    {'name': 'fecha', 'label': 'Fecha apertura', 'field': 'fecha', 'align': 'center'},
                    {'name': 'titulo', 'label': 'Titulo', 'field': 'titulo', 'align': 'left'},
                    {'name': 'fecha_cierre_d3', 'label': 'Cierre D3', 'field': 'fecha_cierre_d3', 'align': 'center'},
                    {'name': 'fecha_cierre_d6', 'label': 'Cierre D6', 'field': 'fecha_cierre_d6', 'align': 'center'},
                    {'name': 'fecha_cierre_final', 'label': 'Cierre final', 'field': 'fecha_cierre_final', 'align': 'center'},
                    {'name': 'estado', 'label': 'Estado 8D', 'field': 'estado', 'align': 'center'},
                    {'name': 'evidencia', 'label': 'Evidencia', 'field': 'evidencia', 'align': 'center'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                ],
                rows=[
                    {
                        'id': int(item['id']),
                        'numero_8d': fix_text(item.get('numero_8d') or f"8D-{int(item['id']):04d}"),
                        'fecha': fix_text(item.get('fecha') or ''),
                        'titulo': fix_text(item.get('resumen_problema') or item.get('titulo') or ''),
                        'fecha_cierre_d3': fix_text(item.get('fecha_cierre_d3') or '-'),
                        'fecha_cierre_d6': fix_text(item.get('fecha_cierre_d6') or '-'),
                        'fecha_cierre_final': fix_text(item.get('fecha_cierre_final') or '-'),
                        'estado': fix_text(item.get('overview_status') or item.get('estado') or 'Abierto'),
                        'estado_color': item.get('overview_color') or 'grey-7',
                        'progress_pct': int(item.get('progress_pct') or 0),
                        'evidencia': 'Si' if str(item.get('archivos_path') or '').strip() else 'No',
                        'acciones': '',
                    }
                    for item in prepared_rows
                ],
                row_key='id',
                pagination=8,
            ).classes('w-full ideas-panel ideas-table mt-4')
            table.props('flat bordered')
            table.add_slot(
                'body-cell-estado',
                '''
                <q-td :props="props">
                    <q-badge
                        :color="{
                            'Abierto': 'negative',
                            'En proceso': 'warning',
                            'En analisis': 'warning',
                            'Avanzado': 'primary',
                            'Implementado': 'primary',
                            'Cerrado': 'positive'
                        }[props.row.estado] || 'grey-7'"
                        rounded
                    >
                        {{ props.row.estado }}
                    </q-badge>
                </q-td>
                ''',
            )
            table.add_slot(
                'body-cell-evidencia',
                '''
                <q-td :props="props">
                    <q-badge :color="props.row.evidencia === 'Si' ? 'positive' : 'grey-6'" rounded>
                        {{ props.row.evidencia }}
                    </q-badge>
                </q-td>
                ''',
            )
            table.add_slot(
                'body-cell-acciones',
                '''
                <q-td :props="props">
                    <div class="row items-center no-wrap q-gutter-sm">
                        <q-btn flat round dense icon="edit" color="primary" @click="$parent.$emit('edit_case', props.row.id)" />
                        <q-btn flat round dense icon="download" color="secondary" @click="$parent.$emit('export_case', props.row.id)" />
                        <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_case', props.row.id)" />
                    </div>
                </q-td>
                ''',
            )
            table.add_slot(
                'body-cell-titulo',
                '''
                <q-td :props="props">
                    <div class="column q-gutter-xs" style="min-width:220px;">
                        <div class="text-body2 text-weight-medium">{{ props.row.titulo }}</div>
                        <q-linear-progress
                            size="8px"
                            rounded
                            :value="(props.row.progress_pct || 0) / 100"
                            :color="props.row.estado_color || 'primary'"
                        />
                        <div class="text-caption text-weight-medium" :class="`text-${props.row.estado_color || 'primary'}`">{{ props.row.estado }}</div>
                        <div class="text-caption text-grey-7">Avance {{ props.row.progress_pct || 0 }}%</div>
                    </div>
                </q-td>
                ''',
            )

            def find_case(case_id: int) -> dict | None:
                return next((item for item in prepared_rows if int(item['id']) == int(case_id)), None)

            def edit_case(case_id: int) -> None:
                current = find_case(case_id)
                if not current:
                    ui.notify('Ese analisis ya no existe.', type='warning')
                    return
                _show_quality_editor(
                    ui,
                    company_id=int(selected_company_id),
                    company_name=company_name,
                    company_info=empresa,
                    ia_enabled=ia_activa,
                    obtener_fuentes_fn=obtener_fuentes_empresa,
                    sugerir_causas_ishikawa_fn=sugerir_causas_ishikawa,
                    row=current,
                    fix_text_fn=fix_text,
                    crear_problema_fn=crear_problema_calidad_8d,
                    actualizar_problema_fn=actualizar_problema_calidad_8d,
                    guardar_5p_fn=guardar_5_porque_problema_calidad,
                    guardar_ishikawa_fn=guardar_ishikawa_problema_calidad,
                    obtener_acciones_fn=obtener_acciones_8d,
                    guardar_accion_fn=guardar_accion_8d,
                    eliminar_accion_fn=eliminar_accion_8d,
                    generar_pdf_8d_fn=generar_pdf_8d,
                )

            def export_case(case_id: int) -> None:
                current = find_case(case_id)
                if not current:
                    ui.notify('Ese analisis ya no existe.', type='warning')
                    return
                try:
                    problema_data = {
                        'empresa': company_name,
                        'razon_social': empresa.get('razon_social') or company_name,
                        'logo_path': empresa.get('logo_path') or '',
                        'color_primario': empresa.get('color_primario') or '',
                        'color_secundario': empresa.get('color_secundario') or '',
                        **(obtener_problema_calidad_detalle(case_id) or current),
                        **(obtener_5_porque_problema_calidad(case_id) or {}),
                        **(obtener_ishikawa_problema_calidad(case_id) or {}),
                    }
                    acciones_d3_d5_d6 = (obtener_acciones_8d(case_id, 'D3') or []) + (obtener_acciones_8d(case_id, 'D5') or []) + (obtener_acciones_8d(case_id, 'D6') or [])
                    pdf_path = generar_pdf_8d(problema_data, acciones_d3_d5_d6) if generar_pdf_8d else generar_reporte_8d(
                        problema_data,
                        obtener_5_porque_problema_calidad(case_id) or {},
                        obtener_ishikawa_problema_calidad(case_id) or {},
                    )
                    ui.download(str(pdf_path))
                except Exception as exc:
                    ui.notify(f'No se pudo generar el reporte: {exc}', type='negative')

            def delete_case(case_id: int) -> None:
                current = find_case(case_id)
                if not current:
                    ui.notify('Ese analisis ya no existe.', type='warning')
                    return
                with ui.dialog() as delete_dialog, ui.card().classes('p-6 max-w-[520px] ideas-panel'):
                    ui.label('Eliminar analisis').classes('text-xl font-bold text-slate-900')
                    ui.label(
                        f"Se eliminara permanentemente el caso '{fix_text(current.get('titulo', ''))}' junto con su 8D, 5 Porques, Ishikawa y acciones asociadas."
                    ).classes('ideas-section-note')
                    with ui.row().classes('w-full justify-end gap-2 mt-4'):
                        ui.button('Cancelar', on_click=delete_dialog.close).props('flat')
                        ui.button(
                            'Eliminar',
                            icon='delete',
                            on_click=lambda: (
                                eliminar_problema_calidad_8d(int(case_id)),
                                delete_dialog.close(),
                                ui.notify('Analisis eliminado correctamente.', type='positive'),
                                ui.navigate.to('/sistema-gestion/calidad'),
                            ),
                        ).props('unelevated color=negative')
                delete_dialog.open()

            table.on('edit_case', lambda event: edit_case(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el analisis.', type='warning'))
            table.on('export_case', lambda event: export_case(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el analisis.', type='warning'))
            table.on('delete_case', lambda event: delete_case(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el analisis.', type='warning'))

            if not prepared_rows:
                ui.label('Todavia no hay analisis cargados para esta empresa.').classes('text-slate-500 mt-4')

