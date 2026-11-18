export const categories = [
  {id:'robot', label:'Robot-Modell', description:'Bewegung und Steuerung · IL und RL'},
  {id:'vision', label:'Vision-Modell', description:'Visuelle Wahrnehmung · Objekte und räumliche Szenen'},
  {id:'quality', label:'Placement-Quality-Modell', description:'Bewertung von Platzierungen und Bewegungsabschnitten'}
];
export const sections = [
  {href:'trainings.html', label:'Modell-Trainings'},
  {href:'index.html', label:'Trainingsergebnisse'},
  {href:'library.html', label:'Paperbibliothek'}
];
export function categoryNavigation(selected) {
  return `<nav id="categories" class="model-categories" aria-label="Modellkategorien">${categories.map(c=>`<a href="trainings.html?category=${c.id}" data-category="${c.id}"${selected===c.id?' aria-current="true"':''}><strong>${c.label}</strong><small>${c.description}</small></a>`).join('')}</nav>`;
}
export function categoryContext(category, page='trainings.html') {
  const links=[{href:`trainings.html?category=${category}`,label:'Trainingsläufe'}];
  if(category==='vision')links.push({href:'vision.html',label:'Vision-Auswertung'});
  return `<nav class="model-context" aria-label="Ansichten im Modellbereich">${links.map(l=>`<a href="${l.href}"${l.href.split('?')[0]===page?' aria-current="page"':''}>${l.label}</a>`).join('')}</nav>${category==='robot'?'<p class="model-note">Wähle unten ein Lernverfahren, um die Erklärung und die zugehörigen Trainingsläufe zu sehen.</p>':category==='vision'?'<p class="model-note">Die Vision-Auswertung ergänzt die Trainingsläufe um Ergebnisse, Diagnosen und Kameraversuche.</p>':'<p class="model-note">Hier werden Modelle zur Bewertung von Platzierungen und Bewegungsabschnitten eingeordnet.</p>'}`;
}
