"""Replay existing guarded validation commands; assess a frozen quality scorer."""
from pathlib import Path
import argparse
import hashlib
import json
import random
import shutil
import time
import traceback
import numpy as np
import torch
import quality_scorer_check as quality
from relative_range import run

HERE=Path(__file__).resolve().parent


def main(scorer,source,out):
    plan=quality.read(scorer/'protocol.json');assert quality.read(scorer/'status.json')['state']=='COMPLETED'
    assert quality.read(scorer/'results.json')['scorer_test_passed']
    manifest=quality.read(source/'manifest.json');assert manifest['complete'] and manifest['ready_for_training']
    rows=[r for r in manifest['rows'] if r['split']=='valid'];assert len(rows)==40
    old_families={r['family'] for r in quality.read(scorer/'dataset_audit.json')['inventory']}
    assert not {r['initial_sha256'] for r in rows}&old_families
    inputs={str(Path(__file__).resolve()):quality.sha(Path(__file__)),str(source/'manifest.json'):quality.sha(source/'manifest.json'),
            str(HERE/'quality_scorer_check.py'):quality.sha(HERE/'quality_scorer_check.py')}
    models=[]
    torch.set_num_threads(4);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    for seed in plan['ensemble_seeds']:
        path=scorer/f'models/mlp_seed{seed}.pth';inputs[str(path)]=quality.sha(path)
        ck=torch.load(path,map_location='cpu',weights_only=False);sd=ck['model']
        model=quality.Scorer(sd['mean'].numpy(),sd['scale'].numpy(),'mlp',plan['width']).cuda()
        model.load_state_dict(sd);model.eval().requires_grad_(False);models.append(model)
    for row in rows:inputs[row['path']]=row['sha256']
    assert not out.exists();out.mkdir()
    quality.write(out/'protocol.json',dict(schema='guarded-quality-transfer-v1',prepared_unix=time.time(),input_hashes=inputs,
        source=str(source),scorer=str(scorer),replays=40,new_actor_training=0,new_scorer_training=0,
        trajectory_rule='Replay recorded commands from fresh resets; exact initial hashes and every pre-action float32 simulator state/observation must match',
        unchanged_quality_target=plan['target'],window_parameters={k:plan[k] for k in ('history','outcome_frames','stride','max_examples_per_episode')},
        wall_clock_cap_seconds=900))
    snap=out/'source_snapshot';snap.mkdir();shutil.copy2(Path(__file__),snap/'quality_scorer_transfer.py')
    deadline=time.time()+900;examples=[];replayed=[]
    for index,row in enumerate(rows):
        assert quality.sha(row['path'])==row['sha256']
        with np.load(row['path'],allow_pickle=False) as f:
            saved={k:f[k].copy() for k in ('state','next_state','x','phase','action','reward')}
        n=len(saved['x']);runtime=saved['state'][:,-19:];next_runtime=saved['next_state'][:,-19:]
        stage=np.argmax(runtime[:,7:9],axis=1)+1;after_stage=np.argmax(next_runtime[:,7:9],axis=1)+1
        retreat=runtime[:,14]>.5;after_retreat=next_runtime[:,14]>.5
        events=np.zeros(n,int);events[(stage==1)&~retreat&after_retreat]=1
        events[(stage==1)&(after_stage==2)]=2
        pre=[];prefix=[];fingers=[];tail=0
        env=run.native.historical.make_env(3)
        try:
            np.random.seed(row['seed']);random.seed(row['seed']);env.reset();env.sim.forward()
            initial=env.sim.get_state().flatten().copy()
            assert hashlib.sha256(initial.tobytes()).hexdigest()==row['initial_sha256']
            for t in range(n):
                run.stop(out,deadline)
                current=env.sim.get_state().flatten()
                physics_dim=saved['state'].shape[1]-18-19
                assert np.array_equal(current.astype('float32'),saved['state'][t,:physics_dim]),f'Physics replay mismatch at {row["seed"]}:{t}'
                obs=env._get_observations(force_update=True)
                ob=run.native.historical.observation(env,obs)
                assert np.array_equal(ob.astype('float32'),saved['state'][t,-37:-19]),'Observation replay mismatch'
                pre.append(ob)
                action=np.zeros(7);action[[0,1,2,6]]=saved['action'][t]
                env.step(action);env.sim.forward();env._get_observations(force_update=True)
                touched=np.array([run.native.finger_contact(env,c) for c in env.cubes])
                valid=np.array([run.native.historical.old.prefix_valid(env,k) and not touched[:k].any() for k in (2,3)])
                prefix.append(valid);fingers.append(touched);tail=tail+1 if valid[-1] else 0
            assert (tail>=50)==row['success'],'Replay final success differs from saved trajectory'
        finally:env.close()
        action=np.zeros((n,7));action[:,[0,1,2,6]]=saved['action']
        a=dict(x=saved['x'],a=action,p=saved['phase'],stage=stage,retreat=retreat,pre_obs=np.asarray(pre),
               prefix_valid=np.asarray(prefix),fingers=np.asarray(fingers),controller_event=events)
        selected,info=quality.extract(a,plan)
        for record in selected:examples.append(dict(**record,family=row['initial_sha256'],source=row['path']))
        replayed.append(dict(seed=row['seed'],family=row['initial_sha256'],success=row['success'],frames=n,**info))
        quality.write(out/'replays.json',replayed)
        quality.write(out/'status.json',dict(state='GUARDED_REPLAY',episode=index+1,total=len(rows),examples=len(examples),updated_unix=time.time()))
    assert examples
    x=np.stack([r['x'] for r in examples]);y=np.asarray([r['y'] for r in examples]);families=np.asarray([r['family'] for r in examples])
    p=np.mean([quality.predict(model,x) for model in models],axis=0)
    m=quality.metrics(y,p,families)
    support=dict(families=len(np.unique(families)),positive_families=len(np.unique(families[y==1])),negative_families=len(np.unique(families[y==0])),examples=len(y))
    g=plan['gate']
    supported=support['families']>=g['min_valid_families'] and min(support['positive_families'],support['negative_families'])>=g['min_class_families']
    quality.write(out/'results.json',dict(metrics=m,support=support,class_support_sufficient=supported,
        guarded_controller_release=False,
        interpretation='No refit or threshold changes; insufficient negative support is not evidence of poor discrimination, but cannot validate useful quality weighting',
        actor_training_started=False,scorer_updates=0,recorded_trajectory_replay_verified=True))
    np.savez_compressed(out/'scores.npz',probability=p,y=y,family=families,frame=np.asarray([r['frame'] for r in examples]))
    assert all(quality.sha(path)==h for path,h in inputs.items())
    quality.write(out/'verification.json',dict(input_hashes_unchanged=True,initial_state_hashes_verified=40,
        all_pre_action_physics_and_observations_matched=True,final_successes_matched=True,
        actor_weights_loaded=False,actor_updates=0,scorer_updates=0))
    quality.write(out/'status.json',dict(state='COMPLETED',class_support_sufficient=supported,updated_unix=time.time()))
    print(json.dumps(dict(state='COMPLETED',metrics=m,support=support,class_support_sufficient=supported)))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scorer',type=Path,default=HERE/'scorer_check_001')
    parser.add_argument('--source',type=Path,default=HERE/'night_001/data');parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args()
    try:main(a.scorer.resolve(),a.source.resolve(),a.output.resolve())
    except Exception:
        if a.output.exists():quality.write(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
