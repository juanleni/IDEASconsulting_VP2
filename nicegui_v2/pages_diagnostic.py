from __future__ import annotations


def register_diagnostic_pages(ui, app, deps: dict) -> None:
    pd, go = deps['pd'], deps['go']
    shell, ensure_platform_access = deps['shell'], deps['ensure_platform_access']
    obtener_empresas, obtener_empresa_detalle, guardar_empresa = deps['obtener_empresas'], deps['obtener_empresa_detalle'], deps['guardar_empresa']
    go_to_management_workspace, set_selection = deps['go_to_management_workspace'], deps['set_selection']
    leer_diagnostico_excel, grouped_questions, load_criteria = deps['leer_diagnostico_excel'], deps['grouped_questions'], deps['load_criteria']
    company_options, current_selection = deps['company_options'], deps['current_selection']
    diagnosis_record, diagnosis_response_dicts, split_evidence_values = deps['diagnosis_record'], deps['diagnosis_response_dicts'], deps['split_evidence_values']
    fix_text, certifications_summary = deps['fix_text'], deps['certifications_summary']
    actualizar_diagnostico, guardar_diagnostico = deps['actualizar_diagnostico'], deps['guardar_diagnostico']
    obtener_nivel, obtener_conclusion = deps['obtener_nivel'], deps['obtener_conclusion']
    diagnosis_rows, diagnosis_badge_style, diagnosis_options = deps['diagnosis_rows'], deps['diagnosis_badge_style'], deps['diagnosis_options']
    build_eje_scores, build_plan, short_axis_label = deps['build_eje_scores'], deps['build_plan'], deps['short_axis_label']
    obtener_mensaje_direccion, quick_card, obtener_prioridad_recomendada = deps['obtener_mensaje_direccion'], deps['quick_card'], deps['obtener_prioridad_recomendada']
    start_edit, render_metrics, eliminar_diagnostico = deps['start_edit'], deps['render_metrics'], deps['eliminar_diagnostico']

    @ui.page('/empresas')
    def companies_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Empresas')
        companies = [{'razon_social': fix_text(name), 'id': company_id, **(obtener_empresa_detalle(company_id) or {})} for company_id, name in obtener_empresas()]
        with shell_container:
            ui.label('Base de empresas').classes('ideas-kicker')
            ui.label('Alta y administración del universo consultivo.').classes('text-3xl font-bold text-slate-900')
            ui.label('Registrá la ficha institucional de cada empresa con el nivel de detalle necesario para los reportes ejecutivos.').classes('ideas-subtitle mb-4')
            with ui.card().classes('ideas-panel w-full'):
                razon_social = ui.input('Razón social').classes('w-full')
                with ui.row().classes('w-full gap-4'):
                    ubicacion = ui.input('Ubicación').classes('col'); rubro = ui.input('Rubro').classes('col'); cantidad_empleados = ui.number('Cantidad de empleados', value=0, min=0, precision=0).classes('col')
                ui.label('Persona de contacto').classes('text-lg font-semibold text-slate-800 mt-2')
                with ui.row().classes('w-full gap-4'):
                    contacto_nombre = ui.input('Nombre').classes('col'); contacto_correo = ui.input('Correo').classes('col')
                with ui.row().classes('w-full gap-4'):
                    contacto_telefono = ui.input('Teléfono').classes('col'); contacto_posicion = ui.input('Posición').classes('col')
                ui.label('Certificaciones').classes('text-lg font-semibold text-slate-800 mt-2')
                with ui.row().classes('w-full gap-4'):
                    cert_9001 = ui.switch('ISO 9001', value=False); cert_14001 = ui.switch('ISO 14001', value=False); cert_45001 = ui.switch('ISO 45001', value=False); cert_iatf = ui.switch('IATF', value=False)
                def save_company() -> None:
                    payload = {'razon_social': razon_social.value or '', 'ubicacion': ubicacion.value or '', 'contacto_nombre': contacto_nombre.value or '', 'contacto_correo': contacto_correo.value or '', 'contacto_telefono': contacto_telefono.value or '', 'contacto_posicion': contacto_posicion.value or '', 'rubro': rubro.value or '', 'cantidad_empleados': int(cantidad_empleados.value or 0), 'cert_iso_9001': 'Sí' if cert_9001.value else 'No', 'cert_iso_14001': 'Sí' if cert_14001.value else 'No', 'cert_iso_45001': 'Sí' if cert_45001.value else 'No', 'cert_iatf': 'Sí' if cert_iatf.value else 'No'}
                    ok, message = guardar_empresa(payload); ui.notify(fix_text(message), type='positive' if ok else 'negative')
                    if ok: ui.navigate.to('/empresas')
                with ui.row().classes('w-full justify-end mt-3'):
                    ui.button('Guardar empresa', icon='save', on_click=save_company).props('unelevated color=primary')
            table_rows = [{'id': item['id'], 'razon_social': item['razon_social'], 'ubicacion': fix_text(item.get('ubicacion', '')), 'rubro': fix_text(item.get('rubro', '')), 'empleados': item.get('cantidad_empleados') or 0, 'contacto': fix_text(item.get('contacto_nombre', '')), 'certificaciones': certifications_summary(item), 'acciones': ''} for item in companies]
            table = ui.table(columns=[{'name': 'razon_social', 'label': 'Razón social', 'field': 'razon_social', 'align': 'left'}, {'name': 'ubicacion', 'label': 'Ubicación', 'field': 'ubicacion', 'align': 'left'}, {'name': 'rubro', 'label': 'Rubro', 'field': 'rubro', 'align': 'left'}, {'name': 'empleados', 'label': 'Empleados', 'field': 'empleados', 'align': 'right'}, {'name': 'contacto', 'label': 'Contacto', 'field': 'contacto', 'align': 'left'}, {'name': 'certificaciones', 'label': 'Certificaciones', 'field': 'certificaciones', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}], rows=table_rows, row_key='id', pagination=8).classes('w-full ideas-card ideas-table p-3 mt-6')
            table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="account_tree" color="primary" @click="$parent.$emit('open_workspace', props.row.id)" /></div></q-td>''')
            table.on('open_workspace', lambda event: go_to_management_workspace(int(event.args), set_selection))

    @ui.page('/diagnostico')
    def diagnostic_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Nuevo Diagnóstico'); df_base = leer_diagnostico_excel().copy(); grouped = grouped_questions(df_base); criteria, regla = load_criteria(); company_map = company_options()
        score_labels = {1: '1 · Inicial', 2: '2 · Parcial', 3: '3 · Implementado', 4: '4 · Estandarizado'}
        edit_id, duplicate_id = app.storage.user.get('edit_diag_id'), app.storage.user.get('duplicate_diag_id')
        preload_id = int(edit_id or duplicate_id) if (edit_id or duplicate_id) else None; preload = diagnosis_record(preload_id); preload_responses = diagnosis_response_dicts(preload_id); preload_map = {(row['eje'], row['pregunta']): row for row in preload_responses}
        with shell_container:
            ui.label('Nuevo diagnóstico').classes('ideas-kicker'); ui.label('Captura estructurada para análisis ejecutivo.').classes('text-3xl font-bold text-slate-900'); ui.label('Registrá cada eje con una evaluación consistente y evidencia asociada para sostener la lectura consultiva posterior.').classes('ideas-subtitle')
            if preload and edit_id: ui.html(f'<div class="ideas-mode-banner">Modo edición<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Estás actualizando un diagnóstico ya registrado.</div>')
            elif preload and duplicate_id: ui.html(f'<div class="ideas-mode-banner">Duplicar como nuevo<strong>{preload["empresa"]} · {preload["fecha"]}</strong>Tomás un corte previo como base para crear una nueva evaluación.</div>')
            with ui.card().classes('ideas-panel w-full mt-4'):
                guide_html = ''.join(f'''<div class="ideas-score-item"><div class="badge">{int(item['escala'])}</div><div style="margin-top:10px;font-weight:800;color:#0f172a;">{fix_text(item['nivel'])}</div><div style="margin-top:8px;color:#475569;line-height:1.55;">{fix_text(item['resumen'])}</div></div>''' for item in criteria)
                ui.label('Criterios de puntuación').classes('text-lg font-semibold text-slate-900'); ui.html(f'<div class="ideas-score-guide mt-3">{guide_html}</div>'); ui.label(f'Regla de evidencia: {fix_text(regla)}').classes('text-sm text-amber-700 mt-3')
            default_company = preload['empresa_id'] if preload else (current_selection()[0] or None); company_select = ui.select(company_map, value=default_company, label='Empresa').classes('w-full mt-5').props('outlined')
            response_inputs, evidence_inputs, evidence_containers, observation_inputs = {}, {}, {}, {}
            def ensure_evidence_fields(key):
                fields = evidence_inputs[key]; values = [fix_text(field.value).strip() for field in fields]
                if values and values[-1] != '':
                    with evidence_containers[key]: new_field = ui.input(f'Evidencia {len(fields) + 1}').classes('w-full').props('outlined')
                    fields.append(new_field); new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key)); return
                for index in reversed([i for i, value in enumerate(values[:-1]) if value == '']): fields.pop(index).delete()
                if not fields:
                    with evidence_containers[key]: new_field = ui.input('Evidencia 1').classes('w-full').props('outlined')
                    fields.append(new_field); new_field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
            for eje, questions in grouped.items():
                with ui.expansion(fix_text(eje), icon='schema').classes('w-full ideas-card mt-4'):
                    for question in questions:
                        key, existing = (eje, question), preload_map.get((eje, question), {})
                        with ui.card().classes('ideas-soft w-full p-4 mb-3'):
                            ui.label(question).classes('text-base font-semibold text-slate-900')
                            response_inputs[key] = ui.select({value: f"{label} · {fix_text(next((c['resumen'] for c in criteria if int(c['escala']) == value), ''))}" for value, label in score_labels.items()}, value=int(existing.get('respuesta', 3)), label='Puntaje').classes('w-full mt-3').props('outlined')
                            with ui.row().classes('w-full gap-4 mt-2'):
                                evidence_containers[key] = ui.column().classes('col w-full gap-2'); observation_inputs[key] = ui.textarea('Observación').classes('col w-full').props('outlined autogrow')
                            evidence_inputs[key] = []; preload_evidences = split_evidence_values(existing.get('evidencia', ''))
                            with evidence_containers[key]:
                                for idx, evidence_value in enumerate(preload_evidences, start=1):
                                    field = ui.input(f'Evidencia {idx}').classes('w-full').props('outlined'); field.value = evidence_value; evidence_inputs[key].append(field)
                                if not preload_evidences or preload_evidences[-1].strip() != '':
                                    evidence_inputs[key].append(ui.input(f'Evidencia {len(evidence_inputs[key]) + 1}').classes('w-full').props('outlined'))
                            for field in evidence_inputs[key]: field.on_value_change(lambda _e, current_key=key: ensure_evidence_fields(current_key))
                            ensure_evidence_fields(key); observation_inputs[key].value = existing.get('observacion', '')
            def save_diagnosis() -> None:
                if not company_select.value: ui.notify('Seleccioná una empresa antes de guardar.', type='warning'); return
                rows = [{'eje': eje, 'pregunta': question, 'respuesta': int(selector.value or 1), 'evidencia': ', '.join([fix_text(field.value).strip() for field in evidence_inputs[(eje, question)] if fix_text(field.value).strip()]), 'observacion': observation_inputs[(eje, question)].value or ''} for (eje, question), selector in response_inputs.items()]
                score = round(sum(item['respuesta'] for item in rows) / len(rows), 2) if rows else 0; nivel = obtener_nivel(score); conclusion = fix_text(obtener_conclusion(score)); empresa_id = int(company_select.value)
                if edit_id:
                    diag_id, _fecha, unchanged = actualizar_diagnostico(int(edit_id), empresa_id, score, nivel, conclusion, rows); ui.notify('No se detectaron cambios; el diagnóstico ya estaba actualizado.' if unchanged else 'Diagnóstico actualizado correctamente.', type='positive')
                else:
                    diag_id, _fecha, duplicated = guardar_diagnostico(empresa_id, score, nivel, conclusion, rows); ui.notify('Ese diagnóstico ya estaba guardado; se reutilizó el corte existente.' if duplicated else 'Diagnóstico guardado correctamente.', type='positive')
                app.storage.user['edit_diag_id'] = None; app.storage.user['duplicate_diag_id'] = None; set_selection(empresa_id, diag_id); ui.navigate.to('/resultados')
            with ui.row().classes('w-full justify-end gap-3 mt-6'):
                ui.button('Cancelar', icon='close', on_click=lambda: ui.navigate.to('/historial')).props('outline'); ui.button('Guardar diagnóstico', icon='save', on_click=save_diagnosis).props('unelevated color=primary')

    @ui.page('/resultados')
    def results_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Resultados'); empresa_id, diagnostico_id = current_selection(); companies = company_options()
        if not empresa_id and companies: empresa_id = next(iter(companies.keys()))
        diag_map = diagnosis_options(empresa_id)
        if not diagnostico_id and diag_map: diagnostico_id = next(iter(diag_map.keys()))
        if diagnostico_id: set_selection(empresa_id, diagnostico_id)
        with shell_container:
            ui.label('Resultados').classes('ideas-kicker'); ui.label('Lectura ejecutiva del diagnóstico seleccionado.').classes('text-3xl font-bold text-slate-900'); ui.label('Unificá score global, lectura por eje y oportunidades prioritarias en una vista de decisión rápida.').classes('ideas-subtitle mb-4')
            with ui.card().classes('ideas-panel w-full'):
                with ui.row().classes('w-full gap-4'):
                    company_select = ui.select(companies, value=empresa_id, label='Empresa').classes('col').props('outlined'); diagnosis_select = ui.select(diag_map, value=diagnostico_id, label='Diagnóstico').classes('col').props('outlined')
            company_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, None), ui.navigate.to('/resultados')))
            diagnosis_select.on_value_change(lambda _e: (set_selection(int(company_select.value) if company_select.value else None, int(diagnosis_select.value) if diagnosis_select.value else None), ui.navigate.to('/resultados')))
            selected = diagnosis_record(diagnostico_id)
            if not selected: ui.label('Todavía no hay un diagnóstico seleccionado para mostrar resultados.').classes('text-slate-500 mt-6'); return
            responses = diagnosis_response_dicts(diagnostico_id); df_resp, eje_scores_df = build_eje_scores(responses); company = obtener_empresa_detalle(selected['empresa_id']); plan_df = build_plan(df_resp, eje_scores_df); nivel = fix_text(selected['nivel'])
            ui.html(f'''<div class="ideas-result-banner mt-6"><div class="eyebrow">Resultado general</div><div class="headline">{selected['empresa']} · Nivel {nivel}</div><div class="support">{selected['fecha']} · {fix_text(obtener_mensaje_direccion(nivel))}</div></div>''')
            fig = go.Figure(go.Bar(x=eje_scores_df['RESPUESTA'], y=eje_scores_df['EJE'], orientation='h', marker_color='#1f7ed6', text=[f'{value:.2f}' for value in eje_scores_df['RESPUESTA']], textposition='outside')); fig.update_layout(height=430, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)')
            radar_base_labels = eje_scores_df['EJE'].tolist(); radar_labels = [short_axis_label(label) for label in radar_base_labels]; radar_values = eje_scores_df['RESPUESTA'].tolist()
            if radar_labels: radar_labels = radar_labels + [radar_labels[0]]; radar_values = radar_values + [radar_values[0]]
            radar = go.Figure(); radar.add_trace(go.Scatterpolar(r=radar_values, theta=radar_labels, fill='toself', line=dict(color='#0f8f61', width=3), fillcolor='rgba(15, 143, 97, 0.22)', name='Madurez por área')); radar.update_layout(height=430, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, range=[1, 4], tickvals=[1, 2, 3, 4], gridcolor='rgba(148,163,184,0.25)'), angularaxis=dict(gridcolor='rgba(148,163,184,0.18)', tickfont=dict(size=10))), showlegend=False)
            gap_values = [max(0, 4 - float(value)) for value in eje_scores_df['RESPUESTA'].tolist()]; gap_chart = go.Figure(go.Bar(x=gap_values, y=eje_scores_df['EJE'], orientation='h', marker_color='#f59e0b', text=[f'{value:.2f}' for value in gap_values], textposition='outside')); gap_chart.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis=dict(range=[0, 4], title='Brecha a estándar 4'), yaxis=dict(autorange='reversed'))
            score_distribution = pd.DataFrame({'Nivel': ['1', '2', '3', '4'], 'Cantidad': [int((df_resp['RESPUESTA'] == 1).sum()) if not df_resp.empty else 0, int((df_resp['RESPUESTA'] == 2).sum()) if not df_resp.empty else 0, int((df_resp['RESPUESTA'] == 3).sum()) if not df_resp.empty else 0, int((df_resp['RESPUESTA'] == 4).sum()) if not df_resp.empty else 0]})
            distribution_chart = go.Figure(go.Bar(x=score_distribution['Nivel'], y=score_distribution['Cantidad'], marker_color=['#dc2626', '#f59e0b', '#38bdf8', '#16a34a'], text=score_distribution['Cantidad'], textposition='outside')); distribution_chart.update_layout(height=360, margin=dict(l=20, r=20, t=20, b=20), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', xaxis_title='Puntaje', yaxis_title='Cantidad de respuestas')
            with ui.tabs().classes('w-full mt-6') as tabs:
                summary_tab = ui.tab('Resumen ejecutivo', icon='dashboard'); plan_tab = ui.tab('Plan de acción', icon='task_alt')
            with ui.tab_panels(tabs, value=summary_tab).classes('w-full bg-transparent'):
                with ui.tab_panel(summary_tab).classes('px-0'):
                    ui.html(f'''<div class="ideas-grid-3">{quick_card('Empresa', selected['empresa'], 'Corte seleccionado para lectura ejecutiva.')}{quick_card('Fecha del corte', selected['fecha'], 'Toma vigente dentro del historial registrado.')}{quick_card('Prioridad recomendada', fix_text(obtener_prioridad_recomendada(nivel)), 'Enfoque sugerido para dirección.')}</div>''')
                    with ui.row().classes('w-full gap-4 mt-6'):
                        with ui.card().classes('ideas-panel col'):
                            ui.label('Performance por área').classes('ideas-section-title'); ui.label('Comparativo visual de madurez por eje para detectar fortalezas y focos de intervención.').classes('ideas-section-note'); ui.plotly(fig).classes('w-full')
                        with ui.card().classes('ideas-panel col'):
                            ui.label('Radar de brechas por área').classes('ideas-section-title'); ui.label('Vista sintética para observar equilibrio, amplitud de capacidades y gaps entre ejes.').classes('ideas-section-note'); ui.plotly(radar).classes('w-full')
                            legend_rows = [{'sigla': short_axis_label(label), 'area': label} for label in radar_base_labels]; ui.table(columns=[{'name': 'sigla', 'label': 'Etiqueta', 'field': 'sigla', 'align': 'left'}, {'name': 'area', 'label': 'Área completa', 'field': 'area', 'align': 'left'}], rows=legend_rows, pagination=6).classes('w-full ideas-table mt-3')
                    with ui.row().classes('w-full gap-4 mt-4'):
                        with ui.card().classes('ideas-panel col'):
                            ui.label('Brecha a estándar objetivo').classes('ideas-section-title'); ui.label('Muestra en formato ejecutivo cuánto le falta a cada eje para alcanzar un nivel 4 estandarizado.').classes('ideas-section-note'); ui.plotly(gap_chart).classes('w-full')
                        with ui.card().classes('ideas-panel col'):
                            ui.label('Distribución de respuestas').classes('ideas-section-title'); ui.label('Resume la concentración del diagnóstico por nivel de cumplimiento.').classes('ideas-section-note'); ui.plotly(distribution_chart).classes('w-full')
                    with ui.row().classes('w-full gap-4 mt-4'):
                        with ui.card().classes('ideas-panel w-full'):
                            ui.label('Ficha ejecutiva').classes('ideas-section-title')
                            ui.label(f"Razón social: {fix_text(company.get('razon_social', selected['empresa'])) if company else selected['empresa']}").classes('text-slate-700'); ui.label(f"Ubicación: {fix_text(company.get('ubicacion', '')) if company else ''}").classes('text-slate-700'); ui.label(f"Rubro: {fix_text(company.get('rubro', '')) if company else ''}").classes('text-slate-700'); ui.label(f"Empleados: {company.get('cantidad_empleados', 0) if company else 0}").classes('text-slate-700'); ui.label(f"Certificaciones: {certifications_summary(company)}").classes('text-slate-700'); ui.separator().classes('my-3'); ui.label(fix_text(obtener_prioridad_recomendada(nivel))).classes('text-slate-800 font-medium')
                with ui.tab_panel(plan_tab).classes('px-0'):
                    ui.label('Plan de acción sugerido').classes('ideas-section-title'); ui.label('Incluye acciones prioritarias para respuestas de 2 o menos y oportunidades de mejora para respuestas de 3.').classes('ideas-section-note'); ui.table(columns=[{'name': 'categoria', 'label': 'Categoría', 'field': 'categoria', 'align': 'left'}, {'name': 'area', 'label': 'Área', 'field': 'area', 'align': 'left'}, {'name': 'prioridad', 'label': 'Prioridad', 'field': 'prioridad', 'align': 'left'}, {'name': 'responsable', 'label': 'Responsable', 'field': 'responsable', 'align': 'left'}, {'name': 'plazo', 'label': 'Plazo', 'field': 'plazo', 'align': 'left'}, {'name': 'impacto', 'label': 'Impacto', 'field': 'impacto', 'align': 'left'}, {'name': 'accion', 'label': 'Acción sugerida', 'field': 'accion', 'align': 'left'}], rows=plan_df.to_dict('records'), pagination=10).classes('w-full ideas-card ideas-table p-3 mt-3')
            with ui.row().classes('w-full justify-end gap-3 mt-6'):
                ui.button('Editar diagnóstico', icon='edit', on_click=lambda: (start_edit(int(diagnostico_id), duplicate=False), ui.navigate.to('/diagnostico'))).props('outline'); ui.button('Duplicar como nuevo', icon='content_copy', on_click=lambda: (start_edit(int(diagnostico_id), duplicate=True), ui.navigate.to('/diagnostico'))).props('unelevated color=primary')

    @ui.page('/historial')
    def history_page() -> None:
        if not ensure_platform_access(): return
        shell_container = shell('Historial'); rows = diagnosis_rows(); app.storage.user['history_selected_id'] = None
        with shell_container:
            ui.label('Historial').classes('ideas-kicker'); ui.label('Overview rápido de la base de diagnósticos.').classes('text-3xl font-bold text-slate-900'); ui.label('Consultá cada corte, actuá sobre el registro y accedé a la información relevante sin ruido visual.').classes('ideas-subtitle mb-4')
            empresas_con_evolucion = len({row['empresa'] for row in rows if sum(1 for item in rows if item['empresa'] == row['empresa']) > 1})
            render_metrics(ui.row().classes('w-full'), [('Empresas registradas', str(len({row['empresa_id'] for row in rows})), 'Universo visible en la base consultiva.'), ('Diagnósticos visibles', str(len(rows)), 'Cortes disponibles para consulta o edición.'), ('Empresas con evolución', str(empresas_con_evolucion), 'Casos con más de un corte registrado.')])
            columns = [{'name': 'empresa', 'label': 'Empresa', 'field': 'empresa', 'align': 'left'}, {'name': 'fecha', 'label': 'Fecha', 'field': 'fecha', 'align': 'left'}, {'name': 'score', 'label': 'Score', 'field': 'score', 'align': 'right'}, {'name': 'nivel', 'label': 'Nivel', 'field': 'nivel', 'align': 'left'}, {'name': 'acciones', 'label': 'Acciones', 'field': 'acciones', 'align': 'center'}]
            table_rows = [{'id': row['id'], 'empresa_id': row['empresa_id'], 'empresa': row['empresa'], 'fecha': row['fecha'], 'score': f"{row['score']:.2f}", 'nivel': row['nivel'], 'acciones': ''} for row in rows]
            table = ui.table(columns=columns, rows=table_rows, row_key='id', pagination=10).classes('w-full ideas-card ideas-table p-3 mt-4'); table.props('flat bordered')
            table.add_slot('body-cell-acciones', '''<q-td :props="props"><div class="row items-center no-wrap q-gutter-sm"><q-btn flat round dense icon="visibility" color="primary" @click="$parent.$emit('open_resultados', props.row.id)" /><q-btn flat round dense icon="edit" color="secondary" @click="$parent.$emit('edit_diag', props.row.id)" /><q-btn flat round dense icon="content_copy" color="amber-8" @click="$parent.$emit('duplicate_diag', props.row.id)" /><q-btn flat round dense icon="delete" color="negative" @click="$parent.$emit('delete_diag', props.row.id)" /></div></q-td>''')
            detail_card = ui.card().classes('ideas-panel w-full mt-4')
            def extract_diag_id(args):
                if args is None: return None
                if isinstance(args, dict):
                    if 'id' in args:
                        try: return int(args['id'])
                        except Exception: return None
                    if 'row' in args: return extract_diag_id(args['row'])
                    return None
                if isinstance(args, (list, tuple)):
                    for item in args:
                        diag_id = extract_diag_id(item)
                        if diag_id is not None: return diag_id
                    return None
                try: return int(args)
                except Exception: return None
            def render_detail(diag_id):
                detail_card.clear(); diag = diagnosis_record(diag_id) if diag_id else None
                if not diag:
                    with detail_card:
                        ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title'); ui.label('Haz click en una fila de la lista superior para visualizar aquí el resumen del diagnóstico y los datos de la empresa.').classes('text-slate-500'); ui.html('''<div class="ideas-grid-2" style="margin-top:18px;"><div class="ideas-quick-card"><div class="label">Ficha de empresa</div><div class="detail">Razón social: -</div><div class="detail">Ubicación: -</div><div class="detail">Rubro: -</div><div class="detail">Empleados: -</div></div><div class="ideas-quick-card"><div class="label">Resumen consultivo</div><div class="detail">Puntos fuertes: -</div><div class="detail">Áreas débiles: -</div><div class="detail">Contacto: -</div><div class="detail">Certificaciones: -</div></div></div>''')
                    return
                app.storage.user['history_selected_id'] = int(diag['id']); company = obtener_empresa_detalle(diag['empresa_id']); responses = diagnosis_response_dicts(diag['id']); df_resp = pd.DataFrame(responses)
                strengths = ', '.join(df_resp[df_resp['respuesta'] >= 3]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'; weaknesses = ', '.join(df_resp[df_resp['respuesta'] <= 2]['eje'].drop_duplicates().head(3).tolist()) if not df_resp.empty else 'Sin datos'
                with detail_card:
                    ui.label('Vista preliminar del diagnóstico seleccionado').classes('ideas-section-title'); ui.label(f"{diag['empresa']} · {diag['fecha']}").classes('text-slate-500'); ui.html(f'<div style="margin-top:12px;display:inline-flex;padding:10px 14px;border-radius:999px;font-weight:800;{diagnosis_badge_style(diag["nivel"])}">Nivel {diag["nivel"]} · Score {diag["score"]:.2f}</div>'); ui.html(f'''<div class="ideas-grid-2" style="margin-top:18px;"><div class="ideas-quick-card"><div class="label">Ficha de empresa</div><div class="detail">Razón social: {fix_text(company.get('razon_social', diag['empresa'])) if company else diag['empresa']}</div><div class="detail">Ubicación: {fix_text(company.get('ubicacion', '')) if company else ''}</div><div class="detail">Rubro: {fix_text(company.get('rubro', '')) if company else ''}</div><div class="detail">Empleados: {company.get('cantidad_empleados', 0) if company else 0}</div></div><div class="ideas-quick-card"><div class="label">Resumen consultivo</div><div class="detail">Puntos fuertes: {fix_text(strengths)}</div><div class="detail">Áreas débiles: {fix_text(weaknesses)}</div><div class="detail">Contacto: {fix_text(company.get('contacto_nombre', '')) if company else ''}</div><div class="detail">Certificaciones: {certifications_summary(company)}</div></div></div>''')
            render_detail(None)
            table.on('rowClick', lambda event: render_detail(extract_diag_id(event.args)))
            table.on('open_resultados', lambda event: (set_selection(diagnosis_record(int(event.args))['empresa_id'], int(event.args)), ui.navigate.to('/resultados')) if diagnosis_record(int(event.args)) else ui.notify('No se encontró ese diagnóstico.', type='warning'))
            table.on('edit_diag', lambda event: (start_edit(int(event.args), duplicate=False), ui.navigate.to('/diagnostico')))
            table.on('duplicate_diag', lambda event: (start_edit(int(event.args), duplicate=True), ui.navigate.to('/diagnostico')))
            def confirm_delete(diag_id: int) -> None:
                diag = diagnosis_record(diag_id)
                if not diag: ui.notify('Ese diagnóstico ya no existe.', type='warning'); return
                with ui.dialog() as dialog, ui.card().classes('p-5'):
                    ui.label('Eliminar diagnóstico').classes('text-lg font-semibold'); ui.label(f"Se eliminará {diag['empresa']} · {diag['fecha']} y también sus respuestas.").classes('text-slate-600')
                    with ui.row().classes('w-full justify-end gap-2 mt-3'):
                        ui.button('Cancelar', on_click=dialog.close).props('flat'); ui.button('Eliminar', color='negative', on_click=lambda: (eliminar_diagnostico(diag_id), dialog.close(), ui.notify('Diagnóstico eliminado correctamente.', type='positive'), ui.navigate.to('/historial')))
                dialog.open()
            table.on('delete_diag', lambda event: confirm_delete(int(event.args)))
