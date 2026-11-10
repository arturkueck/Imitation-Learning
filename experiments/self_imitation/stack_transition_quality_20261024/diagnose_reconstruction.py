from pathlib import Path
import sys,numpy as np
p=Path('experiments/self_imitation/stack_transition_quality_20261024').resolve();sys.path.insert(0,str(p));import enrich_grasp as r
e=r.legacy.make_env(3);e.reset_from_xml_string((r.ALLOWED[0].parent/'model.xml').read_text())
a=np.load(r.ALLOWED[0].parent/'215000.npz')
print('gripper_type',type(e.robots[0].gripper),list(e.robots[0].gripper) if isinstance(e.robots[0].gripper,dict) else 'model')
for t in [0,1,10,100,180,192,200]:
 e.sim.set_state_from_flattened(a['pre_state'][t+1]);e.sim.forward();pos=np.array([e.sim.data.body_xpos[i].copy() for i in e.cube_ids]);err=np.max(np.abs(pos.reshape(-1)-a['post_obs'][t,:9]));g=e.robots[0].gripper
 real=any(e.check_contact(v,e.cubes[2]) for v in g.values()) if isinstance(g,dict) else e.check_contact(g,e.cubes[2])
 print(t,'maxdiff_mm',float(err*1000),'loggedfinger',bool(a['fingers'][t,2]),'legacyfinger',e.check_contact(g,e.cubes[2]),'realcontact',real,'native_grasp',e._check_grasp(g,e.cubes[2]))
e.close()
