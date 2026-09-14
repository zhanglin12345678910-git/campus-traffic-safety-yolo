$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$WatchdogScript = Join-Path $PSScriptRoot 'watch-yolo26-training.ps1'
$TrainingRoot = 'local-path/campus-yolo26-training'
$StdoutLog = Join-Path $TrainingRoot 'watchdog.stdout.log'
$StderrLog = Join-Path $TrainingRoot 'watchdog.stderr.log'

$existing = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -eq 'pwsh.exe' -and $_.CommandLine -match '[\\/]watch-yolo26-training\.ps1(?:"|\s)'
})
if ($existing.Count -gt 0) {
    [ordered]@{status='already_running'; process_ids=@($existing.ProcessId)} | ConvertTo-Json
    return
}

$Pwsh = (Get-Command pwsh -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Source)
$argumentString = '-NoProfile -File "{0}" -IntervalSeconds 60 -RestartDelaySeconds 120 -MaxRestarts 50' -f $WatchdogScript
$process = Start-Process `
    -FilePath $Pwsh `
    -ArgumentList $argumentString `
    -WindowStyle Hidden `
    -RedirectStandardOutput $StdoutLog `
    -RedirectStandardError $StderrLog `
    -PassThru

Start-Sleep -Seconds 2
if ($process.HasExited -and $process.ExitCode -ne 0) {
    $details = if (Test-Path -LiteralPath $StderrLog) { Get-Content -LiteralPath $StderrLog -Raw } else { '' }
    throw "训练守护程序启动失败，退出码 $($process.ExitCode)：$details"
}

[ordered]@{
    status = if ($process.HasExited) { 'completed_immediately' } else { 'started' }
    process_id = $process.Id
    watchdog = $WatchdogScript
    stdout = $StdoutLog
    stderr = $StderrLog
} | ConvertTo-Json
