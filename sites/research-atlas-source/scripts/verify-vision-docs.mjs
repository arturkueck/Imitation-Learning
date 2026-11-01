import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=path.resolve('public');
const html=await fs.readFile(path.join(root,'vision.html'),'utf8');
for(const match of html.matchAll(/(?:href|src)="([^"#]+)"/g)){
 const link=match[1].split(/[?#]/)[0];if(/^(https?:|mailto:)/.test(link))continue;
 await fs.access(path.join(root,link));
}
const manifest=JSON.parse(await fs.readFile(path.join(root,'vision-evidence/manifest.json'),'utf8'));
for(const file of manifest.files){
 const actual=createHash('sha256').update(await fs.readFile(path.join(root,'vision-evidence',file.name))).digest('hex');
 if(actual!==file.published_sha256)throw Error(`Published hash mismatch: ${file.name}`);
}
const data=JSON.parse(await fs.readFile(path.join(root,'vision-research-data.json'),'utf8'));
if(data.refinement?.training_started!==false||data.refinement?.neural_optimizer_updates!==0)throw Error('Missing zero-training evidence');
for(const file of ['refinement-results.json','refinement-report.md','refinement-quality.png','refinement-examples.png'])await fs.access(path.join(root,'vision-evidence',file));
const snapshot=JSON.parse(await fs.readFile(path.join(root,'training-data/index.json'),'utf8'));
for(const run of snapshot.runs)for(const artifact of run.artifacts)await fs.access(path.join(root,artifact.url));
console.log(`Documentation verified: ${manifest.files.length} hashed reports/figures; ${snapshot.runs.length} training runs; refinement complete.`);
