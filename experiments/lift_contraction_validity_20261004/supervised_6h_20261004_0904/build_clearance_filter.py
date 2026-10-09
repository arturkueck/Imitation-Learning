import json,hashlib,shutil,time,tomllib,py_compile
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np,psutil
S=Path(__file__).resolve().parent;R=S.parents[2];O=S/'clearance_filter_001';OLD=S/'local_response_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
status=read(S/'status.json');session=read(S/'session.json');pid=read(S/'coordinator_pid.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert auto['status']=='ACTIVE'
assert all(status['progress'][a]['optimizer_updates']==2000 for a in ['B0','B1']) and status['progress']['evaluation']['episodes_completed']==104
inventory={}
for p in sorted((S/'attempts').glob('attempt_*')):
    inventory[p.name]={n:read(p/n) for n in ['run_result.json','worker_result.json','B0/progress.json','B1/progress.json'] if (p/n).exists()}
for name in ['monitor_checks.jsonl','repairs.jsonl']:
    for line in (S/name).read_text(encoding='utf-8').splitlines():
        if line:json.loads(line)
for p in S.glob('*/launch.json'):
    launch=read(p)
    if 'supervisor_pid' in launch:assert not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time'])),str(p)
sel=read(OLD/'selection.json');excluded=set(sel['excluded_prior_demos'])|set(sel['selected_demos'])
train=read(S/'attempts/attempt_002/dataset_manifest.json')['train_demos']
chosen=np.random.default_rng(4100410).choice(sorted(set(train)-excluded),4,replace=False).tolist()
for key in ['identification','primary_models','secondary_models']:sel.pop(key,None)
sel.update(seed=4100410,selected_demos=chosen,excluded_prior_demos=sorted(excluded),proximity_margin_m=.015,
           primary_masks=['M0_initial_contact_free','M1_initial_and_proximity_contact_free'],identification_fits=0,
           masks_before_response=True,native_version_required='3.2.3')
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256'] and sha(S/'attempts/attempt_002/B0/model_final.pth')==sel['checkpoint_sha256']
O.mkdir()
for name in ['helpers.py','preparation.py','supervise.py','calibration.json']:shutil.copy2(OLD/name,O/name)
shutil.copy2(S/'NEXT_CLEARANCE_FILTER.md',O/'PROTOCOL.md')
with (O/'selection.json').open('x',encoding='utf-8') as f:json.dump(sel,f,indent=2)
source=(OLD/'run.py').read_text(encoding='utf-8').replace('import preparation','import preparation\nimport clearance')
needle="                                anchor, anchor_measure = h.snapshot(env, ctrl), h.measured(sim, ctrl)"
assert source.count(needle)==1
source=source.replace(needle,needle+"\n                                if name == 'reference':\n                                    row['pre_response_filter'] = clearance.filter_anchor(env, ctrl, selection['proximity_margin_m'])\n                                    h.write(OUT / 'result.json', result)")
with (O/'run.py').open('x',encoding='utf-8') as f:f.write(source)
pref=O/'preflight_001';pref.mkdir()
shutil.copy2(OLD/'preflight_001/supervise.py',pref/'supervise.py')
py_compile.compile(str(O/'run.py'),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_started',trigger_utc='2026-10-04T11:07:45.538Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           attempts_reviewed=list(inventory),selected_demos=chosen,seed=4100410,
           decision='Predeclared conservative proximity proxy: technical preflight first, then masks stored before 336 held response branches. No training/fitting or threshold adjustment.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
