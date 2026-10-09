import json,hashlib,time,shutil,tomllib,py_compile
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;O=S/'method_reference_001';D=S/'error_margin_001';ROOT=S.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
status=read(S/'status.json');session=read(S/'session.json');pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30 and status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
assert tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())['status']=='ACTIVE'
assert all(status['progress'][arm]['optimizer_updates']==2000 for arm in ['B0','B1']) and status['progress']['evaluation']['episodes_completed']==104
assert '2.000' in (S/'SESSION_PROTOCOL.md').read_text(encoding='utf-8')
attempts={}
for p in (S/'attempts').glob('attempt_*'):
    attempts[p.name]={n:read(p/n) for n in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json'] if (p/n).exists()}
    attempts[p.name]['logs']={str(log.relative_to(p)):log.read_text(encoding='utf-8',errors='replace').splitlines()[-3:] for log in p.glob('*.log')}
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    for line in (S/name).read_text(encoding='utf-8').splitlines():
        if line:json.loads(line)
for p in S.rglob('launch.json'):
    launch=read(p)
    if 'supervisor_pid' in launch:assert not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
sel=read(D/'selection.json');assert sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256'] and sha(S/'attempts/attempt_002/B0/model_final.pth')==sel['checkpoint_sha256']
raw=read(D/'result.json');assert raw['rows'][0]['demo']=='demo_38'
sources=['error_margin_001/'+n for n in ['result.json','analysis_verification.json','local_identification.json','filter_analysis.json','margin_spec.json','calibration.json','analysis_repair_001/margin_analysis.json','source_hashes.json']]
spec=dict(seed=4100413,planned_frames=12,planned_perturbations=72,dataset_sha256=sel['dataset_sha256'],checkpoint_sha256=sel['checkpoint_sha256'],
          input_hashes={n:sha(S/n) for n in sources},first_fd_anchor=dict(demo=raw['rows'][0]['demo'],t=raw['rows'][0]['t']),
          feature_absolute_tolerance=1e-6,action_region='All7 components within actual nominal minus/plus0.1 endpoints, including clipping; no relaxed tolerance.',
          fixed_session_deadline_unix=session['deadline_unix'],reuse_is_exploratory_not_fresh_confirmation=True,cache_is_privileged=True,
          gradient_lambda=1.,not_selected_for_training=True,policy_updates=0,variants=['M0_raw','M0_margin','M2_raw','M2_margin'])
O.mkdir()
for target,source in [('loss_reference.py','method_loss_source.py'),('checks.py','method_checks_source.py'),('run.py','method_run_source.py')]:shutil.copy2(S/source,O/target)
shutil.copy2(D/'supervise.py',O/'supervise.py');shutil.copy2(S/'NEXT_METHOD_REFERENCE.md',O/'PROTOCOL.md')
with (O/'selection.json').open('x',encoding='utf-8') as out:json.dump(spec,out,indent=2)
with (O/'PROTOCOL.md').open('a',encoding='utf-8') as out:
    out.write('\nVorabimplementationswerte: Policyfeaturemapping rohe konfigurierte vier Inputkeys mit absoluter Toleranz1e-6 (kein physischer Neuversuch), Sensorstörung±5mm gleiches konsistentes EEF/Objektfeature, fester epsilon0.0021163913289946276. Vier VariantenM0/M2×roh/Marge, statische nominale Maske separat vom erst nach physischer Validierung verfügbaren B_cache. Komponentensupport exact tatsächliche ±0.1Endpunkte; kein nach Ergebnis vergrößerter Aktionsbereich. Richtungsableitung erster vorab fixierter Kandidat demo_38,t4, Float64-Klon eps1e-5, relativ1e-5/absolut1e-7; Nichtglattheit separat. Ganze72 im Lossnenner. BC-Gradient offizielles unclipped Trainingsziel, Regularisierer verwendet controllerseitig geklippte Aktionen wie physische Kalibrierung, λ1nurDiagnostik. Bestehende endliche Marge scheitert fachlich; Rechenbarkeit hebt diese Entscheidung nicht auf.\n')
pref=O/'preflight_001';pref.mkdir();shutil.copy2(D/'preflight_001/supervise.py',pref/'supervise.py')
source='''import sys,json,time,traceback
from pathlib import Path
O=Path(__file__).resolve().parent;sys.path.insert(0,str(O.parent))
from checks import run_checks
start=time.monotonic()
try:r=run_checks();r['state']='PREFLIGHT_PASSED';code=0
except BaseException:r=dict(state='FAILED',error=traceback.format_exc());traceback.print_exc();code=2
r['elapsed_seconds']=time.monotonic()-start
with (O/'result.json').open('x',encoding='utf-8') as out:json.dump(r,out,indent=2)
print(json.dumps(r,indent=2));raise SystemExit(code)
'''
with (pref/'run.py').open('x',encoding='utf-8') as out:out.write(source)
for p in O.rglob('*.py'):py_compile.compile(str(p),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_started',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',trigger_utc='2026-10-04T12:39:46.985Z',
           utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,coordinator_identity=pid,coordinator_alive=True,
           deadline_unix=session['deadline_unix'],heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,attempts_reviewed=list(attempts),
           new_policy_updates=0,new_physics_probes=0,decision='Implement isolated full-action/mask/envelope loss reference; numerical preflight then exploratory cache/feature/action-region/gradient audit of existing12frames. No optimizer construction, policy parameter change or production registration; failed empirical envelope remains failed.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as out:out.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
