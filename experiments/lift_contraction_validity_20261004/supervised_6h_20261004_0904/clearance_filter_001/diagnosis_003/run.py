import importlib.util,json,sys,traceback,time
from pathlib import Path
import numpy as np,h5py
O=Path(__file__).resolve().parent;D=O.parent;S=D.parent
sys.path.insert(0,str(D))
import helpers as h
import preparation
import clearance_debug as clearance
h.OUT=O
start=time.monotonic();result=dict(state='RUNNING',policy_training_updates=0,response_probe_steps=0,physics_integration_steps=0,synthetic_cases=[]);env=None
try:
    P=h.PILOT;spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
    import torch,mujoco
    assert mujoco.__version__=='3.2.3'
    for excluded in []:
        for gap in [0.,.005,.020]:
            exclude='<contact><exclude body1="one" body2="two"/></contact>' if excluded else ''
            xml=f'<mujoco><worldbody><body name="one" pos="0 0 0"><freejoint/><geom name="box_one" type="box" size=".02 .02 .02"/></body><body name="two" pos="{.04+gap} 0 0"><freejoint/><geom name="box_two" type="box" size=".02 .02 .02"/></body></worldbody>{exclude}</mujoco>'
            model=mujoco.MjModel.from_xml_string(xml);data=mujoco.MjData(model);mujoco.mj_forward(model,data)
            original=clearance.contacts(model,data,{'box_one','box_two'})
            q=clearance.query(model,data,{'box_one','box_two'},.015)
            expected=not excluded and gap<.015
            assert bool(q['nearby_robot_contacts'])==expected,(excluded,gap,q['nearby_robot_contacts'])
            result['synthetic_cases'].append(dict(gap_m=gap,body_pair_excluded=excluded,original_contacts=original,query=q,expected_nearby=expected))
    from robomimic.utils.file_utils import env_from_checkpoint
    from robomimic.config import config_factory
    import robomimic.utils.obs_utils as ObsUtils
    ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False);cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg)
    env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False)
    # Already observed frame only, not one of the fresh test demos.
    selection=h.read(D/'selection.json');demo='demo_69'
    with h5py.File(h.ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
        d=f['data/'+demo];t=int(.1*(len(d['actions'])-1));np.random.seed(selection['seed']);torch.manual_seed(selection['seed'])
        env.reset_to({'model':d.attrs['model_file'],'states':d['states'][0]});ctrl=env.env.robots[0].composite_controller.part_controllers['right']
        prep=preparation.prepare(env,ctrl,d,t,d['actions'][:],'H_reset',selection)
        assert prep['geometry_passed'] and prep['retained_memory_error']==0 and prep['state_roundtrip_error']==0
        result['known_frame']=dict(demo=demo,t=t,preparation=prep,query=clearance.filter_anchor(env,ctrl,.015))
    result.update(state='PREFLIGHT_PASSED',native_version=mujoco.__version__,synthetic_cases_passed=6,
                  query_forward_calls=7,synthetic_original_forward_calls=6,recorded_reconstructions=1,
                  other_setup_forward_calls_not_instrumented=True)
except BaseException:
    result.update(state='FAILED',error=traceback.format_exc());traceback.print_exc()
finally:
    if env is not None:env.env.close()
    result['elapsed_seconds']=time.monotonic()-start;h.write(O/'result.json',result)
print(json.dumps({k:v for k,v in result.items() if k not in ['known_frame','synthetic_cases']},indent=2))
raise SystemExit(0 if result['state']=='PREFLIGHT_PASSED' else 2)
