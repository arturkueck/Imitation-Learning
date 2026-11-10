import numpy as np
from compare import Gate,bounds_z


def test_gate_requires_three_consecutive_contact_free_frames():
    g=Gate()
    assert not g.update(.03,True,False,True)
    assert not g.update(.03,True,False,True)
    assert not g.update(.03,True,True,True)
    assert not g.update(.03,True,False,True)
    assert not g.update(.03,True,False,True)
    assert g.update(.03,True,False,True)


def test_gate_rejects_insufficient_height_invalid_prefix_and_incomplete_head():
    g=Gate()
    for _ in range(5):assert not g.update(.019,True,False,True)
    for _ in range(5):assert not g.update(.03,False,False,True)
    for _ in range(5):assert not g.update(.03,True,False,False)
    assert g.update(.03,True,False,True)


def test_rotated_box_uses_world_z_extent():
    rotation=np.array([[0,0,1],[0,1,0],[-1,0,0]])
    lo,hi=bounds_z(np.array([0,0,1]),rotation,np.array([.1,.2,.3]),6,9)
    assert abs(lo-.9)<1e-9 and abs(hi-1.1)<1e-9


def test_mesh_uses_conservative_sphere():
    lo,hi=bounds_z(np.array([0,0,1]),np.eye(3),np.ones(3),7,.12)
    assert lo==.88 and hi==1.12
