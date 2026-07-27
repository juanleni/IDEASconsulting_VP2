from __future__ import annotations

import asyncio
import datetime

from core_data import obtener_empresas, obtener_empresa_detalle
from ideas_utils import enviar_correo_alertas_legal_matrix
from modules_legal_matrix import (
    generar_alertas_vencimientos,
    marcar_legal_matrix_alertas_enviadas,
    obtener_legal_matrix_alert_settings,
    obtener_legal_matrix_alertas_vencimiento_abiertas,
)

_scheduler_task = None
HORA_ENVIO = "08:00"


def _ya_paso_la_hora_de_envio() -> bool:
    return datetime.datetime.now().strftime("%H:%M") >= HORA_ENVIO


def procesar_alertas_empresa(empresa_id: int) -> dict | None:
    """Genera alertas de vencimiento y envía el digest diario por email si corresponde.

    Devuelve el resultado del envío o None si no había nada que mandar / ya se envió hoy.
    """
    settings = obtener_legal_matrix_alert_settings(empresa_id)
    if not settings['activo']:
        return None
    if settings['ultimo_envio'] == datetime.date.today().isoformat():
        return None
    if not _ya_paso_la_hora_de_envio():
        return None

    generar_alertas_vencimientos(empresa_id, settings['dias_anticipacion'])
    alertas = obtener_legal_matrix_alertas_vencimiento_abiertas(empresa_id)
    marcar_legal_matrix_alertas_enviadas(empresa_id)
    if not alertas:
        return None

    empresa = obtener_empresa_detalle(empresa_id) or {}
    correo = str(empresa.get('contacto_correo') or '').strip()
    if not correo:
        return None
    return enviar_correo_alertas_legal_matrix(correo, empresa.get('razon_social'), alertas)


async def _loop_scheduler():
    while True:
        try:
            for company_id, _company_name in obtener_empresas():
                procesar_alertas_empresa(int(company_id))
        except Exception:
            pass
        await asyncio.sleep(60)


def start_legal_matrix_alert_scheduler() -> None:
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
