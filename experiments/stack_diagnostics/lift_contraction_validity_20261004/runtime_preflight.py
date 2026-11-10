"""No-training integration check after the preserved failed pilot launch."""
import hashlib
import importlib.util
import json
from pathlib import Path
import time
import traceback

HERE=Path(__file__).resolve().parent
ROOT=Path(__file__).resolve().parents[3]


def sha(p):
    h=hashlib.sha256()
    with p.open('rb') as f:
        for block in iter(lambda:f.read(1048576),b''):h.update(block)
    return h.hexdigest()


def main():
    started=time.monotonic();result={'state':'RUNNING','policy_optimizer_updates':0,'retry_launched':False}
    env=None
    try:
        script=HERE/'sensor_pilot/run.py'
        spec=importlib.util.spec_from_file_location('prepared_pilot',script);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        module.bootstrap()
        import numpy as np
        import torch
        from robomimic.algo import algo_factory
        from robomimic.config import config_factory
        from robomimic.utils import obs_utils as OU, env_utils as EU, file_utils as FU, train_utils as TU
        import robosuite
        import robomimic_ext
        torch.set_num_threads(2)
        shapes={'robot0_eef_pos':(3,), 'robot0_eef_quat':(4,), 'robot0_gripper_qpos':(2,), 'object':(10,)}
        cfg=config_factory('bc_sensor')
        with cfg.values_unlocked():cfg.update(module.read(HERE/'sensor_pilot/B1/config.json'))
        cfg.lock();OU.initialize_obs_utils_with_config(cfg)
        model=algo_factory('bc_sensor',cfg,shapes,7,torch.device('cpu'))
        ds=cfg.train.data[0];metadata=FU.get_env_metadata_from_dataset(dataset_path=ds['path']);metadata['lang']=None
        shape=FU.get_shape_metadata_from_dataset(dataset_config=ds,action_keys=cfg.train.action_keys,all_obs_keys=cfg.all_obs_keys)
        env=EU.create_env_from_metadata(metadata,render=False,render_offscreen=False)
        obs=env.reset()
        b={'obs':{k:torch.tensor(obs[k],dtype=torch.float32)[None] for k in shapes},'goal_obs':None,'actions':torch.zeros(1,7)}
        with torch.no_grad():info=model.train_on_batch(b,1,validate=True)
        before=module.parameter_hash(model)
        target=HERE/'runtime_preflight'/'untrained_roundtrip.pth';target.parent.mkdir(exist_ok=True)
        assert not target.exists(),'Preserve prior preflight outputs'
        TU.save_model(model=model,config=cfg,env_meta=metadata,shape_meta=shape,ckpt_path=str(target),variable_state={'optimizer_updates':0,'untrained_preflight':True})
        policy,_=FU.policy_from_checkpoint(ckpt_path=str(target),device=torch.device('cpu'),verbose=False)
        policy.start_episode();action=policy(ob=obs)
        next_obs,_,_,_=env.step(action)
        assert np.isfinite(action).all() and np.isfinite(next_obs['robot0_eef_pos']).all()
        assert before==module.parameter_hash(policy.policy)
        runtime=ROOT/'praxis/upstream/robosuite/robosuite'
        files={p for p in (runtime/'models/assets').rglob('*') if p.is_file()}
        files.update((runtime/'controllers/config').rglob('*.json'))
        files.add(runtime/'utils/mujoco.dll')
        hashes={str(p.relative_to(ROOT)):sha(p) for p in sorted(files)}
        (HERE/'runtime_preflight/dependency_assets_hashes.json').write_text(json.dumps(hashes,indent=2)+'\n',encoding='utf-8')
        result.update(state='COMPLETE',imports_and_lift_env_reset_step=True,checkpoint_policy_roundtrip=True,
                      untrained_checkpoint_sha256=sha(target),corrected_runner_sha256=sha(script),
                      preserved_original_runner_sha256=sha(HERE/'sensor_pilot/source_snapshot'/script.relative_to(ROOT)),
                      local_method_module=robomimic_ext.__file__,complete_simulator_module=robosuite.__file__,
                      dependency_asset_files=len(files),validation_loss=float(info['losses']['action_loss']))
    except BaseException:
        result.update(state='FAILED',error=traceback.format_exc());raise
    finally:
        if env is not None:env.env.close()
        result['elapsed_seconds']=time.monotonic()-started
        (HERE/'runtime_preflight.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(result,indent=2))


if __name__=='__main__':main()
