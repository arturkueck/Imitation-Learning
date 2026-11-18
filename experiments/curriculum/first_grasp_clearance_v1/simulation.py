"""Frozen three-cube rollouts with isolated first-grasp and clearance probes."""
import hashlib
import numpy as np


def digest(state):
    return hashlib.sha256(state.tobytes()).hexdigest()


COLUMNS = [
    "frame", "placement", "phase", "retreat", "steps", "probability",
    "grasp_ready_streak", "forced_grasp", "guard_blocked", "clearance_streak", "withdrawing",
    "phase_after_decision", "event", "pre_xy", "pre_height", "pre_ready",
    "post_xy", "post_height", "post_source_finger", "post_source_held",
    "post_pair_contact", "post_valid_two", "post_valid_three", "valid_tail", "eef_z",
    "command_x", "command_y", "command_z", "command_gripper",
]


def run_episode(runtime, env, model, seed, arm, plan, out, deadline):
    base, torch, _ = runtime.h.libraries()
    ctl = base.backend()
    obs, initial, z = runtime.h.reset(env, seed)
    positions = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    initial_features = {
        "eef_to_first_source_m": float(np.linalg.norm(obs["robot0_eef_pos"] - positions[1])),
        "first_transport_xy_m": float(np.linalg.norm(positions[1, :2] - positions[0, :2])),
        "first_source_radial_xy_m": float(np.linalg.norm(positions[1, :2])),
    }
    seq = ctl.GuardedSequencer(model, 3, ctl.Clearance(env))
    seq.policy = runtime.h.validation.adapter.make_policy(
        base, ctl.native.historical, model, .8, lambda: seq.stage, 17
    )
    history = hashlib.sha256(initial.tobytes())
    grasp, clearance = plan["grasp"], plan["clearance"]
    release_mode = arm in ("guarded_feedback", "withdraw")
    trace, prefixes = [], {}
    tail, adapted, ready_streak, place_streak, contact_streak = 0, 0, 0, 0, 0
    first_seen, second_lift = False, None
    first_change, withdrawal, feedback = None, None, None
    withdrawal_goal = None
    screen_eligible = False
    release_entered = False
    for frame in range(plan["episode_horizon"]):
        base.check_stop(out, deadline)
        stage, phase, retreat = seq.stage, seq.policy.phase, seq.retreat
        first_grasp = stage == 1 and phase == 1 and not retreat
        final_place = stage == 2 and phase == 5 and not retreat
        final_release = stage == 2 and phase == 6 and not retreat
        release_entered |= final_release
        model.active = stage == 2 and phase == 0 and not retreat
        adapted += int(model.active)
        pos = np.asarray([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        steps = seq.policy.steps
        anchor = seq.policy.anchor
        if anchor is None:
            anchor = pos[stage] if phase < 4 else pos[stage - 1]
        if stage == 2 and phase == 3 and not retreat and second_lift is None:
            second_lift = dict(frame=frame, held=bool(env._check_grasp(env.robots[0].gripper, env.cubes[2].contact_geoms)))
        physical = runtime.engine.placement_features(env, stage, ctl, np) if final_place or final_release else [-1] * 6
        ready = bool((final_place or final_release) and runtime.engine.readiness(physical, plan["placement_readiness"]))
        place_streak = place_streak + 1 if final_place and ready else 0
        with torch.no_grad():
            action, _, probability = seq.policy.action(obs, pos[stage - 1], pos[stage])
        # The 3 coordinates are exactly the existing Greifer-to-anchor features.
        at_goal = first_grasp and steps + 1 >= 5 and np.linalg.norm(
            .1 * seq.policy.last_x[:3] - np.asarray(grasp["goal_offset_m"])
        ) < grasp["goal_distance_max_m"]
        ready_streak = ready_streak + 1 if at_goal else 0
        would_advance = seq.policy.phase != phase
        eligible = first_grasp and runtime.grasp_decision("grasp_ready", steps, would_advance, ready_streak, grasp)
        screen_eligible |= bool(eligible)
        forced = first_grasp and runtime.grasp_decision(arm, steps, would_advance, ready_streak, grasp)
        would_block = bool(final_place and would_advance and (
            place_streak < plan["placement_readiness"]["consecutive_frames"] or
            steps + 1 < plan["placement_readiness"]["minimum_phase_frames"]
        ))
        prefix = None
        is_release_motion = release_mode and final_release
        if first_grasp or final_place or final_release:
            prefix = dict(frame=frame, history_sha256=history.hexdigest(),
                          state_sha256=digest(env.sim.get_state().flatten()))
        if arm == "control" and prefix is not None:
            prefixes[str(frame)] = prefix
        if arm == "guarded_feedback" and final_release:
            prefixes[str(frame)] = prefix
        if first_change is None and (forced or release_mode and would_block or is_release_motion):
            first_change = prefix
        if forced:
            seq.policy.phase, seq.policy.steps, seq.policy.anchor = 2, 0, None
        if release_mode and would_block:
            runtime.engine.guard(seq.policy, phase, steps, anchor, would_advance, place_streak, plan["placement_readiness"])
        if is_release_motion:
            eef = np.asarray(obs["robot0_eef_pos"])
            if feedback is None:
                feedback = runtime.ReleaseController("feedback", eef, plan["release"])
            source = env.cubes[2]
            held = bool(env._check_grasp(env.robots[0].gripper, source.contact_geoms))
            finger = ctl.native.finger_contact(env, source)
            qualified = steps >= plan["release"]["feedback_frames"] and ready and not held and finger
            contact_streak = contact_streak + 1 if qualified else 0
            if arm == "withdraw" and withdrawal is None and contact_streak >= clearance["contact_frames"]:
                withdrawal = dict(prefix, age=steps, pre_xy_m=physical[0], eef_z_m=float(eef[2]))
                withdrawal_goal = eef.copy()
                withdrawal_goal[2] += clearance["lift_m"]
            if withdrawal is None:
                action = feedback.action(eef, pos[stage], pos[stage - 1], np)
            else:
                action = np.zeros(7)
                action[:3] = np.clip(
                    plan["release"]["gain"] * (withdrawal_goal - eef) / plan["release"]["action_scale_m"],
                    -clearance["max_translation_command"], clearance["max_translation_command"],
                )
                action[6] = plan["release"]["gripper"]
        phase_after_decision = seq.policy.phase
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        history.update(action.tobytes())
        history.update(env.sim.get_state().flatten().tobytes())
        m = runtime.h.measurement(env, obs, stage, z[stage], pos[stage], ctl)
        first_seen |= m["valid"][0]
        event = seq.advance(m["valid"][stage - 1], env.sim.data.body_xpos[env.cube_ids[stage]])
        tail = tail + 1 if m["valid"][-1] else 0
        trace.append([
            frame, stage, phase, retreat, steps, probability, ready_streak, forced, release_mode and would_block,
            contact_streak, withdrawal is not None, phase_after_decision, event, physical[0], physical[1], ready,
            m["xy_error"], m["height_above_target"], m["fingers"][stage], m["held"],
            m["pair_contact"], *m["valid"], tail, m["eef"][2], *action[:3], action[6],
        ])
        if tail >= plan["success_frames"] or seq.timed_out:
            break
    values = np.asarray(trace)
    if values.shape[1] != len(COLUMNS) or not np.isfinite(values).all():
        raise ValueError("Invalid trace")
    return dict(
        seed=seed, arm=arm, initial_sha256=digest(initial), initial_features=initial_features,
        success=tail >= plan["success_frames"], frames=frame + 1, final_stage=seq.stage,
        final_phase=seq.policy.phase, retreat_timeout=seq.timed_out, second_lift=second_lift,
        adapted_frames=adapted, first_tower_seen=first_seen, trajectory_sha256=history.hexdigest(),
        first_change=first_change, withdrawal=withdrawal, prefixes=prefixes,
        screen_eligible=screen_eligible and seq.stage == 1 and seq.policy.phase == 1,
        release_entered=release_entered,
    ), values


def verify_group(arms, case):
    control = arms["control"]
    for key, value in case.get("archived", {}).items():
        if control[key] != value:
            raise ValueError(f"Archive mismatch: {case['id']} {key}")
    for arm, row in arms.items():
        if row["initial_sha256"] != control["initial_sha256"]:
            raise ValueError("Unpaired initial state")
        if arm == "control":
            continue
        first = row["first_change"]
        if first is not None and first != control["prefixes"].get(str(first["frame"])):
            raise ValueError(f"Unpaired history before {arm}")
        if first is None and row["trajectory_sha256"] != control["trajectory_sha256"]:
            raise ValueError(f"Unexposed trajectory changed: {arm}")
    if "withdraw" not in arms:
        return
    hold, withdraw = arms["guarded_feedback"], arms["withdraw"]
    if hold["trajectory_sha256"] != case.get("release_archive", hold["trajectory_sha256"]):
        raise ValueError("Guarded-feedback archive changed")
    trigger = withdraw["withdrawal"]
    if trigger is None:
        if hold["trajectory_sha256"] != withdraw["trajectory_sha256"]:
            raise ValueError("Non-triggered withdrawal changed history")
        return
    prefix = {key: trigger[key] for key in ("frame", "history_sha256", "state_sha256")}
    if prefix != hold["prefixes"].get(str(trigger["frame"])):
        raise ValueError("Nonidentical histories at withdrawal")
