"""Diffusion Policy comparisons on existing, immutable train/valid splits."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'experiments/baselines/square/scripts'))
import runtime
import h5py
import numpy as np
from robomimic.config import config_factory
EXP=ROOT/'experiments/baselines/diffusion_20261001'
EXP.mkdir(exist_ok=True)
base=json.loads((ROOT/'experiments/baselines/workday_20261001/stack_two_vision_short/config.json').read_text())
square=json.loads((ROOT/'experiments/baselines/square/bc_rnn/config.json').read_text())
jobs=[]; datasets={}
for name,state,is_square in [('stack_two_diffusion_vision',False,False),
                              ('stack_two_diffusion_state',True,False),
                              ('square_diffusion_vision',False,True)]:
    source=square if is_square else base
    cfg=json.loads(config_factory('diffusion_policy').dump())
    cfg['experiment']=source['experiment'].copy()
    cfg['experiment']['name']=name
    cfg['experiment']['save']=dict(source['experiment']['save'],every_n_epochs=100,
        on_best_validation=False,on_best_rollout_success_rate=False)
    cfg['experiment']['rollout']=dict(source['experiment']['rollout'],enabled=False)
    cfg['train']=dict(source['train'],num_epochs=300,batch_size=8,seq_length=16,frame_stack=2,
        output_dir=str(EXP/name/'runs'))
    cfg['observation']=json.loads(json.dumps(source['observation']))
    if state:
        cfg['observation']['modalities']['obs']['rgb']=[]
        cfg['observation']['modalities']['obs']['low_dim'].append('object')
    cfg['algo']['ddpm']['enabled']=False
    cfg['algo']['ddim']['enabled']=True
    cfg['algo']['ddim']['num_inference_timesteps']=10
    cfg['algo']['horizon'].update(observation_horizon=2,action_horizon=8,prediction_horizon=16)
    folder=EXP/name; folder.mkdir(exist_ok=True)
    path=folder/'config.json'; path.write_text(json.dumps(cfg,indent=2))
    config_factory('diffusion_policy',dic=cfg).lock()
    dataset=cfg['train']['data'][0]['path']
    if dataset not in datasets:
        with h5py.File(dataset,'r') as f:
            train=set(f['mask/train'][:]); valid=set(f['mask/valid'][:])
            assert train and valid and not train&valid
            lower=np.full(7,np.inf); upper=np.full(7,-np.inf)
            for demo in f['data'].values():
                actions=demo['actions'][:]
                assert actions.shape[1]==7 and np.isfinite(actions).all()
                lower=np.minimum(lower,actions.min(axis=0)); upper=np.maximum(upper,actions.max(axis=0))
            assert (lower>=-1).all() and (upper<=1).all(), (lower,upper)
            datasets[dataset]=dict(train=len(train),valid=len(valid),demos=len(f['data']),
                action_min=lower.tolist(),action_max=upper.tolist())
    jobs.append(dict(name=name,config=str(path),horizon=400 if is_square else 500,
        task='Square' if is_square else 'StackTwo',oracle=state,epochs=300))
status=json.loads((ROOT/'experiments/baselines/workday_20261001/status.json').read_text())
gmm=next(r['checkpoint'] for r in status['results'] if r['name']=='square_rnn_gmm' and r['split']=='test')
manifest=dict(jobs=jobs,datasets=datasets,repair_checkpoint=gmm,deadline_hours=6.5,
    selection_episodes=15,test_episodes=50,robustness_episodes=10)
(EXP/'manifest.json').write_text(json.dumps(manifest,indent=2))
print('CONFIGS_READY',json.dumps(manifest),flush=True)
