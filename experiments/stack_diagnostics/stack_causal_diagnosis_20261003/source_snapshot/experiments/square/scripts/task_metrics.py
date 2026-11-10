"""Observable subtask progress, separate from the task success predicate."""
import numpy as np


class StackProgress:
    def __init__(self, raw):
        self.raw = raw
        self.grasped = set()
        self.lifted = set()
        self.base_lifted = False
        self.max_released_tower = 1
        self.correct_pair_steps = np.zeros(len(raw.cubes)-1,dtype=int)

    def update(self):
        raw = self.raw
        pos = np.array([raw.sim.data.body_xpos[i] for i in raw.cube_ids])
        grasp = [raw._check_grasp(raw.robots[0].gripper,c) for c in raw.cubes]
        self.grasped.update(i for i,g in enumerate(grasp) if g)
        self.lifted.update(i for i,p in enumerate(pos) if p[2] > raw.table_offset[2]+.08)
        self.base_lifted |= bool(pos[0,2] > raw.table_offset[2]+.08)
        height = 1
        prefix = abs(pos[0,2]-raw.table_offset[2]-.02) < .008
        for i in range(len(raw.cubes)-1):
            valid = (np.linalg.norm(pos[i+1,:2]-pos[i,:2]) < .009
                and abs(pos[i+1,2]-pos[i,2]-.04) < .008
                and raw.check_contact(raw.cubes[i],raw.cubes[i+1])
                and not grasp[i] and not grasp[i+1])
            self.correct_pair_steps[i] += bool(valid)
            prefix = prefix and valid
            if prefix: height += 1
        self.max_released_tower = max(self.max_released_tower,height)

    def result(self):
        return dict(grasped_cube_indices=sorted(self.grasped),
            lifted_cube_indices=sorted(self.lifted),base_lifted=self.base_lifted,
            max_released_tower_height=self.max_released_tower,
            released_correct_pair_steps=self.correct_pair_steps.tolist())
