"""Trusted-local runtime snapshots including MuJoCo integration/controller state.

Pickles must only be loaded from this experiment's generated, hash-verified files.
No model weights, simulator objects, callbacks or arbitrary external objects are
serialized. Controller/interpolator objects retain identity on restoration.
"""
import copy, hashlib, pickle, random
from pathlib import Path
import numpy as np
import mujoco

SKIP={'sim','model','robot_model','_sensor','_corrupter','_filter','_delayer',
      '_xml_processors','viewer','renderer','part_controllers','grippers','gripper'}

def encode(value):
    if value is None or isinstance(value,(str,int,float,bool,np.generic)):return ('value',copy.deepcopy(value))
    if isinstance(value,np.ndarray):return ('value',value.copy())
    if isinstance(value,dict):return ('dict',{k:encode(v) for k,v in value.items() if not callable(v)})
    if isinstance(value,(list,tuple)):return ('seq',type(value).__name__,[encode(v) for v in value])
    if hasattr(value,'__dict__'):
        return ('object',{k:encode(v) for k,v in value.__dict__.items() if k not in SKIP and not callable(v)})
    raise TypeError(f'Unsupported runtime state {type(value)}')

def decode(node,current=None):
    if node[0]=='value':return copy.deepcopy(node[1])
    if node[0]=='dict':
        old={} if current is None else current
        return {k:decode(v,old.get(k)) for k,v in node[1].items()}
    if node[0]=='seq':
        old=[] if current is None else current
        vals=[decode(v,old[i] if i<len(old) else None) for i,v in enumerate(node[2])]
        return tuple(vals) if node[1]=='tuple' else vals
    if node[0]=='object':
        assert current is not None,'runtime topology mismatch'
        for k,v in node[1].items():setattr(current,k,decode(v,getattr(current,k,None)))
        return current
    raise ValueError('snapshot node')

def xml_sha(env):return hashlib.sha256(env.model.get_xml().encode()).hexdigest()

def capture(env,seq,obs):
    spec=mujoco.mjtState.mjSTATE_INTEGRATION
    state=np.empty(mujoco.mj_stateSize(env.sim.model._model,spec))
    mujoco.mj_getState(env.sim.model._model,env.sim.data._data,state,spec)
    envnames=['cur_time','timestep','done','stable_steps','_obs_cache','_observables']
    robots=[]
    for robot in env.robots:
        runtime={k:encode(v) for k,v in robot.__dict__.items()
                 if k.startswith('recent_') or k=='torques'}
        controllers={k:encode(v) for k,v in robot.part_controllers.items()}
        composite={k:encode(v) for k,v in robot.composite_controller.__dict__.items()
                   if k=='_applied_action_dict'}
        grippers={k:encode({name:value for name,value in g.__dict__.items()
                            if name in ('current_action','_current_action')}) for k,g in robot.gripper.items()}
        robots.append(dict(runtime=runtime,controllers=controllers,composite=composite,grippers=grippers))
    return dict(schema='full_runtime_v1',xml_sha256=xml_sha(env),integration=state,
        env={k:encode(getattr(env,k)) for k in envnames if hasattr(env,k)},robots=robots,
        seq=dict(count=seq.count,stage=seq.stage,pair=seq.pair,retreat=seq.retreat,phase=seq.policy.phase,
                 threshold=seq.policy.threshold,steps=seq.policy.steps,anchor=copy.deepcopy(seq.policy.anchor)),
        obs=copy.deepcopy(obs),numpy_rng=np.random.get_state(),python_rng=random.getstate(),
        env_rng=copy.deepcopy(env.rng.bit_generator.state))

def restore(env,seq,snapshot):
    assert snapshot['schema']=='full_runtime_v1' and snapshot['xml_sha256']==xml_sha(env),'snapshot model/schema mismatch'
    mujoco.mj_setState(env.sim.model._model,env.sim.data._data,snapshot['integration'],mujoco.mjtState.mjSTATE_INTEGRATION)
    env.sim.forward()
    for k,node in snapshot['env'].items():setattr(env,k,decode(node,getattr(env,k,None)))
    for robot,saved in zip(env.robots,snapshot['robots']):
        for k,node in saved['runtime'].items():setattr(robot,k,decode(node,getattr(robot,k,None)))
        for k,node in saved['controllers'].items():decode(node,robot.part_controllers[k])
        for k,node in saved['composite'].items():setattr(robot.composite_controller,k,decode(node,getattr(robot.composite_controller,k,None)))
        for k,node in saved['grippers'].items():
            values=decode(node)
            for field,value in values.items():setattr(robot.gripper[k],field,value)
    saved=snapshot['seq'];assert seq.count==saved.get('count',seq.count),'sequencer count mismatch'
    seq.stage=saved['stage'];seq.pair=saved['pair'];seq.retreat=saved['retreat']
    seq.policy.threshold=saved.get('threshold',.8)
    seq.policy.phase=saved['phase'];seq.policy.steps=saved['steps'];seq.policy.anchor=copy.deepcopy(saved['anchor'])
    np.random.set_state(snapshot['numpy_rng']);random.setstate(snapshot['python_rng'])
    env.rng.bit_generator.state=copy.deepcopy(snapshot['env_rng'])
    return copy.deepcopy(snapshot['obs'])

def save(path,snapshot):
    path=Path(path);assert not path.exists(),'snapshot immutable'
    raw=pickle.dumps(snapshot,protocol=5);path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()

def load(path,expected_sha256):
    raw=Path(path).read_bytes();assert hashlib.sha256(raw).hexdigest()==expected_sha256,'snapshot hash'
    return pickle.loads(raw)

def identity_probe(env,seq,obs):
    """Identical first action and synchronized next integration/obs state."""
    initial=capture(env,seq,obs)
    def step(obs):
        positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]);stage=seq.stage
        action,phase,prob=seq.policy.action(obs,positions[stage-1],positions[stage])
        env.step(action);env.sim.forward();nxt=env._get_observations(force_update=True)
        return action,nxt,capture(env,seq,nxt)['integration']
    action1,obs1,state1=step(obs);restored=restore(env,seq,initial)
    action2,obs2,state2=step(restored)
    action_error=float(np.max(np.abs(action1-action2)));state_error=float(np.max(np.abs(state1-state2)))
    obs_error=max(float(np.max(np.abs(obs1[k]-obs2[k]))) for k in obs1 if isinstance(obs1[k],np.ndarray))
    assert action_error==0 and state_error<1e-10 and obs_error<1e-10,('identity',action_error,state_error,obs_error)
    restore(env,seq,initial)
    return dict(action_max_error=action_error,next_integration_max_error=state_error,next_observation_max_error=obs_error)

def episode_identity_probe(env,seq,snapshot,arrays,frame):
    """Replay a saved action from its actual teacher trajectory, even in a new env."""
    obs=restore(env,seq,snapshot)
    positions=np.array([env.sim.data.body_xpos[i].copy() for i in env.cube_ids]);stage=seq.stage
    action,_,_=seq.policy.action(obs,positions[stage-1],positions[stage])
    action_error=float(np.max(np.abs(action-arrays['a'][frame])))
    env.step(action);env.sim.forward();next_obs=env._get_observations(force_update=True)
    positions=np.array([env.sim.data.body_xpos[i] for i in env.cube_ids]).flatten()
    obs_vector=np.r_[positions,next_obs['robot0_eef_pos'],next_obs['robot0_eef_quat'],next_obs['robot0_gripper_qpos']]
    obs_error=float(np.max(np.abs(obs_vector-arrays['post_obs'][frame])))
    state_error=float(np.max(np.abs(env.sim.get_state().flatten()-arrays['post_state'][frame])))
    restore(env,seq,snapshot)
    assert action_error==0 and obs_error<1e-10 and state_error<1e-10,('episode replay',action_error,obs_error,state_error)
    return dict(teacher_action_max_error=action_error,saved_next_observation_max_error=obs_error,saved_next_state_max_error=state_error)
