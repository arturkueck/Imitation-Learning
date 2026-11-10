"""Frozen-policy, paired development comparison of retreat release criteria."""
from pathlib import Path
from collections import defaultdict
import argparse
import hashlib
import json
import os
import random
import shutil
import sys
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'runtime/numba_cache'))
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG',':4096:8')
sys.path.insert(0,str(ROOT/'praxis/src'))
sys.path.insert(0,str(ROOT/'experiments/self_imitation/stack_transition_quality_20261024'))
import numpy as np
import torch
import native_collector as native
from transition_pilot import audit_arrays, dump, sha


def bounds_z(center,rotation,size,kind,radius):
    # MuJoCo geom type6 = box. Meshes use their conservative bounding sphere.
    extent=float(np.dot(np.abs(rotation.reshape(3,3)[2]),size)) if kind==6 else float(radius)
    return float(center[2]-extent),float(center[2]+extent)


class Clearance:
    def __init__(self,env):
        self.env=env
        grippers=env.robots[0].gripper
        grippers=list(grippers.values()) if isinstance(grippers,dict) else [grippers]
        self.gripper_ids=[env.sim.model.geom_name2id(name) for g in grippers for name in g.contact_geoms]
        self.cube_ids=[[env.sim.model.geom_name2id(name) for name in c.contact_geoms] for c in env.cubes]
        assert self.gripper_ids and all(self.cube_ids)
    def geom(self,j):
        model,data=self.env.sim.model,self.env.sim.data
        return bounds_z(data.geom_xpos[j],data.geom_xmat[j],model.geom_size[j],
                        int(model.geom_type[j]),model.geom_rbound[j])
    def gap(self,prefix):
        bottom=min(self.geom(j)[0] for j in self.gripper_ids)
        top=max(self.geom(j)[1] for ids in self.cube_ids[:prefix] for j in ids)
        return bottom-top


class Gate:
    def __init__(self,margin=.02,frames=3):
        self.margin=margin;self.frames=frames;self.run=0
    def update(self,gap,prefix_valid,tower_contact,learned_done):
        clear=gap>=self.margin and prefix_valid and not tower_contact
        self.run=self.run+1 if clear else 0
        return self.run>=self.frames and learned_done


class GuardedSequencer(native.historical.Sequencer):
    def __init__(self,model,count,clearance):
        super().__init__(model,count)
        self.clearance=clearance;self.gate=Gate();self.retreat_actions=0;self.retreat_anchor=None
        self.timed_out=False
    def advance(self,valid,placed_position):
        if self.retreat:
            self.retreat_actions+=1
            env=self.clearance.env
            contact=any(native.finger_contact(env,c) for c in env.cubes[:self.stage+1])
            done=self.policy.phase>0
            if self.gate.update(self.clearance.gap(self.stage+1),bool(valid),contact,done):
                self.retreat=False;self.stage+=1;self.pair=0;self.policy.reset()
                return 2
            # Repeat the existing learned phase0 action, preserving elapsed time
            # and cached anchor despite an early phase-completion prediction.
            self.policy.phase=0;self.policy.steps=self.retreat_actions
            self.policy.anchor=self.retreat_anchor.copy()
            self.timed_out=self.retreat_actions>=200
            return 0
        event=super().advance(valid,placed_position)
        if event==1:
            self.retreat_actions=0;self.retreat_anchor=self.policy.anchor.copy();self.gate.run=0
        return event


def check_stop(out,deadline):
    if time.time()>=deadline or (out/'STOP').exists():raise TimeoutError('Fixed wall-clock cap or STOP')


@torch.no_grad()
def collect(env,model,seed,arm,out,deadline):
    np.random.seed(seed);random.seed(seed);env.reset();env.sim.forward()
    obs=env._get_observations(force_update=True)
    initial=env.sim.get_state().flatten().copy()
    clearance=Clearance(env)
    seq=(native.historical.Sequencer(model,3) if arm=='baseline' else GuardedSequencer(model,3,clearance))
    records=defaultdict(list);tail=0;release=None;continuous=True;first_loss=None
    for frame in range(1000):
        check_stop(out,deadline)
        policy=seq.policy;stage=seq.stage;phase=policy.phase;steps=policy.steps
        positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        anchor=positions[stage if phase<4 else stage-1].copy() if policy.anchor is None else policy.anchor.copy()
        pre=native.historical.observation(env,obs);pre_state=env.sim.get_state().flatten().copy()
        retreat=seq.retreat
        action,actual,prob=policy.action(obs,positions[stage-1],positions[stage]);assert actual==phase
        env.step(action);env.sim.forward();next_obs=env._get_observations(force_update=True)
        fingers=np.array([native.finger_contact(env,c) for c in env.cubes])
        prefixes=np.array([native.historical.old.prefix_valid(env,k) and not fingers[:k].any() for k in (2,3)])
        row=dict(x=native.historical.vector(obs,anchor,steps),a=action,p=phase,
            y=int(policy.phase!=phase),phase_steps=steps,anchor=anchor,stage=stage,retreat=retreat,
            pre_obs=pre,post_obs=native.historical.observation(env,next_obs),pre_state=pre_state,
            post_state=env.sim.get_state().flatten().copy(),
            held_post=np.array([env._check_grasp(env.robots[0].gripper,c.contact_geoms) for c in env.cubes],bool),
            held_known=True,prefix_valid=prefixes,valid2=prefixes[0],valid=prefixes[-1],
            contacts=np.array([env.check_contact(env.cubes[k],env.cubes[k+1]) for k in range(2)]),
            fingers=fingers,velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes]),
            prob=prob,gripper_vertical_gap=clearance.gap(2))
        event=seq.advance(prefixes[stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        row['controller_event']=event
        if release is not None and not prefixes[0]:
            continuous=False
            if first_loss is None:first_loss=dict(frame=frame,stage=stage,phase=phase,retreat=bool(retreat),tower_contact=bool(fingers[:2].any()))
        if event==1:release=frame
        for k,v in row.items():records[k].append(v)
        obs=next_obs;tail=tail+1 if prefixes[-1] else 0
        if tail>=50 or getattr(seq,'timed_out',False):break
    a={k:np.asarray(v) for k,v in records.items()};a['initial']=initial
    audit_arrays(a,3)
    assert np.array_equal(a['post_state'][:-1],a['pre_state'][1:])
    switches=np.flatnonzero(a['controller_event']==2)
    gap=float(a['gripper_vertical_gap'][switches[0]]) if len(switches) else None
    retreat_frames=int(a['retreat'].sum())
    if arm=='guarded' and len(switches):
        j=int(switches[0]);assert (a['gripper_vertical_gap'][j-2:j+1]>=.02).all()
        assert a['prefix_valid'][j-2:j+1,0].all() and not a['fingers'][j-2:j+1,:2].any()
    # Outcomes: only count native grasp+30mm lift with five consecutive frames.
    ref=float(a['pre_obs'][0,8]);lifted=a['held_post'][:,2]&(a['post_obs'][:,8]>=ref+.03)&(a['stage']==2)
    pickup=None;run=0
    for j,ok in enumerate(lifted):
        run=run+1 if ok else 0
        if run>=5:pickup=j;break
    confirmed=False
    if release is not None and pickup is not None and pickup+50<len(a['x']):
        confirmed=bool(a['prefix_valid'][release:pickup+51,0].all() and not a['fingers'][release:pickup+51,:2].any())
    return a,dict(seed=seed,arm=arm,success=tail>=50,frames=len(a['x']),
        initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),
        first_release_frame=release,pair_switched=bool(len(switches)),retreat_frames=retreat_frames,
        gap_at_switch_m=gap,retreat_timeout=bool(getattr(seq,'timed_out',False)),
        prefix_continuous_after_release=bool(release is not None and continuous),first_prefix_loss=first_loss,
        next_pickup_confirmed=confirmed,next_pickup_frame=pickup)


def compare(out,smoke):
    out.mkdir(parents=True,exist_ok=False);start=time.time();deadline=start+(300 if smoke else 1800)
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    plan=dict(schema='retreat-gate-development-v1',authorization='2026-11-04: Okay after proposed frozen-model controller comparison',
        scope='Fresh paired development rollouts. No training, checkpoint selection, old endtest access or real hardware.',
        seeds=[2026110700,2026110719],technical_seed=2026110600,model_seeds=[1,2,3],
        arms=['baseline','guarded'],gate=dict(margin_m=.02,consecutive_frames=3,
            geometry='All gripper contact geoms; exact world Z box extents, conservative bounding spheres for meshes; all protected cube collision boxes',
            other_conditions='Prefix valid, no tower finger contact, learned phase0 completion',
            motion='Same learned phase0 head until gate; phase time and cached anchor preserved',retreat_timeout_frames=200),
        episode_horizon=1000,wall_clock_cap_seconds=1800,automatic_retry=False,parents=[],created_unix=start,deadline=deadline,
        success='50 consecutive existing strict native full-tower-valid post-action frames',
        limitations='Vertical separation gate does not certify future trajectory collision clearance. Privileged simulator geometry. A controller comparison, not improved neural weights.')
    for seed in (1,2,3):
        path=ROOT/f'experiments/self_imitation/stack_self_imitation_20261023/final_test/C_seed{seed}.pth'
        plan['parents'].append(dict(seed=seed,path=str(path),sha256=sha(path)))
    dump(out/'protocol.json',plan)
    snapshot=out/'source_snapshot';snapshot.mkdir()
    sourcefiles=[Path(__file__).resolve(),Path(native.__file__),Path(native.historical.__file__),Path(sys.modules['method'].__file__),Path(native.historical.old.__file__)]
    sources={}
    for i,p in enumerate(sourcefiles):
        dst=snapshot/f'{i:02d}_{p.name}';shutil.copy2(p,dst);sources[str(p)]=sha(p)
    dump(snapshot/'manifest.json',sources)
    output_rows=[];technical={}
    for parent in plan['parents'][:1] if smoke else plan['parents']:
        model=native.historical.load(parent['path']);seed_model=parent['seed']
        seeds=[plan['technical_seed']] if smoke else range(plan['seeds'][0],plan['seeds'][1]+1)
        env=native.historical.make_env(3)
        try:
            (out/f'model_seed{seed_model}.xml').write_text(env.model.get_xml(),encoding='utf-8')
            for seed in seeds:
                pair={};arrays={}
                for arm in ('baseline','guarded'):
                    check_stop(out,deadline)
                    dump(out/'status.json',dict(state='EVALUATING',model_seed=seed_model,seed=seed,arm=arm,
                        completed=len(output_rows),planned=2 if smoke else 120,pid=os.getpid(),updated_unix=time.time()))
                    a,r=collect(env,model,seed,arm,out,deadline);r['model_seed']=seed_model
                    pair[arm]=r;arrays[arm]=a
                    folder=out/f'traces/seed{seed_model}/{arm}';folder.mkdir(parents=True,exist_ok=True)
                    path=folder/f'{seed}.npz';np.savez_compressed(path,**a)
                    r.update(path=str(path.resolve()),sha256=sha(path));output_rows.append(r)
                    dump(out/'episodes.json',output_rows)
                assert pair['baseline']['initial_sha256']==pair['guarded']['initial_sha256'],'Unpaired initial states'
                # Arms are bit-identical through the first actual retreat action.
                release=pair['baseline']['first_release_frame']
                if release is not None:
                    for key in ('x','a','pre_obs','post_obs','pre_state','post_state'):
                        assert np.array_equal(arrays['baseline'][key][:release+2],arrays['guarded'][key][:release+2]),('Arms differ before gate',key)
                if smoke:
                    reference,rr=native.collect(env,model,3,seed,1000,deadline)
                    for key in reference:
                        assert np.array_equal(reference[key],arrays['baseline'][key]),('Baseline adapter parity',key)
                    technical=dict(baseline_exact_native_parity=True,paired_initial_states=True,
                        identical_before_gate=True,guard_switches_checked=True,
                        guarded_switched=pair['guarded']['pair_switched'],guarded_timeout=pair['guarded']['retreat_timeout'])
        finally:env.close()
        assert sha(parent['path'])==parent['sha256']
    summaries={}
    for parent in plan['parents'][:1] if smoke else plan['parents']:
        ms=parent['seed'];group=[r for r in output_rows if r['model_seed']==ms]
        summaries[str(ms)]={}
        for arm in ('baseline','guarded'):
            rows=[r for r in group if r['arm']==arm]
            summaries[str(ms)][arm]=dict(attempts=len(rows),successes=sum(r['success'] for r in rows),
                confirmed_next_pickups=sum(r['next_pickup_confirmed'] for r in rows),
                timeouts=sum(r['retreat_timeout'] for r in rows),
                continuous_prefix=sum(r['prefix_continuous_after_release'] for r in rows),
                switched=sum(r['pair_switched'] for r in rows),retreat_frames_median=float(np.median([r['retreat_frames'] for r in rows])))
        b={r['seed']:r for r in group if r['arm']=='baseline'}
        g={r['seed']:r for r in group if r['arm']=='guarded'}
        summaries[str(ms)]['paired']=dict(won=sum(g[s]['success'] and not b[s]['success'] for s in b),
            lost=sum(b[s]['success'] and not g[s]['success'] for s in b))
    dump(out/'summary.json',summaries)
    if smoke:dump(out/'preflight.json',technical)
    else:
        lines=['# Controllervergleich: geometrisch geprüfte Rückzugsfreigabe','',
            'Entwicklungsversuch auf20 neuen gepaarten Starts pro eingefrorenem Parent. Keine Trainingsupdates, keine alten Endtestrollouts.','',
            '| Parent | Baseline /20 | Geometrisches Gate /20 | Gewonnen / verloren | Bestätigte nächste Aufnahme Baseline / Gate | Gate-Timeouts |',
            '|---|---:|---:|---|---|---:|']
        for seed,s in summaries.items():
            b,g,p=s['baseline'],s['guarded'],s['paired']
            lines.append(f"| {seed} | {b['successes']} | {g['successes']} | {p['won']} / {p['lost']} | {b['confirmed_next_pickups']} / {g['confirmed_next_pickups']} | {g['timeouts']} |")
        lines+=['','Das Gate verlangt20 mm vertikale Trennung aller Greiferkontaktgeometrien über dem unteren Turm für drei gültige, kontaktfreie Frames sowie den gelernten Phase0-Abschluss. Boxen werden exakt entlang Welt-Z begrenzt; Meshes konservativ mit Bounding-Sphären. Der bestehende gelernte Phase0-Bewegungskopf wird weiter ausgeführt; kein geskriptetes XYZ-Kommando. Ein Rückzug ohne Freigabe nach200 Frames zählt als Controllerfehlschlag.','',
            '„Bestätigte nächste Aufnahme“: fünf native Griff+30mm-Lift-Frames und anschließend50 Frames kontinuierlich gültiger unterer Turm seit Freigabe. Dieser Zusatzwert ist eine Übergangsdiagnose; der vollständige Dreierturmerfolg bleibt das ursprüngliche50-Frame-Kriterium.','',
            'Grenzen: kleine Entwicklungspanels, drei verwandte Parents und privilegierte Simulatorgeometrie. Vertikale Freigabe prüft nicht den gesamten folgenden Bewegungskorridor. Keine Aussage zu neu gelernten Gewichten oder visuellem Closed Loop. Keine unabhängige Endtestbestätigung.','',
            'Baseline-Collector wurde im getrennten technischen Probelauf bitgenau gegen den vorhandenen nativen Collector geprüft. Hauptlauf prüft identische Initialzustände und identische Zustände/Aktionen bis zum ersten Rückzugsframe. Alle Gatefreigaben werden gegen die gespeicherten geometrischen Kriterien geprüft.']
        (out/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    for p,h in sources.items():assert sha(p)==h,'Source changed during run'
    dump(out/'status.json',dict(state='COMPLETED',episodes=len(output_rows),elapsed_seconds=time.time()-start,
        models_unchanged=True,smoke=smoke,updated_unix=time.time(),pid=os.getpid()))
    print(json.dumps(dict(summary=summaries,technical=technical)))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true');args=p.parse_args()
    try:compare(args.output.resolve(),args.smoke)
    except Exception:
        if args.output.exists():dump(args.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),pid=os.getpid(),updated_unix=time.time()))
        raise
