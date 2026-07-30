@echo off
title Laboratorio MCP Civil 3D - Panel de Control
echo ============================================================
echo      Iniciando Laboratorio y Servidor MCP Civil 3D
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Escaneando herramientas y actualizando datos del laboratorio...
python update_dashboard.py

echo.
echo [2/3] Abriendo el Panel de Control en tu navegador predeterminado...
start http://localhost:8000/dashboard.html

echo.
echo [3/3] Servidor activo en http://localhost:8000
echo Presiona Ctrl+C para detener el servidor cuando termines.
echo.

python -m http.server 8000
