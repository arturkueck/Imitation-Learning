"""Tests für pilot_analysis.py (B-1) ausschließlich auf synthetischen Daten. Keine Pilotdaten."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_analysis as pa  # noqa: E402


@pytest.fixture(scope="module")
def panels():
    return pa.load_panels()


def _success(families, k, shift=0):
    """Erfolg auf den Familienindizes shift … shift+k−1 (zyklisch)."""
    n = len(families)
    hits = {(shift + i) % n for i in range(k)}
    return [i in hits for i in range(n)]


def make_data(panels, k=None, shift=None, aborted=None):
    """Synthetischer vollständiger Pilot. k[(arm, parent, panel, round)] überschreibt die Erfolgszahl."""
    k = k or {}
    shift = shift or {}
    aborted = aborted or {}
    base = {"validation_normal": 30, "validation_hard": 15, "two_cube_validation": 80}
    evaluations, runs = [], []
    for parent in pa.PARENTS:
        cells = [("BC", panel, 0) for panel in pa.PANELS]
        for arm in pa.AC_ARMS:
            last = aborted.get((arm, parent), pa.CHECKPOINT_ROUND)
            cells += [(arm, "validation_normal", r) for r in range(1, last + 1)]
            if last == pa.CHECKPOINT_ROUND:
                cells += [(arm, "validation_hard", 4), (arm, "two_cube_validation", 4)]
            runs.append({
                "arm": arm, "parent": parent,
                "status": "complete" if last == pa.CHECKPOINT_ROUND else "aborted",
                "last_evaluated_round": last,
                "rounds": [{"round": r, "online_episodes": 100, "online_frames": 50_000 + r,
                            "critic_updates": 2500, "actor_updates": 1250} for r in range(1, last + 1)],
                "pretrain_episodes": 300 if arm == "AC-IL" else 0,
                "pretrain_frames": 120_000 if arm == "AC-IL" else None,
                "pretrain_updates": 20_000 if arm == "AC-IL" else 0,
                "eval_episodes": 550, "runtime_s": 3600.0,
            })
        for arm, panel, rnd in cells:
            fam = panels["families"][panel]
            kk = k.get((arm, parent, panel, rnd), base[panel])
            ss = shift.get((arm, parent, panel, rnd), 0)
            for seed, ok in zip(fam, _success(fam, kk, ss)):
                evaluations.append({"arm": arm, "parent": parent, "panel": panel, "round": rnd,
                                    "scene_seed": seed, "success": ok})
    return {"schema": pa.INPUT_SCHEMA, "runs": runs, "evaluations": evaluations}


def contrast(result, name, panel):
    return next(c for c in result["contrasts"] if c["name"] == name and c["panel"] == panel)


def rate(result, arm, parent, panel):
    return next(r for r in result["rates"] if (r["arm"], r["parent"], r["panel"]) == (arm, parent, panel))


# --------------------------------------------------------------------------- Panels

def test_panels_have_frozen_sizes_and_exclude_test(panels):
    fam = panels["families"]
    assert [len(fam[p]) for p in pa.PANELS] == [100, 50, 100]
    assert fam["validation_normal"][0] == 2100000400 and fam["validation_normal"][-1] == 2100000499
    assert all(2100000500 <= f <= 2100001499 for f in fam["validation_hard"])
    assert fam["two_cube_validation"][0] == 2100003150
    assert panels["test_ranges"] == ((2100001500, 2100001649), (2100001650, 2100003149))
    for lo, hi in panels["test_ranges"]:
        assert not any(lo <= f <= hi for p in pa.PANELS for f in fam[p])


# --------------------------------------------------------------------------- Kennzahlen

def test_rates_and_primary_contrast(panels):
    k = {("AC-IL", 1, "validation_normal", 4): 45, ("AC-neu", 1, "validation_normal", 4): 35,
         ("AC-IL", 2, "validation_normal", 4): 30, ("AC-neu", 2, "validation_normal", 4): 30,
         ("AC-IL", 3, "validation_normal", 4): 20, ("AC-neu", 3, "validation_normal", 4): 25}
    res = pa.analyze(make_data(panels, k=k), panels)
    assert rate(res, "AC-IL", 1, "validation_normal")["k"] == 45
    assert rate(res, "AC-IL", 1, "validation_normal")["n"] == 100
    assert rate(res, "BC", 2, "validation_hard")["n"] == 50
    c = contrast(res, "AC-IL − AC-neu", "validation_normal")
    assert c["role"] == "primär"
    assert [p["difference"] for p in c["per_parent"]] == pytest.approx([0.10, 0.0, -0.05])
    assert c["mean_over_parents"] == pytest.approx(0.05 / 3)
    assert (c["min"], c["max"], c["spread"]) == pytest.approx((-0.05, 0.10, 0.15))
    # gleiche Startfamilie (shift 0), daher nur in eine Richtung diskordant
    assert c["per_parent"][0]["discordant"] == {"only_a": 10, "only_b": 0, "both": 35, "neither": 55}
    assert "reine Szenenunsicherheit" in c["ci_label"]


def test_discordant_pairs_with_shifted_successes(panels):
    k = {("AC-IL", 1, "validation_normal", 4): 30, ("AC-neu", 1, "validation_normal", 4): 30}
    sh = {("AC-IL", 1, "validation_normal", 4): 10}
    res = pa.analyze(make_data(panels, k=k, shift=sh), panels)
    p1 = contrast(res, "AC-IL − AC-neu", "validation_normal")["per_parent"][0]
    assert p1["difference"] == 0.0
    assert p1["discordant"] == {"only_a": 10, "only_b": 10, "both": 20, "neither": 60}
    lo, hi = p1["scene_ci95"]
    assert lo < 0 < hi


def test_bootstrap_is_fixed_shared_and_reproducible(panels):
    k = {("AC-IL", p, "validation_normal", 4): 40 + p for p in pa.PARENTS}
    data = make_data(panels, k=k)
    a, b = pa.analyze(data, panels), pa.analyze(copy.deepcopy(data), panels)
    assert a["contrasts"] == b["contrasts"]
    idx = pa.bootstrap_indices(100)
    assert idx.shape == (2000, 100)
    assert np.array_equal(idx, np.random.default_rng(7300).integers(0, 100, size=(2000, 100)))
    # Nachrechnung Parent 1 und gemeinsame Ziehung für das Parentmittel
    fam = panels["families"]["validation_normal"]
    diffs = []
    for p in pa.PARENTS:
        x = np.array(_success(fam, 40 + p), float) - np.array(_success(fam, 30), float)
        diffs.append(x[idx].mean(axis=1))
    c = contrast(a, "AC-IL − AC-neu", "validation_normal")
    assert c["per_parent"][0]["scene_ci95"] == pytest.approx(pa.percentile_interval(diffs[0]))
    assert c["mean_scene_ci95"] == pytest.approx(pa.percentile_interval(np.mean(diffs, axis=0)))


def test_identical_arms_give_zero_interval(panels):
    res = pa.analyze(make_data(panels), panels)
    for c in res["contrasts"]:
        assert c["mean_over_parents"] == 0.0
        assert c["mean_scene_ci95"] == [0.0, 0.0]


def test_all_contrasts_present_and_separate(panels):
    res = pa.analyze(make_data(panels), panels)
    keys = {(c["name"], c["panel"], c["role"]) for c in res["contrasts"]}
    assert ("AC-IL − AC-neu", "validation_normal", "primär") in keys
    assert ("AC-neu − BC", "validation_hard", "sekundär") in keys
    assert ("AC-IL − BC", "two_cube_validation", "Zweiererhalt") in keys
    assert len(keys) == 8
    assert res["significance_tests"].startswith("keine")
    assert res["min_relevant_effect_pp"] == 10


# --------------------------------------------------------------------------- Testfamilien und Vertrag

@pytest.mark.parametrize("seed", [2100001500, 2100001649, 2100001650, 2100003149])
def test_test_family_rejected(panels, seed):
    data = make_data(panels)
    data["evaluations"][0]["scene_seed"] = seed
    data["schema"] = "falsch"  # Testsperre greift vor jeder anderen Prüfung
    with pytest.raises(pa.TestFamilyError):
        pa.analyze(data, panels)


def test_test_panel_name_rejected(panels):
    data = make_data(panels)
    data["evaluations"][0]["panel"] = "test_hard"
    with pytest.raises(pa.TestFamilyError):
        pa.analyze(data, panels)


@pytest.mark.parametrize("mutation", ["missing", "duplicate", "foreign", "run_missing", "round", "schema", "type"])
def test_contract_violations(panels, mutation):
    data = make_data(panels)
    ev = data["evaluations"]
    if mutation == "missing":
        ev.pop(5)
    elif mutation == "duplicate":
        ev.append(dict(ev[5]))
    elif mutation == "foreign":
        ev[5]["scene_seed"] = 2100000100  # Critic-Datenfamilie statt Validierung
    elif mutation == "run_missing":
        data["runs"].pop()
    elif mutation == "round":
        ev.append({"arm": "AC-IL", "parent": 1, "panel": "validation_hard", "round": 2,
                   "scene_seed": panels["families"]["validation_hard"][0], "success": True})
    elif mutation == "schema":
        data["schema"] = "anderes"
    elif mutation == "type":
        ev[5]["success"] = 1
    with pytest.raises(pa.ContractError):
        pa.analyze(data, panels)


def test_complete_run_without_hard_panel_rejected(panels):
    data = make_data(panels)
    data["evaluations"] = [e for e in data["evaluations"]
                           if not (e["arm"] == "AC-neu" and e["parent"] == 3 and e["panel"] == "validation_hard")]
    with pytest.raises(pa.ContractError, match="Endprüfung"):
        pa.analyze(data, panels)


# --------------------------------------------------------------------------- Abbruch, Effizienz, Zusammenbruch

def test_aborted_run_uses_last_checkpoint_and_is_flagged(panels):
    k = {("AC-IL", 2, "validation_normal", 1): 33, ("AC-IL", 2, "validation_normal", 2): 37}
    res = pa.analyze(make_data(panels, k=k, aborted={("AC-IL", 2): 2}), panels)
    r = rate(res, "AC-IL", 2, "validation_normal")
    assert (r["k"], r["checkpoint_round"], r["aborted"]) == (37, 2, True)
    h = rate(res, "AC-IL", 2, "validation_hard")
    assert (h["checkpoint_round"], h["round0_is_bc"], h["k"]) == (0, True, 15)
    assert contrast(res, "AC-IL − AC-neu", "validation_normal")["any_aborted"] is True
    e = next(x for x in res["efficiency"] if (x["arm"], x["parent"]) == ("AC-IL", 2))
    assert e["online_episodes"] == "> 200 (abgebrochen)"
    assert e["with_pretrain_episodes"] == "> 500 (abgebrochen)"


def test_efficiency_threshold_reached_or_not(panels):
    k = {("AC-neu", 1, "validation_normal", 2): 40,   # 30 + 10 → erreicht in Runde 2
         ("AC-IL", 1, "validation_normal", 1): 40,    # erreicht in Runde 1
         ("AC-neu", 2, "validation_normal", 4): 39}   # nie erreicht
    res = pa.analyze(make_data(panels, k=k), panels)
    eff = {(e["arm"], e["parent"]): e for e in res["efficiency"]}
    assert eff[("AC-neu", 1)]["reached_round"] == 2
    assert eff[("AC-neu", 1)]["online_episodes"] == 200
    assert eff[("AC-neu", 1)]["online_frames"] == 50_001 + 50_002
    assert eff[("AC-IL", 1)]["online_episodes"] == 100
    assert eff[("AC-IL", 1)]["with_pretrain_episodes"] == 400
    assert eff[("AC-IL", 1)]["with_pretrain_frames"] == 50_001 + 120_000
    assert eff[("AC-neu", 2)]["online_episodes"] == "> 400"
    assert eff[("AC-IL", 3)]["with_pretrain_episodes"] == "> 700"
    assert "with_pretrain_episodes" not in eff[("AC-neu", 1)]


def test_reaches_threshold_integer_rule():
    assert pa.reaches_threshold(40, 100, 30, 100)
    assert not pa.reaches_threshold(39, 100, 30, 100)
    assert pa.reaches_threshold(20, 50, 30, 100)       # 40 % ≥ 30 % + 10
    assert not pa.reaches_threshold(19, 50, 30, 100)
    assert not pa.reaches_threshold(100, 100, 91, 100)  # Schwelle über 100 % unerreichbar


def test_collapse_flags_reporting_only(panels):
    k = {("AC-neu", 1, "validation_normal", 1): 15,   # genau halbe Parentquote → markiert
         ("AC-IL", 1, "validation_normal", 2): 16,    # knapp darüber → nicht markiert
         ("AC-IL", 2, "validation_normal", 4): 5}     # Runde 4 ist keine Zwischenprüfung
    res = pa.analyze(make_data(panels, k=k), panels)
    hits = {(h["arm"], h["parent"], h["round"]) for h in res["collapse_flags"]["hits"]}
    assert hits == {("AC-neu", 1, 1)}


def test_learning_curve_round0_is_bc(panels):
    res = pa.analyze(make_data(panels, k={("BC", 3, "validation_normal", 0): 22}), panels)
    curve = next(c for c in res["learning_curves"] if (c["arm"], c["parent"]) == ("AC-IL", 3))
    assert [p["round"] for p in curve["points"]] == [0, 1, 2, 3, 4]
    assert curve["points"][0]["k"] == 22 and curve["points"][0]["source"].startswith("BC")


def test_costs_reported_separately(panels):
    res = pa.analyze(make_data(panels), panels)
    il = next(c for c in res["costs"] if (c["arm"], c["parent"]) == ("AC-IL", 1))
    neu = next(c for c in res["costs"] if (c["arm"], c["parent"]) == ("AC-neu", 1))
    assert (il["online_episodes"], il["critic_updates"], il["actor_updates"]) == (400, 10_000, 5_000)
    assert (il["pretrain_episodes"], il["pretrain_updates"]) == (300, 20_000)
    assert (neu["pretrain_episodes"], neu["pretrain_updates"]) == (0, 0)


# --------------------------------------------------------------------------- Kommandozeile

def test_cli_writes_json_and_markdown(panels, tmp_path):
    src = tmp_path / "synthetic.json"
    src.write_text(json.dumps(make_data(panels)), encoding="utf-8")
    out, md = tmp_path / "result.json", tmp_path / "result.md"
    assert pa.main(["analyze", "--input", str(src), "--output", str(out), "--markdown", str(md)]) == 0
    result = json.loads(out.read_text(encoding="utf-8"))
    assert result["script_sha256"] == pa.sha256_file(pa.__file__)
    assert result["input_sha256"] == pa.sha256_file(src)
    text = md.read_text(encoding="utf-8")
    assert "reine Szenenunsicherheit" in text and "AC-IL − AC-neu" in text


def test_cli_hash(capsys):
    assert pa.main(["hash"]) == 0
    assert capsys.readouterr().out.strip() == pa.sha256_file(pa.__file__)
