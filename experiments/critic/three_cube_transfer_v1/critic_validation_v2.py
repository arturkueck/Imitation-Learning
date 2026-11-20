"""N2-2b: IL-v2 vortrainieren, gespeicherte A-Rollouts nach §6 auswerten."""

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

from calibration import HERE, ROOT, alive, digest, identity, load_module, read, time_argument, write
import critic_data as cd
import critic_data_noisy as noisy
import critic_validation as cv

OUT = cv.RESULTS / "critic_validation_n2_2b"
TRAINING = (("N2-1", cd.OUT, cd.critic_split, cd.check_arrays),
            ("N2-1b", noisy.OUT, noisy.noisy_split, noisy.check_arrays))
VALIDATION_HASH = "fac1e51d12f47d399b685abd1d1bffa963c5e326ac0b2cfecd5a1c412d9ce570"
VALIDATION_ROWS_HASH = "3e161954b9b9f7644d5e62b09388dbdd5c32897144b3f1d075965253be3672eb"
MAX_CUTOFF = time_argument("2026-11-20T07:30:00+01:00")
MAX_DEADLINE = time_argument("2026-11-20T09:00:00+01:00")
STAGES = dict(INITIALIZING="initializing", LOADING="initializing", TRAINING="training",
              ASSESSING="validation", COMPLETE="complete", PAUSED="paused", FAILED="error")


def approval():
    noisy.preconditions()
    status = (HERE / "STATUS.md").read_text(encoding="utf-8")
    for task in ("N2-1", "N2-1b", "N2-2"):
        if not re.search(rf"^\| {task} \| erledigt \|", status, re.M):
            raise ValueError(f"{task} muss abgeschlossen sein")


def input_spec(directory, schedule, expected_hash, rows_hash=None):
    config_path = directory / "config.json"
    summary = read(directory / "summary.json")
    config_sha = digest(config_path.read_bytes())
    if (read(directory / "supervisor_status.json")["state"] != "COMPLETE"
            or read(config_path)["schedule"] != schedule
            or summary["completed_episodes"] != len(schedule)
            or summary["config_sha256"] != config_sha
            or summary["dataset_sha256"] != expected_hash
            or (rows_hash is not None and summary["rows_sha256"] != rows_hash)):
        raise ValueError(f"Abschlussmanifest unplausibel: {directory.name}")
    rows_raw = [cd.paths(directory, index)[1].read_bytes() for index in range(len(schedule))]
    rows = [json.loads(raw) for raw in rows_raw]
    if (digest("\n".join(row["arrays_sha256"] for row in rows).encode()) != expected_hash
            or digest(b"".join(rows_raw)) != summary["rows_sha256"]):
        raise ValueError(f"Episodenmanifest stimmt nicht: {directory.name}")
    return dict(directory=directory.relative_to(ROOT).as_posix(), schedule=schedule, dataset_sha256=expected_hash,
                config_sha256=config_sha, rows_sha256=summary["rows_sha256"]), rows


def inputs():
    manifests, rows = {}, {}
    hashes = (cv.DATASET_SHA256, read(HERE / "CRITIC_DATA_NOISY_MANIFEST.json")["dataset_sha256"])
    for (task, directory, split, _), data_hash in zip(TRAINING, hashes):
        first, last = split()
        schedule = [[scene, p] for scene in range(first, last + 1) for p in cv.PARENTS]
        manifests[task], rows[task] = input_spec(directory, schedule, data_hash)
    families = cv.panels()
    schedule = [[scene, p, panel] for panel in cv.PANELS for scene in families[panel] for p in cv.PARENTS]
    manifests["N2-2"], rows["N2-2"] = input_spec(cv.OUT, schedule, VALIDATION_HASH, VALIDATION_ROWS_HASH)
    sources = [Path(__file__).resolve(), cv.BASE_CORE, *(HERE / name for name in (
        "calibration.py", "critic_data.py", "critic_data_noisy.py", "critic_validation.py",
        "PROTOCOL.md", "PROTOCOL_V2.md", "splits.json", "splits_v2.json", "splits_v3.json",
        "CRITIC_DATA_NOISY_MANIFEST.json", "difficulty_panels_v1.json", "difficulty_v1.json", "difficulty_v1.sha256",
    ))]
    config = dict(task="N2-2b", protocol="protocol_v2", inputs=manifests, pretraining=cv.PRETRAIN,
                  criteria=cv.CRITERIA, action_index=cv.ACTION_INDEX, rollout_optimizer_updates=0,
                  source_sha256={p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in sources})
    return config, rows


def episode_arrays(directory, index, row, contract):
    raw = cd.paths(directory, index)[0].read_bytes()
    if digest(raw) != row["arrays_sha256"]:
        raise ValueError(f"Episodenhash stimmt nicht: {directory.name}/{index}")
    arrays = cd.decode(raw)
    contract(arrays, row)
    return arrays


def training_data(config, rows, parent, check_stop):
    states, actions, returns, baseline = [], [], [], []
    for task, directory, _, contract in TRAINING:
        schedule = config["inputs"][task]["schedule"]
        scenes = {}
        for index, (_, owner) in enumerate(schedule):
            if owner != parent:
                continue
            check_stop()
            row = rows[task][index]
            cd.check_row(row, index, schedule, scenes)
            arrays = episode_arrays(directory, index, row, contract)
            states.append(arrays["critic_state"])
            actions.append(arrays["executed_action"][:, cv.ACTION_INDEX])
            returns.append(arrays["discounted_return"])
            baseline.append(({k: arrays[k] for k in ("stage", "phase", "discounted_return")}, bool(row["success"])))
    return tuple(np.concatenate(parts) for parts in (states, actions, returns)), cv.baseline_table(baseline)


def save_checkpoint(torch, path, payload):
    temporary = path.with_suffix(".tmp")
    with temporary.open("wb") as stream:
        torch.save(payload, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def train(torch, core, data, parent, checkpoint, config_sha, check_stop, progress, recipe=cv.PRETRAIN):
    states, actions, targets = data
    torch.manual_seed(7100 + parent)
    critic = core.TwinQ(states.astype(np.float64).mean(0), states.astype(np.float64).std(0), recipe["critic_width"])
    optimizer = torch.optim.AdamW(critic.parameters(), lr=recipe["critic_lr"], weight_decay=recipe["weight_decay"])
    sampler = np.random.default_rng(7200 + parent)
    history, window, update = [], [], 0
    if checkpoint.exists():
        saved = torch.load(checkpoint, map_location="cpu", weights_only=True)
        if saved["config_sha256"] != config_sha or saved["parent"] != parent:
            raise ValueError("Fortsetzungspunkt gehört zu einer anderen Konfiguration")
        critic.load_state_dict(saved["critic"])
        optimizer.load_state_dict(saved["optimizer"])
        torch.set_rng_state(saved["torch_rng"])
        sampler.bit_generator.state = saved["sampler"]
        history, window, update = saved["history"], saved["window"], saved["updates"]

    def persist():
        save_checkpoint(torch, checkpoint, dict(
            config_sha256=config_sha, parent=parent, critic=critic.state_dict(), optimizer=optimizer.state_dict(),
            torch_rng=torch.get_rng_state(), sampler=sampler.bit_generator.state, history=history, window=window,
            updates=update,
        ))

    s, a, y = (torch.from_numpy(np.ascontiguousarray(v, dtype=np.float32)) for v in data)
    try:
        while update < recipe["updates"]:
            if update % 100 == 0:
                check_stop()
            ids = torch.from_numpy(sampler.integers(len(states), size=recipe["batch_size"]))
            q1, q2 = critic(s[ids], a[ids])
            loss = (q1 - y[ids]).square().mean() + (q2 - y[ids]).square().mean()
            if not torch.isfinite(loss):
                raise FloatingPointError(f"Critic-Loss bei Update {update + 1} nicht endlich")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            norm = torch.nn.utils.clip_grad_norm_(critic.parameters(), recipe["gradient_clip"])
            if not torch.isfinite(norm):
                raise FloatingPointError(f"Gradient bei Update {update + 1} nicht endlich")
            optimizer.step()
            update += 1
            window.append(float(loss.detach()))
            if update % recipe["log_every"] == 0:
                history.append(dict(update=update, mean_loss=float(np.mean(window))))
                window.clear()
                persist()
                progress(update, history[-1]["mean_loss"])
    except InterruptedError as error:
        persist()
        error.add_note(f"Parent {parent}, dauerhafter Stand nach {update} Updates")
        raise
    persist()
    return critic, optimizer, history


def assess_parent(torch, critic, baseline, config, rows, parent, check_stop):
    table, overall = baseline
    entry = dict(baseline_points=table, baseline_overall_success_rate=overall)
    schedule = config["inputs"]["N2-2"]["schedule"]
    scenes = {}
    for panel in cv.PANELS:
        records, finite, frames, fallback, episodes, successes = [], True, 0, 0, 0, 0
        for index, (_, owner, split) in enumerate(schedule):
            if (owner, split) != (parent, panel):
                continue
            check_stop()
            row = rows["N2-2"][index]
            cv.check_row(row, index, schedule, scenes)
            arrays = episode_arrays(cv.OUT, index, row, cd.check_arrays)
            values = cv.predict(torch, critic, *cv.critic_inputs(arrays))
            finite &= bool(np.isfinite(values).all())
            frames += len(values)
            episodes += 1
            successes += row["success"]
            for point, frame in cv.phase_points(arrays["stage"], arrays["phase"]).items():
                reference = table.get(point, {})
                fallback += point not in table
                records.append(dict(family=row["scene_seed"], point=point, value=float(values[frame]),
                                    discounted_return=float(arrays["discounted_return"][frame]),
                                    success=bool(row["success"]),
                                    baseline_return=reference.get("mean_return", overall),
                                    baseline_success_rate=reference.get("success_rate", overall)))
        check_stop()
        metrics = cv.assess(records)
        if not metrics["finite"]:
            for point in metrics["points"]:
                if not np.isfinite(point["mean_value"]):
                    point["mean_value"] = None
        metrics["checks"] = dict(metrics.get("checks", {}), finite=bool(finite and metrics["finite"]))
        metrics.update(passed=bool(metrics.get("passed", False) and finite), episodes=episodes, successes=successes,
                       frames_predicted=frames, all_frames_finite=finite, baseline_fallback_records=fallback)
        entry[panel] = metrics
    entry["passed"] = entry["validation_normal"]["passed"]
    return entry


def torch_core():
    import torch
    torch.set_num_threads(cv.PRETRAIN["torch_threads"])
    torch.use_deterministic_algorithms(True)
    return torch, load_module("critic_base_core", cv.BASE_CORE)


def frozen_inputs(create=False):
    config, rows = inputs()
    path = OUT / "config.json"
    if create and not path.exists():
        write(path, config)
    if read(path) != config:
        raise ValueError("Eingaben oder Quellen weichen vom eingefrorenen Lauf ab")
    return config, rows, digest(path.read_bytes())


def summary(config, config_sha, assessments, critics):
    decisions = {p: result["passed"] for p, result in assessments.items()}
    return dict(task="N2-2b", config_sha256=config_sha, assessment=assessments, pretraining=critics,
                decision=dict(per_parent=decisions, passed=all(decisions.values())),
                critic_updates_total=sum(meta["updates"] for meta in critics.values()),
                saved_validation_episodes=cv.EXPECTED, new_rollouts=0, rollout_optimizer_updates=0,
                input_dataset_sha256={k: v["dataset_sha256"] for k, v in config["inputs"].items()})


def worker(cutoff, deadline):
    process = identity(os.getpid())
    status_path = OUT / "status.json"
    state = dict(worker=process, training_update=0, current_step=0, total_steps=60000)

    def status(**fields):
        state.update(fields, updated_unix=time.time())
        state.update(stage=STAGES[state["state"]], step=state["current_step"], heartbeat_unix=state["updated_unix"])
        write(status_path, state)

    def check_stop():
        if (OUT / "STOP").exists() or time.time() >= deadline:
            raise InterruptedError("STOP angefordert oder weiche Deadline erreicht")

    try:
        status(state="INITIALIZING")
        approval()
        if time.time() >= cutoff:
            raise InterruptedError("Startfenster geschlossen")
        config, rows, config_sha = frozen_inputs(create=True)
        torch, core = torch_core()
        trained = 0
        starting_updates = True
        for parent in cv.PARENTS:
            check_stop()
            checkpoint = OUT / "critics" / f"parent_{parent}.resume.pt"
            weights, metadata = cv.critic_paths(OUT, parent)
            status(state="LOADING", training_parent=parent, training_update=0, current_step=trained)
            data, baseline = training_data(config, rows, parent, check_stop)
            if metadata.exists():
                critic, meta = cv.load_critic(torch, core, OUT, parent)
                if meta["config_sha256"] != config_sha or meta["updates"] != cv.PRETRAIN["updates"]:
                    raise ValueError(f"Unpassender Abschlusscheckpoint für Parent {parent}")
            else:
                if starting_updates:
                    approval()
                    if time.time() >= cutoff:
                        raise InterruptedError("Startfenster vor dem ersten Update geschlossen")
                    starting_updates = False

                def progress(update, loss):
                    status(state="TRAINING", training_update=update, current_step=trained + update, loss=loss)
                    print(f"Parent {parent} Update {update} Loss {loss:.8g}", flush=True)

                started = time.perf_counter()
                critic, optimizer, history = train(torch, core, data, parent, checkpoint, config_sha, check_stop, progress)
                elapsed = time.perf_counter() - started
                save_checkpoint(torch, weights, dict(critic=critic.state_dict(), critic_optimizer=optimizer.state_dict(),
                                                     updates=cv.PRETRAIN["updates"], parent=parent))
                meta = dict(parent=parent, updates=cv.PRETRAIN["updates"], train_episodes=600, train_frames=len(data[0]),
                            config_sha256=config_sha, weights_sha256=digest(weights.read_bytes()),
                            loss_history=history, finishing_segment_seconds=elapsed)
                write(metadata, meta)
            trained += meta["updates"]
            assessment_path = OUT / "critics" / f"parent_{parent}.assessment.json"
            if not assessment_path.exists():
                status(state="ASSESSING", training_update=meta["updates"], current_step=trained)
                assessment = assess_parent(torch, critic, baseline, config, rows, parent, check_stop)
                write(assessment_path, dict(config_sha256=config_sha, weights_sha256=meta["weights_sha256"],
                                            assessment=assessment))
        write(OUT / "summary.json", checked_summary(config, config_sha))
        status(state="COMPLETE")
    except InterruptedError as error:
        status(state="PAUSED", reason=str(error), continuation=getattr(error, "__notes__", []))
    except Exception as error:
        status(state="FAILED", reason=repr(error))
        raise


def checked_summary(config, config_sha):
    assessments, critics = {}, {}
    for parent in cv.PARENTS:
        weights, metadata = cv.critic_paths(OUT, parent)
        meta = read(metadata)
        assessment = read(OUT / "critics" / f"parent_{parent}.assessment.json")
        if (meta["config_sha256"] != config_sha or assessment["config_sha256"] != config_sha
                or meta["weights_sha256"] != assessment["weights_sha256"]
                or digest(weights.read_bytes()) != meta["weights_sha256"]
                or meta["updates"] != cv.PRETRAIN["updates"]):
            raise ValueError(f"Abschlussartefakte stimmen nicht überein: Parent {parent}")
        assessments[str(parent)] = assessment["assessment"]
        critics[str(parent)] = meta
    return summary(config, config_sha, assessments, critics)


def verify():
    config, rows, config_sha = frozen_inputs()
    finished = checked_summary(config, config_sha)
    if finished != read(OUT / "summary.json"):
        raise ValueError("Summary weicht von den Abschlussartefakten ab")
    torch, core = torch_core()
    for parent in cv.PARENTS:
        _, baseline = training_data(config, rows, parent, lambda: None)
        critic, _ = cv.load_critic(torch, core, OUT, parent)
        actual = assess_parent(torch, critic, baseline, config, rows, parent, lambda: None)
        if actual != finished["assessment"][str(parent)]:
            raise ValueError(f"Neuberechnung weicht ab: Parent {parent}")
    return finished


def window(cutoff, deadline, resume=False):
    # Eine spätere Nacht braucht ein explizites neues Fenster für die Fortsetzung.
    later_night = resume and time.time() >= MAX_DEADLINE
    if (time.time() >= cutoff or not cutoff + 60 < deadline
            or (not later_night and (cutoff > MAX_CUTOFF or deadline > MAX_DEADLINE))):
        raise ValueError("Startfenster geschlossen oder Deadline ungültig")


def supervise(cutoff, deadline, resume):
    window(cutoff, deadline, resume)
    approval()
    if resume:
        previous = read(OUT / "supervisor_status.json")
        if (previous["state"] != "PAUSED" or alive(previous["supervisor"])
                or alive(read(OUT / "status.json")["worker"]) or (OUT / "STOP").exists()):
            raise ValueError("Fortsetzung erfordert PAUSED, beendete Prozesse und entfernte STOP-Datei")
    else:
        OUT.mkdir()
        (OUT / "critics").mkdir()
    claim = OUT / "supervisor.lock"
    with claim.open("x") as lock:
        lock.write(str(os.getpid()))
    path = OUT / "supervisor_status.json"
    state = dict(state="STARTING", supervisor=identity(os.getpid()), cutoff_unix=cutoff, deadline_unix=deadline)
    child = None
    awake = False
    try:
        write(path, state)
        window(cutoff, deadline, resume)
        approval()
        if os.name == "nt":
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (OUT / "worker.log").open("ab") as log:
            child = subprocess.Popen([sys.executable, "-u", str(Path(__file__)), "_worker",
                                      str(cutoff), str(deadline - 60)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
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
    window(time_argument(cutoff), time_argument(deadline), mode == "resume")
    approval()
    if mode == "launch" and OUT.exists():
        raise FileExistsError("Laufordner existiert bereits. Zuerst monitor ausführen.")
    args = [sys.executable, str(Path(__file__)), mode, cutoff, deadline]
    flags = 0x00000008 | 0x00000200  # Detached Windows supervisor in its own process group.
    with (OUT.parent / f"{OUT.name}_supervisor.log").open("ab") as log:
        try:
            child = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags | 0x01000000)
        except OSError:
            child = subprocess.Popen(args, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                     stdin=subprocess.DEVNULL, creationflags=flags)
    print(json.dumps(dict(launcher=identity(child.pid))))


def monitor():
    supervisor_path = OUT / "supervisor_status.json"
    if not supervisor_path.exists():
        print("WARNING | Laufordner ohne Supervisorstatus" if OUT.exists() else "OFFEN | Kein N2-2b-Laufordner")
        return int(OUT.exists())
    supervisor = read(supervisor_path)
    supervisor_alive = alive(supervisor["supervisor"])
    worker_path = OUT / "status.json"
    worker_state = read(worker_path) if worker_path.exists() else {}
    worker_alive = alive(worker_state.get("worker"))
    previous_path = OUT / "monitor_state.json"
    previous = read(previous_path) if previous_path.exists() else {}
    log_path = OUT / "worker.log"
    file_id, offset, errors = None, 0, []
    if log_path.exists():
        with log_path.open("rb") as stream:
            stat = os.fstat(stream.fileno())
            file_id = [stat.st_dev, stat.st_ino]
            if previous.get("log_id") == file_id and previous["log_offset"] <= stat.st_size:
                stream.seek(previous["log_offset"])
            start_offset = stream.tell()
            data = stream.read()
            complete = data.rfind(b"\n") + 1
            offset = start_offset + complete
            errors = [line for line in data[:complete].decode(errors="replace").splitlines()
                      if re.search(r"Traceback|(?:Error|Exception):|nicht endlich|out of memory", line, re.I)]
    now = time.time()
    marker = [worker_state.get(key) for key in ("worker", "state", "training_parent", "current_step")]
    progress = now if marker != previous.get("marker") else previous["progress_unix"]
    verified = previous.get("verified_summary_sha256")
    result = dict(supervisor=supervisor["supervisor"], supervisor_alive=supervisor_alive,
                  worker_alive=worker_alive, worker_exitcode=supervisor.get("worker_exitcode"),
                  deadline_unix=supervisor["deadline_unix"], errors=errors, **worker_state)
    if (supervisor["state"] == "COMPLETE" and worker_state.get("state") == "COMPLETE"
            and supervisor.get("worker_exitcode") == 0 and not worker_alive and not supervisor_alive):
        summary_path = OUT / "summary.json"
        summary_sha = digest(summary_path.read_bytes())
        finished = verify() if verified != summary_sha else read(summary_path)
        verified = summary_sha
        result.update(status="COMPLETE", decision=finished["decision"], critic_updates_total=finished["critic_updates_total"])
    elif supervisor["state"] == "PAUSED" and not worker_alive and not supervisor_alive:
        result.update(status="PAUSED")
    elif (supervisor["state"] == "FAILED" or errors or not supervisor_alive or now >= supervisor["deadline_unix"]):
        result.update(status="ERROR", reason=worker_state.get("reason") or supervisor.get("reason"))
    elif now - progress > 240:
        result.update(status="WARNING", reason="Seit mindestens 240 s kein neuer Fortschritt")
    else:
        result.update(status="OK")
    write(previous_path, dict(log_id=file_id, log_offset=offset, marker=marker, progress_unix=progress,
                              checked_unix=now, verified_summary_sha256=verified, last_result=result))
    print(json.dumps(result))
    return {"ERROR": 2, "WARNING": 1}.get(result["status"], 0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("check", "start", "launch", "resume", "monitor", "_worker"))
    parser.add_argument("arguments", nargs="*")
    args = parser.parse_args()
    if args.command == "check":
        approval()
        config, _ = inputs()
        print(json.dumps({task: len(spec["schedule"]) for task, spec in config["inputs"].items()}))
        return 0
    if args.command == "monitor":
        return monitor()
    if args.command == "start":
        mode, cutoff, deadline = args.arguments
        if mode not in ("launch", "resume"):
            parser.error("start erwartet launch oder resume")
        start(mode, cutoff, deadline)
        return 0
    cutoff, deadline = args.arguments
    if args.command == "_worker":
        if not (OUT / "supervisor.lock").exists():
            parser.error("Worker nur über Supervisor starten")
        worker(float(cutoff), float(deadline))
        return 0
    return supervise(time_argument(cutoff), time_argument(deadline), args.command == "resume")


if __name__ == "__main__":
    raise SystemExit(main())
