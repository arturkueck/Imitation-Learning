$ErrorActionPreference = 'Stop'
$experimentRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$projectRoot = (Resolve-Path (Join-Path $experimentRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot 'praxis\.venv\Scripts\python.exe'
$launcherPath = Join-Path $projectRoot 'experiments\square\scripts\launch.py'
& $pythonPath $launcherPath --experiment-root $experimentRoot
if ($LASTEXITCODE -ne 0) { throw 'Detached launch failed' }
