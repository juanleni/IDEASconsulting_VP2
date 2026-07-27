from __future__ import annotations

import asyncio
from datetime import datetime, timedelta

from modules_legal_curation import ejecutar_conector, listar_fuentes

_scheduler_task = None

FRECUENCIA_A_TIMEDELTA = {
    'diaria': timedelta(days=1),
    'semanal': timedelta(days=7),
    'mensual': timedelta(days=30),
}
INTERVALO_CHEQUEO_SEG = 3600  # revisa una vez por hora si alguna fuente ya corresponde correr


def _corresponde_correr(fuente: dict) -> bool:
    if not fuente.get('activo'):
        return False
    ultima = fuente.get('ultima_corrida')
    if not ultima:
        return True
    intervalo = FRECUENCIA_A_TIMEDELTA.get(fuente.get('frecuencia_recomendada'), timedelta(days=7))
    try:
        ultima_dt = datetime.fromisoformat(ultima)
    except ValueError:
        return True
    ahora = datetime.now(ultima_dt.tzinfo) if ultima_dt.tzinfo else datetime.now()
    return ahora - ultima_dt >= intervalo


async def _loop_scheduler():
    while True:
        try:
            for fuente in listar_fuentes():
                if _corresponde_correr(fuente):
                    # ejecutar_conector hace requests bloqueantes (y, para el
                    # scraper de Boletín, sleeps deliberados) — se corre en
                    # un thread aparte para no congelar el resto de la app
                    # mientras dura la corrida.
                    await asyncio.to_thread(ejecutar_conector, fuente['nombre_fuente'])
        except Exception:
            pass
        await asyncio.sleep(INTERVALO_CHEQUEO_SEG)


def start_legal_curation_scheduler() -> None:
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
