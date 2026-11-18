import fs from 'node:fs/promises';
import {sections,categoryNavigation,categoryContext} from '../public/navigation.js';
const pages=['index.html','findings.html','library.html','trainings.html','vision.html','actor-critic.html'];
for(const page of pages){
  const file=new URL(`../public/${page}`,import.meta.url);
  let html=await fs.readFile(file,'utf8');
  const training=['trainings.html','vision.html','actor-critic.html'].includes(page);
  const active=training?'trainings.html':page==='findings.html'?'index.html':page;
  const header=`<!-- atlas-navigation:start --><header class="atlas-header"><a class="atlas-brand" href="index.html">a. <span>research atlas</span></a><nav class="atlas-nav" aria-label="Hauptnavigation">${sections.map(s=>`<a href="${s.href}"${s.href===active?' aria-current="page"':''}>${s.label}</a>`).join('')}</nav></header><!-- atlas-navigation:end -->`;
  if(html.includes('<!-- atlas-navigation:start -->'))html=html.replace(/<!-- atlas-navigation:start -->[\s\S]*?<!-- atlas-navigation:end -->/,header);
  else if(page==='library.html')html=html.replace(/<body[^>]*>/,`<body class="library-page">${header}`);
  else html=html.replace(/<header\b[\s\S]*?<\/header>/,header);
  if(!html.includes('href="navigation.css"'))html=html.replace('</head>','<link rel="stylesheet" href="navigation.css"></head>');
  if(page==='library.html')html=html.replace(/<a class="nav" href="(?:trainings|findings)\.html">[\s\S]*?<\/a>/g,'');
  html=html.replace(/<aside class="ac-entry"[\s\S]*?<\/aside>/g,'');
  if(training){
    const selected=page==='actor-critic.html'?'robot':'vision';
    const block=`<!-- model-navigation:start -->${categoryNavigation(selected)}<div id="category-context">${categoryContext(selected,page)}</div><!-- model-navigation:end -->`;
    if(html.includes('<!-- model-navigation:start -->'))html=html.replace(/<!-- model-navigation:start -->[\s\S]*?<!-- model-navigation:end -->/,block);
    else if(page==='trainings.html')html=html.replace(/<div id="categories"[\s\S]*?<\/div>/,block);
    else html=html.replace(/<main[^>]*>/,match=>`${match}${block}`);
  }
  await fs.writeFile(file,html);
}
console.log('Shared navigation synchronized across 6 pages.');

// Keep the detailed method documentation available inside the learning-method selector.
const actorPage=await fs.readFile(new URL('../public/actor-critic.html',import.meta.url),'utf8');
const actorBody=actorPage.match(/<main[^>]*>([\s\S]*?)<\/main>/)[1].replace(/<!-- model-navigation:start -->[\s\S]*?<!-- model-navigation:end -->/,'').replace(/<h1>/g,'<h3>').replace(/<\/h1>/g,'</h3>');
await fs.writeFile(new URL('../public/learning-method-content.js',import.meta.url),'export const actorCriticContent = '+JSON.stringify(actorBody)+';\n');
