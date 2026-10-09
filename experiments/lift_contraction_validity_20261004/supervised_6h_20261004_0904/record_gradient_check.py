import json,time,tomllib,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;O=S/'gradient_audit_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
pid=read(S/'coordinator_pid.json');status=read(S/'status.json');session=read(S/'session.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
automation=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text())
assert automation['status']=='ACTIVE'
sup=read(O/'supervisor_result.json');launch=read(O/'launch.json');r=read(O/'result.json');audit=read(O/'verification.json')
assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
assert r['state']=='COMPLETE' and audit['state']=='VERIFIED' and audit['result_sha256']==sha(O/'result.json')
assert r['policy_training_updates']==r['optimizer_constructions']==0
for arm in ['B0','B1']:assert status['progress'][arm]['optimizer_updates']==2000
assert status['progress']['evaluation']['episodes_completed']==104
t=time.time();d=datetime.fromtimestamp(t,timezone.utc)
record=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
            unix=t,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
            coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',optimizer_updates_per_arm=2000,
            evaluation_episodes_completed=104,new_diagnosis_training_updates=0,mechanism_state='GRADIENT_AUDIT_COMPLETE_VERIFIED',
            diagnostic_workers_and_supervisors_exited=True,frames=60,train_demos=8,valid_demos=4,
            parameter_sha256=r['final_parameter_sha256'],result_sha256=sha(O/'result.json'),verification_sha256=sha(O/'verification.json'),
            summaries=r['summaries'],finite_difference_state=r['finite_difference']['state'],
            decision='Recorded-data audit shows phase-dependent gradient scale, no policy improvement. Next predeclared live-domain probe, frozen calibration, no training. Keep original deadline and ACTIVE heartbeat.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
(S/'research_progress.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k!='summaries'},indent=2))
