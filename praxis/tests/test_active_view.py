"""Safety-relevant regressions; no model fitting or optimizer is imported."""
from pathlib import Path
import sys,time
import numpy as np
import pytest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'praxis/src'));sys.path.insert(0,str(ROOT/'experiments/visual_scene_v2_20261101'))
from scene_data import Generator
from active_view.geometry import Box,convex_gap,Hull,hull_data
from active_view.collision import World,ArmChecker,reference_world
from active_view.planner import Plan,Planner,timed_samples,execute_kinematic
from active_view.visual_map import VoxelMap,Observation,reference_difference,FREE,UNKNOWN


@pytest.fixture(scope='module')
def generator():
    g=Generator();g.scene(301,3,force_count=3)
    yield g
    g.close()


@pytest.fixture
def checker(generator):
    return ArmChecker(generator.m,generator.d,reference_world(generator.m,generator.d))


def test_home_all_links_and_locked_fingers(checker):
    assert checker.check(checker.q0).valid
    assert len(checker.joints)==7
    assert len(checker.local)==15
    assert any(x['name']=='camera_housing_proxy' for x in checker.local)
    assert any('finger' in x['name'] for x in checker.local)


def test_joint_limits(checker):
    q=checker.q0.copy();q[3]=checker.limits[3,1]+.1
    assert checker.check(q).reason=='joint_limit'


def test_elbow_obstacle_even_with_clear_camera(checker):
    shape=next(b for b in checker.robot_boxes(checker.q0) if b.name=='robot0_link3_collision')
    camera,_=checker.camera_pose(checker.q0)
    assert np.linalg.norm(camera-shape.center)>.15
    checker.world.boxes.append(Box(shape.center,np.full(3,.012),np.eye(3),'elbow_obstacle'))
    result=checker.check(checker.q0)
    assert not result.valid and result.reason=='world_collision_or_margin'
    assert not result.pair[0].startswith('camera')


def test_camera_housing_has_real_volume(checker):
    camera=next(b for b in checker.robot_boxes(checker.q0) if b.name=='camera_housing_proxy')
    found=False
    for axis in range(3):
        for sign in (-1,1):
            p=camera.center+camera.rotation[:,axis]*camera.half[axis]*sign*.8
            checker.world.boxes.append(Box(p,np.full(3,.002),np.eye(3),'camera_only_obstacle'))
            result=checker.check(checker.q0);checker.world.boxes.pop()
            if not result.valid and result.pair[0].startswith('camera'):found=True;break
        if found:break
    assert found,'Camera proxy is not checked separately from arm meshes'


def test_midpath_collision_with_free_endpoints(checker):
    q=checker.q0.copy();a=q.copy();b=q.copy();a[0]-=.4;b[0]+=.4
    p,_=checker.camera_pose(q);checker.world.boxes.append(Box(p,np.full(3,.020),np.eye(3),'midpath_obstacle'))
    assert checker.check(a).valid and checker.check(b).valid
    assert not checker.check(q).valid
    assert not checker.edge(a,b)


def test_certified_detour(checker):
    q=checker.q0.copy();a=q.copy();b=q.copy();a[0]-=.4;b[0]+=.4
    p,_=checker.camera_pose(q);checker.world.boxes.append(Box(p,np.full(3,.020),np.eye(3),'midpath_obstacle'))
    route=Planner(checker,seed=42).path(a,b,seconds=12.,max_nodes=250)
    assert route is not None
    assert len(route.waypoints)>2
    assert all(checker.edge(x,y) for x,y in zip(route.waypoints[:-1],route.waypoints[1:]))


def test_unknown_cannot_be_bypassed_by_complete_flag(checker):
    checker.world=World([],source='visual',complete=True,max_age=60.)
    assert checker.check(checker.q0).reason=='unknown_world_coverage'


def test_stale_map_blocks_motion(checker):
    checker.world.timestamp=time.monotonic()-10;checker.world.max_age=2.
    assert checker.check(checker.q0).reason=='stale_world_map'


def test_map_revision_blocks_execution_before_move(checker):
    q=checker.q0.copy();target=q.copy();target[0]+=.01
    route=Plan([q,target],checker.world.version,checker.world.source,0)
    checker.world.version+=1;captured=[]
    with pytest.raises(RuntimeError,match='Map changed'):execute_kinematic(checker,route,lambda *a:captured.append(a))
    assert not captured


def test_time_scaling_joint_velocity_and_acceleration():
    a=np.zeros(7);b=np.array([.3,-.2,.1,.2,0,0,.1]);p=Plan([a,b],1,'reference',0)
    samples=timed_samples(p,dt=.002);t=np.array([s[0] for s in samples]);q=np.array([s[1] for s in samples])
    v=np.gradient(q,t,axis=0);acc=np.gradient(v,t,axis=0)
    assert abs(v).max()<.351
    assert abs(acc).max()<.501
    assert np.allclose(q[0],a) and np.allclose(q[-1],b)


def test_visual_carving_requires_observed_background_and_depth():
    size=80;K=np.array([[70.,0,40],[0,70.,40],[0,0,1.]])
    obs=Observation(np.ones((size,size),bool),np.zeros((size,size),bool),np.ones((size,size),bool),
                    np.full((size,size),2.),K,np.eye(3),np.array([0.,0.,1.]))
    grid=VoxelMap([-.1,-.1,.4],[.1,.1,.6],resolution=.05);grid.integrate([obs])
    assert (grid.labels==FREE).all()
    obs.valid[:]=False;grid.integrate([obs]);assert (grid.labels==UNKNOWN).all()
    assert not grid.ray_clear(np.array([0.,0.,.42]),np.array([0.,0.,.58]))


def test_rgb_difference_never_uses_object_poses():
    empty=np.full((30,30,3),200,np.uint8);rgb=empty.copy();rgb[10:20,10:20]=30
    background,foreground=reference_difference(rgb,empty,np.ones((30,30),bool))
    assert foreground[15,15] and not background[15,15]
    assert background[4,4]


def test_visual_map_revision_requires_a_new_snapshot(checker):
    grid=VoxelMap([-1,-1,0],[1,1,2],resolution=.5)
    grid.labels[:]=FREE;grid.version=1;grid.timestamp=time.monotonic()
    checker.world=grid.as_world(max_age=60.)
    grid.version=2
    assert checker.check(checker.q0).reason=='map_revision_changed'


def test_convex_gap_does_not_accept_overlapping_boxes():
    a=Box(np.zeros(3),np.full(3,.1),np.eye(3));b=Box(np.array([.15,0,0]),np.full(3,.1),np.eye(3))
    assert convex_gap(a,b)<0
    b.center[0]=.25;assert 0<convex_gap(a,b)<=.05+1e-7
