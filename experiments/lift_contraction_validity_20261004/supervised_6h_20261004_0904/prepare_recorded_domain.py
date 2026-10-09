import json,hashlib,shutil,time
from datetime import datetime,timezone,timedelta
from pathlib import Path
import psutil
S=Path(__file__).resolve().parent;O=S/'recorded_domain_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
prior=read(S/'mechanism_domain_001/analysis_verification.json');sup=read(S/'mechanism_domain_001/supervisor_result.json')
assert prior['state']=='AUDIT_VERIFIED_DOMAIN_GATE_FAILED'
try:assert abs(psutil.Process(sup['worker']['pid']).create_time()-sup['worker']['create_time'])>.1
except psutil.NoSuchProcess:pass
# Authored worker files can precede selection; no prior launch/output may exist.
assert O.is_dir() and set(p.name for p in O.iterdir())=={'run.py','freeze.py'}
gradient=read(S/'gradient_audit_001/result.json')
selection=dict(seed=4100407,frames=[{k:x[k] for k in ['demo','split','t','fraction','phase','length']} for x in gradient['rows']],
               source_gradient_sha256=sha(S/'gradient_audit_001/result.json'),dataset_sha256=gradient['selection']['dataset_sha256'],
               checkpoint_sha256=gradient['checkpoint_sha256_before'],position_tolerance_m=1e-6,orientation_tolerance_rad=1e-4,
               gripper_qpos_tolerance=1e-9,planned_frames=60,policy_training_updates=0,action_rollout_steps=0,
               reuse_known_frames=True,no_dynamic_validity_claim=True)
(O/'selection.json').write_text(json.dumps(selection,indent=2),encoding='utf-8')
shutil.copy2(S/'NEXT_RECORDED_DOMAIN_MASK.md',O/'PROTOCOL.md')
for name in ['helpers.py','supervise.py']:shutil.copy2(S/'mechanism_domain_001'/name,O/name)
t=time.time();d=datetime.fromtimestamp(t,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_continues',unix=t,utc=d.isoformat(),
           berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),domain_state=prior['state'],eligible_anchors=8,planned_anchors=12,
           decision='Domain probe completed with scientific contact exclusions; no retry or training. Continue same scheduled turn with predeclared static recorded-frame availability audit.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
print('Fresh recorded-frame annotation audit prepared, all 60 existing frames, no replacement or rollout.')
