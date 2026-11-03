"""Persistent capture intent, planned pose, actual image pose and outcome.

No robot commands or learned model live here. Logging 'planned' is a caller's
assertion, not a collision certificate. Desired camera optical pose is always
expressed in robot_base, metres, quaternion wxyz, OpenCV camera axes.
"""
from dataclasses import dataclass,asdict
from datetime import datetime,timezone
from pathlib import Path,PurePosixPath
import hashlib,json,os,uuid
import numpy as np
from scipy.spatial.transform import Rotation

OPTICAL_FRAME='opencv_x_right_y_down_z_forward'
STATUSES={'requested':{'planned','blocked','cancelled'},'planned':{'captured','blocked','failed','cancelled'},
          'captured':{'evaluated'},'evaluated':set(),'blocked':set(),'failed':set(),'cancelled':set()}


def utc_now():return datetime.now(timezone.utc).isoformat()


def vector(value,length):
    a=np.asarray(value,dtype=float)
    if a.shape!=(length,) or not np.isfinite(a).all():raise ValueError(f'Expected finite vector of length {length}')
    return a


def nonempty(value,name):
    if not isinstance(value,str) or not value.strip():raise ValueError(f'Missing {name}')
    return value


@dataclass(frozen=True)
class CameraPose:
    position_m:tuple
    quaternion_wxyz:tuple
    frame_id:str='robot_base'
    optical_frame:str=OPTICAL_FRAME

    def __post_init__(self):
        p=vector(self.position_m,3);q=vector(self.quaternion_wxyz,4)
        if abs(np.linalg.norm(q)-1)>1e-6:raise ValueError('Quaternion must be unit length')
        if self.frame_id!='robot_base' or self.optical_frame!=OPTICAL_FRAME:raise ValueError('Explicit robot_base / OpenCV optical frame required')
        object.__setattr__(self,'position_m',tuple(map(float,p)))
        object.__setattr__(self,'quaternion_wxyz',tuple(map(float,q if q[0]>=0 else -q)))

    def rotation(self):
        w,x,y,z=self.quaternion_wxyz
        return Rotation.from_quat([x,y,z,w]).as_matrix()


def pose_from_mujoco(camera_position_world,camera_rotation_world,T_world_base):
    """Explicit world->base conversion and MuJoCo -Z -> OpenCV +Z optical axes.

    T_world_base maps base coordinates into world coordinates. Never assume
    world and robot base are the same frame.
    """
    transform=np.asarray(T_world_base,dtype=float);rotation=np.asarray(camera_rotation_world,dtype=float)
    if transform.shape!=(4,4) or rotation.shape!=(3,3):raise ValueError('Invalid transform dimensions')
    if not np.isfinite(transform).all() or not np.isfinite(rotation).all():raise ValueError('Nonfinite transform')
    if not np.allclose(transform[3],[0,0,0,1],atol=1e-8):raise ValueError('Invalid homogeneous transform')
    for R in [transform[:3,:3],rotation]:
        if not np.allclose(R.T@R,np.eye(3),atol=1e-6) or not np.isclose(np.linalg.det(R),1,atol=1e-6):raise ValueError('Expected proper rotation')
    R_base_world=transform[:3,:3].T
    p=R_base_world@(vector(camera_position_world,3)-transform[:3,3])
    R=R_base_world@rotation@np.diag([1.,-1.,-1.])
    x,y,z,w=Rotation.from_matrix(R).as_quat()
    return CameraPose(tuple(p),(w,x,y,z))


def pose_error(desired,actual):
    return dict(position_m=float(np.linalg.norm(np.asarray(desired.position_m)-actual.position_m)),
                angle_rad=float(Rotation.from_matrix(desired.rotation().T@actual.rotation()).magnitude()))


@dataclass(frozen=True)
class CaptureRequest:
    request_id:str
    episode_id:str
    scene_revision:str
    source_observation_ids:tuple
    desired_camera_pose:CameraPose
    reason:str
    target_scope:str='scene'
    target_track_ids:tuple=()
    model_revision:str='untrained_design'
    calibration_id:str='unspecified'
    created_at:str=''
    example_only:bool=False

    def __post_init__(self):
        for name in ['request_id','episode_id','scene_revision','reason','model_revision','calibration_id']:
            nonempty(getattr(self,name),name)
        if self.calibration_id=='unspecified':raise ValueError('Calibration revision required')
        if self.target_scope not in ['scene','objects']:raise ValueError('Invalid target scope')
        if self.target_scope=='objects' and not self.target_track_ids:raise ValueError('Object scope requires predicted track IDs')
        if not isinstance(self.source_observation_ids,(tuple,list)) or not isinstance(self.target_track_ids,(tuple,list)):raise ValueError('Observation/track IDs must be sequences')
        if not isinstance(self.example_only,bool):raise ValueError('example_only must be boolean')
        if not self.source_observation_ids:raise ValueError('Source observations required')
        for name in list(self.source_observation_ids)+list(self.target_track_ids):nonempty(name,'observation/track ID')
        if not isinstance(self.desired_camera_pose,CameraPose):raise ValueError('Typed camera pose required')
        timestamp=self.created_at or utc_now();parsed=datetime.fromisoformat(timestamp)
        if parsed.tzinfo is None:raise ValueError('Timestamp must include timezone')
        object.__setattr__(self,'created_at',timestamp)
        object.__setattr__(self,'source_observation_ids',tuple(self.source_observation_ids))
        object.__setattr__(self,'target_track_ids',tuple(self.target_track_ids))

    @classmethod
    def new(cls,**kwargs):return cls(request_id=str(uuid.uuid4()),**kwargs)


def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False)


class RequestJournal:
    """Append-only, hash-chained JSONL. Exclusive writer, flush+fsync on append.

    Locks fail immediately if another writer exists. Stale locks and corrupt
    records are never silently removed/repaired. Hash chaining detects accidental
    changes, not an attacker able to rewrite the entire journal.
    """
    def __init__(self,path):
        self.path=Path(path);self.lock=self.path.with_suffix(self.path.suffix+'.lock')

    def records(self):
        if not self.path.exists():return []
        rows=[];previous=None
        content=self.path.read_text(encoding='utf-8')
        if content and not content.endswith('\n'):raise ValueError('Incomplete journal tail')
        for line in content.splitlines():
            if not line:raise ValueError('Empty/incomplete journal record')
            row=json.loads(line);checksum=row.pop('sha256')
            if row['sequence']!=len(rows) or row['previous_sha256']!=previous:raise ValueError('Broken journal ordering')
            if hashlib.sha256(canonical(row).encode()).hexdigest()!=checksum:raise ValueError('Journal checksum mismatch')
            row['sha256']=checksum;rows.append(row);previous=checksum
        return rows

    def state(self,request_id):
        records=[r for r in self.records() if r['request_id']==request_id and r['status']!='decision']
        if not records:raise KeyError(request_id)
        return records[-1]['status']

    def _append(self,request_id,status,payload,validate):
        self.path.parent.mkdir(parents=True,exist_ok=True)
        descriptor=os.open(self.lock,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
        try:
            os.write(descriptor,str(os.getpid()).encode());os.fsync(descriptor)
            rows=self.records();validate(rows)
            row=dict(schema_version=1,sequence=len(rows),event_id=str(uuid.uuid4()),
                     timestamp=utc_now(),request_id=request_id,status=status,payload=payload,
                     previous_sha256=rows[-1]['sha256'] if rows else None)
            row['sha256']=hashlib.sha256(canonical(row).encode()).hexdigest()
            with self.path.open('a',encoding='utf-8',newline='\n') as f:
                f.write(canonical(row)+'\n');f.flush();os.fsync(f.fileno())
            return row
        finally:
            os.close(descriptor);self.lock.unlink()

    def create(self,request):
        if not isinstance(request,CaptureRequest):raise ValueError('CaptureRequest required')
        def validate(rows):
            if any(r['request_id']==request.request_id for r in rows):raise ValueError('Duplicate request ID')
        return self._append(request.request_id,'requested',asdict(request),validate)

    def decision(self,*,decision_id,episode_id,scene_revision,source_observation_ids,
                 needs_reobserve,request_image,reason,request_id=None,
                 need_probability=None,expected_net_gain_mm=None,candidate_id=None):
        for name,value in [('decision_id',decision_id),('episode_id',episode_id),('scene_revision',scene_revision),('reason',reason)]:nonempty(value,name)
        if not isinstance(needs_reobserve,bool) or not isinstance(request_image,bool):raise ValueError('Boolean decisions required')
        if not source_observation_ids or isinstance(source_observation_ids,str):raise ValueError('Observation sequence required')
        for value in source_observation_ids:nonempty(value,'observation ID')
        if request_image and (not needs_reobserve or request_id is None):raise ValueError('Image request needs intent and request ID')
        if not request_image and request_id is not None:raise ValueError('No-request decision cannot reference a request')
        if need_probability is not None and (not np.isfinite(need_probability) or not 0<=need_probability<=1):raise ValueError('Invalid need probability')
        if expected_net_gain_mm is not None and not np.isfinite(expected_net_gain_mm):raise ValueError('Invalid expected gain')
        if candidate_id is not None:nonempty(candidate_id,'candidate_id')
        payload=dict(decision_id=decision_id,episode_id=episode_id,scene_revision=scene_revision,
                     source_observation_ids=list(source_observation_ids),needs_reobserve=needs_reobserve,
                     request_image=request_image,reason=reason,need_probability=need_probability,
                     expected_net_gain_mm=expected_net_gain_mm,candidate_id=candidate_id)
        def validate(rows):
            if any(r['status']=='decision' and r['payload']['decision_id']==decision_id for r in rows):raise ValueError('Duplicate decision ID')
            if request_image:
                initial=next((r for r in rows if r['request_id']==request_id and r['status']=='requested'),None)
                if initial is None:raise ValueError('Linked request must already exist')
                for key in ['episode_id','scene_revision','source_observation_ids']:
                    if initial['payload'][key]!=payload[key]:raise ValueError('Decision/request context mismatch')
        return self._append(request_id,'decision',payload,validate)

    def transition(self,request_id,status,*,scene_revision,**payload):
        if status not in STATUSES or status=='requested':raise ValueError('Invalid transition status')
        def validate(rows):
            history=[r for r in rows if r['request_id']==request_id and r['status']!='decision']
            if not history:raise KeyError(request_id)
            initial=history[0]['payload']
            if scene_revision!=initial['scene_revision']:raise ValueError('Scene changed; new request/replan required')
            if status not in STATUSES[history[-1]['status']]:raise ValueError('Invalid state transition')
            if status=='planned':
                nonempty(payload.get('plan_id'),'plan_id');nonempty(payload.get('planner_revision'),'planner_revision')
                if payload.get('planning_backend') not in ['sim_reference','visual_verified','known_static_and_visual']:raise ValueError('Explicit planning backend required')
                q=vector(payload.get('joint_positions_rad'),7);payload['joint_positions_rad']=q.tolist()
                # Planned camera pose must be explicit; it can differ from desire.
                pose=CameraPose(**payload['planned_camera_pose']);payload['planned_camera_pose']=asdict(pose)
            elif status=='captured':
                nonempty(payload.get('observation_id'),'observation_id');nonempty(payload.get('calibration_id'),'calibration_id')
                if payload['calibration_id']!=initial['calibration_id']:raise ValueError('Calibration changed; revalidate request')
                image=nonempty(payload.get('image_uri'),'image_uri');parts=PurePosixPath(image)
                if parts.is_absolute() or '..' in parts.parts or '\\' in image or ':' in image:raise ValueError('Relative dataset image URI required')
                actual=CameraPose(**payload['actual_camera_pose']);desired=CameraPose(**initial['desired_camera_pose'])
                payload['actual_camera_pose']=asdict(actual);payload['pose_error']=pose_error(desired,actual)
                captured_at=nonempty(payload.get('captured_at'),'captured_at');stamp=datetime.fromisoformat(captured_at)
                if stamp.tzinfo is None:raise ValueError('Capture timestamp needs timezone')
                if stamp<datetime.fromisoformat(initial['created_at']):raise ValueError('Image predates request')
            elif status=='evaluated':
                nonempty(payload.get('evaluation_id'),'evaluation_id')
                if payload.get('decision') not in ['accept','hold']:raise ValueError('accept/hold decision required')
            else:nonempty(payload.get('reason'),'reason')
        # Reject unknown top-level payloads that could silently mutate intent or
        # smuggle training truth into the operational request history.
        allowed={'planned':{'plan_id','planner_revision','planning_backend','joint_positions_rad','planned_camera_pose'},
                 'captured':{'observation_id','calibration_id','image_uri','actual_camera_pose','captured_at'},
                 'evaluated':{'evaluation_id','decision'},'blocked':{'reason'},'failed':{'reason'},'cancelled':{'reason'}}
        if set(payload)-allowed[status]:raise ValueError('Unexpected operational payload field')
        payload['scene_revision']=scene_revision
        return self._append(request_id,status,payload,validate)
