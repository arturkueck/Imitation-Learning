"""Seal diagnosis configuration/source provenance before long evaluation starts."""
import hashlib,json,shutil
import difflib
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
assert not (OUT/'source_hashes.json').exists()

def digest(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for b in iter(lambda:f.read(1024*1024),b''):h.update(b)
    return h.hexdigest()

p=OUT/'protocol.json';protocol=json.loads(p.read_text())
shutil.copy2(p,OUT/'protocol_prefix_replay_v1.json')
protocol['restore']='original XML/state[0]; replay prefix for controller/gripper memory; restore exact state[k]; force-update/reset achieved OSC goal; exact stored obs[k-1,k] installed in wrapper; subsequent frames live'
protocol['physical_restore_exact_required']=True
protocol['max_restored_observation_position_error_m']=.002
protocol['restore_refinement_reason']='Pure prefix replay exceeded 2mm tolerance at demo_22 after-grasp (EEF 4.884mm). Technical v1/v2 attempts retained; all final anchors must pass Expert controls under v3.'
p.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
before=ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/source_snapshot/praxis/upstream/robomimic/robomimic/algo/diffusion_policy.py'
after=ROOT/'praxis/upstream/robomimic/robomimic/algo/diffusion_policy.py'
patch=''.join(difflib.unified_diff(before.read_text().splitlines(True),after.read_text().splitlines(True),fromfile='a/praxis/upstream/robomimic/robomimic/algo/diffusion_policy.py',tofile='b/praxis/upstream/robomimic/robomimic/algo/diffusion_policy.py'))
(OUT/'unet_config_fix.patch').write_text(patch,encoding='utf-8')
shutil.copy2(before,OUT/'unet_before_config_fix.py')

source=[p for p in OUT.glob('*.py')]
source.extend([ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/normalization_stats.json',ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/C/diffusion/seed_1/config.json',ROOT/'experiments/stack_diagnostics/stack_normalization_20261001/C/direct/seed_1/config.json'])
for directory in ('experiments/stack_diagnostics/stack_followup_20261001/scripts','experiments/stack_diagnostics/stack_normalization_20261001/scripts','experiments/baselines/square/scripts','praxis/src/task_extensions'):
    source.extend((ROOT/directory).glob('*.py'))
for name in ('algo/diffusion_policy.py','algo/algo.py','models/diffusion_policy_nets.py','models/obs_nets.py','utils/dataset.py','utils/obs_utils.py','utils/tensor_utils.py','utils/file_utils.py','utils/env_utils.py','utils/torch_utils.py','utils/train_utils.py','envs/wrappers.py','envs/env_robosuite.py','scripts/train.py'):
    source.append(ROOT/'praxis/upstream/robomimic/robomimic'/name)
for name in ('controllers/parts/controller.py','controllers/parts/arm/osc.py','models/grippers/panda_gripper.py','robots/fixed_base_robot.py'):
    source.append(ROOT/'praxis/upstream/robosuite/robosuite'/name)
source.extend(OUT.glob('*.json'));source.extend(OUT.glob('*.md'))
records={}
for p in sorted(set(source)):
    if not p.is_file():continue
    relative=p.relative_to(ROOT);records[str(relative)]=digest(p)
    dest=OUT/'source_snapshot'/relative;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
(OUT/'source_hashes.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
print(json.dumps(dict(sealed_files=len(records),protocol_sha256=digest(OUT/'protocol.json')),indent=2))
