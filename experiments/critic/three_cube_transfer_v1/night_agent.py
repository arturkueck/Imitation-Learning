"""Windows-Nachtsteuerung. Fortschritt, Freigaben, Aufgaben und Kontingente werden bei jedem Start neu gelesen.

Regeln: AGENTEN_ORCHESTRIERUNG.md im Repository-Stamm. Aufgaben: tasks.json, Kontingente: orchestration.json.
"""
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
TASKS_FILE = FAMILY / "tasks.json"
ORCHESTRATION_FILE = FAMILY / "orchestration.json"
PROVIDERS = ("claude", "codex")
TASK_ID = r"[A-Z][A-Za-z0-9]*(?:-[A-Za-z0-9]+)?"


def load_tasks():
    data = json.loads(TASKS_FILE.read_text(encoding="utf-8-sig"))
    tasks = {}
    for entry in data["tasks"]:
        if not re.fullmatch(TASK_ID, entry["id"]) or entry["id"] in tasks:
            raise ValueError(f"Ungültige oder doppelte Aufgaben-ID in tasks.json: {entry['id']}")
        providers = tuple(entry.get("providers") or PROVIDERS)
        if not providers or set(providers) - set(PROVIDERS):
            raise ValueError(f"Unbekannter Anbieter für {entry['id']}")
        tasks[entry["id"]] = {
            "deps": tuple(entry.get("deps", ())),
            "gate": entry.get("gate"),
            "providers": providers,
            "kind": entry.get("kind", "task"),
            "light": bool(entry.get("light", False)),
            "not_before": datetime.fromisoformat(entry["not_before"]) if entry.get("not_before") else None,
        }
    for task, spec in tasks.items():
        missing = set(spec["deps"]) - set(tasks)
        if missing:
            raise ValueError(f"{task} hängt von unbekannten Aufgaben ab: {sorted(missing)}")
    return tasks


TASKS = load_tasks()
DEPS = {task: spec["deps"] for task, spec in TASKS.items()}
GATED = {task for task, spec in TASKS.items() if spec["gate"]}
ORCHESTRATION = json.loads(ORCHESTRATION_FILE.read_text(encoding="utf-8-sig"))
LIMIT_TEXT = re.compile(
    r"usage limit|rate[ _-]?limit|limit reached|hit your (?:usage )?limit|quota|too many requests|"
    r"\b429\b|overloaded|credit balance", re.IGNORECASE)
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
    rows = re.findall(r"(?m)^\|\s*(" + TASK_ID + r")\s*\|\s*(offen|läuft|erledigt|blockiert)\s*\|", status)
    pause = re.findall(r"(?m)^Gesamtpause: (ja|nein)\s*$", status)
    if len(rows) != len(DEPS) or set(dict(rows)) != set(DEPS) or len(pause) != 1:
        raise ValueError("STATUS.md unvollständig oder mehrdeutig")
    plan = PLAN.read_text(encoding="utf-8-sig")
    approvals = set()
    for group in re.findall(r"(?m)^- \[[xX]\] (" + TASK_ID + r"(?:/" + TASK_ID + r")*):", plan):
        approvals.update(group.split("/"))
    protocol = FAMILY / "PROTOCOL.md"
    if protocol.is_file() and "**Status: FREIGEGEBEN**" in protocol.read_text(encoding="utf-8-sig"):
        approvals.add("N2-1")
    main_protocol = FAMILY / "MAIN_PROTOCOL.md"
    if not (main_protocol.is_file()
            and "**Status: FREIGEGEBEN**" in main_protocol.read_text(encoding="utf-8-sig")):
        approvals.discard("N4-4")
    return dict(rows), approvals, pause == ["ja"]


def approved(task, approvals):
    gate = TASKS[task]["gate"]
    return gate is None or gate in approvals


def select(rows, approvals, already_checked, ledger=None, now=None):
    """Nächste Aufgabe und Anbieter. Laufende Aufgaben (Monitorprüfung) haben Vorrang."""
    now = now or datetime.now()
    for state in ("läuft", "offen"):
        for task, spec in TASKS.items():
            if rows[task] != state or task in already_checked:
                continue
            if state == "offen" and not approved(task, approvals):
                continue
            if state == "offen" and spec["not_before"] and now < spec["not_before"]:
                continue
            if not all(rows[dep] == "erledigt" for dep in spec["deps"]):
                continue
            if ledger is None:
                return task
            if ledger.failures(task) >= ORCHESTRATION.get("max_consecutive_failures_per_task", 2):
                continue
            # Eine Monitorprüfung ist kurz und darf auch bei knappem Kontingent laufen.
            provider = ledger.choose(spec["providers"], light=spec["light"] or state == "läuft", now=now)
            if provider:
                return task, provider
            ledger.note_deferred(task)
    return None


class LimitReached(Exception):
    def __init__(self, provider, until, detail):
        super().__init__(f"{provider}: Kontingent erschöpft bis {until:%d.%m. %H:%M} ({detail})")
        self.provider, self.until, self.detail = provider, until, detail


def parse_reset(text, now=None):
    """Rücksetzzeitpunkt aus einer Limitmeldung, sonst None."""
    now = now or datetime.now()
    if match := re.search(r"\|(\d{10})\b", text):
        return datetime.fromtimestamp(int(match.group(1)))
    if match := re.search(r"resets?_in_seconds\D{0,4}(\d+)", text):
        return now + timedelta(seconds=int(match.group(1)))
    if match := re.search(r"(?:try again|retry|resets?) in (\d+)\s*(second|minute|min|hour|h)", text, re.IGNORECASE):
        unit = match.group(2).lower()
        seconds = {"second": 1, "minute": 60, "min": 60, "hour": 3600, "h": 3600}[unit]
        return now + timedelta(seconds=int(match.group(1)) * seconds)
    if match := re.search(r"resets?(?: at)? (\d{1,2})(?::(\d{2}))?\s*(am|pm)?", text, re.IGNORECASE):
        hour, minute = int(match.group(1)), int(match.group(2) or 0)
        if match.group(3):
            hour = hour % 12 + (12 if match.group(3).lower() == "pm" else 0)
        if hour < 24 and minute < 60:
            at = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            return at if at > now else at + timedelta(days=1)
    return None


def scan_codex_events(raw):
    """Liest Tokenzahlen und Kontingentstände aus `codex exec --json`, soweit vorhanden."""
    used, resets, output_tokens = None, None, 0

    def walk(node):
        nonlocal used, resets, output_tokens
        if isinstance(node, dict):
            if isinstance(node.get("used_percent"), (int, float)):
                used = max(used or 0.0, float(node["used_percent"]))
                if isinstance(node.get("resets_in_seconds"), (int, float)):
                    resets = max(resets or 0, int(node["resets_in_seconds"]))
            for key in ("total_token_usage", "last_token_usage", "usage"):
                value = node.get(key)
                if isinstance(value, dict) and isinstance(value.get("output_tokens"), int):
                    output_tokens = max(output_tokens, value["output_tokens"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    for line in raw.splitlines():
        line = line.strip()
        if line.startswith("{"):
            try:
                walk(json.loads(line))
            except ValueError:
                pass
    return used, resets, output_tokens


class Ledger:
    """Verbrauchsbuch je Nacht und Anbieter, persistent im lokalen Steuerungsordner."""

    def __init__(self, night, available):
        self.path = STATE / f"usage_{night:%Y%m%d}.json"
        self.available = set(available)
        self.data = {"providers": {}, "failures": {}, "deferred": []}
        if self.path.is_file():
            self.data.update(json.loads(self.path.read_text(encoding="utf-8")))
        for provider in PROVIDERS:
            self.data["providers"].setdefault(provider, {
                "runs": 0, "output_tokens": 0, "cost_usd": 0.0,
                "cooldown_until": None, "used_percent": None})

    def save(self):
        self.path.write_text(json.dumps(self.data, ensure_ascii=False, indent=1), encoding="utf-8")

    def config(self, provider):
        return ORCHESTRATION["providers"].get(provider, {})

    def usable(self, provider, light, reserve, now):
        if provider not in self.available:
            return False
        state, config = self.data["providers"][provider], self.config(provider)
        if state["cooldown_until"] and now < datetime.fromisoformat(state["cooldown_until"]):
            return False
        limit = config.get("max_agent_runs_per_night")
        if limit is not None and state["runs"] >= limit - reserve:
            return False
        tokens = config.get("max_output_tokens_per_night")
        if tokens is not None and state["output_tokens"] >= tokens:
            return False
        cost = config.get("max_cost_usd_per_night")
        if cost is not None and state["cost_usd"] >= cost:
            return False
        used = state["used_percent"]
        if used is not None:
            if used >= config.get("stop_above_used_percent", 101):
                return False
            if not light and used >= config.get("defer_heavy_above_used_percent", 101):
                return False
        return True

    def choose(self, providers, light=False, handover=False, now=None):
        now = now or datetime.now()
        reserve = 0 if handover else ORCHESTRATION.get("reserve_runs_for_handover", 1)
        for provider in providers:
            if self.usable(provider, light or handover, reserve, now):
                return provider
        return None

    def record(self, provider, output_tokens=0, cost_usd=0.0, used_percent=None):
        state = self.data["providers"][provider]
        state["runs"] += 1
        state["output_tokens"] += int(output_tokens or 0)
        state["cost_usd"] = round(state["cost_usd"] + float(cost_usd or 0.0), 4)
        if used_percent is not None:
            state["used_percent"] = used_percent
        self.save()

    def cooldown(self, provider, until):
        self.data["providers"][provider]["cooldown_until"] = until.isoformat(timespec="minutes")
        self.save()

    def failures(self, task):
        return self.data["failures"].get(task, 0)

    def fail(self, task):
        self.data["failures"][task] = self.failures(task) + 1
        self.save()

    def succeed(self, task):
        self.data["failures"].pop(task, None)
        self.save()

    def note_deferred(self, task):
        stamp = f"{datetime.now():%H:%M} {task}"
        self.data["deferred"] = (self.data["deferred"] + [stamp])[-50:]
        self.save()

    def summary(self):
        parts = []
        for provider, state in self.data["providers"].items():
            parts.append(f"{provider}: {state['runs']} Agentenläufe, {state['output_tokens']} Ausgabetokens, "
                         f"{state['cost_usd']} USD, Kontingent {state['used_percent']} %, "
                         f"Pause bis {state['cooldown_until'] or '–'}")
        return "; ".join(parts)


def window(now, first, nights=4):
    night = now.date() if now.hour >= 22 else now.date() - timedelta(days=1)
    index = (night - first).days + 1
    deadline = datetime.combine(night + timedelta(days=1), time(9))
    if not 1 <= index <= nights or not datetime.combine(night, time(22)) <= now < deadline:
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
            if (path in (PLAN, Path(__file__).resolve(), TASKS_FILE, ORCHESTRATION_FILE)
                    or path.suffix.lower() not in allowed_types):
                raise ValueError(f"Unerwartete Übergabedatei: {relative}")
        if not path.is_file() or path.stat().st_size > 5_000_000:
            raise ValueError(f"Keine kleine Übergabedatei: {relative}")
        checked.append(str(relative))
    git("add", "--", *checked)
    if git("diff", "--cached", "--name-only", "--", *checked):
        git("commit", "--only", "-m", summary.splitlines()[0], "--", *checked)


def run_claude(executable, prompt, schema, stream, timeout, execution, ledger=None):
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
                            stderr=subprocess.PIPE, timeout=timeout)
    stream.write(result.stdout)
    stream.write(result.stderr)
    text = (result.stdout + result.stderr).decode("utf-8", "replace")
    try:
        response = json.loads(result.stdout)
    except ValueError:
        response = {}
    usage = response.get("usage") or {}
    if ledger is not None:
        ledger.record("claude", usage.get("output_tokens", 0), response.get("total_cost_usd", 0.0))
    failed = result.returncode != 0 or response.get("is_error")
    if failed and LIMIT_TEXT.search(text):
        default = ledger.config("claude").get("default_cooldown_minutes", 60) if ledger else 60
        until = parse_reset(text) or datetime.now() + timedelta(minutes=default)
        raise LimitReached("claude", until, LIMIT_TEXT.search(text).group(0))
    result.check_returncode()
    if response.get("is_error") or not isinstance(response.get("structured_output"), dict):
        raise ValueError("Claude hat keine erfolgreiche strukturierte Übergabe geliefert")
    return response["structured_output"]


def codex_supports_json(executable):
    try:
        text = subprocess.run([executable, "exec", "--help"], capture_output=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return b"--json" in text


def worker(args, task, report, deadline, cutoff, provider, ledger):
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
Bei MORGENUEBERGABE verbleibende Freigaben, den nächsten Schritt und den Kontingentstand nennen. Kein Push oder Merge.
Git-Commits übernimmt die Steuerung: gib zum Abschluss als JSON die geprüften kleinen Dateien dieses Schritts
als einzelne repo-relative Pfade in files und eine aussagekräftige deutsche Commitnachricht in summary an.
Bei unverändertem Stand files leer lassen. Ändere weder die Steuerung noch den Nachtplan. Starte keine weiteren Agenten.
Lies vorher AGENTEN_ORCHESTRIERUNG.md. Neue Aufgaben-IDs (etwa D1a, N2-1b, B-1) stehen im Aufgabenstapel des
NACHTPLAN und in PROTOCOL_V2.md. Arbeite kontingentschonend: nur nötige Dateien lesen, keine großen Logs oder
Rohdaten in den Kontext laden, Rechenzeit in Simulationen statt in Agentenschleifen verbringen. Du bist {provider}.
Stand des Kontingents dieser Nacht: {ledger.summary()}."""
    use_claude = provider == "claude"
    claude_execution = use_claude
    if use_claude and not Path(args.claude).is_file():
        raise FileNotFoundError("Claude Code ist nicht installiert.")
    if task in GATED:
        prompt += (
            "\nDiese Aufgabe enthält Optimizerupdates. Ihre Freigabe gilt laut AGENTEN_ORCHESTRIERUNG.md "
            "für Claude und Codex gleichermaßen. Freigabe unmittelbar vor dem Start im NACHTPLAN prüfen."
        )
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
    agent_limit = ledger.config(provider).get("agent_timeout_minutes", 120) * 60
    timeout = max(1, min(agent_limit, (deadline - datetime.now()).total_seconds()))
    with transcript.open("wb") as stream:
        if use_claude:
            reply = run_claude(args.claude, prompt, HANDOFF_SCHEMA, stream, timeout, claude_execution, ledger)
            answer.write_text(json.dumps(reply, ensure_ascii=False), encoding="utf-8")
        else:
            command = [args.codex, "-a", "never", "exec", "-s", "workspace-write",
                       "--add-dir", str(RESULTS.resolve()), "-C", str(ROOT),
                       "--output-schema", str(schema), "-o", str(answer)]
            if args.codex_json:
                command.append("--json")
            result = subprocess.run(command + ["-"], input=prompt.encode(), cwd=ROOT, env=environment,
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout)
            stream.write(result.stdout)
            text = result.stdout.decode("utf-8", "replace")
            used, resets, output_tokens = scan_codex_events(text)
            ledger.record("codex", output_tokens, 0.0, used)
            config = ledger.config("codex")
            if result.returncode != 0 and LIMIT_TEXT.search(text):
                until = (parse_reset(text) or (datetime.now() + timedelta(seconds=resets) if resets else None)
                         or datetime.now() + timedelta(minutes=config.get("default_cooldown_minutes", 60)))
                raise LimitReached("codex", until, LIMIT_TEXT.search(text).group(0))
            if used is not None and used >= config.get("stop_above_used_percent", 101) and resets:
                ledger.cooldown("codex", datetime.now() + timedelta(seconds=resets))
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


def figure_worker(args, task, deadline, ledger):
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
        reply = run_claude(args.claude, prompt, HANDOFF_SCHEMA, stream, min(remaining, 600), True, ledger)
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
        return window(now, args.first_night, args.nights)
    if now.date() != args.day_until.date() or now >= args.day_until:
        return None
    night = now.date() - timedelta(days=1)
    return (night - args.first_night).days + 1, night, args.day_until


def dispatch(args):
    if git("branch", "--show-current") != BRANCH:
        raise ValueError("Falscher Arbeitszweig")
    seen = set()
    figures_checked = set()
    available = {"codex"} if Path(args.codex).is_file() else set()
    if Path(args.claude).is_file():
        available.add("claude")
    args.codex_json = "codex" in available and codex_supports_json(args.codex)
    suffix = f"_tag_{args.day_until:%Y%m%d}" if args.day_until else ""
    pending = STATE / f"offene_uebergabe{suffix}.txt"
    while (slot := active_window(datetime.now(), args)):
        index, night, deadline = slot
        report = FAMILY / "nights" / f"NACHT_{index}_{night:%Y%m%d}.md"
        rows, approvals, paused = read_queue()
        ledger = Ledger(night, available)
        cutoff = deadline - timedelta(minutes=30 if args.day_until else 90)
        handoff_at = deadline - timedelta(minutes=15) if args.day_until else cutoff
        morning = datetime.now() >= handoff_at
        marker = STATE / f"uebergeben_{night}{suffix}.txt"
        if morning and marker.exists():
            return
        provider = None
        if morning:
            task = "MORGENUEBERGABE"
            provider = ledger.choose(("codex", "claude"), handover=True)
            if provider is None:
                log("Kein Anbieter für die Morgenübergabe verfügbar. " + ledger.summary())
                return
        elif paused:
            log("PAUSE laut STATUS.md")
            return
        else:
            previous = pending.read_text(encoding="ascii") if pending.is_file() else ""
            task = None
            if previous in TASKS and (approved(previous, approvals)
                                      or rows[previous] in ("läuft", "erledigt")):
                provider = ledger.choose(TASKS[previous]["providers"], light=rows[previous] == "läuft")
                if provider:
                    task = previous
            if task is None:
                choice = select(rows, approvals, seen, ledger)
                task, provider = choice if choice else (None, None)
                # A live run gets its monitor check before a figure job.
                if task is None or rows[task] != "läuft":
                    figure = select_figure(rows, figures_checked)
                    if figure and ledger.choose(("claude",)):
                        figures_checked.add(figure)
                        try:
                            figure_worker(args, figure, handoff_at, ledger)
                        except LimitReached as limit:
                            ledger.cooldown(limit.provider, limit.until)
                            log(f"LIMIT {limit}")
                        except Exception:
                            log(f"Abbildungsübergabe für {figure} fehlgeschlagen (Claude)\n" +
                                traceback.format_exc())
                        continue
        if task is None:
            log("Keine weitere freigegebene und mit verfügbarem Kontingent ausführbare Aufgabe. "
                + ledger.summary())
            return
        pending.write_text(task, encoding="ascii")
        try:
            worker(args, task, report, deadline, cutoff, provider, ledger)
        except LimitReached as limit:
            # Kein Fehlschlag der Aufgabe: Anbieter pausieren, Aufgabe bleibt vorgemerkt.
            ledger.cooldown(limit.provider, limit.until)
            log(f"LIMIT {task} {limit}")
            continue
        except Exception:
            if task != "MORGENUEBERGABE":
                ledger.fail(task)
            raise
        if task != "MORGENUEBERGABE":
            ledger.succeed(task)
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
    parser.add_argument("--nights", type=int, default=4, help="Anzahl Kalendernächte ab --first-night")
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
