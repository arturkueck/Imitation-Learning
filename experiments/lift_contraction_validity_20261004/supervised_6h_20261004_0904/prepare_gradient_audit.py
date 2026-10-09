import json, hashlib, shutil, time, tomllib
from pathlib import Path
from datetime import datetime, timezone, timedelta
import numpy as np
import psutil
S=Path(__file__).resolve().parent
R=S.parents[2]
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json');status=read(S/'status.json');pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())
assert auto['status']=='ACTIVE'
for arm in ['B0','B1']:assert status['progress'][arm]['optimizer_updates']==2000
assert status['progress']['evaluation']['episodes_completed']==104
inspected=[]
for p in sorted((S/'attempts').glob('attempt_*')):
    for name in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json']:
        f=p/name
        if f.exists():inspected.append(dict(path=str(f),sha256=sha(f),state=read(f).get('state')))
    for f in sorted(p.glob('*.log')):
        inspected.append(dict(path=str(f),bytes=f.stat().st_size,tail=f.read_text(errors='replace')[-500:]))
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    lines=(S/name).read_text(encoding='utf-8').splitlines()
    inspected.append(dict(path=name,entries=len(lines),latest=json.loads(lines[-1])))
for name in ['mechanism_AB_001','mechanism_AB_002','mechanism_action7_001','mechanism_correction_001']:
    sup=read(S/name/'supervisor_result.json'); launch=read(S/name/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
O=S/'gradient_audit_001';O.mkdir()
prior=read(S/'mechanism_correction_001/selection.json')
excluded=set(prior['excluded_prior_demos'])|set(prior['selected_demos'])
manifest=read(S/'attempts/attempt_002/dataset_manifest.json');rng=np.random.default_rng(4100405)
train=rng.choice(sorted(set(manifest['train_demos'])-excluded),8,replace=False).tolist()
valid=rng.choice(sorted(set(manifest['valid_demos'])-excluded),4,replace=False).tolist()
sel=dict(seed=4100405,train_demos=train,valid_demos=valid,excluded_prior_demos=sorted(excluded),
         fractions=[.05,.10,.15,.50,.85],radius_m=.005,target_ratio=.99,lambda_diagnostic=1.,domain_weight_diagnostic=1.,
         finite_difference_demo=train[0],finite_difference_fraction=.05,finite_difference_epsilon=1e-5,
         finite_difference_relative_tolerance=5e-4,finite_difference_absolute_tolerance=1e-7,
         finite_difference_direction='Per-loss normalized analytic gradient on separate float64 clone; zero gradient reported as degenerate.',
         no_optimizer_construction=True,source_observations='recorded, not physically reconstructed',
         dataset_sha256=manifest['sha256'],checkpoint_sha256=sha(S/'attempts/attempt_002/B0/model_final.pth'))
(O/'selection.json').write_text(json.dumps(sel,indent=2),encoding='utf-8')
shutil.copy2(S/'NEXT_GRADIENT_AUDIT.md',O/'PROTOCOL.md')
shutil.copy2(S/'mechanism_correction_001/calibration.json',O/'calibration.json')
shutil.copy2(S/'mechanism_correction_001/supervise.py',O/'supervise.py')
t=time.time();utc=datetime.fromtimestamp(t,timezone.utc)
rec=dict(actor='agent',scheduled=True,event='scheduled_check_begin',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
         unix=t,utc=utc.isoformat(),berlin=utc.astimezone(timezone(timedelta(hours=2))).isoformat(),
         coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,
         evaluation_episodes_completed=104,diagnostic_workers_and_supervisors_exited=True,inspected=inspected,
         decision='Execute predeclared gradient-scale audit on new recorded train/valid demos; no optimizer or policy update. Keep original deadline.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(rec)+'\n')
print(json.dumps(dict(selection=sel,coordinator_alive=True,heartbeat_status=auto['status'],inspected_files=len(inspected)),indent=2))
