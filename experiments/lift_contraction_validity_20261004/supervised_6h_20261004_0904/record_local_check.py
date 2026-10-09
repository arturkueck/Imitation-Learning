import json,time,tomllib,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;O=S/'local_response_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
pid=read(S/'coordinator_pid.json');status=read(S/'status.json');session=read(S/'session.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert auto['status']=='ACTIVE'
assert all(status['progress'][a]['optimizer_updates']==2000 for a in ['B0','B1'])
assert status['progress']['evaluation']['episodes_completed']==104
processes={}
for p in [O,O/'preflight_001']:
    sup=read(p/'supervisor_result.json');launch=read(p/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
    assert sup['worker_job_closed'] and sup['returncode']==0
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_pid=launch['supervisor_pid'],both_exited=True,elapsed_seconds=sup['elapsed_seconds'])
r=read(O/'result.json');a=read(O/'analysis_verification.json');v=read(O/'local_identification.json');check=read(O/'local_verification.json')
assert r['policy_training_updates']==v['policy_training_updates']==0 and a['raw_sha256']==sha(O/'result.json')
assert check['local_analysis_sha256']==sha(O/'local_identification.json') and check['physical_audit_sha256']==sha(O/'analysis_verification.json')
assert a['eligible_anchors']==v['local_identification_fits']==check['local_fits_checked']==8
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           trigger_utc='2026-10-04T10:37:45.000Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],
           optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,processes=processes,
           worker_state=r['state'],audit_state=a['state'],local_verification_state=check['state'],executed_branches=336,
           planned_anchors=12,eligible_anchors=8,local_simulator_identification_fits=8,new_policy_updates=0,
           primary_better_anchors=8,primary_ratio_error_reduction_percent=56.11910700694469,primary_false_pass_fixed=6,primary_false_pass_local=1,
           raw_sha256=a['raw_sha256'],physical_audit_sha256=sha(O/'analysis_verification.json'),local_analysis_sha256=sha(O/'local_identification.json'),
           independent_local_verification_sha256=sha(O/'local_verification.json'),worker_elapsed_seconds=r['elapsed_seconds'],
           decision='State-local B improves held ratio prediction at all eight eligible anchors; one false contraction pass remains. Four contact anchors retained/excluded. No policy training approval. Next predeclared pre-loss proximity proxy feasibility and fresh held validation. Original deadline/ACTIVE heartbeat retained.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
