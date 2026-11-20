"""N2-1b: Critic-Daten mit Explorationsrauschen (PROTOCOL_V2.md §E, 0 Optimizerupdates).

Befehle (aus dem Repository-Stamm):
  integration                      technische Prüfung vor dem Lauf (nicht Teil der 900 Episoden)
  start launch|resume --cutoff T --deadline T   Supervisor losgelöst starten (empfohlen)
  launch --cutoff T --deadline T   Supervisor im Vordergrund (Zeitstempel mit Zonenoffset)
  resume --cutoff T --deadline T   nach PAUSED exakt an der nächsten Episode fortsetzen
  monitor                          inkrementeller Monitor

Die drei unveränderten A-Parents laufen auf dem Split `critic_data_noisy` (splits_v3.json).
Auf XYZ wird Gaußrauschen σ = 0,05 addiert und mit der Regel aus PROTOCOL.md §7
(ac_smoke.make_bound) in die Grenze der weitesten Stufe δ_max = 0,20 projiziert. Greifer ohne
Rauschen, Abschlusslogit, Sequencer, Rückzug und Uhrkorrektur wie in N2-1 (critic_data.episode).
Datenvertrag wie N2-1, zusätzlich je Frame Rauschwert und Grenze; `parent_action` ist die
Parentaktion, `executed_action` die verrauschte, begrenzte Aktion.
"""

import argparse
import ctypes
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

import numpy as np
import psutil

from calibration import HERE, ROOT, digest, identity, alive, read, time_argument, write
import calibration
import critic_data as cd
from ac_smoke import make_bound


RESULTS = cd.RESULTS
OUT = RESULTS / "critic_data_noisy_n2_1b"
INTEGRATION = RESULTS / "critic_data_noisy_n2_1b_integration"
SPLIT = "critic_data_noisy"
FIRST, LAST = 2100003690, 2100003989
PARENTS = cd.PARENTS
FAMILIES = 300
EXPECTED = FAMILIES * len(PARENTS)
IDX = [0, 1, 2, 6]  # x, y, z, Greifer im 7er-Aktionsvektor (Modellausgabe hat 4 Spalten)
NOISE = dict(
    std_xyz=0.05, std_gripper=0.0, delta_max=0.20, gripper_bound=0.02, seed_base=7600,
    rng="numpy default_rng([7600 + p, Szenenseed]) je Episode: Wurzel 7600 + p nach PROTOCOL_V2.md §E, "
        "je Episode eigener Strom, damit jede Fortsetzung exakt reproduziert",
    projection="a = clip(a_p + b·tanh((a_p + ε − a_p)/b), −1, 1), b_xyz = min(δ_max, 0,5·|a_p,xyz|), "
               "b_Greifer = 0,02, ε_Greifer = 0 (ac_smoke.make_bound, PROTOCOL.md §7)",
)
TOLERANCE = 1e-6
ARRAYS = cd.ARRAYS | {"exploration_noise": ((3,), np.float32), "action_bound": ((4,), np.float32)}


# ---------------------------------------------------------------- Ausführung mit Rauschen

def make_executor(torch, parent, project, rng, std):
    """Modell für die Parent-Policy: Parentaktion + ε auf XYZ, begrenzt; Abschluss vom Parent."""
    class Executor(torch.nn.Module):
        def __init__(self):
            super().__init__()
            self.parent, self.log = parent, []

        def forward(self, x, phase):
            with torch.no_grad():
                a_parent, z = self.parent(x, phase)
                noise = rng.normal(0.0, std).astype(np.float32)
                raw = a_parent.clone()
                raw[..., :3] = raw[..., :3] + torch.from_numpy(noise)[None]
                action, b = project(raw, a_parent)
            self.log.append((a_parent[0].numpy().copy(), action[0].numpy().copy(), b[0].numpy().copy(), noise))
            return action, z
    return Executor()


def episode(base, controller, adapter, torch, project, model, threshold, cap, scene, parent, deadline, out,
            std_xyz=NOISE["std_xyz"]):
    rng = np.random.default_rng([NOISE["seed_base"] + parent, scene])
    executor = make_executor(torch, model, project, rng, np.full(3, std_xyz))
    row, arrays = cd.episode(base, controller, adapter, torch, executor, threshold, cap, scene, parent, deadline, out)
    log = executor.log
    if len(log) != row["frames"]:
        raise ValueError("Ausführungsprotokoll passt nicht zur Framezahl")
    a_parent, action, bound, noise = (np.stack([entry[k] for entry in log]) for k in range(4))
    if not np.array_equal(arrays["executed_action"][:, IDX], action.astype(np.float64)):
        raise ValueError("Ausgeführte Aktion weicht vom Ausführungsprotokoll ab")
    arrays["parent_action"][:, IDX] = a_parent.astype(np.float64)
    arrays["exploration_noise"] = noise.astype(np.float32)
    arrays["action_bound"] = bound.astype(np.float32)
    deviation = np.abs(arrays["executed_action"] - arrays["parent_action"])[:, :3]
    row.update(max_deviation_xyz=float(deviation.max(initial=0)), mean_deviation_xyz=float(deviation.mean()),
               bound_violations=violations(arrays))
    return row, arrays


def violations(arrays):
    """Frames, in denen die ausgeführte Aktion die Grenze oder [−1, 1] verlässt."""
    executed, parent = arrays["executed_action"][:, IDX], arrays["parent_action"][:, IDX]
    bound = arrays["action_bound"].astype(np.float64)
    bad = (np.abs(executed - parent) > bound + TOLERANCE) | (np.abs(executed) > 1 + TOLERANCE)
    return int(bad.any(1).sum())


def check_arrays(arrays, row):
    """Datenvertrag N2-1 plus Rauschvertrag (Grenze, Projektion, unveränderte Restspalten)."""
    if set(arrays) != set(ARRAYS):
        raise ValueError("Unerwartete Arrays")
    for key, (shape, dtype) in ARRAYS.items():
        if arrays[key].shape != (row["frames"], *shape) or arrays[key].dtype != dtype:
            raise ValueError(f"Form oder Typ von {key} ungültig")
    base = {k: arrays[k] for k in cd.ARRAYS}
    base["parent_action"] = arrays["executed_action"]  # N2-1-Prüfung ohne die Gleichheitsbedingung
    cd.check_arrays(base, row)
    executed, parent = arrays["executed_action"], arrays["parent_action"]
    noise, bound = arrays["exploration_noise"].astype(np.float64), arrays["action_bound"].astype(np.float64)
    if not (np.isfinite(parent).all() and np.isfinite(noise).all() and np.isfinite(bound).all()):
        raise ValueError("Nicht endliche Parentaktion, Rauschwerte oder Grenzen")
    if not (np.array_equal(executed[:, 3:6], parent[:, 3:6])
            and np.array_equal(executed[:, 6], np.clip(parent[:, 6], -1, 1))):
        raise ValueError("Greifer- oder Rotationsspalten weichen vom Parent ab")
    expected = np.concatenate([np.minimum(NOISE["delta_max"], 0.5 * np.abs(parent[:, :3])),
                               np.full((len(parent), 1), NOISE["gripper_bound"])], 1)
    if np.abs(bound - expected).max(initial=0) > TOLERANCE:
        raise ValueError("Grenze entspricht nicht δ_max = 0,20")
    if violations(arrays):
        raise ValueError("Grenzverletzung der ausgeführten Aktion")
    b = bound[:, :3]
    projected = np.clip(parent[:, :3] + b * np.tanh(noise / np.where(b > 0, b, 1.0)), -1, 1)
    if np.abs(projected - executed[:, :3]).max(initial=0) > TOLERANCE:
        raise ValueError("Ausgeführte Aktion passt nicht zu Parentaktion und Rauschwert")


# ---------------------------------------------------------------- Plan und Provenienz

def noisy_split():
    entry = next(s for s in read(HERE / "splits_v3.json")["splits"] if s["id"] == SPLIT)
    keys = ("first", "last", "task_cubes", "target_families", "selection")
    if tuple(entry[k] for k in keys) != (FIRST, LAST, 3, FAMILIES, "all"):
        raise ValueError("Bereich critic_data_noisy weicht von PROTOCOL_V2.md §E ab")
    for split in read(HERE / "splits_v3.json")["splits"]:
        if split["id"] != SPLIT and not (split["last"] < FIRST or split["first"] > LAST):
            raise ValueError(f"critic_data_noisy überschneidet {split['id']}")
    return FIRST, LAST


def preconditions():
    """Freigabe und Pausenstand unmittelbar vor dem Start prüfen (keine Selbstfreigabe)."""
    plan_text = (HERE / "NACHTPLAN.md").read_text(encoding="utf-8")
    if not re.search(r"^- \[x\] N2-1b/N2-2b:", plan_text, re.M):
        raise ValueError("Freigabe N2-1b fehlt im NACHTPLAN")
    if not re.search(r"^Gesamtpause: nein\s*$", (HERE / "STATUS.md").read_text(encoding="utf-8"), re.M):
        raise ValueError("Gesamtpause aktiv")
    if "**Status: FREIGEGEBEN**" not in (HERE / "PROTOCOL_V2.md").read_text(encoding="utf-8"):
        raise ValueError("PROTOCOL_V2.md nicht freigegeben")
    noisy_split()


def plan(registry, controller):
    first, last = noisy_split()
    config = cd.plan(registry, controller)
    sources = [Path(__file__), HERE / "critic_data.py", HERE / "ac_smoke.py", HERE / "splits_v3.json",
               HERE / "PROTOCOL_V2.md"]
    config["source_sha256"] |= {p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sources}
    config.update(
        task="N2-1b", protocol="protocol_v2", split=SPLIT,
        schedule=[[scene, parent] for scene in range(first, last + 1) for parent in PARENTS],
        exploration=NOISE, arrays={k: [list(s), np.dtype(t).name] for k, (s, t) in ARRAYS.items()},
        action_index=IDX, bound_tolerance=TOLERANCE,
    )
    return config


def load_episode(out, index, schedule, scenes):
    data_path, row_path = cd.paths(out, index)
    row = read(row_path)
    data = data_path.read_bytes()
    if digest(data) != row["arrays_sha256"]:
        raise ValueError(f"Hash der Episode {index} stimmt nicht")
    cd.check_row(row, index, schedule, scenes)
    check_arrays(cd.decode(data), row)
    return row


def summarize(rows, config_path, out, active_wall_seconds):
    summary = cd.summarize(rows, config_path, out, active_wall_seconds)
    for p in PARENTS:
        own = [r for r in rows if r["parent_seed"] == p]
        frames = sum(r["frames"] for r in own)
        summary["by_parent"][str(p)]["exploration"] = dict(
            max_deviation_xyz=max((r["max_deviation_xyz"] for r in own), default=0.0),
            mean_deviation_xyz=sum(r["mean_deviation_xyz"] * r["frames"] for r in own) / frames if frames else None,
            bound_violations=sum(r["bound_violations"] for r in own))
    summary.update(task="N2-1b", split=SPLIT, exploration=NOISE,
                   bound_violations=sum(r["bound_violations"] for r in rows))
    return summary


# ---------------------------------------------------------------- Lauf

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
        state.update(stage=calibration.STAGES[state["state"]], rendered=state["completed_episodes"],
                     render_total=EXPECTED, split=SPLIT)
        write(status_path, state)

    status()
    try:
        registry, base, torch, controller, adapter = cd.setup(OUT)
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
        project = make_bound(torch, NOISE["delta_max"], NOISE["gripper_bound"])
        schedule = config["schedule"]
        scenes, rows = {}, []
        while len(rows) < EXPECTED and cd.paths(OUT, len(rows))[1].exists():
            rows.append(load_episode(OUT, len(rows), schedule, scenes))
        if any(int(p.stem) >= len(rows) for p in (OUT / "episodes").glob("*.json")):
            raise ValueError("Kanonische Episodenfolge unterbrochen")
        status(state="EVALUATING", completed_episodes=len(rows))
        for index in range(len(rows), EXPECTED):
            scene, parent = schedule[index]
            row, arrays = episode(base, controller, adapter, torch, project, *models[parent], scene, parent,
                                  deadline, OUT)
            data = cd.encode(arrays)
            row.update(index=index, scene_seed=scene, parent_seed=parent, arrays_sha256=digest(data))
            cd.check_row(row, index, schedule, scenes)
            check_arrays(arrays, row)
            data_path, row_path = cd.paths(OUT, index)
            cd.write_bytes(data_path, data)
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
    """Technische Prüfung vor dem Lauf, nicht Teil der 900 Episoden:
    (a) σ = 0 über denselben Ausführungspfad reproduziert N2-1-Episode 0000 (Szene 2100000100, Parent 1);
    (b) σ = 0,05 auf derselben Szene erfüllt den Rauschvertrag ohne Grenzverletzung."""
    reference = read(cd.OUT / "episodes" / "0000.json")
    if (reference["scene_seed"], reference["parent_seed"]) != (2100000100, 1):
        raise ValueError("Unerwartete N2-1-Referenz")
    INTEGRATION.mkdir(exist_ok=False)
    registry, base, torch, controller, adapter = cd.setup(INTEGRATION)
    model = registry.restore_abc_a_for_inference(1, registry.frozen_abc_a()[1])
    project = make_bound(torch, NOISE["delta_max"], NOISE["gripper_bound"])
    checks = {}
    for name, std in (("zero_noise", 0.0), ("noisy", NOISE["std_xyz"])):
        row, arrays = episode(base, controller, adapter, torch, project, *model, 2100000100, 1,
                              time.time() + 600, INTEGRATION, std_xyz=std)
        data = cd.encode(arrays)
        check_arrays(arrays, row)
        check_arrays(cd.decode(data), row)
        checks[name] = dict(frames=row["frames"], success=row["success"], termination=row["termination"],
                            max_deviation_xyz=row["max_deviation_xyz"], bound_violations=row["bound_violations"],
                            noise_std_observed=float(arrays["exploration_noise"].std()),
                            arrays_sha256=digest(data), elapsed_seconds=row["elapsed_seconds"])
        if name == "zero_noise":
            keys = ("initial_sha256", "trajectory_sha256", "success", "frames", "max_stable_frames", "termination")
            comparison = {k: dict(n2_1=reference[k], n2_1b=row[k], equal=reference[k] == row[k]) for k in keys}
            checks[name]["comparison"] = comparison
            checks[name]["passed"] = all(v["equal"] for v in comparison.values()) and row["max_deviation_xyz"] == 0
        else:
            checks[name]["passed"] = row["bound_violations"] == 0 and row["max_deviation_xyz"] > 0
    result = dict(purpose="Technische Prüfung vor N2-1b; nicht Teil der 900 Episoden",
                  reference=(cd.OUT / "episodes/0000.json").relative_to(ROOT).as_posix(),
                  checks=checks, passed=all(c["passed"] for c in checks.values()), optimizer_updates=0)
    write(INTEGRATION / "result.json", result)
    print(json.dumps({k: dict(passed=c["passed"], frames=c["frames"], max_deviation_xyz=c["max_deviation_xyz"],
                              bound_violations=c["bound_violations"]) for k, c in checks.items()}
                     | {"passed": result["passed"]}, ensure_ascii=True))
    return 0 if result["passed"] else 1


def supervise(cutoff, deadline, resume):
    if time.time() >= cutoff or deadline < cutoff + 30:
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")
    preconditions()
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
    preconditions()
    arguments = [sys.executable, str(Path(__file__)), command, "--cutoff", cutoff, "--deadline", deadline]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    RESULTS.mkdir(parents=True, exist_ok=True)
    with (RESULTS / "critic_data_noisy_n2_1b_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags | 0x01000000)
        except OSError:  # Job erlaubt kein CREATE_BREAKAWAY_FROM_JOB
            child = subprocess.Popen(arguments, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
    print(json.dumps(identity(child.pid)))
    return 0


# ---------------------------------------------------------------- Monitor

def verify(config, summary):
    scenes, rows = {}, []
    for index in range(EXPECTED):
        rows.append(load_episode(OUT, index, config["schedule"], scenes))
    expected = summarize(rows, OUT / "config.json", OUT, summary["worker_wall_seconds"])
    if json.loads(json.dumps(expected)) != summary or len(scenes) != FAMILIES:
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
        print("OFFEN | Kein Supervisorstatus für N2-1b")
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
    violations_seen = previous.get("bound_violations", 0)
    while completed < EXPECTED and cd.paths(OUT, completed)[1].is_file():
        row = read(cd.paths(OUT, completed)[1])
        successes += row["success"]
        violations_seen += row["bound_violations"]
        completed += 1
    now = time.time()
    progress_time = now if completed > start else previous.get("progress_time", now)
    output = dict(supervisor=supervisor["supervisor"], supervisor_alive=running, supervisor_state=supervisor["state"],
                  worker=worker_state.get("worker"), worker_alive=worker_running,
                  worker_state=worker_state.get("state"), completed=completed, planned=EXPECTED,
                  new_episodes=completed - start, successes=successes, bound_violations=violations_seen,
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
            "completed_episodes", "families", "successes", "failures", "by_parent", "frames", "bound_violations",
            "dataset_sha256", "rows_sha256", "config_sha256", "worker_episodes_per_hour", "optimizer_updates")})
    elif state == "PAUSED" and not worker_running and supervisor.get("worker_exitcode") == 0:
        code = 0
        output.update(status="PAUSED", reason=worker_state.get("reason"))
    elif (state == "FAILED" or errors or not running or violations_seen
          or (state == "RUNNING" and now >= supervisor["deadline_unix"])):
        code = 2
        output.update(status="ERROR", reason=worker_state.get("reason") or supervisor.get("reason"))
    elif now - progress_time > 180:
        code = 1
        output.update(status="WARNING", reason="Seit mindestens 180 s keine neue persistierte Episode")
    else:
        code = 0
        output.update(status="OK")
    write(previous_path, dict(completed=completed, successes=successes, bound_violations=violations_seen,
                              progress_time=progress_time, checked_unix=now, log_id=file_id, log_offset=offset,
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
