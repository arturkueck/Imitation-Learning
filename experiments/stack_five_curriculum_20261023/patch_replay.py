from pathlib import Path
p=Path('experiments/stack_five_curriculum_20261023/runner.py');s=p.read_text(encoding='utf-8')
s=s.replace('def train(parent,', '''class ReplayPool:
    def __init__(self,rows):
        self.pools=[EpisodePool(rows,n) for n in sorted({r['count'] for r in rows if r['success'] and r['split']=='train'})]
        assert self.pools
    def sample(self,rng,n):
        samples=[self.pools[int(rng.integers(len(self.pools)))].sample(rng,1) for _ in range(n)]
        return tuple(np.concatenate([v[k] for v in samples]) for k in range(3))

def train(parent,''')
s=s.replace('replay=EpisodePool(earlier,3)','replay=ReplayPool(earlier)')
s=s.replace("mixture='32 original +16 earlier three-cube +16 new height'", "mixture='32 original +16 earlier heights +16 new height'")
s=s.replace("decisions.append(dict(height=n,gates=gates));write(OUT/'decisions.json',decisions)","decisions.append(dict(height=n,gates=gates));write(OUT/'decisions.json',decisions)\n            earlier=earlier+rows")
s=s.replace("train(p,i+1,'direct',5,0,rows,earlier,180000", "train(p,i+1,'direct',5,0,rows,json.loads((prior.OUT/'dataset_manifest.json').read_text())['rows'],180000")
s=s.replace("text+=['## Interpretation'", """text+=['## Actual optimizer updates']
    for p in (OUT/'training').glob('*/status.json'):
        if 'technical_smoke' not in str(p):text.append(f'- {p.parent.name}: {json.loads(p.read_text())}')
    text+=['## Collected dataset counts']
    for p in (OUT/'datasets').glob('*/manifest.json'):
        d=json.loads(p.read_text());rr=d['rows'];text.append(f\"- {p.parent.name}: {len(rr)} attempts, {sum(r['success'] and r['split']=='train' for r in rr)} training successes, {sum(r['success'] and r['split']=='valid' for r in rr)} validation successes; complete={d['complete']}\")
    if (OUT/'decisions.json').exists():text+=['## Gates and decisions', '```json', (OUT/'decisions.json').read_text(), '```']
    text+=['## Interpretation'""")
p.write_text(s,encoding='utf-8')
