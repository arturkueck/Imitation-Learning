"""Incremental routine check; no model loads or repository scans."""
from pathlib import Path
import json
import time
import re
import psutil

HERE=Path(__file__).resolve().parent
OUT=HERE/'run_001'


def main():
    folder=OUT/'monitor';folder.mkdir(exist_ok=True)
    path=folder/'state.json'
    prev=json.loads(path.read_text()) if path.exists() else {}
    supervisor=json.loads((HERE/'runtime/run_001.supervisor.json').read_text())
    process=supervisor.get('worker_pid')
    visible=bool(process and psutil.pid_exists(process))
    # Restricted callers cannot enumerate externally launched processes. The
    # supervisor heartbeat follows a successful worker.poll() liveness check.
    heartbeat=supervisor.get('last_check_unix',0)
    alive=visible or (supervisor['state']=='RUNNING' and time.time()-heartbeat<20)
    status=json.loads((OUT/'status.json').read_text())
    log=HERE/'runtime/run_001.worker.log'
    stat=log.stat();offset=prev.get('offset',max(0,stat.st_size-65536))
    if offset>stat.st_size or prev.get('log_created',stat.st_ctime)!=stat.st_ctime:offset=0
    errors=[]
    with log.open('rb') as stream:
        stream.seek(offset)
        for line in stream:
            text=line.decode('utf-8',errors='replace').strip()
            if re.search(r'Traceback|CUDA out of memory|AssertionError|RuntimeError|FloatingPointError',text):errors.append(text[:300])
        offset=stream.tell()
    progress=status.get('step',status.get('attempt',status.get('completed','-')))
    updated=status.get('updated_unix',0)
    if status['state']=='EVALUATING':
        file=OUT/'evaluation'/status['model']/'progress.json'
        if file.exists():
            ev=json.loads(file.read_text());progress=f"{status['model']}:{ev['completed']}/{ev['planned']}";updated=ev['updated_unix']
    level='OK'
    if status['state']=='ERROR' or supervisor['state']=='ERROR' or (not alive and status['state']!='COMPLETED') or errors:level='ERROR'
    elif alive and time.time()-updated>600:level='WARNING'
    data=dict(last_successful_check_unix=time.time() if level=='OK' else prev.get('last_successful_check_unix'),
        offset=offset,log_created=stat.st_ctime,progress=progress,loss=status.get('loss'),
        process_alive=alive,process_observation='direct' if visible else 'fresh_supervisor_poll',
        worker_pid=process,state=status['state'],new_errors=errors,
        handled_problems=prev.get('handled_problems',[]))
    tmp=path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2));tmp.replace(path)
    print(f"{level} | {status['state']} | Fortschritt: {progress} | Loss: {status.get('loss','-')} | Neue Fehler: {len(errors)} | Aktion: keine")
    if level=='ERROR':print(json.dumps(dict(supervisor=supervisor,status=status,new_errors=errors)))


if __name__=='__main__':main()
