"""Inkrementeller Monitor für N1-4."""

import hashlib
import json
import re
import sys
import time

from calibration import EXPECTED, OUT, alive, check_row, episode_path, read, write


def verify_summary(plan, summary):
    scenes, counts = {}, {str(seed): {"successes": 0, "episodes": 0} for seed in (1, 2, 3)}
    raw = hashlib.sha256()
    elapsed = 0
    for index in range(EXPECTED):
        data = episode_path(index).read_bytes()
        raw.update(data)
        row = json.loads(data)
        check_row(row, index, plan["schedule"], scenes)
        counts[str(row["parent_seed"])]["episodes"] += 1
        counts[str(row["parent_seed"])]["successes"] += row["success"]
        elapsed += row["elapsed_seconds"]
    if (len(scenes) != 100 or counts != summary["by_parent"] or
            sum(p["successes"] for p in counts.values()) != summary["successes"] or
            summary["planned_episodes"] != EXPECTED or summary["completed_episodes"] != EXPECTED or
            summary["families"] != len(scenes) or summary["optimizer_updates"] != 0 or
            summary["episode_wall_seconds"] != elapsed or
            summary["episodes_per_hour"] != 3600 * EXPECTED / elapsed or
            summary["worker_wall_seconds"] < elapsed or
            summary["worker_episodes_per_hour"] != 3600 * EXPECTED / summary["worker_wall_seconds"] or
            summary["raw_sha256"] != raw.hexdigest() or
            summary["config_sha256"] != hashlib.sha256((OUT / "config.json").read_bytes()).hexdigest()):
        raise ValueError("Ergebniszusammenfassung stimmt nicht mit den 300 Rohzeilen überein")


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
        print("OFFEN | Kein Supervisorstatus für N1-4")
        return 0 if not OUT.exists() else 2
    supervisor = read(supervisor_path)
    running = alive(supervisor["supervisor"])
    worker = read(worker_path) if worker_path.is_file() else {}
    worker_running = alive(worker.get("worker"))
    previous_path = OUT / "monitor_state.json"
    previous = read(previous_path) if previous_path.is_file() else {}
    file_id, offset, errors = new_errors(previous)
    completed = previous.get("completed", 0)
    successes = previous.get("successes", 0)
    start = completed
    while completed < EXPECTED and episode_path(completed).is_file():
        row = read(episode_path(completed))
        successes += row["success"]
        completed += 1
    now = time.time()
    progress_time = now if completed > start else previous.get("progress_time", now)
    output = dict(supervisor=supervisor["supervisor"], supervisor_alive=running, supervisor_state=supervisor["state"],
                  worker=worker.get("worker"), worker_alive=worker_running, worker_state=worker.get("state"),
                  completed=completed, planned=EXPECTED, new_episodes=completed - start,
                  successes=successes, next_episode=None if completed == EXPECTED else completed,
                  deadline_unix=supervisor["deadline_unix"], errors=errors)
    state = supervisor["state"]
    result_verified = previous.get("result_verified", False)
    if (state == "COMPLETE" and worker.get("state") == "COMPLETE" and not worker_running
            and supervisor.get("worker_exitcode") == 0 and completed == EXPECTED):
        plan, summary = read(OUT / "config.json"), read(OUT / "summary.json")
        if not result_verified:
            verify_summary(plan, summary)
        result_verified = True
        code = 0
        output.update(status="COMPLETE", summary=summary)
    elif state == "PAUSED" and not worker_running and supervisor.get("worker_exitcode") == 0:
        code = 0
        output.update(status="PAUSED", reason=worker.get("reason"))
    elif state == "FAILED" or errors or not running or (state == "RUNNING" and now >= supervisor["deadline_unix"]):
        code = 2
        output.update(status="ERROR", reason=worker.get("reason") or supervisor.get("reason"))
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


if __name__ == "__main__":
    sys.exit(monitor())
