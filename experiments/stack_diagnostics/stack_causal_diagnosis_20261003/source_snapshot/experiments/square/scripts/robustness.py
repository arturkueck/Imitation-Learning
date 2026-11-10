"""Single-factor interventions; audit actual parameters and perturbation events."""
import hashlib
from collections import deque
import mujoco
import numpy as np

CONDITIONS = {
    'nominal': {},
    'action_impulse_x': {'action_impulse':.5,'at_step':20},
    'object_push_x': {'force_newtons':1.,'at_step':20,'duration_steps':5},
    'mass_150pct': {'mass_scale':1.5},
    'mass_70pct': {'mass_scale':.7},
    'friction_50pct': {'friction_scale':.5},
    'controller_gain_80pct': {'kp_scale':.8},
    'proprio_noise_5mm': {'position_noise_std_m':.005},
    'observation_delay_2steps': {'delay_steps':2},
    'image_dark_50pct': {'brightness':.5},
    'image_occlusion_25pct_width': {'occlusion_width_fraction':.25},
    'camera_shift_x_2cm': {'camera_shift_m':.02},
}

def refresh_observation(env):
    from robomimic.envs.wrappers import FrameStackWrapper
    if isinstance(env, FrameStackWrapper):
        obs = env.env.get_observation()
        env.update_obs(obs,reset=True)
        env.obs_history = env._get_initial_obs_history(obs)
        return env._get_stacked_obs_from_history()
    return env.get_observation()

class Intervention:
    def __init__(self, env, name, seed):
        self.raw = env.base_env
        self.sim = self.raw.sim
        self.spec = CONDITIONS[name]
        self.rng = np.random.default_rng(seed+100000)
        self.history = deque(maxlen=self.spec.get('delay_steps',0)+1)
        self.events = []
        if hasattr(self.raw,'cubes'): objects = self.raw.cubes
        elif hasattr(self.raw,'cube'): objects = [self.raw.cube]
        elif hasattr(self.raw,'nuts'): objects = [self.raw.nuts[getattr(self.raw,'nut_id',0)]]
        else: raise ValueError('No supported manipulation object')
        self.body_ids = sorted({self.sim.model.body_name2id(o.root_body) for o in objects})
        self.geom_ids = sorted({self.sim.model.geom_name2id(g) for o in objects for g in o.contact_geoms})
        self.initial_state_hash = hashlib.sha256(np.asarray(env.get_state()['states'],dtype='<f8').tobytes()).hexdigest()
        self.audit = {'parameters':self.spec,'object_body_ids':self.body_ids,
            'initial_state_sha256':self.initial_state_hash,'events':self.events}

    def apply(self):
        model = self.sim.model
        if 'mass_scale' in self.spec:
            state = self.sim.get_state()
            before = model.body_mass[self.body_ids].copy()
            assert (before > 0).all()
            model.body_mass[self.body_ids] *= self.spec['mass_scale']
            model.body_inertia[self.body_ids] *= self.spec['mass_scale']
            mujoco.mj_setConst(model._model,self.sim.data._data)
            self.sim.set_state(state)
            self.audit['mass_before_kg'] = before.tolist()
            self.audit['mass_after_kg'] = model.body_mass[self.body_ids].tolist()
        if 'friction_scale' in self.spec:
            before = model.geom_friction[self.geom_ids].copy()
            model.geom_friction[self.geom_ids,0] *= self.spec['friction_scale']
            self.audit['friction_before'] = before.tolist()
            self.audit['friction_after'] = model.geom_friction[self.geom_ids].tolist()
        if 'kp_scale' in self.spec:
            gains = []
            for robot in self.raw.robots:
                for arm in robot.arms:
                    ctrl = robot.composite_controller.part_controllers[arm]
                    before = ctrl.kp.copy()
                    ctrl.kp *= self.spec['kp_scale']; ctrl.kd *= np.sqrt(self.spec['kp_scale'])
                    gains.append({'before':before.tolist(),'after':ctrl.kp.tolist()})
            self.audit['controller_gains'] = gains
        if 'camera_shift_m' in self.spec:
            index = model.camera_name2id('agentview')
            self.audit['camera_position_before'] = model.cam_pos[index].tolist()
            model.cam_pos[index,0] += self.spec['camera_shift_m']
            self.audit['camera_position_after'] = model.cam_pos[index].tolist()
        self.sim.forward()
        after_hash = hashlib.sha256(np.asarray(self.sim.get_state().flatten(),dtype='<f8').tobytes()).hexdigest()
        self.audit['state_sha256_after_static_intervention'] = after_hash
        assert after_hash == self.initial_state_hash, 'Static intervention changed the initial simulator state'

    def observation(self, obs):
        copy = {k:np.array(v,copy=True) for k,v in obs.items()}
        for key,value in copy.items():
            if key.endswith('eef_pos') and 'position_noise_std_m' in self.spec:
                value += self.rng.normal(0,self.spec['position_noise_std_m'],value.shape)
            if key.endswith('_image'):
                if 'brightness' in self.spec:
                    copy[key] = (value.astype(float)*self.spec['brightness']).clip(0,255).astype(value.dtype)
                if 'occlusion_width_fraction' in self.spec:
                    width = value.shape[-2]; height = value.shape[-3]
                    patch = int(width*self.spec['occlusion_width_fraction'])
                    copy[key][...,height//2-patch//2:height//2+patch//2,
                              width//2-patch//2:width//2+patch//2,:] = 0
        self.history.append(copy)
        return self.history[0]

    def action(self, action, step):
        action = np.array(action,copy=True)
        if 'action_impulse' in self.spec and step == self.spec['at_step']:
            before = float(action[0]); action[0] = np.clip(action[0]+self.spec['action_impulse'],-1,1)
            self.events.append({'step':step,'type':'action_impulse','before':before,'after':float(action[0])})
        self.clear_force()
        if 'force_newtons' in self.spec:
            start = self.spec['at_step']; end = start+self.spec['duration_steps']
            if start <= step < end:
                self.sim.data.xfrc_applied[self.body_ids[0],0] = self.spec['force_newtons']
                self.events.append({'step':step,'type':'object_push','force_N':self.spec['force_newtons']})
        return action

    def clear_force(self):
        self.sim.data.xfrc_applied[self.body_ids,:] = 0
