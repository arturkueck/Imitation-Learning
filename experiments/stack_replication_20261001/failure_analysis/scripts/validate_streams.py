"""Whole-episode parity with unmodified native RolloutPolicy, in a shared process."""
import sys,gc,json
import numpy as np
import rollout,batch_rollout
from common import OUT

sys.argv=['rollout.py','diffusion','1','--starts','2','--native','--group','sequential_reference_v5'];batch_rollout.shared_reference=rollout.main()
sys.argv=['batch_rollout.py','1','--starts','2','--workers','1','--group','stream_validation_v5'];batch_rollout.main();gc.collect()
records=[]
for seed in (46000,46001):
    a=np.load(OUT/f'rollouts/diffusion_seed1_h2_ddim10_sequential_reference_v5/{seed}.npz')['trace'];b=np.load(OUT/f'rollouts/diffusion_seed1_h2_ddim10_stream_validation_v5/{seed}.npz')['trace'];assert a.shape==b.shape;error=float(abs(a-b).max());assert error==0,(seed,error);records.append(dict(start_seed=seed,frames=len(a),max_abs_trace_error=error,all_states_actions_grasp_contact_success_equal=True))
(OUT/'stream_episode_parity.json').write_text(json.dumps(records,indent=2));print('Whole native episodes bitwise equal:',records,flush=True)
(OUT/'stream_episode_parity_v5.json').write_text(json.dumps(records,indent=2))
