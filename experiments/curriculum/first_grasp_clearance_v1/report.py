"""Generate a decision report even if only part of the fixed plan finished."""
from collections import Counter, defaultdict
from datetime import datetime, timezone, timedelta
import json

import numpy as np


def read(path, default=None):
    if not path.is_file():
        return default
    return json.loads(path.read_text(encoding="utf-8"))


def pair(rows, reference, arm):
    pairs = [(r["arms"][reference], r["arms"][arm]) for r in rows if arm in r["arms"]]
    return dict(n=len(pairs), before=sum(a["success"] for a, b in pairs),
        after=sum(b["success"] for a, b in pairs),
        gains=sum(not a["success"] and b["success"] for a, b in pairs),
        losses=sum(a["success"] and not b["success"] for a, b in pairs),
        exposed=sum(b["withdrawal"] is not None if arm == "withdraw" else
                    b["first_change"] is not None for a, b in pairs),
        exits_before=sum((a["final_stage"], a["final_phase"]) != (1, 1) for a, b in pairs),
        exits_after=sum((b["final_stage"], b["final_phase"]) != (1, 1) for a, b in pairs))


def inspect_release(out, case, fields):
    data = {}
    for arm in ("guarded_feedback", "withdraw"):
        with np.load(out / "main" / "traces" / f'{case["id"]}_{arm}.npz') as archive:
            trace = archive["trace"]
        final = trace[-1]
        data[arm] = dict(final_xy_mm=1000 * float(final[fields["post_xy"]]),
            final_finger=int(final[fields["post_source_finger"]]),
            final_z_m=float(final[fields["eef_z"]]),
            max_valid_frames=int(trace[:, fields["valid_tail"]].max()))
    return data


def generate(out, final):
    planned = read(out / "plan.json")
    groups = read(out / "main/groups.json", [])
    selection = read(out / "main/screen_selection.json", {})
    screening = read(out / "main/screening.json", [])
    integrity = read(out / "main/integrity.json", {})
    smoke = read(out / "smoke/integrity.json", {})
    n_episodes = sum(len(g["arms"]) for g in groups) + len(screening)
    if final["state"] == "COMPLETE":
        selected = selection["selected"]
        if (len(screening) != len(planned["screen_seeds"])
                or len(groups) != len(planned["cases"]) + 3 * len(selected)
                or n_episodes != 438 + 9 * len(selected) or integrity["episodes"] != n_episodes):
            raise ValueError("Completed status fails planned coverage check")
    panels = defaultdict(list)
    for group in groups:
        panels[group["case"]["panel"]].append(group)
    def stamp(epoch):
        return datetime.fromtimestamp(epoch, timezone(timedelta(hours=1))).strftime("%H:%M:%S")
    lines = [
        "# Abschlussbericht · Erster Griff und Rückzug nach dem Öffnen", "",
        f"**{final['state']}** · 18.11.2026, {stamp(final['started'])} bis "
        f"{stamp(final['finished'])} Uhr (Europe/Berlin).",
        f"Techniktest {smoke.get('episodes', 0)} Episoden. Hauptlauf **{n_episodes} Episoden** "
        f"in {len(groups)} Vergleichsgruppen und {len(screening)} Sichtungsläufen. "
        "Drei eingefrorene Modelllinien und null Lernupdates.", "",
        "Vollständiger Erfolg verlangt einen Dreierturm über 50 strenge Frames. "
        "Die Vergleiche zählen jede geplante Gruppe, auch wenn der Eingriff nie ausgelöst wurde.", "",
    ]
    if final.get("error"):
        lines.extend([f"**Abbruchgrund** {final['error']}", "",
            "Die folgende Tabelle beschreibt ausschließlich vollständig geprüfte Paargruppen. "
            "Details stehen in worker.log und status.json.", ""])
    labels = {
        "known_grasp_failure": "Geöffnete erste Griffstillstände",
        "known_grasp_success": "Geöffnete Grifferfolge",
        "normal": "Neue normale Familien",
        "critical": "Neue kritisch gesichtete Familien",
        "known_release_failure": "Geöffnete Freigabefehler",
        "known_release_success_control": "Geöffnete Freigabe-Erfolge",
    }
    labels_arm = {"grasp_timeout": "Griff-Timeout", "grasp_ready": "Späte Griffbereitschaft",
                  "withdraw": "Rückzug nach Objektfeedback"}
    mark = (
        "Gewinn bedeutet Erfolg nur mit dem Eingriff. Verlust bedeutet Erfolg nur in der Bezugskontrolle. "
        "Der Rückzug wird mit Objektfeedback und anschließendem Halten verglichen."
    )
    lines.extend([mark, "", "| Panel | Regel | Paare | Erfolge Bezug → Variante | Gewinne | Verluste | Eingriffe |",
                 "|---|---|---:|---:|---:|---:|---:|"])
    outcomes = {}
    for panel, rows in panels.items():
        outcomes[panel] = {}
        for ref, arm in (("control", "grasp_timeout"), ("control", "grasp_ready"),
                         ("guarded_feedback", "withdraw")):
            result = pair(rows, ref, arm)
            if not result["n"]:
                continue
            by_parent = {m: pair([r for r in rows if r["case"]["model"] == m], ref, arm)
                         for m in sorted({r["case"]["model"] for r in rows})}
            outcomes[panel][arm] = dict(result, by_parent=by_parent)
            lines.append(f"| {labels[panel]} | {labels_arm[arm]} | {result['n']} | "
                         f"{result['before']} → {result['after']} | {result['gains']} | "
                         f"{result['losses']} | {result['exposed']} |")
    n_eligible = sum(bool(r["screen_eligible"]) for r in screening)
    lines.extend(["", "## Erster Griff", "",
        f"Die unveränderte Referenz endete bei {sum((r['final_stage'], r['final_phase']) == (1, 1) for r in screening)} "
        f"von {len(screening)} gesichteten Familien beim ersten Absenken. "
        f"Davon erfüllten {n_eligible} die vorher festgelegte Bereitschaftsbedingung. "
        f"Das kritische Panel umfasst {len(selection.get('selected', []))} dieser Familien. "
        "Die Selektionsreferenz und die anderen beiden Modelllinien werden einzeln ausgewiesen.", "",
        "| Panel | Modelllinie | Regel | Paare | Gewinne / Verluste | Eingriffe |",
        "|---|---|---|---:|---:|---:|"])
    for panel in ("normal", "critical"):
        for arm, result in outcomes.get(panel, {}).items():
            for model, b in result["by_parent"].items():
                if b["n"]:
                    lines.append(f"| {labels[panel]} | {model} | {labels_arm[arm]} | {b['n']} | "
                                 f"{b['gains']} / {b['losses']} | {b['exposed']} |")
    known = outcomes.get("known_grasp_failure", {})
    if known.get("grasp_ready"):
        for arm in ("grasp_timeout", "grasp_ready"):
            b = known[arm]
            lines.extend(["", f"{labels_arm[arm]} verlässt den bekannten Stillstand in "
                f"{b['exits_after']} von {b['n']} Paaren. Vollständig gelingen {b['after']} Aufgaben."])
    lines.extend(["", "## Rückzug nach dem Öffnen", ""])
    critical_anchor = next((g for g in groups if g["case"]["id"] == "release_g16_failure"), None)
    terminal = None
    if critical_anchor:
        columns = {n: i for i, n in enumerate(read(out / "trace_schema.json"))}
        terminal = inspect_release(out, critical_anchor["case"], columns)
        trigger = critical_anchor["arms"]["withdraw"]["withdrawal"]
        if trigger is not None:
            lines.append(f"Im früheren Kontaktfall (Szene 2026189042, Modelllinie 3) "
                         f"wurde der Rückzug nach {trigger['age']} Freigabeschritten ausgelöst.")
        else:
            lines.append("Im früheren Kontaktfall wurde die Rückzugsregel nicht ausgelöst.")
        lines.extend(["", "| Regel | XY am Ende | Fingerkontakt am Ende | Längste gültige Folge |",
                      "|---|---:|---|---:|"])
        for arm, label in (("guarded_feedback", "Halten"), ("withdraw", "Rückzug")):
            b = terminal[arm]
            lines.append(f"| {label} | {b['final_xy_mm']:.2f} mm | "
                         f"{'ja' if b['final_finger'] else 'nein'} | {b['max_valid_frames']}/50 |")
    else:
        lines.append("Der Referenzfall war bei Abschluss des Prozesses noch nicht vollständig ausgewertet.")
    lines.extend(["", "## Folgerung für den Lernvergleich", ""])
    fresh = outcomes.get("critical", {}).get("grasp_ready", {})
    fresh_gain_families = sorted({g["case"]["seed"] for g in panels.get("critical", [])
        if g["arms"]["grasp_ready"]["success"] and not g["arms"]["control"]["success"]})
    normal_losses = outcomes.get("normal", {}).get("grasp_ready", {}).get("losses", 0)
    if final["state"] != "COMPLETE":
        lines.append("Die Lernentscheidung bleibt bis zur vollständigen Prüfung offen.")
    elif fresh.get("exposed", 0) and len(fresh_gain_families) >= 2 and not normal_losses:
        lines.append(f"Die Bereitschaftsregel rettet Aufgaben aus {len(fresh_gain_families)} neuen kritischen "
            "Familien. Das stützt den vorbereiteten Vergleich einer gezielten und einer zufälligen "
            "Expertenabfrage bei gleichem Budget. Der nächste Schritt ist ein eigenes Lernprotokoll "
            "mit unabhängigen Trainingsseeds und gesperrtem Blindtest.")
    else:
        lines.append("Die Prüfung liefert noch keinen hinreichend breiten Nachweis, um den "
            "vorbereiteten BC-Vergleich direkt zu starten. Entscheidend sind die Zahl neuer Familien "
            "mit Rettungen, die Auslösung und die Verluste auf normalen Szenen.")
    lines.extend(["",
        "Die gezielt gesichteten Fälle erlauben eine Aussage über den Fehlermechanismus in diesen "
        "Zuständen. Die gemeinsame Nutzung von Szenen und Modelllinien begrenzt Aussagen über "
        "neue Trainingsinitialisierungen. Normale und kritische Familien bleiben Entwicklungsdaten.", "",
        "Die Abschlussprüfung umfasst die archivierten Kontrollen, die identische Historie bis zum "
        "jeweiligen Eingriff, Initialzustände, die Parameter und die Zahl der vollständigen Episoden. "
        "Fallausgänge, Sichtung, Traces und Integritätsnachweise liegen im Laufordner.", ""])
    summary = dict(episodes=n_episodes, groups=len(groups), screening=len(screening), outcomes=outcomes,
        selected=selection, fresh_grasp_gain_families=fresh_gain_families,
        screening_endpoints=dict(Counter(f"{r['final_stage']}/{r['final_phase']}" for r in screening)),
        terminal_anchor=terminal, integrity=integrity, smoke=smoke)
    (out / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (out / "ABSCHLUSSBERICHT.md").write_text("\n".join(lines), encoding="utf-8")
