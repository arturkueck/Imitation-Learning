"""Freeze PDFs and page-local layout-line references for the keynote register."""
from pathlib import Path
from urllib.request import Request, urlopen
import hashlib
import json
import pypdf

BASE = Path(__file__).resolve().parent
OUT = BASE / 'keynote_sources'
OUT.mkdir(exist_ok=True)
SOURCES = {
    'dagger': ('../dagger.pdf', 'https://proceedings.mlr.press/v15/ross11a/ross11a.pdf'),
    'dart': ('../dart.pdf', 'https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf'),
    'stable_bc': ('../stable_bc.pdf', 'https://arxiv.org/pdf/2408.06246v1'),
    'act': ('../act.pdf', 'https://www.roboticsproceedings.org/rss19/p016.pdf'),
    'diffusion_policy': ('../diffusion_policy.pdf', 'https://www.roboticsproceedings.org/rss19/p026.pdf'),
    'umi': ('umi.pdf', 'https://www.roboticsproceedings.org/rss20/p045.pdf'),
    'libero': ('libero.pdf', 'https://proceedings.neurips.cc/paper_files/paper/2023/file/8c3c666820ea055a77726d66fc7d447f-Paper-Datasets_and_Benchmarks.pdf'),
    'open_x': ('open_x.pdf', 'https://arxiv.org/pdf/2310.08864v5'),
}
manifest = {}
for key, (rel, url) in SOURCES.items():
    pdf = OUT / rel
    if not pdf.exists():
        data = urlopen(Request(url, headers={'User-Agent': 'Mozilla/5.0'}), timeout=45).read()
        assert data.startswith(b'%PDF'), url
        pdf.write_bytes(data)
    reader = pypdf.PdfReader(pdf)
    pages = [[line.rstrip() for line in page.extract_text(extraction_mode='layout').splitlines() if line.strip()] for page in reader.pages]
    (OUT / f'{key}.pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
    numbered = [f'{key}: PDF-Seiten ab 1; Z = nichtleere Layout-Textzeile je Seite; keine Original-Zeilennummern.', '']
    for p, lines in enumerate(pages, 1):
        numbered += [f'===== PDF S. {p} ====='] + [f'S{p:02d}:Z{n:03d} | {line}' for n, line in enumerate(lines, 1)] + ['']
    (OUT / f'{key}.numbered.txt').write_text('\n'.join(numbered) + '\n', encoding='utf-8')
    manifest[key] = {'pdf': rel, 'source': url, 'sha256': hashlib.sha256(pdf.read_bytes()).hexdigest(), 'pages': len(pages), 'line_counts': [len(p) for p in pages]}
    print(key, len(pages), flush=True)
(OUT / 'manifest.json').write_text(json.dumps({'pypdf_version': pypdf.__version__, 'convention': 'layout extraction, remove blank lines, retain both columns, count each page from 1', 'papers': manifest}, indent=2), encoding='utf-8')
