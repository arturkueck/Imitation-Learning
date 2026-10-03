from pathlib import Path
from urllib.request import urlopen, Request
from pypdf import PdfReader
import json, hashlib
p=Path(__file__).parent
urls={
 'stable_bc_author':'https://collab.me.vt.edu/Stable-BC/static/resources/Stable-BC.pdf',
 'stable_bc_aam':'https://ieeexplore.ieee.org/ielam/7083369/10805214/10829660-aam.pdf',
 'stable_bc_arxiv_v1':'https://arxiv.org/pdf/2408.06246v1',
}
for k,u in urls.items():
 try:
  d=urlopen(Request(u,headers={'User-Agent':'Mozilla/5.0'}),timeout=30).read()
  if not d.startswith(b'%PDF'): raise ValueError('not PDF')
  (p/f'{k}.pdf').write_bytes(d)
  r=PdfReader(p/f'{k}.pdf'); pages=[x.extract_text(extraction_mode='layout') for x in r.pages]
  (p/f'{k}.pages.json').write_text(json.dumps(pages,ensure_ascii=False,indent=2),encoding='utf-8')
  print(k,len(pages),hashlib.sha256(d).hexdigest(),pages[0][:900])
 except Exception as e: print(k,type(e).__name__,str(e))
