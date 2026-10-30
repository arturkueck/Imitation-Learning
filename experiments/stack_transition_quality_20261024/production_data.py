"""Bounded native data preparation only. Never performs optimizer updates."""
from pathlib import Path
import argparse, hashlib, json, os, time
from datetime import datetime, timezone
HERE=Path(__file__).resolve().parent
os.environ.setdefault('NUMBA_CACHE_DIR',str(HERE/'numba_cache'))
import numpy as np
import torch
import native_collector as native
import state_replay
from transition_pilot import sha,dump,extract,audit_teacher,split_audit

def run(output,plan_path,probe=False,resume=False,max_seconds=1800):
    output=Path(output);plan_path=Path(plan_path);plan=json.loads(plan_path.read_text())
    plan_hash=sha(plan_path);start=time.time();origin=start;deadline=start+min(max_seconds,1800)
    torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False
    parents=plan['parents'];models=[]
    for info in parents:
        assert sha(info['path'])==info['sha256'],'parent changed'
        models.append(native.historical.load(info['path']))
    if resume:
        manifest=json.loads((output/'manifest.json').read_text());assert manifest['plan_sha256']==plan_hash,'plan changed'
        origin=manifest.get('preparation_start_epoch',datetime.strptime(manifest['started_utc'],'%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
        deadline=min(deadline,origin+1800)
        for row in manifest['rows']:assert sha(row['path'])==row['sha256'],'source changed'
    else:
        output.mkdir(parents=True,exist_ok=False)
        manifest=dict(schema='native_transition_dataset_v3',plan_sha256=plan_hash,
            preparation_start_epoch=start,
            started_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),complete=False,
            original_sha256=sha(native.historical.DATA),rows=[],sections=[],prepared_starts=[],
            rejection_rows=[],production_training_started=False,score_version='strict_contact_lift_v1_no_clearance')
        (output/'source_plan.json').write_bytes(plan_path.read_bytes())
        subset={k:plan[k] for k in ('collection','events','score','parents')}
        dump(output/'data_rules.json',subset)
        manifest['data_rules_sha256']=sha(output/'data_rules.json')
    seen={(r['count'],r['seed']) for r in manifest['rows']}
    revision_path=output/'cohort_revision_v2.json'
    revision=json.loads(revision_path.read_text()) if revision_path.exists() else None
    if revision is not None:
        assert revision['reason']=='measured_runtime_only' and revision['quality_gates_unchanged'] is True
        allowed=revision['fixed_indices'];assert allowed==list(range(60))+list(range(160,200))
        manifest['cohort_revision_sha256']=sha(revision_path)
        manifest['effective_data_rules_sha256']=hashlib.sha256((manifest['data_rules_sha256']+manifest['cohort_revision_sha256']).encode()).hexdigest()
    else:allowed=list(range(200))
    # Fixed early probe covers train AND valid before inspecting any outcome.
    indices=list(range(20))+list(range(160,180))
    if not probe:indices += [i for i in allowed if i not in indices]
    try:
        for count,base in ((3,510000),(4,511000)):
            env=native.historical.make_env(count);folder=output/f'n{count}';folder.mkdir(exist_ok=True)
            try:
                xmlpath=folder/'model.xml';xml=env.model.get_xml()
                if xmlpath.exists():assert xmlpath.read_text(encoding='utf-8')==xml
                else:xmlpath.write_text(xml,encoding='utf-8')
                for index in indices:
                    seed=base+index
                    if (count,seed) in seen:continue
                    if time.time()>=deadline:raise TimeoutError('fixed preparation wall-clock cap')
                    split='train' if index<160 else 'valid';ti=index%3
                    family=f'native-v3:n{count}:seed{seed}';snapshots={}
                    def hook(frame,env,seq,obs):
                        if not (seq.retreat and seq.policy.steps==0):return
                        prefix=seq.stage+1
                        if prefix in snapshots:return
                        snap=state_replay.capture(env,seq,obs)
                        proof=state_replay.identity_probe(env,seq,obs)
                        snapshots[prefix]=(frame,snap,proof)
                    arrays,report=native.collect(env,models[ti],count,seed,500*(count-1),deadline,hook)
                    audit_teacher(arrays,models[ti],'cuda')
                    path=folder/f'{seed}.npz';assert not path.exists()
                    np.savez_compressed(path,**arrays)
                    row=dict(report,path=str(path.resolve()),sha256=sha(path),teacher=parents[ti]['path'],
                        teacher_sha256=parents[ti]['sha256'],split=split,native_collector=True,
                        initial_sha256=hashlib.sha256(arrays['initial'].tobytes()).hexdigest(),
                        initial_family_id=family,xml_sha256=sha(xmlpath),teacher_action_audit='all frames single inference')
                    row['success']=row['complete_success']
                    reject=[];sections=extract(arrays,row,reject,dict(held_post=arrays['held_post'],held_known=arrays['held_known']))
                    for section in sections:section['initial_family_id']=family
                    manifest['sections'].extend(sections);manifest['rejection_rows'].extend(reject)
                    manifest['rows'].append(row);seen.add((count,seed))
                    # First20 validation families define a fixed prepared panel;
                    # unavailable starts remain explicit denominator failures.
                    if split=='valid':
                        prefix=count-1;confirm=index>=180
                        panel_seed=(525000 if confirm else 520000)+(prefix-2)*1000+index-(180 if confirm else 160)
                        prepared=dict(seed=panel_seed,count=count,prefix=prefix,split=split,
                            panel='confirmation' if confirm else 'development',
                            family_id=family,episode=str(path.resolve()),episode_sha256=row['sha256'])
                        if prefix in snapshots:
                            frame,snap,proof=snapshots[prefix]
                            snapshotpath=folder/f'{seed}_prefix{prefix}.pkl'
                            snapshotsha=state_replay.save(snapshotpath,snap)
                            prepared.update(prepared=True,path=str(snapshotpath.resolve()),sha256=snapshotsha,
                                frame=frame,replay_verified=True,replay_proof=proof)
                        else:prepared.update(prepared=False,replay_verified=False,reason='teacher did not reach released stable prefix')
                        manifest['prepared_starts'].append(prepared)
                    split_audit(manifest['rows'])
                    train=[s for s in manifest['sections'] if s['split']=='train']
                    norm=float(np.mean([s['raw_weight'] for s in train])) if train else None
                    manifest['train_only_normalizer']=norm
                    for s in manifest['sections']:s['weight']=s['raw_weight']/norm if norm else None
                    dump(output/'manifest.json',manifest)
                    dump(output/'prepared_starts.json',dict(rows=manifest['prepared_starts']))
                    dump(output/'status.json',dict(state='COLLECTING',count=count,seed=seed,
                        episodes=len(manifest['rows']),sections=len(manifest['sections']),elapsed_seconds=time.time()-start))
            finally:env.close()
        expected={(count,base+i) for count,base in ((3,510000),(4,511000)) for i in allowed}
        assert seen<=expected,'collected outside frozen cohort'
        manifest['complete']=seen==expected
        manifest['expected_episodes']=len(expected)
        manifest['preparation_state']='PROBE_COMPLETE' if probe else 'COLLECTION_COMPLETE'
    except Exception as exc:
        manifest['preparation_state']='STOPPED_WITH_PARTIAL_DATA';manifest['error']=repr(exc)
        dump(output/'manifest.json',manifest);raise
    finally:
        finished=time.time()
        manifest['preparation_start_epoch']=origin
        manifest['preparation_finished_epoch']=finished
        manifest['elapsed_invocation_seconds']=finished-start
        manifest['elapsed_seconds']=manifest['elapsed_invocation_seconds']
        manifest['total_preparation_elapsed_seconds']=finished-origin
        dump(output/'manifest.json',manifest)
    dump(output/'status.json',dict(state=manifest['preparation_state'],episodes=len(manifest['rows']),sections=len(manifest['sections']),elapsed_seconds=manifest['elapsed_seconds']))
    return manifest

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--collect',action='store_true')
    parser.add_argument('--probe',action='store_true');parser.add_argument('--resume',action='store_true')
    parser.add_argument('--output',type=Path);parser.add_argument('--plan',type=Path,default=HERE/'training_plan.json')
    args=parser.parse_args()
    if not args.collect:print('DRY_RUN: native data preparation only; no optimizer updates');return
    assert args.output;run(args.output,args.plan,args.probe,args.resume)

if __name__=='__main__':main()
