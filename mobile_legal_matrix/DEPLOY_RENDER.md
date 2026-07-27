# Deploy en Render

## Qué hace esta configuración

Se agregó un **segundo servicio** al `render.yaml` de la raíz del repo,
`ideas-mobile-legal-matrix`, junto al servicio existente
`ideas-consulting-v2` (la plataforma de escritorio). Mismo repo, mismo
`requirements.txt`, arranque distinto:

```yaml
- type: web
  name: ideas-mobile-legal-matrix
  runtime: python
  plan: free
  buildCommand: pip install -r requirements.txt
  startCommand: python mobile_legal_matrix/app.py
  autoDeploy: false
  envVars:
    - key: MOBILE_LEGAL_MATRIX_STORAGE_SECRET
      generateValue: true
```

`mobile_legal_matrix/app.py` ya usa el puerto de entorno `PORT` (igual que
`nicegui_v2/app.py`) — no requiere ningún cambio adicional para correr en
Render.

## ⚠️ Importante: esta prueba usa una copia de datos, no la base en vivo

Cada servicio de Render es un contenedor separado con su propio disco. Este
segundo servicio parte de su **propia copia** de `ideas.db` (la que esté en
el repo al momento del deploy) — no comparte en vivo lo que se cargue
después desde la plataforma de escritorio, ni al revés. Sirve para probar
diseño, login, evidencia y Face ID en un teléfono real con HTTPS — no para
validar que los datos estén sincronizados entre ambas apps.

(Si más adelante hace falta que compartan datos en vivo, la opción real es
migrar a una base compartida en red — ej. Render Postgres — en vez de
SQLite local. Es un cambio más grande, no algo para esta prueba.)

También aplica la misma limitación que ya tiene `ideas-consulting-v2`: en
Render free el disco no es persistente entre redeploys — cualquier norma o
evidencia que se cargue durante la prueba se pierde en el próximo deploy,
salvo que se le agregue un disco persistente (paid add-on) desde el
dashboard de Render.

## Pasos (dashboard de Render — no se puede automatizar desde acá)

1. Confirmar que este repo esté subido a GitHub con los últimos cambios.
2. Entrar a `https://render.com` con la cuenta que ya tienen.
3. Si el Blueprint (`ideas-consulting-v2`) ya está conectado a este repo,
   Render va a detectar el nuevo servicio `ideas-mobile-legal-matrix` del
   `render.yaml` solo — buscar la opción de **sincronizar el Blueprint**
   (`Blueprints` → el blueprint existente → "Sync" o similar) en vez de
   crear uno nuevo desde cero.
4. Si no está conectado como Blueprint todavía: `New +` → `Blueprint` →
   conectar el repo → Render va a proponer crear **ambos** servicios
   (`ideas-consulting-v2` y `ideas-mobile-legal-matrix`) a la vez.
5. Confirmar el deploy del servicio `ideas-mobile-legal-matrix`.

## Resultado

Render da una URL pública HTTPS propia para este servicio, por ejemplo:

- `https://ideas-mobile-legal-matrix.onrender.com`

Se abre igual que cualquier página desde el navegador del celular — sin
estar en la misma red que ninguna PC, sin configurar firewall. Al ser HTTPS
real, ahí sí van a funcionar cosas que no podían probarse en LAN por
`http://` (Face ID/WebAuthn, en el momento en que se implemente el lado
servidor).

## Login para probar

Usa los mismos usuarios que ya existen en la copia de `ideas.db` que se
suba con el deploy (ej. los que ya están cargados en Empresa Demo). Un
usuario `EMPRESA_USER`/`EMPRESA_ADMIN` nuevo se puede crear desde la
plataforma de escritorio antes de hacer el deploy, para asegurarse de que
esa copia lo incluya.
