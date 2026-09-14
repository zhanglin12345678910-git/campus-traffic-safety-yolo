function Get-YoloTrainingProgress {
    param(
        [Parameter(Mandatory)][string]$LogPath,
        [Parameter(Mandatory)][string]$ResultsPath,
        [ValidateRange(16384, 1048576)][int]$TailBytes = 131072
    )

    $result = [ordered]@{
        stage = 'unknown'
        epoch = $null
        epochs = $null
        batch = $null
        batches = $null
        percent = $null
        last_completed_epoch = $null
        latest_metrics = $null
    }

    if (Test-Path -LiteralPath $ResultsPath) {
        $metric = Import-Csv -LiteralPath $ResultsPath | Select-Object -Last 1
        if ($metric) {
            $result.last_completed_epoch = [int]$metric.epoch
            $result.latest_metrics = [ordered]@{
                precision = [double]$metric.'metrics/precision(B)'
                recall = [double]$metric.'metrics/recall(B)'
                map50 = [double]$metric.'metrics/mAP50(B)'
                map50_95 = [double]$metric.'metrics/mAP50-95(B)'
            }
        }
    }

    if (-not (Test-Path -LiteralPath $LogPath)) {
        return [pscustomobject]$result
    }

    $stream = [System.IO.File]::Open(
        $LogPath,
        [System.IO.FileMode]::Open,
        [System.IO.FileAccess]::Read,
        [System.IO.FileShare]::ReadWrite -bor [System.IO.FileShare]::Delete
    )
    try {
        $length = [math]::Min([long]$TailBytes, $stream.Length)
        [void]$stream.Seek(-$length, [System.IO.SeekOrigin]::End)
        $reader = [System.IO.StreamReader]::new($stream, [System.Text.Encoding]::UTF8, $true, 4096, $true)
        try { $text = $reader.ReadToEnd() }
        finally { $reader.Dispose() }
    }
    finally {
        $stream.Dispose()
    }

    $escape = [regex]::Escape([string][char]27)
    $clean = [regex]::Replace($text, "$escape\[[0-?]*[ -/]*[@-~]", '')
    $trainMatches = [regex]::Matches(
        $clean,
        '(?m)(?<epoch>\d+)/(?<epochs>\d+)[^\r\n]*?(?<percent>\d+)%[^\r\n]*?(?<batch>\d+)/(?<batches>\d+)'
    )
    $validationMatches = [regex]::Matches(
        $clean,
        '(?m)Class[^\r\n]*?(?<percent>\d+)%[^\r\n]*?(?<batch>\d+)/(?<batches>\d+)'
    )
    $latestTrain = $null
    if ($trainMatches.Count -gt 0) {
        $maxTrainBatches = ($trainMatches | ForEach-Object { [int]$_.Groups['batches'].Value } | Measure-Object -Maximum).Maximum
        $completeTrainMatches = @($trainMatches | Where-Object { [int]$_.Groups['batches'].Value -eq $maxTrainBatches })
        $latestTrain = $completeTrainMatches[$completeTrainMatches.Count - 1]
    }
    $latestValidation = $null
    if ($validationMatches.Count -gt 0) {
        $maxValidationBatches = ($validationMatches | ForEach-Object { [int]$_.Groups['batches'].Value } | Measure-Object -Maximum).Maximum
        $completeValidationMatches = @($validationMatches | Where-Object { [int]$_.Groups['batches'].Value -eq $maxValidationBatches })
        $latestValidation = $completeValidationMatches[$completeValidationMatches.Count - 1]
    }

    if ($latestValidation -and (-not $latestTrain -or $latestValidation.Index -gt $latestTrain.Index)) {
        $result.stage = 'validation'
        if ($latestTrain) {
            $result.epoch = [int]$latestTrain.Groups['epoch'].Value
            $result.epochs = [int]$latestTrain.Groups['epochs'].Value
        }
        $result.percent = [int]$latestValidation.Groups['percent'].Value
        $result.batch = [int]$latestValidation.Groups['batch'].Value
        $result.batches = [int]$latestValidation.Groups['batches'].Value
    }
    elseif ($latestTrain) {
        $result.stage = 'training'
        $result.epoch = [int]$latestTrain.Groups['epoch'].Value
        $result.epochs = [int]$latestTrain.Groups['epochs'].Value
        $result.percent = [int]$latestTrain.Groups['percent'].Value
        $result.batch = [int]$latestTrain.Groups['batch'].Value
        $result.batches = [int]$latestTrain.Groups['batches'].Value
    }

    [pscustomobject]$result
}
