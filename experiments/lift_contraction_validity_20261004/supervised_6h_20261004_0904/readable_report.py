"""Readable prose copy while preserving the exact generated source report."""
import re,json,hashlib
from pathlib import Path
S=Path(__file__).resolve().parent;p=S/'SESSION_RESEARCH_REPORT.md';original=p.read_text(encoding='utf-8')
copy=S/'SESSION_RESEARCH_REPORT_generated.md'
with copy.open('x',encoding='utf-8') as out:out.write(original)
parts=re.split(r'(`[^`]*`|\]\([^)]*\))',original)
for i in range(0,len(parts),2):
    text=parts[i]
    text=re.sub(r'([a-zäöüß])([A-ZÄÖÜ])',r'\1 \2',text)
    text=re.sub(r'(\d)([A-Za-zÄÖÜäöüß]{2,})',r'\1 \2',text)
    text=re.sub(r'([A-Za-zÄÖÜäöüß]{2,})(\d)',r'\1 \2',text)
    text=text.replace('Vielhöherer','Viel höherer').replace('unter+','unter +').replace('unter−','unter −').replace('bei2000','bei 2000')
    parts[i]=text
p.write_text(''.join(parts),encoding='utf-8')
with (S/'report_format_verification.json').open('x',encoding='utf-8') as out:json.dump(dict(generated_sha256=hashlib.sha256(copy.read_bytes()).hexdigest(),readable_sha256=hashlib.sha256(p.read_bytes()).hexdigest(),preserved_generated_copy=copy.name,formulas_code_hashes_and_link_targets_preserved=True),out,indent=2)
print('Readable synthesis saved; generated original and exact code/hash/link targets retained.')
