param([ValidatePattern('^ready_[0-9]+$')][string]$RunName = 'ready_001')
$ErrorActionPreference = 'Stop'
$projectPath = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonPath = Join-Path $projectPath 'praxis\.venv\Scripts\python.exe'
$nightScript = Join-Path $PSScriptRoot 'night.py'
$runPath = Join-Path $PSScriptRoot $RunName
& $pythonPath $nightScript preflight --output $runPath
if ($LASTEXITCODE -ne 0) { throw 'Nachtlauf-Vorpruefung fehlgeschlagen.' }
$arguments = @('-u', ('"' + $nightScript + '"'), 'supervise', '--output', ('"' + $runPath + '"'), '--device', 'cuda')
$nightProcess = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runPath 'supervisor.stdout.log') -RedirectStandardError (Join-Path $runPath 'supervisor.stderr.log') -PassThru
$nightProcess | Select-Object Id,StartTime | ConvertTo-Json -Compress
