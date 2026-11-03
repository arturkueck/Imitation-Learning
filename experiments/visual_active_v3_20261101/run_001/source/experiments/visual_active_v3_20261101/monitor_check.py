"""Incremental two-hour agent check. No model weights and no training actions."""
from pathlib import Path
import json,time,re
from completion_gate import check,HERE,contained,save


def main():
    result=check();state=json.loads((HERE/'monitor_state.json').read_text());relative=state.get('run_directory')
    if not relative:print(json.dumps(result));return
    run=contained(HERE,relative);folder=run/'monitor';folder.mkdir(exist_ok=True)
    path=folder/'state.json';old=json.loads(path.read_text()) if path.exists() else {}
    raw=json.loads((run/'status.json').read_text()) if (run/'status.json').exists() else {}
    log=run/'worker.log';offset=old.get('log_offset',0);identity=None;messages=[];tail=old.get('partial_line','')
    if log.exists():
        stat=log.stat();identity=[stat.st_dev,stat.st_ino]
        if identity!=old.get('log_identity') or stat.st_size<offset:
            offset=max(0,stat.st_size-65536);tail=''
        with log.open('rb') as stream:
            stream.seek(offset);new=stream.read(65536);offset=stream.tell()
        text=tail+new.decode('utf-8',errors='replace');lines=text.split('\n');tail=lines.pop()
        messages=[line[-1000:] for line in lines if re.search(r'Traceback|CUDA.*out of memory|RuntimeError|nonfinite|NaN|\bInf\b|Error:',line,re.I)]
    progress={k:raw.get(k) for k in ['stage','epoch','step','rendered','render_total','split','loss','heartbeat_unix']}
    advanced=progress!=old.get('progress')
    value=dict(checked_unix=time.time(),log_offset=offset,log_identity=identity,partial_line=tail,
               progress=progress,process_status=result.get('status'),last_errors=messages)
    save(path,value)
    print(json.dumps(dict(**result,progress=progress,changed=advanced,new_errors=messages,
        stale_30_minutes=bool(raw.get('heartbeat_unix') and time.time()-raw['heartbeat_unix']>1800))))


if __name__=='__main__':main()
