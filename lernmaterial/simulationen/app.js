(function(){
  'use strict';
  const M=window.LearningModels,$=id=>document.getElementById(id),num=id=>Number($(id).value),fmt=(x,n=3)=>Number(x).toLocaleString('de-DE',{maximumFractionDigits:n,minimumFractionDigits:Math.min(n,2)});
  const svgNS='http://www.w3.org/2000/svg',colors=['var(--s1)','var(--s2)','var(--s3)','var(--s4)'];
  function node(tag,attrs={},text){const el=document.createElementNS(svgNS,tag);Object.entries(attrs).forEach(([k,v])=>el.setAttribute(k,v));if(text!==undefined)el.textContent=text;return el;}
  function plot(id,series,opt={}){
    const el=$(id);el.replaceChildren();
    const legend=document.createElement('div');legend.className='legend';series.filter(s=>s.name).forEach((s,i)=>{const item=document.createElement('span'),swatch=document.createElement('span');swatch.className='swatch';swatch.style.background=colors[s.color??i%4];item.append(swatch,document.createTextNode(s.name));legend.append(item);});el.append(legend);
    const W=Math.max(290,el.clientWidth),H=opt.height||300,L=W<420?64:80,R=18,T=15,B=52;
    const svg=node('svg',{viewBox:`0 0 ${W} ${H}`,role:'img','aria-label':opt.description||`${opt.xTitle}; ${opt.yTitle}`});el.append(svg);
    svg.append(node('title',{},opt.description||'Berechnetes Lernmodell'));
    const all=series.flatMap(s=>s.points).filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
    if(!all.length)return;
    let x0=opt.xDomain?opt.xDomain[0]:Math.min(...all.map(p=>p.x)),x1=opt.xDomain?opt.xDomain[1]:Math.max(...all.map(p=>p.x));
    let y0=opt.yDomain?opt.yDomain[0]:Math.min(0,...all.map(p=>p.y)),y1=opt.yDomain?opt.yDomain[1]:Math.max(0,...all.map(p=>p.y));
    if(x0===x1){x0-=.5;x1+=.5;}if(y0===y1){y0-=.1;y1+=.1;}
    if(!opt.xDomain){const p=(x1-x0)*.04;x0-=p;x1+=p;}if(!opt.yDomain){const p=(y1-y0)*.09;y0-=p;y1+=p;}
    const X=x=>L+(x-x0)/(x1-x0)*(W-L-R),Y=y=>H-B-(y-y0)/(y1-y0)*(H-T-B);
    for(let i=0;i<4;i++){
      const x=x0+(x1-x0)*i/3,y=y0+(y1-y0)*i/3;
      svg.append(node('line',{x1:L,x2:W-R,y1:Y(y),y2:Y(y),class:'grid'}));
      svg.append(node('text',{x:L-9,y:Y(y)+4,'text-anchor':'end'},fmt(y,2)));
      svg.append(node('text',{x:X(x),y:H-B+22,'text-anchor':i===0?'start':i===3?'end':'middle'},fmt(x,1)));
    }
    svg.append(node('rect',{x:L,y:T,width:W-L-R,height:H-T-B,fill:'none',class:'axis'}));
    svg.append(node('text',{x:(L+W-R)/2,y:H-6,'text-anchor':'middle'},opt.xTitle));
    svg.append(node('text',{transform:`translate(15 ${(T+H-B)/2}) rotate(-90)`,'text-anchor':'middle'},opt.yTitle));
    const clipId=`clip-${id}`,defs=node('defs'),clip=node('clipPath',{id:clipId});clip.append(node('rect',{x:L,y:T,width:W-L-R,height:H-T-B}));defs.append(clip);svg.append(defs);const group=node('g',{'clip-path':`url(#${clipId})`});svg.append(group);
    series.forEach((s,i)=>{const color=colors[s.color??i%4],points=s.points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y));
      if(s.scatter){points.forEach(p=>{const dot=node('circle',{cx:X(p.x),cy:Y(p.y),r:s.radius||2.5,fill:color,opacity:s.opacity??.65});dot.append(node('title',{},`x=${fmt(p.x)}, y=${fmt(p.y)}`));group.append(dot);});}
      else if(points.length){group.append(node('polyline',{points:points.map(p=>`${X(p.x)},${Y(p.y)}`).join(' '),fill:'none',stroke:color,'stroke-width':s.width||2.2,'stroke-dasharray':s.dash||'','stroke-linejoin':'round',opacity:s.opacity??1}));if(points.length===1)group.append(node('circle',{cx:X(points[0].x),cy:Y(points[0].y),r:3,fill:color}));}
    });
  }
  function outputs(ids){ids.forEach(id=>$(id+'-out').textContent=fmt(num(id),2));}
  let tab='error',rounds=0,cache=null;
  function error(){outputs(['q','bias']);const q=num('q'),b=num('bias'),values=M.recurrence(q,b);plot('error-chart',[{name:'eingestelltes q',points:values},{name:'Vergleich q=0.7',points:M.recurrence(.7,b),dash:'6 4'}],{xTitle:'Schritt t',yTitle:'Fehler e (abstrakt)',xDomain:[0,25]});$('error-result').textContent=`Nach 25 Schritten: e=${fmt(values.at(-1).y)}.`+(q<1?` Bei dauerhaftem b ist der Grenzwert b/(1−q)=${fmt(b/(1-q))}.`:' Für q≥1 folgt kein abklingender Grenzwert aus dieser Rekursion.');}
  function data(){outputs(['start','dart-sigma']);const c=M.collection(rounds,num('dart-sigma'),num('start')),curves=[{name:'Expert',color:3,points:[]},{name:'BC',color:0,points:[]},{name:'DAgger',color:1,points:[]},{name:'DART',color:2,points:[]}];
    for(let i=0;i<=100;i++){const x=-2+4*i/100;curves[0].points.push({x,y:M.expert(x)});[c.bc,c.dagger,c.dart].forEach((model,j)=>curves[j+1].points.push({x,y:M.predict(model,x)}));}
    curves.push({name:'nominale Expertlabels',color:0,scatter:true,points:c.base.map(p=>({x:p.x,y:p.u})),radius:3});
    plot('policy-chart',curves,{xDomain:[-2,2],xTitle:'Zustand x (abstrakt)',yTitle:'Aktion u (abstrakt)'});
    const traces=[c.bc,c.dagger,c.dart].map(m=>M.rollout(m,num('start')));
    plot('rollout-chart',traces.map((points,i)=>({name:['BC-Rollout','DAgger-Rollout','DART-Rollout'][i],points})),{xTitle:'Schritt t',yTitle:'Abweichung x (abstrakt)',xDomain:[0,50]});
    $('round-count').textContent=`${rounds} DAgger-Runde(n)`;
    $('data-result').replaceChildren();const wrap=document.createElement('div');wrap.className='table-wrap';const table=document.createElement('table');table.innerHTML='<thead><tr><th>Modell</th><th>Labels</th><th>w₁</th><th>w₃</th><th>Testende</th></tr></thead>';const body=document.createElement('tbody');
    [c.bc,c.dagger,c.dart].forEach((model,i)=>{const tr=document.createElement('tr');[ ['BC','DAgger','DART'][i],[c.base,c.daggerData,c.dartData][i].length,fmt(model.w1),fmt(model.w3),traces[i].length<51?'Abbruch bei |x|>4':fmt(traces[i].at(-1).y)].forEach(v=>{const td=document.createElement('td');td.textContent=v;tr.append(td);});body.append(tr);});table.append(body);wrap.append(table);$('data-result').append(wrap);
  }
  function coupling(){outputs(['c','d']);const c=num('c'),d=num('d'),product=$('coupling-mode').value==='product';$('d').disabled=product;$('d-label').style.opacity=product?.5:1;
    const withTerm=M.coupling(c,d,product),without=M.coupling(0,d,product),syms=product?['x','y']:['eₓ','eᵧ'];
    plot('coupling-chart',[{name:`${syms[0]} mit c=${fmt(c,2)}`,points:withTerm.map(p=>({x:p.t,y:p.z[0]}))},{name:`${syms[0]} ohne c-Term`,points:without.map(p=>({x:p.t,y:p.z[0]})),dash:'6 4'},{name:`${syms[1]} mit Term`,points:withTerm.map(p=>({x:p.t,y:p.z[1]})),color:2,dash:'2 4'}],{xTitle:'Zeit (abstrakte Einheiten)',yTitle:'Zustand / Fehler (abstrakt)',xDomain:[0,10]});
    plot('phase-chart',[{name:'mit Term: Zustandskurve',points:withTerm.map(p=>({x:p.z[0],y:p.z[1]}))},{name:'ohne Term: Zustandskurve',points:without.map(p=>({x:p.z[0],y:p.z[1]})),dash:'6 4'},{name:'gemeinsamer Start',scatter:true,color:3,points:[{x:withTerm[0].z[0],y:withTerm[0].z[1]}],radius:4}],{xTitle:syms[0]+' (abstrakt)',yTitle:syms[1]+' (abstrakt)'});
    if(product){$('coupling-formula').textContent=`ẋ=−x+${fmt(c)}xy, ẏ=−y. J(x,y)=[−1+cy, cx; 0, −1]. Start x=0.25,y=1.`;$('coupling-result').textContent=`Am Ursprung: Eigenwerte −1,−1, mit und ohne Produkt. Am Start: ẋ=${fmt(-.25+c*.25)}. Ein Produktterm ist nicht dasselbe wie ein konstanter Axy-Block.`;}
    else{const e=M.eig(c,d),no=M.eig(0,d);$('coupling-formula').textContent=`A=[−1, ${fmt(c)}; ${fmt(d)}, −1], z=(eₓ,eᵧ). Start eₓ=0.2,eᵧ=0.8.`;const label=e.imag?`${fmt(e.real[0])} ± ${fmt(e.imag)}i`:e.real.map(v=>fmt(v)).join(', ');$('coupling-result').textContent=`Mit Term: Eigenwerte ${label}. Ohne c-Term: ${no.real.map(v=>fmt(v)).join(', ')}. Maximaler Realteil ${fmt(Math.max(...e.real))}: ${Math.max(...e.real)<0?'lineares System asymptotisch stabil':Math.max(...e.real)>0?'mindestens ein instabiler Modus':'keine strikte Hurwitz-Stabilität'}. Startnorm ${fmt(Math.hypot(...withTerm[0].z))}, größte berechnete Norm ${fmt(Math.max(...withTerm.map(p=>Math.hypot(...p.z))))}.`+(withTerm.length<501?' Kurve am Sicherheitslimit abgeschnitten.':'');}
  }
  function chunk(){outputs(['horizon','m']);const ensemble=$('ensemble').checked;$('horizon').disabled=ensemble;$('m').disabled=!ensemble;const current=M.chunk(num('horizon'),ensemble,num('m')),baseline=M.chunk(1);plot('chunk-chart',[{name:'eingestellte Ausführung',points:current.points},{name:'Feedback in jedem Schritt, ohne TE',points:baseline.points,dash:'6 4'},{name:'Ziel',points:current.target,color:3,dash:'2 4'}],{xTitle:'Roboterschritt t',yTitle:'Position (abstrakt)'});const first=current.actions.findIndex((a,i)=>i>=12&&a<current.points[i].y);$('chunk-result').textContent=`Erste Bewegung zum neuen Ziel: Befehl in Schritt ${first}. Zielwechsel ist Schritt 12. ${ensemble?'Ensembling kombiniert nur Vorhersagen für denselben Zeitpunkt.':'Vorausgesagter Chunk Tₚ=10; ausgeführt Tₐ='+num('horizon')+'.'}`;}
  function diffusion(){outputs(['denoise-step']);const seed=num('sample-seed'),step=num('denoise-step');if(!cache||cache.seed!==seed)cache={seed,history:M.diffusion(seed)};const values=cache.history[step],bins=48,min=-4,max=4,width=(max-min)/bins,hist=Array(bins).fill(0);values.forEach(a=>{const index=Math.floor((a-min)/width);if(index>=0&&index<bins)hist[index]++;});const density=Array.from({length:161},(_,i)=>{const x=min+(max-min)*i/160,v=.18**2;return{x,y:(Math.exp(-((x+1)**2)/(2*v))+Math.exp(-((x-1)**2)/(2*v)))/(2*Math.sqrt(2*Math.PI*v))};});
    const empirical=hist.flatMap((n,i)=>[{x:min+i*width,y:n/values.length/width},{x:min+(i+1)*width,y:n/values.length/width}]);plot('density-chart',[{name:'vorgegebene Zieldichte',points:density,color:2},{name:'Stichprobendichte bei Iteration '+step,points:empirical,color:0,dash:'6 4'}],{xTitle:'Aktion a (abstrakt)',yTitle:'Dichte (1/Aktion)',xDomain:[-4,4],yDomain:[0,1.1*Math.max(...density.map(p=>p.y),...empirical.map(p=>p.y))]});
    const paths=Array.from({length:12},(_,i)=>({name:i===0?'12 beispielhafte Samples':null,points:cache.history.slice(0,step+1).map((row,j)=>({x:j,y:row[i]})),color:0,width:1.4,opacity:.55}));paths.push({name:'deterministischer MSE-Mittelwert',points:[{x:0,y:0},{x:100,y:0}],color:1,dash:'6 4'});plot('samples-chart',paths,{xTitle:'Recheniteration j (kein Roboterschritt)',yTitle:'Sampleaktion a (abstrakt)',xDomain:[0,100]});const left=values.filter(v=>v<0).length,near=values.filter(v=>Math.abs(v)<.3).length;$('diffusion-result').textContent=`120 Samples: ${left} links, ${120-left} rechts; ${near} im mittleren Bereich |a|<0.3. Zweimoden-Mittelwert = 0. Keine Task-Erfolgsmetrik.`;
  }
  function noise(){outputs(['rho','alpha']);const c=M.covariance(.2,.4,num('rho'),20,num('alpha'));plot('noise-chart',[{name:'140 gezogene Aktionsstörungen',scatter:true,points:c.samples}],{xTitle:'Noise η₁ (abstrakte Aktion)',yTitle:'Noise η₂ (abstrakte Aktion)',height:390});$('noise-result').textContent=`Σα=[${fmt(c.matrix[0][0],4)}, ${fmt(c.matrix[0][1],4)}; ${fmt(c.matrix[1][0],4)}, ${fmt(c.matrix[1][1],4)}]. trΣ=${fmt(c.trace,4)}. T trΣ=${fmt(20*c.trace)} = α.`;}
  const renderers={error,data,coupling,chunk,diffusion,noise};
  function render(){renderers[tab]();}
  document.querySelectorAll('[data-tab]').forEach(button=>button.addEventListener('click',()=>{tab=button.dataset.tab;document.querySelectorAll('[data-tab]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));document.querySelectorAll('.lab').forEach(s=>s.hidden=s.id!==tab);render();}));
  document.querySelectorAll('input,select').forEach(el=>el.addEventListener('input',render));
  $('dagger-round').addEventListener('click',()=>{rounds=Math.min(5,rounds+1);data();});$('data-reset').addEventListener('click',()=>{rounds=0;data();});
  $('denoise-next').addEventListener('click',()=>{$('denoise-step').value=Math.min(100,num('denoise-step')+10);diffusion();});$('denoise-reset').addEventListener('click',()=>{$('denoise-step').value=0;diffusion();});
  let timer;window.addEventListener('resize',()=>{clearTimeout(timer);timer=setTimeout(render,100);});render();
})();
