import runtime
import argparse
from contextlib import nullcontext
import json
import random
import sys
from pathlib import Path
import imageio.v2 as imageio
import numpy as np
import torch
from robomimic.utils.file_utils import policy_from_checkpoint, env_from_checkpoint
import video_views
from robustness import CONDITIONS, Intervention, refresh_observation
from task_metrics import StackProgress

torch.set_num_threads(4)
parser = argparse.ArgumentParser()
parser.add_argument('checkpoint', type=Path)
parser.add_argument('method')
parser.add_argument('--output-root', type=Path, default=runtime.ROOT / 'experiments/square')
parser.add_argument('--episodes', type=int, default=20)
parser.add_argument('--horizon', type=int, default=400)
parser.add_argument('--seed', type=int, default=6000)
parser.add_argument('--layout', choices=['collage','single'], default='collage')
parser.add_argument('--post-roll-seconds', type=float, default=2.0)
parser.add_argument('--condition', choices=list(CONDITIONS), default='nominal')
parser.add_argument('--video-episodes', type=int, default=None)
args = parser.parse_args()
assert args.episodes > 0 and args.horizon > 0 and args.post_roll_seconds >= 0
assert args.video_episodes is None or args.video_episodes >= 0
checkpoint, method = args.checkpoint, args.method
EXP = args.output_root.resolve()
videos = EXP / 'videos' / method
videos.mkdir(parents=True, exist_ok=True)
policy, ckpt = policy_from_checkpoint(ckpt_path=str(checkpoint))
env, _ = env_from_checkpoint(ckpt_dict=ckpt, render=False, render_offscreen=True)
rollouts = []
for episode in range(args.episodes):
    seed = args.seed + episode
    random.seed(seed); np.random.seed(seed); torch.manual_seed(seed)
    policy.start_episode()
    obs = env.reset()
    obs = env.reset_to(env.get_state())
    intervention = Intervention(env,args.condition,seed)
    intervention.apply()
    obs = refresh_observation(env)
    if args.layout == 'collage':
        video_views.setup_cameras(env)
    total, success = 0.0, False
    record_video = args.video_episodes is None or episode < args.video_episodes
    video = videos / f'rollout_{episode:02d}.mp4' if record_video else None
    stable_tail, dropped = True, False
    progress = StackProgress(env.base_env) if hasattr(env.base_env,'cube_ids') else None
    with (imageio.get_writer(str(video), fps=20) if record_video else nullcontext()) as writer:
        for step in range(args.horizon):
            with torch.no_grad():
                action = policy(ob=intervention.observation(obs))
            action = intervention.action(action,step)
            obs, reward, done, _ = env.step(action)
            intervention.clear_force()
            total += float(reward)
            if progress is not None: progress.update()
            success = bool(env.is_success()['task'])
            dropped |= any(env.base_env.sim.data.body_xpos[i][2] < env.base_env.table_offset[2]-.05
                           for i in intervention.body_ids)
            if record_video and step % 5 == 0:
                image = (video_views.frame(env) if args.layout == 'collage' else
                    env.render(mode='rgb_array',height=256,width=256,camera_name='agentview'))
                writer.append_data(image)
            if done or success:
                break
        measured_length = step + 1
        # Real simulation continuation after measurement ends; never add to scores.
        tail_steps = int(round(args.post_roll_seconds * env.base_env.control_freq))
        tail_frames = int(round(args.post_roll_seconds * 20))
        frames_written = 0
        for tail_step in range(tail_steps):
            with torch.no_grad():
                action = policy(ob=intervention.observation(obs))
            obs, _, _, _ = env.step(action)
            stable_tail &= bool(env.is_success()['task'])
            dropped |= any(env.base_env.sim.data.body_xpos[i][2] < env.base_env.table_offset[2]-.05
                           for i in intervention.body_ids)
            desired = ((tail_step + 1) * tail_frames) // tail_steps
            if record_video and desired > frames_written:
                image = (video_views.frame(env) if args.layout == 'collage' else
                    env.render(mode='rgb_array',height=256,width=256,camera_name='agentview'))
                while frames_written < desired:
                    writer.append_data(image)
                    frames_written += 1
        success_after_tail = bool(env.is_success()['task'])
    result = {'seed':seed,'success':success,'return':total,'length':measured_length,
        'success_after_video_tail':success_after_tail,
        'sustained_success':bool(success and stable_tail and success_after_tail),
        'object_fell_below_table':bool(dropped), 'intervention':intervention.audit,
        'video_tail_seconds':args.post_roll_seconds,'video':str(video) if video else None}
    if progress is not None: result['stack_progress'] = progress.result()
    rollouts.append(result)
    print(json.dumps(result), flush=True)
result = {'algorithm':method,'checkpoint':str(checkpoint),'episodes':args.episodes,
    'horizon':args.horizon,
    'video_layout':args.layout, 'seed_start':args.seed,
    'video_tail_seconds':args.post_roll_seconds,
    'condition':args.condition, 'condition_parameters':CONDITIONS[args.condition],
    'sustained_success_rate':float(np.mean([r['sustained_success'] for r in rollouts])),
    'object_drop_rate':float(np.mean([r['object_fell_below_table'] for r in rollouts])),
    'successes':sum(r['success'] for r in rollouts),
    'success_rate':float(np.mean([r['success'] for r in rollouts])),
    'avg_return':float(np.mean([r['return'] for r in rollouts])),
    'avg_episode_length':float(np.mean([r['length'] for r in rollouts])), 'rollouts':rollouts}
out = EXP / 'evaluation' / method
out.mkdir(parents=True, exist_ok=True)
(out / 'evaluation_results.json').write_text(json.dumps(result,indent=2))
# Keep all 20 videos: every observed success is retained automatically.
print('EVALUATION_COMPLETED', flush=True)
