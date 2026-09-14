param(
    [ValidateRange(1, 65535)][int]$BackendPort = 8000,
    [ValidateRange(1, 65535)][int]$Port = 5173
)

$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot 'frontend')
$env:VITE_DEV_API_TARGET = "http://127.0.0.1:$BackendPort"
npm.cmd run dev -- --host 127.0.0.1 --port $Port --strictPort
exit $LASTEXITCODE
