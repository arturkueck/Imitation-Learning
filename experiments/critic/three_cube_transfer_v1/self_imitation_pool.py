"""S-1: 1.200 Episoden mit eingefrorenen A-Parents und IL-v2 (PROTOCOL_V3.md §3)."""

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

import calibration
from calibration import HERE, ROOT, alive, digest, identity, load_module, read, time_argument, write
import critic_data as cd
import critic_data_noisy as noisy
import critic_validation as cv
from action_sensitivity_v2 import N2_2B, N2_2B_SUMMARY_SHA


OUT = cd.RESULTS / "self_imitation_pool_s1"
SPLIT = "online_interaction"
FIRST, LAST = 2100003250, 2100003649
FAMILIES = LAST - FIRST + 1
SCHEDULE = [[scene, parent] for scene in range(FIRST, LAST + 1) for parent in cd.PARENTS]
EXPECTED = len(SCHEDULE)
NOISE = noisy.NOISE | {"seed_base": 7800, "rng": "NumPy PCG64: ein Strom je Parent, Seed 7800 + p"}
MAX_CUTOFF = time_argument("2026-11-20T13:30:00+01:00")
MAX_DEADLINE = time_argument("2026-11-20T14:00:00+01:00")
STAGE_2 = cd.CRITIC_COLUMNS.index("stage_2")
PHASE_0 = cd.CRITIC_COLUMNS.index("phase_0")
ARRAYS = noisy.ARRAYS | {"il_v2_value": ((), np.float64)}


def approval():
    if "Gesamtpause: nein" not in (HERE / "STATUS.md").read_text(encoding="utf-8").splitlines():
        raise ValueError("Gesamtpause aktiv oder unklar")
    if "**Status: FREIGEGEBEN**" not in (HERE / "PROTOCOL_V3.md").read_text(encoding="utf-8"):
        raise ValueError("Protokoll v3 nicht freigegeben")


def check_split():
    for manifest in ("splits_v2.json", "splits_v3.json"):
        splits = read(HERE / manifest)["splits"]
        entry = next(split for split in splits if split["id"] == SPLIT)
        keys = ("first", "last", "task_cubes", "target_families", "selection")
        if tuple(entry[key] for key in keys) != (FIRST, LAST, 3, FAMILIES, "all"):
            raise ValueError(f"Poolfamilien weichen in {manifest} vom Protokoll ab")
        for split in splits:
            if split["id"] != SPLIT and split["first"] <= LAST and split["last"] >= FIRST:
                raise ValueError(f"Poolfamilien überschneiden {split['id']}")


def critic_manifest():
    path = N2_2B / "summary.json"
    if digest(path.read_bytes()) != N2_2B_SUMMARY_SHA:
        raise ValueError("N2-2b-Abschluss weicht vom dokumentierten SHA-256 ab")
    summary = read(path)
    if not summary["decision"]["passed"]:
        raise ValueError("N2-2b hat §6 nicht bestanden")
    return summary["pretraining"]


def config_for(registry, controller, critic_metadata):
    config = cd.plan(registry, controller)
    sources = [Path(__file__), HERE / "critic_data_noisy.py", HERE / "critic_validation.py",
               HERE / "ac_smoke.py", HERE / "action_sensitivity_v2.py", HERE / "PROTOCOL_V3.md",
               HERE / "splits_v3.json", cv.BASE_CORE]
    config["source_sha256"].update({path.relative_to(ROOT).as_posix(): digest(path.read_bytes())
                                    for path in sources})
    config.update(
        task="S-1", protocol="protocol_v3", split=SPLIT, schedule=SCHEDULE, exploration=NOISE,
        arrays={key: [list(shape), np.dtype(dtype).name] for key, (shape, dtype) in ARRAYS.items()},
        critic_action_indices=cv.ACTION_INDEX, critic_action="executed_action",
        critic_summary_sha256=N2_2B_SUMMARY_SHA,
        critic_weights_sha256={p: meta["weights_sha256"] for p, meta in critic_metadata.items()},
        phase_boundary="0-basiert, start und last_frame inklusiv; completed bei Wechsel von (stage, phase) im Folgezustand",
        software={name: getattr(sys.modules[name], "__version__", None)
                  for name in ("torch", "numpy", "robosuite", "mujoco")},
    )
    return config


def phase_boundaries(arrays):
    stage, phase = arrays["stage"], arrays["phase"]
    switches = np.flatnonzero((stage[1:] != stage[:-1]) | (phase[1:] != phase[:-1])) + 1
    starts = [0, *switches.tolist()]
    ends = [*switches.tolist(), len(stage)]
    final_state = arrays["next_critic_state"][-1]
    completed_final = bool(np.isfinite(final_state).all() and (
        int(final_state[STAGE_2]) + 1 != stage[-1]
        or final_state[PHASE_0:PHASE_0 + 7].argmax() != phase[-1]))
    return [
        dict(stage=int(stage[start]), phase=int(phase[start]), start_frame=start, last_frame=end - 1,
             completed=end < len(stage) or completed_final)
        for start, end in zip(starts, ends)
    ]


def enrich(torch, critic, arrays):
    arrays["il_v2_value"] = cv.predict(
        torch, critic, arrays["critic_state"], arrays["executed_action"][:, cv.ACTION_INDEX].astype(np.float32))
    return phase_boundaries(arrays)


def check_arrays(arrays, row):
    noisy.check_arrays({key: value for key, value in arrays.items() if key != "il_v2_value"}, row)
    values = arrays["il_v2_value"]
    if values.dtype != np.float64 or values.shape != (row["frames"],) or not np.isfinite(values).all():
        raise ValueError("IL-v2-Werte müssen je Frame endlich und vollständig sein")
    if phase_boundaries(arrays) != row["phase_boundaries"]:
        raise ValueError("Phasengrenzen stimmen nicht mit den Frames überein")


def check_noise_stream(rng, arrays, row):
    expected = rng.normal(0.0, NOISE["std_xyz"], size=(row["frames"], 3)).astype(np.float32)
    if not np.array_equal(expected, arrays["exploration_noise"]) or rng.bit_generator.state != row["rng_after"]:
        raise ValueError(f"Rauschstrom der Episode {row['index']} inkonsistent")


def load_rows():
    rows, scenes = [], {}
    rngs = {p: np.random.default_rng(NOISE["seed_base"] + p) for p in cd.PARENTS}
    for index in range(EXPECTED):
        data_path, row_path = cd.paths(OUT, index)
        if not row_path.is_file():
            break
        row, data = read(row_path), data_path.read_bytes()
        cd.check_row(row, index, SCHEDULE, scenes)
        if digest(data) != row["arrays_sha256"]:
            raise ValueError(f"SHA-256 der Episode {index} stimmt nicht")
        arrays = cd.decode(data)
        check_arrays(arrays, row)
        check_noise_stream(rngs[row["parent_seed"]], arrays, row)
        rows.append(row)
    if len(list((OUT / "episodes").glob("*.json"))) != len(rows):
        raise ValueError("Kanonische Episodenfolge unterbrochen")
    return rows, scenes, rngs


def summarize(rows, seconds, interruptions):
    summary = cd.summarize(rows, OUT / "config.json", OUT, seconds)
    summary.update(task="S-1", split=SPLIT, planned_episodes=EXPECTED,
                   interruptions=interruptions, bound_violations=sum(r["bound_violations"] for r in rows),
                   frames_with_critic_value=summary["frames"])
    return summary


def verify():
    rows, scenes, _ = load_rows()
    summary = read(OUT / "summary.json")
    config = read(OUT / "config.json")
    if config["schedule"] != SCHEDULE or config["task"] != "S-1" or config["optimizer_updates"] != 0:
        raise ValueError("Konfiguration weicht vom S-1-Vertrag ab")
    for path, expected in config["source_sha256"].items():
        if digest((ROOT / path).read_bytes()) != expected:
            raise ValueError(f"Quellhash stimmt nicht: {path}")
    if (len(rows) != EXPECTED or len(scenes) != FAMILIES
            or summarize(rows, summary["worker_wall_seconds"], summary["interruptions"]) != summary):
        raise ValueError("Vollständigkeit oder Abschlussmanifest fehlerhaft")
    return summary


def worker(deadline):
    path = OUT / "status.json"
    previous = read(path) if path.exists() else {}
    started = time.perf_counter()
    previous_seconds = previous.get("active_wall_seconds", 0)
    state = dict(state="INITIALIZING", worker=identity(os.getpid()), render_total=EXPECTED,
                 optimizer_updates=0, split=SPLIT, rendered=previous.get("rendered", 0),
                 interruptions=previous.get("interruptions", 0), active_episode=None)

    def status(**fields):
        state.update(fields, heartbeat_unix=time.time(),
                     active_wall_seconds=previous_seconds + time.perf_counter() - started)
        state["stage"] = calibration.STAGES[state["state"]]
        write(path, state)

    status()
    try:
        approval()
        check_split()
        metadata = critic_manifest()
        registry, base, torch, controller, adapter = cd.setup(OUT)
        torch.use_deterministic_algorithms(True)
        core = load_module("s1_critic_core", cv.BASE_CORE)
        config_path = OUT / "config.json"
        config = config_for(registry, controller, metadata)
        if config_path.exists():
            if read(config_path) != config:
                raise ValueError("Provenienz des bestehenden S-1-Laufs geändert")
        else:
            write(config_path, config)
        models, critics = {}, {}
        for parent in cd.PARENTS:
            base.check_stop(OUT, deadline)
            models[parent] = registry.restore_abc_a_for_inference(parent, config["parents"][str(parent)])
            critic, meta = cv.load_critic(torch, core, N2_2B, parent)
            if meta != metadata[str(parent)]:
                raise ValueError(f"IL-v2-Metadaten für Parent {parent} stimmen nicht")
            critics[parent] = critic

        rows, scenes, rngs = load_rows()
        project = noisy.make_bound(torch, NOISE["delta_max"], NOISE["gripper_bound"])
        status(state="EVALUATING", rendered=len(rows))
        for index in range(len(rows), EXPECTED):
            base.check_stop(OUT, deadline)
            scene, parent = SCHEDULE[index]
            status(active_episode=index)
            model, threshold, cap = models[parent]
            rng = rngs[parent]
            executor = noisy.make_executor(torch, model, project, rng, np.full(3, NOISE["std_xyz"]))
            row, arrays = cd.episode(base, controller, adapter, torch, executor, threshold, cap,
                                     scene, parent, deadline, OUT)
            parent_action, action, bound, noise = (np.stack(column) for column in zip(*executor.log))
            if not np.array_equal(arrays["executed_action"][:, noisy.IDX], action):
                raise ValueError("Ausgeführte Aktion weicht vom Ausführungsprotokoll ab")
            arrays["parent_action"][:, noisy.IDX] = parent_action
            arrays.update(exploration_noise=noise, action_bound=bound)
            deviation = np.abs(arrays["executed_action"][:, :3] - arrays["parent_action"][:, :3])
            row.update(index=index, scene_seed=scene, parent_seed=parent, rng_after=rng.bit_generator.state,
                       phase_boundaries=enrich(torch, critics[parent], arrays),
                       max_deviation_xyz=float(deviation.max()), mean_deviation_xyz=float(deviation.mean()),
                       bound_violations=noisy.violations(arrays))
            cd.check_row(row, index, SCHEDULE, scenes)
            check_arrays(arrays, row)
            data = cd.encode(arrays)
            row["arrays_sha256"] = digest(data)
            data_path, row_path = cd.paths(OUT, index)
            cd.write_bytes(data_path, data)
            write(row_path, row)
            rows.append(row)
            status(rendered=len(rows), active_episode=None)

        write(OUT / "summary.json", summarize(rows, previous_seconds + time.perf_counter() - started,
                                               state["interruptions"]))
        status(state="COMPLETE")
    except (InterruptedError, TimeoutError) as error:
        status(state="PAUSED", reason=str(error),
               interruptions=state["interruptions"] + int(state["active_episode"] is not None))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def check_window(cutoff, deadline, resume):
    later_window = resume and time.time() >= MAX_DEADLINE
    if (time.time() >= cutoff or deadline < cutoff + 120
            or (not later_window and (cutoff > MAX_CUTOFF or deadline > MAX_DEADLINE))):
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")


def supervise(cutoff, deadline, resume):
    check_window(cutoff, deadline, resume)
    approval()
    path = OUT / "supervisor_status.json"
    if resume:
        previous = read(path)
        if (previous["state"] != "PAUSED" or alive(previous["supervisor"])
                or alive(read(OUT / "status.json")["worker"]) or (OUT / "STOP").exists()):
            raise ValueError("Fortsetzung erfordert PAUSED, beendete Prozesse und entfernte STOP-Datei")
    else:
        OUT.mkdir()
        (OUT / "episodes").mkdir()
    claim = OUT / "supervisor.lock"
    with claim.open("x") as lock:
        lock.write(str(os.getpid()))
    state = dict(state="STARTING", supervisor=identity(os.getpid()), cutoff_unix=cutoff, deadline_unix=deadline)
    child = None
    awake = False
    try:
        write(path, state)
        check_window(cutoff, deadline, resume)
        approval()
        awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (OUT / "worker.log").open("ab") as log:
            child = subprocess.Popen([sys.executable, "-u", str(Path(__file__)), "_worker", str(deadline - 120)],
                                     cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            state.update(state="RUNNING", launcher=identity(child.pid), sleep_prevention=awake)
            write(path, state)
            code = child.wait(timeout=max(0.01, deadline - time.time()))
        state.update(state=read(OUT / "status.json")["state"] if code == 0 else "FAILED", worker_exitcode=code)
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
        write(path, state)
        claim.unlink()
    return int(state["state"] == "FAILED")


def start(mode, cutoff, deadline):
    check_window(time_argument(cutoff), time_argument(deadline), mode == "resume")
    approval()
    if mode == "launch" and OUT.exists():
        raise FileExistsError("Laufordner existiert. Zuerst monitor ausführen.")
    args = [sys.executable, str(Path(__file__)), mode, "--cutoff", cutoff, "--deadline", deadline]
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    with (OUT.parent / f"{OUT.name}_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, creationflags=flags | 0x01000000)
        except OSError:
            child = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                     stderr=subprocess.STDOUT, creationflags=flags)
    print(json.dumps({"launcher": identity(child.pid)}))
    return 0


def new_errors(previous):
    path = OUT / "worker.log"
    if not path.exists():
        return None, 0, []
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        log_id = [info.st_dev, info.st_ino]
        offset = previous.get("log_offset", 0) if previous.get("log_id") == log_id else 0
        stream.seek(offset if offset <= info.st_size else 0)
        offset = stream.tell()
        data = stream.read()
    complete = data.rfind(b"\n") + 1
    errors = [line for line in data[:complete].decode(errors="replace").splitlines()
              if re.search(r"Traceback|(?:Error|Exception):|nonfinite|out of memory", line, re.I)]
    return log_id, offset + complete, errors


def monitor():
    supervisor_path = OUT / "supervisor_status.json"
    if not supervisor_path.exists():
        print("OFFEN | Kein Supervisorstatus für S-1")
        return 2 if OUT.exists() else 0
    supervisor = read(supervisor_path)
    worker_path = OUT / "status.json"
    state = read(worker_path) if worker_path.exists() else {}
    running, worker_running = alive(supervisor["supervisor"]), alive(state.get("worker"))
    path = OUT / "monitor_state.json"
    previous = read(path) if path.exists() else {}
    log_id, offset, errors = new_errors(previous)
    completed = start_count = previous.get("completed", 0)
    successes = previous.get("successes", 0)
    while completed < EXPECTED and cd.paths(OUT, completed)[1].is_file():
        successes += read(cd.paths(OUT, completed)[1])["success"]
        completed += 1

    now = time.time()
    new_session = previous.get("supervisor") != supervisor["supervisor"]
    progress = now if completed > start_count or new_session else previous.get("progress_time", now)
    result = dict(status="OK", supervisor=supervisor["supervisor"], supervisor_alive=running,
                  worker=state.get("worker"), worker_alive=worker_running, worker_state=state.get("state"),
                  completed=completed, planned=EXPECTED, new_episodes=completed - start_count,
                  successes=successes, next_episode=completed if completed < EXPECTED else None,
                  cutoff_unix=supervisor["cutoff_unix"], deadline_unix=supervisor["deadline_unix"],
                  optimizer_updates=0, errors=errors)
    manifest_sha = None
    stage = supervisor["state"]
    if stage in ("COMPLETE", "PAUSED") and not worker_running and supervisor.get("worker_exitcode") == 0:
        result.update(status=stage, reason=state.get("reason"), interruptions=state["interruptions"])
        if stage == "COMPLETE":
            manifest_sha = digest((OUT / "summary.json").read_bytes())
            result["summary"] = read(OUT / "summary.json") if manifest_sha == previous.get("manifest_sha") else verify()
            result["manifest_sha256"] = manifest_sha
    elif (stage == "FAILED" or state.get("state") == "FAILED" or errors or not running
          or now >= supervisor["deadline_unix"]):
        result.update(status="ERROR", reason=state.get("reason") or supervisor.get("reason"))
    elif now - progress > 180:
        result.update(status="WARNING", reason="Seit 180 s keine neue persistierte Episode")

    write(path, dict(completed=completed, successes=successes, progress_time=progress, checked_unix=now,
                     supervisor=supervisor["supervisor"], log_id=log_id, log_offset=offset, manifest_sha=manifest_sha))
    print(json.dumps(result, ensure_ascii=True))
    return {"ERROR": 2, "WARNING": 1}.get(result["status"], 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    detached = commands.add_parser("start")
    detached.add_argument("mode", choices=("launch", "resume"))
    for command in (detached, commands.add_parser("launch"), commands.add_parser("resume")):
        command.add_argument("--cutoff", required=True)
        command.add_argument("--deadline", required=True)
    commands.add_parser("_worker").add_argument("deadline", type=float)
    commands.add_parser("monitor")
    commands.add_parser("verify")
    args = parser.parse_args()
    if args.command == "start":
        return start(args.mode, args.cutoff, args.deadline)
    if args.command == "_worker":
        if not (OUT / "supervisor.lock").exists():
            parser.error("Worker nur über den Supervisor starten")
        worker(args.deadline)
        return 0
    if args.command == "monitor":
        return monitor()
    if args.command == "verify":
        print(json.dumps(verify(), ensure_ascii=True))
        return 0
    return supervise(time_argument(args.cutoff), time_argument(args.deadline), args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
