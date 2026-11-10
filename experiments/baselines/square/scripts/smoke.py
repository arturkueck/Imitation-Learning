import runtime
import json
import subprocess
import sys
from pathlib import Path
import torch
import imageio.v2 as imageio
import numpy as np
from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint

EXP = runtime.ROOT / 'experiments/baselines/square'
SMOKE = EXP / 'smoke'
SMOKE.mkdir(exist_ok=True)
for method in ('bc','bc_rnn','bc_transformer'):
    cfg = json.loads((EXP / method / 'config.json').read_text())
    cfg['train'].update(num_epochs=1,output_dir=str(SMOKE / method))
    cfg['experiment'].update(epoch_every_n_steps=3,validation_epoch_every_n_steps=2)
    cfg['experiment']['save']['every_n_epochs'] = 1
    path = SMOKE / f'{method}.json'
    path.write_text(json.dumps(cfg,indent=2))
    with (SMOKE / f'{method}.log').open('w') as log:
        subprocess.run([sys.executable,'-u',str(EXP / 'scripts/train_model.py'),str(path)],
            stdout=log,stderr=subprocess.STDOUT,check=True)
    checkpoint = next((SMOKE / method).glob('**/models/*.pth'))
    policy, ckpt = policy_from_checkpoint(ckpt_path=str(checkpoint))
    env, _ = env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=True)
    policy.start_episode()
    obs = env.reset()
    obs = env.reset_to(env.get_state())
    with imageio.get_writer(str(SMOKE / f'{method}.mp4'),fps=20) as writer:
        for _ in range(3):
            action = policy(ob=obs)
            assert action.shape == (7,) and np.isfinite(action).all()
            obs, _, _, _ = env.step(action)
            writer.append_data(env.render(mode='rgb_array',height=256,width=256,camera_name='agentview'))
    del env, policy, ckpt
    torch.cuda.empty_cache()
    print(f'SMOKE_OK {method}: 3 train batches, validation, checkpoint reload, 3 rollout steps, MP4',flush=True)
