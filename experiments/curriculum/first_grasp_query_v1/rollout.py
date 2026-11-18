"""Measurement, candidate logging and paired simulation for the first grasp."""
import hashlib

import numpy as np
import torch


def rollout(h, env, policy_model, seed, plan, out, deadline, *, prefix=False, capture=False,
            completion_head=None, timeout=False):
    base = h.libraries()[0]
    ctl = base.backend()
    obs, initial, _ = h.reset(env, seed)
    seq = ctl.GuardedSequencer(policy_model, 3, ctl.Clearance(env))
    seq.policy = h.validation.adapter.make_policy(base, ctl.native.historical, policy_model,
        plan["threshold"], lambda: seq.stage, 17)
    candidates = []
    first_lift = None
    tail = 0
    transition_frame = None
    fallback = False
    limit = plan["prefix_horizon"] if prefix else plan["horizon"]
    for frame in range(limit):
        base.check_stop(out, deadline)
        stage, phase, steps = seq.stage, seq.policy.phase, seq.policy.steps
        first_descent = stage == 1 and phase == 1 and not seq.retreat
        pos = [env.sim.data.body_xpos[i].copy() for i in env.cube_ids]
        if prefix and phase == 3:
            if bool(env._check_grasp(env.robots[0].gripper, env.cubes[1].contact_geoms)):
                first_lift = frame
            break
        anchor = (pos[stage] if phase < 4 else pos[stage - 1]) if seq.policy.anchor is None else seq.policy.anchor.copy()
        # Preserve the existing action and its exact input contract.
        with torch.no_grad():
            action, _, probability = seq.policy.action(obs, pos[stage - 1], pos[stage])
            x = seq.policy.last_x.copy()
            if first_descent and completion_head is not None:
                logit = completion_head(torch.as_tensor(x[None], device=next(completion_head.parameters()).device))[0, 4]
                if float(logit.sigmoid()) >= plan["threshold"]:
                    seq.policy.phase, seq.policy.steps, seq.policy.anchor = 2, 0, None
                else:
                    seq.policy.phase, seq.policy.steps, seq.policy.anchor = 1, steps + 1, anchor
        if first_descent:
            if capture and steps % plan["candidate_stride"] == 0:
                distance = float(np.linalg.norm(.1 * x[:3] - np.asarray([0., 0., .003])))
                candidates.append(dict(frame=frame, steps=steps, x=x.tolist(), probability=probability, distance_m=distance,
                    target=(anchor + np.asarray([0., 0., .003])).tolist(), eef=obs["robot0_eef_pos"].tolist()))
            if timeout and seq.policy.phase == 1 and steps >= 100:
                seq.policy.phase, seq.policy.steps, seq.policy.anchor = 2, 0, None
                fallback = True
            if seq.policy.phase == 2:
                transition_frame = frame
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        if prefix:
            continue
        valid = [ctl.native.historical.old.prefix_valid(env, k)
            and not any(ctl.native.finger_contact(env, cube) for cube in env.cubes[:k]) for k in (2, 3)]
        seq.advance(valid[stage - 1], env.sim.data.body_xpos[env.cube_ids[stage]])
        tail = tail + 1 if valid[-1] else 0
        if tail >= plan["stable_frames"] or seq.timed_out:
            break
    return dict(seed=seed, initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
        frames=frame + 1, success=tail >= plan["stable_frames"], stable_tail=tail,
        stage=seq.stage, phase=seq.policy.phase, first_transition=transition_frame, timeout_used=fallback,
        difficulty_frames=first_lift if first_lift is not None else limit + 1,
        difficulty_censored=first_lift is None), candidates


def expert_label(candidate):
    """The fixed StackExpert phase-1 completion predicate, replayed on a query."""
    error = np.linalg.norm(np.asarray(candidate["target"]) - np.asarray(candidate["eef"]))
    return int(candidate["steps"] + 1 >= 5 and error < .006)


def is_priority(candidate, threshold=.8):
    return candidate["steps"] >= 5 and candidate["distance_m"] <= .012 and candidate["probability"] < threshold


def query_indices(candidates, rng):
    """Select both arm assignments before evaluating any label."""
    if len(candidates) < 4:
        return None
    last = len(candidates) - 1
    inner = list(range(1, last))
    random_indices = rng.choice(inner, size=2, replace=False).tolist()
    # Near the target with low confidence first. Prefer the later frame for ties.
    targeted_indices = sorted(inner, key=lambda index: (
        not is_priority(candidates[index]),
        candidates[index]["distance_m"] + .006 * candidates[index]["probability"],
        -candidates[index]["steps"],
    ))[:2]
    return {"random": [0, last, *random_indices], "targeted": [0, last, *targeted_indices]}
