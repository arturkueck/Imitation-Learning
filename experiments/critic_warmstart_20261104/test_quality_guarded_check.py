from quality_guarded_check import jobs,parity
import quality_scorer_check as q
import numpy as np
import pytest
import quality_guarded_check as guarded


def test_schedule_keeps_old_validation_out_and_fixes_attempts():
    rows=[dict(split='train',seed=i,teacher={'seed':1+i%3}) for i in range(120)]
    rows.append(dict(split='valid',seed=999,teacher={'seed':1}))
    scheduled=jobs(rows)
    assert len(scheduled)==440
    train={z for s,z,_,_ in scheduled if s=='train'}
    valid={z for s,z,_,_ in scheduled if s=='valid'}
    assert len(train)==240 and len(valid)==200 and not train&valid
    assert 999 not in train|valid
    assert sum(r is not None for _,_,_,r in scheduled)==120


def test_reconstruction_rejects_different_recorded_action(tmp_path):
    n=2;a=dict(initial=np.zeros(3),x=np.zeros((n,10)),p=np.zeros(n,int),a=np.zeros((n,7)),
        pre_state=np.zeros((n,4)),post_state=np.zeros((n,4)),pre_obs=np.zeros((n,18)),post_obs=np.zeros((n,18)))
    path=tmp_path/'trace.npz';state=np.zeros((n,41),dtype='float32')
    np.savez(path,x=a['x'].astype('float32'),phase=a['p'],action=np.zeros((n,4),dtype='float32'),state=state,next_state=state)
    import hashlib
    row=dict(path=str(path),sha256=q.sha(path),initial_sha256=hashlib.sha256(a['initial'].tobytes()).hexdigest())
    parity(a,row)
    a['a'][1,0]=.01
    with pytest.raises(AssertionError):parity(a,row)


def test_windows_sharing_retry_is_bounded(monkeypatch):
    calls=[]
    def locked(path,value):
        calls.append(1)
        raise PermissionError('sharing violation')
    monkeypatch.setattr(guarded,'_atomic_write',locked)
    monkeypatch.setattr(guarded.time,'sleep',lambda _:None)
    with pytest.raises(PermissionError):guarded.resilient_write(None,{})
    assert len(calls)==20
