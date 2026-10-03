from pathlib import Path
from urllib.request import urlopen, Request
import hashlib, json
from pypdf import PdfReader

root = Path(__file__).resolve().parents[2]
dest = root / 'literature' / '_research'
dest.mkdir(parents=True, exist_ok=True)
sources = {
 'dagger': 'https://proceedings.mlr.press/v15/ross11a/ross11a.pdf',
 'dart': 'https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf',
 'act': 'https://www.roboticsproceedings.org/rss19/p016.pdf',
 'diffusion_policy': 'https://www.roboticsproceedings.org/rss19/p026.pdf',
 'stable_bc': root / 'latex/Stable-BC - Controlling Covariate Shift with Stable Behavior Cloning.pdf',
}
manifest = {}
for key, source in sources.items():
 path = dest / f'{key}.pdf'
 if isinstance(source, Path):
  data = source.read_bytes()
 elif path.exists():
  data = path.read_bytes()
 else:
  data = urlopen(Request(source, headers={'User-Agent': 'Mozilla/5.0'}), timeout=60).read()
 if not data.startswith(b'%PDF'):
  raise ValueError(f'Not a PDF: {key}')
 path.write_bytes(data)
 reader = PdfReader(path)
 pages = [page.extract_text(extraction_mode='layout') for page in reader.pages]
 (dest / f'{key}.txt').write_text('\n\n'.join(f'===== PDF PAGE {i+1} =====\n{t}' for i,t in enumerate(pages)), encoding='utf-8')
 (dest / f'{key}.pages.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2), encoding='utf-8')
 manifest[key] = {'source': str(source), 'sha256': hashlib.sha256(data).hexdigest(), 'pdf_pages': len(pages), 'metadata': {str(k): str(v) for k,v in (reader.metadata or {}).items()}}
 print(key, len(pages), pages[0][:350].replace('\n', ' '))
(dest / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
