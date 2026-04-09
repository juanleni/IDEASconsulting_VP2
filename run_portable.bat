@echo off
setlocal

cd /d "%~dp0"

set "PYTHON_DIR=%~dp0python"
set "PYTHON_EXE=%PYTHON_DIR%\python.exe"

if not exist "%PYTHON_EXE%" (
    echo No se encontro el runtime de Python en:
    echo %PYTHON_EXE%
    pause
    exit /b 1
)

"%PYTHON_EXE%" "%~dp0portable_start.py"

endlocal
