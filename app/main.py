from __future__ import annotations

from fastapi import FastAPI
from nicegui import run as nicegui_run
from nicegui import ui

from app.api.routers.auditor import router as auditor_router
from app.api.routers.auth import router as auth_router
from app.api.routers.quality import router as quality_router
from app.api.routers.rag import router as rag_router
from app.core.config import settings
from app.ui.auth_pages import get_browser_token, render_login_page
from app.ui.layout import executive_shell


api = FastAPI(title="IDEAS SaaS API", version="0.1.0")
api.include_router(auth_router, prefix="/api")
api.include_router(quality_router, prefix="/api")
api.include_router(rag_router, prefix="/api")
api.include_router(auditor_router, prefix="/api")


@ui.page("/")
def index_page() -> None:
    token = get_browser_token()
    user_name = "Usuario autenticado" if token else "Sesion no iniciada"
    executive_shell(
        company_name="Empresa activa",
        user_name=user_name,
        api_base_url="/api",
        jwt_token=token,
        module_key="general",
    )
    with ui.column().classes("w-full max-w-[1200px] mx-auto p-6"):
        ui.label("Plataforma IDEAS - Frontend Lean").classes("text-2xl font-bold text-slate-900")
        ui.label("NiceGUI montado sobre FastAPI con patron multi-tenant.").classes("text-slate-600")
        if not token:
            ui.button("Ingresar", icon="login", on_click=lambda: ui.navigate.to("/login")).props("unelevated")


@ui.page("/login")
def login_page() -> None:
    render_login_page()


def build_application() -> FastAPI:
    try:
        nicegui_run.setup = lambda: None
        ui.run_with(api, storage_secret=settings.nicegui_storage_secret)
    except Exception:
        # Compatibilidad con versiones de NiceGUI sin run_with en este contexto.
        pass
    return api


app = build_application()
