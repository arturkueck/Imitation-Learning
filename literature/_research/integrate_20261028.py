from pathlib import Path
import json,shutil
ROOT=Path(__file__).resolve().parents[2]
SRC=Path(__file__).parent/'sources_20261028'
SITE=ROOT/'sites/research-atlas-editorial/.sites-checkout'
def main():
    papers=[]
    for name in ['review_curation','review_dagger','review_generation']:
        papers.extend(json.loads((SRC/(name+'.json')).read_text(encoding='utf-8'))['papers'])
    assert len(papers)==6
    manifest=json.loads((SRC/'manifest.json').read_text())
    dest=SITE/'public/evidence/sources_20261028';dest.mkdir(parents=True,exist_ok=True)
    for p in papers:
        key=p['id']; pages=json.loads((SRC/(key+'.pages.json')).read_text(encoding='utf-8'))
        assert len(p['notes'])>=5
        for n in p['notes']:
            for page,start,end,context in n['locators']:
                assert 1<=page<=len(pages) and 1<=start<=end<=len(pages[page-1]),(key,n)
        p['url']=p.get('url',p['pdf'].replace('/pdf/','/abs/'))
        p['sourcePdf']=p['pdf'];p['pdf']='evidence/sources_20261028/'+key+'.pdf'
        p['readingEdition']='evidence/sources_20261028/'+key+'.numbered.txt'
        p['pages']=['\n'.join(page) for page in pages]
        for ext in ['pdf','numbered.txt','pages.json']:shutil.copy2(SRC/(key+'.'+ext),dest/(key+'.'+ext))
    shutil.copy2(SRC/'manifest.json',dest/'manifest.json')
    path=SITE/'public/research.json';data=json.loads(path.read_text(encoding='utf-8'))
    ids={p['id'] for p in papers};data['papers']=[p for p in data['papers'] if p['id'] not in ids]+papers
    data['updated']='29 Oct 2026';data['noteCount']=sum(len(p['notes']) for p in data['papers'])
    path.write_text(json.dumps(data,ensure_ascii=False),encoding='utf-8')
    notes=['# Neue Paper: Quellenvermerke','Stand: 29.10.2026. Seiten ab erster PDF-Seite; Zeilen sind eigene nichtleere Layoutzeilen pro Seite. Formeln und Spalten können Extraktionsartefakte enthalten.']
    for p in papers:
        notes += ['\n## '+p['name'],p['version'],p['sourcePdf'],'\nProjektbezug (eigene Einordnung): '+p.get('projectRelevance','')]
        for n in p['notes']:notes+=['\n### '+n['id']+' — '+n['label'],n['note']]+[f'PDF S. {l[0]}, Z. {l[1]}–{l[2]}, {l[3]}' for l in n['locators']]
    (ROOT/'literature/PAPER_KEYNOTES_2026-10-28.md').write_text('\n\n'.join(notes),encoding='utf-8')
    print(len(data['papers']),data['noteCount'])
if __name__=='__main__':main()
