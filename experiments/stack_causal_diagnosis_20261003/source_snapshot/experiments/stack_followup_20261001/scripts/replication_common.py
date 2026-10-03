"""Frozen replication protocol. Existing seed1 is an independent full training run."""
import json,hashlib
import torch
from direct_common import ROOT,SOURCE,DATA
from balance_common import digest
OUT=ROOT/'experiments/stack_replication_20261001';OUT.mkdir(exist_ok=True)
OLD=ROOT/'experiments/stack_direct_20261001'
def folder(kind,seed):return OUT/kind/f'seed_{seed}'
def checkpoint(kind,seed):
    if seed==1:return SOURCE['checkpoint'] if kind=='diffusion' else str(OLD/'model_final.pth')
    f=folder(kind,seed)
    if kind=='direct':return str(f/'model_final.pth')
    paths=list((f/'runs').glob('**/models/model_epoch_300.pth'));assert len(paths)==1,paths;return str(paths[0])
def rollouts(kind,seed):return OLD/kind/'rollouts' if seed==1 else folder(kind,seed)/'rollouts'
def weight_digest(model):
    h=hashlib.sha256()
    for name,t in model.state_dict().items():h.update(name.encode());h.update(t.detach().cpu().numpy().tobytes())
    return h.hexdigest()
def prepare():
    assert not (OUT/'protocol.json').exists();config=json.loads((ROOT/'experiments/stack_followup_20261001/state_scheduler_fixed/config.json').read_text())
    for seed in (2,3):
        for kind in ('direct','diffusion'):folder(kind,seed).mkdir(parents=True,exist_ok=True)
        c=json.loads(json.dumps(config));c['train']['seed']=seed;c['train']['output_dir']=str(folder('diffusion',seed)/'runs');c['experiment']['name']=f'stack_diffusion_replication_seed_{seed}';(folder('diffusion',seed)/'config.json').write_text(json.dumps(c,indent=2))
    p=dict(training_seeds=[1,2,3],model_classes=['diffusion','direct'],gradient_updates_each=30000,batch_size=8,training_examples_each=240000,training_frames=27322,train_demos=180,valid_demos=20,history_frames=2,chunk_length=16,executed_action_slice=[1,3],sampling='unchanged within model; uniform with replacement; original Diffusion DataLoader and original direct numpy Generator',data_sha256=digest(DATA),seed1_reused=True,seed1_checkpoints={k:checkpoint(k,1) for k in ('diffusion','direct')},fixed_start_seeds=list(range(46000,46040)),fixed_start_hashes={str(r['seed']):r['initial_state_sha256'] for r in json.loads((OLD/'diffusion/rollouts/results.json').read_text())},offline_panel='same saved 20 validation demos, offsets -10..10; original common and paired diffusion noise',replication_unit='training seed; 40 starts nested within each training replicate',no_dynamics_features=True,no_phase_balancing=True,no_xy_heuristics=True,black_image_demos_unchanged=62,why_three_seeds='one CUDA GPU, approximately 26 GB initial free disk; two new full trainings and 80 rollouts per family; actual costs recorded',no_checkpoint_selection=True)
    (OUT/'protocol.json').write_text(json.dumps(p,indent=2))
if __name__=='__main__':prepare()
