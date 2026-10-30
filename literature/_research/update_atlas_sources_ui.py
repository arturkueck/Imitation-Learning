from pathlib import Path
P=Path(__file__).resolve().parents[2]/'sites/research-atlas-editorial/.sites-checkout/public'
p=P/'app.js';s=p.read_text(encoding='utf-8')
s=s.replace("n+' papers · 48 reviewed keynotes'","n+' papers · '+papers.reduce((a,p)=>a+p.notes.length,0)+' reviewed keynotes';const metric=document.querySelector('.stats>div:nth-child(2) b');if(metric)metric.textContent=papers.reduce((a,p)=>a+p.notes.length,0)")
s=s.replace("'All 48 keynotes exported'","'All keynotes exported'")
s=s.replace('The library is a snapshot from 21 October 2026.','The library includes six additional papers reviewed on 29 October 2026. Lines are frozen layout-text rows; formulas, spacing and multi-column extraction may contain artifacts. Use the PDF to verify mathematical expressions.')
s=s.replace('${recommendationHTML(p)}${p.notes.map(noteHtml)', '${p.readingEdition?`<p><a href="${esc(p.readingEdition)}" target="_blank" rel="noopener">Numbered reading edition ↗</a> · <a href="${esc(p.sourcePdf)}" target="_blank" rel="noopener">Publisher / arXiv source ↗</a></p><p class="source-description">Project relevance (editorial interpretation): ${esc(p.projectRelevance)}</p>`:""}${recommendationHTML(p)}${p.notes.map(noteHtml)')
s=s.replace('<button class="button" data-copy-citation="${n.id}"', '${p.readingEdition?`<p><a href="${esc(p.readingEdition)}" target="_blank" rel="noopener">Open numbered reading edition ↗</a></p>`:""}<button class="button" data-copy-citation="${n.id}"')
p.write_text(s,encoding='utf-8')
p=P/'library.html';s=p.read_text(encoding='utf-8').replace('acht Arbeiten und 48','14 Arbeiten und 84').replace('8 papers · 48 keynotes','14 papers · 84 keynotes').replace('<b>08</b>','<b>14</b>').replace('<b>48</b>','<b>84</b>');p.write_text(s,encoding='utf-8')
