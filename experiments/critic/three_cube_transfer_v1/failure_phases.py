"""B-2: Fehlerphasen der A-Parents aus bereits erhobenen N1-4- und N2-1-Daten.

Nur Lesen vorhandener Rohdaten, keine Rollouts, keine Optimizerupdates, keine Testfamilien.

Befehle (aus dem Repository-Stamm):
  run      Rohdaten prüfen, auswerten, `failure_phases.json` schreiben, Tabellen ausgeben
  tables   Tabellen aus vorhandener `failure_phases.json` erneut ausgeben

Operationalisierung (vor der Auswertung festgelegt, siehe FAILURE_PHASES.md):

* Endpunkt eines Fehlschlags: (Stufe, Policy-Phase, Rückzug) im letzten Frame.
* Endsegment: längster Suffix der Episode mit demselben Endpunkt.
* Nötige Korrektur (horizontal, im Endzustand nach der letzten Aktion):
  - Phasen 0–3 (Greifen, Anker ist der zu tragende Würfel): Versatz Greifer → zu tragender Würfel.
  - Phasen 4–6 (Transport, Ablage, Lösen, Anker ist die Basis): Versatz zu tragender Würfel →
    Basiswürfel, gekürzt um die Gültigkeitstoleranz 9 mm (`prefix_valid`).
  - Rückzug: keine geometrische Korrektur definiert.
* Reichweite unter der Bindung (§7 v1): je Achse i die Summe der zusätzlich kommandierbaren
  Sollwertverschiebungen im Endsegment, `R_i = 0,05 m · Σ_t min(δ_max, 0,5·|a_parent,t,i|)`.
  Quote `q = max_i |e_i| / R_i`; q ≤ 1 heißt erreichbar in idealisierter Kinematik.
"""

import argparse
import hashlib
import io
import json
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT / "praxis/results/critic/three_cube_transfer_v1"
N14 = RESULTS / "calibration_n1_4"
N21 = RESULTS / "critic_data_n2_1"
OUT = HERE / "failure_phases.json"

PARENTS = (1, 2, 3)
N14_EXPECTED, N21_EXPECTED = 300, 900
N21_DATASET_SHA256 = "9f0aeaaff68734ffa2bd2a14bc91bd32c3c92db5fc255af1029a580daff9a2ba"
ALLOWED_SPLITS = {"calibration": (2100000000, 2100000099), "critic_data": (2100000100, 2100000399)}

# Aktionsskala: OSC_POSE, control_delta, output_max 0,05 m je Einheit (stack_two/task_info.json).
ACTION_SCALE_M = 0.05
DELTAS = (0.05, 0.10, 0.20)
XY_TOL_M, Z_TOL_M, CUBE_M, LIFT_Z_M = 0.009, 0.008, 0.04, 0.05
REST_WIDTH = 0.01  # Ruhe-Frame: Breite b_x und b_y bei δ_max = 0,20 beide < 0,01 (0,5 mm/Schritt)
PHASE_NAMES = {0: "Anfahren", 1: "Absenken zum Greifen", 2: "Schließen", 3: "Anheben",
               4: "Transport", 5: "Ablegen", 6: "Lösen"}

COL_CUBE = {0: slice(0, 3), 1: slice(3, 6), 2: slice(6, 9)}
COL_EEF = slice(21, 24)


class TestFamilyError(RuntimeError):
    """Eine Szene liegt außerhalb der für B-2 erlaubten bereits geöffneten Splits."""


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def check_split(scene, split, splits):
    """Szene muss im erlaubten Split liegen und darf keinen Test-/Validierungssplit berühren."""
    first, last = ALLOWED_SPLITS[split]
    if not first <= scene <= last:
        raise TestFamilyError(f"Szene {scene} liegt nicht in {split}")
    for entry in splits:
        if entry["id"] != split and entry["first"] <= scene <= entry["last"]:
            raise TestFamilyError(f"Szene {scene} gehört zu {entry['id']}")


def final_segment_start(stage, phase, retreat):
    """Index des ersten Frames im längsten Suffix mit demselben (Stufe, Phase, Rückzug)."""
    key = np.stack([np.asarray(stage, np.int64), np.asarray(phase, np.int64),
                    np.asarray(retreat, np.int64)], axis=1)
    if len(key) == 0:
        raise ValueError("leere Episode")
    same = np.all(key == key[-1], axis=1)
    start = len(key)
    while start > 0 and same[start - 1]:
        start -= 1
    return start


def needed_correction(state, stage, phase, retreat):
    """Horizontale Korrektur e (m, 2) im Endzustand und Gruppe; None bei Rückzug."""
    carried = np.asarray(state[COL_CUBE[stage]], np.float64)
    base = np.asarray(state[COL_CUBE[stage - 1]], np.float64)
    if retreat:
        return "Rückzug", None
    if phase <= 3:
        eef = np.asarray(state[COL_EEF], np.float64)
        return "Greifen (0–3)", carried[:2] - eef[:2]
    offset = base[:2] - carried[:2]
    distance = float(np.linalg.norm(offset))
    if distance <= XY_TOL_M:
        return "Ablage (4–6)", np.zeros(2)
    return "Ablage (4–6)", offset * (distance - XY_TOL_M) / distance


def reach(parent_xy, delta):
    """Zusätzlich kommandierbare Sollwertverschiebung je Achse (m) unter der Bindung."""
    parent_xy = np.asarray(parent_xy, np.float64).reshape(-1, 2)
    return ACTION_SCALE_M * np.minimum(delta, 0.5 * np.abs(parent_xy)).sum(axis=0)


def reach_ratio(correction, reach_xy):
    correction = np.abs(np.asarray(correction, np.float64))
    if not np.any(correction > 0):
        return 0.0
    with np.errstate(divide="ignore", invalid="ignore"):
        ratios = np.where(correction > 0, correction / np.asarray(reach_xy, np.float64), 0.0)
    return float(np.max(ratios))


def category(ratio):
    if ratio == 0.0:
        return "keine nötig"
    return "innerhalb" if ratio <= 1.0 else "außerhalb"


def end_flags(state, stage):
    cubes = {k: np.asarray(state[s], np.float64) for k, s in COL_CUBE.items()}

    def on(upper, lower):
        return bool(np.linalg.norm(cubes[upper][:2] - cubes[lower][:2]) <= XY_TOL_M
                    and abs(cubes[upper][2] - cubes[lower][2] - CUBE_M) <= Z_TOL_M)

    base_on_table = abs(cubes[0][2] - CUBE_M / 2) <= Z_TOL_M
    return dict(
        carried_lifted=bool(cubes[stage][2] > LIFT_Z_M),
        carried_on_table=bool(abs(cubes[stage][2] - CUBE_M / 2) <= Z_TOL_M),
        carried_on_base=on(stage, stage - 1),
        base_intact=bool(base_on_table and (stage == 1 or on(1, 0))),
    )


def analyze_episode(arrays):
    """Kennzahlen eines Fehlschlags aus den Übergangsarrays (Datenvertrag N2-1)."""
    stage, phase, retreat = arrays["stage"], arrays["phase"], arrays["retreat"]
    start = final_segment_start(stage, phase, retreat)
    end_stage, end_phase, end_retreat = int(stage[-1]), int(phase[-1]), bool(retreat[-1])
    state = np.asarray(arrays["next_critic_state"][-1], np.float64)
    if not np.isfinite(state).all():
        raise ValueError("nicht endlicher Endzustand")
    group, correction = needed_correction(state, end_stage, end_phase, end_retreat)
    parent_xy = np.asarray(arrays["parent_action"], np.float64)[start:, :2]
    widths = np.minimum(0.20, 0.5 * np.abs(parent_xy))
    # Gegenprobe der Geometrie: Basis beim ersten Frame in Stufe 2 (Sequencer hat sie dort als gültig erkannt).
    second = np.flatnonzero(np.asarray(stage) == 2)
    entry = (end_flags(np.asarray(arrays["critic_state"][second[0]], np.float64), 2)["base_intact"]
             if len(second) else None)
    row = dict(
        base_intact_at_stage2_entry=entry,
        end_stage=end_stage, end_phase=end_phase, end_retreat=end_retreat, group=group,
        segment_frames=int(len(stage) - start),
        rest_share=float(np.mean(np.all(widths < REST_WIDTH, axis=1))),
        median_width_mm_020=float(np.median(widths) * ACTION_SCALE_M * 1000),
        **end_flags(state, end_stage),
    )
    if correction is None:
        row.update(correction_mm=None, ratio={str(d): None for d in DELTAS})
    else:
        row.update(correction_mm=float(np.linalg.norm(correction) * 1000),
                   ratio={str(d): reach_ratio(correction, reach(parent_xy, d)) for d in DELTAS})
    return row


def quantiles(values):
    values = [v for v in values if v is not None]
    if not values:
        return None
    q = np.percentile(np.asarray(values, np.float64), [25, 50, 75])
    return dict(n=len(values), q25=float(q[0]), median=float(q[1]), q75=float(q[2]),
                min=float(min(values)), max=float(max(values)))


def load_n14(splits):
    summary = read(N14 / "summary.json")
    paths = [N14 / "episodes" / f"{i:03d}.json" for i in range(N14_EXPECTED)]
    raw = b"".join(p.read_bytes() for p in paths)
    if digest(raw) != summary["raw_sha256"]:
        raise ValueError("N1-4: raw_sha256 stimmt nicht mit summary.json")
    rows = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    for row in rows:
        check_split(row["scene_seed"], "calibration", splits)
    if sum(r["success"] for r in rows) != summary["successes"]:
        raise ValueError("N1-4: Erfolgszahl stimmt nicht")
    return rows, summary["raw_sha256"]


def load_n21(splits):
    summary = read(N21 / "summary.json")
    rows, hashes = [], []
    for index in range(N21_EXPECTED):
        data = (N21 / "episodes" / f"{index:04d}.npz").read_bytes()
        meta = read(N21 / "episodes" / f"{index:04d}.json")
        if digest(data) != meta["arrays_sha256"]:
            raise ValueError(f"N2-1: Hash der Episode {index} stimmt nicht")
        check_split(meta["scene_seed"], "critic_data", splits)
        hashes.append(meta["arrays_sha256"])
        row = dict(scene_seed=meta["scene_seed"], parent_seed=meta["parent_seed"],
                   success=bool(meta["success"]), termination=meta["termination"],
                   frames=meta["frames"], max_stable_frames=meta["max_stable_frames"],
                   reached_second_placement=bool(meta["reached_second_placement"]))
        if not row["success"]:
            with np.load(io.BytesIO(data), allow_pickle=False) as archive:
                arrays = {k: archive[k] for k in ("stage", "phase", "retreat", "parent_action",
                                                  "critic_state", "next_critic_state")}
            row.update(analyze_episode(arrays))
        rows.append(row)
    dataset = digest("\n".join(hashes).encode())
    if dataset != summary["dataset_sha256"] or dataset != N21_DATASET_SHA256:
        raise ValueError("N2-1: dataset_sha256 stimmt nicht")
    return rows, dataset


def outcome_table(rows):
    """Ausgänge je Parent mit vollständigem Nenner (für N1-4 und N2-1 gleich)."""
    table = {}
    for p in PARENTS + ("gesamt",):
        sub = [r for r in rows if p == "gesamt" or r["parent_seed"] == p]
        fail = [r for r in sub if not r["success"]]
        table[str(p)] = dict(
            episodes=len(sub), successes=len(sub) - len(fail), failures=len(fail),
            fail_stage1=sum(not r["reached_second_placement"] for r in fail),
            fail_stage2=sum(r["reached_second_placement"] for r in fail),
            fail_tower_seen=sum(r["max_stable_frames"] > 0 for r in fail),
            terminations={t: sum(r["termination"] == t for r in sub)
                          for t in sorted({r["termination"] for r in rows})},
        )
    return table


def family_table(rows):
    by_scene = {}
    for r in rows:
        by_scene.setdefault(r["scene_seed"], []).append(r["success"])
    counts = {str(k): 0 for k in range(4)}
    for outcomes in by_scene.values():
        if len(outcomes) != 3:
            raise ValueError("Familie nicht vollständig gepaart")
        counts[str(3 - sum(outcomes))] += 1
    return dict(families=len(by_scene), failing_parents=counts)


def endpoint_tables(rows):
    failures = [r for r in rows if not r["success"]]
    endpoints = sorted({(r["end_stage"], r["end_phase"], r["end_retreat"]) for r in failures})
    table = []
    for stage, phase, retreat in endpoints:
        sub = [r for r in failures if (r["end_stage"], r["end_phase"], r["end_retreat"])
               == (stage, phase, retreat)]
        entry = dict(stage=stage, phase=phase, retreat=retreat,
                     name=("Rückzug" if retreat else PHASE_NAMES[phase]),
                     counts={str(p): sum(r["parent_seed"] == p for r in sub) for p in PARENTS},
                     total=len(sub), segment_frames=quantiles([r["segment_frames"] for r in sub]),
                     rest_share=quantiles([r["rest_share"] for r in sub]),
                     correction_mm=quantiles([r["correction_mm"] for r in sub]),
                     carried_lifted=sum(r["carried_lifted"] for r in sub),
                     carried_on_table=sum(r["carried_on_table"] for r in sub),
                     carried_on_base=sum(r["carried_on_base"] for r in sub),
                     base_intact=sum(r["base_intact"] for r in sub),
                     stage2_entries=sum(r["base_intact_at_stage2_entry"] is not None for r in sub),
                     base_intact_at_stage2_entry=sum(bool(r["base_intact_at_stage2_entry"]) for r in sub),
                     categories=(None if retreat else
                                 {str(d): {c: sum(category(r["ratio"][str(d)]) == c for r in sub)
                                           for c in ("keine nötig", "innerhalb", "außerhalb")}
                                  for d in DELTAS}))
        table.append(entry)
    return table


def binding_table(rows):
    failures = [r for r in rows if not r["success"]]
    out = {}
    for group in ("Greifen (0–3)", "Ablage (4–6)", "Rückzug"):
        sub = [r for r in failures if r["group"] == group]
        entry = dict(failures=len(sub),
                     counts={str(p): sum(r["parent_seed"] == p for r in sub) for p in PARENTS},
                     correction_mm=quantiles([r["correction_mm"] for r in sub]),
                     median_width_mm_020=quantiles([r["median_width_mm_020"] for r in sub]),
                     rest_share=quantiles([r["rest_share"] for r in sub]))
        if group != "Rückzug":
            entry["categories"] = {
                str(d): {str(p): {c: sum(category(r["ratio"][str(d)]) == c
                                         for r in sub if p == "gesamt" or r["parent_seed"] == p)
                                  for c in ("keine nötig", "innerhalb", "außerhalb")}
                         for p in PARENTS + ("gesamt",)}
                for d in DELTAS}
            entry["ratio"] = {str(d): quantiles([r["ratio"][str(d)] for r in sub
                                                 if r["ratio"][str(d)] not in (0.0, None)
                                                 and np.isfinite(r["ratio"][str(d)])])
                              for d in DELTAS}
            entry["ratio_infinite"] = {str(d): sum(not np.isfinite(r["ratio"][str(d)]) for r in sub)
                                       for d in DELTAS}
        out[group] = entry
    return out


def run():
    splits = read(HERE / "splits.json")["splits"]
    n14, n14_sha = load_n14(splits)
    n21, n21_sha = load_n21(splits)
    result = dict(
        task="B-2", schema="failure_phases.v1", optimizer_updates=0, rollouts=0,
        sources=dict(n1_4=dict(path="praxis/results/critic/three_cube_transfer_v1/calibration_n1_4",
                               raw_sha256=n14_sha, episodes=len(n14)),
                     n2_1=dict(path="praxis/results/critic/three_cube_transfer_v1/critic_data_n2_1",
                               dataset_sha256=n21_sha, episodes=len(n21))),
        script_sha256=digest(Path(__file__).read_bytes()),
        constants=dict(action_scale_m=ACTION_SCALE_M, deltas=list(DELTAS), xy_tol_m=XY_TOL_M,
                       z_tol_m=Z_TOL_M, lift_z_m=LIFT_Z_M, rest_width=REST_WIDTH),
        n1_4=dict(outcomes=outcome_table(n14), families=family_table(n14)),
        n2_1=dict(outcomes=outcome_table(n21), families=family_table(n21),
                  endpoints=endpoint_tables(n21), binding=binding_table(n21)),
    )
    text = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    OUT.write_text(text + "\n", encoding="utf-8")
    return result


def fmt(q, key="median", digits=1):
    return "–" if q is None else f"{q[key]:.{digits}f}"


def tables(result):
    lines = []
    for name in ("n1_4", "n2_1"):
        lines.append(f"### {name} Ausgänge")
        lines.append("| Parent | Episoden | Erfolge | Fehlschläge | davon Stufe 1 | davon Stufe 2 | Turm kurz gültig | Endgründe |")
        lines.append("|---|---:|---:|---:|---:|---:|---:|---|")
        for p, e in result[name]["outcomes"].items():
            lines.append(f"| {p} | {e['episodes']} | {e['successes']}/{e['episodes']} | {e['failures']}/{e['episodes']} | "
                         f"{e['fail_stage1']}/{e['failures']} | {e['fail_stage2']}/{e['failures']} | "
                         f"{e['fail_tower_seen']}/{e['failures']} | {e['terminations']} |")
        lines.append(f"Familien: {result[name]['families']}")
    lines.append("### n2_1 Endpunkte")
    lines.append("| Stufe | Phase | Name | P1 | P2 | P3 | gesamt | Endsegment Frames Median [Q1; Q3] | Ruheanteil Median | Korrektur mm Median [Q1; Q3] | über 0,05 m | auf Tisch | auf Basis | Basis intakt Ende | Basis intakt Eintritt St. 2 |")
    lines.append("|---|---|---|---:|---:|---:|---:|---|---:|---|---:|---:|---:|---:|---:|")
    for e in result["n2_1"]["endpoints"]:
        lines.append(f"| {e['stage']} | {e['phase']}{' R' if e['retreat'] else ''} | {e['name']} | "
                     f"{e['counts']['1']} | {e['counts']['2']} | {e['counts']['3']} | {e['total']} | "
                     f"{fmt(e['segment_frames'], digits=0)} [{fmt(e['segment_frames'], 'q25', 0)}; {fmt(e['segment_frames'], 'q75', 0)}] | "
                     f"{fmt(e['rest_share'], digits=2)} | {fmt(e['correction_mm'])} [{fmt(e['correction_mm'], 'q25')}; {fmt(e['correction_mm'], 'q75')}] | "
                     f"{e['carried_lifted']}/{e['total']} | {e['carried_on_table']}/{e['total']} | {e['carried_on_base']}/{e['total']} | "
                     f"{e['base_intact']}/{e['total']} | {e['base_intact_at_stage2_entry']}/{e['stage2_entries']} |")
    lines.append("| Stufe | Phase | n | δ 0,05 keine/innen/außen | δ 0,10 | δ 0,20 |")
    lines.append("|---|---|---:|---|---|---|")
    for e in result["n2_1"]["endpoints"]:
        if e["categories"]:
            cells = [" / ".join(str(e["categories"][str(d)][c]) for c in ("keine nötig", "innerhalb", "außerhalb"))
                     for d in DELTAS]
            lines.append(f"| {e['stage']} | {e['phase']} | {e['total']} | " + " | ".join(cells) + " |")
    lines.append("### n2_1 Bindung")
    for group, e in result["n2_1"]["binding"].items():
        lines.append(f"{group}: {e['failures']} Fehlschläge {e['counts']}, Korrektur mm {e['correction_mm']}, "
                     f"Breite mm/Schritt (δ=0,20) {e['median_width_mm_020']}, Ruheanteil {e['rest_share']}")
        if "categories" in e:
            lines.append("| δ_max | Parent | keine nötig | innerhalb | außerhalb | q Median (endlich, > 0) | q = ∞ |")
            lines.append("|---|---|---:|---:|---:|---:|---:|")
            for d, per in e["categories"].items():
                for p, c in per.items():
                    n = sum(c.values())
                    lines.append(f"| {d} | {p} | {c['keine nötig']}/{n} | {c['innerhalb']}/{n} | {c['außerhalb']}/{n} | "
                                 f"{fmt(e['ratio'][d], digits=2) if p == 'gesamt' else ''} | {e['ratio_infinite'][d] if p == 'gesamt' else ''} |")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("command", choices=("run", "tables"))
    args = parser.parse_args(argv)
    result = run() if args.command == "run" else read(OUT)
    sys.stdout.reconfigure(encoding="utf-8")
    print(tables(result))


if __name__ == "__main__":
    main()
