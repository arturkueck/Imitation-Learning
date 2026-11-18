$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
$taskPython = Join-Path $taskRoot 'praxis/.venv/Scripts/python.exe'
$taskPipeline = Join-Path $PSScriptRoot 'pipeline.py'
$taskOutput = Join-Path $taskRoot 'praxis/results/curriculum/targeted_correction_budget_v1/night_20261117'
$taskStatus = Get-Content -LiteralPath (Join-Path $taskOutput 'status.json') -Raw | ConvertFrom-Json
if ($taskStatus.state -ne 'READY') { throw 'Expected READY. No automatic restart.' }
if (Test-Path -LiteralPath (Join-Path $taskOutput 'launch.json')) { throw 'This run was already launched.' }
& $taskPython $taskPipeline verify --output $taskOutput
if ($LASTEXITCODE -ne 0) { throw 'Frozen-input verification failed.' }
$taskArguments = @('-u', ('"{0}"' -f $taskPipeline), 'run', '--output', ('"{0}"' -f $taskOutput))
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList $taskArguments -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskOutput 'launcher.stdout.log') -RedirectStandardError (Join-Path $taskOutput 'launcher.stderr.log')
[pscustomobject]@{ launcher_pid = $taskProcess.Id; output = $taskOutput; deadline = '2026-11-18 09:00 Europe/Berlin' } | ConvertTo-Json
