"""Evaluate a trained Lift policy with paired, reproducible object offsets."""

import argparse
import json
from pathlib import Path

import numpy as np
import torch

import robomimic_ext  # noqa: F401 - registers custom checkpoints
from robomimic.utils.file_utils import env_from_checkpoint, policy_from_checkpoint


def evaluate(checkpoint, episodes, horizon, seed, offset, action_impulse_x=0.0, impulse_step=20):
    policy, ckpt = policy_from_checkpoint(ckpt_path=str(checkpoint), verbose=False)
    env, _ = env_from_checkpoint(ckpt_dict=ckpt, render=False, render_offscreen=False)
    results = []
    for episode in range(episodes):
        episode_seed = seed + episode
        np.random.seed(episode_seed)
        torch.manual_seed(episode_seed)
        policy.start_episode()
        obs = env.reset()
        if offset != (0.0, 0.0):
            joint = env.env.cube.joints[0]
            cube_qpos = env.env.sim.data.get_joint_qpos(joint).copy()
            cube_qpos[:2] += offset
            env.env.sim.data.set_joint_qpos(joint, cube_qpos)
            env.env.sim.forward()
            obs = env.get_observation()

        initial_cube_qpos = env.env.sim.data.get_joint_qpos(env.env.cube.joints[0]).copy()
        initial_eef_pos = np.array(obs["robot0_eef_pos"], copy=True)

        success = False
        steps = horizon
        for step in range(horizon):
            action = policy(ob=obs)
            if step == impulse_step and action_impulse_x != 0.0:
                action = np.array(action, copy=True)
                action[0] = np.clip(action[0] + action_impulse_x, -1.0, 1.0)
            obs, _, _, _ = env.step(action)
            if bool(env.is_success()["task"]):
                success = True
                steps = step + 1
                break
        results.append({
            "seed": episode_seed,
            "success": success,
            "steps": steps,
            "initial_cube_qpos": initial_cube_qpos.tolist(),
            "initial_eef_pos": initial_eef_pos.tolist(),
        })
    return {
        "checkpoint": str(checkpoint),
        "algo": ckpt["algo_name"],
        "episodes": episodes,
        "horizon": horizon,
        "object_offset_xy_m": list(offset),
        "action_impulse_x": action_impulse_x,
        "impulse_step": impulse_step if action_impulse_x != 0.0 else None,
        "successes": sum(item["success"] for item in results),
        "success_rate": sum(item["success"] for item in results) / episodes,
        "mean_steps": float(np.mean([item["steps"] for item in results])),
        "rollouts": results,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--horizon", type=int, default=400)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--offset-x", type=float, default=0.0)
    parser.add_argument("--offset-y", type=float, default=0.0)
    parser.add_argument("--action-impulse-x", type=float, default=0.0)
    parser.add_argument("--impulse-step", type=int, default=20)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = evaluate(
        args.checkpoint.resolve(), args.episodes, args.horizon, args.seed,
        (args.offset_x, args.offset_y), args.action_impulse_x, args.impulse_step,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key != "rollouts"}, indent=2))


if __name__ == "__main__":
    main()
