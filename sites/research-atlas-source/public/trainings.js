import {learningMethods, matchesMethod, methodExplanation} from './learning-methods.js';
import {categoryNavigation, categoryContext, categories} from './navigation.js';
import {mountBoxViewer} from './box-viewer.js';
const $=id=>document.getElementById(id);
let activeViewers=[],refreshPending=false;
function clearViewers(){for(const dispose of activeViewers)dispose();activeViewers=[]}
function startViewer(id,artifact){const host=$(id);if(host&&artifact)activeViewers.push(mountBoxViewer(host,artifact.url))}
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt=(v,d=0)=>typeof v==='number'&&Number.isFinite(v)?new Intl.NumberFormat('de-DE',{maximumFractionDigits:d}).format(v):'—';
const date=v=>v&&Number.isFinite(Date.parse(v))?new Date(v).toLocaleString('de-DE',{timeZone:'Europe/Berlin'}):'—';
function runTimestamp(r){
 const started=r.startedAt||r.config?.started||(Number.isFinite(r.config?.started_unix)?new Date(r.config.started_unix*1000).toISOString():null);
 if(started&&Number.isFinite(Date.parse(started)))return 'Start: '+date(started);
 if(r.heartbeat&&Number.isFinite(Date.parse(r.heartbeat)))return 'Letzter Status: '+date(r.heartbeat);
 const evidence=(r.artifacts||[]).map(a=>a.updatedAt).filter(v=>v&&Number.isFinite(Date.parse(v))).sort((a,b)=>Date.parse(b)-Date.parse(a))[0];
 return (evidence?'Nachweis: ':'Datenstand: ')+date(evidence||data?.generatedAt);
}
const names={planned:'Entwurf · nicht gestartet',cancelled:'Abgebrochen',running:'Training aktiv',completed:'Abgeschlossen',error:'Fehler',stale:'Status veraltet',unknown:'Status unbekannt'};
const methods=Object.fromEntries(Object.entries(learningMethods).map(([key,value])=>[key,value.label]));
let shownMethod=null;
function explainMethod(){const method=$('method-select').value;if(shownMethod!==method){$('method-explanation').innerHTML=methodExplanation(method);shownMethod=method}}
function syncSelection(){const params=new URLSearchParams(location.search);params.set('category',category);params.set('method',$('method-select').value);if(runId)params.set('run',runId);else params.delete('run');history.replaceState(null,'',`?${params}`)}
const variants={fixed:'Zwei feste Kameras',fixed_wrist:'Fest + Handkamera',M1:'M1 · eine Handansicht',M2:'M2 · gespeicherte Handansichten'};
let geometryEpoch=null,geometryModel='',geometryKey='';
let data=null,category=categories.find(c=>c.id===new URLSearchParams(location.search).get('category'))?.id||'vision',runId=new URLSearchParams(location.search).get('run'),tab=new URLSearchParams(location.search).get('tab')||'overview',modelKey='',busy=false,comparisonKey=new URLSearchParams(location.search).get('comparison')||'';
function state(r){return r.status==='running'&&(!r.heartbeat||Date.now()-Date.parse(r.heartbeat)>180000)?'stale':r.status}
function run(){return data?.runs.find(r=>r.id===runId)}
function pairs(rows){return `<div class="table-wrap"><table class="kv"><tbody>${rows.map(([k,v])=>`<tr><td>${esc(k)}</td><td>${esc(v)}</td></tr>`).join('')}</tbody></table></div>`}
function link(a){return /^\/training-assets\/[\w-]+\/[\w.-]+$/.test(a.url)?esc(a.url):'#'}
function image(a){return `<a href="${link(a)}" target="_blank" rel="noopener"><img class="artifact" src="${link(a)}?v=${encodeURIComponent(a.updatedAt||'')}" alt="${esc(a.label)}" loading="lazy"></a>`}
function empty(text){return `<div class="empty">${esc(text)}</div>`}
function draw(){
 explainMethod();
 if(!data)return;
 const selectedRun=data.runs.find(r=>r.id===runId);if(selectedRun)category=selectedRun.category;
 $('categories').outerHTML=categoryNavigation(category);
 $('category-context').innerHTML=categoryContext(category);
 const list=data.runs.filter(r=>r.category===category&&matchesMethod(r,$('method-select').value));
 if(!list.some(r=>r.id===runId))runId=list[0]?.id||null;
 $('run-select').innerHTML=list.map(r=>`<option value="${esc(r.id)}">${esc(r.title)} · ${esc(runTimestamp(r))} · ${esc(names[state(r)])}</option>`).join('');
 $('run-select').value=runId||'';$('run-select').disabled=!list.length;
 $('empty').hidden=!!list.length;$('run-content').hidden=!list.length;
 $('empty').textContent='Für diese Kategorie und das gewählte Lernverfahren ist noch kein Trainingslauf registriert. Die Erklärung zum gewählten Lernverfahren ist oben verfügbar.';
 const active=data.runs.filter(r=>state(r)==='running').length;
 $('global-status').textContent=active?`${active} aktiver Lauf / Läufe`:'Kein aktiver Trainingslauf';
 syncSelection();
 const r=run();if(!r){clearViewers();return;}
 $('run-heading').innerHTML=`<div class="run-heading"><div><p class="eyebrow">${esc(methods[r.method]||r.method)}</p><h2>${esc(r.title)}</h2><p class="muted">${esc(runTimestamp(r))} · Berliner Zeit</p><p class="muted">${esc(r.description)}</p></div><span class="badge ${esc(state(r))}">${esc(names[state(r)])}</span></div>`;
 $('summary').innerHTML=[['Parameter',fmt(r.parameters)],['Modellseeds',r.plannedSeeds.length?fmt(r.plannedSeeds.length):fmt(new Set(r.models.map(m=>m.seed)).size)||'—'],['Optimizerupdates',fmt(r.lastStep)],['Modellvarianten',r.models.length?fmt(r.models.length):'Noch untrainiert']].map(([k,v])=>`<div class="stat"><small>${esc(k)}</small><strong>${esc(v)}</strong></div>`).join('');
 const cfg=r.config||{},opt=cfg.optimization||cfg.optimizer_defaults||cfg;
 $('panel-overview').innerHTML=`${r.status==='planned'?'<div class="notice"><strong>Geplant, noch nicht trainiert.</strong> Architektur und Konfiguration sind ein Entwurf. Zu diesem Entwurf liegen noch keine trainierten Gewichte, Losskurven oder validierten Rekonstruktionen vor.</div>':''}${state(r)==='stale'?'<div class="notice"><strong>Kein aktueller Fortschrittsnachweis.</strong> Der letzte Heartbeat ist älter als drei Minuten. Der Prozessstatus ist ungeklärt.</div>':''}${r.error?`<div class="notice error">${esc(r.error)}</div>`:''}<div class="grid"><article class="card"><h3>Laufstatus</h3>${pairs([['Status',names[state(r)]],['Letzter Trainingsstatus',date(r.heartbeat)],['Aktuelle Phase',r.stage||'Noch nicht gestartet'],['Epoche',r.progress?.epoch??'—'],['Szenenerzeugung',r.progress?.total?`${fmt(r.progress.completed)} / ${fmt(r.progress.total)} · ${r.progress.split}`:'—'],['Geplante Endzeit',date(r.deadline)],['Checkpoints',r.checkpointInfo]])}</article><article class="card"><h3>Aufgabe und Lernverfahren</h3><p>${esc(r.description)}</p><p class="muted">Die Modellkategorie beschreibt die Aufgabe. ${esc(methods[r.method]||r.method)} bezeichnet das Lernverfahren.</p>${pairs([['Kategorie',data.categories.find(c=>c.id===r.category)?.label],['Hardware',r.runtime?.gpu||'Noch nicht gemessen'],['PyTorch',r.runtime?.torch||'—']])}</article></div>${r.status==='cancelled'?'<div class="notice">Auf Nutzerwunsch beendet. Die Updates sind gesichert; eine abgeschlossene Auswertung oder bestandene Endtests werden daraus nicht abgeleitet.</div>':''}`;
 $('panel-model').innerHTML=`<div class="grid"><article class="card"><h3>Architektur</h3>${pairs(r.architecture||[])}</article><article class="card"><h3>Trainingskonfiguration</h3>${pairs([['Parameter',fmt(r.parameters)],['Optimierer',opt.optimizer||'AdamW'],['Lernrate',opt.learning_rate??opt.lr??'—'],['Weight Decay',opt.weight_decay??'—'],['Batchgröße',opt.effective_batch_size??opt.batch??'—'],['Loss',cfg.loss||'Siehe vollständige Konfiguration'],['Epochenlimit',opt.maximum_epochs??'Update-/Zeitbudget; keine festen Epochen'],['Seeds',(r.plannedSeeds||[]).join(', ')||'In den Messreihen ausgewiesen']])}</article></div><article class="card"><h3>Daten und Bewertung</h3>${r.id==='vision-scene-v2'?'<p>0–5 Objekte, Würfel und Quader; verstreute Szenen, Türme, Wände und Verdeckungen. Familienweise getrennte Trainings-, Validierungs- und Testdaten. Die geplanten Datenmengen werden vor Start im Laufzeitbenchmark geprüft.</p>':'<p>V1 lokalisiert zwei farblich zugeordnete Objektmittelpunkte. Es lernt keine Greifbewegungen, Zielanordnungen oder Lego-Montage. Die Bilder stammen aus statischen Simulationsszenen.</p>'}<details><summary>Vollständige gespeicherte Konfiguration</summary><pre>${esc(JSON.stringify(cfg,null,2))}</pre></details>${r.results?`<details><summary>Gespeicherte Ergebnisse</summary><pre>${esc(JSON.stringify(r.results,null,2))}</pre></details>`:''}</article>`;
 const options=r.models.map(m=>`${m.seed}/${m.variant}`);if(!options.includes(modelKey))modelKey=options[0]||'';
 $('model-select').innerHTML=r.models.map(m=>`<option value="${esc(`${m.seed}/${m.variant}`)}">Seed ${esc(m.seed)} · ${esc(variants[m.variant]||m.variant)}</option>`).join('');$('model-select').value=modelKey;$('model-select').disabled=!options.length;
 $('model-table').innerHTML=r.models.length?`<div class="table-wrap"><table><thead><tr><th>Seed</th><th>Kameravariante</th><th>Updates</th><th>Train Loss</th><th>Val Loss</th><th>Min Val Loss</th><th>Zuordnung</th><th>Anzahl korrekt</th><th>Recall ≤10mm</th></tr></thead><tbody>${r.models.map(m=>`<tr><td>${esc(m.seed)}</td><td>${esc(variants[m.variant]||m.variant)}</td><td>${fmt(m.step)}</td><td>${fmt(m.train,7)}</td><td>${fmt(m.validation,7)}</td><td>${fmt(m.bestValidation,7)}</td><td>${m.positionMm===null?'—':fmt(m.positionMm,2)+' mm'}</td><td>${m.countAccuracy==null?'—':fmt(m.countAccuracy*100,1)+' %'}</td><td>${m.recall10mm==null?'—':fmt(m.recall10mm*100,1)+' %'}</td></tr>`).join('')}</tbody></table></div><p class="muted">Letzter vollständiger Messpunkt je Modell; Seed-Ergebnisse bleiben getrennt. Min Val ist der kleinste gemessene Gesamt-Loss; V2 wählt Checkpoints nach dem stratifizierten Loss. Zuordnung bezeichnet den Fehler zugeordneter Objektplätze, nicht erfolgreichen Robotereinsatz. Recall berücksichtigt zusätzlich die Erkennung.</p>`:'';
 const demo=r.artifacts.find(a=>a.kind==='demo');
 $('panel-geometry').innerHTML=`<div class="card"><h3>Simulation und rekonstruierte Szene</h3><p>Vorgesehen alle fünf Epochen: Position, Abmessungen, symmetriebewusste Orientierung, 3D-IoU und fehlende oder zusätzliche Objekte. Cyan zeigt die Simulation, Orange die Vorhersage; beide halbtransparent.</p>${demo?`<div class="notice"><strong>Illustration mit künstlichen Fehlern.</strong> Dieses Bild zeigt das Ausgabeformat, keine trainierte Modellvorhersage.</div>${image(demo)}`:empty('Für diesen Lauf sind keine echten 3D-Vergleichsbilder registriert.')}<p class="muted">Das neue Modell beschreibt Objekte zunächst als Quader, nicht als detailliertes Mesh. Gleiche Validierungsszenen ermöglichen den Vergleich über die Epochen.</p></div>`;
 $('panel-files').innerHTML=`<div class="card"><h3>Artefakte und Nachweise</h3>${r.artifacts.map(a=>`<a class="artifact-link" href="${link(a)}" target="_blank" rel="noopener">${esc(a.label)} ↗</a>`).join('')||'<p>Noch keine Artefakte.</p>'}<p class="muted">Gewichtsdateien werden nicht in den Browser geladen. Die Anzeige enthält nur freigegebene Messdaten und Abbildungen.</p><p class="muted">Datenstand: ${esc(date(data.generatedAt))} · ${data.transport==='local'?'lokale Trainingsdateien':'exportierter Snapshot'}</p>${r.readErrors?.length?`<p class="error">${esc(r.readErrors.join(' · '))}</p>`:''}</div>`;

 $('tab-geometry').textContent=r.id.startsWith('bc-')?'Aufgabenerfolg':'3D-Abgleich';
 if(r.id.startsWith('bc-')){
  const prepared=r.id==='bc-abc-30k'&&r.status==='planned';
  if(prepared){
   const notice=$('panel-overview').querySelector('.notice');
   if(notice)notice.innerHTML='<strong>A/B/C vorbereitet, noch nicht gestartet.</strong> Drei A-Modelle werden neu trainiert. Sechs vollstaendige B/C-30k-Checkpoints sind bereits vorhanden; die neue korrigierte Endauswertung ist offen.';
   $('summary').innerHTML=[['Parameter','129.955'],['Trainingsseeds','3'],['Budget je Modell','30.000 Updates'],['Modellstaende','3 neu / 6 vorhanden']].map(([k,v])=>`<div class="stat"><small>${k}</small><strong>${v}</strong></div>`).join('');
  }
  $('panel-model').innerHTML=`<div class="grid"><article class="card"><h3>BC-Policy</h3>${pairs(r.architecture||[])}<p>Die Architektur erzeugt Roboteraktionen aus privilegierten Zustandsmerkmalen. Sie ist kein Vision-Modell.</p></article><article class="card"><h3>Daten und Auswertung</h3><p>180 Trainings- und 20 Validierungstrajektorien aus Zweier-Demonstrationen. Hauptziel: vollstaendiger stabiler Dreierturm bei vorgegebener Paarreihenfolge. Mindestens 50 gueltige Frames; keine Auswahl anhand des Endtests.</p><p>${prepared?'Gleiche Initialgewichte und 30k-Budgets, B/C aus geprueften vorhandenen Checkpoints. Alle Arme erhalten dieselbe Zeitbehandlung.':'Historische Vergleichspanels und Ausfuehrungskorrekturen sind getrennte Untersuchungen. Prozentwerte verschiedener Panels duerfen nicht als gemeinsame Lernkurve gelesen werden.'}</p></article></div><article class="card"><h3>Einordnung und Quellen</h3><p><a href="curriculum.html">Aktueller BC-/Curriculum-Forschungsstand</a></p><p>Die Lossansicht zeigt, falls vorhanden, Aktions-MSE aus protokollierten Trainingsbatches und auf unveraenderten Validierungsdemonstrationen. Ein geringerer Offlinefehler ist kein Nachweis eines stabilen Turms.</p><details><summary>Gespeicherte Konfiguration</summary><pre>${esc(JSON.stringify(cfg,null,2))}</pre></details>${r.results?`<details><summary>Messwerte / Protokoll</summary><pre>${esc(JSON.stringify(r.results,null,2))}</pre></details>`:''}</article>`;
  $('model-table').innerHTML=r.models.length?`<div class="table-wrap"><table><thead><tr><th>Trainingsseed</th><th>Variante</th><th>Update</th><th>Train Aktions-MSE</th><th>Val Aktions-MSE</th></tr></thead><tbody>${r.models.map(m=>`<tr><td>${esc(m.seed)}</td><td>${esc(m.variant)}</td><td>${fmt(m.step)}</td><td>${fmt(m.train,7)}</td><td>${fmt(m.validation,7)}</td></tr>`).join('')}</tbody></table></div><p class="muted">Pro Seed getrennte Messungen. Die MSE-Tabelle ersetzt keine Zwei-/Dreierturm-Erfolgsraten und bestimmt keinen Best-of-Test-Checkpoint.</p>`:'';
  $('panel-geometry').innerHTML='<div class="card"><h3>Stapelaufgabe und Erfolg</h3><p>Hier wird keine RGB- oder Quaderrekonstruktion bewertet. Geprueft werden Turmgeometrie, echte Wuerfelkontakte, Fingerkontaktfreiheit, Geschwindigkeiten und 50 aufeinanderfolgende gueltige Frames.</p><p><a href="curriculum.html">Ergebnistabellen, Zeitdiagnose und abgeschlossener A/B/C-Vergleich ↗</a></p></div>';
 }



/* bc-correction-view:start */
 if(r.id==='bc-approach-correction'){
  const t=r.results;
  $('summary').innerHTML=[['B-Vorfahren','3'],['Trainierte Komponenten','12'],['Updates je Komponente','5.000'],['Neue Bestätigungsstarts','50 · gemeinsam']].map(([k,v])=>`<div class="stat"><small>${k}</small><strong>${v}</strong></div>`).join('');
  $('panel-model').innerHTML=`<div class="grid"><article class="card"><h3>Getrennte BC-Komponenten</h3>${pairs(r.architecture||[])}<p>Je B-Vorfahr vier fortgesetzte Kopien. Nur die gesamte Phase-0-MLP lernt; übrige Phasen bleiben bitgleich. Neue Ausgaben werden nur beim zweiten Anfahren außerhalb des Rückzugs aktiviert.</p><p>Aktions- und Abschlusskopie werden separat trainiert. Die kombinierte Ausführung nutzt exakt dieselben Kopien und erhält keine weiteren Updates. Es ist kein Critic.</p></article><article class="card"><h3>Daten und Endpunkt</h3><p>40 Trainings- und zehn Validierungsfamilien versucht; tatsächlich 36 bzw. neun Familien enthalten. Ganze Ausgangsszenen bleiben über Controller und Frames in einem Split. 2.069 Trainings- und 499 Validierungsframes; zusätzlich ursprüngliches Phase-0-Replay.</p><p>Zwölf Komponenten, je 5.000 zusätzliche Updates. Fester Endpunkt; keine Best-of-Test-Auswahl. Bestätigung: 50 neue gemeinsame Starts je drei Modellseeds.</p></article></div><article class="card"><h3>Gespeicherter Trainingsvertrag</h3><pre>${esc(JSON.stringify(cfg,null,2))}</pre><p><a href="curriculum.html#correction-method">Vorgehen und Grenzen ↗</a></p></article>`;
  $('model-table').innerHTML=`<div class="table-wrap"><table><thead><tr><th>Modellseed</th><th>Komponente</th><th>Zusätzliche Updates</th><th>Train-Loss</th><th>Val-Metrik</th></tr></thead><tbody>${r.models.map(m=>`<tr><td>${esc(m.seed)}</td><td>${esc(m.variant)}</td><td>${fmt(m.step)}</td><td>${fmt(m.train,7)}</td><td>${fmt(m.validation,7)}</td></tr>`).join('')}</tbody></table></div><p class="muted">Aktionskopie: MSE. Abschlusskopie: Training 0,1 × gewichtete BCE, Validierung 0,1 × ungewichtete BCE. Protokollierte Batch-Losses, keine Epochenmittel; nicht über verschiedene Terme hinweg vergleichen. Keine Auswahl nach minimalem Validierungsloss.</p>`;
  const labels={baseline:'Ursprüngliches B',replay:'Replay-Fortsetzung',action:'Nur Aktionen',completion:'Nur Abschluss',combined:'Aktionen + Abschluss'};
  $('panel-geometry').innerHTML=['confirmation','development'].map(panel=>`<div class="card"><h3>${panel==='confirmation'?'Neue Bestätigung':'Bekannte Entwicklungsszenen'}</h3><p>${panel==='confirmation'?'50':'20'} gemeinsame Szenen × drei Modellseeds; keine unabhängigen Szenen über Modellseeds. Vollständiger Dreierturm für 50 strenge stabile Frames ohne Fingerkontakt.</p><div class="table-wrap"><table><thead><tr><th>Ausführung</th><th>Erfolge</th><th>Gewinne / Verluste gegen B</th><th>Gegen Replay</th></tr></thead><tbody>${Object.entries(t.aggregate[panel]).map(([p,v])=>`<tr><td>${esc(labels[p])}</td><td>${v.successes}/${v.n}</td><td>${t.paired[panel].baseline[p].gains} / ${t.paired[panel].baseline[p].losses}</td><td>${t.paired[panel].replay[p].gains} / ${t.paired[panel].replay[p].losses}</td></tr>`).join('')}</tbody></table></div></div>`).join('')+'<p><a href="curriculum.html#bc-correction">Seedwerte, Methode, Quellen und Aussagegrenzen ↗</a></p>';
 }
 /* bc-correction-view:end */
 drawGeometry(r);drawChart();selectTab(tab);
}

function drawGeometry(r){
 clearViewers();
 const gifs=r.artifacts.filter(a=>a.kind==='comparison-gif');
 if(!gifs.some(a=>a.name===comparisonKey))comparisonKey=gifs[0]?.name||'';
 const chosen=gifs.find(a=>a.name===comparisonKey);
 const comparison=chosen?`<div class="card" id="comparison-gifs"><h3>Nachschauen: GIF-Vergleich in drei Farben</h3><div class="notice"><strong>Erzwungene technische Zusatzaufnahmen.</strong> Diese simulierten Abläufe zeigen echte eingefrorene Modellvorhersagen. Größere geometrische Blickwechsel sind zusätzliche Diagnosedemos; die visuelle Freigabe ist dort weiterhin blockiert, die Bewegung nutzt ausdrücklich Simulatorreferenz. Die gelernte Produktionsentscheidung bestand die Qualitätsprüfung nicht und bleibt deaktiviert.</div><p><strong style="color:#23d9eb">Cyan: echte Simulationsposition.</strong> <strong style="color:#ff9b42">Orange: erste Vorhersage.</strong> <strong style="color:#67e889">Grün: nach zusätzlicher Aufnahme.</strong> Orange bleibt stehen; Grün erscheint erst nach der Aufnahme.</p><label>Blickwechsel-Beispiel<select id="comparison-select">${gifs.map(a=>`<option value="${esc(a.name)}" ${a.name===comparisonKey?'selected':''}>${esc(a.label)}</option>`).join('')}</select></label>${image(chosen)}<p class="muted">Drei Kamerabilder, 3D-Abgleich und Draufsicht. Gleiche Weltkoordinaten ohne nachträgliche Ausrichtung. Enthält Verbesserungen und Verschlechterungen. Satzfehler in mm-äq. kombiniert Position, Ecken und fehlende/zusätzliche Objekte. Ganze Wege erneut mit Simulatorreferenz geprüft; kein Realroboter-Freiraumnachweis.</p></div>`:'';
 const interactive=r.artifacts.find(a=>chosen&&a.name===chosen.name.replace('.gif','.scene.json'));
 const comparisonContent=interactive?comparison.replace(image(chosen),`<h3>Interaktiver 3D-Abgleich</h3><div id="comparison-viewer"></div><details ${/^comparison-(0[6789]|1[01])_/.test(chosen.name)?'open':''}><summary>Kamerabewegung als GIF ansehen</summary>${image(chosen)}</details>`):comparison;
 const available=r.artifacts.filter(a=>a.kind==='geometry');if(!available.length){if(comparisonContent)$('panel-geometry').innerHTML=comparisonContent;else if(r.id==='vision-active-v3-design')$('panel-geometry').innerHTML=`<div class="card"><h3>Historischer V3-Entwurf</h3><p>Die fertigen Ergebnisse und die fünf GIFs gehören zum abgeschlossenen V3-Lauf.</p><a class="artifact-link" href="?run=vision-active-v3-run1&amp;tab=geometry">Abgeschlossenen V3-Lauf mit GIFs öffnen ↗</a></div>`;startViewer('comparison-viewer',interactive);return;}
 const epochs=[...new Set(available.map(a=>a.epoch))].sort((a,b)=>b-a);
 if(!epochs.includes(geometryEpoch))geometryEpoch=epochs[0];
 const epochRows=available.filter(a=>a.epoch===geometryEpoch);
 const models=[...new Set(epochRows.map(a=>`${a.seed}/${a.variant}`))];
 if(!models.includes(geometryModel))geometryModel=models[0];
 const candidates=epochRows.filter(a=>`${a.seed}/${a.variant}`===geometryModel);
 let selected=candidates.find(a=>a.name===geometryKey)||candidates[0];geometryKey=selected.name;
 const input=r.artifacts.find(a=>a.name===selected.name.replace('_overlay.png','_inputs.png'));
 const metrics=r.artifacts.find(a=>a.name===selected.name.replace('_overlay.png','_metrics.json'));
 $('panel-geometry').innerHTML=comparisonContent+`<div class="card"><h3>Simulation und Modellvorhersage</h3><p>Cyan: wirkliche Geometrie. Orange: vom Modell geschätzte Position, Größe und Orientierung. Beide halbtransparent; keine nachträgliche Ausrichtung.</p>${geometryEpoch===0?'<div class="notice">Epoche 0 zeigt den Ausgangszustand dieses Laufs; V3 startet aus bereits trainierten V2-Gewichten.</div>':''}<div class="chart-controls"><label>Epoche<select id="geometry-epoch">${epochs.map(e=>`<option value="${e}" ${e===geometryEpoch?'selected':''}>${e}</option>`).join('')}</select></label><label>Modell<select id="geometry-model">${models.map(m=>`<option value="${esc(m)}" ${m===geometryModel?'selected':''}>Seed ${esc(m.split('/')[0])} · ${esc(variants[m.split('/')[1]]||m.split('/')[1])}</option>`).join('')}</select></label><label>Szene<select id="geometry-scene">${candidates.map(a=>`<option value="${esc(a.name)}" ${a.name===selected.name?'selected':''}>${esc(a.label)}</option>`).join('')}</select></label></div><div id="geometry-viewer"></div><details><summary>Gespeicherten 3D-Plot ansehen</summary>${image(selected)}</details>${metrics?`<a href="${link(metrics)}" target="_blank" rel="noopener">Geometriekennzahlen dieser Szene ↗</a>`:''}${input?`<h3>Verwendete Kamerabilder</h3>${image(input)}`:''}</div>`;
 const geometryScene=r.artifacts.find(a=>a.name===selected.name.replace('_overlay.png','_scene.json'));
 if(!geometryScene)$('geometry-viewer').remove();
 startViewer('comparison-viewer',interactive);startViewer('geometry-viewer',geometryScene);
}
$('panel-geometry').addEventListener('change',e=>{if(e.target.id==='comparison-select'){comparisonKey=e.target.value;const params=new URLSearchParams(location.search);params.set('comparison',comparisonKey);history.replaceState(null,'',`?${params}#comparison-gifs`)}else if(e.target.id==='geometry-epoch'){geometryEpoch=Number(e.target.value);geometryKey=''}else if(e.target.id==='geometry-model'){geometryModel=e.target.value;geometryKey=''}else if(e.target.id==='geometry-scene'){geometryKey=e.target.value}else{return}drawGeometry(run())});

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
function selectTab(next){tab=['overview','model','loss','geometry','files'].includes(next)?next:'overview';for(const b of document.querySelectorAll('[data-tab]')){const selected=b.dataset.tab===tab;b.setAttribute('aria-selected',String(selected));b.tabIndex=selected?0:-1;$(`panel-${b.dataset.tab}`).hidden=!selected}const params=new URLSearchParams(location.search);params.set('category',category);if(runId)params.set('run',runId);params.set('tab',tab);history.replaceState(null,'',`?${params}`)}
async function refresh(){
 if(busy)return;busy=true;$('refresh').disabled=true;
 try{
  let snapshot,local=false;
  try{const response=await fetch('/api/trainings',{cache:'no-store',signal:AbortSignal.timeout(7000)});if(!response.ok)throw Error();snapshot=await response.json();if(snapshot.schemaVersion!==1)throw Error();local=snapshot.transport==='local'}catch{const response=await fetch('/training-data/index.json',{cache:'no-store',signal:AbortSignal.timeout(7000)});if(!response.ok)throw Error('Keine Trainingsdaten erreichbar');snapshot=await response.json()}
  if(snapshot.schemaVersion!==1||!Array.isArray(snapshot.runs)||!Array.isArray(snapshot.categories))throw Error('Ungültiges Datenformat');const unchanged=data&&data.transport===snapshot.transport&&JSON.stringify(data.runs)===JSON.stringify(snapshot.runs);data=snapshot;
  $('connection').textContent=local?`Lokal verbunden · Aktualisierung alle 15 s · ${date(data.generatedAt)}`:`Snapshot vom ${date(data.generatedAt)} · keine Live-Verbindung zum Trainingsrechner`;
  $('fetch-error').hidden=true;if(!unchanged||refreshPending){if(document.querySelector('.box-viewer[data-dragging="true"]'))refreshPending=true;else{draw();refreshPending=false}}
 }catch(error){$('fetch-error').hidden=false;$('fetch-error').textContent=`Aktualisierung fehlgeschlagen: ${error.message}. ${data?'Letzter geladener Stand bleibt sichtbar.':''}`;$('connection').textContent='Keine aktuelle Datenverbindung';if(data)draw()}
 finally{busy=false;$('refresh').disabled=false}
}
document.addEventListener('click',e=>{const b=e.target.closest('#categories [data-category]');if(b&&!e.ctrlKey&&!e.metaKey&&!e.shiftKey&&!e.altKey&&e.button===0){e.preventDefault();category=b.dataset.category;runId=null;modelKey='';geometryEpoch=null;geometryKey='';syncSelection();$('categories').outerHTML=categoryNavigation(category);$('category-context').innerHTML=categoryContext(category);draw()}});
$('run-select').addEventListener('change',()=>{runId=$('run-select').value;modelKey='';geometryEpoch=null;geometryKey='';syncSelection();draw()});
$('method-select').addEventListener('change',()=>{runId=null;modelKey='';syncSelection();draw()});$('model-select').addEventListener('change',()=>{modelKey=$('model-select').value;drawChart()});$('metric-select').addEventListener('change',drawChart);$('log-scale').addEventListener('change',drawChart);$('refresh').addEventListener('click',refresh);
document.querySelector('.tabs').addEventListener('click',e=>{const b=e.target.closest('[data-tab]');if(b)selectTab(b.dataset.tab)});
document.querySelector('.tabs').addEventListener('keydown',e=>{const tabs=[...document.querySelectorAll('[data-tab]')],at=tabs.indexOf(document.activeElement);if(at<0)return;let n;if(e.key==='ArrowRight')n=(at+1)%tabs.length;if(e.key==='ArrowLeft')n=(at+tabs.length-1)%tabs.length;if(e.key==='Home')n=0;if(e.key==='End')n=tabs.length-1;if(n!==undefined){e.preventDefault();selectTab(tabs[n].dataset.tab);tabs[n].focus()}});
const requestedMethod=new URLSearchParams(location.search).get('method');if(requestedMethod==='all'||learningMethods[requestedMethod])$('method-select').value=requestedMethod;
explainMethod();
$('categories').outerHTML=categoryNavigation(category);$('category-context').innerHTML=categoryContext(category);
setInterval(()=>{if(!document.hidden)refresh()},15000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)refresh()});refresh();
