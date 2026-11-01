import {test} from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import {buildSnapshot,localTrainingRequest,inside} from './training-monitor.mjs';

async function fixture(t){
 const root=await fs.mkdtemp(path.join(os.tmpdir(),'atlas-training-'));
 t.after(()=>fs.rm(root,{recursive:true,force:true}));
 await fs.mkdir(path.join(root,'monitor'));await fs.mkdir(path.join(root,'run'));
 const write=(name,data)=>fs.writeFile(path.join(root,name),JSON.stringify(data));
 await write('monitor/training-runs.json',{schemaVersion:1,runs:[{id:'test',category:'vision',method:'supervised',kind:'training',directory:'run',config:'config.json',artifacts:[]}]});
 await write('run/config.json',{seeds:[1],lr:.001,token:'must-not-export',checkpoint_path:'F:\\private\\weights.pth'});
 await write('run/curves.json',[{seed:1,arm:'fixed',updates:20,train_mse:.1,validation_mse:.2}]);
 return {root,write};
}
test('cancelled run stays cancelled despite a recent training heartbeat',async t=>{
 const {root,write}=await fixture(t);await write('run/status.json',{stage:'train',heartbeat_unix:Date.now()/1000});await write('run/user_stop.json',{reason:'user'});
 const data=await buildSnapshot(root);assert.equal(data.runs[0].status,'cancelled');assert.equal(data.runs[0].models[0].step,20);
 assert.equal(data.runs[0].models[0].train,.1);assert.equal(data.runs[0].models[0].validation,.2);
 assert.ok(!JSON.stringify(data).includes('must-not-export'));assert.ok(!JSON.stringify(data).includes('private'));
});
test('stale status is never presented as verified running',async t=>{
 const {root,write}=await fixture(t);await write('run/status.json',{stage:'train',heartbeat_unix:Date.now()/1000-600});
 assert.equal((await buildSnapshot(root)).runs[0].status,'stale');
});
test('malformed metrics are reported rather than replaced with invented progress',async t=>{
 const {root}=await fixture(t);await fs.writeFile(path.join(root,'run/curves.json'),'{broken');
 const r=(await buildSnapshot(root)).runs[0];assert.equal(r.models.length,0);assert.equal(r.lastStep,null);assert.ok(r.readErrors.includes('Nicht lesbar: curves.json'));
});
test('local endpoint rejects foreign Host and does not expose arbitrary artifact paths',async()=>{
 const response={status:null,writeHead(code){this.status=code;return this},end(){return this}};
 assert.equal(await localTrainingRequest({headers:{host:'evil.example'},method:'GET'},response,'/api/trainings','unused'),true);
 assert.equal(response.status,403);assert.throws(()=>inside('F:\\workspace','../../secret'));
});
