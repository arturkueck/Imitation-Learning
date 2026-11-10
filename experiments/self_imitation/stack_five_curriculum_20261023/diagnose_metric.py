import sys
from pathlib import Path
sys.path.insert(0,str(Path('experiments/self_imitation/stack_five_curriculum_20261023').resolve()))
import runner as r
import numpy as np
for n in [2,5]:
 e=r.make_env(n);e.reset()
 for i,c in enumerate(e.cubes):e.sim.data.set_joint_qpos(c.joints[0],np.r_[[0,0,e.table_offset[2]+.02+.04*i],[1,0,0,0]]);e.sim.data.set_joint_qvel(c.joints[0],np.zeros(6))
 e.sim.forward()
 for _ in range(250):e.sim.step()
 e.sim.forward()
 print('N',n,'valid',r.old.prefix_valid(e,n),'p',[e.sim.data.body_xpos[i].tolist() for i in e.cube_ids],'contact',[e.check_contact(e.cubes[i],e.cubes[i+1]) for i in range(n-1)],'grip',[e.check_contact(e.robots[0].gripper,c) for c in e.cubes],'v',[e.sim.data.get_joint_qvel(c.joints[0]).tolist() for c in e.cubes],flush=True)
 e.close()
