"""No training. Native C baseline + preregistered phase-start continuations.

The runner does not launch gripper/horizon/training experiments automatically.
"""
import argparse, csv, hashlib, json, random, sys, time, traceback
from collections import deque
from pathlib import Path
from types import SimpleNamespace
import h5py, numpy as np, torch

ROOT=Path(__file__).resolve().parents[2];OUT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'experiments/stack_normalization_20261001/scripts'))
from common import KEYS, DATA, Normalizer, checkpoint, demos, digest, DirectChunk, flatten
from robomimic.utils.file_utils import load_dict_from_checkpoint,policy_from_checkpoint,env_from_checkpoint,config_from_checkpoint
from robomimic.utils import obs_utils
from task_extensions.stack_expert import StackExpert
from robustness import Intervention,refresh_observation
import video_views

class DirectPolicy:
    def __init__(self,path,norm):
        ck=torch.load(path,map_location='cpu',weights_only=False)
        assert ck['normalization_stats']==json.loads((ROOT/'experiments/stack_normalization_20261001/normalization_stats.json').read_text())
        self.model=DirectChunk().cuda().eval();self.model.load_state_dict(ck['ema'])
        self.norm=norm;self.queue=deque()
    def start_episode(self):self.queue.clear()
    def __call__(self,ob):
        if not self.queue:
            x=torch.tensor(flatten(self.norm.observations(ob)),device='cuda')
            chunk=self.model(x)[0].detach().cpu().numpy()
            raw=self.norm.inverse_actions(chunk);self.norm.check_actions(raw)
            assert abs(self.norm.actions(raw)-chunk).max()<1e-6
            self.queue.extend(raw[1:3])
        return self.queue.popleft()

def write(p,obj):
    p=Path(p);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(obj,indent=2,allow_nan=False),encoding='utf-8');tmp.replace(p)

def seed(s):
    random.seed(s);np.random.seed(s);torch.manual_seed(s)

def expert_memory(d,k,raw):
    """Reconstruct hidden FSM using saved observations, then attach it to live sim."""
    fake=SimpleNamespace(cubes=[0,1],cube_ids=[0,1],sim=SimpleNamespace(data=SimpleNamespace(body_xpos=None)))
    expert=StackExpert(SimpleNamespace(base_env=fake))
    for i in range(k):
        fake.sim.data.body_xpos=d['obs']['object'][i].reshape(2,3)
        a=expert({'robot0_eef_pos':d['obs']['robot0_eef_pos'][i]})
        assert abs(a-d['actions'][i]).max()<1e-6
    assert expert.phase==int(d['phase'][k]);expert.raw=raw
    return expert

def anchors(d):
    phase=d['phase'];first=lambda ph:int(np.flatnonzero(phase==ph)[0]);transport=np.flatnonzero(phase==4)
    return dict(A_after_grasp=first(3),B_after_lift=first(4),C_mid_transport=int(transport[len(transport)//2]),D_end_transport=int(transport[-1]),E_before_lowering=first(5),F_before_release=first(6))

def restore(env,f,d,k,s):
    """Replay controller/gripper memory, then restore the exact recorded physical state."""
    seed(s);group=f['data'][d['name']]
    initial={'model':group.attrs['model_file'],'states':group['states'][0]}
    if 'ep_meta' in group.attrs:initial['ep_meta']=group.attrs['ep_meta']
    ob=env.reset_to(initial)
    for a in d['actions'][:k]:ob,_,_,_=env.step(a)
    prefix_errors={key:float(abs(np.asarray(ob[key])[-1]-d['obs'][key][k]).max()) for key in KEYS}
    # Pure replay can drift millimeters. Do not quietly relax the precision criterion.
    ob=env.reset_to({'states':group['states'][k]})
    raw=env.base_env
    controller=raw.robots[0].part_controllers['right'];controller.update(force=True);controller.reset_goal(goal_update_mode='achieved')
    # The original native observation buffers can lag the physical simulator by a microstep.
    # Check geometry before installing the exact recorded two-frame policy history.
    ob=refresh_observation(env)
    errors={key:float(abs(np.asarray(ob[key])[-1]-d['obs'][key][k]).max()) for key in KEYS}
    position_error=max(errors['object'],errors['robot0_eef_pos'])
    assert position_error<.002,('Invalid Expert replay position',d['name'],k,errors)
    assert errors['robot0_gripper_qpos']<.002,('Invalid Expert replay fingers',errors)
    held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]))
    assert held,('Invalid phase start, no grasp',d['name'],k)
    live_state=env.get_state()['states'].copy()
    assert np.array_equal(live_state,group['states'][k]),'Physical restore differs from recorded state'
    for key in KEYS:
        env.obs_history[key]=deque([d['obs'][key][max(0,k-1)][None].copy(),d['obs'][key][k][None].copy()],maxlen=2)
    ob=env._get_stacked_obs_from_history()
    return ob,dict(saved_state_sha256=hashlib.sha256(group['states'][k].tobytes()).hexdigest(),replayed_state_sha256=hashlib.sha256(live_state.tobytes()).hexdigest(),pure_prefix_observation_errors=prefix_errors,restore_observation_errors=errors,initial_grasp=held,exact_saved_physical_state=True,initial_history='exact stored t-1,t; next observations live'),live_state

def make_policy(kind,ck,norm):
    if kind=='expert':return None,[]
    if kind=='direct':return DirectPolicy(checkpoint('C','direct',1),norm),[]
    p,_=policy_from_checkpoint(ckpt_dict=ck)
    for k in KEYS:
        for s in ('offset','scale'):assert np.array_equal(p.obs_normalization_stats[k][s],norm.obs[k][s])
    assert np.array_equal(p.action_normalization_stats['actions']['offset'],np.zeros((1,7),np.float32))
    assert np.array_equal(p.action_normalization_stats['actions']['scale'],np.ones((1,7),np.float32))
    chunks=[];old=p.policy.noise_scheduler.step
    def record(*args,**kwargs):
        result=old(*args,**kwargs)
        timestep=kwargs.get('timestep',args[1] if len(args)>1 else None)
        if int(timestep)==0:chunks.append(result.prev_sample.detach().cpu().numpy()[0].copy())
        return result
    p.policy.noise_scheduler.step=record
    return p,chunks

def geometries(t):
    delta=t[:,4:7]-t[:,1:4];xy=np.linalg.norm(delta[:,:2],axis=1);held=t[:,34]>0
    position=(xy<.009)&(delta[:,2]>.032)
    lower=position&(abs(delta[:,2]-.04)<.008)
    return dict(grasp=held,retained_lift=held&(t[:,6]>.88),position=position,lower=lower,release=lower&~held&(t[:,35]>0))

def run_episode(env,policy,chunks,kind,norm,ob,horizon,initial_state):
    raw=env.base_env;trace=[];states=[];observations={k:[] for k in KEYS};measured=None;tail=0;success=False
    initial_pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);init_delta=initial_pos[1]-initial_pos[0]
    initial=dict(xy_m=float(np.linalg.norm(init_delta[:2])),relative_height_m=float(init_delta[2]),position=bool(np.linalg.norm(init_delta[:2])<.009 and init_delta[2]>.032),lower=bool(np.linalg.norm(init_delta[:2])<.009 and abs(init_delta[2]-.04)<.008))
    chunk_steps=[]
    for step in range(horizon+40):
        po={k:np.asarray(ob[k]) for k in KEYS}
        for k in KEYS:observations[k].append(po[k].copy())
        count=len(chunks)
        with torch.no_grad():
            if kind=='expert':action=np.asarray(policy({'robot0_eef_pos':po['robot0_eef_pos'][-1]}))
            else:
                if kind=='diffusion' and step==0:
                    actual=policy._prepare_observation(po);expected=norm.observations(po)
                    assert max(float(abs(actual[k][0].cpu().numpy()-expected[k]).max()) for k in KEYS)<1e-6
                action=np.asarray(policy(ob=po)).copy()
        norm.check_actions(action)
        if len(chunks)>count:chunk_steps.append(step)
        if kind=='diffusion':
            # C has identity action inversion; compare executed command with the full sampled chunk.
            ci=step-chunk_steps[-1]+1
            assert np.array_equal(action,chunks[-1][ci]),'Sampler slice/queue/inversion mismatch'
        ob,_,done,_=env.step(action)
        pos=np.array([raw.sim.data.body_xpos[i].copy() for i in raw.cube_ids]);quat=np.array([raw.sim.data.body_xquat[i].copy() for i in raw.cube_ids])
        held=bool(raw._check_grasp(raw.robots[0].gripper,raw.cubes[1]));ok=bool(env.is_success()['task'])
        trace.append(np.r_[step,pos.ravel(),quat.ravel(),np.asarray(ob['robot0_eef_pos'])[-1],np.asarray(ob['robot0_gripper_qpos'])[-1],action,action,held,raw.check_contact(*raw.cubes),ok]);states.append(env.get_state()['states'].copy())
        if measured is None and (ok or done or step==horizon-1):measured=step+1;success=ok
        elif measured is not None:
            tail+=1
            if tail==40:break
    t=np.array(trace);assert np.isfinite(t).all();a=t[:measured];geom=geometries(a)
    from dynamics_common import extra_metrics
    result=dict(measured_steps=measured,**extra_metrics(t,measured),initial_geometry=initial,
        phase_conditioned_stages={k:bool(v.any()) for k,v in geom.items()},
        position_held=bool((geom['position']&geom['grasp']).any()),lower_held=bool((geom['lower']&geom['grasp']).any()),
        held_fraction=float(geom['grasp'].mean()),first_grasp_loss=next((i for i in range(1,len(a)) if a[i-1,34]>0 and a[i,34]==0),None),
        sustained_success=bool(success and tail==40 and np.all(t[measured:,36]>0) and not t[measured:,34].any() and np.all(t[measured:,35]>0)),
        max_rotation_command_norm=float(np.linalg.norm(a[:,23:26],axis=1).max()),gripper_sign_switches=int(((a[1:,26]>0)!=(a[:-1,26]>0)).sum()))
    result.update({f'phase_{k}':bool(v.any()) for k,v in geom.items()})
    # Goal direction uses the PRE-action EEF/goal, unlike the legacy post-action trace diagnostic.
    eo=np.asarray(observations['robot0_eef_pos'])[:measured,-1,:2]
    go=np.asarray(observations['object'])[:measured,-1,:2];vec=go-eo
    mag=np.linalg.norm(a[:,20:22],axis=1);dist=np.linalg.norm(vec,axis=1)
    mask=(mag>.01)&(dist>.002)
    cos=(a[:,20:22]*vec).sum(1)/np.maximum(mag*dist,1e-9)
    result.update(xy_action_norm_mean=float(mag.mean()),pre_action_goal_cosine_mean=float(cos[mask].mean()) if mask.any() else None,pre_action_goal_cosine_frames=int(mask.sum()))
    arrays=dict(trace=t,states=np.asarray(states),initial_state=initial_state,measured=measured,chunks=np.asarray(chunks),chunk_start_steps=np.asarray(chunk_steps),**{k:np.asarray(v) for k,v in observations.items()})
    return result,arrays

def prepare():
    assert not (OUT/'protocol.json').exists(),'Refusing overwrite'
    cfg=json.loads((ROOT/'experiments/stack_normalization_20261001/C/diffusion/seed_1/config.json').read_text())
    ds=sorted([d for d in demos() if d['split']=='valid'],key=lambda d:int(d['name'].split('_')[-1]))[:5]
    cp=checkpoint('C','diffusion',1)
    protocol=dict(training=False,training_seed=1,checkpoint=str(cp),checkpoint_sha256=digest(cp),direct_checkpoint_sha256=digest(checkpoint('C','direct',1)),dataset=str(DATA),dataset_sha256=digest(DATA),normalization='C, frozen train stats, no action normalization',prediction_horizon=16,observation_horizon=2,checkpoint_action_horizon=8,effective_execute_horizon=2,ddim_steps=10,prediction_type='epsilon',ema=True,baseline_seeds=list(range(46000,46040)),baseline_horizon=500,phase_horizon=120,tail_steps=40,phase_anchor_rule='first 5 validation demos sorted by numeric suffix; predefined 6 anchors',phase_anchors=[dict(demo=d['name'],anchors=anchors(d)) for d in ds],phase_models=['expert','direct','diffusion'],phase_seed_rule='91000+demo suffix, reset after replay and before inference for all models',restore='original XML/state[0], replay stored expert prefix, consistent live 2-frame history; position/finger max error <2mm; initial grasp required',expert_control_required=True,automatic_followup=False)
    write(OUT/'protocol.json',protocol);write(OUT/'policy_config_original.json',cfg)
    cfg['algo']['horizon']['action_horizon']=2;write(OUT/'policy_config_effective.json',cfg)
    print(json.dumps(protocol,indent=2))

def execute(stage):
    protocol=json.loads((OUT/'protocol.json').read_text());norm=Normalizer('C')
    assert digest(DATA)==protocol['dataset_sha256'];assert digest(protocol['checkpoint'])==protocol['checkpoint_sha256']
    torch.set_num_threads(4);ck=load_dict_from_checkpoint(ckpt_path=protocol['checkpoint'])
    cfg=json.loads(ck['config']);assert cfg['algo']['ddim']['prediction_type']=='epsilon' and cfg['algo']['ddim']['num_inference_timesteps']==10
    cfg['algo']['horizon']['action_horizon']=2;ck['config']=json.dumps(cfg)
    native_config,_=config_from_checkpoint(ckpt_dict=ck);obs_utils.initialize_obs_utils_with_config(native_config)
    env,_=env_from_checkpoint(ckpt_dict=ck,render=False,render_offscreen=True)
    torch.backends.cuda.matmul.allow_tf32=False
    try:
        if stage=='baseline':
            dest=OUT/'experiment_0_baseline';dest.mkdir(exist_ok=False);policy,chunks=make_policy('diffusion',ck,norm);rows=[]
            original=json.loads((ROOT/'experiments/stack_replication_20261001/protocol.json').read_text())
            for s in protocol['baseline_seeds']:
                seed(s);policy.start_episode();chunks.clear();ob=env.reset();ob=env.reset_to(env.get_state());inter=Intervention(env,'nominal',s);inter.apply();ob=refresh_observation(env)
                assert inter.initial_state_hash==original['fixed_start_hashes'][str(s)]
                video_views.setup_cameras(env)
                r,z=run_episode(env,policy,chunks,'diffusion',norm,ob,500,env.get_state()['states'].copy());r.update(model='diffusion',seed=s,initial_state_sha256=inter.initial_state_hash)
                np.savez_compressed(dest/f'{s}.npz',**z);rows.append(r);write(dest/'results.json',rows)
                print(json.dumps(dict(stage=stage,completed=len(rows),total=40,stacks=sum(x['sustained_success'] for x in rows))),flush=True)
        else:
            dest=OUT/('preflight_v3' if stage=='smoke' else 'anchor_preflight_v3' if stage=='validate_anchors' else 'experiment_1_phases');dest.mkdir(exist_ok=False);rows=[]
            models={} if stage=='validate_anchors' else {kind:make_policy(kind,ck,norm) for kind in ('direct','diffusion')}
            byname={d['name']:d for d in demos()};panel=protocol['phase_anchors'][:1] if stage=='smoke' else protocol['phase_anchors']
            with h5py.File(DATA,'r') as f:
                for item in panel:
                    d=byname[item['demo']]
                    selected={'F_before_release':item['anchors']['F_before_release']} if stage=='smoke' else item['anchors']
                    for label,k in selected.items():
                        expected_hash=None
                        for kind in (('expert',) if stage=='validate_anchors' else ('expert','direct','diffusion')):
                            s=91000+int(d['name'].split('_')[-1]);ob,meta,initial=restore(env,f,d,k,s)
                            if expected_hash is None:expected_hash=meta['replayed_state_sha256']
                            assert expected_hash==meta['replayed_state_sha256'],'Unpaired phase start'
                            if kind=='expert':policy=expert_memory(d,k,env.base_env);chunks=[]
                            else:
                                policy,chunks=models[kind];policy.start_episode();chunks.clear()
                            seed(s)
                            r,z=run_episode(env,policy,chunks,kind,norm,ob,120 if stage!='smoke' or kind=='expert' else 2,initial)
                            r.update(model=kind,demo=d['name'],phase=label,expert_frame=k,seed=s,**meta)
                            expert_mag=float(np.linalg.norm(d['actions'][k,:2]));r['first_action_xy_over_expert']=float(np.linalg.norm(z['trace'][0,20:22])/expert_mag) if expert_mag>.1 else None
                            r['first_action_xy_over_expert_reference']='stored Expert action at the same anchor; undefined if Expert XY norm <=0.1'
                            np.savez_compressed(dest/f"{d['name']}_{label}_{kind}.npz",**z);rows.append(r);write(dest/'results.json',rows)
                            if kind=='expert':assert r['sustained_success'],'Expert restore/continuation control failed; phase evidence invalid'
                            print(json.dumps(dict(stage=stage,model=kind,demo=d['name'],phase=label,stable=r['sustained_success'],completed=len(rows))),flush=True)
        write(dest/'complete.json',dict(completed=True,episodes=len(rows),stage=stage))
        fieldnames=['model','seed','demo','phase','expert_frame','sustained_success','grasp','lift','transport_started','phase_retained_lift','phase_position','phase_lower','phase_release','position_held','lower_held','held_fraction','gripper_sign_switches','max_cube_height_m','xy_action_norm_mean','pre_action_goal_cosine_mean','first_action_xy_over_expert']
        with (dest/'results.csv').open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=fieldnames,extrasaction='ignore');w.writeheader();w.writerows(rows)
    finally:env.base_env.close()

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('stage',choices=['prepare','smoke','validate_anchors','baseline','phases']);arg=p.parse_args()
    try:
        if arg.stage=='prepare':prepare()
        else:execute(arg.stage)
    except Exception:
        write(OUT/f'{arg.stage}_failed.json',dict(stage=arg.stage,cause=traceback.format_exc()));raise
