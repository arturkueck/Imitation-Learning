"""Independently check recorded actions, endpoint and the timeout contrast."""
import argparse
import json
from pathlib import Path

import numpy as np


def audit(out):
    def read(name):
        return json.loads((out / name).read_text(encoding="utf-8"))

    if read("status.json")["state"] != "COMPLETE":
        raise ValueError("Expected a completed diagnosis")
    cols = {name: i for i, name in enumerate(read("trace_schema.json"))}
    count = 0
    prefix_checks = 0
    record_cols = [cols[c] for c in ("frame", "placement", "phase", "retreat", "steps",
        "pre_xy", "post_xy", "post_height", "post_source_finger", "post_source_held", "eef_z",
        "valid_tail", "command_x", "command_y", "command_z", "command_gripper")]

    def check_trace(path, row):
        nonlocal count
        with np.load(path) as archive:
            values = archive["trace"]
        if len(values) != row["frames"] or not np.array_equal(values[:, cols["frame"]], np.arange(len(values))):
            raise ValueError(f"Frame sequence mismatch: {path.name}")
        tail = 0
        for r in values:
            tail = tail + 1 if r[cols["post_valid_three"]] else 0
            if tail != r[cols["valid_tail"]]:
                raise ValueError(f"Invalid consecutive-frame counter: {path.name}")
        if bool(tail >= 50) != row["success"]:
            raise ValueError(f"Outcome mismatch: {path.name}")
        count += 1
        return values

    for mode in ("smoke", "main"):
        for group in read(f"{mode}/groups.json"):
            identifier = group["case"]["id"]
            arms = group["arms"]
            traces = {arm: check_trace(out / mode / "traces" / f"{identifier}_{arm}.npz", row)
                      for arm, row in arms.items()}
            for arm, row in arms.items():
                if arm == "control":
                    continue
                stop = row["first_change"]["frame"] if row["first_change"] else len(traces[arm])
                if not np.array_equal(traces[arm][:stop, record_cols], traces["control"][:stop, record_cols]):
                    raise ValueError(f"Pre-intervention trace mismatch: {identifier} {arm}")
                prefix_checks += 1
            if "withdraw" in arms:
                event = arms["withdraw"]["withdrawal"]
                stop = event["frame"] if event else len(traces["withdraw"])
                if not np.array_equal(traces["withdraw"][:stop, record_cols], traces["guarded_feedback"][:stop, record_cols]):
                    raise ValueError(f"Withdrawal prefix mismatch: {identifier}")
                prefix_checks += 1
    for row in read("main/screening.json"):
        check_trace(out / "main/traces" / f"screen_{row['seed']}_control.npz", row)
    if count != read("summary.json")["episodes"] + read("smoke/integrity.json")["episodes"]:
        raise ValueError("Number of verified traces differs from supervisor totals")

    # The reference-model column is conditioned directly on the selection rule.
    critical = [g for g in read("main/groups.json") if g["case"]["panel"] == "critical"]
    contrast = {}
    for label, groups in (("screening_reference", [g for g in critical if g["case"]["block"] == "data_1"]),
                          ("other_models", [g for g in critical if g["case"]["block"] != "data_1"])):
        pairs = [(g["arms"]["grasp_timeout"]["success"], g["arms"]["grasp_ready"]["success"]) for g in groups]
        contrast[label] = dict(n=len(pairs), timeout=sum(a for a, b in pairs), ready=sum(b for a, b in pairs),
                               ready_wins=sum(not a and b for a, b in pairs), ready_losses=sum(a and not b for a, b in pairs))
    result = dict(state="PASS", traces=count, matched_recorded_prefixes=prefix_checks, critical_timeout_contrast=contrast)
    (out / "trace_audit.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    audit(parser.parse_args().output)
