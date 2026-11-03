import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here=path.dirname(fileURLToPath(import.meta.url));
export async function workspaceRoot(start=here){
 let candidate=path.resolve(start);
 for(;;){try{await fs.access(path.join(candidate,'monitor/training-runs.json'));return candidate}catch{}
  const parent=path.dirname(candidate);if(parent===candidate)return null;candidate=parent;}
}
async function json(file){try{return JSON.parse((await fs.readFile(file,'utf8')).replace(/^\uFEFF/,''))}catch(e){if(e.code==='ENOENT')return null;throw e}}
export function inside(root,relative){const target=path.resolve(root,relative),rel=path.relative(root,target);if(rel.startsWith('..')||path.isAbsolute(rel))throw Error('Invalid registry path');return target}
export async function registry(root){const data=await json(path.join(root,'monitor/training-runs.json'));if(!data||data.schemaVersion!==1)throw Error('Trainingsregister fehlt oder ist inkompatibel');return data.runs;}
function publicConfig(value){
 if(Array.isArray(value))return value.map(publicConfig);
 if(value&&typeof value==='object')return Object.fromEntries(Object.entries(value).filter(([k])=>!/(path|directory|credential|token|secret|teacher|data_from|file|source_sha)/i.test(k)).map(([k,v])=>[k,publicConfig(v)]));
 if(typeof value==='string'&&(/^[A-Za-z]:[\\/]/.test(value)||value.startsWith('file:')))return '[lokaler Pfad]';
 return value;
}
const finite=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
export async function buildSnapshot(root,{transport='local'}={}){
 const entries=await registry(root),runs=[];
 for(const entry of entries){
  const base=inside(root,entry.directory),errors=[];
  const read=async relative=>{try{return await json(inside(base,relative))}catch{errors.push(`Nicht lesbar: ${path.basename(relative)}`);return null}};
  const config=await read(entry.config),raw=await read('status.json'),runtime=await read('runtime.json');
  const curves=await read(entry.curves||'curves.json')||[];
  const stop=await read('user_stop.json');
  let status=entry.kind==='design'?'planned':entry.kind==='completed'?'completed':'unknown';
  if(stop||raw?.stage==='cancelled_by_user')status='cancelled';
  else if(raw?.stage==='error')status='error';else if(raw?.stage==='complete')status='completed';
  else if(['train','render','validation','initializing','training','geometry','checkpoint'].includes(raw?.stage))status='running';
  const last=raw?.last_worker_status||raw;
  const heartbeat=last?.heartbeat_unix?new Date(last.heartbeat_unix*1000).toISOString():last?.time||null;
  if(status==='running'&&(!heartbeat||Date.now()-Date.parse(heartbeat)>180000))status='stale';
  const normalized=curves.map(r=>({seed:r.seed,variant:r.arm,step:r.updates??r.update,
   epoch:r.epoch??null,train:finite(r.train_loss??r.train_mse),validation:finite(r.validation_loss??r.validation_mse),
   probe:finite(r.probe_loss??r.train_probe_mse),batch:finite(r.batch_mse??r.loss),
   countAccuracy:finite(r.validation_count_accuracy),recall10mm:finite(r.validation_recall_10mm),
   components:r.validation_components||null,
   positionMm:finite(r.validation_mm),elapsedSeconds:finite(r.elapsed_seconds)}));
  const keys=[...new Set(normalized.map(r=>`${r.seed}/${r.variant}`))];
  const models=keys.map(key=>{const points=normalized.filter(r=>`${r.seed}/${r.variant}`===key);
   const latest=points.at(-1);return {seed:latest.seed,variant:latest.variant,step:latest.step,
    train:latest.train,validation:latest.validation,positionMm:latest.positionMm,
    countAccuracy:latest.countAccuracy,recall10mm:latest.recall10mm,
    bestValidation:Math.min(...points.map(r=>r.validation).filter(v=>v!==null))};});
  const artifacts=[];
  const listed=[...(entry.artifacts||[]),...(entry.geometryIndex?(await read(entry.geometryIndex)||[]):[])];
  for(const a of listed){try{const stat=await fs.stat(inside(base,a.file));if(stat.isFile())artifacts.push({name:a.name,label:a.label,kind:a.kind,epoch:a.epoch,seed:a.seed,variant:a.variant,url:`/training-assets/${entry.id}/${a.name}`,updatedAt:stat.mtime.toISOString()})}catch{}}
  runs.push({id:entry.id,category:entry.category,method:entry.method,title:entry.title,description:entry.description,
   status,stage:last?.stage||null,heartbeat,parameters:entry.parameters,architecture:entry.architecture,
   config:publicConfig(config),runtime:runtime?{torch:runtime.torch,numpy:runtime.numpy,gpu:runtime.gpu}:null,
   plannedSeeds:config?.paired_seeds||config?.seeds||[],models,curves:normalized,artifacts,
   lastStep:models.length?Math.max(...models.map(m=>m.step),finite(last?.step)??0):finite(last?.step),
   progress:{completed:finite(last?.rendered),total:finite(last?.render_total),split:last?.split||null,epoch:finite(last?.epoch)},
   deadline:config?.deadline_unix?new Date(config.deadline_unix*1000).toISOString():null,
   results:publicConfig(await read(entry.results||'results.json')),
   checkpointInfo:entry.kind==='design'?'Noch keine trainierten Gewichte':entry.kind==='training'?'Best und Latest je Seed/Kameravariante; letzter vollständiger Validierungszyklus':'Archivierte Pilot-Checkpoints',
   error:raw?.stage==='error'?String(raw.error||raw.reason||'Fehler gemeldet'):null,readErrors:errors});
 }
 return {schemaVersion:1,generatedAt:new Date().toISOString(),transport,pollSeconds:15,categories:[
  {id:'robot',label:'Robot-Modell',description:'Bewegung und Steuerung · beispielsweise IL oder RL'},
  {id:'vision',label:'Vision-Modell',description:'Visuelle Wahrnehmung · Objekte und räumliche Szenen'},
  {id:'quality',label:'Placement-Quality-Modell',description:'Bewertung von Platzierungen und Bewegungsabschnitten'}],runs};
}
export async function localTrainingRequest(req,res,pathname,root){
 if(pathname!=='/api/trainings'&&!pathname.startsWith('/training-assets/'))return false;
 const host=(req.headers.host||'').replace(/:\d+$/,'');
 if(!['127.0.0.1','localhost','[::1]'].includes(host)){res.writeHead(403).end();return true}
 if(!['GET','HEAD'].includes(req.method)){res.writeHead(405,{'Allow':'GET, HEAD'}).end();return true}
 if(!root){res.writeHead(503,{'Content-Type':'application/json'}).end(JSON.stringify({error:'Kein lokaler Trainingsordner verbunden'}));return true}
 try{
  if(pathname==='/api/trainings'){
   const body=JSON.stringify(await buildSnapshot(root));res.writeHead(200,{'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'});res.end(req.method==='HEAD'?undefined:body);return true;
  }
  const [,prefix,id,name,...extra]=pathname.split('/');
  if(extra.length||prefix!=='training-assets')throw Error('Unknown artifact');
  const entry=(await registry(root)).find(r=>r.id===id);
  const extraArtifacts=entry?.geometryIndex?(await json(inside(inside(root,entry.directory),entry.geometryIndex))||[]):[];
  const artifact=[...(entry?.artifacts||[]),...extraArtifacts].find(a=>a.name===name);
  if(!artifact){res.writeHead(404).end();return true}
  const file=inside(inside(root,entry.directory),artifact.file),bytes=await fs.readFile(file);
  res.writeHead(200,{'Content-Type':name.endsWith('.png')?'image/png':name.endsWith('.gif')?'image/gif':name.endsWith('.json')?'application/json; charset=utf-8':'text/plain; charset=utf-8','Cache-Control':'no-store','X-Content-Type-Options':'nosniff'});res.end(req.method==='HEAD'?undefined:bytes);return true;
 }catch{res.writeHead(503,{'Content-Type':'application/json'}).end(JSON.stringify({error:'Trainingsdaten vorübergehend nicht lesbar'}));return true}
}
export async function exportSnapshot(root,publicRoot){
 const snapshot=await buildSnapshot(root,{transport:'snapshot'});
 await fs.mkdir(path.join(publicRoot,'training-data'),{recursive:true});
 for(const entry of await registry(root))for(const a of [...(entry.artifacts||[]),...(entry.geometryIndex?(await json(inside(inside(root,entry.directory),entry.geometryIndex))||[]):[])]){
  try{const target=path.join(publicRoot,'training-assets',entry.id,a.name);await fs.mkdir(path.dirname(target),{recursive:true});await fs.copyFile(inside(inside(root,entry.directory),a.file),target)}catch(e){if(e.code!=='ENOENT')throw e}
 }
 await fs.writeFile(path.join(publicRoot,'training-data/index.json'),JSON.stringify(snapshot));return snapshot;
}
if(process.argv[1]&&path.resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const root=await workspaceRoot();if(!root)throw Error('Workspace nicht gefunden');
 const result=await exportSnapshot(root,path.resolve(here,'../public'));console.log(`Trainingssnapshot: ${result.runs.length} Läufe, ${result.generatedAt}`);
}
