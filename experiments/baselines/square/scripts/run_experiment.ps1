param([Parameter(Mandatory=$true)][ValidateSet('bc','bc_rnn','bc_transformer')][string]$Algorithm)
$ErrorActionPreference = 'Stop'
$experimentRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$projectRoot = (Resolve-Path (Join-Path $experimentRoot '..\..')).Path
$pythonPath = Join-Path $projectRoot 'praxis\.venv\Scripts\python.exe'
& $pythonPath (Join-Path $PSScriptRoot 'train_model.py') (Join-Path $experimentRoot "$Algorithm\config.json")
if ($LASTEXITCODE -ne 0) { throw 'Training failed' }
$model = Get-ChildItem (Join-Path $experimentRoot "$Algorithm\runs") -Recurse -Filter 'model_epoch_50*.pth'
if (@($model).Count -ne 1) { throw 'Final checkpoint absent or ambiguous' }
& $pythonPath (Join-Path $PSScriptRoot 'evaluate.py') $model.FullName $Algorithm
if ($LASTEXITCODE -ne 0) { throw 'Evaluation failed' }
