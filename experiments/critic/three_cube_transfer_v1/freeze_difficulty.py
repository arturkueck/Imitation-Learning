"""N1-5: Grenzen aus N1-4 einfrieren und Panels aus Startgeometrie bilden."""

import argparse
from collections import Counter, defaultdict
import importlib.metadata
import math
import os
from pathlib import Path
import random
import time

from calibration import (
    CURRICULUM, EXPECTED, HERE, OUT, ROOT, alive, check_row, digest,
    episode_path, load_module, read, write,
)
from difficulty import VERSION, initial_features


METRIC = "transport_total_xy_m"
CLASSES = ("leicht", "mittel", "schwer")
RULE = HERE / "difficulty_v1.json"
SEAL = HERE / "difficulty_v1.sha256"
PANELS = HERE / "difficulty_panels_v1.json"
SPLITS = HERE / "splits.json"
PANEL_IDS = ("validation_normal", "validation_hard", "test_normal", "test_hard")


def sha(path):
    return digest(path.read_bytes())


def checked_calibration():
    status = read(OUT / "status.json")
    supervisor = read(OUT / "supervisor_status.json")
    summary = read(OUT / "summary.json")
    config_path = OUT / "config.json"
    config = read(config_path)
    if (status["state"] != "COMPLETE" or supervisor["state"] != "COMPLETE"
            or supervisor["worker_exitcode"] != 0
            or alive(status["worker"]) or alive(supervisor["supervisor"])):
        raise RuntimeError("N1-4 hat keinen geprüften abgeschlossenen Prozessstand.")
    if any(record["optimizer_updates"] for record in (status, summary, config)):
        raise ValueError("Optimizerupdates im Kalibrierungsnachweis")
    for path, expected_hash in config["source_sha256"].items():
        if sha(ROOT / path) != expected_hash:
            raise ValueError(f"Quelle gegenüber N1-4 verändert: {path}")
    paths = sorted((OUT / "episodes").glob("*.json"))
    if paths != [episode_path(index) for index in range(EXPECTED)]:
        raise ValueError("Kalibrierungsdateien nicht vollständig")
    if (sha(config_path) != summary["config_sha256"]
            or digest(b"".join(path.read_bytes() for path in paths)) != summary["raw_sha256"]):
        raise ValueError("Kalibrierungshashes stimmen nicht überein")

    calibration = next(split for split in read(SPLITS)["splits"] if split["id"] == "calibration")
    seeds = range(calibration["first"], calibration["last"] + 1)
    schedule = [[seed, parent] for seed in seeds for parent in (1, 2, 3)]
    if config["schedule"] != schedule or len(schedule) != EXPECTED:
        raise ValueError("Unerwarteter Kalibrierungsplan")
    scenes, episodes = {}, defaultdict(dict)
    for index, path in enumerate(paths):
        row = read(path)
        check_row(row, index, schedule, scenes)
        if row["features"] != initial_features(row["initial_xyz_m"], row["table_offset_m"]):
            raise ValueError(f"Merkmale stimmen in Episode {index} nicht überein.")
        episodes[row["scene_seed"]][row["parent_seed"]] = row["success"]

    by_parent = {str(parent): {"successes": sum(outcomes[parent] for outcomes in episodes.values()),
                              "episodes": len(episodes)} for parent in (1, 2, 3)}
    if (summary["families"] != len(episodes) or summary["completed_episodes"] != EXPECTED
            or summary["by_parent"] != by_parent
            or summary["successes"] != sum(row["successes"] for row in by_parent.values())):
        raise ValueError("Kalibrierungsnenner oder Erfolgszahlen stimmen nicht überein.")
    return summary, config, scenes, episodes


def classify(value, lower, upper):
    if value < lower:
        return "leicht"
    if value < upper:
        return "mittel"
    return "schwer"


def calibrate(summary, scenes, episodes):
    values = {seed: scene[3][METRIC] for seed, scene in scenes.items()}
    sorted_values = sorted(values.values())
    cuts = [math.ceil(len(values) * part / 3) for part in (1, 2)]
    brackets = [sorted_values[cut - 1:cut + 1] for cut in cuts]
    if any(low >= high for low, high in brackets):
        raise ValueError("Bindung an einer Drittelgrenze der Kalibrierungswerte")
    lower, upper = [(low + high) / 2 for low, high in brackets]
    groups = defaultdict(list)
    for seed, value in values.items():
        groups[classify(value, lower, upper)].append(seed)
    statistics = {}
    for label in CLASSES:
        seeds = groups[label]
        statistics[label] = {
            "families": len(seeds), "episodes": 3 * len(seeds),
            "successes": sum(sum(episodes[seed].values()) for seed in seeds),
            "successes_by_parent": {str(parent): sum(episodes[seed][parent] for seed in seeds)
                                    for parent in (1, 2, 3)},
        }
    return {
        "version": VERSION,
        "metric": METRIC,
        "unit": "m",
        "calibration": {
            "families": len(scenes), "episodes": EXPECTED,
            "raw_sha256": summary["raw_sha256"], "config_sha256": summary["config_sha256"],
            "method": "Sortieren und nach Rang ceil(n/3) bzw. ceil(2n/3) teilen; "
                      "Mittelwerte der jeweils angrenzenden Messwerte als Grenzen.",
            "adjacent_values_m": brackets, "class_counts": statistics,
        },
        "source_sha256": {path.name: sha(path) for path in (SPLITS, HERE / "difficulty.py", Path(__file__))},
        "lower_m": lower,
        "upper_m": upper,
        "class_intervals": {"leicht": "x < lower_m", "mittel": "lower_m <= x < upper_m",
                            "schwer": "upper_m <= x"},
    }


def panels(rule, config, scenes, cutoff):
    for name in ("numpy", "robosuite", "mujoco", "torch"):
        if importlib.metadata.version(name) != config["software"][name]:
            raise ValueError(f"Abweichende Softwareversion für {name}")
    os.environ["NUMBA_CACHE_DIR"] = str(OUT / "numba")
    registry = load_module("difficulty_registry", CURRICULUM / "registry.py")
    base, torch = registry.libraries()
    np = base.np
    base.configure(1)
    historical = base.backend().native.historical
    first_seed = min(scenes)
    random.seed(first_seed)
    np.random.seed(first_seed)
    torch.manual_seed(first_seed)
    env = historical.make_env(3)

    def geometry(seed):
        if time.monotonic() >= cutoff or (OUT.parent / "STOP").exists():
            raise TimeoutError("Zeitlimit oder lokaler STOP bei der Panelzuordnung")
        random.seed(seed)
        np.random.seed(seed)
        env.reset()
        env.sim.forward()
        positions = env.sim.data.body_xpos[env.cube_ids]
        return initial_features(positions, env.table_offset), digest(
            env.sim.get_state().flatten().tobytes()
        )

    results = {}
    try:
        for seed, (expected_hash, _, _, expected_features) in scenes.items():
            if geometry(seed) != (expected_features, expected_hash):
                raise ValueError(f"Reset reproduziert Kalibrierungsstart {seed} nicht.")
        seen = {scene[0] for scene in scenes.values()}
        for split in read(SPLITS)["splits"]:
            panel_id = split["id"]
            if panel_id not in PANEL_IDS:
                continue
            counts = Counter(dict.fromkeys(CLASSES, 0))
            selected = []
            for seed in range(split["first"], split["last"] + 1):
                features, state_hash = geometry(seed)
                label = classify(features[METRIC], rule["lower_m"], rule["upper_m"])
                counts[label] += 1
                if state_hash in seen:
                    raise ValueError(f"Doppelte Anfangszustandsidentität bei Seed {seed}")
                seen.add(state_hash)
                if split["selection"] == "all" or label == "schwer":
                    selected.append([seed, label, features[METRIC]])
                if split["selection"] == "hard_first" and len(selected) == split["target_families"]:
                    break
            results[panel_id] = {
                "selection": split["selection"], "candidates_checked": sum(counts.values()),
                "candidate_class_counts": counts, "target_families": split["target_families"],
                "shortfall": split["target_families"] - len(selected), "families": selected,
            }
    finally:
        env.close()
    return {"version": VERSION, "difficulty_sha256": sha(RULE),
            "columns": ["scene_seed", "difficulty_class", METRIC],
            "calibration_resets_verified": len(scenes), "rollouts": 0, "optimizer_updates": 0,
            "panels": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("step", choices=("freeze", "assign"))
    args = parser.parse_args()
    cutoff = time.monotonic() + 40
    summary, config, scenes, episodes = checked_calibration()
    rule = calibrate(summary, scenes, episodes)
    if args.step == "freeze":
        if RULE.exists() or SEAL.exists():
            raise FileExistsError("Ein Schwierigkeitsartefakt ist bereits vorhanden.")
        write(RULE, rule)
        with SEAL.open("x", encoding="ascii") as stream:
            stream.write(f"{sha(RULE)}  {RULE.name}\n")
        print(rule["calibration"]["class_counts"])
    else:
        if read(RULE) != rule or SEAL.read_text(encoding="ascii").split() != [sha(RULE), RULE.name]:
            raise ValueError("Schwierigkeitsregel oder Prüfsumme verändert")
        result = panels(rule, config, scenes, cutoff)
        if PANELS.exists():
            if read(PANELS) != result:
                raise ValueError("Panelzuordnung weicht von der gespeicherten Zuordnung ab.")
        else:
            write(PANELS, result)
        for panel, counts in result["panels"].items():
            print(panel, len(counts["families"]), counts["candidates_checked"], counts["shortfall"])


if __name__ == "__main__":
    main()
