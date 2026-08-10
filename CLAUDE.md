# IDEAS / IDEUS — contexto del proyecto

Repo local: `C:\Users\RRHH\Documents\IDEAS`. GitHub: `juanleni/IDEASconsulting_VP2` (branch `main`).
Deploy: Render — servicio `ideas-consulting-v2` (plataforma principal) + `ideas-mobile-legal-matrix` (app mobile). Config en `render.yaml`, ambos `autoDeploy: false` (deploy manual desde el dashboard de Render).

Git no está en el PATH en esta máquina: usar `& "C:\Program Files\Git\cmd\git.exe" ...`.

## Qué es esto

Plataforma de consultoría (IDEAS Consulting) con un sitio público institucional y un sistema de gestión interno (actualmente en proceso de rebranding a **"IDEUS"**, posicionado como "by IDEAS Consulting") para clientes: Calidad/8D, Ambiente, SST, Riesgos, KPIs, Documentos, Laboratorio, Mapas de proceso y **Matriz Legal Digital** (el módulo con más desarrollo activo últimamente).

## Arquitectura — 3 frentes en paralelo

1. **`nicegui_v2/`** — plataforma principal en producción. NiceGUI + SQLite (`ideas.db` en la raíz del repo, resuelto por ruta relativa). Contiene la web pública (`pages_public.py`, `institutional_app.py`) y el sistema de gestión (`app.py` es el shell/router principal, `modules_*.py` un módulo por área, `core_data.py`/`database.py` acceso a datos). Archivos delicados: `app.py`, `pdf_reports.py`, `render.yaml`, `requirements.txt` — tocar con cuidado, guardar copia antes de cambios grandes.
2. **`mobile_legal_matrix/`** — PWA independiente (puerto 8600 local), un solo módulo (Matriz Legal). No depende de que `nicegui_v2` esté corriendo, pero **reutiliza sus helpers** (`modules_legal_matrix.py`, `core_data.py`, misma `ideas.db`, misma tabla `usuarios`, misma función `verificar_usuario`) — no duplica lógica de negocio. Login real, splash screen, carga de evidencia (cámara/galería/archivo). Deployada en Render sobre HTTPS real (necesario para service workers / push a futuro). Ver `mobile_legal_matrix/README.md` y `mobile_legal_matrix/SPEC_mobile_legal_matrix_v2.md` para el detalle de producto y el roadmap (Face ID/WebAuthn, diff de actualizaciones IDEAS, push notifications, KPIs nuevos — todo eso está spec'ado pero no implementado aún).
3. **`app/`** — prototipo WIP de una arquitectura nueva (FastAPI multi-tenant + Postgres, routers/servicios/repositorios separados). Empezado 2026-07-20 (commit `8eca987`, marcado WIP). Embrionario, no reemplaza nada en producción todavía — no asumir que es el camino ya decidido, confirmar antes de invertir tiempo ahí.

## Estado al 2026-08-10

**Últimos 7 commits (2026-07-27)** — foco: Matriz Legal Digital.
- App mobile con login real, evidencia, deploy en Render.
- Shell responsive mobile en la plataforma principal.
- Scheduler de alertas de vencimiento + template del dashboard.
- **Panel de curación normativa** (`modules_legal_curation.py`, solo `IDEAS_ADMIN`): ingesta candidatos desde SAIJ, Boletín Oficial SRT (scraper) y SRT Digesto (API), a una tabla `normas_raw` para revisar/aprobar antes de que lleguen a la matriz de un cliente. El conector SRT Digesto saca su propio token de auth del endpoint público de SRT en cada corrida (sin credencial guardada). Verificado end-to-end con datos reales.
  **Gap conocido, no resuelto:** "aprobar" solo marca la norma como revisada en `normas_raw` — todavía no decide a qué empresa(s) se publica, porque ese mapeo empresa↔norma no está definido en ningún lado.

**WIP sin commitear (lo que se venía trabajando en la última sesión):**
Rebranding del sistema de gestión a **"IDEUS"** (wordmark "IDEUS" + "by IDEAS Consulting"). Toca `app.py`, `pages_public.py`, `institutional_app.py`, `ideas_utils.py` (nuevo helper reutilizable `ideus_wordmark_html()`) y todos los `modules_*.py` (probablemente solo por el título de página / imports, revisar diff antes de commitear). Además:
- Panel nuevo en Usuarios (`modules_users.py`): contraseña de borrado total de la Matriz Legal + configuración de alertas por email, para `EMPRESA_ADMIN`.
- `pages_public.py`: ~475 líneas nuevas, rediseño de secciones del sitio público (stats, hero, etc.).
- Sin trackear todavía: `nicegui_v2/tests/` (tests del scheduler de alertas de Matriz Legal) y `nicegui_v2/Curacion Normas/` (prototipos fuente de los 3 conectores de curación normativa, ya integrados en `modules_legal_curation.py`).

**Antes de seguir:** decidir si el rebranding a IDEUS se commitea tal cual o se sigue iterando — está a medio camino (mezcla cambios de branding con el panel de contraseña/alertas de Matriz Legal en los mismos archivos sin commitear).

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
