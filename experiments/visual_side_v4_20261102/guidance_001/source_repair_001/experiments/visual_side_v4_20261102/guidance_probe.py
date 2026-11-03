"""Diagnose camera-bank rejection reasons on preserved pilot observations."""
import json,time
from collections import Counter
import numpy as np
import torch
import pilot as P
from pilot_bank import choose,static_signature
from data_v3 import PoseGenerator,object_path_free,swept_envelopes
from active_view.collision import ArmChecker,reference_world
from active_view.side_views import optical_axis_error,side_frame
from active_view.geometry import Box,segment_aabb_intersection
from ensemble_uncertainty import group_predictions

def main():
    out=P.HERE/'guidance_probe_001';out.mkdir(exist_ok=False);P.settings();began=time.perf_counter()
    source=P.HERE/'pilot_002';rows=[json.loads(x) for x in (source/'families.jsonl').read_text().splitlines()]
    models=[];run=P.ROOT/'experiments/visual_active_v3_20261101/run_001';hashes=json.loads((source/'checkpoint_hashes.json').read_text())
    for seed in [1,2,3]:
        path=run/'checkpoints'/f'M2_seed{seed}_best.pth';assert P.sha(path)==hashes[path.name]
        m=P.ScenePerception().cuda().eval();m.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);models.append(m)
    focuses=[]
    for row in rows:
        with np.load(source/'samples'/f'sample_{row["index"]:04d}.npz') as z:data={k:np.array(z[k])[None] for k in z.files}
        predictions=P.infer(models,data,[0],(0,))[0];groups=group_predictions(predictions)
        if not groups:focuses.append(None);continue
        target=max(groups,key=lambda x:(3-x['support'],x['spread_mm']))
        focuses.append(dict(center=target['position'],radius=float(np.clip(np.linalg.norm(target['size'])/2+target['spread_mm']/1000,.04,.09))))
    P.save(out/'focuses.json',focuses)
    g=PoseGenerator();counts=Counter();bank=[]
    try:
        g._setup(np.random.default_rng(94140202),0,'scattered',False);c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));g.qadr=c.qadr
        entries=json.loads((source/'bank.json').read_text())['entries'];start=np.array(entries[0]['waypoints'][0]);c.set_q(start)
        assert static_signature(g,c)==json.loads((source/'bank.json').read_text())['static_signature']
        for e in entries:
            e={**e,**{k:np.array(e[k]) for k in ['q','camera','rotation','waypoints']}}
            lows=[];highs=[]
            for a,b in zip(e['waypoints'][:-1],e['waypoints'][1:]):
                low,high=swept_envelopes(c,a,b,pieces=128);lows.append(low);highs.append(high)
            e['low']=np.concatenate(lows);e['high']=np.concatenate(highs);bank.append(e)
            np.savez_compressed(out/f'certificate_{e["id"]:02d}.npz',**{k:e[k] for k in ['low','high','waypoints','q','camera','rotation']})
        body=g.m.body(g.env.robots[0].robot_model.root_body).id;base=g.d.xpos[body].copy()
        details=[]
        for row,focus in zip(rows,focuses):
            requested='right' if row['requested_family']=='difficult' else row['requested_family'];reasons=Counter();accepted=[]
            with np.load(source/'samples'/f'sample_{row["index"]:04d}.npz') as z:truth={k:np.array(z[k]) for k in ['positions','sizes','rotations','active']}
            c.world=reference_world(g.m,g.d)
            c.world.boxes=[b for b in c.world.boxes if b.geom not in set(sum(g.geoms,[]))]
            c.world.boxes += [Box(truth['positions'][i],truth['sizes'][i]/2,truth['rotations'][i],f'label_object_{i}') for i in np.flatnonzero(truth['active'])]
            for e in bank:
                if e['family']!=requested:continue
                if focus is None:reasons['no_focus']+=1;continue
                if not object_path_free(e['low'],e['high'],**truth):reasons['swept_object']+=1;continue
                center=np.array(focus['center']);radius=focus['radius'];delta=center-e['camera'];distance=np.linalg.norm(delta)
                error=optical_axis_error(e['camera'],e['rotation'],center)
                if distance<=radius+.05 or np.deg2rad(error)+np.arcsin(min(.999,radius/distance))>np.deg2rad(g.m.cam_fovy[c.camera]/2)*.96:reasons['fov']+=1;continue
                axis=side_frame(base,center)['left' if requested=='elevated' else requested]
                if (e['camera']-center)@axis<.10:reasons['side']+=1;continue
                end=center-delta/distance*radius
                if any(segment_aabb_intersection(e['camera'],end,b,padding=.002) for b in c.world.boxes):reasons['sightline']+=1;continue
                accepted.append(e['id'])
            if accepted:counts[requested]+=1
            details.append(dict(index=row['index'],family=row['requested_family'],accepted=accepted,reasons=dict(reasons)))
        P.save(out/'diagnosis.json',dict(captured_by_family=dict(counts),details=details,elapsed_seconds=time.perf_counter()-began))
        print(json.dumps(dict(captured_by_family=dict(counts),rejections=dict(sum((Counter(r['reasons']) for r in details),Counter())),seconds=time.perf_counter()-began)),flush=True)
    finally:g.close()

if __name__=='__main__':main()
