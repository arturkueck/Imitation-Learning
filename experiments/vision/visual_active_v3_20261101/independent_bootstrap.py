"""WMI service entry point. Refuse job-bound processes before executing work."""
from pathlib import Path
import sys,runpy
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/vision/visual_overnight_20261101'))
from night import independence,save

mode=sys.argv[1];run=Path(sys.argv[2]).resolve();log=Path(sys.argv[3]).resolve()
if mode not in ['guard','supervise'] or not run.is_relative_to(HERE) or not log.is_relative_to(HERE):raise ValueError('Invalid bootstrap arguments')
with log.open('x',encoding='utf-8',buffering=1) as stream:
    sys.stdout=stream;sys.stderr=stream
    proof=independence();save(HERE/f'{mode}_wmi_proof.json',proof)
    if not proof['query_ok'] or proof['in_job']:raise RuntimeError('Refusing job-bound WMI bootstrap')
    if mode=='guard':
        sys.argv=[str(HERE/'deadline_guard.py'),'guard'];runpy.run_path(str(HERE/'deadline_guard.py'),run_name='__main__')
    else:
        sys.argv=[str(HERE/'train_v3.py'),'supervise',str(run)];runpy.run_path(str(HERE/'train_v3.py'),run_name='__main__')
