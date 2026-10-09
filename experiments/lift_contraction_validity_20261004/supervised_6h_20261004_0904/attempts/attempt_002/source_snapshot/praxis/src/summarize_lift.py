"""Summarize paired Lift rollout JSON files without inferential overclaiming."""

import argparse
import json
import statistics
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--eval-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--bc-tag", default="")
    parser.add_argument("--extension-tag", default="w1")
    args = parser.parse_args()
    rows = []
    bc_name = "bc" + (f"_{args.bc_tag}" if args.bc_tag else "")
    extension_name = "bc_contraction" + (f"_{args.extension_tag}" if args.extension_tag else "")
    conditions = tuple(
        condition for condition in (
            "nominal", "offset_x_2cm", "offset_x_minus_2cm", "impulse_x_1", "impulse_x_minus_1"
        ) if (args.eval_dir / f"lift_ph_{bc_name}_seed1_{condition}.json").exists()
    )
    for seed in (1, 2, 3):
        for condition in conditions:
            bc_file = args.eval_dir / f"lift_ph_{bc_name}_seed{seed}_{condition}.json"
            ext_file = args.eval_dir / f"lift_ph_{extension_name}_seed{seed}_{condition}.json"
            bc = json.loads(bc_file.read_text(encoding="utf-8"))
            ext = json.loads(ext_file.read_text(encoding="utf-8"))
            assert [r["seed"] for r in bc["rollouts"]] == [r["seed"] for r in ext["rollouts"]]
            if "initial_cube_qpos" in bc["rollouts"][0]:
                for b, e in zip(bc["rollouts"], ext["rollouts"]):
                    assert all(abs(x - y) < 1e-8 for x, y in zip(b["initial_cube_qpos"], e["initial_cube_qpos"]))
                    assert all(abs(x - y) < 1e-8 for x, y in zip(b["initial_eef_pos"], e["initial_eef_pos"]))
            rows.append({
                "training_seed": seed,
                "condition": condition,
                "episodes": bc["episodes"],
                "bc_successes": bc["successes"],
                "extension_successes": ext["successes"],
                "bc_only_successes": sum(b["success"] and not e["success"] for b, e in zip(bc["rollouts"], ext["rollouts"])),
                "extension_only_successes": sum(e["success"] and not b["success"] for b, e in zip(bc["rollouts"], ext["rollouts"])),
                "bc_mean_steps": bc["mean_steps"],
                "extension_mean_steps": ext["mean_steps"],
            })
    aggregate = {}
    for condition in conditions:
        selected = [r for r in rows if r["condition"] == condition]
        n = sum(r["episodes"] for r in selected)
        aggregate[condition] = {
            "episodes_per_method": n,
            "bc_successes": sum(r["bc_successes"] for r in selected),
            "extension_successes": sum(r["extension_successes"] for r in selected),
            "bc_success_rate": sum(r["bc_successes"] for r in selected) / n,
            "extension_success_rate": sum(r["extension_successes"] for r in selected) / n,
            "mean_paired_rate_difference_by_training_seed": statistics.mean(
                (r["extension_successes"] - r["bc_successes"]) / r["episodes"] for r in selected
            ),
            "sd_paired_rate_difference_by_training_seed": statistics.stdev(
                (r["extension_successes"] - r["bc_successes"]) / r["episodes"] for r in selected
            ),
        }
    report = {"rows": rows, "aggregate": aggregate}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
