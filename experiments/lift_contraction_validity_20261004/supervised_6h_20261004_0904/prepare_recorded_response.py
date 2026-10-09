import json,hashlib,shutil,time,tomllib
from datetime import datetime,timezone,timedelta
from pathlib import Path
import numpy as np,psutil
S=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json');status=read(S/'status.json');identity=read(S/'coordinator_pid.json')
assert alive(identity) and time.time()-status['updated_unix']<30
assert session['deadline_unix']==status['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
automation=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert automation['status']=='ACTIVE'
inspected=[]
for p in sorted((S/'attempts').glob('attempt_*')):
    for name in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json']:
        f=p/name
        if f.exists():inspected.append(dict(path=str(f),sha256=sha(f),state=read(f).get('state')))
    for f in sorted(p.glob('*.log')):inspected.append(dict(path=str(f),bytes=f.stat().st_size,tail=f.read_text(errors='replace')[-500:]))
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    lines=(S/name).read_text(encoding='utf-8').splitlines();inspected.append(dict(path=name,entries=len(lines),latest=json.loads(lines[-1])))
for name in ['mechanism_AB_001','mechanism_AB_002','mechanism_action7_001','mechanism_correction_001','gradient_audit_001','mechanism_domain_001','recorded_domain_001']:
    sup=read(S/name/'supervisor_result.json');launch=read(S/name/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
for arm in ['B0','B1']:assert status['progress'][arm]['optimizer_updates']==2000
assert status['progress']['evaluation']['episodes_completed']==104
prior=read(S/'mechanism_domain_001/selection.json');excluded=set(prior['excluded_prior_demos'])|set(prior['selected_demos'])
manifest=read(S/'attempts/attempt_002/dataset_manifest.json')
demos=np.random.default_rng(4100408).choice(sorted(set(manifest['train_demos'])-excluded),4,replace=False).tolist()
O=S/'recorded_response_001';O.mkdir()
selection=dict(seed=4100408,selected_demos=demos,excluded_prior_demos=sorted(excluded),anchor_fractions=[.1,.5,.85],histories=['H_prefix','H_reset'],
               physical_delta_m=.005,action_delta=.1,position_tolerance_m=1e-6,degenerate_threshold_m=1e-6,legacy_degenerate_threshold_m=1e-5,
               ratio_threshold=.99,total_anchors=24,unique_recorded_anchors=12,branches_per_anchor=28,planned_branches=672,
               standardized_aux_fields=['ctrl','act','qacc_warmstart','qfrc_applied','xfrc_applied','userdata'],
               standardized_aux_value=0,standardized_env_clock='recorded sim time; timestep=t; done=False',
               fit_updates=0,policy_training_updates=0,dataset_sha256=manifest['sha256'],checkpoint_sha256=sha(S/'attempts/attempt_002/B0/model_final.pth'))
(O/'selection.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
for name in ['helpers.py','supervise.py']:shutil.copy2(S/'mechanism_domain_001'/name,O/name)
shutil.copy2(S/'mechanism_domain_001/calibration.json',O/'calibration.json');shutil.copy2(S/'NEXT_RECORDED_RESPONSE.md',O/'PROTOCOL.md')
t=time.time();d=datetime.fromtimestamp(t,timezone.utc)
record=dict(actor='agent',scheduled=True,event='scheduled_check_begin',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
            unix=t,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),coordinator_identity=identity,
            coordinator_alive=True,heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
            inspected=inspected,decision='Preflight then predeclared recorded-state response test under two controlled histories, frozen calibration and no training. Keep original deadline.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(dict(selection=selection,coordinator_alive=True,heartbeat_status='ACTIVE'),indent=2))
