"""Fit a local translation response for Lift using training demonstrations only.

The fitted row-vector mapping is delta_eef ~= action[:3] @ K + intercept.
The intercept is reported but cancels in the contraction loss's action difference.
"""

import argparse
import json
from pathlib import Path

import h5py
import numpy as np


def fit(dataset: Path, filter_key: str) -> dict:
    with h5py.File(dataset, "r") as handle:
        demos = [key.decode() if isinstance(key, bytes) else key for key in handle[f"mask/{filter_key}"][:]]
        actions = np.concatenate([handle[f"data/{name}/actions"][:, :3] for name in demos])
        deltas = np.concatenate([
            handle[f"data/{name}/next_obs/robot0_eef_pos"][:]
            - handle[f"data/{name}/obs/robot0_eef_pos"][:]
            for name in demos
        ])
    design = np.column_stack([actions, np.ones(len(actions))])
    coefficients, _, _, _ = np.linalg.lstsq(design, deltas, rcond=None)
    prediction = design @ coefficients
    residual = ((deltas - prediction) ** 2).sum(axis=0)
    total = ((deltas - deltas.mean(axis=0)) ** 2).sum(axis=0)
    return {
        "dataset": str(dataset),
        "filter_key": filter_key,
        "demonstrations": len(demos),
        "transitions": len(actions),
        "dynamics_matrix": coefficients[:3].tolist(),
        "intercept": coefficients[3].tolist(),
        "r2_by_axis": (1 - residual / total).tolist(),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--filter-key", default="train")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = fit(args.dataset, args.filter_key)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
