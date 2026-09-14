$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$Python = 'local-path/python.exe'
$TrainingRoot = 'local-path/campus-yolo26-training'
$StatusFile = Join-Path $TrainingRoot 'status.json'
$EvaluationFile = Join-Path $TrainingRoot 'evaluation-result.json'
$Dataset = 'local-path/tt100k.yaml'
$TrainingRun = Join-Path $TrainingRoot 'yolo26m-tt100k-640'
$TrainingArgsFile = Join-Path $TrainingRun 'args.yaml'
$TrainingResultsFile = Join-Path $TrainingRun 'results.csv'
$FinalWeight = Join-Path $ProjectRoot 'models\yolo26-tt100k-best.pt'
$AcceptanceFile = Join-Path $TrainingRoot 'final-acceptance.json'
$DockerAcceptanceFile = Join-Path $ProjectRoot 'outputs\docker-runtime-acceptance.json'

foreach ($required in @($StatusFile, $EvaluationFile, $FinalWeight, $Dataset, $TrainingArgsFile, $TrainingResultsFile)) {
    if (-not (Test-Path -LiteralPath $required)) {
        throw "缺少最终验收文件：$required"
    }
}

$status = Get-Content -LiteralPath $StatusFile -Raw | ConvertFrom-Json
$acceptedTrainingStatuses = @('completed', 'completed_partial_by_user')
if ($status.status -notin $acceptedTrainingStatuses) {
    throw "训练状态不是可验收状态：$($status.status)"
}
if ($status.status -eq 'completed_partial_by_user') {
    if ($status.stop_reason -ne 'user_requested') {
        throw "提前停止的训练缺少用户终止依据：$($status.stop_reason)"
    }
    if ([int]$status.completed_epochs -lt 1 -or [int]$status.completed_epochs -ge [int]$status.requested_epochs) {
        throw "提前停止轮次记录非法：$($status.completed_epochs)/$($status.requested_epochs)"
    }
}
if (-not (Test-Path -LiteralPath $status.model)) {
    throw "训练状态记录的 best.pt 不存在：$($status.model)"
}
if (-not [bool]$status.promoted) { throw '训练状态未确认正式权重晋升成功' }
if ((Split-Path -Leaf $status.model) -ne 'best.pt' -or $status.model -match 'smoke') {
    throw "训练状态中的模型不是正式 best.pt：$($status.model)"
}

$evaluation = Get-Content -LiteralPath $EvaluationFile -Raw | ConvertFrom-Json
if ($evaluation.split -ne 'test' -or [int]$evaluation.test_images -ne 3992) {
    throw "独立测试集记录不完整：split=$($evaluation.split), images=$($evaluation.test_images)"
}
if ([int]$evaluation.class_count -ne 45) {
    throw "模型类别数不是 TT100K 45 类：$($evaluation.class_count)"
}
if (@($evaluation.class_names).Count -ne 45) { throw '评估记录未保存完整的 45 类名称' }
if ([int64]$evaluation.weights_size_bytes -ne (Get-Item -LiteralPath $status.model).Length) {
    throw '评估记录的权重大小与 best.pt 不一致'
}
$integrity = $evaluation.integrity_checks
if (
    [int]$integrity.expected_test_images -ne 3992 -or
    [int]$integrity.expected_classes -ne 45 -or
    [int]$integrity.expected_epochs -ne 80 -or
    -not [bool]$integrity.full_training_fraction -or
    -not [bool]$integrity.class_names_match_dataset -or
    -not [bool]$integrity.training_data_matches_evaluation -or
    -not [bool]$integrity.non_smoke_best_checkpoint
) {
    throw '独立评估的完整数据与非冒烟完整性检查未全部通过'
}
$trainingArtifacts = $evaluation.training_artifacts
if (
    [double]$trainingArtifacts.fraction -ne 1.0 -or
    -not [bool]$trainingArtifacts.validation_enabled -or
    [int]$trainingArtifacts.configured_epochs -ne 80 -or
    [int]$trainingArtifacts.training_imgsz -ne 640 -or
    [int]$trainingArtifacts.completed_epochs -lt 1 -or
    $trainingArtifacts.training_name -notmatch 'yolo26'
) {
    throw '训练来源记录不能证明完整 YOLO26 训练配置'
}
$trainingRows = @(Import-Csv -LiteralPath $TrainingResultsFile)
$bestValidationRow = $trainingRows |
    Sort-Object { [double]$_.'metrics/mAP50-95(B)' } -Descending |
    Select-Object -First 1
if (-not $bestValidationRow) { throw 'results.csv 中没有可选择的验证轮次' }
if ([int]$bestValidationRow.epoch -ne [int]$evaluation.checkpoint_completed_epoch) {
    throw "best.pt 不是已完成轮次中 mAP50-95 最高的检查点：CSV epoch=$($bestValidationRow.epoch)，checkpoint=$($evaluation.checkpoint_completed_epoch)"
}
foreach ($metric in @('precision', 'recall', 'map50', 'map50_95')) {
    $value = [double]$evaluation.$metric
    if ([double]::IsNaN($value) -or [double]::IsInfinity($value) -or $value -lt 0 -or $value -gt 1) {
        throw "非法评估指标 $metric=$value"
    }
}

$bestHash = (Get-FileHash -LiteralPath $status.model -Algorithm SHA256).Hash.ToLowerInvariant()
$finalHash = (Get-FileHash -LiteralPath $FinalWeight -Algorithm SHA256).Hash.ToLowerInvariant()
$datasetHash = (Get-FileHash -LiteralPath $Dataset -Algorithm SHA256).Hash.ToLowerInvariant()
$trainingArgsHash = (Get-FileHash -LiteralPath $TrainingArgsFile -Algorithm SHA256).Hash.ToLowerInvariant()
$trainingResultsHash = (Get-FileHash -LiteralPath $TrainingResultsFile -Algorithm SHA256).Hash.ToLowerInvariant()
if ($bestHash -ne $finalHash -or $evaluation.weights_sha256.ToLowerInvariant() -ne $bestHash) {
    throw 'best.pt、系统正式权重与评估记录的 SHA-256 不一致'
}
if ($evaluation.dataset_yaml_sha256.ToLowerInvariant() -ne $datasetHash) {
    throw '评估记录与当前 TT100K 数据配置的 SHA-256 不一致'
}
if (
    $trainingArtifacts.args_yaml_sha256.ToLowerInvariant() -ne $trainingArgsHash -or
    $trainingArtifacts.results_csv_sha256.ToLowerInvariant() -ne $trainingResultsHash
) {
    throw '评估记录与训练 args.yaml/results.csv 的 SHA-256 不一致'
}

Set-Location (Join-Path $ProjectRoot 'backend')
$env:DATABASE_URL = 'sqlite:///./data/final-acceptance.db'
& $Python -m alembic upgrade head
if ($LASTEXITCODE -ne 0) { throw 'Alembic 迁移验收失败' }
& $Python -m pytest -q
if ($LASTEXITCODE -ne 0) { throw '后端测试验收失败' }

Set-Location (Join-Path $ProjectRoot 'frontend')
npm run typecheck
if ($LASTEXITCODE -ne 0) { throw '前端类型检查失败' }
npm run build
if ($LASTEXITCODE -ne 0) { throw '前端生产构建失败' }

Set-Location $ProjectRoot
& $Python 'scripts\e2e_smoke.py' `
    --weights $FinalWeight `
    --image 'samples\tt100k-10132.jpg' `
    --knowledge 'knowledge\校园交通巡检示例规范.md' `
    --device 0 `
    --output 'outputs\formal-model-e2e.json'
if ($LASTEXITCODE -ne 0) { throw '正式权重端到端巡检验收失败' }

docker compose --env-file .env.example config --quiet
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 配置验收失败' }
& (Join-Path $PSScriptRoot 'docker-runtime-acceptance.ps1')
if ($LASTEXITCODE -ne 0) { throw 'Docker Compose 运行态验收失败' }
if (-not (Test-Path -LiteralPath $DockerAcceptanceFile)) { throw 'Docker 运行态验收未生成结构化证据' }
$dockerAcceptance = Get-Content -LiteralPath $DockerAcceptanceFile -Raw | ConvertFrom-Json
if ($dockerAcceptance.status -ne 'passed') { throw "Docker 运行态验收记录不是 passed：$($dockerAcceptance.status)" }

$trainingCompletionPolicy = if ($status.status -eq 'completed_partial_by_user') {
    'accepted_user_stopped_checkpoint'
}
else {
    'completed_or_early_stopped'
}

@{
    status = 'passed'
    verified_at = (Get-Date).ToString('o')
    model = $FinalWeight
    model_sha256 = $finalHash
    model_size_bytes = [int64]$evaluation.weights_size_bytes
    dataset_yaml_sha256 = $datasetHash
    training_args_sha256 = $trainingArgsHash
    training_results_sha256 = $trainingResultsHash
    checkpoint_completed_epoch = $evaluation.checkpoint_completed_epoch
    training_completed_epochs = [int]$trainingArtifacts.completed_epochs
    training_requested_epochs = [int]$status.requested_epochs
    training_status = [string]$status.status
    training_stop_reason = [string]$status.stop_reason
    training_completion_policy = $trainingCompletionPolicy
    selection_criterion = 'highest_validation_map50_95'
    selected_validation_map50 = [double]$bestValidationRow.'metrics/mAP50(B)'
    selected_validation_map50_95 = [double]$bestValidationRow.'metrics/mAP50-95(B)'
    test_images = [int]$evaluation.test_images
    precision = [double]$evaluation.precision
    recall = [double]$evaluation.recall
    map50 = [double]$evaluation.map50
    map50_95 = [double]$evaluation.map50_95
    backend_tests = 'passed'
    frontend_typecheck = 'passed'
    frontend_build = 'passed'
    database_migration = 'passed'
    formal_model_e2e = 'passed'
    compose_config = 'passed'
    docker_runtime = 'passed'
    docker_runtime_evidence = $DockerAcceptanceFile
} | ConvertTo-Json | Set-Content -LiteralPath $AcceptanceFile -Encoding utf8

Get-Content -LiteralPath $AcceptanceFile
