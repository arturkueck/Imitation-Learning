"""Smoke-test actual intervention parameters on both project-local tasks."""
import runtime
import json
import numpy as np
from robomimic.utils.env_utils import create_env_for_data_processing
from robustness import CONDITIONS, Intervention, refresh_observation

for task in ['stack_four','cube_handover']:
    info = json.loads((runtime.ROOT/'experiments/baselines/additional_tasks'/task/'task_info.json').read_text())
    for name in CONDITIONS:
        env = create_env_for_data_processing(info['environment'],camera_names=['agentview'],
            camera_height=64,camera_width=64,reward_shaping=False)
        env.reset()
        intervention = Intervention(env,name,123)
        intervention.apply()
        obs = refresh_observation(env)
        changed = intervention.observation(obs)
        audit = intervention.audit
        if 'mass_scale' in intervention.spec:
            assert np.allclose(np.array(audit['mass_after_kg']),
                np.array(audit['mass_before_kg'])*intervention.spec['mass_scale'])
        if 'friction_scale' in intervention.spec:
            assert np.allclose(np.array(audit['friction_after'])[:,0],
                np.array(audit['friction_before'])[:,0]*.5)
        if 'kp_scale' in intervention.spec:
            for gain in audit['controller_gains']:
                assert np.allclose(gain['after'],np.array(gain['before'])*.8)
        if 'camera_shift_m' in intervention.spec:
            assert np.isclose(audit['camera_position_after'][0]-audit['camera_position_before'][0],.02)
        if 'brightness' in intervention.spec:
            assert not np.array_equal(changed['agentview_image'],obs['agentview_image'])
        if 'delay_steps' in intervention.spec:
            altered = {k:v.copy() for k,v in obs.items()}
            altered['robot0_eef_pos'] += .1
            delayed = intervention.observation(altered)
            assert np.array_equal(delayed['robot0_eef_pos'],obs['robot0_eef_pos'])
        action = np.zeros(info['action_dimension']); action[6::7] = -1
        for step in [20,21,25]:
            actual = intervention.action(action,step)
            if name == 'action_impulse_x' and step == 20: assert actual[0] == .5
            if name == 'object_push_x':
                assert env.base_env.sim.data.xfrc_applied[intervention.body_ids[0],0] == (1 if step < 25 else 0)
            env.step(actual); intervention.clear_force()
        assert np.isfinite(env.get_state()['states']).all()
        print('TASK_CONDITION_OK',task,name,flush=True)
        del env
