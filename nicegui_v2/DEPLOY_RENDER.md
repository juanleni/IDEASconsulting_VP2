# Deploy en Render

## Qué hace esta configuración

La app quedó preparada para publicarse en Render usando:

- `requirements.txt`
- `render.yaml`
- arranque web desde `nicegui_v2/app.py`

Cuando Render publique la app:

- usará el puerto de entorno `PORT`
- levantará NiceGUI en `0.0.0.0`

## Pasos

1. Subir este proyecto a un repositorio GitHub.
2. Entrar a `https://render.com`.
3. Crear una cuenta o iniciar sesión.
4. Elegir `New +` → `Blueprint`.
5. Conectar el repositorio.
6. Render detectará `render.yaml`.
7. Confirmar el deploy.

## Resultado

Render te dará un enlace público, por ejemplo:

- `https://ideas-consulting-v2.onrender.com`

Tu equipo podrá abrirlo desde navegador sin instalar Python.

## Qué debe quedar en el repo

Mantén estos archivos y carpetas:

- `nicegui_v2/`
- `Data/`
- `database.py`
- `ideas_utils.py`
- `requirements.txt`
- `render.yaml`
- `ideas.db`
- `logo.png`
- `ideas_home_banner.png`

No hace falta subir:

- `portable/`
- `reportes/`
- `__pycache__/`
- `.nicegui/`
- `.vscode/`

## Importante

Esta opción es buena para evaluación y pruebas internas.

La app hoy usa archivos locales y SQLite:

- `ideas.db`
- carpeta `Data`
- carpeta `reportes`

En Render free el almacenamiento local no es persistente a largo plazo.
Eso significa:

- sirve para demos y revisión del equipo
- no es ideal todavía para una operación real con datos que deban conservarse siempre

## Recomendación

Usar Render gratis para evaluación.
Si la validan, el siguiente paso sería migrar la base a una base externa persistente y revisar almacenamiento de reportes.
