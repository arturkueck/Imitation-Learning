"""D1b: dieselbe Aktionsprobe wie D1a mit dem eingefrorenen Critic IL-v2."""

from datetime import datetime, timedelta
from pathlib import Path
import sys
import time

import numpy as np

from action_sensitivity import K, OUT as D1A, PHASES, draw_actions, phase_metrics
import ac_smoke as smoke
from calibration import HERE, ROOT, digest, load_module, read, write
import critic_validation as cv


OUT = smoke.RESULTS / "action_sensitivity_d1b"
N2_2B = smoke.RESULTS / "critic_validation_n2_2b"
D1A_RAW_SHA = "5094b4290a0370013ec9e5fc5d114edc75972166008cf9e5751976f57f77b1a3"
N2_2B_SUMMARY_SHA = "767bccfcfb9a972bbb064039c2eb1abaa55477e41d5aac69e038c23c4b142e94"


def summarize(values, reference):
    rows, stages = [], []
    expected_keys = {f"p{p}_phase" for p in smoke.PARENTS}
    for delta in smoke.DELTAS:
        pooled = {"IL-v2": [], "neu": []}
        for parent in smoke.PARENTS:
            prefix = f"p{parent}_d{delta:.2f}"
            phases = values[f"p{parent}_phase"]
            if not np.array_equal(phases, np.repeat(list(PHASES), 64)):
                raise ValueError(f"Unerwartete Driftframes für Parent {parent}")
            for variant in pooled:
                key = f"{prefix}_{variant}"
                expected_keys.add(key)
                advantages = values[key]
                if advantages.shape != (len(phases), K):
                    raise ValueError(f"Ungültiges Format: {key}")
                if variant == "neu" and not np.array_equal(advantages, reference[key]):
                    raise ValueError(f"Zufallsreferenz weicht von D1a ab: {key}")
                pooled[variant].append(advantages)
                rows.extend(dict(parent=parent, phase=phase, delta=delta, variant=variant,
                                 **phase_metrics(advantages[phases == phase])) for phase in PHASES)
        il, new = (phase_metrics(np.concatenate(pooled[variant])) for variant in pooled)
        il_std, new_std = il["median_frame_std"], new["median_frame_std"]
        stages.append(dict(delta=delta, il=il, new=new, ratio=il_std / new_std,
                           passed=bool(il_std >= 0.01 and il_std >= 1.5 * new_std)))
    if set(values) != expected_keys:
        raise ValueError("Unerwartete Einträge in den gespeicherten Vorteilen")
    return dict(rows=rows, stages=stages, passed=any(stage["passed"] for stage in stages))


def main():
    reference_path = D1A / "advantages.npz"
    if digest(reference_path.read_bytes()) != D1A_RAW_SHA:
        raise ValueError("D1a-Referenz weicht vom dokumentierten SHA-256 ab")
    with np.load(reference_path, allow_pickle=False) as reference:
        if sys.argv[1:] == ["--verify"]:
            summary = read(OUT / "summary.json")
            raw_path = OUT / "advantages.npz"
            if digest(raw_path.read_bytes()) != summary["advantages_sha256"]:
                raise ValueError("SHA-256 der gespeicherten Vorteile stimmt nicht")
            with np.load(raw_path, allow_pickle=False) as values:
                if any(summary[key] != expected for key, expected in summarize(values, reference).items()):
                    raise ValueError("Neuberechnete Gruppen oder Entscheidung weichen ab")
            print(f"VERIFY OK | {len(summary['rows'])} Gruppen | bestanden: {summary['passed']}")
            return
        if sys.argv[1:]:
            raise SystemExit("Aufruf ohne Argumente oder mit --verify")
        run(reference)


def run(reference):
    started = time.perf_counter()
    prior_path = N2_2B / "summary.json"
    if digest(prior_path.read_bytes()) != N2_2B_SUMMARY_SHA:
        raise ValueError("N2-2b-Abschluss stimmt nicht mit dem dokumentierten SHA-256 überein")
    prior = read(prior_path)
    if not prior["decision"]["passed"]:
        raise ValueError("N2-2b hat §6 nicht bestanden")
    config_path = smoke.OUT / "config.json"
    config = read(config_path)
    for path, expected in config["source_sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"Eingefrorene N2-3-Quelle wurde verändert: {path}")

    berlin = datetime.now().astimezone()
    if not (berlin.utcoffset() == timedelta(hours=1)
            and datetime(2026, 11, 19, 22, tzinfo=berlin.tzinfo) <= berlin
            < datetime(2026, 11, 20, 7, 30, tzinfo=berlin.tzinfo)):
        raise SystemExit("D1b liegt außerhalb des Startfensters für Nacht 2")
    if "Gesamtpause: nein" not in (HERE / "STATUS.md").read_text(encoding="utf-8").splitlines():
        raise SystemExit("Gesamtpause aktiv oder unklar")
    OUT.mkdir(exist_ok=False)

    import torch

    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    registry = load_module("d1b_registry", ROOT / "experiments/curriculum/registry.py")
    core = load_module("d1b_critic", cv.BASE_CORE)
    values, weights = {}, {}
    with torch.inference_mode():
        for parent in smoke.PARENTS:
            key = str(parent)
            probe = smoke.probe_frames(parent)
            actor, _, _ = registry.restore_abc_a_for_inference(parent, config["parents"][key])
            center, _ = actor(torch.from_numpy(probe["x"]), torch.from_numpy(probe["phase"]))
            center = center.numpy()
            if not (np.isfinite(center) & (np.abs(center) <= 1)).all():
                raise ValueError(f"Ungültige Parentaktion für Parent {parent}")
            il, meta = cv.load_critic(torch, core, N2_2B, parent)
            weights[key] = meta["weights_sha256"]
            if weights[key] != prior["pretraining"][key]["weights_sha256"]:
                raise ValueError(f"Critic IL-v2 {parent} weicht vom Abschluss N2-2b ab")
            original, meta = cv.load_critic(torch, core, cv.OUT, parent)
            if meta["weights_sha256"] != config["il_critic_sha256"][key]:
                raise ValueError(f"N2-2-Critic {parent} weicht vom eingefrorenen N2-3-Start ab")
            torch.manual_seed(7100 + parent)
            new = core.TwinQ(original.mean.numpy(), original.std.numpy(), cv.PRETRAIN["critic_width"])
            critics = {"IL-v2": il, "neu": new.eval().requires_grad_(False)}
            q_parent = {variant: cv.predict(torch, critic, probe["state"], center)
                        for variant, critic in critics.items()}
            rng = np.random.default_rng(7500 + parent)
            states = np.repeat(probe["state"], K, axis=0)
            values[f"p{parent}_phase"] = probe["phase"]
            for delta in smoke.DELTAS:
                actions = draw_actions(center, delta, rng).reshape(-1, 4)
                for variant, critic in critics.items():
                    q = cv.predict(torch, critic, states, actions).reshape(-1, K)
                    values[f"p{parent}_d{delta:.2f}_{variant}"] = q - q_parent[variant][:, None]

    result = summarize(values, reference)
    raw_path = OUT / "advantages.npz"
    np.savez_compressed(raw_path, **values)
    summary = dict(task="D1b", **result, optimizer_updates=0, rollouts=0,
                   critic_sha256=weights, dataset_sha256=cv.DATASET_SHA256,
                   n2_2b_summary_sha256=N2_2B_SUMMARY_SHA, d1a_advantages_sha256=D1A_RAW_SHA,
                   n2_3_config_sha256=digest(config_path.read_bytes()),
                   protocol_sha256=digest((HERE / "PROTOCOL_V2.md").read_bytes()),
                   script_sha256=digest(Path(__file__).read_bytes()),
                   advantages_sha256=digest(raw_path.read_bytes()), seconds=time.perf_counter() - started)
    write(OUT / "summary.json", summary)
    print(f"D1b COMPLETE | {len(result['rows'])} Gruppen | bestanden: {result['passed']} | {summary['seconds']:.2f} s")


if __name__ == "__main__":
    main()
