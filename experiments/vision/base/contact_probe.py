"""Targeted contact diagnosis, no global rerun or altered safety thresholds."""
import json,numpy as np
import pilot as P
from guidance_validate import candidate_order
from replay_scene import restore_scene
from data_v3 import PoseGenerator
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Planner,Focus
from active_view.camera_guidance import refine_view,join_routes
from active_view.geometry import segment_aabb_intersection

def main():
    out=P.HERE/'guidance_001';index=140;old=json.loads((P.HERE/'pilot_002/families.jsonl').read_text().splitlines()[index])
    with np.load(P.HERE/'pilot_002/samples'/f'sample_{index:04d}.npz') as z:sample={k:np.array(z[k]) for k in z.files}
    description=json.loads((P.HERE/'guidance_probe_001/focuses.json').read_text())[index];focus=Focus(np.array(description['center']),description['radius'])
    metadata=json.loads((out/'bank.json').read_text());bank=[]
    for e in metadata['entries']:
        with np.load(out/f'certificate_{e["id"]:03d}.npz') as z:e.update({k:np.array(z[k]) for k in z.files if k!='id'})
        bank.append(e)
    g=PoseGenerator()
    try:
        replay=restore_scene(g,sample,old);c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));start=g.base_qpos[c.qadr].copy();c.set_q(start)
        base=g.d.xpos[g.m.body(g.env.robots[0].robot_model.root_body).id].copy();pc,_=c.camera_pose(start)
        proposals,reasons=candidate_order(bank,focus,'right',c,base,pc,{k:sample[k] for k in ['positions','sizes','rotations','active']})
        for e in proposals[:5]:
            r=refine_view(Planner(c),focus,pc,base,'right',e['q'])
            if r['stage']!='aimed':continue
            camera=r['metrics']['camera'];delta=focus.center-camera;end=focus.center-delta/np.linalg.norm(delta)*focus.radius
            if any(segment_aabb_intersection(camera,end,b,padding=.002) for b in c.world.boxes):continue
            route=join_routes(e['waypoints'],r['suffix'])
            for segment,(a,b) in enumerate(zip(route[:-1],route[1:])):
                for alpha in np.linspace(0,1,9):
                    q=a+(b-a)*alpha;c.set_q(q);bad=[]
                    for contact in g.d.contact[:g.d.ncon]:
                        aa=g.m.geom(int(contact.geom1)).name or '';bb=g.m.geom(int(contact.geom2)).name or '';ra=aa.startswith(('robot0_','gripper0_'));rb=bb.startswith(('robot0_','gripper0_'));other=bb if ra else aa
                        if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:bad.append(dict(a=aa,b=bb,distance=float(contact.dist)))
                    if bad:
                        check=c.check(q);value=dict(index=index,bank=e['id'],segment=segment,alpha=float(alpha),q=q,replay=replay,contacts=bad,checker=dict(valid=check.valid,reason=check.reason,clearance=check.clearance,pair=check.pair))
                        P.save(out/'contact_probe.json',value);print(json.dumps(value,default=P.jsonable),flush=True);return
            print(json.dumps(dict(bank=e['id'],native='passed')),flush=True)
    finally:g.close()

if __name__=='__main__':main()
