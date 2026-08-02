@echo off
:: Wrapper script to dynamically resolve the path to RevitCortex server
:: It defaults to the current user's profile path for portability across machines.

set REVITCORTEX_PATH=%USERPROFILE%\.revitcortex\server\RevitCortex.Server.exe

if exist "%REVITCORTEX_PATH%" (
    "%REVITCORTEX_PATH%" %*
) else (
    echo Error: RevitCortex server not found at %REVITCORTEX_PATH% >&2
    echo Please ensure RevitCortex is installed or update the path in this script. >&2
    exit /b 1
)
