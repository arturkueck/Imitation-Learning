"""Actual agent invocation only. Never schedules itself or extends deadline."""
import argparse,csv,hashlib,json,time,tomllib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;ROOT=S.parents[2];P=S/'attempts/attempt_002'
parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['snapshot','final'],required=True);parser.add_argument('--trigger');args=parser.parse_args()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
hashcache={}
def sha(p):
    p=p.resolve()
    if p not in hashcache:
        h=hashlib.sha256()
        with p.open('rb') as f:
            for block in iter(lambda:f.read(1048576),b''):h.update(block)
        hashcache[p]=h.hexdigest()
    return hashcache[p]
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json');status=read(S/'status.json');identity=read(S/'coordinator_pid.json');now=time.time()
assert session['deadline_unix']==status['deadline_unix']==1791119479.6970713
automation=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())
assert automation['status']=='ACTIVE'
if args.phase=='snapshot':assert now<session['deadline_unix'] and alive(identity) and now-status['updated_unix']<30
else:
    assert now>=session['deadline_unix'] and not alive(identity)
    ended=read(S/'session_result.json')
    assert ended['state']=='WINDOW_FINISHED' and ended['awake_request_released'] and ended['coordinator_exiting']
jobs=[]
for p in S.rglob('supervisor_result.json'):
    ended=read(p);launch=read(p.parent/'launch.json');worker=ended['worker'];supervisor=dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])
    assert not alive(worker) and not alive(supervisor) and ended['worker_job_closed'],str(p)
    assert launch['deadline_unix']<=session['deadline_unix']
    jobs.append(dict(path=str(p.relative_to(S)),worker=worker,supervisor=supervisor,both_exited=True,job_closed=True,returncode=ended['returncode']))
assert read(P/'pairing_audit.json')['passed'] and read(P/'worker_result.json')['paired_initial_states']
dataset=read(P/'dataset_manifest.json');assert sha(Path(dataset['path']))==dataset['sha256']
sources=read(P/'source_hashes.json')
for name,digest in sources.items():assert sha(ROOT/name)==digest,name
assets=read(S.parent/'runtime_preflight/dependency_assets_hashes.json')
for name,digest in assets.items():assert sha(ROOT/name)==digest,name
diagnostic_sources=0;manifest_paths=[]
for p in S.rglob('source_hashes.json'):
    if 'attempts' in p.relative_to(S).parts:continue
    for name,digest in read(p).items():
        target=S/'build_domain_worker.py' if name=='worker_builder_sha256' else p.parent/name
        assert sha(target)==digest,str(target);diagnostic_sources+=1
    manifest_paths.append(str(p.relative_to(S)))
training={}
for arm in ['B0','B1']:
    r=read(P/arm/'training_result.json');assert r['state']=='COMPLETED' and r['optimizer_updates']==2000
    assert sha(P/arm/'model_final.pth')==r['final_checkpoint_sha256']
    with (P/arm/'losses.csv').open(encoding='utf-8') as f:updates=[int(x['optimizer_update']) for x in csv.DictReader(f) if x['split']=='train']
    assert updates==list(range(1,2001));training[arm]=r
assert training['B0']['initial_parameters_sha256']==training['B1']['initial_parameters_sha256'] and training['B0']['batch_sequence_sha256']==training['B1']['batch_sequence_sha256']
episodes=0;pairing=[]
for update,condition,n in [(500,'nominal',6),(1000,'nominal',6),(2000,'nominal',10),(2000,'sensor_y_plus5mm',10),(2000,'sensor_y_minus5mm',10),(2000,'action_impulse_x_plus0.5',10)]:
    ev=[read(P/arm/'evaluation'/f'{update}_{condition}.json') for arm in ['B0','B1']]
    for r in ev:
        assert r['state']=='COMPLETED' and r['episodes_completed']==n and sha(Path(r['checkpoint']))==r['checkpoint_sha256']
        assert sum(x['success'] for x in r['rollouts'])==r['successes'];episodes+=n
    for a,b in zip(ev[0]['rollouts'],ev[1]['rollouts']):assert a['seed']==b['seed'] and a['initial_cube_qpos']==b['initial_cube_qpos'] and a['initial_eef_pos']==b['initial_eef_pos']
    pairing.append(dict(update=update,condition=condition,episodes_per_arm=n,B0_successes=ev[0]['successes'],B1_successes=ev[1]['successes']))
assert episodes==104
launcher=read(S/'launcher_pid.json')
if args.phase=='final':assert not alive(launcher)
pilot_workers=[]
for p in psutil.process_iter(['pid','cmdline']):
    try:
        if any(str(P/'run.py').lower()==str(a).lower() for a in p.info['cmdline'] or []):pilot_workers.append(p.pid)
    except (psutil.NoSuchProcess,psutil.AccessDenied):pass
assert not pilot_workers
d=datetime.now(timezone.utc)
result=dict(state='FINAL_SESSION_PROVENANCE_AND_SHUTDOWN_VERIFIED' if args.phase=='final' else 'PREDEADLINE_PROVENANCE_VERIFIED',actor='agent',scheduled=bool(args.trigger),trigger_utc=args.trigger,
            phase=args.phase,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=time.time(),
            deadline_unix=session['deadline_unix'],coordinator_identity=identity,coordinator_alive=alive(identity),launcher_identity=launcher,launcher_alive=alive(launcher),
            heartbeat_status_before_pause=automation['status'],awake_release_verified=args.phase=='final',optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
            pilot_source_files_verified=len(sources),runtime_assets_verified=len(assets),diagnostic_source_entries_verified=diagnostic_sources,diagnostic_source_manifests=manifest_paths,
            diagnostic_jobs=jobs,all_diagnostic_workers_and_supervisors_exited=True,pilot_workers=pilot_workers,
            dataset_sha256=dataset['sha256'],final_checkpoint_sha256={arm:r['final_checkpoint_sha256'] for arm,r in training.items()},paired_outcomes=pairing,
            loss_reference_sha256=sha(S/'method_reference_001/loss_reference.py'),method_audit_sha256=sha(S/'method_reference_001/result.json'),
            report_sha256_before_operational_append=sha(S/'SESSION_RESEARCH_REPORT.md'),
            decision='After exact deadline and verified shutdown, pause existing heartbeat; no further run.' if args.phase=='final' else 'Keep monitoring ACTIVE until exact deadline; research synthesis complete and no more training.')
path=S/(('final_verification_' if args.phase=='final' else 'precloseout_verification_')+str(int(result['unix']))+'.json')
with path.open('x',encoding='utf-8') as out:json.dump(result,out,indent=2)
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(result)+'\n')
if args.phase=='final':
    with (S/'SESSION_RESEARCH_REPORT.md').open('a',encoding='utf-8') as out:
        out.write('\n\n## Tatsächlicher operativer Abschluss\n\n'+f"Geprüft {result['berlin']}: WINDOW_FINISHED nach unveränderter Deadline, Coordinator und Launcher beendet, alle {len(jobs)} gespeicherten Diagnoseworker/-Supervisoren beendet und Jobs geschlossen; Pilotworker nicht aktiv. Wachhalteanforderung durch Coordinatorfinally freigegeben und Prozessende verifiziert. Quellen {len(sources)} Pilotdateien/{len(assets)} Runtimeassets/{diagnostic_sources} Diagnose-Sourceeinträge, Dataset/Endcheckpoints/Updates/Losszeilen/Batch-/Startpaarungen und104Episoden erneut geprüft. [Abschlussnachweis]({path.name}). Automation wird erst nach dieser Prüfung pausiert; Bestätigung separat in automation_closeout.json. Keine weitere Training-/Simulatorrunde.\n")
    (S/'research_progress.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k not in ['diagnostic_jobs','diagnostic_source_manifests']},indent=2))
