from pathlib import Path
import json,re,hashlib
out=Path('experiments/stack_transition_quality_20261024').resolve();doc=(out/'README.md').read_text(encoding='utf-8')
links=re.findall(r'\]\(([^)]+)\)',doc)
for link in links:
 if not link.startswith('https://'):assert (out/link).exists(),link
x=json.loads((out/'illustration.json').read_text());assert x['synthetic'] and abs(sum(x['relative_new_pool_shares'])-1)<1e-12
assert all(.5<=w<=2 for w in x['raw_weights']);assert abs(sum(x['replay_fractions'].values())-1)<1e-12
files=[out/'README.md',out/'make_figures.py',out/'illustration.json',*sorted((out/'figures').glob('*'))]
manifest=dict(status='DOCUMENTED_PROPOSAL_ONLY',new_training_started=False,figures_visually_checked=True,synthetic_example_values=True,artifacts={str(p.relative_to(out)):dict(bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in files})
(out/'documentation_manifest.json').write_text(json.dumps(manifest,indent=2))
print('Documentation links and illustrative weights verified; 3 PNG and 3 SVG figures.')
