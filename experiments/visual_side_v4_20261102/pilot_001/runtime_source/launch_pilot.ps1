$ErrorActionPreference = 'Stop'
$experimentRoot = $PSScriptRoot
$workspaceRoot = Split-Path (Split-Path $experimentRoot -Parent) -Parent
$runPath = Join-Path $experimentRoot 'pilot_001'
$pythonExe = 'C:\Users\artur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
if (Test-Path -LiteralPath (Join-Path $runPath 'wmi_launch.json')) { throw 'Launch already recorded; inspect before retry.' }
$startup = New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ ShowWindow = [uint16]0; CreateFlags = [uint32]0x01000000 }
$entry = Join-Path $experimentRoot 'runtime_entry.py'
$command = '"' + $pythonExe + '" "' + $entry + '" supervise "' + $runPath + '"'
$result = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$workspaceRoot;ProcessStartupInformation=$startup}
if ($result.ReturnValue -ne 0) { throw "WMI launch failed: $($result.ReturnValue)" }
@{supervisor_pid=$result.ProcessId;launch_method='WMI base Python, breakaway, hidden';time=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runPath 'wmi_launch.json') -Encoding utf8
Get-Content -LiteralPath (Join-Path $runPath 'wmi_launch.json')
