"""Synthetische Tests für N2-2 (ohne Simulation, ohne echte Critic-Daten)."""

import json
import time

import numpy as np
import pytest

import critic_validation as cv


def test_phase_points_first_frame_per_stage_and_phase():
    stage = [1, 1, 1, 1, 2, 2, 2]
    phase = [0, 0, 1, 1, 0, 1, 1]
    assert cv.phase_points(stage, phase) == {"stage1_phase0": 0, "stage1_phase1": 2,
                                             "stage2_phase0": 4, "stage2_phase1": 5}


def test_auc_ties_order_and_bootstrap_weights():
    scores = np.array([0.9, 0.8, 0.3, 0.1])
    labels = np.array([True, True, False, False])
    m = cv.auc_matrix(scores, labels)
    assert cv.weighted_auc(m, np.ones(2), np.ones(2)) == 1.0
    m = cv.auc_matrix(-scores, labels)
    assert cv.weighted_auc(m, np.ones(2), np.ones(2)) == 0.0
    m = cv.auc_matrix(np.zeros(4), labels)
    assert cv.weighted_auc(m, np.ones(2), np.ones(2)) == 0.5
    # Häufigkeitsgewichte entsprechen duplizierten Beobachtungen.
    scores = np.array([0.6, 0.2, 0.4, 0.5])
    labels = np.array([True, True, False, False])
    weighted = cv.weighted_auc(cv.auc_matrix(scores, labels), np.array([2.0, 1.0]), np.array([1.0, 3.0]))
    expanded = cv.auc_matrix(np.array([0.6, 0.6, 0.2, 0.4, 0.5, 0.5, 0.5]),
                             np.array([True, True, True, False, False, False, False]))
    assert np.isclose(weighted, cv.weighted_auc(expanded, np.ones(3), np.ones(4)))
    batch = cv.weighted_auc(cv.auc_matrix(scores, labels), np.array([[2.0, 1.0], [0, 0]]), np.array([[1.0, 3.0], [1, 1]]))
    assert np.isclose(batch[0], weighted) and np.isnan(batch[1])


def test_ece_known_values():
    prediction = np.array([0.05, 0.05, 0.95, 0.95, 1.2])
    target = np.array([0.0, 0.1, 1.0, 0.9, 1.0])
    value, table = cv.ece(prediction, target, 10)
    # Klasse 0: |0,05 − 0,05| = 0; Klasse 9: |(0,95+0,95+1,2)/3 − 0,9667| = 0,0667
    assert np.isclose(value, 3 / 5 * abs((0.95 + 0.95 + 1.2) / 3 - (1.0 + 0.9 + 1.0) / 3))
    assert [t["bin"] for t in table] == [0, 9]


def records(informative, families=60, points=("stage1_phase0", "stage1_phase3", "stage2_phase2"), seed=0):
    rng = np.random.default_rng(seed)
    out = []
    for family in range(families):
        success = family % 2 == 0
        for k, point in enumerate(points):
            ret = 0.995 ** (400 - 100 * k) if success else 0.0
            value = ret + rng.normal(0, 0.02) if informative else 0.4
            out.append(dict(family=family, point=point, value=value, discounted_return=ret, success=success,
                            baseline_return=0.5 * 0.995 ** (400 - 100 * k)))
    return out


def test_assess_passes_informative_and_fails_phase_only():
    good = cv.assess(records(True))
    assert good["eligible_points"] == 3 and good["weighted_auc"] > 0.95
    assert good["checks"]["better_than_phase"] and good["passed"]
    flat = cv.assess(records(False))
    assert flat["weighted_auc"] == 0.5 and not flat["checks"]["more_than_phase"] and not flat["passed"]


def test_assess_not_assessable_with_single_point_and_nonfinite():
    single = cv.assess(records(True, points=("stage1_phase0",)))
    assert not single["checks"]["assessable"] and not single["passed"]
    broken = records(True)
    broken[0]["value"] = float("nan")
    result = cv.assess(broken)
    assert not result["finite"] and not result["passed"]


def test_assess_is_reproducible():
    a, b = cv.assess(records(True, seed=3)), cv.assess(records(True, seed=3))
    assert json.dumps(a) == json.dumps(b)


def test_baseline_table_and_fallback():
    def episode(stages, phases, success):
        n = len(stages)
        value = 0.995 ** np.arange(n - 1, -1, -1) if success else np.zeros(n)
        return dict(stage=np.array(stages), phase=np.array(phases), discounted_return=value), success
    table, overall = cv.baseline_table([episode([1, 1, 2], [0, 1, 0], True), episode([1, 1, 1], [0, 0, 1], False)])
    assert overall == 0.5
    assert table["stage1_phase0"]["success_rate"] == 0.5 and table["stage2_phase0"]["episodes"] == 1
    assert np.isclose(table["stage1_phase1"]["mean_return"], (0.995 + 0.0) / 2)


def test_pretraining_is_deterministic_and_measures_speed(monkeypatch, tmp_path):
    import torch
    core = cv.load_module("critic_base_core_test", cv.BASE_CORE)
    monkeypatch.setitem(cv.PRETRAIN, "updates", 200)
    monkeypatch.setitem(cv.PRETRAIN, "log_every", 100)
    torch.set_num_threads(cv.PRETRAIN["torch_threads"])
    torch.use_deterministic_algorithms(True)
    rng = np.random.default_rng(0)
    states = rng.normal(size=(5000, 40)).astype(np.float32)
    actions = rng.uniform(-1, 1, size=(5000, 4)).astype(np.float32)
    targets = (states[:, 0] > 0).astype(np.float64)
    runs = []
    for _ in range(2):
        started = time.perf_counter()
        critic, _, history, _ = cv.pretrain(torch, core, states, actions, targets, 1, time.time() + 600, tmp_path)
        runs.append((critic.state_dict(), history, time.perf_counter() - started))
    assert all(torch.equal(runs[0][0][k], runs[1][0][k]) for k in runs[0][0])
    assert [h["mean_loss"] for h in runs[0][1]] == [h["mean_loss"] for h in runs[1][1]]
    assert len(runs[0][1]) == 2 and all(np.isfinite(h["mean_loss"]) for h in runs[0][1])
    print(f"Vortraining synthetisch: {200 / runs[0][2]:.0f} Updates/s")
    other, *_ = cv.pretrain(torch, core, states, actions, targets, 2, time.time() + 600, tmp_path)
    assert not torch.equal(other.state_dict()["q1.0.weight"], runs[0][0]["q1.0.weight"])
    (tmp_path / "STOP").write_text("")
    with pytest.raises(InterruptedError):
        cv.pretrain(torch, core, states, actions, targets, 1, time.time() + 600, tmp_path)


@pytest.mark.skipif(not (cv.DATA / "summary.json").is_file(), reason="N2-1-Daten lokal nicht vorhanden")
def test_assessment_pipeline_on_critic_data_with_untrained_critic(tmp_path):
    """Technische Prüfung des Auswertungspfads auf echten N2-1-Daten eines Parents:
    zufällig initialisierter Critic, 0 Optimizerupdates, keine Validierungs- oder Testdaten."""
    import torch
    core = cv.load_module("critic_base_core_test", cv.BASE_CORE)
    episodes = cv.load_critic_data(1)
    assert len(episodes) == 300 and sum(s for _, s in episodes) == 125
    table, overall = cv.baseline_table(episodes)
    assert np.isclose(overall, 125 / 300) and table["stage1_phase0"]["episodes"] == 300
    states = np.concatenate([cv.critic_inputs(a)[0] for a, _ in episodes[:20]])
    torch.manual_seed(0)
    critic = core.TwinQ(states.mean(0), states.std(0), cv.PRETRAIN["critic_width"])
    optimizer = torch.optim.AdamW(critic.parameters(), lr=cv.PRETRAIN["critic_lr"])
    (tmp_path / "critics").mkdir()
    cv.save_critic(torch, tmp_path, 1, critic, optimizer, [dict(update=0, mean_loss=0.0, seconds=0.0)], 1.0,
                   len(states), 0.0, "test")
    loaded, meta = cv.load_critic(torch, core, tmp_path, 1)
    records = []
    for index, (arrays, success) in enumerate(episodes[:60]):
        values = cv.predict(torch, loaded, *cv.critic_inputs(arrays))
        assert np.allclose(values, cv.predict(torch, critic.eval(), *cv.critic_inputs(arrays)))
        for point, frame in cv.phase_points(arrays["stage"], arrays["phase"]).items():
            records.append(dict(family=index, point=point, value=float(values[frame]), success=success,
                                discounted_return=float(arrays["discounted_return"][frame]),
                                baseline_return=table[point]["mean_return"]))
    result = cv.assess(records)
    json.dumps(result, allow_nan=False)
    assert result["finite"] and set(result["checks"]) == {"finite", "assessable", "more_than_phase",
                                                          "better_than_phase", "calibration"}


def test_validation_panels_only():
    families = cv.panels()
    assert {k: len(v) for k, v in families.items()} == {"validation_normal": 100, "validation_hard": 50}
    seeds = families["validation_normal"] + families["validation_hard"]
    assert len(set(seeds)) == 150 and min(seeds) >= 2100000400 and max(seeds) <= 2100001499


def test_dashboard_entry():
    runs = json.loads((cv.ROOT / "monitor/training-runs.json").read_text(encoding="utf-8"))["runs"]
    entry = next(r for r in runs if r["id"] == "three-cube-transfer-v1-critic-validation")
    assert entry["directory"] == cv.OUT.relative_to(cv.ROOT).as_posix()
    assert len({r["id"] for r in runs}) == len(runs)
