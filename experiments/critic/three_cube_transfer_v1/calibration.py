"""N1-4: überwachte Kalibrierung mit eingefrorenen A-Policies."""

import argparse
import ctypes
from datetime import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import random
import subprocess
import sys
import time

import psutil

from difficulty import initial_features


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
OUT = ROOT / "praxis/results/critic/three_cube_transfer_v1/calibration_n1_4"
CURRICULUM = ROOT / "experiments/curriculum"
EXPECTED = 300
HORIZON = 1000
STABLE = 50
STAGES = {"INITIALIZING": "initializing", "EVALUATING": "validation",
          "COMPLETE": "complete", "PAUSED": "paused", "FAILED": "error"}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, value):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.flush()
        os.fsync(stream.fileno())
    for attempt in range(5):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(0.02)


def identity(pid):
    return {"pid": pid, "created_unix": psutil.Process(pid).create_time()}


def alive(process):
    if process is None:
        return False
    try:
        return identity(process["pid"]) == process
    except psutil.NoSuchProcess:
        return False


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def inputs(registry, controller):
    panel = next(split for split in read(HERE / "splits.json")["splits"]
                 if split["id"] == "calibration")
    first, last = panel["first"], panel["last"]
    if (first, last, panel["task_cubes"], panel["target_families"], panel["selection"]) != (
        2100000000, 2100000099, 3, 100, "all"
    ):
        raise ValueError("Kalibrierungsbereich geändert")
    historical = controller.native.historical
    paths = [
        Path(__file__), HERE / "difficulty.py", HERE / "splits.json",
        Path(registry.__file__), CURRICULUM / "axis_bc_20261110/core.py",
        CURRICULUM / "axis_bc_clock_validation_20261112/policy.py",
        Path(controller.__file__), Path(controller.native.__file__),
        Path(historical.__file__), Path(historical.prior.__file__),
        Path(historical.old.__file__),
        ROOT / "praxis/src/task_extensions/environments.py",
        ROOT / "experiments/baselines/additional_tasks/stack_two/task_info.json",
    ]
    return {
        "parents": {str(seed): entry for seed, entry in registry.frozen_abc_a().items()},
        "schedule": [[scene, parent] for scene in range(first, last + 1) for parent in (1, 2, 3)],
        "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in paths},
        "device": "cpu",
        "horizon_frames": HORIZON,
        "success_frames": STABLE,
        "optimizer_updates": 0,
    }


def digest(data):
    return hashlib.sha256(data).hexdigest()


def episode(base, controller, adapter, torch, np, model, threshold, cap, seed, deadline):
    historical = controller.native.historical
    started = time.perf_counter()
    base.check_stop(OUT, deadline)
    # New environment and per-episode seeds make the next episode independent
    # of simulator and RNG state from previous episodes.
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    env = historical.make_env(3)
    try:
        random.seed(seed)
        np.random.seed(seed)
        env.reset()
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        initial = env.sim.get_state().flatten().copy()
        positions = env.sim.data.body_xpos[env.cube_ids].copy()
        table_offset = np.asarray(env.table_offset)
        geometry = initial_features(positions, table_offset)
        initial_xyz = positions.tolist()
        seq = controller.GuardedSequencer(model, 3, controller.Clearance(env))
        seq.policy = adapter.make_policy(base, historical, model, threshold, lambda: seq.stage, cap)
        tail = longest = 0
        trajectory = hashlib.sha256()
        for frame in range(1, HORIZON + 1):
            base.check_stop(OUT, deadline)
            stage = seq.stage
            trajectory.update(env.sim.get_state().flatten().tobytes())
            action, _, _ = seq.policy.action(obs, positions[stage - 1], positions[stage])
            trajectory.update(action.tobytes())
            env.step(action)
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            positions = env.sim.data.body_xpos[env.cube_ids].copy()
            fingers = [controller.native.finger_contact(env, cube) for cube in env.cubes]
            valid = [historical.old.prefix_valid(env, k) and not any(fingers[:k]) for k in (2, 3)]
            seq.advance(valid[stage - 1], positions[stage])
            tail = tail + 1 if valid[-1] else 0
            longest = max(longest, tail)
            if tail >= STABLE or seq.timed_out:
                break
        trajectory.update(env.sim.get_state().flatten().tobytes())
        success = tail >= STABLE
        result = dict(
            initial_sha256=digest(initial.tobytes()), trajectory_sha256=trajectory.hexdigest(),
            initial_xyz_m=initial_xyz,
            features=geometry, table_offset_m=table_offset.tolist(), success=success,
            frames=frame, max_stable_frames=longest, reached_second_placement=seq.stage == 2,
            termination="success" if success else "retreat_timeout" if seq.timed_out else "horizon",
        )
    finally:
        env.close()
    result["elapsed_seconds"] = time.perf_counter() - started
    return result


def episode_path(index):
    return OUT / "episodes" / f"{index:03d}.json"


def check_row(row, index, schedule, scenes):
    if [row["scene_seed"], row["parent_seed"]] != schedule[index]:
        raise ValueError(f"Unerwartete Szenen-/Parent-Zuordnung in Episode {index}")
    key = (row["initial_sha256"], row["initial_xyz_m"], row["table_offset_m"], row["features"])
    if scenes.setdefault(row["scene_seed"], key) != key:
        raise ValueError(f"Startzustände unterscheiden sich für Szene {row['scene_seed']}")
    if (not 1 <= row["frames"] <= HORIZON or
            row["success"] != (row["max_stable_frames"] == STABLE) or
            row["success"] != (row["termination"] == "success")):
        raise ValueError(f"Ungültiges Episodenergebnis {index}")


def worker(deadline):
    status_path = OUT / "status.json"
    previous = read(status_path) if status_path.exists() else {}
    previous_wall = previous.get("active_wall_seconds", 0)
    started = time.perf_counter()
    state = dict(state="INITIALIZING", worker=identity(os.getpid()), planned_episodes=EXPECTED,
                 completed_episodes=previous.get("completed_episodes", 0), optimizer_updates=0)

    def status(**fields):
        state.update(fields, heartbeat_unix=time.time(),
                     active_wall_seconds=previous_wall + time.perf_counter() - started)
        state.update(stage=STAGES[state["state"]], rendered=state["completed_episodes"],
                     render_total=EXPECTED, split="calibration")
        write(status_path, state)

    status()
    try:
        os.environ["NUMBA_CACHE_DIR"] = str(OUT / "numba")
        registry = load_module("calibration_registry", CURRICULUM / "registry.py")
        base, torch = registry.libraries()
        np = base.np
        base.configure(1)
        controller = base.backend()
        adapter = load_module("calibration_clock", CURRICULUM / "axis_bc_clock_validation_20261112/policy.py")
        plan = inputs(registry, controller)
        plan["seeds"] = [1, 2, 3]
        plan["software"] = {name: getattr(sys.modules[name], "__version__", None)
                            for name in ("torch", "numpy", "robosuite", "mujoco")}
        plan_path = OUT / "config.json"
        if plan_path.exists():
            if read(plan_path) != plan:
                raise ValueError("Provenienz des bestehenden Laufs geändert")
        else:
            write(plan_path, plan)
        models = {int(seed): registry.restore_abc_a_for_inference(int(seed), entry)
                  for seed, entry in plan["parents"].items()}
        schedule = plan["schedule"]
        scenes, rows = {}, []
        files = sorted((OUT / "episodes").glob("*.json"))
        for index, path in enumerate(files):
            if path != episode_path(index) or index >= EXPECTED:
                raise ValueError("Kanonische Episodenfolge unterbrochen")
            row = read(path)
            check_row(row, index, schedule, scenes)
            rows.append(row)
        status(state="EVALUATING", completed_episodes=len(rows))
        for index in range(len(rows), EXPECTED):
            scene, parent = schedule[index]
            row = episode(base, controller, adapter, torch, np, *models[parent], scene, deadline)
            row.update(scene_seed=scene, parent_seed=parent)
            check_row(row, index, schedule, scenes)
            write(episode_path(index), row)
            rows.append(row)
            status(completed_episodes=len(rows))
        seconds = sum(row["elapsed_seconds"] for row in rows)
        active_wall_seconds = previous_wall + time.perf_counter() - started
        summary = dict(
            planned_episodes=EXPECTED, completed_episodes=len(rows), families=len(scenes),
            successes=sum(row["success"] for row in rows),
            by_parent={str(p): dict(successes=sum(r["success"] for r in rows if r["parent_seed"] == p),
                                    episodes=sum(r["parent_seed"] == p for r in rows))
                       for p in (1, 2, 3)},
            episode_wall_seconds=seconds, episodes_per_hour=3600 * len(rows) / seconds,
            worker_wall_seconds=active_wall_seconds,
            worker_episodes_per_hour=3600 * len(rows) / active_wall_seconds,
            raw_sha256=digest(b"".join(episode_path(i).read_bytes() for i in range(len(rows)))),
            config_sha256=digest(plan_path.read_bytes()), optimizer_updates=0,
        )
        write(OUT / "summary.json", summary)
        status(state="COMPLETE")
    except (InterruptedError, TimeoutError) as error:
        status(state="PAUSED", reason=str(error))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def time_argument(value):
    timestamp = datetime.fromisoformat(value)
    if timestamp.utcoffset() is None:
        raise ValueError("Zeitzonenoffset erforderlich")
    return timestamp.timestamp()


def supervise(cutoff, deadline, resume):
    if time.time() >= cutoff or deadline < cutoff + 30:
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")
    if resume:
        previous = read(OUT / "supervisor_status.json")
        if (previous["state"] != "PAUSED" or alive(previous["supervisor"])
                or alive(read(OUT / "status.json")["worker"]) or (OUT / "STOP").exists()):
            raise ValueError("Fortsetzung erfordert PAUSED, inaktive Prozesse und entfernte STOP-Datei")
    else:
        OUT.mkdir()
        (OUT / "episodes").mkdir()
    claim = OUT / "supervisor.lock"
    with claim.open("x") as lock:
        lock.write(str(os.getpid()))
    path = OUT / "supervisor_status.json"
    state = dict(state="STARTING", supervisor=identity(os.getpid()), deadline_unix=deadline)
    child = None
    awake = False
    try:
        write(path, state)
        if time.time() >= cutoff:
            raise TimeoutError("Startfenster geschlossen")
        if os.name == "nt":
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (OUT / "worker.log").open("ab") as log:
            child = subprocess.Popen([sys.executable, "-u", str(Path(__file__)), "_worker",
                                      "--deadline", str(deadline - 30)], cwd=ROOT,
                                     stdout=log, stderr=subprocess.STDOUT)
            state.update(state="RUNNING", launcher=identity(child.pid), sleep_prevention=awake)
            write(path, state)
            code = child.wait(timeout=max(0.01, deadline - time.time()))
        state.update(state=read(OUT / "status.json")["state"], worker_exitcode=code)
        if code != 0:
            state["state"] = "FAILED"
    except subprocess.TimeoutExpired:
        state.update(state="FAILED", reason="Harte Deadline erreicht")
    except Exception as error:
        state.update(state="FAILED", reason=repr(error))
        raise
    finally:
        if child is not None and child.poll() is None:
            for process in reversed(psutil.Process(child.pid).children(recursive=True)):
                try:
                    process.kill()
                except psutil.NoSuchProcess:
                    pass
            child.kill()
            child.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state["updated_unix"] = time.time()
        write(path, state)
        claim.unlink()
    return int(state["state"] == "FAILED")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("launch", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--cutoff", type=time_argument, required=True)
        command.add_argument("--deadline", type=time_argument, required=True)
    commands.add_parser("_worker").add_argument("--deadline", type=float, required=True)
    args = parser.parse_args()
    if args.command == "_worker":
        if not (OUT / "supervisor.lock").exists():
            parser.error("Worker nur über den Supervisor starten")
        worker(args.deadline)
        return 0
    return supervise(args.cutoff, args.deadline, args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
