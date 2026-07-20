from __future__ import annotations

from nicegui import ui

from app.ui.smart_assist import render_smart_assist


def executive_shell(
    company_name: str,
    user_name: str,
    api_base_url: str = "/api",
    jwt_token: str | None = None,
    module_key: str = "general",
) -> None:
    with ui.right_drawer(value=False).classes("ideas-ai-drawer p-4 w-[460px] max-w-[92vw]") as drawer:
        render_smart_assist(api_base_url=api_base_url, jwt_token=jwt_token, module_key=module_key)

    with ui.header().classes("bg-white shadow-sm border-b border-slate-200"):
        with ui.row().classes("w-full items-center justify-between px-4 py-2"):
            with ui.row().classes("items-center gap-3"):
                ui.image("/assets/logo.png").classes("w-8 h-8 object-contain")
                with ui.column().classes("gap-0"):
                    ui.label("IDEAS Consulting").classes("text-slate-900 font-bold")
                    ui.label(company_name).classes("text-xs text-slate-500")
            with ui.row().classes("items-center gap-2"):
                ui.label(user_name).classes("text-sm text-slate-600")
                assist_button = ui.button(icon="auto_awesome").props("flat round dense")
                assist_button.on_click(drawer.toggle)
