"""Tests für B-2 (failure_phases.py) auf synthetischen Daten, ohne Rohdaten."""

import math

import numpy as np
import pytest

import failure_phases as fp


SPLITS = [
    {"id": "calibration", "first": 2100000000, "last": 2100000099},
    {"id": "critic_data", "first": 2100000100, "last": 2100000399},
    {"id": "test_normal", "first": 2100001500, "last": 2100001649},
]


def state(a=(0, 0, 0.02), b=(0.1, 0, 0.02), c=(0.2, 0, 0.02), eef=(0, 0, 0.2)):
    s = np.zeros(40)
    s[0:3], s[3:6], s[6:9], s[21:24] = a, b, c, eef
    return s


def test_split_guard_rejects_test_and_foreign_scenes():
    fp.check_split(2100000000, "calibration", SPLITS)
    fp.check_split(2100000399, "critic_data", SPLITS)
    with pytest.raises(fp.TestFamilyError):
        fp.check_split(2100001500, "critic_data", SPLITS)
    with pytest.raises(fp.TestFamilyError):
        fp.check_split(2100000100, "calibration", SPLITS)


def test_final_segment_is_longest_constant_suffix():
    stage = [1, 1, 1, 2, 2, 2, 2]
    phase = [0, 4, 4, 0, 0, 3, 3]
    retreat = [0, 0, 0, 1, 0, 0, 0]
    assert fp.final_segment_start(stage, phase, retreat) == 5
    assert fp.final_segment_start([1, 1], [2, 2], [0, 0]) == 0
    # Rückzug trennt Segmente trotz gleicher Phase
    assert fp.final_segment_start([2, 2, 2], [0, 0, 0], [1, 0, 0]) == 1


def test_grasp_correction_is_gripper_to_carried_cube():
    group, e = fp.needed_correction(state(b=(0.10, 0.02, 0.02), eef=(0.07, 0.06, 0.1)), 1, 1, False)
    assert group == "Greifen (0–3)"
    assert np.allclose(e, [0.03, -0.04])
    # Stufe 2 trägt Würfel C
    _, e2 = fp.needed_correction(state(c=(0.3, 0.0, 0.02), eef=(0.25, 0.0, 0.1)), 2, 0, False)
    assert np.allclose(e2, [0.05, 0.0])


def test_placement_correction_subtracts_tolerance():
    group, e = fp.needed_correction(state(a=(0, 0, 0.02), b=(0.029, 0, 0.06)), 1, 5, False)
    assert group == "Ablage (4–6)"
    assert np.allclose(e, [-0.020, 0.0])
    _, inside = fp.needed_correction(state(a=(0, 0, 0.02), b=(0.005, 0.005, 0.06)), 1, 6, False)
    assert np.all(inside == 0)
    assert fp.needed_correction(state(), 2, 0, True) == ("Rückzug", None)


def test_reach_respects_state_dependent_width():
    parent = np.array([[1.0, 0.0], [0.1, -0.3], [0.02, 0.5]])
    # δ = 0,20: Breiten x = 0,20; 0,05; 0,01  → 0,26 · 0,05 m; y = 0; 0,15; 0,20 → 0,35 · 0,05 m
    assert np.allclose(fp.reach(parent, 0.20), [0.013, 0.0175])
    assert np.allclose(fp.reach(parent, 0.05), [0.05 * 0.11, 0.05 * 0.10])
    assert np.allclose(fp.reach(np.zeros((5, 2)), 0.20), [0.0, 0.0])


def test_ratio_and_categories():
    assert fp.reach_ratio([0.0, 0.0], [0.0, 0.0]) == 0.0
    assert fp.reach_ratio([0.01, 0.0], [0.02, 0.0]) == pytest.approx(0.5)
    assert fp.reach_ratio([0.01, 0.03], [0.02, 0.01]) == pytest.approx(3.0)
    assert math.isinf(fp.reach_ratio([0.0, 0.01], [0.5, 0.0]))
    assert [fp.category(q) for q in (0.0, 0.5, 1.0, 1.01, math.inf)] == [
        "keine nötig", "innerhalb", "innerhalb", "außerhalb", "außerhalb"]


def test_end_flags():
    tower = state(a=(0, 0, 0.02), b=(0.004, 0, 0.061), c=(0.2, 0, 0.1))
    flags = fp.end_flags(tower, 2)
    assert flags == dict(carried_lifted=True, carried_on_table=False, carried_on_base=False,
                         base_intact=True)
    stacked = fp.end_flags(state(a=(0, 0, 0.02), b=(0.004, 0, 0.061), c=(0.0, 0.003, 0.1)), 2)
    assert stacked["carried_on_base"] and stacked["carried_lifted"] and not stacked["carried_on_table"]
    broken = state(a=(0, 0, 0.02), b=(0.05, 0, 0.02), c=(0.2, 0, 0.02))
    assert fp.end_flags(broken, 2)["base_intact"] is False
    assert fp.end_flags(broken, 1)["base_intact"] is True


def test_analyze_episode_end_to_end():
    n = 10
    arrays = dict(
        stage=np.array([1] * 4 + [2] * 6, np.int8),
        phase=np.array([5, 5, 6, 6, 0, 0, 1, 1, 1, 1], np.int8),
        retreat=np.zeros(n, bool),
        parent_action=np.zeros((n, 7)),
        next_critic_state=np.tile(state(c=(0.2, 0.0, 0.02), eef=(0.19, 0.0, 0.05)), (n, 1)),
    )
    arrays["critic_state"] = arrays["next_critic_state"].copy()
    arrays["critic_state"][4, 3:6] = (0.0, 0.0, 0.06)  # B auf A beim Eintritt in Stufe 2
    arrays["parent_action"][6:, 0] = 0.4  # b_x = 0,20 bei δ = 0,20; 0,05 bei δ = 0,05
    row = fp.analyze_episode(arrays)
    assert (row["end_stage"], row["end_phase"], row["segment_frames"]) == (2, 1, 4)
    assert row["correction_mm"] == pytest.approx(10.0)
    # R_x(0,20) = 0,05 · 4 · 0,20 = 0,04 m → q = 0,25; R_x(0,05) = 0,01 m → q = 1
    assert row["ratio"]["0.2"] == pytest.approx(0.25)
    assert row["ratio"]["0.05"] == pytest.approx(1.0)
    assert row["rest_share"] == 0.0
    assert row["base_intact_at_stage2_entry"] is True
    assert row["base_intact"] is False  # am Ende liegt B neben A
    arrays["next_critic_state"][-1, 0] = np.nan
    with pytest.raises(ValueError):
        fp.analyze_episode(arrays)


def test_tables_keep_full_denominators():
    rows = []
    for scene in (1, 2):
        for p in fp.PARENTS:
            success = scene == 1 and p == 1
            rows.append(dict(scene_seed=scene, parent_seed=p, success=success,
                             termination="success" if success else "horizon",
                             reached_second_placement=p != 3, max_stable_frames=50 if success else 0))
    out = fp.outcome_table(rows)
    assert out["gesamt"]["episodes"] == 6 and out["gesamt"]["failures"] == 5
    assert out["1"]["failures"] == 1 and out["3"]["fail_stage1"] == 2
    fam = fp.family_table(rows)
    assert fam == dict(families=2, failing_parents={"0": 0, "1": 0, "2": 1, "3": 1})
    with pytest.raises(ValueError):
        fp.family_table(rows[:-1])
