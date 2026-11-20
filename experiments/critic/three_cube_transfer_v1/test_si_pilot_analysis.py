"""Tests für si_pilot_analysis.py (S-0) ausschließlich auf synthetischen Daten. Keine Pilotdaten."""
import copy
import json
import sys
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pilot_analysis as b1  # noqa: E402
import seed_count as sc  # noqa: E402
import si_pilot_analysis as sa  # noqa: E402


@pytest.fixture(scope="module")
def panels():
    return sa.load_panels()


def _success(families, k, shift=0):
    n = len(families)
    hits = {(shift + i) % n for i in range(k)}
    return [i in hits for i in range(n)]


def _sha(c):
    return c * 64


def make_data(panels, k=None, shift=None):
    """Synthetischer vollständiger Pilot. k[(arm, parent, panel)] überschreibt die Erfolgszahl."""
    k = k or {}
    shift = shift or {}
    base = {"validation_normal": 30, "validation_hard": 15, "two_cube_validation": 80}
    evaluations, runs, det = [], [], []
    for parent in sa.PARENTS:
        for arm in sa.ARMS:
            for panel in sa.PANELS:
                fam = panels["families"][panel]
                kk = k.get((arm, parent, panel), base[panel])
                ss = shift.get((arm, parent, panel), 0)
                for seed, ok in zip(fam, _success(fam, kk, ss)):
                    evaluations.append({"arm": arm, "parent": parent, "panel": panel,
                                        "scene_seed": seed, "success": ok})
        for arm in sa.SI_ARMS:
            runs.append({
                "arm": arm, "parent": parent, "status": "complete", "updates": 5000,
                "minibatch_seed": 7700 + parent, "demo_fraction": 0.5,
                "checkpoint_sha256": _sha("a" if arm == "SI-E" else "b"), "selection_sha256": _sha("c"),
                "demo_frames": 90_000, "self_success_episodes": 120, "self_success_frames": 60_000,
                "prefix_episodes": 0 if arm == "SI-E" else 40, "prefix_families": 0 if arm == "SI-E" else 35,
                "prefix_frames": 0 if arm == "SI-E" else 9_000, "eval_episodes": 250,
                "update_runtime_s": 600.0, "eval_runtime_s": 900.0})
        fam = panels["families"]["validation_normal"]
        bc = _success(fam, k.get(("BC", parent, "validation_normal"), 30),
                      shift.get(("BC", parent, "validation_normal"), 0))
        for i in range(sa.DETERMINISM_FAMILIES):
            det.append({"parent": parent, "panel": "validation_normal", "scene_seed": fam[i],
                        "n2_2_success": bc[i], "rerun_success": bc[i]})
    return {"schema": sa.INPUT_SCHEMA, "runs": runs, "evaluations": evaluations, "bc_determinism": det,
            "pool": {"episodes": 1200, "frames": 700_000, "runtime_s": 5400.0}}


def contrast(result, name, panel):
    return next(c for c in result["contrasts"] if c["name"] == name and c["panel"] == panel)


def run_of(data, arm, parent):
    return next(r for r in data["runs"] if (r["arm"], r["parent"]) == (arm, parent))


# --------------------------------------------------------------------------- Übernahme aus B-1

def test_b1_is_frozen_and_hash_matches_file():
    assert sa.check_b1_frozen() == sa.B1_SHA256
    line = (HERE / "pilot_analysis.sha256").read_text(encoding="utf-8").split()
    assert line[0] == sa.B1_SHA256 and line[1] == "pilot_analysis.py"


def test_b1_hash_mismatch_is_rejected(tmp_path):
    fake = tmp_path / "pilot_analysis.py"
    fake.write_bytes((HERE / "pilot_analysis.py").read_bytes() + b"\n")
    with pytest.raises(sa.ContractError, match="eingefroren"):
        sa.check_b1_frozen(fake)


def test_inherited_constants():
    assert (sa.BOOTSTRAP_DRAWS, sa.BOOTSTRAP_SEED) == (2000, 7300)
    assert sa.PANELS == ("validation_normal", "validation_hard", "two_cube_validation")
    assert sa.CHECKPOINT_UPDATES == 5000 and sa.MIN_RELEVANT_EFFECT_PP == 5


def test_panels_frozen_sizes(panels):
    assert [len(panels["families"][p]) for p in sa.PANELS] == [100, 50, 100]


# --------------------------------------------------------------------------- Ergebnisse

def test_rates_and_primary_contrast(panels):
    k = {("SI-K", 1, "validation_normal"): 40, ("SI-K", 2, "validation_normal"): 35,
         ("SI-K", 3, "validation_normal"): 30}
    res = sa.analyze(make_data(panels, k=k), panels)
    prim = contrast(res, "SI-K − SI-E", "validation_normal")
    assert prim["role"].startswith("primär")
    assert [p["difference"] for p in prim["per_parent"]] == pytest.approx([0.10, 0.05, 0.0])
    assert prim["mean_over_parents"] == pytest.approx(0.05)
    assert prim["spread"] == pytest.approx(0.10)
    # Shift 0 bei beiden Armen: SI-K umfasst SI-E vollständig
    assert prim["per_parent"][0]["discordant"] == {"only_a": 10, "only_b": 0, "both": 30, "neither": 60}
    assert len(res["rates"]) == 3 * 3 * 3
    assert all(r["n"] == len(panels["families"][r["panel"]]) for r in res["rates"])


def test_all_planned_contrasts_present(panels):
    res = sa.analyze(make_data(panels), panels)
    got = [(c["name"], c["panel"]) for c in res["contrasts"]]
    assert got == [(c[0], c[1]) for c in sa.CONTRASTS]
    assert sum(c["role"].startswith("primär") for c in res["contrasts"]) == 1
    assert not any(p.startswith("test") for p in res["panel_sizes"])


def test_bootstrap_recomputed_with_shared_draws(panels):
    k = {("SI-K", p, "validation_normal"): 30 + 3 * p for p in sa.PARENTS}
    shift = {("SI-K", p, "validation_normal"): 7 * p for p in sa.PARENTS}
    data = make_data(panels, k=k, shift=shift)
    res = sa.analyze(data, panels)
    fam = panels["families"]["validation_normal"]
    idx = np.random.default_rng(7300).integers(0, len(fam), size=(2000, len(fam)))
    boots = []
    for parent in sa.PARENTS:
        a = np.array(_success(fam, 30 + 3 * parent, 7 * parent), dtype=float)
        b = np.array(_success(fam, 30), dtype=float)
        boot = (a - b)[idx].mean(axis=1)
        boots.append(boot)
        got = contrast(res, "SI-K − SI-E", "validation_normal")["per_parent"][parent - 1]["scene_ci95"]
        assert got == pytest.approx(list(np.quantile(boot, [0.025, 0.975])))
    mean_ci = contrast(res, "SI-K − SI-E", "validation_normal")["mean_scene_ci95"]
    assert mean_ci == pytest.approx(list(np.quantile(np.mean(boots, axis=0), [0.025, 0.975])))


def test_reproducible(panels):
    data = make_data(panels, k={("SI-E", 2, "validation_hard"): 20})
    assert json.dumps(sa.analyze(data, panels)) == json.dumps(sa.analyze(copy.deepcopy(data), panels))


def test_two_cube_side_condition_boundary(panels):
    # BC 80/100; SI-E 70 = genau 10 pp (nicht mehr als 10) → nein; SI-K 69 → ja
    k = {("SI-E", 1, "two_cube_validation"): 70, ("SI-K", 1, "two_cube_validation"): 69}
    res = sa.analyze(make_data(panels, k=k), panels)
    rows = {(r["arm"], r["parent"]): r for r in res["two_cube_side_condition"]["rows"]}
    assert rows[("SI-E", 1)]["exceeds_10pp"] is False
    assert rows[("SI-K", 1)]["exceeds_10pp"] is True
    assert rows[("SI-K", 1)]["drop_pp"] == pytest.approx(11.0)
    assert res["two_cube_side_condition"]["any_exceeded"] is True
    assert sa.two_cube_drop_exceeded(90, 80, 100) is False


def test_data_volumes_and_gate_report(panels):
    data = make_data(panels)
    run_of(data, "SI-K", 2)["prefix_frames"] = 5_999   # 65.999 / 60.000 < 1,10
    run_of(data, "SI-K", 3)["prefix_families"] = 9
    res = sa.analyze(data, panels)
    ratio = {r["parent"]: r for r in res["data_volumes"] if r["arm"] == "SI-K/SI-E"}
    assert ratio[1]["self_frame_ratio"] == pytest.approx(69_000 / 60_000)
    assert ratio[1]["gate_frames_met"] and ratio[1]["gate_families_met"]
    assert not ratio[2]["gate_frames_met"]
    run_of(data, "SI-K", 2)["prefix_frames"] = 6_000   # genau 1,10
    assert {r["parent"]: r for r in sa.analyze(data, panels)["data_volumes"]
            if r["arm"] == "SI-K/SI-E"}[2]["gate_frames_met"]
    assert not ratio[3]["gate_families_met"]
    si_k = next(r for r in res["data_volumes"] if (r["arm"], r["parent"]) == ("SI-K", 1))
    assert si_k["self_frames"] == 69_000


def test_costs_separated(panels):
    res = sa.analyze(make_data(panels), panels)
    assert res["costs"]["total_updates"] == 30_000
    assert res["costs"]["pool"]["episodes"] == 1200
    assert len(res["costs"]["runs"]) == 6


def test_bc_determinism_reported_not_decisive(panels):
    data = make_data(panels)
    row = next(r for r in data["bc_determinism"] if r["parent"] == 2)
    row["rerun_success"] = not row["n2_2_success"]
    res = sa.analyze(data, panels)
    det = {r["parent"]: r for r in res["bc_determinism"]["rows"]}
    assert det[2]["matches"] == 9 and det[2]["mismatch_families"] == [row["scene_seed"]]
    assert res["bc_determinism"]["all_match"] is False
    assert det[1]["matches"] == 10


def test_seed_count_inputs_feed_b3(panels):
    k = {("SI-K", 1, "validation_normal"): 40, ("SI-K", 2, "validation_normal"): 35,
         ("SI-K", 3, "validation_normal"): 32}
    res = sa.analyze(make_data(panels, k=k), panels)
    inp = res["seed_count_inputs"]
    assert inp["delta"] == 0.05 and inp["eval_families"] == 100
    assert inp["pilot_differences"] == pytest.approx([0.10, 0.05, 0.02])
    assert inp["discordance_rate"] == pytest.approx((0.10 + 0.05 + 0.02) / 3)
    plan = sc.plan(delta=inp["delta"], pilot_differences=inp["pilot_differences"],
                   eval_families=inp["eval_families"], discordance_rate=inp["discordance_rate"])
    assert plan["n_required"] >= sc.MIN_SEEDS
    assert "--delta 0.05" in inp["command"]


# --------------------------------------------------------------------------- Vertrag

@pytest.mark.parametrize("seed", [2100001500, 2100001649, 2100001650, 2100003149])
def test_test_family_rejected_first(panels, seed):
    data = make_data(panels)
    data["schema"] = "falsch"              # Testfamilie wird vor allem anderen erkannt
    data["evaluations"][0]["scene_seed"] = seed
    with pytest.raises(sa.TestFamilyError):
        sa.analyze(data, panels)


def test_test_panel_and_determinism_test_family_rejected(panels):
    data = make_data(panels)
    data["evaluations"][0]["panel"] = "test_normal"
    with pytest.raises(sa.TestFamilyError):
        sa.analyze(data, panels)
    data = make_data(panels)
    data["bc_determinism"][0]["scene_seed"] = 2100001600
    with pytest.raises(sa.TestFamilyError):
        sa.analyze(data, panels)


def _mutate(panels, fn):
    data = make_data(panels)
    fn(data)
    return data


VIOLATIONS = {
    "schema": lambda d: d.update(schema=b1.INPUT_SCHEMA),
    "missing_family": lambda d: d["evaluations"].pop(),
    "duplicate_family": lambda d: d["evaluations"].append(dict(d["evaluations"][0])),
    "foreign_family": lambda d: d["evaluations"][0].update(scene_seed=2100003650),
    "unknown_arm": lambda d: d["evaluations"][0].update(arm="AC-IL"),
    "round_field": lambda d: d["evaluations"][0].update(round=4),
    "success_not_bool": lambda d: d["evaluations"][0].update(success=1),
    "aborted_run": lambda d: d["runs"][0].update(status="aborted"),
    "missing_run": lambda d: d["runs"].pop(),
    "duplicate_run": lambda d: d["runs"].append(dict(d["runs"][0])),
    "updates": lambda d: d["runs"][0].update(updates=4999),
    "minibatch_seed": lambda d: d["runs"][0].update(minibatch_seed=7700),
    "demo_fraction": lambda d: d["runs"][0].update(demo_fraction=0.6),
    "checkpoint_sha": lambda d: d["runs"][0].update(checkpoint_sha256="x"),
    "same_checkpoint": lambda d: d["runs"][1].update(checkpoint_sha256=d["runs"][0]["checkpoint_sha256"]),
    "si_e_prefix": lambda d: d["runs"][0].update(prefix_frames=10),
    "success_pool_differs": lambda d: d["runs"][1].update(self_success_frames=60_001),
    "selection_differs": lambda d: d["runs"][1].update(selection_sha256=_sha("d")),
    "prefix_families_gt_episodes": lambda d: d["runs"][1].update(prefix_families=41),
    "negative_runtime": lambda d: d["runs"][0].update(update_runtime_s=-1.0),
    "pool_size": lambda d: d["pool"].update(episodes=1199),
    "pool_missing": lambda d: d.pop("pool"),
    "determinism_count": lambda d: d["bc_determinism"].pop(),
    "determinism_inconsistent": lambda d: d["bc_determinism"][0].update(
        n2_2_success=not d["bc_determinism"][0]["n2_2_success"]),
    "determinism_two_cube_panel": lambda d: d["bc_determinism"][0].update(panel="two_cube_validation"),
    "determinism_foreign": lambda d: d["bc_determinism"][0].update(scene_seed=2100003150),
}


@pytest.mark.parametrize("name", sorted(VIOLATIONS))
def test_contract_violations(panels, name):
    with pytest.raises(sa.ContractError):
        sa.analyze(_mutate(panels, VIOLATIONS[name]), panels)


def test_missing_cell(panels):
    data = make_data(panels)
    data["evaluations"] = [r for r in data["evaluations"]
                           if not (r["arm"] == "BC" and r["parent"] == 3 and r["panel"] == "two_cube_validation")]
    with pytest.raises(sa.ContractError, match="fehlt"):
        sa.analyze(data, panels)


# --------------------------------------------------------------------------- Kommandozeile

def test_cli_writes_hashes_and_markdown(panels, tmp_path):
    inp = tmp_path / "si_pilot_outcomes.json"
    inp.write_text(json.dumps(make_data(panels)), encoding="utf-8")
    out, md = tmp_path / "analysis.json", tmp_path / "analysis.md"
    assert sa.main(["analyze", "--input", str(inp), "--output", str(out), "--markdown", str(md)]) == 0
    res = json.loads(out.read_text(encoding="utf-8"))
    assert res["script_sha256"] == b1.sha256_file(HERE / "si_pilot_analysis.py")
    assert res["input_sha256"] == b1.sha256_file(inp)
    assert res["inherited_from"]["sha256"] == sa.B1_SHA256
    text = md.read_text(encoding="utf-8")
    assert "SI-K − SI-E" in text and "Nebenbedingung" in text


def test_cli_hash(capsys):
    assert sa.main(["hash"]) == 0
    assert capsys.readouterr().out.strip() == b1.sha256_file(HERE / "si_pilot_analysis.py")
