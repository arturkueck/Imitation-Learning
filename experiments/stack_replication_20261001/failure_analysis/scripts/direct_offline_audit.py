"""Verify every reused Direct chunk against native batch-1 final EMA inference."""
import numpy as np,torch
from common import *
numerics();rows=[]
for seed in (1,2,3):
    ck=torch.load(checkpoint('direct',seed),map_location='cpu',weights_only=False)
    model=DirectChunk().cuda().eval();model.load_state_dict(ck['ema'])
    predictions=[]
    with torch.no_grad():
        for i in range(420):
            ob={k:PANEL[k][i] for k in KEYS}
            predictions.append(model(torch.tensor(flatten(ob),device='cuda'))[0].cpu().numpy())
    native=np.array(predictions);old=direct_chunks(seed);error=float(abs(native-old).max())
    assert native.shape==old.shape==(420,16,7) and error<1e-5, (seed,error)
    x,_,_=fields(native);y,_,_=fields(old)
    rows.append(dict(seed=seed,observations_verified=420,all_chunk_positions=16,checkpoint_sha256=digest(checkpoint('direct',seed)),native_batch_size=1,max_abs_all7_error=error,transport_first_xy_mean_delta=float((x[OFFSETS>=6,1]-y[OFFSETS>=6,1]).mean()),saved_predictions_agree_to_1e_minus5=True))
dump('direct_offline_parity.json',rows);print(json.dumps(rows,indent=2))
