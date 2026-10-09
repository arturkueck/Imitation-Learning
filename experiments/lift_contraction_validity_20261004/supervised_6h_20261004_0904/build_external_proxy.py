import json,hashlib,shutil,time,tomllib,py_compile
from pathlib import Path
from datetime import datetime,timezone,timedelta
import numpy as np,psutil
S=Path(__file__).resolve().parent;R=S.parents[2];O=S/'external_proxy_001';OLD=S/'clearance_filter_001'
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
chosen=np.random.default_rng(4100411).choice(sorted(set(train)-excluded),4,replace=False).tolist()
sel.update(seed=4100411,selected_demos=chosen,excluded_prior_demos=sorted(excluded),
           primary_masks=['M2_initial_and_external_proximity_contact_free'],control_masks=['M0_initial_contact_free','M1_initial_and_proximity_contact_free'],
           useful_candidate_gate=dict(false_accept=0,minimum_true_accept=4,denominator=12),
           dynamic_label_includes_all_actual_robot_self_contacts=True)
assert sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==sel['dataset_sha256'] and sha(S/'attempts/attempt_002/B0/model_final.pth')==sel['checkpoint_sha256']
O.mkdir()
for name in ['helpers.py','preparation.py','supervise.py','calibration.json','analyze_audit.py','history_audit.py']:shutil.copy2(OLD/name,O/name)
shutil.copy2(S/'NEXT_EXTERNAL_PROXY.md',O/'PROTOCOL.md')
with (O/'selection.json').open('x',encoding='utf-8') as f:json.dump(sel,f,indent=2)
shutil.copy2(OLD/'run_defined_arrays.py',O/'run.py')
source=(OLD/'clearance_defined_arrays.py').read_text(encoding='utf-8')
needle="    return dict(initial_robot_contacts=initial,proximity=info,anchor_before_query=before,anchor_after_query=after,"
assert source.count(needle)==1
source=source.replace(needle,"    near=info['nearby_robot_contacts']\n    internal=[c for c in near if all(n in names for n in c['names'])]\n    external=[c for c in near if not all(n in names for n in c['names'])]\n    assert all(sum(n in names for n in c['names'])==1 for c in external)\n"+needle)
source=source.replace("computed_before_any_response_action=True,policy_training_updates=0)",
                      "internal_proximity_contacts=internal,external_proximity_contacts=external,\n                M2_initial_and_external_proximity_contact_free=not initial and not external,\n                dynamic_label_retains_all_actual_self_contacts=True,computed_before_any_response_action=True,policy_training_updates=0)")
with (O/'clearance_defined_arrays.py').open('x',encoding='utf-8') as f:f.write(source)
pref=O/'preflight_001';pref.mkdir();shutil.copy2(OLD/'preflight_003/supervise.py',pref/'supervise.py')
source=(OLD/'preflight_003/run.py').read_text(encoding='utf-8')
needle="        result['known_frame']=dict(demo=demo,t=t,preparation=prep,query=clearance.filter_anchor(env,ctrl,.015))"
assert source.count(needle)==1
source=source.replace(needle,needle+"\n        known=result['known_frame']['query']\n        assert known['M0_initial_contact_free'] and not known['M1_initial_and_proximity_contact_free'] and known['M2_initial_and_external_proximity_contact_free']\n        assert known['internal_proximity_contacts'] and not known['external_proximity_contacts']")
with (pref/'run.py').open('x',encoding='utf-8') as f:f.write(source)
for p in [O/'clearance_defined_arrays.py',O/'run.py',pref/'run.py']:py_compile.compile(str(p),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_started',trigger_utc='2026-10-04T11:37:45.990Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           attempts_reviewed=list(inventory),selected_demos=chosen,seed=4100411,
           decision='One predeclared external-vs-all proximity scope test, same 15mm query and all actual self contacts in unchanged dynamic label. Technical preflight first. No training, fitting, threshold or seed sweep.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
