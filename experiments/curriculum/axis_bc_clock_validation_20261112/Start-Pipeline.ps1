param([ValidatePattern('^ready_[0-9]+$')][string]$RunName = 'ready_001')
$ErrorActionPreference = 'Stop'
$projectPath = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonPath = Join-Path $projectPath 'praxis\.venv\Scripts\python.exe'
$pipelineScript = Join-Path $PSScriptRoot 'pipeline.py'
$runPath = Join-Path $PSScriptRoot $RunName
& $pythonPath $pipelineScript preflight --output $runPath
if ($LASTEXITCODE -ne 0) { throw 'Pipeline-Vorpruefung fehlgeschlagen.' }
$arguments = @('-u', ('"' + $pipelineScript + '"'), 'supervise', '--output', ('"' + $runPath + '"'), '--device', 'cuda')
$pipelineProcess = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runPath 'supervisor.stdout.log') -RedirectStandardError (Join-Path $runPath 'supervisor.stderr.log') -PassThru
$pipelineProcess | Select-Object Id,StartTime | ConvertTo-Json -Compress
