"""Fixed development-only replay and prebuilt-tower intervention; no training."""
import copy,hashlib,json,random,time
from pathlib import Path
from collections import deque
import numpy as np
import torch
import imageio.v2 as imageio
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from run import OUT,ROOT,Model,features,prefix_valid,robosuite,write

DEST=OUT/'replay_diagnosis'
CASES=[('relative_seed1',30000),('relative_seed2',10000),('relative_seed2',30000)]
SEEDS=list(range(61000,61005))

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def env_create():
    kw=copy.deepcopy(json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())['environment']['env_kwargs'])
    kw.update(has_offscreen_renderer=True,use_camera_obs=False,has_renderer=False,hard_reset=False,horizon=1000)
    return robosuite.make('StackThree',**kw)

@torch.no_grad()
def episode(env,model,seed,mode,folder,video):
    np.random.seed(seed);random.seed(seed);obs=env.reset()
    initial=env.sim.get_state().flatten().copy();initial_hash=hashlib.sha256(initial.tobytes()).hexdigest()
    stage=1;first=None
    if mode=='prebuilt':
        # Explicit diagnostic intervention, never counted as full-task success.
        base=env.sim.data.body_xpos[env.cube_ids[0]].copy()
        env.sim.data.set_joint_qpos(env.cubes[1].joints[0],np.r_[base+[0,0,.04],[1,0,0,0]])
        env.sim.data.set_joint_qvel(env.cubes[1].joints[0],np.zeros(6));env.sim.forward()
        for _ in range(40):obs,_,_,_=env.step(np.array([0,0,0,0,0,0,-1.]))
        assert prefix_valid(env,2),'Prebuilt tower did not settle'
        stage=2;first=0
    start_state=env.sim.get_state().flatten().copy()
    hist=deque(maxlen=2);queue=deque();stable=0;pair_stable=0;rows=[];frames=[]
    writer=imageio.get_writer(str(folder/f'{mode}_{seed}.mp4'),fps=10) if video else None
    try:
        for t in range(1000):
            p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            local={k:obs[k] for k in ['robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']};local['object']=np.r_[p[stage-1],p[stage]]
            x=features(local,'relative');hist.append(x)
            if len(hist)==1:hist.append(x.copy())
            if not queue:queue.extend(model(torch.tensor(np.stack(hist).reshape(1,30),device='cuda'))[0].cpu().numpy()[1:3])
            action=queue.popleft();eef_before=obs['robot0_eef_pos'].copy();stage_before=stage
            obs,_,_,_=env.step(action)
            p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
            grasp=[env._check_grasp(env.robots[0].gripper,c) for c in env.cubes]
            finger=[env.check_contact(env.robots[0].gripper,c) for c in env.cubes]
            contacts=[env.check_contact(env.cubes[i],env.cubes[i+1]) for i in range(2)]
            valid2=prefix_valid(env,2);valid3=prefix_valid(env,3)
            velocities=np.concatenate([env.sim.data.get_joint_qvel(c.joints[0]).copy() for c in env.cubes])
            rows.append(np.r_[t,stage_before,p.flatten(),obs['robot0_eef_pos'],action,grasp,finger,contacts,valid2,valid3,velocities])
            pair_stable=pair_stable+1 if valid2 else 0
            if stage==1 and pair_stable>=10:stage=2;first=t+1;hist.clear();queue.clear()
            stable=stable+1 if valid3 else 0
            if video and t%2==0:
                frame=env.sim.render(width=640,height=480,camera_name='agentview')[::-1].copy();writer.append_data(frame)
                if t in [0,100,200,400,600,800]:frames.append((t,frame))
            if stable>=50:break
    finally:
        if writer:writer.close()
    a=np.array(rows);np.savez_compressed(folder/f'{mode}_{seed}.npz',trace=a,initial_state=initial,start_state=start_state)
    # Fixed trace schema: time,stage,xyz9,eef3,action7,grasp3,finger3,contacts2,valid2,valid3,vel18.
    second=a[a[:,1]==2];s=second
    r=dict(seed=seed,mode=mode,initial_sha256=initial_hash,first_stack_step=first,success=stable>=50,steps=len(a),second_steps=len(s))
    if len(s):
        p=s[:,2:11].reshape(-1,3,3);delta=p[:,2]-p[:,1];xy=np.linalg.norm(delta[:,:2],axis=1)
        lifted=p[:,2,2]>.88;near=lifted&(xy<.03);aligned=lifted&(xy<.009)
        placed=aligned&(np.abs(delta[:,2]-.04)<.008)&(s[:,28]>0)
        r.update(grasp_c=bool((s[:,23]>0).any()),lift_c=bool(lifted.any()),near_target=bool(near.any()),
            aligned=bool(aligned.any()),contact_at_target=bool(placed.any()),released_at_target=bool((placed&(s[:,26]==0)&(s[:,23]==0)).any()),
            max_c_z=float(p[:,2,2].max()),min_xy_after_lift=float(xy[lifted].min()) if lifted.any() else None,
            lower_geometry_lost=bool(((np.linalg.norm(p[:,1,:2]-p[:,0,:2],axis=1)>.009)|(np.abs(p[:,1,2]-p[:,0,2]-.04)>.008)).any()),
            lower_gripper_contact=bool((s[:,24:26]>0).any()),
            final_c_minus_target=delta[-1].tolist(),final_eef_minus_c=(s[-1,11:14]-p[-1,2]).tolist(),
            last100_action_mean=s[-100:,14:21].mean(0).tolist())
    if video:
        fig,ax=plt.subplots(1,len(frames),figsize=(3*len(frames),3),squeeze=False)
        for axis,(t,img) in zip(ax[0],frames):axis.imshow(img);axis.set_title(f'{t/20:.1f} s');axis.axis('off')
        fig.suptitle(f'{folder.name} / {mode} / Start {seed}');fig.tight_layout();fig.savefig(folder/f'{mode}_{seed}_frames.png',dpi=120);plt.close(fig)
    return r

def main():
    DEST.mkdir(exist_ok=False);torch.set_num_threads(4)
    manifest=dict(cases=CASES,seeds=SEEDS,horizon=1000,prebuilt_settle_steps=40,
        selection='first five pre-existing development seeds, fixed before replay; videos seed61000 for each case and condition',
        caveat='Prebuilt intervention changes object placement, robot/scene history and initial gripper pose versus natural transition; not an isolated causal height effect.',
        trace_columns=['step','stage']+[f'{c}_{k}' for c in 'ABC' for k in 'xyz']+[f'eef_{k}' for k in 'xyz']+[f'action{i}' for i in range(7)]+[f'grasp{c}' for c in 'ABC']+[f'finger{c}' for c in 'ABC']+['contactAB','contactBC','valid2','valid3']+[f'velocity{c}{i}' for c in 'ABC' for i in range(6)])
    manifest['checkpoint_hashes']={f'{case}/{update}':digest(OUT/case/f'update_{update}.pth') for case,update in CASES}
    write(DEST/'protocol.json',manifest);results=[]
    for case,update in CASES:
        folder=DEST/f'{case}_u{update}';folder.mkdir()
        ck=torch.load(OUT/case/f'update_{update}.pth',map_location='cpu',weights_only=False);model=Model().cuda().eval();model.load_state_dict(ck['model'])
        env=env_create()
        try:
            old=json.loads((OUT/case/f'dev3_{update}.json').read_text());old={r['seed']:r for r in old['rows']}
            for mode in ['continuous','prebuilt']:
                for seed in SEEDS:
                    r=episode(env,model,seed,mode,folder,seed==61000);r.update(case=case,update=update)
                    if mode=='continuous':
                        r['replay_matches']=r['initial_sha256']==old[seed]['initial_sha256'] and r['first_stack_step']==old[seed]['first_stack_step'] and r['success']==old[seed]['success']
                        assert r['replay_matches'],r
                    results.append(r);write(DEST/'results.json',results);print(json.dumps(r),flush=True)
        finally:env.close()
    assert manifest['checkpoint_hashes']=={f'{c}/{u}':digest(OUT/c/f'update_{u}.pth') for c,u in CASES}
    write(DEST/'status.json',dict(state='COMPLETED',episodes=len(results),checkpoint_hashes_unchanged=True))

if __name__=='__main__':main()
