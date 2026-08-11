# IDEAS / IDEUS — contexto del proyecto

Repo local: `C:\Users\RRHH\Documents\IDEAS`. GitHub: `juanleni/IDEASconsulting_VP2` (branch `main`).
Deploy: Render — servicio `ideas-consulting-v2` (plataforma principal) + `ideas-mobile-legal-matrix` (app mobile). Config en `render.yaml`, ambos `autoDeploy: false` (deploy manual desde el dashboard de Render).

Git no está en el PATH en esta máquina: usar `& "C:\Program Files\Git\cmd\git.exe" ...`.

## Qué es esto

Plataforma de consultoría. **IDEAS Consulting** es la consultora; **IDEUS** es el nombre del producto/plataforma en sí (sistema de gestión), mostrado como "IDEUS — by IDEAS Consulting". Sitio público institucional + sistema de gestión interno para clientes: Calidad/8D, Ambiente, SST, Riesgos, KPIs, Documentos, Laboratorio, Mapas de proceso y **Matriz Legal Digital** (el módulo con más desarrollo activo últimamente).

## Arquitectura — 3 frentes en paralelo

1. **`nicegui_v2/`** — plataforma principal en producción. NiceGUI + SQLite (`ideas.db` en la raíz del repo, resuelto por ruta relativa). Contiene la web pública (`pages_public.py`, `institutional_app.py`) y el sistema de gestión (`app.py` es el shell/router principal, `modules_*.py` un módulo por área, `core_data.py`/`database.py` acceso a datos). Archivos delicados: `app.py`, `pdf_reports.py`, `render.yaml`, `requirements.txt` — tocar con cuidado, guardar copia antes de cambios grandes.
2. **`mobile_legal_matrix/`** — PWA independiente (puerto 8600 local), un solo módulo (Matriz Legal). No depende de que `nicegui_v2` esté corriendo, pero **reutiliza sus helpers** (`modules_legal_matrix.py`, `core_data.py`, misma `ideas.db`, misma tabla `usuarios`, misma función `verificar_usuario`) — no duplica lógica de negocio. Login real, splash screen, carga de evidencia (cámara/galería/archivo). Deployada en Render sobre HTTPS real (necesario para service workers / push a futuro). Ver `mobile_legal_matrix/README.md` y `mobile_legal_matrix/SPEC_mobile_legal_matrix_v2.md` para el detalle de producto y el roadmap (Face ID/WebAuthn, diff de actualizaciones IDEAS, push notifications, KPIs nuevos — todo eso está spec'ado pero no implementado aún).
3. **`app/`** — prototipo WIP de una arquitectura nueva (FastAPI multi-tenant + Postgres, routers/servicios/repositorios separados). Empezado 2026-07-20 (commit `8eca987`, marcado WIP). Embrionario, no reemplaza nada en producción todavía. **En pausa, ver `ADR-001-arquitectura-app-prototipo.md`** (2026-08-10): recomendación es no seguir invirtiendo ahí por ahora (sin tests, no arranca tal cual en un entorno limpio, no conectado a Render, sin razón de negocio documentada para Postgres hoy) y en cambio replicar el patrón de "capa de servicios" directamente sobre `nicegui_v2/` — recomendación pendiente de confirmar por Juan, no una decisión ya tomada.

## Estado al 2026-08-11

**Commits del 2026-07-27** — foco: Matriz Legal Digital (mobile, scheduler de alertas, panel de curación normativa con SAIJ/Boletín Oficial/SRT Digesto).

**Commits del 2026-08-10 (primera tanda)** — rebranding a IDEUS, deep-link de admin por `empresa_id`, panel de contraseña/alertas de Matriz Legal en Usuarios, tests, prototipos de curación como referencia.

**Commits del 2026-08-10/11 (segunda tanda) — sprint de robustecimiento integral en 5 fases**, trabajado desde un Proyecto de Claude.ai ("Cowork") y commiteado localmente en esta sesión (quedó hecho pero sin commitear por un `.git/index.lock` stale de esa sesión anterior, ya limpiado):

- **Fase 0-1 — seguridad + aislamiento multi-tenant**: secrets movidos a env vars de Render; `ideas.db` sacado del tracking de git (ver más abajo); `core_data.py` con fixes de `empresa_id` en funciones de escritura que antes permitían tocar datos de otra empresa (mismo fix en `modules_lab.py`); rate limiting básico de login (5 intentos / 15 min → bloqueo 15 min); CI con GitHub Actions corriendo pytest en cada push/PR; base de backup automático diario (`db_backup_scheduler.py`) + bloque de disco persistente documentado y comentado en `render.yaml` (activar solo si se pasa a plan pago de Render).
- **Fase 2 — gaps funcionales QHSE**: 3 módulos nuevos — **Auditorías Internas** (`modules_audits.py`, ISO 9.2), **Revisión por la Dirección** (`modules_management_review.py`, ISO 9.3, con snapshot automático de auditorías/8D/riesgos/KPIs/legal), **Gestión Documental real** (`modules_document_control.py`, repositorio con versiones/estados, distinto de la biblioteca de referencia normativa existente); SST completado (incidentes, matriz de peligros, EPP); y se cerró el gap de curación normativa: ahora "aprobar" una norma deja elegir a qué empresa(s) se publica (`norma_empresa_publicacion`).
- **Fase 3 — marca y experiencia**: tipografía Poppins (self-hosted, `assets/fonts/`) de punta a punta — plataforma, sitio público, iframe de Matriz Legal, PDFs (con embebido de fuente verificado), app mobile; wordmark IDEUS extendido a Matriz Legal y mobile; bug corregido (menú lateral no se mostraba para `EMPRESA_ADMIN`/`EMPRESA_USER`); **exports de PDF (KPIs, mapa de procesos, 8D) movidos a `run.io_bound` con estado de loading en el botón** — antes corrían síncronos sobre el event loop y bloqueaban el websocket de todos los clientes conectados mientras duraba la generación.
- **Fase 4 — deuda técnica y arquitectura**: `requirements.txt` podado (streamlit/pyinstaller/fpdf2/PyMuPDF fuera, sin uso en producción, movidos a `requirements-legacy-portable.txt`); piloto de extracción de capa de servicios — `modules_legal_matrix.py` dividido en `legal_matrix_service.py` (datos/lógica, sin NiceGUI, testeable) + `modules_legal_matrix.py` (solo UI/rutas); **`ADR-001-arquitectura-app-prototipo.md`** (nuevo): recomienda pausar `app/` (ver sección de arquitectura arriba) — pendiente de confirmación de Juan, no una decisión tomada.

Detalle completo, fecha por fecha, en `CHANGELOG_STATUS.txt`.

**Investigado en esta sesión — "connection lost" intermitente en local:** la causa más probable eran justamente los exports de PDF sync mencionados en Fase 3 (ya corregidos ahí). Quedan **sin corregir** otros puntos con el mismo patrón — llamadas bloqueantes directo en el loop de un scheduler async, sin `asyncio.to_thread`/`run.io_bound` — que también pueden gatillarlo: `services/lab_ai_scheduler.py` (llamadas a OpenAI), `services/legal_matrix_alert_scheduler.py` (envío de email SMTP), `services/db_backup_scheduler.py` (copia del archivo de base). `services/legal_curation_scheduler.py` ya está bien resuelto (usa `asyncio.to_thread` a propósito, con comentario explicando por qué). Si el problema persiste después de esta tanda, ahí es donde mirar primero.

## Pendientes conocidos

- Pushear todos estos commits a GitHub y hacer Manual Deploy en Render (`autoDeploy` está en `false`).
- `nicegui_v2/ideas.db` — archivo suelto sin trackear que no debería existir ahí (la app espera `ideas.db` solo en la raíz). Sin confirmar aún si borrarlo.
- Confirmar o corregir la recomendación de `ADR-001` sobre `app/`.
- Decidir si se sube el plan de Render a uno pago para activar disco persistente + backup real.
- Borrar logos demo con marcas de terceros (Pepsi, Adidas, Coca-Cola) y PDFs de prueba generados durante la verificación de Fase 4 (permisos no dejaron borrarlos desde esa sesión).
- Replicar el patrón de extracción de capa de servicios (piloto en Matriz Legal, Fase 4) en el resto de los módulos.
- Wrappear en `asyncio.to_thread`/`run.io_bound` las llamadas bloqueantes que quedan en `lab_ai_scheduler.py`, `legal_matrix_alert_scheduler.py` y `db_backup_scheduler.py` (ver nota de "connection lost" arriba).
- Definir el mapeo empresa↔norma quedó resuelto en Fase 2 — lo que sigue abierto ahí es el resto del roadmap del panel de curación (nada bloqueante conocido).
- Calidad/8D: editar y eliminar acciones D5/D6 individuales desde la tabla, múltiples árboles de 5 Porqués por factor retenido, llevar acciones D5/D6 al PDF ejecutivo.
- Mobile (`SPEC_mobile_legal_matrix_v2.md`): Face ID/WebAuthn, diff de actualizaciones de IDEAS, push notifications, KPIs nuevos del dashboard.

## Accesos y flujo de trabajo

- Login plataforma: usuario `IDEAS`, contraseña `2026`, ruta `/plataforma`.
- **Intérprete correcto para correr local: Python 3.10**, no el `python` por default del PATH. Esta máquina tiene varios Python instalados (3.14 en `C:\Python314`, 3.10 en `C:\Users\RRHH\AppData\Local\Programs\Python\Python310`) y solo el 3.10 tiene NiceGUI y el resto de las dependencias instaladas. Usar la ruta completa: `"C:\Users\RRHH\AppData\Local\Programs\Python\Python310\python.exe" nicegui_v2/app.py` (plataforma, puerto 8502) / `... mobile_legal_matrix/app.py` (mobile, puerto 8600) — correr desde la raíz del repo, con `/` en la ruta (no `\`, si se ejecuta desde Git Bash una barra invertida antes de una letra se come el separador).
- Flujo: editar local → probar local → commit → push a GitHub → si Render no auto-actualiza (`autoDeploy: false`), Manual Deploy → "Deploy latest commit" desde el dashboard.
- Detalle completo de deploy/troubleshooting en `ACTUALIZACION_WEB_IDEAS.txt` (plataforma principal) y `mobile_legal_matrix/DEPLOY_RENDER.md` (mobile).
- Changelog ejecutivo (para uso no técnico) en `CHANGELOG_STATUS.txt` — mantenerlo actualizado con fecha / módulo / qué cambió / impacto / pendientes cuando se cierre trabajo grande.
- Si `git` tira `Unable to create '.git/index.lock': File exists` y no hay ningún proceso `git.exe` corriendo (`tasklist`), es un lock stale de una sesión anterior — borrar `.git/index.lock` a mano y reintentar.
