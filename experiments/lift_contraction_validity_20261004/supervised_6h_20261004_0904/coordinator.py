"""Bounded six-hour research supervision with authorized, documented technical repair."""
import argparse
import csv
import ctypes
from datetime import datetime, timezone, timedelta
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import traceback

SESSION=Path(__file__).resolve().parent
ROOT=SESSION.parents[2]
PYTHON=ROOT/'praxis/.venv/Scripts/python.exe'
BERLIN=timezone(timedelta(hours=2))  # This session is on 04 Oct 2026, before DST ends.


def read(p):return json.loads(Path(p).read_text(encoding='utf-8'))


def write(p,value):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp')
    tmp.write_text(json.dumps(value,indent=2,allow_nan=False)+'\n',encoding='utf-8');tmp.replace(p)


def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()


def append(p,value):
    now=time.time();value={'unix':now,'utc':datetime.fromtimestamp(now,timezone.utc).isoformat(),
                          'berlin':datetime.fromtimestamp(now,BERLIN).isoformat(),**value}
    with Path(p).open('a',encoding='utf-8') as f:f.write(json.dumps(value,allow_nan=False)+'\n')


def alive(record):
    import psutil
    try:
        p=psutil.Process(record['pid'])
        return abs(p.create_time()-record['create_time'])<.1 and p.is_running()
    except (psutil.NoSuchProcess,psutil.AccessDenied,KeyError):return False


def job():
    spec=importlib.util.spec_from_file_location('session_job',SESSION/'job.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module.Job()


def attempt_status(attempt):
    detail={}
    if attempt is None:return detail
    for arm in ['B0','B1']:
        p=attempt/arm/'training_result.json'
        if not p.exists():p=attempt/arm/'progress.json'
        if p.exists():
            r=read(p);detail[arm]={k:r.get(k) for k in ['state','optimizer_updates','loss','loss_last','elapsed_seconds']}
    p=attempt/'worker_status.json'
    if p.exists():detail['evaluation']=read(p)
    return detail


def record(state,attempt=None,**extra):
    cfg=read(SESSION/'session.json')
    value={'state':state,'coordinator_pid':os.getpid(),'deadline_unix':cfg['deadline_unix'],
           'deadline_berlin':cfg['deadline_berlin'],'attempt':str(attempt) if attempt else None,
           'progress':attempt_status(attempt),'updated_unix':time.time(),**extra}
    write(SESSION/'status.json',value);return value


def local_check(value,event):
    append(SESSION/'monitor_checks.jsonl',{'actor':'local_supervisor','event':event,'status':value})


def run_process(args,deadline,attempt,stage):
    import psutil
    owned=job();p=None;started=time.time();timed_out=False;stalled=False
    last_activity=started;last_signature=None;last_local=0
    try:
        with (attempt/f'{stage}.log').open('ab',buffering=0) as log:
            p=subprocess.Popen(args,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                               creationflags=subprocess.CREATE_NO_WINDOW|subprocess.CREATE_NEW_PROCESS_GROUP)
            owned.assign(p)
            identity={'pid':p.pid,'create_time':psutil.Process(p.pid).create_time()}
            write(attempt/f'{stage}_process.json',identity)
            previous=None
            while p.poll() is None:
                now=time.time()
                if now>=deadline:
                    timed_out=True;owned.terminate();p.wait(timeout=5);break
                if stage=='worker' and now>=deadline-90 and not (attempt/'STOP_REQUESTED').exists():
                    (attempt/'STOP_REQUESTED').write_text('Session or attempt deadline: safe checkpoint and stop',encoding='utf-8')
                value=record(stage.upper(),attempt,worker=identity,attempt_deadline_unix=deadline)
                files=[attempt/f'{stage}.log']+list(attempt.glob('B?/progress.json'))+list(attempt.glob('B?/evaluation/*.json'))
                signature=tuple((str(q),q.stat().st_mtime_ns,q.stat().st_size) for q in files if q.exists())
                if signature!=last_signature:last_activity=now;last_signature=signature
                if now-last_activity>600:
                    stalled=True;owned.terminate();p.wait(timeout=5);break
                compact=json.dumps(value['progress'],sort_keys=True)
                if previous is None or compact!=previous or now-last_local>=1800:
                    local_check(value,'worker_check');previous=compact;last_local=now
                time.sleep(min(5,max(.1,deadline-now)))
            result={'returncode':p.returncode,'timed_out':timed_out,'stalled':stalled,
                    'elapsed_seconds':time.time()-started,'worker':identity}
            write(attempt/f'{stage}_process_result.json',result);return result
    finally:
        if p is not None and p.poll() is None:owned.terminate();p.wait(timeout=5)
        owned.close()


def prepare_attempt(reason):
    attempts=SESSION/'attempts';attempts.mkdir(exist_ok=True)
    existing=sorted(attempts.glob('attempt_*'))
    index=max([int(p.name.split('_')[-1]) for p in existing]+[0])+1
    attempt=attempts/f'attempt_{index:03d}';attempt.mkdir()
    shutil.copy2(SESSION/'runner_template.py',attempt/'run.py')
    shutil.copy2(SESSION/'PILOT_PROTOCOL.md',attempt/'PILOT_PROTOCOL.md')
    shutil.copy2(SESSION/'SESSION_PROTOCOL.md',attempt/'SESSION_PROTOCOL.md')
    write(attempt/'attempt.json',{'index':index,'reason':reason,'created_unix':time.time(),
                                'template_sha256':sha(SESSION/'runner_template.py'),
                                'preflight_script_sha256':sha(SESSION/'gpu_preflight.py')})
    append(SESSION/'repairs.jsonl',{'event':'new_attempt','attempt':str(attempt),'reason':reason})
    return attempt


def summarize(attempt):
    worker=read(attempt/'worker_result.json');assert worker['state']=='COMPLETED'
    assert read(attempt/'pairing_audit.json')['passed'] and worker['paired_initial_states']
    rows=[]
    for update,condition,n in [(500,'nominal',6),(1000,'nominal',6),(2000,'nominal',10),
                              (2000,'sensor_y_plus5mm',10),(2000,'sensor_y_minus5mm',10),(2000,'action_impulse_x_plus0.5',10)]:
        pair={arm:read(attempt/arm/'evaluation'/f'{update}_{condition}.json') for arm in ['B0','B1']}
        for arm,r in pair.items():
            assert r['state']=='COMPLETED' and r['episodes_completed']==n
            assert r['successes']==sum(x['success'] for x in r['rollouts'])
            assert sha(r['checkpoint'])==r['checkpoint_sha256']
        for a,b in zip(pair['B0']['rollouts'],pair['B1']['rollouts']):
            assert a['seed']==b['seed'] and a['initial_cube_qpos']==b['initial_cube_qpos'] and a['initial_eef_pos']==b['initial_eef_pos']
        rows.append({'updates':update,'condition':condition,'episodes':n,
                     'B0_successes':pair['B0']['successes'],'B1_successes':pair['B1']['successes'],
                     'B0_impulses_applied':sum(x['impulse_applied'] for x in pair['B0']['rollouts']),
                     'B1_impulses_applied':sum(x['impulse_applied'] for x in pair['B1']['rollouts'])})
    sensors={arm:sum(r[f'{arm}_successes'] for r in rows if r['condition'].startswith('sensor_')) for arm in ['B0','B1']}
    nominal=next(r for r in rows if r['updates']==2000 and r['condition']=='nominal')
    times={}
    for arm in ['B0','B1']:
        csv_rows=list(csv.DictReader((attempt/arm/'losses.csv').open(encoding='utf-8')))
        training=[r for r in csv_rows if r['split']=='train'];assert len(training)==2000
        assert [int(r['optimizer_update']) for r in training]==list(range(1,2001))
        r=read(attempt/arm/'training_result.json');assert r['optimizer_updates']==2000 and r['state']=='COMPLETED'
        assert sha(attempt/arm/'model_final.pth')==r['final_checkpoint_sha256']
        curve=[]
        for update in [500,1000,2000]:
            ev=read(attempt/arm/'evaluation'/f'{update}_nominal.json')
            curve.append({'updates':update,'successes_first6':sum(e['success'] for e in ev['rollouts'][:6]),
                          'training_elapsed_seconds':float(training[update-1]['elapsed_seconds'])})
        reached=next((curve[i] for i in range(1,len(curve)) if curve[i-1]['successes_first6']>=4 and curve[i]['successes_first6']>=4),None)
        times[arm]={'curve':curve,'sustained_threshold_4of6_confirmed_at':reached,'censored':reached is None,
                    'total_training_seconds':r['elapsed_seconds'],'loss_last':r['loss_last'],'loss_last100':r['loss_last100']}
    summary={'state':'COMPLETED','attempt':str(attempt),'seed':41004,'training_updates_per_arm':2000,'rows':rows,
             'sensor_successes_out_of_20':sensors,'nominal_successes_out_of_10':{a:nominal[f'{a}_successes'] for a in ['B0','B1']},
             'pilot_rule_passed':sensors['B1']-sensors['B0']>=2 and nominal['B1_successes']-nominal['B0_successes']>=-1,
             'learning_and_costs':times,'evaluation_seconds':worker['evaluation_elapsed_seconds'],
             'preflight_seconds':read(attempt/'preflight_result.json')['elapsed_seconds'],
             'paired_initial_parameters_batches_starts_verified':True,'robust_algorithmic_improvement_established':False}
    write(SESSION/'pilot_summary.json',summary)
    lines=['# Beaufsichtigter BC-Methodenpilot','',f"Status: COMPLETED. Versuch: `{attempt.name}`. Seed 41004, je 2.000 Updates.",'',
           '| Updates | Bedingung | BC | Sensor-Augmentation | Episoden pro Arm |','|---:|---|---:|---:|---:|']
    for r in rows:lines.append(f"| {r['updates']} | {r['condition']} | {r['B0_successes']} | {r['B1_successes']} | {r['episodes']} |")
    lines+=['',f"Sensorbedingungen zusammen: BC {sensors['B0']}/20, Augmentation {sensors['B1']}/20. Pilotregel bestanden: {summary['pilot_rule_passed']}.",
            '',f"Trainingszeit BC: {times['B0']['total_training_seconds']:.1f} s; Augmentation: {times['B1']['total_training_seconds']:.1f} s. Evaluation: {summary['evaluation_seconds']:.1f} s.",
            '', 'Lift-Nativerfolg; Sensorbias und echter Aktionsimpuls getrennt. Keine Auswahl eines Zwischencheckpoints. Hashes sowie Anfangsgewichts-, Batch- und Start-Paarung überprüft.',
            '', 'Ein Entwicklungsseed: kein Nachweis robuster Trainingsverbesserung, physischer Stabilität oder allgemeiner schnellerer Konvergenz. Kein weiterer Lauf nur wegen schwacher Resultate.',
            '', 'Rohdaten/Hashes im angegebenen Versuch; vollständige Lernkurve und Kosten in pilot_summary.json. Technische Versuche und Reparaturen bleiben in attempts und repairs.jsonl erhalten.',
            '', 'Die sechs Stunden lange Forschungsaufsicht bleibt bis zur fixierten Deadline aktiv. Der Agent-Heartbeat soll jetzt Auswertung und nächste fachlich begründete Diagnose bearbeiten.']
    (SESSION/'RESULT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def coordinator():
    import psutil
    cfg=read(SESSION/'session.json');assert time.time()<cfg['deadline_unix']
    identity={'pid':os.getpid(),'create_time':psutil.Process().create_time()};write(SESSION/'coordinator_pid.json',identity)
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.SetThreadExecutionState.argtypes=[ctypes.c_uint32];kernel.SetThreadExecutionState.restype=ctypes.c_uint32
    assert kernel.SetThreadExecutionState(0x80000001),'Failed to request awake state'
    attempt=None;end_state='WINDOW_FINISHED';last_local=0;last_state=None
    try:
        while time.time()<cfg['deadline_unix']:
            attempts=sorted((SESSION/'attempts').glob('attempt_*')) if (SESSION/'attempts').exists() else []
            signal=SESSION/'repair_signal.json'
            if not attempts or signal.exists():
                reason='Initial corrected launch, explicitly requested by user'
                if signal.exists():
                    request=read(signal);reason=request['reason']
                    signature=sha(SESSION/'runner_template.py')+sha(SESSION/'gpu_preflight.py')
                    if attempts and read(attempts[-1]/'attempt.json').get('repair_signature')==signature:
                        append(SESSION/'repairs.jsonl',{'event':'request_rejected','reason':'No new concrete repair since last attempted repair','request':request})
                        signal.rename(SESSION/f'rejected_repair_{int(time.time())}.json');continue
                    signal.rename(SESSION/f'accepted_repair_{int(time.time())}.json')
                attempt=prepare_attempt(reason)
                info=read(attempt/'attempt.json');info['repair_signature']=sha(SESSION/'runner_template.py')+sha(SESSION/'gpu_preflight.py');write(attempt/'attempt.json',info)
                deadline=min(cfg['deadline_unix'],time.time()+7200)
                phases=[('prepare',[str(PYTHON),'-u',str(attempt/'run.py'),'prepare'],120),
                        ('preflight',[str(PYTHON),'-u',str(SESSION/'gpu_preflight.py'),str(attempt)],300),
                        ('worker',[str(PYTHON),'-u',str(attempt/'run.py'),'worker'],7200)]
                passed=True;details={}
                for stage,args,stage_seconds in phases:
                    p=run_process(args,min(deadline,time.time()+stage_seconds),attempt,stage);details[stage]=p
                    if p['returncode']!=0 or p['timed_out'] or p['stalled']:
                        passed=False;break
                result={'state':'COMPLETED' if passed else 'TIMED_OUT' if time.time()>=deadline else 'FAILED',
                        'processes':details,'finished_unix':time.time(),'attempt_deadline_unix':deadline,
                        'fresh_attempt':True,'automatic_repair_authorized':True,'worker_job_closed':True}
                write(attempt/'run_result.json',result)
                if passed:
                    try:summarize(attempt)
                    except BaseException:
                        result.update(state='FAILED_SUMMARY',error=traceback.format_exc());write(attempt/'run_result.json',result)
                value=record('PILOT_COMPLETE_RESEARCH_ACTIVE' if result['state']=='COMPLETED' else 'WAITING_AGENT_REPAIR',attempt,last_attempt_result=result)
                local_check(value,'attempt_finished');last_local=time.time();last_state=value['state']
            else:
                attempt=attempts[-1]
                completed=(SESSION/'pilot_summary.json').exists()
                state='PILOT_COMPLETE_RESEARCH_ACTIVE' if completed else 'WAITING_AGENT_REPAIR'
                value=record(state,attempt,heartbeat_must_remain_active=True)
                if time.time()-last_local>=1800 or state!=last_state:
                    local_check(value,'periodic_session_check');last_local=time.time();last_state=state
                time.sleep(min(5,max(.1,cfg['deadline_unix']-time.time())))
    except BaseException:
        end_state='COORDINATOR_FAILED';write(SESSION/'coordinator_error.json',{'error':traceback.format_exc(),'unix':time.time()});traceback.print_exc()
    finally:
        kernel.SetThreadExecutionState(0x80000000)
        result=record(end_state,attempt,awake_request_released=True,coordinator_exiting=True)
        write(SESSION/'session_result.json',result);local_check(result,'session_finished')


def start():
    cfg=read(SESSION/'session.json');assert time.time()<cfg['deadline_unix'],'Fixed six-hour window expired'
    p=SESSION/'coordinator_pid.json'
    if p.exists() and alive(read(p)):
        print(json.dumps({'state':'ALREADY_ACTIVE','identity':read(p)}));return
    # Recover only after the old coordinator and its Job-owned workers have ended.
    import psutil
    for info in psutil.process_iter(['pid','cmdline']):
        try:
            if any(str(SESSION/'attempts').lower() in str(a).lower() and str(a).endswith('run.py') for a in (info.info['cmdline'] or [])):
                raise RuntimeError(f'Existing attempt worker {info.pid}; inspect before restarting coordinator')
        except psutil.AccessDenied:continue
    with (SESSION/'coordinator.log').open('ab',buffering=0) as log:
        proc=subprocess.Popen([str(PYTHON),'-u',str(SESSION/'coordinator.py'),'run'],cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log,stderr=log,
                              creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_NO_WINDOW,close_fds=True)
    write(SESSION/'launcher_pid.json',{'pid':proc.pid,'create_time':psutil.Process(proc.pid).create_time()})
    print(json.dumps({'coordinator_launcher_pid':proc.pid,'deadline_berlin':cfg['deadline_berlin']},indent=2))


def repair(reason):
    assert time.time()<read(SESSION/'session.json')['deadline_unix'],'Window expired'
    if (SESSION/'pilot_summary.json').exists():raise RuntimeError('Completed pilot is not a technical failure; do not repeat it')
    state=read(SESSION/'status.json') if (SESSION/'status.json').exists() else {}
    assert state.get('state') not in ['PREPARE','PREFLIGHT','WORKER'],'A worker is still active'
    assert not (SESSION/'repair_signal.json').exists(),'A repair is already pending'
    write(SESSION/'repair_signal.json',{'reason':reason,'requested_unix':time.time(),'template_sha256':sha(SESSION/'runner_template.py')})
    append(SESSION/'repairs.jsonl',{'event':'repair_requested','reason':reason})
    print('Repair queued without extending the fixed deadline')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['start','run','status','repair']);p.add_argument('--reason');a=p.parse_args()
    if a.mode=='start':start()
    elif a.mode=='run':coordinator()
    elif a.mode=='repair':assert a.reason;repair(a.reason)
    else:print(json.dumps(read(SESSION/'status.json') if (SESSION/'status.json').exists() else read(SESSION/'session.json'),indent=2))
