"""Mirror reviewed public source/assets without rewriting unchanged locked files."""
from pathlib import Path
import hashlib,shutil
ROOT=Path(__file__).resolve().parents[2];src=ROOT/'sites/research-vision-editor';dst=ROOT/'sites/research-atlas-source'
files=[p for folder in ['training-assets','training-data','vision-evidence'] for p in (src/'public'/folder).rglob('*') if p.is_file()]
files += [src/'public'/p for p in ['trainings.js','vision-research-data.json']]
changed=0
for p in files:
    q=dst/p.relative_to(src)
    if q.exists() and hashlib.sha256(p.read_bytes()).digest()==hashlib.sha256(q.read_bytes()).digest():continue
    q.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,q);changed+=1
print('Updated public files:',changed)
