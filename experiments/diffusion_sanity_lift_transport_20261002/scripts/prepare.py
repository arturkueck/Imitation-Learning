"""Prepare one prefix-only diagnostic; never launch or train here."""
import json,sys,shutil,hashlib
from pathlib import Path
import numpy as np,h5py
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parents[1]
OLD=ROOT/'experiments/stack_normalization_20261001'
sys.path.insert(0,str(ROOT/'experiments/stack_followup_20261001/scripts'))
from transport_data import demos,DATA,KEYS
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(1048576),b''):h.update(b)
    return h.hexdigest()
def write(p,x):p.write_text(json.dumps(x,indent=2,allow_nan=False),encoding='utf-8')

def main():
    assert not (OUT/'preflight.json').exists() and not (OUT/'worker_started.json').exists(),'Experiment already sealed or started'
    dest=OUT/'C/diffusion/seed_1';dest.mkdir(parents=True,exist_ok=True)
    rows=demos();cuts=[]
    with h5py.File(DATA,'r') as src,h5py.File(OUT/'early_demonstrations.hdf5','w') as dst:
        for k,v in src.attrs.items():dst.attrs[k]=v
        src.copy('mask',dst)
        group=dst.create_group('data')
        for k,v in src['data'].attrs.items():group.attrs[k]=v
        for d in rows:
            start=int(np.flatnonzero(d['phase']==4)[0]);o=d['obs']['object']
            ref=o[start,3:5];goal=o[start,:2]-ref;length=float(np.linalg.norm(goal));assert length>.03
            unit=goal/length;progress=(o[:,3:5]-ref)@unit
            ids=np.flatnonzero((np.arange(len(o))>=start)&(d['phase']==4)&(progress>=.03))
            assert len(ids),f'No 3 cm early transport prefix: {d["name"]}'
            stop=int(ids[0])+1;original=src['data'][d['name']];target=group.create_group(d['name'])
            for k,v in original.attrs.items():target.attrs[k]=v
            target.attrs['num_samples']=stop
            for k in ('actions','rewards','dones','states'):
                if k in original:target.create_dataset(k,data=original[k][:stop],compression='gzip')
            ob=target.create_group('obs')
            for k in KEYS:
                a=original['obs'][k][:stop];ob.create_dataset(k,data=a,compression='gzip')
                assert np.array_equal(a,d['obs'][k][:stop])
            assert np.array_equal(target['actions'][:],d['actions'][:stop])
            cuts.append(dict(demo=d['name'],split=d['split'],original_frames=len(o),retained_frames=stop,transport_onset=start,retained_progress_m=float(progress[stop-1]),max_retained_phase=int(d['phase'][:stop].max())))
        group.attrs['total']=sum(x['retained_frames'] for x in cuts)
    assert sum(d['split']=='train' for d in cuts)==180 and sum(d['split']=='valid' for d in cuts)==20
    assert all(d['max_retained_phase']==4 for d in cuts)
    write(OUT/'prefix_manifest.json',cuts)
    shutil.copy2(OLD/'normalization_stats.json',OUT/'normalization_stats.json')
    config=json.loads((OLD/'C/diffusion/seed_1/config.json').read_text())
    config['train']['data'][0]['path']=str(OUT/'early_demonstrations.hdf5')
    config['train']['output_dir']=str(dest/'runs');config['experiment']['name']='diffusion_sanity_lift_transport_seed_1'
    write(dest/'config.json',config);write(OUT/'config.json',config)
    source=OUT/'source_snapshot';source.mkdir(exist_ok=True)
    for name in ('common.py','train.py','evaluate.py','offline.py','analyze.py'):
        shutil.copy2(OLD/'scripts'/name,source/name)
    common=(source/'common.py').read_text()
    common=common.replace("OUT = ROOT / 'experiments/stack_normalization_20261001'", "OUT = ROOT / 'experiments/diffusion_sanity_lift_transport_20261002'\nDATA = OUT / 'early_demonstrations.hdf5'")
    (OUT/'scripts/common.py').write_text(common,encoding='utf-8')
    train=(source/'train.py').read_text()
    begin=train.index('    def get_obs(self):');end=train.index('    DU.SequenceDataset.normalize_obs=get_obs',begin)
    train=train[:begin]+"    def get_obs(self):\n        # Preserve EXACT original C statistics, not refitted prefix statistics.\n        return n.obs\n"+train[end:]
    needle="            model_ref.append(model)"
    train=train.replace(needle,needle+"\n            assert weight_digest(model.nets)==read(ROOT/'experiments/stack_normalization_20261001/C/diffusion/seed_1/initialization.json')['initial_weights_sha256'], 'Fresh initialization differs from original C seed 1'")
    train=train.replace('train_stats_match_native=True','frozen_original_C_stats=True')
    (OUT/'scripts/train.py').write_text(train,encoding='utf-8')
    for name in ('offline.py','analyze.py'):shutil.copy2(source/name,OUT/'scripts'/name)
    ev=(source/'evaluate.py').read_text()
    ev=ev.replace('from dynamics_common import extra_metrics','from dynamics_common import extra_metrics\nfrom sanity_metrics import metrics')
    ev=ev.replace('for step in range(540):','for step in range(500):')
    begin=ev.index('                if measured is None and (ok or done or step==499):')
    end=ev.index('            t=np.array(trace);',begin)
    ev=ev[:begin]+"                early=metrics(np.array(trace))\n                if early['simplified_success'] or done or step==499:\n                    measured=step+1;success=early['simplified_success'];break\n"+ev[end:]
    ev=ev.replace('sustained_success=bool(success and np.all(t[measured:,36]>0))','sustained_success=False,**metrics(t)')
    ev=ev.replace("stable_stacks=sum(x['sustained_success'] for x in results)","simplified_successes=sum(x['simplified_success'] for x in results)")
    (OUT/'scripts/evaluate.py').write_text(ev,encoding='utf-8')
    baseline=json.loads((OLD/'protocol.json').read_text())['baseline_protocol']
    protocol=dict(seed=1,gradient_updates=30000,baseline_protocol=baseline,data_change='Each unchanged demonstration prefix ends at first >=3 cm projected transport within expert phase 4. Original train/valid split retained. No rebalancing.',normalization='Exact frozen observation statistics from original C; no action normalization; not refitted to prefixes.',task='grasp, lift, short target-directed transport; no positioning/lowering/release/stack requirement',evaluation_horizon=500,terminate_on_simplified_success=True,success_definition='Held object lifted >0.88 m for 3 consecutive frames, then transport start: held, B-z>0.98 m, XY speed>0.02 m/s and motion goal-cosine>0.5 for 3 frames. From preceding position of transport onset: >=0.02 m projected progress toward fixed initial target, held and B-z>0.98 m throughout, >=3 moving frames (speed>0.005 m/s), >=80% of moving frames have current-target motion cosine>0.5.',offline_xy_expert='Same saved original 20-demo validation panel and fixed diffusion noise; median action XY/Expert and mean target cosine at offsets +6..+10. Diagnostic may extend beyond cropped training prefixes. Online actual motion direction reported separately.',action_execution='unchanged positions 1:3, two actions per replanning, 16x7 chunks, history 2',single_run_only=True,no_replication=True,no_additional_experiments=True)
    write(OUT/'protocol.json',protocol)
    originals=[DATA,OLD/'C/diffusion/seed_1/config.json',OLD/'normalization_stats.json',OLD/'C/diffusion/seed_1/initialization.json']
    shared=ROOT/'experiments/stack_followup_20261001/scripts'
    originals += [shared/n for n in ('direct_common.py','transport_data.py','balance_common.py','dynamics_common.py','replication_common.py')]
    originals += [ROOT/'experiments/square/scripts'/n for n in ('runtime.py','scheduler_fix.py','robustness.py','video_views.py')]
    originals += list((OLD/'source_snapshot/praxis').rglob('*.py'))
    records={}
    for i,p in enumerate(originals):
        if p==DATA:continue
        # Flatten archival names to avoid Windows path-length failures.
        target=source/'dependencies'/(str(i)+'_'+p.name);target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        records[str(p.relative_to(ROOT))]=sha(p)
    write(OUT/'provenance.json',dict(original_dataset=dict(path=str(DATA),sha256=sha(DATA)),prefix_dataset_sha256=sha(OUT/'early_demonstrations.hdf5'),source_config_sha256=sha(OLD/'C/diffusion/seed_1/config.json'),config_sha256=sha(OUT/'config.json'),original_source_hashes=records))
    print(json.dumps(dict(train_demos=180,valid_demos=20,frames=sum(d['retained_frames'] for d in cuts),max_phase=4,prepared=True)))
if __name__=='__main__':main()
