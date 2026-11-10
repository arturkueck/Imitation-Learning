"""Hidden independent WMI entry point, registered before importing ML libraries."""
from pathlib import Path
import sys,runpy,site,os
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
site.addsitedir(str(ROOT/'praxis/.venv/Lib/site-packages'))
sys.path.insert(0,str(HERE));sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import independence,save
mode=sys.argv[1]
if mode not in ['smoke','smoke2','smokerepair','production']:raise ValueError('Invalid mode')
out=HERE/'run_001'/({'smoke':'followup_smoke_001','smoke2':'followup_smoke_002','smokerepair':'followup_smoke_repair001'}.get(mode,'followup_001'))
out.mkdir(exist_ok=True)
with (out/'worker.log').open('x',encoding='utf-8',buffering=1) as stream:
    sys.stdout=stream;sys.stderr=stream
    proof=independence();save(out/'bootstrap_independence.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Job-bound followup bootstrap refused')
    from deadline_guard import register
    save(out/'worker_identity.json',register(os.getpid(),'followup_'+mode,HERE/'run_001'))
    sys.argv=[str(HERE/'followup_v3.py')]+(['--smoke'] if mode.startswith('smoke') else [])+(['--second'] if mode=='smoke2' else [])+(['--repair'] if mode=='smokerepair' else [])
    runpy.run_path(str(HERE/'followup_v3.py'),run_name='__main__')
