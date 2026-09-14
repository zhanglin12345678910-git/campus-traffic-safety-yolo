param(
    [string]$HostAddress = '127.0.0.1',
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173
)

$ErrorActionPreference = 'Stop'

$projectRoot = Split-Path -Parent $PSScriptRoot
$backendDir = Join-Path $projectRoot 'backend'
$frontendDir = Join-Path $projectRoot 'frontend'
$outputDir = Join-Path $projectRoot 'outputs'
$pythonCommand = if ($env:PYTHON_EXE) { $env:PYTHON_EXE } else { 'python' }
$pythonExe = (Get-Command $pythonCommand -ErrorAction Stop).Source
$npmExe = (Get-Command 'npm.cmd' -ErrorAction Stop).Source
New-Item -ItemType Directory -Path $outputDir -Force | Out-Null

if (-not (Test-Path -LiteralPath $pythonExe)) {
    throw "Python environment not found: $pythonExe"
}
if (-not (Test-Path -LiteralPath $npmExe)) {
    throw "npm not found: $npmExe"
}

$createdNew = $false
$mutex = [System.Threading.Mutex]::new($true, 'Local\CampusSafetyAgentPreview', [ref]$createdNew)
if (-not $createdNew) {
    $mutex.Dispose()
    exit 0
}

$env:DATABASE_URL = 'sqlite:///./data/local-preview.db'
$env:QDRANT_URL = ''
$env:QDRANT_PATH = './data/qdrant-preview'
$env:YOLO_MODEL_PATH = '../models/yolo26-tt100k-best.pt'
$env:YOLO_DEVICE = 'cpu'

$backend = $null
$frontend = $null
$exitCode = 0

try {
    $backendStart = @{
        FilePath = $pythonExe
        ArgumentList = @('-m', 'uvicorn', 'app.main:app', '--host', $HostAddress, '--port', "$BackendPort")
        WorkingDirectory = $backendDir
        WindowStyle = 'Hidden'
        RedirectStandardOutput = Join-Path $outputDir 'preview-backend.stdout.log'
        RedirectStandardError = Join-Path $outputDir 'preview-backend.stderr.log'
        PassThru = $true
    }
    $backend = Start-Process @backendStart

    $env:VITE_DEV_API_TARGET = "http://${HostAddress}:$BackendPort"
    $frontendStart = @{
        FilePath = $npmExe
        ArgumentList = @('run', 'dev', '--', '--host', $HostAddress, '--port', "$FrontendPort", '--strictPort')
        WorkingDirectory = $frontendDir
        WindowStyle = 'Hidden'
        RedirectStandardOutput = Join-Path $outputDir 'preview-frontend.stdout.log'
        RedirectStandardError = Join-Path $outputDir 'preview-frontend.stderr.log'
        PassThru = $true
    }
    $frontend = Start-Process @frontendStart

    while ($true) {
        $backend.Refresh()
        $frontend.Refresh()
        if ($backend.HasExited -or $frontend.HasExited) {
            $exitCode = 1
            break
        }
        Start-Sleep -Seconds 2
    }
}
finally {
    foreach ($process in @($backend, $frontend)) {
        if ($null -ne $process) {
            $process.Refresh()
            if (-not $process.HasExited) {
                Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
            }
        }
    }
    $mutex.ReleaseMutex()
    $mutex.Dispose()
}

exit $exitCode
