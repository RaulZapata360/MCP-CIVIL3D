<#
.SYNOPSIS
  Compila el plugin C# de Civil 3D y lo despliega en el bundle de autoload de Autodesk.

.DESCRIPTION
  Todas las rutas de ORIGEN son relativas al repositorio (autocontenido):
    - Codigo:      server/Civil3D-MCP-Plugin/
    - Referencias: server/C_References/   (DLLs de Civil 3D versionados en el repo)

  El unico destino externo es la carpeta que Autodesk EXIGE para el autoload:
    %APPDATA%\Autodesk\ApplicationPlugins\Civil3DMcp.bundle
  No se puede evitar (asi descubre Civil 3D los plugins), pero este script la
  reconstruye entera desde cero, asi que en un PC nuevo basta con ejecutarlo.

.PARAMETER SkipBuild
  Despliega el ultimo binario compilado sin volver a compilar.

.PARAMETER Configuration
  Release (por defecto) o Debug.

.EXAMPLE
  powershell -ExecutionPolicy Bypass -File server\scripts\deploy-plugin.ps1
#>
[CmdletBinding()]
param(
  [switch]$SkipBuild,
  [ValidateSet('Release', 'Debug')]
  [string]$Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'

# --- Rutas internas al repositorio -------------------------------------------
$scriptDir  = $PSScriptRoot
$serverRoot = Split-Path -Parent $scriptDir
$repoRoot   = Split-Path -Parent $serverRoot
$pluginDir  = Join-Path $serverRoot 'Civil3D-MCP-Plugin'
$csproj     = Join-Path $pluginDir  'Civil3DMcpPlugin.csproj'
$refsDir    = Join-Path $serverRoot 'C_References'

Write-Host "Repositorio : $repoRoot"
Write-Host "Plugin      : $pluginDir"
Write-Host "Referencias : $refsDir"
Write-Host ''

if (-not (Test-Path $csproj)) {
  throw "No se encontro el proyecto del plugin en: $csproj"
}

# Las 5 DLLs de Civil 3D que exige el .csproj (HintPath = ..\C_References)
$requiredRefs = @(
  'accoremgd.dll', 'AcDbMgd.dll', 'acmgd.dll', 'AecBaseMgd.dll', 'AeccDbMgd.dll'
)
$missing = $requiredRefs | Where-Object { -not (Test-Path (Join-Path $refsDir $_)) }
if ($missing) {
  throw "Faltan referencias de Civil 3D en '$refsDir': $($missing -join ', ')"
}

# --- Compilacion --------------------------------------------------------------
if (-not $SkipBuild) {
  if (-not (Get-Command dotnet -ErrorAction SilentlyContinue)) {
    throw "No se encontro 'dotnet' en el PATH. Instala el .NET SDK."
  }
  Write-Host "[1/3] Compilando plugin ($Configuration)..."
  & dotnet build $csproj -c $Configuration --nologo
  if ($LASTEXITCODE -ne 0) { throw "Fallo la compilacion del plugin." }
} else {
  Write-Host "[1/3] Compilacion omitida (-SkipBuild)."
}

# --- Localizar el binario recien compilado -----------------------------------
Write-Host "[2/3] Localizando binario compilado..."
$builtDll = Get-ChildItem -Path (Join-Path $pluginDir "bin\$Configuration") `
                          -Filter 'Civil3DMcpPlugin.dll' -Recurse -ErrorAction SilentlyContinue |
            Sort-Object LastWriteTime -Descending |
            Select-Object -First 1

if (-not $builtDll) {
  throw "No se encontro Civil3DMcpPlugin.dll en bin\$Configuration. Compila primero (sin -SkipBuild)."
}
$outDir = $builtDll.Directory.FullName
Write-Host "      -> $($builtDll.FullName)"
Write-Host "      -> compilado: $($builtDll.LastWriteTime)"

# --- Desplegar al bundle de autoload -----------------------------------------
Write-Host "[3/3] Desplegando al bundle de Autodesk..."
$bundle   = Join-Path $env:APPDATA 'Autodesk\ApplicationPlugins\Civil3DMcp.bundle'
$contents = Join-Path $bundle 'Contents'

# Respaldo del bundle anterior (por si hay que volver atras)
if (Test-Path $bundle) {
  $backup = "$bundle.bak"
  if (Test-Path $backup) { Remove-Item $backup -Recurse -Force }
  Copy-Item $bundle $backup -Recurse -Force
  Write-Host "      respaldo: $backup"
  Remove-Item $contents -Recurse -Force -ErrorAction SilentlyContinue
}

New-Item -ItemType Directory -Path $contents -Force | Out-Null

# Copiamos el DLL y sus metadatos de runtime; NO las DLLs de Civil 3D
# (Private=False en el .csproj: las aporta el propio Civil 3D en ejecucion).
foreach ($pattern in @('Civil3DMcpPlugin.dll', 'Civil3DMcpPlugin.deps.json', 'Civil3DMcpPlugin.runtimeconfig.json', '*.pdb')) {
  Get-ChildItem -Path $outDir -Filter $pattern -ErrorAction SilentlyContinue |
    Copy-Item -Destination $contents -Force
}

$packageContents = @'
<?xml version="1.0" encoding="utf-8"?>
<ApplicationPackage
    SchemaVersion="1.0"
    AutodeskProduct="AutoCAD"
    Name="Civil3D MCP"
    AppVersion="1.0.0"
    ProductType="Application"
    Description="Civil 3D MCP plugin - JSON-RPC TCP listener on port 8080">
  <CompanyDetails Name="Sacred-G" Url="https://github.com/Sacred-G/Civil3D-mcp" />
  <Components Description="Civil3D MCP Plugin">
    <RuntimeRequirements OS="Win64" Platform="AutoCAD*" SeriesMin="R25.1" SeriesMax="R25.1" />
    <ComponentEntry
        AppName="Civil3DMcp"
        Version="1.0.0"
        ModuleName="./Contents/Civil3DMcpPlugin.dll"
        LoadOnAutoCADStartup="True"
        LoadOnCommandInvocation="False" />
  </Components>
</ApplicationPackage>
'@
Set-Content -Path (Join-Path $bundle 'PackageContents.xml') -Value $packageContents -Encoding utf8

Write-Host ''
Write-Host "OK. Plugin desplegado en: $bundle"
Get-ChildItem $contents | Select-Object Name, Length, LastWriteTime | Format-Table -AutoSize
Write-Host "IMPORTANTE: reinicia Civil 3D para que cargue el plugin nuevo."
