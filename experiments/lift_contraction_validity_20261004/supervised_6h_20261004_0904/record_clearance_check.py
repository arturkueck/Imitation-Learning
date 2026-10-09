import json,time,tomllib,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
import psutil
S=Path(__file__).resolve().parent;O=S/'clearance_filter_001'
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:return abs(psutil.Process(i['pid']).create_time()-i['create_time'])<.1
    except psutil.NoSuchProcess:return False
pid=read(S/'coordinator_pid.json');status=read(S/'status.json');session=read(S/'session.json')
assert alive(pid) and time.time()-status['updated_unix']<30
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713 and time.time()<session['deadline_unix']
auto=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text());assert auto['status']=='ACTIVE'
assert all(status['progress'][a]['optimizer_updates']==2000 for a in ['B0','B1']) and status['progress']['evaluation']['episodes_completed']==104
processes={}
for p in [O]+sorted(O.glob('preflight_*'))+[O/'diagnosis_003',O/'query_verification_001']:
    sup=read(p/'supervisor_result.json');launch=read(p/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
    assert sup['worker_job_closed'] and launch['deadline_unix']<=session['deadline_unix']
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_pid=launch['supervisor_pid'],both_exited=True,returncode=sup['returncode'],elapsed_seconds=sup['elapsed_seconds'])
r=read(O/'result.json');a=read(O/'analysis_verification.json');f=read(O/'filter_analysis.json');q=read(O/'query_verification_001/result.json')
assert a['raw_sha256']==f['raw_sha256']==q['raw_sha256']==sha(O/'result.json')
assert q['filter_analysis_sha256']==sha(O/'filter_analysis.json') and q['state']=='NATIVE_FILTER_QUERIES_INDEPENDENTLY_REPRODUCED'
assert r['policy_training_updates']==r['fit_updates']==0 and a['eligible_anchors']==8 and a['executed_branches']==336
assert f['masks']['M1']['accepted']==0 and f['masks']['M1']['false_reject']==8 and f['masks']['M0']['false_accept']==1
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           trigger_utc='2026-10-04T11:07:45.538Z',utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),unix=now,
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status='ACTIVE',deadline_unix=session['deadline_unix'],optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           processes=processes,worker_state=r['state'],audit_state=a['state'],mask_state='SCIENTIFIC_ZERO_COVERAGE_REJECTED',native_query_reproduction_state=q['state'],
           executed_branches=336,planned_anchors=12,eligible_anchors=8,M0=f['masks']['M0'],M1=f['masks']['M1'],new_policy_updates=0,new_fits=0,
           raw_sha256=sha(O/'result.json'),physical_audit_sha256=sha(O/'analysis_verification.json'),filter_analysis_sha256=sha(O/'filter_analysis.json'),
           independent_query_verification_sha256=sha(O/'query_verification_001/result.json'),worker_elapsed_seconds=r['elapsed_seconds'],
           decision='All-pair proximity proxy rejected for zero coverage, original scientific negative preserved. Nominal contact flag still has one false accept. External-only scope is posthoc on old data and requires the predeclared fresh comparison; all actual self contacts remain in unchanged dynamic label. No training/sweep; original deadline and ACTIVE heartbeat.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
