from __future__ import annotations

import asyncio
import datetime
import sqlite3

from core_data import DB_PATH, obtener_empresas
from services.lab_ai_report_service import generate_daily_ai_summary
from services.lab_alert_service import run_rules_and_alert

_scheduler_task = None


def _time_matches(target_hhmm: str) -> bool:
    now = datetime.datetime.now().strftime("%H:%M")
    return str(target_hhmm or "").strip() == now


def _weekday_matches(name: str) -> bool:
    return datetime.datetime.now().strftime("%A").lower() == str(name or "").strip().lower()


def _load_settings(company_id: int) -> dict:
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """
        SELECT ia_automatica_activa, scheduler_activo, frecuencia_diaria, frecuencia_semanal_dia, frecuencia_semanal_hora, auto_summary_activo, max_analisis_por_ciclo
        FROM lab_ai_settings
        WHERE empresa_id = ?
        """,
        (int(company_id),),
    )
    row = c.fetchone()
    conn.close()
    if not row:
        return {
            "ia_automatica_activa": 1,
            "scheduler_activo": 0,
            "frecuencia_diaria": "08:30",
            "frecuencia_semanal_dia": "monday",
            "frecuencia_semanal_hora": "09:00",
            "auto_summary_activo": 1,
            "max_analisis_por_ciclo": 20,
        }
    keys = ["ia_automatica_activa", "scheduler_activo", "frecuencia_diaria", "frecuencia_semanal_dia", "frecuencia_semanal_hora", "auto_summary_activo", "max_analisis_por_ciclo"]
    return dict(zip(keys, row))


async def _loop_scheduler():
    while True:
        try:
            for company_id, _company_name in obtener_empresas():
                cfg = _load_settings(int(company_id))
                if not int(cfg.get("scheduler_activo") or 0):
                    continue
                if _time_matches(str(cfg.get("frecuencia_diaria") or "08:30")):
                    # run_rules_and_alert / generate_daily_ai_summary llaman a OpenAI
                    # de forma bloqueante -- se corren en un thread aparte para no
                    # congelar el resto de la app (websockets de todos los clientes)
                    # mientras dura la llamada.
                    await asyncio.to_thread(run_rules_and_alert, int(company_id), actor="scheduler_diario")
                    if int(cfg.get("auto_summary_activo") or 1):
                        await asyncio.to_thread(generate_daily_ai_summary, int(company_id))
                if _weekday_matches(str(cfg.get("frecuencia_semanal_dia") or "monday")) and _time_matches(str(cfg.get("frecuencia_semanal_hora") or "09:00")):
                    await asyncio.to_thread(run_rules_and_alert, int(company_id), actor="scheduler_semanal")
        except Exception:
            pass
        await asyncio.sleep(60)


def start_lab_ai_scheduler() -> None:
    global _scheduler_task
    if _scheduler_task and not _scheduler_task.done():
        return
    coro = _loop_scheduler()
    try:
        loop = asyncio.get_running_loop()
        _scheduler_task = loop.create_task(coro)
    except Exception:
        try:
            coro.close()
        except Exception:
            pass
        _scheduler_task = None
