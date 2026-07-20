from __future__ import annotations

import datetime

from core_data import (
    obtener_lab_acciones_empresa,
    obtener_lab_auditorias_empresa,
    obtener_lab_calibraciones_empresa,
    obtener_lab_competencias_empresa,
    obtener_lab_equipos_empresa,
    obtener_lab_incertidumbre_empresa,
    obtener_lab_informes_empresa,
    obtener_lab_metodos_empresa,
    obtener_lab_muestras_empresa,
)


def _date_or_none(text: str) -> datetime.date | None:
    raw = str(text or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
        try:
            return datetime.datetime.strptime(raw, fmt).date()
        except Exception:
            continue
    return None


def run_lab_rules_check(company_id: int) -> list[dict]:
    alerts: list[dict] = []
    today = datetime.date.today()
    equipos = obtener_lab_equipos_empresa(int(company_id))
    metodos = obtener_lab_metodos_empresa(int(company_id))
    muestras = obtener_lab_muestras_empresa(int(company_id))
    competencias = obtener_lab_competencias_empresa(int(company_id))
    incertidumbre = obtener_lab_incertidumbre_empresa(int(company_id))
    informes = obtener_lab_informes_empresa(int(company_id))
    auditorias = obtener_lab_auditorias_empresa(int(company_id))
    acciones = obtener_lab_acciones_empresa(int(company_id))
    calibraciones = obtener_lab_calibraciones_empresa(int(company_id))

    metodo_vigentes = {str(m.get("codigo") or "").strip() for m in metodos if str(m.get("estado") or "").strip().lower() == "vigente"}
    metodo_obsoletos = {str(m.get("codigo") or "").strip() for m in metodos if str(m.get("estado") or "").strip().lower() == "obsoleto"}
    inc_metodos = {str(i.get("metodo") or "").strip() for i in incertidumbre}

    for eq in equipos:
        eq_id = int(eq.get("id") or 0)
        proxima = _date_or_none(str(eq.get("fecha_proxima_calibracion") or ""))
        if proxima and proxima < today:
            alerts.append({"titulo": "Equipo con calibración vencida", "descripcion": f"Equipo {eq.get('nombre','')} vencido desde {proxima}.", "modulo_origen": "equipos", "registro_tipo": "equipo", "registro_id": eq_id, "criticidad": "alta", "tipo": "vencimiento", "requiere_ia": 1})
        if str(eq.get("criticidad") or "").strip().lower() in {"alta", "critica"} and not str(eq.get("certificado") or "").strip():
            alerts.append({"titulo": "Equipo crítico sin certificado", "descripcion": f"Equipo {eq.get('nombre','')} no posee certificado adjunto.", "modulo_origen": "equipos", "registro_tipo": "equipo", "registro_id": eq_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(eq.get("responsable") or "").strip():
            alerts.append({"titulo": "Equipo sin responsable", "descripcion": f"Equipo {eq.get('nombre','')} sin responsable definido.", "modulo_origen": "equipos", "registro_tipo": "equipo", "registro_id": eq_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(eq.get("ubicacion") or "").strip():
            alerts.append({"titulo": "Equipo sin ubicación", "descripcion": f"Equipo {eq.get('nombre','')} sin ubicación registrada.", "modulo_origen": "equipos", "registro_tipo": "equipo", "registro_id": eq_id, "criticidad": "baja", "tipo": "incompleto", "requiere_ia": 0})

    for met in metodos:
        met_id = int(met.get("id") or 0)
        code = str(met.get("codigo") or "").strip()
        estado = str(met.get("estado") or "").strip().lower()
        if estado == "vigente" and not str(met.get("validacion") or "").strip() and not str(met.get("verificacion") or "").strip():
            alerts.append({"titulo": "Método vigente sin validación/verificación", "descripcion": f"Método {code} vigente sin validación o verificación.", "modulo_origen": "metodos", "registro_tipo": "metodo", "registro_id": met_id, "criticidad": "alta", "tipo": "incoherencia", "requiere_ia": 1})
        if not str(met.get("responsable_tecnico") or "").strip():
            alerts.append({"titulo": "Método sin responsable técnico", "descripcion": f"Método {code} sin responsable técnico.", "modulo_origen": "metodos", "registro_tipo": "metodo", "registro_id": met_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(met.get("equipos_requeridos") or "").strip():
            alerts.append({"titulo": "Método sin equipos asociados", "descripcion": f"Método {code} sin equipos requeridos declarados.", "modulo_origen": "metodos", "registro_tipo": "metodo", "registro_id": met_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(met.get("competencias_requeridas") or "").strip():
            alerts.append({"titulo": "Método sin competencias requeridas", "descripcion": f"Método {code} sin competencias requeridas.", "modulo_origen": "metodos", "registro_tipo": "metodo", "registro_id": met_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if code and code not in inc_metodos:
            alerts.append({"titulo": "Método sin incertidumbre asociada", "descripcion": f"Método {code} no tiene registros de incertidumbre.", "modulo_origen": "incertidumbre", "registro_tipo": "metodo", "registro_id": met_id, "criticidad": "alta", "tipo": "incoherencia", "requiere_ia": 1})

    for m in muestras:
        mid = int(m.get("id") or 0)
        metodo = str(m.get("metodo") or "").strip()
        if not str(m.get("codigo_unico") or "").strip():
            alerts.append({"titulo": "Muestra sin código único", "descripcion": f"Muestra {mid} sin código único.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(m.get("condicion_recepcion") or "").strip():
            alerts.append({"titulo": "Muestra sin condición de recepción", "descripcion": f"Muestra {mid} sin condición de recepción.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(m.get("cadena_custodia") or "").strip():
            alerts.append({"titulo": "Muestra sin cadena de custodia", "descripcion": f"Muestra {mid} sin cadena de custodia.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "alta", "tipo": "incompleto", "requiere_ia": 1})
        if not metodo:
            alerts.append({"titulo": "Muestra sin método asociado", "descripcion": f"Muestra {mid} sin método.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "alta", "tipo": "incoherencia", "requiere_ia": 1})
        if metodo and metodo in metodo_obsoletos:
            alerts.append({"titulo": "Muestra activa con método obsoleto", "descripcion": f"Muestra {mid} usa método obsoleto {metodo}.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "critica", "tipo": "riesgo", "requiere_ia": 1})
        compromiso = _date_or_none(str(m.get("fecha_compromiso") or ""))
        if compromiso and compromiso < today and str(m.get("estado") or "").strip().lower() not in {"cerrada", "final"}:
            alerts.append({"titulo": "Muestra vencida respecto a compromiso", "descripcion": f"Muestra {mid} vencida respecto a {compromiso}.", "modulo_origen": "muestras", "registro_tipo": "muestra", "registro_id": mid, "criticidad": "alta", "tipo": "vencimiento", "requiere_ia": 0})

    informes_por_muestra = {str(i.get("muestra") or "").strip() for i in informes}
    for m in muestras:
        if str(m.get("estado") or "").strip().lower() in {"cerrada", "final"} and str(m.get("codigo_unico") or "").strip() not in informes_por_muestra:
            alerts.append({"titulo": "Muestra cerrada sin informe", "descripcion": f"Muestra {m.get('codigo_unico','')} cerrada sin informe asociado.", "modulo_origen": "informes", "registro_tipo": "muestra", "registro_id": int(m.get("id") or 0), "criticidad": "alta", "tipo": "incoherencia", "requiere_ia": 1})

    for c in competencias:
        cid = int(c.get("id") or 0)
        venc = _date_or_none(str(c.get("vencimiento") or ""))
        if venc and venc < today:
            alerts.append({"titulo": "Competencia vencida", "descripcion": f"{c.get('persona','')} con competencia vencida ({venc}).", "modulo_origen": "competencias", "registro_tipo": "competencia", "registro_id": cid, "criticidad": "alta", "tipo": "vencimiento", "requiere_ia": 1})
        if not str(c.get("evidencia") or "").strip():
            alerts.append({"titulo": "Competencia sin evidencia", "descripcion": f"Competencia de {c.get('persona','')} sin evidencia.", "modulo_origen": "competencias", "registro_tipo": "competencia", "registro_id": cid, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
        if not str(c.get("evaluador") or "").strip():
            alerts.append({"titulo": "Competencia sin evaluador", "descripcion": f"Competencia de {c.get('persona','')} sin evaluador.", "modulo_origen": "competencias", "registro_tipo": "competencia", "registro_id": cid, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})

    for inf in informes:
        iid = int(inf.get("id") or 0)
        if str(inf.get("estado") or "").strip().lower() == "emitido":
            if not str(inf.get("revisor") or "").strip():
                alerts.append({"titulo": "Informe emitido sin revisor", "descripcion": f"Informe {inf.get('numero_informe','')} emitido sin revisor.", "modulo_origen": "informes", "registro_tipo": "informe", "registro_id": iid, "criticidad": "alta", "tipo": "incoherencia", "requiere_ia": 1})
            if not str(inf.get("incertidumbre") or "").strip():
                alerts.append({"titulo": "Informe emitido sin incertidumbre", "descripcion": f"Informe {inf.get('numero_informe','')} sin incertidumbre declarada.", "modulo_origen": "informes", "registro_tipo": "informe", "registro_id": iid, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
            if str(inf.get("metodo") or "").strip() in metodo_obsoletos:
                alerts.append({"titulo": "Informe emitido con método obsoleto", "descripcion": f"Informe {inf.get('numero_informe','')} usa método obsoleto.", "modulo_origen": "informes", "registro_tipo": "informe", "registro_id": iid, "criticidad": "critica", "tipo": "riesgo", "requiere_ia": 1})

    for au in auditorias:
        aid = int(au.get("id") or 0)
        fecha = _date_or_none(str(au.get("fecha") or ""))
        if fecha and fecha < today and str(au.get("estado") or "").strip().lower() in {"abierta", "en curso"}:
            alerts.append({"titulo": "Auditoría abierta vencida", "descripcion": f"Auditoría {aid} vencida desde {fecha}.", "modulo_origen": "auditorias", "registro_tipo": "auditoria", "registro_id": aid, "criticidad": "alta", "tipo": "vencimiento", "requiere_ia": 0})
        if str(au.get("resultado") or "").strip().lower() in {"no conforme", "parcial"} and not str(au.get("accion") or "").strip():
            alerts.append({"titulo": "Hallazgo sin acción correctiva", "descripcion": f"Auditoría {aid} tiene hallazgo sin acción.", "modulo_origen": "auditorias", "registro_tipo": "auditoria", "registro_id": aid, "criticidad": "alta", "tipo": "incompleto", "requiere_ia": 1})

    for ac in acciones:
        ac_id = int(ac.get("id") or 0)
        venc = _date_or_none(str(ac.get("vencimiento") or ""))
        if venc and venc < today and str(ac.get("estado") or "").strip().lower() not in {"cerrada", "eficaz"}:
            alerts.append({"titulo": "Acción correctiva vencida", "descripcion": f"Acción {ac_id} vencida sin cierre.", "modulo_origen": "acciones", "registro_tipo": "accion", "registro_id": ac_id, "criticidad": "alta", "tipo": "vencimiento", "requiere_ia": 0})
        if str(ac.get("estado") or "").strip().lower() in {"cerrada", "eficaz"} and not str(ac.get("evidencia") or "").strip():
            alerts.append({"titulo": "Cierre sin evidencia", "descripcion": f"Acción {ac_id} cerrada sin evidencia.", "modulo_origen": "acciones", "registro_tipo": "accion", "registro_id": ac_id, "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})

    if not calibraciones:
        alerts.append({"titulo": "Sin historial de calibraciones", "descripcion": "No hay registros de calibración para la empresa.", "modulo_origen": "calibraciones", "registro_tipo": "empresa", "registro_id": int(company_id), "criticidad": "media", "tipo": "incompleto", "requiere_ia": 0})
    return alerts


def run_record_rules_check(record_type: str, record_id: int, company_id: int) -> list[dict]:
    all_alerts = run_lab_rules_check(int(company_id))
    selected = []
    for item in all_alerts:
        if str(item.get("registro_tipo") or "").strip().lower() == str(record_type or "").strip().lower() and int(item.get("registro_id") or 0) == int(record_id):
            selected.append(item)
    return selected

