"""Prepare a clean retry without changing the task or learning parameters."""
import json,shutil,hashlib,ast
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3];OUT=Path(__file__).resolve().parent
OLD=ROOT/'experiments/stack_diagnostics/diffusion_sanity_lift_transport_20261002'
oldname=OLD.name;newname=OUT.name
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')
assert not (OUT/'config.json').exists(),'Retry already prepared'
for name in ('early_demonstrations.hdf5','normalization_stats.json','prefix_manifest.json','environment_frozen.txt','provenance.json'):
    shutil.copy2(OLD/name,OUT/name)
shutil.copytree(OLD/'source_snapshot',OUT/'source_snapshot')
(OUT/'scripts').mkdir()
for p in (OLD/'scripts').glob('*.py'):
    (OUT/'scripts'/p.name).write_text(p.read_text(encoding='utf-8').replace(oldname,newname),encoding='utf-8')
for name in ('config.json','protocol.json','start_command.txt','METRIKEN.md','start.ps1'):
    (OUT/name).write_text((OLD/name).read_text(encoding='utf-8').replace(oldname,newname),encoding='utf-8')
dest=OUT/'C/diffusion/seed_1';dest.mkdir(parents=True)
shutil.copy2(OUT/'config.json',dest/'config.json')
# Replace cached Windows console streams with actual text files. Do not use dup2.
p=OUT/'scripts/run.py';s=p.read_text(encoding='utf-8')
old="log=(OUT/'run.log').open('a',encoding='utf-8',buffering=1)\nos.dup2(log.fileno(),1);os.dup2(log.fileno(),2)"
assert old in s
new="""smoke='--logging-self-test' in sys.argv
log=(OUT/('logging_smoke.log' if smoke else 'run.log')).open('a',encoding='utf-8',buffering=1)
sys.stdout=log;sys.stderr=log
if smoke:
    print('PARENT_STDOUT_OK',flush=True)
    subprocess.run([sys.executable,'-u','-c',"import sys; print('CHILD_STDOUT_OK'); print('CHILD_STDERR_OK',file=sys.stderr)"],stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,check=True)
    log.flush()
    (OUT/'logging_smoke_complete.json').write_text(json.dumps({'passed':True,'no_training':True,'pid':os.getpid()}),encoding='utf-8')
    sys.exit(0)"""
s=s.replace(old,new).replace('cwd=ROOT,stdout=log','cwd=ROOT,stdin=subprocess.DEVNULL,stdout=log')
s=s.replace("write(OUT/'failed.json',dict(state='FAILED',cause=traceback.format_exc(),finished_unix=time.time()));traceback.print_exc();sys.exit(1)","write(OUT/'failed.json',dict(state='FAILED',cause=traceback.format_exc(),finished_unix=time.time()));write(OUT/'worker_status.json',dict(state='FAILED',pid=os.getpid()));traceback.print_exc();sys.exit(1)")
p.write_text(s,encoding='utf-8')
p=OUT/'start.ps1';s=p.read_text(encoding='utf-8')
s=s.replace('-WindowStyle Hidden -PassThru','-WindowStyle Hidden -RedirectStandardOutput (Join-Path $PSScriptRoot \'startup_stdout.log\') -RedirectStandardError (Join-Path $PSScriptRoot \'startup_stderr.log\') -PassThru')
p.write_text(s,encoding='utf-8')
source=ROOT/'experiments/stack_diagnostics/stack_replication_20261001/FINAL_EXPERIMENT_SYNTHESIS.md'
shutil.copy2(source,OUT/'source_snapshot/FINAL_EXPERIMENT_SYNTHESIS.md')
write(OUT/'retry_provenance.json',dict(previous_failed_experiment=str(OLD),previous_failure_sha256=sha(OLD/'failed.json'),synthesis_sha256=sha(source),training_was_never_started=True,prefix_dataset_unchanged=sha(OUT/'early_demonstrations.hdf5')==sha(OLD/'early_demonstrations.hdf5'),normalization_unchanged=sha(OUT/'normalization_stats.json')==sha(OLD/'normalization_stats.json'),changes=['Output paths/date only','Replace Windows console stream redirection with Python file streams','Explicit stdin DEVNULL and file-backed child stdout/stderr','FAILED status on worker exceptions']))
for p in (OUT/'scripts').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
print('RETRY PREPARED; NOT STARTED')
