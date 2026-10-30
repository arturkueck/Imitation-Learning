"""Download pinned source PDFs and freeze page-local nonempty layout lines."""
from pathlib import Path
from urllib.request import Request, urlopen
from concurrent.futures import ThreadPoolExecutor
import hashlib, json, pypdf
OUT = Path(__file__).parent / 'sources_20261028'
OUT.mkdir(exist_ok=True)
SOURCES = {'demo_score':'2503.03707v2','cupid':'2506.19121v2','policy_calibrated_dagger':'2609.30462v1','reward_dagger':'2610.04054v1','demogen':'2502.16932v1','psd_quality':'2605.01544v2'}
def acquire(item):
    key,version=item
    url='https://arxiv.org/pdf/'+version
    pdf=OUT/(key+'.pdf')
    if not pdf.exists():
        data=urlopen(Request(url,headers={'User-Agent':'Mozilla/5.0'}),timeout=90).read()
        assert data.startswith(b'%PDF'), (key, data[:100])
        pdf.write_bytes(data)
    pages=[[s.rstrip() for s in p.extract_text(extraction_mode='layout').splitlines() if s.strip()] for p in pypdf.PdfReader(pdf).pages]
    (OUT/(key+'.pages.json')).write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=[f'{key} / arXiv:{version}. PDF pages start at 1. Z = custom nonempty layout line per page, not official publication lines.','']
    for p,rows in enumerate(pages,1):
        lines += [f'===== PDF S. {p} =====']+[f'S{p:02}:Z{n:03} | {s}' for n,s in enumerate(rows,1)]+['']
    (OUT/(key+'.numbered.txt')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
    result={'id':key,'version':version,'source':url,'pdf':pdf.name,'sha256':hashlib.sha256(pdf.read_bytes()).hexdigest(),'pages':len(pages),'line_counts':list(map(len,pages))}
    print(key,len(pages),pdf.stat().st_size,flush=True)
    return result
if __name__=='__main__':
    with ThreadPoolExecutor(max_workers=3) as pool: result=list(pool.map(acquire,SOURCES.items()))
    (OUT/'manifest.json').write_text(json.dumps({'retrieved':'2026-10-28','pypdf_version':pypdf.__version__,'convention':'Nonempty layout lines, page-local, both columns retained. Cite column and section.','papers':result},ensure_ascii=False,indent=2),encoding='utf-8')
