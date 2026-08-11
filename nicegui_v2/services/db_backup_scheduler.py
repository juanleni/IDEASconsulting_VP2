from __future__ import annotations

import asyncio
import datetime
from pathlib import Path

from core_data import BACKUP_DIR, crear_backup_db, listar_backups_db

_scheduler_task = None

INTERVALO_CHEQUEO_SEG = 60 * 60  # revisa cada 1h si corresponde backup
FRECUENCIA_HORAS = 24  # backup automatico cada 24hs
RETENCION_BACKUPS = 30  # cuantos backups automaticos conservar (~1 mes si es diario)

_marker_path = Path(BACKUP_DIR) / ".last_auto_backup"


def _ya_toca_backup() -> bool:
    if not _marker_path.exists():
        return True
    try:
        last = datetime.datetime.fromisoformat(_marker_path.read_text().strip())
    except Exception:
        return True
    return (datetime.datetime.now() - last) >= datetime.timedelta(hours=FRECUENCIA_HORAS)


def _marcar_backup_hecho() -> None:
    try:
        Path(BACKUP_DIR).mkdir(parents=True, exist_ok=True)
        _marker_path.write_text(datetime.datetime.now().isoformat())
    except Exception:
        pass


def _podar_backups_viejos() -> None:
    """Conserva solo los ultimos RETENCION_BACKUPS backups automaticos para no llenar el disco."""
    try:
        backups = listar_backups_db(limit=10_000)
        for item in backups[RETENCION_BACKUPS:]:
            try:
                Path(item["path"]).unlink(missing_ok=True)
            except Exception:
                pass
    except Exception:
        pass


def ejecutar_backup_si_corresponde(force: bool = False) -> tuple[bool, str] | None:
    """Corre un backup si paso la frecuencia configurada (o siempre si force=True).

    NOTA importante (Fase 1, 2026-08-10): esto respalda ideas.db a la carpeta local
    `backups/` -- protege contra un bug o una accion destructiva durante una sesion
    corriendo, pero en Render plan free esa misma carpeta se pierde en cada redeploy
    igual que ideas.db. No reemplaza un backup fuera del disco de la app (S3 u otro
    almacenamiento externo) ni el disco persistente pendiente de activar (ver render.yaml).
    """
    if not force and not _ya_toca_backup():
        return None
    ok, msg = crear_backup_db()
    if ok:
        _marcar_backup_hecho()
        _podar_backups_viejos()
    return ok, msg


async def _loop_scheduler():
    while True:
        try:
            ejecutar_backup_si_corresponde()
        except Exception:
            pass
        await asyncio.sleep(INTERVALO_CHEQUEO_SEG)


def start_db_backup_scheduler() -> None:
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
