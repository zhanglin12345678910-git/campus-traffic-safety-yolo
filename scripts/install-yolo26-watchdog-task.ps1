#requires -Version 7.0

param(
    [string]$TaskName = 'CampusSafetyYolo26Watchdog',
    [ValidateRange(1, 60)]
    [int]$SafetyIntervalMinutes = 5
)

$ErrorActionPreference = 'Stop'

$WatchdogScript = Join-Path $PSScriptRoot 'watch-yolo26-training.ps1'
$Pwsh = (Get-Command pwsh -ErrorAction Stop | Select-Object -First 1 -ExpandProperty Source)
$UserId = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
$arguments = '-NoProfile -File "{0}" -IntervalSeconds 30 -RestartDelaySeconds 60 -MaxRestarts 50' -f $WatchdogScript

$action = New-ScheduledTaskAction -Execute $Pwsh -Argument $arguments
$logonTrigger = New-ScheduledTaskTrigger -AtLogOn -User $UserId
$safetyTrigger = New-ScheduledTaskTrigger `
    -Once `
    -At ((Get-Date).AddMinutes(1)) `
    -RepetitionInterval ([timespan]::FromMinutes($SafetyIntervalMinutes))
$principal = New-ScheduledTaskPrincipal -UserId $UserId -LogonType Interactive -RunLevel Limited
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([timespan]::Zero) `
    -MultipleInstances IgnoreNew `
    -RestartCount 50 `
    -RestartInterval ([timespan]::FromMinutes(1))
$task = New-ScheduledTask -Action $action -Trigger @($logonTrigger, $safetyTrigger) -Principal $principal -Settings $settings
Register-ScheduledTask -TaskName $TaskName -InputObject $task -Force | Out-Null
Start-ScheduledTask -TaskName $TaskName
Start-Sleep -Seconds 3

$registered = Get-ScheduledTask -TaskName $TaskName
$info = Get-ScheduledTaskInfo -TaskName $TaskName
[ordered]@{
    task_name = $TaskName
    state = [string]$registered.State
    last_run_time = $info.LastRunTime.ToString('o')
    last_task_result = $info.LastTaskResult
    next_run_time = if ($info.NextRunTime -gt [datetime]::MinValue) { $info.NextRunTime.ToString('o') } else { $null }
    execute = $Pwsh
    arguments = $arguments
    user = $UserId
    execution_time_limit = 'PT0S'
    safety_interval_minutes = $SafetyIntervalMinutes
    trigger_count = @($registered.Triggers).Count
} | ConvertTo-Json
