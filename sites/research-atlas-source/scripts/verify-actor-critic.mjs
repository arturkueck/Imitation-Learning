import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
const root=path.resolve('public');
const html=await fs.readFile(path.join(root,'actor-critic.html'),'utf8');
for(const match of html.matchAll(/(?:href|src)="([^"#]+)"/g)){
  const link=match[1].split(/[?#]/)[0];if(/^(https?:|mailto:)/.test(link))continue;
  await fs.access(path.join(root,link));
}
const evidence=path.join(root,'actor-critic-evidence');
const manifest=JSON.parse(await fs.readFile(path.join(evidence,'manifest.json'),'utf8'));
for(const f of manifest.files){
  const buf=await fs.readFile(path.join(evidence,f.name));
  if(createHash('sha256').update(buf).digest('hex')!==f.published_sha256)throw Error(`Hash mismatch: ${f.name}`);
  if(/[A-Z]:\\|C:\\Users|siwc_bypass|bearer_token/i.test(buf.toString()))throw Error(`Unsanitized public artifact: ${f.name}`);
}
const status=JSON.parse(await fs.readFile(path.join(evidence,'setup-status.json'),'utf8'));
const config=JSON.parse(await fs.readFile(path.join(evidence,'config.json'),'utf8'));
if(status.scientific_training_started!==false||status.efficacy_demonstrated!==false||config.training_enabled!==false)throw Error('Invalid scientific training status');
if(!status.bounded_workflow.passed||!status.bounded_workflow.checkpoint_restore_tested)throw Error('Missing pipeline proof');
if(config.arms.A.bc_coefficient!==0||config.arms.B.bc_coefficient!==0||config.arms.C.bc_coefficient<=0)throw Error('Incorrect BC ablation');
for(const arm of Object.values(status.arms))if(!arm.finite_losses||!arm.completion_reference_unchanged||!arm.real_rollout_completed)throw Error('Incomplete technical arm');
const navigation=await fs.readFile(path.join(root,'navigation.js'),'utf8');
const trainings=await fs.readFile(path.join(root,'trainings.html'),'utf8');
const methods=await fs.readFile(path.join(root,'learning-method-content.js'),'utf8');
if(!trainings.includes('value="actor-critic"')||navigation.includes("label:'Actor-Critic · Methodensetup'")||!methods.includes('keinen Critic-Warmstart-Vorteil'))throw Error('Missing inline Actor-Critic explanation');
if(!html.includes('Wissenschaftlicher Vergleich nicht gestartet')||!html.includes('keinen Critic-Warmstart-Vorteil'))throw Error('Missing claim boundaries');
console.log(`Actor-Critic documentation verified: ${manifest.files.length} hashed artifacts; all 3 technical arms; scientific training disabled.`);
