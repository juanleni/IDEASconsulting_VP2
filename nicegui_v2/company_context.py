from __future__ import annotations

from nicegui import app, ui


def empresa_id_from_query() -> int | None:
    """Lee ?empresa_id=<id> de la URL de la pestaña actual.

    A diferencia de app.storage.user (compartido por todas las pestañas del
    mismo navegador), la URL es propia de cada pestaña: es la única forma de
    que un admin pueda tener la Empresa A abierta en una pestaña y la Empresa B
    en otra sin que la selección de una pise la de la otra.
    """
    try:
        raw = ui.context.client.request.query_params.get('empresa_id')
    except Exception:
        return None
    try:
        return int(raw) if raw else None
    except Exception:
        return None


def empresa_id_from_query_for_admin() -> int | None:
    """Como empresa_id_from_query, pero solo para sesiones admin.

    El query param viaja en la URL y cualquier usuario lo puede editar a
    mano. Un usuario de rol "empresa" nunca debe poder cambiar de empresa
    así (su empresa queda fijada por logged_empresa_id); solo el admin, que
    ya puede navegar libremente entre empresas, puede usarlo para anclar la
    selección a esta pestaña.
    """
    if str(app.storage.user.get('role') or '').strip().lower() != 'admin':
        return None
    return empresa_id_from_query()


def with_empresa_id(path: str, empresa_id: int | None) -> str:
    """Agrega (o reemplaza) el query param empresa_id en una ruta interna."""
    base = path.split('?', 1)[0]
    if not empresa_id:
        return base
    return f"{base}?empresa_id={int(empresa_id)}"
