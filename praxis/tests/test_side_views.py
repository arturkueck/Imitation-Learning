from pathlib import Path
import sys
import numpy as np
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'praxis/src'))
from active_view.side_views import side_frame,aimed_pose,optical_axis_error

def test_robot_right_and_left_are_opposite_and_base_is_backward():
    frame=side_frame(np.array([-.6,0,.8]),np.array([0,0,.85]))
    np.testing.assert_allclose(frame['right'],[0,-1,0]);np.testing.assert_allclose(frame['left'],[0,1,0]);np.testing.assert_allclose(frame['base'],[-1,0,0])

def test_side_translations_always_aim_back_to_focus_even_when_rolling_wrist():
    focus=np.array([0.,0.,.85])
    for p in [np.array([0,-.3,.95]),np.array([0,.3,.95]),np.array([-.3,0,.95])]:
        for roll in [0,np.pi/2,-np.pi/2,np.pi]:
            R=aimed_pose(p,focus,roll)
            np.testing.assert_allclose(R.T@R,np.eye(3),atol=1e-12)
            assert optical_axis_error(p,R,focus)<1e-5

def test_optical_axis_error_rejects_camera_looking_away():
    p=np.array([.3,0,.95]);focus=np.array([0,0,.85]);R=aimed_pose(p,focus)
    wrong=R@np.diag([-1,1,-1]);assert optical_axis_error(p,wrong,focus)>179.9
