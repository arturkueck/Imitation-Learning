"""Windows-Nachtsteuerung. Fortschritt und Freigaben werden bei jedem Start neu gelesen."""
import argparse
import json
import os
from datetime import date, datetime, time, timedelta
from pathlib import Path
import re
import subprocess
import traceback

FAMILY = Path(__file__).resolve().parent
ROOT = FAMILY.parents[2]
REL = FAMILY.relative_to(ROOT)
PLAN = FAMILY / "NACHTPLAN.md"
STATUS = FAMILY / "STATUS.md"
BRANCH = "experiment_three_cube_critic"
STATE = Path(os.environ["LOCALAPPDATA"]) / "Codex" / "three-cube-night"
RESULTS = ROOT / "praxis/results/critic/three_cube_transfer_v1"
DEPS = {
    "N1-1": (), "N1-2": ("N1-1",), "N1-3": (),
    "N1-4": ("N1-2", "N1-3"), "N1-5": ("N1-4",),
    "N1-6": ("N1-2", "N1-3", "N1-4", "N1-5"),
    "N2-1": ("N1-6",), "N2-2": ("N2-1",), "N2-3": ("N2-2",),
    "N2-4": ("N2-3",), "N3-1": ("N2-4",), "N3-2": ("N3-1",),
    "N4-1": ("N3-2",), "N4-2": ("N4-1",), "N4-3": ("N4-2",),
    "N4-4": ("N4-3",),
}
GATED = {"N2-2", "N2-3", "N3-1", "N4-4"}


def git(*args):
    return subprocess.check_output(["git", "-C", ROOT, *args], encoding="utf-8").strip()


def read_queue():
    status = STATUS.read_text(encoding="utf-8-sig")
    rows = re.findall(r"(?m)^\|\s*(N\d-\d)\s*\|\s*(offen|läuft|erledigt|blockiert)\s*\|", status)
    pause = re.findall(r"(?m)^Gesamtpause: (ja|nein)\s*$", status)
    if len(rows) != len(DEPS) or set(dict(rows)) != set(DEPS) or len(pause) != 1:
        raise ValueError("STATUS.md unvollständig oder mehrdeutig")
    plan = PLAN.read_text(encoding="utf-8-sig")
    approvals = set()
    for group in re.findall(r"(?m)^- \[[xX]\] (N\d-\d(?:/N\d-\d)*):", plan):
        approvals.update(group.split("/"))
    return dict(rows), approvals, pause == ["ja"]


def select(rows, approvals, already_checked):
    for state in ("läuft", "offen"):
        for task, required in DEPS.items():
            if rows[task] != state or task in already_checked:
                continue
            if state == "offen" and task in GATED and task not in approvals:
                continue
            if all(rows[dep] == "erledigt" for dep in required):
                return task
    return None


def window(now, first):
    night = now.date() if now.hour >= 22 else now.date() - timedelta(days=1)
    index = (night - first).days + 1
    deadline = datetime.combine(night + timedelta(days=1), time(9))
    if not 1 <= index <= 4 or not datetime.combine(night, time(22)) <= now < deadline:
        return None
    return index, night, deadline


def log(message):
    with (STATE / "dispatcher.log").open("a", encoding="utf-8") as stream:
        print(datetime.now().isoformat(timespec="seconds"), message, file=stream, flush=True)


def commit_report(files, summary):
    if not files:
        return
    allowed_docs = {Path("experiments/critic/README.md"), Path("monitor/training-runs.json")}
    checked = []
    for name in files:
        path = (ROOT / name).resolve()
        relative = path.relative_to(ROOT)
        if relative not in allowed_docs:
            path.relative_to(FAMILY)
            if path in (PLAN, Path(__file__).resolve()) or path.suffix.lower() not in {
                ".md", ".py", ".json", ".csv", ".toml", ".yaml", ".yml", ".ps1",
            }:
                raise ValueError(f"Unerwartete Übergabedatei: {relative}")
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError(f"Keine kleine Übergabedatei: {relative}")
        checked.append(str(relative))
    git("add", "--", *checked)
    staged = subprocess.run(["git", "-C", ROOT, "diff", "--cached", "--quiet", "--", *checked])
    if staged.returncode == 1:
        git("commit", "--only", "-m", summary.splitlines()[0], "--", *checked)
    else:
        staged.check_returncode()


def worker(args, task, report, deadline):
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S_%f")
    answer = STATE / (stamp + ".json")
    transcript = STATE / (stamp + ".log")
    schema = STATE / "handoff-schema.json"
    schema.write_text(json.dumps({"type": "object", "additionalProperties": False, "properties": {
        "files": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"}}, "required": ["files", "summary"]}), encoding="utf-8")
    prompt = f"""Du bist der zuständige Nachtagent für {task}. Arbeitszweig {BRANCH}.
Lies AGENTS.md, Agend.md, experiments/AGENTS.md und in {REL.as_posix()} NACHTPLAN.md und STATUS.md.
Dein Auftrag ist genau {task}. Bei einer Aufgaben-ID die Aufgabe wirklich bearbeiten und verifizieren.
Bei MORGENUEBERGABE nur offene Prozesse mit ihrem Monitor prüfen, exakt fortsetzbar anhalten und die Nacht abschließen.
Jetzt {now:%d.%m.%Y %H:%M} Europe/Berlin, keine neuen Läufe ab 07:30, Übergabe bis {deadline:%d.%m.%Y %H:%M}.
Prüfe die Uhr vor jedem Laufstart. Lange Läufe nur unter eigenem Supervisor mit wirksamer Deadline,
inkrementellem Monitor und Eintrag im Dashboard. Beende deinen Agenten nach dem Start mit dokumentierter
Prozessidentität und Monitorbefehl; der Zeitplan übernimmt die nächste Prüfung. Keine zweite Instanz.
Für laufende Arbeit zuerst ihren Monitor verwenden. Bei gesundem unverändertem Stand kurz enden.
Nur im aktuellen Worktree arbeiten. Lokale Daten und die bestehende venv sind unter praxis/ eingebunden.
Freigaben unmittelbar vor jedem Optimizerupdate-Lauf im NACHTPLAN prüfen. Niemals Freigaben selbst erteilen.
Bei widerrufener Freigabe einen laufenden Auftrag nur prüfen und sicher übergeben. Nach einem
Abbruch nie eigenständig einen wissenschaftlichen Lauf wiederholen. Prüfe bei vorhandenen Teilständen
zuerst Prozessidentität, bereits erbrachte Arbeit und den letzten belegbaren Fortsetzungspunkt.
Bei Sofortstopp Gesamtpause: ja in STATUS.md setzen, dokumentieren und zurückgeben. Bei rein lokaler Blockade
nur die betroffene Aufgabe blockieren. Testfamilien bleiben geschlossen gemäß Plan.
Beachte die Fertig-wenn-Spalte. Vor dem Abschluss Arbeit prüfen und Nachweise verlinken. Aktualisiere die
Tabellenzeile in STATUS.md (Format erhalten), den gemeinsamen Nachtbericht {report.relative_to(ROOT).as_posix()}
mit den sechs Abschnitten und den Statussatz in experiments/critic/README.md. Für jede Nacht nur einen Bericht.
Lass begonnene Aufgaben mit belastbarem Fortsetzungspunkt auf läuft. Niemals wissenschaftliche Ergebnisse erfinden.
Bei MORGENUEBERGABE verbleibende Freigaben und den nächsten Schritt nennen. Kein Push oder Merge.
Git-Commits übernimmt die Steuerung: gib zum Abschluss als JSON die geprüften kleinen Dateien dieses Schritts
als einzelne repo-relative Pfade in files und eine aussagekräftige deutsche Commitnachricht in summary an.
Bei unverändertem Stand files leer lassen. Ändere weder die Steuerung noch den Nachtplan. Starte keine weiteren Agenten."""
    log(f"START {task} {transcript.name}")
    with transcript.open("wb") as stream:
        result = subprocess.run([args.codex, "-a", "never", "exec", "-s", "workspace-write",
                                 "--add-dir", str(RESULTS.resolve()), "-C", str(ROOT),
                                 "--output-schema", str(schema), "-o", str(answer), "-"],
                                input=prompt.encode(), cwd=ROOT, stdout=stream, stderr=stream,
                                timeout=max(1, (deadline - datetime.now()).total_seconds()))
    result.check_returncode()
    reply = json.loads(answer.read_text(encoding="utf-8-sig"))
    commit_report(reply["files"], f"{task} {reply['summary']}")
    log(f"ENDE {task} {reply['summary']}")


def dispatch(args):
    if git("branch", "--show-current") != BRANCH:
        raise ValueError("Falscher Arbeitszweig")
    seen = set()
    pending = STATE / "offene_uebergabe.txt"
    while (slot := window(datetime.now(), args.first_night)):
        index, night, deadline = slot
        report = FAMILY / "nights" / f"NACHT_{index}_{night:%Y%m%d}.md"
        rows, approvals, paused = read_queue()
        morning = datetime.now() >= deadline - timedelta(minutes=90)
        marker = STATE / f"uebergeben_{night}.txt"
        if morning and marker.exists():
            return
        if morning:
            task = "MORGENUEBERGABE"
        elif paused:
            log("PAUSE laut STATUS.md")
            return
        elif pending.is_file() and pending.read_text(encoding="ascii") in DEPS:
            task = pending.read_text(encoding="ascii")
        else:
            task = select(rows, approvals, seen)
        if task is None:
            log("Keine weitere freigegebene Aufgabe")
            return
        pending.write_text(task, encoding="ascii")
        worker(args, task, report, deadline)
        if morning:
            if not report.is_file() or git("status", "--porcelain", "--", report):
                raise ValueError("Nachtübergabe fehlt im Commit")
            marker.write_text(git("rev-parse", "HEAD"), encoding="ascii")
            pending.unlink()
            return
        current, _, paused = read_queue()
        if current[task] == "erledigt":
            if not report.is_file() or git("status", "--porcelain", "--", STATUS, report):
                raise ValueError("Aufgabenübergabe fehlt im Commit")
        pending.unlink()
        if paused:
            return
        seen.add(task)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--first-night", type=date.fromisoformat, required=True)
    parser.add_argument("--codex", required=True)
    args = parser.parse_args()
    STATE.mkdir(exist_ok=True, parents=True)
    try:
        dispatch(args)
    except Exception:
        log(traceback.format_exc())
        raise
