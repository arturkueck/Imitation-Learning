import ctypes,json,os,time
from ctypes import wintypes
from pathlib import Path
P=Path(__file__).resolve().parent
kernel=ctypes.WinDLL('kernel32',use_last_error=True)
kernel.GetCurrentProcess.restype=wintypes.HANDLE
kernel.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
kernel.IsProcessInJob.restype=wintypes.BOOL
flag=wintypes.BOOL();ok=kernel.IsProcessInJob(kernel.GetCurrentProcess(),None,ctypes.byref(flag))
(P/'independent_process_probe_v2.json').write_text(json.dumps(dict(pid=os.getpid(),is_process_in_job=bool(flag.value),query_ok=bool(ok),error=ctypes.get_last_error(),started=time.time())))
time.sleep(2)
(P/'independent_process_probe_v2.done').write_text(str(time.time()))
