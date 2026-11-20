"""Tests für seed_count.py (B-3) auf Beispielwerten, ohne Pilotdaten."""
import json
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seed_count as sc  # noqa: E402


# --------------------------------------------------------------------------- Verteilungen gegen Tabellenwerte

@pytest.mark.parametrize("p, df, expected", [
    (0.975, 1, 12.706205), (0.975, 2, 4.302653), (0.975, 3, 3.182446),
    (0.975, 9, 2.262157), (0.975, 30, 2.042272), (0.95, 5, 2.015048), (0.025, 4, -2.776445),
])
def test_t_quantiles(p, df, expected):
    assert sc.t_ppf(p, df) == pytest.approx(expected, abs=2e-6)


@pytest.mark.parametrize("p, expected", [(0.975, 1.959964), (0.8, 0.841621), (0.5, 0.0)])
def test_normal_quantiles(p, expected):
    assert sc.norm_ppf(p) == pytest.approx(expected, abs=2e-6)


@pytest.mark.parametrize("p, df, expected", [
    (0.2, 2, -2 * math.log(0.8)), (0.05, 9, 3.325113), (0.95, 1, 3.841459), (0.975, 10, 20.483177),
    (0.2, 3, 1.005174),
])
def test_chi2_quantiles(p, df, expected):
    assert sc.chi2_ppf(p, df) == pytest.approx(expected, abs=2e-5)


def test_betainc_symmetry_and_bounds():
    assert sc.betainc(2.5, 2.5, 0.5) == pytest.approx(0.5, abs=1e-12)
    assert sc.betainc(1.0, 1.0, 0.3) == pytest.approx(0.3, abs=1e-12)
    assert sc.betainc(3.0, 2.0, 0.0) == 0.0 and sc.betainc(3.0, 2.0, 1.0) == 1.0


# --------------------------------------------------------------------------- Teststärke

def test_power_reference_value():
    # Einstichproben-/gepaarter t-Test, d = 1, n = 10, α = 0,05 zweiseitig: 0,8031 (G*Power)
    assert sc.paired_t_power(10, 0.10, 0.10) == pytest.approx(0.8031, abs=5e-4)


def test_power_without_effect_equals_alpha():
    assert sc.paired_t_power(6, 1e-12, 0.1, alpha=0.05) == pytest.approx(0.05, abs=1e-4)


@pytest.mark.parametrize("n, delta, sd", [(4, 0.10, 0.08), (5, 0.10, 0.12), (8, 0.10, 0.15)])
def test_power_matches_monte_carlo(n, delta, sd):
    rng = np.random.default_rng(20261119)
    reps = 400_000
    x = rng.normal(delta, sd, size=(reps, n))
    t = x.mean(axis=1) / (x.std(axis=1, ddof=1) / math.sqrt(n))
    crit = sc.t_ppf(0.975, n - 1)
    mc = float(np.mean(np.abs(t) > crit))
    assert sc.paired_t_power(n, delta, sd) == pytest.approx(mc, abs=0.004)


@pytest.mark.parametrize("sd, expected", [(0.10, 10), (0.20, 34)])
def test_n_for_power_reference(sd, expected):
    # d = 1 → 10, d = 0,5 → 34 (33,37 aufgerundet)
    assert sc.n_for_power(0.10, sd) == expected


@pytest.mark.parametrize("sd", [0.03, 0.07, 0.11, 0.16])
def test_n_for_power_is_minimal(sd):
    n = sc.n_for_power(0.10, sd)
    assert sc.paired_t_power(n, 0.10, sd) >= 0.80
    if n > 2:
        assert sc.paired_t_power(n - 1, 0.10, sd) < 0.80


def test_power_monotone_in_n_and_effect():
    powers = [sc.paired_t_power(n, 0.10, 0.12) for n in range(3, 15)]
    assert all(a < b for a, b in zip(powers, powers[1:]))
    assert sc.paired_t_power(8, 0.05, 0.12) < sc.paired_t_power(8, 0.10, 0.12)


def test_min_detectable_effect_inverts_power():
    mde = sc.min_detectable_effect(7, 0.12)
    assert sc.paired_t_power(7, mde, 0.12) == pytest.approx(0.80, abs=1e-6)


def test_precision():
    assert sc.ci_halfwidth(10, 0.1) == pytest.approx(2.262157 * 0.1 / math.sqrt(10), abs=1e-6)
    n = sc.n_for_precision(0.05, 0.1)
    assert sc.ci_halfwidth(n, 0.1) <= 0.05 < sc.ci_halfwidth(n - 1, 0.1)


# --------------------------------------------------------------------------- Streuung

def test_pilot_sd_and_upper_limit():
    s, df = sc.pilot_sd([0.0, 0.1, 0.2])
    assert (s, df) == (pytest.approx(0.1), 2)
    upper = sc.sd_upper_limit(s, df, 0.80)
    assert upper == pytest.approx(0.1 * math.sqrt(2 / (-2 * math.log(0.8))), abs=1e-6)  # Faktor 2,117
    assert sc.sd_upper_limit(s, df, 0.90) > upper > s


def test_scene_floor():
    assert sc.scene_sd_floor(150, 0.30) == pytest.approx(math.sqrt(0.30 / 150))
    assert sc.scene_sd_floor(100, 0.0) == 0.0


def test_floor_binds_when_pilot_spread_is_zero():
    out = sc.plan(pilot_differences=[0.1, 0.1, 0.1], eval_families=150, discordance_rate=0.30)
    assert out["spread"]["sd_point"] == 0.0
    assert out["spread"]["floor_binding"] is True
    assert out["spread"]["sd_plan"] == pytest.approx(math.sqrt(0.30 / 150))
    assert out["n_power_at_sd_point"] is None


def test_zero_spread_without_floor_rejected():
    with pytest.raises(sc.InputError):
        sc.plan(pilot_differences=[0.1, 0.1, 0.1])


# --------------------------------------------------------------------------- Plan und Budget

def test_plan_uses_upper_limit_not_point():
    out = sc.plan(pilot_differences=[0.05, 0.10, 0.15])  # s = 0,05
    sp = out["spread"]
    assert sp["sd_plan"] == pytest.approx(sp["sd_upper"]) and sp["sd_upper"] > sp["sd_point"]
    assert out["n_required"] == sc.n_for_power(0.10, sp["sd_upper"])
    assert out["n_required"] >= out["n_power_at_sd_point"]
    assert out["at_required"]["power"] >= 0.80


def test_min_rule_more_than_three_seeds():
    out = sc.plan(sd_assumed=0.02)
    assert out["n_power"] < sc.MIN_SEEDS
    assert out["n_required"] == sc.MIN_SEEDS == 4
    assert out["power_table"][0]["n"] == 4


def test_precision_target_can_dominate():
    out = sc.plan(sd_assumed=0.10, target_halfwidth=0.04)
    assert out["n_precision"] > out["n_power"]
    assert out["n_required"] == out["n_precision"]


def test_budget_feasible():
    out = sc.plan(sd_assumed=0.10, cost_components={"bc_parent": 2.0, "ac_runs": 1.5},
                  budget_hours=40.0, fixed_hours=5.0)
    assert out["budget"]["n_affordable"] == 10
    assert out["decision"] == "machbar" and out["n_recommended"] == 10
    assert out["budget"]["cost_at_required_hours"] == pytest.approx(40.0)


def test_budget_insufficient_is_not_silently_reduced():
    out = sc.plan(sd_assumed=0.10, cost_components={"bc_parent": 2.0, "ac_runs": 1.5},
                  budget_hours=30.0, fixed_hours=5.0)
    b = out["budget"]
    assert b["n_affordable"] == 7
    assert out["decision"] == "Budget reicht nicht"
    assert out["n_recommended"] is None and "AGENTS.md §1" in out["user_decision_required"]
    assert b["at_affordable"]["power"] < 0.80
    assert b["at_affordable"]["min_detectable_effect"] > 0.10
    assert b["at_affordable"]["below_min_rule"] is False


def test_budget_below_min_rule_flagged():
    out = sc.plan(sd_assumed=0.02, cost_components={"x": 10.0}, budget_hours=30.0)
    assert out["budget"]["n_affordable"] == 3
    assert out["decision"] == "Budget reicht nicht"
    assert out["budget"]["at_affordable"]["below_min_rule"] is True


def test_affordable_seeds_edges():
    assert sc.affordable_seeds(10.0, 2.5) == 4
    assert sc.affordable_seeds(3.0, 2.5, fixed_hours=5.0) == 0
    assert sc.cost_per_seed({"a": 1.25, "b": 0.75}) == 2.0


@pytest.mark.parametrize("kwargs", [
    {"delta": 0.0, "sd_assumed": 0.1},
    {"delta": -0.1, "sd_assumed": 0.1},
    {"sd_assumed": 0.1, "pilot_differences": [0.0, 0.1]},
    {},
    {"pilot_differences": [0.1]},
    {"pilot_differences": [0.1, 1.5]},
    {"pilot_differences": [0.1, float("nan")]},
    {"sd_assumed": -0.1},
    {"sd_assumed": 0.1, "eval_families": 150},
    {"sd_assumed": 0.1, "eval_families": 150, "discordance_rate": 1.2},
    {"sd_assumed": 0.1, "budget_hours": 10.0},
    {"sd_assumed": 0.1, "cost_components": {"a": -1.0}, "budget_hours": 10.0},
    {"sd_assumed": 0.1, "power": 1.0},
])
def test_invalid_inputs_rejected(kwargs):
    with pytest.raises(sc.InputError):
        sc.plan(**kwargs)


def test_plan_is_deterministic():
    kw = dict(pilot_differences=[0.02, 0.09, 0.13], eval_families=150, discordance_rate=0.25,
              cost_components={"a": 3.0}, budget_hours=50.0)
    assert json.dumps(sc.plan(**kw), sort_keys=True) == json.dumps(sc.plan(**kw), sort_keys=True)


# --------------------------------------------------------------------------- Pilotauswertung (synthetisch)

def _synthetic_pilot_result(k_il=(40, 32, 30), k_neu=(30, 30, 30)):
    import pilot_analysis as pa
    import test_pilot_analysis as tpa
    panels = pa.load_panels()
    k = {}
    for parent, a, b in zip(pa.PARENTS, k_il, k_neu):
        k[("AC-IL", parent, "validation_normal", 4)] = a
        k[("AC-neu", parent, "validation_normal", 4)] = b
    return pa.analyze(tpa.make_data(panels, k=k), panels)


def test_reads_pilot_analysis_output():
    pilot = sc.read_pilot_analysis(_synthetic_pilot_result())
    assert pilot["differences"] == pytest.approx([0.10, 0.02, 0.0])
    assert pilot["parents"] == [1, 2, 3]
    # verschachtelte Erfolge: diskordant genau |k_a − k_b|
    assert pilot["discordance_rate_per_parent"] == pytest.approx([0.10, 0.02, 0.0])
    assert pilot["n_families_pilot"] == 100 and pilot["any_aborted"] is False


def test_pilot_analysis_rejects_test_panels_and_wrong_version():
    result = _synthetic_pilot_result()
    bad = json.loads(json.dumps(result))
    bad["panel_sizes"]["test_normal"] = 150
    with pytest.raises(sc.TestFamilyError):
        sc.read_pilot_analysis(bad)
    bad = json.loads(json.dumps(result))
    bad["contrasts"][0]["panel"] = "test_hard"
    with pytest.raises(sc.TestFamilyError):
        sc.read_pilot_analysis(bad)
    bad = json.loads(json.dumps(result))
    bad["analysis_version"] = "pilot_analysis_v0"
    with pytest.raises(sc.InputError):
        sc.read_pilot_analysis(bad)


def test_pilot_analysis_inconsistent_discordance_rejected():
    bad = json.loads(json.dumps(_synthetic_pilot_result()))
    primary = next(c for c in bad["contrasts"] if c["role"] == "primär")
    primary["per_parent"][0]["discordant"]["both"] += 1
    with pytest.raises(sc.InputError):
        sc.read_pilot_analysis(bad)


# --------------------------------------------------------------------------- Kommandozeile

def test_cli_example(capsys):
    assert sc.main(["example", "--json"]) == 0
    grid = json.loads(capsys.readouterr().out)
    assert grid["label"] == sc.EXAMPLE_LABEL
    by_sd = {r["sd"]: r for r in grid["rows"]}
    assert by_sd[0.10]["n_required"] == 10 and by_sd[0.05]["n_required"] >= 4


def test_cli_plan_from_pilot_analysis(tmp_path, capsys):
    path = tmp_path / "pilot.json"
    path.write_text(json.dumps(_synthetic_pilot_result(), ensure_ascii=False), encoding="utf-8")
    out = tmp_path / "plan.json"
    args = ["plan", "--pilot-analysis", str(path), "--eval-families", "150",
            "--cost", "bc=2", "--cost", "ac=1.5", "--budget-hours", "60", "--out", str(out)]
    assert sc.main(args) == 0
    first = out.read_bytes()
    assert sc.main(args) == 0
    assert out.read_bytes() == first
    result = json.loads(first)
    assert result["source"]["parents"] == [1, 2, 3]
    assert len(result["source"]["sha256"]) == 64
    assert result["spread"]["discordance_rate"] == pytest.approx(0.04)
    assert result["n_required"] >= 4
    assert "Seedzahl" in capsys.readouterr().out


def test_cli_rejects_invalid(capsys):
    assert sc.main(["plan", "--sd", "0.1", "--budget-hours", "5"]) == 2
    assert "FEHLER" in capsys.readouterr().err
