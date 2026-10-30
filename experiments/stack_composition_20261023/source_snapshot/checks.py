"""Semantic checks before spending the overnight budget."""
import copy, json
from types import SimpleNamespace as NS
import numpy as np
import torch
from run import features,load_data,Model,prefix_valid,make_env,OUT,write
from task_extensions.stack_expert import StackExpert

def main():
    checks={}
    obs=dict(object=np.array([.1,.1,.82,-.1,-.1,.83]),robot0_eef_pos=np.array([0,0,1.1]),robot0_eef_quat=np.array([0,0,0,1]),robot0_gripper_qpos=np.array([.02,-.02]))
    shifted=copy.deepcopy(obs);delta=np.array([.05,-.03,.04]);shifted['object']+=np.tile(delta,2);shifted['robot0_eef_pos']+=delta
    assert np.allclose(features(obs,'relative'),features(shifted,'relative'))
    checks['relative_translation_invariance']=True
    raw=load_data('raw');rel=load_data('relative')
    for split in raw:assert np.array_equal(raw[split][1],rel[split][1])
    checks['identical_action_targets_across_arms']=True
    # Positive and negative success cases: geometry alone must never suffice.
    contacts=True;finger_contact=False;grasp=False;velocity=np.zeros(6)
    cubes=[NS(joints=['a']),NS(joints=['b']),NS(joints=['c'])];gripper=object()
    env=NS(cube_ids=[0,1,2],cubes=cubes,table_offset=np.array([0,0,.8]),robots=[NS(gripper=gripper)],
        sim=NS(data=NS(body_xpos=np.array([[0.,0.,.82],[0.,0.,.86],[0.,0.,.90]]),get_joint_qvel=lambda _:velocity)),
        check_contact=lambda a,b: finger_contact if a is gripper else contacts,_check_grasp=lambda a,b:grasp)
    assert prefix_valid(env,3)
    contacts=False;assert not prefix_valid(env,3);contacts=True
    finger_contact=True;assert not prefix_valid(env,3);finger_contact=False
    velocity=np.array([.04,0,0,0,0,0]);assert not prefix_valid(env,3);velocity=np.zeros(6)
    env.sim.data.body_xpos[2,0]=.02;assert not prefix_valid(env,3)
    checks['success_rejects_no_contact_finger_support_motion_and_bad_geometry']=True
    # Exact paired reset states, independent of preceding episode length.
    env=make_env(3)
    try:
        np.random.seed(61999);env.reset();first=env.sim.get_state().flatten().copy()
        for _ in range(7):env.step(np.array([0,0,0,0,0,0,-1]))
        np.random.seed(61999);env.reset();second=env.sim.get_state().flatten().copy()
        assert np.array_equal(first,second),np.max(abs(first-second))
    finally:env.close()
    checks['paired_resets_exact']=True
    oracle={}
    for count in [2,3]:
        env=make_env(count);successes=[]
        try:
            for seed in [61990,61991,61992]:
                np.random.seed(seed);obs=env.reset();expert=StackExpert(NS(base_env=env));tail=0
                for _ in range(1000):
                    obs,_,_,_=env.step(expert(obs));tail=tail+1 if prefix_valid(env,count) else 0
                    if tail>=50:break
                successes.append(tail>=50)
        finally:env.close()
        oracle[str(count)]=successes
        assert any(successes),('No oracle positive control',count)
    checks['scripted_expert_positive_controls_no_training_data']=oracle
    # Serialization reproduces the next optimizer step, not just predictions.
    torch.set_num_threads(4);torch.manual_seed(123)
    model=Model();opt=torch.optim.AdamW(model.parameters(),lr=1e-4)
    x=torch.tensor(rel['train'][0][:8]);y=torch.tensor(rel['train'][1][:8])
    def step(m,o):
        o.zero_grad();loss=(m(x)-y).square().mean();loss.backward();o.step()
    step(model,opt);snapshot=copy.deepcopy(dict(model=model.state_dict(),optimizer=opt.state_dict()))
    restored=Model();restored.load_state_dict(snapshot['model']);restored_opt=torch.optim.AdamW(restored.parameters(),lr=1e-4);restored_opt.load_state_dict(snapshot['optimizer'])
    step(model,opt);step(restored,restored_opt)
    assert all(torch.equal(a,b) for a,b in zip(model.parameters(),restored.parameters()))
    checks['restored_optimizer_next_step_exact_cpu']=True
    write(OUT/'checks.json',checks);print(json.dumps(checks,indent=2))

if __name__=='__main__':main()
