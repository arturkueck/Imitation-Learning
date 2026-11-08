"""Prepare, explicitly launch, or inspect the 5+3+3 hour IL feasibility study."""
import argparse
from collections import Counter
import ctypes
from datetime import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
CONFIG = HERE / "protocol.json"
LEGACY = HERE.parent / "critic_warmstart_20261104"
DEFAULT = HERE / "night_001"
SMOKE = HERE / "smoke_001"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding="utf-8")
    for attempt in range(5):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 4:
                raise
            time.sleep(.1)


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def inventory():
    import paired_sim as sim
    old = read(LEGACY / "critic_audit_001/protocol.json")["input_hashes"]
    files = {CONFIG, HERE / "night.py", HERE / "paired_sim.py",
             HERE.parent / "additional_tasks/stack_two/task_info.json"}
    for module in list(sys.modules.values()):
        location = getattr(module, "__file__", None)
        if location:
            path = Path(location).resolve()
            if path.suffix == ".py" and (path.is_relative_to(HERE.parent) or
                    "task_extensions" in path.parts or "robosuite" in path.parts):
                files.add(path)
    for seed in (1, 2, 3):
        for path in (Path(sim.run.parent(seed)["path"]), LEGACY / f"night_001/warm/seed{seed}/warm.pth"):
            if sha(path) != old[str(path)]:
                raise ValueError(f"Checkpoint weicht vom geprüften Bestand ab: {path}")
            files.add(path)
    return {str(path): sha(path) for path in sorted(files)}


def verify(out):
    seal = read(out / "ready.json")
    if str(Path(sys.executable).resolve()) != seal["python"]:
        raise ValueError("Bitte den vorbereiteten Projektinterpreter verwenden")
    for path, expected in seal["hashes"].items():
        if sha(path) != expected:
            raise ValueError(f"Vorbereiteter Eingang hat sich geändert: {path}")
    return seal


def database(out):
    db = sqlite3.connect(out / "pairs.sqlite3", timeout=10)
    db.executescript("""
        CREATE TABLE IF NOT EXISTS families(scene INTEGER PRIMARY KEY, initial TEXT NOT NULL UNIQUE);
        CREATE TABLE IF NOT EXISTS pairs(
            phase TEXT, direction TEXT, scene INTEGER, data TEXT NOT NULL,
            PRIMARY KEY (phase, direction, scene));
    """)
    return db


def wilson(k, n):
    if not n:
        return [0., 1.]
    p, z = k/n, 1.96
    den = 1 + z*z/n
    center = (p+z*z/(2*n))/den
    half = z * math.sqrt(p*(1-p)/n + z*z/(4*n*n))/den
    return [max(0., center-half), min(1., center+half)]


def tally(counts, row):
    counts["families"] += 1
    for key in ("reached", "different", "win", "loss", "timing_only", "qc"):
        counts[key] += int(row[key])
    counts["flips"] += int(row["win"] or row["loss"])
    counts["q_correct"] += int(row["q_correct"] is True)
    counts["q_tied_on_flip"] += int(row["q_correct"] is not None and abs(row["q_delta"]) <= 1e-6)
    prefer_source = row["reached"] and row["q_delta"] > 1e-6
    counts["q_wins_vs_reference"] += int(prefer_source and row["win"])
    counts["q_losses_vs_reference"] += int(prefer_source and row["loss"])
    for key in ("segment_only_win", "segment_only_loss"):
        counts[key] += int(row.get(key, False))


def stats(out, phase, names, first=None):
    result = {}
    with sqlite3.connect(out / "pairs.sqlite3") as db:
        for name in names:
            counter = Counter(families=0, reached=0, different=0, flips=0, win=0, loss=0,
                              q_correct=0, q_tied_on_flip=0, timing_only=0, qc=0)
            by_reference = {}
            for (data,) in db.execute(
                    "SELECT data FROM pairs WHERE phase=? AND direction=? ORDER BY scene LIMIT ?",
                    (phase, name, first or -1)):
                row = json.loads(data)
                tally(counter, row)
                tally(by_reference.setdefault(row["reference"], Counter()), row)
            result[name] = dict(counter, interval=wilson(counter["flips"], counter["families"]),
                                by_reference=by_reference)
    return result


def choose(results, config):
    selected = []
    for group in ("Einzelaktion", "Bewegungsabschnitt"):
        names = [name for name, spec in config["directions"].items() if spec["group"] == group]
        if any(results[name]["families"] == 0 for name in names):
            raise RuntimeError(f"Keine verwertbare Breitenprüfung für alle Richtungen in {group}")
        selected.append(max(names, key=lambda name: (results[name]["interval"][0],
                                                      results[name]["reached"]/results[name]["families"])))
    return selected


def report(out, phase, names, config):
    folder = out / phase
    folder.mkdir(exist_ok=True)
    results = stats(out, phase, names)
    core = stats(out, phase, names, config["pilot_families"])
    write(folder / "summary.json", results)
    write(folder / "first60.json", core)
    for name, s in results.items():
        lo, hi = s["interval"]
        content = [f"# {name} · {phase}", "", config["directions"][name]["question"], "",
                   f"Abgeschlossene Startfamilien: {s['families']}. Prüfstelle erreicht: {s['reached']}. "
                   f"Unterschiedliche Bewegungen: {s['different']}.",
                   f"Nur Quelle erfolgreich: {s['win']}. Nur Referenz erfolgreich: {s['loss']}. "
                   f"Nur Zeitunterschied bei beidseitigem Erfolg: {s['timing_only']}.",
                   f"Erfolgswechsel: {s['flips']}/{s['families']}. Deskriptives 95-%-Wilson-Intervall: "
                   f"{lo:.1%}–{hi:.1%}. Q1-Richtung korrekt bei {s['q_correct']}/{s['flips']} Wechseln "
                   f"(Q-Gleichstände unter allen Wechseln: {s['q_tied_on_flip']}).",
                   f"Erster geplanter 60er-Block: {core[name]['flips']}/{core[name]['families']}. "
                   f"Identische Kontrollwiederholungen: {s['qc']}.", "",
                   "Die Auswahl nutzt nur die Breite. Die Vertiefung hat eigene Familien. "
                   "Gezählt wird pro Startfamilie, einschließlich nicht erreichter Prüfstellen."]
        if phase != "breadth":
            content.append(f"Die vorab festgelegte Q1-Auswahl ergäbe gegenüber durchgängiger Referenz "
                           f"{s['q_wins_vs_reference']} gewonnene und {s['q_losses_vs_reference']} verlorene "
                           "Erfolge auf diesen gepaarten Verzweigungen. Gleichstände wählen die Referenz. "
                           "Eine perfekte Auswahl könnte alle Fälle der Spalte »Nur Quelle erfolgreich« retten.")
            if config["directions"][name]["frames"] > 1:
                content.append(f"20 Schritte gegen nur den ersten Quellschritt am selben Zustand: "
                               f"{s['segment_only_win']} gewonnene und {s['segment_only_loss']} verlorene Erfolge.")
        (folder / f"{name}.md").write_text("\n\n".join(content)+"\n", encoding="utf-8")
    return results


def worker(out, phase, names, deadline, smoke):
    import paired_sim as sim
    config = read(CONFIG)
    models, critics = sim.initialize()
    db = database(out)
    phases = ["breadth", "deep1", "deep2"]
    base = config["seed_bases"]["smoke"] + phases.index(phase)*1000 if smoke else config["seed_bases"][phase]
    counts = Counter()
    current = {"state": "ACTIVE", "phase": phase, "worker_pid": os.getpid()}
    def progress(**extra):
        write(out / "progress.json", dict(current, updated=time.time(), counts=dict(counts), **extra))
    try:
        for index in ([0, 6] if smoke else range(100000)):
            for name in names:
                sim.check_time(out / "STOP", deadline)
                scene = base + index
                progress(direction=name, scene=scene)
                row = sim.measure(models, critics, scene, index, config["directions"][name], config,
                                  out / "STOP", deadline, index % config["control_every"] == 0,
                                  deep=phase != "breadth")
                with db:
                    db.execute("INSERT INTO families VALUES (?,?) ON CONFLICT(scene) DO NOTHING",
                               (scene, row["initial"]))
                    stored = db.execute("SELECT initial FROM families WHERE scene=?", (scene,)).fetchone()[0]
                    if stored != row["initial"]:
                        raise ValueError("Gleiche Startfamilie hat verschiedene Initialzustände")
                    db.execute("INSERT INTO pairs VALUES (?,?,?,?)",
                               (phase, name, scene, json.dumps(row, allow_nan=False)))
                counts[name] += 1
        else:
            if not smoke:
                raise RuntimeError("Reservierter Seedbereich erschöpft")
    except TimeoutError:
        if time.time() < deadline:
            raise
    finally:
        db.close()
    progress(phase_finished=True)


def health(out):
    import psutil
    path = out / "status.json"
    status = read(path)
    progress = read(out / "progress.json") if (out / "progress.json").exists() else {}
    worker_pid = status.get("worker_pid")
    active = status["state"] == "RUNNING"
    alive = active and worker_pid and psutil.pid_exists(worker_pid)
    if active and not psutil.pid_exists(status["pid"]):
        status["state"] = "ERROR: Supervisor beendet"
    elif active and worker_pid and (not alive or
            time.time()-max(status["phase_started"], progress.get("updated", 0)) > 300):
        status["state"] = "WARNING: Worker oder Fortschritt prüfen"
    print(json.dumps(dict(status=status, progress=progress), ensure_ascii=False))


def terminate_tree(proc):
    import psutil
    try:
        parent = psutil.Process(proc.pid)
        for child in reversed(parent.children(recursive=True)):
            try:
                child.kill()
            except psutil.NoSuchProcess:
                pass
        parent.kill()
    except psutil.NoSuchProcess:
        pass
    proc.wait(timeout=10)


def supervise(out, smoke=False):
    config = read(CONFIG)
    launch_time = read(out / "launch.json")["time"]
    status = dict(state="STARTING", pid=os.getpid(), smoke=smoke)
    worker_proc = None
    kernel = ctypes.windll.kernel32
    try:
        awake = bool(kernel.SetThreadExecutionState(0x80000001))
        status.update(keep_awake=awake)
        if not smoke:
            verify(out)
        database(out).close()
        names = list(config["directions"])
        selected = []
        end = launch_time
        for index, phase in enumerate(("breadth", "deep1", "deep2")):
            end = time.time()+300 if smoke else end+config["phase_hours"][index]*3600
            assigned = names if index == 0 else [selected[index-1]]
            cutoff = end - (10 if smoke else 25)
            if (out / "STOP").exists():
                raise InterruptedError("STOP angefordert")
            if not smoke and time.time() >= cutoff:
                raise TimeoutError("Geplantes Zeitfenster verpasst")
            args = [sys.executable, "-u", str(HERE/"night.py"), "_worker", "--out", str(out),
                    "--phase", phase, "--names", *assigned, "--cutoff", str(cutoff)]
            if smoke:
                args.append("--technical")
            with (out / f"{phase}.log").open("xb") as log:
                worker_proc = subprocess.Popen(args, cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log,
                                               stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
                status.update(state="RUNNING", phase=phase, directions=assigned, phase_started=time.time(),
                              phase_end=end, worker_pid=worker_proc.pid)
                write(out / "status.json", status)
                while worker_proc.poll() is None:
                    if (out / "STOP").exists():
                        raise InterruptedError("STOP angefordert")
                    if time.time() >= end:
                        raise TimeoutError("Worker überschritt sein Zeitfenster")
                    progress_file = out/"progress.json"
                    last_progress = max(status["phase_started"],
                                        progress_file.stat().st_mtime if progress_file.exists() else 0)
                    if time.time() - last_progress > 300:
                        raise TimeoutError("Fünf Minuten ohne abgeschlossene Familie oder neuen Arbeitsauftrag")
                    time.sleep(1)
                if (out / "STOP").exists():
                    raise InterruptedError("STOP angefordert")
                if worker_proc.returncode:
                    raise RuntimeError(f"Workerfehler {worker_proc.returncode}: {phase}.log")
            results = report(out, phase, assigned, config)
            if any(not s["families"] for s in results.values()):
                raise RuntimeError(f"Zeitfenster ohne auswertbare Familien in {phase}")
            if not smoke:
                # Keep the hour-five decision and slot boundaries fixed.
                while time.time() < end and index < 2:
                    if (out / "STOP").exists():
                        raise InterruptedError("STOP angefordert")
                    time.sleep(min(1, max(0, end-time.time())))
            if index == 0:
                selected = choose(results, config)
                write(out/"selection.json", dict(selected=selected, basis=results, time=time.time(),
                      rule="Je Gruppe höchste untere Wilson-Grenze für Erfolgswechsel pro Familie, "
                           "danach Erreichbarkeitsquote und Protokollreihenfolge."))
        if not smoke:
            verify(out)
        lines = ["# Abschluss des Nachtlaufs", "", "Technischer Smoke." if smoke else
                 "Unabhängige Vertiefungen nach Auswahl auf Entwicklungsfamilien.", ""]
        for phase, name in zip(("deep1", "deep2"), selected):
            result = read(out/phase/"summary.json")[name]
            n, k = result["families"], result["flips"]
            lo, hi = result["interval"]
            target = config["target_rate"]
            view = ("über" if lo >= target else "unter" if hi < target else "unentschieden gegenüber")
            lines.append(f"- [{name}]({phase}/{name}.md) · {k}/{n} Erfolgswechsel, "
                         f"95-%-Intervall {lo:.1%}–{hi:.1%}, {view} der 10-%-Planungsschwelle.")
        (out/"ERGEBNIS.md").write_text("\n".join(lines)+"\n", encoding="utf-8")
        status.update(state="COMPLETED")
    except BaseException as exc:
        if worker_proc and worker_proc.poll() is None:
            terminate_tree(worker_proc)
        status.update(state="STOPPED" if isinstance(exc, InterruptedError) else "ERROR", error=str(exc))
        (out/"diagnosis.log").write_text(traceback.format_exc(), encoding="utf-8")
        raise
    finally:
        kernel.SetThreadExecutionState(0x80000000)
        status.update(ended=time.time(), worker_pid=None)
        write(out/"status.json", status)


def prepare(out, smoke):
    if read(smoke/"status.json")["state"] != "COMPLETED" or not read(smoke/"status.json")["smoke"]:
        raise ValueError("Vollständiger technischer Durchlauf fehlt")
    hashes = inventory()
    if hashes != read(smoke/"inputs.json"):
        raise ValueError("Eingänge seit Smoke geändert")
    selection = read(smoke/"selection.json")
    for direction, stats_row in selection["basis"].items():
        if stats_row["families"] != 2 or stats_row["qc"] < 1:
            raise ValueError(f"Unvollständige Kontrollmessung für {direction}")
    hashes[str(smoke/"inputs.json")] = sha(smoke/"inputs.json")
    hashes[str(smoke/"status.json")] = sha(smoke/"status.json")
    out.mkdir(exist_ok=False)
    write(out/"ready.json", dict(python=str(Path(sys.executable).resolve()), hashes=hashes,
                                 smoke=str(smoke), prepared=time.time()))
    write(out/"status.json", dict(state="READY", scientific_run_started=False))
    print(f"READY | {out}")


def launch(out):
    verify(out)
    config = read(CONFIG)
    now = time.time()
    deadline = datetime.fromisoformat(config["deadline_berlin"]).timestamp()
    if now + sum(config["phase_hours"])*3600 > deadline:
        raise ValueError("Zu spät für volle 5+3+3 Stunden bis 08.11.2026 12:00 Berlin")
    if read(out/"status.json")["state"] != "READY" or (out/"STOP").exists():
        raise ValueError("Ausgabe nicht startbereit")
    with (out/"launch.json").open("x") as lock:
        json.dump(dict(time=now), lock)
    try:
        with (out/"supervisor.log").open("xb") as log:
            proc = subprocess.Popen([sys.executable, "-u", str(HERE/"night.py"), "_supervise", "--out", str(out)],
                                    cwd=ROOT, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                    creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP)
    except Exception as exc:
        write(out/"status.json", dict(state="ERROR", error=str(exc)))
        raise
    print(f"Gestartet | Supervisor {proc.pid} | {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["smoke", "prepare", "launch", "status", "_supervise", "_worker"])
    parser.add_argument("--out", type=Path)
    parser.add_argument("--smoke-source", type=Path, default=SMOKE)
    parser.add_argument("--phase")
    parser.add_argument("--names", nargs="+")
    parser.add_argument("--cutoff", type=float)
    parser.add_argument("--technical", action="store_true")
    args = parser.parse_args()
    out = (args.out or (SMOKE if args.command == "smoke" else DEFAULT)).resolve()
    if args.command == "smoke":
        out.mkdir(exist_ok=False)
        write(out/"inputs.json", inventory())
        write(out/"launch.json", dict(time=time.time()))
        supervise(out, smoke=True)
    elif args.command == "prepare":
        prepare(out, args.smoke_source.resolve())
    elif args.command == "launch":
        launch(out)
    elif args.command == "status":
        health(out)
    elif args.command == "_worker":
        worker(out, args.phase, args.names, args.cutoff, args.technical)
    else:
        supervise(out)
