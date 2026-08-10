# Prompt para Claude Code — Matriz Legal Digital: conectores de normativa + panel de curación

Contexto del proyecto:
Trabajo sobre el módulo "Matriz Legal Digital" dentro de la plataforma IDEAS Consulting
(NiceGUI + FastAPI + SQLite, base ideas.db). El módulo ya tiene tablas: legal_requirements,
legal_sites, legal_evidence, legal_audits, legal_alerts, legal_audit_log, legal_matrix_settings.
Todas las tablas usan empresa_id para aislar por cliente (multi-tenant) y los endpoints validan
pertenencia vía _frame_guard. Modelo de roles existente: IDEAS_ADMIN (staff de IDEAS, acceso
global), EMPRESA_ADMIN, EMPRESA_USER.

IMPORTANTE — Separación de responsabilidades (esto define permisos, no solo alcance de tarea):
Todo lo relacionado a scraping, ingesta cruda y clasificación de normativa es una función
EXCLUSIVA e INTERNA del staff de IDEAS Consulting (rol IDEAS_ADMIN). Las empresas clientes
NUNCA acceden a esta capa, ni disparan búsquedas, ni ven normas_raw ni nada del pipeline de
ingesta. IDEAS Consulting es quien releva, actualiza y comunica la normativa. La empresa
cliente solo ve el resultado ya curado y aprobado en legal_requirements/legal_alerts/etc.
Las tablas y endpoints de esta tarea (normas_raw, legal_sources_watch, y los conectores)
deben quedar completamente fuera del alcance de cualquier empresa_id de cliente. No llevan
empresa_id.

## 1. Esquema nuevo

```sql
CREATE TABLE IF NOT EXISTS legal_sources_watch (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nombre_fuente TEXT NOT NULL UNIQUE,   -- "SAIJ - Normativa Provincial", "Digesto SRT", "Boletin Oficial PBA"...
    tipo_conector TEXT,                    -- dataset_abierto | scraper | api | manual
    url_base TEXT,
    frecuencia_recomendada TEXT,           -- mensual | semanal | diaria
    ultima_corrida TEXT,
    activo INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS normas_raw (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    jurisdiccion TEXT NOT NULL,           -- nacional | provincial | municipal | organismo
    provincia TEXT,
    organismo_emisor TEXT,
    tipo_norma TEXT,
    numero TEXT,
    fecha_sancion TEXT,
    fecha_publicacion TEXT,
    titulo TEXT,
    resumen TEXT,
    tema TEXT,                            -- ambiente | sst | ambos | otro
    estado TEXT,                          -- vigente | derogada | modificatoria | sin_eficacia | desconocido
    norma_relacionada TEXT,
    link_fuente TEXT,
    fuente_id INTEGER REFERENCES legal_sources_watch(id),
    primera_vez_detectada TEXT,
    ultima_corrida_detectada TEXT,
    es_nuevo INTEGER DEFAULT 1,           -- true hasta que IDEAS_ADMIN lo revise
    cambio_detectado TEXT,                -- descripción corta si una corrida posterior cambió el estado
    fecha_scraping TEXT,
    revisado_por TEXT,
    fecha_aprobacion TEXT,
    publicado_a_empresa INTEGER DEFAULT 0,
    UNIQUE(fuente_id, provincia, tipo_norma, numero, fecha_sancion)
);
```

## 2. Conectores a integrar (ya prototipados, adjunto la lógica de cada uno — revisala y adaptala al estilo del repo en vez de reescribir desde cero)

**2.1. SAIJ — Normativa Provincial** (dataset_abierto, frecuencia mensual)
- Descarga CSV de `https://datos.jus.gob.ar/dataset/d59c2d29-d561-4ad2-a032-cc82b40db2d3/resource/0ebc70cc-0e71-4158-ab75-9759339e4cbd/download/base-saij-normativa-provincial.csv`
- Filtra por provincia(s) configurada(s) y clasifica tema (ambiente/sst) por palabras clave en título/resumen.
- Campos del CSV: provincia_nombre, tipo_norma, numero_norma, estado_vigencia, fecha, fecha_publicacion, nombre_norma, titulo_resumido, titulo_sumario, informacion_digesto, texto_actualizado, provincia_id.

**2.2. Digesto SRT** (api, frecuencia semanal)
- `POST https://api.srt.gob.ar/v1/resoluciones/full`, Content-Type: application/json.
- Payload: `{NroResolucion, Cantidad, Asunto, OrganismoEmisor, TipoNorma, BoletinOficial, FechaDesde, FechaHasta (ISO), NroExpediente, Voces}`.
- Respuesta: array de `{Tipo, Organismo, Asunto, Link, Subtipo, TieneArchvios, Numero, Anio, Fecha, NumeroAnio, NumeroAnioCorto, OID}`.
- ⚠️ Verificar primero, antes de dar por definitivo el conector:
  - Si `Cantidad` pagina o es un tope absoluto (probar con un rango de fechas amplio y ver si el conteo devuelto se estanca en el valor de `Cantidad`).
  - Este endpoint NO trae el campo "Estado" (vigente/derogada/etc.) que sí menciona la FAQ del sitio (`https://digesto.srt.gob.ar/PreguntasFrecuentes.html`). Buscar si hay un endpoint de detalle por norma (probablemente se dispara al hacer click en un resultado puntual dentro de digesto.srt.gob.ar — inspeccionar de nuevo con DevTools Network si hace falta) que sí traiga ese dato. Hasta confirmarlo, cargar con estado="desconocido".
  - CORS: esta API respondió con `Access-Control-Allow-Origin: *`, así que se puede llamar server-side sin problema. (Confirmado que NO se puede llamar client-side desde un entorno sandboxeado tipo artifact — hacerlo siempre desde el backend.)

**2.3. Boletín Oficial (por organismo, ej. SRT)** (scraper, frecuencia diaria/semanal — usar solo si el punto 2.2 no cubre todo)
- Listado por día: `https://www.boletinoficial.gob.ar/seccion/primera/{AAAAMMDD}?rubro=1715` (rubro=Resoluciones; confirmar que el código no cambió).
- Detalle: `https://www.boletinoficial.gob.ar/detalleAviso/primera/{id}/{AAAAMMDD}`.
- Extracción por regex sobre texto plano (no depender de clases CSS): número (`Resolución (\d+/\d{4})`), fecha de sanción (`Buenos Aires,\s*(\d{2}/\d{2}/\d{4})`), fecha de publicación (`Fecha de publicación\s*(\d{2}/\d{2}/\d{4})`), resumen (primer bloque tras "CONSIDERANDO:").
- Delay mínimo 1.5s entre requests. Confirmar robots.txt vigente antes de desplegar en producción.
- OPDS (opds.gba.gov.ar) está descartado como fuente de scraping directo: su robots.txt lo deniega explícitamente. No intentar.

## 3. Lógica de diff (igual para las tres fuentes)

Al insertar una norma, buscar por `(fuente_id, tipo_norma, numero, fecha_sancion)`:
- No existe → INSERT con `es_nuevo=1`, `primera_vez_detectada=ahora`.
- Existe y `estado` cambió → UPDATE con `es_nuevo=1` y `cambio_detectado="Estado cambió de X a Y"`.
- Existe y sin cambios → solo actualizar `ultima_corrida_detectada`.

## 4. Panel de curación (IDEAS_ADMIN únicamente)

Adjunto mockup de referencia visual (React) con el layout esperado — replicar el comportamiento en NiceGUI, no necesariamente el código React:
- Rail lateral con lista de fuentes conectadas (nombre, punto verde/gris según `activo`, frecuencia).
- Tabla principal de `normas_raw`: número+tipo (monoespaciado), título, jurisdicción, badge de tema (ambiente/sst), estado de vigencia (punto de color), estado de revisión (pendiente/aprobada/rechazada), badge "Nuevo" si `es_nuevo=1`.
- Filtros: texto libre, fuente, tema, estado de revisión.
- Panel de detalle al seleccionar una fila: todos los campos + botón "Aprobar y publicar" (mueve/copia el registro a legal_requirements y pone `publicado_a_empresa=1`, `es_nuevo=0`, `revisado_por=<usuario actual>`, `fecha_aprobacion=ahora`) + botón "Rechazar".
- Botón "Actualizar" por fuente (o global): dispara el conector correspondiente **desde el backend** (endpoint FastAPI, nunca fetch directo desde el navegador — ya confirmamos que un fetch client-side a estas APIs no funciona en entornos sandboxeados, y además expondría estas llamadas fuera del control de IDEAS_ADMIN). Mientras corre, mostrar estado de carga; al terminar, refrescar la tabla y mostrar cuántas normas nuevas/actualizadas trajo.

## 5. Scheduler

Job programado (APScheduler embebido en la app FastAPI) por fuente, respetando `frecuencia_recomendada` de cada una en `legal_sources_watch`. Loggear cada corrida (éxito/error, cantidad nuevas/actualizadas) en algún lado visible para IDEAS_ADMIN — puede ser una extensión simple de legal_audit_log o una tabla nueva `legal_sync_log` si conviene más.

## 6. Qué pedirte que hagas primero, antes de escribir todo el código

1. Confirmar en el repo real los nombres exactos de columnas/tablas existentes que puedan chocar con esta propuesta.
2. Correr el conector de Digesto SRT en modo dry-run contra un rango de fechas chico y confirmar la paginación antes de dejarlo automático.
3. Preguntarme si algo de esto no coincide con una decisión que ya tomamos y no quedó reflejada acá.
