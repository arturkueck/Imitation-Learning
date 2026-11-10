"""ONE training followed by its necessary offline/rollout evaluation, then exit."""
import os,sys,json,time,traceback,subprocess,hashlib,ctypes,statistics
from pathlib import Path
OUT=Path(__file__).resolve().parents[1];ROOT=Path(__file__).resolve().parents[4]
smoke='--logging-self-test' in sys.argv
log=(OUT/('logging_smoke.log' if smoke else 'run.log')).open('a',encoding='utf-8',buffering=1)
sys.stdout=log;sys.stderr=log
if smoke:
    print('PARENT_STDOUT_OK',flush=True)
    subprocess.run([sys.executable,'-u','-c',"import sys; print('CHILD_STDOUT_OK'); print('CHILD_STDERR_OK',file=sys.stderr)"],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    log.flush()
    (OUT/'logging_smoke_complete.json').write_text(json.dumps({'passed':True,'no_training':True,'pid':os.getpid()}),encoding='utf-8')
    sys.exit(0)
from common import read,write,digest,folder,checkpoint
def main():
    assert read(OUT/'preflight.json')['passed']
    assert not (OUT/'worker_started.json').exists(),'Refusing duplicate run'
    for name,record in read(OUT/'prepared_hashes.json')['files'].items():
        assert digest(OUT/name)==record['sha256'],f'Prepared artifact changed: {name}'
    write(OUT/'worker_started.json',dict(pid=os.getpid(),seed=1,started_unix=time.time()))
    for stage in ('train','offline','evaluate'):
        write(OUT/'worker_status.json',dict(state='RUNNING',stage=stage,pid=os.getpid()))
        print('STAGE',stage,flush=True)
        subprocess.run([sys.executable,'-u',str(OUT/'scripts'/f'{stage}.py'),'C','diffusion','1'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    from analyze import offline,csvwrite
    dest=folder('C','diffusion',1);rows=read(dest/'rollouts/results.json');assert len(rows)==40
    o,frames,pairs,onsets=offline('C','diffusion',1,dest)
    summary=dict(n=40,seed=1,simplified_successes=sum(r['simplified_success'] for r in rows),grasp_successes=sum(r['grasp_success'] for r in rows),lift_successes=sum(r['lift_success'] for r in rows),transport_started=sum(r['transport_started_sanity'] for r in rows),xy_over_expert_median=o['xy_over_expert']['q'][2],target_cosine_mean=o['goal_cosine']['mean'],training=read(dest/'training_complete.json'),offline=o)
    summary['simplified_success_fraction']=summary['simplified_successes']/40
    summary['max_object_height_m_median']=statistics.median(r['max_object_height_m'] for r in rows)
    summary['max_object_height_m_max']=max(r['max_object_height_m'] for r in rows)
    for key in ('motion_goal_cosine_mean','correct_motion_fraction','xy_action_goal_cosine_mean'):
        values=[r[key] for r in rows if r[key] is not None]
        summary[key]=statistics.mean(values) if values else None
    write(OUT/'results.json',dict(summary=summary,rollouts=rows,offline_frames=frames,protocol=read(OUT/'protocol.json')))
    csvwrite(OUT/'rollout_metrics.csv',rows);csvwrite(OUT/'offline_metrics.csv',frames)
    # Audit saved optimizer state as well as the trainer's counters.
    import torch,numpy as np
    ck=torch.load(checkpoint('C','diffusion',1),map_location='cpu',weights_only=False)
    assert {int(s['step']) for s in ck['model']['optimizers']['policy']['state'].values()}=={30000}
    assert ck['model']['lr_schedulers']['policy']['last_epoch']==30000
    assert read(dest/'initialization.json')['initial_weights_sha256']==read(ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/C/diffusion/seed_1/initialization.json')['initial_weights_sha256']
    audit=np.load(dest/'training_audit.npz');assert len(audit['loss'])==30000 and np.isfinite(audit['loss']).all()
    csvwrite(OUT/'training_losses.csv',[dict(update=i+1,loss=float(x),lr=float(audit['lr'][i])) for i,x in enumerate(audit['loss'])])
    write(OUT/'verification.json',dict(passed=True,optimizer_updates=30000,scheduler_updates=30000,ema_updates=summary['training']['ema_updates'],fresh_seed1_initialization_matches_C=True,rollouts=read(dest/'rollout_verification.json'),offline=read(dest/'offline_verification.json')))
    records={str(p.relative_to(OUT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in OUT.rglob('*') if p.is_file() and p.name not in ('hashes.json','run.log','worker_status.json') and p.suffix not in ('.pyc','.tmp')}
    write(OUT/'hashes.json',dict(algorithm='SHA-256',files=records))
    write(OUT/'worker_status.json',dict(state='COMPLETED',pid=os.getpid()))
    write(OUT/'complete.json',dict(state='COMPLETED',verified=True,seed=1,summary=summary,finished_unix=time.time()))
    print('COMPLETED',json.dumps(summary),flush=True)
if __name__=='__main__':
    ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
    try:main()
    except Exception:
        write(OUT/'failed.json',dict(state='FAILED',cause=traceback.format_exc(),finished_unix=time.time()));write(OUT/'worker_status.json',dict(state='FAILED',pid=os.getpid()));traceback.print_exc();sys.exit(1)
    finally:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
