// Read Site authorization through hidden stdin; never persist it.
import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
if(process.stdin.isTTY)process.stdin.setRawMode(true);
process.stdin.setEncoding('utf8');process.stdin.resume();
console.log('Ready for private Site verification JSON on stdin (input hidden).');
const input=await new Promise((resolve,reject)=>{
 let text='';
 const receive=chunk=>{
  text+=chunk;
  if(text.includes('\u0003'))reject(new Error('Cancelled'));
  if(/[\r\n]/.test(text)){
   process.stdin.off('data',receive);process.stdin.pause();
   if(process.stdin.isTTY)process.stdin.setRawMode(false);
   try{resolve(JSON.parse(text.trim()))}catch{reject(new Error('Invalid verification input'))}
  }
 };
 process.stdin.on('data',receive);
});
const {url,token}=input;
const base=path.resolve('sites/research-actor-critic-editor/public');
const digest=b=>createHash('sha256').update(b).digest('hex');
async function verify(file){
 const response=await fetch(new URL('/'+file,url),{headers:{'OAI-Sites-Authorization':`Bearer ${token}`},signal:AbortSignal.timeout(20000)});
 if(!response.ok)throw Error(`${file}: HTTP ${response.status}`);
 const live=Buffer.from(await response.arrayBuffer()),local=await fs.readFile(path.join(base,file));
 let hostingInjection=false;
 if(digest(live)!==digest(local)&&file.endsWith('.html')){
  const liveText=live.toString(),localText=local.toString(),end=localText.lastIndexOf('</body>');
  const before=localText.slice(0,end),after=localText.slice(end);
  if(end>=0&&liveText.startsWith(before)&&liveText.endsWith(after)){
   const injected=liveText.slice(before.length,liveText.length-after.length);
   hostingInjection=injected.startsWith('<script>(function(){function c()')&&injected.endsWith('</script>')&&
     injected.includes('__CF$cv$params')&&injected.includes('/cdn-cgi/challenge-platform/');
  }
 }
 if(digest(live)!==digest(local)&&!hostingInjection){
  const liveText=live.toString(),localText=local.toString();
  let prefix=0;while(prefix<Math.min(liveText.length,localText.length)&&liveText[prefix]===localText[prefix])prefix++;
  console.log(JSON.stringify({file,status:response.status,type:response.headers.get('content-type'),
   title:liveText.match(/<title>([^<]*)<\/title>/)?.[1],live_bytes:live.length,local_bytes:local.length,
   contains_planned_marker:liveText.includes('Wissenschaftlicher Vergleich nicht gestartet'),
   common_prefix_chars:prefix,first_difference_live:liveText.slice(prefix,prefix+180),first_difference_local:localText.slice(prefix,prefix+180)}));
  throw Error(`${file}: served content mismatch`);
 }
 return {file,served_sha256:digest(live),source_sha256:digest(local),
   cloudflare_html_injection_excluded:hostingInjection,status:response.status};
}
const manifest=JSON.parse(await fs.readFile(path.join(base,'actor-critic-evidence/manifest.json'),'utf8'));
const files=['actor-critic.html','actor-critic.css','actor-critic-entry.css','atlas-theme.css','index.html','findings.html','trainings.html',
 'actor-critic-evidence/manifest.json',...manifest.files.map(f=>'actor-critic-evidence/'+f.name)];
const checks=[];
for(const file of files)checks.push(await verify(file));
const result={passed:true,url:new URL('/actor-critic.html',url).href,served_files:checks,access_preserved:true,visual_browser_qa:'unavailable: local browser disabled in Work settings'};
await fs.writeFile('experiments/critic_warmstart_20261104/frontend-verification.json',JSON.stringify(result,null,2));
console.log(JSON.stringify({passed:true,matched_files:checks.length,url:result.url}));
