$ErrorActionPreference = 'Stop'
$taskRoot = (Resolve-Path -LiteralPath (Join-Path $PSScriptRoot '..\..')).Path
$taskPython = Join-Path $taskRoot 'praxis\.venv\Scripts\python.exe'
$taskScript = 'experiments/diffusion_sanity_lift_transport_20261003/scripts/run.py'
$taskLaunchFile = Join-Path $PSScriptRoot 'launch.json'
if ((Test-Path -LiteralPath $taskLaunchFile) -or (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'worker_started.json'))) {
    throw 'This experiment has already been launched; refusing a duplicate.'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'preflight.json'))) { throw 'Preflight is missing.' }
$taskProcess = Start-Process -FilePath $taskPython -ArgumentList @('-u', $taskScript) -WorkingDirectory $taskRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot 'startup_stdout.log') -RedirectStandardError (Join-Path $PSScriptRoot 'startup_stderr.log') -PassThru
$taskInfo = [ordered]@{
    launcher_pid = $taskProcess.Id
    executable = $taskPython
    arguments = @('-u', $taskScript)
    working_directory = $taskRoot
    launched_at = [DateTimeOffset]::Now.ToString('o')
    window_style = 'Hidden'
    log_file = (Join-Path $PSScriptRoot 'run.log')
    worker_pid_file = (Join-Path $PSScriptRoot 'worker_started.json')
    start_command = 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File experiments/diffusion_sanity_lift_transport_20261003/start.ps1'
}
[System.IO.File]::WriteAllText($taskLaunchFile, ($taskInfo | ConvertTo-Json -Depth 4), [System.Text.UTF8Encoding]::new($false))
# One immediate launch check; no waiting for training and no polling.
$taskProcess.Refresh()
if ($taskProcess.HasExited) { throw "Worker exited during launch (exit $($taskProcess.ExitCode)); inspect run.log." }
$taskInfo | ConvertTo-Json -Depth 4
