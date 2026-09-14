param(
    [ValidateRange(10, 600)]
    [int]$IntervalSeconds = 60,
    [ValidateRange(10, 1800)]
    [int]$RestartDelaySeconds = 120,
    [ValidateRange(1, 100)]
    [int]$MaxRestarts = 50
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$TrainingRoot = 'local-path/campus-yolo26-training'
$StatusFile = Join-Path $TrainingRoot 'status.json'
$LastWeight = Join-Path $TrainingRoot 'yolo26m-tt100k-640\weights\last.pt'
$RunnerScript = Join-Path $PSScriptRoot 'run-yolo26-baseline.ps1'
$WatchdogLog = Join-Path $TrainingRoot 'watchdog.jsonl'
$WatchdogStatusFile = Join-Path $TrainingRoot 'watchdog-status.json'
$StdoutLog = Join-Path $TrainingRoot 'baseline.stdout.log'
$ResultsFile = Join-Path $TrainingRoot 'yolo26m-tt100k-640\results.csv'
$RunnerStdoutLog = Join-Path $TrainingRoot 'watchdog-runner.stdout.log'
$RunnerStderrLog = Join-Path $TrainingRoot 'watchdog-runner.stderr.log'
$WatchdogMutex = [System.Threading.Mutex]::new($false, 'Local\CampusSafetyYolo26Watchdog')
$WatchdogLockAcquired = $false

. (Join-Path $PSScriptRoot 'training-progress.ps1')

function Write-WatchdogEvent {
    param(
        [Parameter(Mandatory)][string]$Event,
        [hashtable]$Details = @{}
    )
    [ordered]@{
        timestamp = (Get-Date).ToString('o')
        event = $Event
        details = $Details
    } | ConvertTo-Json -Compress -Depth 5 | Add-Content -LiteralPath $WatchdogLog -Encoding utf8
}

function Write-WatchdogStatus {
    param(
        [Parameter(Mandatory)][string]$Status,
        [string]$Message = ''
    )
    [ordered]@{
        status = $Status
        pid = $PID
        updated_at = (Get-Date).ToString('o')
        interval_seconds = $IntervalSeconds
        restart_delay_seconds = $RestartDelaySeconds
        restart_count = $restartCount
        progress = Get-YoloTrainingProgress -LogPath $StdoutLog -ResultsPath $ResultsFile
        message = $Message
    } | ConvertTo-Json | Set-Content -LiteralPath $WatchdogStatusFile -Encoding utf8
}

function Get-TrainingProcesses {
    @(Get-CimInstance Win32_Process -ErrorAction Stop | Where-Object {
        $_.Name -match '^(python|pwsh|powershell)(\.exe)?$' -and
        $_.CommandLine -match 'train_yolo26\.py|evaluate_yolo26\.py|run-yolo26-baseline\.ps1'
    })
}

New-Item -ItemType Directory -Force -Path $TrainingRoot | Out-Null
$restartCount = 0
$missingChecks = 0
$lastPulse = [datetime]::MinValue

try {
    try {
        $WatchdogLockAcquired = $WatchdogMutex.WaitOne(0)
    }
    catch [System.Threading.AbandonedMutexException] {
        $WatchdogLockAcquired = $true
    }
    if (-not $WatchdogLockAcquired) {
        Write-Output '已有 YOLO26 训练守护程序运行，本次不重复启动。'
        return
    }

    Write-WatchdogEvent -Event 'watchdog_started' -Details @{pid=$PID; interval_seconds=$IntervalSeconds}
    Write-WatchdogStatus -Status 'running' -Message '正在监控正式训练'

    while ($true) {
        $status = $null
        if (Test-Path -LiteralPath $StatusFile) {
            try { $status = Get-Content -LiteralPath $StatusFile -Raw | ConvertFrom-Json }
            catch { Write-WatchdogEvent -Event 'status_read_error' -Details @{message=$_.Exception.Message} }
        }

        if ($status -and $status.status -in @('stopped_by_user', 'completed_partial_by_user')) {
            Write-WatchdogEvent -Event 'training_stopped_by_user' -Details @{
                completed_epochs = $status.completed_epochs
                selected_checkpoint = $status.selected_checkpoint
            }
            Write-WatchdogStatus -Status 'stopped_by_user' -Message '用户已终止训练，禁止自动恢复'
            break
        }

        if ($status -and $status.status -eq 'completed') {
            Write-WatchdogEvent -Event 'training_completed' -Details @{model=$status.model; evaluation=$status.evaluation}
            Write-WatchdogStatus -Status 'completed' -Message '训练、评估和权重晋升已完成'
            break
        }

        try {
            $activeProcesses = Get-TrainingProcesses
        }
        catch {
            Write-WatchdogEvent -Event 'process_check_error' -Details @{message=$_.Exception.Message}
            Write-WatchdogStatus -Status 'degraded' -Message '进程检查失败，为防重复启动暂不恢复'
            Start-Sleep -Seconds $IntervalSeconds
            continue
        }

        if ($activeProcesses.Count -gt 0) {
            $missingChecks = 0
            if ((Get-Date) - $lastPulse -ge [timespan]::FromMinutes(30)) {
                Write-WatchdogEvent -Event 'training_alive' -Details @{
                    process_ids = @($activeProcesses.ProcessId)
                    training_status = if ($status) { $status.status } else { 'unknown' }
                    progress = Get-YoloTrainingProgress -LogPath $StdoutLog -ResultsPath $ResultsFile
                }
                $lastPulse = Get-Date
            }
            Write-WatchdogStatus -Status 'running' -Message '训练或独立评估进程正常'
            Start-Sleep -Seconds $IntervalSeconds
            continue
        }

        $missingChecks++
        if ($missingChecks -lt 2) {
            Write-WatchdogStatus -Status 'checking' -Message '首次未发现训练进程，等待复核'
            Start-Sleep -Seconds $IntervalSeconds
            continue
        }

        if (-not (Test-Path -LiteralPath $LastWeight)) {
            Write-WatchdogEvent -Event 'restart_blocked' -Details @{reason='last.pt 不存在'}
            Write-WatchdogStatus -Status 'blocked' -Message '缺少 last.pt，不能安全恢复'
            break
        }
        if ($restartCount -ge $MaxRestarts) {
            Write-WatchdogEvent -Event 'restart_limit_reached' -Details @{restart_count=$restartCount}
            Write-WatchdogStatus -Status 'blocked' -Message '达到自动恢复次数上限'
            break
        }

        $restartCount++
        $missingChecks = 0
        Write-WatchdogEvent -Event 'restart_started' -Details @{
            restart_count = $restartCount
            previous_status = if ($status) { $status.status } else { 'missing' }
            checkpoint = $LastWeight
        }
        Write-WatchdogStatus -Status 'restarting' -Message "第 $restartCount 次从 last.pt 恢复"
        try {
            $pwsh = (Get-Command pwsh -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Source)
            $runnerArguments = '-NoProfile -File "{0}" -Batch 12 -Workers 0' -f $RunnerScript
            $runnerProcess = Start-Process `
                -FilePath $pwsh `
                -ArgumentList $runnerArguments `
                -WindowStyle Hidden `
                -RedirectStandardOutput $RunnerStdoutLog `
                -RedirectStandardError $RunnerStderrLog `
                -PassThru
            Start-Sleep -Seconds 2
            if ($runnerProcess.HasExited -and $runnerProcess.ExitCode -ne 0) {
                throw "训练启动器立即退出，退出码 $($runnerProcess.ExitCode)"
            }
            Write-WatchdogEvent -Event 'runner_spawned' -Details @{
                restart_count = $restartCount
                process_id = $runnerProcess.Id
                exited_immediately = $runnerProcess.HasExited
            }
        }
        catch {
            Write-WatchdogEvent -Event 'runner_failed' -Details @{restart_count=$restartCount; message=$_.Exception.Message}
        }
        Start-Sleep -Seconds $RestartDelaySeconds
    }
}
finally {
    if ($WatchdogLockAcquired) { $WatchdogMutex.ReleaseMutex() }
    $WatchdogMutex.Dispose()
}
