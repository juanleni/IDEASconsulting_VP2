# IDEAS / IDEUS — contexto del proyecto

Repo local: `C:\Users\RRHH\Documents\IDEAS`. GitHub: `juanleni/IDEASconsulting_VP2` (branch `main`).
Deploy: Render — servicio `ideas-consulting-v2` (plataforma principal) + `ideas-mobile-legal-matrix` (app mobile). Config en `render.yaml`, ambos `autoDeploy: false` (deploy manual desde el dashboard de Render).

Git no está en el PATH en esta máquina: usar `& "C:\Program Files\Git\cmd\git.exe" ...`.

## Qué es esto

Plataforma de consultoría. **IDEAS Consulting** es la consultora; **IDEUS** es el nombre del producto/plataforma en sí (sistema de gestión), mostrado como "IDEUS — by IDEAS Consulting". Sitio público institucional + sistema de gestión interno para clientes: Calidad/8D, Ambiente, SST, Riesgos, KPIs, Documentos, Laboratorio, Mapas de proceso y **Matriz Legal Digital** (el módulo con más desarrollo activo últimamente).

## Arquitectura — 3 frentes en paralelo

1. **`nicegui_v2/`** — plataforma principal en producción. NiceGUI + SQLite (`ideas.db` en la raíz del repo, resuelto por ruta relativa). Contiene la web pública (`pages_public.py`, `institutional_app.py`) y el sistema de gestión (`app.py` es el shell/router principal, `modules_*.py` un módulo por área, `core_data.py`/`database.py` acceso a datos). Archivos delicados: `app.py`, `pdf_reports.py`, `render.yaml`, `requirements.txt` — tocar con cuidado, guardar copia antes de cambios grandes.
2. **`mobile_legal_matrix/`** — PWA independiente (puerto 8600 local), un solo módulo (Matriz Legal). No depende de que `nicegui_v2` esté corriendo, pero **reutiliza sus helpers** (`modules_legal_matrix.py`, `core_data.py`, misma `ideas.db`, misma tabla `usuarios`, misma función `verificar_usuario`) — no duplica lógica de negocio. Login real, splash screen, carga de evidencia (cámara/galería/archivo). Deployada en Render sobre HTTPS real (necesario para service workers / push a futuro). Ver `mobile_legal_matrix/README.md` y `mobile_legal_matrix/SPEC_mobile_legal_matrix_v2.md` para el detalle de producto y el roadmap (Face ID/WebAuthn, diff de actualizaciones IDEAS, push notifications, KPIs nuevos — todo eso está spec'ado pero no implementado aún).
3. **`app/`** — prototipo WIP de una arquitectura nueva (FastAPI multi-tenant + Postgres, routers/servicios/repositorios separados). Empezado 2026-07-20 (commit `8eca987`, marcado WIP). Embrionario, no reemplaza nada en producción todavía — no asumir que es el camino ya decidido, confirmar antes de invertir tiempo ahí.

## Estado al 2026-08-10

**Commits previos (2026-07-27)** — foco: Matriz Legal Digital.
- App mobile con login real, evidencia, deploy en Render.
- Shell responsive mobile en la plataforma principal.
- Scheduler de alertas de vencimiento + template del dashboard.
- **Panel de curación normativa** (`modules_legal_curation.py`, solo `IDEAS_ADMIN`): ingesta candidatos desde SAIJ, Boletín Oficial SRT (scraper) y SRT Digesto (API), a una tabla `normas_raw` para revisar/aprobar antes de que lleguen a la matriz de un cliente. El conector SRT Digesto saca su propio token de auth del endpoint público de SRT en cada corrida (sin credencial guardada). Verificado end-to-end con datos reales.
  **Gap conocido, no resuelto:** "aprobar" solo marca la norma como revisada en `normas_raw` — todavía no decide a qué empresa(s) se publica, porque ese mapeo empresa↔norma no está definido en ningún lado.

**Commits nuevos de esta sesión (2026-08-10), local en `main`, ya hechos pero todavía no pusheados a GitHub:**
- `Rebrand management platform as IDEUS, by IDEAS Consulting` — helper reutilizable `ideus_wordmark_html()` en `ideas_utils.py`, aplicado en `app.py`, `institutional_app.py`, `pages_public.py`, `pages_platform.py` (topbar, login, sitio público, meta tags, page titles).
- `Let IDEAS_ADMIN deep-link into a company's workspace/module via empresa_id` — los 8 `modules_*.py` + `pages_management.py` ahora leen `empresa_id` de la query string para `IDEAS_ADMIN`, y se sacó el bloqueo que le impedía a admin entrar a `/sistema-gestion`.
- `Add Matriz Legal delete-password and email alert settings to Usuarios` — panel para `EMPRESA_ADMIN`: contraseña de borrado total de la matriz + alertas por email configurables.
- `Add pytest suite for Matriz Legal and its alert scheduler` — `nicegui_v2/tests/` + `requirements-dev.txt`.
- `Add legal-curation prototype sources for reference` — `nicegui_v2/Curacion Normas/` (fuentes originales de los 3 conectores, no se importan desde la app).
- `Add CLAUDE.md project context` — este archivo.

**Pendiente, no algo para "seguir trabajando" sino housekeeping:**
- Pushear a GitHub (`git push`) y, si Render no auto-actualiza, Manual Deploy de `ideas-consulting-v2` en el dashboard.
- `nicegui_v2/ideas.db` — archivo suelto sin trackear que no debería existir ahí (la app espera `ideas.db` solo en la raíz del repo). Sin confirmar aún si borrarlo.
- `ideas.db` (raíz) tiene cambios sin commitear (datos de prueba locales, no código) — no se commiteó a propósito.

## Pendientes conocidos

- Definir el mapeo empresa↔norma para el flujo de aprobación del panel de curación normativa.
- Calidad/8D: editar y eliminar acciones D5/D6 individuales desde la tabla, múltiples árboles de 5 Porqués por factor retenido, llevar acciones D5/D6 al PDF ejecutivo.
- Mobile (`SPEC_mobile_legal_matrix_v2.md`): Face ID/WebAuthn, diff de actualizaciones de IDEAS (qué campo cambió, antes/después), push notifications (requiere HTTPS real + definir infraestructura), KPIs nuevos del dashboard.
- Migrar de SQLite a una base más robusta para uso productivo serio (hoy `ideas.db` en disco, sin persistencia garantizada entre redeploys de Render free tier).

## Accesos y flujo de trabajo

- Login plataforma: usuario `IDEAS`, contraseña `2026`, ruta `/plataforma`.
- Probar local: `python nicegui_v2\app.py` (plataforma) / `python mobile_legal_matrix\app.py` (mobile, puerto 8600, correr desde la raíz del repo).
- Flujo: editar local → probar local → commit → push a GitHub → si Render no auto-actualiza (`autoDeploy: false`), Manual Deploy → "Deploy latest commit" desde el dashboard.
- Detalle completo de deploy/troubleshooting en `ACTUALIZACION_WEB_IDEAS.txt` (plataforma principal) y `mobile_legal_matrix/DEPLOY_RENDER.md` (mobile).
- Changelog ejecutivo (para uso no técnico) en `CHANGELOG_STATUS.txt` — mantenerlo actualizado con fecha / módulo / qué cambió / impacto / pendientes cuando se cierre trabajo grande.
