"""Export the current website table, one keynote per column."""
from pathlib import Path
import csv,json
ROOT=Path(__file__).resolve().parents[2]
data=json.loads((ROOT/'sites/research-atlas-source/public/research.json').read_text(encoding='utf-8'))
papers=data['papers']
count=max(len(p.get('notes',[])) for p in papers)
headers=['Paper','Full title','Year','Topic','Innovation','Data','Method','Venue','Limits','PDF version','PDF source','Project relevance']+[f'Keynote {i}' for i in range(1,count+1)]
rows=[]
for p in papers:
    if p['id']=='demo_score':
        rows.append(['']*len(headers))
    row=[p.get(k,'') for k in ['name','fullTitle','year','topic','innovation','data','method','venue','limit','version']]
    row += [p.get('sourcePdf',p.get('pdf','')),p.get('projectRelevance','')]
    notes=[]
    for n in p.get('notes',[]):
        refs='; '.join(f'PDF p. {v[0]}, custom lines {v[1]}-{v[2]} ({v[3]})' for v in n['locators'])
        notes.append(f"{n['id']} - {n['label']}\n{n['note']}\n{refs}")
    row+=notes+['']*(count-len(notes));rows.append(row)
out=ROOT/'output/Paper_Table_Keynotes_2026-10-29.csv'
with out.open('w',encoding='utf-8-sig',newline='') as f:
    writer=csv.writer(f,delimiter=';',quoting=csv.QUOTE_ALL);writer.writerow(headers);writer.writerows(rows)
with out.open(encoding='utf-8-sig',newline='') as f:
    actual=list(csv.reader(f,delimiter=';'))
assert actual==[headers]+[[str(x) for x in r] for r in rows]
assert actual[9]==['']*len(headers)
print(f'{len(papers)} papers; blank separator after original eight papers; {out}')
