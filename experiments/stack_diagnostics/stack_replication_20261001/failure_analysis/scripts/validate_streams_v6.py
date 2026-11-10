"""Validate four independent graph streams against four complete native episodes."""
import sys,gc,json,faulthandler
import numpy as np
import rollout,batch_rollout
from common import OUT

faulthandler.enable();faulthandler.dump_traceback_later(300,repeat=True)
sys.argv=['rollout.py','diffusion','1','--starts','4','--native','--group','sequential_reference_v6']
batch_rollout.shared_reference=rollout.main()
sys.argv=['batch_rollout.py','1','--starts','4','--workers','4','--group','stream_validation_v6']
batch_rollout.main();gc.collect()
records=[]
for seed in range(46000,46004):
    a=np.load(OUT/f'rollouts/diffusion_seed1_h2_ddim10_sequential_reference_v6/{seed}.npz')['trace']
    b=np.load(OUT/f'rollouts/diffusion_seed1_h2_ddim10_stream_validation_v6/{seed}.npz')['trace']
    assert a.shape==b.shape
    error=float(abs(a-b).max());assert error==0,(seed,error)
    records.append(dict(start_seed=seed,frames=len(a),max_abs_trace_error=error,all_states_actions_grasp_contact_success_equal=True))
(OUT/'stream_episode_parity_v6.json').write_text(json.dumps(records,indent=2))
print('Four streams, whole native episodes bitwise equal:',records,flush=True)
faulthandler.cancel_dump_traceback_later()
