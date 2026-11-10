"""Read-only diagnosis of final policies on the existing nominal seeds."""
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'experiments/square/scripts'))
import runtime
import json, random
import numpy as np
import torch
from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
from robustness import Intervention, refresh_observation
import video_views

torch.set_num_threads(4)
EXP = ROOT / 'experiments/additional_tasks/stack_four'
results = {}
for method in ('bc_rnn', 'bc_transformer'):
    saved = json.loads((EXP / 'evaluation' / method / 'evaluation_results.json').read_text())
    policy, ckpt = policy_from_checkpoint(ckpt_path=saved['checkpoint'])
    env, _ = env_from_checkpoint(ckpt_dict=ckpt, render=False, render_offscreen=True)
    rows = []
    for seed in range(6000, 6003):
        random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
        policy.start_episode()
        env.reset(); env.reset_to(env.get_state())
        intervention = Intervention(env, 'nominal', seed); intervention.apply()
        obs = refresh_observation(env); video_views.setup_cameras(env)
        raw = env.base_env
        grasps = np.zeros(4, dtype=int); lifted = np.zeros(4, dtype=int)
        pairs = np.zeros(3, dtype=int); max_height = 1; full_valid = 0
        snapshots = []
        for step in range(1000):
            with torch.no_grad():
                action = policy(ob=obs)
            obs, _, _, _ = env.step(action)
            pos = np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids])
            grasp = [bool(raw._check_grasp(raw.robots[0].gripper, c)) for c in raw.cubes]
            grasps += grasp
            lifted += pos[:, 2] > raw.table_offset[2] + .08
            valid_pairs = []
            for i in range(3):
                valid_pairs.append(bool(np.linalg.norm(pos[i+1,:2]-pos[i,:2]) < .009
                    and abs(pos[i+1,2]-pos[i,2]-.04) < .008
                    and raw.check_contact(raw.cubes[i],raw.cubes[i+1])
                    and not grasp[i] and not grasp[i+1]))
            pairs += valid_pairs
            height = 1
            if abs(pos[0,2]-(raw.table_offset[2]+.02)) < .008:
                for pair in valid_pairs:
                    if not pair: break
                    height += 1
            max_height = max(max_height, height)
            full_valid += raw.tower_is_valid()
            if step % 100 == 99:
                snapshots.append({'step': step+1, 'xyz':pos.round(4).tolist(),
                    'grasp':grasp,'gripper_command':float(action[-1])})
        row = dict(seed=seed, grasp_steps=grasps.tolist(), lifted_steps=lifted.tolist(),
            released_correct_pair_steps=pairs.tolist(), max_ordered_tower_height=max_height,
            full_valid_steps=int(full_valid), snapshots=snapshots)
        rows.append(row)
        print(method, seed, json.dumps({k:v for k,v in row.items() if k!='snapshots'}), flush=True)
    results[method] = rows
    env.base_env.close()
(EXP / 'diagnostics/rollout_diagnosis.json').write_text(json.dumps(results, indent=2))
