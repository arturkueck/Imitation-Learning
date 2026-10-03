/* Reine Rechenmodelle. Keine Roboterdaten und keine Paperreproduktion. */
(function (root) {
  'use strict';
  const square=x=>x*x;
  function rng(seed=1){let s=seed>>>0;return()=>{s=(1664525*s+1013904223)>>>0;return(s+.5)/4294967296;};}
  function normal(random){return Math.sqrt(-2*Math.log(random()))*Math.cos(2*Math.PI*random());}
  function recurrence(q,b,e0=.1,n=25){let e=e0;const values=[{x:0,y:e}];for(let t=1;t<=n;t++){e=q*e+b;values.push({x:t,y:e});}return values;}
  function eig(c,d){const p=c*d;return p>=0?{real:[-1+Math.sqrt(p),-1-Math.sqrt(p)],imag:0}:{real:[-1,-1],imag:Math.sqrt(-p)};}
  function rk4(fn,initial,dt=.02,n=500){let z=initial.slice();const out=[{t:0,z:z.slice()}];for(let j=1;j<=n;j++){
    const k1=fn(z),k2=fn(z.map((v,i)=>v+dt*k1[i]/2)),k3=fn(z.map((v,i)=>v+dt*k2[i]/2)),k4=fn(z.map((v,i)=>v+dt*k3[i]));
    z=z.map((v,i)=>v+dt*(k1[i]+2*k2[i]+2*k3[i]+k4[i])/6);out.push({t:j*dt,z:z.slice()});
    if(z.some(v=>!Number.isFinite(v)||Math.abs(v)>50))break;
  }return out;}
  function coupling(c,d,product=false){return rk4(z=>product?[-z[0]+c*z[0]*z[1],-z[1]]:[-z[0]+c*z[1],d*z[0]-z[1]],product?[.25,1]:[.2,.8]);}
  const expert=x=>-x-.6*x*x*x;
  const nominal=()=>Array.from({length:24},(_,i)=>{const x=-.2+.4*i/23;return{x,u:expert(x)};});
  function fit(data){
    // Mittelwertloss + 0.002*(w1^2+(w3-1.2)^2).
    // Der absichtlich ungünstige Kubikprior macht fehlende Datenabdeckung sichtbar.
    const r=.002,n=data.length;let a=r,b=0,c=r,v=0,w=r*1.2;
    for(const p of data){const f=p.x,g=p.x**3;a+=f*f/n;b+=f*g/n;c+=g*g/n;v+=f*p.u/n;w+=g*p.u/n;}
    const det=a*c-b*b;return{w1:(v*c-b*w)/det,w3:(a*w-b*v)/det};
  }
  const predict=(model,x)=>model.w1*x+model.w3*x*x*x;
  function rollout(model,start,n=50){let x=start;const trace=[{x:0,y:x}];for(let j=1;j<=n;j++){x+=.08*predict(model,x);trace.push({x:j,y:x});if(Math.abs(x)>4)break;}return trace;}
  function collection(rounds=0,sigma=3,start=1.4,seed=7){
    const base=nominal(),bc=fit(base);let daggerData=base.slice(),dagger=bc;
    for(let i=0;i<rounds;i++){const trace=rollout(dagger,start);daggerData.push(...trace.filter(p=>Math.abs(p.y)<=4).map(p=>({x:p.y,u:expert(p.y)})));dagger=fit(daggerData);}
    const random=rng(seed),dartData=base.slice(),executed=[];let x=.1;
    for(let j=0;j<120;j++){const u=expert(x),noise=sigma*normal(random);dartData.push({x,u});executed.push({x,u,label:u,execution:u+noise});x+=.08*(u+noise);}
    return{base,bc,dagger,daggerData,dart:fit(dartData),dartData,executed};
  }
  function chunk(horizon=4,ensemble=false,m=.25,n=40){
    let state=0,queue=[],plans=[];const points=[{x:0,y:state}],target=[],actions=[];
    for(let t=0;t<n;t++){
      const goal=t<12?1:-1;target.push({x:t,y:goal});
      if(ensemble||queue.length===0){let p=state;const chunk=[];for(let k=0;k<10;k++){p+=.25*(goal-p);chunk.push(p);}if(ensemble)plans.push({issued:t,values:chunk});else queue=chunk.slice(0,horizon);}
      let action;
      if(ensemble){plans=plans.filter(p=>t-p.issued<10);let sum=0,total=0;plans.forEach((p,i)=>{const w=Math.exp(-m*i);sum+=w*p.values[t-p.issued];total+=w;});action=sum/total;}
      else action=queue.shift();
      state=action;actions.push(action);points.push({x:t+1,y:state});
    }
    target.push({x:n,y:-1});return{points,target,actions};
  }
  function score(a,v){const l=-square(a+1)/(2*v),r=-square(a-1)/(2*v),max=Math.max(l,r),pl=Math.exp(l-max),pr=Math.exp(r-max);return(pl*(-1-a)+pr*(1-a))/(v*(pl+pr));}
  function diffusion(seed=11,n=100,count=120){const random=rng(seed),values=Array.from({length:count},()=>1.2*normal(random)),history=[values.slice()];for(let j=0;j<n;j++){
    const sigma=1-j/Math.max(1,n-1),v=.18**2+sigma*sigma,h=.01;
    for(let i=0;i<count;i++)values[i]+=h*score(values[i],v)+Math.sqrt(2*h)*normal(random);
    history.push(values.slice());
  }return history;}
  function covariance(sx,sy,rho,T,alpha,seed=13){const raw=[[sx*sx,rho*sx*sy],[rho*sx*sy,sy*sy]],scale=alpha/(T*(raw[0][0]+raw[1][1])),matrix=raw.map(row=>row.map(v=>v*scale)),random=rng(seed),samples=[];
    for(let i=0;i<140;i++){const z1=normal(random),z2=normal(random);samples.push({x:Math.sqrt(scale)*sx*z1,y:Math.sqrt(scale)*sy*(rho*z1+Math.sqrt(1-rho*rho)*z2)});}return{matrix,samples,scale,trace:matrix[0][0]+matrix[1][1]};
  }
  const api={rng,normal,recurrence,eig,rk4,coupling,expert,nominal,fit,predict,rollout,collection,chunk,score,diffusion,covariance};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.LearningModels=api;
})(typeof window==='undefined'?globalThis:window);
