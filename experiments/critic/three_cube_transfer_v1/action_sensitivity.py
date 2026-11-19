"""D1a nach PROTOCOL_V2 §A. Nur Inferenz auf den festen N2-3-Driftframes."""

from datetime import datetime, timedelta
from pathlib import Path
import time

import numpy as np

import ac_smoke as smoke
import critic_validation as cv
from calibration import HERE, ROOT, digest, load_module, read, write


OUT = smoke.RESULTS / "action_sensitivity_d1a"
K = 32
PHASES = range(7)
MIN_GAP = 1e-3


def draw_actions(center, delta, rng):
    width = np.full_like(center, smoke.SMOKE["gripper_bound"])
    width[:, :3] = np.minimum(delta, 0.5 * np.abs(center[:, :3]))
    low = np.maximum(-1, center - width)[:, None, :]
    high = np.minimum(1, center + width)[:, None, :]
    actions = rng.uniform(low, high, size=(len(center), K, 4)).astype(np.float32)
    if not ((low <= actions) & (actions <= high)).all():
        raise ValueError("Aktion außerhalb des Ausführungsbereichs")
    return actions


def phase_metrics(advantages):
    if not np.isfinite(advantages).all():
        raise ValueError("Nicht endlicher Vorteil")
    ordered = np.sort(advantages, axis=1)
    unique_best = (ordered[:, -1] - ordered[:, -2]) > MIN_GAP
    return dict(
        frames=len(advantages),
        actions=advantages.size,
        std=float(advantages.std()),
        median_frame_std=float(np.median(advantages.std(axis=1))),
        abs_q90=float(np.quantile(np.abs(advantages), 0.90)),
        unique_best=int(unique_best.sum()),
    )


def measure_parent(torch, core, registry, config, parent):
    probe = smoke.probe_frames(parent)
    if np.bincount(probe["phase"], minlength=len(PHASES)).tolist() != [64] * len(PHASES):
        raise ValueError(f"Unerwartete Anzahl Driftframes für Parent {parent}")
    actor, _, _ = registry.restore_abc_a_for_inference(parent, config["parents"][str(parent)])
    center, _ = actor(torch.from_numpy(probe["x"]), torch.from_numpy(probe["phase"]))
    center = center.numpy()
    if not (np.isfinite(center) & (np.abs(center) <= 1)).all():
        raise ValueError(f"Ungültige Parentaktion für Parent {parent}")

    il, meta = cv.load_critic(torch, core, cv.OUT, parent)
    if meta["weights_sha256"] != config["il_critic_sha256"][str(parent)]:
        raise ValueError(f"N2-2-Critic {parent} weicht vom eingefrorenen N2-3-Start ab")
    torch.manual_seed(7100 + parent)
    new = core.TwinQ(il.mean.numpy(), il.std.numpy(), cv.PRETRAIN["critic_width"])
    critics = {"IL": il, "neu": new.eval().requires_grad_(False)}
    q_parent = {variant: cv.predict(torch, critic, probe["state"], center)
                for variant, critic in critics.items()}
    rng = np.random.default_rng(7500 + parent)
    states = np.repeat(probe["state"], K, axis=0)
    rows, measurements = [], {}
    for delta in smoke.DELTAS:
        actions = draw_actions(center, delta, rng).reshape(-1, 4)
        for variant, critic in critics.items():
            q = cv.predict(torch, critic, states, actions).reshape(-1, K)
            advantages = q - q_parent[variant][:, None]
            rows.extend(dict(parent=parent, phase=phase, delta=delta, variant=variant,
                             **phase_metrics(advantages[probe["phase"] == phase]))
                        for phase in PHASES)
            measurements[f"p{parent}_d{delta:.2f}_{variant}"] = advantages
    measurements[f"p{parent}_phase"] = probe["phase"]
    return rows, measurements


def main():
    started = time.perf_counter()
    berlin = datetime.now().astimezone()
    if not (berlin.utcoffset() == timedelta(hours=1)
            and datetime(2026, 11, 19, 22, tzinfo=berlin.tzinfo) <= berlin
            < datetime(2026, 11, 20, 7, 30, tzinfo=berlin.tzinfo)):
        raise SystemExit("D1a liegt außerhalb des Startfensters für Nacht 2")
    if "Gesamtpause: nein" not in (HERE / "STATUS.md").read_text(encoding="utf-8").splitlines():
        raise SystemExit("Gesamtpause aktiv oder unklar")

    # Exklusiv anlegen, damit auch ein Teilstand einen Doppelstart verhindert.
    OUT.mkdir(exist_ok=False)
    import torch

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    config_path = smoke.OUT / "config.json"
    config = read(config_path)
    for path, expected in config["source_sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"Eingefrorene N2-3-Quelle wurde verändert: {path}")
    registry = load_module("d1_registry", ROOT / "experiments/curriculum/registry.py")
    core = load_module("d1_critic", cv.BASE_CORE)
    rows, measurements = [], {}
    with torch.inference_mode():
        for parent in smoke.PARENTS:
            parent_rows, parent_values = measure_parent(torch, core, registry, config, parent)
            rows.extend(parent_rows)
            measurements.update(parent_values)
    raw_path = OUT / "advantages.npz"
    np.savez_compressed(raw_path, **measurements)
    summary = dict(task="D1a", rows=rows, optimizer_updates=0, rollouts=0,
                   dataset_sha256=cv.DATASET_SHA256, critic_sha256=config["il_critic_sha256"],
                   n2_3_config_sha256=digest(config_path.read_bytes()),
                   protocol_sha256=digest((HERE / "PROTOCOL_V2.md").read_bytes()),
                   script_sha256=digest(Path(__file__).read_bytes()),
                   advantages_sha256=digest(raw_path.read_bytes()), seconds=time.perf_counter() - started)
    write(OUT / "summary.json", summary)
    advantages = sum(row["actions"] for row in rows)
    print(f"D1a COMPLETE | {len(rows)} Gruppen | {advantages} Vorteile | {summary['seconds']:.2f} s")


if __name__ == "__main__":
    main()
