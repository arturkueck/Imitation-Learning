"""Validate custom tasks, render previews, and save dataset-gated BC configs."""
import sys
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT / 'experiments/square/scripts'))
import runtime
import video_views
import imageio.v2 as imageio
import numpy as np
from robomimic.envs.env_robosuite import EnvRobosuite
from robomimic.utils import obs_utils

obs_utils.initialize_obs_utils_with_obs_specs({'obs':{'rgb':['agentview_image'],'low_dim':[]}})

BASE = ROOT / 'experiments/additional_tasks'
source = json.loads((ROOT / 'experiments/square/dataset_info.json').read_text())
controller = source['environment']['env_kwargs']['controller_configs']
summary = {}
for task,env_name,robots in [('stack_four','StackFour',['Panda']),
                           ('cube_handover','CubeHandover',['Panda','Panda'])]:
    folder = BASE / task
    folder.mkdir(parents=True,exist_ok=True)
    kwargs = dict(robots=robots,controller_configs=controller if len(robots)==1 else [controller,controller],
        camera_names=['agentview'],camera_heights=64,camera_widths=64,
        control_freq=20,horizon=1000,ignore_done=True,reward_shaping=False)
    if len(robots)==2: kwargs['env_configuration'] = 'opposed'
    env = EnvRobosuite(env_name=env_name,render=False,render_offscreen=True,use_image_obs=True,**kwargs)
    obs = env.reset()
    assert not env.is_success()['task'], 'Initial scene must not be successful'
    action_dimension = env.action_dimension
    assert action_dimension == 7*len(robots)
    video_views.setup_cameras(env)
    imageio.imwrite(folder / 'scene.png',video_views.frame(env))
    with imageio.get_writer(str(folder / 'scene_preview.mp4'),fps=20) as writer:
        for _ in range(40):
            action = np.zeros(action_dimension)
            action[6::7] = -1
            obs,_,_,_ = env.step(action)
            writer.append_data(video_views.frame(env))
    if task == 'stack_four':
        # Predicate check ONLY: construct a tower in simulator state, settle it,
        # then topple it. Not an expert trajectory or recorded policy result.
        raw = env.base_env
        for i,cube in enumerate(raw.cubes):
            raw.sim.data.set_joint_qpos(cube.joints[0],np.array([0.,0.,.82+.04*i,1.,0.,0.,0.]))
            raw.sim.data.set_joint_qvel(cube.joints[0],np.zeros(6))
        raw.sim.forward()
        for _ in range(30): env.step(action)
        assert env.is_success()['task'], 'A settled four-cube tower must be successful'
        raw.sim.data.set_joint_qpos(raw.cubeD.joints[0],np.array([.15,0.,.82,1.,0.,0.,0.]))
        raw.sim.forward(); env.step(action)
        assert not env.is_success()['task'], 'Removing top cube must revoke success'
    info = {'task':task,'environment':env.serialize(),'action_dimension':action_dimension,
        'camera_keys':['agentview_image'],'proprioception_keys':[
            f'robot{i}_{key}' for i in range(len(robots))
            for key in ['eef_pos','eef_quat','gripper_qpos']],
        'dataset':str(folder / 'data/image_demonstrations.hdf5'),
        'status':'NEEDS_DEMONSTRATIONS','preview_is':'untrained environment; open grippers and zero arm actions'}
    (folder / 'task_info.json').write_text(json.dumps(info,indent=2))
    for method in ['bc','bc_rnn','bc_transformer']:
        cfg = json.loads((ROOT / 'experiments/square' / method / 'config.json').read_text())
        cfg['experiment']['name'] = f'{task}_{method}'
        cfg['train'].update(data=[{'path':info['dataset']}],output_dir=str(folder/method/'runs'),num_epochs=1000)
        cfg['observation']['modalities']['obs']['low_dim'] = info['proprioception_keys']
        cfg['experiment']['save']['every_n_epochs'] = 100
        cfg['experiment']['rollout']['horizon'] = 1000
        out = folder / method; out.mkdir(exist_ok=True)
        (out / 'config.json').write_text(json.dumps(cfg,indent=2))
    summary[task] = info
    print('TASK_SMOKE_OK',task,action_dimension,flush=True)
    del env
(BASE / 'status.json').write_text(json.dumps(summary,indent=2))
