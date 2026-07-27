# Spec técnica — App mobile Matriz Legal (IDEAS Consulting)

**Para:** Claude Code
**Contexto de partida:** ya existe un prototipo funcional en `mobile_legal_matrix/`
(NiceGUI, puerto 8600, reutiliza `nicegui_v2/modules_legal_matrix.py` y
`nicegui_v2/core_data.py` contra la misma `ideas.db`). Este documento define
el siguiente salto: de PoC a app usable por el cliente final.

**No romper:** `nicegui_v2/app.py` sigue siendo la plataforma principal de
escritorio. Todo lo de acá vive en `mobile_legal_matrix/`, reutilizando
funciones existentes en vez de duplicar lógica, tal como se viene haciendo.

---

## 0. Resumen de alcance de esta iteración

1. Login real (reutilizando usuarios existentes) + Face ID/WebAuthn
2. Splash screen de marca
3. Carga de evidencia con cámara / galería / archivo
4. Notificaciones push (vencimientos + actualizaciones de IDEAS)
5. Nuevos KPIs en el dashboard mobile
6. Cambios de modelo de datos necesarios para soportar 1, 4 y 5

Fuera de alcance por ahora (backlog, no bloquea esta entrega): auditorías
completas, importación de Excel, exportación a PDF, notificaciones push de
otros módulos que no sean Matriz Legal.

---

## 1. Login

### 1.1 Decisión de producto (ya confirmada)
- **No hay selector de empresa.** El usuario ingresa usuario + contraseña y
  el servidor resuelve `empresa_id` a partir de ese usuario.
- Los usuarios son **los mismos que ya existen** en la plataforma principal
  — no se crea un sistema de usuarios paralelo.
- Face ID / biometría del dispositivo: **habilitado**, como método
  secundario post-primer-login (no reemplaza usuario/contraseña, la
  complementa).

### 1.2 Modelo de usuarios (confirmado)
Hay dos poblaciones de usuario claramente distintas — el modelo de datos y
el login tienen que reflejar esta diferencia desde el arranque, no
agregarla después como parche:

- **Usuarios cliente**: pertenecen a **una sola empresa**, siempre. No hay
  ambigüedad de "a qué empresa entro" — el `empresa_id` sale directo del
  usuario. Roles dentro de esta población:
  - **Lector**: ve todo, no puede cambiar nada.
  - **Editor**: puede cambiar estado de normas y cargar evidencia.
- **Usuarios IDEAS** (el prestador del servicio, no un cliente): acceso
  transversal a todas las empresas. Roles:
  - **Admin general**: puede operar sobre cualquier empresa (ej. cargar una
    `ideas_update`, ver KPIs cruzados, dar soporte).
  - **Super admin**: además de lo anterior, gestión de usuarios/empresas y
    configuración global.

Esto significa que la tabla/lógica de usuarios necesita un campo de tipo de
cuenta (`account_type`: `client` / `ideas_staff`) además del rol
(`reader`/`editor` para clientes, `admin`/`superadmin` para IDEAS), y que
`empresa_id` es **obligatorio y fijo** para usuarios `client`, pero
**nulo/no aplica** (o "todas") para usuarios `ideas_staff` — su alcance de
empresa se decide en cada pantalla/acción, no en el login.

Para esta primera versión del mobile alcanza con soportar bien el login de
**usuarios cliente** (que es el 100% del uso diario en el celular). El
acceso de usuarios IDEAS puede quedar reservado a la plataforma de
escritorio por ahora — no hace falta construirle una vista mobile propia en
esta entrega, pero el modelo de datos de abajo ya lo deja preparado para
cuando se decida sumarlo.

### 1.3 Implementación
- Reutilizar la función de autenticación ya existente en `nicegui_v2`
  (revisar y confirmar el nombre exacto — se mencionó
  `verificar_login_empresa` o equivalente — y su contrato: qué recibe, qué
  devuelve, si ya distingue `account_type` o si hoy asume que todo usuario
  es de tipo cliente).
- Sesión: token (JWT o cookie de sesión firmada) que fija `empresa_id`,
  `account_type` y `rol` del usuario logueado. Sesión persistente para no
  re-loguear cada vez que se abre la PWA.
- HTTPS obligatorio en todo el flujo (además, es requisito duro para
  service workers y push — ver sección 4).

### 1.4 Face ID / biometría — WebAuthn
- Usar la API estándar del navegador `WebAuthn` (`navigator.credentials`),
  no una librería de terceros.
- Flujo:
  1. Primer login: usuario + contraseña, éxito → ofrecer "¿Querés activar
     Face ID para la próxima vez?".
  2. Si acepta: se registra una credencial (`navigator.credentials.create`)
     ligada a ese dispositivo y usuario, y se guarda el `credential_id` del
     lado del servidor asociado al usuario (tabla nueva, ver sección 6).
  3. Logins siguientes desde ese mismo dispositivo: se ofrece el botón
     "Ingresar con Face ID" que dispara
     `navigator.credentials.get()` — si la validación biométrica es
     exitosa, el servidor emite sesión sin pedir contraseña de nuevo.
- Este flujo es 100% estándar de la industria (es lo mismo que usan bancos
  y apps grandes en web) — no requiere hardware/SDK propietario de Apple ni
  de Google.

### 1.5 Splash screen
- Fondo blanco, logo de IDEAS Consulting centrado, indicador de carga
  moderno (anillo con `stroke-dasharray`, no el spinner default del
  navegador).
- Duración mínima artificial de ~1.5-2 segundos aunque la carga real sea
  instantánea, para que se sienta "pro" y no parpadee.
- Aprovechar esos 1.5-2 segundos para precargar en paralelo los datos del
  dashboard (KPIs, alertas) para que al terminar el splash la home ya esté
  lista — evita un segundo loading inmediatamente después.
- Definir un tope máximo (ej. 4 segundos): si la carga real no terminó,
  mostrar igual la app con lo último cacheado en vez de dejar al usuario
  pegado en el splash.

---

## 2. Carga de evidencia (cámara / galería / archivo)

### 2.1 UX
- Un solo control de "Adjuntar evidencia" que abre el selector nativo del
  sistema operativo con las tres opciones (tomar foto / elegir de galería /
  elegir archivo) — igual al selector de adjuntos de Claude.
- Esto se logra con un único `<input type="file" accept="image/*,application/pdf" capture="environment">`
  — el menú con las tres opciones lo arma el propio SO (iOS/Android) al
  tocar el input, **no hay que construir un selector custom**.
- En NiceGUI: `ui.upload()` ya envuelve este input; configurar `accept` y
  no restringir a una sola fuente.

### 2.2 Backend
- Guardar el archivo en
  `mobile_legal_matrix/data/evidence/{empresa_id}/{requirement_id}/{uuid}.{ext}`
  — **no** en la carpeta que ya sirve `/assets` sin restricción, para no
  exponer archivos de evidencia vía HTTP directo sin control de acceso.
- Registrar en la tabla existente `legal_evidence` (reutilizar, no
  duplicar): referencia al archivo, `requirement_id`, `empresa_id`,
  usuario que la cargó, fecha, y — nuevo — el **origen** (`camera`,
  `gallery`, `file`) para tener trazabilidad de cómo se generó cada
  evidencia.
- Validar tipo de archivo y tamaño máximo en el servidor (no confiar solo en
  el `accept` del input, que es solo una sugerencia del lado cliente).

---

## 3. Diff / historial de actualizaciones de IDEAS

Requisito previo indispensable para que las notificaciones de "norma
actualizada por IDEAS" tengan contenido real (no solo "algo cambió").

### 3.1 Modelo
- Cuando una actualización de norma se origina desde el lado de IDEAS (vs.
  un cambio de estado hecho por un usuario de la empresa), guardar:
  - qué campos cambiaron (ej. `proxima_revision`, texto del requisito,
    categoría)
  - valor anterior y valor nuevo de cada campo
  - timestamp y origen = `ideas_update`
- Esto puede ser una fila nueva en `legal_audit_log` con un campo
  `change_type` (`ideas_update` vs. `user_status_change` vs. `user_edit`) y
  un campo `diff` (JSON con los pares campo/antes/después).
- El dashboard/detalle de norma muestra este diff en un bloque destacado
  ("Actualizada por IDEAS · qué cambió") — ya validado en el mockup.

### 3.2 Quién dispara esto
- A definir con el equipo de contenido/legal de IDEAS: ¿la actualización
  normativa hoy la carga alguien manualmente en `nicegui_v2`, o hay (o
  habrá) un proceso de scraping/carga masiva? Esto no cambia el modelo de
  datos de arriba, pero sí determina si hace falta una UI de "actualización
  masiva" en la plataforma principal.

---

## 4. Notificaciones push

### 4.1 Realidad técnica a comunicarle al cliente (importante)
- **Android**: push funciona igual que cualquier notificación nativa, sin
  restricciones relevantes.
- **iPhone/Safari**: push **solo** funciona si el usuario instaló la PWA en
  la pantalla de inicio (no funciona con una pestaña de Safari abierta,
  aunque el usuario haya dado permiso). Requiere iOS 16.4+ (cobertura real
  hoy: prácticamente toda la base de iPhones activos).
- Consecuencia de producto: el flujo de "agregar a pantalla de inicio" que
  ya existe deja de ser solo estético — es **requisito funcional** para que
  las alertas push lleguen en iPhone. Conviene reforzar el onboarding con
  un mini-tutorial la primera vez que el usuario entra desde Safari sin
  tenerla instalada.

### 4.2 Stack sugerido
- Librería: `pywebpush` (Python, compatible con el stack actual).
- Claves VAPID (par pública/privada) generadas una sola vez para todo el
  servidor — identifican al backend ante los navegadores.
- Nueva tabla `push_subscriptions`: `empresa_id`, `user_id`, `endpoint`,
  `keys` (p256dh + auth), `created_at`, `user_agent` (útil para debug).
- Service worker (`sw.js`) en `mobile_legal_matrix/`: recibe el evento
  `push`, muestra la notificación con `title`/`body`, y al tocarla abre la
  app en la pantalla correspondiente (ej. detalle de la norma).

### 4.3 Disparadores concretos
1. **Vencimiento de norma**: enganchar el envío push al mismo momento en
   que `generar_alertas_vencimientos` crea una fila nueva en `legal_alerts`
   — mismo scheduler, se le agrega un paso más al final, sin duplicar la
   lógica de detección de vencimientos que ya existe.
2. **Actualización por IDEAS**: dispara cuando se guarda un registro con
   `change_type = ideas_update` (ver sección 3) — el texto de la
   notificación puede armarse directamente del `diff` guardado (ej. "Res.
   123/2026 actualizada: nueva fecha de revisión 08/08/2026").
3. Ambos casos: solo se envía a los usuarios de la `empresa_id`
   correspondiente que tengan una suscripción activa (tabla 4.2) y — a
   futuro, si se suma multi-sede — filtrando por sede si corresponde.

### 4.4 Suscripción del lado cliente
- Al loguearse (o desde una pantalla de "Notificaciones" en ajustes), pedir
  permiso de notificaciones y registrar la suscripción
  (`PushManager.subscribe`) contra el backend.
- Si el usuario está en iPhone y no instaló la PWA todavía, mostrar el
  aviso de "para recibir alertas en tu iPhone, agregá la app a tu pantalla
  de inicio" en vez de fallar silenciosamente.

---

## 5. KPIs nuevos en el dashboard mobile

Sumar al dashboard actual (que ya tiene % cumplimiento global, normas
totales, alertas abiertas, vencen en 30 días):

| KPI | Fuente | Notas |
|---|---|---|
| % auditorías planificadas vs. realizadas | `legal_audits` | Requiere que esa tabla tenga fecha planificada vs. fecha real, confirmar si ya existe ese campo |
| Antigüedad promedio de alertas sin resolver | `legal_alerts` | `now() - fecha_creacion` promedio de las abiertas |
| Normas actualizadas por IDEAS (últimos 30 días) | `legal_audit_log` filtrando `change_type = ideas_update` | Ya vista en el mockup de Inicio |
| Vencen en 7 días (además del de 30) | `legal_alerts` / `legal_requirements` | Da urgencia inmediata sin abrir el detalle |

Dejar explícitamente **fuera** del mobile (quedan solo en el dashboard de
escritorio): tendencias históricas, comparativas entre sedes, tiempo de
ciclo de investigación detallado — son de uso más analítico y compiten mal
en pantalla chica.

---

## 6. Cambios de modelo de datos (resumen para no perder nada)

Tablas nuevas:
- `push_subscriptions` (empresa_id, user_id, endpoint, keys_p256dh,
  keys_auth, user_agent, created_at)
- `webauthn_credentials` (user_id, credential_id, public_key, device_label,
  created_at, last_used_at)

Cambios sobre tablas existentes:
- `legal_evidence`: agregar campo `source` (`camera` / `gallery` / `file`)
- `legal_audit_log`: agregar `change_type` (`ideas_update` /
  `user_status_change` / `user_edit`) y `diff` (JSON)
- `legal_audits` (a confirmar si falta): campo de fecha planificada
  separado de fecha real, si no existe ya
- Tabla de usuarios (la que ya exista en `nicegui_v2`): agregar
  `account_type` (`client` / `ideas_staff`). Para `client`, `empresa_id`
  sigue siendo obligatorio y único como hoy. Para `ideas_staff`, rol
  (`admin` / `superadmin`) determina alcance transversal — no se le fija
  una `empresa_id` en el login.

---

## 7. Orden de implementación sugerido

1. **Evidencias con cámara/galería/archivo** — bajo riesgo, alto impacto
   visible, no depende de nada más de esta lista.
2. **Login real + roles + Face ID** — bloqueante para sacar esto de modo
   PoC; sin esto, cualquiera en la red ve/edita la matriz de la empresa.
3. **Modelo de diff de IDEAS** (sección 3) — necesario antes del punto 4.
4. **Push notifications** — depende de 2 (HTTPS + usuarios identificados) y
   de 3 (contenido real del mensaje).
5. **KPIs nuevos del dashboard** — el más independiente, se puede hacer en
   paralelo con cualquiera de los anteriores.

---

## 8. Preguntas abiertas que quedan pendientes de decidir (no bloquean el
arranque, pero conviene resolver pronto)

- ~~¿Un usuario puede tener más de una empresa asociada hoy?~~ Resuelto:
  usuarios cliente pertenecen a una sola empresa siempre; los usuarios
  IDEAS (admin general / super admin) son una población aparte con acceso
  transversal — ver sección 1.2.
- ¿La tabla de usuarios actual en `nicegui_v2` ya distingue de alguna forma
  usuarios IDEAS de usuarios cliente, o hoy todos se tratan igual y hay que
  introducir `account_type` desde cero? (afecta el esfuerzo real de 1.2/1.3)
- ¿Cómo se genera hoy una `ideas_update` — carga manual o hay planes de
  automatizarla? (afecta 3.2, no afecta el modelo de datos)
- ¿`legal_audits` ya tiene fecha planificada vs. fecha real, o hay que
  agregarla? (afecta KPI de sección 5)
- Distribución final: ¿PWA (como ahora) o se evalúa empaquetado nativo más
  adelante? — no cambia nada de esta entrega, pero condiciona cuánto
  esfuerzo vale la pena poner en pulir el "agregar a inicio".

---

## Addendum — respuestas confirmadas contra el código real (2026-07-27)

Investigación hecha antes de implementar, contra `nicegui_v2/core_data.py` y
`nicegui_v2/modules_users.py`:

- **La tabla `usuarios` ya distingue cliente vs. IDEAS staff**, no hizo
  falta agregar `account_type`. `rol` ∈ `{IDEAS_ADMIN, EMPRESA_ADMIN,
  EMPRESA_USER}`; `IDEAS_ADMIN` tiene `empresa_id` null (transversal),
  `EMPRESA_ADMIN`/`EMPRESA_USER` tienen `empresa_id` fijo y obligatorio.
  Coincide exactamente con el modelo de esta spec.
- **La función real es `verificar_usuario(username, password)`** (no
  `verificar_login_empresa`, que es un login distinto por-empresa sin
  identidad de persona, usado en el portal público). Es la misma que usa
  el fallback local de `nicegui_v2/pages_platform.py:/plataforma` cuando la
  API remota no responde. Hash `pbkdf2_sha256`, igual esquema que ya se
  reutilizaba en Matriz Legal.
- **No existía "Lector" como rol propio** — se implementó como mapeo
  específico del mobile: `EMPRESA_ADMIN` → editor, `EMPRESA_USER` → lector
  (sin cambiar nada del comportamiento de esos roles en el escritorio).
- **`legal_audits` no tiene fecha planificada/real como columnas
  separadas**, pero `fecha` (programada) + `resultado` + `fecha_cierre`
  alcanza para el KPI de la sección 5 sin tocar el schema.
- Implementado en esta entrega: **login real (usuario/contraseña) +
  splash + evidencia**. Face ID/WebAuthn, diff de IDEAS, push y los KPIs
  nuevos quedan para una próxima iteración — push en particular no se
  puede probar sin HTTPS real, así que no tiene sentido construirlo todavía.
