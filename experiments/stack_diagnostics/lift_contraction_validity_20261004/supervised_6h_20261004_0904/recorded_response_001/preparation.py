"""Known Ersatzhistories at exactly recorded qpos/qvel; no historical replay claim."""
import copy,hashlib
import numpy as np
import helpers as h
ARM_DERIVED={'ref_pos','ref_ori_mat','ref_pos_vel','ref_ori_vel','joint_pos','joint_vel','J_pos','J_ori','J_full','mass_matrix','new_update'}
GRIP_DERIVED={'joint_pos','joint_vel','new_update'}
def capture(obj,excluded):
    result={}
    for k,v in vars(obj).items():
        if k in excluded:continue
        try:h.simple(v)
        except TypeError:continue
        result[k]=copy.deepcopy(v)
    return result
def restore(obj,values):
    for k,v in values.items():setattr(obj,k,copy.deepcopy(v))
def serial(values):return {k:h.simple(v) for k,v in values.items()}
def quatangle(a,b):
    a,b=np.array(a),np.array(b)
    return float(2*np.arccos(np.clip(abs(a@b)/(np.linalg.norm(a)*np.linalg.norm(b)),0,1)))
def prepare(env,ctrl,d,t,actions,history,selection):
    robot=env.env.robots[0];sim=env.env.sim;gc=robot.composite_controller.part_controllers['right_gripper']
    assert ctrl.interpolator_pos is None and ctrl.interpolator_ori is None and gc.interpolator is None
    ctrl.update_initial_joints(d['obs/robot0_joint_pos'][0])
    if history=='H_prefix':
        for action in actions[:t]:h.stop_check();env.step(action);h.COUNTS['prefix_actions']+=1
        ctrl.update(force=True)
        arm_history=capture(ctrl,ARM_DERIVED);grip_history=capture(gc,GRIP_DERIVED)
        gripper_memory=capture(robot.gripper['right'],set())
    else:
        assert history=='H_reset'
        arm_history=grip_history=gripper_memory=None
    recorded=d['states'][t];env.reset_to({'states':recorded})
    # Standardize solver/actuator/applied-force state, while retaining recorded qpos/qvel.
    for k in selection['standardized_aux_fields']:getattr(sim.data,k)[:]=0
    assert sim.data.mocap_pos.size==sim.data.mocap_quat.size==0
    ctrl.update(force=True);gc.update(force=True)
    if history=='H_prefix':
        restore(ctrl,arm_history);restore(gc,grip_history);restore(robot.gripper['right'],gripper_memory)
    else:
        ctrl.update_initial_joints(d['obs/robot0_joint_pos'][t])
        ctrl.reset_goal()
        arm_history=capture(ctrl,ARM_DERIVED);grip_history=capture(gc,GRIP_DERIVED)
        gripper_memory=capture(robot.gripper['right'],set())
    for k in selection['standardized_aux_fields']:getattr(sim.data,k)[:]=0
    if hasattr(env.env,'timestep'):env.env.timestep=t
    if hasattr(env.env,'cur_time'):env.env.cur_time=float(sim.data.time)
    if hasattr(env.env,'done'):env.env.done=False
    expected=dict(right=serial(arm_history),right_gripper=serial(grip_history),gripper=serial(gripper_memory))
    actual=dict(right=serial(capture(ctrl,ARM_DERIVED)),right_gripper=serial(capture(gc,GRIP_DERIVED)),gripper=serial(capture(robot.gripper['right'],set())))
    error=h.difference(expected,actual)
    obs=env.get_observation();want={k:d['obs/'+k][t] for k in ['object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos']}
    metrics=dict(eef_position_error_m=float(np.linalg.norm(obs['robot0_eef_pos']-want['robot0_eef_pos'])),
                 object_position_error_m=float(np.linalg.norm(obs['object'][:3]-want['object'][:3])),
                 object_relative_error_m=float(np.linalg.norm(obs['object'][-3:]-want['object'][-3:])),
                 eef_orientation_error_rad=quatangle(obs['robot0_eef_quat'],want['robot0_eef_quat']),
                 object_orientation_error_rad=quatangle(obs['object'][3:7],want['object'][3:7]),
                 gripper_qpos_error=float(np.max(np.abs(obs['robot0_gripper_qpos']-want['robot0_gripper_qpos']))))
    geometry=bool(max(metrics[k] for k in ['eef_position_error_m','object_position_error_m','object_relative_error_m'])<=1e-6
                  and max(metrics[k] for k in ['eef_orientation_error_rad','object_orientation_error_rad'])<=1e-4 and metrics['gripper_qpos_error']<=1e-9)
    roundtrip=float(np.max(np.abs(np.asarray(env.get_state()['states'])-recorded)))
    aux_error=max([float(np.max(np.abs(getattr(sim.data,k)),initial=0)) for k in selection['standardized_aux_fields']]+[0.])
    assert error<=1e-9 and aux_error==0 and roundtrip<=1e-9,'Preparation history or recorded state failed; no mechanism inference'
    return dict(history=history,expected_retained_memory=expected,retained_memory_error=error,standardized_aux_error=aux_error,
                state_roundtrip_error=roundtrip,recorded_state_sha256=hashlib.sha256(recorded.tobytes()).hexdigest(),
                geometry_metrics=metrics,geometry_passed=geometry,
                recorded_observation={k:v.tolist() for k,v in want.items()},
                roles=dict(arm_derived_recomputed=sorted(ARM_DERIVED),gripper_derived_recomputed=sorted(GRIP_DERIVED),interpolators_none=True),
                no_original_history_claim=True)
