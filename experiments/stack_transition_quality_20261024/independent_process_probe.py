import ctypes,json,os,time
from pathlib import Path
P=Path(__file__).resolve().parent
flag=ctypes.wintypes.BOOL() if hasattr(ctypes,'wintypes') else ctypes.c_int()
ok=ctypes.windll.kernel32.IsProcessInJob(ctypes.windll.kernel32.GetCurrentProcess(),None,ctypes.byref(flag))
(P/'independent_process_probe.json').write_text(json.dumps(dict(pid=os.getpid(),is_process_in_job=bool(flag.value),query_ok=bool(ok),started=time.time())))
time.sleep(3)
(P/'independent_process_probe.done').write_text(str(time.time()))
