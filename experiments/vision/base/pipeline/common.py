from pathlib import Path
import hashlib,json,os,time,math
from datetime import datetime,timezone
ROOT=Path(__file__).resolve().parents[4]
EXPERIMENT=Path(__file__).resolve().parents[1]
def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def save(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    with temp.open('w',encoding='utf-8') as f:json.dump(value,f,indent=2,allow_nan=False);f.flush();os.fsync(f.fileno())
    temp.replace(path)
def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def rooted(relative):
    p=(ROOT/relative).resolve()
    if not p.is_relative_to(ROOT.resolve()):raise ValueError('Path outside repository')
    return p
def event(run,stage,**values):
    value=dict(time=now(),heartbeat_unix=time.time(),pid=os.getpid(),stage=stage,**values)
    save(Path(run)/'status.json',value)
    with (Path(run)/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(value,allow_nan=False)+'\n')
def check_stop(run,reserve=0):
    if (Path(run)/'STOP_REQUESTED').exists():raise InterruptedError('STOP_REQUESTED')
    budget=Path(run)/'budget.json'
    if budget.exists() and time.time()>=read(budget)['deadline_unix']-reserve:raise TimeoutError('Fixed run deadline reached')
def begin_budget(run,hours):
    path=Path(run)/'budget.json'
    if path.exists():
        if hours is not None:raise ValueError('Existing deadline cannot be reset; omit --hours')
        return read(path)
    if hours is None or not math.isfinite(hours) or hours<=0:raise ValueError('First launch needs explicit finite positive --hours')
    value=dict(started=now(),started_unix=time.time(),deadline_unix=time.time()+hours*3600,hours=hours)
    save(path,value);return value
