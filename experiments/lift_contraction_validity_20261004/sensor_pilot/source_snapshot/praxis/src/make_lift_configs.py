"""Generate paired BC / contraction-BC robomimic configs from one template."""

import argparse
import copy
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--dynamics", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--results-dir", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--epochs", type=int, default=50)
    parser.add_argument("--steps-per-epoch", type=int, default=100)
    parser.add_argument("--rollout", action="store_true")
    parser.add_argument("--weight", type=float, default=0.01)
    parser.add_argument("--tag", default="")
    parser.add_argument("--methods", nargs="+", choices=("bc", "bc_contraction"), default=("bc", "bc_contraction"))
    parser.add_argument("--train-filter", default="train")
    parser.add_argument("--valid-filter", default="valid")
    args = parser.parse_args()

    template = json.loads(args.template.read_text(encoding="utf-8"))
    dynamics = json.loads(args.dynamics.read_text(encoding="utf-8"))
    for method in args.methods:
        cfg = copy.deepcopy(template)
        cfg["algo_name"] = method
        tag = f"_{args.tag}" if args.tag else ""
        cfg["experiment"]["name"] = f"lift_ph_{method}{tag}_seed{args.seed}"
        cfg["experiment"]["validate"] = True
        cfg["experiment"]["rollout"]["enabled"] = args.rollout
        cfg["experiment"]["render_video"] = False
        cfg["experiment"]["logging"]["log_tb"] = False
        cfg["experiment"]["epoch_every_n_steps"] = args.steps_per_epoch
        cfg["experiment"]["validation_epoch_every_n_steps"] = min(20, args.steps_per_epoch)
        cfg["experiment"]["save"]["every_n_epochs"] = args.epochs
        cfg["experiment"]["save"]["on_best_validation"] = False
        cfg["train"]["data"] = [{"path": str(args.dataset.resolve())}]
        cfg["train"]["output_dir"] = str(args.results_dir.resolve())
        cfg["train"]["hdf5_filter_key"] = args.train_filter
        cfg["train"]["hdf5_validation_filter_key"] = args.valid_filter
        cfg["train"]["num_epochs"] = args.epochs
        cfg["train"]["seed"] = args.seed
        cfg["algo"]["actor_layer_dims"] = [256, 256]
        if method == "bc_contraction":
            cfg["algo"]["contraction"] = {
                "weight": args.weight,
                "radius": 0.005,
                "target_ratio": 0.99,
                "eef_key": "robot0_eef_pos",
                "object_key": "object",
                "dynamics_matrix": dynamics["dynamics_matrix"],
            }
        args.output_dir.mkdir(parents=True, exist_ok=True)
        output = args.output_dir / f"lift_ph_{method}{tag}_seed{args.seed}.json"
        output.write_text(json.dumps(cfg, indent=2) + "\n", encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
