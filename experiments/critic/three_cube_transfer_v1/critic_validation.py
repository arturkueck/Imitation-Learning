"""N2-2: Critic je A-Parent vortrainieren und nach PROTOCOL.md §6 validieren.

Befehle (aus dem Repository-Stamm):
  start launch|resume --cutoff T --deadline T   Supervisor losgelöst starten (empfohlen)
  launch --cutoff T --deadline T   Supervisor im Vordergrund (Zeitstempel mit Zonenoffset)
  resume --cutoff T --deadline T   nach PAUSED exakt fortsetzen
  monitor                          inkrementeller Monitor

Ablauf im Worker: (1) Vortraining der drei Critics auf den N2-1-Daten des jeweiligen
Parents (20.000 Updates, Batch 256, Lernrate 3e-4, kein Early Stopping), danach
eingefroren per SHA-256. (2) A-Rollouts mit eingefrorenen Parents auf
`validation_normal` (100) und `validation_hard` (50) nach dem Datenvertrag aus N2-1.
(3) Auswertung nach §6. Testfamilien werden nicht berührt.
"""

import argparse
import ctypes
import hashlib
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


RESULTS = cd.RESULTS
OUT = RESULTS / "critic_validation_n2_2"
DATA = cd.OUT
PARENTS = cd.PARENTS
GAMMA = cd.GAMMA
DATASET_SHA256 = "9f0aeaaff68734ffa2bd2a14bc91bd32c3c92db5fc255af1029a580daff9a2ba"
PANELS = ("validation_normal", "validation_hard")
PANEL_SIZES = {"validation_normal": 100, "validation_hard": 50}
EXPECTED = sum(PANEL_SIZES.values()) * len(PARENTS)
ACTION_INDEX = [0, 1, 2, 6]  # x, y, z, Greifer (PROTOCOL.md §2: trainierte Teile)
PRETRAIN = dict(updates=20000, batch_size=256, critic_lr=3e-4, weight_decay=1e-6, gradient_clip=10.0,
                critic_width=256, log_every=500, torch_threads=4, device="cpu",
                target="beobachteter diskontierter Return (Monte-Carlo, wie Learner.warm in base/core.py)",
                init_seed="7100 + p", sampler_seed="7200 + p (numpy default_rng)")
CRITERIA = dict(auc_min=0.60, auc_lower_gt=0.50, min_successes=10, min_failures=10, min_points=2,
                ece_max=0.10, ece_bins=10, bootstrap_draws=2000, bootstrap_seed=7300, interval=0.95)
STAGES = {"INITIALIZING": "initializing", "TRAINING": "training", "EVALUATING": "validation",
          "ASSESSING": "validation", "COMPLETE": "complete", "PAUSED": "paused", "FAILED": "error"}
BASE_CORE = ROOT / "experiments/critic/base/core.py"


# ---------------------------------------------------------------- Phasenpunkte und Kennzahlen

def phase_points(stage, phase):
    """Erster Frame jeder erreichten Kombination aus Stufe und Policy-Phase (§6).
    Frame 0 ist stets der erste Frame seiner Kombination und deckt den Episodenstart ab."""
    points = {}
    for frame, key in enumerate(zip(np.asarray(stage).tolist(), np.asarray(phase).tolist())):
        points.setdefault(f"stage{key[0]}_phase{key[1]}", frame)
    return points


def auc_matrix(scores, labels):
    """Vergleichsmatrix positiv × negativ (1, 0,5 bei Gleichstand, 0) für die Mann-Whitney-AUC."""
    positive, negative = scores[labels], scores[~labels]
    return (positive[:, None] > negative[None, :]) + 0.5 * (positive[:, None] == negative[None, :])


def weighted_auc(matrix, w_pos, w_neg):
    """AUC mit Häufigkeitsgewichten (Bootstrap); Zeilen von w_* sind Ziehungen."""
    denominator = w_pos.sum(-1) * w_neg.sum(-1)
    numerator = np.einsum("...i,ij,...j->...", w_pos, matrix, w_neg)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(denominator > 0, numerator / np.where(denominator > 0, denominator, 1), np.nan)


def ece(prediction, target, bins):
    """Gleich breite Klassen des Vorhersagewerts auf [0, 1]; Werte außerhalb fallen in die Randklassen."""
    index = np.clip(np.floor(np.clip(prediction, 0, 1) * bins).astype(int), 0, bins - 1)
    total = 0.0
    table = []
    for b in range(bins):
        mask = index == b
        if mask.any():
            gap = abs(float(prediction[mask].mean()) - float(target[mask].mean()))
            total += mask.sum() / len(prediction) * gap
            table.append(dict(bin=b, n=int(mask.sum()), mean_prediction=float(prediction[mask].mean()),
                              mean_return=float(target[mask].mean())))
    return total, table


def assess(records, criteria=CRITERIA):
    """Kennzahlen nach §6 für eine Liste von Phasenpunkt-Datensätzen eines Parents und Panels.

    records: dicts mit family, point, value, discounted_return, success, baseline_return.
    """
    c = criteria
    families = sorted({r["family"] for r in records})
    family_index = {f: i for i, f in enumerate(families)}
    fam = np.array([family_index[r["family"]] for r in records])
    value = np.array([r["value"] for r in records], np.float64)
    target = np.array([r["discounted_return"] for r in records], np.float64)
    success = np.array([r["success"] for r in records], bool)
    baseline = np.array([r["baseline_return"] for r in records], np.float64)
    finite = bool(np.isfinite(value).all())
    points = sorted({r["point"] for r in records})
    per_point, eligible = [], []
    for point in points:
        mask = np.array([r["point"] == point for r in records])
        k, n = int(success[mask].sum()), int(mask.sum())
        entry = dict(point=point, episodes=n, successes=k, failures=n - k,
                     mean_value=float(value[mask].mean()), mean_return=float(target[mask].mean()),
                     baseline_return=float(baseline[mask][0]),
                     eligible=k >= c["min_successes"] and n - k >= c["min_failures"])
        if entry["eligible"] and finite:
            matrix = auc_matrix(value[mask], success[mask])
            entry["auc"] = float(weighted_auc(matrix, np.ones(k), np.ones(n - k)))
            eligible.append((point, n, matrix, fam[mask][success[mask]], fam[mask][~success[mask]]))
        per_point.append(entry)
    result = dict(families=len(families), point_records=len(records), finite=finite, points=per_point,
                  eligible_points=len(eligible))
    if not finite:
        result.update(passed=False, reason="nicht endliche Vorhersagen")
        return result
    weights = np.array([n for _, n, *_ in eligible], np.float64)
    aucs = np.array([e["auc"] for e in per_point if "auc" in e])
    result["weighted_auc"] = float((weights * aucs).sum() / weights.sum()) if eligible else None
    error_critic, error_baseline = (value - target) ** 2, (baseline - target) ** 2
    result.update(mse_critic=float(error_critic.mean()), mse_baseline=float(error_baseline.mean()),
                  mse_difference=float((error_critic - error_baseline).mean()))
    result["ece"], result["ece_bins"] = ece(value, target, c["ece_bins"])

    rng = np.random.default_rng(c["bootstrap_seed"])
    counts = np.stack([np.bincount(rng.integers(len(families), size=len(families)), minlength=len(families))
                       for _ in range(c["bootstrap_draws"])]).astype(np.float64)
    record_weights = counts[:, fam]
    difference = ((record_weights * (error_critic - error_baseline)).sum(1) / record_weights.sum(1))
    alpha = (1 - c["interval"]) / 2
    result["mse_difference_interval"] = [float(np.quantile(difference, alpha)), float(np.quantile(difference, 1 - alpha))]
    if eligible:
        point_auc = np.stack([weighted_auc(matrix, counts[:, pos], counts[:, neg])
                              for _, _, matrix, pos, neg in eligible], 1)
        point_n = np.stack([counts[:, pos].sum(1) + counts[:, neg].sum(1) for *_, pos, neg in eligible], 1)
        defined = np.isfinite(point_auc)
        draw = (np.where(defined, point_auc, 0) * point_n * defined).sum(1) / (point_n * defined).sum(1)
        result["weighted_auc_interval"] = [float(np.nanquantile(draw, alpha)), float(np.nanquantile(draw, 1 - alpha))]
        result["bootstrap_undefined_point_draws"] = int((~defined).sum())
    checks = dict(
        finite=finite,
        assessable=len(eligible) >= c["min_points"],
        more_than_phase=bool(len(eligible) >= c["min_points"] and result["weighted_auc"] >= c["auc_min"]
                             and result["weighted_auc_interval"][0] > c["auc_lower_gt"]),
        better_than_phase=bool(result["mse_difference_interval"][1] < 0),
        calibration=bool(result["ece"] <= c["ece_max"]),
    )
    result.update(checks=checks, passed=all(checks.values()))
    return result


def baseline_table(episodes):
    """Phasen-Baseline aus den Critic-Daten eines Parents: Erfolgsquote und mittlerer
    diskontierter Return je Phasenpunkt unter den Episoden, die ihn erreichen."""
    table = {}
    for arrays, success in episodes:
        for point, frame in phase_points(arrays["stage"], arrays["phase"]).items():
            entry = table.setdefault(point, dict(episodes=0, successes=0, return_sum=0.0))
            entry["episodes"] += 1
            entry["successes"] += int(success)
            entry["return_sum"] += float(arrays["discounted_return"][frame])
    overall = sum(s for _, s in episodes) / len(episodes)
    return {p: dict(episodes=e["episodes"], success_rate=e["successes"] / e["episodes"],
                    mean_return=e["return_sum"] / e["episodes"]) for p, e in sorted(table.items())}, overall


# ---------------------------------------------------------------- Vortraining

def critic_inputs(arrays):
    return arrays["critic_state"].astype(np.float32), arrays["parent_action"][:, ACTION_INDEX].astype(np.float32)


def pretrain(torch, core, states, actions, targets, parent, deadline, out, log=None):
    """20.000 Monte-Carlo-Regressionsschritte wie Learner.warm (base/core.py), ohne Early Stopping."""
    c = PRETRAIN
    mean = states.astype(np.float64).mean(0)
    std = states.astype(np.float64).std(0)
    torch.manual_seed(7100 + parent)
    critic = core.TwinQ(mean, std, c["critic_width"])
    optimizer = torch.optim.AdamW(critic.parameters(), lr=c["critic_lr"], weight_decay=c["weight_decay"])
    rng = np.random.default_rng(7200 + parent)
    s, a, y = (torch.from_numpy(np.ascontiguousarray(v)) for v in (states, actions, targets.astype(np.float32)))
    history, window = [], []
    started = time.perf_counter()
    for update in range(1, c["updates"] + 1):
        if update % 100 == 1:
            cd_check_stop(out, deadline)
        ids = torch.from_numpy(rng.integers(len(states), size=c["batch_size"]))
        q1, q2 = critic(s[ids], a[ids])
        loss = (q1 - y[ids]).square().mean() + (q2 - y[ids]).square().mean()
        if not torch.isfinite(loss):
            raise FloatingPointError(f"Nicht endlicher Critic-Loss bei Update {update}")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        norm = torch.nn.utils.clip_grad_norm_(critic.parameters(), c["gradient_clip"])
        if not torch.isfinite(norm):
            raise FloatingPointError(f"Nicht endliche Gradientennorm bei Update {update}")
        optimizer.step()
        window.append(float(loss.detach()))
        if update % c["log_every"] == 0:
            history.append(dict(update=update, mean_loss=float(np.mean(window)),
                                seconds=time.perf_counter() - started))
            window = []
            if log:
                log(history[-1])
    return critic, optimizer, history, time.perf_counter() - started


def cd_check_stop(out, deadline):
    if (out / "STOP").exists():
        raise InterruptedError("STOP requested")
    if time.time() >= deadline:
        raise TimeoutError("Wall-clock budget exhausted")


def predict(torch, critic, states, actions):
    values = []
    with torch.no_grad():
        for j in range(0, len(states), 4096):
            q1, q2 = critic(torch.from_numpy(states[j:j + 4096]), torch.from_numpy(actions[j:j + 4096]))
            values.append(torch.minimum(q1, q2).numpy().astype(np.float64))
    return np.concatenate(values) if values else np.zeros(0)


# ---------------------------------------------------------------- Laufplan

def panels():
    manifest = read(HERE / "difficulty_panels_v1.json")
    expected_rule = (HERE / "difficulty_v1.sha256").read_text(encoding="utf-8").split()[0]
    if manifest["difficulty_sha256"] != expected_rule or digest((HERE / "difficulty_v1.json").read_bytes()) != expected_rule:
        raise ValueError("Schwierigkeitsregel weicht vom eingefrorenen SHA-256 ab")
    splits = {s["id"]: s for s in read(HERE / "splits.json")["splits"]}
    result = {}
    for panel in PANELS:
        seeds = sorted(int(f[0]) for f in manifest["panels"][panel]["families"])
        first, last = splits[panel]["first"], splits[panel]["last"]
        if len(seeds) != PANEL_SIZES[panel] or len(set(seeds)) != len(seeds) or not all(first <= s <= last for s in seeds):
            raise ValueError(f"Panel {panel} weicht vom Protokoll ab")
        if panel == "validation_hard" and any(f[1] != "schwer" for f in manifest["panels"][panel]["families"]):
            raise ValueError("Schwieriges Panel enthält nicht schwere Familien")
        result[panel] = seeds
    return result


def plan(registry, controller):
    families = panels()
    sources = [Path(__file__), HERE / "critic_data.py", HERE / "calibration.py", HERE / "splits.json",
               HERE / "splits_v2.json", HERE / "PROTOCOL.md", HERE / "difficulty_panels_v1.json",
               HERE / "difficulty_v1.json", BASE_CORE, Path(registry.__file__)]
    return {
        "task": "N2-2", "protocol": "protocol_v1",
        "critic_data": dict(directory=DATA.relative_to(ROOT).as_posix(), dataset_sha256=DATASET_SHA256),
        "parents": {str(seed): entry for seed, entry in registry.frozen_abc_a().items()},
        "schedule": [[scene, parent, panel] for panel in PANELS for scene in families[panel] for parent in PARENTS],
        "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sources},
        "pretraining": PRETRAIN, "criteria": CRITERIA, "action_index": ACTION_INDEX,
        "rollout": dict(device="cpu", horizon_frames=cd.HORIZON, success_frames=cd.STABLE, gamma=GAMMA,
                        exploration="keine; ausgeführte Aktion = Parentaktion", optimizer_updates=0,
                        episode_function="critic_data.episode (N2-1)"),
        "phase_points": "erster Frame je erreichter Kombination (Stufe, Policy-Phase); Frame 0 enthalten",
        "baseline": "je Phasenpunkt mittlerer diskontierter Return bzw. Erfolgsquote in den Critic-Daten desselben Parents; fehlt der Punkt: Gesamterfolgsquote des Parents",
        "value": "V(s) = min(Q1, Q2)(s, a_parent(s)) mit a_parent = gespeicherte Parentaktion (x, y, z, Greifer)",
    }


def load_critic_data(parent):
    """Alle 300 N2-1-Episoden eines Parents mit Hash- und Vertragsprüfung laden."""
    summary = read(DATA / "summary.json")
    if summary["dataset_sha256"] != DATASET_SHA256 or summary["completed_episodes"] != cd.EXPECTED:
        raise ValueError("N2-1-Datensatz weicht vom dokumentierten Hash ab")
    schedule = read(DATA / "config.json")["schedule"]
    scenes, episodes = {}, []
    for index, (scene, owner) in enumerate(schedule):
        if owner != parent:
            continue
        row = cd.load_episode(DATA, index, schedule, scenes)
        arrays = cd.decode(cd.paths(DATA, index)[0].read_bytes())
        episodes.append((arrays, bool(row["success"])))
    if len(episodes) != cd.FAMILIES:
        raise ValueError("Unerwartete Episodenzahl in den Critic-Daten")
    return episodes


def critic_paths(out, parent):
    return out / "critics" / f"parent_{parent}.pt", out / "critics" / f"parent_{parent}.json"


def save_critic(torch, out, parent, critic, optimizer, history, seconds, frames, train_mse, config_sha):
    weights_path, meta_path = critic_paths(out, parent)
    temporary = weights_path.with_suffix(".tmp")
    torch.save(dict(critic=critic.state_dict(), critic_optimizer=optimizer.state_dict(),
                    parent=parent, updates=PRETRAIN["updates"], pretraining=PRETRAIN), temporary)
    temporary.replace(weights_path)
    meta = dict(parent=parent, updates=PRETRAIN["updates"], batch_size=PRETRAIN["batch_size"],
                train_frames=frames, train_episodes=cd.FAMILIES, wall_seconds=seconds,
                updates_per_second=PRETRAIN["updates"] / seconds, loss_history=history,
                in_sample_return_mse=train_mse, normalization_from="Critic-Datenframes dieses Parents (N2-1)",
                config_sha256=config_sha, weights_sha256=digest(weights_path.read_bytes()))
    write(meta_path, meta)
    return meta


def load_critic(torch, core, out, parent):
    weights_path, meta_path = critic_paths(out, parent)
    meta = read(meta_path)
    if digest(weights_path.read_bytes()) != meta["weights_sha256"]:
        raise ValueError(f"Critic {parent} weicht vom eingefrorenen SHA-256 ab")
    checkpoint = torch.load(weights_path, map_location="cpu", weights_only=True)
    state = checkpoint["critic"]
    critic = core.TwinQ(state["mean"].numpy(), state["std"].numpy(), PRETRAIN["critic_width"])
    critic.load_state_dict(state)
    return critic.eval().requires_grad_(False), meta


def check_row(row, index, schedule, scenes):
    if [row["scene_seed"], row["parent_seed"], row["panel"]] != schedule[index] or row["index"] != index:
        raise ValueError(f"Unerwartete Szenen-/Parent-Zuordnung in Episode {index}")
    if scenes.setdefault(row["scene_seed"], row["initial_sha256"]) != row["initial_sha256"]:
        raise ValueError(f"Startzustände unterscheiden sich für Szene {row['scene_seed']}")


def load_episode(out, index, schedule, scenes):
    data_path, row_path = cd.paths(out, index)
    row = read(row_path)
    data = data_path.read_bytes()
    if digest(data) != row["arrays_sha256"]:
        raise ValueError(f"Hash der Episode {index} stimmt nicht")
    check_row(row, index, schedule, scenes)
    arrays = cd.decode(data)
    cd.check_arrays(arrays, row)
    return row, arrays


def evaluate(torch, core, out, schedule):
    """Auswertung nach §6 aus den gespeicherten Rollouts und eingefrorenen Critics."""
    scenes, result = {}, {}
    episodes = [load_episode(out, i, schedule, scenes) for i in range(len(schedule))]
    for parent in PARENTS:
        critic, meta = load_critic(torch, core, out, parent)
        table, overall = baseline_table(load_critic_data(parent))
        entry = dict(critic_weights_sha256=meta["weights_sha256"], baseline_overall_success_rate=overall,
                     baseline_points=table)
        for panel in PANELS:
            records, all_finite, frames, fallback = [], True, 0, 0
            chosen = [(row, arrays) for row, arrays in episodes
                      if row["parent_seed"] == parent and row["panel"] == panel]
            for row, arrays in chosen:
                values = predict(torch, critic, *critic_inputs(arrays))
                all_finite &= bool(np.isfinite(values).all())
                frames += len(values)
                for point, frame in phase_points(arrays["stage"], arrays["phase"]).items():
                    known = point in table
                    fallback += not known
                    records.append(dict(family=row["scene_seed"], point=point, value=float(values[frame]),
                                        discounted_return=float(arrays["discounted_return"][frame]),
                                        success=bool(row["success"]),
                                        baseline_return=table[point]["mean_return"] if known else overall,
                                        baseline_success_rate=table[point]["success_rate"] if known else overall))
            metrics = assess(records)
            metrics["checks"] = dict(metrics.get("checks", {}), finite=bool(all_finite and metrics["finite"]))
            metrics["passed"] = bool(metrics.get("passed", False) and all_finite)
            metrics.update(episodes=len(chosen), successes=sum(r["success"] for r, _ in chosen),
                           frames_predicted=frames, all_frames_finite=all_finite, baseline_fallback_records=fallback)
            entry[panel] = metrics
        entry["passed"] = entry["validation_normal"]["passed"]
        result[str(parent)] = entry
    return result


# ---------------------------------------------------------------- Worker, Supervisor, Monitor

def summarize(out, rows, critics, assessment, active_wall_seconds, config_path):
    by = {}
    for panel in PANELS:
        for parent in PARENTS:
            chosen = [r for r in rows if r["panel"] == panel and r["parent_seed"] == parent]
            by.setdefault(panel, {})[str(parent)] = dict(
                episodes=len(chosen), successes=sum(r["success"] for r in chosen),
                terminations={t: sum(r["termination"] == t for r in chosen) for t in cd.TERMINATIONS},
                frames=sum(r["frames"] for r in chosen))
    rollout_seconds = sum(r["elapsed_seconds"] for r in rows)
    return dict(
        planned_episodes=EXPECTED, completed_episodes=len(rows), by_panel=by,
        rollout_episode_seconds=rollout_seconds, rollout_episodes_per_hour=3600 * len(rows) / rollout_seconds,
        pretraining={str(p): dict(updates=m["updates"], wall_seconds=m["wall_seconds"],
                                  updates_per_second=m["updates_per_second"], weights_sha256=m["weights_sha256"],
                                  final_mean_loss=m["loss_history"][-1]["mean_loss"],
                                  in_sample_return_mse=m["in_sample_return_mse"]) for p, m in critics.items()},
        critic_updates_total=sum(m["updates"] for m in critics.values()), rollout_optimizer_updates=0,
        assessment=assessment,
        decision=dict(per_parent={p: a["passed"] for p, a in assessment.items()},
                      passed=all(a["passed"] for a in assessment.values())),
        trajectories_sha256=digest("\n".join(r["trajectory_sha256"] for r in rows).encode()),
        dataset_sha256=digest("\n".join(r["arrays_sha256"] for r in rows).encode()),
        rows_sha256=digest(b"".join(cd.paths(out, i)[1].read_bytes() for i in range(len(rows)))),
        config_sha256=digest(config_path.read_bytes()), worker_wall_seconds=active_wall_seconds,
        hash_contract="dataset_sha256 = SHA-256 der zeilenweise verketteten arrays_sha256 in Episodenreihenfolge",
    )


def worker(deadline):
    status_path = OUT / "status.json"
    previous = read(status_path) if status_path.exists() else {}
    previous_wall = previous.get("active_wall_seconds", 0)
    started = time.perf_counter()
    state = dict(state="INITIALIZING", worker=identity(os.getpid()), planned_episodes=EXPECTED,
                 completed_episodes=previous.get("completed_episodes", 0),
                 critics_done=previous.get("critics_done", 0), optimizer_updates=previous.get("optimizer_updates", 0))

    def status(**fields):
        state.update(fields, heartbeat_unix=time.time(),
                     active_wall_seconds=previous_wall + time.perf_counter() - started)
        state.update(stage=STAGES[state["state"]], rendered=state["completed_episodes"],
                     render_total=EXPECTED, split="validation_normal+validation_hard")
        write(status_path, state)

    status()
    try:
        registry, base, torch, controller, adapter = cd.setup(OUT)
        core = load_module("critic_base_core", BASE_CORE)
        config = plan(registry, controller)
        config["software"] = {name: getattr(sys.modules[name], "__version__", None)
                              for name in ("torch", "numpy", "robosuite", "mujoco")}
        config_path = OUT / "config.json"
        if config_path.exists():
            if read(config_path) != config:
                raise ValueError("Provenienz des bestehenden Laufs geändert")
        else:
            write(config_path, config)
        config_sha = digest(config_path.read_bytes())
        # (1) Vortraining, Einheit der Fortsetzung ist ein vollständig gespeicherter Critic.
        torch.set_num_threads(PRETRAIN["torch_threads"])
        critics = {}
        for parent in PARENTS:
            weights_path, meta_path = critic_paths(OUT, parent)
            if meta_path.exists():
                load_critic(torch, core, OUT, parent)
                critics[str(parent)] = read(meta_path)
                continue
            status(state="TRAINING", training_parent=parent)
            episodes = load_critic_data(parent)
            states = np.concatenate([critic_inputs(a)[0] for a, _ in episodes])
            actions = np.concatenate([critic_inputs(a)[1] for a, _ in episodes])
            targets = np.concatenate([a["discounted_return"] for a, _ in episodes])
            del episodes
            critic, optimizer, history, seconds = pretrain(
                torch, core, states, actions, targets, parent, deadline, OUT,
                log=lambda h: status(training_update=h["update"], training_loss=h["mean_loss"]))
            train_mse = float(np.mean((predict(torch, critic.eval(), states, actions) - targets) ** 2))
            critics[str(parent)] = save_critic(torch, OUT, parent, critic, optimizer, history, seconds,
                                               len(states), train_mse, config_sha)
            status(critics_done=len(critics), optimizer_updates=PRETRAIN["updates"] * len(critics))
        status(critics_done=len(critics), optimizer_updates=PRETRAIN["updates"] * len(critics))
        # (2) Validierungsrollouts mit eingefrorenen Parents, 0 Updates.
        models = {int(seed): registry.restore_abc_a_for_inference(int(seed), entry)
                  for seed, entry in config["parents"].items()}
        schedule = config["schedule"]
        scenes, rows = {}, []
        while len(rows) < EXPECTED and cd.paths(OUT, len(rows))[1].exists():
            rows.append(load_episode(OUT, len(rows), schedule, scenes)[0])
        if any(int(p.stem) >= len(rows) for p in (OUT / "episodes").glob("*.json")):
            raise ValueError("Kanonische Episodenfolge unterbrochen")
        status(state="EVALUATING", completed_episodes=len(rows))
        for index in range(len(rows), EXPECTED):
            scene, parent, panel = schedule[index]
            row, arrays = cd.episode(base, controller, adapter, torch, *models[parent], scene, parent, deadline, OUT)
            data = cd.encode(arrays)
            row.update(index=index, scene_seed=scene, parent_seed=parent, panel=panel, arrays_sha256=digest(data))
            check_row(row, index, schedule, scenes)
            cd.check_arrays(arrays, row)
            data_path, row_path = cd.paths(OUT, index)
            cd.write_bytes(data_path, data)
            write(row_path, row)
            rows.append(row)
            status(completed_episodes=len(rows))
        # (3) Auswertung nach §6.
        status(state="ASSESSING")
        assessment = evaluate(torch, core, OUT, schedule)
        summary = summarize(OUT, rows, critics, assessment, previous_wall + time.perf_counter() - started, config_path)
        write(OUT / "summary.json", summary)
        status(state="COMPLETE")
    except (InterruptedError, TimeoutError) as error:
        status(state="PAUSED", reason=str(error))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def preconditions():
    """Freigabe, Pause, Protokollstatus und N2-1-Abschluss vor dem Start prüfen."""
    plan_text = (HERE / "NACHTPLAN.md").read_text(encoding="utf-8")
    if "- [x] N2-2/N2-3" not in plan_text:
        raise ValueError("Freigabe N2-2/N2-3 im Nachtplan fehlt")
    if "Gesamtpause: nein" not in (HERE / "STATUS.md").read_text(encoding="utf-8"):
        raise ValueError("Gesamtpause aktiv oder unklar")
    if "**Status: FREIGEGEBEN**" not in (HERE / "PROTOCOL.md").read_text(encoding="utf-8"):
        raise ValueError("Protokoll nicht freigegeben")
    if read(DATA / "supervisor_status.json")["state"] != "COMPLETE" or read(DATA / "summary.json")["dataset_sha256"] != DATASET_SHA256:
        raise ValueError("N2-1 nicht abgeschlossen oder Datensatzhash abweichend")


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
        (OUT / "episodes").mkdir()
        (OUT / "critics").mkdir()
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
    """Supervisor als vom aufrufenden Agenten losgelösten Prozess starten."""
    if time.time() >= time_argument(cutoff):
        raise ValueError("Startfenster geschlossen")
    preconditions()
    arguments = [sys.executable, str(Path(__file__)), command, "--cutoff", cutoff, "--deadline", deadline]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    with (RESULTS / "critic_validation_n2_2_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags | 0x01000000)
        except OSError:  # Job erlaubt kein CREATE_BREAKAWAY_FROM_JOB
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
    print(json.dumps(identity(child.pid)))
    return 0


def verify(config, summary):
    """Einmaliger Endabgleich: Rohepisoden, Critic-Hashes und Auswertung neu berechnen."""
    import torch
    torch.set_num_threads(PRETRAIN["torch_threads"])
    torch.use_deterministic_algorithms(True)
    core = load_module("critic_base_core", BASE_CORE)
    scenes, rows = {}, []
    for index in range(EXPECTED):
        rows.append(load_episode(OUT, index, config["schedule"], scenes)[0])
    critics = {str(p): read(critic_paths(OUT, p)[1]) for p in PARENTS}
    assessment = evaluate(torch, core, OUT, config["schedule"])
    expected = summarize(OUT, rows, critics, assessment, summary["worker_wall_seconds"], OUT / "config.json")
    if json.loads(json.dumps(expected)) != summary or len(scenes) != sum(PANEL_SIZES.values()):
        raise ValueError("Zusammenfassung stimmt nicht mit Rohepisoden, Critics und Auswertung überein")


def new_errors(previous):
    path = OUT / "worker.log"
    if not path.exists():
        return None, 0, []
    with path.open("rb") as stream:
        stat = path.stat()
        file_id = [stat.st_dev, stat.st_ino]
        offset = previous.get("log_offset", 0) if previous.get("log_id") == file_id else 0
        stream.seek(offset if offset <= stat.st_size else 0)
        data = stream.read()
        complete = data.rfind(b"\n") + 1
        errors = [line.strip() for line in data[:complete].decode(errors="replace").splitlines()
                  if re.search(r"Traceback|(?:Error|Exception):|nonfinite|nicht endlich|out of memory", line, re.I)]
        return file_id, stream.tell() - len(data) + complete, errors


def monitor():
    supervisor_path, worker_path = OUT / "supervisor_status.json", OUT / "status.json"
    if not supervisor_path.is_file():
        print("OFFEN | Kein Supervisorstatus für N2-2")
        return 0 if not OUT.exists() else 2
    supervisor = read(supervisor_path)
    running = alive(supervisor["supervisor"])
    worker_state = read(worker_path) if worker_path.is_file() else {}
    worker_running = alive(worker_state.get("worker"))
    previous_path = OUT / "monitor_state.json"
    previous = read(previous_path) if previous_path.is_file() else {}
    file_id, offset, errors = new_errors(previous)
    completed = start = previous.get("completed", 0)
    successes = previous.get("successes", 0)
    while completed < EXPECTED and cd.paths(OUT, completed)[1].is_file():
        successes += read(cd.paths(OUT, completed)[1])["success"]
        completed += 1
    critics = sum(critic_paths(OUT, p)[1].is_file() for p in PARENTS)
    marker = [completed, critics, worker_state.get("training_update"), worker_state.get("state")]
    now = time.time()
    progress_time = now if marker != previous.get("marker") else previous.get("progress_time", now)
    output = dict(supervisor=supervisor["supervisor"], supervisor_alive=running, supervisor_state=supervisor["state"],
                  worker=worker_state.get("worker"), worker_alive=worker_running,
                  worker_state=worker_state.get("state"), critics_done=critics,
                  training_parent=worker_state.get("training_parent"),
                  training_update=worker_state.get("training_update"),
                  completed=completed, planned=EXPECTED, new_episodes=completed - start, successes=successes,
                  next_episode=None if completed == EXPECTED else completed,
                  deadline_unix=supervisor["deadline_unix"], errors=errors)
    state = supervisor["state"]
    result_verified = previous.get("result_verified", False)
    if (state == "COMPLETE" and worker_state.get("state") == "COMPLETE" and not worker_running
            and supervisor.get("worker_exitcode") == 0 and completed == EXPECTED):
        summary = read(OUT / "summary.json")
        if not result_verified:
            verify(read(OUT / "config.json"), summary)
        result_verified = True
        code = 0
        output.update(status="COMPLETE", decision=summary["decision"],
                      successes_by_panel={pn: {p: v["successes"] for p, v in d.items()}
                                          for pn, d in summary["by_panel"].items()},
                      dataset_sha256=summary["dataset_sha256"], critic_updates_total=summary["critic_updates_total"])
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
    write(previous_path, dict(completed=completed, successes=successes, marker=marker, progress_time=progress_time,
                              checked_unix=now, log_id=file_id, log_offset=offset, result_verified=result_verified))
    print(json.dumps(output, ensure_ascii=True))
    return code


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
    commands.add_parser("monitor")
    commands.add_parser("check")
    args = parser.parse_args()
    if args.command == "start":
        time_argument(args.deadline)
        return detach(args.mode, args.cutoff, args.deadline)
    if args.command == "_worker":
        if not (OUT / "supervisor.lock").exists():
            parser.error("Worker nur über den Supervisor starten")
        worker(args.deadline)
        return 0
    if args.command == "check":
        preconditions()
        families = panels()
        print(json.dumps({k: [len(v), v[0], v[-1]] for k, v in families.items()}))
        return 0
    if args.command == "monitor":
        return monitor()
    return supervise(args.cutoff, args.deadline, args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
