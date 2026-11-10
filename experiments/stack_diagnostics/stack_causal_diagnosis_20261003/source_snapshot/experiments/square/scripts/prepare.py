import runtime
import argparse
import hashlib
import json
from pathlib import Path
import h5py
import numpy as np
import torch
from robomimic.utils.file_utils import get_env_metadata_from_dataset
from robomimic.utils.env_utils import create_env_for_data_processing
from robomimic.scripts.dataset_states_to_obs import dataset_states_to_obs

ROOT = runtime.ROOT
EXP = ROOT / 'experiments/square'
SOURCE = ROOT / 'praxis/data/square/ph/low_dim_v15.hdf5'
TARGET = SOURCE.with_name('image_64_v15.hdf5')

if __name__ == '__main__':
    torch.set_num_threads(4)
    if not TARGET.exists():
        env = create_env_for_data_processing(get_env_metadata_from_dataset(str(SOURCE)),
            camera_names=['agentview'], camera_height=64, camera_width=64, reward_shaping=False)
        obs = env.reset()
        env.step(np.zeros(7))
        frame = env.render(mode='rgb_array', height=256, width=256, camera_name='agentview')
        import imageio.v2 as imageio
        imageio.imwrite(EXP / 'render_smoke.png', frame)
        print('RENDER_SMOKE_OK', obs['agentview_image'].shape, flush=True)
        del env
        args = argparse.Namespace(dataset=str(SOURCE), output_name=TARGET.name,
            n=None, shaped=False, camera_names=['agentview'], camera_height=64,
            camera_width=64, depth=False, done_mode=0, copy_rewards=True,
            copy_dones=True, exclude_next_obs=True, compress=True)
        dataset_states_to_obs(args)
    with h5py.File(TARGET) as f:
        demos = list(f['data'])
        demo = f['data'][demos[0]]
        train = [x.decode() for x in f['mask/train'][:]]
        valid = [x.decode() for x in f['mask/valid'][:]]
        assert not set(train) & set(valid)
        assert set(train + valid) == set(demos)
        info = {'task':'Square', 'dataset':str(TARGET), 'source':str(SOURCE),
            'source_sha256':hashlib.file_digest(SOURCE.open('rb'), 'sha256').hexdigest(),
            'demos':len(demos), 'train_demos':train, 'validation_demos':valid,
            'observation_shapes':{k:list(v.shape[1:]) for k,v in demo['obs'].items()},
            'action_dimension':demo['actions'].shape[-1],
            'environment':json.loads(f['data'].attrs['env_args'])}
    (EXP / 'dataset_info.json').write_text(json.dumps(info, indent=2))
    print('DATASET_READY', len(demos), len(train), len(valid), flush=True)
