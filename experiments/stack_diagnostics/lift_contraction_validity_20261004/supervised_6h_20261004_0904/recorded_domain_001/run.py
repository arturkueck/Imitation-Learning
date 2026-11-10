"""Static recorded-state geometry and annotation availability, no policy or actions."""
import hashlib,importlib.util,json,time,traceback
from pathlib import Path
import numpy as np,h5py
import helpers as h
O=h.OUT;S=h.SESSION;R=h.ROOT;P=h.PILOT
def quatangle(a,b):
    a,b=np.array(a),np.array(b);n=np.linalg.norm(a)*np.linalg.norm(b)
    return float(2*np.arccos(np.clip(abs(a@b)/n,0,1))) if n>0 else None
def run():
    start=time.monotonic();env=None;selection=h.read(O/'selection.json')
    result=dict(state='RUNNING',selection=selection,rows=[],policy_training_updates=0,optimizer_constructions=0,
                action_rollout_steps=0,explicit_forward_calls=0,reset_to_calls=0)
    assert not (O/'result.json').exists();h.write(O/'result.json',result)
    try:
        assert h.sha(P/'B0/model_final.pth')==selection['checkpoint_sha256']
        assert h.sha(R/'praxis/data/lift/ph/low_dim_v15.hdf5')==selection['dataset_sha256']
        assert h.sha(S/'gradient_audit_001/result.json')==selection['source_gradient_sha256']
        spec=importlib.util.spec_from_file_location('frozen_pilot',P/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core);core.bootstrap()
        import torch
        from robomimic.config import config_factory
        from robomimic.utils.file_utils import env_from_checkpoint
        import robomimic.utils.obs_utils as ObsUtils
        torch.set_num_threads(2);torch.manual_seed(selection['seed']);np.random.seed(selection['seed'])
        ckpt=torch.load(P/'B0/model_final.pth',map_location='cpu',weights_only=False)
        cfg=config_factory('bc',dic=json.loads(ckpt['config']));ObsUtils.initialize_obs_utils_with_config(cfg)
        env,_=env_from_checkpoint(ckpt_dict=ckpt,render=False,render_offscreen=False)
        def prohibit_step(*args,**kwargs):raise RuntimeError('Static audit prohibits env.step')
        env.step=prohibit_step
        result['observation_pipeline']=dict(native_keys=ckpt['shape_metadata']['all_obs_keys'],
                                            observation_normalization=cfg.train.hdf5_normalize_obs,
                                            actor_constructed=False,controller_history_reconstruction=False)
        with h5py.File(R/'praxis/data/lift/ph/low_dim_v15.hdf5','r') as f:
            for selection_row in selection['frames']:
                h.stop_check();demo,t=selection_row['demo'],selection_row['t'];d=f['data/'+demo]
                recorded_state=d['states'][t];xml=d.attrs['model_file'];env.reset_to({'model':xml,'states':recorded_state});result['reset_to_calls']+=1
                env.env.sim.forward();result['explicit_forward_calls']+=1
                obs=env.get_observation();robot=env.env.robots[0];contacts=h.robot_contacts(env.env.sim,robot)
                wanted={k:d['obs/'+k][t] for k in ckpt['shape_metadata']['all_obs_keys']}
                position=float(np.linalg.norm(obs['robot0_eef_pos']-wanted['robot0_eef_pos']))
                object_position=float(np.linalg.norm(obs['object'][:3]-wanted['object'][:3]))
                relative=float(np.linalg.norm(obs['object'][-3:]-wanted['object'][-3:]))
                eef_angle=quatangle(obs['robot0_eef_quat'],wanted['robot0_eef_quat']);object_angle=quatangle(obs['object'][3:7],wanted['object'][3:7])
                gripper=float(np.max(np.abs(obs['robot0_gripper_qpos']-wanted['robot0_gripper_qpos'])))
                roundtrip=np.asarray(env.get_state()['states'])
                roundtrip_error=float(np.max(np.abs(roundtrip-recorded_state))) if roundtrip.shape==recorded_state.shape else None
                metrics=dict(eef_position_error_m=position,object_position_error_m=object_position,object_relative_error_m=relative,
                             eef_orientation_error_rad=eef_angle,object_orientation_error_rad=object_angle,gripper_qpos_error=gripper,
                             state_roundtrip_error=roundtrip_error)
                geometry=bool(max(position,object_position,relative)<=selection['position_tolerance_m'] and eef_angle is not None and object_angle is not None
                              and max(eef_angle,object_angle)<=selection['orientation_tolerance_rad'] and gripper<=selection['gripper_qpos_tolerance'])
                extras={k:dict(max_absolute_error=float(np.max(np.abs(np.array(obs[k])-d['obs/'+k][t]))),
                               recorded=d['obs/'+k][t].tolist(),reconstructed=np.array(obs[k]).tolist())
                        for k in d['obs'] if k not in wanted and k in obs and np.array(obs[k]).shape==d['obs/'+k][t].shape}
                row={**selection_row,'recorded':{k:v.tolist() for k,v in wanted.items()},
                     'reconstructed':{k:np.asarray(obs[k]).tolist() for k in wanted},'recorded_dtypes':{k:str(d['obs/'+k].dtype) for k in wanted},
                     'metrics':metrics,'geometry_passed':geometry,'robot_contacts':contacts,'contact_free':not contacts,
                     'static_annotation_eligible':geometry and not contacts,'extra_features':extras,
                     'recorded_state_sha256':hashlib.sha256(recorded_state.tobytes()).hexdigest(),
                     'xml_sha256':hashlib.sha256(xml.encode() if isinstance(xml,str) else xml).hexdigest()}
                result['rows'].append(row);result['elapsed_seconds']=time.monotonic()-start;h.write(O/'result.json',result)
                print(f'{demo} t={t}: geometry={geometry}, contacts={len(contacts)}',flush=True)
        assert len(result['rows'])==60
        result.update(state='COMPLETE_STATIC_AUDIT',checkpoint_sha256_after=h.sha(P/'B0/model_final.pth'),
                      decision='Static recorded-frame annotation only. Start contact freedom does not establish valid dynamic regularization or expert-label semantics.')
        assert result['checkpoint_sha256_after']==selection['checkpoint_sha256']
        return 0
    except BaseException as exc:
        result.update(state='INTERRUPTED' if isinstance(exc,InterruptedError) else 'FAILED',error=traceback.format_exc());traceback.print_exc();return 2
    finally:
        if env is not None:env.env.close()
        result['elapsed_seconds']=time.monotonic()-start;h.write(O/'result.json',result)
if __name__=='__main__':raise SystemExit(run())
