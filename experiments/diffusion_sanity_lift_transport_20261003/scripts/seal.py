"""Freeze the prepared run's relevant sources and configuration before launch."""
import ast,shutil,json
from common import *
def main():
    assert read(OUT/'preflight.json')['passed'] and not (OUT/'worker_started.json').exists()
    for p in (OUT/'scripts').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    provenance=read(OUT/'provenance.json');current={}
    provenance['config_sha256']=digest(OUT/'config.json')
    provenance['prefix_dataset_sha256']=digest(OUT/'early_demonstrations.hdf5')
    upstream=ROOT/'praxis/upstream/robomimic/robomimic'
    names=('scripts/train.py','algo/algo.py','algo/diffusion_policy.py','utils/dataset.py','utils/obs_utils.py','utils/torch_utils.py','utils/train_utils.py','models/diffusion_policy_nets.py')
    for i,name in enumerate(names):
        p=upstream/name;current[str(p.relative_to(ROOT))]=digest(p)
        shutil.copy2(p,OUT/'source_snapshot/dependencies'/f'live_{i}_{p.name}')
    provenance['live_upstream_source_hashes']=current
    write(OUT/'provenance.json',provenance)
    shutil.copy2(ROOT/'experiments/stack_normalization_20261001/environment_frozen.txt',OUT/'environment_frozen.txt')
    (OUT/'run.log').touch()
    records={str(p.relative_to(OUT)):dict(sha256=digest(p),bytes=p.stat().st_size) for p in OUT.rglob('*') if p.is_file() and p.name not in ('prepared_hashes.json','run.log') and p.suffix not in ('.pyc','.tmp')}
    write(OUT/'prepared_hashes.json',dict(algorithm='SHA-256',files=records))
    print(json.dumps(dict(prepared_files=len(records),sealed=True,training_runs_planned=1,seed=1)))
if __name__=='__main__':main()
