# Distribucion IDEAS

## Opcion recomendada

Generar una carpeta portable para Windows y subir esa carpeta comprimida a Drive.

## Opcion 1: carpeta portable recomendada

1. Abrir PowerShell en la carpeta del proyecto.
2. Ejecutar:

```powershell
.\build_portable.ps1
```

3. El resultado queda en:

```text
portable\IDEAS_Portable\
```

La otra persona solo debe ejecutar:

```text
run_portable.bat
```

## Opcion 2: ejecutable

Si aun quieres probar la variante `.exe`, puedes generar:

```powershell
.\build_exe.ps1
```

Resultado:

```text
dist\IDEAS_Consulting\
```

## Que subir a Drive

Subir comprimida la carpeta completa:

```text
portable\IDEAS_Portable\
```

No subir solo un archivo suelto. Tiene que viajar la carpeta completa porque incluye runtime, `Data`, logo, banner y base de datos.

## Que hace la otra persona

1. Descargar y descomprimir la carpeta.
2. Abrir `run_portable.bat`.
3. La app se levanta sola y abre el navegador en `http://localhost:8501`.

## Notas

- Esto sirve para otra PC Windows.
- No necesita Python instalado en la PC destino.
- Si cambias la app, vuelve a correr `.\build_portable.ps1` y sube una nueva carpeta.
