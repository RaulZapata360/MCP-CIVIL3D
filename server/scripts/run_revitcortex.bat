@echo off
:: Wrapper para resolver la ruta del servidor RevitCortex.
:: Orden de busqueda (de mas portable a menos):
::   1. Copia local dentro del propio repositorio: tools\revitcortex\  (autocontenida)
::   2. Variable de entorno REVITCORTEX_HOME (override explicito)
::   3. Instalacion por usuario: %USERPROFILE%\.revitcortex\
:: Asi el repo funciona igual en cualquier PC sin editar rutas a mano.

setlocal

:: %~dp0 = server\scripts\  ->  subimos dos niveles hasta la raiz del repo
for %%I in ("%~dp0..\..") do set "REPO_ROOT=%%~fI"

set "EXE_REL=server\RevitCortex.Server.exe"

:: (1) Copia local dentro del repositorio
if exist "%REPO_ROOT%\tools\revitcortex\%EXE_REL%" (
    "%REPO_ROOT%\tools\revitcortex\%EXE_REL%" %*
    exit /b %ERRORLEVEL%
)

:: (2) Override explicito por variable de entorno
if defined REVITCORTEX_HOME (
    if exist "%REVITCORTEX_HOME%\%EXE_REL%" (
        "%REVITCORTEX_HOME%\%EXE_REL%" %*
        exit /b %ERRORLEVEL%
    )
)

:: (3) Instalacion estandar en el perfil del usuario
if exist "%USERPROFILE%\.revitcortex\%EXE_REL%" (
    "%USERPROFILE%\.revitcortex\%EXE_REL%" %*
    exit /b %ERRORLEVEL%
)

echo Error: no se encontro RevitCortex.Server.exe. >&2
echo Rutas probadas: >&2
echo   - %REPO_ROOT%\tools\revitcortex\%EXE_REL% >&2
if defined REVITCORTEX_HOME echo   - %REVITCORTEX_HOME%\%EXE_REL% >&2
echo   - %USERPROFILE%\.revitcortex\%EXE_REL% >&2
echo Instala RevitCortex, copialo en tools\revitcortex\ o define REVITCORTEX_HOME. >&2
exit /b 1
