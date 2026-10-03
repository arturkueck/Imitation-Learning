"""Artifact identity, validation-panel alignment, and frozen inference-only protocol."""
import argparse,platform
import h5py,torch,diffusers
from common import *
from transport_data import DATA

p=argparse.ArgumentParser();p.add_argument('--final',action='store_true');args=p.parse_args()
prior=json.loads((OUT.parent/'verification.json').read_text());records=[]
for r in prior['records']:
    actual=digest(r['checkpoint']);assert actual==r['checkpoint_sha256'];records.append(dict(model=r['model_class'],seed=r['training_seed'],checkpoint=r['checkpoint'],sha256=actual))
dh=digest(DATA);assert dh==PROTOCOL['data_sha256']
with h5py.File(DATA,'r') as f:
    valid={v.decode() for v in f['mask/valid'][:]}
    for i,r in enumerate(META):
        assert r['demo'] in valid;d=f['data'][r['demo']];t=r['step'];ids=[max(0,t-1),t]
        for k in KEYS:assert np.array_equal(PANEL[k][i],d['obs/'+k][ids])
        expected=d['actions'][np.clip(np.arange(t-1,t+15),0,len(d['actions'])-1)]
        assert np.array_equal(PANEL['expected'][i],expected)
noise=np.load(OUT/'noise64.npy');assert noise.shape==(420,64,16,7)
settings=dict(no_training=True,no_optimizer_updates=True,ema_weights=True,no_action_postprocessing=True,no_observation_changes=True,executed_chunk_slice='indices [1:1+h], h in 1,2,4; index0 is past action',ddim_steps=[5,10,20,50],ddim_eta=0,ddim_train_steps=100,all_offline_conditions_draws=64,paired_same_initial_noise_all_ddim_steps_and_training_seeds=True,panel_observations_verified=420,expert_action_alignment_verified=420*16,validation_demos=20,offsets=[-10,10],transport_subset=[6,10],random_seed_new_noise=20261001,first8_noise='existing common_noise.npz',fixed_starts=PROTOCOL['fixed_start_seeds'],fixed_start_hashes=PROTOCOL['fixed_start_hashes'],rollout_horizon=500,stability_tail=40,control_hz=20,xyz_units='dimensionless normalized controller commands, not metres',strong_action_thresholds=dict(xy_gt=.25,goal_cosine_gt=.5),native_cuda_matmul_tf32=False,native_cudnn_tf32=True,native_cudnn_benchmark=True,kernel_caches='all rollout horizons within a common process; historical replay gaps recorded',weights=records,data_sha256=dh,panel_sha256=digest(PRIOR/'panel.npz'),noise64_sha256=digest(OUT/'noise64.npy'),versions=dict(python=platform.python_version(),torch=torch.__version__,diffusers=diffusers.__version__,cuda=torch.version.cuda,cudnn=torch.backends.cudnn.version(),gpu=torch.cuda.get_device_name()))
if args.final:
    initial=json.loads((OUT/'protocol.json').read_text());assert initial['weights']==settings['weights'];assert initial['data_sha256']==dh
    dump('final_input_verification.json',dict(checkpoints_unchanged=6,data_unchanged=True,validation_observations_verified=420,expert_chunk_positions_verified=6720,noise_identity_unchanged=initial['noise64_sha256']==settings['noise64_sha256'],weights=records))
else:dump('protocol.json',settings)
print('Input hashes and all 420×16 expert action targets verified.',flush=True)
