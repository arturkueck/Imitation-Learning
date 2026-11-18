param([ValidatePattern('^ready_[0-9]+$')][string]$RunName = 'ready_001')
$ErrorActionPreference = 'Stop'
$projectPath = (Get-Item -LiteralPath $PSScriptRoot).Parent.Parent.Parent.FullName
$pythonPath = Join-Path $projectPath 'praxis\.venv\Scripts\python.exe'
$trainScript = Join-Path $PSScriptRoot 'train.py'
$runPath = Join-Path $projectPath ('praxis\results\curriculum\abc_comparison_20261112\' + $RunName)
& $pythonPath $trainScript preflight --output $runPath
if ($LASTEXITCODE -ne 0) { throw 'A/B/C-Vorpruefung fehlgeschlagen.' }
$arguments = @('-u', ('"' + $trainScript + '"'), 'supervise', '--output', ('"' + $runPath + '"'), '--device', 'cuda')
$abcProcess = Start-Process -FilePath $pythonPath -ArgumentList $arguments -WorkingDirectory $projectPath -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runPath 'supervisor.stdout.log') -RedirectStandardError (Join-Path $runPath 'supervisor.stderr.log') -PassThru
$abcProcess | Select-Object Id,StartTime | ConvertTo-Json -Compress
