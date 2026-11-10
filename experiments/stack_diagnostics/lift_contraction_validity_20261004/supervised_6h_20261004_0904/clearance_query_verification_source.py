"""Independent nominal reconstructions and proximity re-query; no response actions."""
import importlib.util,json,sys,time,traceback,hashlib
from pathlib import Path
import numpy as np,h5py
O=Path(__file__).resolve().parent;D=O.parent;S=D.parent
sys.path.insert(0,str(D));import helpers as h
import preparation,clearance_defined_arrays as clearance
h.OUT=O
start=time.monotonic();result=dict(state='RUNNING',physics_integration_steps=0,response_probe_actions=0,policy_training_updates=0,rows=[]);env=None
try:
    original=h.read(D/'result.json');a=h.read(D/'filter_analysis.json');sel=h.read(D/'selection.json')
    assert original['state'] in ['COMPLETE_DATA','DOMAIN_GATE_FAILED'] and a['raw_sha256']==h.sha(D/'result.json')
    P=h.PILOT;spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
    import torch,mujoco
    torch.set_num_threads(2)
    from robomimic.utils.file_utils import env_from_checkpoint
    from robomimic.config import config_factory
    import robomimic.utils.obs_utils as ObsUtils
    ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False);cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg)
    env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False)
    with h5py.File(h.ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
        for row in original['rows']:
            h.stop_check();d=f['data/'+row['demo']];t=row['t'];np.random.seed(sel['seed']);torch.manual_seed(sel['seed'])
            env.reset_to({'model':d.attrs['model_file'],'states':d['states'][0]});ctrl=env.env.robots[0].composite_controller.part_controllers['right']
            info=preparation.prepare(env,ctrl,d,t,d['actions'][:],'H_reset',sel);assert info['geometry_passed']
            q=clearance.filter_anchor(env,ctrl,.015);previous=row['pre_response_filter']
            assert h.difference(q['anchor_before_query'],previous['anchor_before_query'])==0
            assert q['initial_robot_contacts']==previous['initial_robot_contacts']
            assert q['proximity']['nearby_robot_contacts']==previous['proximity']['nearby_robot_contacts']
            for mask in ['M0_initial_contact_free','M1_initial_and_proximity_contact_free']:assert q[mask]==previous[mask]
            result['rows'].append(dict(demo=row['demo'],t=t,nominal_state_and_controller_error=0.,contact_lists_exactly_reproduced=True,
                                       masks_exactly_reproduced=True,original_state_unchanged=True,
                                       nearby_contacts=q['proximity']['nearby_robot_contacts']))
            h.write(O/'result.json',result)
    assert len(result['rows'])==12
    result.update(state='NATIVE_FILTER_QUERIES_INDEPENDENTLY_REPRODUCED',reconstructed_anchors=12,query_forward_calls=12,
                  raw_sha256=h.sha(D/'result.json'),filter_analysis_sha256=h.sha(D/'filter_analysis.json'),source_sha256=h.sha(Path(__file__)),
                  native_version=mujoco.__version__,other_setup_forward_calls_not_instrumented=True)
except BaseException:
    result.update(state='FAILED',error=traceback.format_exc());traceback.print_exc()
finally:
    if env is not None:env.env.close()
    result['elapsed_seconds']=time.monotonic()-start;h.write(O/'result.json',result)
print(json.dumps({k:v for k,v in result.items() if k!='rows'},indent=2))
raise SystemExit(0 if result['state']=='NATIVE_FILTER_QUERIES_INDEPENDENTLY_REPRODUCED' else 2)
