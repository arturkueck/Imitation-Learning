"""Prepare, verify and explicitly launch the first-grasp query comparison."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import traceback

os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")

import numpy as np
import torch

from analysis import report
from rollout import expert_label, is_priority, query_indices, rollout

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN_ROOT = ROOT / "praxis/results/curriculum/first_grasp_query_v1"
V2 = HERE.parent / "targeted_correction_budget_v2/pipeline.py"
spec = importlib.util.spec_from_file_location("query_v2_supervisor", V2)
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
h, read, write = runtime.h, runtime.read, runtime.write
CAL = ROOT / "praxis/results/curriculum/first_grasp_clearance_v1/run_001"
BASE_CFG = HERE.parent / "axis_bc_20261110/config.json"
REFERENCE = "mixed_s1_u30000"
ARMS = ("base", "timeout", "random", "targeted")


def expand(bounds):
    return list(range(bounds[0], bounds[1] + 1))


def validate(plan):
    if len(set(plan["seeds"])) != 10 or len(plan["seeds"]) != 10:
        raise ValueError("Require ten independent initializations")
    sets = {key: set(expand(value)) for key, value in plan["scene_seeds"].items()}
    if sum(map(len, sets.values())) != len(set.union(*sets.values())):
        raise ValueError("Scenario namespaces overlap")
    if plan["batch_size"] != 64 or plan["queries_per_family"] != 4 or plan["candidate_stride"] < 1:
        raise ValueError("Changed query or batch contract")
    if plan["stable_frames"] != 50 or plan["horizon"] != 1000:
        raise ValueError("Changed task endpoint")
    if not (plan["validation_hard_n"] <= len(sets["validation_hard_pool"])
            and plan["test_hard_n"] <= len(sets["test_hard_pool"])):
        raise ValueError("Insufficient hard candidates")


def namespace(plan):
    requested = {seed for span in plan["scene_seeds"].values() for seed in expand(span)}
    checked = []
    for directory in (ROOT / "experiments", ROOT / "praxis/results/curriculum"):
        for pattern in ("config.json", "plan.json"):
            for path in directory.rglob(pattern):
                if path.is_relative_to(HERE):
                    continue
                if path.is_relative_to(RUN_ROOT) and len(path.relative_to(RUN_ROOT).parts) > 2:
                    continue  # Snapshot copies are covered by the top-level run plan.
                data = read(path)
                if path.is_relative_to(RUN_ROOT) and data.get("schema") == plan["schema"]:
                    state_file = path.parent / "status.json"
                    prepared_only = (state_file.is_file()
                        and read(state_file)["state"] in ("READY", "PREPARATION_FAILED")
                        and not (path.parent / "launch.json").exists()
                        and not (path.parent / "test_opened.json").exists())
                    if data.get("technical_only") or prepared_only:
                        continue
                def intersects(value):
                    if isinstance(value, dict):
                        return any(intersects(v) for v in value.values())
                    if isinstance(value, list):
                        if len(value) == 2 and all(type(n) is int for n in value):
                            return any(value[0] <= s <= value[1] for s in requested)
                        return any(intersects(v) for v in value)
                    return type(value) is int and value in requested
                if intersects(data):
                    raise ValueError(f"Scenario namespace collision with {path}")
                checked.append(str(path.relative_to(ROOT)))
    return dict(checked=sorted(checked), collisions=0, scenarios=len(requested))


def calibrate(plan):
    if read(CAL / "status.json")["state"] != "COMPLETE" or read(CAL / "trace_audit.json")["state"] != "PASS":
        raise ValueError("Require the verified calibration source")
    cols = {c: i for i, c in enumerate(read(CAL / "trace_schema.json"))}
    traces, rows = [], []
    for row in read(CAL / "main/screening.json"):
        path = CAL / "main/traces" / f'screen_{row["seed"]}_control.npz'
        with np.load(path) as archive:
            trace = archive["trace"][:plan["prefix_horizon"]]
        # The previous frame records the grasp measured before the first lift action.
        at = np.flatnonzero((trace[:, cols["placement"]] == 1) & (trace[:, cols["phase"]] == 3))
        reached = bool(len(at) and at[0] > 0 and trace[at[0]-1, cols["post_source_held"]])
        frames = int(at[0]) if reached else plan["prefix_horizon"] + 1
        rows.append(dict(seed=row["seed"], initial_sha256=row["initial_sha256"],
            reference_success=row["success"], frames=frames, censored=not reached))
        traces.append(path)
    if len(rows) != 96:
        raise ValueError("Unexpected calibration size")
    easy, hard = np.quantile([r["frames"] for r in rows], [1/3, 2/3], method="higher").astype(int)
    if easy >= hard or hard > plan["prefix_horizon"]:
        raise ValueError("Degenerate measured difficulty")
    spec = dict(version="first-lift-latency-v1", reference=REFERENCE, easy_below=int(easy),
        hard_from=int(hard), units="control frames", censor_value=plan["prefix_horizon"] + 1)
    for row in rows:
        row["difficulty"] = band(row["frames"], spec)
    summary = {name: dict(n=sum(r["difficulty"] == name for r in rows),
        successes=sum(r["difficulty"] == name and r["reference_success"] for r in rows))
        for name in ("easy", "medium", "hard")}
    spec.update(calibration_counts=summary, calibration_rows=rows)
    return spec, traces


def band(frames, spec):
    return "easy" if frames < spec["easy_below"] else "hard" if frames >= spec["hard_from"] else "medium"


def dependency_snapshot(base, out, paths):
    modules = list(sys.modules.values()) + [h, h.registry, h.validation, h.validation.adapter,
        h.runtime, runtime.bc, runtime.analysis]
    for module in modules:
        filename = getattr(module, "__file__", None)
        if not filename:
            continue
        path = Path(filename).resolve()
        if path.suffix == ".py" and path.is_file() and path.is_relative_to(ROOT) and ROOT / "praxis/.venv" not in path.parents:
            paths.add(path)
    write(out / "provenance.json", {str(path.relative_to(ROOT)): base.sha(path) for path in sorted(paths)})
    for path in paths:
        if path.suffix in (".py", ".json", ".md") and not path.is_relative_to(out):
            target = out / "sources" / path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())


def prepare(out, smoke):
    if out.exists() or not out.is_relative_to(RUN_ROOT):
        raise ValueError("Require a new study results directory")
    plan = read(HERE / "config.json")
    validate(plan)
    audit = namespace(plan)
    base, _, _ = h.libraries()
    base.backend()
    base.load_data()
    plan["difficulty"], traces = calibrate(plan)
    plan["technical_only"] = smoke
    if smoke:
        tech = expand(plan["scene_seeds"]["technical"])
        plan.update(seeds=[3999], seed_lists=dict(train=tech[:4], validation_normal=tech[4:5],
            validation_hard_pool=tech[5:6], test_normal=tech[6:7], test_hard_pool=tech[7:]),
            validation_hard_n=1, test_hard_n=1, base_updates=4, correction_updates=4,
            minimum_train_families=1, minimum_priority_families=0, minimum_label_count_by_class=0,
            bootstrap_draws=20, maximum_seconds=600, exit_reserve_seconds=20)
    else:
        plan["seed_lists"] = {key: expand(bounds) for key, bounds in plan["scene_seeds"].items() if key != "technical"}
    plan["base_config"] = read(BASE_CFG)
    if not torch.cuda.is_available():
        raise RuntimeError("The planned runtime needs CUDA")
    out.mkdir(parents=True)
    runtime.status(out, state="PREPARING", technical_only=smoke, training_started=False)
    write(out / "plan.json", plan)
    write(out / "namespace.json", audit)
    reference = h.registry.restore(REFERENCE, "cuda")[0].eval().requires_grad_(False)
    base.configure(plan["seeds"][0])
    env = base.backend().native.historical.make_env(3)
    try:
        scene_info = {}
        score_families(env, reference, plan, out, time.time() + 600,
            ("train", "validation_normal", "validation_hard_pool"), scene_info, preview=True)
        val = panels(plan, scene_info, "validation")
        preview = {key: sum(r["partition"] == "train" and r.get(key, False) for r in scene_info.values())
            for key in ("reference_query_eligible", "reference_priority_available")}
        if preview["reference_query_eligible"] < plan["minimum_train_families"]:
            raise ValueError("Coverage preflight failed even on the frozen reference")
        write(out / "development_families.json", dict(assignments=scene_info, selected=val, preview=preview))
    except BaseException as exc:
        runtime.status(out, state="PREPARATION_FAILED", error=repr(exc), training_started=False)
        raise
    finally:
        env.close()
    paths = set(HERE.glob("*.py")) | set(traces) | {HERE / "config.json", HERE / "README.md", ROOT / "AGENTS.md",
        BASE_CFG, base.ARRAYS, base.MANIFEST, V2, HERE.parent / "models.json",
        out / "plan.json", out / "development_families.json",
        CAL / "main/screening.json", CAL / "trace_schema.json", CAL / "trace_audit.json"}
    entry = read(HERE.parent / "models.json")["models"][REFERENCE]
    paths.add(ROOT / entry["checkpoint"])
    dependency_snapshot(base, out, paths)
    runtime.status(out, state="READY", technical_only=smoke, training_started=False,
        gpu=torch.cuda.get_device_name(0), difficulty=plan["difficulty"]["calibration_counts"])
    print(f"READY {'technical' if smoke else 'scientific'} {out}")


def train_parent(base, historical, data, plan, seed, folder, hook):
    cfg = copy.deepcopy(plan["base_config"])
    cfg["updates"] = plan["base_updates"]
    if plan["technical_only"]:
        for stage, end in zip(cfg["stages"], (1, 2, cfg["updates"])):
            stage["end_update"] = end
    batches, shuffle = base.schedule(data, cfg, seed)
    np.savez_compressed(folder / "base_schedule.npz", batches=batches, order=shuffle)
    base.configure(seed)
    model = historical.PhaseNet(cfg["width"]).to("cuda")
    optimizer = torch.optim.AdamW(model.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
    weight = base.positive_weights(data, "cuda")
    for update, idx in enumerate(shuffle, 1):
        hook("TRAINING_PARENT", update)
        metrics = base.step(model, optimizer, data, batches[idx], weight, cfg, update, "cuda")
        if update % 500 == 0 or update == len(shuffle):
            hook("TRAINING_PARENT", update, metrics)
    save(folder / "base.pth", model, optimizer, seed, len(shuffle))
    return model.eval().requires_grad_(False)


def save(path, model, optimizer, seed, update):
    tmp = path.with_suffix(".tmp")
    torch.save(dict(model=model.state_dict(), optimizer=optimizer.state_dict(), seed=seed, update=update,
        torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all()), tmp)
    tmp.replace(path)


def build_pools(env, parent, plan, out, deadline, seed, hook, scene_info):
    rng = np.random.default_rng(seed + 41)
    labels = {arm: [] for arm in ("random", "targeted")}
    ledger, priority_families = [], 0
    for i, family in enumerate(plan["seed_lists"]["train"], 1):
        hook("COLLECTING", i)
        row, candidates = rollout(h, env, parent, family, plan, out, deadline, prefix=True, capture=True)
        if row["initial_sha256"] != scene_info[family]["initial_sha256"]:
            raise ValueError("Different family initial state at collection")
        assignment = query_indices(candidates, rng)
        record = dict(seed=family, initial_sha256=row["initial_sha256"],
            difficulty=scene_info[family]["difficulty"], windows=len(candidates),
            assignment=assignment, queries={})
        if assignment is not None:
            priority_families += int(any(is_priority(candidates[k]) for k in assignment["targeted"][2:]))
            for arm, indices in assignment.items():
                queried = [dict(candidates[k], label=expert_label(candidates[k])) for k in indices]
                labels[arm].extend((item["x"], item["label"]) for item in queried)
                record["queries"][arm] = queried
            record["calls"] = sum(map(len, record["queries"].values()))
            record["distinct_query_states"] = len(set(assignment["random"] + assignment["targeted"]))
        ledger.append(record)
    arrays = {key: (np.asarray([x for x, _ in pairs], dtype=np.float32),
        np.asarray([v for _, v in pairs], dtype=np.float32)) for key, pairs in labels.items()}
    proof = dict(attempts=len(ledger), accepted=sum(r["assignment"] is not None for r in ledger),
        priority_families=priority_families, budget_per_arm=len(labels["random"]),
        actual_calls=sum(r.get("calls", 0) for r in ledger), families=ledger)
    return arrays, proof


def fit_heads(parent, data, labels, plan, folder, seed, hook):
    rng = np.random.default_rng(seed + 42)
    n = plan["correction_updates"]
    phase_rows = np.flatnonzero(data[2] == 1)
    replay = rng.choice(phase_rows, size=(n, 32))
    pulled = rng.integers(len(labels["random"][0]), size=(n, 32))
    np.savez_compressed(folder / "query_schedule.npz", replay=replay, queries=pulled)
    cfg = plan["base_config"]
    weight = h.libraries()[0].positive_weights(data, "cuda")[1]
    heads = {}
    for arm in ("random", "targeted"):
        head = copy.deepcopy(parent.heads[1]).train().requires_grad_(True)
        optimizer = torch.optim.AdamW(head.parameters(), lr=cfg["lr"], weight_decay=cfg["weight_decay"])
        x, y = labels[arm]
        for i in range(n):
            hook(f"TRAINING_{arm.upper()}", i + 1)
            inputs = torch.as_tensor(np.concatenate((data[0][replay[i]], x[pulled[i]])), device="cuda")
            expected = torch.as_tensor(np.concatenate((data[3][replay[i]], y[pulled[i]])), device="cuda")
            loss = torch.nn.functional.binary_cross_entropy_with_logits(head(inputs)[:, 4], expected, pos_weight=weight)
            if not torch.isfinite(loss):
                raise FloatingPointError("Nonfinite completion loss")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if not torch.isfinite(torch.nn.utils.clip_grad_norm_(head.parameters(), cfg["gradient_clip"])):
                raise FloatingPointError("Nonfinite completion gradient")
            optimizer.step()
            if (i + 1) % 250 == 0 or i + 1 == n:
                hook(f"TRAINING_{arm.upper()}", i + 1, dict(bce=float(loss.detach())))
        save(folder / f"{arm}.pth", head, optimizer, seed, n)
        heads[arm] = head.eval().requires_grad_(False)
    return heads


def score_families(env, reference, plan, out, deadline, names, scene_info, *, preview=False):
    seen = {r["initial_sha256"] for r in plan["difficulty"]["calibration_rows"]}
    seen.update(r["initial_sha256"] for r in scene_info.values())
    for name in names:
        for i, seed in enumerate(plan["seed_lists"][name], 1):
            if i == 1 or i % 16 == 0:
                runtime.status(out, state="SCORING_SCENES", panel=name, completed=i-1)
            row, windows = rollout(h, env, reference, seed, plan, out, deadline, prefix=True,
                capture=preview and name == "train")
            row["difficulty"] = band(row["difficulty_frames"], plan["difficulty"])
            row["partition"] = name
            if row["initial_sha256"] in seen:
                raise ValueError("Coincident physical initial states across families")
            seen.add(row["initial_sha256"])
            if preview and name == "train":
                row["reference_query_eligible"] = len(windows) >= 4
                row["reference_priority_available"] = len(windows) >= 4 and any(is_priority(x) for x in windows[1:-1])
            scene_info[seed] = row


def panels(plan, scene_info, split):
    result = {f"{split}_normal": plan["seed_lists"][f"{split}_normal"]}
    hard = [seed for seed in plan["seed_lists"][f"{split}_hard_pool"] if
            plan["technical_only"] or scene_info[seed]["difficulty"] == "hard"]
    n = plan[f"{split}_hard_n"]
    if len(hard) < n:
        raise ValueError(f"Too few pre-specified difficult {split} families, {len(hard)}/{n}")
    result[f"{split}_hard"] = hard[:n]
    return result


def worker(out, deadline):
    plan = read(out / "plan.json")
    base, _, _ = h.libraries()
    env = None
    runtime.status(out, state="INITIALIZING", training_started=False)
    try:
        runtime.verify(out)
        base.configure(plan["seeds"][0])
        historical = base.backend().native.historical
        data = base.load_data()["train"]
        env = historical.make_env(3)
        reference = h.registry.restore(REFERENCE, "cuda")[0].eval().requires_grad_(False)
        prepared = read(out / "development_families.json")
        scene_info = {int(seed): row for seed, row in prepared["assignments"].items()}
        val, results = prepared["selected"], {}
        checkpoints = {}
        for seed in plan["seeds"]:
            folder = out / f"line_{seed}"
            folder.mkdir()
            def hook(stage, step, metrics=None):
                base.check_stop(out, deadline)
                if step == 1 or step % 500 == 0 or metrics is not None:
                    runtime.status(out, state=stage, seed=seed, step=step, metrics=metrics, training_started=True)
            parent = train_parent(base, historical, data, plan, seed, folder, hook)
            if plan["technical_only"]:
                # Exercise fresh initialization above and use a functioning fixture for the remaining smoke path.
                (folder / "base.pth").rename(folder / "technical_fresh_parent.pth")
                parent = reference
                torch.save(dict(model=parent.state_dict(), seed=seed, technical_fixture=True), folder / "base.pth")
            frozen_parent = h.registry.tensor_digest(parent.state_dict())
            arrays, proof = build_pools(env, parent, plan, out, deadline, seed, hook, scene_info)
            write(folder / "queries.json", proof)
            if proof["accepted"] < plan["minimum_train_families"] or proof["priority_families"] < plan["minimum_priority_families"]:
                raise ValueError(f"Coverage gate failed in line {seed}")
            for arm, (_, y) in arrays.items():
                if min(int(y.sum()), len(y)-int(y.sum())) < plan["minimum_label_count_by_class"]:
                    raise ValueError(f"Class coverage gate failed in line {seed} / {arm}")
            fit_heads(parent, data, arrays, plan, folder, seed, hook)
            if h.registry.tensor_digest(parent.state_dict()) != frozen_parent:
                raise ValueError("Parent changed during head fitting")
            for name in ("base", "random", "targeted"):
                path = folder / f"{name}.pth"
                checkpoints[str(path.relative_to(out))] = base.sha(path)
        write(out / "frozen_checkpoints.json", checkpoints)
        # Test namespaces are opened only after all endpoint checkpoints exist.
        with (out / "test_opened.json").open("x", encoding="utf-8") as file:
            json.dump(dict(at=time.time(), checkpoint_hashes=checkpoints), file)
        score_families(env, reference, plan, out, deadline, ("test_normal", "test_hard_pool"), scene_info)
        test = panels(plan, scene_info, "test")
        write(out / "family_manifest.json", dict(assignments=scene_info, selected=val | test))
        for seed in plan["seeds"]:
            folder = out / f"line_{seed}"
            parent = historical.PhaseNet(plan["base_config"]["width"]).to("cuda")
            parent.load_state_dict(torch.load(folder / "base.pth", weights_only=True, map_location="cuda")["model"])
            parent.eval().requires_grad_(False)
            heads = {}
            for arm in ("random", "targeted"):
                head = copy.deepcopy(parent.heads[1])
                head.load_state_dict(torch.load(folder / f"{arm}.pth", weights_only=True, map_location="cuda")["model"])
                heads[arm] = head.eval().requires_grad_(False)
            results[str(seed)] = {}
            for panel, families in (test | val).items():
                results[str(seed)][panel] = {}
                for arm in ARMS:
                    rows = []
                    for i, family in enumerate(families, 1):
                        if i == 1 or i % 8 == 0:
                            runtime.status(out, state="EVALUATING", seed=seed, panel=panel, arm=arm, episode=i, training_started=True)
                        row, _ = rollout(h, env, parent, family, plan, out, deadline,
                            timeout=arm == "timeout", completion_head=heads.get(arm))
                        if row["initial_sha256"] != scene_info[family]["initial_sha256"]:
                            raise ValueError("Unpaired test initial state")
                        row["difficulty"] = scene_info[family]["difficulty"]
                        rows.append(row)
                    results[str(seed)][panel][arm] = rows
                    write(out / "results.json", results)
        if any(base.sha(out / path) != digest for path, digest in checkpoints.items()):
            raise ValueError("Checkpoint changed after freeze")
        runtime.verify(out)
        report(out, results, plan, write)
        runtime.status(out, state="COMPLETE", technical_only=plan["technical_only"], lines=len(plan["seeds"]))
    except BaseException as exc:
        state = "PARTIAL_TIME_CAP" if isinstance(exc, TimeoutError) else "STOPPED" if isinstance(exc, InterruptedError) else "FAILED"
        runtime.status(out, state=state, error=repr(exc), traceback=traceback.format_exc(), technical_only=plan["technical_only"])
        (out / "REPORT.md").write_text(f"# Abschlussbericht\n\n{state}\n\n{exc}\n\n"
            "Vollständige Teilresultate und Checkpoints liegen im Laufordner.\n", encoding="utf-8")
        raise
    finally:
        if env is not None:
            env.close()


# Reuse the verified Windows watchdog, deadline and heartbeat implementation.
runtime.HERE, runtime.__file__ = HERE, __file__


def launch(out):
    try:
        runtime.run(out)
    finally:
        if (out / "launch.json").exists() and not (out / "REPORT.md").exists():
            state = read(out / "status.json")
            (out / "REPORT.md").write_text(
                "# Abschlussbericht\n\n" + state["state"] + "\n\n" +
                str(state.get("error", "Terminalstatus und Ergebnisse stehen im Laufordner.")) + "\n",
                encoding="utf-8",
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("prepare", "run", "worker", "verify"))
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--smoke", action="store_true")
    parser.add_argument("--deadline", type=float)
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(RUN_ROOT):
        parser.error("Output must stay in study directory")
    if args.command == "prepare":
        prepare(out, args.smoke)
    elif args.command == "verify":
        runtime.verify(out)
        print("Frozen inputs verified")
    elif args.command == "run":
        launch(out)
    else:
        worker(out, args.deadline)
