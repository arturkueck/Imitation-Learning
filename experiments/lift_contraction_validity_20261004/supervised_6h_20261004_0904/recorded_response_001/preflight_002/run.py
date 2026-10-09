import importlib.util,json,sys,traceback,time
from pathlib import Path
import numpy as np,h5py
O=Path(__file__).resolve().parent;D=O.parent;S=D.parent
sys.path.insert(0,str(D))
import helpers as h
import preparation
h.OUT=O
def history_changes(a,b,path=""):
    if isinstance(a,dict) and isinstance(b,dict):
        rows=[]
        for k in sorted(set(a)|set(b)):rows += history_changes(a.get(k),b.get(k),path+"/"+k)
        return rows
    if a is None or b is None:
        return [] if a is b else [dict(field=path,change="presence",prefix_value=a,reset_value=b)]
    if isinstance(a,(str,bool)) or isinstance(b,(str,bool)):
        return [] if a==b else [dict(field=path,change="categorical",prefix_value=a,reset_value=b)]
    x,y=np.asarray(a),np.asarray(b)
    if x.shape!=y.shape:return [dict(field=path,change="shape",prefix_shape=x.shape,reset_shape=y.shape)]
    error=float(np.max(np.abs(x-y),initial=0))
    return [dict(field=path,change="numeric",max_absolute_difference=error)] if error else []

start=time.monotonic();result=dict(state='RUNNING',training_updates=0,response_probe_steps=0,preparations=[]);env=None
try:
    selection=h.read(D/'selection.json');P=h.PILOT
    spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
    import torch
    from robomimic.utils.file_utils import env_from_checkpoint
    from robomimic.config import config_factory
    import robomimic.utils.obs_utils as ObsUtils
    ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False);cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg)
    env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False)
    demo=selection['selected_demos'][0]
    with h5py.File(h.ROOT/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
        d=f['data/'+demo];t=int(selection['anchor_fractions'][0]*(len(d['actions'])-1));snapshots=[]
        for history in selection['histories']:
            np.random.seed(selection['seed']);torch.manual_seed(selection['seed']);env.reset_to({'model':d.attrs['model_file'],'states':d['states'][0]})
            ctrl=env.env.robots[0].composite_controller.part_controllers['right']
            info=preparation.prepare(env,ctrl,d,t,d['actions'][:],history,selection);snapshot=h.snapshot(env,ctrl)
            assert info['geometry_passed'] and info['retained_memory_error']==0 and info['state_roundtrip_error']==0
            result['preparations'].append(dict(history=history,demo=demo,t=t,info=info,snapshot=snapshot));snapshots.append(snapshot)
        physical_error=h.difference(snapshots[0]['sim'],snapshots[1]['sim']);clock_error=h.difference(snapshots[0]['env_time'],snapshots[1]['env_time'])
        assert physical_error==clock_error==0
        result.update(state='PREFLIGHT_PASSED',same_recorded_physical_state_error=physical_error,same_env_clock_error=clock_error,
                      intended_controller_history_difference=history_changes(snapshots[0]['controllers'],snapshots[1]['controllers']),
                      intended_gripper_memory_difference=h.difference(snapshots[0]['gripper_memory'],snapshots[1]['gripper_memory']),
                      counts=h.COUNTS)
except BaseException:
    result.update(state='FAILED',error=traceback.format_exc());traceback.print_exc()
finally:
    if env is not None:env.env.close()
    result['elapsed_seconds']=time.monotonic()-start;h.write(O/'result.json',result)
print(json.dumps({k:v for k,v in result.items() if k!='preparations'},indent=2))
raise SystemExit(0 if result['state']=='PREFLIGHT_PASSED' else 2)
