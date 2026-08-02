@echo off
title MCP Civil 3D - Setup de Entorno
echo ============================================================
echo      Inicializando Entorno de Trabajo MCP Civil 3D
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/3] Verificando dependencias de Node.js (Servidor principal)
if exist "server\package.json" (
    cd server
    call npm install
    cd ..
    echo Dependencias de Node.js instaladas correctamente.
) else (
    echo No se encontro server\package.json, saltando npm install...
)
echo.

echo [2/3] Verificando entorno de Python (Skills de Dominio)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Advertencia: Python no esta instalado o no esta en el PATH.
    echo Algunas skills locales podrian no funcionar.
) else (
    echo Python detectado correctamente.
)
echo.

echo [3/3] Configurando variables de entorno
echo El sistema usara la ruta %USERPROFILE%\.revitcortex\server\RevitCortex.Server.exe para RevitCortex.
echo.

echo ============================================================
echo Setup completado.
echo Puedes iniciar el laboratorio usando 'iniciar_laboratorio.bat'
echo ============================================================
pause
