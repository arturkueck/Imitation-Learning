"""Freeze fresh selection and the already verified H_reset physical worker."""
import json,hashlib,shutil,time,tomllib,py_compile
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np,psutil
S=Path(__file__).resolve().parent;R=S.parents[2];O=S/'local_response_001';OLD=S/'recorded_response_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
session=read(S/'session.json');status=read(S/'status.json');pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert session['deadline_unix']==status['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert auto['status']=='ACTIVE'
assert all(status['progress'][a]['optimizer_updates']==2000 for a in ['B0','B1'])
assert status['progress']['evaluation']['episodes_completed']==104
inventory=[]
for attempt in sorted((S/'attempts').glob('attempt_*')):
    for name in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json']:
        if (attempt/name).exists():read(attempt/name);inventory.append(str((attempt/name).relative_to(S)))
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    for line in (S/name).read_text(encoding='utf-8').splitlines():
        if line:json.loads(line)
for p in S.glob('*/launch.json'):
    launch=read(p)
    if 'supervisor_pid' in launch:assert not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])),str(p)
manifest=read(S/'attempts/attempt_002/dataset_manifest.json')
sel=read(OLD/'selection.json');excluded=set(sel['excluded_prior_demos'])|set(sel['selected_demos'])
chosen=np.random.default_rng(4100409).choice(sorted(set(manifest['train_demos'])-excluded),4,replace=False).tolist()
sel.update(seed=4100409,selected_demos=chosen,excluded_prior_demos=sorted(excluded),histories=['H_reset'],total_anchors=12,unique_recorded_anchors=12,planned_branches=336,
           identification='Separate nominal plus/minus action branches; per-anchor B_local=lstsq(D,Y). No optimizer or policy fitting.',
           primary_models=['A_B7_fixed','A_B7_local'],secondary_models=['I_B7_local'])
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256']
assert sha(S/'attempts/attempt_002/B0/model_final.pth')==sel['checkpoint_sha256']
O.mkdir()
for name in ['helpers.py','preparation.py','supervise.py','calibration.json']:shutil.copy2(OLD/name,O/name)
shutil.copy2(S/'NEXT_LOCAL_RESPONSE.md',O/'PROTOCOL.md')
with (O/'selection.json').open('x',encoding='utf-8') as f:json.dump(sel,f,indent=2)
source=(OLD/'run.py').read_text(encoding='utf-8').replace('planned_branches=672','planned_branches=336').replace("== 24 and sum(len(r['branches']) for r in result['rows']) == 672","== 12 and sum(len(r['branches']) for r in result['rows']) == 336")
assert '== 12' in source and '== 336' in source
with (O/'run.py').open('x',encoding='utf-8') as f:f.write(source)
pref=O/'preflight_001';pref.mkdir()
source=(OLD/'preflight_002/run.py').read_text(encoding='utf-8').replace("for history in selection['histories']:","for history in ['H_reset','H_reset']:")
with (pref/'run.py').open('x',encoding='utf-8') as f:f.write(source)
source=(OLD/'preflight_002/supervise.py').read_text(encoding='utf-8')
with (pref/'supervise.py').open('x',encoding='utf-8') as f:f.write(source)
for p in [O/'run.py',pref/'run.py',pref/'supervise.py']:py_compile.compile(str(p),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_started',trigger_utc='2026-10-04T10:37:45.000Z',
           utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],
           optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,attempt_outputs_reviewed=inventory,
           decision='Execute predeclared fixed-vs-local action response identification on four fresh Train demos; no policy training, immutable deadline.',
           selected_demos=chosen,seed=4100409)
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
