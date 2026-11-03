from pathlib import Path
import sys,math
from types import SimpleNamespace
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from active_view.camera_guidance import swept_envelopes,refine_view,join_routes
from active_view.side_views import aimed_pose
from active_view.planner import Focus

class SweepChecker:
    radii=np.array([[.1]])
    world_margin=.01
    def robot_boxes(self,q):
        p=.1*np.array([np.cos(q[0]),np.sin(q[0]),0])
        return [SimpleNamespace(vertices=p[None])]

def test_fine_sweep_retains_margin_and_contains_intermediate_motion():
    c=SweepChecker();low,high=swept_envelopes(c,[0],[1.8],128)
    for i in range(128):
        for alpha in np.linspace(i/128,(i+1)/128,5):
            p=c.robot_boxes([alpha*1.8])[0].vertices[0]
            assert np.all(p-c.world_margin>=low[i]-1e-10)
            assert np.all(p+c.world_margin<=high[i]+1e-10)
    coarse_lo,coarse_hi=swept_envelopes(c,[0],[1.8],32)
    assert np.mean(high-low)<np.mean(coarse_hi-coarse_lo)

class AimChecker:
    q0=np.array([0.]);camera=0
    m=SimpleNamespace(cam_fovy=[75.])
    def __init__(self,edge_free=True,shift=0):self.edge_free=edge_free;self.shift=shift;self.edge_calls=0
    def set_q(self,q):self.q=np.array(q)
    def camera_pose(self,q):
        p=np.array([self.shift if q[0]>.5 else 0,-.35,1.])
        R=aimed_pose(p,np.array([0,0,.9]))
        if q[0]<.5:
            a=.2;R=R@np.array([[np.cos(a),0,np.sin(a)],[0,1,0],[-np.sin(a),0,np.cos(a)]])
        return p,R
    def check(self,q):return SimpleNamespace(valid=True)
    def edge(self,a,b):self.edge_calls+=1;return self.edge_free

def run_refine(c):
    planner=SimpleNamespace(checker=c,ik=lambda *a,**kw:np.array([1.]))
    return refine_view(planner,Focus(np.array([0,0,.9]),.04),np.array([0,0,1.4]),np.array([-.6,0,.8]),'right',np.array([0.]))

def test_target_refinement_requires_certified_suffix_and_restores_virtual_start():
    c=AimChecker();r=run_refine(c)
    assert r['stage']=='aimed' and r['refined']
    assert r['metrics']['optical_axis_error_deg']<1e-5
    assert c.edge_calls>0
    np.testing.assert_array_equal(c.q,c.q0)
    c=AimChecker(edge_free=False);r=run_refine(c)
    assert r['stage']=='blocked'
    assert 'refinement_suffix_not_certified' in r['rejections']

def test_refinement_does_not_accept_large_unplanned_translation():
    c=AimChecker(shift=.03);r=run_refine(c)
    assert r['stage']=='blocked'
    assert 'refinement_translation_too_large' in r['rejections']
    assert c.edge_calls==0

def test_resumed_numpy_route_is_concatenated_instead_of_broadcast_added():
    prefix=np.array([[0.,.2],[.1,.5],[.3,.8]]);suffix=np.array([[.3,.8],[.4,.9]])
    expected=np.array([[0.,.2],[.1,.5],[.3,.8],[.4,.9]])
    result=join_routes(prefix,suffix)
    np.testing.assert_array_equal(result,expected)
    np.testing.assert_array_equal(join_routes(prefix.tolist(),suffix.tolist()),expected)
    result[0][0]=10
    assert prefix[0,0]==0
    import pytest
    with pytest.raises(ValueError,match='discontinuous'):join_routes(prefix,[[.31,.8]])
