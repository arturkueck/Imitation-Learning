$ErrorActionPreference = 'Stop'
$experimentRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$projectRoot = (Resolve-Path (Join-Path $experimentRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot 'praxis\.venv\Scripts\python.exe'
& $pythonPath (Join-Path $PSScriptRoot 'launch.py')
if ($LASTEXITCODE -ne 0) { throw 'Detached launch failed' }
