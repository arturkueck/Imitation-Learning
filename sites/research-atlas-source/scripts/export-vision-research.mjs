import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {workspaceRoot,buildSnapshot,registry,inside} from './training-monitor.mjs';

const site=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'..');
const root=await workspaceRoot();if(!root)throw Error('Research workspace missing');
const read=async p=>JSON.parse((await fs.readFile(p,'utf8')).replace(/^\uFEFF/,''));
const vision=path.join(root,'experiments/visual_scene_v2_20261101');
const publicRoot=path.join(site,'public');const assets=path.join(publicRoot,'vision-evidence');
await fs.mkdir(assets,{recursive:true});
const sanitize=v=>Array.isArray(v)?v.map(sanitize):v&&typeof v==='object'?Object.fromEntries(Object.entries(v).filter(([k])=>!/token|credential|secret/i.test(k)).map(([k,x])=>[k,sanitize(x)])):typeof v==='string'&&(/^[A-Za-z]:[\\/]/.test(v)||v.startsWith('file:'))?'[lokaler Pfad]':v;
const manifest=[];
async function artifact(relative,name){
 const source=inside(root,relative),target=path.join(assets,name);
 const bytes=await fs.readFile(source);let output=bytes;
 if(name.endsWith('.json'))output=Buffer.from(JSON.stringify(sanitize(JSON.parse(bytes.toString('utf8'))),null,2));
 await fs.writeFile(target,output);
 manifest.push({name,source:relative,source_sha256:createHash('sha256').update(bytes).digest('hex'),published_sha256:createHash('sha256').update(output).digest('hex')});
}
const files=[
 ['experiments/visual_scene_v2_20261101/ASSESSMENT.md','vision-assessment.md'],
 ['experiments/visual_scene_v2_20261101/run_001/loss.png','training-loss.png'],
 ['experiments/visual_scene_v2_20261101/uncertainty_001/results.json','ensemble-results.json'],
 ['experiments/visual_scene_v2_20261101/uncertainty_001/README.md','ensemble-report.md'],
 ['experiments/visual_scene_v2_20261101/uncertainty_001/fixed_wrist_uncertainty.png','ensemble.png'],
 ['experiments/visual_scene_v2_20261101/image_consistency_001/results.json','rgb-results.json'],
 ['experiments/visual_scene_v2_20261101/image_consistency_001/QUALITY.md','rgb-report.md'],
 ['experiments/visual_scene_v2_20261101/image_consistency_001/fixed_wrist_comparison.png','rgb-comparison.png'],
 ['experiments/visual_scene_v2_20261101/reference_consistency_002/results.json','reference-results.json'],
 ['experiments/visual_scene_v2_20261101/reference_consistency_002/README.md','reference-report.md'],
 ['experiments/visual_scene_v2_20261101/reference_consistency_002/reference_examples.png','reference-examples.png'],
 ['experiments/active_view_20261101/README.md','active-view-report.md'],
 ['experiments/active_view_20261101/reference_demo_002/report.json','active-view-results.json'],
 ['experiments/active_view_20261101/reference_demo_002/motion.gif','active-view.gif']
];
for(const item of files)await artifact(...item);
const refinement=path.join(vision,'refinement_001');let refine=null;
try{refine=await read(path.join(refinement,'results.json'));}catch(e){if(e.code!=='ENOENT')throw e;}
await artifact('experiments/visual_scene_v2_20261101/refinement_001/locked_plan.json','refinement-plan.json');
if(refine){
 for(const [file,name] of [['results.json','refinement-results.json'],['paired_quality.png','refinement-quality.png'],['best_worst_examples.png','refinement-examples.png']])await artifact(`experiments/visual_scene_v2_20261101/refinement_001/${file}`,name);
 try{await artifact('experiments/visual_scene_v2_20261101/refinement_001/README.md','refinement-report.md');}catch(e){if(e.code!=='ENOENT')throw e;}
}
let activeCamera=null;
try{activeCamera=await read(path.join(vision,'active_camera_001/results.json'));}catch(e){if(e.code!=='ENOENT')throw e;}
if(activeCamera){
 for(const [file,name] of [['results.json','active-camera-results.json'],['locked_plan.json','active-camera-plan.json'],['README.md','active-camera-report.md'],['quality.png','active-camera-quality.png'],['case_00/wrist_before_after.png','active-camera-images.png'],['case_00/motion.gif','active-camera-motion.gif']])await artifact(`experiments/visual_scene_v2_20261101/active_camera_001/${file}`,name);
}
const proposed=path.join(root,'experiments/visual_active_v3_20261101');
const plannedTraining={config:await read(path.join(proposed,'PROPOSED_CONFIG.json')),heads:await read(path.join(proposed,'model_info.json'))};
for(const [file,name] of [['PLAN.md','v3-plan.md'],['PROPOSED_CONFIG.json','v3-config.json'],['model_info.json','v3-heads.json'],['capture-request.schema.json','v3-request-schema.json'],['DATA_CONTRACT.md','v3-data-contract.md'],['example/capture_requests.jsonl','v3-request-example.jsonl']])await artifact(`experiments/visual_active_v3_20261101/${file}`,name);
const data={updatedAt:new Date().toISOString(),activeCamera,plannedTraining,training:{epochs:91,updatesPerModel:34125,seeds:3,models:6,parameters:904112,
 correctedTest:[{panel:'2.000 IID-Szenen',camera:'Fest',position:5.95,count:.9635,recall:.8852},{panel:'2.000 IID-Szenen',camera:'Fest + Hand',position:5.11,count:.9665,recall:.9189},{panel:'512 veränderte Quaderszenen',camera:'Fest',position:17.43,count:.6003,recall:.2589},{panel:'512 veränderte Quaderszenen',camera:'Fest + Hand',position:14.92,count:.6654,recall:.3537}]},
 ensemble:await read(path.join(vision,'uncertainty_001/results.json')),rgb:await read(path.join(vision,'image_consistency_001/results.json')),
 reference:await read(path.join(vision,'reference_consistency_002/results.json')),
 activeView:await read(path.join(root,'experiments/active_view_20261101/reference_demo_002/report.json')),
 refinement:refine,refinementStatus:await read(path.join(refinement,'status.json'))};
await fs.writeFile(path.join(publicRoot,'vision-research-data.json'),JSON.stringify(sanitize(data)));
await fs.writeFile(path.join(assets,'manifest.json'),JSON.stringify({updatedAt:data.updatedAt,files:manifest},null,2));

// Export full curves and a bounded geometry selection. Avoid copying the
// thousands of local QA images into a hosted documentation snapshot.
const snapshot=await buildSnapshot(root,{transport:'snapshot'});
for(const run of snapshot.runs){
 run.artifacts=run.artifacts.filter(a=>!a.kind.startsWith('geometry')||/^best_.*scene000[0-3]_/.test(a.name)||/^epoch_000_/.test(a.name));
}
for(const entry of await registry(root)){
 const base=inside(root,entry.directory);let extra=[];
 if(entry.geometryIndex)extra=await read(inside(base,entry.geometryIndex));
 const listed=[...(entry.artifacts||[]),...extra];const run=snapshot.runs.find(r=>r.id===entry.id);
 for(const a of run.artifacts){
  const source=listed.find(x=>x.name===a.name);if(!source)throw Error(`Missing source for ${a.name}`);
  const target=path.join(publicRoot,'training-assets',entry.id,a.name);await fs.mkdir(path.dirname(target),{recursive:true});
  await fs.copyFile(inside(base,source.file),target);
 }
}
await fs.writeFile(path.join(publicRoot,'training-data/index.json'),JSON.stringify(snapshot));
console.log(JSON.stringify({reports:manifest.length,refinementComplete:!!refine,geometryAssets:snapshot.runs.reduce((n,r)=>n+r.artifacts.filter(a=>a.kind.startsWith('geometry')).length,0)}));
