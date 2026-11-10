"""Paired sensitivity to old vs new offline execution, not a pure batch-size intervention."""
import numpy as np
from common import *

rows=[]
for seed in (1,2,3):
    for steps in (5,10,20,50):
        old=existing_diffusion(seed,steps)
        if old is None:continue
        new=np.load(OUT/f'diffusion_seed{seed}_ddim{steps}.npz')['chunks'][:,:8]
        assert old.shape==new.shape and np.isfinite(old).all()
        x,_,c=fields(old);y,_,d=fields(new);m=OFFSETS>=6
        oldok=(x[m,:,1]>.25)&(c[m,:,1]>.5);newok=(y[m,:,1]>.25)&(d[m,:,1]>.5)
        rows.append(dict(seed=seed,steps=steps,paired_draws=8,transport_observations=100,
            max_abs_all_chunk_error=float(abs(new-old).max()),
            transport_first_xy_paired_mean_delta=float((y[m,:,1]-x[m,:,1]).mean()),
            transport_first_xy_mean_absolute_sample_delta=float(abs(y[m,:,1]-x[m,:,1]).mean()),
            transport_first_cosine_paired_mean_delta=float((d[m,:,1]-c[m,:,1]).mean()),
            strong_targeted_probability_delta=float(newok.mean()-oldok.mean()),
            strong_targeted_classification_flip_fraction=float((oldok!=newok).mean()),
            scope='same existing initial noises; old batch64 artifacts vs new batch128 execution; backend and execution details not independently isolated'))
dump('offline_batch_sensitivity.json',rows);csvwrite('offline_batch_sensitivity.csv',rows)
print(json.dumps(rows,indent=2))
