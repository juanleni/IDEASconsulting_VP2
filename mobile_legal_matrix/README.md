# Matriz Legal · Mobile

App para celular de IDEAS Consulting, con un solo módulo: **Matriz Legal**.
Es un proyecto paralelo e independiente de `nicegui_v2/` — no modifica ni
depende de que la plataforma principal esté corriendo. Corre en su propio
proceso NiceGUI, en un puerto distinto (8600), pero reutiliza la misma base
`ideas.db` y funciones ya existentes de `nicegui_v2/modules_legal_matrix.py`
y `nicegui_v2/core_data.py` (login local, normalización de estado,
generación de alertas de vencimiento, log de auditoría) para no duplicar
lógica. Ver `SPEC_mobile_legal_matrix_v2.md` para el detalle de producto de
esta iteración.

## Login

Usa los **mismos usuarios que ya existen** en la plataforma principal (tabla
`usuarios`, misma función `verificar_usuario`, mismo hash `pbkdf2_sha256`).
No hay selector de empresa: el `empresa_id` sale directo del usuario
logueado.

- **EMPRESA_ADMIN** → editor: puede cambiar estado de normas y cargar
  evidencia.
- **EMPRESA_USER** → lector: solo lectura en esta app (ve todo, no puede
  editar ni cargar evidencia). Esta distinción es específica del mobile —
  no cambia nada del comportamiento de esos roles en el escritorio.
- **IDEAS_ADMIN** (staff IDEAS, acceso transversal a todas las empresas):
  bloqueado a propósito en esta versión — se le muestra un aviso pidiendo
  que use la plataforma de escritorio (fuera de alcance, ver spec §1.2).

La sesión persiste en `app.storage.user` (cookie firmada), no hay que
volver a loguearse cada vez que se abre la PWA.

## Qué incluye

- **Splash screen** de marca al abrir la app (logo + anillo de carga, ~1.5s).
- **Header estilo iOS**: marca de IDEAS Consulting, título grande dinámico
  por sección (large title), nombre de empresa + usuario logueado, botón de
  **actualizar** (relee `ideas.db` y corre la detección de vencimientos),
  **campanita de alertas con badge rojo** (se repite en el tab "Alertas" de
  abajo) y botón de **cerrar sesión**.
- **Navegación inferior tipo tab bar de iOS**: translúcida con blur, sin la
  barra indicadora de Material, iconos outline.
- **Inicio**: KPIs (cumplimiento %, normas totales, alertas abiertas,
  próximas a vencer) y barra de estado por categoría.
- **Normas**: buscador, filtro por estado, tarjetas, alta rápida (editor),
  detalle con cambio de estado (editor) y **carga de evidencia** (cámara,
  galería o archivo — un solo control, el selector nativo del SO se encarga
  de las tres opciones).
- **Alertas**: alertas de vencimiento abiertas, botón para resolverlas
  (editor).
- **Sedes**: listado de solo lectura (alta/edición sigue en la plataforma
  principal).

Muestra los datos reales de la plataforma principal en vivo: lo que se
carga en `nicegui_v2` para una empresa aparece acá tal cual, sin pasos de
sincronización.

## Evidencia: detalle técnico

- Los archivos se guardan en `mobile_legal_matrix/evidence_files/{empresa_id}/{requirement_id}/{uuid}.ext`
  — **no** bajo `mobile_legal_matrix/data/`, porque esa carpeta se sirve
  públicamente sin autenticación bajo `/assets` (logo, manifest, íconos).
  Se sirven mediante `/evidence-file/{empresa_id}/{evidence_id}`, una ruta
  que valida sesión + que la empresa coincida antes de devolver el archivo.
- Se registran en la tabla existente `legal_evidence` (la misma que usa el
  escritorio) con un campo nuevo, `source`, agregado de forma aditiva
  (`ALTER TABLE ... ADD COLUMN`, mismo patrón que ya usa `_ensure_tables` en
  `modules_legal_matrix.py`) — la migración vive en `data.py` del lado
  mobile, no se tocó el archivo original.
- **Limitación real, no una decisión de diseño**: no hay forma de saber
  desde JS/HTML si el usuario tocó "Cámara", "Galería" o "Archivo" en el
  selector nativo — el navegador no expone esa información salvo que se
  usen controles separados con el atributo `capture` forzado (lo que
  rompería el "un solo botón" pedido). Por ahora `source` se guarda como
  `'mobile'` para todo lo cargado desde acá; si más adelante hace falta la
  distinción real, la alternativa es dos botones en vez de uno.

## Cómo correrlo

Desde la raíz del repo (necesario porque `ideas.db` se resuelve con ruta
relativa, igual que en `nicegui_v2/app.py`):

```
python mobile_legal_matrix/app.py
```

Por defecto levanta en el puerto `8600` (configurable con la variable de
entorno `MOBILE_LEGAL_MATRIX_PORT`). Para probarlo desde el celular, conectá
el teléfono a la misma red que la PC y abrí `http://<ip-de-tu-pc>:8600` (la
IP se imprime en la consola al arrancar).

## Alcance / próximos pasos (ver spec para el detalle completo)

- **Face ID / WebAuthn** (spec §1.4): todavía no implementado — el login es
  usuario/contraseña únicamente por ahora.
- **Diff de actualizaciones de IDEAS** (spec §3) y **KPIs nuevos** (spec §5):
  no implementados en esta iteración.
- **Push notifications** (spec §4): no implementado — necesita HTTPS real
  (no funciona sobre una IP de LAN en `http://`, ni siquiera en localhost
  para push real) y todavía no está decidido dónde se despliega esto en
  producción. No tiene sentido construirlo hasta resolver eso.
- El logo se sirve desde `mobile_legal_matrix/data/ideas_mark.png` bajo
  `/assets/...`. A diferencia de `nicegui_v2/app.py` (que expone toda la
  raíz del repo en `/assets`), acá `/assets` solo apunta a esa carpeta
  puntual — no expone `ideas.db` ni el resto del repositorio por HTTP.
- Sedes sigue siendo de solo lectura.
- No incluye importación de Excel, auditorías ni exportación a PDF.
