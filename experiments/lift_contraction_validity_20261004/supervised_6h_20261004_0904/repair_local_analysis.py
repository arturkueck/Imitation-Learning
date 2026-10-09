"""Preserve the frozen analysis and correct a metadata key in a fresh folder."""
import json,hashlib,time,py_compile
from pathlib import Path
from datetime import datetime,timezone,timedelta
S=Path(__file__).resolve().parent;O=S/'local_response_001';N=O/'analysis_repair_001';N.mkdir()
source=(O/'analyze_local.py').read_text(encoding='utf-8')
assert source.count("audit['passed']")==2
source=source.replace("O=Path(__file__).resolve().parent","O=Path(__file__).resolve().parent.parent").replace("audit['passed']","audit['eligible']")
with (N/'analyze_local.py').open('x',encoding='utf-8') as f:f.write(source)
py_compile.compile(str(N/'analyze_local.py'),doraise=True)
now=time.time();d=datetime.fromtimestamp(now,timezone.utc)
record=dict(actor='agent',event='local_analysis_preexecution_repair',unix=now,utc=d.isoformat(),berlin=d.astimezone(timezone(timedelta(hours=2))).isoformat(),
            reason='Inspection caught wrong metadata key before analysis execution: independent physical audit exposes eligible, not passed. Frozen original analysis retained; new analysis uses verified eligible field. No physical or numerical gate changed.',
            original_source_sha256=hashlib.sha256((O/'analyze_local.py').read_bytes()).hexdigest(),
            repair_source=str(N/'analyze_local.py'),repair_source_sha256=hashlib.sha256((N/'analyze_local.py').read_bytes()).hexdigest(),
            original_analysis_executed=False,primary_simulator_rerun=False,new_policy_updates=0,coordinator_training_repair_not_requested=True)
with (N/'REPAIR.json').open('x',encoding='utf-8') as f:json.dump(record,f,indent=2)
with (S/'repairs.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record)+'\n')
print(json.dumps(record,indent=2))
