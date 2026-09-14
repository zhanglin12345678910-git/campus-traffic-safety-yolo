#requires -Version 7.0

param(
    [ValidateRange(60, 1800)]
    [int]$TimeoutSeconds = 600
)

$ErrorActionPreference = 'Stop'

$ProjectRoot = Split-Path -Parent $PSScriptRoot
$ResultFile = Join-Path $ProjectRoot 'outputs\docker-runtime-acceptance.json'
$LogFile = Join-Path $ProjectRoot 'outputs\docker-runtime-acceptance.log'
$ComposeArguments = @('compose', '--project-name', 'campus-safety-acceptance', '--env-file', '.env.example')
if (Test-Path -LiteralPath (Join-Path $ProjectRoot '.env')) {
    $ComposeArguments += @('--env-file', '.env')
}
$ComposeArguments += @('-f', 'docker-compose.yml', '-f', 'docker-compose.acceptance.yml')
$startedAt = (Get-Date).ToString('o')
$script:DockerServerVersion = ''
$script:RunningServices = @()
$script:ApiHealth = $null
$script:QdrantVersion = ''
$script:FrontendStatusCode = 0
$script:DatabaseSchema = $null
$script:KnowledgeProbe = $null
$script:InspectionProbe = $null

function Invoke-Docker {
    param([Parameter(Mandatory)][string[]]$Arguments)
    & docker @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "docker $($Arguments -join ' ') 退出码为 $LASTEXITCODE"
    }
}

function Invoke-MultipartJson {
    param(
        [Parameter(Mandatory)][string]$Uri,
        [Parameter(Mandatory)][string]$FilePath,
        [Parameter(Mandatory)][string]$FileName,
        [Parameter(Mandatory)][string]$ContentType,
        [hashtable]$Fields = @{},
        [hashtable]$Headers = @{},
        [ValidateRange(1, 600)][int]$RequestTimeoutSeconds = 60
    )

    $curlArguments = @(
        '--silent', '--show-error', '--fail-with-body',
        '--request', 'POST',
        '--max-time', [string]$RequestTimeoutSeconds
    )
    foreach ($headerName in $Headers.Keys) {
        $curlArguments += @('--header', "${headerName}: $($Headers[$headerName])")
    }
    foreach ($fieldName in $Fields.Keys) {
        $curlArguments += @('--form', "${fieldName}=$($Fields[$fieldName])")
    }
    $curlArguments += @(
        '--form', "file=@${FilePath};filename=${FileName};type=${ContentType}",
        $Uri
    )

    $rawOutput = @(& curl.exe @curlArguments)
    $curlExitCode = $LASTEXITCODE
    $responseBody = $rawOutput -join [Environment]::NewLine
    if ($curlExitCode -ne 0) {
        throw "multipart 请求失败（curl 退出码 $curlExitCode）：$responseBody"
    }
    try {
        return $responseBody | ConvertFrom-Json
    }
    catch {
        throw "multipart 请求未返回有效 JSON：$responseBody"
    }
}

function Write-AcceptanceResult {
    param(
        [Parameter(Mandatory)][string]$Status,
        [string]$ErrorMessage = ''
    )
    $result = [ordered]@{
        status = $Status
        started_at = $startedAt
        finished_at = (Get-Date).ToString('o')
        compose_project = 'campus-safety-acceptance'
        frontend_url = 'http://127.0.0.1:8081/'
        api_health_url = 'http://127.0.0.1:8081/api/v1/health'
        qdrant_url = 'http://127.0.0.1:6334/'
        required_services = @('mysql', 'qdrant', 'backend', 'frontend')
        docker_server_version = $script:DockerServerVersion
        running_services = @($script:RunningServices)
        api_health = $script:ApiHealth
        qdrant_version = $script:QdrantVersion
        frontend_status_code = $script:FrontendStatusCode
        database_schema = $script:DatabaseSchema
        knowledge_probe = $script:KnowledgeProbe
        inspection_probe = $script:InspectionProbe
        error = $ErrorMessage
    }
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $ResultFile) | Out-Null
    $result | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $ResultFile -Encoding utf8
}

Set-Location $ProjectRoot

try {
    $dockerVersionOutput = @(& docker info --format '{{.ServerVersion}}')
    if ($LASTEXITCODE -ne 0 -or $dockerVersionOutput.Count -eq 0) {
        throw 'Docker Engine 不可用或未返回服务端版本'
    }
    $script:DockerServerVersion = ([string]$dockerVersionOutput[0]).Trim()
    if (-not $script:DockerServerVersion) { throw 'Docker Engine 返回了空版本号' }
    Invoke-Docker -Arguments ($ComposeArguments + @('config', '--quiet'))
    Invoke-Docker -Arguments ($ComposeArguments + @('up', '-d', '--build'))

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    $lastReason = '等待服务启动'
    $ready = $false
    do {
        try {
            $runningServices = @(& docker @ComposeArguments ps --services --status running)
            if ($LASTEXITCODE -ne 0) {
                throw '无法读取 Compose 服务状态'
            }
            $missingServices = @('mysql', 'qdrant', 'backend', 'frontend') | Where-Object { $_ -notin $runningServices }
            if ($missingServices.Count -gt 0) {
                throw "服务尚未全部运行：$($missingServices -join ', ')"
            }
            $script:RunningServices = $runningServices

            $health = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/api/v1/health' -TimeoutSec 10
            if ($health.status -ne 'ok') { throw "后端健康状态为 $($health.status)" }
            if ($health.services.database -ne 'ok') { throw 'MySQL 健康检查未通过' }
            if ($health.services.qdrant.status -ne 'ok') { throw 'Qdrant 健康检查未通过' }
            if (-not [bool]$health.services.yolo.configured) { throw '正式 YOLO26 权重未挂载' }
            $script:ApiHealth = $health

            $qdrant = Invoke-RestMethod -Uri 'http://127.0.0.1:6334/' -TimeoutSec 10
            if (-not $qdrant.version) { throw 'Qdrant 根端点未返回版本' }
            $script:QdrantVersion = [string]$qdrant.version

            $frontend = Invoke-WebRequest -Uri 'http://127.0.0.1:8081/' -TimeoutSec 10
            if ($frontend.StatusCode -ne 200 -or $frontend.Content -notmatch 'id="app"') {
                throw '前端页面未正确返回 Vue 挂载点'
            }
            $script:FrontendStatusCode = [int]$frontend.StatusCode

            $ready = $true
            break
        }
        catch {
            $lastReason = $_.Exception.Message
            Start-Sleep -Seconds 5
        }
    } while ((Get-Date) -lt $deadline)

    if (-not $ready) { throw "Docker 运行态验收超时：$lastReason" }

    $schemaOutput = @(Invoke-Docker -Arguments ($ComposeArguments + @('exec', '-T', 'backend', 'python', '-m', 'app.docker_probe')))
    $schemaLine = $schemaOutput | Where-Object { $_ -match '^\s*\{' } | Select-Object -Last 1
    if (-not $schemaLine) { throw '数据库迁移探针未返回 JSON' }
    $script:DatabaseSchema = $schemaLine | ConvertFrom-Json
    if ($script:DatabaseSchema.status -ne 'passed' -or $script:DatabaseSchema.missing_tables.Count -gt 0) {
        throw '容器 MySQL 表结构或 Alembic 版本验收失败'
    }

    $apiHeaders = @{}
    $localEnvFile = Join-Path $ProjectRoot '.env'
    if (Test-Path -LiteralPath $localEnvFile) {
        $apiKeyLine = Get-Content -LiteralPath $localEnvFile | Where-Object { $_ -match '^\s*API_KEY\s*=' } | Select-Object -Last 1
        if ($apiKeyLine) {
            $apiKey = ($apiKeyLine -replace '^\s*API_KEY\s*=\s*', '').Trim().Trim('"').Trim("'")
            if ($apiKey) { $apiHeaders['X-API-Key'] = $apiKey }
        }
    }

    $knowledgeFile = Get-Item -LiteralPath (Join-Path $ProjectRoot 'knowledge\校园交通巡检示例规范.md')
    $knowledge = Invoke-MultipartJson `
        -Uri 'http://127.0.0.1:8081/api/v1/knowledge/documents' `
        -FilePath $knowledgeFile.FullName `
        -FileName 'campus-inspection-rules.md' `
        -ContentType 'text/markdown' `
        -Headers $apiHeaders `
        -RequestTimeoutSeconds 60
    if ($knowledge.status -ne 'ready' -or [int]$knowledge.chunk_count -lt 1) {
        throw 'Docker 知识文档未完成 Qdrant 入库'
    }
    $searchBody = @{query='校园交通标志巡检处置要求'; top_k=3} | ConvertTo-Json
    $search = Invoke-RestMethod `
        -Method Post `
        -Uri 'http://127.0.0.1:8081/api/v1/knowledge/search' `
        -Headers $apiHeaders `
        -ContentType 'application/json' `
        -Body $searchBody `
        -TimeoutSec 30
    if ([int]$search.total -lt 1) { throw 'Docker Qdrant 检索未返回已入库知识' }
    $script:KnowledgeProbe = [ordered]@{
        document_id = $knowledge.id
        chunks = [int]$knowledge.chunk_count
        search_hits = [int]$search.total
    }

    # Use a sharp TT100K road image so the production image-quality guardrail
    # passes naturally and the container must exercise the real YOLO path.
    $sampleImage = Get-Item -LiteralPath (Join-Path $ProjectRoot 'frontend\src\assets\incidents\dormitory-road.jpg')
    $inspection = Invoke-MultipartJson `
        -Uri 'http://127.0.0.1:8081/api/v1/inspections' `
        -FilePath $sampleImage.FullName `
        -FileName 'tt100k-dormitory-road.jpg' `
        -ContentType 'image/jpeg' `
        -Headers $apiHeaders `
        -Fields @{
            location='Docker 最终验收点'
            area_type='校园主干道'
            description='正式 YOLO26 容器端到端验收'
        } `
        -RequestTimeoutSeconds 60
    if (-not $inspection.id) { throw 'Docker 巡检任务创建失败' }
    $null = Invoke-RestMethod `
        -Method Post `
        -Uri "http://127.0.0.1:8081/api/v1/inspections/$($inspection.id)/execute" `
        -Headers $apiHeaders `
        -TimeoutSec 30

    $inspectionDeadline = (Get-Date).AddMinutes(5)
    do {
        Start-Sleep -Seconds 2
        $detail = Invoke-RestMethod `
            -Uri "http://127.0.0.1:8081/api/v1/inspections/$($inspection.id)" `
            -Headers $apiHeaders `
            -TimeoutSec 30
    } while ($detail.status -notin @('completed', 'review', 'rejected', 'error') -and (Get-Date) -lt $inspectionDeadline)
    if ($detail.status -notin @('completed', 'review')) {
        throw "Docker 巡检未成功完成：$($detail.status)"
    }
    if (-not $detail.report_id -or -not $detail.risk_result) {
        throw 'Docker 巡检缺少风险结果或报告'
    }

    $trace = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8081/api/v1/inspections/$($inspection.id)/trace" `
        -Headers $apiHeaders `
        -TimeoutSec 30
    $detectStep = @($trace.steps | Where-Object { $_.node_name -eq 'detect_traffic_signs' -and $_.status -eq 'success' })
    $reportStep = @($trace.steps | Where-Object { $_.node_name -eq 'generate_report' -and $_.status -eq 'success' })
    if ($detectStep.Count -eq 0 -or $reportStep.Count -eq 0) {
        throw 'Docker LangGraph 轨迹缺少成功的检测或报告节点'
    }
    $report = Invoke-RestMethod `
        -Uri "http://127.0.0.1:8081/api/v1/reports/$($detail.report_id)" `
        -Headers $apiHeaders `
        -TimeoutSec 30
    if (-not $report.id -or ([string]$report.html_content).Length -lt 50) {
        throw 'Docker 报告内容未正确生成'
    }

    $postRunHealth = Invoke-RestMethod -Uri 'http://127.0.0.1:8081/api/v1/health' -TimeoutSec 10
    if (-not [bool]$postRunHealth.services.yolo.loaded -or [int]$postRunHealth.services.yolo.load_count -lt 1) {
        throw 'Docker 正式 YOLO26 未在真实巡检中加载'
    }
    $script:ApiHealth = $postRunHealth
    $script:InspectionProbe = [ordered]@{
        task_id = $inspection.id
        status = $detail.status
        detections = @($detail.detections).Count
        risk_level = $detail.risk_result.risk_level
        trace_nodes = @($trace.steps.node_name)
        report_id = $report.id
        report_length = ([string]$report.html_content).Length
        yolo_model = $postRunHealth.services.yolo.model_name
        yolo_load_count = [int]$postRunHealth.services.yolo.load_count
    }

    Write-AcceptanceResult -Status 'passed'
    Get-Content -LiteralPath $ResultFile
}
catch {
    $message = $_.Exception.Message
    Write-AcceptanceResult -Status 'failed' -ErrorMessage $message
    try { & docker @ComposeArguments ps | Out-String | Set-Content -LiteralPath $LogFile -Encoding utf8 }
    catch { }
    throw
}
