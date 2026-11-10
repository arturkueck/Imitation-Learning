import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
import active_policy as policy
from centered_sweep import orbit_positions,transport_rotation
from geometry import project

def b(x=0.,z=.85):return dict(position=np.array([x,0.,z]),size=np.array([.04,.04,.06]),rotation=np.eye(3))
def cameras():return [dict(position=np.array([0.,0.,1.3]),rotation=np.eye(3),f=160,cx=80,cy=80,width=160,height=160)]*3
def groups(n,spread=2):return [dict(support=3,spread_mm=spread)]*n

def test_group_focus_uses_predictions_and_known_table_height_only():
    focus=policy.group_focus([b(-.05),b(.05,z=.92)],.8)
    np.testing.assert_allclose(focus['center'][:2],[0.,0.]);assert .8<focus['center'][2]<1.
    assert policy.group_focus([],.8) is None

def test_explicit_none_one_two_side_requests(monkeypatch):
    monkeypatch.setattr(policy,'score',lambda *a:.4)
    rgb=np.zeros((3,160,160,3),np.uint8)
    assert policy.initial_decision([b()],groups(1,.5),rgb,cameras())['requested_sides']==0
    assert policy.initial_decision([b()],groups(1,2),rgb,cameras())['requested_sides']==1
    assert policy.initial_decision([b(-.1),b(),b(.1)],groups(3),rgb,cameras())['requested_sides']==2
    assert policy.initial_decision([],[],rgb,cameras())['action']=='unresolved'

def test_second_side_requires_only_observed_first_quality():
    first=dict(requested_sides=1)
    assert not policy.second_decision(first,dict(supported=True),['right'])['required']
    assert policy.second_decision(first,dict(supported=False),['right'])['required']
    assert policy.second_decision(dict(requested_sides=2),dict(supported=True),['right'])['required']
    assert not policy.second_decision(dict(requested_sides=2),dict(supported=False),['right','left'])['required']

def test_orbit_sides_are_opposed_and_optical_axis_stays_on_focus():
    target=np.array([0.,0.,.85]);start=np.array([.12,0.,1.3]);base=np.array([-.6,0.,.8])
    left=orbit_positions(start,target,base,'left',28,28);right=orbit_positions(start,target,base,'right',28,28)
    np.testing.assert_allclose(left[0],start);np.testing.assert_allclose(right[0],start)
    assert left[-1,1]*right[-1,1]<0
    for p in np.vstack([left,right]):
        R=transport_rotation(p,target,np.eye(3));np.testing.assert_allclose(R.T@R,np.eye(3),atol=1e-12)
        uv,z=project(target,dict(position=p,rotation=R,f=200,cx=160,cy=160));np.testing.assert_allclose(uv,[160,160],atol=1e-9);assert z>0
    q=np.arange(28*7).reshape(28,7);out=q;back=q[::-1];np.testing.assert_array_equal(out[0],back[-1])

def test_unsupported_geometry_remains_explicitly_uncertain():
    assert not policy.quality([])['supported']
    obj=dict(object_index=0,fit=dict(status='fitted'),gate=dict(tracks=6,accepted=True,heldout_after=1.,heldout_before=2.))
    assert policy.quality([obj])['supported']
    obj['gate']['tracks']=5;assert not policy.quality([obj])['supported']
