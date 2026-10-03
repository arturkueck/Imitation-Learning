"""Sequential GPU jobs; conditional replication fixed before seeing results."""
import subprocess,sys,os,time,traceback,shutil,ctypes
from datetime import datetime,timezone
from common import *
status=dict(state='RUNNING',pid=os.getpid(),completed=[],failures=[])
def save():
    status['updated_at']=datetime.now(timezone.utc).isoformat();write(OUT/'status.json',status)
def command(script,v,kind,seed):
    dest=folder(v,kind,seed);label=f'{v}/{kind}/seed_{seed}/{script}'
    status['current']=label;save()
    with (dest/(script+'.log')).open('w',encoding='utf-8') as log:
        child=subprocess.Popen([sys.executable,'-u',str(OUT/'scripts'/f'{script}.py'),v,kind,str(seed)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        status['child_pid']=child.pid;save();code=child.wait()
    status.pop('child_pid',None)
    if code:
        status['failures'].append(dict(job=label,returncode=code,aborted=read(dest/'aborted.json') if (dest/'aborted.json').exists() else None));save();return False
    status['completed'].append(label);save();return True
def retain_final(v,seed):
    dest=folder(v,'diffusion',seed);final=checkpoint(v,'diffusion',seed).resolve();records=[]
    for path in (dest/'runs').rglob('*.pth'):
        resolved=path.resolve();assert resolved.is_relative_to(OUT.resolve())
        keep=resolved==final;records.append(dict(path=str(path.relative_to(OUT)),sha256=digest(path),bytes=path.stat().st_size,retained=keep))
        if not keep:path.unlink()
    write(dest/'checkpoint_retention.json',dict(policy='retain final update 30000; hashes of intermediate and duplicate checkpoints preserved',records=records))
def job(v,kind,seed):
    dest=folder(v,kind,seed)
    if not (dest/'training_complete.json').exists():
        if not command('train',v,kind,seed):return
    if kind=='diffusion' and not (dest/'checkpoint_retention.json').exists():retain_final(v,seed)
    if not (dest/'offline_verification.json').exists():
        if not command('offline',v,kind,seed):return
    if not (dest/'rollout_verification.json').exists():
        if not command('evaluate',v,kind,seed):return
    write(dest/'evaluation_complete.json',dict(complete=True,stacks=sum(x['sustained_success'] for x in read(dest/'rollouts/results.json'))))
def report():
    with (OUT/'analysis.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u',str(OUT/'scripts/analyze.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Analysis failed; see analysis.log'
def main():
    assert read(OUT/'preflight.json')['passed'];save()
    first=folder('B','direct',1)
    while not (first/'training_complete.json').exists():
        assert not (first/'aborted.json').exists(), 'Initial direct training aborted'
        status['current']='B/direct/seed_1/train (existing foreground process)';save();time.sleep(10)
    for v in VARIANTS:
        for kind in ('direct','diffusion'):job(v,kind,1)
        report()
    qualified=[];threshold=read(OUT/'protocol.json')['extension_threshold_stacks']
    for v in VARIANTS:
        path=folder(v,'diffusion',1)/'evaluation_complete.json'
        if path.exists() and read(path)['stacks']>=threshold:qualified.append(v)
    write(OUT/'replication_decision.json',dict(threshold=threshold,qualified_variants=qualified,rule=read(OUT/'protocol.json')['extension_rule']))
    for v in qualified:
        for seed in (2,3):
            for kind in ('direct','diffusion'):job(v,kind,seed)
            report()
    status['state']='COMPLETED' if not status['failures'] else 'COMPLETED_WITH_ABORTS';save();report()
    with (OUT/'verify.log').open('w',encoding='utf-8') as log:
        result=subprocess.run([sys.executable,'-u',str(OUT/'scripts/verify.py')],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    assert result.returncode==0,'Verification failed; see verify.log'
    write(OUT/'complete.json',dict(state=status['state'],verified=True,qualified_variants=qualified))
if __name__=='__main__':
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:main()
    except Exception:
        status['state']='FAILED';status['fatal_error']=traceback.format_exc();save();raise
    finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
