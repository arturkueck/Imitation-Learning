import numpy as np
from diagnose import first_run, max_run, first_pair_rejection, stage_progress, transition_metrics


def arrays():
    n=100
    pos=np.zeros((n,3,3));pos[:,:,2]=[.82,.86,.82]
    return dict(x=np.zeros((n,10)),pre_obs=pos.reshape(n,9).copy(),
        post_obs=pos.reshape(n,9).copy(),stage=np.ones(n,int),retreat=np.zeros(n,bool),
        p=np.full(n,3),held_post=np.zeros((n,3),bool),held_known=np.ones(n,bool),
        controller_event=np.zeros(n,int),prefix_valid=np.ones((n,2),bool),
        fingers=np.zeros((n,3),bool))


def test_confirmation_requires_consecutive_frames():
    assert first_run([True,True,False,True,True,True],3)==5
    assert first_run([True,True,False,True,True],3) is None
    assert max_run([True,True,False,True,True,True])==3


def test_native_lift_is_not_inferred_from_height_alone():
    a=arrays();a['post_obs'][10:20,5]=.90
    assert not stage_progress(a,1)['lifted']
    a['held_post'][10:15,1]=True
    assert stage_progress(a,1)['lift_frame']==14


def test_lift_cannot_bridge_retreat_or_stage_boundary():
    a=arrays();a['post_obs'][10:15,5]=.90;a['held_post'][10:15,1]=True
    a['retreat'][12]=True
    assert not stage_progress(a,1)['lifted']
    a['retreat'][12]=False;a['stage'][12]=2
    assert not stage_progress(a,1)['lifted']


def test_future_contact_rejection_is_not_reported_as_collapse():
    a=arrays();a['controller_event'][20]=1
    assert first_pair_rejection(a)=='accepted'
    a['fingers'][50,0]=True;a['prefix_valid'][50,0]=False
    assert first_pair_rejection(a)=='prefix_interrupted_with_contact'
    assert a['post_obs'][50,2]==.82


def test_transition_counts_executed_retreat_frame_before_switch():
    a=arrays()
    a['controller_event'][20]=1;a['controller_event'][21]=2
    a['retreat'][21]=True;a['prob']=np.full(100,.95)
    a['pre_obs']=np.pad(a['pre_obs'],((0,0),(0,9)))
    a['post_obs']=np.pad(a['post_obs'],((0,0),(0,9)))
    a['pre_obs'][:,11]=.87;a['post_obs'][:,11]=.871
    t=transition_metrics(a,20)
    assert t['retreat_frames']==1 and t['switch_frame']==21
    assert abs(t['retreat_eef_height_gain_m']-.001)<1e-9
