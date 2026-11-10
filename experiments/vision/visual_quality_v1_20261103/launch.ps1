param([ValidatePattern('^prepared_[0-9]+$')][string]$Run='prepared_001',[ValidateRange(1,12)][double]$Hours=12)
$ErrorActionPreference='Stop'
$runPath=Join-Path $PSScriptRoot $Run
if (Test-Path -LiteralPath (Join-Path $runPath 'launch_requested.json')) { throw 'Launch already recorded; do not retry blindly.' }
$pythonExe='C:\Users\artur\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
$workspaceRoot=Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
$startup=New-CimInstance -ClassName Win32_ProcessStartup -ClientOnly -Property @{ShowWindow=[uint16]0;CreateFlags=[uint32]0x01000000}
$entry=Join-Path $PSScriptRoot 'runtime.py'
$command='"'+$pythonExe+'" "'+$entry+'" supervise "'+$runPath+'" '+$Hours
$result=Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine=$command;CurrentDirectory=$workspaceRoot;ProcessStartupInformation=$startup}
if ($result.ReturnValue -ne 0) { throw "WMI start failed: $($result.ReturnValue)" }
@{supervisor_pid=$result.ProcessId;hours=$Hours;time=(Get-Date).ToUniversalTime().ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $runPath 'launch_requested.json') -Encoding utf8
