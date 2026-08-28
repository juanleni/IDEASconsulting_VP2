# ADR-001 — Camino hacia una arquitectura nueva: qué hacer con `app/`

**Estado:** ✅ confirmado por Juan (2026-08-28) — Opción B, pausar `app/` sin borrarlo.
**Fecha:** 2026-08-10.
**Contexto de esta nota:** parte de la Fase 4 (reducción de deuda técnica) del plan de robustecimiento de IDEUS. El plan pedía explícitamente no seguir invirtiendo tiempo en `app/` sin antes documentar y confirmar la decisión — esta nota es esa documentación, no una decisión ya tomada.

## 1. Qué es `app/` hoy

Un prototipo embrionario (~1.440 líneas en 33 archivos) de una arquitectura distinta a la de `nicegui_v2/`: FastAPI + SQLAlchemy async + PostgreSQL (via `asyncpg`) con separación en capas (`api/routers`, `services`, `repositories`, `models`, `schemas`), auth JWT propia, un motor RAG sobre `pgvector` para IA documental, y una UI NiceGUI montada sobre ese FastAPI (`ui.run_with(api)`) en vez de standalone.

Puntos concretos:
- Los archivos datan de mayo de 2026 (2026-05-12 a 2026-05-21 según mtime), aunque `CLAUDE.md` documenta el inicio del prototipo como 2026-07-20 (commit `8eca987`, marcado WIP). Esa discrepancia de fechas no se resolvió — puede deberse a que el commit de julio reorganizó/reescribió trabajo empezado antes; no tuvo impacto en esta evaluación porque de cualquier manera el prototipo sigue sin terminar y sin decisión formal.
- **No arranca en este sandbox tal cual está**: `import app.main` falla (`ModuleNotFoundError: No module named 'jose'`) — la dependencia declarada es `python-jose[cryptography]`, que instala el paquete `jose`, así que es un problema de entorno resoluble, no un bug de código, pero confirma que nadie lo corrió end-to-end recientemente.
- **No tiene tests** (`nicegui_v2/tests/` tiene 63 tests activos; no existe equivalente para `app/`).
- **No está conectado a Render**: `render.yaml` solo hace build/deploy de `nicegui_v2/app.py` y `mobile_legal_matrix/app.py`. La única mención de `app/` en `render.yaml` es un comentario aclarando que la migración a Postgres (que `app/` representa) sigue sin decidirse.
- Requiere Postgres real (`asyncpg`, `pgvector`) — hoy la plataforma corre 100% sobre SQLite (`ideas.db`), sin infraestructura Postgres provisionada en ningún lado.
- No reimplementa ninguno de los módulos funcionales que sí existen en `nicegui_v2/` (Calidad/8D completo, Auditorías, Revisión por la Dirección, SST, Ambiente, Riesgos, KPIs, Matriz Legal, Gestión Documental, Laboratorio, Mapas de proceso). Solo tiene un router de Calidad/8D parcial y un motor RAG.

## 2. Por qué esto necesita una decisión explícita, no "seguir agregando"

`nicegui_v2/` es la plataforma real, en producción, con clientes reales y una base de código que en las Fases 0-3 recibió trabajo serio de hardening (aislamiento multi-tenant, backups, rate limiting, CI, módulos QHSE completos, rebranding). `app/` es un experimento paralelo sin ese nivel de inversión ni de verificación.

Mantener dos frentes de arquitectura activos simultáneamente sin una decisión — "vamos a migrar" o "esto es exploratorio, no lo tocamos por ahora" — tiene un costo real: cualquier feature nueva potencialmente hecha dos veces, confusión sobre dónde vive la lógica de negocio "correcta", y `app/` acumulando código muerto si nadie lo vuelve a tocar (que es lo que pasó entre mayo y agosto).

## 3. Opciones

**Opción A — Migración completa a `app/` (Postgres + FastAPI, con o sin NiceGUI de UI).**
Terminar `app/` hasta que reemplace a `nicegui_v2/` por completo: reimplementar los ~10 módulos QHSE, migrar los datos de SQLite a Postgres, resolver auth/multi-tenant/RLS de forma equivalente a lo que hoy tiene `nicegui_v2/` (que ya pasó por Fase 1 de hardening), y solo entonces cortar el tráfico de producción. Esfuerzo grande (semanas, no días) y riesgo de mantener dos sistemas en paralelo mientras tanto.

**Opción B — Archivar `app/` por ahora, sin borrarlo.**
Dejarlo en el repo como referencia/spike, documentado como "no activo", y enfocar todo el esfuerzo en `nicegui_v2/` (que ya funciona, tiene clientes, y acaba de recibir una ronda completa de hardening). Revisar la decisión más adelante si surge una razón concreta para migrar (ej. SQLite se vuelve un cuello de botella real, o se necesita multi-tenant a nivel de infraestructura que SQLite no puede dar).

**Opción C — Migración incremental, con `app/` como capa de servicios reutilizable.**
En vez de una reescritura completa, extraer gradualmente lógica de `nicegui_v2/` hacia servicios/repositorios al estilo de `app/repositories/base_repository.py`, empezando por los módulos con más deuda técnica, mientras `nicegui_v2/` sigue siendo la UI y el punto de entrada en producción. La extracción de Matriz Legal a `legal_matrix_service.py` (Fase 4, Tarea 35, terminada hoy) es exactamente este patrón aplicado sin tocar `app/` en absoluto — sugiere que no hace falta el prototipo separado para lograr el beneficio de "menos monolito".

## 4. Recomendación

**Opción B, con revisión periódica.** Motivos concretos:

- El costo de terminar `app/` (Opción A) es alto y el beneficio no está cuantificado — no hay una razón documentada de negocio para migrar a Postgres hoy (la limitación real de SQLite, "sin persistencia garantizada entre redeploys de Render free tier", tiene una mitigación mucho más barata: subir a un plan pago de Render y usar disco persistente, ya dejada lista y comentada en `render.yaml`).
- El patrón que se buscaba en `app/` (separación de capas, servicios testeables) ya se está logrando de forma incremental dentro de `nicegui_v2/` sin necesidad de una reescritura completa — Opción C, en la práctica, se puede hacer directamente sobre `nicegui_v2/` sin `app/` como intermediario.
- Mantener `app/` "vivo" pero sin dueño ni roadmap (como pasó de mayo a agosto) es peor que decidir explícitamente pausarlo: evita que alguien invierta tiempo ahí pensando que es el camino ya decidido.

Si en el futuro aparece una razón concreta para Postgres real (multi-tenant a nivel de infraestructura, necesidad de RLS de base de datos, volumen que SQLite no soporte), ahí sí vale la pena retomar `app/` — o empezar de cero con lo aprendido, dado que quedaría desactualizado.

## 5. Qué implica esta recomendación en la práctica (no ejecutado, para confirmar)

- No se declara "muerto" ni se borra `app/` — queda en el repo, sin más inversión, como referencia.
- Se agrega una nota corta en la sección de `app/` de `CLAUDE.md` marcándolo "en pausa, ver ADR-001" para que quede claro para cualquiera (yo en una sesión futura, u otra persona) que no es el camino activo.
- El patrón de extracción de servicios (Tarea 35, Matriz Legal) se toma como el modelo a replicar directamente en `nicegui_v2/`, no como un paso hacia `app/`.

**Confirmado por Juan el 2026-08-28.** `app/` queda en pausa, sin más inversión, como referencia — no se borra. El patrón de extracción de servicios (Tarea 35, Matriz Legal) es el modelo a replicar directamente sobre `nicegui_v2/`, módulo por módulo, según deuda técnica.
