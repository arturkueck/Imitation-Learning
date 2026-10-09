import sys,json,time,traceback
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O.parent))
from checks import run_checks
start=time.monotonic()
try:r=run_checks();r['state']='PREFLIGHT_PASSED';code=0
except BaseException:r=dict(state='FAILED',error=traceback.format_exc());traceback.print_exc();code=2
r['elapsed_seconds']=time.monotonic()-start
with (O/'result.json').open('x',encoding='utf-8') as out:json.dump(r,out,indent=2)
print(json.dumps(r,indent=2));raise SystemExit(code)
