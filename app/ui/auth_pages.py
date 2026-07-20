from __future__ import annotations

from nicegui import app as nicegui_app
from nicegui import ui

from app.db.session import AsyncSessionLocal
from app.services.auth_service import authenticate_user, create_access_token


def get_browser_token() -> str | None:
    token = nicegui_app.storage.browser.get("access_token")
    return str(token) if token else None


def clear_browser_session() -> None:
    nicegui_app.storage.browser.pop("access_token", None)
    nicegui_app.storage.browser.pop("user_name", None)


def render_login_page() -> None:
    clear_browser_session()

    with ui.column().classes("w-full min-h-screen items-center justify-center bg-slate-50 px-4"):
        with ui.card().classes("w-full max-w-[420px] p-6 gap-4"):
            ui.label("IDEAS Consulting").classes("text-2xl font-bold text-slate-900")
            ui.label("Acceso a plataforma").classes("text-sm text-slate-500")

            email = ui.input("Email").props("outlined dense").classes("w-full")
            password = ui.input("Password", password=True, password_toggle_button=True).props("outlined dense").classes("w-full")
            status = ui.label("").classes("text-sm text-red-600")

            async def submit() -> None:
                status.text = ""
                async with AsyncSessionLocal() as session:
                    user = await authenticate_user(session=session, email=email.value or "", password=password.value or "")
                if not user:
                    status.text = "Email o password invalidos."
                    return

                token = create_access_token(user)
                nicegui_app.storage.browser["access_token"] = token.access_token
                nicegui_app.storage.browser["user_name"] = user.email
                ui.navigate.to("/")

            password.on("keydown.enter", submit)
            ui.button("Ingresar", icon="login", on_click=submit).props("unelevated").classes("w-full")
