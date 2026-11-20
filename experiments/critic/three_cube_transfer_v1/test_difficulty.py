"""Analytische Beispiele ohne Szenenseeds, Simulator oder Policy."""

import json
import math

import numpy as np
import pytest

from difficulty import initial_features


def test_geometry_and_reproducibility():
    positions = np.array([[0.02, -0.03, 0.82], [0.14, -0.03, 0.82], [0.02, 0.06, 0.82]])
    original = positions.copy()
    center = np.array([0.05, -0.07, 0.8])
    result = initial_features(positions, center)
    assert result["version"] == "difficulty_v1"
    assert {k: v for k, v in result.items() if k != "version"} == pytest.approx({
        "b_to_base_xy_m": 0.12,
        "c_to_tower_xy_m": 0.09,
        "transport_total_xy_m": 0.21,
        "min_pair_gap_xy_m": 0.05,
        "base_x_from_table_center_m": -0.03,
        "base_y_from_table_center_m": 0.04,
        "max_radius_from_table_center_m": math.hypot(0.03, 0.13),
    })
    assert json.loads(json.dumps(result, allow_nan=False)) == initial_features(positions, center)
    np.testing.assert_array_equal(positions, original)
    shift = np.array([0.5, -0.25, 0.10])
    shifted = initial_features(positions + shift, center + shift)
    for key in result.keys() - {"version"}:
        assert shifted[key] == pytest.approx(result[key])


@pytest.mark.parametrize(("dx", "dy", "gap"), [
    (0.07, 0.08, 0.05), (0.04, 0.02, 0.0), (0.02, 0.01, 0.0),
])
def test_closest_pair_can_be_b_and_c(dx, dy, gap):
    positions = [(-0.16, -0.16, 0.82), (0, 0, 0.82), (dx, dy, 0.82)]
    assert initial_features(positions, (0, 0, 0.8))["min_pair_gap_xy_m"] == pytest.approx(gap)


@pytest.mark.parametrize(("positions", "center"), [
    ([(0, 0, 0)] * 2, (0, 0, 0)), ([(0, 0, 0)] * 4, (0, 0, 0)),
    ([(0, 0)] * 3, (0, 0, 0)), ([(0, 0, math.nan)] * 3, (0, 0, 0)),
    ([(0, 0, 0)] * 3, (math.inf, 0, 0)),
])
def test_rejects_invalid_geometry(positions, center):
    with pytest.raises(ValueError):
        initial_features(positions, center)
