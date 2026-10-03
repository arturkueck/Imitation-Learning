'use strict';
const assert=require('node:assert/strict'),M=require('./engine.js');
const close=(a,b,tol=1e-7)=>assert.ok(Math.abs(a-b)<tol,`${a} != ${b}`);
close(M.recurrence(.7,0,.1,10).at(-1).y,.1*.7**10);
close(M.recurrence(.7,.03,.2,10).at(-1).y,.1+(.2-.1)*.7**10);
close(M.eig(2,1).real[0],-1+Math.sqrt(2));assert.ok(M.eig(0,1).real.every(x=>x<0));
const no=M.coupling(0,0);close(no.at(-1).z[0],.2*Math.exp(-10),1e-8);
const prod=M.coupling(2,0,true);for(const p of prod){close(p.z[1],Math.exp(-p.t),1e-7);close(p.z[0],.25*Math.exp(-p.t+2*(1-Math.exp(-p.t))),1e-7);}
assert.ok(Math.hypot(...M.coupling(4,0)[20].z)>Math.hypot(.2,.8),'Transient norm growth expected');
const data=M.collection(1,3,1.4),bc=M.rollout(data.bc,1.4),dag=M.rollout(data.dagger,1.4);
assert.ok(bc.length<51,'Constructed BC prior must show extrapolation problem');assert.equal(dag.length,51);assert.ok(Math.abs(dag.at(-1).y)<.1);
assert.ok(data.executed.some(p=>p.execution!==p.label));for(const p of data.dartData)close(p.u,M.expert(p.x));
close(M.score(0,.5),0);assert.ok(M.score(.8,.18**2)>0);assert.ok(M.score(-.8,.18**2)<0);
const diffusion=M.diffusion(11),final=diffusion.at(-1);assert.equal(diffusion.length,101);assert.equal(final.length,120);assert.ok(final.every(Number.isFinite));assert.ok(final.some(x=>x<-.5)&&final.some(x=>x>.5));assert.ok(final.filter(x=>Math.abs(x)<.3).length<12);
assert.deepEqual(M.diffusion(11),diffusion,'Fixed seed must reproduce sample paths');
const cov=M.covariance(.2,.4,.7,20,1);close(cov.trace*20,1);assert.ok(cov.matrix[0][0]*cov.matrix[1][1]-cov.matrix[0][1]**2>0);
const ch=M.chunk(8),fast=M.chunk(1);assert.ok(ch.actions[12]>0);assert.ok(fast.actions[12]<fast.points[12].y);
for(const h of [1,4,10])for(const en of [false,true])assert.ok(M.chunk(h,en,.3).actions.every(Number.isFinite));
console.log('PASS: recurrence, analytical eigenvalues, RK4 against exact solutions, transient growth, label distinction, DAgger training, score, seeded sampler, covariance budget, chunk feedback.');
