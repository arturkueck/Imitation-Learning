"""Paired frozen-BC intervention in the second grasp; no optimizer updates."""
from pathlib import Path
from types import SimpleNamespace
from datetime import datetime
import argparse
import ctypes
import hashlib
import importlib.util
import json
import os
import subprocess
import sys
import time
import traceback

_spec=importlib.util.spec_from_file_location('bc_phase_skill_helpers',Path(__file__).with_name('audit.py'))
audit=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(audit)

HERE=Path(__file__).resolve().parent
ROOT=audit.ROOT
read,write=audit.read,audit.write


def episode(env,model,seed,arm,out,deadline,plan):
    base,torch,np=audit.libraries();controller=base.backend()
    from task_extensions.stack_expert import StackExpert
    obs,initial,z=audit.reset(env,seed)
    seq=controller.GuardedSequencer(model,3,controller.Clearance(env))
    seq.policy=audit.validation.adapter.make_policy(base,controller.native.historical,model,.8,lambda:seq.stage,17)
    digest=hashlib.sha256(initial.tobytes());prefix=None;entry=None;lift=None;teacher=None
    trace=[];tail=0;expert_frames=0;intervention_done=False
    for frame in range(1000):
        base.check_stop(out,deadline)
        stage,phase,retreat=seq.stage,seq.policy.phase,seq.retreat
        pos=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if stage==2 and not retreat and prefix is None:
            prefix=digest.hexdigest();entry=frame
            if arm=='expert_grasp':
                teacher=StackExpert(SimpleNamespace(base_env=env));teacher.cube_index=2
        if stage==2 and phase==3 and lift is None and not retreat:
            lift=dict(frame=frame,held=bool(env._check_grasp(env.robots[0].gripper,env.cubes[2].contact_geoms)),
                      lower_valid=bool(controller.native.historical.old.prefix_valid(env,2)))
        expert_action=teacher is not None and not intervention_done
        if expert_action:
            phase=teacher.phase
            action=teacher(obs);probability=float(teacher.phase!=phase);expert_frames+=1
            seq.policy.phase=teacher.phase;seq.policy.steps=teacher.phase_steps;seq.policy.anchor=None
            if teacher.phase==3:
                # Preserve the last Close action; BC starts Lift on next frame.
                intervention_done=True;seq.policy.steps=0
        else:
            with torch.no_grad():action,phase,probability=seq.policy.action(obs,pos[stage-1],pos[stage])
        env.step(action);env.sim.forward();obs=env._get_observations(force_update=True)
        if prefix is None:
            digest.update(action.tobytes());digest.update(env.sim.get_state().flatten().tobytes())
        m=audit.measurement(env,obs,stage,z[stage],pos[stage]+np.array([0,0,.24]),controller)
        event=seq.advance(m['valid'][stage-1],env.sim.data.body_xpos[env.cube_ids[stage]])
        tail=tail+1 if m['valid'][-1] else 0
        trace.append(np.r_[frame,stage,phase,retreat,expert_action,probability,event,tail,m['eef'],m['positions'].ravel(),action,m['fingers'],m['valid'],m['velocities']])
        if tail>=50 or seq.timed_out:break
    return dict(seed=seed,arm=arm,success=tail>=50,frames=frame+1,
        initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(),prefix_sha256=prefix,
        second_grasp_entry_frame=entry,second_lift=lift,expert_frames=expert_frames,
        expert_completed=intervention_done,final_stage=seq.stage,final_phase=seq.policy.phase,
        retreat_timeout=seq.timed_out),np.asarray(trace)


def summarize(pairs):
    return dict(pairs=len(pairs),optimizer_updates=0,
        control_successes=sum(r['control']['success'] for r in pairs),
        intervention_successes=sum(r['expert_grasp']['success'] for r in pairs),
        gains=sum(not r['control']['success'] and r['expert_grasp']['success'] for r in pairs),
        losses=sum(r['control']['success'] and not r['expert_grasp']['success'] for r in pairs),
        control_second_lifts=sum(r['control']['second_lift'] is not None for r in pairs),
        control_grasps=sum(bool((r['control']['second_lift'] or {}).get('held')) for r in pairs),
        intervention_second_lifts=sum(r['expert_grasp']['second_lift'] is not None for r in pairs),
        intervention_grasps=sum(bool((r['expert_grasp']['second_lift'] or {}).get('held')) for r in pairs))


def worker(out,deadline):
    plan=read(out/'plan.json');base,torch,np=audit.libraries();base.configure(1)
    proof=read(out/'provenance.json')
    for path,digest in proof.items():
        if base.sha(ROOT/path)!=digest:raise ValueError('Input hash mismatch: '+path)
    prior={(r['model'],r['seed']):r for r in read(ROOT/plan['reference_results'])}
    pairs=[];controller=base.backend()
    try:
        for model_id in plan['models']:
            model,_,_=audit.registry.restore(model_id,'cuda');model.eval()
            env=controller.native.historical.make_env(3)
            try:
                for seed in plan['seeds']:
                    pair=dict(model=model_id,seed=seed)
                    for arm in ('control','expert_grasp'):
                        write(out/'status.json',dict(state='EVALUATING',pid=os.getpid(),model=model_id,seed=seed,arm=arm,completed_pairs=len(pairs),updated_unix=time.time(),deadline=deadline))
                        result,trace=episode(env,model,seed,arm,out,deadline,plan)
                        result['model']=model_id;pair[arm]=result
                        np.savez_compressed(out/'traces'/f'{model_id}_{seed}_{arm}.npz',trace=trace)
                    left,right=pair['control'],pair['expert_grasp']
                    for key in ('initial_sha256','prefix_sha256','second_grasp_entry_frame'):
                        if left[key]!=right[key]:raise ValueError('Paired prefix mismatch: '+key)
                    expected=prior[(model_id,seed)]
                    if any(left[k]!=expected[k] for k in ('initial_sha256','success','frames','final_stage','final_phase','retreat_timeout')):
                        raise ValueError('Control does not reproduce prior diagnosis')
                    if left['prefix_sha256'] is None and left['success']!=right['success']:
                        raise ValueError('Unexposed branches differ')
                    pairs.append(pair);write(out/'pairs.json',pairs);write(out/'summary.json',summarize(pairs))
            finally:env.close()
        for path,digest in proof.items():
            if base.sha(ROOT/path)!=digest:raise ValueError('Input changed: '+path)
        result=summarize(pairs);result['complete']=True;write(out/'summary.json',result)
        lines=['# Zweiter Greifprozess: gepaarte Intervention','',
               'Unveränderte B-Modelle; vorhandene Entwicklungsszenen; keine Optimizer-Updates. Expertenübernahme ausschließlich beim zweiten Approach/Grasp-Descend/Close, danach wieder BC.','',
               f"Paare: {result['pairs']}; Gesamtaufgabe: Kontrolle {result['control_successes']}, Experteneingriff {result['intervention_successes']}; Gewinne {result['gains']}, Verluste {result['losses']}.",'',
               f"Erkannter Griff am zweiten Lift: Kontrolle {result['control_grasps']}/{result['control_second_lifts']}, Eingriff {result['intervention_grasps']}/{result['intervention_second_lifts']}.",'',
               'Alle Kontrollausgänge reproduzieren die vorherige Diagnose. Anfangszustände und gesamte Simulations-/Aktionshistorie vor dem Eingriff stimmen paarweise exakt überein.','',
               'Dies prüft die Wirkung einer Expertenübernahme im zweiten Greifablauf; es ist kein Nachweis eines BC-Lernfortschritts und isoliert nicht die einzelnen drei ersetzten Phasen. Drei Modellseeds teilen dieselben 20 Szenen. Keine neuen Bestätigungsszenen wurden geöffnet.']
        (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
        write(out/'status.json',dict(state='COMPLETE',pid=os.getpid(),completed_pairs=len(pairs),updated_unix=time.time()))
    except BaseException as exc:
        write(out/'status.json',dict(state='FAILED',error=repr(exc),traceback=traceback.format_exc(),completed_pairs=len(pairs),updated_unix=time.time()))
        raise


def supervise(out,until,smoke):
    if out.exists() or not out.is_relative_to(ROOT):raise ValueError('Require new workspace output')
    end=datetime.fromisoformat(until)
    if end.tzinfo is None:raise ValueError('Deadline needs explicit timezone offset')
    deadline_requested=end.timestamp()
    if deadline_requested<=time.time():raise ValueError('Requested deadline is in the past')
    out.mkdir(parents=True);(out/'traces').mkdir()
    start=time.time();deadline=min(deadline_requested,start+1200)-10
    models=['mixed_s1_u30000','mixed_s2_u30000','mixed_s3_u30000']
    plan=dict(schema='second-grasp-intervention-v1',models=models[:1] if smoke else models,
        seeds=[2026113000] if smoke else list(range(2026113000,2026113020)),
        reference_results='praxis/results/curriculum/phase_skill_audit_v1/run_001/full_rollouts.json',
        intervention='Only second-placement expert phases 0,1,2; return to unchanged BC at Lift',
        requested_end=until,deadline=deadline,maximum_seconds=1200,technical_only=smoke,
        optimizer_updates=0,automatic_restart=False,pc_shutdown=False)
    write(out/'plan.json',plan)
    base,_,_=audit.libraries();entries=read(HERE.parent/'models.json')['models']
    paths=[Path(__file__),HERE/'audit.py',HERE.parent/'registry.py',HERE/'NEXT_EXPERIMENT.md',
           HERE.parent/'axis_bc_clock_validation_20261112/policy.py',ROOT/plan['reference_results']]
    paths += [ROOT/entries[m]['checkpoint'] for m in plan['models']]
    write(out/'provenance.json',{str(p.relative_to(ROOT)):base.sha(p) for p in paths})
    awake=False;process=None;state=dict(pid=os.getpid(),started_unix=start,deadline=deadline,state='STARTING')
    try:
        if os.name=='nt':awake=bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('w',encoding='utf-8') as log:
            process=subprocess.Popen([sys.executable,'-u',str(Path(__file__).resolve()),'--worker','--output',str(out),'--deadline',str(deadline)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
            state.update(state='RUNNING',worker_pid=process.pid,sleep_prevention_active=awake)
            write(out/'supervisor_status.json',state)
            try:code=process.wait(timeout=max(1,deadline+5-time.time()))
            except subprocess.TimeoutExpired:
                process.kill();process.wait();raise TimeoutError('Hard runtime limit reached')
            if code:raise RuntimeError('Worker failed; see worker.log')
        state['state']=read(out/'status.json')['state']
    except BaseException as exc:
        state.update(state='FAILED',error=repr(exc));raise
    finally:
        if process is not None and process.poll() is None:process.kill();process.wait()
        if awake:ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(),sleep_prevention_active=False)
        write(out/'supervisor_status.json',state)


def status(out):
    import psutil
    supervisor=read(out/'supervisor_status.json')
    current=read(out/'status.json') if (out/'status.json').exists() else {}
    active=supervisor['state']=='RUNNING'
    alive=False
    if active:
        try:
            proc=psutil.Process(supervisor['worker_pid'])
            alive=proc.is_running() and proc.create_time()>=supervisor['started_unix']-2
        except psutil.NoSuchProcess:pass
    state=current.get('state',supervisor['state'])
    if active and not alive:state='WARNING_WORKER_NOT_ALIVE'
    prior=read(out/'monitor_state.json') if (out/'monitor_state.json').exists() else {}
    log=out/'worker.log';offset=prior.get('log_offset',0);errors=[]
    if log.exists():
        size=log.stat().st_size
        if offset>size:offset=0
        with log.open('rb') as stream:
            stream.seek(offset);new=stream.read().decode('utf-8',errors='replace')
        errors=[line for line in new.splitlines() if 'Traceback' in line or 'Error:' in line]
        offset=size
    progressed=current.get('completed_pairs',0)>prior.get('completed_pairs',-1)
    if active and alive and not progressed and time.time()-current.get('updated_unix',time.time())>300:state='WARNING_NO_PROGRESS'
    write(out/'monitor_state.json',dict(checked_unix=time.time(),log_offset=offset,completed_pairs=current.get('completed_pairs',0),state=state))
    print(json.dumps(dict(state=state,worker_alive=alive if active else None,
        completed_pairs=current.get('completed_pairs',0),total_pairs=len(read(out/'plan.json')['seeds'])*len(read(out/'plan.json')['models']),
        new_errors=errors,deadline=supervisor['deadline'],optimizer_updates=0)))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    p.add_argument('--until');p.add_argument('--smoke',action='store_true');p.add_argument('--worker',action='store_true');p.add_argument('--deadline',type=float);p.add_argument('--status',action='store_true')
    args=p.parse_args()
    if args.status:status(args.output.resolve())
    elif args.worker:worker(args.output.resolve(),args.deadline)
    else:
        if not args.until:p.error('--until with explicit UTC offset is required')
        supervise(args.output.resolve(),args.until,args.smoke)
