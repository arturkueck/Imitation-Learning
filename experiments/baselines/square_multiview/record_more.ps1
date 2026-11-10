param([int]$Episodes = 50)
$ErrorActionPreference = 'Stop'
$outputRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $outputRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot 'praxis\.venv\Scripts\python.exe'
$evaluator = Join-Path $projectRoot 'experiments\baselines\square\scripts\evaluate.py'
$logRoot = Join-Path $outputRoot 'logs'
New-Item -ItemType Directory -Path $logRoot -Force | Out-Null
foreach ($algorithm in @('bc_rnn','bc_transformer')) {
    $checkpointPath = Join-Path $projectRoot "experiments\baselines\square_overnight\$algorithm\final.pth"
    & $pythonPath -u $evaluator $checkpointPath $algorithm --output-root $outputRoot --episodes $Episodes --layout collage *> (Join-Path $logRoot "$algorithm.log")
    if ($LASTEXITCODE -ne 0) { throw "Video generation failed: $algorithm" }
}
