import numpy as np
from quality_scorer_check import features,extract,settings,auc,top_weights,family_weights


def trace():
    n=100
    return dict(x=np.zeros((n,10)),a=np.zeros((n,7)),p=np.zeros(n,int),stage=np.r_[np.ones(20),np.full(80,2)],
        retreat=np.zeros(n,bool),pre_obs=np.zeros((n,18)),prefix_valid=np.ones((n,2),bool),fingers=np.zeros((n,3),bool),
        controller_event=np.r_[np.zeros(10),1,np.zeros(89)])


def test_features_never_use_future_or_target_validity():
    a=trace();before=features(a,30,5)
    a['x'][31:]=999;a['a'][31:]=999;a['pre_obs'][31:]=999
    a['prefix_valid'][:]=False;a['fingers'][:]=True
    assert np.array_equal(before,features(a,30,5))


def test_labels_require_full_future_and_intact_prestate():
    a=trace();rows,_=extract(a,settings())
    assert rows and max(r['frame'] for r in rows)<=50 and all(r['y']==1 for r in rows)
    a['fingers'][40,0]=True;rows,_=extract(a,settings())
    assert any(r['y']==0 for r in rows)
    assert all(r['frame']!=41 for r in rows) # Already invalid current pair is ineligible.


def test_family_weights_and_tied_rankings_do_not_favor_long_episodes():
    family=np.array(['a','a','a','b']);w=family_weights(family)
    assert np.isclose(w[:3].sum(),.5) and np.isclose(w[3],.5)
    y=np.array([0,1,0,1]);p=np.ones(4)
    assert np.isclose(auc(y,p,w),.5)
    selected=top_weights(p,w,.25)
    assert np.allclose(selected,w*.25)
    assert np.isclose(selected.sum(),.25)
