import copy
import numpy as np
import pytest
from pilot import partial_sections, quality, split_audit, weighted_loss


def fixture():
    n=100
    pos=np.zeros((n,3,3));pos[:,:,2]=[.82,.86,.82]
    a=dict(x=np.zeros((n,10)),controller_event=np.zeros(n,int),stage=np.ones(n,int),
           p=np.full(n,6),retreat=np.zeros(n,bool),prefix_valid=np.ones((n,2),bool),
           fingers=np.zeros((n,3),bool),held_post=np.zeros((n,3),bool),held_known=np.ones(n,bool),
           post_obs=pos.reshape(n,9),pre_obs=pos.reshape(n,9).copy())
    a['controller_event'][20]=1
    row=dict(count=3,native_collector=True,path='synthetic.npz',split='train',
             initial_sha256='family',teacher_sha256='teacher')
    return a,row


def test_confirmed_first_pair_excludes_future_actions():
    a,r=fixture();sections=partial_sections(a,r)
    assert len(sections)==1 and sections[0]['end']==21
    assert sections[0]['confirmed_post_frame']==70


@pytest.mark.parametrize('signal', ['prefix','finger','censored'])
def test_future_failure_or_missing_tail_rejects_section(signal):
    a,r=fixture()
    if signal=='prefix':a['prefix_valid'][60,0]=False
    elif signal=='finger':a['fingers'][60,1]=True
    else:
        for k in a:a[k]=a[k][:60]
    assert partial_sections(a,r)==[]


def test_initial_family_cannot_cross_split():
    rows=[dict(split='train',initial_sha256='same',count=3,seed=1),
          dict(split='valid',initial_sha256='same',count=3,seed=2)]
    with pytest.raises(AssertionError,match='family leakage'):split_audit(rows)


def test_quality_and_normalized_loss():
    a,_=fixture();q=quality(a,21,71,2)
    a['post_obs'][50,0]=.01
    assert .5<=quality(a,21,71,2)<q<=1
    e=np.array([1.,3.]);w=np.array([.5,1.])
    assert weighted_loss(e,w)==pytest.approx(weighted_loss(e,10*w))
