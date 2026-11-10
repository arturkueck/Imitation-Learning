"""Wait for the active experiment, then run a controlled scheduler/horizon test."""
import ctypes
from ctypes import wintypes
from datetime import datetime,timezone
import json, os, subprocess, sys, time, traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
SHARED=ROOT/'experiments/square/scripts'; sys.path.insert(0,str(SHARED))
from atomic_json import write_json
EXP=ROOT/'experiments/stack_followup_20261001'
LOGS=EXP/'logs'; LOGS.mkdir(exist_ok=True)
manifest=json.loads((EXP/'manifest.json').read_text())
status=dict(state='WAITING_FOR_ACTIVE_RUN',pid=os.getpid(),results=[],errors=[],
    wait_for=manifest['wait_for_status'],change=manifest['change'])
deadline=None
kernel=ctypes.windll.kernel32
kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
kernel.OpenProcess.restype=wintypes.HANDLE
kernel.WaitForSingleObject.argtypes=[wintypes.HANDLE,wintypes.DWORD]
kernel.CloseHandle.argtypes=[wintypes.HANDLE]

def alive(pid):
    handle=kernel.OpenProcess(0x00100000,False,int(pid))
    if not handle: return False
    try: return kernel.WaitForSingleObject(handle,0)==258
    finally: kernel.CloseHandle(handle)

def save():
    status['updated_at']=datetime.now(timezone.utc).isoformat()
    write_json(EXP/'status.json',status)
    rows=['# Gezielter Stapel-Vergleich','',f"Status: {status['state']}",'',
        'Dieser Lauf wartet auf das Ende des bestehenden Diffusion-Prozesses. Er unterbricht ihn nicht.',
        'Vergleich: bisheriger State-Diffusion-Checkpoint vs. neu trainiertes State-Modell mit korrigiertem Scheduler; jeweils 8 oder 2 ausgeführte Aktionen pro Neuplanung.',
        'Training unverändert 300 Epochen / 100 Batches / Batchgröße 8 / Seed 1; identische Daten und Architektur. Die Trainingsänderung betrifft ausschließlich die Scheduler-Schritte. Inferenzhorizonte werden auf denselben Gewichten verglichen.',
        'Je Variante 20 Tests ab Seed 46000. Eine Trainingsinitialisierung; kleine Unterschiede sind noch kein belastbarer Nachweis.','',
        '| Modell | Ausführungsblock | Erfolg | Nachlauf stabil | B gegriffen | B angehoben | Paar abgelegt |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in status['results']:
        rows.append(f"| {r['model']} | {r['action_horizon']} | {r['success_rate']:.0%} | {r['sustained_success_rate']:.0%} | {r['grasp_B']:.0%} | {r['lift_B']:.0%} | {r['placed_pair']:.0%} |")
    rows+=['','Fehler:']
    rows += [f'- {e}' for e in status['errors']] or ['Keine bisher.']
    (EXP/'RESULTS.md').write_text('\n'.join(rows),encoding='utf-8')

def run(script,args,label,minutes):
    status['current_step']=label; save()
    with (LOGS/(label+'.log')).open('w') as log:
        child=subprocess.Popen([sys.executable,'-u',str(SHARED/script),*map(str,args)],
            cwd=str(ROOT),stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT)
        status['child_pid']=child.pid; save()
        try: code=child.wait(timeout=max(1,min(minutes*60,deadline-time.monotonic()-30)))
        except subprocess.TimeoutExpired:
            subprocess.run(['taskkill','/PID',str(child.pid),'/T','/F'],capture_output=True)
            child.wait(timeout=30); raise TimeoutError(label+' exceeded budget')
        finally: status.pop('child_pid',None)
    if code: raise RuntimeError(label+': exit '+str(code))

def main():
    global deadline
    assert json.loads((EXP/'preflight.json').read_text())['validated']
    # Wait for both terminal status AND process exit; do not compete for GPU.
    wait_started=time.monotonic()
    while True:
        previous=json.loads(Path(manifest['wait_for_status']).read_text())
        finished=previous['state'] in ('COMPLETED','COMPLETED_WITH_ERRORS','FAILED')
        if finished and not alive(previous['pid']): break
        status['active_run_state']=previous['state']; save()
        if time.monotonic()-wait_started>8*3600: raise TimeoutError('Active experiment did not finish within eight hours')
        time.sleep(10)
    deadline=time.monotonic()+manifest['deadline_hours']*3600
    status['state']='TRAINING'; status['started_at']=datetime.now(timezone.utc).isoformat(); save()
    if list((EXP/'state_scheduler_fixed/runs').glob('**/*.pth')): raise RuntimeError('Existing follow-up run; refusing overwrite')
    run('train_model_corrected.py',[manifest['config']],'train_fixed_scheduler',75)
    fixed=next((EXP/'state_scheduler_fixed/runs').glob('**/models/model_epoch_300.pth'))
    hashes=[]
    for model,path in [('baseline',manifest['baseline_checkpoint']),('fixed_scheduler',str(fixed))]:
        for horizon in manifest['action_horizons']:
            label=model+'_h'+str(horizon); status['state']='EVALUATING'; save()
            run('evaluate_horizon.py',[path,label,'--action-horizon',horizon,'--output-root',EXP,
                '--episodes',manifest['test_episodes'],'--seed',manifest['test_seed'],
                '--horizon','500','--video-episodes','3'],'evaluate_'+label,35)
            data=json.loads((EXP/'evaluation'/label/'evaluation_results.json').read_text())
            stages=[r['stack_progress'] for r in data['rollouts']]
            row=dict(model=model,action_horizon=horizon,success_rate=data['success_rate'],
                sustained_success_rate=data['sustained_success_rate'],
                grasp_B=sum(1 in r['grasped_cube_indices'] for r in stages)/len(stages),
                lift_B=sum(1 in r['lifted_cube_indices'] for r in stages)/len(stages),
                placed_pair=sum(r['released_correct_pair_steps'][0]>0 for r in stages)/len(stages))
            status['results'].append(row)
            hashes.append([(r['seed'],r['intervention']['initial_state_sha256']) for r in data['rollouts']]); save()
    status['paired_starts_verified']=all(h==hashes[0] for h in hashes)
    assert status['paired_starts_verified']
    status['state']='COMPLETED'; save()

if __name__=='__main__':
    kernel.SetThreadExecutionState(0x80000001); save()
    try: main()
    except Exception:
        status['state']='FAILED'; status['errors'].append(traceback.format_exc()); save(); raise
    finally: kernel.SetThreadExecutionState(0x80000000)
