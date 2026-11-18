import {methodGuides} from './learning-method-guides.js';
import {actorCriticContent} from './learning-method-content.js';

export const learningMethods = {
  supervised: {label:'Überwachtes Lernen', description:'Das Modell lernt aus Eingaben und vorgegebenen Zielwerten. Im Vision-Bereich sind das beispielsweise Bilder und die dazugehörigen Objektpositionen, Größen oder Orientierungen. Der Loss misst die Abweichung von diesen Zielwerten.'},
  il: {label:'Imitation Learning', description:'Eine Policy lernt Handlungen aus Demonstrationen. Bei Behavior Cloning wird die Abweichung von den gezeigten Aktionen minimiert. Auch qualitätsgewichtetes Behavior Cloning bleibt Imitation Learning; es ist dadurch noch kein Actor-Critic-Verfahren.'},
  rl: {label:'Reinforcement Learning', description:'Eine Policy lernt aus den Folgen ihrer Aktionen und einem definierten Reward. Ziel ist ein hoher zukünftiger Ertrag. Actor-Critic ist eine konkrete Verfahrensfamilie innerhalb von Reinforcement Learning.'},
  'actor-critic': {label:'Actor-Critic', description:'Actor-Critic ist ein Reinforcement-Learning-Verfahren: Der Actor wählt Aktionen, der Critic schätzt deren zukünftigen Ertrag. Die Bewertung des Critics führt die Updates des Actors. Im lokalen Robot-Setup wird ein bereits durch Imitation gelernter Actor weitertrainiert; verglichen werden Critic-Warmstart sowie Actor-Updates mit und ohne zusätzlichen Behavior-Cloning-Term.'}
};

export function matchesMethod(run, method) {
  if(method==='all')return true;
  if(method==='rl')return run.method==='rl'||run.method==='actor-critic';
  return run.method===method;
}

export function methodExplanation(method) {
  const info=learningMethods[method];
  if(!info)return '<p class="muted">Wähle ein Lernverfahren, um seine Erklärung und die dazugehörigen Trainingsläufe anzuzeigen. Actor-Critic ist unter Reinforcement Learning eingeordnet.</p>';
  return `<h2>${info.label}</h2><p>${info.description}</p>${methodGuides[method]||''}${method==='actor-critic'?`<p class="notice"><strong>Lokales Setup technisch geprüft.</strong> Der wissenschaftliche Vergleich ist noch nicht gestartet; ein Vorteil ist nicht nachgewiesen.</p><details><summary>Versuchssetup, Vergleiche und Nachweise</summary><div class="method-document">${actorCriticContent}</div></details>`:''}`;
}
