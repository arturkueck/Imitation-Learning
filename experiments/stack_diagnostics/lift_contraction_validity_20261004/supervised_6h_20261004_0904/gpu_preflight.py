"""Full pipeline check with discarded one-update test models, before fresh training."""
import importlib.util
import json
from pathlib import Path
import sys
import time
import traceback


def main(attempt):
    started=time.monotonic();env=None
    spec=importlib.util.spec_from_file_location('attempt_core',attempt/'run.py');core=importlib.util.module_from_spec(spec);spec.loader.exec_module(core)
    result={'state':'RUNNING','test_optimizer_updates':{},'pilot_optimizer_updates':0}
    try:
        core.bootstrap()
        import numpy as np
        import torch
        from torch.utils.data import DataLoader
        from robomimic.algo import algo_factory
        from robomimic.config import config_factory
        from robomimic.utils import train_utils as TU, obs_utils as OU, file_utils as FU, env_utils as EU
        assert torch.cuda.is_available(),'GPU unavailable'
        torch.set_num_threads(2)
        cfgs={}
        for arm,algo in [('B0','bc'),('B1','bc_sensor')]:
            cfg=config_factory(algo)
            with cfg.unlocked():
                cfg.update(core.read(attempt/arm/'config.json'))
                cfg.algo.optim_params.policy.num_train_batches=100
                cfg.algo.optim_params.policy.num_epochs=20
            cfg.lock();cfgs[arm]=cfg
        OU.initialize_obs_utils_with_config(cfgs['B0'])
        ds=cfgs['B0'].train.data[0]
        metadata=FU.get_env_metadata_from_dataset(dataset_path=ds['path']);metadata['lang']=None
        shapes=FU.get_shape_metadata_from_dataset(dataset_config=ds,action_keys=cfgs['B0'].train.action_keys,all_obs_keys=cfgs['B0'].all_obs_keys)
        trainset,validset=TU.load_data_for_training(cfgs['B0'],obs_keys=shapes['all_obs_keys'])
        raw=next(iter(DataLoader(trainset,batch_size=100,shuffle=False,num_workers=0,drop_last=True)))
        initial={};losses={};last_policy=None
        directory=attempt/'preflight';directory.mkdir(exist_ok=True)
        for arm,algo in [('B0','bc'),('B1','bc_sensor')]:
            OU.initialize_obs_utils_with_config(cfgs[arm]);torch.manual_seed(41004)
            model=algo_factory(algo,cfgs[arm],shapes['all_shapes'],shapes['ac_dim'],torch.device('cuda'))
            initial[arm]=core.parameter_hash(model)
            batch=model.process_batch_for_training(raw)
            info=model.train_on_batch(batch,1,validate=False);torch.cuda.synchronize()
            steps={int(s['step']) for s in model.optimizers['policy'].state.values()}
            assert steps=={1};result['test_optimizer_updates'][arm]=1
            losses[arm]=float(info['losses']['action_loss']);assert np.isfinite(losses[arm])
            target=directory/f'{arm}_test_one_update.pth';assert not target.exists()
            TU.save_model(model=model,config=cfgs[arm],env_meta=metadata,shape_meta=shapes,ckpt_path=str(target),
                          variable_state={'preflight_only':True,'optimizer_updates':1})
            policy,_=FU.policy_from_checkpoint(ckpt_path=str(target),device=torch.device('cuda'),verbose=False)
            assert core.parameter_hash(policy.policy)==core.parameter_hash(model)
            last_policy=policy
        assert initial['B0']==initial['B1']
        env=EU.create_env_from_metadata(metadata,render=False,render_offscreen=False)
        obs=env.reset();last_policy.start_episode();action=last_policy(ob=obs)
        obs,_,_,_=env.step(action)
        assert np.isfinite(action).all() and np.isfinite(obs['robot0_eef_pos']).all()
        result.update(state='COMPLETE',gpu=torch.cuda.get_device_name(0),torch=torch.__version__,dataset_sha256=core.sha(Path(ds['path'])),
                      initial_parameters_equal=True,losses=losses,simulator_step=True,checkpoint_roundtrip=True,
                      test_checkpoint_hashes={p.name:core.sha(p) for p in directory.glob('*.pth')})
    except BaseException:
        result.update(state='FAILED',error=traceback.format_exc());traceback.print_exc()
    finally:
        if env is not None:env.env.close()
        result['elapsed_seconds']=time.monotonic()-started;core.write(attempt/'preflight_result.json',result)
        print(json.dumps(result,indent=2),flush=True)
    return 0 if result['state']=='COMPLETE' else 2


if __name__=='__main__':sys.exit(main(Path(sys.argv[1]).resolve()))
