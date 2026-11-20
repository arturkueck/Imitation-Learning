"""B-1: vorab eingefrorene Pilotauswertung nach PROTOCOL.md §10 (protocol_v1, gültig unter protocol_v2).

Das Skript liest ausschließlich eine Ergebnisdatei im Vertrag ``three_cube_transfer_v1.pilot_outcomes.v1``
(siehe PILOT_ANALYSIS.md) sowie die eingefrorenen Panel-Definitionen (``splits_v3.json``,
``difficulty_panels_v1.json``). Es startet keine Simulation, lädt keine Modelle und führt keine
Optimizerupdates aus. Testfamilien werden abgewiesen, bevor irgendetwas berechnet wird.

Festlegungen (vor Sicht auf Pilotdaten):

* Panels: ``validation_normal`` (100), ``validation_hard`` (50), ``two_cube_validation`` (100), getrennt.
* Fester Checkpoint: Runde 4 (§8). Abgebrochene Läufe gehen mit ihrem letzten ausgewerteten Prüfpunkt
  ein und werden gekennzeichnet (§9). Runde 0 der AC-Arme ist der BC-Wert desselben Parents (§8).
* Primär: AC-IL − AC-neu je Parent auf ``validation_normal``, Mittel über die Parents und Spannweite.
* Sekundär: AC-neu − BC, AC-IL − BC (regulär und schwierig), AC-IL − AC-neu (schwierig),
  Zweierpanel AC − BC.
* Paarung: diskordante Familienpaare je Parent. 95-%-Perzentilintervall aus dem Familienbootstrap
  (2.000 Ziehungen, Seed 7300, Ziehung je Panel einmal, alle Kontraste und Parents eines Panels
  teilen dieselben Ziehungen). Ausdrücklich reine Szenenunsicherheit.
* Effizienz: Schwelle = Parentquote + 10 Prozentpunkte auf ``validation_normal``. Erste Prüfrunde
  mit Quote ≥ Schwelle (Schwelle erreicht). Sonst „> 400“. AC-IL zusätzlich mit 300 Vortrainingsepisoden.
* Keine Signifikanztests, keine p-Werte. Kleinster relevanter Effekt 10 Prozentpunkte nur als Bezug.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np

ANALYSIS_VERSION = "pilot_analysis_v1"
INPUT_SCHEMA = "three_cube_transfer_v1.pilot_outcomes.v1"
HERE = Path(__file__).resolve().parent

ARMS = ("BC", "AC-neu", "AC-IL")
AC_ARMS = ("AC-neu", "AC-IL")
PARENTS = (1, 2, 3)
PANELS = ("validation_normal", "validation_hard", "two_cube_validation")
TEST_SPLITS = ("test_normal", "test_hard")
CHECKPOINT_ROUND = 4
INTERMEDIATE_ROUNDS = (1, 2, 3)
EPISODES_PER_ROUND = 100
PRETRAIN_EPISODES = 300
THRESHOLD_PP = 10            # Effizienzschwelle: Parentquote + 10 Prozentpunkte
MIN_RELEVANT_EFFECT_PP = 10  # kleinster relevanter Effekt im primären Kontrast
BOOTSTRAP_DRAWS = 2000
BOOTSTRAP_SEED = 7300
INTERVAL = 0.95
SCENE_CI_LABEL = "95-%-Familienbootstrap, reine Szenenunsicherheit (deckt keine Streuung durch neues Training ab)"

# Auf welchen Panels und Runden welche Arme ausgewertet werden (§5, §8).
REQUIRED_ROUNDS = {
    ("BC", "validation_normal"): (0,),
    ("BC", "validation_hard"): (0,),
    ("BC", "two_cube_validation"): (0,),
    ("AC", "validation_normal"): (1, 2, 3, 4),
    ("AC", "validation_hard"): (4,),
    ("AC", "two_cube_validation"): (4,),
}

CONTRASTS = (
    # (Name, Panel, Arm a, Arm b, Rolle)
    ("AC-IL − AC-neu", "validation_normal", "AC-IL", "AC-neu", "primär"),
    ("AC-neu − BC", "validation_normal", "AC-neu", "BC", "sekundär"),
    ("AC-IL − BC", "validation_normal", "AC-IL", "BC", "sekundär"),
    ("AC-IL − AC-neu", "validation_hard", "AC-IL", "AC-neu", "sekundär"),
    ("AC-neu − BC", "validation_hard", "AC-neu", "BC", "sekundär"),
    ("AC-IL − BC", "validation_hard", "AC-IL", "BC", "sekundär"),
    ("AC-neu − BC", "two_cube_validation", "AC-neu", "BC", "Zweiererhalt"),
    ("AC-IL − BC", "two_cube_validation", "AC-IL", "BC", "Zweiererhalt"),
)


class ContractError(ValueError):
    """Eingabe verletzt den Ergebnisvertrag (fehlende, doppelte oder fremde Familien, falsche Felder)."""


class TestFamilyError(ContractError):
    """Eingabe enthält eine Testfamilie. Testfamilien bleiben bis zur Öffnung nach MAIN_PROTOCOL.md geschlossen."""

    __test__ = False  # kein pytest-Testfall


def sha256_file(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- Panels

def load_panels(splits_path=HERE / "splits_v3.json", panels_path=HERE / "difficulty_panels_v1.json"):
    """Familienlisten der drei Auswertungspanels und Bereiche der gesperrten Testsplits."""
    splits = {s["id"]: s for s in json.loads(Path(splits_path).read_text(encoding="utf-8"))["splits"]}
    hard = json.loads(Path(panels_path).read_text(encoding="utf-8"))["panels"]["validation_hard"]
    panels = {
        "validation_normal": _range_families(splits["validation_normal"]),
        "validation_hard": tuple(sorted(int(f[0]) for f in hard["families"])),
        "two_cube_validation": _range_families(splits["two_cube_validation"]),
    }
    for name, families in panels.items():
        target = splits[name]["target_families"]
        if len(families) != target or len(set(families)) != target:
            raise ContractError(f"Panel {name}: {len(families)} Familien statt {target}")
    test_ranges = tuple((splits[t]["first"], splits[t]["last"]) for t in TEST_SPLITS)
    return {"families": panels, "test_ranges": test_ranges}


def _range_families(split):
    if split["selection"] != "all":
        raise ContractError(f"Split {split['id']}: Auswahl {split['selection']} nicht als Bereich lesbar")
    return tuple(range(int(split["first"]), int(split["last"]) + 1))


# --------------------------------------------------------------------------- Prüfung der Eingabe

def reject_test_families(data, test_ranges):
    """Bricht ab, sobald irgendeine Szenenkennung der Eingabe in einem Testbereich liegt."""
    for i, row in enumerate(data.get("evaluations", ())):
        seed = row.get("scene_seed")
        if isinstance(seed, int) and any(lo <= seed <= hi for lo, hi in test_ranges):
            raise TestFamilyError(f"evaluations[{i}]: Szenenseed {seed} ist eine Testfamilie")
        if row.get("panel") in TEST_SPLITS:
            raise TestFamilyError(f"evaluations[{i}]: Panel {row.get('panel')} ist gesperrt")


def _run_key(run):
    return run["arm"], int(run["parent"])


def validate(data, panels):
    """Prüft den Vertrag vollständig und liefert Erfolgsvektoren je (Arm, Parent, Panel, Runde)."""
    reject_test_families(data, panels["test_ranges"])
    if data.get("schema") != INPUT_SCHEMA:
        raise ContractError(f"Schema {data.get('schema')!r} statt {INPUT_SCHEMA!r}")

    runs = {}
    for run in data.get("runs", ()):
        key = _run_key(run)
        if key[0] not in AC_ARMS or key[1] not in PARENTS:
            raise ContractError(f"Lauf {key}: unbekannter Arm oder Parent")
        if key in runs:
            raise ContractError(f"Lauf {key} doppelt")
        if run.get("status") not in ("complete", "aborted"):
            raise ContractError(f"Lauf {key}: Status {run.get('status')!r}")
        last = int(run.get("last_evaluated_round", -1))
        if run["status"] == "complete" and last != CHECKPOINT_ROUND:
            raise ContractError(f"Lauf {key}: vollständig, aber letzte Prüfrunde {last}")
        if run["status"] == "aborted" and not 0 <= last < CHECKPOINT_ROUND:
            raise ContractError(f"Lauf {key}: abgebrochen mit unzulässiger letzter Prüfrunde {last}")
        rounds = sorted(int(r["round"]) for r in run.get("rounds", ()))
        if rounds != list(range(1, len(rounds) + 1)) or len(rounds) < last:
            raise ContractError(f"Lauf {key}: Rundenkosten {rounds} passen nicht zur letzten Prüfrunde {last}")
        runs[key] = run
    for arm in AC_ARMS:
        for parent in PARENTS:
            if (arm, parent) not in runs:
                raise ContractError(f"Lauf ({arm}, {parent}) fehlt. Kein Lauf wird ausgeschlossen (§9).")

    cells = {}
    for i, row in enumerate(data.get("evaluations", ())):
        arm, parent, panel = row.get("arm"), row.get("parent"), row.get("panel")
        rnd, seed, success = row.get("round"), row.get("scene_seed"), row.get("success")
        if arm not in ARMS or parent not in PARENTS or panel not in PANELS:
            raise ContractError(f"evaluations[{i}]: Arm {arm!r}, Parent {parent!r} oder Panel {panel!r} unbekannt")
        if not isinstance(rnd, int) or not isinstance(seed, int) or not isinstance(success, bool):
            raise ContractError(f"evaluations[{i}]: round/scene_seed ganzzahlig und success boolesch erwartet")
        cells.setdefault((arm, parent, panel, rnd), {})
        cell = cells[(arm, parent, panel, rnd)]
        if seed in cell:
            raise ContractError(f"evaluations[{i}]: Familie {seed} doppelt in {(arm, parent, panel, rnd)}")
        cell[seed] = success

    outcomes = {}
    for key, cell in cells.items():
        arm, parent, panel, rnd = key
        kind = "BC" if arm == "BC" else "AC"
        allowed = REQUIRED_ROUNDS[(kind, panel)]
        if rnd not in allowed:
            raise ContractError(f"{key}: Runde {rnd} ist für {kind} auf {panel} nicht vorgesehen")
        if kind == "AC" and rnd > int(runs[(arm, parent)]["last_evaluated_round"]):
            raise ContractError(f"{key}: Auswertung nach der letzten Prüfrunde des Laufs")
        families = panels["families"][panel]
        if set(cell) != set(families):
            missing = len(set(families) - set(cell))
            foreign = len(set(cell) - set(families))
            raise ContractError(f"{key}: {missing} fehlende und {foreign} fremde Familien. Vollständiger Nenner nötig.")
        outcomes[key] = np.array([cell[f] for f in families], dtype=bool)

    for parent in PARENTS:
        for panel in PANELS:
            if ("BC", parent, panel, 0) not in outcomes:
                raise ContractError(f"BC-Auswertung Parent {parent} auf {panel} fehlt")
        for arm in AC_ARMS:
            last = int(runs[(arm, parent)]["last_evaluated_round"])
            for rnd in REQUIRED_ROUNDS[("AC", "validation_normal")]:
                if rnd <= last and (arm, parent, "validation_normal", rnd) not in outcomes:
                    raise ContractError(f"{arm} Parent {parent}: Prüfrunde {rnd} auf validation_normal fehlt")
            if last == CHECKPOINT_ROUND:
                for panel in ("validation_hard", "two_cube_validation"):
                    if (arm, parent, panel, CHECKPOINT_ROUND) not in outcomes:
                        raise ContractError(f"{arm} Parent {parent}: Endprüfung auf {panel} fehlt")
    return outcomes, runs


# --------------------------------------------------------------------------- Bausteine

def checkpoint_outcome(outcomes, runs, arm, parent, panel):
    """Erfolgsvektor am festen Checkpoint, bei Abbruch am letzten ausgewerteten Prüfpunkt (§8, §9).

    Runde 0 eines AC-Arms ist der BC-Wert desselben Parents (identischer Actor vor dem ersten Update)."""
    if arm == "BC":
        return outcomes[("BC", parent, panel, 0)], 0
    last = int(runs[(arm, parent)]["last_evaluated_round"])
    for rnd in range(min(last, CHECKPOINT_ROUND), 0, -1):
        if (arm, parent, panel, rnd) in outcomes:
            return outcomes[(arm, parent, panel, rnd)], rnd
    return outcomes[("BC", parent, panel, 0)], 0


def bootstrap_indices(n_families, draws=BOOTSTRAP_DRAWS, seed=BOOTSTRAP_SEED):
    """Feste Familienziehungen eines Panels: Matrix draws × n mit Indizes, mit Zurücklegen."""
    return np.random.default_rng(seed).integers(0, n_families, size=(draws, n_families))


def percentile_interval(values, level=INTERVAL):
    lo, hi = np.quantile(np.asarray(values, dtype=np.float64), [(1 - level) / 2, (1 + level) / 2])
    return [float(lo), float(hi)]


def discordant(a, b):
    """Diskordante Familienpaare: nur a erfolgreich, nur b erfolgreich."""
    return {"only_a": int(np.sum(a & ~b)), "only_b": int(np.sum(~a & b)),
            "both": int(np.sum(a & b)), "neither": int(np.sum(~a & ~b))}


def reaches_threshold(k_ac, n_ac, k_parent, n_parent, threshold_pp=THRESHOLD_PP):
    """k_ac/n_ac ≥ k_parent/n_parent + threshold_pp/100, ganzzahlig ohne Rundungsfehler."""
    return 100 * k_ac * n_parent >= (100 * k_parent + threshold_pp * n_parent) * n_ac


# --------------------------------------------------------------------------- Analyse

def analyze(data, panels):
    outcomes, runs = validate(data, panels)
    result = {
        "analysis_version": ANALYSIS_VERSION,
        "input_schema": INPUT_SCHEMA,
        "evaluation_scope": "nur Validierung, Testfamilien geschlossen",
        "panel_sizes": {p: len(panels["families"][p]) for p in PANELS},
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED, "interval": INTERVAL,
                      "unit": "Familie, gemeinsame Ziehung je Panel für alle Arme und Parents",
                      "label": SCENE_CI_LABEL},
        "shared_scenes": "Die drei Parents teilen Validierungs-, Online- und Critic-Datenfamilien. "
                         "Parents sind getrennte Lernverläufe, Szenen sind keine unabhängigen Wiederholungen.",
        "min_relevant_effect_pp": MIN_RELEVANT_EFFECT_PP,
        "significance_tests": "keine (drei Seeds erlauben keinen Bestätigungsschluss)",
    }

    rates = []
    vectors = {}
    for panel in PANELS:
        for parent in PARENTS:
            for arm in ARMS:
                vec, rnd = checkpoint_outcome(outcomes, runs, arm, parent, panel)
                vectors[(arm, parent, panel)] = vec
                aborted = arm != "BC" and runs[(arm, parent)]["status"] == "aborted"
                rates.append({"arm": arm, "parent": parent, "panel": panel, "k": int(vec.sum()),
                              "n": int(vec.size), "rate": float(vec.mean()), "checkpoint_round": rnd,
                              "aborted": aborted,
                              "round0_is_bc": arm != "BC" and rnd == 0})
    result["rates"] = rates

    contrasts = []
    for name, panel, arm_a, arm_b, role in CONTRASTS:
        idx = bootstrap_indices(len(panels["families"][panel]))
        per_parent, boot_by_parent = [], []
        for parent in PARENTS:
            a, b = vectors[(arm_a, parent, panel)], vectors[(arm_b, parent, panel)]
            diff_vec = a.astype(np.float64) - b.astype(np.float64)
            boot = diff_vec[idx].mean(axis=1)
            boot_by_parent.append(boot)
            per_parent.append({"parent": parent, "k_a": int(a.sum()), "k_b": int(b.sum()), "n": int(a.size),
                               "difference": float(diff_vec.mean()), "discordant": discordant(a, b),
                               "scene_ci95": percentile_interval(boot)})
        diffs = [p["difference"] for p in per_parent]
        mean_boot = np.mean(boot_by_parent, axis=0)
        contrasts.append({
            "name": name, "panel": panel, "arm_a": arm_a, "arm_b": arm_b, "role": role,
            "per_parent": per_parent,
            "mean_over_parents": float(np.mean(diffs)),
            "mean_scene_ci95": percentile_interval(mean_boot),
            "min": float(min(diffs)), "max": float(max(diffs)), "spread": float(max(diffs) - min(diffs)),
            "ci_label": SCENE_CI_LABEL,
            "any_aborted": any(runs[(arm, p)]["status"] == "aborted"
                               for arm in (arm_a, arm_b) if arm != "BC" for p in PARENTS),
        })
    result["contrasts"] = contrasts

    curves, efficiency, collapse = [], [], []
    for arm in AC_ARMS:
        for parent in PARENTS:
            run = runs[(arm, parent)]
            last = int(run["last_evaluated_round"])
            bc = outcomes[("BC", parent, "validation_normal", 0)]
            k_bc, n_bc = int(bc.sum()), int(bc.size)
            points = [{"round": 0, "k": k_bc, "n": n_bc, "source": "BC (§8, Runde 0)"}]
            for rnd in range(1, last + 1):
                vec = outcomes[(arm, parent, "validation_normal", rnd)]
                points.append({"round": rnd, "k": int(vec.sum()), "n": int(vec.size), "source": arm})
            curves.append({"arm": arm, "parent": parent, "aborted": run["status"] == "aborted", "points": points})

            for pt in points[1:]:
                if pt["round"] in INTERMEDIATE_ROUNDS and 2 * pt["k"] * n_bc <= k_bc * pt["n"]:
                    collapse.append({"arm": arm, "parent": parent, "round": pt["round"],
                                     "k": pt["k"], "n": pt["n"], "parent_k": k_bc, "parent_n": n_bc})

            cost_rounds = {int(r["round"]): r for r in run["rounds"]}
            reached = None
            for pt in points[1:]:
                if reaches_threshold(pt["k"], pt["n"], k_bc, n_bc):
                    reached = pt["round"]
                    break
            entry = {"arm": arm, "parent": parent, "parent_k": k_bc, "parent_n": n_bc,
                     "threshold_rate": k_bc / n_bc + THRESHOLD_PP / 100, "reached_round": reached,
                     "aborted": run["status"] == "aborted"}
            if reached is None:
                done = sum(int(cost_rounds[r]["online_episodes"]) for r in range(1, last + 1))
                planned = CHECKPOINT_ROUND * EPISODES_PER_ROUND
                entry["online_episodes"] = f"> {planned}" if run["status"] == "complete" else f"> {done} (abgebrochen)"
                entry["online_frames"] = None
            else:
                entry["online_episodes"] = sum(int(cost_rounds[r]["online_episodes"]) for r in range(1, reached + 1))
                entry["online_frames"] = sum(int(cost_rounds[r]["online_frames"]) for r in range(1, reached + 1))
            if arm == "AC-IL":
                pre_ep = int(run.get("pretrain_episodes", PRETRAIN_EPISODES))
                pre_fr = run.get("pretrain_frames")
                if reached is None:
                    entry["with_pretrain_episodes"] = (f"> {CHECKPOINT_ROUND * EPISODES_PER_ROUND + pre_ep}"
                                                       if run["status"] == "complete" else
                                                       f"> {done + pre_ep} (abgebrochen)")
                    entry["with_pretrain_frames"] = None
                else:
                    entry["with_pretrain_episodes"] = entry["online_episodes"] + pre_ep
                    entry["with_pretrain_frames"] = (None if pre_fr is None
                                                     else entry["online_frames"] + int(pre_fr))
            efficiency.append(entry)
    result["learning_curves"] = curves
    result["efficiency"] = efficiency
    result["collapse_flags"] = {"rule": "Zwischenprüfung Runde 1–3: Quote ≤ halbe Parentquote (§8), berichtend",
                                "hits": collapse}

    cost_fields = ("online_episodes", "online_frames", "critic_updates", "actor_updates")
    costs = []
    for arm in AC_ARMS:
        for parent in PARENTS:
            run = runs[(arm, parent)]
            row = {"arm": arm, "parent": parent, "status": run["status"]}
            for field in cost_fields:
                row[field] = sum(int(r[field]) for r in run["rounds"])
            row["pretrain_episodes"] = int(run.get("pretrain_episodes", 0))
            row["pretrain_frames"] = run.get("pretrain_frames")
            row["pretrain_updates"] = int(run.get("pretrain_updates", 0))
            row["eval_episodes"] = int(run.get("eval_episodes", 0))
            row["runtime_s"] = float(run.get("runtime_s", math.nan))
            costs.append(row)
    result["costs"] = costs
    return result


# --------------------------------------------------------------------------- Ausgabe

def _pct(x):
    return f"{100 * x:+.1f}"


def render_markdown(result):
    lines = [f"# Pilotauswertung ({result['analysis_version']})", "",
             f"Umfang: {result['evaluation_scope']}. Keine Signifikanztests. {result['shared_scenes']}", "",
             "## Erfolg am festen Checkpoint", "", "| Panel | Parent | Arm | k/n | Runde | Hinweis |",
             "|---|---|---|---|---|---|"]
    for r in result["rates"]:
        note = "abgebrochen" if r["aborted"] else ""
        lines.append(f"| {r['panel']} | {r['parent']} | {r['arm']} | {r['k']}/{r['n']} | {r['checkpoint_round']} | {note} |")
    lines += ["", "## Kontraste (Prozentpunkte)", "", f"Intervalle: {result['bootstrap']['label']}.", "",
              "| Rolle | Panel | Kontrast | Parent 1 | Parent 2 | Parent 3 | Mittel [KI] | Spannweite |",
              "|---|---|---|---|---|---|---|---|"]
    for c in result["contrasts"]:
        cells = [f"{_pct(p['difference'])} ({p['discordant']['only_a']}:{p['discordant']['only_b']})"
                 for p in c["per_parent"]]
        lo, hi = c["mean_scene_ci95"]
        lines.append(f"| {c['role']} | {c['panel']} | {c['name']} | " + " | ".join(cells)
                     + f" | {_pct(c['mean_over_parents'])} [{_pct(lo)}; {_pct(hi)}] | {100 * c['spread']:.1f} |")
    lines += ["", "In Klammern je Parent: diskordante Familien (nur a : nur b).", "",
              "## Effizienz (Schwelle Parentquote + 10 Prozentpunkte)", "",
              "| Arm | Parent | Schwelle | Runde | Onlineepisoden | Frames | mit Vortraining |", "|---|---|---|---|---|---|---|"]
    for e in result["efficiency"]:
        pre = e.get("with_pretrain_episodes", "–")
        lines.append(f"| {e['arm']} | {e['parent']} | {100 * e['threshold_rate']:.0f} % | {e['reached_round'] or '–'} | "
                     f"{e['online_episodes']} | {e['online_frames'] if e['online_frames'] is not None else '–'} | {pre} |")
    hits = result["collapse_flags"]["hits"]
    lines += ["", f"Zusammenbruchsmarken (berichtend): {len(hits)}", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("analyze", help="Ergebnisdatei nach §10 auswerten")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--markdown", type=Path)
    run.add_argument("--splits", type=Path, default=HERE / "splits_v3.json")
    run.add_argument("--panels", type=Path, default=HERE / "difficulty_panels_v1.json")
    sub.add_parser("hash", help="SHA-256 dieses Skripts ausgeben")
    args = parser.parse_args(argv)
    if args.command == "hash":
        print(sha256_file(__file__))
        return 0
    panels = load_panels(args.splits, args.panels)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(data, panels)
    result["script_sha256"] = sha256_file(__file__)
    result["input_sha256"] = sha256_file(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(render_markdown(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
