# SPEC — Migración de diseño visual del demo IDEUS a `nicegui_v2/` (producción)

**Fecha:** 2026-09-03
**Para:** Claude Code, trabajando sobre el repo real (`nicegui_v2/`)
**Origen:** demo interactivo standalone (`IDEUS_demo_DALFILM.html`) armado como pieza comercial, cuyo sistema visual y de interacción le gustó más a Juan que el actual.

---

## Instrucciones para Claude Code — leer antes de tocar nada

1. **No crear ninguna tabla ni módulo sin auditar primero.** Antes de ejecutar cualquier `CREATE TABLE` de este documento, buscar en el repo (`modules_*.py`, `database.py`, el schema de `ideas.db`) si ya existe algo equivalente con otro nombre. Si existe, adaptar/renombrar en vez de duplicar.
2. **Las tres tablas de la sección 2** (`kpi_dashboards`, `procesos_mapa`, `kpi_historial`) están marcadas como "nuevas" porque, hasta donde sabemos, no existe nada parecido — pero confirmarlo igual antes de crearlas es más barato que descubrir un duplicado después.
3. **SST es el caso especial (sección 4): no construir nada nuevo ahí todavía.** Primero inventariar qué existe hoy en `modules_sst.py` (LTA, ausentismo, permisos de trabajo, análisis de accidentes) y reportar el hallazgo — recién con esa respuesta se decide si es reskin o desarrollo nuevo. Si hay dudas, preguntar antes de escribir código, no asumir.
4. **Todo lo que no esté en la sección 2** es reskin: reusar los datos y la lógica de negocio que ya existen en cada `modules_*.py`, solo cambiando la capa visual con las clases de `ideus_design_system.css`. Ningún valor puede quedar hardcodeado como en el demo.
5. Si algo de este documento no coincide con lo que el código real muestra (un módulo que se suponía que no existía, una tabla con otro nombre haciendo lo mismo), **el código real manda** — este spec es una guía de diseño, no la fuente de verdad del estado del repo.

---

## 0. Lo más importante: esto es un reskin, no un reemplazo de arquitectura

El demo es HTML/CSS/JS estático con **datos 100% inventados, hardcodeados en JS** (no hay backend, no hay `ideas.db`, no hay autenticación real). La plataforma real sigue siendo NiceGUI + FastAPI + SQLite, con `app.py` como shell/router y un `modules_*.py` por área. **No se reemplaza esa arquitectura.** Lo que se migra es:

- La paleta, tipografía y el "lenguaje visual" de los componentes (tarjetas, tabs, tablas, diagramas).
- Los patrones de interacción (menú con indicador deslizante, tabs funcionales, tarjetas de proceso clickeables, gráficos por KPI).

NiceGUI permite esto sin fricción: soporta CSS propio vía `ui.add_css()`, HTML/JS custom vía `ui.html()` y `ui.run_javascript()`, y componentes Vue a medida. Ningún patrón del demo queda afuera por limitación técnica — todo es cableado, no reescritura de framework.

**Regla de oro para todo este trabajo:** ningún valor que en el demo está hardcodeado (KPIs, tendencias, contenido de los diagramas de tortuga, notificaciones) puede quedar hardcodeado en producción. Todo tiene que salir de `ideas.db` a través de los `modules_*.py` existentes, o de las tablas nuevas descriptas en la sección 2.

---

## 1. Archivos entregados

| Archivo | Contenido | Uso |
|---|---|---|
| `ideus_design_system.css` | Tokens de color/tipografía + todas las clases de componente (`.ideus-*`), namespaced para no chocar con clases de Quasar/Tailwind que ya usa NiceGUI | Cargar una vez, globalmente, con `ui.add_css(Path('ideus_design_system.css').read_text())` en `app.py` |
| `ideus_charts.js` | Funciones puras: `ideusMoveIndicator()`, `ideusGaugeSVG()`, `ideusBarsSVG()`, `ideusStreakHTML()`, `ideusKpiChartHTML()` | Cargar una vez vía `ui.add_body_html('<script>' + Path('ideus_charts.js').read_text() + '</script>')`, después invocar desde Python con `ui.run_javascript(...)` cada vez que haya que (re)dibujar un gráfico |

Todas las clases CSS llevan el prefijo `ideus-` a propósito, para poder convivir con las clases de Quasar sin colisión y para que sea fácil de encontrar/reemplazar si en el futuro se decide sacar todo a un design token system más formal.

---

## 2. Datos nuevos que esto requiere (no existen hoy en `ideas.db`)

Dos features del demo son genuinamente nuevas — no son solo "reskin", son funcionalidad que hoy no existe en la plataforma real:

### 2.1. Dashboards de KPI personalizados ("Mis dashboards")

En el demo, el usuario arma un dashboard eligiendo KPIs de distintos procesos y le pone un nombre (ej. "Reunión de Producción"). En el demo esto vive en una variable JS que se pierde al recargar — **eso no sirve para producción**, tiene que persistir por usuario/empresa.

Tabla nueva sugerida:

```sql
CREATE TABLE kpi_dashboards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id),
    nombre TEXT NOT NULL,
    kpi_ids TEXT NOT NULL,        -- JSON array de strings, ej. '["k-plan","k-cal"]'
    creado_en TEXT NOT NULL,
    actualizado_en TEXT NOT NULL
);
```

Y una **biblioteca de KPIs disponibles** (el demo la define como un array fijo en JS con 21 KPIs de ejemplo). En producción, esta biblioteca no puede ser un array fijo — tiene que reflejar los KPIs *que ese `modules_*.py` ya calcula* para la empresa logueada. Recomendación: un registro central simple,

```python
# kpi_registry.py — un dict o función por módulo que expone qué KPIs ofrece
KPI_REGISTRY = {
    'k-amb': {'label': 'Cumplimiento — Ambiente', 'cat': 'Ambiente', 'chart': 'gauge',
               'fetch': lambda empresa_id: modules_ambiente.get_cumplimiento_pct(empresa_id)},
    'k-sst': {'label': 'Cumplimiento — SST', 'cat': 'SST', 'chart': 'gauge',
               'fetch': lambda empresa_id: modules_sst.get_cumplimiento_pct(empresa_id)},
    # ...
}
```

Cada módulo (`modules_ambiente.py`, `modules_sst.py`, etc.) expone una función `get_kpis_disponibles(empresa_id)` que devuelve sus propios KPIs con esta forma; `kpi_registry.py` los agrega todos. Así, si mañana se agrega un módulo nuevo, sus KPIs aparecen solos en el armador sin tocar el armador en sí.

### 2.2. Mapas de proceso con diagrama de tortuga

Hoy `modules_*.py` no tiene un módulo de "Mapas de proceso" con contenido real — en el demo, el contenido de cada tortuga (entradas, salidas, recursos, método, KPIs) está hardcodeado en HTML. En producción esto necesita ser **editable por un `EMPRESA_ADMIN` o `IDEAS_ADMIN`**, no fijo en el código.

Tabla nueva sugerida:

```sql
CREATE TABLE procesos_mapa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL REFERENCES empresas(id),
    nombre TEXT NOT NULL,                  -- "Producción", "Calidad", etc.
    tipo TEXT NOT NULL,                    -- 'turtle' | 'simple'
    icono TEXT,                            -- emoji o nombre de ícono
    responsable TEXT,
    objetivo TEXT,
    -- Solo si tipo = 'turtle':
    entradas TEXT,          -- JSON array de strings
    salidas TEXT,           -- JSON array de strings
    recursos TEXT,          -- JSON array de strings ("¿con qué?")
    con_quien TEXT,         -- JSON array de strings
    metodo TEXT,            -- JSON array de strings ("¿cómo?")
    kpi_ids TEXT,           -- JSON array, referencia a KPI_REGISTRY (para el link "Ver panel de KPIs")
    -- Solo si tipo = 'simple':
    flujo TEXT,             -- JSON array de 3 strings (entrada/paso/salida)
    orden INTEGER DEFAULT 0
);
```

Con esto, un módulo nuevo `modules_mapas_proceso.py` (CRUD simple) reemplaza el contenido hardcodeado del demo, y el `EMPRESA_ADMIN` puede cargar/editar los procesos de su propia empresa sin tocar código.

### 2.3. Historial para los mini-gráficos de tendencia (`ideusBarsSVG`)

Los sparklines de 6 barras necesitan una serie histórica. Para KPIs que ya son agregables desde tablas existentes (ej. "No conformidades abiertas" agrupadas por mes desde la tabla de reclamos), se puede calcular al vuelo con una query `GROUP BY strftime('%Y-%m', fecha)`. Para KPIs que **no** son naturalmente históricos en el esquema actual (ej. un "% de cumplimiento" que hoy se guarda como valor único, no serie temporal), hace falta una tabla de snapshots:

```sql
CREATE TABLE kpi_historial (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    empresa_id INTEGER NOT NULL,
    kpi_id TEXT NOT NULL,
    periodo TEXT NOT NULL,      -- '2026-08'
    valor REAL NOT NULL
);
```

poblada por un job mensual simple (mismo patrón que el scheduler que ya existe para alertas de vencimiento de normas).

---

## 3. Mapeo de componentes — módulos existentes

| Componente del demo | Clase(s) CSS | Módulo real a restylear | Notas |
|---|---|---|---|
| Sidebar + indicador deslizante | `.ideus-sidebar`, `.ideus-nav-indicator`, `.ideus-nav-item` | `app.py` (shell/router) | El indicador requiere JS: en cada navegación, llamar `ideusMoveIndicator()` vía `ui.run_javascript()` pasándole los `id`/selector del ítem activo |
| Topbar con logo de la empresa | `.ideus-topbar`, `.ideus-client-badge` | `app.py` | Usar el logo ya cargado por empresa (si no existe ese campo en `empresas`, agregarlo — `logo_url` o `logo_blob`) |
| Tabs funcionales (subnavegación) | `.ideus-tabs`, `.ideus-tab` | Cualquier módulo con subsecciones — el caso de referencia es SST (Matriz de riesgo / Incidentes / LTA / Ausentismo / Permisos / Análisis) | Si `modules_sst.py` no tiene hoy submódulos de LTA/Ausentismo/Permisos, ver sección 4 |
| Tarjetas KPI + gráficos | `.ideus-kpi-card`, `.ideus-kpi-chart` | `pages_management.py` (dashboard) + `kpi_registry.py` nuevo | Usar `ideusKpiChartHTML()` para generar el SVG del lado del cliente, o generarlo server-side y mandarlo ya armado — cualquiera de las dos funciona |
| Armador de dashboards personalizados | `.ideus-kpi-picker`, `.ideus-dash-name-input` | Módulo nuevo, `modules_kpi_dashboards.py` | CRUD sobre `kpi_dashboards` (sección 2.1) |
| Mapas de proceso (grilla + tortuga) | `.ideus-process-grid`, `.ideus-turtle-grid` | Módulo nuevo, `modules_mapas_proceso.py` | CRUD sobre `procesos_mapa` (sección 2.2) |
| Tablas de datos con pills de estado | `table.ideus-data`, `.ideus-pill` | Todos los módulos con listados (Matriz Legal, Documentos, Calidad/8D, etc.) | Reemplaza las tablas actuales de Quasar (`ui.table`) por HTML propio vía `ui.html()`, o se restylean los componentes `ui.table` existentes con estas clases |
| Layout de detalle (split + volver) | `.ideus-split`, `.ideus-back-link` | Vistas de detalle existentes (detalle de norma, detalle de documento, etc.) | |
| Kanban de Calidad/8D | `.ideus-kanban`, `.ideus-kcard` | `modules_calidad.py` | Ya existe la lógica de 8D — esto es puramente visual |

---

## 4. Sobre el módulo SST ampliado

El demo le agregó a SST cuatro pestañas que **no sabemos si existen hoy** en `modules_sst.py`: gestión de LTA (Lost Time Accident), días perdidos por enfermedad, formularios de trabajo seguro (permisos), y análisis de accidentes (5 Porqués). Antes de que Claude Code encare el reskin de SST, confirmar con Juan si esas cuatro funcionalidades:

- (a) ya existen en `modules_sst.py` con otro nombre/forma, y solo hay que restylear, o
- (b) son funcionalidad nueva que hay que construir de cero (tablas, CRUD, todo), inspirada en lo que se armó como mockup en el demo.

Es la diferencia entre "un día de reskin" y "una funcionalidad nueva completa" — vale la pena confirmarlo antes de estimar.

---

## 5. Plan de migración sugerido (incremental)

No tocar todo junto — la plataforma está en producción y sirviendo clientes reales (DALFILM entre ellos). Orden sugerido, de menor a mayor riesgo:

1. **Cargar `ideus_design_system.css` globalmente** (cambio de bajo riesgo — no rompe funcionalidad, solo estética) y restylear el shell (sidebar + topbar + indicador) en `app.py`. Esto ya cambia la sensación general de toda la plataforma con un solo cambio.
2. **Restylear el dashboard principal** (`pages_management.py`) con las tarjetas KPI nuevas, usando los KPIs que ya se calculan hoy (sin el armador personalizado todavía).
3. **Restylear un módulo de listado** (buen candidato: Matriz Legal Digital, que es el más activo) con `table.ideus-data` + `.ideus-pill`, como piloto antes de replicar al resto.
4. **Construir el armador de dashboards personalizados** (tabla `kpi_dashboards` + `kpi_registry.py`) — funcionalidad nueva, sección 2.1.
5. **Construir Mapas de proceso** (tabla `procesos_mapa` + CRUD + vista de tortuga) — funcionalidad nueva, sección 2.2, probablemente el paquete de trabajo más grande de todos.
6. **Confirmar y resolver SST ampliado** (sección 4) al final, una vez decidido si es reskin o funcionalidad nueva.

---

## 6. Fuente de referencia

El archivo `IDEUS_demo_DALFILM.html` (adjunto en el proyecto) es la referencia visual pixel-a-pixel de cómo se ve cada patrón terminado — útil para comparar contra el resultado del reskin en cada paso. No es código para copiar tal cual (es HTML/JS estático con datos falsos), es la maqueta a igualar visualmente con datos reales.
