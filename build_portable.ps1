$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$pythonRoot = "C:\Users\RRHH\AppData\Local\Programs\Python\Python310"
$portableRoot = Join-Path $root "portable"
$packageRoot = Join-Path $portableRoot "IDEAS_Portable"
$pythonTarget = Join-Path $packageRoot "python"

if (-not (Test-Path $pythonRoot)) {
    throw "No se encontro el runtime de Python en $pythonRoot"
}

if (Test-Path $packageRoot) {
    Remove-Item -Recurse -Force $packageRoot
}

$null = New-Item -ItemType Directory -Force -Path $packageRoot

Write-Host "Copiando runtime de Python..."
robocopy $pythonRoot $pythonTarget /E /NFL /NDL /NJH /NJS /NP | Out-Null

Write-Host "Copiando archivos de la app..."
Copy-Item IDEASapp.py $packageRoot
Copy-Item ideas_data.py $packageRoot
Copy-Item ideas_utils.py $packageRoot
Copy-Item database.py $packageRoot
Copy-Item portable_start.py $packageRoot
Copy-Item run_portable.bat $packageRoot
Copy-Item DISTRIBUCION.md $packageRoot
Copy-Item ideas.db $packageRoot

if (Test-Path "logo.png") { Copy-Item logo.png $packageRoot }
if (Test-Path "ideas_home_banner.png") { Copy-Item ideas_home_banner.png $packageRoot }
if (Test-Path "Data") { Copy-Item Data $packageRoot -Recurse }

$readmePath = Join-Path $packageRoot "LEEME_PORTABLE.txt"
@"
IDEAS Consulting - Version portable

1. Copiar toda esta carpeta a otra PC con Windows.
2. Ejecutar run_portable.bat
3. La app se abre en el navegador.

Importante:
- No mover archivos fuera de esta carpeta.
- Mantener la carpeta python, Data, logo, banner y base de datos juntos.
- Si el navegador abre antes de tiempo, esperar unos segundos y recargar localhost:8501.
"@ | Set-Content -Encoding UTF8 $readmePath

Write-Host ""
Write-Host "Portable listo en:" $packageRoot
