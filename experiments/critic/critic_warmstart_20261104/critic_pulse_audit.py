"""Short policy-change pulses, scored by discounted critic action advantages."""
from pathlib import Path
import argparse
from datetime import datetime
import hashlib
import json
import random
import shutil
import time
import traceback
import numpy as np
import torch
import critic_action_audit as one

HERE=Path(__file__).resolve().parent
run=one.run


def advantage_sum(values,gamma):
    values=np.asarray(values,dtype=float)
    assert np.isfinite(values).all()
    return float(np.dot(gamma**np.arange(len(values)),values))


@torch.no_grad()
def branch(bundle,record,kind,cfg,out,deadline,length):
    context=record['context'];scene=record['scene_seed'];probe=record['probe'];other='final' if context=='parent' else 'parent'
    critic=bundle['critics']['warm' if context=='parent' else 'final']
    env=run.native.historical.make_env(3)
    try:
        np.random.seed(scene);random.seed(scene);env.reset();env.sim.forward()
        obs=env._get_observations(force_update=True)
        seq=run.controller.GuardedSequencer(bundle[context],3,run.controller.Clearance(env))
        h=hashlib.sha256();tail=0;success=False;steps=[];matched=False
        for frame in range(cfg['finite_task_horizon']):
            run.stop(out,deadline)
            state,x,phase=run.features(env,seq,obs,frame,cfg['finite_task_horizon'])
            key=(seq.stage,phase,seq.policy.steps)
            positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            action,actual,_=seq.policy.action(obs,positions[seq.stage-1],positions[seq.stage]);assert actual==phase
            normal=action[one.ACTIVE].astype('float32').copy()
            one.digest_update(h,env,state,normal)
            if frame==probe['frame']:
                assert h.hexdigest()==probe['prefix_sha256'],'Pulse prefix mismatch'
                assert list(key)==probe['key'];matched=True
            if probe['frame']<=frame<probe['frame']+length:
                if kind=='policy':candidate=normal
                elif kind in ('q_up','q_down'):
                    candidate=one.gradient_action(critic,state,normal,.1 if kind=='q_up' else -.1)
                elif kind=='other_actor':
                    candidate=bundle[other](torch.tensor(x[None],device='cuda'),torch.tensor([phase],device='cuda'))[0][0].cpu().numpy()
                else:raise ValueError(kind)
                base_values=one.values(bundle['critics'],state,normal)
                new_values=one.values(bundle['critics'],state,candidate)
                advantages={name:{key:new_values[name][key]-base_values[name][key] for key in ('q1','minimum')} for name in bundle['critics']}
                steps.append(dict(frame=frame,state_sha256=hashlib.sha256(state.tobytes()).hexdigest(),
                                  policy_action=normal.tolist(),executed_action=candidate.tolist(),advantages=advantages))
                action[one.ACTIVE]=candidate
            env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
            fingers=np.array([run.native.finger_contact(env,c) for c in env.cubes])
            valid=np.array([run.native.historical.old.prefix_valid(env,k) and not fingers[:k].any() for k in (2,3)])
            seq.advance(valid[seq.stage-1],env.sim.data.body_xpos[env.cube_ids[seq.stage]])
            tail=tail+1 if valid[-1] else 0;success=tail>=50
            if success or seq.timed_out or frame+1==cfg['finite_task_horizon']:break
        assert matched and steps
        predicted={name:{key:advantage_sum([r['advantages'][name][key] for r in steps],cfg['gamma']) for key in ('q1','minimum')}
                   for name in bundle['critics']}
        measured=one.discounted_return(success,probe['frame'],frame,cfg['gamma'])
        baseline=record['variants']['policy']
        return dict(kind=kind,steps=steps,predicted_return_change=predicted,measured_return=measured,
                    measured_return_change=measured-baseline['measured_return'],success=bool(success),
                    baseline_success=baseline['outcome']['success'],last_frame=frame,
                    baseline_last_frame=baseline['outcome']['last_frame'],prefix_matched=True)
    finally:env.close()


def summarize(rows):
    result={}
    for context in ('parent','final'):
        critic='warm' if context=='parent' else 'final'
        for kind in ('q_up','q_down','other_actor'):
            group=[r for r in rows if r['context']==context and r['result']['kind']==kind]
            counts={k:0 for k in ('correct','wrong','outcome_tie','prediction_tie')}
            cases=[]
            for row in group:
                r=row['result'];pred=r['predicted_return_change'][critic]['q1'];actual=r['measured_return_change']
                counts[one.preference(pred,actual)]+=1
                if pred>1e-6 and actual < -1e-6:
                    cases.append(dict(model_seed=row['model_seed'],scene=row['scene_seed'],probe=row['probe']['key'],
                        predicted_improvement=pred,measured_change=actual,baseline_success=r['baseline_success'],modified_success=r['success']))
            result[f'{context}:{kind}']=dict(cases=len(group),matching_critic=critic,ordering=counts,
                predicted_better_actual_worse=cases,
                success_losses=sum(r['result']['baseline_success'] and not r['result']['success'] for r in group),
                success_wins=sum(not r['result']['baseline_success'] and r['result']['success'] for r in group))
    return result


def main(primary,source,out,smoke=False):
    assert json.loads((primary/'status.json').read_text())['state']=='COMPLETED'
    records=json.loads((primary/'counterfactuals.json').read_text())
    if smoke:records=records[:1]
    inputs=dict(json.loads((primary/'protocol.json').read_text())['input_hashes'])
    for file in (Path(__file__),primary/'counterfactuals.json',primary/'verification.json'):
        inputs[str(file.resolve())]=run.sha(file)
    assert all(run.sha(path)==h for path,h in inputs.items())
    assert not out.exists();out.mkdir()
    run.dump(out/'protocol.json',dict(schema='critic-advantage-pulse-v1',prepared_unix=time.time(),input_hashes=inputs,
        primary=str(primary),length=20,kinds=['q_up','q_down','other_actor'],smoke=smoke,
        prediction='sum gamma**i * [Q_pi(s_i,a_modified_i)-Q_pi(s_i,pi(s_i))] over actual pulse path',
        actual='Return after pulse then unchanged policy, minus original policy return at identical initial probe',
        caveat='Not a comparison of a single Q-value against a forced 20-step intervention; all states come from two shared development families',
        optimizer_updates=0,wall_clock_cap_seconds=600 if smoke else 2700))
    snap=out/'source_snapshot';snap.mkdir();shutil.copy2(Path(__file__),snap/'critic_pulse_audit.py')
    torch.set_num_threads(4);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    cfg=json.loads((HERE/'night_001/config.json').read_text())
    deadline=min(time.time()+(600 if smoke else 2700),datetime.fromisoformat('2026-11-05T14:00:00+00:00').timestamp())
    bundles={s:one.load_bundle(s,source) for s in sorted({r['model_seed'] for r in records})}
    rows=[]
    for record in records:
        bundle=bundles[record['model_seed']]
        if smoke:
            check=branch(bundle,record,'policy',cfg,out,deadline,20)
            assert check['measured_return_change']==0 and check['last_frame']==check['baseline_last_frame']
            assert all(abs(v)<1e-12 for r in check['predicted_return_change'].values() for v in r.values())
        for kind in ('q_up','q_down','other_actor'):
            run.dump(out/'status.json',dict(state='PULSE_EVALUATION',model_seed=record['model_seed'],scene=record['scene_seed'],
                     context=record['context'],probe=record['probe']['key'],kind=kind,cases=len(rows),updated_unix=time.time()))
            result=branch(bundle,record,kind,cfg,out,deadline,20)
            rows.append(dict(model_seed=record['model_seed'],scene_seed=record['scene_seed'],context=record['context'],probe=record['probe'],result=result))
            run.dump(out/'pulses.json',rows);run.dump(out/'summary.json',summarize(rows))
    assert all(run.sha(path)==h for path,h in inputs.items())
    run.dump(out/'verification.json',dict(input_hashes_unchanged=True,prefixes_matched=True,optimizer_updates=0,cases=len(rows)))
    run.dump(out/'status.json',dict(state='COMPLETED',cases=len(rows),updated_unix=time.time()))
    print(json.dumps(dict(state='COMPLETED',cases=len(rows),smoke=smoke)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--primary',type=Path,default=HERE/'critic_audit_001')
    p.add_argument('--source',type=Path,default=HERE/'pilot_002');p.add_argument('--output',type=Path,required=True)
    p.add_argument('--smoke',action='store_true');a=p.parse_args()
    try:main(a.primary.resolve(),a.source.resolve(),a.output.resolve(),a.smoke)
    except Exception:
        if a.output.exists():run.dump(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time()))
        raise
