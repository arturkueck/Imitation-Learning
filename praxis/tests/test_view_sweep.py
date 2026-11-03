"""Broad-view geometry and no silent reference fallback for visual exploration."""
from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'praxis/src'))
from active_view.view_sweep import view_change,inspect_or_probe
from active_view.collision import Check
from types import SimpleNamespace

def test_large_joint_motion_is_not_confused_with_new_camera_baseline():
    c=view_change([0,0,1],[0,0,1],[0,0,0]);assert c['baseline_m']==0 and c['angle_deg']==0
    c=view_change([1,0,0],[0,1,0],[0,0,0]);assert abs(c['angle_deg']-90)<1e-8 and abs(c['baseline_m']-np.sqrt(2))<1e-8

def test_visual_gate_never_silently_uses_reference_world():
    planner=SimpleNamespace(checker=SimpleNamespace(world=SimpleNamespace(source='reference')))
    assert inspect_or_probe(planner,None,np.zeros(7))['reason']=='reference_geometry_is_not_visual_clearance'

def test_unverified_initial_arm_cannot_move_to_observe_unknown_space():
    checker=SimpleNamespace(world=SimpleNamespace(source='visual'),check=lambda q:Check(False,-1,'unknown_space'))
    result=inspect_or_probe(SimpleNamespace(checker=checker),None,np.zeros(7))
    assert result['stage']=='blocked' and result['detail']=='unknown_space' and 'plan' not in result
