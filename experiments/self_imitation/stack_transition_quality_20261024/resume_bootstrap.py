import sys,site,runpy,ctypes,json,os,time
from ctypes import wintypes
from pathlib import Path
P=Path(__file__).resolve().parent
site.addsitedir(r'F:\Desktop\Programmieren\IT\Imitation Learning\praxis\.venv\Lib\site-packages')
sys.path.insert(0,str(P))
k=ctypes.WinDLL('kernel32',use_last_error=True)
k.GetCurrentProcess.restype=wintypes.HANDLE
k.IsProcessInJob.argtypes=[wintypes.HANDLE,wintypes.HANDLE,ctypes.POINTER(wintypes.BOOL)]
k.IsProcessInJob.restype=wintypes.BOOL
flag=wintypes.BOOL();ok=k.IsProcessInJob(k.GetCurrentProcess(),None,ctypes.byref(flag))
proof=dict(pid=os.getpid(),query_ok=bool(ok),is_process_in_job=bool(flag.value),unix=time.time(),argv=sys.argv)
(P/('process_independence_'+str(os.getpid())+'.json')).write_text(json.dumps(proof))
assert ok and not flag.value,'Refusing training inside a kill-on-close process job'
runpy.run_path(str(P/'resume_run.py'),run_name='__main__')
