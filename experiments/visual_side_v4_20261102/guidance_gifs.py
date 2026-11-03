"""Render first successful case per direction, including failed perception updates."""
import json,time,math
import numpy as np
import torch
from PIL import Image
import pilot as P
from data_v3 import PoseGenerator
from make_comparison_gifs import Panel,groups,corners
from followup_core import errors,observable
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Plan,timed_samples
from replay_scene import restore_scene

def main():
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--run',default='guidance_001');args=p.parse_args();out=P.HERE/args.run;folder=out/'animations';folder.mkdir(exist_ok=False);P.settings()
    source=P.HERE/'pilot_002';summary=json.loads((out/'report.json').read_text());capture_audit=json.loads((out/'capture_audit.json').read_text());assert capture_audit['passed']
    rows={r['index']:r for r in [json.loads(s) for s in (out/'families.jsonl').read_text().splitlines()]}
    original={r['index']:r for r in [json.loads(s) for s in (source/'families.jsonl').read_text().splitlines()]}
    hashes=json.loads((source/'checkpoint_hashes.json').read_text());models=[]
    for seed in [1,2,3]:
        path=P.ROOT/'experiments/visual_active_v3_20261101/run_001/checkpoints'/f'M2_seed{seed}_best.pth';assert P.sha(path)==hashes[path.name]
        model=P.ScenePerception().cuda().eval();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);models.append(model)
    reports=[];g=PoseGenerator()
    try:
        for family in ['left','right','base']:
            if family not in summary['examples']:continue
            index=summary['examples'][family];record=rows[index];prior=original[index]
            with np.load(source/'samples'/f'sample_{index:04d}.npz') as z:data={k:np.array(z[k])[None] for k in z.files}
            with np.load(out/'captures'/f'{index:04d}.npz') as z:
                for k in z.files:data[k][0,2]=z[k]
            data['pose_available'][0,2]=True
            before=P.infer(models,data,[0],(0,))[0];after=P.infer(models,data,[0],(0,2))[0]
            mask=observable(data,0,(0,))|observable(data,0,(0,2));old=errors(before,data,0,mask);new=errors(after,data,0,mask)
            old_error=float(np.mean([v['error_mm'] for v in old]));new_error=float(np.mean([v['error_mm'] for v in new]));first=groups(before);last=groups(after)
            truth={k:data[k][0] for k in ['positions','sizes','rotations','active','count','kind','family']}
            restore_scene(g,{k:v[0] for k,v in data.items()},prior)
            c=ArmChecker(g.m,g.d,reference_world(g.m,g.d));g.qadr=c.qadr;route=[np.array(q) for q in record['waypoints']];c.set_q(route[0])
            gt=[dict(center=truth['positions'][i],size=truth['sizes'][i],rotation=truth['rotations'][i]) for i in np.flatnonzero(truth['active'])]
            pts=np.concatenate([corners(b) for b in gt+first+last]);low=pts.min(0)-.025;high=np.maximum(pts.max(0)+.025,low+.10);low[2]=min(low[2],.795)
            label={'left':'Kamera links | Blick nach rechts zum Ziel','right':'Kamera rechts | Blick nach links zum Ziel','base':'Kamera zur Basis | Blick von Basis weg zum Ziel'}[family]
            panel=Panel(gt,first,[last],label,(low,high),old_error)
            panel.fig.texts[1].set_text(f'Neue Kamerafuehrung | Zielabweichung {record["optical_axis_error_deg"]:.2f} Grad | kein neues Training')
            panel.fig.texts[-1].set_text('Simulationsreferenz fuer ganze Armwege; keine visuelle Realroboterfreigabe. Neue Schaetzung wird nicht uebernommen.')
            frames=[];durations=[];trajectory=[]
            def frame(text,updated=None,score=None,duration=150):
                P.native_check(g);images=[g.env.sim.render(width=160,height=160,camera_name=cam)[::-1].copy() for cam in ['agentview','frontview','robot0_eye_in_hand']]
                frames.append(panel.frame(images,updated,text,score,int(updated is not None)));durations.append(duration)
            frame('Erste Aufnahme: Orange bleibt als Referenz stehen',duration=1000)
            plan=Plan(route,c.world.version,c.world.source,0)
            for stamp,q in timed_samples(plan,dt=.25):
                c.set_q(q);pc,R=c.camera_pose(q);trajectory.append(dict(time=stamp,q=q,camera=pc,rotation=R))
                frame(f'Gekoppelte Fahrt und Neigung | {record["camera_change"]["baseline_m"]*100:.1f} cm Versatz')
            c.set_q(record['q']);frame('Aufnahme am Ziel: Gruen ist Diagnose, keine automatische Uebernahme',last,new_error,duration=2500)
            name=f'guidance_{family}';frames[-1].save(folder/(name+'.png'));palette=frames[-1].convert('P',palette=Image.Palette.ADAPTIVE,colors=256)
            encoded=[im.quantize(palette=palette,dither=Image.Dither.NONE) for im in frames]
            encoded[0].save(folder/(name+'.gif'),save_all=True,append_images=encoded[1:],duration=durations,loop=0,optimize=True,disposal=1)
            P.save(folder/(name+'.scene.json'),dict(ground_truth=gt,initial_prediction=first,updated_predictions=[last],
                inspection_camera=dict(focus=record['desired_focus'],start=dict(position=trajectory[0]['camera'],rotation=trajectory[0]['rotation']),
                    goal=record['actual_camera'],path=[s['camera'] for s in trajectory]),
                source_case=dict(family_index=index,before=old,after=new),update_adopted=False))
            P.save(folder/(name+'.trajectory.json'),trajectory)
            report=dict(family=family,index=index,frames=len(frames),baseline_m=record['camera_change']['baseline_m'],angle_deg=record['camera_change']['angle_deg'],
                elevation_deg=record['elevation_deg'],axis_error_deg=record['optical_axis_error_deg'],initial_set_error_mm=old_error,updated_set_error_mm=new_error,
                update_adopted=False,training_started=False,geometry_backend='sim_reference')
            reports.append(report);print(json.dumps(report),flush=True)
            import matplotlib.pyplot as plt
            plt.close(panel.fig)
    finally:g.close()
    P.save(folder/'report.json',reports)

if __name__=='__main__':main()
