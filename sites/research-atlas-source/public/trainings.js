const $=id=>document.getElementById(id);
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=0)=>typeof v==='number'&&Number.isFinite(v)?new Intl.NumberFormat('de-DE',{maximumFractionDigits:d}).format(v):'—';
const date=v=>v&&Number.isFinite(Date.parse(v))?new Date(v).toLocaleString('de-DE',{timeZone:'Europe/Berlin'}):'—';
const names={planned:'Entwurf · nicht gestartet',cancelled:'Abgebrochen',running:'Training aktiv',completed:'Abgeschlossen',error:'Fehler',stale:'Status veraltet',unknown:'Status unbekannt'};
const methods={supervised:'Überwachtes Lernen',il:'Imitation Learning',rl:'Reinforcement Learning'};
const variants={fixed:'Zwei feste Kameras',fixed_wrist:'Fest + Handkamera'};
let geometryEpoch=null,geometryModel='',geometryKey='';
let data=null,category='vision',runId=new URLSearchParams(location.search).get('run'),tab='overview',modelKey='',busy=false;
function state(r){return r.status==='running'&&(!r.heartbeat||Date.now()-Date.parse(r.heartbeat)>180000)?'stale':r.status}
function run(){return data?.runs.find(r=>r.id===runId)}
function pairs(rows){return `<div class="table-wrap"><table class="kv"><tbody>${rows.map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div>`}
function link(a){return /^\/training-assets\/[\w-]+\/[\w.-]+$/.test(a.url)?esc(a.url):'#'}
function image(a){return `<a href="${link(a)}" target="_blank" rel="noopener"><img class="artifact" src="${link(a)}?v=${encodeURIComponent(a.updatedAt||'')}" alt="${esc(a.label)}" loading="lazy"></a>`}
function empty(text){return `<div class="empty">${esc(text)}</div>`}
function draw(){
 if(!data)return;
 $('categories').innerHTML=data.categories.map(c=>`<button class="category" data-category="${esc(c.id)}" aria-pressed="${c.id===category}"><strong>${esc(c.label)} <span class="count">${data.runs.filter(r=>r.category===c.id).length}</span></strong><small>${esc(c.description)}</small></button>`).join('');
 const list=data.runs.filter(r=>r.category===category&&($('method-select').value==='all'||r.method===$('method-select').value));
 if(!list.some(r=>r.id===runId))runId=list[0]?.id||null;
 $('run-select').innerHTML=list.map(r=>`<option value="${esc(r.id)}">${esc(r.title)} · ${esc(names[state(r)])}</option>`).join('');
 $('run-select').value=runId||'';$('run-select').disabled=!list.length;
 $('empty').hidden=!!list.length;$('run-content').hidden=!list.length;
 $('empty').textContent='In dieser Kategorie ist noch kein passender Trainingslauf registriert. RL und IL können später als Lernverfahren ergänzt werden.';
 const active=data.runs.filter(r=>state(r)==='running').length;
 $('global-status').textContent=active?`${active} aktiver Lauf / Läufe`:'Kein aktiver Trainingslauf';
 const r=run();if(!r)return;
 $('run-heading').innerHTML=`<div class="run-heading"><div><p class="eyebrow">${esc(methods[r.method]||r.method)}</p><h2>${esc(r.title)}</h2><p class="muted">${esc(r.description)}</p></div><span class="badge ${esc(state(r))}">${esc(names[state(r)])}</span></div>`;
 $('summary').innerHTML=[['Parameter',fmt(r.parameters)],['Modellseeds',r.plannedSeeds.length?fmt(r.plannedSeeds.length):fmt(new Set(r.models.map(m=>m.seed)).size)||'—'],['Optimizerupdates',fmt(r.lastStep)],['Modellvarianten',r.models.length?fmt(r.models.length):'Noch untrainiert']].map(([k,v])=>`<div class="stat"><small>${esc(k)}</small><strong>${esc(v)}</strong></div>`).join('');
 const cfg=r.config||{},opt=cfg.optimization||cfg.optimizer_defaults||cfg;
 $('panel-overview').innerHTML=`${r.status==='planned'?'<div class="notice"><strong>Geplant, noch nicht trainiert.</strong> Architektur und Konfiguration sind ein Entwurf. Es liegen keine V2-Losskurven oder echten V2-Rekonstruktionen vor.</div>':''}${state(r)==='stale'?'<div class="notice"><strong>Kein aktueller Fortschrittsnachweis.</strong> Der letzte Heartbeat ist älter als drei Minuten. Der Prozessstatus ist ungeklärt.</div>':''}${r.error?`<div class="notice error">${esc(r.error)}</div>`:''}<div class="grid"><article class="card"><h3>Laufstatus</h3>${pairs([['Status',names[state(r)]],['Letzter Trainingsstatus',date(r.heartbeat)],['Aktuelle Phase',r.stage||'Noch nicht gestartet'],['Epoche',r.progress?.epoch??'—'],['Szenenerzeugung',r.progress?.total?`${fmt(r.progress.completed)} / ${fmt(r.progress.total)} · ${r.progress.split}`:'—'],['Geplante Endzeit',date(r.deadline)],['Checkpoints',r.checkpointInfo]])}</article><article class="card"><h3>Aufgabe und Lernverfahren</h3><p>${esc(r.description)}</p><p class="muted">Die Modellkategorie beschreibt die Aufgabe. ${esc(methods[r.method]||r.method)} bezeichnet das Lernverfahren.</p>${pairs([['Kategorie',data.categories.find(c=>c.id===r.category)?.label],['Hardware',r.runtime?.gpu||'Noch nicht gemessen'],['PyTorch',r.runtime?.torch||'—']])}</article></div>${r.status==='cancelled'?'<div class="notice">Auf Nutzerwunsch beendet. Die Updates sind gesichert; eine abgeschlossene Auswertung oder bestandene Endtests werden daraus nicht abgeleitet.</div>':''}`;
 $('panel-model').innerHTML=`<div class="grid"><article class="card"><h3>Architektur</h3>${pairs(r.architecture||[])}</article><article class="card"><h3>Trainingskonfiguration</h3>${pairs([['Parameter',fmt(r.parameters)],['Optimierer',opt.optimizer||'AdamW'],['Lernrate',opt.learning_rate??opt.lr??'—'],['Weight Decay',opt.weight_decay??'—'],['Batchgröße',opt.effective_batch_size??opt.batch??'—'],['Loss',cfg.loss||'Siehe vollständige Konfiguration'],['Epochenlimit',opt.maximum_epochs??'Update-/Zeitbudget; keine festen Epochen'],['Seeds',(r.plannedSeeds||[]).join(', ')||'In den Messreihen ausgewiesen']])}</article></div><article class="card"><h3>Daten und Bewertung</h3>${r.id==='vision-scene-v2'?'<p>0–5 Objekte, Würfel und Quader; verstreute Szenen, Türme, Wände und Verdeckungen. Familienweise getrennte Trainings-, Validierungs- und Testdaten. Die geplanten Datenmengen werden vor Start im Laufzeitbenchmark geprüft.</p>':'<p>V1 lokalisiert zwei farblich zugeordnete Objektmittelpunkte. Es lernt keine Greifbewegungen, Zielanordnungen oder Lego-Montage. Die Bilder stammen aus statischen Simulationsszenen.</p>'}<details><summary>Vollständige gespeicherte Konfiguration</summary><pre>${esc(JSON.stringify(cfg,null,2))}</pre></details>${r.results?`<details><summary>Gespeicherte Ergebnisse</summary><pre>${esc(JSON.stringify(r.results,null,2))}</pre></details>`:''}</article>`;
 const options=r.models.map(m=>`${m.seed}/${m.variant}`);if(!options.includes(modelKey))modelKey=options[0]||'';
 $('model-select').innerHTML=r.models.map(m=>`<option value="${esc(`${m.seed}/${m.variant}`)}">Seed ${esc(m.seed)} · ${esc(variants[m.variant]||m.variant)}</option>`).join('');$('model-select').value=modelKey;$('model-select').disabled=!options.length;
 $('model-table').innerHTML=r.models.length?`<div class="table-wrap"><table><thead><tr><th>Seed</th><th>Kameravariante</th><th>Updates</th><th>Train Loss</th><th>Val Loss</th><th>Min Val Loss</th><th>Zuordnung</th><th>Anzahl korrekt</th><th>Recall ≤10mm</th></tr></thead><tbody>${r.models.map(m=>`<tr><td>${esc(m.seed)}</td><td>${esc(variants[m.variant]||m.variant)}</td><td>${fmt(m.step)}</td><td>${fmt(m.train,7)}</td><td>${fmt(m.validation,7)}</td><td>${fmt(m.bestValidation,7)}</td><td>${m.positionMm===null?'—':fmt(m.positionMm,2)+' mm'}</td><td>${m.countAccuracy==null?'—':fmt(m.countAccuracy*100,1)+' %'}</td><td>${m.recall10mm==null?'—':fmt(m.recall10mm*100,1)+' %'}</td></tr>`).join('')}</tbody></table></div><p class="muted">Letzter vollständiger Messpunkt je Modell; Seed-Ergebnisse bleiben getrennt. Min Val ist der kleinste gemessene Gesamt-Loss; V2 wählt Checkpoints nach dem stratifizierten Loss. Zuordnung bezeichnet den Fehler zugeordneter Objektplätze, nicht erfolgreichen Robotereinsatz. Recall berücksichtigt zusätzlich die Erkennung.</p>`:'';
 const demo=r.artifacts.find(a=>a.kind==='demo');
 $('panel-geometry').innerHTML=`<div class="card"><h3>Simulation und rekonstruierte Szene</h3><p>Vorgesehen alle fünf Epochen: Position, Abmessungen, symmetriebewusste Orientierung, 3D-IoU und fehlende oder zusätzliche Objekte. Cyan zeigt die Simulation, Orange die Vorhersage; beide halbtransparent.</p>${demo?`<div class="notice"><strong>Illustration mit künstlichen Fehlern.</strong> Dieses Bild zeigt das Ausgabeformat, keine trainierte Modellvorhersage.</div>${image(demo)}`:empty('Für diesen Lauf sind keine echten 3D-Vergleichsbilder registriert.')}<p class="muted">Das neue Modell beschreibt Objekte zunächst als Quader, nicht als detailliertes Mesh. Gleiche Validierungsszenen ermöglichen den Vergleich über die Epochen.</p></div>`;
 $('panel-files').innerHTML=`<div class="card"><h3>Artefakte und Nachweise</h3>${r.artifacts.map(a=>`<a class="artifact-link" href="${link(a)}" target="_blank" rel="noopener">${esc(a.label)} ↗</a>`).join('')||'<p>Noch keine Artefakte.</p>'}<p class="muted">Gewichtsdateien werden nicht in den Browser geladen. Die Anzeige enthält nur freigegebene Messdaten und Abbildungen.</p><p class="muted">Datenstand: ${esc(date(data.generatedAt))} · ${data.transport==='local'?'lokale Trainingsdateien':'exportierter Snapshot'}</p>${r.readErrors?.length?`<p class="error">${esc(r.readErrors.join(' · '))}</p>`:''}</div>`;
 drawGeometry(r);drawChart();selectTab(tab);
}

function drawGeometry(r){
 const available=r.artifacts.filter(a=>a.kind==='geometry');if(!available.length)return;
 const epochs=[...new Set(available.map(a=>a.epoch))].sort((a,b)=>b-a);
 if(!epochs.includes(geometryEpoch))geometryEpoch=epochs[0];
 const epochRows=available.filter(a=>a.epoch===geometryEpoch);
 const models=[...new Set(epochRows.map(a=>`${a.seed}/${a.variant}`))];
 if(!models.includes(geometryModel))geometryModel=models[0];
 const candidates=epochRows.filter(a=>`${a.seed}/${a.variant}`===geometryModel);
 let selected=candidates.find(a=>a.name===geometryKey)||candidates[0];geometryKey=selected.name;
 const input=r.artifacts.find(a=>a.name===selected.name.replace('_overlay.png','_inputs.png'));
 const metrics=r.artifacts.find(a=>a.name===selected.name.replace('_overlay.png','_metrics.json'));
 $('panel-geometry').innerHTML=`<div class="card"><h3>Simulation und Modellvorhersage</h3><p>Cyan: wirkliche Geometrie. Orange: vom Modell geschätzte Position, Größe und Orientierung. Beide halbtransparent; keine nachträgliche Ausrichtung.</p>${geometryEpoch===0?'<div class="notice">Epoche 0 zeigt den initialisierten, noch untrainierten Modellzustand.</div>':''}<div class="chart-controls"><label>Epoche<select id="geometry-epoch">${epochs.map(e=>`<option value="${e}" ${e===geometryEpoch?'selected':''}>${e}</option>`).join('')}</select></label><label>Modell<select id="geometry-model">${models.map(m=>`<option value="${esc(m)}" ${m===geometryModel?'selected':''}>Seed ${esc(m.split('/')[0])} · ${esc(variants[m.split('/')[1]])}</option>`).join('')}</select></label><label>Szene<select id="geometry-scene">${candidates.map(a=>`<option value="${esc(a.name)}" ${a.name===selected.name?'selected':''}>${esc(a.label)}</option>`).join('')}</select></label></div>${image(selected)}${metrics?`<a href="${link(metrics)}" target="_blank" rel="noopener">Geometriekennzahlen dieser Szene ↗</a>`:''}${input?`<h3>Verwendete Kamerabilder</h3>${image(input)}`:''}</div>`;
}
$('panel-geometry').addEventListener('change',e=>{if(e.target.id==='geometry-epoch'){geometryEpoch=Number(e.target.value);geometryKey=''}else if(e.target.id==='geometry-model'){geometryModel=e.target.value;geometryKey=''}else if(e.target.id==='geometry-scene'){geometryKey=e.target.value}else{return}drawGeometry(run())});

function drawChart(){
 const r=run();if(!r)return;const rows=r.curves.filter(p=>`${p.seed}/${p.variant}`===modelKey);
 const position=$('metric-select').value==='position',log=!position&&$('log-scale').checked;
 const series=position?[['positionMm','Validation · mm','#e8b571']]:[['train','Training · Loss','#63d6cd'],['validation','Validation · Loss','#e8b571'],['probe','Feste Trainingsprobe','#89a9ee']];
 const points=series.flatMap(([key])=>rows.filter(p=>Number.isFinite(p[key])&&(!log||p[key]>0)).map(p=>[p.step,log?Math.log10(p[key]):p[key]]));
 if(points.length<2){$('chart').innerHTML=empty('Für diese Auswahl liegen noch keine gemessenen Kurven vor.');return}
 const xMax=Math.max(...points.map(p=>p[0]),1);let yMin=log?Math.min(...points.map(p=>p[1])):0,yMax=Math.max(...points.map(p=>p[1]));if(yMax<=yMin)yMax=yMin+1;
 const X=x=>65+x/xMax*780,Y=y=>270-(y-yMin)/(yMax-yMin)*235;
 let svg='<svg class="loss-chart" viewBox="0 0 880 325" role="img" aria-label="Gemessener Trainingsverlauf"><title>Training und Validation nach Optimizerupdates</title>';
 for(let i=0;i<5;i++){const y=yMin+(yMax-yMin)*i/4;svg+=`<line x1="65" x2="845" y1="${Y(y)}" y2="${Y(y)}" stroke="#31414c"/><text x="55" y="${Y(y)+4}" text-anchor="end">${esc(Number(log?10**y:y).toPrecision(3))}</text>`}
 for(let i=0;i<5;i++){const x=xMax*i/4;svg+=`<text x="${X(x)}" y="292" text-anchor="middle">${fmt(x)}</text>`}
 for(const [key,,color]of series){const filtered=rows.filter(p=>Number.isFinite(p[key])&&(!log||p[key]>0));if(filtered.length)svg+=`<polyline fill="none" stroke="${color}" stroke-width="2.3" points="${filtered.map(p=>`${X(p.step)},${Y(log?Math.log10(p[key]):p[key])}`).join(' ')}"/>`}
 svg+='<text x="455" y="318" text-anchor="middle">Optimizerupdates</text></svg>';
 $('chart').innerHTML=svg+`<div class="chart-legend">${series.map(([,label,color])=>`<span><i class="legend-line" style="background:${color}"></i>${esc(label)}</span>`).join('')}</div><p class="muted">${position?'Mittlerer euklidischer Positionsfehler auf der Validierung.':'Loss wie in der Konfiguration angegeben. V1: normierter XYZ-MSE. V2: gewichteter Gesamt-Loss; Training über die Epoche aggregiert, Validation im Evalmodus. Die Trainingsprobe wird separat dargestellt.'}</p>`;
}
function selectTab(next){tab=next;for(const b of document.querySelectorAll('[data-tab]')){const selected=b.dataset.tab===tab;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;$(`panel-${b.dataset.tab}`).hidden=!selected}}
async function refresh(){
 if(busy)return;busy=true;$('refresh').disabled=true;
 try{
  let snapshot,local=false;
  try{const response=await fetch('/api/trainings',{cache:'no-store',signal:AbortSignal.timeout(7000)});if(!response.ok)throw Error();snapshot=await response.json();if(snapshot.schemaVersion!==1)throw Error();local=snapshot.transport==='local'}catch{const response=await fetch('/training-data/index.json',{cache:'no-store',signal:AbortSignal.timeout(7000)});if(!response.ok)throw Error('Keine Trainingsdaten erreichbar');snapshot=await response.json()}
  if(snapshot.schemaVersion!==1||!Array.isArray(snapshot.runs)||!Array.isArray(snapshot.categories))throw Error('Ungültiges Datenformat');data=snapshot;
  $('connection').textContent=local?`Lokal verbunden · Aktualisierung alle 15 s · ${date(data.generatedAt)}`:`Snapshot vom ${date(data.generatedAt)} · keine Live-Verbindung zum Trainingsrechner`;
  $('fetch-error').hidden=true;draw();
 }catch(error){$('fetch-error').hidden=false;$('fetch-error').textContent=`Aktualisierung fehlgeschlagen: ${error.message}. ${data?'Letzter geladener Stand bleibt sichtbar.':''}`;$('connection').textContent='Keine aktuelle Datenverbindung';if(data)draw()}
 finally{busy=false;$('refresh').disabled=false}
}
$('categories').addEventListener('click',e=>{const b=e.target.closest('[data-category]');if(b){category=b.dataset.category;runId=null;draw()}});
$('run-select').addEventListener('change',()=>{runId=$('run-select').value;modelKey='';geometryEpoch=null;geometryKey='';history.replaceState(null,'',`?run=${encodeURIComponent(runId)}`);draw()});
$('method-select').addEventListener('change',draw);$('model-select').addEventListener('change',()=>{modelKey=$('model-select').value;drawChart()});$('metric-select').addEventListener('change',drawChart);$('log-scale').addEventListener('change',drawChart);$('refresh').addEventListener('click',refresh);
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(b)selectTab(b.dataset.tab)});
document.querySelector('.tabs').addEventListener('keydown',e=>{const tabs=[...document.querySelectorAll('[data-tab]')],at=tabs.indexOf(document.activeElement);if(at<0)return;let n;if(e.key==='ArrowRight')n=(at+1)%tabs.length;if(e.key==='ArrowLeft')n=(at+tabs.length-1)%tabs.length;if(e.key==='Home')n=0;if(e.key==='End')n=tabs.length-1;if(n!==undefined){e.preventDefault();selectTab(tabs[n].dataset.tab);tabs[n].focus()}});
setInterval(()=>{if(!document.hidden)refresh()},15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});refresh();
