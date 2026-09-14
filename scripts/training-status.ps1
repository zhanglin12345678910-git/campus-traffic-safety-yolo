$TrainingRoot = 'local-path/campus-yolo26-training'
$StatusFile = Join-Path $TrainingRoot 'status.json'
$ResultsFile = Join-Path $TrainingRoot 'yolo26m-tt100k-640\results.csv'
$StdoutLog = Join-Path $TrainingRoot 'baseline.stdout.log'
$StderrLog = Join-Path $TrainingRoot 'baseline.stderr.log'

. (Join-Path $PSScriptRoot 'training-progress.ps1')

if (Test-Path -LiteralPath $StatusFile) {
    Get-Content -LiteralPath $StatusFile
} else {
    Write-Output '{"status":"not_started"}'
}
if (Test-Path -LiteralPath $ResultsFile) {
    Write-Output '--- latest metric ---'
    Get-Content -LiteralPath $ResultsFile -Tail 2
}
Write-Output '--- structured progress ---'
Get-YoloTrainingProgress -LogPath $StdoutLog -ResultsPath $ResultsFile | ConvertTo-Json -Depth 5
if (Test-Path -LiteralPath $StdoutLog) {
    Write-Output '--- latest output ---'
    Get-Content -LiteralPath $StdoutLog -Tail 8
}
if ((Test-Path -LiteralPath $StderrLog) -and (Get-Item -LiteralPath $StderrLog).Length -gt 0) {
    Write-Output '--- latest error ---'
    Get-Content -LiteralPath $StderrLog -Tail 12
}
