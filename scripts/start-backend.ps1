param(
    [string]$PythonExe = $(if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { 'python' }),
    [ValidateRange(1, 65535)][int]$Port = 8000
)

$ErrorActionPreference = 'Stop'
if (-not (Get-Command $PythonExe -ErrorAction SilentlyContinue)) {
    throw "Project Python environment not found: $PythonExe"
}
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location (Join-Path $ProjectRoot 'backend')
& $PythonExe -m uvicorn app.main:app --host 127.0.0.1 --port $Port
exit $LASTEXITCODE
