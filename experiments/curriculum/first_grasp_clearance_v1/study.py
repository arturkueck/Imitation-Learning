"""Run the complete frozen diagnosis, including automatic final reporting."""
from datetime import datetime
from pathlib import Path
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

import numpy as np
from simulation import COLUMNS, run_episode, verify_group

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREV = HERE.parent / "selective_completion_release_v1"
spec = importlib.util.spec_from_file_location("first_grasp_previous", PREV / "pipeline.py")
previous = importlib.util.module_from_spec(spec)
spec.loader.exec_module(previous)
read, write = previous.read, previous.write
NIGHT = ROOT / "praxis/results/curriculum/targeted_correction_budget_v2/night_20261117"
PRIOR = ROOT / "praxis/results/curriculum/selective_completion_release_v1/run_001"
MAXIMUM_SECONDS = 4500
END = datetime.fromisoformat("2026-11-18T20:00:00+01:00").timestamp()
NORMAL = range(2026201000, 2026201016)
SCREEN = range(2026202000, 2026202096)
CRITICAL_CAP = 12
GRASP = ("control", "grasp_timeout", "grasp_ready")
RELEASE = ("control", "guarded_feedback", "withdraw")
NORMAL_ARMS = GRASP + RELEASE[1:]


def build_plan(out):
    old = read(PREV / "config.json")
    plan = {k: old[k] for k in ("source_run", "source_policy", "grasp", "release",
        "placement_readiness", "episode_horizon", "success_frames", "optimizer_updates")}
    plan["clearance"] = {"contact_frames": 3, "lift_m": .04, "max_translation_command": .3}
    plan["normal_seeds"], plan["screen_seeds"] = list(NORMAL), list(SCREEN)
    plan["critical_cap"], plan["deadline_local"] = CRITICAL_CAP, "2026-11-18T20:00:00+01:00"
    plan["maximum_seconds"] = MAXIMUM_SECONDS
    parents = [(b["id"], b["heldout_model"]) for b in read(NIGHT / "plan.json")["blocks"]]
    plan["parents"] = parents
    if len(parents) != 3:
        raise ValueError("Require the three frozen parent lines")
    with (NIGHT / "rollouts.jsonl").open(encoding="utf-8") as stream:
        archived = [json.loads(line) for line in stream]
    target = [r for r in archived if r["panel"] == "confirmation" and r["policy"] == "targeted"
              and (r["block"], r["model"]) in parents]
    failures = [r for r in target if not r["success"] and (r["final_stage"], r["final_phase"]) == (1, 1)]
    bad_seeds = {r["seed"] for r in failures}
    if len(failures) != 22 or len(bad_seeds) != 13:
        raise ValueError("Unexpected archived first grasp cohort")
    cases = []

    def add(row, panel, arms, identifier, **extra):
        case = dict(id=identifier, panel=panel, arms=arms, seed=row["seed"],
                    block=row["block"], model=row["model"], **extra)
        if "success" in row:
            case["archived"] = {k: row[k] for k in previous.res.ARCHIVE_FIELDS}
        cases.append(case)

    for row in sorted(failures, key=lambda r: (r["block"], r["seed"])):
        add(row, "known_grasp_failure", GRASP, f'known_grasp_fail_{row["block"]}_{row["seed"]}')
    for block, model in parents:
        good = sorted((r for r in target if r["block"] == block and r["success"] and r["seed"] not in bad_seeds),
                      key=lambda r: r["seed"])[:2]
        for row in good:
            add(row, "known_grasp_success", GRASP, f'known_grasp_ok_{block}_{row["seed"]}')
    prior_groups = read(PRIOR / "groups.json")
    for group in prior_groups:
        old_case, arms = group["case"], group["arms"]
        if old_case["stratum"] in ("release_failure", "release_success_control"):
            add(dict(arms["control"], block=old_case["block"], model=old_case["model"]),
                "known_" + old_case["stratum"], RELEASE, old_case["id"],
                release_archive=arms["guarded_feedback"]["trajectory_sha256"])
    for seed in NORMAL:
        for block, model in parents:
            add(dict(seed=seed, block=block, model=model), "normal", NORMAL_ARMS, f"normal_{seed}_{block}")
    if sum(len(c["arms"]) for c in cases) != 342:
        raise ValueError("Fixed episode count changed")
    plan["cases"] = cases
    historical_rows = archived + [g["arms"]["control"] for g in prior_groups]
    previous_calibration = ROOT / "praxis/results/curriculum/completion_placement_check_v1/run_001/groups.json"
    historical_rows += [g["arms"]["control"] for g in read(previous_calibration)]
    old_seeds = {r["seed"] for r in historical_rows}
    if (set(NORMAL) | set(SCREEN)) & old_seeds:
        raise ValueError("New scene seed used in an opened panel")
    plan["archived_initial_states"] = sorted({r["initial_sha256"] for r in historical_rows})
    return plan


def audit_namespace(out):
    requested = set(NORMAL) | set(SCREEN)
    checked = 0

    def scan(value, key=""):
        if isinstance(value, dict):
            return any(scan(v, k) for k, v in value.items())
        if isinstance(value, list):
            if "seed" in key.lower() and len(value) == 2 and all(type(v) is int for v in value):
                return any(value[0] <= n <= value[1] for n in requested)
            return any(scan(v, key) for v in value)
        return type(value) is int and value in requested

    for directory in (ROOT / "experiments", ROOT / "praxis/results/curriculum"):
        for filename in ("config.json", "plan.json"):
            for path in directory.rglob(filename):
                if path.is_relative_to(HERE) or path.is_relative_to(out):
                    continue
                if scan(read(path)):
                    raise ValueError(f"New seed collides with recorded plan: {path}")
                checked += 1
    return checked


def prepare(out):
    if out.exists() or not out.is_relative_to(ROOT / "praxis/results/curriculum"):
        raise ValueError("Require a new results directory")
    plan = build_plan(out)
    plan["namespace_plans_checked"] = audit_namespace(out)
    base, _, _ = previous.h.libraries()
    base.backend()
    previous.prior.verify(NIGHT)
    previous.prior.verify_frozen(NIGHT)
    previous.res.verify(PRIOR)
    out.mkdir(parents=True)
    write(out / "plan.json", plan)
    write(out / "trace_schema.json", COLUMNS)
    paths = previous.dependency_files() | {Path(previous.__file__).resolve(), *HERE.glob("*.py"), HERE / "README.md",
        PREV / "config.json", out / "plan.json", out / "trace_schema.json", PRIOR / "groups.json",
        NIGHT / "rollouts.jsonl", NIGHT / "plan.json", NIGHT / "composition.json", NIGHT / "frozen_components.json"}
    registry = read(HERE.parent / "models.json")["models"]
    composition = read(NIGHT / "composition.json")
    for block, model in plan["parents"]:
        paths.add(ROOT / registry[model]["checkpoint"])
        component = composition[f"{block}/{model}/targeted"]
        paths.update(ROOT / component[k] for k in ("actor", "completion"))
    write(out / "provenance.json", {str(p.relative_to(ROOT)): base.sha(p) for p in sorted(paths)})
    for path in paths:
        if path.suffix in (".py", ".md", ".json") and not path.is_relative_to(out):
            snapshot = out / "sources" / path.relative_to(ROOT)
            snapshot.parent.mkdir(parents=True, exist_ok=True)
            snapshot.write_bytes(path.read_bytes())
    write(out / "status.json", {"state": "READY"})


def run_worker(out, mode, deadline):
    base, _, _ = previous.h.libraries()
    base.configure(1)
    previous.res.verify(out)
    plan = read(out / "plan.json")
    path = out / mode
    path.mkdir()
    traces = path / "traces"
    traces.mkdir()
    env = base.backend().native.historical.make_env(3)
    models, model_hashes, scene_hashes = {}, {}, {}
    archive_hashes = set(plan["archived_initial_states"])
    groups, screening = [], []

    def run(case, arm):
        key = (case["block"], case["model"])
        if key not in models:
            models[key] = previous.res.load_model(case, plan)
            model_hashes[key] = previous.h.registry.tensor_digest(models[key].state_dict())
        row, trace = run_episode(previous, env, models[key], case["seed"], arm, plan, out, deadline)
        seed, initial = row["seed"], row["initial_sha256"]
        if initial != scene_hashes.setdefault(seed, initial):
            raise ValueError("Initial states differ across arms/parents")
        if case["panel"] in ("normal", "critical", "screen") and initial in archive_hashes:
            raise ValueError("New state matches archive")
        np.savez_compressed(traces / f'{case["id"]}_{arm}.npz', trace=trace)
        return row

    def progress(stage):
        write(out / "status.json", dict(state="RUNNING", stage=stage, groups=len(groups),
                                        screened=len(screening), optimizer_updates=0))

    def compare(case):
        progress(mode + "_" + case["panel"])
        arms = {arm: run(case, arm) for arm in case["arms"]}
        verify_group(arms, case)
        for row in arms.values():
            row.pop("prefixes")
        groups.append(dict(case=case, arms=arms))
        write(path / "groups.json", groups)
        return arms

    try:
        fixed = plan["cases"]
        if mode == "smoke":
            compare(fixed[0])
            compare(next(c for c in fixed if c["id"] == "release_g16_failure"))
        else:
            for case in fixed:
                compare(case)
            block, model = plan["parents"][0]
            for seed in plan["screen_seeds"]:
                progress("screen")
                case = dict(id=f"screen_{seed}", seed=seed, block=block, model=model, panel="screen")
                row = run(case, "control")
                row.pop("prefixes")
                screening.append(row)
                write(path / "screening.json", screening)
            selected = [row for row in screening if row["screen_eligible"]][:plan["critical_cap"]]
            write(path / "screen_selection.json", dict(
                n=len(screening), all_eligible=[r["seed"] for r in screening if r["screen_eligible"]],
                selected=[r["seed"] for r in selected],
            ))
            for row in selected:
                for block, model in plan["parents"]:
                    case = dict(id=f'critical_{row["seed"]}_{block}', seed=row["seed"], block=block,
                                model=model, panel="critical", arms=GRASP)
                    arms = compare(case)
                    if model == plan["parents"][0][1] and arms["control"]["trajectory_sha256"] != row["trajectory_sha256"]:
                        raise ValueError("Reference replay differs from screening")
        for key, model in models.items():
            if model_hashes[key] != previous.h.registry.tensor_digest(model.state_dict()):
                raise ValueError("Frozen parameters changed")
            if any(p.requires_grad for p in model.parameters()):
                raise ValueError("Unfrozen model parameter")
        previous.res.verify(out)
        previous.prior.verify_frozen(NIGHT)
        write(path / "integrity.json", dict(groups=len(groups), screening=len(screening),
            episodes=sum(len(g["arms"]) for g in groups) + len(screening), optimizer_updates=0,
            frozen_parameters=True, histories_matched=True, archives_reproduced=True))
    finally:
        env.close()


def supervise(out):
    import report
    started = time.time()
    deadline = min(END - 90, started + MAXIMUM_SECONDS - 30)
    if deadline <= started:
        raise TimeoutError("Deadline reached before launch")
    final = dict(state="FAILED", started=started, deadline=deadline)
    awake = False
    proc = None
    try:
        if os.name == "nt":
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out / "worker.log").open("x", encoding="utf-8") as log:
            for mode, limit in (("smoke", min(deadline, time.time() + 600)), ("main", deadline)):
                if mode == "main" and not (out / "smoke/integrity.json").is_file():
                    raise ValueError("Smoke did not pass")
                write(out / "status.json", dict(state="RUNNING", stage=mode))
                proc = subprocess.Popen([sys.executable, "-u", str(__file__), mode,
                    "--output", str(out), "--deadline", str(limit)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
                final[f"{mode}_pid"] = proc.pid
                code = proc.wait(timeout=max(1., min(limit + 5, deadline + 5) - time.time()))
                final[f"{mode}_returncode"] = code
                if code != 0:
                    raise RuntimeError(f"{mode} process exited with {code}")
        final["state"] = "COMPLETE"
    except BaseException as exc:
        final["error"] = repr(exc)
        final["traceback"] = traceback.format_exc()
    finally:
        if proc is not None and proc.poll() is None:
            proc.kill()
            proc.wait(timeout=15)
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        final.update(finished=time.time(), optimizer_updates=0)
        try:
            report.generate(out, final)
        except Exception:
            final.update(state="FAILED", report_error=traceback.format_exc())
            (out / "ABSCHLUSSBERICHT.md").write_text(
                f"# Abschlussbericht\n\nAuswertung fehlgeschlagen. Siehe Statusdatei und verfügbare Einzelergebnisse.\n\n{final}\n",
                encoding="utf-8",
            )
        write(out / "status.json", final)
    print(json.dumps(final))
    return 0 if final["state"] == "COMPLETE" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "smoke", "main"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--deadline", type=float)
    args = parser.parse_args()
    output = args.output.resolve()
    if args.command == "prepare":
        prepare(output)
    elif args.command == "run":
        sys.exit(supervise(output))
    else:
        run_worker(output, args.command, args.deadline)
