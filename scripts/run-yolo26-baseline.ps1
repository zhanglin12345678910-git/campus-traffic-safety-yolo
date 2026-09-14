param(
    [ValidateRange(1, 128)]
    [int]$Batch = 12,
    [ValidateRange(0, 16)]
    [int]$Workers = 0
)

$ErrorActionPreference = 'Stop'

$RunnerMutex = [System.Threading.Mutex]::new($false, 'Local\CampusSafetyYolo26Runner')
$RunnerLockAcquired = $false
try {
    $RunnerLockAcquired = $RunnerMutex.WaitOne(0)
}
catch [System.Threading.AbandonedMutexException] {
    $RunnerLockAcquired = $true
}
if (-not $RunnerLockAcquired) {
    Write-Output '已有 YOLO26 正式训练启动器运行，本次不重复启动。'
    $RunnerMutex.Dispose()
    return
}

try {
$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = 'local-path/python.exe'
$Dataset = 'local-path/tt100k.yaml'
$TrainingRoot = 'local-path/campus-yolo26-training'
$RunDir = Join-Path $TrainingRoot 'yolo26m-tt100k-640'
$BestWeight = Join-Path $RunDir 'weights\best.pt'
$LastWeight = Join-Path $RunDir 'weights\last.pt'
$FinalWeight = Join-Path $ProjectRoot 'models\yolo26-tt100k-best.pt'
$StdoutLog = Join-Path $TrainingRoot 'baseline.stdout.log'
$StderrLog = Join-Path $TrainingRoot 'baseline.stderr.log'
$StatusFile = Join-Path $TrainingRoot 'status.json'
$EvaluationFile = Join-Path $TrainingRoot 'evaluation-result.json'
$env:YOLO_CONFIG_DIR = Join-Path $TrainingRoot 'ultralytics-config'
$UltralyticsSettings = Join-Path $env:YOLO_CONFIG_DIR 'Ultralytics\settings.json'
$UltralyticsWeights = Join-Path $TrainingRoot 'weights'
$PreviousStatus = $null
if (Test-Path -LiteralPath $StatusFile) {
    try {
        $PreviousStatus = Get-Content -LiteralPath $StatusFile -Raw | ConvertFrom-Json
    }
    catch {
        # 状态文件损坏时仍可依靠 last.pt 恢复训练，错误会保留在本次 stderr 中。
        $_ | Out-String | Add-Content -LiteralPath $StderrLog
    }
}
if ($PreviousStatus -and $PreviousStatus.status -in @('stopped_by_user', 'completed_partial_by_user')) {
    throw 'YOLO26 训练已按用户要求终止；启动器拒绝自动或误操作恢复。'
}
$ResumePostTraining = (
    $PreviousStatus -and
    $PreviousStatus.status -in @('running', 'failed') -and
    $PreviousStatus.phase -in @('evaluation', 'promotion') -and
    (Test-Path -LiteralPath $BestWeight)
)

New-Item -ItemType Directory -Force -Path $TrainingRoot,$env:YOLO_CONFIG_DIR,$UltralyticsWeights | Out-Null
Set-Location $ProjectRoot

$AttemptId = (Get-Date).ToString('yyyyMMdd-HHmmss')
if ((Test-Path -LiteralPath $StdoutLog) -and (Get-Item -LiteralPath $StdoutLog).Length -gt 0) {
    Move-Item -LiteralPath $StdoutLog -Destination (Join-Path $TrainingRoot "baseline.$AttemptId.stdout.log")
}
if ((Test-Path -LiteralPath $StderrLog) -and (Get-Item -LiteralPath $StderrLog).Length -gt 0) {
    Move-Item -LiteralPath $StderrLog -Destination (Join-Path $TrainingRoot "baseline.$AttemptId.stderr.log")
}

# Ultralytics 的默认目录位于用户主目录，受限运行环境可能无权访问；统一迁到训练目录。
if (-not (Test-Path -LiteralPath $UltralyticsSettings)) {
    & $Python -c 'import ultralytics' | Out-Null
}
$settings = Get-Content -LiteralPath $UltralyticsSettings -Raw | ConvertFrom-Json
$settings.weights_dir = $UltralyticsWeights
$settings.runs_dir = $TrainingRoot
$settings.datasets_dir = Join-Path $TrainingRoot 'datasets'
$settings | ConvertTo-Json | Set-Content -LiteralPath $UltralyticsSettings -Encoding utf8

# AMP 一致性检查需要官方 yolo26n 权重；优先复用已下载文件，避免运行中写用户目录。
$AmpWeight = Join-Path $UltralyticsWeights 'yolo26n.pt'
$ExistingAmpWeight = Join-Path (Split-Path -Parent $ProjectRoot) 'weights\yolo26n.pt'
if ((-not (Test-Path -LiteralPath $AmpWeight)) -and (Test-Path -LiteralPath $ExistingAmpWeight)) {
    Copy-Item -LiteralPath $ExistingAmpWeight -Destination $AmpWeight
}

$startedAt = (Get-Date).ToString('o')
$Phase = if ($ResumePostTraining) { 'evaluation' } else { 'training' }

try {
    if (-not $ResumePostTraining) {
        @{status='running'; phase=$Phase; started_at=$startedAt; attempt=$AttemptId; preset='baseline'; train_images=28083; validation_images=8016; epochs=80; batch=$Batch; workers=$Workers} |
            ConvertTo-Json | Set-Content -LiteralPath $StatusFile -Encoding utf8

        $arguments = @(
            'training\train_yolo26.py',
            '--preset', 'baseline',
            '--data', $Dataset,
            '--device', '0',
            '--workers', $Workers.ToString(),
            '--batch', $Batch.ToString(),
            '--project', $TrainingRoot
        )
        if (Test-Path -LiteralPath $LastWeight) {
            $arguments += '--resume'
        }
        & $Python @arguments 1>> $StdoutLog 2>> $StderrLog
        if ($LASTEXITCODE -ne 0) {
            throw "YOLO26 训练退出码为 $LASTEXITCODE"
        }
    }
    if (-not (Test-Path -LiteralPath $BestWeight)) {
        throw "训练结束但未找到 best.pt"
    }
    $Phase = 'evaluation'
    @{
        status='running'
        phase=$Phase
        started_at=$startedAt
        attempt=$AttemptId
        preset='baseline'
        model=$BestWeight
        test_images=3992
        batch=8
        workers=0
    } | ConvertTo-Json | Set-Content -LiteralPath $StatusFile -Encoding utf8
    & $Python 'training\evaluate_yolo26.py' `
        --weights $BestWeight `
        --data $Dataset `
        --imgsz 640 `
        --device 0 `
        --batch 8 `
        --workers 0 `
        --output $EvaluationFile 1>> $StdoutLog 2>> $StderrLog
    if ($LASTEXITCODE -ne 0) {
        throw "独立测试集评估退出码为 $LASTEXITCODE"
    }
    $Phase = 'promotion'
    @{
        status='running'
        phase=$Phase
        started_at=$startedAt
        attempt=$AttemptId
        preset='baseline'
        model=$BestWeight
        evaluation=$EvaluationFile
        promotion_target=$FinalWeight
    } | ConvertTo-Json | Set-Content -LiteralPath $StatusFile -Encoding utf8
    $promoted = $false
    Copy-Item -LiteralPath $BestWeight -Destination $FinalWeight -Force
    $bestHash = (Get-FileHash -LiteralPath $BestWeight -Algorithm SHA256).Hash
    $finalHash = (Get-FileHash -LiteralPath $FinalWeight -Algorithm SHA256).Hash
    if ($bestHash -ne $finalHash) {
        throw '正式权重复制后的 SHA-256 与 best.pt 不一致'
    }
    $promoted = $true
    @{
        status='completed'
        phase='completed'
        started_at=$startedAt
        finished_at=(Get-Date).ToString('o')
        attempt=$AttemptId
        preset='baseline'
        model=$BestWeight
        promoted=$promoted
        promotion_target=$FinalWeight
        evaluation=$EvaluationFile
    } | ConvertTo-Json | Set-Content -LiteralPath $StatusFile -Encoding utf8
}
catch {
    @{
        status='failed'
        phase=$Phase
        started_at=$startedAt
        finished_at=(Get-Date).ToString('o')
        attempt=$AttemptId
        error=$_.Exception.Message
        resumable=(Test-Path -LiteralPath $LastWeight)
    } | ConvertTo-Json | Set-Content -LiteralPath $StatusFile -Encoding utf8
    throw
}
}
finally {
    if ($RunnerLockAcquired) { $RunnerMutex.ReleaseMutex() }
    $RunnerMutex.Dispose()
}
