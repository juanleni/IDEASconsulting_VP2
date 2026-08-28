@echo off
REM Reinicia y abre la plataforma IDEUS local con el ultimo codigo guardado.
REM Doble clic en este archivo cada vez que Cowork (o vos) editen algo y
REM quieran verlo: mata la instancia anterior si quedo corriendo, levanta
REM una nueva y abre el navegador.

echo Cerrando instancia anterior (si habia)...
taskkill /F /FI "WINDOWTITLE eq IDEUS local*" >nul 2>nul

cd /d "%~dp0"
echo Levantando IDEUS local...
start "IDEUS local" "C:\Users\RRHH\AppData\Local\Programs\Python\Python310\python.exe" nicegui_v2\app.py

echo Esperando a que arranque...
timeout /t 5 >nul

start "" "http://localhost:8502/"

echo Listo. La ventana "IDEUS local" que quedo abierta tiene los logs del servidor -- no la cierres mientras estes probando.
