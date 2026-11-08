"""Bounded current-controller data collection and family-held-out scorer check."""
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import sys
import time
import traceback
import numpy as np
import torch
import quality_scorer_check as q
from stability import run

HERE=Path(__file__).resolve().parent
_atomic_write=q.write


def resilient_write(path,value):
    # Windows readers/antivirus may briefly deny replace while sharing a file.
    for attempt in range(20):
        try:return _atomic_write(path,value)
        except PermissionError:
            if attempt==19:raise
            time.sleep(.1)


q.write=resilient_write


def jobs(rows,smoke=False):
    old=[r for r in rows if r['split']=='train']
    if smoke:
        return [('train',r['seed'],r['teacher']['seed'],r) for r in old[:2]]
    assert len(old)==120
    return ([('train',r['seed'],r['teacher']['seed'],r) for r in old]
        + [('train',2026115000+i,1+i%3,None) for i in range(120)]
        + [('valid',2026116000+i,1+i%3,None) for i in range(200)])


def parity(a,row):
    assert q.sha(row['path'])==row['sha256']
    assert hashlib.sha256(a['initial'].tobytes()).hexdigest()==row['initial_sha256']
    with np.load(row['path'],allow_pickle=False) as saved:
        assert len(saved['x'])==len(a['x'])
        for new,old in [('x','x'),('p','phase')]:
            assert np.array_equal(a[new].astype(saved[old].dtype),saved[old]),old
        assert np.array_equal(a['a'][:,[0,1,2,6]].astype('float32'),saved['action'])
        dim=saved['state'].shape[1]-37
        for new,old in [('pre_state','state'),('post_state','next_state')]:
            assert np.array_equal(a[new].astype('float32'),saved[old][:,:dim]),new
        assert np.array_equal(a['pre_obs'].astype('float32'),saved['state'][:,-37:-19])
        assert np.array_equal(a['post_obs'].astype('float32'),saved['next_state'][:,-37:-19])


def main(out,smoke=False,recover=None):
    assert not out.exists(),'Never overwrite a run'
    source=HERE/'night_001/data/manifest.json';manifest=q.read(source)
    historical=q.read(HERE/'scorer_check_001/dataset_audit.json')
    forbidden={r['family'] for r in historical['inventory']}
    forbidden.update(r['initial_sha256'] for r in manifest['rows'] if r['split']=='valid')
    scheduled=jobs(manifest['rows'],smoke)
    parents=[run.parent(s) for s in (1,2,3)]
    files=[Path(__file__).resolve(),Path(q.__file__),Path(run.__file__),Path(run.controller.__file__),
           Path(run.native.__file__),Path(run.native.historical.__file__),
           Path(sys.modules['method'].__file__),Path(run.native.historical.old.__file__),source,
           HERE/'scorer_check_001/dataset_audit.json']
    inputs={str(p):q.sha(p) for p in files}
    inputs.update({p['path']:p['sha256'] for p in parents})
    inputs.update({r['path']:r['sha256'] for _,_,_,r in scheduled if r})
    assert q.sha(run.controller.__file__)==manifest['controller_sha256']
    recovered=[];prior=None
    if recover:
        prior=q.read(recover/'protocol.json')
        assert q.read(recover/'status.json')['state']=='ERROR'
        assert not prior.get('infrastructure_recovery'),'Only one recovery permitted'
        for path,h in prior['input_hashes'].items():
            if Path(path).resolve()!=Path(__file__).resolve():assert q.sha(path)==h,path
        recovered=q.read(recover/'episodes.json')
        assert len(recovered)<len(scheduled)
        for row,(split,seed,parent,_) in zip(recovered,scheduled):
            assert (row['split'],row['seed'],row['parent'])==(split,seed,parent)
            assert q.sha(row['path'])==row['sha256']
            inputs[row['path']]=row['sha256']
        inputs[str(recover/'protocol.json')]=q.sha(recover/'protocol.json')
        inputs[str(recover/'episodes.json')]=q.sha(recover/'episodes.json')
    plan=q.settings();plan.update(schema='guarded-section-quality-v1',
        scope='Current frozen guarded controller; stage2 approach; measured50-frame continuation; development check, no actor benefit claim',
        wall_clock_cap_seconds=1800,new_simulator_rollouts=320 if not smoke else 0,
        collection_cap_seconds=1800,collection_schedule=[dict(split=s,seed=z,parent=p,reconstruction=r is not None) for s,z,p,r in scheduled],
        stopping='Fixed attempts; no adaptive class enrichment, retries or threshold changes',
        old_validation_excluded=True,actor_training_ready=False,technical_only=smoke,
        input_hashes=inputs,prepared_unix=time.time(),parents=parents)
    if prior:
        assert plan['collection_schedule']==prior['collection_schedule']
        plan.update(infrastructure_recovery=dict(source=str(recover),preserved_episodes=len(recovered),
            reason='Transient Windows sharing violation on atomic status replacement',
            repair='Bounded20x100ms retries for PermissionError only; no scientific change',
            original_deadline_unix=prior['prepared_unix']+prior['collection_cap_seconds'],
            original_script_sha256=prior['input_hashes'][str(Path(__file__).resolve())]))
    out.mkdir();q.write(out/'protocol.json',plan)
    snap=out/'source_snapshot';snap.mkdir()
    for i,p in enumerate(files):shutil.copy2(p,snap/f'{i:02d}_{p.name}')
    torch.set_num_threads(4);torch.use_deterministic_algorithms(True)
    torch.backends.cuda.matmul.allow_tf32=False;torch.backends.cudnn.allow_tf32=False
    models={p['seed']:run.native.historical.load(p['path']).eval().requires_grad_(False) for p in parents}
    deadline=(prior['prepared_unix']+prior['collection_cap_seconds'] if prior else time.time()+plan['collection_cap_seconds'])
    records=[];inventory=list(recovered);seen={}
    for row in recovered:
        with np.load(row['path'],allow_pickle=False) as f:a={k:f[k] for k in f.files}
        family=hashlib.sha256(a['initial'].tobytes()).hexdigest()
        assert family==row['initial_sha256'] and family not in forbidden and family not in seen
        seen[family]=row['split'];selected,info=q.extract(a,plan)
        assert info['sampled']==row['sampled']
        for v in selected:records.append(dict(**v,family=family,split=row['split'],source=row['path']))
    env=run.native.historical.make_env(3)
    try:
        (out/'model.xml').write_text(env.model.get_xml(),encoding='utf-8')
        for index,(split,seed,parent,row) in enumerate(scheduled):
            if index<len(recovered):continue
            run.stop(out,deadline)
            q.write(out/'status.json',dict(state='COLLECTING',completed=index,total=len(scheduled),split=split,seed=seed,pid=os.getpid(),updated_unix=time.time()))
            a,r=run.controller.collect(env,models[parent],seed,'guarded',out,deadline)
            family=r['initial_sha256'];assert family not in forbidden
            assert family not in seen,'Duplicate start family'
            seen[family]=split
            if row:
                parity(a,row);assert r['success']==row['success']
            folder=out/'traces'/split;folder.mkdir(parents=True,exist_ok=True)
            path=folder/f'{seed}.npz';np.savez_compressed(path,**a)
            selected,info=q.extract(a,plan)
            inventory.append(dict(**r,**info,split=split,parent=parent,path=str(path),sha256=q.sha(path),reconstruction_verified=row is not None))
            for v in selected:records.append(dict(**v,family=family,split=split,source=str(path)))
            q.write(out/'episodes.json',inventory)
    finally:env.close()
    assert all(q.sha(p)==h for p,h in inputs.items()),'Inputs changed'
    if smoke:
        q.write(out/'verification.json',dict(passed=True,reconstructions=len(inventory),full_state_action_observation_parity=True,actor_updates=0))
        q.write(out/'status.json',dict(state='COMPLETED',technical_only=True,updated_unix=time.time()))
        return
    data={};counts={}
    for split in ('train','valid'):
        selected=[r for r in records if r['split']==split]
        if not selected:continue
        d={k:np.asarray([r[k] for r in selected]) for k in ('x','y','family','frame','source','distance')}
        assert np.isfinite(d['x']).all();data[split]=d
        counts[split]=dict(examples=len(d['y']),families=len(np.unique(d['family'])),
            positive_families=len(np.unique(d['family'][d['y']==1])),negative_families=len(np.unique(d['family'][d['y']==0])),safe_examples=int(d['y'].sum()))
    q.write(out/'dataset_audit.json',dict(counts=counts,inventory=inventory,feature_dimensions=records[0]['x'].size if records else 0,
        endtest_files_read=0,label_input_separation='Unchanged features and50-frame labels',initial_families_disjoint=True))
    np.savez_compressed(out/'dataset.npz',**{f'{s}_{k}':v for s,d in data.items() for k,v in d.items()})
    support=(len(data)==2 and counts['train']['families']>=40 and counts['valid']['families']>=20
             and all(min(c['positive_families'],c['negative_families'])>=10 for c in counts.values()))
    q.write(out/'collection_verification.json',dict(input_hashes_unchanged=True,reconstructed_training_families=120,
        fresh_training_families=120,fresh_validation_families=200,family_disjoint=True,actor_updates=0,actor_weights_unchanged=True))
    if support:
        q.evaluate(out,plan,data,counts,inputs)
    else:
        q.write(out/'results.json',dict(class_support_sufficient=False,counts=counts,scorer_updates=0,actor_updates=0,actor_training_ready=False))
        q.write(out/'status.json',dict(state='COMPLETED',class_support_sufficient=False,updated_unix=time.time()))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--smoke',action='store_true')
    p.add_argument('--recover-from',type=Path);a=p.parse_args()
    try:main(a.output.resolve(),a.smoke,a.recover_from.resolve() if a.recover_from else None)
    except Exception:
        if a.output.exists():q.write(a.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),pid=os.getpid(),updated_unix=time.time()))
        raise
