$ErrorActionPreference = 'Stop'
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot 'backend')
python -m pytest
Set-Location (Join-Path $ProjectRoot 'frontend')
npm run typecheck
npm run build
Set-Location $ProjectRoot
docker compose config --quiet
