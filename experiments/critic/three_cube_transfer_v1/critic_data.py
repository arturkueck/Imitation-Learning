"""N2-1: Critic-Daten mit den drei eingefrorenen A-Parents erheben (0 Optimizerupdates).

Befehle (aus dem Repository-Stamm):
  integration                      einzelne technische Prüfung auf Kalibrierungsepisode 000
  start launch|resume --cutoff T --deadline T   Supervisor losgelöst starten (empfohlen)
  launch --cutoff T --deadline T   Supervisor im Vordergrund (Zeitstempel mit Zonenoffset)
  resume --cutoff T --deadline T   nach PAUSED exakt an der nächsten Episode fortsetzen
  monitor                          inkrementeller Monitor

Datenvertrag nach PROTOCOL.md §4. Szenen ausschließlich aus dem Split `critic_data`.
"""

import argparse
import ctypes
import hashlib
import io
import json
import os
from pathlib import Path
import random
import re
import subprocess
import sys
import time

import numpy as np
import psutil

from calibration import (CURRICULUM, HERE, ROOT, digest, identity, alive, load_module,
                         read, time_argument, write)
import calibration


RESULTS = ROOT / "praxis/results/critic/three_cube_transfer_v1"
OUT = RESULTS / "critic_data_n2_1"
INTEGRATION = RESULTS / "critic_data_n2_1_integration"
PARENTS = (1, 2, 3)
FAMILIES = 300
EXPECTED = FAMILIES * len(PARENTS)
HORIZON = calibration.HORIZON
STABLE = calibration.STABLE
GAMMA = 0.995
RETREAT_TIMEOUT = 200
STAGES = calibration.STAGES
CUBES = "ABC"

# Spaltenzuordnung der Critic-Eingabe (PROTOCOL.md §4, §12). Positionen relativ zur
# Tischmitte (table_offset) in Metern, Quaternionen dimensionslos.
CRITIC_COLUMNS = (
    [f"cube_{c}_{a}_m" for c in CUBES for a in "xyz"]
    + [f"cube_{c}_quat_{a}" for c in CUBES for a in "wxyz"]
    + [f"eef_{a}_m" for a in "xyz"]
    + [f"eef_quat_{a}" for a in "xyzw"]
    + ["gripper_qpos_0_m", "gripper_qpos_1_m"]
    + ["stage_2"]
    + [f"phase_{k}" for k in range(7)]
    + ["retreat"]
    + ["remaining_time"]
)
CRITIC_DIM = len(CRITIC_COLUMNS)
ACTOR_COLUMNS = ["eef_minus_anchor_x_dm", "eef_minus_anchor_y_dm", "eef_minus_anchor_z_dm",
                 "eef_quat_x", "eef_quat_y", "eef_quat_z", "eef_quat_w",
                 "gripper_qpos_0_scaled", "gripper_qpos_1_scaled", "clock_input"]
ACTION_COLUMNS = ["x", "y", "z", "rot_x", "rot_y", "rot_z", "gripper"]
TERMINATIONS = ("success", "retreat_timeout", "horizon", "simulator_instability")
ARRAYS = {
    "frame": ((), np.int32), "stage": ((), np.int8), "phase": ((), np.int8),
    "retreat": ((), np.bool_), "phase_steps": ((), np.int32), "retreat_actions": ((), np.int32),
    "critic_state": ((CRITIC_DIM,), np.float32), "actor_input": ((10,), np.float32),
    "actor_phase": ((), np.int8), "executed_action": ((7,), np.float64),
    "parent_action": ((7,), np.float64), "next_critic_state": ((CRITIC_DIM,), np.float32),
    "reward": ((), np.float32), "terminal": ((), np.bool_), "discounted_return": ((), np.float64),
}


def critic_state(env, obs, positions, table_offset, stage, phase, retreat, frame):
    """Privilegierter Zustand an der Episodengrenze `frame` (bereits ausgeführte Frames)."""
    quats = np.asarray([env.sim.data.body_xquat[i] for i in env.cube_ids], dtype=np.float64)
    phases = np.zeros(7)
    phases[phase] = 1.0
    value = np.concatenate([
        (positions - table_offset).ravel(), quats.ravel(),
        np.asarray(obs["robot0_eef_pos"]) - table_offset, np.asarray(obs["robot0_eef_quat"]),
        np.asarray(obs["robot0_gripper_qpos"]), [float(stage == 2)], phases, [float(retreat)],
        [(HORIZON - frame) / HORIZON],
    ]).astype(np.float32)
    if value.shape != (CRITIC_DIM,):
        raise ValueError("Critic-Zustand hat unerwartete Länge")
    return value


def returns(length, success):
    """Reward, Terminalflag und beobachteter diskontierter Return einer Episode."""
    reward = np.zeros(length, np.float32)
    terminal = np.zeros(length, np.bool_)
    terminal[-1] = True
    if success:
        reward[-1] = 1.0
        value = GAMMA ** np.arange(length - 1, -1, -1, dtype=np.float64)
    else:
        value = np.zeros(length, np.float64)
    return reward, terminal, value


def mujoco_warnings(env):
    try:
        data = getattr(env.sim.data, "_data", env.sim.data)
        return [int(item.number) for item in data.warning]
    except (AttributeError, TypeError):
        return None


def episode(base, controller, adapter, torch, model, threshold, cap, seed, parent, deadline, out):
    """Wie calibration.episode, zusätzlich mit Übergängen nach Datenvertrag."""
    historical = controller.native.historical
    started = time.perf_counter()
    base.check_stop(out, deadline)
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
        table_offset = np.asarray(env.table_offset, dtype=np.float64)
        seq = controller.GuardedSequencer(model, 3, controller.Clearance(env))
        seq.policy = adapter.make_policy(base, historical, model, threshold, lambda: seq.stage, cap)
        tail = longest = 0
        trajectory = hashlib.sha256()
        rows = {key: [] for key in ARRAYS if key not in ("reward", "terminal", "discounted_return")}
        instability = False
        state = env.sim.get_state().flatten()
        for frame in range(1, HORIZON + 1):
            base.check_stop(out, deadline)
            stage = seq.stage
            policy = seq.policy
            phase, steps, retreat = policy.phase, policy.steps, seq.retreat
            before = critic_state(env, obs, positions, table_offset, stage, phase, retreat, frame - 1)
            trajectory.update(state.tobytes())
            action, actual, _ = policy.action(obs, positions[stage - 1], positions[stage])
            if actual != phase:
                raise ValueError("Phasenzuordnung des Parents inkonsistent")
            trajectory.update(action.tobytes())
            rows["frame"].append(frame - 1)
            rows["stage"].append(stage)
            rows["phase"].append(phase)
            rows["retreat"].append(retreat)
            rows["phase_steps"].append(steps)
            rows["retreat_actions"].append(seq.retreat_actions)
            rows["critic_state"].append(before)
            rows["actor_input"].append(np.asarray(policy.last_x, np.float32))
            rows["actor_phase"].append(phase)
            rows["executed_action"].append(action.copy())
            rows["parent_action"].append(action.copy())
            env.step(action)
            env.sim.forward()
            obs = env._get_observations(force_update=True)
            positions = env.sim.data.body_xpos[env.cube_ids].copy()
            state = env.sim.get_state().flatten()
            if not (np.isfinite(state).all() and np.isfinite(positions).all()
                    and all(np.isfinite(np.asarray(v)).all() for v in obs.values())):
                instability = True
                rows["next_critic_state"].append(np.full(CRITIC_DIM, np.nan, np.float32))
                break
            fingers = [controller.native.finger_contact(env, cube) for cube in env.cubes]
            valid = [historical.old.prefix_valid(env, k) and not any(fingers[:k]) for k in (2, 3)]
            seq.advance(valid[stage - 1], positions[stage])
            tail = tail + 1 if valid[-1] else 0
            longest = max(longest, tail)
            rows["next_critic_state"].append(critic_state(
                env, obs, positions, table_offset, seq.stage, seq.policy.phase, seq.retreat, frame))
            if tail >= STABLE or seq.timed_out:
                break
        trajectory.update(state.tobytes())
        success = tail >= STABLE and not instability
        termination = ("simulator_instability" if instability else "success" if success
                       else "retreat_timeout" if seq.timed_out else "horizon")
        arrays = {key: np.asarray(value, dtype=ARRAYS[key][1]) for key, value in rows.items()}
        arrays["reward"], arrays["terminal"], arrays["discounted_return"] = returns(frame, success)
        result = dict(
            initial_sha256=digest(initial.tobytes()), trajectory_sha256=trajectory.hexdigest(),
            success=success, frames=frame, max_stable_frames=longest,
            reached_second_placement=seq.stage == 2, termination=termination,
            reached_points=sorted({(int(s), int(p), bool(r)) for s, p, r in
                                   zip(arrays["stage"], arrays["phase"], arrays["retreat"])}),
            mujoco_warning_counts=mujoco_warnings(env),
        )
    finally:
        env.close()
    result["elapsed_seconds"] = time.perf_counter() - started
    return result, arrays


def check_arrays(arrays, row):
    """Datenvertrag einer Episode prüfen (Formen, Konsistenz, Reward/Return)."""
    n = row["frames"]
    if set(arrays) != set(ARRAYS):
        raise ValueError("Unerwartete Arrays")
    for key, (shape, dtype) in ARRAYS.items():
        if arrays[key].shape != (n, *shape) or arrays[key].dtype != dtype:
            raise ValueError(f"Form oder Typ von {key} ungültig")
    if not np.array_equal(arrays["frame"], np.arange(n)):
        raise ValueError("Framenummern unterbrochen")
    if not np.array_equal(arrays["executed_action"], arrays["parent_action"]):
        raise ValueError("Ausgeführte Aktion weicht vom eingefrorenen Parent ab")
    if not np.array_equal(arrays["actor_phase"], arrays["phase"]):
        raise ValueError("Actorphase inkonsistent")
    if not np.array_equal(arrays["critic_state"][1:], arrays["next_critic_state"][:-1]):
        raise ValueError("Folgezustand passt nicht zum nächsten Zustand")
    finite = [k for k in ARRAYS if k != "next_critic_state"]
    if not all(np.isfinite(arrays[k].astype(np.float64)).all() for k in finite):
        raise ValueError("Nicht endliche Werte")
    if row["termination"] != "simulator_instability" and not np.isfinite(arrays["next_critic_state"]).all():
        raise ValueError("Nicht endlicher Folgezustand")
    reward, terminal, value = returns(n, row["success"])
    if not (np.array_equal(arrays["reward"], reward) and np.array_equal(arrays["terminal"], terminal)
            and np.array_equal(arrays["discounted_return"], value)):
        raise ValueError("Reward, Terminalflag oder Return ungültig")
    if (row["termination"] not in TERMINATIONS or not 1 <= n <= HORIZON
            or row["success"] != (row["termination"] == "success")
            or row["success"] != (row["max_stable_frames"] == STABLE)):
        raise ValueError("Ungültiger Episodenausgang")


def encode(arrays):
    buffer = io.BytesIO()
    np.savez_compressed(buffer, **arrays)
    return buffer.getvalue()


def decode(data):
    with np.load(io.BytesIO(data), allow_pickle=False) as archive:
        return {key: archive[key] for key in archive.files}


def write_bytes(path, data):
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def paths(out, index):
    return out / "episodes" / f"{index:04d}.npz", out / "episodes" / f"{index:04d}.json"


def critic_split():
    entries = [next(s for s in read(HERE / name)["splits"] if s["id"] == "critic_data")
               for name in ("splits.json", "splits_v2.json")]
    keys = ("first", "last", "task_cubes", "target_families", "selection")
    if any(tuple(e[k] for k in keys) != (2100000100, 2100000399, 3, FAMILIES, "all") for e in entries):
        raise ValueError("Critic-Datenbereich weicht vom Protokoll ab")
    return entries[0]["first"], entries[0]["last"]


def plan(registry, controller):
    first, last = critic_split()
    historical = controller.native.historical
    sources = [
        Path(__file__), HERE / "calibration.py", HERE / "splits.json", HERE / "splits_v2.json",
        HERE / "PROTOCOL.md", Path(registry.__file__), CURRICULUM / "axis_bc_20261110/core.py",
        CURRICULUM / "axis_bc_clock_validation_20261112/policy.py",
        Path(controller.__file__), Path(controller.native.__file__),
        Path(historical.__file__), Path(historical.prior.__file__), Path(historical.old.__file__),
        ROOT / "praxis/src/task_extensions/environments.py",
        ROOT / "experiments/baselines/additional_tasks/stack_two/task_info.json",
    ]
    return {
        "task": "N2-1", "protocol": "protocol_v1", "split": "critic_data",
        "parents": {str(seed): entry for seed, entry in registry.frozen_abc_a().items()},
        "schedule": [[scene, parent] for scene in range(first, last + 1) for parent in PARENTS],
        "source_sha256": {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sources},
        "device": "cpu", "horizon_frames": HORIZON, "success_frames": STABLE, "gamma": GAMMA,
        "retreat_timeout_actions": RETREAT_TIMEOUT, "optimizer_updates": 0,
        "exploration": "keine; ausgeführte Aktion = Parentaktion",
        "critic_columns": CRITIC_COLUMNS, "actor_columns": ACTOR_COLUMNS,
        "action_columns": ACTION_COLUMNS, "arrays": {k: [list(s), np.dtype(t).name] for k, (s, t) in ARRAYS.items()},
        "terminations": list(TERMINATIONS),
    }


def setup(out):
    os.environ["NUMBA_CACHE_DIR"] = str(out / "numba")
    registry = load_module("critic_data_registry", CURRICULUM / "registry.py")
    base, torch = registry.libraries()
    base.configure(1)
    controller = base.backend()
    adapter = load_module("critic_data_clock", CURRICULUM / "axis_bc_clock_validation_20261112/policy.py")
    return registry, base, torch, controller, adapter


def check_row(row, index, schedule, scenes):
    if [row["scene_seed"], row["parent_seed"]] != schedule[index] or row["index"] != index:
        raise ValueError(f"Unerwartete Szenen-/Parent-Zuordnung in Episode {index}")
    if scenes.setdefault(row["scene_seed"], row["initial_sha256"]) != row["initial_sha256"]:
        raise ValueError(f"Startzustände unterscheiden sich für Szene {row['scene_seed']}")


def load_episode(out, index, schedule, scenes):
    data_path, row_path = paths(out, index)
    row = read(row_path)
    data = data_path.read_bytes()
    if digest(data) != row["arrays_sha256"]:
        raise ValueError(f"Hash der Episode {index} stimmt nicht")
    check_row(row, index, schedule, scenes)
    check_arrays(decode(data), row)
    return row


def summarize(rows, config_path, out, active_wall_seconds):
    successes = {str(p): sum(r["success"] for r in rows if r["parent_seed"] == p) for p in PARENTS}
    episodes = {str(p): sum(r["parent_seed"] == p for r in rows) for p in PARENTS}
    terminations = {str(p): {t: sum(r["termination"] == t for r in rows if r["parent_seed"] == p)
                             for t in TERMINATIONS} for p in PARENTS}
    points = {}
    for r in rows:
        for stage, phase, retreat in r["reached_points"]:
            key = f"stage{stage}_phase{phase}" + ("_retreat" if retreat else "")
            entry = points.setdefault(key, {str(p): {"episodes": 0, "successes": 0} for p in PARENTS})
            entry[str(r["parent_seed"])]["episodes"] += 1
            entry[str(r["parent_seed"])]["successes"] += r["success"]
    episode_hashes = [r["arrays_sha256"] for r in rows]
    seconds = sum(r["elapsed_seconds"] for r in rows)
    return dict(
        planned_episodes=EXPECTED, completed_episodes=len(rows),
        families=len({r["scene_seed"] for r in rows}),
        successes=sum(successes.values()), failures=len(rows) - sum(successes.values()),
        by_parent={p: dict(episodes=episodes[p], successes=successes[p], failures=episodes[p] - successes[p],
                           terminations=terminations[p],
                           frames=sum(r["frames"] for r in rows if r["parent_seed"] == int(p)))
                   for p in episodes},
        frames=sum(r["frames"] for r in rows), reached_points=dict(sorted(points.items())),
        episode_wall_seconds=seconds, worker_wall_seconds=active_wall_seconds,
        worker_episodes_per_hour=3600 * len(rows) / active_wall_seconds,
        dataset_sha256=digest("\n".join(episode_hashes).encode()),
        rows_sha256=digest(b"".join(paths(out, i)[1].read_bytes() for i in range(len(rows)))),
        config_sha256=digest(config_path.read_bytes()), optimizer_updates=0,
        hash_contract="dataset_sha256 = SHA-256 der zeilenweise verketteten arrays_sha256 in Episodenreihenfolge",
    )


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
                     render_total=EXPECTED, split="critic_data")
        write(status_path, state)

    status()
    try:
        registry, base, torch, controller, adapter = setup(OUT)
        config = plan(registry, controller)
        config["software"] = {name: getattr(sys.modules[name], "__version__", None)
                              for name in ("torch", "numpy", "robosuite", "mujoco")}
        config_path = OUT / "config.json"
        if config_path.exists():
            if read(config_path) != config:
                raise ValueError("Provenienz des bestehenden Laufs geändert")
        else:
            write(config_path, config)
        models = {int(seed): registry.restore_abc_a_for_inference(int(seed), entry)
                  for seed, entry in config["parents"].items()}
        schedule = config["schedule"]
        scenes, rows = {}, []
        while len(rows) < EXPECTED and paths(OUT, len(rows))[1].exists():
            rows.append(load_episode(OUT, len(rows), schedule, scenes))
        if any(int(p.stem) >= len(rows) for p in (OUT / "episodes").glob("*.json")):
            raise ValueError("Kanonische Episodenfolge unterbrochen")
        status(state="EVALUATING", completed_episodes=len(rows))
        for index in range(len(rows), EXPECTED):
            scene, parent = schedule[index]
            row, arrays = episode(base, controller, adapter, torch, *models[parent], scene, parent, deadline, OUT)
            data = encode(arrays)
            row.update(index=index, scene_seed=scene, parent_seed=parent, arrays_sha256=digest(data))
            check_row(row, index, schedule, scenes)
            check_arrays(arrays, row)
            data_path, row_path = paths(OUT, index)
            write_bytes(data_path, data)
            write(row_path, row)
            rows.append(row)
            status(completed_episodes=len(rows))
        summary = summarize(rows, config_path, OUT, previous_wall + time.perf_counter() - started)
        write(OUT / "summary.json", summary)
        status(state="COMPLETE")
    except (InterruptedError, TimeoutError) as error:
        status(state="PAUSED", reason=str(error))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def integration():
    """Einzelne technische Prüfung: Kalibrierungsepisode 000 (Szene 2100000000, Parent 1)
    muss mit dem Erhebungscode dieselbe Trajektorie liefern. Nicht Teil der 900 Episoden."""
    reference = read(calibration.OUT / "episodes" / "000.json")
    if (reference["scene_seed"], reference["parent_seed"]) != (2100000000, 1):
        raise ValueError("Unerwartete Kalibrierungsreferenz")
    INTEGRATION.mkdir(exist_ok=False)
    registry, base, torch, controller, adapter = setup(INTEGRATION)
    entry = registry.frozen_abc_a()[1]
    model = registry.restore_abc_a_for_inference(1, entry)
    row, arrays = episode(base, controller, adapter, torch, *model, 2100000000, 1,
                          time.time() + 600, INTEGRATION)
    data = encode(arrays)
    row.update(index=0, scene_seed=2100000000, parent_seed=1, arrays_sha256=digest(data))
    check_arrays(arrays, row)
    check_arrays(decode(data), row)
    keys = ("initial_sha256", "trajectory_sha256", "success", "frames", "max_stable_frames", "termination")
    comparison = {k: dict(calibration=reference[k], n2_1=row[k], equal=reference[k] == row[k]) for k in keys}
    result = dict(purpose="Einzelne technische Integrationsprüfung nach PROTOCOL.md §12; nicht Teil der 900 Episoden",
                  reference=str((calibration.OUT / "episodes/000.json").relative_to(ROOT).as_posix()),
                  comparison=comparison, passed=all(v["equal"] for v in comparison.values()),
                  critic_dim=CRITIC_DIM, frames=row["frames"], arrays_sha256=row["arrays_sha256"],
                  elapsed_seconds=row["elapsed_seconds"], mujoco_warning_counts=row["mujoco_warning_counts"],
                  optimizer_updates=0)
    write(INTEGRATION / "result.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "comparison"} |
                     {"equal": {k: v["equal"] for k, v in comparison.items()}}, ensure_ascii=True))
    return 0 if result["passed"] else 1


def supervise(cutoff, deadline, resume):
    if time.time() >= cutoff or deadline < cutoff + 30:
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")
    if not read(INTEGRATION / "result.json")["passed"]:
        raise ValueError("Integrationsprüfung nicht bestanden")
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
    state = dict(state="STARTING", supervisor=identity(os.getpid()), deadline_unix=deadline, cutoff_unix=cutoff)
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
                                      "--deadline", str(deadline - 60)], cwd=ROOT,
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


def detach(command, cutoff, deadline):
    """Supervisor als vom aufrufenden Agenten losgelösten Prozess starten."""
    if time.time() >= time_argument(cutoff):
        raise ValueError("Startfenster geschlossen")
    arguments = [sys.executable, str(Path(__file__)), command, "--cutoff", cutoff, "--deadline", deadline]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "critic_data_n2_1_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags | 0x01000000)
        except OSError:  # Job erlaubt kein CREATE_BREAKAWAY_FROM_JOB
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
    print(json.dumps(identity(child.pid)))
    return 0


def verify(config, summary):
    scenes, rows = {}, []
    for index in range(EXPECTED):
        rows.append(load_episode(OUT, index, config["schedule"], scenes))
    expected = summarize(rows, OUT / "config.json", OUT, summary["worker_wall_seconds"])
    if expected != summary or len(scenes) != FAMILIES:
        raise ValueError("Zusammenfassung stimmt nicht mit den 900 Rohepisoden überein")


def new_errors(previous):
    path = OUT / "worker.log"
    if not path.exists():
        return None, 0, []
    with path.open("rb") as stream:
        stat = path.stat()
        file_id = [stat.st_dev, stat.st_ino]
        offset = previous.get("log_offset", 0) if previous.get("log_id") == file_id else 0
        stream.seek(offset if offset <= stat.st_size else 0)
        data = stream.read()
        complete = data.rfind(b"\n") + 1
        errors = [line.strip() for line in data[:complete].decode(errors="replace").splitlines()
                  if re.search(r"Traceback|(?:Error|Exception):|nonfinite|out of memory", line, re.I)]
        return file_id, stream.tell() - len(data) + complete, errors


def monitor():
    supervisor_path, worker_path = OUT / "supervisor_status.json", OUT / "status.json"
    if not supervisor_path.is_file():
        print("OFFEN | Kein Supervisorstatus für N2-1")
        return 0 if not OUT.exists() else 2
    supervisor = read(supervisor_path)
    running = alive(supervisor["supervisor"])
    worker_state = read(worker_path) if worker_path.is_file() else {}
    worker_running = alive(worker_state.get("worker"))
    previous_path = OUT / "monitor_state.json"
    previous = read(previous_path) if previous_path.is_file() else {}
    file_id, offset, errors = new_errors(previous)
    completed = start = previous.get("completed", 0)
    successes = previous.get("successes", 0)
    while completed < EXPECTED and paths(OUT, completed)[1].is_file():
        successes += read(paths(OUT, completed)[1])["success"]
        completed += 1
    now = time.time()
    progress_time = now if completed > start else previous.get("progress_time", now)
    output = dict(supervisor=supervisor["supervisor"], supervisor_alive=running, supervisor_state=supervisor["state"],
                  worker=worker_state.get("worker"), worker_alive=worker_running,
                  worker_state=worker_state.get("state"), completed=completed, planned=EXPECTED,
                  new_episodes=completed - start, successes=successes,
                  next_episode=None if completed == EXPECTED else completed,
                  deadline_unix=supervisor["deadline_unix"], errors=errors)
    state = supervisor["state"]
    result_verified = previous.get("result_verified", False)
    if (state == "COMPLETE" and worker_state.get("state") == "COMPLETE" and not worker_running
            and supervisor.get("worker_exitcode") == 0 and completed == EXPECTED):
        summary = read(OUT / "summary.json")
        if not result_verified:
            verify(read(OUT / "config.json"), summary)
        result_verified = True
        code = 0
        output.update(status="COMPLETE", summary={k: summary[k] for k in (
            "completed_episodes", "families", "successes", "failures", "by_parent", "frames",
            "dataset_sha256", "rows_sha256", "config_sha256", "worker_episodes_per_hour", "optimizer_updates")})
    elif state == "PAUSED" and not worker_running and supervisor.get("worker_exitcode") == 0:
        code = 0
        output.update(status="PAUSED", reason=worker_state.get("reason"))
    elif state == "FAILED" or errors or not running or (state == "RUNNING" and now >= supervisor["deadline_unix"]):
        code = 2
        output.update(status="ERROR", reason=worker_state.get("reason") or supervisor.get("reason"))
    elif now - progress_time > 180:
        code = 1
        output.update(status="WARNING", reason="Seit mindestens 180 s keine neue persistierte Episode")
    else:
        code = 0
        output.update(status="OK")
    write(previous_path, dict(completed=completed, successes=successes, progress_time=progress_time,
                              checked_unix=now, log_id=file_id, log_offset=offset,
                              result_verified=result_verified))
    print(json.dumps(output, ensure_ascii=True))
    return code


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("launch", "resume"):
        command = commands.add_parser(name)
        command.add_argument("--cutoff", type=time_argument, required=True)
        command.add_argument("--deadline", type=time_argument, required=True)
    start = commands.add_parser("start")
    start.add_argument("mode", choices=("launch", "resume"))
    start.add_argument("--cutoff", required=True)
    start.add_argument("--deadline", required=True)
    commands.add_parser("_worker").add_argument("--deadline", type=float, required=True)
    commands.add_parser("integration")
    commands.add_parser("monitor")
    args = parser.parse_args()
    if args.command == "start":
        time_argument(args.deadline)
        return detach(args.mode, args.cutoff, args.deadline)
    if args.command == "_worker":
        if not (OUT / "supervisor.lock").exists():
            parser.error("Worker nur über den Supervisor starten")
        worker(args.deadline)
        return 0
    if args.command == "integration":
        return integration()
    if args.command == "monitor":
        return monitor()
    return supervise(args.cutoff, args.deadline, args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
