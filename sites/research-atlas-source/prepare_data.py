from pathlib import Path
import json,re
ROOT=Path(__file__).resolve().parents[2]
DEST=Path(__file__).resolve().parent/'dist'
raw=(ROOT/'RESEARCH_NOTIZEN_2026-10-21.md').read_text(encoding='utf-8')
table=raw[raw.index('| Paper | Innovation |'):raw.index('\n\n**Konferenz und Universität')]
notes=json.loads((ROOT/'literature/_research/keynote_sources/keynotes.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'literature/_research/keynote_sources/manifest.json').read_text(encoding='utf-8'))['papers']
keys=['dagger','dart','stable_bc','act','diffusion_policy','umi','libero','open_x']
topics=['Robustness','Robustness','Robustness','Policy learning','Policy learning','Data & cameras','Transfer','Transfer']
years=[2011,2017,2025,2023,2023,2024,2023,2024]
papers=[]
for row,key,topic,year in zip(table.splitlines()[2:],keys,topics,years):
 cells=[v.strip() for v in row.strip('|').split('|')]
 name,url=re.match(r'\[(.+?)\]\((.+?)\)',cells[0]).groups()
 entries=[]
 for n in notes:
  if n['paper']!=key: continue
  matched=re.search(r'\*\*'+re.escape(n['id'])+r' — (.+?):\*\*',cells[7])
  entries.append({**n,'label':matched.group(1) if matched else 'Keynote'})
 papers.append(dict(id=key,name=name,url=url,topic=topic,year=year,innovation=cells[1],data=cells[2],method=cells[3],venue=cells[4],limit=cells[5],version=cells[6].split('<br>')[0],pdf=manifest[key]['source'],notes=entries))
(DEST/'research.json').write_text(json.dumps({'papers':papers,'updated':'21 Oct 2026','noteCount':len(notes)},ensure_ascii=False),encoding='utf-8')
assert len(papers)==8 and sum(len(p['notes']) for p in papers)==48
print('Prepared 8 papers and 48 verified keynotes.')
