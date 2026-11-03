"""Measure possible joint-space camera bands using explicit simulation geometry."""
from pathlib import Path
import sys,time,json
import numpy as np
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'praxis/src'))
from scene_data import Generator
from active_view.collision import ArmChecker,reference_world

def main():
    g=Generator();g.scene(9362001,0,force_count=0)
    c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));q=c.q0.copy();p,R=c.camera_pose(q)
    print(json.dumps(dict(q=q.tolist(),camera=p.tolist(),check=c.check(q).__dict__)),flush=True)
    rng=np.random.default_rng(9362110);accepted=[];started=time.time()
    for i in range(96):
        scale=(.035,.09,.18,.30)[i%4];candidate=q+rng.uniform(-scale,scale,7)
        result=c.check(candidate)
        if not result.valid:continue
        pc,rc=c.camera_pose(candidate);distance=float(np.linalg.norm(pc-p))
        if not .008<distance<.25:continue
        # Shared camera bank is scene-independent. Per-scene checks are still required.
        if c.edge(q,candidate):accepted.append(dict(q=candidate.tolist(),position=pc.tolist(),rotation=rc.tolist(),distance=distance))
        if i%12==0:print(json.dumps(dict(at=i,accepted=len(accepted),seconds=time.time()-started)),flush=True)
    (HERE/'pose_probe_result.json').write_text(json.dumps(dict(base_q=q.tolist(),base_position=p.tolist(),accepted=accepted,elapsed=time.time()-started),indent=2))
    g.close()
if __name__=='__main__':main()
