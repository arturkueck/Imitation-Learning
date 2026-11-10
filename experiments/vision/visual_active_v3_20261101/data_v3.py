"""Pose-robust RGB data. GT supplies labels and explicit sim-reference collision audit only."""
from pathlib import Path
import sys,json,time,itertools
import numpy as np
import mujoco
from PIL import Image
from dataclasses import asdict
HERE=Path(__file__).resolve().parent;ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'experiments/vision/visual_scene_v2_20261101'))
sys.path.insert(0,str(ROOT/'praxis/src'))
from scene_data import Generator,ORIGIN,CAMS
from physical_setup import physical_setup
from active_view.collision import ArmChecker,reference_world
from active_view.geometry import Box
from active_view.capture_requests import RequestJournal,CaptureRequest,pose_from_mujoco,utc_now

SIGNS=np.array(list(itertools.product((-1,1),repeat=3)))
KINDS=['scattered','mixed','tower','wall']


def digest(path):
    import hashlib
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):h.update(b)
    return h.hexdigest()


def assignment(seed,index):
    rng=np.random.default_rng(np.random.SeedSequence([seed,index]))
    n=int(rng.choice(6,p=[.05,.19,.19,.19,.19,.19]))
    # Joint allocation matches nonempty target marginals without invalid fallback layouts.
    p=[1,0,0,0] if n<2 else ([.0625,.3125,.625,0] if n==2 else [.0625,.3125,.375,.25])
    return n,str(rng.choice(KINDS,p=p))


def swept_envelopes(checker,a,b,pieces=32):
    """Conservative swept AABBs, with analytic per-body displacement bounds.

    Static/self safety is independently certified by checker.edge. For each
    half-segment every moving point stays within radii @ abs(delta_q)/2 of
    its midpoint geometry. AABB overlap rejects; it never proves collision.
    """
    low=[];high=[]
    for t in range(pieces):
        left=a+(b-a)*t/pieces;right=a+(b-a)*(t+1)/pieces
        shapes=checker.robot_boxes((left+right)/2)
        bounds=checker.radii@np.abs(right-left)/2+checker.world_margin+1e-8
        for shape,margin in zip(shapes,bounds):
            low.append(shape.vertices.min(0)-margin);high.append(shape.vertices.max(0)+margin)
    return np.asarray(low),np.asarray(high)


def object_path_free(low,high,positions,sizes,rotations,active):
    for i in np.flatnonzero(active):
        corners=(SIGNS*sizes[i]/2)@rotations[i].T+positions[i]
        if np.any(np.all((high>=corners.min(0))&(low<=corners.max(0)),axis=1)):return False
    return True


class PoseGenerator(Generator):
    _setup=physical_setup
    def make_bank(self,seed=9362110,attempts=240):
        self.scene(9362001,0,force_count=0)
        world=reference_world(self.m,self.d)
        object_ids=set(sum(self.geoms,[]))
        world.boxes=[b for b in world.boxes if b.geom not in object_ids]
        checker=ArmChecker(self.m,self.d,world);q=checker.q0.copy()
        if not checker.check(q).valid:raise RuntimeError('Base pose is not valid')
        self.base_q=q;self.qadr=checker.qadr.copy()
        p,_=checker.camera_pose(q)
        rng=np.random.default_rng(seed);bank=[]
        for i in range(attempts):
            scale=(.035,.09,.18,.30)[i%4]
            candidate=q.copy() if i==0 else q+rng.uniform(-scale,scale,7)
            if not checker.check(candidate).valid:continue
            pc,R=checker.camera_pose(candidate);distance=float(np.linalg.norm(pc-p))
            band='original' if i==0 else 'near' if .01<=distance<.04 else 'medium' if .04<=distance<.12 else 'oblique' if .12<=distance<=.22 else None
            if band is None:continue
            # Calibration and object-independent orientation/FOV constraint only.
            look=(np.array([0.,0.,.92])-pc);look/=np.linalg.norm(look)
            if np.dot(-R[:,2],look)<np.cos(np.deg2rad(38)):continue
            if not checker.edge(q,candidate):continue
            low,high=swept_envelopes(checker,q,candidate)
            bank.append(dict(q=candidate,position=pc,rotation=R,distance=distance,band=band,low=low,high=high))
            if all(sum(x['band']==b for x in bank)>=target for b,target in [('original',1),('near',12),('medium',12),('oblique',8)]):break
        self.checker=checker;self.bank=bank
        if any(sum(x['band']==b for x in bank)<3 for b in ['near','medium','oblique']):
            raise RuntimeError('Insufficient collision-certified pose bands')
        checker.set_q(q)
        root=self.env.robots[0].robot_model.root_body;body=self.m.body(root).id
        self.T_world_base=np.eye(4);self.T_world_base[:3,:3]=self.d.xmat[body].reshape(3,3);self.T_world_base[:3,3]=self.d.xpos[body]
        self.camera_holdout=[]
        for band in ['near','medium','oblique']:
            self.camera_holdout.extend([j for j,x in enumerate(bank) if x['band']==band][::5])
        return dict(seed=seed,attempts=i+1,static_self_checks=checker.checks,source='sim_reference',camera_holdout_ids=self.camera_holdout,
                    base_q=q.tolist(),T_world_base=self.T_world_base.tolist(),
                    candidates=[{k:(v.tolist() if isinstance(v,np.ndarray) else v) for k,v in x.items() if k not in ['low','high']} for x in bank])

    def setup_family(self,seed,index,ood=False,camera_ood=False):
        rng=np.random.default_rng(np.random.SeedSequence([seed,index]));n,kind=assignment(seed,index)
        if ood:kind='scattered' # OOD result is explicitly restricted to scattered layouts.
        for _ in range(40):
            try:
                sizes,pos=self._setup(rng,n,kind,ood)
                rotations=np.array([self.d.xmat[b].reshape(3,3).copy() for b in self.bodies])
                active=np.arange(5)<n
                valid=[j for j,x in enumerate(self.bank) if (x['band']=='original' or ((j in self.camera_holdout)==camera_ood)) and object_path_free(x['low'],x['high'],pos,sizes,rotations,active)]
                selected=[]
                for band,count in [('original',1),('near',2),('medium',2),('oblique',1)]:
                    ids=[j for j in valid if self.bank[j]['band']==band]
                    if len(ids)<count:raise ValueError('insufficient_object_safe_'+band)
                    selected.extend(rng.choice(ids,count,replace=False).tolist())
                return dict(positions=pos.astype('float32'),sizes=sizes.astype('float32'),rotations=rotations.astype('float32'),
                            active=active,count=np.int64(n),kind=np.int64(KINDS.index(kind)),family=np.array([seed,index],np.int64)),selected
            except ValueError as e:self.rejections[str(e)]=self.rejections.get(str(e),0)+1
        raise RuntimeError(f'No valid family with all pose bands: {seed}/{index}/{n}/{kind}')

    def observation(self,truth,q):
        # Preserve settled object state; checker's frozen empty scene is not used here.
        self.d.qpos[self.qadr]=q;self.d.qvel[:]=0;self.env.sim.forward()
        images=[];rays=[];visible=np.zeros((5,3),np.float32);poses=[];robot_fraction=[]
        robot_ids=[i for i in range(self.m.ngeom) if (self.m.geom(i).name or '').startswith(('robot0_','gripper0_'))]
        for view,cam in enumerate(CAMS):
            rgb=self.env.sim.render(width=160,height=160,camera_name=cam)[::-1].copy()
            if rgb.max()<20 or rgb.mean()<1:raise RuntimeError('Invalid rendered RGB')
            images.append(rgb)
            seg=self.env.sim.render(width=160,height=160,camera_name=cam,segmentation=True)[::-1]
            robot_fraction.append(float(np.isin(seg[:,:,1],robot_ids).mean()))
            cid=self.m.camera(cam).id;R=self.d.cam_xmat[cid].reshape(3,3).copy();origin=self.d.cam_xpos[cid].copy()
            poses.append(dict(position=origin.tolist(),rotation=R.tolist()))
            focal=80/np.tan(np.deg2rad(self.m.cam_fovy[cid]/2));u,v=np.meshgrid(np.arange(20)*8+.5,np.arange(20)*8+.5)
            local=np.stack([(u-80)/focal,-(v-80)/focal,-np.ones_like(u)],axis=-1)
            directions=local@R.T;directions/=np.linalg.norm(directions,axis=-1,keepdims=True)
            rays.append(np.concatenate([directions,np.broadcast_to((origin-ORIGIN)/.1,directions.shape)],axis=-1))
            for i in np.flatnonzero(truth['active']):
                try:
                    self.m.geom_group[:]=5;self.m.geom_group[self.geoms[i]]=self.groups[self.geoms[i]]
                    isolated=self.env.sim.render(width=160,height=160,camera_name=cam,segmentation=True)[::-1]
                    mask=np.isin(isolated[:,:,1],self.geoms[i])&(isolated[:,:,0]==int(mujoco.mjtObj.mjOBJ_GEOM))
                    numerator=(np.isin(seg[:,:,1],self.geoms[i])&(seg[:,:,0]==int(mujoco.mjtObj.mjOBJ_GEOM))).sum()
                    visible[i,view]=min(1.,float(numerator)/max(1,int(mask.sum())))
                finally:self.m.geom_group[:]=self.groups
        return dict(images=np.asarray(images,np.uint8),rays=np.asarray(rays,np.float32),visibility=visible,
                    camera_positions=np.array([p['position'] for p in poses],np.float32),
                    camera_rotations=np.array([p['rotation'] for p in poses],np.float32),
                    robot_fraction=np.asarray(robot_fraction,np.float32))

    def family(self,seed,index,folder,ood=False,camera_ood=False):
        truth,selected=self.setup_family(seed,index,ood,camera_ood);episode=f'{seed}-{index}';revision=episode+'-static'
        folder.mkdir(parents=True,exist_ok=False);journal=RequestJournal(folder/'capture_requests.jsonl')
        rows=[];source=['initial-fixed-left','initial-fixed-right','initial-wrist']
        for at,j in enumerate(selected):
            entry=self.bank[j];pose=pose_from_mujoco(entry['position'],entry['rotation'],self.T_world_base)
            req=None
            if at:
                req=CaptureRequest.new(episode_id=episode,scene_revision=revision,source_observation_ids=source,
                                      desired_camera_pose=pose,reason='training_view_coverage_'+entry['band'],
                                      model_revision='data_collection_no_learned_requester',calibration_id='sim-calibration-'+episode)
                journal.create(req)
                journal.decision(decision_id=req.request_id+'-decision',episode_id=episode,scene_revision=revision,
                                 source_observation_ids=source,needs_reobserve=True,request_image=True,
                                 reason='scheduled_training_coverage_not_model_uncertainty',request_id=req.request_id,candidate_id=str(j))
                journal.transition(req.request_id,'planned',scene_revision=revision,plan_id=f'bank-{j}',
                                   planner_revision='static_self_certified_swept_object_aabb_v1',planning_backend='sim_reference',
                                   joint_positions_rad=entry['q'].tolist(),planned_camera_pose=asdict(pose))
            row=self.observation(truth,entry['q']);rows.append(row)
            Image.fromarray(row['images'][2]).save(folder/f'wrist_{at}.png')
            if req:
                actual=pose_from_mujoco(row['camera_positions'][2],row['camera_rotations'][2],self.T_world_base)
                journal.transition(req.request_id,'captured',scene_revision=revision,observation_id=f'wrist-{at}',
                                   calibration_id=req.calibration_id,image_uri=f'wrist_{at}.png',
                                   actual_camera_pose=asdict(actual),captured_at=utc_now())
            else:journal.decision(decision_id=episode+'-initial',episode_id=episode,scene_revision=revision,
                                  source_observation_ids=source,needs_reobserve=False,request_image=False,reason='initial_context')
        result={k:np.stack([r[k] for r in rows]) for k in rows[0]}
        result.update(truth);result['pose_ids']=np.array(selected,np.int64)
        result['joint_positions']=np.stack([self.bank[i]['q'] for i in selected]).astype('float32')
        (folder/'calibration.json').write_text(json.dumps(dict(T_world_base=self.T_world_base.tolist(),
            camera_names=CAMS,simulated_static_scene=True,planning_backend='sim_reference',pose_ids=selected,
            images_array_index='[family, pose, camera, y, x, rgb]',journal_intents='scheduled coverage, not learned requests'),indent=2))
        return result
