import json, hashlib, shutil, time, tomllib, py_compile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np, psutil
S=Path(__file__).resolve().parent; ROOT=S.parents[2]; OLD=S/'external_proxy_001'; O=S/'error_margin_001'
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try: return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess: return False
session=read(S/'session.json'); status=read(S/'status.json'); pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert session['deadline_unix']==status['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
assert tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())['status']=='ACTIVE'
assert all(status['progress'][arm]['optimizer_updates']==2000 for arm in ['B0','B1'])
assert status['progress']['evaluation']['episodes_completed']==104
protocol=(S/'SESSION_PROTOCOL.md').read_text(encoding='utf-8'); assert '2.000' in protocol
inventory={}
for p in sorted((S/'attempts').glob('attempt_*')):
    inventory[p.name]={name:read(p/name) for name in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json'] if (p/name).exists()}
    inventory[p.name]['log_tails']={str(log.relative_to(p)):log.read_text(encoding='utf-8',errors='replace').splitlines()[-4:] for log in p.glob('*.log')}
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    for line in (S/name).read_text(encoding='utf-8').splitlines():
        if line: json.loads(line)
for p in S.rglob('launch.json'):
    launch=read(p)
    if 'supervisor_pid' in launch:
        assert not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])),str(p)
spec=read(S/'NEXT_ERROR_MARGIN.json'); assert spec['seed']==4100412
assert sha(S/Path(spec['calibration_source']))==spec['calibration_source_sha256']
assert sha(S/'local_response_001/result.json')==spec['calibration_raw_sha256']
old=read(S/Path(spec['calibration_source']))
errors=[x['models']['A_B7_local']['vector_error_m']/np.linalg.norm(x['delta_m']) for x in old['conditional_policy_raw']]
assert len(errors)==48 and max(errors)==spec['empirical_normalized_vector_error_max']
manifest=read(S/'attempts/attempt_002/dataset_manifest.json')
chosen=np.random.default_rng(spec['seed']).choice(sorted(set(manifest['train_demos'])-set(spec['excluded_prior_demos'])),4,replace=False).tolist()
assert chosen==spec['selected_demos'] and sha(OLD/'calibration.json')==spec['fixed_response_calibration_sha256']
assert sha(ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5')==spec['dataset_sha256'] and sha(S/'attempts/attempt_002/B0/model_final.pth')==spec['checkpoint_sha256']
sel=read(OLD/'selection.json'); sel.update(seed=spec['seed'],selected_demos=chosen,excluded_prior_demos=spec['excluded_prior_demos'],error_margin_spec=spec)
O.mkdir()
for name in ['run.py','helpers.py','preparation.py','clearance_defined_arrays.py','supervise.py','calibration.json','analyze_audit.py','history_audit.py','analyze_filter.py']:
    shutil.copy2(OLD/name,O/name)
shutil.copy2(S/'NEXT_ERROR_MARGIN.md',O/'PROTOCOL.md')
shutil.copy2(S/'NEXT_ERROR_MARGIN.json',O/'margin_spec.json')
with (O/'selection.json').open('x',encoding='utf-8') as f: json.dump(sel,f,indent=2)
source=(S/'local_response_001/analysis_repair_001/analyze_local.py').read_text(encoding='utf-8')
assert source.count('O=Path(__file__).resolve().parent.parent')==1
source=source.replace('O=Path(__file__).resolve().parent.parent','O=Path(__file__).resolve().parent')
with (O/'analyze_local.py').open('x',encoding='utf-8') as f: f.write(source)
for folder in ['preflight_001','query_verification_001']:
    (O/folder).mkdir()
    for name in ['run.py','supervise.py']: shutil.copy2(OLD/folder/name,O/folder/name)
for name in ['analyze_margin.py','verify_margin.py']: shutil.copy2(S/('error_'+name),O/name)
for p in O.rglob('*.py'): py_compile.compile(str(p),doraise=True)
now=time.time(); d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_started',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           trigger_utc='2026-10-04T12:09:46.504Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,deadline_unix=session['deadline_unix'],heartbeat_status='ACTIVE',
           optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,attempts_reviewed=list(inventory),
           seed=spec['seed'],selected_demos=chosen,epsilon_train=spec['empirical_normalized_vector_error_max'],
           decision='Execute predeclared frozen empirical vector-error envelope on four fresh Train demos, same A/localB7 and exact physical/domain gates. No policy training, bound tuning or checkpoint selection. Technical preflight before primary data.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f: f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
