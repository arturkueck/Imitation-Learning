"""Frozen one-action counterfactual audit by deterministic full-prefix replay."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import random
import shutil
import sys
import time
import traceback
import numpy as np
import torch
from core import TwinQ,FixedCompletion
from relative_range import RelativeMovement,run

HERE=Path(__file__).resolve().parent
ACTIVE=[0,1,2,6]


def protocol(smoke=False):
    return dict(schema='critic-one-action-audit-v1',model_seeds=[1] if smoke else [1,2,3],
        scene_seeds=[2026113990] if smoke else [2026113000,2026113001],
        policy_contexts=['parent'] if smoke else ['parent','final'],
        probes=[[1,0,5]] if smoke else [[1,0,5],[1,4,5],[2,0,5]],
        variants=['policy','other_actor','q_up','q_down','reverse_xyz','open_gripper'],
        local_xyz_step=.1,discount=.995,finite_horizon=1000,
        intervention='Exactly one executed action; subsequently unchanged context policy and native guarded sequencer',
        state_matching='Fresh environments replay the entire original prefix; bitwise prefix hashes include physics, controls, solver warmstart, features and proposed actions',
        primary='Within-state Q1 ordering versus measured discounted return under the corresponding deployed deterministic continuation',
        secondary='Twin-Q minimum, near-policy versus stress actions, success changes and ties',
        caveats=['Sparse returns may leave many actions tied',
                 'Warmup labels mix behavior parents; they are not a promise of exact per-parent Q',
                 'Final TD targets used action smoothing; deployed deterministic continuation differs from that objective',
                 'No significance or generalization claim from two shared start families',
                 'A single-action diagnostic does not isolate every cause of whole-policy failure'],
        wall_clock_cap_seconds=600 if smoke else 5400,smoke=smoke,
        optimizer_updates=0,reserved_endtests_enabled=False,no_resampling_unreachable_probes=True)


def discounted_return(success,probe_frame,last_frame,gamma):
    assert last_frame>=probe_frame
    return float(gamma**(last_frame-probe_frame)) if success else 0.


def preference(pred_delta,true_delta,tol=1e-6):
    if abs(true_delta)<=tol:return 'outcome_tie'
    if abs(pred_delta)<=tol:return 'prediction_tie'
    return 'correct' if pred_delta*true_delta>0 else 'wrong'


def load_bundle(seed,source):
    parent_path=Path(run.parent(seed)['path'])
    warm_path=HERE/f'night_001/warm/seed{seed}/warm.pth'
    final_path=source/f'seed{seed}/round4.pth'
    warm=torch.load(warm_path,map_location='cuda',weights_only=False)
    final=torch.load(final_path,map_location='cuda',weights_only=False)
    parent=run.native.historical.load(parent_path).eval().requires_grad_(False)
    final_actor=RelativeMovement(copy.deepcopy(parent),parent,.2,.5,.02).cuda()
    final_actor.load_state_dict(final['actor'])
    reference=copy.deepcopy(parent);reference.load_state_dict(final['reference'])
    policy=FixedCompletion(final_actor,reference).eval().requires_grad_(False)
    critics={}
    for name,ck in (('warm',warm),('final',final)):
        sd=ck['critic'];q=TwinQ(sd['mean'],sd['std'],ck['config']['critic_width']).cuda()
        q.load_state_dict(sd);q.eval().requires_grad_(False);critics[name]=q
    return dict(parent=parent,final=policy,critics=critics,
                files=[parent_path,warm_path,final_path])


@torch.no_grad()
def values(critics,state,action):
    st=torch.tensor(state[None],device='cuda');a=torch.tensor(np.asarray(action,dtype='float32')[None],device='cuda')
    result={}
    for name,q in critics.items():
        q1,q2=q(st,a)
        result[name]=dict(q1=q1.item(),q2=q2.item(),minimum=torch.minimum(q1,q2).item())
    assert all(np.isfinite(v) for row in result.values() for v in row.values())
    return result


def gradient_action(critic,state,action,amount):
    with torch.enable_grad():
        st=torch.tensor(state[None],device='cuda')
        a=torch.tensor(np.asarray(action,dtype='float32')[None],device='cuda',requires_grad=True)
        q1,_=critic(st,a);g=torch.autograd.grad(q1.sum(),a)[0][0,:3].detach().cpu().numpy()
    delta=amount*g/max(float(np.linalg.norm(g)),1e-12)
    result=np.asarray(action,dtype='float32').copy();result[:3]=np.clip(result[:3]+delta,-1,1)
    return result


def digest_update(h,env,state,normal):
    for array in (env.sim.get_state().flatten(),env.sim.data.ctrl,env.sim.data.qacc_warmstart,state,normal):
        a=np.ascontiguousarray(array);h.update(a.tobytes())


@torch.no_grad()
def rollout(bundle,context,scene,cfg,out,deadline,planned,intervention=None):
    env=run.native.historical.make_env(3)
    try:
        np.random.seed(scene);random.seed(scene);env.reset();env.sim.forward()
        obs=env._get_observations(force_update=True)
        initial=hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest()
        seq=run.controller.GuardedSequencer(bundle[context],3,run.controller.Clearance(env))
        tail=0;success=False;probes={};h=hashlib.sha256();applied=False
        targets={tuple(p) for p in planned['probes']}
        for frame in range(cfg['finite_task_horizon']):
            run.stop(out,deadline)
            state,x,phase=run.features(env,seq,obs,frame,cfg['finite_task_horizon'])
            key=(seq.stage,phase,seq.policy.steps)
            positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            action,actual,_=seq.policy.action(obs,positions[seq.stage-1],positions[seq.stage]);assert actual==phase
            normal=action[ACTIVE].astype('float32').copy()
            digest_update(h,env,state,normal)
            if intervention is None and key in targets and str(key) not in probes:
                probes[str(key)]=dict(key=list(key),frame=frame,state=state.tolist(),x=x.tolist(),phase=phase,
                    prefix_sha256=h.hexdigest(),action=normal.tolist())
            if intervention is not None and frame==intervention['frame']:
                assert h.hexdigest()==intervention['prefix_sha256'],'Counterfactual prefix mismatch: no outcome accepted'
                assert list(key)==intervention['key']
                action[ACTIVE]=intervention['action'];applied=True
            env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
            fingers=np.array([run.native.finger_contact(env,c) for c in env.cubes])
            valid=np.array([run.native.historical.old.prefix_valid(env,k) and not fingers[:k].any() for k in (2,3)])
            seq.advance(valid[seq.stage-1],env.sim.data.body_xpos[env.cube_ids[seq.stage]])
            tail=tail+1 if valid[-1] else 0;success=tail>=50
            if success or seq.timed_out or frame+1==cfg['finite_task_horizon']:break
        if intervention is not None:assert applied,'Intervention never reached'
        return dict(scene_seed=scene,context=context,initial_sha256=initial,success=bool(success),last_frame=frame,
            termination='success' if success else 'controller_failure' if seq.timed_out else 'finite_task_horizon',
            last_stage=seq.stage,last_phase=seq.policy.phase,probes=probes)
    finally:env.close()


@torch.no_grad()
def candidates(bundle,context,probe,planned):
    a=np.asarray(probe['action'],dtype='float32');state=np.asarray(probe['state'],dtype='float32')
    other='final' if context=='parent' else 'parent'
    x=torch.tensor(np.asarray(probe['x'],dtype='float32')[None],device='cuda')
    phase=torch.tensor([probe['phase']],device='cuda')
    proposed=bundle[other](x,phase)[0][0].cpu().numpy()
    critic=bundle['critics']['warm' if context=='parent' else 'final']
    reverse=a.copy();reverse[:3]*=-1
    opened=a.copy();opened[3]=-1
    actions=dict(policy=a,other_actor=proposed,
        q_up=gradient_action(critic,state,a,planned['local_xyz_step']),
        q_down=gradient_action(critic,state,a,-planned['local_xyz_step']),
        reverse_xyz=reverse,open_gripper=opened)
    return {name:dict(action=act.tolist(),predictions=values(bundle['critics'],state,act),
                     category='stress' if name in ('reverse_xyz','open_gripper') else 'near_policy')
            for name,act in actions.items()}


def summarize(rows):
    summary={}
    for context in ('parent','final'):
        matching='warm' if context=='parent' else 'final'
        for critic in ('warm','final'):
            counts={k:0 for k in ('correct','wrong','outcome_tie','prediction_tie')}
            local={k:0 for k in counts};up={k:0 for k in ('better','worse','unchanged','not_predicted_better')}
            states=0;regrets=[];positive_controls=dict(worse=0,better=0,unchanged=0)
            for row in rows:
                if row['context']!=context:continue
                states+=1;variants=list(row['variants'].items());base=row['variants']['policy']
                for i,(name,a) in enumerate(variants):
                    if name in ('reverse_xyz','open_gripper'):
                        delta=a['measured_return']-base['measured_return']
                        positive_controls['worse' if delta < -1e-6 else 'better' if delta > 1e-6 else 'unchanged']+=1
                    for _,b in variants[i+1:]:
                        if np.max(np.abs(np.asarray(a['action'])-np.asarray(b['action'])))<=1e-6:continue
                        label=preference(a['predictions'][critic]['q1']-b['predictions'][critic]['q1'],a['measured_return']-b['measured_return'])
                        counts[label]+=1
                        if a['category']==b['category']=='near_policy':local[label]+=1
                chosen=max(row['variants'].values(),key=lambda r:r['predictions'][critic]['q1'])
                regrets.append(max(r['measured_return'] for _,r in variants)-chosen['measured_return'])
                delta_q=row['variants']['q_up']['predictions'][critic]['q1']-base['predictions'][critic]['q1']
                delta_r=row['variants']['q_up']['measured_return']-base['measured_return']
                up['not_predicted_better' if delta_q<=1e-6 else 'better' if delta_r>1e-6 else 'worse' if delta_r < -1e-6 else 'unchanged']+=1
            summary[f'{context}:{critic}']=dict(states=states,critic_matches_continuation=critic==matching,
                pair_orderings=counts,near_policy_pair_orderings=local,q_up_outcomes=up,
                mean_regret_over_tested_actions=float(np.mean(regrets)) if regrets else None,
                stress_controls=positive_controls)
    return summary


def main(source,out,smoke):
    planned=protocol(smoke);cfg=json.loads((HERE/'night_001/config.json').read_text())
    assert not out.exists();out.mkdir()
    inputs={str(p):run.sha(p) for p in (Path(__file__),HERE/'core.py',HERE/'run.py',HERE/'relative_range.py',
        Path(run.controller.__file__),Path(run.native.__file__),Path(run.native.historical.__file__),
        Path(sys.modules['method'].__file__),Path(run.native.historical.old.__file__))}
    bundles={s:load_bundle(s,source) for s in planned['model_seeds']}
    for bundle in bundles.values():
        for file in bundle['files']:inputs[str(file)]=run.sha(file)
    run.dump(out/'protocol.json',dict(**planned,input_hashes=inputs,prepared_unix=time.time()))
    snap=out/'source_snapshot';snap.mkdir()
    for i,path in enumerate(inputs):
        if Path(path).suffix=='.py':shutil.copy2(path,snap/f'{i:02d}_{Path(path).name}')
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    deadline=time.time()+planned['wall_clock_cap_seconds'];rows=[];baselines=[];rollouts=0
    for model_seed,bundle in bundles.items():
        for scene in planned['scene_seeds']:
            for context in planned['policy_contexts']:
                run.dump(out/'status.json',dict(state='BASELINE',model_seed=model_seed,scene=scene,context=context,rollouts=rollouts,updated_unix=time.time()))
                baseline=rollout(bundle,context,scene,cfg,out,deadline,planned);rollouts+=1
                baseline['model_seed']=model_seed;baselines.append(baseline);run.dump(out/'baselines.json',baselines)
                if smoke:
                    probe=next(iter(baseline['probes'].values()))
                    repeat=rollout(bundle,context,scene,cfg,out,deadline,planned,dict(probe,action=probe['action']));rollouts+=1
                    assert (repeat['success'],repeat['last_frame'],repeat['termination'])==(baseline['success'],baseline['last_frame'],baseline['termination'])
                for probe in baseline['probes'].values():
                    variants=candidates(bundle,context,probe,planned)
                    done=[]
                    for name,row in variants.items():
                        run.dump(out/'status.json',dict(state='COUNTERFACTUAL',model_seed=model_seed,scene=scene,context=context,
                            probe=probe['key'],variant=name,states=len(rows),rollouts=rollouts,updated_unix=time.time()))
                        duplicate=next((v for v in done if np.max(np.abs(np.asarray(v['action'])-np.asarray(row['action'])))<=1e-6),None)
                        if name=='policy':outcome=baseline;row['reused_baseline']=True
                        elif duplicate is not None:
                            outcome=duplicate['outcome'];row['same_action_reused']=True
                        else:
                            outcome=rollout(bundle,context,scene,cfg,out,deadline,planned,dict(probe,action=row['action']));rollouts+=1
                            assert outcome['initial_sha256']==baseline['initial_sha256']
                        row['outcome']={k:v for k,v in outcome.items() if k!='probes'}
                        row['measured_return']=discounted_return(outcome['success'],probe['frame'],outcome['last_frame'],cfg['gamma'])
                        done.append(row)
                    rows.append(dict(model_seed=model_seed,scene_seed=scene,context=context,probe=probe,variants=variants))
                    run.dump(out/'counterfactuals.json',rows);run.dump(out/'summary.json',summarize(rows))
    for path,h in inputs.items():assert run.sha(path)==h, f'Input changed: {path}'
    missing=[dict(model_seed=b['model_seed'],scene=b['scene_seed'],context=b['context'],missing=[p for p in planned['probes'] if str(tuple(p)) not in b['probes']]) for b in baselines]
    run.dump(out/'verification.json',dict(inputs_unchanged=True,input_hashes=len(inputs),prefix_replay_matching=True,
        states=len(rows),rollouts=rollouts,missing_probes=missing,optimizer_updates=0))
    run.dump(out/'status.json',dict(state='COMPLETED',states=len(rows),rollouts=rollouts,updated_unix=time.time()))
    print(json.dumps(dict(state='COMPLETED',states=len(rows),rollouts=rollouts,smoke=smoke)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,default=HERE/'pilot_002')
    p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');a=p.parse_args()
    try:main(a.source.resolve(),a.output.resolve(),a.smoke)
    except Exception:
        if a.output.exists():run.dump(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
