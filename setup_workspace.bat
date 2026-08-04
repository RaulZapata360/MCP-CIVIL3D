@echo off
title MCP Civil 3D - Setup de Entorno
echo ============================================================
echo      Inicializando Entorno de Trabajo MCP Civil 3D
echo ============================================================
echo.
echo  Este script deja el repositorio listo en un PC nuevo.
echo  Todas las rutas son relativas a esta carpeta: no hay que
echo  editar nada a mano al clonar en otra maquina.
echo.

cd /d "%~dp0"

echo [1/5] Dependencias de Node.js (servidor MCP)
if exist "server\package.json" (
    pushd server
    call npm install
    popd
    echo       Dependencias de Node.js instaladas.
) else (
    echo       No se encontro server\package.json, saltando npm install...
)
echo.

echo [2/5] Compilando el servidor MCP (TypeScript -^> build/)
if exist "server\package.json" (
    pushd server
    call npm run build
    popd
    echo       Servidor MCP compilado en server\build\.
)
echo.

echo [3/5] Verificando entorno de Python (skills de dominio)
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo       Advertencia: Python no esta en el PATH.
    echo       Las skills locales y el dashboard no funcionaran.
) else (
    echo       Python detectado correctamente.
)
echo.

echo [4/5] Verificando referencias de Civil 3D (server\C_References\)
set "REFS_OK=1"
for %%F in (accoremgd.dll AcDbMgd.dll acmgd.dll AecBaseMgd.dll AeccDbMgd.dll) do (
    if not exist "server\C_References\%%F" (
        echo       FALTA: server\C_References\%%F
        set "REFS_OK=0"
    )
)
if "%REFS_OK%"=="1" (
    echo       Las 5 referencias de Civil 3D estan presentes.
) else (
    echo       Faltan referencias: no se podra compilar el plugin C#.
)
echo.

echo [5/5] Plugin de Civil 3D
echo       Para compilar y desplegar el plugin en Civil 3D ejecuta:
echo         powershell -ExecutionPolicy Bypass -File server\scripts\deploy-plugin.ps1
echo       (reconstruye el bundle de autoload; hay que reiniciar Civil 3D despues)
echo.
echo       RevitCortex se resuelve en este orden:
echo         1) tools\revitcortex\server\RevitCortex.Server.exe   (dentro del repo)
echo         2) %%REVITCORTEX_HOME%%\server\RevitCortex.Server.exe
echo         3) %%USERPROFILE%%\.revitcortex\server\RevitCortex.Server.exe
echo.

echo ============================================================
echo Setup completado.
echo Inicia el laboratorio con 'iniciar_laboratorio.bat'
echo ============================================================
pause
