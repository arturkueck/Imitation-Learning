// Perspective 3D viewer for measured cuboids. No model inference or fitted alignment.
const C={truth:'#23d9eb',initial:'#ff9b42',updated:'#67e889'};
const SIGNS=[[-1,-1,-1],[-1,-1,1],[-1,1,-1],[-1,1,1],[1,-1,-1],[1,-1,1],[1,1,-1],[1,1,1]];
const FACES=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]];
const sessions=new Map();
const dot=(a,b)=>a.reduce((v,x,i)=>v+x*b[i],0),sub=(a,b)=>a.map((x,i)=>x-b[i]);
const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];
const norm=a=>{const n=Math.hypot(...a);return a.map(x=>x/n)};
const finite=a=>Array.isArray(a)&&a.every(Number.isFinite);
const boundsOf=points=>{const low=[0,1,2].map(i=>Math.min(...points.map(p=>p[i]))),high=[0,1,2].map(i=>Math.max(...points.map(p=>p[i])));return {low,high,center:low.map((x,i)=>(x+high[i])/2),radius:Math.max(.035,Math.hypot(...sub(high,low))/2)}};

export function boxCorners(b){
 if(!finite(b.center)||b.center.length!==3||!finite(b.size)||b.size.length!==3||b.size.some(x=>x<=0)||!Array.isArray(b.rotation)||b.rotation.length!==3||b.rotation.some(r=>!finite(r)||r.length!==3))throw Error('Ungültige Boxgeometrie');
 return SIGNS.map(s=>b.center.map((x,i)=>x+b.rotation[i].reduce((n,v,j)=>n+v*s[j]*b.size[j]/2,0)));
}
export function readScene(raw){
 if(!raw||(!('ground_truth' in raw)&&!('predictions' in raw)&&!('initial_prediction' in raw)))throw Error('Ungültiges Szenenformat');
 const truth=raw.ground_truth||[],initial=raw.initial_prediction||raw.predictions||[],updates=raw.updated_predictions||[];
 if(!Array.isArray(truth)||!Array.isArray(initial)||!Array.isArray(updates)||updates.some(x=>!Array.isArray(x)))throw Error('Ungültiges Szenenformat');
 const all=[...truth,...initial,...updates.flat()];if(all.length>200)throw Error('Zu viele Boxen');
 if(!all.length)return {truth,initial,updates,low:[-.1,-.1,.8],high:[.1,.1,1],center:[0,0,.9],radius:.17,empty:true};
 const points=all.flatMap(boxCorners),scene={truth,initial,updates,...boundsOf(points)};
 if(raw.inspection_camera){
  const inspection=raw.inspection_camera;
  if(!finite(inspection.focus)||inspection.focus.length!==3||!Array.isArray(inspection.path)||inspection.path.some(p=>!finite(p)||p.length!==3))throw Error('Ungültiger Kameraweg');
  for(const pose of [inspection.start,inspection.goal]){if(!pose||!finite(pose.position)||pose.position.length!==3||!Array.isArray(pose.rotation)||pose.rotation.length!==3||pose.rotation.some(r=>!finite(r)||r.length!==3))throw Error('Ungültige Kamerapose')}
  scene.inspection=inspection;scene.cameraBounds=boundsOf([...points,...inspection.path,inspection.start.position,inspection.goal.position,inspection.focus]);
 }
 return scene;
}
export function projectPoint(point,target,yaw,pitch,distance,width,height){
 const direction=[Math.cos(pitch)*Math.cos(yaw),Math.cos(pitch)*Math.sin(yaw),Math.sin(pitch)];
 const eye=target.map((v,i)=>v+direction[i]*distance),forward=direction.map(x=>-x),right=norm(cross(forward,[0,0,1])),up=cross(right,forward),v=sub(point,eye),depth=dot(v,forward);
 if(depth<=.00001)return null;
 const focal=Math.min(width,height)*1.05;
 return {x:width/2+dot(v,right)*focal/depth,y:height/2-dot(v,up)*focal/depth,depth};
}

export function mountBoxViewer(host,url){
 let dead=false,frame=0,resize,observer,scene,state,last=0,visible=true,dirty=true,width=1,height=1,drag=null,idleUntil=0;
 const abort=new AbortController();
 host.classList.add('box-viewer');
 host.innerHTML=`<div class="viewer-toolbar"><button type="button" data-action="auto" aria-pressed="true">Automatik pausieren</button><button type="button" data-action="reset">Ansicht zurücksetzen</button><button type="button" data-action="in" aria-label="3D vergrößern">+</button><button type="button" data-action="out" aria-label="3D verkleinern">−</button><label class="viewer-step" hidden>Aufnahmezustand<select aria-label="Aufnahmezustand"></select></label></div><div class="viewer-layers"><label><input type="checkbox" data-layer="truth" checked><span style="color:${C.truth}">Simulation</span></label><label><input type="checkbox" data-layer="initial" checked><span style="color:${C.initial}">Erste Vorhersage</span></label><label data-updated hidden><input type="checkbox" data-layer="updated" checked><span style="color:${C.updated}">Nach Zusatzaufnahme</span></label></div><div class="viewer-stage"><canvas tabindex="0" aria-label="Interaktiver 3D-Abgleich. Ziehen dreht; Mausrad zoomt; rechte Maustaste verschiebt. Pfeiltasten drehen, Plus und Minus zoomen."></canvas><div class="viewer-tip" hidden></div><p class="viewer-status" role="status">3D-Szene wird geladen …</p></div><p class="muted viewer-hint">Ziehen: drehen · Mausrad: zoomen · Rechts ziehen: verschieben · Doppelklick: zurücksetzen. Langsame automatische Drehung pausiert beim Bedienen. Gleiche Weltkoordinaten in Metern; keine nachträgliche Ausrichtung.</p>`;
 const canvas=host.querySelector('canvas'),ctx=canvas.getContext('2d'),status=host.querySelector('.viewer-status'),tip=host.querySelector('.viewer-tip'),auto=host.querySelector('[data-action=auto]');
 function dispose(){if(dead)return;dead=true;abort.abort();cancelAnimationFrame(frame);resize?.disconnect();observer?.disconnect()}
 function event(el,name,fn,options={}){el.addEventListener(name,fn,{...options,signal:abort.signal})}
 function autoLabel(){auto.textContent=state.auto?'Automatik pausieren':'Automatik fortsetzen';auto.setAttribute('aria-pressed',String(state.auto))}
 function viewBounds(){return state.camera&&scene.cameraBounds?scene.cameraBounds:scene}
 function reset(){const bounds=viewBounds();state.yaw=-1.05;state.pitch=.48;state.distance=bounds.radius*3.2;state.target=[...bounds.center];dirty=true;tip.hidden=true}
 function zoom(factor){const bounds=viewBounds();state.distance=Math.max(bounds.radius*1.65,Math.min(bounds.radius*24,state.distance*factor));dirty=true;idleUntil=performance.now()+2000}
 function project(p){return projectPoint(p,state.target,state.yaw,state.pitch,state.distance,width,height)}
 function groups(){return [[scene.truth,'truth'],[scene.initial,'initial'],[state.stage?scene.updates[state.stage-1]||[]:[],'updated']].filter(([,key])=>state.layers[key])}
 function line(a,b,color='#405365',weight=1){a=project(a);b=project(b);if(!a||!b)return;ctx.beginPath();ctx.moveTo(a.x,a.y);ctx.lineTo(b.x,b.y);ctx.strokeStyle=color;ctx.lineWidth=weight;ctx.stroke()}
 function render(){
  ctx.clearRect(0,0,width,height);ctx.fillStyle='#101b28';ctx.fillRect(0,0,width,height);
  const bounds=viewBounds(),side=Math.max(...sub(bounds.high,bounds.low),.08),span=side*1.25,z=scene.low[2],x=bounds.center[0],y=bounds.center[1];
  for(let i=0;i<=8;i++){const d=-span/2+i*span/8;line([x+d,y-span/2,z],[x+d,y+span/2,z],'#263c4d');line([x-span/2,y+d,z],[x+span/2,y+d,z],'#263c4d')}
  const origin=[x-span/2,y-span/2,z];
  for(const [end,label]of [[[x+span/2,y-span/2,z],'X'],[[x-span/2,y+span/2,z],'Y'],[[x-span/2,y-span/2,z+span],'Z']]){
   line(origin,end,'#8aa0b3',1.3);const q=project(end);if(q){ctx.fillStyle='#d3dfe9';ctx.font='13px system-ui';ctx.fillText(label+' [m]',q.x+6,q.y-6)}
  }
  const faces=[],centers=[];
  for(const [boxes,key]of groups())for(const [i,b]of boxes.entries()){
   const pts=boxCorners(b).map(project);if(pts.some(p=>!p))continue;
   for(const f of FACES)faces.push({points:f.map(j=>pts[j]),depth:f.reduce((sum,j)=>sum+pts[j].depth,0)/f.length,key});
   const q=project(b.center);if(q)centers.push({...q,key,i,box:b});
  }
  faces.sort((a,b)=>b.depth-a.depth);
  for(const face of faces){ctx.beginPath();face.points.forEach((p,i)=>i?ctx.lineTo(p.x,p.y):ctx.moveTo(p.x,p.y));ctx.closePath();ctx.globalAlpha=face.key==='truth'?.10:.025;ctx.fillStyle=C[face.key];ctx.fill();ctx.globalAlpha=.8;ctx.strokeStyle=C[face.key];ctx.lineWidth=face.key==='truth'?1.1:1.5;ctx.stroke()}
  ctx.globalAlpha=1;
  for(const p of centers){ctx.strokeStyle=C[p.key];ctx.fillStyle=C[p.key];ctx.lineWidth=2;ctx.beginPath();if(p.key==='truth'){ctx.arc(p.x,p.y,3,0,Math.PI*2);ctx.fill()}else{const s=p.key==='initial'?3.5:0,t=p.key==='initial'?3.5:4;ctx.moveTo(p.x-(s||t),p.y-s);ctx.lineTo(p.x+(s||t),p.y+s);ctx.moveTo(p.x-s,p.y+(s||t));ctx.lineTo(p.x+s,p.y-(s||t));ctx.stroke()}}
  if(state.camera&&scene.inspection){
   const camera=scene.inspection;ctx.setLineDash([4,4]);
   for(let i=1;i<camera.path.length;i++)line(camera.path[i-1],camera.path[i],'#d2dbe0',1.5);
   for(const [pose,label]of [[camera.start,'Startkamera'],[camera.goal,'Zielkamera']]){
    const distance=Math.hypot(...sub(camera.focus,pose.position)),end=pose.position.map((x,i)=>x-pose.rotation[i][2]*distance);
    line(pose.position,end,label==='Zielkamera'?'#ffffff':'#899ba8',1.6);
    const p=project(pose.position);if(p){ctx.fillStyle='#edf4fa';ctx.font='12px system-ui';ctx.fillText(label,p.x+8,p.y-8);ctx.beginPath();ctx.arc(p.x,p.y,4,0,Math.PI*2);ctx.fill()}
   }
   ctx.setLineDash([]);const p=project(camera.focus);if(p){ctx.fillStyle='#fff';ctx.font='12px system-ui';ctx.fillText('Ziel aus Vorhersage',p.x+8,p.y+16)}
  }
  canvas.dataset.yaw=state.yaw.toFixed(5);canvas.dataset.pitch=state.pitch.toFixed(5);canvas.dataset.distance=state.distance.toFixed(6);canvas.dataset.auto=String(state.auto);canvas.dataset.stage=String(state.stage);canvas.dataset.boxes=String(centers.length);canvas.dataset.camera=String(!!state.camera);
 }
 function tick(t){
  if(dead)return;if(!host.isConnected){dispose();return}
  const dt=last?Math.min((t-last)/1000,.05):0;last=t;
  if(scene&&visible&&!document.hidden){if(state.auto&&!drag&&t>idleUntil){state.yaw+=dt*.10;dirty=true}if(dirty){render();dirty=false}}
  frame=requestAnimationFrame(tick);
 }
 function hover(e){
  if(!scene||drag)return;const r=canvas.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;let hit=null,best=15;
  for(const [boxes,key]of groups())for(const [i,b]of boxes.entries()){const q=project(b.center);if(!q)continue;const d=Math.hypot(q.x-mx,q.y-my);if(d<best){best=d;hit={key,i,b}}}
  tip.hidden=!hit;
  if(hit){tip.textContent=({truth:'Simulation',initial:'Erste Vorhersage',updated:'Aktualisiert'})[hit.key]+` #${hit.i}: `+hit.b.center.map((x,i)=>'XYZ'[i]+' '+x.toFixed(4)+' m').join(' · ');tip.style.left=Math.min(mx+12,Math.max(0,width-280))+'px';tip.style.top=Math.min(my+12,height-55)+'px'}
 }
 event(canvas,'contextmenu',e=>e.preventDefault());
 event(canvas,'pointerdown',e=>{if(!scene||![0,2].includes(e.button))return;e.preventDefault();canvas.focus({preventScroll:true});canvas.setPointerCapture(e.pointerId);drag={id:e.pointerId,x:e.clientX,y:e.clientY,pan:e.button===2||e.shiftKey};host.dataset.dragging='true';tip.hidden=true});
 event(canvas,'pointermove',e=>{
  if(!drag){hover(e);return}if(e.pointerId!==drag.id)return;
  const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;
  if(drag.pan){const right=[-Math.sin(state.yaw),Math.cos(state.yaw),0],up=[-Math.sin(state.pitch)*Math.cos(state.yaw),-Math.sin(state.pitch)*Math.sin(state.yaw),Math.cos(state.pitch)],scale=state.distance/(Math.min(width,height)*1.05);state.target=state.target.map((v,i)=>v-dx*right[i]*scale+dy*up[i]*scale)}
  else{state.yaw-=dx*.006;state.pitch=Math.max(-1.35,Math.min(1.35,state.pitch+dy*.006))}dirty=true;
 });
 for(const name of ['pointerup','pointercancel','lostpointercapture'])event(canvas,name,e=>{if(drag&&e.pointerId===drag.id){drag=null;delete host.dataset.dragging;idleUntil=performance.now()+2000}});
 event(canvas,'pointerleave',()=>{tip.hidden=true});event(canvas,'dblclick',()=>{if(scene){reset();idleUntil=performance.now()+2000}});
 event(canvas,'wheel',e=>{if(!scene)return;e.preventDefault();zoom(Math.exp(Math.max(-150,Math.min(150,e.deltaY))*.0015))},{passive:false});
 event(canvas,'keydown',e=>{if(!scene)return;const step=.10;if(e.key==='ArrowLeft')state.yaw+=step;else if(e.key==='ArrowRight')state.yaw-=step;else if(e.key==='ArrowUp')state.pitch=Math.min(1.35,state.pitch+step);else if(e.key==='ArrowDown')state.pitch=Math.max(-1.35,state.pitch-step);else if(['+','='].includes(e.key))zoom(.85);else if(e.key==='-')zoom(1.18);else if(e.key==='Home')reset();else return;e.preventDefault();dirty=true;idleUntil=performance.now()+2000});
 event(host,'click',e=>{if(!scene)return;const action=e.target.closest('[data-action]')?.dataset.action;if(action==='auto'){state.auto=!state.auto;dirty=true;autoLabel()}if(action==='reset')reset();if(action==='in')zoom(.85);if(action==='out')zoom(1.18)});
 event(host,'change',e=>{if(!scene)return;if(e.target.hasAttribute('data-camera')){state.camera=e.target.checked;reset()}else if(e.target.dataset.layer)state.layers[e.target.dataset.layer]=e.target.checked;else if(e.target.tagName==='SELECT')state.stage=Number(e.target.value);dirty=true;tip.hidden=true});
 fetch(url,{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('3D-Daten fehlen');return r.json()}).then(raw=>{
  if(dead)return;scene=readScene(raw);state=sessions.get(url);
  if(!state){state={auto:!matchMedia('(prefers-reduced-motion: reduce)').matches,stage:scene.updates.length,layers:{truth:true,initial:true,updated:true},camera:!!scene.inspection};reset();sessions.set(url,state)}
  if(scene.inspection){const label=document.createElement('label'),input=document.createElement('input'),text=document.createElement('span');input.type='checkbox';input.setAttribute('data-camera','');input.checked=state.camera;text.textContent='Kameraweg und Blickrichtung';label.append(input,text);host.querySelector('.viewer-layers').append(label)}
  state.stage=Math.min(state.stage,scene.updates.length);autoLabel();
  for(const input of host.querySelectorAll('[data-layer]'))input.checked=state.layers[input.dataset.layer];
  if(scene.updates.length){const label=host.querySelector('.viewer-step');label.hidden=false;const select=label.querySelector('select');for(let i=0;i<=scene.updates.length;i++){const option=document.createElement('option');option.value=i;option.textContent=i?'Nach Zusatzaufnahme '+i:'Nur erste Aufnahme';select.append(option)}select.value=state.stage;host.querySelector('[data-updated]').hidden=false}
  status.hidden=!scene.empty;if(scene.empty)status.textContent='Leere Szene: keine Objekte und keine Vorhersagen.';canvas.dataset.loaded='true';
  resize=new ResizeObserver(()=>{const r=canvas.getBoundingClientRect();width=Math.max(1,r.width);height=Math.max(1,r.height);const ratio=Math.min(devicePixelRatio||1,2);canvas.width=Math.round(width*ratio);canvas.height=Math.round(height*ratio);ctx.setTransform(ratio,0,0,ratio,0,0);dirty=true});resize.observe(canvas);
  observer=new IntersectionObserver(entries=>{visible=entries[0].isIntersecting;if(visible)dirty=true});observer.observe(canvas);frame=requestAnimationFrame(tick);
 }).catch(e=>{if(e.name!=='AbortError'){status.textContent='Interaktive 3D-Daten konnten nicht geladen werden. Die gespeicherten Abbildungen bleiben verfügbar.';canvas.dataset.loaded='error'}});
 return dispose;
}
