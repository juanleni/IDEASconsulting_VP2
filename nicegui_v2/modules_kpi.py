from __future__ import annotations

import calendar
import json
import unicodedata

from nicegui import app, ui


KPI_CATEGORIES = [
    'Calidad',
    'Produccion',
    'Logistica',
    'Finanzas',
    'Comercial',
    'Recursos Humanos',
    'Compras',
    'Ingenieria',
    'IT',
    'Ambiental',
    'Salud ocupacional',
    'Compliance',
    'Direccion',
]

KPI_FREQUENCIES = ['Diaria', 'Semanal', 'Mensual', 'Trimestral', 'Semestral', 'Anual']
KPI_TRENDS = ['Estable', 'Positiva', 'Negativa', 'En revision']
PROCESS_ICONS = {
    'calidad': 'fact_check',
    'produccion': 'precision_manufacturing',
    'logistica': 'local_shipping',
    'ambiental': 'eco',
    'seguridad': 'health_and_safety',
    'mantenimiento': 'build_circle',
}


def go_to_kpi_module(company_id: int | None = None, set_selection_fn=None) -> None:
    if company_id:
        app.storage.user['management_company_id'] = int(company_id)
        if set_selection_fn:
            set_selection_fn(int(company_id), None)
    ui.navigate.to('/sistema-gestion/kpis')


def _build_kpi_rows(rows: list[dict], fix_text_fn) -> list[dict]:
    built_rows = []
    for row in rows:
        built_rows.append(
            {
                'id': int(row['id']),
                'codigo': fix_text_fn(row.get('codigo') or '—'),
                'nombre': fix_text_fn(row.get('nombre') or ''),
                'categoria': fix_text_fn(row.get('categoria') or 'Sin categoria'),
                'meta': fix_text_fn(row.get('meta') or 'Sin meta'),
                'frecuencia': fix_text_fn(row.get('frecuencia') or 'Sin frecuencia'),
                'responsable': fix_text_fn(row.get('responsable') or 'Sin responsable'),
                'valor_actual': fix_text_fn(row.get('valor_actual') or 'Sin dato'),
                'tendencia': fix_text_fn(row.get('tendencia') or 'Sin definir'),
                'fecha_actualizacion': fix_text_fn(row.get('fecha_actualizacion') or 'Pendiente'),
                'acciones': '',
            }
        )
    return built_rows


def _extract_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, dict):
        if 'id' in value:
            return _extract_int(value['id'])
        if 'row' in value:
            return _extract_int(value['row'])
        return None
    if isinstance(value, (list, tuple)):
        for item in value:
            found = _extract_int(item)
            if found is not None:
                return found
        return None
    try:
        return int(value)
    except Exception:
        return None


def _show_kpi_editor(
    *,
    ui,
    fix_text_fn,
    row: dict | None,
    company_id: int,
    agregar_kpi_empresa_fn,
    actualizar_kpi_fn,
) -> None:
    is_edit = bool(row)
    with ui.dialog() as dialog, ui.card().classes('w-[940px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
        ui.label('Editar KPI' if is_edit else 'Nuevo KPI').classes('text-2xl font-bold text-slate-900')
        ui.label('Define el indicador con su meta, frecuencia, responsable y criterio de seguimiento para que forme parte del sistema de gestion de la empresa.').classes('ideas-section-note')

        codigo_input = ui.input('Codigo', value=fix_text_fn(row.get('codigo', '')) if row else '').classes('w-full').props('outlined')
        nombre_input = ui.input('Nombre del KPI', value=fix_text_fn(row.get('nombre', '')) if row else '').classes('w-full mt-3').props('outlined')

        with ui.row().classes('w-full gap-4 mt-3'):
            categoria_input = ui.select(KPI_CATEGORIES, value=fix_text_fn(row.get('categoria', '')) if row else None, label='Categoria').classes('col').props('outlined use-input fill-input')
            frecuencia_input = ui.select(KPI_FREQUENCIES, value=fix_text_fn(row.get('frecuencia', '')) if row else None, label='Frecuencia').classes('col').props('outlined')
            tendencia_input = ui.select(KPI_TRENDS, value=fix_text_fn(row.get('tendencia', '')) if row else None, label='Tendencia').classes('col').props('outlined')

        with ui.row().classes('w-full gap-4 mt-3'):
            meta_input = ui.input('Meta', value=fix_text_fn(row.get('meta', '')) if row else '').classes('col').props('outlined')
            unidad_input = ui.input('Unidad', value=fix_text_fn(row.get('unidad', '')) if row else '', placeholder='%, PPM, horas, dias, ARS...').classes('col').props('outlined')
            valor_actual_input = ui.input('Valor actual', value=fix_text_fn(row.get('valor_actual', '')) if row else '').classes('col').props('outlined')

        with ui.row().classes('w-full gap-4 mt-3'):
            responsable_input = ui.input('Responsable', value=fix_text_fn(row.get('responsable', '')) if row else '').classes('col').props('outlined')
            fuente_input = ui.input('Fuente de datos', value=fix_text_fn(row.get('fuente', '')) if row else '').classes('col').props('outlined')

        formula_input = ui.textarea('Formula de calculo', value=fix_text_fn(row.get('formula', '')) if row else '').classes('w-full mt-3').props('outlined autogrow')
        observaciones_input = ui.textarea('Observaciones', value=fix_text_fn(row.get('observaciones', '')) if row else '').classes('w-full mt-3').props('outlined autogrow')

        def save_kpi() -> None:
            payload = {
                'codigo': codigo_input.value or '',
                'nombre': nombre_input.value or '',
                'categoria': categoria_input.value or '',
                'formula': formula_input.value or '',
                'meta': meta_input.value or '',
                'frecuencia': frecuencia_input.value or '',
                'responsable': responsable_input.value or '',
                'fuente': fuente_input.value or '',
                'unidad': unidad_input.value or '',
                'valor_actual': valor_actual_input.value or '',
                'tendencia': tendencia_input.value or '',
                'observaciones': observaciones_input.value or '',
            }
            if is_edit:
                ok, message = actualizar_kpi_fn(
                    int(row['id']),
                    payload['codigo'],
                    payload['nombre'],
                    payload['categoria'],
                    payload['formula'],
                    payload['meta'],
                    payload['frecuencia'],
                    payload['responsable'],
                    payload['fuente'],
                    payload['unidad'],
                    payload['valor_actual'],
                    payload['tendencia'],
                    payload['observaciones'],
                )
            else:
                ok, message = agregar_kpi_empresa_fn(
                    int(company_id),
                    payload['nombre'],
                    payload['codigo'],
                    payload['categoria'],
                    payload['formula'],
                    payload['meta'],
                    payload['frecuencia'],
                    payload['responsable'],
                    payload['fuente'],
                    payload['unidad'],
                    payload['valor_actual'],
                    payload['tendencia'],
                    payload['observaciones'],
                )
            ui.notify(fix_text_fn(message), type='positive' if ok else 'negative')
            if ok:
                dialog.close()
                ui.navigate.to('/sistema-gestion/kpis')

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('Cancelar', on_click=dialog.close).props('flat')
            ui.button('Guardar KPI', icon='save', on_click=save_kpi).props('unelevated color=primary')
    dialog.open()


def register_kpi_module(ui, deps: dict) -> None:
    ensure_platform_access = deps['ensure_platform_access']
    shell = deps['shell']
    company_options = deps['company_options']
    current_selection = deps['current_selection']
    set_selection = deps['set_selection']
    obtener_empresa_detalle = deps['obtener_empresa_detalle']
    fix_text = deps['fix_text']
    render_metrics = deps['render_metrics']
    quick_card = deps['quick_card']
    certifications_summary = deps['certifications_summary']
    obtener_kpis_empresa = deps['obtener_kpis_empresa']
    guardar_kpi = deps['guardar_kpi']
    actualizar_kpi_meses = deps['actualizar_kpi_meses']
    actualizar_kpi_diario_y_periodos = deps.get('actualizar_kpi_diario_y_periodos')
    obtener_mapa_procesos_empresa = deps['obtener_mapa_procesos_empresa']
    go = deps['go']
    obtener_kpi_detalle = deps['obtener_kpi_detalle']
    obtener_grupos_kpi_empresa = deps.get('obtener_grupos_kpi_empresa')
    crear_grupo_kpi_empresa = deps.get('crear_grupo_kpi_empresa')
    agregar_kpi_empresa = deps['agregar_kpi_empresa']
    actualizar_kpi = deps['actualizar_kpi']
    actualizar_dashboard_principal_kpi = deps.get('actualizar_dashboard_principal_kpi')
    actualizar_grupos_personalizados_kpi = deps.get('actualizar_grupos_personalizados_kpi')
    eliminar_kpi = deps['eliminar_kpi']
    generar_pdf_kpis = deps.get('generar_pdf_kpis')
    def _open_export_kpis_dialog(company_name: str, company_logo_path: str, kpis_rows: list[dict]) -> None:
        if not generar_pdf_kpis:
            ui.notify('Generación de PDF no disponible.', type='warning')
            return
        if not kpis_rows:
            ui.notify('No hay KPI para exportar.', type='warning')
            return

        options_map = {
            int(row['id']): fix_text(row.get('nombre') or f"KPI {row.get('id')}")
            for row in kpis_rows
        }
        with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[97vw] p-6 rounded-[26px] ideas-panel'):
            ui.label('Exportar reporte KPI').classes('text-2xl font-bold text-slate-900')
            ui.label('Selecciona qué KPI incluir y cómo armar el PDF final.').classes('ideas-section-note')

            selected_kpis = ui.select(
                options_map,
                value=list(options_map.keys()),
                multiple=True,
                label='KPI a incluir',
            ).classes('w-full mt-3').props('outlined use-chips')

            with ui.grid(columns=2).classes('w-full gap-3 mt-4'):
                include_summary = ui.switch('Incluir resumen ejecutivo', value=True)
                include_charts = ui.switch('Incluir gráficos mensuales', value=True)
                include_comments = ui.switch('Incluir comentarios/desvíos', value=True)
                include_mensual = ui.switch('Incluir tabla mensual Ene-Dic', value=False)
                include_codigo = ui.switch('Columna código', value=True)
                include_categoria = ui.switch('Columna categoría', value=True)
                include_meta = ui.switch('Columna meta', value=True)
                include_valor = ui.switch('Columna valor actual', value=True)
                include_tendencia = ui.switch('Columna tendencia', value=True)
                include_responsable = ui.switch('Columna responsable', value=True)

            def do_export() -> None:
                chart_state = app.storage.user.setdefault('kpi_chart_state', {})
                selected_ids = {int(item) for item in (selected_kpis.value or [])}
                selected_rows = [dict(row) for row in kpis_rows if int(row.get('id') or 0) in selected_ids]
                if not selected_rows:
                    ui.notify('Selecciona al menos un KPI para exportar.', type='warning')
                    return
                for row in selected_rows:
                    kpi_id = int(row.get('id') or 0)
                    state = chart_state.get(str(kpi_id), {})
                    row['_export_vista'] = state.get('vista', 'Mensual')
                    row['_export_month_key'] = state.get('month_key', 'ene')
                    row['_export_year_key'] = state.get('year_key', '2026')
                    row['_export_chart_type'] = state.get('chart_type') or row.get('tipo_grafico')
                options = {
                    'include_summary': bool(include_summary.value),
                    'include_charts': bool(include_charts.value),
                    'include_comments': bool(include_comments.value),
                    'include_mensual': bool(include_mensual.value),
                    'include_codigo': bool(include_codigo.value),
                    'include_categoria': bool(include_categoria.value),
                    'include_meta': bool(include_meta.value),
                    'include_valor': bool(include_valor.value),
                    'include_tendencia': bool(include_tendencia.value),
                    'include_responsable': bool(include_responsable.value),
                    'custom_logo_path': company_logo_path,
                }
                try:
                    pdf_path = generar_pdf_kpis(company_name, selected_rows, options)
                    dialog.close()
                    ui.download(str(pdf_path))
                except Exception as exc:
                    ui.notify(f'No se pudo generar el PDF de KPI: {exc}', type='negative')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Generar y descargar PDF', icon='picture_as_pdf', on_click=do_export).props('unelevated color=primary')
        dialog.open()

    meses = [
        ('ene', 'Ene'), ('feb', 'Feb'), ('mar', 'Mar'), ('abr', 'Abr'),
        ('may', 'May'), ('jun', 'Jun'), ('jul', 'Jul'), ('ago', 'Ago'),
        ('sep', 'Sep'), ('oct', 'Oct'), ('nov', 'Nov'), ('dic', 'Dic'),
    ]

    def _to_float(value) -> float | None:
        if value in (None, ''):
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _uses_ytd(kpi: dict) -> bool:
        return int(kpi.get('usa_ytd') or 0) == 1

    def _is_manual_ytd(kpi: dict) -> bool:
        return str(kpi.get('tipo_ytd') or '').strip().lower().startswith('manual')

    def _calc_ytd(kpi: dict) -> float | None:
        if not _uses_ytd(kpi):
            return None
        if _is_manual_ytd(kpi):
            return _to_float(kpi.get('ytd_manual_val'))
        values = [_to_float(kpi.get(key)) for key, _label in meses]
        valid_values = [value for value in values if value is not None]
        return sum(valid_values) / len(valid_values) if valid_values else None

    def _format_number(value) -> str:
        number = _to_float(value)
        if number is None:
            return 'Sin dato'
        return str(int(number)) if float(number).is_integer() else f'{number:.2f}'

    def _normalize_objetivo_sentido(value: str | None) -> str:
        raw = str(value or '').strip().lower()
        if raw in ('menor_mejor', 'ok_bajo_objetivo'):
            return 'menor_mejor'
        if raw in ('mayor_mejor', 'ok_sobre_objetivo'):
            return 'mayor_mejor'
        if any(token in raw for token in ('bajo', 'menor', 'debajo', '↓')):
            return 'menor_mejor'
        return 'mayor_mejor'

    def _kpi_status(item: dict) -> tuple[bool | None, float | None]:
        objetivo = _to_float(item.get('objetivo'))
        if objetivo is None:
            return None, None
        current = _calc_ytd(item) if _uses_ytd(item) else _to_float(item.get('valor_actual'))
        if current is None:
            current = _to_float(item.get('anual_manual_val')) or _to_float(item.get('mensual_manual_val'))
        if current is None:
            current = next((_to_float(item.get(key)) for key, _ in reversed(meses) if _to_float(item.get(key)) is not None), None)
        if current is None:
            return None, None
        sentido = _normalize_objetivo_sentido(item.get('objetivo_sentido'))
        ok = current >= objetivo if sentido == 'mayor_mejor' else current <= objetivo
        return ok, current

    def _daily_period_key(month_key: str, year_value: int | str | None = None) -> str:
        year_clean = str(year_value or 2026).strip()
        return f'{year_clean}-{month_key}'

    def _daily_values_for_month(kpi: dict, month_key: str, year_value: int | str | None = None) -> list[float | None]:
        raw = str(kpi.get('diario_json') or '').strip()
        if not raw:
            return []
        try:
            parsed = json.loads(raw)
        except Exception:
            return []
        if not isinstance(parsed, dict):
            return []
        month_data = parsed.get(_daily_period_key(month_key, year_value))
        if month_data is None:
            month_data = parsed.get(month_key)  # compatibilidad con datos previos
        if not isinstance(month_data, list):
            return []
        values = []
        for item in month_data:
            values.append(_to_float(item))
        return values

    def _available_daily_years(kpi: dict) -> list[str]:
        raw = str(kpi.get('diario_json') or '').strip()
        if not raw:
            return [str(2026)]
        try:
            parsed = json.loads(raw)
        except Exception:
            return [str(2026)]
        if not isinstance(parsed, dict):
            return [str(2026)]
        years = set()
        for key in parsed.keys():
            if '-' in str(key):
                years.add(str(key).split('-', 1)[0])
        return sorted(years) or [str(2026)]

    def _available_views(kpi: dict) -> list[str]:
        views = []
        is_daily_freq = str(kpi.get('frecuencia') or '').strip().lower().startswith('dia')
        has_daily = any(_daily_values_for_month(kpi, key) for key, _ in meses)
        if is_daily_freq or has_daily:
            views.append('Diaria')
        monthly_values = [_to_float(kpi.get(key)) for key, _label in meses]
        if any(value is not None for value in monthly_values) or _to_float(kpi.get('mensual_manual_val')) is not None:
            views.append('Mensual')
        annual_value = _calc_ytd(kpi) if _uses_ytd(kpi) else _to_float(kpi.get('anual_manual_val'))
        if annual_value is not None:
            views.append('Anual')
        return views or ['Mensual']

    def generar_grafico_kpi(kpi, go, vista='Mensual', month_key='ene', year_key='2026', chart_type_override=None):
        objetivo = _to_float(kpi.get('objetivo'))
        labels = [label for _key, label in meses]
        values = [_to_float(kpi.get(key)) for key, _label in meses]
        plot_values = [value if value is not None else 0 for value in values]
        tipo_grafico = fix_text(kpi.get('tipo_grafico') or 'Barra').strip().lower().replace('í', 'i').replace('ã­', 'i')
        tipo_grafico = fix_text(chart_type_override or kpi.get('tipo_grafico') or 'Barra').strip().lower().replace('í', 'i')
        latest_value = next((value for value in reversed(values) if value is not None), None)
        ytd_value = _calc_ytd(kpi)
        current_value = ytd_value if ytd_value is not None else latest_value
        vista_clean = str(vista or 'Mensual').strip().lower()
        if vista_clean.startswith('dia'):
            daily_values = _daily_values_for_month(kpi, month_key, year_key)
            if daily_values:
                labels = [str(i) for i in range(1, len(daily_values) + 1)]
                values = daily_values
                plot_values = [value if value is not None else 0 for value in daily_values]
            else:
                labels = ['Diario']
                day_value = _to_float(kpi.get('valor_actual'))
                if day_value is None:
                    day_value = current_value
                values = [day_value]
                plot_values = [day_value if day_value is not None else 0]
        elif vista_clean.startswith('an'):
            labels = ['Anual']
            annual_value = ytd_value if ytd_value is not None else _to_float(kpi.get('anual_manual_val'))
            if annual_value is None:
                annual_value = current_value
            values = [annual_value]
            plot_values = [annual_value if annual_value is not None else 0]
        elif vista_clean.startswith('men'):
            if all(value is None for value in values):
                monthly_manual = _to_float(kpi.get('mensual_manual_val'))
                if monthly_manual is not None:
                    labels = ['Mensual']
                    values = [monthly_manual]
                    plot_values = [monthly_manual]
        objetivo_sentido = _normalize_objetivo_sentido(kpi.get('objetivo_sentido'))

        def _is_ok(v: float | None) -> bool | None:
            if v is None or objetivo is None:
                return None
            return v >= objetivo if objetivo_sentido == 'mayor_mejor' else v <= objetivo

        colors = []
        for value in values:
            if value is None:
                colors.append('#cbd5e1')
            elif _is_ok(value) is False:
                colors.append('#ef4444')
            else:
                colors.append('#1f7ed6')

        fig = go.Figure()
        if tipo_grafico.startswith('gauge'):
            gauge_value = current_value or 0
            gauge_max = max(gauge_value, objetivo or gauge_value or 1) * 1.25
            fig.add_trace(
                go.Indicator(
                    mode='gauge+number',
                    value=gauge_value,
                    gauge={
                        'axis': {'range': [0, gauge_max]},
                        'bar': {'color': '#1f7ed6'},
                        'threshold': {'line': {'color': '#ef4444', 'width': 4}, 'thickness': 0.8, 'value': objetivo or 0},
                    },
                    number={'suffix': f" {fix_text(kpi.get('unidad') or '')}"},
                )
            )
        elif tipo_grafico.startswith('bullet'):
            bullet_value = current_value or 0
            bullet_max = max(bullet_value, objetivo or bullet_value or 1) * 1.25
            fig.add_trace(
                go.Indicator(
                    mode='number+gauge',
                    value=bullet_value,
                    gauge={
                        'shape': 'bullet',
                        'axis': {'range': [0, bullet_max]},
                        'bar': {'color': '#1f7ed6'},
                        'threshold': {'line': {'color': '#ef4444', 'width': 3}, 'thickness': 0.75, 'value': objetivo or 0},
                    },
                    number={'suffix': f" {fix_text(kpi.get('unidad') or '')}"},
                )
            )
        elif tipo_grafico.startswith('radar'):
            fig.add_trace(
                go.Scatterpolar(
                    r=plot_values,
                    theta=labels,
                    fill='toself',
                    line={'color': '#1f7ed6', 'width': 3},
                    hovertemplate='%{theta}: %{r}<extra></extra>',
                )
            )
            if objetivo is not None:
                fig.add_trace(
                    go.Scatterpolar(
                        r=[objetivo for _ in labels],
                        theta=labels,
                        fill=None,
                        line={'color': '#ef4444', 'dash': 'dot', 'width': 2},
                        hovertemplate='Objetivo: %{r}<extra></extra>',
                    )
                )
            fig.update_layout(polar={'radialaxis': {'visible': True}})
        elif tipo_grafico.startswith('barra'):
            fig.add_trace(
                go.Bar(
                    x=labels,
                    y=plot_values,
                    marker_color=colors,
                    text=[_format_number(value) if value is not None else '' for value in values],
                    textposition='outside',
                    hovertemplate='%{x}: %{y}<extra></extra>',
                )
            )
        else:
            fig.add_trace(
                go.Scatter(
                    x=labels,
                    y=plot_values,
                    mode='lines+markers',
                    line={'color': '#1f7ed6', 'width': 3},
                    marker={'size': 8, 'color': colors},
                    hovertemplate='%{x}: %{y}<extra></extra>',
                )
            )
        if objetivo is not None and (tipo_grafico.startswith('barra') or tipo_grafico.startswith('línea') or tipo_grafico.startswith('linea')):
            fig.add_hline(
                y=objetivo,
                line_dash='dot',
                line_color='#ef4444',
                annotation_text=f"Objetivo {'↑' if objetivo_sentido == 'mayor_mejor' else '↓'} {_format_number(objetivo)}",
                annotation_position='top left',
            )
        fig.update_layout(
            height=280,
            margin={'l': 28, 'r': 16, 't': 24, 'b': 32},
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(248,250,252,0.85)',
            showlegend=False,
            yaxis={'gridcolor': 'rgba(148,163,184,0.22)', 'zeroline': False},
            xaxis={'gridcolor': 'rgba(148,163,184,0.10)'},
            font={'family': 'Aptos, Segoe UI, sans-serif', 'color': '#334155'},
        )
        return fig

    def _process_options(company_id: int) -> dict[int, str]:
        rows = obtener_mapa_procesos_empresa(int(company_id))
        return {int(row['id']): fix_text(row.get('proceso_nombre') or row.get('proceso_codigo') or '') for row in rows}

    def _show_new_kpi_dialog(company_id: int, kpi: dict | None = None) -> None:
        is_edit = bool(kpi)
        process_map = _process_options(company_id)
        with ui.dialog() as dialog, ui.card().classes('w-[760px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
            ui.label('Editar KPI' if is_edit else 'Nuevo KPI').classes('text-2xl font-bold text-slate-900')
            ui.label('Crea el indicador, vinculalo a un proceso y define como se calculara su seguimiento anual.').classes('ideas-section-note')
            nombre_input = ui.input('Nombre del KPI', value=fix_text(kpi.get('nombre') or '') if kpi else '').classes('w-full mt-3').props('outlined')
            proceso_value = int(kpi.get('proceso_id')) if kpi and kpi.get('proceso_id') else next(iter(process_map.keys())) if process_map else None
            proceso_select = ui.select(process_map, label='Proceso', value=proceso_value).classes('w-full mt-3').props('outlined')
            with ui.row().classes('w-full gap-4 mt-3'):
                objetivo_input = ui.number('Objetivo / Meta', value=_to_float(kpi.get('objetivo')) if kpi else None, format='%.2f').classes('col').props('outlined')
                unidad_input = ui.input('Unidad', value=fix_text(kpi.get('unidad') or '') if kpi else '', placeholder='%, PPM, horas, unidades...').classes('col').props('outlined')
                grafico_select = ui.select(['Barra', 'Línea', 'Gauge', 'Bullet', 'Radar'], value=fix_text(kpi.get('tipo_grafico') or 'Barra') if kpi else 'Barra', label='Tipo de Gráfico').classes('col').props('outlined')
            objetivo_sentido_select = ui.select(
                {'ok_sobre_objetivo': '↑ OK Sobre Objetivo', 'ok_bajo_objetivo': '↓ OK Bajo Objetivo'},
                value='ok_bajo_objetivo' if _normalize_objetivo_sentido((kpi or {}).get('objetivo_sentido')) == 'menor_mejor' else 'ok_sobre_objetivo',
                label='Regla de cumplimiento',
            ).classes('w-full mt-3').props('outlined')
            responsable_input = ui.input('Responsable', value=fix_text(kpi.get('responsable') or '') if kpi else '').classes('w-full mt-3').props('outlined')
            frecuencia_select = ui.select(
                ['Diaria', 'Mensual', 'Anual'],
                value=fix_text(kpi.get('frecuencia') or 'Mensual') if kpi else 'Mensual',
                label='Frecuencia de carga',
            ).classes('w-full mt-3').props('outlined')
            incluir_ytd = ui.switch('Incluir YTD', value=_uses_ytd(kpi or {})).classes('mt-3')
            with ui.column().classes('w-full mt-2') as ytd_box:
                tipo_ytd_select = ui.select(
                    ['Automático (Promedio)', 'Manual (Ingreso directo)'],
                    value='Automático (Promedio)',
                    label='Tipo de YTD',
                ).classes('w-full').props('outlined')
            ytd_box.bind_visibility_from(incluir_ytd, 'value')
            destacar_switch = ui.switch('Destacar en Dashboard principal', value=int((kpi or {}).get('mostrar_en_dashboard', 1) or 0) == 1).classes('mt-3')

            def save_new_kpi() -> None:
                responsable = str(responsable_input.value or '').strip()
                if not responsable:
                    ui.notify('El responsable es obligatorio para guardar el KPI.', type='warning')
                    return
                tipo_ytd = ''
                if incluir_ytd.value:
                    tipo_ytd = 'Manual' if str(tipo_ytd_select.value or '').startswith('Manual') else 'Automático'
                freq_value = str(frecuencia_select.value or 'Mensual')
                if is_edit:
                    ok, message = actualizar_kpi(
                        int(kpi['id']),
                        nombre=nombre_input.value or '',
                        meta='' if objetivo_input.value is None else str(objetivo_input.value),
                        unidad=unidad_input.value or '',
                        objetivo=objetivo_input.value,
                        responsable=responsable,
                        frecuencia=freq_value,
                        mostrar_en_dashboard=1 if destacar_switch.value else 0,
                        proceso_id=proceso_select.value,
                        tipo_grafico=grafico_select.value or 'Barra',
                        usa_ytd=1 if incluir_ytd.value else 0,
                        tipo_ytd=tipo_ytd,
                        objetivo_sentido=_normalize_objetivo_sentido(objetivo_sentido_select.value),
                    )
                else:
                    ok, message, _kpi_id = guardar_kpi(
                        int(company_id),
                        proceso_select.value,
                        nombre_input.value or '',
                        objetivo_input.value,
                        unidad_input.value or '',
                        grafico_select.value or 'Barra',
                        1 if incluir_ytd.value else 0,
                        tipo_ytd,
                        1 if destacar_switch.value else 0,
                        responsable,
                        freq_value,
                        _normalize_objetivo_sentido(objetivo_sentido_select.value),
                    )
                ui.notify(fix_text(message), type='positive' if ok else 'negative')
                if ok:
                    dialog.close()
                    ui.navigate.to('/sistema-gestion/kpis')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar KPI', icon='save', on_click=save_new_kpi).props('unelevated color=primary')
        dialog.open()

    def _show_months_dialog(kpi: dict) -> None:
        with ui.dialog() as dialog, ui.card().classes('w-[880px] max-w-[96vw] p-6 rounded-[28px] ideas-panel'):
            ui.label(f"Cargar meses - {fix_text(kpi.get('nombre') or '')}").classes('text-2xl font-bold text-slate-900')
            ui.label('Registra los valores mensuales y deja visible la justificacion cuando el indicador se aleja del objetivo.').classes('ideas-section-note')
            month_inputs = {}
            with ui.grid(columns=4).classes('w-full gap-3 mt-4'):
                for key, label in meses:
                    month_inputs[key] = ui.number(label, value=_to_float(kpi.get(key)), format='%.2f').props('outlined')
            ytd_manual_input = None
            if _is_manual_ytd(kpi):
                ytd_manual_input = ui.number('Valor YTD Actual', value=_to_float(kpi.get('ytd_manual_val')), format='%.2f').classes('w-full mt-4').props('outlined')
            comentario_input = ui.textarea(
                'Comentarios / Justificación de desvíos',
                value=fix_text(kpi.get('comentarios_desvio') or ''),
            ).classes('w-full mt-4 bg-red-50 text-red-900 rounded-lg').props('outlined autogrow')

            def save_months() -> None:
                months_payload = {key: field.value for key, field in month_inputs.items()}
                ytd_manual_value = ytd_manual_input.value if ytd_manual_input else None
                ok, message = actualizar_kpi_meses(int(kpi['id']), months_payload, ytd_manual_value, comentario_input.value or '')
                ui.notify(fix_text(message), type='positive' if ok else 'negative')
                if ok:
                    dialog.close()
                    ui.navigate.to('/sistema-gestion/kpis')

            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar meses', icon='save', on_click=save_months).props('unelevated color=primary')
        dialog.open()

    def _show_daily_dialog(kpi: dict) -> None:
        if not actualizar_kpi_diario_y_periodos:
            ui.notify('Carga diaria no disponible.', type='warning')
            return
        month_map = {key: label for key, label in meses}
        selected_month_key = {'value': 'ene'}
        selected_year_value = {'value': '2026'}
        daily_inputs = []
        state = {'daily': {}}
        try:
            state['daily'] = json.loads(str(kpi.get('diario_json') or '').strip()) if str(kpi.get('diario_json') or '').strip() else {}
        except Exception:
            state['daily'] = {}

        with ui.dialog() as dialog, ui.card().classes('w-[980px] max-w-[97vw] p-6 rounded-[28px] ideas-panel'):
            ui.label(f"Carga diaria - {fix_text(kpi.get('nombre') or '')}").classes('text-2xl font-bold text-slate-900')
            ui.label('Selecciona el mes y carga valores por día según cantidad real de días.').classes('ideas-section-note')
            years = _available_daily_years(kpi)
            with ui.row().classes('w-full gap-3 mt-2'):
                year_select = ui.select(years, value=years[-1], label='Año').classes('w-[160px]').props('outlined')
                month_select = ui.select(month_map, value='ene', label='Mes').classes('w-[220px]').props('outlined')
            selected_year_value['value'] = str(year_select.value or years[-1])
            mensual_manual_input = None
            anual_manual_input = None
            if _uses_ytd(kpi) and not _is_manual_ytd(kpi):
                ui.label('MTD/YTD automático: los valores mensual y anual se calculan automáticamente con la carga diaria.').classes('w-full mt-3 text-sm text-slate-600')
            else:
                mensual_manual_input = ui.number('Valor mensual manual', value=_to_float(kpi.get('mensual_manual_val')), format='%.2f').classes('w-full mt-3').props('outlined')
                anual_manual_input = ui.number('Valor anual manual', value=_to_float(kpi.get('anual_manual_val')), format='%.2f').classes('w-full mt-3').props('outlined')

            days_box = ui.column().classes('w-full mt-4')

            def render_days() -> None:
                days_box.clear()
                daily_inputs.clear()
                month_key = str(month_select.value or 'ene')
                year_value = str(year_select.value or '2026')
                selected_month_key['value'] = month_key
                selected_year_value['value'] = year_value
                month_idx = [key for key, _ in meses].index(month_key) + 1
                year = int(year_value)
                total_days = calendar.monthrange(year, month_idx)[1]
                period_key = _daily_period_key(month_key, year_value)
                existing = state['daily'].get(period_key) if isinstance(state['daily'], dict) else None
                if existing is None and isinstance(state['daily'], dict):
                    existing = state['daily'].get(month_key)
                existing = existing if isinstance(existing, list) else []
                with days_box:
                    ui.label(f'Días del mes ({total_days})').classes('ideas-section-title')
                    with ui.grid(columns=7).classes('w-full gap-2 mt-2'):
                        for day in range(1, total_days + 1):
                            prev = existing[day - 1] if day - 1 < len(existing) else None
                            inp = ui.number(f'D{day}', value=_to_float(prev), format='%.2f').props('outlined dense')
                            daily_inputs.append(inp)

            def save_daily() -> None:
                month_key = selected_month_key['value']
                year_value = selected_year_value['value']
                period_key = _daily_period_key(month_key, year_value)
                state['daily'][period_key] = [inp.value if inp.value not in (None, '') else None for inp in daily_inputs]
                daily_json = json.dumps(state['daily'], ensure_ascii=False)
                mensual_value = mensual_manual_input.value if mensual_manual_input else None
                anual_value = anual_manual_input.value if anual_manual_input else None
                if _uses_ytd(kpi) and not _is_manual_ytd(kpi):
                    month_values = [_to_float(item) for item in state['daily'].get(period_key, [])]
                    month_values = [item for item in month_values if item is not None]
                    mensual_value = (sum(month_values) / len(month_values)) if month_values else None
                    monthly_avgs = []
                    for key, _label in meses:
                        vals = [_to_float(item) for item in state['daily'].get(_daily_period_key(key, year_value), [])]
                        vals = [item for item in vals if item is not None]
                        if vals:
                            monthly_avgs.append(sum(vals) / len(vals))
                    anual_value = (sum(monthly_avgs) / len(monthly_avgs)) if monthly_avgs else None
                ok, msg = actualizar_kpi_diario_y_periodos(
                    int(kpi['id']),
                    daily_json,
                    mensual_value,
                    anual_value,
                )
                ui.notify(fix_text(msg), type='positive' if ok else 'negative')
                if ok:
                    dialog.close()
                    ui.navigate.to('/sistema-gestion/kpis')

            month_select.on_value_change(lambda _e: render_days())
            year_select.on_value_change(lambda _e: render_days())
            render_days()
            with ui.row().classes('w-full justify-end gap-2 mt-5'):
                ui.button('Cancelar', on_click=dialog.close).props('flat')
                ui.button('Guardar carga diaria', icon='save', on_click=save_daily).props('unelevated color=primary')
        dialog.open()

    @ui.page('/sistema-gestion/kpis')
    def kpi_module_page() -> None:
        if not ensure_platform_access():
            return

        shell_container = shell('Indicadores KPI', back_route='/sistema-gestion')
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
            ui.label('Indicadores clave de performance').classes('ideas-kicker')
            ui.label('Modulo KPI por empresa').classes('text-3xl font-bold text-slate-900')
            ui.label('Define, actualiza y sigue indicadores de gestion asociados a la empresa activa, sin mezclar informacion entre clientes.').classes('ideas-subtitle mb-3')

            if not company_map:
                ui.label('Primero necesitas registrar una empresa para habilitar el modulo KPI.').classes('text-slate-500')
                return

            if str(app.storage.user.get('role') or '') == 'admin':
                company_select = ui.select(company_map, value=selected_company_id, label='Empresa-cliente').classes('w-full').props('outlined')
                company_select.on_value_change(
                    lambda _e: (
                        app.storage.user.__setitem__('management_company_id', int(company_select.value) if company_select.value else None),
                        set_selection(int(company_select.value), None) if company_select.value else None,
                        ui.navigate.to('/sistema-gestion/kpis'),
                    )
                )

            if not selected_company_id:
                ui.label('Selecciona una empresa para comenzar.').classes('text-slate-500 mt-4')
                return

            company = obtener_empresa_detalle(selected_company_id)
            company_name = fix_text(company.get('razon_social', company_map.get(selected_company_id, ''))) if company else fix_text(company_map.get(selected_company_id, ''))
            kpis = obtener_kpis_empresa(int(selected_company_id))

            with_target = sum(1 for item in kpis if _to_float(item.get('objetivo')) is not None)
            with_ytd = sum(1 for item in kpis if _uses_ytd(item))
            with_deviation = sum(1 for item in kpis if str(item.get('comentarios_desvio') or '').strip())

            if False:
                ui.html(
                f'''
                <div class="ideas-workspace-banner w-full mt-4">
                    <div class="eyebrow">Sistema de gestion · KPI</div>
                    <div class="headline">{company_name}</div>
                    <div class="support">
                        Tablero mensual con objetivos, desvíos visibles, YTD automático o manual y trazabilidad por proceso.
                    </div>
                </div>
                '''
            )

                render_metrics(
                    ui.row().classes('w-full mt-4'),
                    [
                        ('KPI activos', str(len(kpis)), 'Indicadores actualmente registrados para la empresa seleccionada.'),
                        ('Con objetivo', str(with_target), 'Indicadores con linea de cumplimiento definida.'),
                        ('Con YTD', str(with_ytd), 'Indicadores con acumulado anual automatico o manual.'),
                        ('Con desvio justificado', str(with_deviation), 'Indicadores con alerta y comentario del responsable.'),
                    ],
                )

            with ui.row().classes('w-full justify-between items-center mt-6'):
                with ui.column().classes('gap-0'):
                    ui.label('Tablero KPI').classes('ideas-section-title')
                    ui.label('Las barras rojas muestran meses bajo objetivo y los comentarios dejan visible la causa del desvio.').classes('ideas-section-note')
                with ui.row().classes('items-center gap-2'):
                    ui.button(
                        'Exportar a PDF',
                        icon='picture_as_pdf',
                        color='red-8',
                        on_click=lambda: _open_export_kpis_dialog(company_name, str((company or {}).get('logo_path') or ''), kpis),
                    ).props('unelevated')
                    ui.button('Nuevo KPI', icon='add_chart', on_click=lambda: _show_new_kpi_dialog(int(selected_company_id))).props('unelevated color=secondary')

            def confirm_delete_kpi(kpi_id: int) -> None:
                row = obtener_kpi_detalle(int(kpi_id))
                if not row:
                    ui.notify('Ese KPI ya no existe.', type='warning')
                    return
                with ui.dialog() as dialog, ui.card().classes('p-5 max-w-[560px]'):
                    ui.label('Eliminar KPI').classes('text-lg font-semibold')
                    ui.label(f"Se eliminara permanentemente el KPI {fix_text(row.get('nombre', ''))}. Esta accion no se puede deshacer.").classes('text-slate-600')
                    with ui.row().classes('w-full justify-end gap-2 mt-3'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat')

                        def do_delete() -> None:
                            eliminar_kpi(int(kpi_id))
                            dialog.close()
                            ui.notify('KPI eliminado correctamente.', type='positive')
                            ui.navigate.to('/sistema-gestion/kpis')

                        ui.button('Eliminar', color='negative', on_click=do_delete)
                dialog.open()

            if not kpis:
                with ui.card().classes('ideas-panel w-full mt-4'):
                    ui.label('Todavia no hay KPI cargados para esta empresa.').classes('text-slate-600')
                    ui.button('Crear primer KPI', icon='add_chart', on_click=lambda: _show_new_kpi_dialog(int(selected_company_id))).props('unelevated color=primary')
                return

            def render_kpi_card(kpi: dict) -> None:
                ytd_value = _calc_ytd(kpi)
                proceso_nombre = fix_text(kpi.get('proceso_nombre') or 'Sin proceso')
                comentario = fix_text(kpi.get('comentarios_desvio') or '')
                with ui.card().classes('ideas-panel w-full'):
                    with ui.row().classes('w-full justify-between items-start gap-3'):
                        with ui.column().classes('gap-1'):
                            ui.label(fix_text(kpi.get('nombre') or 'KPI sin nombre')).classes('text-xl font-bold text-slate-900')
                            ui.badge(proceso_nombre, color='blue-grey').classes('px-3 py-2')
                        with ui.row().classes('items-center gap-2'):
                            ui.button(icon='settings', on_click=lambda row=kpi: _show_new_kpi_dialog(int(selected_company_id), row)).props('flat round color=secondary')
                            ui.button(icon='edit_calendar', on_click=lambda row=kpi: _show_months_dialog(row)).props('flat round color=primary')
                            ui.button(icon='delete', on_click=lambda row_id=int(kpi['id']): confirm_delete_kpi(row_id)).props('flat round color=negative')

                    if False and _uses_ytd(kpi):
                        ui.html(
                            f'''
                            <div style="margin-top:14px;padding:16px;border-radius:20px;background:linear-gradient(135deg, rgba(31,126,214,.10), rgba(15,143,97,.10));border:1px solid rgba(31,126,214,.18);">
                                <div style="font-size:.72rem;font-weight:800;letter-spacing:.10em;text-transform:uppercase;color:#475569;">YTD</div>
                                <div style="font-size:2.15rem;font-weight:800;color:#0f172a;line-height:1;margin-top:6px;">{_format_number(ytd_value)} <span style="font-size:1rem;color:#64748b;">{fix_text(kpi.get('unidad') or '')}</span></div>
                                <div style="margin-top:6px;color:#64748b;">{fix_text(kpi.get('tipo_ytd') or 'Automático')}</div>
                            </div>
                            '''
                        )

                    views = _available_views(kpi)
                    default_view = 'Mensual' if 'Mensual' in views else views[0]
                    month_map = {key: label for key, label in meses}
                    year_options = _available_daily_years(kpi)
                    chart_state = app.storage.user.setdefault('kpi_chart_state', {})
                    kpi_state = chart_state.get(str(int(kpi.get('id') or 0)), {})
                    initial_view = kpi_state.get('vista') if kpi_state.get('vista') in views else default_view
                    initial_month = kpi_state.get('month_key') if kpi_state.get('month_key') in month_map else 'ene'
                    initial_year = kpi_state.get('year_key') if kpi_state.get('year_key') in year_options else year_options[-1]
                    initial_type = kpi_state.get('chart_type') or fix_text(kpi.get('tipo_grafico') or 'Barra')
                    with ui.row().classes('w-full items-center gap-2 mt-2'):
                        if _uses_ytd(kpi):
                            ui.html(
                                f'<div style="padding:6px 10px;border-radius:10px;background:rgba(31,126,214,.08);border:1px solid rgba(31,126,214,.18);font-size:.82rem;font-weight:700;color:#0f172a;white-space:nowrap;">YTD: {_format_number(ytd_value)} {fix_text(kpi.get("unidad") or "")}</div>'
                            )
                        vista_chart = ui.select(views, value=initial_view, label='Vista').classes('w-[120px]').props('outlined dense')
                        month_chart = ui.select(month_map, value=initial_month, label='Mes').classes('w-[92px]').props('outlined dense')
                        year_chart = ui.select(year_options, value=initial_year, label='Año').classes('w-[92px]').props('outlined dense')
                        tipo_chart = ui.select(
                            ['Barra', 'Línea', 'Gauge', 'Bullet', 'Radar'],
                            value=initial_type,
                            label='Gráfico',
                        ).classes('w-[110px]').props('outlined dense')
                        cargar_diario_btn = ui.button(icon='calendar_month', on_click=lambda row=kpi: _show_daily_dialog(row)).props('flat round color=primary')
                    month_chart.bind_visibility_from(vista_chart, 'value', lambda v: str(v or '').lower().startswith('dia'))
                    year_chart.bind_visibility_from(vista_chart, 'value', lambda v: str(v or '').lower().startswith('dia'))
                    cargar_diario_btn.bind_visibility_from(vista_chart, 'value', lambda v: str(v or '').lower().startswith('dia'))
                    @ui.refreshable
                    def _render_chart():
                        chart_state = app.storage.user.setdefault('kpi_chart_state', {})
                        chart_state[str(int(kpi.get('id') or 0))] = {
                            'vista': vista_chart.value or 'Mensual',
                            'month_key': month_chart.value or 'ene',
                            'year_key': year_chart.value or '2026',
                            'chart_type': tipo_chart.value or (kpi.get('tipo_grafico') or 'Barra'),
                        }
                        ui.plotly(
                            generar_grafico_kpi(
                                kpi,
                                go,
                                vista_chart.value or 'Mensual',
                                month_key=month_chart.value or 'ene',
                                year_key=year_chart.value or '2026',
                                chart_type_override=tipo_chart.value or None,
                            )
                        ).classes('w-full mt-2')
                    _render_chart()
                    vista_chart.on_value_change(lambda _e: _render_chart.refresh())
                    month_chart.on_value_change(lambda _e: _render_chart.refresh())
                    year_chart.on_value_change(lambda _e: _render_chart.refresh())
                    tipo_chart.on_value_change(lambda _e: _render_chart.refresh())

                    with ui.row().classes('w-full justify-between text-sm text-slate-500 mt-1'):
                        ui.label(f"Objetivo: {_format_number(kpi.get('objetivo'))} {fix_text(kpi.get('unidad') or '')}")
                        ui.label(f"Ult. actualización: {fix_text(kpi.get('fecha_actualizacion') or 'Pendiente')}")

                    ok_state, current_state_value = _kpi_status(kpi)
                    if ok_state is not None:
                        sentido = _normalize_objetivo_sentido(kpi.get('objetivo_sentido'))
                        arrow_ok = 'arrow_upward' if sentido == 'mayor_mejor' else 'arrow_downward'
                        arrow_nok = 'arrow_downward' if sentido == 'mayor_mejor' else 'arrow_upward'
                        with ui.row().classes('w-full items-center gap-2 mt-2'):
                            ui.icon(arrow_ok if ok_state else arrow_nok, color='positive' if ok_state else 'negative')
                            ui.icon('check_circle' if ok_state else 'cancel', color='positive' if ok_state else 'negative')
                            ui.label(
                                f"{'OK' if ok_state else 'NOK'} · Actual {_format_number(current_state_value)} vs Objetivo {_format_number(kpi.get('objetivo'))}"
                            ).classes('text-sm font-semibold text-green-700' if ok_state else 'text-sm font-semibold text-red-700')

                    if comentario:
                        with ui.element('div').classes('w-full mt-3 bg-red-50 text-red-900 border border-red-200 rounded-xl p-4'):
                            ui.label('Alerta de Desvío:').classes('font-bold')
                            ui.label(comentario).classes('mt-1')

            dashboard_kpis = [item for item in kpis if int(item.get('dashboard_principal') or 0) == 1]
            if not dashboard_kpis:
                dashboard_kpis = [item for item in kpis if int(item.get('mostrar_en_dashboard', 1) or 0) == 1]
            with ui.tabs().classes('w-full mt-6') as tabs:
                dashboard_tab = ui.tab('Dashboard Principal', icon='donut_large').props('no-caps')
                all_tab = ui.tab('Todos los KPI', icon='table_chart').props('no-caps')
                groups_tab = ui.tab('Grupos y Reuniones', icon='co_present').props('no-caps')
            with ui.tab_panels(tabs, value=dashboard_tab).classes('w-full bg-transparent'):
                with ui.tab_panel(dashboard_tab).classes('px-0'):
                    if not dashboard_kpis:
                        with ui.card().classes('ideas-panel w-full mt-4'):
                            ui.label('No hay KPIs destacados en el dashboard principal.').classes('text-slate-600')
                            ui.label('Abrí Todos los KPIs y activá "Destacar en Dashboard principal" en los indicadores clave.').classes('ideas-section-note')
                    else:
                        with ui.grid(columns=2).classes('ideas-grid-2 w-full mt-4'):
                            for kpi in dashboard_kpis:
                                render_kpi_card(kpi)
                with ui.tab_panel(all_tab).classes('px-0'):
                    grouped_by_process = {}
                    for kpi in kpis:
                        process_name = fix_text(kpi.get('proceso_nombre') or 'Sin proceso')
                        grouped_by_process.setdefault(process_name, []).append(kpi)
                    process_names = sorted(grouped_by_process.keys(), key=lambda item: item.lower())
                    process_tabs_map = {}
                    if process_names:
                        with ui.tabs().classes('w-full mt-4') as process_tabs:
                            process_tabs_map['__all__'] = ui.tab('Todos', icon='table_rows').props('no-caps')
                            for process_name in process_names:
                                process_norm = unicodedata.normalize('NFKD', process_name).encode('ascii', 'ignore').decode('ascii').lower()
                                process_icon = PROCESS_ICONS.get(process_norm, 'analytics')
                                process_tabs_map[process_name] = ui.tab(process_name, icon=process_icon).props('no-caps')
                        with ui.tab_panels(process_tabs, value=process_tabs_map['__all__']).classes('w-full bg-transparent'):
                            for process_name in ['__all__'] + process_names:
                                with ui.tab_panel(process_tabs_map[process_name]).classes('px-0'):
                                    process_kpis = kpis if process_name == '__all__' else grouped_by_process.get(process_name, [])
                                    rows = []
                                    for item in process_kpis:
                                        ytd_value = _calc_ytd(item)
                                        rows.append({
                                            'id': int(item.get('id') or 0),
                                            'nombre': fix_text(item.get('nombre') or ''),
                                            'unidad': fix_text(item.get('unidad') or ''),
                                            'meta': _format_number(item.get('objetivo') or item.get('meta')),
                                            'ytd': _format_number(ytd_value),
                                            'responsable': fix_text(item.get('responsable') or 'Sin responsable'),
                                            'fecha_actualizacion': fix_text(item.get('fecha_actualizacion') or 'Pendiente'),
                                            'dashboard_principal': int(item.get('dashboard_principal') or 0) == 1,
                                        })

                                    table = ui.table(
                                        columns=[
                                            {'name': 'nombre', 'label': 'Nombre', 'field': 'nombre', 'align': 'left'},
                                            {'name': 'unidad', 'label': 'Unidad', 'field': 'unidad', 'align': 'left'},
                                            {'name': 'meta', 'label': 'Meta', 'field': 'meta', 'align': 'left'},
                                            {'name': 'ytd', 'label': 'YTD', 'field': 'ytd', 'align': 'left'},
                                            {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                                            {'name': 'fecha_actualizacion', 'label': 'Última actualización', 'field': 'fecha_actualizacion', 'align': 'left'},
                                            {'name': 'dashboard_principal', 'label': 'Dashboard Principal', 'field': 'dashboard_principal', 'align': 'center'},
                                        ],
                                        rows=rows,
                                        row_key='id',
                                        pagination=0,
                                    ).classes('ideas-panel w-full mt-2')
                                    table.props('flat bordered dense wrap-cells')
                                    table.add_slot(
                                        'body-cell-dashboard_principal',
                                        r'''
                                        <q-td :props="props" class="text-center">
                                          <q-toggle
                                            :model-value="props.row.dashboard_principal"
                                            color="primary"
                                            @update:model-value="$parent.$emit('toggle_dashboard_principal', { id: props.row.id, value: $event })"
                                          />
                                        </q-td>
                                        '''
                                    )

                                    def _on_toggle_dashboard_principal_new(event):
                                        payload = event.args or {}
                                        kpi_id = int(payload.get('id') or 0)
                                        value = 1 if bool(payload.get('value')) else 0
                                        if not kpi_id:
                                            return
                                        if actualizar_dashboard_principal_kpi:
                                            ok, message = actualizar_dashboard_principal_kpi(kpi_id, value)
                                        else:
                                            ok, message = False, 'No se encontró función para actualizar dashboard principal.'
                                        ui.notify(fix_text(message), type='positive' if ok else 'negative')
                                        if ok:
                                            ui.navigate.to('/sistema-gestion/kpis')

                                    table.on('toggle_dashboard_principal', _on_toggle_dashboard_principal_new)
                    else:
                        ui.label('No hay KPI cargados por proceso.').classes('ideas-section-note mt-4')
                    for process_name, process_kpis in []:
                        ui.label(process_name).classes('ideas-section-title mt-6')
                        rows = []
                        for item in process_kpis:
                            ytd_value = _calc_ytd(item)
                            rows.append({
                                'id': int(item.get('id') or 0),
                                'nombre': fix_text(item.get('nombre') or ''),
                                'unidad': fix_text(item.get('unidad') or ''),
                                'meta': _format_number(item.get('objetivo') or item.get('meta')),
                                'ytd': _format_number(ytd_value),
                                'responsable': fix_text(item.get('responsable') or 'Sin responsable'),
                                'fecha_actualizacion': fix_text(item.get('fecha_actualizacion') or 'Pendiente'),
                                'dashboard_principal': int(item.get('dashboard_principal') or 0) == 1,
                            })

                        table = ui.table(
                            columns=[
                                {'name': 'nombre', 'label': 'Nombre', 'field': 'nombre', 'align': 'left'},
                                {'name': 'unidad', 'label': 'Unidad', 'field': 'unidad', 'align': 'left'},
                                {'name': 'meta', 'label': 'Meta', 'field': 'meta', 'align': 'left'},
                                {'name': 'ytd', 'label': 'YTD', 'field': 'ytd', 'align': 'left'},
                                {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                                {'name': 'fecha_actualizacion', 'label': 'Última actualización', 'field': 'fecha_actualizacion', 'align': 'left'},
                                {'name': 'dashboard_principal', 'label': 'Dashboard Principal', 'field': 'dashboard_principal', 'align': 'center'},
                            ],
                            rows=rows,
                            row_key='id',
                            pagination=0,
                        ).classes('ideas-panel w-full mt-2')
                        table.props('flat bordered dense wrap-cells')
                        table.add_slot(
                            'body-cell-dashboard_principal',
                            r'''
                            <q-td :props="props" class="text-center">
                              <q-toggle
                                :model-value="props.row.dashboard_principal"
                                color="primary"
                                @update:model-value="$parent.$emit('toggle_dashboard_principal', { id: props.row.id, value: $event })"
                              />
                            </q-td>
                            '''
                        )

                        def _on_toggle_dashboard_principal(event):
                            payload = event.args or {}
                            kpi_id = int(payload.get('id') or 0)
                            value = 1 if bool(payload.get('value')) else 0
                            if not kpi_id:
                                return
                            if actualizar_dashboard_principal_kpi:
                                ok, message = actualizar_dashboard_principal_kpi(kpi_id, value)
                            else:
                                ok, message = False, 'No se encontró función para actualizar dashboard principal.'
                            ui.notify(fix_text(message), type='positive' if ok else 'negative')
                            if ok:
                                ui.navigate.to('/sistema-gestion/kpis')

                        table.on('toggle_dashboard_principal', _on_toggle_dashboard_principal)
                with ui.tab_panel(groups_tab).classes('px-0'):
                    grupos_actuales = []
                    if obtener_grupos_kpi_empresa:
                        grupos_actuales = list(obtener_grupos_kpi_empresa(int(selected_company_id)))
                    grupos_model = sorted(set(grupos_actuales), key=lambda x: x.lower())

                    with ui.card().classes('ideas-panel w-full mt-4'):
                        ui.label('Grupos y Reuniones').classes('ideas-section-title')
                        ui.label('Crea grupos y navega por tabs iconadas para ver KPI ordenados por reunión.').classes('ideas-section-note')
                        def open_create_group_dialog() -> None:
                            with ui.dialog() as create_dialog, ui.card().classes('w-[520px] max-w-[94vw] p-5'):
                                ui.label('Crear grupo').classes('text-lg font-bold text-slate-900')
                                nuevo_grupo = ui.input('Nombre del grupo').classes('w-full mt-2').props('outlined autofocus')

                                def create_group_tabs() -> None:
                                    name = str(nuevo_grupo.value or '').strip()
                                    if not name:
                                        ui.notify('Ingresa un nombre de grupo.', type='warning')
                                        return
                                    if not crear_grupo_kpi_empresa:
                                        ui.notify('No se encontró función para crear grupos.', type='negative')
                                        return
                                    ok, message = crear_grupo_kpi_empresa(int(selected_company_id), name)
                                    ui.notify(fix_text(message), type='positive' if ok else 'warning')
                                    if not ok:
                                        return
                                    create_dialog.close()
                                    ui.run_javascript('window.location.reload()')

                                with ui.row().classes('w-full justify-end gap-2 mt-3'):
                                    ui.button('Cancelar', on_click=create_dialog.close).props('flat')
                                    ui.button('Crear', icon='add', on_click=create_group_tabs).props('unelevated color=primary')
                            create_dialog.open()

                        with ui.row().classes('w-full justify-end mt-2'):
                            ui.button('Crear grupo', icon='add', on_click=open_create_group_dialog).props('unelevated color=primary')

                        def open_group_editor(group_name: str) -> None:
                            with ui.dialog() as dialog, ui.card().classes('w-[920px] max-w-[96vw] p-5'):
                                ui.label(f'Editar grupo: {group_name}').classes('text-lg font-bold')
                                ui.label('Selecciona KPI y define orden para esta reunión.').classes('ideas-section-note')
                                with ui.column().classes('w-full gap-2 mt-3'):
                                    for item in kpis:
                                        raw = str(item.get('grupos_personalizados') or '').strip()
                                        parsed = []
                                        if raw:
                                            try:
                                                candidate = json.loads(raw)
                                                if isinstance(candidate, list):
                                                    parsed = [entry for entry in candidate if isinstance(entry, dict)]
                                            except Exception:
                                                parsed = []
                                        existing = next((entry for entry in parsed if str(entry.get('grupo') or '').strip().lower() == group_name.lower()), None)
                                        included = existing is not None
                                        order_value = int(existing.get('orden') or 1) if existing else 1
                                        with ui.row().classes('w-full items-center justify-between gap-3 py-2 border-b border-slate-100'):
                                            with ui.column().classes('gap-0'):
                                                ui.label(fix_text(item.get('nombre') or 'KPI')).classes('font-semibold text-slate-900')
                                                ui.label(fix_text(item.get('proceso_nombre') or 'Sin proceso')).classes('text-xs text-slate-500')
                                            include_toggle = ui.switch('Incluir', value=included).props('dense')
                                            order_input = ui.number('Orden', value=order_value, min=1, step=1).classes('w-[110px]').props('outlined dense')

                                            def persist_group_state(kpi_id=int(item.get('id') or 0), target_group=group_name, toggle=include_toggle, order_field=order_input):
                                                if not kpi_id or not actualizar_grupos_personalizados_kpi:
                                                    return
                                                row = obtener_kpi_detalle(kpi_id)
                                                if not row:
                                                    return
                                                current_raw = str(row.get('grupos_personalizados') or '').strip()
                                                current = []
                                                if current_raw:
                                                    try:
                                                        loaded = json.loads(current_raw)
                                                        if isinstance(loaded, list):
                                                            current = [entry for entry in loaded if isinstance(entry, dict)]
                                                    except Exception:
                                                        current = []
                                                current = [entry for entry in current if str(entry.get('grupo') or '').strip().lower() != target_group.lower()]
                                                if bool(toggle.value):
                                                    current.append({'grupo': target_group, 'orden': int(order_field.value or 1)})
                                                current = sorted(current, key=lambda entry: (int(entry.get('orden') or 9999), str(entry.get('grupo') or '').lower()))
                                                ok, msg = actualizar_grupos_personalizados_kpi(kpi_id, current)
                                                ui.notify(fix_text(msg), type='positive' if ok else 'negative')

                                            include_toggle.on_value_change(lambda _e, fn=persist_group_state: fn())
                                            order_input.on_value_change(lambda _e, fn=persist_group_state: fn())
                                with ui.row().classes('w-full justify-end mt-3'):
                                    ui.button('Cerrar', on_click=lambda: (dialog.close(), ui.run_javascript('window.location.reload()'))).props('unelevated color=primary')
                            dialog.open()

                        def open_group_dashboard(group_name: str) -> None:
                            selected_kpis = []
                            for item in kpis:
                                raw = str(item.get('grupos_personalizados') or '').strip()
                                parsed = []
                                if raw:
                                    try:
                                        candidate = json.loads(raw)
                                        if isinstance(candidate, list):
                                            parsed = [entry for entry in candidate if isinstance(entry, dict)]
                                    except Exception:
                                        parsed = []
                                existing = next((entry for entry in parsed if str(entry.get('grupo') or '').strip().lower() == group_name.lower()), None)
                                if existing:
                                    selected_kpis.append((int(existing.get('orden') or 9999), item))
                            selected_kpis = [item for _order, item in sorted(selected_kpis, key=lambda row: row[0])]
                            if not selected_kpis:
                                ui.notify('Este grupo no tiene KPI seleccionados.', type='warning')
                                return

                            fullscreen_id = f'group-dashboard-{int(selected_company_id)}-{abs(hash(group_name)) % 1000000}'
                            with ui.dialog() as dialog, ui.card().classes('w-[1180px] max-w-[97vw] p-5'):
                                with ui.row().classes('w-full items-center justify-between'):
                                    with ui.column().classes('gap-0'):
                                        ui.label(f'Dashboard · {group_name}').classes('text-xl font-bold text-slate-900')
                                        ui.label('Vista consolidada de los KPI seleccionados para esta reunión.').classes('ideas-section-note')
                                    ui.button(
                                        'Pantalla completa',
                                        icon='fullscreen',
                                        on_click=lambda fid=fullscreen_id: ui.run_javascript(
                                            f"""
                                            const el = document.getElementById('{fid}');
                                            if (!el) return;
                                            if (document.fullscreenElement) {{
                                                document.exitFullscreen();
                                            }} else {{
                                                el.requestFullscreen();
                                            }}
                                            """
                                        ),
                                    ).props('outline color=secondary')
                                with ui.element('div').props(f'id={fullscreen_id}').classes('w-full'):
                                    with ui.grid(columns=2).classes('w-full gap-4 mt-3'):
                                        for item in selected_kpis:
                                            with ui.card().classes('ideas-panel p-4'):
                                                ui.label(fix_text(item.get('nombre') or 'KPI')).classes('font-bold text-slate-900')
                                                ui.label(fix_text(item.get('proceso_nombre') or 'Sin proceso')).classes('text-xs text-slate-500')
                                                ui.plotly(
                                                    generar_grafico_kpi(
                                                        item,
                                                        go,
                                                        'Mensual',
                                                        month_key='ene',
                                                        year_key='2026',
                                                        chart_type_override=None,
                                                    )
                                                ).classes('w-full mt-2')
                                with ui.row().classes('w-full justify-end mt-3'):
                                    ui.button('Cerrar', on_click=dialog.close).props('unelevated color=primary')
                            dialog.open()

                        if grupos_model:
                            reunion_tabs_map = {}
                            with ui.tabs().classes('w-full mt-4') as reunion_tabs:
                                for group_name in grupos_model:
                                    reunion_tabs_map[group_name] = ui.tab(group_name, icon='trending_up').props('no-caps')
                            with ui.tab_panels(reunion_tabs, value=reunion_tabs_map[grupos_model[0]]).classes('w-full bg-transparent'):
                                for group_name in grupos_model:
                                    with ui.tab_panel(reunion_tabs_map[group_name]).classes('px-0'):
                                        group_rows = []
                                        for item in kpis:
                                            raw = str(item.get('grupos_personalizados') or '').strip()
                                            parsed = []
                                            if raw:
                                                try:
                                                    candidate = json.loads(raw)
                                                    if isinstance(candidate, list):
                                                        parsed = [entry for entry in candidate if isinstance(entry, dict)]
                                                except Exception:
                                                    parsed = []
                                            existing = next((entry for entry in parsed if str(entry.get('grupo') or '').strip().lower() == group_name.lower()), None)
                                            if not existing:
                                                continue
                                            group_rows.append({
                                                'orden': int(existing.get('orden') or 9999),
                                                'nombre': fix_text(item.get('nombre') or 'KPI'),
                                                'proceso': fix_text(item.get('proceso_nombre') or 'Sin proceso'),
                                                'unidad': fix_text(item.get('unidad') or ''),
                                                'responsable': fix_text(item.get('responsable') or 'Sin responsable'),
                                                'ytd': _format_number(_calc_ytd(item)),
                                            })
                                        group_rows = sorted(group_rows, key=lambda row: (int(row['orden']), row['nombre'].lower()))
                                        if not group_rows:
                                            ui.label('No hay KPI asignados a este grupo.').classes('text-slate-500 mt-3')
                                        else:
                                            ui.table(
                                                columns=[
                                                    {'name': 'orden', 'label': 'Orden', 'field': 'orden', 'align': 'left'},
                                                    {'name': 'nombre', 'label': 'KPI', 'field': 'nombre', 'align': 'left'},
                                                    {'name': 'proceso', 'label': 'Proceso', 'field': 'proceso', 'align': 'left'},
                                                    {'name': 'unidad', 'label': 'Unidad', 'field': 'unidad', 'align': 'left'},
                                                    {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                                                    {'name': 'ytd', 'label': 'YTD', 'field': 'ytd', 'align': 'left'},
                                                ],
                                                rows=group_rows,
                                                row_key='nombre',
                                                pagination=0,
                                            ).classes('w-full mt-3').props('flat bordered dense wrap-cells')
                                        with ui.row().classes('w-full justify-end mt-2'):
                                            ui.button('Ver Dashboard', icon='dashboard', on_click=lambda g=group_name: open_group_dashboard(g)).props('flat color=secondary')
                                            ui.button('Editar grupo', icon='tune', on_click=lambda g=group_name: open_group_editor(g)).props('outline color=primary')
                        else:
                            ui.label('Aún no hay grupos creados.').classes('text-slate-500 mt-4')

                    if False:
                        _legacy_groups_block_disabled = True
                        ui.label('Grupos de Dashboard').classes('ideas-section-title')
                        ui.label('Crea grupos personalizados y define qué KPIs se incluyen en cada reunión.').classes('ideas-section-note')

                        nuevo_grupo = ui.input('Nombre del grupo (Ej: Reunión de Producción)').classes('w-full mt-2').props('outlined')

                        @ui.refreshable
                        def render_groups() -> None:
                            with ui.column().classes('w-full gap-3 mt-4'):
                                for group_name in grupos_model:
                                    with ui.expansion(group_name, icon='groups').classes('ideas-panel w-full'):
                                        for item in kpis:
                                            raw = str(item.get('grupos_personalizados') or '').strip()
                                            parsed = []
                                            if raw:
                                                try:
                                                    candidate = json.loads(raw)
                                                    if isinstance(candidate, list):
                                                        parsed = [entry for entry in candidate if isinstance(entry, dict)]
                                                except Exception:
                                                    parsed = []

                                            existing = next((entry for entry in parsed if str(entry.get('grupo') or '').strip().lower() == group_name.lower()), None)
                                            included = existing is not None
                                            order_value = int(existing.get('orden') or 1) if existing else 1

                                            with ui.row().classes('w-full items-center justify-between gap-3 py-2 border-b border-slate-100'):
                                                with ui.column().classes('gap-0'):
                                                    ui.label(fix_text(item.get('nombre') or 'KPI')).classes('font-semibold text-slate-900')
                                                    ui.label(f"{fix_text(item.get('unidad') or '')} · Responsable: {fix_text(item.get('responsable') or 'Sin responsable')}").classes('text-xs text-slate-500')

                                                include_toggle = ui.switch('Incluir', value=included).props('dense')
                                                order_input = ui.number('Orden', value=order_value, min=1, step=1).classes('w-[110px]').props('outlined dense')

                                                def persist_group_state(kpi_id=int(item.get('id') or 0), target_group=group_name, toggle=include_toggle, order_field=order_input):
                                                    if not kpi_id or not actualizar_grupos_personalizados_kpi:
                                                        return
                                                    row = obtener_kpi_detalle(kpi_id)
                                                    if not row:
                                                        return
                                                    current_raw = str(row.get('grupos_personalizados') or '').strip()
                                                    current = []
                                                    if current_raw:
                                                        try:
                                                            loaded = json.loads(current_raw)
                                                            if isinstance(loaded, list):
                                                                current = [entry for entry in loaded if isinstance(entry, dict)]
                                                        except Exception:
                                                            current = []
                                                    current = [entry for entry in current if str(entry.get('grupo') or '').strip().lower() != target_group.lower()]
                                                    if bool(toggle.value):
                                                        current.append({'grupo': target_group, 'orden': int(order_field.value or 1)})
                                                    current = sorted(current, key=lambda entry: (int(entry.get('orden') or 9999), str(entry.get('grupo') or '').lower()))
                                                    ok, msg = actualizar_grupos_personalizados_kpi(kpi_id, current)
                                                    ui.notify(fix_text(msg), type='positive' if ok else 'negative')
                                                    if ok:
                                                        ui.navigate.to('/sistema-gestion/kpis')

                                                include_toggle.on_value_change(lambda _e, fn=persist_group_state: fn())
                                                order_input.on_value_change(lambda _e, fn=persist_group_state: fn())

                        def create_group() -> None:
                            name = str(nuevo_grupo.value or '').strip()
                            if not name:
                                ui.notify('Ingresa un nombre de grupo.', type='warning')
                                return
                            if name.lower() in {g.lower() for g in grupos_model}:
                                ui.notify('Ese grupo ya existe.', type='warning')
                                return
                            grupos_model.append(name)
                            grupos_model.sort(key=lambda g: g.lower())
                            nuevo_grupo.value = ''
                            render_groups.refresh()

                        with ui.row().classes('w-full justify-end mt-2'):
                            ui.button('Crear Grupo', icon='add', on_click=create_group).props('unelevated color=primary')
                        render_groups()
            return

            with ui.grid(columns=2).classes('ideas-grid-2 w-full mt-4'):
                for kpi in kpis:
                    ytd_value = _calc_ytd(kpi)
                    proceso_nombre = fix_text(kpi.get('proceso_nombre') or 'Sin proceso')
                    comentario = fix_text(kpi.get('comentarios_desvio') or '')
                    with ui.card().classes('ideas-panel w-full'):
                        with ui.row().classes('w-full justify-between items-start gap-3'):
                            with ui.column().classes('gap-1'):
                                ui.label(fix_text(kpi.get('nombre') or 'KPI sin nombre')).classes('text-xl font-bold text-slate-900')
                                ui.badge(proceso_nombre, color='blue-grey').classes('px-3 py-2')
                            with ui.row().classes('items-center gap-2'):
                                ui.button(icon='edit_calendar', on_click=lambda row=kpi: _show_months_dialog(row)).props('flat round color=primary')
                                ui.button(icon='delete', on_click=lambda row_id=int(kpi['id']): confirm_delete_kpi(row_id)).props('flat round color=negative')

                        if _uses_ytd(kpi):
                            ui.html(
                                f'''
                                <div style="margin-top:14px;padding:16px;border-radius:20px;background:linear-gradient(135deg, rgba(31,126,214,.10), rgba(15,143,97,.10));border:1px solid rgba(31,126,214,.18);">
                                    <div style="font-size:.72rem;font-weight:800;letter-spacing:.10em;text-transform:uppercase;color:#475569;">YTD</div>
                                    <div style="font-size:2.15rem;font-weight:800;color:#0f172a;line-height:1;margin-top:6px;">{_format_number(ytd_value)} <span style="font-size:1rem;color:#64748b;">{fix_text(kpi.get('unidad') or '')}</span></div>
                                    <div style="margin-top:6px;color:#64748b;">{fix_text(kpi.get('tipo_ytd') or 'Automático')}</div>
                                </div>
                                '''
                            )

                        views = _available_views(kpi)
                        default_view = 'Mensual' if 'Mensual' in views else views[0]
                        vista_chart = ui.select(views, value=default_view, label='Vista del gráfico').classes('w-[220px] mt-2').props('outlined dense')
                        @ui.refreshable
                        def _render_chart():
                            ui.plotly(generar_grafico_kpi(kpi, go, vista_chart.value or 'Mensual')).classes('w-full mt-2')
                        _render_chart()
                        vista_chart.on_value_change(lambda _e: _render_chart.refresh())

                        with ui.row().classes('w-full justify-between text-sm text-slate-500 mt-1'):
                            ui.label(f"Objetivo: {_format_number(kpi.get('objetivo'))} {fix_text(kpi.get('unidad') or '')}")
                            ui.label(f"Ult. actualización: {fix_text(kpi.get('fecha_actualizacion') or 'Pendiente')}")

                        if comentario:
                            with ui.element('div').classes('w-full mt-3 bg-red-50 text-red-900 border border-red-200 rounded-xl p-4'):
                                ui.label('Alerta de Desvío:').classes('font-bold')
                                ui.label(comentario).classes('mt-1')
            return

            with_meta = sum(1 for item in kpis if str(item.get('meta') or '').strip())
            with_owner = sum(1 for item in kpis if str(item.get('responsable') or '').strip())
            negative_trend = sum(1 for item in kpis if fix_text(item.get('tendencia') or '').strip().lower() == 'negativa')

            ui.html(
                f'''
                <div class="ideas-workspace-banner w-full mt-4">
                    <div class="eyebrow">Sistema de gestion · KPI</div>
                    <div class="headline">{company_name}</div>
                    <div class="support">
                        Este modulo concentra los indicadores ejecutivos y operativos de la empresa activa, con estructura base para metas, frecuencia, responsables y seguimiento.
                    </div>
                </div>
                '''
            )

            render_metrics(
                ui.row().classes('w-full mt-4'),
                [
                    ('KPI activos', str(len(kpis)), 'Indicadores actualmente registrados para la empresa seleccionada.'),
                    ('Con meta definida', str(with_meta), 'KPI que ya cuentan con una meta explicitada.'),
                    ('Con responsable', str(with_owner), 'Indicadores con dueño claro para el seguimiento.'),
                    ('Tendencia negativa', str(negative_trend), 'Alertas visibles para foco de gestion inmediato.'),
                ],
            )

            ui.html(
                f'''<div class="ideas-grid-3" style="margin-top:18px;">
                {quick_card('Empresa activa', company_name, 'Contexto actual sobre el que se construye el tablero de indicadores.')}
                {quick_card('Certificaciones', certifications_summary(company), 'Util para alinear indicadores con exigencias del sistema de gestion.')}
                {quick_card('Rubro', fix_text(company.get('rubro', 'Sin definir')) if company else 'Sin definir', 'Ayuda a orientar categorias, fuentes y metas del modulo KPI.')}
                </div>'''
            )

            with ui.card().classes('ideas-panel w-full mt-6'):
                ui.label('Alta rapida de KPI').classes('ideas-section-title')
                ui.label('Registra un nuevo indicador base y despues podras profundizarlo o editarlo en la misma vista.').classes('ideas-section-note')
                with ui.row().classes('w-full gap-4 mt-3'):
                    quick_name = ui.input('Nombre del KPI').classes('col').props('outlined')
                    quick_code = ui.input('Codigo').classes('col').props('outlined')
                    quick_category = ui.select(KPI_CATEGORIES, label='Categoria').classes('col').props('outlined')

                def save_quick_kpi() -> None:
                    ok, message = agregar_kpi_empresa(
                        int(selected_company_id),
                        quick_name.value or '',
                        quick_code.value or '',
                        quick_category.value or '',
                    )
                    ui.notify(fix_text(message), type='positive' if ok else 'negative')
                    if ok:
                        ui.navigate.to('/sistema-gestion/kpis')

                with ui.row().classes('w-full justify-end mt-3'):
                    ui.button('Agregar KPI', icon='add', on_click=save_quick_kpi).props('unelevated color=primary')

            with ui.row().classes('w-full justify-between items-center mt-6'):
                with ui.column().classes('gap-0'):
                    ui.label('Listado de KPI').classes('ideas-section-title')
                    ui.label('Gestiona el set de indicadores de la empresa activa desde una sola vista ejecutiva.').classes('ideas-section-note')
                ui.button(
                    'Nuevo KPI completo',
                    icon='add_chart',
                    on_click=lambda: _show_kpi_editor(
                        ui=ui,
                        fix_text_fn=fix_text,
                        row=None,
                        company_id=int(selected_company_id),
                        agregar_kpi_empresa_fn=agregar_kpi_empresa,
                        actualizar_kpi_fn=actualizar_kpi,
                    ),
                ).props('unelevated color=secondary')

            table_rows = _build_kpi_rows(kpis, fix_text)
            table = ui.table(
                columns=[
                    {'name': 'codigo', 'label': 'Codigo', 'field': 'codigo', 'align': 'left'},
                    {'name': 'nombre', 'label': 'KPI', 'field': 'nombre', 'align': 'left'},
                    {'name': 'categoria', 'label': 'Categoria', 'field': 'categoria', 'align': 'left'},
                    {'name': 'meta', 'label': 'Meta', 'field': 'meta', 'align': 'left'},
                    {'name': 'frecuencia', 'label': 'Frecuencia', 'field': 'frecuencia', 'align': 'left'},
                    {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'},
                    {'name': 'valor_actual', 'label': 'Valor actual', 'field': 'valor_actual', 'align': 'left'},
                    {'name': 'tendencia', 'label': 'Tendencia', 'field': 'tendencia', 'align': 'left'},
                    {'name': 'fecha_actualizacion', 'label': 'Ult. actualizacion', 'field': 'fecha_actualizacion', 'align': 'left'},
                    {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'},
                ],
                rows=table_rows,
                row_key='id',
                pagination=10,
            ).classes('w-full ideas-card ideas-table p-3 mt-4')
            table.props('flat bordered')
            table.add_slot(
                'body-cell-acciones',
                '''
                <q-td :props="props">
                    <div class="row items-center no-wrap q-gutter-sm">
                        <q-btn flat round dense icon="edit" color="primary" @click="$parent.$emit('edit_kpi', props.row.id)" />
                        <q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_kpi', props.row.id)" />
                    </div>
                </q-td>
                ''',
            )

            def edit_kpi(kpi_id: int) -> None:
                row = obtener_kpi_detalle(int(kpi_id))
                if not row:
                    ui.notify('Ese KPI ya no existe.', type='warning')
                    return
                _show_kpi_editor(
                    ui=ui,
                    fix_text_fn=fix_text,
                    row=row,
                    company_id=int(selected_company_id),
                    agregar_kpi_empresa_fn=agregar_kpi_empresa,
                    actualizar_kpi_fn=actualizar_kpi,
                )

            def confirm_delete_kpi(kpi_id: int) -> None:
                row = obtener_kpi_detalle(int(kpi_id))
                if not row:
                    ui.notify('Ese KPI ya no existe.', type='warning')
                    return
                with ui.dialog() as dialog, ui.card().classes('p-5 max-w-[560px]'):
                    ui.label('Eliminar KPI').classes('text-lg font-semibold')
                    ui.label(f"Se eliminara permanentemente el KPI {fix_text(row.get('nombre', ''))}. Esta accion no se puede deshacer.").classes('text-slate-600')
                    with ui.row().classes('w-full justify-end gap-2 mt-3'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat')

                        def do_delete() -> None:
                            eliminar_kpi(int(kpi_id))
                            dialog.close()
                            ui.notify('KPI eliminado correctamente.', type='positive')
                            ui.navigate.to('/sistema-gestion/kpis')

                        ui.button('Eliminar', color='negative', on_click=do_delete)
                dialog.open()

            table.on('edit_kpi', lambda event: edit_kpi(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el KPI seleccionado.', type='warning'))
            table.on('delete_kpi', lambda event: confirm_delete_kpi(_extract_int(event.args)) if _extract_int(event.args) is not None else ui.notify('No se pudo identificar el KPI seleccionado.', type='warning'))
