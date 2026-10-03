"""Artifact completeness, native parity, equal latent pairs, immutable source files."""
import json,numpy as np
from switch_data import OUT
from balance_common import EXP as PREVIOUS,SOURCE,digest,DATA
p=json.loads((OUT/'protocol.json').read_text());assert digest(DATA)==p['dataset_sha256'];old=json.loads((PREVIOUS/'protocol.json').read_text());assert digest(SOURCE['checkpoint'])==old['source_sha256'];checks=0
for v in ('source','uniform','balanced'):
    if v!='source':assert digest(p['checkpoints'][v])==json.loads((PREVIOUS/v/'training_audit.json').read_text())['final_checkpoint_sha256']
    assert json.loads((OUT/v/'verification.json').read_text())['native_ddim_max_error']==0
    assert json.loads((OUT/v/'paired_verification.json').read_text())['native_ddim_max_error']==0
    for name in p['configs']:
        z=np.load(OUT/v/(name+'.npz'));assert z['chunks'].shape==(4320,16,7);assert np.isfinite(z['chunks']).all();assert len(z['paths'])==32;assert z['paths'].shape[1]==len(z['timesteps']);checks+=1
    for name in ('paired_ddim10','paired_ddim100'):
        z=np.load(OUT/v/(name+'.npz'));assert z['chunks'].shape==(1280,16,7);assert np.isfinite(z['chunks']).all();checks+=1
    z=np.load(OUT/v/'forward_denoiser.npz');assert np.isfinite(z['decoded']).all()
z=np.load(OUT/'paired_noise.npz');noise=z['noise'];assert np.array_equal(noise[::2],noise[1::2])
out=dict(all_checks_passed=True,sampler_prediction_files=checks,full_chunks_saved=98400,models_unchanged=True,dataset_unchanged=True,native_ddim_error_all_models=0,paired_noise_bit_identical=True,shared_old_observations_verified=p['shared_saved_observations_verified'],training=False,architecture_changes=False)
(OUT/'verification.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
