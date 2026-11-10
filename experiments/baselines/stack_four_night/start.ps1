$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
$projectRoot = (Resolve-Path (Join-Path $experimentRoot '..\..')).Path
& (Join-Path $projectRoot 'praxis\.venv\Scripts\python.exe') (Join-Path $projectRoot 'experiments\baselines\square\scripts\launch.py') --experiment-root $experimentRoot
if ($LASTEXITCODE -ne 0) { throw 'Independent process launch failed' }
