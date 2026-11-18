# Registriert vier Kalendernächte auf dem lokalen Rechner.
[CmdletBinding()]
param([Parameter(Mandatory)][datetime] $FirstNight)
$ErrorActionPreference = 'Stop'
$taskName = 'Codex - Dreierturm Nachtagenten'
if ((Get-TimeZone).Id -ne 'W. Europe Standard Time') {
    throw 'Die Aufgabe erwartet die lokale Windows-Zeitzone Europe/Berlin.'
}
$repo = (Resolve-Path (Join-Path $PSScriptRoot '../../..')).Path
if ((git -C $repo branch --show-current) -ne 'experiment_three_cube_critic') {
    throw 'Installation nur im Experiment-Worktree.'
}
$python = (Get-Item -LiteralPath "$repo/praxis/.venv/Scripts/pythonw.exe").FullName
$codex = (Get-Command codex.exe -CommandType Application | Select-Object -First 1).Source
$results = Join-Path $repo 'praxis/results/critic/three_cube_transfer_v1'
[IO.Directory]::CreateDirectory($results) | Out-Null
$arguments = '"{0}" --first-night {1} --codex "{2}"' -f (Join-Path $PSScriptRoot 'night_agent.py'), $FirstNight.ToString('yyyy-MM-dd'), $codex
$action = New-ScheduledTaskAction -Execute $python -Argument $arguments -WorkingDirectory $repo
$triggers = foreach ($day in 0..3) {
    foreach ($offset in 0,3,6,9,9.5,10.5) {
        $at = $FirstNight.Date.AddDays($day).AddHours(22 + $offset)
        if ($at -gt (Get-Date)) { New-ScheduledTaskTrigger -Once -At $at }
    }
}
if (-not $triggers) { throw 'Alle vier Nächte sind bereits vorbei.' }
$settings = New-ScheduledTaskSettingsSet -MultipleInstances IgnoreNew -WakeToRun -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit (New-TimeSpan -Hours 12)
$principal = New-ScheduledTaskPrincipal -UserId ([Security.Principal.WindowsIdentity]::GetCurrent().Name) -LogonType Interactive -RunLevel Limited
Register-ScheduledTask -TaskName $taskName -Description 'Je Aufgabe ein Codex-Agent. Übergaben nach NACHTPLAN.md auf experiment_three_cube_critic.' -Action $action -Trigger $triggers -Settings $settings -Principal $principal | Select-Object TaskName,State
