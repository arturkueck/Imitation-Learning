import json,time,tomllib,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
pid=read(S/'coordinator_pid.json');status=read(S/'status.json');session=read(S/'session.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert auto['status']=='ACTIVE'
for arm in ['B0','B1']:assert status['progress'][arm]['optimizer_updates']==2000
assert status['progress']['evaluation']['episodes_completed']==104
diagnoses={}
for name in ['mechanism_domain_001','recorded_domain_001']:
    O=S/name;r=read(O/'result.json');a=read(O/'analysis_verification.json');sup=read(O/'supervisor_result.json');launch=read(O/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
    assert r['policy_training_updates']==0 and a['raw_sha256']==sha(O/'result.json')
    diagnoses[name]=dict(worker_state=r['state'],audit_state=a['state'],raw_sha256=sha(O/'result.json'),
                        audit_sha256=sha(O/'analysis_verification.json'),worker_identity=sup['worker'],worker_and_supervisor_exited=True,
                        elapsed_seconds=r['elapsed_seconds'])
domain=read(S/'mechanism_domain_001/analysis_verification.json');recorded=read(S/'recorded_domain_001/analysis_verification.json')
t=time.time();d=datetime.fromtimestamp(t,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           unix=t,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           new_diagnosis_training_updates=0,diagnoses=diagnoses,domain_eligible_anchors=8,domain_planned_anchors=12,
           domain_executed_branches=336,recorded_geometry_passed=60,recorded_frames=60,recorded_static_contact_free=49,
           decision='Scientific domain failure preserved: all 4 late anchors contact. Static annotation available, not a sufficient dynamic mask. Next predeclared recorded-state response/history test, no training; original deadline and ACTIVE heartbeat.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
