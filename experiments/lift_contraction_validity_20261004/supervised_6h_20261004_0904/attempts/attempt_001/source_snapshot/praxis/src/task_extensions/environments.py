import numpy as np
from robosuite.environments.manipulation.stack import Stack
from robosuite.environments.manipulation.two_arm_handover import TwoArmHandover
from robosuite.environments.manipulation.two_arm_env import TwoArmEnv
from robosuite.environments.manipulation.manipulation_env import ManipulationEnv
from robosuite.models.arenas import TableArena
from robosuite.models.objects import BoxObject
from robosuite.models.tasks import ManipulationTask
from robosuite.utils.placement_samplers import UniformRandomSampler
from robosuite.utils.observables import Observable, sensor
from robosuite.utils import transform_utils as T


class StackFour(Stack):
    """Four 4-cm cubes, ordered bottom-to-top A/B/C/D, released and stable."""
    cube_count = 4
    def _load_model(self):
        ManipulationEnv._load_model(self)
        self.robots[0].robot_model.set_base_xpos(
            self.robots[0].robot_model.base_xpos_offset['table'](self.table_full_size[0]))
        arena = TableArena(table_full_size=self.table_full_size,
            table_friction=self.table_friction,table_offset=self.table_offset)
        arena.set_origin([0,0,0])
        self.cubes = [BoxObject(name=f'cube{letter}',size=[.02]*3,rgba=color,
            density=500,friction=[1,.005,.0001]) for letter,color in list(zip('ABCD',
            ([.85,.15,.15,1],[.15,.75,.2,1],[.15,.3,.9,1],[.95,.75,.1,1])))[:self.cube_count]]
        for letter,cube in zip('ABCD',self.cubes):
            setattr(self,'cube'+letter,cube)
        self.placement_initializer = UniformRandomSampler(name='FourCubeSampler',
            mujoco_objects=self.cubes,x_range=[-.16,.16],y_range=[-.16,.16],rotation=0,
            ensure_valid_placement=True,ensure_object_boundary_in_range=True,
            reference_pos=self.table_offset,z_offset=.01)
        self.model = ManipulationTask(mujoco_arena=arena,
            mujoco_robots=[r.robot_model for r in self.robots],mujoco_objects=self.cubes)

    def _setup_references(self):
        Stack._setup_references(self)
        self.cube_ids = [self.sim.model.body_name2id(c.root_body) for c in self.cubes]

    def _setup_observables(self):
        observables = ManipulationEnv._setup_observables(self)
        if self.use_object_obs:
            for cube,body_id in zip(self.cubes,self.cube_ids):
                def position(cache, index=body_id):
                    return self.sim.data.body_xpos[index].copy()
                position.__name__ = cube.name + '_pos'
                observables[position.__name__] = Observable(name=position.__name__,
                    sensor=sensor(modality='object')(position),sampling_rate=self.control_freq)
        return observables

    def _reset_internal(self):
        self.stable_steps = 0
        Stack._reset_internal(self)

    def tower_is_valid(self):
        positions = [self.sim.data.body_xpos[i] for i in self.cube_ids]
        if abs(positions[0][2]-(self.table_offset[2]+.02)) > .008:
            return False
        for i in range(len(self.cubes)-1):
            if np.linalg.norm(positions[i+1][:2]-positions[i][:2]) > .009:
                return False
            if abs(positions[i+1][2]-positions[i][2]-.04) > .008:
                return False
            if not self.check_contact(self.cubes[i],self.cubes[i+1]):
                return False
        for cube in self.cubes:
            if self._check_grasp(self.robots[0].gripper,cube):
                return False
            velocity = self.sim.data.get_joint_qvel(cube.joints[0])
            if np.linalg.norm(velocity[:3]) > .03 or np.linalg.norm(velocity[3:]) > .3:
                return False
        return True

    def _post_action(self, action):
        self.stable_steps = self.stable_steps+1 if self.tower_is_valid() else 0
        return super()._post_action(action)

    def _check_success(self):
        return self.stable_steps >= int(.5*self.control_freq)

    def reward(self, action=None):
        return float(self._check_success()) * (self.reward_scale or 1.)


class StackTwo(StackFour):
    """Same geometry and stability criterion, with only A and B present."""
    cube_count = 2


class CubeHandover(TwoArmHandover):
    """Two Panda arms transfer a cube; donor grasp must precede receiver grasp."""
    def __init__(self, *args, **kwargs):
        if kwargs.get('prehensile',True) is False:
            raise ValueError('CubeHandover starts with the cube on the table')
        super().__init__(*args,**kwargs)

    def _load_model(self):
        TwoArmEnv._load_model(self)
        if len(self.robots) != 2 or self.env_configuration != 'opposed':
            raise ValueError('CubeHandover requires two single-arm robots, opposed')
        for robot,angle,offset in zip(self.robots,(np.pi/2,-np.pi/2),(-.25,.25)):
            pos = robot.robot_model.base_xpos_offset['table'](self.table_full_size[0])
            rotation = np.array([0.,0.,angle])
            pos = T.euler2mat(rotation) @ np.array(pos) + [0,offset,0]
            robot.robot_model.set_base_xpos(pos); robot.robot_model.set_base_ori(rotation)
        # Use a full table for cube pickup and a shared central handover space.
        self.table_offset = np.array([0.,0.,.8])
        arena = TableArena(table_full_size=(.8,1.2,.05),
            table_friction=self.table_friction,table_offset=self.table_offset)
        arena.set_origin([0,0,0])
        self.cube = BoxObject(name='handover_cube',size=[.025]*3,
            rgba=[.2,.45,.9,1],density=500,friction=[1,.005,.0001])
        self.placement_initializer = UniformRandomSampler(name='CubeSampler',
            mujoco_objects=self.cube,x_range=[-.1,.1],y_range=[-.2,-.1],rotation=0,
            ensure_valid_placement=True,reference_pos=self.table_offset,z_offset=.01)
        self.model = ManipulationTask(mujoco_arena=arena,
            mujoco_robots=[r.robot_model for r in self.robots],mujoco_objects=self.cube)

    def _setup_references(self):
        TwoArmEnv._setup_references(self)
        self.cube_id = self.sim.model.body_name2id(self.cube.root_body)

    def _setup_observables(self):
        observables = TwoArmEnv._setup_observables(self)
        if self.use_object_obs:
            @sensor(modality='object')
            def cube_pos(cache):
                return self.sim.data.body_xpos[self.cube_id].copy()
            observables['cube_pos'] = Observable(name='cube_pos',sensor=cube_pos,
                sampling_rate=self.control_freq)
        return observables

    def _reset_internal(self):
        self.donor_grasp_seen = False
        self.transfer_stable_steps = 0
        TwoArmEnv._reset_internal(self)
        if not self.deterministic_reset:
            for pos,quat,obj in self.placement_initializer.sample().values():
                self.sim.data.set_joint_qpos(obj.joints[0],np.r_[pos,quat])

    def transfer_is_valid(self):
        donor = self._check_grasp(self.robots[0].gripper,self.cube)
        receiver = self._check_grasp(self.robots[1].gripper,self.cube)
        lifted = self.sim.data.body_xpos[self.cube_id][2] > self.table_offset[2]+.1
        return self.donor_grasp_seen and receiver and not donor and lifted

    def _post_action(self, action):
        if self._check_grasp(self.robots[0].gripper,self.cube):
            self.donor_grasp_seen = True
        self.transfer_stable_steps = self.transfer_stable_steps+1 if self.transfer_is_valid() else 0
        return super()._post_action(action)

    def _check_success(self):
        return self.transfer_stable_steps >= int(.5*self.control_freq)

    def reward(self, action=None):
        return float(self._check_success()) * (self.reward_scale or 1.)

    def visualize(self, vis_settings):
        ManipulationEnv.visualize(self,vis_settings)
