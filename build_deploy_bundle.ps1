$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

$distRoot = Join-Path $root "dist"
$bundleRoot = Join-Path $distRoot "deploy_bundle"

if (Test-Path $bundleRoot) {
    Remove-Item -Recurse -Force $bundleRoot
}

$null = New-Item -ItemType Directory -Force -Path $bundleRoot

# Carpetas/fuentes necesarias para ejecutar la app en servidor.
$includeDirs = @(
    "nicegui_v2",
    "assets",
    "Data",
    "Biblioteca"
)

$includeFiles = @(
    "database.py",
    "ideas_utils.py",
    "requirements.txt",
    "render.yaml",
    "ideas.db",
    "logo.png",
    "ideas_home_banner.png"
)

# Patrones de exclusion seguros (solo artefactos de entorno / peso).
$excludeDirs = @(
    "__pycache__",
    ".git",
    ".vscode",
    ".nicegui",
    "portable",
    "reportes",
    "uploads",
    "backups",
    "notebooklm_package",
    "notebooklm_export",
    "dist"
)

$excludeFiles = @(
    "*.pyc",
    "*.pyo",
    "*.log",
    "direct_stdout.txt",
    "direct_stderr.txt"
)

Write-Host "Armando deploy bundle en $bundleRoot"

foreach ($dir in $includeDirs) {
    if (-not (Test-Path $dir)) { continue }
    $source = Join-Path $root $dir
    $target = Join-Path $bundleRoot $dir
    $null = New-Item -ItemType Directory -Force -Path $target
    robocopy $source $target /E /NFL /NDL /NJH /NJS /NP /XD $excludeDirs /XF $excludeFiles | Out-Null
}

foreach ($file in $includeFiles) {
    if (Test-Path $file) {
        Copy-Item $file $bundleRoot -Force
    }
}

$readmePath = Join-Path $bundleRoot "DEPLOY_BUNDLE_README.txt"
@"
IDEAS - Deploy Bundle (limpio)

Este paquete excluye artefactos pesados de desarrollo:
- portable/
- reportes/
- uploads/
- backups/
- notebooklm_*/

No modifica el proyecto original.

Sugerencia:
1) Validar localmente desde esta carpeta.
2) Subir solo el contenido de deploy_bundle al entorno de deploy.
"@ | Set-Content -Encoding UTF8 $readmePath

$bytes = (Get-ChildItem -Path $bundleRoot -Recurse -File | Measure-Object -Property Length -Sum).Sum
$mb = [math]::Round(($bytes / 1MB), 2)
Write-Host "Bundle listo. Tamaño aproximado: $mb MB"
