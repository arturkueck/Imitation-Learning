"""Log this actual scheduled agent check, not a watchdog-generated event."""
import json
import time
import hashlib
import tomllib
from datetime import datetime, timezone, timedelta
from pathlib import Path
import psutil

S = Path(__file__).resolve().parent
def read(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def alive(i):
    try:
        p=psutil.Process(i['pid'])
        return abs(p.create_time()-i['create_time'])<.1 and p.is_running()
    except psutil.NoSuchProcess: return False
def append(p,r):
    with p.open('a',encoding='utf-8') as f: f.write(json.dumps(r,allow_nan=False)+'\n')

identity=read(S/'coordinator_pid.json')
# Identity file includes additional metadata; PID and creation time are authoritative.
if 'create_time' not in identity: identity={'pid':identity['pid'],'create_time':identity['created_unix']}
assert alive(identity)
session=read(S/'session.json'); status=read(S/'status.json')
assert status['deadline_unix']==session['deadline_unix']==1791119479.6970713
assert time.time()<session['deadline_unix'] and time.time()-status['updated_unix']<30
automation=tomllib.loads((Path.home()/'.codex/automations/bc-forschung-fortschritt-und-trainings-pr-fen/automation.toml').read_text(encoding='utf-8'))
assert automation['status']=='ACTIVE'
M=S/'mechanism_correction_001'; a=read(M/'analysis_repair_002/analysis_result.json')
assert a['state']=='ANALYSIS_REPAIRED_VERIFIED'
sup=read(M/'supervisor_result.json'); launch=read(M/'launch.json')
assert not alive(sup['worker']) and not alive({'pid':launch['supervisor_pid'],'create_time':launch['supervisor_create_time']})
for name,digest in a['inputs'].items(): assert sha(M/name)==digest
for arm in ['B0','B1']: assert status['progress'][arm]['optimizer_updates']==2000
assert status['progress']['evaluation']['episodes_completed']==104
now=time.time(); stamp=datetime.fromtimestamp(now,timezone.utc)
assert stamp.date().isoformat()=='2026-10-04'
# Berlin is UTC+02 on this explicitly bounded October 4 session; no tzdata installation required.
berlin_zone=timezone(timedelta(hours=2),name='Europe/Berlin')
record=dict(actor='agent',scheduled=True,event='scheduled_check_research_completed',
            automation_id='bc-forschung-fortschritt-und-trainings-pr-fen',unix=now,
            utc=stamp.isoformat(),berlin=stamp.astimezone(berlin_zone).isoformat(),
            coordinator_identity=identity,coordinator_alive=True,heartbeat_status='ACTIVE',
            optimizer_updates_per_arm=2000,evaluation_episodes_completed=104,new_diagnosis_training_updates=0,
            mechanism_state=a['state'],original_worker_state='FAILED_POSTPROCESSING',
            valid_anchors=12,valid_branches=312,diagnostic_workers_and_supervisors_exited=True,
            result_sha256=sha(M/'result.json'),analysis_sha256=sha(M/'analysis_repair_002/analysis_result.json'),
            primary=a['primary'],summaries=a['summaries'],
            decision='Correction analysis repaired without rerunning physics. Better 7D prediction, both calibrated arms 72/72 threshold; no BC improvement claim. Next predeclared gradient-scale audit without updates. Original deadline/heartbeat unchanged.')
append(S/'repairs.jsonl',dict(actor='agent',event='diagnosis_analysis_repair',unix=now,utc=record['utc'],berlin=record['berlin'],
                            reason='Correction worker duplicated predicted_ratio in dict aggregation after all 312 branches. Preserve FAILED worker; only stored-data analysis repaired in fresh folders. First audit precision assumption rejected and retained; actual precision recomputes all actions/predictions exactly.',
                            worker_identity=sup['worker'],repair_source=str(M/'analysis_repair_002/analyze.py'),
                            repair_source_sha256=sha(M/'analysis_repair_002/analyze.py'),repeated_physical_branches=0,new_training_updates=0,
                            coordinator_training_repair_not_requested=True))
append(S/'agent_checks.jsonl',record)
(S/'research_progress.json').write_text(json.dumps(record,indent=2,allow_nan=False),encoding='utf-8')
print(json.dumps({k:v for k,v in record.items() if k not in ['primary','summaries']},indent=2))
