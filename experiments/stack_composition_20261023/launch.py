from pathlib import Path
import subprocess,sys,json,os,hashlib,shutil
OUT=Path(__file__).resolve().parent
if (OUT/'launch.json').exists():raise RuntimeError('Existing launch; refusing duplicate')
assert (OUT/'checks.json').exists() and (OUT/'smoke_result.json').exists()
sources={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.py')}
(OUT/'source_hashes.json').write_text(json.dumps(sources,indent=2))
snapshot=OUT/'source_snapshot';snapshot.mkdir(exist_ok=False)
for p in OUT.glob('*.py'):shutil.copy2(p,snapshot/p.name)
root=OUT.parents[1]
for p in [root/'praxis/src/task_extensions/environments.py',root/'praxis/src/task_extensions/stack_expert.py',root/'experiments/square/scripts/runtime.py',root/'experiments/additional_tasks/stack_two/task_info.json']:
    shutil.copy2(p,snapshot/p.name)
(OUT/'requirements.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze'],text=True))
with (OUT/'supervisor.log').open('ab',buffering=0) as log:
    p=subprocess.Popen([sys.executable,'-u',str(OUT/'supervisor.py')],stdin=subprocess.DEVNULL,stdout=log,stderr=log,
        close_fds=True,creationflags=subprocess.DETACHED_PROCESS|subprocess.CREATE_NEW_PROCESS_GROUP|subprocess.CREATE_BREAKAWAY_FROM_JOB)
info=dict(pid=p.pid,python=sys.executable,supervisor=str(OUT/'supervisor.py'))
(OUT/'launch.json').write_text(json.dumps(info,indent=2));print(json.dumps(info))
