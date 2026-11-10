"""Post-hoc GIF replays: true boxes / initial estimate / acquired-image estimate.

No optimization, policy tuning, hardware commands or changes to experiment data.
Uses the nonreserved forced-capture technical smoke, never pretends the disabled
production policy requested these views. Actual recorded paths are reconstructed
kinematically and independently checked before rendering.
"""
from pathlib import Path
import os
os.environ['CUBLAS_WORKSPACE_CONFIG']=':4096:8'
import sys,json,hashlib,time,itertools,gc
import numpy as np
import torch
from PIL import Image
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from mpl_toolkits.mplot3d.art3d import Poly3DCollection
from dataclasses import asdict

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'praxis/src'))
from preflight import settings
from data_v3 import PoseGenerator,object_path_free
from model_v3 import ScenePerception
from followup_core import infer,observable,errors
from ensemble_uncertainty import group_predictions
from active_view.collision import ArmChecker,reference_world
from active_view.planner import Plan,timed_samples

RUN=HERE/'run_001';SOURCE=RUN/'followup_smoke_repair001'
SIGNS=np.array(list(itertools.product((-1,1),repeat=3)))
FACES=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]
COLORS={'truth':'#23d9eb','initial':'#ff9b42','updated':'#67e889'}
CASES=[('test_iid',0,'01_bruecke'),('test_iid',4,'02_turm'),('test_iid',5,'03_turm_verschlechterung'),
       ('test_camera_ood',7,'04_kamera_holdout'),('test_geometry_ood',1,'05_lange_duenne_quader')]
KIND=['Verstreut','Gemischt','Turm','Bruecke / Wand']

def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda:f.read(8*1024*1024),b''):h.update(block)
    return h.hexdigest()

def jsonable(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,dict):return {k:jsonable(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [jsonable(v) for v in value]
    return value

def save(path,value):path.write_text(json.dumps(jsonable(value),indent=2,ensure_ascii=False),encoding='utf-8')

def groups(pred):
    return [dict(center=g['position'],size=g['size'],rotation=g['rotation'],support=g['support']) for g in group_predictions(pred)]

def corners(box):return (SIGNS*np.asarray(box['size'])/2)@np.asarray(box['rotation']).T+box['center']

def draw_boxes(ax,boxes,color,style):
    for b in boxes:
        pts=corners(b);faces=[[pts[j] for j in f] for f in FACES]
        alpha={'truth':.18,'initial':.025,'updated':.04}[style]
        rgba=matplotlib.colors.to_rgba(color,alpha)
        poly=Poly3DCollection(faces,facecolors=[rgba],edgecolors=matplotlib.colors.to_rgba(color,.85),linewidths=.85 if style=='truth' else 1.1)
        ax.add_collection3d(poly)
        p=b['center'];ax.scatter(*p,color=color,s=20,marker={'truth':'o','initial':'x','updated':'+'}[style],depthshade=False)


class Panel:
    def __init__(self,truth,initial,all_updates,label,bounds,initial_score):
        self.truth=truth;self.initial=initial;self.label=label;self.bounds=bounds;self.initial_score=initial_score
        self.fig=plt.figure(figsize=(12,7.5),dpi=100,facecolor='#101b28')
        self.fig.text(.03,.95,label,color='white',fontsize=16,weight='bold')
        self.fig.text(.03,.914,'Technischer Versuch: Zusatzaufnahmen ERZWUNGEN  |  M2, drei Seeds  |  keine gelernte Freigabe',color='#e7ba73',fontsize=10)
        handles=[Patch(facecolor=matplotlib.colors.to_rgba(COLORS[k],.2),edgecolor=COLORS[k],label=v) for k,v in
                 [('truth','Simulation: echte Position'),('initial','Erste Vorhersage'),('updated','Nach Zusatzaufnahme')]]
        legend=self.fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.51,.884),ncol=3,frameon=False,fontsize=10)
        for text in legend.get_texts():text.set_color('white')
        self.cameras=[self.fig.add_axes([x,.555,.145,.245]) for x in [.03,.19,.35]]
        for ax,name in zip(self.cameras,['Festkamera links','Festkamera rechts','Handkamera']):
            ax.set_title(name,color='white',fontsize=10);ax.set_axis_off()
        self.ax3=self.fig.add_axes([.515,.13,.465,.665],projection='3d')
        self.ax2=self.fig.add_axes([.06,.13,.40,.31])
        self.phase=self.fig.text(.03,.505,'',color='white',fontsize=11,weight='bold')
        self.score=self.fig.text(.03,.468,'',color='#c0cddb',fontsize=10)
        self.fig.text(.03,.065,'3D und Draufsicht: gleiche Weltkoordinaten, keine Anpassung an Sollpositionen.',color='#a9bac9',fontsize=9)
        self.fig.text(.03,.035,'Rekonstruierter kinematischer Ablauf; gesamte Wege erneut mit Simulatorreferenz auf Kollisionen geprueft.',color='#a9bac9',fontsize=8.5)
        self.ims=None

    def frame(self,images,updated,phase,score,capture_number):
        if self.ims is None:self.ims=[ax.imshow(im,interpolation='nearest') for ax,im in zip(self.cameras,images)]
        else:
            for obj,im in zip(self.ims,images):obj.set_data(im)
        self.phase.set_text(phase)
        suffix='noch nicht aufgenommen' if updated is None else f'{score:.2f} mm-aeq. nach Aufnahme {capture_number}'
        self.score.set_text(f'Satzfehler*: zuerst {self.initial_score:.2f}  |  {suffix}')
        self.ax3.clear();self.ax3.set_facecolor('#101b28')
        self.ax2.clear();self.ax2.set_facecolor('#101b28')
        active=[(self.truth,'truth'),(self.initial,'initial')]+([] if updated is None else [(updated,'updated')])
        for boxes,key in active:
            draw_boxes(self.ax3,boxes,COLORS[key],key)
            for b in boxes:
                pts=corners(b)[:,:2]
                from scipy.spatial import ConvexHull
                hull=ConvexHull(pts);ring=np.r_[hull.vertices,hull.vertices[0]]
                self.ax2.plot(pts[ring,0],pts[ring,1],color=COLORS[key],alpha=.8,lw=1)
                self.ax2.scatter(*np.asarray(b['center'])[:2],c=COLORS[key],s=24,marker={'truth':'o','initial':'x','updated':'+'}[key])
        for i,b in enumerate(self.truth):
            self.ax3.text(*b['center'],f' GT{i}',fontsize=7,color=COLORS['truth'])
        low,high=self.bounds
        self.ax3.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),zlim=(low[2],high[2]))
        self.ax3.set_box_aspect(high-low);self.ax3.view_init(elev=25,azim=-58)
        for name in ['x','y','z']:
            axis=getattr(self.ax3,name+'axis');axis.label.set_color('#b5c6d5');axis.set_tick_params(colors='#b5c6d5',labelsize=8)
            axis.set_pane_color((.07,.115,.16,1));axis._axinfo['grid']['color']=(.3,.38,.45,.3)
        self.ax3.set_xlabel('X [m]');self.ax3.set_ylabel('Y [m]');self.ax3.set_zlabel('Z [m]')
        self.ax3.set_title('3D-Abgleich: Geometrie und Objektzentren',color='white',fontsize=11,pad=6)
        self.ax2.set(xlim=(low[0],high[0]),ylim=(low[1],high[1]),xlabel='X [m]',ylabel='Y [m]')
        self.ax2.set_aspect('equal',adjustable='box');self.ax2.grid(alpha=.15);self.ax2.tick_params(colors='#b5c6d5',labelsize=8)
        self.ax2.xaxis.label.set_color('#b5c6d5');self.ax2.yaxis.label.set_color('#b5c6d5')
        self.ax2.set_title('Draufsicht: Punkte = Zentren, Umrisse = Boxen',color='white',fontsize=10)
        for spine in self.ax2.spines.values():spine.set_color('#476078')
        self.fig.canvas.draw()
        return Image.fromarray(np.asarray(self.fig.canvas.buffer_rgba())[:,:,:3].copy())


def render_case(g,models,out,split,i,name):
    data={p.stem:np.load(p,mmap_mode='r') for p in (SOURCE/'data'/split).glob('*.npy')}
    case=json.loads((SOURCE/f'{split}_cases.json').read_text())[i]
    if not case['captures']:raise RuntimeError('Selected example has no recorded acquisition')
    family=data['family'][i];truth,_=g.setup_family(int(family[0]),int(family[1]),ood=split=='test_geometry_ood',camera_ood=split=='test_camera_ood')
    if not np.allclose(truth['positions'],data['positions'][i],atol=1e-6) or not np.allclose(truth['sizes'],data['sizes'][i],atol=1e-6):raise RuntimeError('Regenerated scene differs from source')
    dest=out/name;dest.mkdir(exist_ok=False)
    live={k:np.array(v[i:i+1],copy=True) for k,v in data.items()}
    initial=infer(models,live,[0],(0,))[0];before=groups(initial)
    actual_updates=[];hist=(0,);replay_checks=[]
    # Inference uses frozen checkpoints only, with actual saved wrist photos.
    for attempt,capture in enumerate(case['captures']):
        q=int(capture['candidate']);j=int(data['pose_ids'][i,q])
        row=g.observation(truth,g.bank[j]['q'])
        saved=np.asarray(Image.open(SOURCE/'policy'/split/f'{i:06d}'/f'wrist_{attempt}.png').convert('RGB'))
        difference=np.abs(row['images'].astype(np.int16)-data['images'][i,q].astype(np.int16))
        wrist_difference=int(np.abs(row['images'][2].astype(np.int16)-saved.astype(np.int16)).max())
        if difference.max()>1 or (difference>0).mean()>.001 or wrist_difference>1:raise RuntimeError('Replay RGB substantively differs')
        row['images'][2]=saved
        for k,v in row.items():live[k][0,q]=v
        hist=hist+(q,);pred=infer(models,live,[0],hist)[0]
        actual_updates.append(groups(pred))
        mask=observable(data,i,(0,))|observable(data,i,hist)
        evaluated=errors(pred,data,i,mask)
        discrepancy=max(abs(a['error_mm']-b['error_mm']) for a,b in zip(evaluated,capture['after']))
        # Subpixel raster drift may produce minute numerical inference changes.
        if discrepancy>.05:raise RuntimeError(f'Inference no longer matches recorded case: {discrepancy}mm-equivalent')
        replay_checks.append(dict(max_rgb_channel_difference=int(difference.max()),saved_wrist_max_channel_difference=wrist_difference,
                                  recorded_score_max_difference_mm=discrepancy,history=hist))
    truth_boxes=[dict(center=truth['positions'][j],size=truth['sizes'][j],rotation=truth['rotations'][j]) for j in np.flatnonzero(truth['active'])]
    pts=np.concatenate([corners(b) for boxes in [truth_boxes,before]+actual_updates for b in boxes])
    low=pts.min(0)-.022;high=pts.max(0)+.022;low[2]=min(.795,low[2]);high=np.maximum(high,low+.08)
    panel=Panel(truth_boxes,before,actual_updates,f'{name[:2]} | {KIND[int(data["kind"][i])]} | {len(truth_boxes)} Objekte',
                (low,high),float(np.mean([r['error_mm'] for r in case['initial']])))
    q0=g.bank[int(data['pose_ids'][i,0])]['q'];g.d.qpos[g.qadr]=q0;g.env.sim.forward()
    checker=ArmChecker(g.m,g.d,reference_world(g.m,g.d));checker.set_q(q0)
    frames=[];durations=[];path_log=[];current=None;current_score=None;number=0;native_samples=0
    def camera_images():
        return [g.env.sim.render(width=160,height=160,camera_name=n)[::-1].copy() for n in ['agentview','frontview','robot0_eye_in_hand']]
    def add(phase,duration=125):
        nonlocal native_samples
        for contact in g.d.contact[:g.d.ncon]:
            a=g.m.geom(int(contact.geom1)).name or '';b=g.m.geom(int(contact.geom2)).name or ''
            ra=a.startswith(('robot0_','gripper0_'));rb=b.startswith(('robot0_','gripper0_'));other=b if ra else a
            if ra!=rb and not other.startswith('fixed_mount0_') and contact.dist< -1e-6:raise RuntimeError('Native robot-world penetration')
        native_samples+=1
        frames.append(panel.frame(camera_images(),current,phase,current_score,number));durations.append(duration)
    add('Erste Aufnahme: Orange bleibt als Referenz erhalten',1200)
    previous=q0.copy()
    for attempt,capture in enumerate(case['captures']):
        p=int(capture['candidate']);entry=g.bank[int(data['pose_ids'][i,p])]
        if not object_path_free(entry['low'],entry['high'],truth['positions'],truth['sizes'],truth['rotations'],truth['active']):raise RuntimeError('Swept object envelope failed')
        waypoints=[previous,g.base_q,entry['q']]
        for a,b in zip(waypoints[:-1],waypoints[1:]):
            if not checker.edge(a,b):raise RuntimeError('Whole-arm path refused')
        plan=Plan(waypoints,checker.world.version,checker.world.source,checker.checks)
        samples=timed_samples(plan,dt=.125)
        for stamp,q in samples:
            checker.set_q(q)
            add(f'Arm bewegt sich zur Zusatzaufnahme {attempt+1} | noch kein neues Bild')
            path_log.append(dict(capture=attempt,t=float(stamp),q=q.tolist()))
        previous=entry['q'].copy();checker.set_q(previous)
        add(f'Zusatzaufnahme {attempt+1}: Bild aufgenommen, Modell wird ausgewertet',600)
        current=actual_updates[attempt];current_score=float(np.mean([x['error_mm'] for x in capture['after']]));number=attempt+1
        add(f'Nach Zusatzaufnahme {number}: aktualisierte Vorhersage in Gruen',1600)
    difference=float(np.mean([a['error_mm']-b['error_mm'] for a,b in zip(case['initial'],case['final'])]))
    verdict='kleiner' if difference>0 else 'groesser'
    add(f'Ergebnis: Satzfehler um {abs(difference):.2f} mm-aeq. {verdict}',2200)
    frames[-1].save(dest/'poster.png');frames[0].save(dest/'initial.png')
    palette=frames[-1].convert('P',palette=Image.Palette.ADAPTIVE,colors=256)
    encoded=[f.quantize(palette=palette,dither=Image.Dither.NONE) for f in frames]
    gif=dest/'comparison.gif';encoded[0].save(gif,save_all=True,append_images=encoded[1:],duration=durations,loop=0,optimize=True,disposal=1)
    save(dest/'scene_comparison.json',dict(source_case=case,ground_truth=truth_boxes,initial_prediction=before,updated_predictions=actual_updates,
         prediction_representation='three-seed group_predictions, center mean and size/rotation medoid; never fitted to ground truth',
         replay_checks=replay_checks,path=path_log,trajectory_checks=checker.checks,native_frames_checked=native_samples,
         note='New kinematic reconstruction of recorded forced technical views; not a video of learned production actions'))
    info=dict(name=name,split=split,family=family,objects=len(truth_boxes),captures=len(case['captures']),
         original_set_error_before_mm=float(np.mean([r['error_mm'] for r in case['initial']])),
         original_set_error_after_mm=float(np.mean([r['error_mm'] for r in case['final']])),
         error_reduction_mm=difference,gif=str(gif.relative_to(out)),poster=str((dest/'poster.png').relative_to(out)),
         frames_written=Image.open(gif).n_frames,duration_ms=sum(durations),sha256=sha(gif),replay_checks=replay_checks)
    save(dest/'manifest.json',info);plt.close(panel.fig);del frames,encoded;gc.collect()
    print(json.dumps(jsonable(info)),flush=True)
    return info


def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='comparison_gifs_001');parser.add_argument('--cases',type=int,default=5);args=parser.parse_args()
    settings();out=HERE/args.name;out.mkdir(exist_ok=False)
    models=[];hashes={};expected=json.loads((RUN/'checkpoint_hashes.json').read_text())
    for seed in [1,2,3]:
        path=RUN/'checkpoints'/f'M2_seed{seed}_best.pth';hashes[path.name]=sha(path)
        if hashes[path.name]!=expected[path.name]:raise RuntimeError('Frozen checkpoint changed')
        model=ScenePerception().cuda();model.load_state_dict(torch.load(path,map_location='cuda',weights_only=False)['model']);model.eval();models.append(model)
    g=PoseGenerator();started=time.time();results=[]
    try:
        g.make_bank()
        for split,i,name in CASES[:args.cases]:results.append(render_case(g,models,out,split,i,name))
    finally:g.close()
    save(out/'manifest.json',dict(created_unix=time.time(),elapsed_seconds=time.time()-started,cases=results,checkpoint_hashes=hashes,
        source=str(SOURCE.relative_to(ROOT)),source_case_hashes={s:sha(SOURCE/f'{s}_cases.json') for s in set(x[0] for x in CASES[:args.cases])},
        colors=COLORS,training=False,policy_changed=False,selection='illustrative purposive selection; includes improvements and regressions',
        production_policy='disabled; zero learned production captures',motion='post-hoc kinematic reconstruction, paths rechecked using sim_reference'))
    (out/'README.md').write_text('''# Blickwechsel und drei Boxfarben

Cyan: echte Simulationsgeometrie. Orange: erste Vorhersage. Grün: nach tatsächlichem zusätzlichem Handkamerabild erneut berechnete Vorhersage. Zentren und Boxen sind unverändert in Weltkoordinaten, ohne räumliche Registrierung oder künstliche Vergrößerung der Fehler. Orange bleibt während des gesamten GIFs stehen; Grün erscheint erst nach einer Aufnahme.

Quelle: followup_smoke_repair001, ausdrücklich erzwungener technischer Aufnahmetest mit nicht reservierten Seeds. Die kalibrierte Produktionspolicy blieb deaktiviert. Diese GIFs zeigen deshalb keinen erfolgreichen autonomen Nachschauzyklus. Die dargestellten Bewegungen sind jetzt aus den gespeicherten Gelenkposen rekonstruierte kinematische Abläufe; vor dem Rendern wurden die ganzen Wege mit Selbst-/Umwelt-/Kamerageometrie erneut geprüft. Simulatorreferenz, kein Realroboter und kein Beleg rein visueller Sicherheit.

Die drei eingefrorenen M2-Checkpoints wurden gehasht. Vorhersagen wurden im Inferenzmodus mit tatsächlichen gespeicherten Handbildern und nachgerenderten festen Ansichten berechnet. Der Replay-Abgleich erlaubt nur die bereits dokumentierte minimale Rasterrundung. Scores müssen bis auf höchstens0,05 äquivalente mm zum gespeicherten technischen Fall passen; tatsächliche Differenzen stehen im Manifest.

*Satzfehler* ist ein Fehlermaß in äquivalenten Millimetern: Position plus0,25×Eckenfehler mit Strafen für fehlende und zusätzliche Objekte. Es ist keine reine Positions-MAE. Verbesserungen und Verschlechterungen sind enthalten. Die fünf Fälle sind illustrative Beispiele, keine repräsentative Erfolgsquote. Keine Gewichte, Policy, Trainingsdaten oder früheren Resultate wurden geändert. manifest.json und scene_comparison.json enthalten Quellen, Posen, Vorhersagen und Auditdaten.
''',encoding='utf-8')
    print(json.dumps(dict(done=True,directory=str(out),cases=len(results),elapsed_seconds=time.time()-started)),flush=True)
if __name__=='__main__':main()
