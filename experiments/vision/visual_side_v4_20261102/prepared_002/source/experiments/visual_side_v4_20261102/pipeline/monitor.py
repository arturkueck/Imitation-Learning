"""Incremental deterministic status check; never restarts a worker."""
import json,time
from pathlib import Path
from .common import read,save

def check(run):
    run=Path(run);path=run/'events.jsonl';state_path=run/'monitor_state.json';state=read(state_path) if state_path.exists() else {}
    status=read(run/'status.json');offset=state.get('offset',0);new=[]
    if path.exists():
        size=path.stat().st_size
        if offset>size:offset=0
        with path.open('rb') as f:
            f.seek(offset);data=f.read(65536);end=data.rfind(b'\n')
            if end>=0:
                new=[json.loads(line) for line in data[:end+1].splitlines()];offset+=end+1
    changed=state.get('stage')!=status['stage'] or state.get('step')!=status.get('step') or bool(new)
    error=status['stage']=='error' or any(r['stage']=='error' for r in new)
    result=dict(level='ERROR' if error else 'READY' if status['stage']=='prepared' else 'DONE' if status['stage']=='complete' else 'WARNING' if time.time()-status.get('heartbeat_unix',0)>600 else 'OK',
        stage=status['stage'],step=status.get('step'),new_errors=sum(r['stage']=='error' for r in new),changed=changed,action='none',training_started=status.get('training_started',False))
    # Host PID isolation must not be mistaken for a crashed process.
    if status.get('pid') and status['stage'] not in ['prepared','complete']:
        try:
            import psutil
            process=psutil.Process(status['pid']);result['process_visibility']='visible'
            if status.get('pid_created') and abs(process.create_time()-status['pid_created'])>1:result.update(level='WARNING',process_visibility='pid_reused')
        except Exception:result['process_visibility']='unknown_no_restart'
    save(state_path,dict(offset=offset,stage=status['stage'],step=status.get('step'),checked_unix=time.time()))
    return result
