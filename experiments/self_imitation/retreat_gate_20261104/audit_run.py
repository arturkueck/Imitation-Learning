"""Independent integrity/count audit. Reads only this development run's traces."""
from pathlib import Path
import hashlib
import json
import collections
import numpy as np

HERE=Path(__file__).resolve().parent
RUN=HERE/'run_001'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def longest(mask):
    run=best=0
    for ok in mask:
        run=run+1 if ok else 0;best=max(best,run)
    return best


def main():
    status=json.loads((RUN/'status.json').read_text());assert status['state']=='COMPLETED'
    plan=json.loads((RUN/'protocol.json').read_text())
    rows=json.loads((RUN/'episodes.json').read_text());assert len(rows)==120
    assert collections.Counter((r['model_seed'],r['arm']) for r in rows)==collections.Counter({(s,a):20 for s in (1,2,3) for a in ('baseline','guarded')})
    lookup={(r['model_seed'],r['seed'],r['arm']):r for r in rows}
    assert len(lookup)==120
    gates=paired=0;successes=collections.Counter();pickups=collections.Counter()
    all_initial={}
    for seed in range(plan['seeds'][0],plan['seeds'][1]+1):
        for ms in (1,2,3):
            arrays={}
            for arm in ('baseline','guarded'):
                r=lookup[ms,seed,arm];path=Path(r['path']).resolve()
                assert path.is_relative_to((RUN/'traces').resolve())
                assert sha(path)==r['sha256']
                with np.load(path,allow_pickle=False) as f:a={k:f[k] for k in f.files}
                assert all(np.isfinite(v).all() for v in a.values())
                assert hashlib.sha256(a['initial'].tobytes()).hexdigest()==r['initial_sha256']
                assert all_initial.setdefault(seed,r['initial_sha256'])==r['initial_sha256'],'Different seed state between parents'
                assert np.array_equal(a['post_obs'][:-1],a['pre_obs'][1:])
                assert np.array_equal(a['post_state'][:-1],a['pre_state'][1:])
                success=longest(a['valid'])>=50;assert success==r['success']
                releases=np.flatnonzero(a['controller_event']==1)
                switches=np.flatnonzero(a['controller_event']==2)
                assert len(releases)<=1 and len(switches)<=1
                if arm=='guarded' and len(switches):
                    j=int(switches[0]);g=plan['gate']
                    sl=slice(j-g['consecutive_frames']+1,j+1)
                    assert (a['gripper_vertical_gap'][sl]>=g['margin_m']).all()
                    assert a['prefix_valid'][sl,0].all() and not a['fingers'][sl,:2].any()
                    assert a['prob'][j]>=.8 and a['p'][j]==0
                    gates+=1
                lift=a['held_post'][:,2]&(a['post_obs'][:,8]>=a['pre_obs'][0,8]+.03)&(a['stage']==2)
                run=0;pickup=None
                for j,ok in enumerate(lift):
                    run=run+1 if ok else 0
                    if run==5:pickup=j;break
                confirmed=False
                if len(releases) and pickup is not None and pickup+50<len(a['x']):
                    sl=slice(int(releases[0]),pickup+51)
                    confirmed=bool(a['prefix_valid'][sl,0].all() and not a['fingers'][sl,:2].any())
                assert confirmed==r['next_pickup_confirmed']
                successes[ms,arm]+=int(success);pickups[ms,arm]+=int(confirmed)
                arrays[arm]=a
            a,b=arrays['baseline'],arrays['guarded']
            assert np.array_equal(a['initial'],b['initial'])
            releases=np.flatnonzero(a['controller_event']==1)
            end=int(releases[0])+2 if len(releases) else min(len(a['x']),len(b['x']))
            for k in ('x','a','pre_state','post_state','pre_obs','post_obs'):
                assert np.array_equal(a[k][:end],b[k][:end]),('Pre-gate mismatch',k)
            paired+=1
    summary=json.loads((RUN/'summary.json').read_text())
    for seed in (1,2,3):
        for arm in ('baseline','guarded'):
            assert summary[str(seed)][arm]['successes']==successes[seed,arm]
            assert summary[str(seed)][arm]['confirmed_next_pickups']==pickups[seed,arm]
    for p in plan['parents']:assert sha(p['path'])==p['sha256']
    sources=json.loads((RUN/'source_snapshot/manifest.json').read_text())
    for p,h in sources.items():assert sha(p)==h
    result=dict(passed=True,episodes=120,paired_starts=paired,guarded_switches_checked=gates,
        finite_and_continuous=True,success_and_pickup_recomputed=True,
        identical_states_across_all_models=True,identical_actions_before_gate=True,
        models_and_scientific_sources_unchanged=True,old_endtest_access=False,
        auditor_sha256=sha(__file__),episodes_manifest_sha256=sha(RUN/'episodes.json'))
    (RUN/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result))


if __name__=='__main__':main()
