"""Independent CPU/data diagnosis; does not load or alter active training."""
import json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/square/scripts'))
import runtime
import h5py
import numpy as np
import imageio.v2 as imageio
from PIL import Image,ImageDraw
from robomimic.utils.env_utils import create_env_for_data_processing
from task_extensions.stack_expert import make_expert
OUT=ROOT/'experiments/diffusion_20261001/diagnostics'; OUT.mkdir(exist_ok=True)
info=json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())
env=create_env_for_data_processing(info['environment'],camera_names=['agentview'],camera_height=64,
    camera_width=64,reward_shaping=False)
results=[]
with h5py.File(info['dataset'],'r') as f:
    for split in ('train','valid'):
        for encoded in f['mask/'+split][:3]:
            name=encoded.decode(); demo=f['data'][name]; states=demo['states'][:]; actions=demo['actions'][:]
            reset={'model':demo.attrs['model_file'],'states':states[0]}
            if 'ep_meta' in demo.attrs: reset['ep_meta']=demo.attrs['ep_meta']
            obs=env.reset_to(reset)
            state_errors=[]
            initial_obs_errors={k:float(np.max(np.abs(obs[k]-demo['obs/'+k][0])))
                for k in info['proprioception_keys']+info['object_keys']}
            initial_image_mae=float(np.abs(obs['agentview_image'].astype(float)-demo['obs/agentview_image'][0]).mean())
            for step,action in enumerate(actions):
                obs,_,_,_=env.step(action)
                if step+1<len(states): state_errors.append(float(np.max(np.abs(env.get_state()['states']-states[step+1]))))
            replay_success=bool(env.is_success()['task'])
            # Replay recorded states to verify labels and observation transforms,
            # independent of cumulative physics drift in an action-only replay.
            env.reset_to(reset); expert=make_expert(env)
            label_error=0.; obs_error=0.; image_checks=[]; phase_counts={}; change_steps=[]
            for step,state in enumerate(states):
                obs=env.reset_to({'states':state})
                label=np.asarray(expert(obs),dtype=np.float32)
                label_error=max(label_error,float(np.max(np.abs(label-actions[step]))))
                for key in info['proprioception_keys']+info['object_keys']:
                    obs_error=max(obs_error,float(np.max(np.abs(obs[key]-demo['obs/'+key][step]))))
                phase_counts[str(expert.phase)]=phase_counts.get(str(expert.phase),0)+1
                if step and actions[step,-1]!=actions[step-1,-1]: change_steps.append(step)
                if step in (0,len(states)//2,len(states)-1):
                    stored=demo['obs/agentview_image'][step].astype(float)
                    actual=obs['agentview_image'].astype(float)
                    image_checks.append(dict(step=step,mae=float(abs(actual-stored).mean()),
                        flipped_mae=float(abs(actual[::-1]-stored).mean())))
            row=dict(demo=name,split=split,length=len(actions),action_replay_success=replay_success,
                state_error_first=state_errors[0],state_error_max=max(state_errors),
                initial_obs_errors=initial_obs_errors,initial_image_mae=initial_image_mae,
                restored_state_observation_max_error=obs_error,expert_label_max_error=label_error,
                image_checks=image_checks,gripper_switch_steps=change_steps,phase_counts=phase_counts)
            results.append(row); print(json.dumps(row),flush=True)
            (OUT/'demo_replay.json').write_text(json.dumps(results,indent=2))
env.base_env.close()
# Inspect already generated videos; decoding is CPU-only.
for tag,folder in [('bc_vision',ROOT/'experiments/workday_20261001/videos/test/stack_two_vision_short'),
                   ('dp_vision',ROOT/'experiments/diffusion_20261001/videos/test/stack_two_diffusion_vision'),
                   ('dp_state',ROOT/'experiments/diffusion_20261001/videos/test/stack_two_diffusion_state')]:
    for episode in (0,1):
        path=folder/f'rollout_{episode:02d}.mp4'
        if not path.exists(): continue
        reader=imageio.get_reader(str(path)); count=reader.count_frames()
        indices=[min(count-1,i) for i in (0,10,30,60,90,99)]
        sheet=Image.new('RGB',(1152,808),'white'); draw=ImageDraw.Draw(sheet)
        for index,frame in enumerate(indices):
            x=index%3*384; y=index//3*404
            sheet.paste(Image.fromarray(reader.get_data(frame)).resize((384,384)),(x,y+20))
            draw.text((x+4,y+3),f'{tag} seed {26000+episode} frame {frame}',fill='black')
        sheet.save(OUT/f'{tag}_{episode}_grid.png'); reader.close()
print('DIAGNOSIS_COMPLETED',flush=True)
