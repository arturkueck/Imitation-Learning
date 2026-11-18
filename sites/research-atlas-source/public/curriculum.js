const host=document.getElementById('result-chart');
const note=document.getElementById('chart-note');
let evidence;
function render(count){
  host.replaceChildren();
  for(const [name,entry] of Object.entries(evidence.clockConfirmation.models)){
    const r=entry[String(count)];
    if(!r||![r.n,r.original_successes,r.bounded_successes].every(Number.isFinite)||r.n<=0)throw Error('Ungültige Messdaten');
    const row=document.createElement('div');row.className='bar-row';
    const label=document.createElement('span');label.className='bar-label';
    label.textContent=(name.startsWith('mixed')?'Durchmischt':'Curriculum')+' · Seed '+name.split('seed')[1];
    const bars=document.createElement('div');bars.className='bar-pair';
    for(const [key,value] of [['original',r.original_successes],['bounded',r.bounded_successes]]){
      const track=document.createElement('div');track.className='bar-track';
      const bar=document.createElement('div');bar.className='bar '+key;bar.style.width=(100*value/r.n)+'%';
      bar.textContent=value+'/'+r.n;bar.setAttribute('aria-label',(key==='original'?'Original':'Zeitbegrenzt')+': '+value+' von '+r.n);
      track.append(bar);bars.append(track);
    }
    row.append(label,bars);host.append(row);
  }
  note.textContent=count===3?'Je 100 gleiche frische Starts pro Modell. Zwei Vorgeschichten mit je drei Trainingsseeds.':'Je 20 gleiche frische Starts pro Modell. Die Zeitintervention wird beim Zweierstapel nicht aktiviert; sämtliche Paare sind bitgenau identisch.';
  for(const button of document.querySelectorAll('[data-count]'))button.setAttribute('aria-pressed',String(Number(button.dataset.count)===count));
}
try{
  const response=await fetch('curriculum-evidence/results.json');if(!response.ok)throw Error('Messdatei nicht erreichbar');
  evidence=await response.json();render(3);
  for(const button of document.querySelectorAll('[data-count]'))button.addEventListener('click',()=>render(Number(button.dataset.count)));
}catch(error){host.textContent='Die interaktive Ansicht ist nicht verfügbar. Die statische Tabelle und verlinkten Messdaten bleiben zugänglich.';}
