const $=id=>document.getElementById(id);
const esc=v=>String(v??'—').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const n=(v,d=2)=>Number.isFinite(v)?new Intl.NumberFormat('de-DE',{maximumFractionDigits:d}).format(v):'—';
const pct=v=>`${n(v*100)} %`;
const table=(headers,rows)=>`<div class="table-wrap"><table><thead><tr>${headers.map(h=>`<th>${esc(h)}</th>`).join('')}</tr></thead><tbody>${rows.map(r=>`<tr>${r.map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>`;
const stats=rows=>rows.map(([label,value])=>`<div class="stat"><small>${esc(label)}</small><strong>${esc(value)}</strong></div>`).join('');
function comparisonTable(data,key){
 const s=data.results.fixed_wrist;const budget=s.budgets[key];const selected=s.selected_recipe;
 return table(['Verfahren','Erkannte Fehler','Fehler unter beibehaltenen'],[['Seed-Streuung',pct(budget.ensemble.flagged_bad_fraction),pct(budget.ensemble.accepted_bad_fraction)],['Bildkonsistenz',pct(budget.image.flagged_bad_fraction),pct(budget.image.accepted_bad_fraction)],['Ausgewählte Kombination',pct(budget[selected].flagged_bad_fraction),pct(budget[selected].accepted_bad_fraction)]]);
}
try{
 const response=await fetch('vision-research-data.json',{cache:'no-cache'});if(!response.ok)throw Error('Missing data');const d=await response.json();
 $('updated').textContent=` Export: ${new Date(d.updatedAt).toLocaleString('de-DE',{timeZone:'Europe/Berlin'})}.`;
 $('training-stats').innerHTML=stats([['Epochen',n(d.training.epochs,0)],['Updates je Modell',n(d.training.updatesPerModel,0)],['Modelle / Seeds',`${d.training.models} / ${d.training.seeds}`],['Parameter je Modell',n(d.training.parameters,0)]]);
 $('training-table').innerHTML=table(['Panel','Kameras','Zuordnungsfehler','Anzahl korrekt','Erkannt und ≤10 mm'],d.training.correctedTest.map(r=>[r.panel,r.camera,`${n(r.position)} mm`,pct(r.count),pct(r.recall)]));
 const u=d.ensemble.results.fixed_wrist;
 $('ensemble-table').innerHTML=table(['Fest + Handkamera','Zurückgehaltene Validierung'],[['Beibehaltene Gruppen',pct(u.held_rule.retained_fraction)],['Markierte Fehler',pct(u.held_rule.flagged_bad_fraction)],['Fehler unter beibehaltenen Gruppen',pct(u.held_rule.accepted_bad_fraction)],['Fehler unter beibehaltenen Turmgruppen',pct(u.by_arrangement['2'].rule.accepted_bad_fraction)]]);
 $('rgb-table').innerHTML=comparisonTable(d.rgb,'10pct');
 const r=d.reference.segmentation.held;
 $('reference-stats').innerHTML=stats([['Mittlerer IoU · nichtleer',pct(r.macro_iou_positive)],['Pixel-Präzision',pct(r.precision)],['Pixel-Recall',pct(r.recall)],['Leere Ansichten mit Fehlalarm',`0 / ${r.empty_views}`]]);
 const rr=d.reference.ranking.fixed_wrist,rb=rr.budgets['0.1'];
 $('reference-table').innerHTML=table(['Fest + Hand · 10 % Prüfbudget','Erkannte Fehler','Fehler unter beibehaltenen'],[['Seed-Streuung',pct(rb.ensemble.flagged_bad_fraction),pct(rb.ensemble.accepted_bad_fraction)],['Referenz-Bildprüfung',pct(rb.image.flagged_bad_fraction),pct(rb.image.accepted_bad_fraction)],['Ausgewählte Kombination',pct(rb[rr.selected_recipe].flagged_bad_fraction),pct(rb[rr.selected_recipe].accepted_bad_fraction)]]);
 if(d.refinement){
  const e=d.refinement.evaluation;
  $('refinement-result').innerHTML=`<div class="notice"><strong>Begrenzter Versuch abgeschlossen.</strong> ${esc(e.scenes)} neue Prüfszenen, ${esc(e.objects)} paarweise zugeordnete Objekte. Kein Modelltraining.</div>`+table(['Messgröße','Vorher','Nachher'],[['Mittlerer Positionsfehler',`${n(e.position_before_mean_mm)} mm`,`${n(e.position_after_mean_mm)} mm`],['Mittlerer Ecken-RMSE',`${n(e.corner_before_mean_mm)} mm`,`${n(e.corner_after_mean_mm)} mm`],['Größenfehler MAE',`${n(e.size_before_mean_mm)} mm`,`${n(e.size_after_mean_mm)} mm`],['Mittlerer Szenen-Recall bei 10 mm',pct(e.recall10_before),pct(e.recall10_after)]])+`<p>Mehr als 1 mm verbessert: ${esc(e.improved_over_1mm)} · verschlechtert: ${esc(e.worsened_over_1mm)} · höchstens 1 mm Änderung: ${esc(e.essentially_unchanged)}. Mögliche Mehrdeutigkeit in ${esc(e.ambiguous_scenes)} Prüfszenen.</p><p class="muted">Gepaarte Positionsänderung, Szenen-Bootstrap-95%-Intervall: ${n(e.paired_position_delta_bootstrap95_mm[0])} bis ${n(e.paired_position_delta_bootstrap95_mm[1])} mm. Negative Änderung bedeutet weniger Fehler. Kleiner Pilot; keine Freigabe durch einen besseren Bildscore.</p><figure><a href="vision-evidence/refinement-quality.png"><img src="vision-evidence/refinement-quality.png" alt="Gepaarte Positions- und Geometriefehler vor und nach Korrektur" loading="lazy"></a></figure>`;
  const verdict=document.createElement('p');verdict.className='notice';verdict.textContent='Kein verlässlicher Positionsvorteil nachgewiesen. Der Eckenfehler sinkt etwas, der mittlere Positionsfehler und der 10-mm-Recall werden schlechter. Die Korrektur bleibt ein Diagnoseprototyp.';$('refinement-result').prepend(verdict);
  $('refinement-sources').innerHTML='<div class="result-links"><a href="vision-evidence/refinement-results.json">Korrektur-Messwerte ↗</a><a href="vision-evidence/refinement-examples.png">Größte Verbesserung und Verschlechterung ↗</a><a href="vision-evidence/refinement-report.md">Korrektur-Bericht ↗</a></div>';
 }else $('refinement-result').textContent=`Versuch läuft: ${d.refinementStatus.completed||0} / ${d.refinementStatus.total||24} Szenen. Es liegen noch keine abgeschlossenen Qualitätszahlen vor. Dies ist ein archivierter Exportstand.`;
 $('motion-result').innerHTML=stats([['Geprüfte Kollisionskörper',n(d.activeView.collision_shapes,0)],['Wiedergabeschritte',n(d.activeView.playback_samples,0)],['Kollisionsprüfungen',n(d.activeView.collision_checks,0)],['Native Umwelt-Durchdringungen',n(d.activeView.native_robot_world_penetrations,0)]]);
}catch(error){$('load-error').hidden=false;$('updated').textContent=' Daten nicht verfügbar.';console.error(error);}
