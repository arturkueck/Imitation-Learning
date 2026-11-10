"""Paired measurements on trajectories of frozen imitation policies."""
from pathlib import Path
import hashlib
import os
import random
import sys
import time

HERE = Path(__file__).resolve().parent
LEGACY = Path(__file__).resolve().parents[2] / 'critic/critic_warmstart_20261104'
os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
sys.path.insert(0, str(LEGACY))
import critic_action_audit as audit
import numpy as np
import torch

run = audit.run


def initialize():
    torch.set_num_threads(2)
    torch.backends.cuda.matmul.allow_tf32 = False
    torch.backends.cudnn.allow_tf32 = False
    torch.use_deterministic_algorithms(True)
    models, critics = {}, {}
    for seed in (1, 2, 3):
        path = run.parent(seed)["path"]
        models[seed] = run.native.historical.load(path).eval().requires_grad_(False)
        ck = torch.load(LEGACY / f"night_001/warm/seed{seed}/warm.pth",
                        map_location="cuda", weights_only=False)
        sd = ck["critic"]
        critic = audit.TwinQ(sd["mean"], sd["std"], ck["config"]["critic_width"]).cuda()
        critic.load_state_dict(sd)
        critics[seed] = critic.eval().requires_grad_(False)
    return models, critics


def check_time(stop, deadline):
    if stop.exists():
        raise InterruptedError("STOP angefordert")
    if time.time() >= deadline:
        raise TimeoutError("Zeitfenster beendet")


@torch.inference_mode()
def trajectory(models, critic, teacher, reference, scene, direction, config, stop, deadline,
               recorded=None, first_only=False):
    """Record source once; replay that prefix, then intervene on movement only.

    Source movement + reference completion during the window is the declared
    collection policy. Following it yields actual recorded state/action pairs.
    """
    env = run.native.historical.make_env(3)
    try:
        np.random.seed(scene)
        random.seed(scene)
        env.reset()
        env.sim.forward()
        initial = hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest()
        obs = env._get_observations(force_update=True)
        seq = run.controller.GuardedSequencer(models[teacher], 3, run.controller.Clearance(env))
        digest = hashlib.sha256()
        window = []
        start = prefix = None
        stable_frames = 0
        for frame in range(config["horizon"]):
            check_time(stop, deadline)
            phase = seq.policy.phase
            key = [seq.stage, phase, seq.policy.steps]
            state, x, _ = run.features(env, seq, obs, frame, config["horizon"])
            if start is None and key == direction["probe"] and not seq.retreat:
                start = frame
                seq.policy.model = models[reference]
            positions = [env.sim.data.body_xpos[i].copy() for i in env.cube_ids]
            action, actual, _ = seq.policy.action(obs, positions[seq.stage-1], positions[seq.stage])
            assert actual == phase
            normal = action[audit.ACTIVE].astype("float32")
            if start is None or frame == start:
                audit.digest_update(digest, env, state, normal)
            if frame == start:
                prefix = digest.hexdigest()
                if recorded is not None:
                    assert (initial, start, prefix) == (recorded["initial"], recorded["start"], recorded["prefix"])
                    if first_only:
                        action[audit.ACTIVE] = recorded["window"][0]["action"]
            if start is not None and frame < start + direction["frames"] and recorded is None:
                source = models[teacher](torch.as_tensor(x[None], device="cuda"),
                                         torch.tensor([phase], device="cuda"))[0][0].cpu().numpy()
                st = torch.as_tensor(state[None], device="cuda")
                # Score-Baustein des Vorschlags: dieselbe Situation s_t,
                # zwei Aktionen. normal ist die Referenzaktion pi_0(x_t),
                # source die hier tatsaechlich ausgefuehrte Sammleraktion a_t.
                # Die spaeter zu trainierende Policy pi_theta spielt in
                # dieser festen Bewertung noch keine Rolle.
                q_ref = critic(st, torch.as_tensor(normal[None], device="cuda"))[0].item()
                q_src = critic(st, torch.as_tensor(source[None], device="cuda"))[0].item()
                assert np.isfinite([*source, *normal, q_ref, q_src]).all()
                window.append(dict(x=x.tolist(), phase=phase, action=source.tolist(),
                                   reference=normal.tolist(), q_delta=q_src-q_ref))
                action[audit.ACTIVE] = source
            env.step(action)
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            fingers = [run.native.finger_contact(env, cube) for cube in env.cubes]
            valid = [run.native.historical.old.prefix_valid(env, n) and not any(fingers[:n])
                     for n in (2, 3)]
            seq.advance(valid[seq.stage-1], env.sim.data.body_xpos[env.cube_ids[seq.stage]])
            stable_frames = stable_frames + 1 if valid[-1] else 0
            success = stable_frames >= 50
            if success or seq.timed_out:
                break
        if recorded is not None:
            assert start == recorded["start"] and prefix == recorded["prefix"]
        termination = "success" if success else "timeout" if seq.timed_out else "horizon"
        return dict(initial=initial, start=start, prefix=prefix, success=success,
                    last=frame, termination=termination, window=window)
    finally:
        env.close()


def measure(models, critics, scene, index, direction, config, stop, deadline, control, deep=False):
    # All nine ordered teacher/reference pairs appear once in nine families.
    reference = 1 + index % 3
    teacher = 1 + (index % 3 + 1 + index // 3 % 3) % 3
    args = (models, critics[reference], teacher, reference, scene, direction, config, stop, deadline)
    source = trajectory(*args)
    row = dict(scene=scene, teacher=teacher, reference=reference, initial=source["initial"],
               start=source["start"], prefix=source["prefix"], reached=source["start"] is not None,
               qc=False, different=False, win=False, loss=False, timing_only=False,
               q_correct=None, q_delta=None, return_delta=None)
    if control:
        assert trajectory(*args) == source, "Identischer Kontrollrollout weicht ab"
        row["qc"] = True
    window = source.pop("window")
    row.update(source=source, window=window)
    if not row["reached"]:
        return row
    row["different"] = any(step["action"] != step["reference"] for step in window)
    if teacher == reference:
        assert not row["different"]
    other = trajectory(*args, recorded=source) if row["different"] or control else dict(source)
    other.pop("window", None)
    if not row["different"]:
        assert other == source
    gamma = config["gamma"]
    source_return = audit.discounted_return(source["success"], source["start"], source["last"], gamma)
    ref_return = audit.discounted_return(other["success"], source["start"], other["last"], gamma)
    # Abschnittsscore: Summe der einzelnen Q(s_t,a_t)-Q(s_t,pi_0(x_t)).
    # Im Machbarkeitstest diskontiert (Protokoll: gamma=0.995); die Formel
    # im Projektvorschlag ist die ungewichtete Summe mit gamma=1.
    # delta wird hier nur gegen gemessene Outcomes geprueft. Eine Abbildung
    # f(delta), die Normalisierung zu w_tau und Actortraining folgen hier nicht.
    delta = sum(gamma**i * s["q_delta"] for i, s in enumerate(window))
    win = source["success"] and not other["success"]
    loss = other["success"] and not source["success"]
    row.update(reference_outcome=other, win=win, loss=loss, q_delta=delta,
               return_delta=source_return-ref_return,
               timing_only=source["success"] and other["success"] and source["last"] != other["last"])
    if win or loss:
        row["q_correct"] = (delta > 1e-6 and win) or (delta < -1e-6 and loss)
    if deep and direction["frames"] > 1:
        # Isolate the benefit/cost of the remainder of the recorded segment.
        if window[0]["action"] == window[0]["reference"]:
            first = other
        else:
            first = trajectory(*args, recorded=dict(source, window=window), first_only=True)
        row["first_only"] = {k: first[k] for k in ("success", "last", "termination")}
        row["segment_only_win"] = source["success"] and not first["success"]
        row["segment_only_loss"] = first["success"] and not source["success"]
    return row
