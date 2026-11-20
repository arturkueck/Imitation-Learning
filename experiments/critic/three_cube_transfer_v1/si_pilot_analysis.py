"""S-0: vorab eingefrorene Pilotauswertung der Selbstimitation nach PROTOCOL_V3.md §7 (protocol_v3).

Das Skript liest ausschließlich eine Ergebnisdatei im Vertrag ``three_cube_transfer_v1.si_pilot_outcomes.v1``
(siehe SI_PILOT_ANALYSIS.md) sowie die eingefrorenen Panel-Definitionen (``splits_v3.json``,
``difficulty_panels_v1.json``). Es startet keine Simulation, lädt keine Modelle und führt keine
Optimizerupdates aus. Testfamilien werden abgewiesen, bevor irgendetwas berechnet wird.

Übertragen aus ``pilot_analysis.py`` (B-1, ``pilot_analysis_v1``), dessen SHA-256 vor jeder Rechnung
geprüft wird: Panels, Testfamilienabweisung, Familienbootstrap (2.000 Ziehungen, Seed 7300, eine Ziehung
je Panel für alle Arme und Parents), Perzentilintervall und diskordante Paare. Neu gegenüber B-1:

* Arme BC, SI-E, SI-K (v3 §2). Fester Checkpoint nach 5.000 Updates, keine Runden, keine Auswahl.
* Primär (SI-005a): SI-K − SI-E je Parent auf ``validation_normal``, Mittel über die drei Parents.
* Sekundär: SI-E − BC (SI-005b) und SI-K − BC auf ``validation_normal``; alle drei Kontraste getrennt
  auf ``validation_hard``. Zweiererhalt SI-E − BC und SI-K − BC auf ``two_cube_validation`` mit der
  berichtenden Nebenbedingung „Abfall um mehr als 10 Prozentpunkte“.
* Datenmengen je Arm und Parent, Kosten (Pool-, Update- und Auswertungszeit) getrennt.
* BC-Werte auf der Validierung stammen aus N2-2; die Determinismusprüfung (10 Familien je Parent)
  wird berichtet und nicht zur Auswahl verwendet.
* Eingaben für ``seed_count.py`` (B-3) mit kleinstem relevantem Effekt +5 Prozentpunkte.
* Keine Signifikanztests, keine p-Werte.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_analysis as b1  # noqa: E402  (eingefroren, SHA wird geprüft)

ANALYSIS_VERSION = "si_pilot_analysis_v1"
INPUT_SCHEMA = "three_cube_transfer_v1.si_pilot_outcomes.v1"
B1_SHA256 = "ad7d627422e99c2f19eb36c7214e3c1dd7b5fe0ccd1dd0d7bbbc6d15be0f18a2"

ARMS = ("BC", "SI-E", "SI-K")
SI_ARMS = ("SI-E", "SI-K")
PARENTS = b1.PARENTS
PANELS = b1.PANELS
CHECKPOINT_UPDATES = 5000
MINIBATCH_SEED_BASE = 7700
DEMO_FRACTION = 0.5
POOL_EPISODES = 1200
DETERMINISM_FAMILIES = 10
DETERMINISM_PANELS = ("validation_normal", "validation_hard")
TWO_CUBE_DROP_PP = 10        # Nebenbedingung: Abfall um mehr als 10 Prozentpunkte (berichtend)
MIN_RELEVANT_EFFECT_PP = 5   # v3 §7: kleinster relevanter Effekt für den Hauptvergleich
GATE_FRAME_RATIO = 1.10      # v3 §4, nur zur Berichtsprüfung
GATE_MIN_FAMILIES = 10
BOOTSTRAP_DRAWS = b1.BOOTSTRAP_DRAWS
BOOTSTRAP_SEED = b1.BOOTSTRAP_SEED
SCENE_CI_LABEL = b1.SCENE_CI_LABEL
HEX64 = re.compile(r"^[0-9a-f]{64}$")

ContractError = b1.ContractError
TestFamilyError = b1.TestFamilyError

CONTRASTS = (
    # (Name, Panel, Arm a, Arm b, Rolle)
    ("SI-K − SI-E", "validation_normal", "SI-K", "SI-E", "primär (SI-005a)"),
    ("SI-E − BC", "validation_normal", "SI-E", "BC", "sekundär (SI-005b)"),
    ("SI-K − BC", "validation_normal", "SI-K", "BC", "sekundär, berichtend"),
    ("SI-K − SI-E", "validation_hard", "SI-K", "SI-E", "sekundär, schwierig"),
    ("SI-E − BC", "validation_hard", "SI-E", "BC", "sekundär, schwierig"),
    ("SI-K − BC", "validation_hard", "SI-K", "BC", "sekundär, schwierig"),
    ("SI-E − BC", "two_cube_validation", "SI-E", "BC", "Zweiererhalt"),
    ("SI-K − BC", "two_cube_validation", "SI-K", "BC", "Zweiererhalt"),
)

RUN_INT_FIELDS = ("updates", "minibatch_seed", "demo_frames", "self_success_episodes", "self_success_frames",
                  "prefix_episodes", "prefix_families", "prefix_frames", "eval_episodes")
RUN_FLOAT_FIELDS = ("update_runtime_s", "eval_runtime_s")


def check_b1_frozen(path=HERE / "pilot_analysis.py"):
    """Die übernommenen Bausteine stammen aus der eingefrorenen B-1-Version."""
    actual = b1.sha256_file(path)
    if actual != B1_SHA256:
        raise ContractError(f"pilot_analysis.py hat SHA-256 {actual}, eingefroren ist {B1_SHA256}")
    return actual


def load_panels(splits_path=HERE / "splits_v3.json", panels_path=HERE / "difficulty_panels_v1.json"):
    return b1.load_panels(splits_path, panels_path)


# --------------------------------------------------------------------------- Prüfung der Eingabe

def _is_int(x):
    return isinstance(x, int) and not isinstance(x, bool)


def _is_num(x):
    return (isinstance(x, (int, float)) and not isinstance(x, bool)) and math.isfinite(x)


def reject_test_families(data, test_ranges):
    """Wie B-1, zusätzlich für die Familien der Determinismusprüfung."""
    b1.reject_test_families(data, test_ranges)
    b1.reject_test_families({"evaluations": data.get("bc_determinism", ())}, test_ranges)


def _validate_runs(data):
    runs = {}
    for run in data.get("runs", ()):
        arm, parent = run.get("arm"), run.get("parent")
        key = (arm, parent)
        if arm not in SI_ARMS or parent not in PARENTS:
            raise ContractError(f"Lauf {key}: unbekannter Arm oder Parent")
        if key in runs:
            raise ContractError(f"Lauf {key} doppelt")
        if run.get("status") != "complete":
            raise ContractError(f"Lauf {key}: Status {run.get('status')!r}. Ohne vollständigen Lauf gibt es keinen "
                                "festen Checkpoint. Kein stiller Ausschluss, der Nutzer entscheidet (v3 §5).")
        for field in RUN_INT_FIELDS:
            if not _is_int(run.get(field)) or run[field] < 0:
                raise ContractError(f"Lauf {key}: {field} muss eine nichtnegative ganze Zahl sein")
        for field in RUN_FLOAT_FIELDS:
            if run.get(field) is not None and (not _is_num(run[field]) or run[field] < 0):
                raise ContractError(f"Lauf {key}: {field} muss endlich und nichtnegativ sein oder fehlen")
        if run["updates"] != CHECKPOINT_UPDATES:
            raise ContractError(f"Lauf {key}: {run['updates']} Updates statt {CHECKPOINT_UPDATES} (fester Checkpoint)")
        if run["minibatch_seed"] != MINIBATCH_SEED_BASE + parent:
            raise ContractError(f"Lauf {key}: Minibatch-Seed {run['minibatch_seed']} statt {MINIBATCH_SEED_BASE + parent}")
        if run.get("demo_fraction") != DEMO_FRACTION:
            raise ContractError(f"Lauf {key}: Zweieranteil {run.get('demo_fraction')!r} statt {DEMO_FRACTION}")
        for field in ("checkpoint_sha256", "selection_sha256"):
            if not isinstance(run.get(field), str) or not HEX64.match(run[field]):
                raise ContractError(f"Lauf {key}: {field} ist kein SHA-256")
        if arm == "SI-E" and (run["prefix_episodes"] or run["prefix_families"] or run["prefix_frames"]):
            raise ContractError(f"Lauf {key}: SI-E enthält keine Präfixe gescheiterter Episoden (v3 §2)")
        if run["prefix_families"] > run["prefix_episodes"]:
            raise ContractError(f"Lauf {key}: mehr Präfixfamilien als Präfixepisoden")
        runs[key] = run
    for parent in PARENTS:
        for arm in SI_ARMS:
            if (arm, parent) not in runs:
                raise ContractError(f"Lauf ({arm}, {parent}) fehlt. Kein Lauf wird ausgeschlossen.")
        e, k = runs[("SI-E", parent)], runs[("SI-K", parent)]
        for field in ("self_success_episodes", "self_success_frames", "selection_sha256"):
            if e[field] != k[field]:
                raise ContractError(f"Parent {parent}: {field} unterscheidet sich zwischen SI-E und SI-K. "
                                    "Beide Arme nutzen dieselben erfolgreichen Episoden desselben Pools (v3 §2).")
        if e["checkpoint_sha256"] == k["checkpoint_sha256"]:
            raise ContractError(f"Parent {parent}: SI-E und SI-K haben denselben Checkpoint")
    return runs


def _validate_pool(data):
    pool = data.get("pool")
    if not isinstance(pool, dict):
        raise ContractError("Angabe pool fehlt")
    if pool.get("episodes") != POOL_EPISODES:
        raise ContractError(f"Pool mit {pool.get('episodes')!r} statt {POOL_EPISODES} Episoden (v3 §3)")
    if not _is_int(pool.get("frames")) or pool["frames"] <= 0:
        raise ContractError("pool.frames muss eine positive ganze Zahl sein")
    if pool.get("runtime_s") is not None and (not _is_num(pool["runtime_s"]) or pool["runtime_s"] < 0):
        raise ContractError("pool.runtime_s muss endlich und nichtnegativ sein oder fehlen")
    return pool


def validate(data, panels):
    """Prüft den Vertrag vollständig und liefert Erfolgsvektoren je (Arm, Parent, Panel)."""
    reject_test_families(data, panels["test_ranges"])
    if data.get("schema") != INPUT_SCHEMA:
        raise ContractError(f"Schema {data.get('schema')!r} statt {INPUT_SCHEMA!r}")
    runs = _validate_runs(data)
    pool = _validate_pool(data)

    cells = {}
    for i, row in enumerate(data.get("evaluations", ())):
        arm, parent, panel = row.get("arm"), row.get("parent"), row.get("panel")
        seed, success = row.get("scene_seed"), row.get("success")
        if arm not in ARMS or parent not in PARENTS or panel not in PANELS:
            raise ContractError(f"evaluations[{i}]: Arm {arm!r}, Parent {parent!r} oder Panel {panel!r} unbekannt")
        if "round" in row:
            raise ContractError(f"evaluations[{i}]: v3 kennt keine Prüfrunden, nur den festen Checkpoint")
        if not _is_int(seed) or not isinstance(success, bool):
            raise ContractError(f"evaluations[{i}]: scene_seed ganzzahlig und success boolesch erwartet")
        cell = cells.setdefault((arm, parent, panel), {})
        if seed in cell:
            raise ContractError(f"evaluations[{i}]: Familie {seed} doppelt in {(arm, parent, panel)}")
        cell[seed] = success

    outcomes = {}
    for arm in ARMS:
        for parent in PARENTS:
            for panel in PANELS:
                key = (arm, parent, panel)
                if key not in cells:
                    raise ContractError(f"Auswertung {key} fehlt")
                families = panels["families"][panel]
                cell = cells[key]
                if set(cell) != set(families):
                    missing = len(set(families) - set(cell))
                    foreign = len(set(cell) - set(families))
                    raise ContractError(f"{key}: {missing} fehlende und {foreign} fremde Familien. "
                                        "Vollständiger Nenner nötig.")
                outcomes[key] = np.array([cell[f] for f in families], dtype=bool)

    determinism = _validate_determinism(data, panels, cells)
    return outcomes, runs, pool, determinism


def _validate_determinism(data, panels, cells):
    """Determinismusprüfung der BC-Werte aus N2-2 (v3 §5, S-5): genau 10 Familien je Parent."""
    by_parent = {p: {} for p in PARENTS}
    for i, row in enumerate(data.get("bc_determinism", ())):
        parent, panel, seed = row.get("parent"), row.get("panel"), row.get("scene_seed")
        old, new = row.get("n2_2_success"), row.get("rerun_success")
        if parent not in PARENTS or panel not in DETERMINISM_PANELS:
            raise ContractError(f"bc_determinism[{i}]: Parent {parent!r} oder Panel {panel!r} unzulässig")
        if not _is_int(seed) or not isinstance(old, bool) or not isinstance(new, bool):
            raise ContractError(f"bc_determinism[{i}]: scene_seed ganzzahlig, Ausgänge boolesch erwartet")
        if seed not in panels["families"][panel]:
            raise ContractError(f"bc_determinism[{i}]: Familie {seed} gehört nicht zu {panel}")
        if (panel, seed) in by_parent[parent]:
            raise ContractError(f"bc_determinism[{i}]: Familie {seed} doppelt für Parent {parent}")
        if cells[("BC", parent, panel)][seed] != old:
            raise ContractError(f"bc_determinism[{i}]: n2_2_success widerspricht dem BC-Wert in evaluations")
        by_parent[parent][(panel, seed)] = (old, new)
    result = []
    for parent in PARENTS:
        rows = by_parent[parent]
        if len(rows) != DETERMINISM_FAMILIES:
            raise ContractError(f"bc_determinism: Parent {parent} hat {len(rows)} statt {DETERMINISM_FAMILIES} Familien")
        mismatches = sorted([seed for (panel, seed), (old, new) in rows.items() if old != new])
        result.append({"parent": parent, "families": len(rows), "matches": len(rows) - len(mismatches),
                       "mismatch_families": mismatches})
    return result


# --------------------------------------------------------------------------- Bausteine

def two_cube_drop_exceeded(k_arm, k_bc, n, drop_pp=TWO_CUBE_DROP_PP):
    """Fällt der Arm um mehr als drop_pp Prozentpunkte unter BC? Ganzzahlig ohne Rundungsfehler."""
    return 100 * (k_bc - k_arm) > drop_pp * n


# --------------------------------------------------------------------------- Analyse

def analyze(data, panels):
    b1_sha = check_b1_frozen()
    outcomes, runs, pool, determinism = validate(data, panels)
    result = {
        "analysis_version": ANALYSIS_VERSION,
        "input_schema": INPUT_SCHEMA,
        "protocol": "protocol_v3 §7",
        "inherited_from": {"script": "pilot_analysis.py", "version": b1.ANALYSIS_VERSION, "sha256": b1_sha},
        "evaluation_scope": "nur Validierung und Zweierpanel, Testfamilien geschlossen",
        "panel_sizes": {p: len(panels["families"][p]) for p in PANELS},
        "checkpoint": f"fest nach {CHECKPOINT_UPDATES} Updates, keine Auswahl",
        "bootstrap": {"draws": BOOTSTRAP_DRAWS, "seed": BOOTSTRAP_SEED, "interval": b1.INTERVAL,
                      "unit": "Familie, gemeinsame Ziehung je Panel für alle Arme und Parents",
                      "label": SCENE_CI_LABEL},
        "shared_scenes": "Die drei Parents teilen Validierungs-, Zweier- und Poolfamilien. Parents sind getrennte "
                         "Lernverläufe, Szenen sind keine unabhängigen Wiederholungen.",
        "validation_reuse": "validation_normal und validation_hard wurden in N2-2/N2-2b zur Critic-Abnahme "
                            "ausgerollt. Die SI-Auswahl verwendet sie nicht (v3 §6).",
        "bc_source": "BC-Werte auf validation_normal und validation_hard aus N2-2, Zweierpanel aus S-5",
        "min_relevant_effect_pp": MIN_RELEVANT_EFFECT_PP,
        "significance_tests": "keine (drei Seeds erlauben keinen Bestätigungsschluss)",
    }

    rates = []
    for panel in PANELS:
        for parent in PARENTS:
            for arm in ARMS:
                vec = outcomes[(arm, parent, panel)]
                rates.append({"arm": arm, "parent": parent, "panel": panel, "k": int(vec.sum()),
                              "n": int(vec.size), "rate": float(vec.mean())})
    result["rates"] = rates

    contrasts = []
    for name, panel, arm_a, arm_b, role in CONTRASTS:
        idx = b1.bootstrap_indices(len(panels["families"][panel]))
        per_parent, boot_by_parent = [], []
        for parent in PARENTS:
            a, b = outcomes[(arm_a, parent, panel)], outcomes[(arm_b, parent, panel)]
            diff_vec = a.astype(np.float64) - b.astype(np.float64)
            boot = diff_vec[idx].mean(axis=1)
            boot_by_parent.append(boot)
            per_parent.append({"parent": parent, "k_a": int(a.sum()), "k_b": int(b.sum()), "n": int(a.size),
                               "difference": float(diff_vec.mean()), "discordant": b1.discordant(a, b),
                               "scene_ci95": b1.percentile_interval(boot)})
        diffs = [p["difference"] for p in per_parent]
        contrasts.append({
            "name": name, "panel": panel, "arm_a": arm_a, "arm_b": arm_b, "role": role,
            "per_parent": per_parent,
            "mean_over_parents": float(np.mean(diffs)),
            "mean_scene_ci95": b1.percentile_interval(np.mean(boot_by_parent, axis=0)),
            "min": float(min(diffs)), "max": float(max(diffs)), "spread": float(max(diffs) - min(diffs)),
            "ci_label": SCENE_CI_LABEL,
        })
    result["contrasts"] = contrasts

    side = []
    for arm in SI_ARMS:
        for parent in PARENTS:
            a = outcomes[(arm, parent, "two_cube_validation")]
            b = outcomes[("BC", parent, "two_cube_validation")]
            k_a, k_b, n = int(a.sum()), int(b.sum()), int(a.size)
            side.append({"arm": arm, "parent": parent, "k_arm": k_a, "k_bc": k_b, "n": n,
                         "drop_pp": 100 * (k_b - k_a) / n,
                         "exceeds_10pp": two_cube_drop_exceeded(k_a, k_b, n)})
    result["two_cube_side_condition"] = {
        "rule": "Abfall des Arms unter seinen BC-Parent um mehr als 10 Prozentpunkte, nur berichtend (v3 §1)",
        "rows": side, "any_exceeded": any(r["exceeds_10pp"] for r in side)}

    data_rows = []
    for parent in PARENTS:
        e, k = runs[("SI-E", parent)], runs[("SI-K", parent)]
        for arm in SI_ARMS:
            run = runs[(arm, parent)]
            data_rows.append({
                "arm": arm, "parent": parent, "demo_frames": run["demo_frames"], "demo_fraction": DEMO_FRACTION,
                "self_success_episodes": run["self_success_episodes"],
                "self_success_frames": run["self_success_frames"],
                "prefix_episodes": run["prefix_episodes"], "prefix_families": run["prefix_families"],
                "prefix_frames": run["prefix_frames"],
                "self_frames": run["self_success_frames"] + run["prefix_frames"],
                "selection_sha256": run["selection_sha256"], "checkpoint_sha256": run["checkpoint_sha256"]})
        e_self = e["self_success_frames"]
        k_self = k["self_success_frames"] + k["prefix_frames"]
        data_rows.append({
            "arm": "SI-K/SI-E", "parent": parent,
            "self_frame_ratio": (k_self / e_self) if e_self > 0 else None,
            "gate_frames_met": 100 * k_self >= round(100 * GATE_FRAME_RATIO) * e_self,
            "gate_families_met": k["prefix_families"] >= GATE_MIN_FAMILIES,
            "note": "Gate nach v3 §4 entscheidet S-2 vor dem Training; hier nur nachgerechnet und berichtet"})
    result["data_volumes"] = data_rows

    costs = {"pool": {"episodes": pool["episodes"], "frames": pool["frames"], "runtime_s": pool.get("runtime_s"),
                      "note": "gemeinsamer Pool aller Parents (S-1), 0 Optimizerupdates"},
             "runs": [{"arm": arm, "parent": parent, "updates": runs[(arm, parent)]["updates"],
                       "update_runtime_s": runs[(arm, parent)].get("update_runtime_s"),
                       "eval_episodes": runs[(arm, parent)]["eval_episodes"],
                       "eval_runtime_s": runs[(arm, parent)].get("eval_runtime_s")}
                      for arm in SI_ARMS for parent in PARENTS],
             "total_updates": sum(r["updates"] for r in runs.values())}
    result["costs"] = costs

    result["bc_determinism"] = {
        "rule": f"{DETERMINISM_FAMILIES} Familien je Parent erneut mit BC ausgerollt und mit N2-2 verglichen, berichtend",
        "rows": determinism, "all_match": all(not r["mismatch_families"] for r in determinism)}

    primary = contrasts[0]
    rates_dis = [(p["discordant"]["only_a"] + p["discordant"]["only_b"]) / p["n"] for p in primary["per_parent"]]
    diffs = [p["difference"] for p in primary["per_parent"]]
    n_fam = primary["per_parent"][0]["n"]
    dis = float(np.mean(rates_dis))
    result["seed_count_inputs"] = {
        "contrast": "SI-K − SI-E auf validation_normal je Parent",
        "pilot_differences": diffs, "discordance_rate": dis, "eval_families": n_fam,
        "delta": MIN_RELEVANT_EFFECT_PP / 100,
        "command": ("praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/seed_count.py plan "
                    "--pilot-differences " + " ".join(repr(d) for d in diffs)
                    + f" --discordance-rate {dis!r} --eval-families {n_fam} --delta {MIN_RELEVANT_EFFECT_PP / 100!r}"
                    + " --cost NAME=STUNDEN --budget-hours H"),
        "note": "Budget und Kosten je Seed legt der Hauptvergleich fest. Die Kontrastbeschriftung in der Ausgabe "
                "von seed_count_v1 lautet fest „AC-IL − AC-neu“; maßgeblich ist der hier genannte Kontrast."}
    return result


# --------------------------------------------------------------------------- Ausgabe

def _pct(x):
    return f"{100 * x:+.1f}"


def render_markdown(result):
    lines = [f"# Pilotauswertung Selbstimitation ({result['analysis_version']})", "",
             f"Umfang: {result['evaluation_scope']}. {result['checkpoint']}. Keine Signifikanztests. "
             f"{result['shared_scenes']} {result['validation_reuse']}", "",
             "## Erfolg am festen Checkpoint", "", "| Panel | Parent | Arm | k/n |", "|---|---|---|---|"]
    for r in result["rates"]:
        lines.append(f"| {r['panel']} | {r['parent']} | {r['arm']} | {r['k']}/{r['n']} |")
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
              "## Zweierpanel, Nebenbedingung (berichtend)", "", "| Arm | Parent | Arm k/n | BC k/n | > 10 pp Abfall |",
              "|---|---|---|---|---|"]
    for r in result["two_cube_side_condition"]["rows"]:
        lines.append(f"| {r['arm']} | {r['parent']} | {r['k_arm']}/{r['n']} | {r['k_bc']}/{r['n']} | "
                     f"{'ja' if r['exceeds_10pp'] else 'nein'} |")
    lines += ["", "## Datenmengen", "", "| Arm | Parent | Zweierframes | Erfolgsepisoden | Erfolgsframes | "
              "Präfixe (Familien) | Präfixframes |", "|---|---|---|---|---|---|---|"]
    for r in result["data_volumes"]:
        if r["arm"] in SI_ARMS:
            lines.append(f"| {r['arm']} | {r['parent']} | {r['demo_frames']} | {r['self_success_episodes']} | "
                         f"{r['self_success_frames']} | {r['prefix_episodes']} ({r['prefix_families']}) | "
                         f"{r['prefix_frames']} |")
    det = result["bc_determinism"]
    lines += ["", f"BC-Determinismus: {'alle Familien gleich' if det['all_match'] else 'ABWEICHUNG'} "
              + ", ".join(f"P{r['parent']} {r['matches']}/{r['families']}" for r in det["rows"]), "",
              f"Seedzahl-Eingaben (δ = {result['seed_count_inputs']['delta']}): `{result['seed_count_inputs']['command']}`", ""]
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("analyze", help="Ergebnisdatei nach v3 §7 auswerten")
    run.add_argument("--input", required=True, type=Path)
    run.add_argument("--output", required=True, type=Path)
    run.add_argument("--markdown", type=Path)
    run.add_argument("--splits", type=Path, default=HERE / "splits_v3.json")
    run.add_argument("--panels", type=Path, default=HERE / "difficulty_panels_v1.json")
    sub.add_parser("hash", help="SHA-256 dieses Skripts ausgeben")
    args = parser.parse_args(argv)
    if args.command == "hash":
        print(b1.sha256_file(__file__))
        return 0
    panels = load_panels(args.splits, args.panels)
    data = json.loads(args.input.read_text(encoding="utf-8"))
    result = analyze(data, panels)
    result["script_sha256"] = b1.sha256_file(__file__)
    result["input_sha256"] = b1.sha256_file(args.input)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.markdown:
        args.markdown.write_text(render_markdown(result), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
