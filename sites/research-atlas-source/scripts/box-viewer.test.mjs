import test from 'node:test';
import assert from 'node:assert/strict';
import {boxCorners,readScene,projectPoint} from '../public/box-viewer.js';
const box={center:[.1,.2,.83],size:[.04,.06,.08],rotation:[[0,-1,0],[1,0,0],[0,0,1]]};
test('cuboid rotation preserves world center and actual dimensions',()=>{
 const pts=boxCorners(box),center=[0,1,2].map(i=>pts.reduce((s,p)=>s+p[i],0)/8);
 center.forEach((v,i)=>assert.ok(Math.abs(v-box.center[i])<1e-12));
 const spans=[0,1,2].map(i=>Math.max(...pts.map(p=>p[i]))-Math.min(...pts.map(p=>p[i])));
 spans.forEach((v,i)=>assert.ok(Math.abs(v-[.06,.04,.08][i])<1e-12));
});
test('scene includes all acquired states without aligning their positions',()=>{
 const later={...box,center:[.3,.2,.83]},scene=readScene({ground_truth:[box],initial_prediction:[box],updated_predictions:[[later]]});
 assert.equal(scene.updates.length,1);assert.equal(scene.updates[0][0].center[0],.3);assert.ok(scene.high[0]>.3);
 assert.throws(()=>boxCorners({...box,size:[0,1,1]}));assert.throws(()=>readScene({}));
});
test('perspective orbit changes projected position but keeps target centered',()=>{
 const center=[0,0,0];
 for(const yaw of [0,1,2]){const p=projectPoint(center,center,yaw,.5,2,800,500);assert.equal(p.x,400);assert.ok(Math.abs(p.y-250)<1e-10)}
 const a=projectPoint([.2,0,0],center,0,.5,2,800,500),b=projectPoint([.2,0,0],center,1,.5,2,800,500);
 assert.ok(Math.abs(a.x-b.x)>10);
});
test('valid empty scenes remain inspectable instead of being reported as load failures',()=>{
 const scene=readScene({ground_truth:[],predictions:[]});assert.equal(scene.empty,true);assert.equal(scene.truth.length,0);assert.ok(scene.radius>0);
});
test('camera view uses actual optical axes and never transforms object coordinates',()=>{
 const inspection={focus:[.1,.2,.83],start:{position:[-.2,0,1.1],rotation:[[1,0,0],[0,1,0],[0,0,1]]},goal:{position:[.4,-.2,.94],rotation:[[1,0,0],[0,1,0],[0,0,1]]},path:[[-.2,0,1.1],[.4,-.2,.94]]};
 const scene=readScene({ground_truth:[box],predictions:[box],inspection_camera:inspection});
 assert.deepEqual(scene.truth[0].center,box.center);assert.deepEqual(scene.inspection.goal.position,inspection.goal.position);assert.ok(scene.cameraBounds.radius>scene.radius);
});
