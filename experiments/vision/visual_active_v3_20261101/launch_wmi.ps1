$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
$workspaceRoot = Split-Path (Split-Path $experimentRoot -Parent) -Parent
$runPath = Join-Path $experimentRoot 'run_001'
$pythonExe = 'C:\Users\artur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath (Join-Path $experimentRoot 'deadline_guard.lock')) { throw 'An existing guard must be inspected before launch.' }
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0; CreateFlags = [uint32]0x01000000 }
$bootstrap = Join-Path $experimentRoot 'independent_bootstrap.py'
$guardLog = Join-Path $experimentRoot 'deadline_guard_retry001.log'
$supervisorLog = Join-Path $runPath 'supervisor_retry001.log'
if ((Test-Path -LiteralPath $guardLog) -or (Test-Path -LiteralPath $supervisorLog)) { throw 'Retry logs already exist; do not repeat launch blindly.' }
$guardCommand = '"' + $pythonExe + '" "' + $bootstrap + '" guard "' + $runPath + '" "' + $guardLog + '"'
$guard = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$guardCommand;CurrentDirectory=$workspaceRoot;ProcessStartupInformation=$startup}
if ($guard.ReturnValue -ne 0) { throw "WMI guard launch failed: $($guard.ReturnValue)" }
$supervisorCommand = '"' + $pythonExe + '" "' + $bootstrap + '" supervise "' + $runPath + '" "' + $supervisorLog + '"'
$supervisor = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$supervisorCommand;CurrentDirectory=$workspaceRoot;ProcessStartupInformation=$startup}
if ($supervisor.ReturnValue -ne 0) { throw "WMI supervisor launch failed: $($supervisor.ReturnValue)" }
@{guard_pid=$guard.ProcessId;supervisor_pid=$supervisor.ProcessId;launch_method='WMI base Python, breakaway, hidden';time=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runPath 'launch_retry001.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $runPath 'launch_retry001.json')
