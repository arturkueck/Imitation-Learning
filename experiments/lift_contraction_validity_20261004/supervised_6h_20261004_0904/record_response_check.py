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
assert all(status['progress'][arm]['optimizer_updates']==2000 for arm in ['B0','B1'])
assert status['progress']['evaluation']['episodes_completed']==104
pilot={}
for p in sorted((S/'attempts').glob('attempt_*')):
    pilot[p.name]={k:read(p/k) for k in ['run_result.json','worker_result.json'] if (p/k).exists()}
    for arm in ['B0','B1']:
        if (p/arm/'progress.json').exists():pilot[p.name][arm]=read(p/arm/'progress.json')
monitor=[json.loads(x) for x in (S/'monitor_checks.jsonl').read_text(encoding='utf-8').splitlines() if x]
repairs=[json.loads(x) for x in (S/'repairs.jsonl').read_text(encoding='utf-8').splitlines() if x]
O=S/'recorded_response_001';r=read(O/'result.json');a=read(O/'analysis_verification.json');pairs=read(O/'history_comparison.json')
processes={}
for p in [O,O/'preflight_001',O/'preflight_002']:
    sup=read(p/'supervisor_result.json');launch=read(p/'launch.json')
    assert not alive(sup['worker']) and not alive(dict(pid=launch['supervisor_pid'],create_time=launch['supervisor_create_time']))
    assert sup['worker_job_closed']
    processes[p.name]=dict(worker_identity=sup['worker'],supervisor_pid=launch['supervisor_pid'],both_exited=True,returncode=sup['returncode'])
assert r['policy_training_updates']==r['fit_updates']==0 and a['raw_sha256']==sha(O/'result.json')
assert pairs['analysis_sha256']==sha(O/'analysis_verification.json') and pairs['raw_sha256']==a['raw_sha256']
assert a['executed_branches']==672 and a['eligible_anchors']==16
t=time.time();d=datetime.fromtimestamp(t,timezone.utc)
event=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',
           trigger_utc='2026-10-04T10:07:44.501Z',unix=t,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
           coordinator_identity=pid,coordinator_alive=True,heartbeat_status=auto['status'],session_deadline_unix=session['deadline_unix'],
           pilot_attempt_results_reviewed=list(pilot),optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,
           monitor_records_reviewed=len(monitor),repair_records_reviewed=len(repairs),processes=processes,
           diagnosis_state=r['state'],audit_state=a['state'],executed_branches=672,eligible_history_anchors=16,planned_history_anchors=24,
           new_training_updates=0,new_fit_updates=0,raw_sha256=a['raw_sha256'],audit_sha256=sha(O/'analysis_verification.json'),
           history_comparison_sha256=sha(O/'history_comparison.json'),worker_elapsed_seconds=r['elapsed_seconds'],
           false_contraction_passes_per_history=6,
           decision='Scientific domain failure preserved. Small effect of the two explicit histories; fixed B7 still makes six false contraction passes per history on eligible recorded frames. Next predeclared local-vs-fixed response test; no policy training. Original deadline and ACTIVE automation retained.')
with (S/'agent_checks.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(event)+'\n')
(S/'research_progress.json').write_text(json.dumps(event,indent=2),encoding='utf-8')
print(json.dumps(event,indent=2))
