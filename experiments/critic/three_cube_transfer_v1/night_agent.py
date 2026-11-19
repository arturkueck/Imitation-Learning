"""Windows-Nachtsteuerung. Fortschritt und Freigaben werden bei jedem Start neu gelesen."""
import argparse
import json
import msvcrt
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
GATED = {"N2-1", "N2-2", "N2-3", "N3-1", "N4-4"}
CLAUDE_TASKS = {task for task in DEPS if not task.startswith("N1-")}
FIGURES = FAMILY / "figures"
FIGURE_MILESTONES = {
    "N2-2": ("CRITIC_VALIDATION.md", "Vortrainingsloss je Parent, Critic-Validierung "
             "gegen die Phasen-Baseline und BC-Aufgabenerfolg mit Nennern"),
    "N2-3": ("AC_SMOKE.md", "Actor-Drift über die beiden Runden je Variante und Parent, "
             "technische Stabilitätskriterien und Erhalt der Parent-Erfolge"),
    "N4-1": ("PILOT_REPORT.md", "Aufgabenerfolg je Seed und Arm über die Onlineinteraktionen, "
             "gepaarte Endergebnisse und getrennte Trainingslosses, soweit aufgezeichnet"),
}
HANDOFF_SCHEMA = json.dumps({
    "type": "object", "additionalProperties": False,
    "properties": {"files": {"type": "array", "items": {"type": "string"}},
                   "summary": {"type": "string"}},
    "required": ["files", "summary"],
})


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
    protocol = FAMILY / "PROTOCOL.md"
    if protocol.is_file() and "**Status: FREIGEGEBEN**" in protocol.read_text(encoding="utf-8-sig"):
        approvals.add("N2-1")
    main_protocol = FAMILY / "MAIN_PROTOCOL.md"
    if not (main_protocol.is_file()
            and "**Status: FREIGEGEBEN**" in main_protocol.read_text(encoding="utf-8-sig")):
        approvals.discard("N4-4")
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
    shared_files = {
        Path("experiments/critic/README.md"),
        Path("experiments/curriculum/registry.py"),
        Path("monitor/training-runs.json"),
    }
    checked = []
    for name in files:
        path = (ROOT / name).resolve()
        relative = path.relative_to(ROOT)
        if relative not in shared_files:
            path.relative_to(FAMILY)
            allowed_types = {".md", ".py", ".json", ".csv", ".toml", ".yaml", ".yml", ".ps1", ".sha256"}
            if path.is_relative_to(FIGURES):
                allowed_types.add(".png")
            if path in (PLAN, Path(__file__).resolve()) or path.suffix.lower() not in allowed_types:
                raise ValueError(f"Unerwartete Übergabedatei: {relative}")
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError(f"Keine kleine Übergabedatei: {relative}")
        checked.append(str(relative))
    git("add", "--", *checked)
    if git("diff", "--cached", "--name-only", "--", *checked):
        git("commit", "--only", "-m", summary.splitlines()[0], "--", *checked)


def run_claude(executable, prompt, schema, stream, timeout, execution):
    command = [
        executable, "--print", "--safe-mode", "--strict-mcp-config",
        "--no-session-persistence", "--permission-mode", "acceptEdits",
        "--tools", "Read,Glob,Grep,Edit,Write,Bash" if execution else "Read,Glob,Grep,Edit,Write",
        "--output-format", "json",
        "--json-schema", schema,
    ]
    if execution:
        command.extend([
            "--allowedTools",
            "Bash(./praxis/.venv/Scripts/python.exe -m pytest *)",
            f"Bash(./praxis/.venv/Scripts/python.exe {REL.as_posix()}/*.py*)",
            "Bash(date*)", "Bash(git status*)", "Bash(git diff*)",
        ])
    result = subprocess.run(command, input=prompt.encode(), cwd=ROOT, stdout=subprocess.PIPE,
                            stderr=stream, timeout=timeout)
    stream.write(result.stdout)
    result.check_returncode()
    response = json.loads(result.stdout)
    if response.get("is_error") or not isinstance(response.get("structured_output"), dict):
        raise ValueError("Claude hat keine erfolgreiche strukturierte Übergabe geliefert")
    return response["structured_output"]


def worker(args, task, report, deadline, cutoff):
    now = datetime.now()
    stamp = now.strftime("%Y%m%d_%H%M%S_%f")
    answer = STATE / (stamp + ".json")
    transcript = STATE / (stamp + ".log")
    schema = STATE / "handoff-schema.json"
    schema.write_text(HANDOFF_SCHEMA, encoding="utf-8")
    daytime = (
        "Dies ist der vom Nutzer freigegebene Tagesbetrieb. Die hier genannten Zeiten ersetzen "
        "für diesen Durchgang die Uhrzeiten des Nachtplans. Forschungsregeln und Freigaben gelten."
        if args.day_until else ""
    )
    prompt = f"""Du bist der zuständige Nachtagent für {task}. Arbeitszweig {BRANCH}.
Lies AGENTS.md, Agend.md, experiments/AGENTS.md und in {REL.as_posix()} NACHTPLAN.md und STATUS.md.
Dein Auftrag ist genau {task}. Bei einer Aufgaben-ID die Aufgabe wirklich bearbeiten und verifizieren.
Bei MORGENUEBERGABE nur offene Prozesse mit ihrem Monitor prüfen, exakt fortsetzbar anhalten und die Nacht abschließen.
Jetzt {now:%d.%m.%Y %H:%M} Europe/Berlin, keine neuen Läufe ab {cutoff:%H:%M}, Übergabe bis {deadline:%d.%m.%Y %H:%M}.
{daytime}
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
    claude_failure = STATE / f"claude_n1_6_failed_{now:%Y%m%d}.txt"
    claude_execution = task in CLAUDE_TASKS
    use_claude = claude_execution or bool(args.claude and args.day_until and task == "N1-6"
                                         and not claude_failure.exists())
    if claude_execution and not Path(args.claude).is_file():
        raise FileNotFoundError("Die freigegebenen Aufgaben benötigen Claude Code.")
    provider = "Claude" if use_claude else "Codex"
    if use_claude and not claude_execution:
        prompt += "\nSchreibe ausschließlich Protokoll und Übergabedokumente. Starte weder Simulationen noch Training."
    if claude_execution:
        prompt += (
            "\nDer Nutzer hat dieses Pilotprotokoll und die markierten Schritte für Claude freigegeben. "
            "Nutze Bash mit ./praxis/.venv/Scripts/python.exe für die Familienskripte und pytest. "
            "Lange Versuche als beaufsichtigten Hintergrundprozess starten und mit geprüftem Monitor übergeben. "
            "Halte den gegebenen Cutoff und die Deadline im Supervisor durchsetzbar fest. "
            "Bei einer laufenden Aufgabe zuerst den dokumentierten Monitor ausführen. "
            "Bei fehlendem Nachweis einer nötigen Freigabe, Abbruchbedingung oder einer Protokolländerung "
            "nach Nachtplan stoppen. Git-Commits übernimmt der Dispatcher."
        )
    if task == "N2-1":
        prompt += (
            "\nAuftrag: Implementiere und verifiziere N2-1, dann starte die freigegebenen 900 Rollouts "
            "unter Supervisor, sobald die technischen Prüfungen bestanden sind. Nutze den Claude-Vorabbericht "
            "20261119_111234_199645_N2-1_claude_preflight.md im lokalen Dispatcher-Ordner als technische Grundlage. "
            "Die Freigaben und Behandlung von Fehlern stehen in PROTOCOL.md §11–12. "
            "Ein einzelner Vergleich auf der bestehenden Kalibrierungsfamilie ist als technischer Test freigegeben. "
            "Für N2-1 sind genau 0 Optimizerupdates vorgesehen. Verwende ausschließlich critic_data zum Sammeln."
        )
    log(f"START {task} {transcript.name} ({provider})")
    environment = os.environ.copy()
    environment["PATH"] = str(Path(args.codex).parent) + os.pathsep + environment.get("PATH", "")
    timeout = max(1, (deadline - datetime.now()).total_seconds())
    with transcript.open("wb") as stream:
        if use_claude:
            try:
                reply = run_claude(args.claude, prompt, HANDOFF_SCHEMA, stream, timeout, claude_execution)
            except (subprocess.SubprocessError, ValueError, OSError):
                if not claude_execution:
                    claude_failure.touch()
                    log("Claude-Übergabe fehlgeschlagen. N1-6 beim nächsten Termin an Codex geben.")
                raise
            answer.write_text(json.dumps(reply, ensure_ascii=False), encoding="utf-8")
        else:
            result = subprocess.run([args.codex, "-a", "never", "exec", "-s", "workspace-write",
                                     "--add-dir", str(RESULTS.resolve()), "-C", str(ROOT),
                                     "--output-schema", str(schema), "-o", str(answer), "-"],
                                    input=prompt.encode(), cwd=ROOT, env=environment, stdout=stream, stderr=stream,
                                    timeout=timeout)
            result.check_returncode()
            reply = json.loads(answer.read_text(encoding="utf-8-sig"))
    commit_report(reply["files"], f"{task} {reply['summary']}")
    log(f"ENDE {task} {reply['summary']}")


def select_figure(rows, checked):
    for task in FIGURE_MILESTONES:
        if rows[task] != "erledigt" or task in checked:
            continue
        folder = FIGURES / task.lower()
        if not ((folder / "README.md").is_file() and (folder / "plot.py").is_file()
                and any(folder.glob("*.png")) and not git("status", "--porcelain", "--", folder)):
            return task
    return None


def figure_worker(args, task, deadline):
    document, subject = FIGURE_MILESTONES[task]
    folder = FIGURES / task.lower()
    relative = folder.relative_to(ROOT).as_posix()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    transcript = STATE / f"{stamp}_{task}_figures.log"
    prompt = f"""Du bist Claude und übernimmst die wissenschaftlichen Abbildungen für {task}.
Lies AGENTS.md, experiments/AGENTS.md und {REL.as_posix()}/{document}. Verwende ausschließlich
dessen verifizierte Ergebniszusammenfassungen und kleine aggregierte Metrikdateien. Keine Rohtrajektorien,
Gewichte, Testfamilien, Simulation, Optimizerupdates oder Änderungen an Versuchscode und Statusdateien.
Erstelle unter {relative}/ klare Abbildungen als PNG und einen reproduzierbaren Generator plot.py
mit der Projekt-venv und Matplotlib (Agg). Thema: {subject}.
Nutze als Quellen genau die verifizierten Werte und führe den Generator aus:
./praxis/.venv/Scripts/python.exe {relative}/plot.py
Prüfe die PNGs visuell. Beschrifte Achsen, Einheiten, Gruppen, Nenner und gegebenenfalls Intervalle.
Halte Loss, technische Stabilität und Aufgabenerfolg auseinander. Runde erst bei der Anzeige.
Dokumentiere Quellen, Aufruf, Abbildungen und Aussagegrenzen in {relative}/README.md.
Schreibe ausschließlich in diesem Abbildungsordner. Gib dessen neuen oder aktualisierten Dateien
als repo-relative Pfade in files und eine aussagekräftige Zeile in summary aus. Kein Git-Commit."""
    log(f"START FIGURES {task} {transcript.name} (Claude)")
    remaining = (deadline - datetime.now()).total_seconds()
    if remaining <= 0:
        return
    with transcript.open("wb") as stream:
        reply = run_claude(args.claude, prompt, HANDOFF_SCHEMA, stream, min(remaining, 600), True)
    files = [(ROOT / name).resolve() for name in reply["files"]]
    required = {folder / "README.md", folder / "plot.py"}
    images = [path for path in files if path.suffix.lower() == ".png"]
    if not (all(path.is_relative_to(folder) for path in files) and required.issubset(files) and images):
        raise ValueError(f"Unvollständige oder unzulässige Abbildungsübergabe für {task}")
    for png in images:
        with png.open("rb") as stream:
            if stream.read(8) != bytes.fromhex("89504e470d0a1a0a"):
                raise ValueError(f"Ungültige PNG-Datei: {png.name}")
    commit_report(reply["files"], f"{task} Abbildungen: {reply['summary']}")
    log(f"ENDE FIGURES {task} {relative} (Claude)")


def active_window(now, args):
    if not args.day_until:
        return window(now, args.first_night)
    if now.date() != args.day_until.date() or now >= args.day_until:
        return None
    night = now.date() - timedelta(days=1)
    return (night - args.first_night).days + 1, night, args.day_until


def dispatch(args):
    if git("branch", "--show-current") != BRANCH:
        raise ValueError("Falscher Arbeitszweig")
    seen = set()
    figures_checked = set()
    suffix = f"_tag_{args.day_until:%Y%m%d}" if args.day_until else ""
    pending = STATE / f"offene_uebergabe{suffix}.txt"
    while (slot := active_window(datetime.now(), args)):
        index, night, deadline = slot
        report = FAMILY / "nights" / f"NACHT_{index}_{night:%Y%m%d}.md"
        rows, approvals, paused = read_queue()
        cutoff = deadline - timedelta(minutes=30 if args.day_until else 90)
        handoff_at = deadline - timedelta(minutes=15) if args.day_until else cutoff
        morning = datetime.now() >= handoff_at
        marker = STATE / f"uebergeben_{night}{suffix}.txt"
        if morning and marker.exists():
            return
        if morning:
            task = "MORGENUEBERGABE"
        elif paused:
            log("PAUSE laut STATUS.md")
            return
        else:
            previous = pending.read_text(encoding="ascii") if pending.is_file() else ""
            if previous in DEPS and (previous not in GATED or previous in approvals
                                     or rows[previous] in ("läuft", "erledigt")):
                task = previous
            else:
                task = select(rows, approvals, seen)
                # A live run gets its monitor check before a figure job.
                if task is None or rows[task] != "läuft":
                    figure = select_figure(rows, figures_checked)
                    if figure:
                        figures_checked.add(figure)
                        try:
                            figure_worker(args, figure, handoff_at)
                        except Exception:
                            log(f"Abbildungsübergabe für {figure} fehlgeschlagen (Claude)\n" +
                                traceback.format_exc())
                        continue
        if task is None:
            log("Keine weitere freigegebene Aufgabe")
            return
        pending.write_text(task, encoding="ascii")
        worker(args, task, report, deadline, cutoff)
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
    parser.add_argument("--claude", default=str(Path.home() / ".local/bin/claude.exe"))
    parser.add_argument("--day-until", type=datetime.fromisoformat,
                        help="Einmaliges Tagesfenster mit lokaler Berliner Uhrzeit")
    args = parser.parse_args()
    if args.day_until and args.day_until.tzinfo:
        parser.error("--day-until erwartet lokale Uhrzeit ohne Offset")
    STATE.mkdir(exist_ok=True, parents=True)
    with (STATE / "dispatcher.lock").open("a+b") as lock:
        lock.seek(0)
        try:
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            log("Andere Steuerungsinstanz ist aktiv")
        else:
            try:
                dispatch(args)
            except Exception:
                log(traceback.format_exc())
                raise
