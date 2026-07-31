@echo off
title Ecosistema Unificado MCP Civil 3D - Laboratorio y Control
echo ============================================================
echo      Iniciando Ecosistema Unificado MCP Civil 3D
echo ============================================================
echo  Mecanismo 1: Engine MCP (server/)
echo  Mecanismo 2: Skills de Dominio (skills/)
echo  Mecanismo 3: Dashboard QA (dashboard.html & verificacion/)
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Escaneando herramientas del servidor interno y actualizando datos...
python update_dashboard.py

echo.
echo [2/3] Abriendo el Panel de Control en tu navegador predeterminado...
start http://localhost:8000/dashboard.html

echo.
echo [3/3] Servidor de Dashboard activo en http://localhost:8000
echo Presiona Ctrl+C para detener el servidor cuando termines.
echo.

python -m http.server 8000
