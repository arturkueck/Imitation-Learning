"""Prepare independent, reviewable comparisons; preserve all previous runs."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'experiments/baselines/square/scripts'))
import runtime
import imageio.v2 as imageio
import numpy as np
from robomimic.envs.env_robosuite import EnvRobosuite
from robomimic.utils import obs_utils
import video_views

EXP = ROOT/'experiments/baselines/workday_20261001'
TASK = ROOT/'experiments/baselines/additional_tasks/stack_two'
TASK.mkdir(parents=True,exist_ok=True)
obs_utils.initialize_obs_utils_with_obs_specs({'obs':{'rgb':['agentview_image'],'low_dim':[]}})
source = json.loads((ROOT/'experiments/baselines/additional_tasks/stack_four/task_info.json').read_text())
kwargs = source['environment']['env_kwargs'].copy()
kwargs['horizon'] = 500
env = EnvRobosuite(env_name='StackTwo',render=False,render_offscreen=True,use_image_obs=True,**kwargs)
obs = env.reset()
assert len(env.base_env.cubes)==2 and env.action_dimension==7
assert not env.is_success()['task']
assert obs['object'].shape == (6,)
video_views.setup_cameras(env)
imageio.imwrite(TASK/'scene.png',video_views.frame(env))
raw = env.base_env
for i,cube in enumerate(raw.cubes):
    raw.sim.data.set_joint_qpos(cube.joints[0],np.r_[0.,0.,.82+.04*i,1.,0.,0.,0.])
    raw.sim.data.set_joint_qvel(cube.joints[0],np.zeros(6))
raw.sim.forward()
for _ in range(30): env.step(np.r_[np.zeros(6),-1.])
assert env.is_success()['task'], 'Settled two-cube tower must pass'
raw.sim.data.set_joint_qpos(raw.cubeB.joints[0],np.r_[.15,0.,.82,1.,0.,0.,0.])
raw.sim.forward(); env.step(np.r_[np.zeros(6),-1.])
assert not env.is_success()['task'], 'Removing B must revoke success'
info = dict(task='stack_two',environment=env.serialize(),action_dimension=7,
    camera_keys=['agentview_image'],proprioception_keys=source['proprioception_keys'],
    object_keys=['object'],object_order=['cubeA_pos','cubeB_pos'],dataset=str(TASK/'data/image_demonstrations.hdf5'),
    status='NEEDS_DEMONSTRATIONS',horizon=500)
(TASK/'task_info.json').write_text(json.dumps(info,indent=2))
env.base_env.close()

jobs=[]
for name,context,state in [('stack_two_vision_short',5,False),
                            ('stack_two_vision_long',20,False),
                            ('stack_two_state_long',20,True),
                            ('square_rnn_gmm',5,False)]:
    square = name.startswith('square')
    cfg=json.loads((ROOT/'experiments/baselines/square/bc_rnn/config.json').read_text())
    cfg['experiment']['name']=name
    cfg['experiment']['save']['every_n_epochs']=50
    cfg['experiment']['save']['on_best_validation']=False
    cfg['experiment']['rollout']['enabled']=False
    cfg['train'].update(output_dir=str(EXP/name/'runs'),num_epochs=400,
        seq_length=context,batch_size=16 if context==5 else 4)
    cfg['algo']['rnn']['horizon']=context
    cfg['experiment']['rollout']['horizon']=400 if square else 500
    if square:
        cfg['algo']['gmm']['enabled']=True
    else:
        cfg['train']['data']=[{'path':info['dataset']}]
        cfg['observation']['modalities']['obs']['low_dim']=info['proprioception_keys']+(
            info['object_keys'] if state else [])
        if state: cfg['observation']['modalities']['obs']['rgb']=[]
    folder=EXP/name; folder.mkdir(parents=True,exist_ok=True)
    config=folder/'config.json'; config.write_text(json.dumps(cfg,indent=2))
    jobs.append(dict(name=name,config=str(config),horizon=400 if square else 500,
        kind='Square' if square else 'StackTwo',context=context,
        oracle_object_positions=state,epochs=400))
(EXP/'manifest.json').write_text(json.dumps(dict(jobs=jobs,deadline_hours=6.5,
    nominal_selection_episodes=15,final_test_episodes=50,robustness_episodes=10,
    seeds=dict(selection=6000,final_test=26000,robustness=36000)),indent=2))

# Audit actual saved measurements, including historical weaker algorithms.
audit=[]
for path in (ROOT/'experiments').rglob('evaluation_results.json'):
    if any(s in path.parts for s in ('robustness','smoke','robustness_smoke','robustness_verified')):
        continue
    data=json.loads(path.read_text())
    if isinstance(data,dict) and 'checkpoint' in data:
        audit.append(dict(path=str(path),checkpoint=data['checkpoint'],
            episodes=data['episodes'],success_rate=data['success_rate']))
(EXP/'prior_results_audit.json').write_text(json.dumps(audit,indent=2))
print('SETUP_VALIDATED',json.dumps(jobs),flush=True)
