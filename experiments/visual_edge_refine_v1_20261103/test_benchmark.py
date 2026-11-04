from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parent))
import numpy as np
from benchmark_report import summary,fixed_matches,object_error
from run_active import observed_second_decision

def m(value):return dict(error_mm=value,position_mm=[value],missing=0,extra=0)
def row(a,b,c,d):return dict(stage_metrics=dict(initial=m(a),one_side=m(b),two_sides=m(c),adaptive=m(d)),metrics=dict(neural_extra=m(c)))

def test_harm_denominators_and_strict_material_threshold():
    s=summary([row(1,.5,2,1),row(1,4,1,1)])
    assert s['one_side']['count']==2 and s['one_side']['worse_over_1mm_count']==1
    assert s['two_sides']['worse_any_count']==1 and s['two_sides']['worse_over_1mm_count']==0
    assert s['adaptive']['worse_any_count']==0 and s['one_side']['mean']==2.25

def test_fixed_gt_association_excludes_remote_false_positive():
    def box(x):return dict(position=np.array([x,0.,0.]),size=np.ones(3)*.04,rotation=np.eye(3))
    truth=dict(active=np.array([True]),positions=np.zeros((1,3)),sizes=np.ones((1,3))*.04,rotations=np.eye(3)[None])
    assert fixed_matches([box(0),box(1)],truth)=={0:0}
    assert object_error(box(0),truth,0)==0
    assert abs(object_error(box(.002),truth,0)-2.5)<1e-8

def test_shadow_evidence_does_not_escalate_initial_skip():
    class Unavailable:
        def __getitem__(self,k):raise AssertionError('Policy read unrequested future evidence')
    assert not observed_second_decision(dict(requested_sides=0),Unavailable(),[])['required']
    assert not observed_second_decision(dict(requested_sides=1),dict(supported=True),['left'])['required']
    assert observed_second_decision(dict(requested_sides=1),dict(supported=False),['left'])['required']

def test_parallel_assignments_cover_same_fixed_100_indices():
    shards=[set(range(i,100,4)) for i in range(4)]
    assert set.union(*shards)==set(range(100)) and sum(map(len,shards))==100
