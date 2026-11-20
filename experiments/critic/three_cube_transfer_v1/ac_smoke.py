"""N2-3: technischer Smoke des Actor-Critic-Loops mit AWAC-artiger Bindung (PROTOCOL.md §7).

Befehle (aus dem Repository-Stamm):
  check                                         Vorbedingungen, Splits und Plan prüfen (keine Simulation)
  start launch|resume --cutoff T --deadline T   Supervisor losgelöst starten (empfohlen)
  launch --cutoff T --deadline T                Supervisor im Vordergrund
  resume --cutoff T --deadline T                nach PAUSED fortsetzen
  monitor                                       inkrementeller Monitor

Ablauf: (1) Parent-Baseline auf `constraint_development` (3 × 20, eingefroren, 0 Updates).
(2) Bindungsstufen δ_max = 0,05 → 0,10 → 0,20. Je Stufe sechs unabhängige Läufe
(AC-neu, AC-IL × Parent 1–3): 2 Runden × 10 Episoden auf `smoke_interaction`, nach jeder
Episode 25 Critic-Updates, nach jedem zweiten Critic-Update ein Actorupdate. Danach
deterministische Prüfung auf `constraint_development`. Die Prüfung endet bei der ersten
gescheiterten Stufe. Erfolge von AC-neu und AC-IL werden nicht verglichen. Technischer
Smoke ohne Wirksamkeitsaussage. Testfamilien werden nicht berührt.

Fortsetzungseinheit ist ein vollständiger Lauf beziehungsweise eine Parent-Baseline. Ein
unterbrochener Teil wird als verworfen verschoben und vollständig deterministisch neu
ausgeführt (PROTOCOL.md §9, Infrastrukturunterbrechung).
"""

import argparse
import copy
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import psutil

from calibration import HERE, ROOT, digest, identity, alive, load_module, read, time_argument, write
import critic_data as cd
import critic_validation as cv


RESULTS = cd.RESULTS
OUT = RESULTS / "ac_smoke_n2_3"
PARENTS = cd.PARENTS
VARIANTS = ("neu", "il")
DELTAS = (0.05, 0.10, 0.20)
IDX = cv.ACTION_INDEX  # x, y, z, Greifer
BASE_CORE = cv.BASE_CORE
BASE_CONFIG = ROOT / "experiments/critic/base/config.json"
SMOKE = dict(
    rounds=2, episodes_per_round=10, critic_updates_per_episode=25, policy_delay=2,
    awac_lambda=0.1, weight_cap=20.0, gripper_bound=0.02, exploration_std=[0.05, 0.05, 0.05, 0.0],
    bound_tolerance=1e-6, q_range=[-0.05, 1.05], ess_min_fraction=0.10,
    max_lost_per_parent=2, max_lost_total=3, probe_frames_per_phase=64, probe_seed="7400 + p",
    critic_init_seed="7100 + p", rng_seed="7200 + p (SeedSequence.spawn(2): Exploration, Minibatches)",
    torch_threads=2, parallel_runs=6, device="cpu",
)
# Aus experiments/critic/base/config.json übernommen (nicht im Protokoll verändert).
HYPER_KEYS = ("batch_size", "actor_lr", "critic_lr", "weight_decay", "gradient_clip", "target_tau", "gamma",
              "critic_width")
STAGES = {"INITIALIZING": "initializing", "BASELINE": "validation", "SMOKE": "training",
          "COMPLETE": "complete", "PAUSED": "paused", "FAILED": "error"}
PAUSED_EXIT = 3


def hyper():
    config = read(BASE_CONFIG)
    values = {k: config[k] for k in HYPER_KEYS}
    if (values["gamma"] != cd.GAMMA or values["critic_width"] != cv.PRETRAIN["critic_width"]
            or values["batch_size"] != 256):
        raise ValueError("Basiskonfiguration passt nicht zu Protokoll oder Critic")
    return values


def split_range(name):
    entry = next(s for s in read(HERE / "splits_v2.json")["splits"] if s["id"] == name)
    expected = {"constraint_development": (2100003650, 2100003669), "smoke_interaction": (2100003670, 2100003689)}
    if (entry["first"], entry["last"]) != expected[name] or entry["target_families"] != 20 or entry["task_cubes"] != 3:
        raise ValueError(f"Split {name} weicht vom Protokoll ab")
    return list(range(entry["first"], entry["last"] + 1))


def run_name(delta, variant, parent):
    return f"d{delta:.2f}_{variant}_p{parent}"


# ---------------------------------------------------------------- Bindung und Actor

def make_bound(torch, delta, gripper):
    def bounds(a_parent):
        b = torch.empty_like(a_parent)
        b[..., :3] = torch.clamp(0.5 * a_parent[..., :3].abs(), max=delta)
        b[..., 3] = gripper
        return b

    def project(raw, a_parent):
        """a = clip(a_p + b · tanh((a_raw − a_p)/b), −1, 1); bei b = 0 exakt a_p."""
        b = bounds(a_parent)
        safe = torch.where(b > 0, b, torch.ones_like(b))
        return (a_parent + b * torch.tanh((raw - a_parent) / safe)).clamp(-1, 1), b
    return project


def make_executor(torch, actor, parent, project, explore_rng, std):
    """Modell für DevicePolicy: begrenzte Actoraktion, Abschluss vom eingefrorenen Parent."""
    class Executor(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.actor, self.parent = actor, parent
            self.explore, self.log = False, []

        def forward(self, x, phase):
            with torch.no_grad():
                raw, _ = self.actor(x, phase)
                a_parent, z = self.parent(x, phase)
                if self.explore:
                    noise = torch.from_numpy(np.concatenate([explore_rng.normal(0.0, std[:3]), [0.0]]).astype(np.float32))
                    raw = raw + noise[None]
                action, b = project(raw, a_parent)
            self.log.append((a_parent[0].numpy().copy(), action[0].numpy().copy(), b[0].numpy().copy()))
            return action, z
    return Executor()


def violations(log, tolerance):
    a_parent = np.stack([l[0] for l in log]).astype(np.float64)
    action = np.stack([l[1] for l in log]).astype(np.float64)
    b = np.stack([l[2] for l in log]).astype(np.float64)
    deviation = np.abs(action - a_parent)
    bad = (deviation > b + tolerance) | (np.abs(action) > 1 + tolerance) | ~np.isfinite(action)
    return int(bad.any(1).sum()), float(deviation[:, :3].max(initial=0)), float(deviation[:, 3].max(initial=0))


# ---------------------------------------------------------------- Replay und Updates

def transitions(arrays):
    """Übergänge einer Episode für das Replay; nicht endliche terminale Folgezustände werden maskiert."""
    n = len(arrays["frame"])
    terminal = arrays["terminal"].astype(np.float32)
    next_state = arrays["next_critic_state"].copy()
    bad = ~np.isfinite(next_state).all(1)
    if (bad & (terminal == 0)).any():
        raise ValueError("Nicht endlicher nichtterminaler Folgezustand")
    next_state[bad] = 0.0
    x, phase = arrays["actor_input"].astype(np.float32), arrays["actor_phase"].astype(np.int64)
    following = np.minimum(np.arange(n) + 1, n - 1)
    return dict(state=arrays["critic_state"].astype(np.float32),
                action=arrays["executed_action"][:, IDX].astype(np.float32),
                reward=arrays["reward"].astype(np.float32), terminal=terminal, next_state=next_state,
                x=x, phase=phase, next_x=x[following], next_phase=phase[following])


class Learner:
    """Twin-Q mit TD-Ziel ohne Zielrauschen und AWAC-artigem Actorupdate (PROTOCOL.md §7)."""

    def __init__(self, torch, actor, parent, critic, project, hp, smoke, batch_rng):
        self.torch, self.hp, self.smoke, self.rng = torch, hp, smoke, batch_rng
        self.actor, self.parent, self.critic, self.project = actor, parent, critic, project
        self.target_actor = copy.deepcopy(actor).requires_grad_(False)
        self.target_critic = copy.deepcopy(critic).requires_grad_(False)
        self.actor_opt = torch.optim.AdamW(actor.parameters(), lr=hp["actor_lr"], weight_decay=hp["weight_decay"])
        self.critic_opt = torch.optim.AdamW(critic.parameters(), lr=hp["critic_lr"], weight_decay=hp["weight_decay"])
        self.critic_updates = self.actor_updates = 0

    def bounded(self, actor, x, phase):
        raw, _ = actor(x, phase)
        with self.torch.no_grad():
            a_parent, _ = self.parent(x, phase)
        return self.project(raw, a_parent)[0]

    def update(self, replay):
        torch, hp = self.torch, self.hp
        ids = self.rng.integers(len(replay["state"]), size=hp["batch_size"])
        b = {k: torch.from_numpy(np.ascontiguousarray(v[ids])) for k, v in replay.items()}
        with torch.no_grad():
            next_action = self.bounded(self.target_actor, b["next_x"], b["next_phase"])
            t1, t2 = self.target_critic(b["next_state"], next_action)
            target = (b["reward"] + hp["gamma"] * (1 - b["terminal"]) * torch.minimum(t1, t2)).clamp(0, 1)
        q1, q2 = self.critic(b["state"], b["action"])
        critic_loss = (q1 - target).square().mean() + (q2 - target).square().mean()
        metrics = dict(critic_loss=float(critic_loss.detach()), q_min=float(torch.minimum(q1, q2).min().detach()),
                       q_max=float(torch.maximum(q1, q2).max().detach()), target_mean=float(target.mean()))
        finite = bool(torch.isfinite(critic_loss))
        if finite:
            self.critic_opt.zero_grad(set_to_none=True)
            critic_loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(self.critic.parameters(), hp["gradient_clip"])
            finite = bool(torch.isfinite(norm))
            if finite:
                self.critic_opt.step()
        self.critic_updates += 1
        if finite and self.critic_updates % self.smoke["policy_delay"] == 0:
            self.critic.requires_grad_(False)
            prediction = self.bounded(self.actor, b["x"], b["phase"])
            with torch.no_grad():
                q_data = torch.minimum(*self.critic(b["state"], b["action"]))
                q_policy = torch.minimum(*self.critic(b["state"], prediction.detach()))
                advantage = q_data - q_policy
                weight = torch.exp(advantage / self.smoke["awac_lambda"]).clamp(max=self.smoke["weight_cap"])
            actor_loss = (weight * (prediction - b["action"]).square().sum(-1)).mean()
            finite = bool(torch.isfinite(actor_loss) and torch.isfinite(weight).all())
            if finite:
                self.actor_opt.zero_grad(set_to_none=True)
                actor_loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(self.actor.parameters(), hp["gradient_clip"])
                finite = bool(torch.isfinite(norm))
                if finite:
                    self.actor_opt.step()
            self.critic.requires_grad_(True)
            self.actor_updates += 1
            ess = float(weight.sum() ** 2 / weight.square().sum())
            metrics.update(actor_loss=float(actor_loss.detach()), weight_mean=float(weight.mean()),
                           weight_max=float(weight.max()), weight_capped=float((weight >= self.smoke["weight_cap"]).float().mean()),
                           ess=ess, advantage_mean=float(advantage.mean()),
                           q_min=min(metrics["q_min"], float(q_data.min()), float(q_policy.min())),
                           q_max=max(metrics["q_max"], float(q_data.max()), float(q_policy.max())))
            if finite:
                with torch.no_grad():
                    for target_net, source in ((self.target_actor, self.actor), (self.target_critic, self.critic)):
                        for target_p, p in zip(target_net.parameters(), source.parameters()):
                            target_p.lerp_(p, hp["target_tau"])
        metrics["finite"] = finite and all(np.isfinite(v) for v in metrics.values() if isinstance(v, float))
        return metrics


def aggregate(metrics):
    actor = [m for m in metrics if "actor_loss" in m]
    finite_values = lambda key, items: [m[key] for m in items]
    return dict(
        critic_updates=len(metrics), actor_updates=len(actor), all_finite=all(m["finite"] for m in metrics),
        critic_loss_mean=float(np.mean(finite_values("critic_loss", metrics))),
        critic_loss_last=metrics[-1]["critic_loss"],
        q_min=float(min(finite_values("q_min", metrics))), q_max=float(max(finite_values("q_max", metrics))),
        actor_loss_mean=float(np.mean(finite_values("actor_loss", actor))) if actor else None,
        weight_mean=float(np.mean(finite_values("weight_mean", actor))) if actor else None,
        weight_max=float(max(finite_values("weight_max", actor))) if actor else None,
        weight_capped_fraction=float(np.mean(finite_values("weight_capped", actor))) if actor else None,
        ess_mean=float(np.mean(finite_values("ess", actor))) if actor else None,
        ess_min=float(min(finite_values("ess", actor))) if actor else None,
        advantage_mean=float(np.mean(finite_values("advantage_mean", actor))) if actor else None,
    )


def probe_frames(parent):
    """Feste Critic-Datenframes je Phase für Drift- und Q-Messung (64 je Phase, Seed 7400 + p)."""
    episodes = cv.load_critic_data(parent)
    keys = ("actor_input", "actor_phase", "critic_state")
    data = {k: np.concatenate([a[k] for a, _ in episodes]) for k in keys}
    rng = np.random.default_rng(7400 + parent)
    chosen = []
    for phase in range(7):
        ids = np.flatnonzero(data["actor_phase"] == phase)
        chosen.append(np.sort(rng.choice(ids, size=min(SMOKE["probe_frames_per_phase"], len(ids)), replace=False)))
    ids = np.concatenate(chosen)
    return dict(x=data["actor_input"][ids].astype(np.float32), phase=data["actor_phase"][ids].astype(np.int64),
                state=data["critic_state"][ids].astype(np.float32))


def drift(torch, learner, probe):
    with torch.no_grad():
        x, phase, state = (torch.from_numpy(probe[k]) for k in ("x", "phase", "state"))
        raw, _ = learner.actor(x, phase)
        a_parent, _ = learner.parent(x, phase)
        action, _ = learner.project(raw, a_parent)
        q_parent = torch.minimum(*learner.critic(state, a_parent))
        q_actor = torch.minimum(*learner.critic(state, action))
    deviation = (action - a_parent).abs().numpy()
    raw_deviation = (raw - a_parent).abs().numpy()
    per_phase = {str(k): dict(n=int((probe["phase"] == k).sum()),
                              mean_xyz=float(deviation[probe["phase"] == k, :3].mean()),
                              max_xyz=float(deviation[probe["phase"] == k, :3].max()))
                 for k in range(7) if (probe["phase"] == k).any()}
    return dict(mean_xyz=float(deviation[:, :3].mean()), max_xyz=float(deviation[:, :3].max()),
                mean_gripper=float(deviation[:, 3].mean()), max_gripper=float(deviation[:, 3].max()),
                raw_mean_xyz=float(raw_deviation[:, :3].mean()), raw_max_xyz=float(raw_deviation[:, :3].max()),
                per_phase=per_phase,
                q_parent_min=float(q_parent.min()), q_parent_max=float(q_parent.max()),
                q_actor_min=float(q_actor.min()), q_actor_max=float(q_actor.max()),
                finite=bool(np.isfinite(deviation).all() and torch.isfinite(q_parent).all() and torch.isfinite(q_actor).all()))


def replay_q(torch, learner, replay):
    with torch.no_grad():
        values = cv.predict(torch, learner.critic, replay["state"], replay["action"])
    return dict(n=len(values), min=float(values.min()), max=float(values.max()), finite=bool(np.isfinite(values).all()))


# ---------------------------------------------------------------- Einzelne Läufe (Kindprozesse)

def prepare_dir(final):
    """Unvollständige Teilstände nach §9 als verworfen verschieben, nie löschen."""
    work = final.with_name(final.name + ".partial")
    if work.exists():
        target = OUT / "discarded"
        target.mkdir(exist_ok=True)
        k = sum(1 for _ in target.glob(final.name + "_*"))
        work.rename(target / f"{final.name}_{k}")
    work.mkdir(parents=True)
    return work


def clean(value):
    """Nicht endliche Kennzahlen als Text sichern, damit sie berichtet statt verworfen werden."""
    if isinstance(value, float) and not np.isfinite(value):
        return repr(value)
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [clean(v) for v in value]
    return value


def finish_dir(work, final, result):
    write(work / "result.json", clean(result))
    work.rename(final)


def rollout(base, controller, adapter, torch, model, threshold, cap, scene, parent, deadline, work):
    # STOP-Datei und Deadline gelten laufweit (OUT); Arbeitsdateien liegen in `work`.
    row, arrays = cd.episode(base, controller, adapter, torch, model, threshold, cap, scene, parent, deadline, OUT)
    keys = ("initial_sha256", "trajectory_sha256", "success", "frames", "termination", "max_stable_frames",
            "elapsed_seconds")
    return {k: row[k] for k in keys} | dict(scene_seed=scene), arrays


def baseline(parent, deadline):
    """Unveränderter Parent auf `constraint_development` (identischer Episodenpfad wie N2-1)."""
    final = OUT / "baseline" / f"parent_{parent}"
    work = prepare_dir(final)
    registry, base, torch, controller, adapter = cd.setup(work)
    torch.set_num_threads(SMOKE["torch_threads"])
    config = read(OUT / "config.json")
    model = registry.restore_abc_a_for_inference(parent, config["parents"][str(parent)])
    rows = []
    for scene in config["constraint_development"]:
        row, arrays = rollout(base, controller, adapter, torch, *model, scene, parent, deadline, work)
        rows.append(row)
        write(work / "progress.json", dict(episodes=len(rows)))
    finish_dir(work, final, dict(parent=parent, rows=rows, successes=sum(r["success"] for r in rows),
                                 optimizer_updates=0))


def smoke_run(delta, variant, parent, deadline):
    final = OUT / "runs" / run_name(delta, variant, parent)
    work = prepare_dir(final)
    registry, base, torch, controller, adapter = cd.setup(work)
    torch.set_num_threads(SMOKE["torch_threads"])
    torch.use_deterministic_algorithms(True)
    core = load_module("critic_base_core", BASE_CORE)
    config = read(OUT / "config.json")
    hp = config["hyper"]
    started = time.perf_counter()
    parent_model, threshold, cap = registry.restore_abc_a_for_inference(parent, config["parents"][str(parent)])
    il_critic, meta = cv.load_critic(torch, core, cv.OUT, parent)
    if meta["weights_sha256"] != config["il_critic_sha256"][str(parent)]:
        raise ValueError("IL-Critic weicht vom eingefrorenen Hash ab")
    state = il_critic.state_dict()
    if variant == "il":
        critic = copy.deepcopy(il_critic).train().requires_grad_(True)
    else:
        torch.manual_seed(7100 + parent)  # gleiche Initialisierung wie vor dem Vortraining in N2-2
        critic = core.TwinQ(state["mean"].numpy(), state["std"].numpy(), hp["critic_width"])
    actor = copy.deepcopy(parent_model).requires_grad_(True)
    explore_rng, batch_rng = (np.random.default_rng(s) for s in np.random.SeedSequence(7200 + parent).spawn(2))
    project = make_bound(torch, delta, SMOKE["gripper_bound"])
    learner = Learner(torch, actor, parent_model, critic, project, hp, SMOKE, batch_rng)
    executor = make_executor(torch, actor, parent_model, project, explore_rng, np.asarray(SMOKE["exploration_std"]))
    probe = probe_frames(parent)
    history = [dict(round=0, critic_updates=0, actor_updates=0, drift=drift(torch, learner, probe))]
    if history[0]["drift"]["max_xyz"] != 0 or history[0]["drift"]["max_gripper"] != 0:
        raise ValueError("Actor weicht vor dem ersten Update vom Parent ab")
    online, parts, total_violations = [], [], 0
    update_seconds = rollout_seconds = 0.0
    scenes = config["smoke_interaction"]
    per_round = SMOKE["episodes_per_round"]
    for round_index in range(SMOKE["rounds"]):
        metrics = []
        for scene in scenes[round_index * per_round:(round_index + 1) * per_round]:
            executor.explore, executor.log = True, []
            t0 = time.perf_counter()
            row, arrays = rollout(base, controller, adapter, torch, executor, threshold, cap, scene, parent, deadline, work)
            rollout_seconds += time.perf_counter() - t0
            if len(executor.log) != row["frames"] or not np.array_equal(
                    arrays["executed_action"][:, IDX], np.stack([l[1] for l in executor.log]).astype(np.float64)):
                raise ValueError("Ausführungsprotokoll passt nicht zur Episode")
            count, max_xyz, max_gripper = violations(executor.log, SMOKE["bound_tolerance"])
            total_violations += count
            arrays["parent_action"][:, IDX] = np.stack([l[0] for l in executor.log]).astype(np.float64)
            row.update(round=round_index + 1, bound_violations=count, max_deviation_xyz=max_xyz,
                       max_deviation_gripper=max_gripper)
            parts.append(transitions(arrays))
            replay = cd_concat(parts)
            t0 = time.perf_counter()
            for _ in range(SMOKE["critic_updates_per_episode"]):
                metrics.append(learner.update(replay))
            update_seconds += time.perf_counter() - t0
            online.append(row)
            write(work / "progress.json", dict(online_episodes=len(online), critic_updates=learner.critic_updates))
            if not metrics[-1]["finite"]:
                break
        history.append(dict(round=round_index + 1, critic_updates=learner.critic_updates,
                            actor_updates=learner.actor_updates, updates=aggregate(metrics),
                            drift=drift(torch, learner, probe), replay_q=replay_q(torch, learner, replay),
                            online_successes=sum(r["success"] for r in online if r["round"] == round_index + 1)))
        if not history[-1]["updates"]["all_finite"]:
            break
    development = []
    executor.explore = False
    for scene in config["constraint_development"]:
        executor.log = []
        row, _ = rollout(base, controller, adapter, torch, executor, threshold, cap, scene, parent, deadline, work)
        count, max_xyz, max_gripper = violations(executor.log, SMOKE["bound_tolerance"])
        total_violations += count
        row.update(bound_violations=count, max_deviation_xyz=max_xyz, max_deviation_gripper=max_gripper)
        development.append(row)
        write(work / "progress.json", dict(online_episodes=len(online), development_episodes=len(development),
                                           critic_updates=learner.critic_updates))
    checkpoint = work / "checkpoint.pt"
    torch.save(dict(actor=actor.state_dict(), critic=critic.state_dict(),
                    target_actor=learner.target_actor.state_dict(), target_critic=learner.target_critic.state_dict(),
                    actor_optimizer=learner.actor_opt.state_dict(), critic_optimizer=learner.critic_opt.state_dict(),
                    explore_rng=explore_rng.bit_generator.state, batch_rng=batch_rng.bit_generator.state,
                    critic_updates=learner.critic_updates, actor_updates=learner.actor_updates), checkpoint)
    finish_dir(work, final, dict(
        delta_max=delta, variant=variant, parent=parent, technical_only=True,
        critic_init="N2-2 vortrainiert (SHA-256 geprüft)" if variant == "il" else "zufällig, torch.manual_seed(7100 + p)",
        critic_updates=learner.critic_updates, actor_updates=learner.actor_updates,
        online=online, online_successes=sum(r["success"] for r in online), online_frames=sum(r["frames"] for r in online),
        development=development, development_successes=sum(r["success"] for r in development),
        bound_violations=total_violations, history=history,
        rollout_seconds=rollout_seconds, update_seconds=update_seconds, wall_seconds=time.perf_counter() - started,
        checkpoint_sha256=digest(checkpoint.read_bytes())))


def cd_concat(parts):
    return {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}


# ---------------------------------------------------------------- Stufenbewertung

def assess_stage(delta, runs, baselines):
    """Bestehensregel nach §7. Lesart B (entscheidend, konservativ): je Parent über beide Varianten
    ≤ 2 verlorene Parent-Erfolge, alle sechs Läufe zusammen ≤ 3. Lesart A (berichtet): je Variante
    je Parent ≤ 2 und Summe der drei Parents ≤ 3."""
    s = SMOKE
    entries, lost = {}, {}
    for (variant, parent), result in sorted(runs.items()):
        parent_rows = {r["scene_seed"]: r["success"] for r in baselines[parent]["rows"]}
        lost_families = [r["scene_seed"] for r in result["development"] if parent_rows[r["scene_seed"]] and not r["success"]]
        gained = [r["scene_seed"] for r in result["development"] if r["success"] and not parent_rows[r["scene_seed"]]]
        lost[(variant, parent)] = len(lost_families)
        rounds = [h for h in result["history"] if h["round"] > 0]
        finite = (all(h["updates"]["all_finite"] and h["drift"]["finite"] and h["replay_q"]["finite"] for h in rounds)
                  and len(rounds) == s["rounds"] and result["critic_updates"] == 500 and result["actor_updates"] == 250)
        q_low, q_high = s["q_range"]
        q_after = [v for h in rounds for v in (h["replay_q"]["min"], h["replay_q"]["max"], h["drift"]["q_parent_min"],
                                               h["drift"]["q_parent_max"], h["drift"]["q_actor_min"], h["drift"]["q_actor_max"])]
        q_updates = [v for h in rounds for v in (h["updates"]["q_min"], h["updates"]["q_max"])]
        numeric = lambda values: all(isinstance(v, (int, float)) for v in values)
        finite = finite and numeric(q_after) and numeric(q_updates)
        if not finite:  # nicht endliche Werte wurden als Text gesichert
            q_after = [v for v in q_after if isinstance(v, (int, float))]
            q_updates = [v for v in q_updates if isinstance(v, (int, float))]
        ess = [h["updates"]["ess_mean"] for h in rounds if isinstance(h["updates"]["ess_mean"], (int, float))]
        ess_mean = float(np.mean(ess)) if ess else None
        checks = dict(finite=finite,
                      q_range=bool(q_after and q_low <= min(q_after) and max(q_after) <= q_high),
                      no_violations=result["bound_violations"] == 0,
                      ess=bool(ess_mean is not None and ess_mean >= s["ess_min_fraction"] * 256))
        entries[f"{variant}_p{parent}"] = dict(
            checks=checks, technical_pass=all(checks.values()), lost_parent_successes=lost_families,
            new_successes=gained, development_successes=result["development_successes"],
            parent_development_successes=baselines[parent]["successes"], ess_mean=ess_mean,
            q_after_rounds=[min(q_after), max(q_after)] if q_after else None,
            q_during_updates_incl_init=[min(q_updates), max(q_updates)] if q_updates else None,
            q_during_updates_in_range=bool(q_updates and q_low <= min(q_updates) and max(q_updates) <= q_high),
            online_successes=result["online_successes"], bound_violations=result["bound_violations"],
            final_drift_mean_xyz=rounds[-1]["drift"]["mean_xyz"] if rounds else None,
            final_drift_max_xyz=rounds[-1]["drift"]["max_xyz"] if rounds else None)
    per_parent_b = {p: sum(lost[(v, p)] for v in VARIANTS) for p in PARENTS}
    reading_b = (all(n <= s["max_lost_per_parent"] for n in per_parent_b.values())
                 and sum(per_parent_b.values()) <= s["max_lost_total"])
    reading_a = {v: bool(all(lost[(v, p)] <= s["max_lost_per_parent"] for p in PARENTS)
                         and sum(lost[(v, p)] for p in PARENTS) <= s["max_lost_total"]) for v in VARIANTS}
    technical = all(e["technical_pass"] for e in entries.values())
    return dict(delta_max=delta, runs=entries, technical_pass=technical,
                lost_per_parent_both_variants=per_parent_b, lost_total=sum(per_parent_b.values()),
                retention_reading_b=bool(reading_b), retention_reading_a=reading_a,
                passed=bool(technical and reading_b),
                readings_disagree=bool(technical and reading_b != all(reading_a.values())))


# ---------------------------------------------------------------- Plan, Worker, Supervisor, Monitor

def plan(registry):
    sources = [Path(__file__), HERE / "critic_validation.py", HERE / "critic_data.py", HERE / "calibration.py",
               HERE / "splits_v2.json", HERE / "PROTOCOL.md", BASE_CORE, BASE_CONFIG, Path(registry.__file__)]
    critics = {str(p): read(cv.critic_paths(cv.OUT, p)[1])["weights_sha256"] for p in PARENTS}
    return {
        "task": "N2-3", "protocol": "protocol_v1", "technical_only": True,
        "parents": {str(seed): entry for seed, entry in registry.frozen_abc_a().items()},
        "il_critic_sha256": critics, "n2_2_summary_sha256": digest((cv.OUT / "summary.json").read_bytes()),
        "smoke_interaction": split_range("smoke_interaction"),
        "constraint_development": split_range("constraint_development"),
        "deltas": list(DELTAS), "variants": list(VARIANTS), "smoke": SMOKE, "hyper": hyper(),
        "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sources},
        "replay": "nur eigene Onlineerfahrung des Laufs; keine Critic-Daten im Replay",
        "critic_target": "r + γ(1−t)·min Q_ziel(s', π_ziel,begrenzt(s')), ohne Zielrauschen, geklemmt auf [0, 1]",
        "actor_loss": "mean(w · ||π_begrenzt(s) − a||²), w = min(exp((Q(s,a) − Q(s,π(s)))/λ), 20), Q = min(Q1, Q2), keine Batchnormierung",
        "optimizers": "beide Varianten frisch (AdamW); Ziel-Netze Polyak nach jedem Actorupdate",
        "q_range_check": "entscheidend: Critic-Ausgaben nach jeder Runde auf Replay (ausgeführte Aktionen) und festen Probeframes (Parent- und Actoraktion); berichtet: Q während der Updates inklusive Initialisierung",
        "retention_rule": "entscheidend Lesart B (je Parent über beide Varianten ≤ 2, alle sechs Läufe ≤ 3); berichtet Lesart A (je Variante)",
        "parallelization": "Läufe einer Stufe als getrennte Prozesse mit festen Seeds und 2 Torch-Threads; Ergebnis hängt nicht von der Prozesszahl ab",
    }


def children(jobs, deadline, log_dir):
    """Kindprozesse parallel starten und warten; Rückgabe Exitcodes."""
    processes = []
    try:
        for name, arguments in jobs:
            log = (log_dir / f"{name}.log").open("ab")
            processes.append((name, subprocess.Popen(
                [sys.executable, "-u", str(Path(__file__)), *arguments, "--deadline", str(deadline)],
                cwd=ROOT, stdout=log, stderr=subprocess.STDOUT), log))
        return {name: process.wait() for name, process, _ in processes}
    finally:
        for _, process, log in processes:
            if process.poll() is None:
                process.kill()
                process.wait()
            log.close()


def worker(deadline):
    status_path = OUT / "status.json"
    previous = read(status_path) if status_path.exists() else {}
    previous_wall = previous.get("active_wall_seconds", 0)
    started = time.perf_counter()
    state = dict(state="INITIALIZING", worker=identity(os.getpid()), stages_done=previous.get("stages_done", []))

    def status(**fields):
        state.update(fields, heartbeat_unix=time.time(), active_wall_seconds=previous_wall + time.perf_counter() - started)
        state.update(stage=STAGES[state["state"]])
        write(status_path, state)

    status()
    try:
        registry = load_module("ac_smoke_registry", cd.CURRICULUM / "registry.py")
        config = plan(registry)
        config_path = OUT / "config.json"
        if config_path.exists():
            if read(config_path) != config:
                raise ValueError("Provenienz des bestehenden Laufs geändert")
        else:
            write(config_path, config)
        logs = OUT / "logs"
        check_stop()
        status(state="BASELINE")
        missing = [p for p in PARENTS if not (OUT / "baseline" / f"parent_{p}" / "result.json").is_file()]
        codes = children([(f"baseline_p{p}", ["_baseline", "--parent", str(p)]) for p in missing], deadline, logs)
        check_codes(codes)
        baselines = {p: read(OUT / "baseline" / f"parent_{p}" / "result.json") for p in PARENTS}
        stages = []
        for delta in DELTAS:
            check_stop()
            status(state="SMOKE", delta_max=delta)
            jobs = [(run_name(delta, v, p), ["_run", "--delta", str(delta), "--variant", v, "--parent", str(p)])
                    for v in VARIANTS for p in PARENTS
                    if not (OUT / "runs" / run_name(delta, v, p) / "result.json").is_file()]
            check_codes(children(jobs, deadline, logs))
            runs = {(v, p): read(OUT / "runs" / run_name(delta, v, p) / "result.json") for v in VARIANTS for p in PARENTS}
            assessment = assess_stage(delta, runs, baselines)
            write(OUT / "stages" / f"stage_{delta:.2f}.json", assessment)
            stages.append(assessment)
            status(stages_done=[s["delta_max"] for s in stages])
            if not assessment["passed"]:
                break
        passed = [s["delta_max"] for s in stages if s["passed"]]
        write(OUT / "summary.json", summarize(baselines, stages, passed, previous_wall + time.perf_counter() - started))
        status(state="COMPLETE")
    except (InterruptedError, TimeoutError) as error:
        status(state="PAUSED", reason=str(error))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def check_stop():
    if (OUT / "STOP").exists():
        raise InterruptedError("STOP requested")


def check_codes(codes):
    if any(code == PAUSED_EXIT for code in codes.values()):
        raise TimeoutError(f"Kindprozess pausiert: {codes}")
    if any(code != 0 for code in codes.values()):
        raise RuntimeError(f"Kindprozess fehlgeschlagen: {codes}")


def summarize(baselines, stages, passed, wall):
    runs = [read(p) for p in sorted((OUT / "runs").glob("*/result.json"))]
    return dict(
        technical_only=True, statement="Technischer Smoke, ausdrücklich ohne Wirksamkeitsaussage",
        parent_development_successes={str(p): b["successes"] for p, b in baselines.items()},
        stages=stages, stages_checked=[s["delta_max"] for s in stages], stages_passed=passed,
        chosen_delta_max=max(passed) if passed else None,
        pilot_prerequisite=bool(passed),
        readings_disagree=any(s["readings_disagree"] for s in stages),
        runs=len(runs), critic_updates_total=sum(r["critic_updates"] for r in runs),
        actor_updates_total=sum(r["actor_updates"] for r in runs),
        online_episodes=sum(len(r["online"]) for r in runs), development_episodes=sum(len(r["development"]) for r in runs),
        baseline_episodes=sum(len(b["rows"]) for b in baselines.values()),
        rollout_seconds_runs=sum(r["rollout_seconds"] for r in runs),
        update_seconds_runs=sum(r["update_seconds"] for r in runs),
        update_seconds_per_run_mean=float(np.mean([r["update_seconds"] for r in runs])) if runs else None,
        discarded_partials=sorted(p.name for p in (OUT / "discarded").glob("*")) if (OUT / "discarded").exists() else [],
        run_result_sha256={p.parent.name: digest(p.read_bytes()) for p in sorted((OUT / "runs").glob("*/result.json"))},
        config_sha256=digest((OUT / "config.json").read_bytes()), worker_wall_seconds=wall,
    )


def preconditions():
    plan_text = (HERE / "NACHTPLAN.md").read_text(encoding="utf-8")
    if "- [x] N2-2/N2-3" not in plan_text:
        raise ValueError("Freigabe N2-2/N2-3 im Nachtplan fehlt")
    if "Gesamtpause: nein" not in (HERE / "STATUS.md").read_text(encoding="utf-8"):
        raise ValueError("Gesamtpause aktiv oder unklar")
    if "**Status: FREIGEGEBEN**" not in (HERE / "PROTOCOL.md").read_text(encoding="utf-8"):
        raise ValueError("Protokoll nicht freigegeben")
    summary = read(cv.OUT / "summary.json")
    if read(cv.OUT / "supervisor_status.json")["state"] != "COMPLETE" or not summary["decision"]["passed"]:
        raise ValueError("N2-2 nicht abgeschlossen oder Critic-Validierung nicht bestanden")


def supervise(cutoff, deadline, resume):
    if time.time() >= cutoff or deadline < cutoff + 30:
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")
    preconditions()
    if resume:
        previous = read(OUT / "supervisor_status.json")
        if (previous["state"] != "PAUSED" or alive(previous["supervisor"])
                or alive(read(OUT / "status.json")["worker"]) or (OUT / "STOP").exists()):
            raise ValueError("Fortsetzung erfordert PAUSED, inaktive Prozesse und entfernte STOP-Datei")
    else:
        OUT.mkdir()
        for name in ("baseline", "runs", "stages", "logs"):
            (OUT / name).mkdir()
    claim = OUT / "supervisor.lock"
    with claim.open("x") as lock:
        lock.write(str(os.getpid()))
    path = OUT / "supervisor_status.json"
    state = dict(state="STARTING", supervisor=identity(os.getpid()), deadline_unix=deadline, cutoff_unix=cutoff)
    child = None
    awake = False
    try:
        write(path, state)
        if time.time() >= cutoff:
            raise TimeoutError("Startfenster geschlossen")
        if os.name == "nt":
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (OUT / "worker.log").open("ab") as log:
            child = subprocess.Popen([sys.executable, "-u", str(Path(__file__)), "_worker",
                                      "--deadline", str(deadline - 60)], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT)
            state.update(state="RUNNING", launcher=identity(child.pid), sleep_prevention=awake)
            write(path, state)
            code = child.wait(timeout=max(0.01, deadline - time.time()))
        state.update(state=read(OUT / "status.json")["state"], worker_exitcode=code)
        if code != 0:
            state["state"] = "FAILED"
    except subprocess.TimeoutExpired:
        state.update(state="FAILED", reason="Harte Deadline erreicht")
    except Exception as error:
        state.update(state="FAILED", reason=repr(error))
        raise
    finally:
        if child is not None and child.poll() is None:
            for process in reversed(psutil.Process(child.pid).children(recursive=True)):
                try:
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
            child.kill()
            child.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state["updated_unix"] = time.time()
        write(path, state)
        claim.unlink()
    return int(state["state"] == "FAILED")


def detach(command, cutoff, deadline):
    if time.time() >= time_argument(cutoff):
        raise ValueError("Startfenster geschlossen")
    preconditions()
    arguments = [sys.executable, str(Path(__file__)), command, "--cutoff", cutoff, "--deadline", deadline]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    with (RESULTS / "ac_smoke_n2_3_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags | 0x01000000)
        except OSError:
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
    print(json.dumps(identity(child.pid)))
    return 0


def verify(summary):
    """Einmaliger Endabgleich: Stufenbewertungen aus den Laufergebnissen neu berechnen."""
    baselines = {p: read(OUT / "baseline" / f"parent_{p}" / "result.json") for p in PARENTS}
    for stage in summary["stages"]:
        delta = stage["delta_max"]
        runs = {(v, p): read(OUT / "runs" / run_name(delta, v, p) / "result.json") for v in VARIANTS for p in PARENTS}
        for (v, p), result in runs.items():
            path = OUT / "runs" / run_name(delta, v, p) / "checkpoint.pt"
            if digest(path.read_bytes()) != result["checkpoint_sha256"]:
                raise ValueError(f"Checkpoint {run_name(delta, v, p)} weicht ab")
        if json.loads(json.dumps(assess_stage(delta, runs, baselines))) != stage:
            raise ValueError(f"Stufe {delta} stimmt nicht mit den Laufergebnissen überein")
    hashes = {p.parent.name: digest(p.read_bytes()) for p in sorted((OUT / "runs").glob("*/result.json"))}
    if hashes != summary["run_result_sha256"]:
        raise ValueError("Laufergebnisse weichen von summary.json ab")


def new_errors(previous):
    found, offsets = [], dict(previous.get("log_offsets", {}))
    for path in [OUT / "worker.log", *sorted((OUT / "logs").glob("*.log"))]:
        if not path.exists():
            continue
        key = path.name
        with path.open("rb") as stream:
            size = path.stat().st_size
            offset = offsets.get(key, 0)
            stream.seek(offset if offset <= size else 0)
            data = stream.read()
            complete = data.rfind(b"\n") + 1
            found += [f"{key}: {line.strip()}" for line in data[:complete].decode(errors="replace").splitlines()
                      if re.search(r"Traceback|(?:Error|Exception):|nonfinite|nicht endlich|out of memory", line, re.I)]
            offsets[key] = stream.tell() - len(data) + complete
    return offsets, found


def progress():
    """Persistierter Fortschritt: abgeschlossene Teile und Episoden in laufenden Teilen."""
    done = sorted(p.parent.name for p in OUT.glob("*/*/result.json"))
    partial = {}
    for path in OUT.glob("*/*.partial/progress.json"):
        try:
            partial[path.parent.name] = read(path)
        except (OSError, ValueError):
            pass
    return done, partial


def monitor():
    supervisor_path, worker_path = OUT / "supervisor_status.json", OUT / "status.json"
    if not supervisor_path.is_file():
        print("OFFEN | Kein Supervisorstatus für N2-3")
        return 0 if not OUT.exists() else 2
    supervisor = read(supervisor_path)
    running = alive(supervisor["supervisor"])
    worker_state = read(worker_path) if worker_path.is_file() else {}
    worker_running = alive(worker_state.get("worker"))
    previous_path = OUT / "monitor_state.json"
    previous = read(previous_path) if previous_path.is_file() else {}
    offsets, errors = new_errors(previous)
    done, partial = progress()
    marker = [done, partial, worker_state.get("state")]
    now = time.time()
    progress_time = now if marker != previous.get("marker") else previous.get("progress_time", now)
    output = dict(supervisor=supervisor["supervisor"], supervisor_alive=running, supervisor_state=supervisor["state"],
                  worker=worker_state.get("worker"), worker_alive=worker_running, worker_state=worker_state.get("state"),
                  delta_max=worker_state.get("delta_max"), stages_done=worker_state.get("stages_done"),
                  completed_parts=len(done), new_parts=len(set(done) - set(previous.get("marker", [[]])[0])),
                  in_progress=partial, deadline_unix=supervisor["deadline_unix"], errors=errors[-10:])
    state = supervisor["state"]
    result_verified = previous.get("result_verified", False)
    if (state == "COMPLETE" and worker_state.get("state") == "COMPLETE" and not worker_running
            and supervisor.get("worker_exitcode") == 0):
        summary = read(OUT / "summary.json")
        if not result_verified:
            verify(summary)
        result_verified = True
        code = 0
        output.update(status="COMPLETE", stages_checked=summary["stages_checked"], stages_passed=summary["stages_passed"],
                      chosen_delta_max=summary["chosen_delta_max"], readings_disagree=summary["readings_disagree"],
                      critic_updates_total=summary["critic_updates_total"], actor_updates_total=summary["actor_updates_total"])
        output.pop("in_progress")
    elif state == "PAUSED" and not worker_running and supervisor.get("worker_exitcode") == 0:
        code = 0
        output.update(status="PAUSED", reason=worker_state.get("reason"))
    elif state == "FAILED" or errors or not running or (state == "RUNNING" and now >= supervisor["deadline_unix"]):
        code = 2
        output.update(status="ERROR", reason=worker_state.get("reason") or supervisor.get("reason"))
    elif now - progress_time > 240:
        code = 1
        output.update(status="WARNING", reason="Seit mindestens 240 s kein neuer persistierter Fortschritt")
    else:
        code = 0
        output.update(status="OK")
    write(previous_path, dict(marker=marker, progress_time=progress_time, checked_unix=now,
                              log_offsets=offsets, result_verified=result_verified))
    print(json.dumps(output, ensure_ascii=True))
    return code


def child_main(function, *arguments):
    try:
        function(*arguments)
    except (InterruptedError, TimeoutError) as error:
        print(f"PAUSED: {error}", flush=True)
        return PAUSED_EXIT
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("launch", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--cutoff", type=time_argument, required=True)
        command.add_argument("--deadline", type=time_argument, required=True)
    start = commands.add_parser("start")
    start.add_argument("mode", choices=("launch", "resume"))
    start.add_argument("--cutoff", required=True)
    start.add_argument("--deadline", required=True)
    commands.add_parser("_worker").add_argument("--deadline", type=float, required=True)
    base_child = commands.add_parser("_baseline")
    base_child.add_argument("--parent", type=int, required=True)
    base_child.add_argument("--deadline", type=float, required=True)
    run_child = commands.add_parser("_run")
    run_child.add_argument("--delta", type=float, required=True)
    run_child.add_argument("--variant", choices=VARIANTS, required=True)
    run_child.add_argument("--parent", type=int, required=True)
    run_child.add_argument("--deadline", type=float, required=True)
    commands.add_parser("monitor")
    commands.add_parser("check")
    args = parser.parse_args()
    if args.command == "start":
        time_argument(args.deadline)
        return detach(args.mode, args.cutoff, args.deadline)
    if args.command in ("_worker", "_baseline", "_run") and not (OUT / "supervisor.lock").exists():
        parser.error("Nur über den Supervisor starten")
    if args.command == "_worker":
        worker(args.deadline)
        return 0
    if args.command == "_baseline":
        return child_main(baseline, args.parent, args.deadline)
    if args.command == "_run":
        if args.delta not in DELTAS or args.parent not in PARENTS:
            parser.error("Unbekannte Stufe oder Parent")
        return child_main(smoke_run, args.delta, args.variant, args.parent, args.deadline)
    if args.command == "check":
        preconditions()
        registry = load_module("ac_smoke_registry", cd.CURRICULUM / "registry.py")
        config = plan(registry)
        print(json.dumps(dict(smoke=[config["smoke_interaction"][0], config["smoke_interaction"][-1]],
                              development=[config["constraint_development"][0], config["constraint_development"][-1]],
                              hyper=config["hyper"], il_critic_sha256=config["il_critic_sha256"])))
        return 0
    if args.command == "monitor":
        return monitor()
    return supervise(args.cutoff, args.deadline, args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
