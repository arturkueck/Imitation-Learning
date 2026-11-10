"""Run the frozen paired Lift comparison across three training seeds."""

import argparse
import json
from pathlib import Path

from evaluate_lift import evaluate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--episodes", type=int, default=20)
    parser.add_argument("--rollout-seed", type=int, default=6000)
    parser.add_argument("--horizon", type=int, default=400)
    parser.add_argument("--epoch", type=int, default=20)
    parser.add_argument("--bc-tag", default="")
    parser.add_argument("--extension-tag", default="w1")
    parser.add_argument("--output-subdir", default="final_eval")
    parser.add_argument(
        "--conditions", nargs="+", choices=(
            "nominal", "offset_x_2cm", "offset_x_minus_2cm", "impulse_x_1", "impulse_x_minus_1"
        ),
        default=("nominal", "offset_x_2cm"),
    )
    args = parser.parse_args()
    output_dir = args.results_dir / args.output_subdir
    output_dir.mkdir(parents=True, exist_ok=True)
    for seed in (1, 2, 3):
        methods = (
            "bc" + (f"_{args.bc_tag}" if args.bc_tag else ""),
            "bc_contraction" + (f"_{args.extension_tag}" if args.extension_tag else ""),
        )
        for method in methods:
            name = f"lift_ph_{method}_seed{seed}"
            checkpoints = sorted((args.results_dir / name).glob(f"*/models/model_epoch_{args.epoch}.pth"))
            if len(checkpoints) != 1:
                raise RuntimeError(f"expected one checkpoint for {name}, found {len(checkpoints)}")
            condition_specs = {
                "nominal": ((0.0, 0.0), 0.0),
                "offset_x_2cm": ((0.02, 0.0), 0.0),
                "offset_x_minus_2cm": ((-0.02, 0.0), 0.0),
                "impulse_x_1": ((0.0, 0.0), 1.0),
                "impulse_x_minus_1": ((0.0, 0.0), -1.0),
            }
            for condition in args.conditions:
                offset, impulse = condition_specs[condition]
                result = evaluate(
                    checkpoints[0], args.episodes, args.horizon, args.rollout_seed, offset,
                    action_impulse_x=impulse,
                )
                output = output_dir / f"{name}_{condition}.json"
                output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
                print(f"{name} {condition}: {result['successes']}/{args.episodes}", flush=True)


if __name__ == "__main__":
    main()
