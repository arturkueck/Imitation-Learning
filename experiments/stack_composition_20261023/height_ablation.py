"""Physical target-height sweep, paired reset states, no model updates."""
import copy,json,hashlib,random,xml.etree.ElementTree as ET
from collections import deque
import numpy as np
import torch
from run import OUT,ROOT,Model,features,write,robosuite
from task_extensions.environments import StackTwo
from task_extensions.stack_expert import StackExpert
from types import SimpleNamespace

DEST=OUT/'height_ablation'
HEIGHTS=[0,.01,.02,.03,.04]
SEEDS=list(range(61000,61005))
CASES=[('relative_seed1',30000),('relative_seed2',10000),('relative_seed2',30000)]

class HeightStack(StackTwo):
    def _load_model(self):
        super()._load_model()
        body=ET.SubElement(self.model.worldbody,'body',name='height_support',mocap='true',pos='0 0 0.78')
        ET.SubElement(body,'geom',name='height_support_geom',type='box',size='.02 .02 .02',rgba='.4 .4 .4 1',friction='1 .005 .0001')

def env_create():
    kw=copy.deepcopy(json.loads((ROOT/'experiments/additional_tasks/stack_two/task_info.json').read_text())['environment']['env_kwargs'])
    kw.update(has_offscreen_renderer=False,use_camera_obs=False,has_renderer=False,hard_reset=False,horizon=1000)
    return robosuite.make('HeightStack',**kw)

def prepare(env,seed,height):
    mid=env.sim.model.body_mocapid[env.sim.model.body_name2id('height_support')]
    np.random.seed(seed);random.seed(seed);obs=env.reset()
    a=env.sim.data.body_xpos[env.cube_ids[0]].copy()
    env.sim.data.mocap_pos[mid]=[a[0],a[1],env.table_offset[2]-.02]
    env.sim.forward()
    for _ in range(40):obs,_,_,_=env.step(np.array([0,0,0,0,0,0,-1.]))
    # All heights share the exact same settled robot and source state.
    q=env.sim.data.get_joint_qpos(env.cubes[0].joints[0]).copy();q[2]+=height
    env.sim.data.set_joint_qpos(env.cubes[0].joints[0],q)
    env.sim.data.set_joint_qvel(env.cubes[0].joints[0],np.zeros(6))
    env.sim.data.mocap_pos[mid]=[q[0],q[1],env.table_offset[2]+height-.02]
    env.sim.forward();obs=env._get_observations(force_update=True)
    full=env.sim.get_state().flatten().copy()
    # qpos/qvel with target entries removed: strict pairing check across heights.
    qp=env.sim.data.qpos.copy();qv=env.sim.data.qvel.copy()
    ap=env.sim.model.get_joint_qpos_addr(env.cubes[0].joints[0]);av=env.sim.model.get_joint_qvel_addr(env.cubes[0].joints[0])
    paired=np.r_[np.delete(qp,np.arange(*ap)),np.delete(qv,np.arange(*av))]
    p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
    assert abs(p[0,2]-env.table_offset[2]-.02-height)<.001
    assert abs(p[1,2]-env.table_offset[2]-.02)<.001
    assert env.check_contact(env.cubes[0],'height_support_geom') or (height==0)
    return obs,full,hashlib.sha256(paired.tobytes()).hexdigest(),p

def valid(env,height):
    a,b=[env.sim.data.body_xpos[i] for i in env.cube_ids]
    if abs(a[2]-(env.table_offset[2]+height+.02))>.008:return False
    if np.linalg.norm(a[:2]-b[:2])>.009 or abs(b[2]-a[2]-.04)>.008:return False
    if not env.check_contact(env.cubes[0],env.cubes[1]):return False
    if height>0 and not env.check_contact(env.cubes[0],'height_support_geom'):return False
    for c in env.cubes:
        if env._check_grasp(env.robots[0].gripper,c) or env.check_contact(env.robots[0].gripper,c):return False
        v=env.sim.data.get_joint_qvel(c.joints[0])
        if np.linalg.norm(v[:3])>.03 or np.linalg.norm(v[3:])>.3:return False
    return True

@torch.no_grad()
def rollout(env,model,seed,height,folder,expert=False):
    obs,initial,pair_hash,start=prepare(env,seed,height)
    if expert:controller=StackExpert(SimpleNamespace(base_env=env))
    hist=deque(maxlen=2);queue=deque();rows=[];tail=0
    for t in range(1000):
        p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        if expert:action=controller(obs)
        else:
            local={k:obs[k] for k in ['robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']};local['object']=p.flatten()
            hist.append(features(local,'relative'))
            if len(hist)==1:hist.append(hist[0].copy())
            if not queue:queue.extend(model(torch.tensor(np.stack(hist).reshape(1,30),device='cuda'))[0].cpu().numpy()[1:3])
            action=queue.popleft()
        obs,_,_,_=env.step(action)
        p=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids])
        held=env._check_grasp(env.robots[0].gripper,env.cubes[1]);finger=env.check_contact(env.robots[0].gripper,env.cubes[1])
        contact=env.check_contact(*env.cubes);ok=valid(env,height);tail=tail+1 if ok else 0
        rows.append(np.r_[t,p.flatten(),obs['robot0_eef_pos'],action,held,finger,contact,ok,env.sim.data.time])
        if tail>=50:break
    a=np.array(rows);delta=a[:,4:7]-a[:,1:4];xy=np.linalg.norm(delta[:,:2],axis=1);lift=a[:,6]>.88
    placed=(xy<.009)&(np.abs(delta[:,2]-.04)<.008)&(a[:,19]>0)
    r=dict(seed=seed,height_cm=round(height*100),success=tail>=50,steps=len(a),paired_hash=pair_hash,start_positions=start.tolist(),
        grasp=bool((a[:,17]>0).any()),lift=bool(lift.any()),near=bool((lift&(xy<.03)).any()),
        placed=bool(placed.any()),release=bool((placed&(a[:,18]==0)&(a[:,17]==0)).any()),
        min_xy_after_lift=float(xy[lift].min()) if lift.any() else None,
        target_displaced=bool((np.linalg.norm(a[:,1:4]-start[0],axis=1)>.015).any()))
    np.savez_compressed(folder/f'h{round(height*100)}_seed{seed}.npz',trace=a,initial=initial)
    return r

def main():
    DEST.mkdir(exist_ok=False);torch.set_num_threads(4)
    hashes={f'{c}/{u}':hashlib.sha256((OUT/c/f'update_{u}.pth').read_bytes()).hexdigest() for c,u in CASES}
    write(DEST/'protocol.json',dict(heights_cm=[h*100 for h in HEIGHTS],seeds=SEEDS,cases=CASES,horizon=1000,
        checkpoint_hashes=hashes,preparation='40 neutral steps at height0; translate target and kinematic pedestal only; preserve all other qpos/qvel exactly',
        success='50 continuous valid frames, contact, no finger support, low velocity, target on pedestal at specified height',
        limitations='Two dynamic cubes on fixed pedestal. Not a free three-cube tower. Changing height also changes exposed pedestal geometry. Five development starts, no inferential significance claim.',
        trace_columns=['step','Ax','Ay','Az','Bx','By','Bz','eefx','eefy','eefz']+[f'action{i}' for i in range(7)]+['grasp','finger','contact','valid','sim_time']))
    env=env_create();results=[];pairs={};positions={}
    try:
        control=DEST/'expert_control';control.mkdir()
        checks=[]
        for h in [0,.04]:
            r=rollout(env,None,61990,h,control,expert=True);assert r['success'],r;checks.append(r)
        write(DEST/'expert_checks.json',checks)
        for case,u in CASES:
            folder=DEST/f'{case}_u{u}';folder.mkdir()
            model=Model().cuda().eval();model.load_state_dict(torch.load(OUT/case/f'update_{u}.pth',map_location='cpu',weights_only=False)['model'])
            for h in HEIGHTS:
                for seed in SEEDS:
                    r=rollout(env,model,seed,h,folder);r.update(case=case,update=u)
                    assert pairs.setdefault(seed,r['paired_hash'])==r['paired_hash'],'Pairing changed'
                    p=np.array(r['start_positions']);p[0,2]-=h
                    assert np.allclose(positions.setdefault(seed,p),p,atol=1e-12,rtol=0)
                    results.append(r);write(DEST/'results.json',results);print(json.dumps(r),flush=True)
    finally:env.close()
    assert hashes=={f'{c}/{u}':hashlib.sha256((OUT/c/f'update_{u}.pth').read_bytes()).hexdigest() for c,u in CASES}
    write(DEST/'status.json',dict(state='COMPLETED',episodes=len(results),paired_states_exact=True,checkpoint_hashes_unchanged=True))

if __name__=='__main__':main()
