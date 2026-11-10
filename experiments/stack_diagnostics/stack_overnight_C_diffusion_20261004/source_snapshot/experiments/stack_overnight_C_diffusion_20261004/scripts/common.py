"""Frozen normalization-only factorial experiment; original models and metrics."""
import sys, json, hashlib, copy
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parents[3]
SHARED = ROOT / 'experiments/stack_followup_20261001/scripts'
sys.path.insert(0, str(SHARED))
import direct_common
from direct_common import DirectChunk, flatten, ORDER
from transport_data import DATA, KEYS, demos
from balance_common import digest, SOURCE
OUT = ROOT / 'experiments/stack_normalization_20261001'
VARIANTS = {'B': (False, True), 'C': (True, False), 'D': (True, True)}
def read(path): return json.loads(Path(path).read_text(encoding='utf-8'))
def write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + '.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8'); temp.replace(path)
def folder(variant, kind, seed): return OUT / variant / kind / f'seed_{seed}'
def checkpoint(variant, kind, seed):
    dest = folder(variant, kind, seed)
    if kind == 'direct': return dest / 'model_final.pth'
    files = list((dest/'runs').glob('**/models/model_epoch_300.pth'))
    assert len(files) == 1, files
    return files[0]
def stats_arrays(stats):
    return {k: {s: np.asarray(v, dtype=np.float32) for s,v in d.items()} for k,d in stats.items()}
class Normalizer:
    def __init__(self, variant):
        self.variant = variant; self.obs_enabled, self.action_enabled = VARIANTS[variant]
        s = read(OUT/'normalization_stats.json')
        self.obs = stats_arrays(s['observation']); self.action = stats_arrays(s['action'])['actions']
    def observations(self, ob):
        if not self.obs_enabled: return {k: np.asarray(v, dtype=np.float32) for k,v in ob.items()}
        return {k: (np.asarray(v,dtype=np.float32)-self.obs[k]['offset'])/self.obs[k]['scale'] for k,v in ob.items()}
    def actions(self, a):
        a = np.asarray(a,dtype=np.float32)
        return (a-self.action['offset'])/self.action['scale'] if self.action_enabled else a
    def inverse_actions(self, a):
        a = np.asarray(a,dtype=np.float32)
        return a*self.action['scale']+self.action['offset'] if self.action_enabled else a
    def check_actions(self, a):
        a = np.asarray(a)
        assert a.ndim>0 and a.shape[-1] == 7, f'Malformed actions, shape={a.shape}'
        bad=np.argwhere(~np.isfinite(a) | (np.abs(a)>1.00001))
        if len(bad):
            details=[dict(index=idx.tolist(),value=str(a[tuple(idx)])) for idx in bad[:8]]
            raise ValueError(f'Invalid controller actions for {self.variant}: {details}')
def prepare():
    import csv
    from robomimic.utils.dataset import action_stats_to_normalization_stats
    from replication_common import weight_digest
    assert not (OUT/'protocol.json').exists(), 'Refusing to overwrite frozen experiment'
    ds = demos(); train = [d for d in ds if d['split']=='train']; valid = [d for d in ds if d['split']=='valid']
    assert len(train)==180 and len(valid)==20
    records=[]; obs_stats={}; action_stats={}
    def channel_stats(a, group, key):
        a=np.asarray(a,dtype=np.float64)
        for j in range(a.shape[1]):
            records.append(dict(group=group,key=key,channel=j,n=len(a),min=float(a[:,j].min()),max=float(a[:,j].max()),mean=float(a[:,j].mean()),std=float(a[:,j].std())))
        return dict(min=a.min(0,keepdims=True),max=a.max(0,keepdims=True),mean=a.mean(0,keepdims=True),sqdiff=((a-a.mean(0))**2).sum(0,keepdims=True),n=len(a))
    for k in KEYS:
        a=np.concatenate([d['obs'][k] for d in train]); s=channel_stats(a,'observation',k)
        obs_stats[k]=dict(offset=s['mean'].astype(np.float32),scale=(a.astype(np.float64).std(0,keepdims=True)+1e-3).astype(np.float32))
    a=np.concatenate([d['actions'] for d in train]); s=channel_stats(a,'action','actions')
    action_stats=action_stats_to_normalization_stats({'actions':s},{'actions':{'normalization':'min_max'}})
    def lists(d): return {k:{j:v.tolist() for j,v in t.items()} for k,t in d.items()}
    write(OUT/'normalization_stats.json',dict(observation=lists(obs_stats),action=lists(action_stats),fit_split='train only',fit_frames=len(a),observation_method='(x-mean)/(population_std+0.001), native Robomimic formula',action_method='native Robomimic min_max to [-0.999999,+0.999999]; ranges<0.0001 use scale=1 and offset=min; no clipping',raw_channel_statistics=records))
    with (OUT/'channel_statistics.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(records[0]));w.writeheader();w.writerows(records)
    base=read(ROOT/'experiments/stack_replication_20261001/protocol.json');assert digest(DATA)==base['data_sha256']
    configs={}; tests=[]
    for v in VARIANTS:
        n=Normalizer(v); norm=n.actions(a); back=n.inverse_actions(norm)
        err=float(np.max(abs(a-back)));assert err<1e-6 and np.isfinite(norm).all() and abs(norm).max()<=1.000001
        oe={}
        for k in KEYS:
            raw=np.concatenate([d['obs'][k] for d in train]); z=n.observations({k:raw})[k]
            inv=z*n.obs[k]['scale']+n.obs[k]['offset'] if n.obs_enabled else z
            oe[k]=float(abs(inv-raw).max());assert oe[k]<1e-6
        tests.append(dict(variant=v,action_roundtrip_max_error=err,observation_roundtrip_max_error=oe,finite=True))
        for seed in (1,2,3):
            for kind in ('direct','diffusion'):
                dest=folder(v,kind,seed);dest.mkdir(parents=True,exist_ok=True)
                if kind=='direct':
                    c=read(ROOT/'experiments/stack_direct_20261001/config.json');c['seed']=seed
                    c['observation_normalization']=n.obs_enabled;c['action_normalization']='native min_max' if n.action_enabled else c['action_normalization']
                else:
                    c=read(ROOT/'experiments/stack_followup_20261001/state_scheduler_fixed/config.json');c['train']['seed']=seed;c['train']['output_dir']=str(dest/'runs');c['experiment']['name']=f'stack_normalization_{v}_diffusion_seed_{seed}'
                    c['train']['hdf5_normalize_obs']=n.obs_enabled;c['train']['action_config']['actions']['normalization']='min_max' if n.action_enabled else None
                write(dest/'config.json',c);configs[str(dest.relative_to(OUT)/'config.json')]=digest(dest/'config.json')
    write(OUT/'protocol.json',dict(baseline_protocol=base,baseline_not_retrained=True,variants={v:dict(observation=o,action=a) for v,(o,a) in VARIANTS.items()},normalization_stats_sha256=digest(OUT/'normalization_stats.json'),config_sha256=configs,gradient_updates=30000,seed1_all_variants=True,extension_rule='For each variant with >=8/40 stable diffusion stacks (20 percentage points above 0/40 baseline), train BOTH model classes additionally with seeds 2 and 3; no selection between qualifying variants',extension_threshold_stacks=8,checkpoints='final update 30000 only; no selection',sampling='unchanged historical trainer per model class; paired seeds across normalization cells',validation_normalization='same train-fit statistics as training and rollout',no_other_learning_changes=True))
    write(OUT/'preflight.json',dict(passed=True,roundtrips=tests,train_demos=180,valid_demos=20,train_frames=len(a),raw_channel_statistics=records))
    print(json.dumps(records,indent=2))
if __name__=='__main__': prepare()
