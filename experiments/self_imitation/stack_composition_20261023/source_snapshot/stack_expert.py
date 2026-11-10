"""Candidate state-based demonstration controller. Accept demos only on success."""
import numpy as np

class StackExpert:
    def __init__(self, env):
        self.raw = env.base_env
        self.cube_index = 1
        self.phase = 0
        self.phase_steps = 0
        self.target = None

    def __call__(self, observation):
        raw = self.raw
        pos = np.array(observation['robot0_eef_pos'])
        if self.cube_index >= len(raw.cubes):
            return np.r_[np.zeros(6),-1.]
        cube = raw.sim.data.body_xpos[raw.cube_ids[self.cube_index]].copy()
        base = raw.sim.data.body_xpos[raw.cube_ids[0]].copy()
        if self.target is None:
            targets = [cube+[0,0,.14],cube+[0,0,.003],cube+[0,0,.003],
                cube+[0,0,.24],base+[0,0,.04*self.cube_index+.15],
                base+[0,0,.04*self.cube_index+.002],
                base+[0,0,.04*self.cube_index+.002],
                base+[0,0,.04*self.cube_index+.15]]
            self.target = targets[self.phase]
        grip = 1. if self.phase in (2,3,4,5) else -1.
        action = np.r_[np.clip(.6*(self.target-pos)/.05,-1,1),np.zeros(3),grip]
        self.phase_steps += 1
        reached = np.linalg.norm(self.target-pos) < .006
        ready = self.phase_steps >= 20 if self.phase in (2,6) else reached and self.phase_steps >= 5
        if ready:
            self.phase += 1; self.phase_steps = 0; self.target = None
            if self.phase == 8:
                self.cube_index += 1; self.phase = 0
        return action

def make_expert(env):
    return StackExpert(env)
