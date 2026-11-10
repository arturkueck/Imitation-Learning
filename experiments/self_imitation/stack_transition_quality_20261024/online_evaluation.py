"""Native transition/full-rollout evaluation; no training or default simulation.

Prepared snapshots must originate from disjoint benchmark families and carry a
validated complete replay snapshot. Preparation failures remain denominator rows.
"""
from pathlib import Path
import hashlib,json,time
import numpy as np

HERE=Path(__file__).resolve().parent

def check_deadline(deadline):
    if time.time()>=deadline: raise TimeoutError('evaluation deadline')

def rate(result):
    assert result['attempts']>0 and result.get('complete',False),'incomplete evaluation'
    return result['successes']/result['attempts']

def selection_score(metrics, baseline, update):
    """Worst prepared stratum, full4, negative worst lower regression, earlier."""
    primary=min(rate(metrics[k]) for k in ('prepared_prefix2','prepared_prefix3'))
    regression=max([0.]+[rate(baseline[k])-rate(metrics[k]) for k in ('full_stack2','full_stack3')])
    return (primary,rate(metrics['full_stack4']),-regression,-int(update))

class TransitionJudge:
    """Streaming metric: 5 native grasp+lift frames, then50 protected frames.

    Prefix must be continuously valid from the initial prepared state. Pickup
    confirmation is bounded at200 actions; following50 are outcome-only.
    """
    def __init__(self,source_z,initial_valid=True,max_pickup=200,grasp_frames=5,tail_frames=50):
        self.source_z=float(source_z);self.continuous=bool(initial_valid)
        self.max_pickup=max_pickup;self.grasp_frames=grasp_frames;self.tail_frames=tail_frames
        self.grasp_run=0;self.pickup=None;self.steps=0;self.tail=0
        self.contact_frames=0;self.invalid_frames=0;self.success=False
    def step(self,*,valid,held,source_z,tower_contact=False):
        self.steps+=1;self.continuous &= bool(valid) and not tower_contact
        self.contact_frames+=int(tower_contact);self.invalid_frames+=int(not valid)
        if self.pickup is None:
            self.grasp_run=self.grasp_run+1 if held and source_z>=self.source_z+.03 else 0
            if self.grasp_run>=self.grasp_frames and self.steps<=self.max_pickup:self.pickup=self.steps
        else:self.tail+=1
        self.success=self.pickup is not None and self.tail>=self.tail_frames and self.continuous
        return self.success or not self.continuous or (self.pickup is None and self.steps>=self.max_pickup)
    def result(self):
        return dict(success=bool(self.success),steps=self.steps,pickup_step=self.pickup,
                    confirmation_frames=self.tail,continuous_prefix=bool(self.continuous),
                    invalid_frames=self.invalid_frames,tower_contact_frames=self.contact_frames)

def _summary(rows,total,complete=True):
    return dict(successes=sum(bool(r.get('success',False)) for r in rows),attempts=len(rows),
                planned_attempts=total,complete=complete and len(rows)==total,rows=rows)

class _Progress:
    """Durable completed rows plus a separately marked possibly consumed start."""
    def __init__(self,path,total):
        self.path=None if path is None else Path(path);self.total=total;self.rows=[];self.active=None
        if self.path is not None:
            self.path.parent.mkdir(parents=True,exist_ok=True)
            assert not self.path.exists(),'evaluation progress exists; automatic rerun forbidden'
        self.write()
    def write(self,complete=False):
        if self.path is None:return
        data=_summary(self.rows,self.total,complete)
        data.update(in_progress_seed=self.active,completed_starts=[r['seed'] for r in self.rows],
                    possibly_consumed_unfinished_starts=[] if self.active is None else [self.active],
                    updated_unix=time.time(),automatic_repeat_forbidden=True)
        tmp=self.path.with_suffix('.tmp');tmp.write_text(json.dumps(data,indent=2),encoding='utf-8');tmp.replace(self.path)
    def begin(self,seed):self.active=int(seed);self.write()
    def add(self,row):self.rows.append(row);self.active=None;self.write()
    def finish(self,result):self.active=None;self.write(result['complete'])

def _restore(env,model,row):
    """Load a hash-verified complete replay snapshot without replacing model."""
    import state_replay
    from native_collector import historical
    assert row.get('replay_verified',False),'prepared snapshot replay not verified'
    snapshot=state_replay.load(row['path'],row['sha256'])
    seq=historical.Sequencer(model,len(env.cubes))
    obs=state_replay.restore(env,seq,snapshot)
    return obs,seq

def evaluate_prepared(model,rows,deadline,*,restore=None,max_frames=250,progress_path=None):
    from native_collector import historical, finger_contact
    restore=restore or _restore;results=[];envs={};progress=_Progress(progress_path,len(rows))
    try:
        for row in rows:
            check_deadline(deadline);prefix=int(row['prefix']);count=prefix+1
            progress.begin(row['seed'])
            if not row.get('prepared',True):
                result=dict(seed=row['seed'],success=False,preparation_failure=row.get('reason','unavailable prepared state'))
                results.append(result);progress.add(result);continue
            env=envs.get(count)
            if env is None:env=envs[count]=historical.make_env(count)
            # A restore failure is technical, never silently turned into a policy failure.
            obs,seq=restore(env,model,row)
            source=prefix;positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            initial=historical.old.prefix_valid(env,prefix) and not any(finger_contact(env,c) for c in env.cubes[:prefix])
            judge=TransitionJudge(positions[source,2],initial)
            max_displacement=0.;reference=positions[:prefix].copy();phase_counts={}
            finished=False
            for _ in range(max_frames):
                check_deadline(deadline);phase=seq.policy.phase
                phase_counts[str(phase)]=phase_counts.get(str(phase),0)+1
                positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                action,_,_=seq.policy.action(obs,positions[seq.stage-1],positions[seq.stage])
                env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
                fingers=np.array([finger_contact(env,c) for c in env.cubes])
                valid=historical.old.prefix_valid(env,prefix) and not fingers[:prefix].any()
                positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
                max_displacement=max(max_displacement,float(np.linalg.norm(positions[:prefix]-reference,axis=-1).max()))
                held=env._check_grasp(env.robots[0].gripper,env.cubes[source].contact_geoms)
                finished=judge.step(valid=valid,held=held,source_z=positions[source,2],tower_contact=bool(fingers[:prefix].any()))
                # Keep the exact unchanged sequencer; phase0 retreat belongs to the prior pair.
                valid_stage=historical.old.prefix_valid(env,seq.stage+1) and not fingers[:seq.stage+1].any()
                seq.advance(valid_stage,positions[seq.stage])
                if finished:break
            result=judge.result();result.update(seed=row['seed'],prefix=prefix,max_lower_displacement_m=max_displacement,
                                                phase_frames=phase_counts,censored=not finished)
            results.append(result)
            progress.add(result)
    finally:
        for env in envs.values():env.close()
    result=_summary(results,len(rows),complete=all(not r.get('censored',False) for r in results))
    progress.finish(result);return result

def evaluate_full(model,count,seeds,deadline,*,max_frames=None,progress_path=None):
    from native_collector import historical, collect
    progress=_Progress(progress_path,len(seeds));env=historical.make_env(count);rows=[]
    try:
        for seed in seeds:
            check_deadline(deadline)
            progress.begin(seed)
            a,r=collect(env,model,count,seed,max_frames or 500*(count-1),deadline)
            r['success']=bool(r['complete_success']);r['technical_censored']=bool(r['censored'])
            r['phase_frames']={str(p):int((a['p']==p).sum()) for p in range(7)}
            r['retreat_frames']=int(a['retreat'].sum());rows.append(r);progress.add(r)
    finally:env.close()
    result=_summary(rows,len(seeds),complete=all(not r['technical_censored'] for r in rows))
    progress.finish(result);return result

def evaluator_from_plan(plan,prepared_manifests,progress_root=None):
    """Callback(path, seed, update, split, deadline) used by paired training."""
    def evaluate(path,seed,update,split,deadline):
        from native_collector import historical
        from transition_pilot import sha
        checkpoint=Path(path);checkpoint_hash=sha(checkpoint)
        # Training paths are .../B0_seed1/update3000.pth; frozen paths are
        # .../final_test/B0_seed1.pth. Keep arms distinct even for identical hashes.
        name=checkpoint.stem if checkpoint.stem.startswith(('B0_seed','B_seed')) else checkpoint.parent.name
        progress_folder=None
        if progress_root is not None:
            progress_folder=Path(progress_root)/split/name/f'update{update}_{checkpoint_hash[:16]}'
            progress_folder.mkdir(parents=True,exist_ok=False)
            (progress_folder/'callback.json').write_text(json.dumps(dict(checkpoint=str(checkpoint.resolve()),
                checkpoint_sha256=checkpoint_hash,model=name,seed=seed,update=update,split=split),indent=2),encoding='utf-8')
        model=historical.load(path);ranges=plan['evaluation'][split];result={}
        for key,limits in ranges.items():
            seeds=list(range(int(limits[0]),int(limits[1])+1))
            if key.startswith('prepared_prefix'):
                manifest=prepared_manifests[split][key]
                data=json.loads(Path(manifest).read_text()) if isinstance(manifest,(str,Path)) else manifest
                rows=data['rows'];assert [int(r['seed']) for r in rows]==seeds,'prepared panel seed mismatch'
                result[key]=evaluate_prepared(model,rows,deadline,progress_path=None if progress_folder is None else progress_folder/(key+'.json'))
            elif key.startswith('full_stack'):result[key]=evaluate_full(model,int(key[-1]),seeds,deadline,progress_path=None if progress_folder is None else progress_folder/(key+'.json'))
        return result
    return evaluate

def prepare_reserved_panels(plan,output,deadline,frozen_selectionpath,*,plan_sha256=None,technical=False):
    """Once-only Teacher construction AFTER every selected model is frozen.

    Source families540000/541000 are distinct from panel identifiers530000/531000.
    They never enter collection/training. Technical mode uses only498003 and
    writes a clearly excluded one-family preparation artifact.
    """
    from native_collector import historical,collect
    from transition_pilot import sha,dump
    import state_replay
    output=Path(output);output.mkdir(parents=True,exist_ok=False)
    selection_path=Path(frozen_selectionpath);frozen=json.loads(selection_path.read_text())
    expected={f'{arm}_seed{seed}' for arm in ('B0','B') for seed in (1,2,3)}
    assert set(frozen)==expected,'all six selected models must be frozen before preparation'
    for info in frozen.values():assert sha(info['path'])==info['sha256'],'frozen model changed before panel preparation'
    planhash=plan_sha256 or hashlib.sha256(json.dumps(plan,sort_keys=True,separators=(',',':')).encode()).hexdigest()
    marker=dict(state='PREPARATION_STARTED',plan_sha256=planhash,selection_sha256=sha(selection_path),
                frozen_model_hashes={name:f['sha256'] for name,f in frozen.items()},technical_only=technical,
                started_unix=time.time(),no_automatic_retry=True)
    with (output/'preparation.started.json').open('x',encoding='utf-8') as stream:json.dump(marker,stream,indent=2)
    parents=plan['parents'];assert len(parents)==3
    models=[]
    for p in parents:
        assert sha(p['path'])==p['sha256'],'construction Teacher mutated'
        models.append(historical.load(p['path']))
    panels={};active_rows=[]
    class Captured(Exception):pass
    try:
        for prefix,source_base in ((2,540000),(3,541000)):
            if technical and prefix!=2:continue
            key=f'prepared_prefix{prefix}';limits=plan['evaluation']['reserved_final'][key]
            panel_seeds=[498003] if technical else list(range(limits[0],limits[1]+1))
            assert technical or len(panel_seeds)==50,'frozen reserved panel requires50 starts per prefix'
            rows=[];active_rows=rows;path=output/f'{key}.json';panels[key]=str(path.resolve())
            env=historical.make_env(prefix+1)
            try:
                for index,panel_seed in enumerate(panel_seeds):
                    check_deadline(deadline);source_seed=498003 if technical else source_base+index
                    teacher_index=index%3;captured={}
                    def hook(frame,current_env,seq,obs):
                        if not(seq.retreat and seq.policy.steps==0 and seq.stage+1==prefix):return
                        snapshot=state_replay.capture(current_env,seq,obs)
                        proof=state_replay.identity_probe(current_env,seq,obs)
                        captured.update(snapshot=snapshot,proof=proof,frame=frame)
                        raise Captured()
                    frame_count=None
                    try:
                        _,report=collect(env,models[teacher_index],prefix+1,source_seed,500*prefix,deadline,hook)
                        frame_count=report['frames']
                    except Captured:frame_count=captured['frame']
                    row=dict(seed=panel_seed,source_seed=source_seed,count=prefix+1,prefix=prefix,
                        family_id=f'reserved-native-v3:n{prefix+1}:seed{source_seed}',panel='technical' if technical else 'reserved_final',
                        teacher=parents[teacher_index]['path'],teacher_sha256=parents[teacher_index]['sha256'],
                        construction_frames=frame_count,technical_only=technical,never_training_data=True)
                    if captured:
                        snapshot_path=output/f'{source_seed}_prefix{prefix}.pkl'
                        snapshot_hash=state_replay.save(snapshot_path,captured['snapshot'])
                        row.update(prepared=True,path=str(snapshot_path.resolve()),sha256=snapshot_hash,
                                   frame=captured['frame'],replay_verified=True,replay_proof=captured['proof'])
                    else:row.update(prepared=False,replay_verified=False,reason='fixed Teacher attempt never reached released stable prefix')
                    rows.append(row)
                    dump(path,dict(complete=len(rows)==len(panel_seeds),rows=rows,planned_attempts=len(panel_seeds),
                                   technical_only=technical,plan_sha256=planhash))
            finally:env.close()
        dump(output/'prepared_panels.json',dict(complete=True,panels=panels,technical_only=technical,
                                                plan_sha256=planhash,frozen_selection_sha256=sha(selection_path)))
        return panels
    except Exception as exc:
        dump(output/'partial.json',dict(state='PARTIAL_PREPARATION',error=repr(exc),panels=panels,
                                        active_rows=len(active_rows),technical_only=technical))
        raise

if __name__=='__main__':
    print(json.dumps(dict(mode='DRY_RUN',simulation_started=False,module='native online evaluation')))
