"""Paired camera-guidance validation; frozen V3 predictions, zero updates."""
import json,time,math,shutil
from collections import Counter
import numpy as np
import pilot as P
from data_v3 import PoseGenerator,object_path_free
from pilot_bank import static_signature
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Planner,Focus
from active_view.side_views import aimed_pose,optical_axis_error,side_frame
from active_view.camera_guidance import swept_envelopes,refine_view,view_metrics
from active_view.geometry import segment_aabb_intersection

SOURCE=P.HERE/'pilot_002'
def certificate(c,waypoints,out,id):
    low=[];high=[]
    for a,b in zip(waypoints[:-1],waypoints[1:]):
        if not c.edge(a,b):return None
        lo,hi=swept_envelopes(c,a,b,pieces=128);low.append(lo);high.append(hi)
    camera,R=c.camera_pose(waypoints[-1]);value=dict(id=id,q=waypoints[-1],waypoints=waypoints,camera=camera,rotation=R,low=np.concatenate(low),high=np.concatenate(high))
    path=out/f'certificate_{id:03d}.npz';np.savez_compressed(path,**value)
    value['certificate_sha256']=P.sha(path);return value

def build_bank(g,out):
    began=time.perf_counter();g._setup(np.random.default_rng(94140202),0,'scattered',False)
    c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=g.base_qpos[c.qadr].copy();g.qadr=c.qadr;c.set_q(start)
    signature=static_signature(g,c);assert signature==json.loads((SOURCE/'bank.json').read_text())['static_signature']
    bank=[];source=P.HERE/'pilot_001/families.jsonl'
    records=[json.loads(x) for x in source.read_text().splitlines()]
    for r in records:
        if r.get('stage')!='captured':continue
        family='right' if r['requested_family']=='difficult' else r['requested_family']
        route=[start]+[np.asarray(q,float) for q in r['waypoints']]
        route=[q for i,q in enumerate(route) if i==0 or np.max(np.abs(q-route[i-1]))>1e-9]
        entry=certificate(c,route,out,len(bank))
        if entry is None:continue
        entry.update(family=family,origin=dict(kind='preserved_predicted_focus_pose',index=r['index']))
        bank.append(entry)
        print(json.dumps(dict(stage='expanded_certificate',id=entry['id'],family=family)),flush=True)
    # No object GT: workspace-centred anchors only. Include wider posture seeds
    # and roll variants for the formerly absent base-looking-outward family.
    anchors=[np.array([0.,0.,.90]),np.array([-.08,0.,.98])]
    planner=Planner(c,seed=94140311);base_audit=Counter();seeds=[start]+[e['q'] for e in bank]
    for anchor in anchors:
        for lateral in [-.12,.12,0.]:
            position=anchor+np.array([-.32,lateral,.22])
            for roll in [0.,math.pi/2,-math.pi/2,math.pi]:
                desired=aimed_pose(position,anchor,roll);q=None
                ranked=[]
                for seed in seeds:
                    pc,rc=c.camera_pose(seed);ranked.append((np.linalg.norm(pc-position)+.1*np.linalg.norm(rc-desired),seed))
                for _,seed in sorted(ranked,key=lambda x:x[0])[:5]:
                    base_audit['ik_attempts']+=1;q=planner.ik(position,desired,seed,iterations=160)
                    if q is not None:break
                if q is None:continue
                base_audit['valid_ik']+=1
                metrics,why=view_metrics(c,q,Focus(anchor,.04),c.camera_pose(start)[0],g.d.xpos[g.m.body(g.env.robots[0].robot_model.root_body).id].copy(),'base')
                if metrics is None:base_audit[why]+=1;continue
                plan=planner.path(start,q,max_nodes=100,seconds=3.)
                if plan is None:base_audit['path_blocked']+=1;continue
                entry=certificate(c,plan.waypoints,out,len(bank))
                if entry is None:base_audit['recertification_failed']+=1;continue
                entry.update(family='base',origin=dict(kind='object_independent_workspace_anchor',anchor=anchor))
                bank.append(entry);seeds.append(q);base_audit['certified']+=1
                print(json.dumps(dict(stage='base_certificate',id=entry['id'])),flush=True)
                break
            if base_audit['certified']>=4:break
        if base_audit['certified']>=4:break
    c.set_q(start)
    P.save(out/'bank.json',dict(signature=signature,envelope_pieces=128,world_margin_m=c.world_margin,self_margin_m=c.self_margin,
        entries=[{k:v for k,v in e.items() if k not in ['low','high']} for e in bank],base_search=dict(base_audit),seconds=time.perf_counter()-began))
    return start,signature,bank

def candidate_order(bank,focus,family,c,base,start_camera,truth):
    scored=[];reasons=Counter();requested='right' if family=='difficult' else family
    for e in bank:
        if e['family']!=requested:continue
        if not object_path_free(e['low'],e['high'],**truth):reasons['swept_object']+=1;continue
        delta=e['camera']-focus.center;distance=np.linalg.norm(delta)
        if distance<=focus.radius+.05:reasons['too_close']+=1;continue
        axis=side_frame(base,focus.center)['left' if requested=='elevated' else requested]
        if delta@axis<.10:reasons['wrong_side']+=1;continue
        error=optical_axis_error(e['camera'],e['rotation'],focus.center)
        if error>60:reasons['excessive_retargeting']+=1;continue
        score=error+.2*np.linalg.norm(e['camera']-start_camera)
        scored.append((score,e))
    return [e for _,e in sorted(scored,key=lambda v:v[0])],reasons

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--name',default='guidance_001');args=p.parse_args()
    out=P.HERE/args.name;out.mkdir(exist_ok=False);(out/'source').mkdir();P.settings();began=time.perf_counter()
    files=[__file__,str(P.HERE/'guidance_probe.py'),str(P.ROOT/'praxis/src/active_view/camera_guidance.py'),str(P.ROOT/'praxis/src/active_view/collision.py'),str(P.ROOT/'praxis/src/active_view/side_views.py'),str(P.HERE/'pilot_bank.py')]
    for name in files:
        f=P.Path(name);dest=out/'source'/f.relative_to(P.ROOT);dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dest)
    P.save(out/'manifest.json',dict(training_started=False,optimizer_updates=0,validation_only=True,source='pilot_002 same 200 development families',
        source_families_sha256=P.sha(SOURCE/'families.jsonl'),focuses_sha256=P.sha(P.HERE/'guidance_probe_001/focuses.json'),
        changes=['all preserved pose seeds instead of three per family','128-piece conservative envelopes instead of 32','target-centred FK-verified wrist refinement','explicit base-family search'],
        source_hashes={str(P.Path(f).relative_to(P.ROOT)):P.sha(f) for f in files}))
    old=[json.loads(x) for x in (SOURCE/'families.jsonl').read_text().splitlines()];focuses=json.loads((P.HERE/'guidance_probe_001/focuses.json').read_text())
    g=PoseGenerator();records=[];audited=[];selected_examples={};reason_totals=Counter()
    try:
        start,signature,bank=build_bank(g,out);bank_seconds=time.perf_counter()-began
        for previous,description in zip(old,focuses):
            if (out/'STOP_REQUESTED').exists():raise RuntimeError('Guidance stop requested')
            tick=time.perf_counter();index=previous['index'];family=previous['requested_family'];record=dict(index=index,requested_family=family,old_stage=previous['stage'],stage='blocked')
            with np.load(SOURCE/'samples'/f'sample_{index:04d}.npz') as z:sample={k:np.array(z[k]) for k in z.files}
            assert P.sha(SOURCE/'samples'/f'sample_{index:04d}.npz')==previous['sample_sha256']
            if description is None:record['reason']='no_predicted_focus'
            elif not any(e['family']==('right' if family=='difficult' else family) for e in bank):record['reason']='no_certified_bank_candidate'
            else:
                rng=np.random.default_rng(np.random.SeedSequence([94140202,index]))
                for _ in range(40):
                    try:g._setup(rng,previous['count'],previous['kind'],previous['shape']=='long_thin');break
                    except ValueError:pass
                else:raise RuntimeError('Scene reconstruction failed')
                actual=np.array([g.d.xpos[b].copy() for b in g.bodies])
                if np.max(np.abs(actual-sample['positions']))>1e-5:raise RuntimeError('Stored scene mismatch')
                c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));g.qadr=c.qadr;c.set_q(start)
                if static_signature(g,c)!=signature:raise RuntimeError('Bank contract changed')
                if not c.check(start).valid:raise RuntimeError('Initial arm not free')
                focus=Focus(np.array(description['center']),description['radius']);body=g.m.body(g.env.robots[0].robot_model.root_body).id;base=g.d.xpos[body].copy();start_camera,_=c.camera_pose(start)
                truth={k:sample[k] for k in ['positions','sizes','rotations','active']}
                proposals,reasons=candidate_order(bank,focus,family,c,base,start_camera,truth);record['precheck_reasons']=dict(reasons);record['candidate_count']=len(proposals)
                chosen=None;refine_reasons=Counter();planner=Planner(c,seed=94140312+index)
                for e in proposals[:5]:
                    result=refine_view(planner,focus,start_camera,base,'right' if family=='difficult' else family,e['q'])
                    if result['stage']!='aimed':refine_reasons[result['reason']]+=1;continue
                    camera=result['metrics']['camera'];delta=focus.center-camera;distance=np.linalg.norm(delta);end=focus.center-delta/distance*focus.radius
                    if any(segment_aabb_intersection(camera,end,b,padding=.002) for b in c.world.boxes):refine_reasons['sightline_occluded']+=1;continue
                    route=e['waypoints']+[q for q in result['suffix'][1:]]
                    chosen=(e,result,route);break
                record['refinement_reasons']=dict(refine_reasons)
                if chosen:
                    e,result,route=chosen;states=0
                    for a,b in zip(route[:-1],route[1:]):
                        for alpha in np.linspace(0,1,9):c.set_q(a+(b-a)*alpha);P.native_check(g);states+=1
                    # Independent full-world edge checks on representative newly
                    # admitted cases, beyond the analytic object certificate.
                    group=(family,previous['kind'])
                    if previous['stage']!='captured' and group not in audited:
                        for a,b in zip(route[:-1],route[1:]):
                            if not c.edge(a,b):raise RuntimeError('Independent full-world path audit failed')
                        audited.append(group);record['independent_full_path_audit']=True
                    metrics=result['metrics'];record.update(stage='captured',bank_id=e['id'],refined=result['refined'],q=result['q'],waypoints=route,
                        actual_camera=dict(position=metrics['camera'],rotation=metrics['rotation']),desired_focus=focus.center,
                        optical_axis_error_deg=metrics['optical_axis_error_deg'],elevation_deg=metrics['elevation_deg'],camera_change=metrics['change'],native_replay_states=states)
                    if family not in selected_examples:
                        c.set_q(result['q']);row=g.observation({k:sample[k] for k in ['positions','sizes','rotations','active','count','kind','family']},result['q'])
                        np.savez_compressed(out/f'example_{family}.npz',**row);P.save(out/f'example_{family}.json',record);selected_examples[family]=index
                else:record['reason']='no_admissible_target_centred_view'
                reason_totals.update(reasons);reason_totals.update(refine_reasons)
                c.set_q(start)
            record['seconds']=time.perf_counter()-tick;records.append(record)
            with (out/'families.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(record,default=P.jsonable)+'\n')
            if (index+1)%20==0:
                status=dict(stage='guidance_validation',completed=index+1,total=200,captured=sum(r['stage']=='captured' for r in records),elapsed_seconds=time.perf_counter()-began)
                P.save(out/'status.json',status);print(json.dumps(status),flush=True)
    finally:g.close()
    captured=[r for r in records if r['stage']=='captured'];comparison={f:dict(attempted=sum(r['requested_family']==f for r in records),before=sum(r['requested_family']==f and r['old_stage']=='captured' for r in records),after=sum(r['requested_family']==f and r['stage']=='captured' for r in records)) for f in ['right','left','base','elevated','difficult']}
    report=dict(training_started=False,optimizer_updates=0,completed=True,comparison=comparison,total_before=47,total_after=len(captured),
        bank_entries=len(bank),bank_seconds=bank_seconds,validation_seconds=time.perf_counter()-began-bank_seconds,elapsed_seconds=time.perf_counter()-began,
        independent_full_path_audits=len(audited),audited_groups=audited,native_replay_states=sum(r.get('native_replay_states',0) for r in records),native_robot_world_penetrations=0,
        maximum_axis_error_deg=max([r['optical_axis_error_deg'] for r in captured],default=None),mean_axis_error_deg=float(np.mean([r['optical_axis_error_deg'] for r in captured])) if captured else None,
        refined_views=sum(r.get('refined',False) for r in records),examples=selected_examples,rejections=dict(reason_totals),
        scope='Paired development-set simulation reference validation, no blind-test/perception-quality or visual-free-space claim')
    P.save(out/'report.json',report);P.save(out/'status.json',dict(stage='completed',training_started=False));print(json.dumps(report,default=P.jsonable),flush=True)

if __name__=='__main__':main()
