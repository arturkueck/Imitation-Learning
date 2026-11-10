"""Record successful expert rollouts in robomimic HDF5, with trajectory split."""
import argparse
import importlib
import json
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT / 'experiments/baselines/square/scripts'))
import runtime
import h5py
import numpy as np
from robomimic.utils.env_utils import create_env_for_data_processing

parser = argparse.ArgumentParser()
parser.add_argument('--task',choices=['stack_two','stack_four','cube_handover'],required=True)
parser.add_argument('--expert',required=True,help='module:function creating a callable expert from env')
parser.add_argument('--demos',type=int,default=200)
parser.add_argument('--attempts',type=int,default=600)
parser.add_argument('--seed',type=int,default=100)
parser.add_argument('--horizon',type=int,default=1000)
parser.add_argument('--output',type=Path,help='Alternate output for technical tests')
args = parser.parse_args()
assert args.demos >= 2 and args.attempts >= args.demos
folder = ROOT / 'experiments/baselines/additional_tasks' / args.task
info = json.loads((folder / 'task_info.json').read_text())
path = args.output.resolve() if args.output else Path(info['dataset'])
path.parent.mkdir(parents=True,exist_ok=True)
if path.exists(): raise RuntimeError('Dataset exists; will not overwrite it')
env = create_env_for_data_processing(info['environment'],camera_names=['agentview'],
    camera_height=64,camera_width=64,reward_shaping=False)
module, name = args.expert.split(':')
factory = getattr(importlib.import_module(module),name)
report = {'task':args.task,'expert':args.expert,'attempts':[],'accepted':0}
report['ready_for_baseline'] = False
report['dataset'] = str(path)
with h5py.File(path,'w') as f:
    data = f.create_group('data'); data.attrs['env_args'] = json.dumps(env.serialize())
    total = 0
    for attempt in range(args.attempts):
        np.random.seed(args.seed+attempt)
        obs = env.reset(); initial = env.get_state(); expert = factory(env)
        records = {'actions':[],'states':[],'rewards':[],'dones':[]}
        observations = {k:[] for k in info['camera_keys']+info['proprioception_keys']+info.get('object_keys',[])}
        for step in range(args.horizon):
            action = np.asarray(expert(obs),dtype=np.float32)
            assert action.shape == (info['action_dimension'],) and np.isfinite(action).all()
            state = env.get_state()['states']
            for key in observations: observations[key].append(np.array(obs[key],copy=True))
            obs,reward,done,_ = env.step(action)
            records['actions'].append(action); records['states'].append(state)
            records['rewards'].append(reward); records['dones'].append(done)
            if env.is_success()['task']: break
        success = bool(env.is_success()['task'])
        report['attempts'].append({'seed':args.seed+attempt,'success':success,'length':step+1})
        print(json.dumps(report['attempts'][-1]),flush=True)
        if success:
            group = data.create_group(f"demo_{report['accepted']}")
            for key,values in records.items(): group.create_dataset(key,data=np.array(values))
            for key,values in observations.items():
                group.create_dataset('obs/'+key,data=np.array(values),compression='gzip')
            group.attrs['model_file'] = initial['model']
            if 'ep_meta' in initial: group.attrs['ep_meta'] = initial['ep_meta']
            group.attrs['num_samples'] = step+1
            total += step+1; report['accepted'] += 1
            f.flush()
        if args.output is None:
            (folder / 'collection_report.json').write_text(json.dumps(report,indent=2))
        if report['accepted'] == args.demos: break
    data.attrs['total'] = total
    if report['accepted'] >= 2:
        names = np.array([f'demo_{i}'.encode() for i in range(report['accepted'])])
        indices = np.random.default_rng(1).permutation(len(names))
        valid_count = max(1,round(.1*len(names)))
        masks = f.create_group('mask')
        masks.create_dataset('valid',data=names[indices[:valid_count]])
        masks.create_dataset('train',data=names[indices[valid_count:]])
report['ready_for_baseline'] = report['accepted'] == args.demos
report['dataset'] = str(path)
report_path = path.with_suffix('.collection_report.json')
report_path.write_text(json.dumps(report,indent=2))
if args.output is None:
    (folder / 'collection_report.json').write_text(json.dumps(report,indent=2))
if not report['ready_for_baseline']:
    raise RuntimeError(f"Only {report['accepted']}/{args.demos} demos succeeded; dataset is incomplete, inspect report")
