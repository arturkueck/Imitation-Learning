"""Cross-check published aggregates against complete recorded rollout pairs."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import argparse
import json
import subprocess

ROOT=Path(__file__).resolve().parents[2]
def read(path):return json.loads(path.read_text(encoding='utf-8'))


class Page(HTMLParser):
    def __init__(self):super().__init__();self.ids=[];self.links=[]
    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        if 'id' in attrs:self.ids.append(attrs['id'])
        for key in ('href','src'):
            if key in attrs:self.links.append(attrs[key])


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--public',type=Path,required=True);args=parser.parse_args();public=args.public.resolve()
    evidence=read(public/'curriculum-evidence/conclusion.json');run=ROOT/'praxis/results/curriculum/approach_bc_correction_v1/ready_001'
    rows=read(run/'rollouts.json');assert len(rows)==1050
    for panel,models in evidence['training']['summary'].items():
        for model,policies in models.items():
            selected=[r for r in rows if r['panel']==panel and r['model']==model]
            starts={}
            for r in selected:
                if r['seed'] in starts:assert starts[r['seed']]==r['initial_sha256']
                starts[r['seed']]=r['initial_sha256']
            for policy,v in policies.items():
                subset=[r for r in selected if r['policy']==policy]
                assert len(subset)==v['n'] and sum(r['success'] for r in subset)==v['successes']
    for panel,comparators in evidence['training']['paired'].items():
        for comparator,policies in comparators.items():
            ref={(r['model'],r['seed']):r['success'] for r in rows if r['panel']==panel and r['policy']==comparator}
            for policy,v in policies.items():
                selected=[r for r in rows if r['panel']==panel and r['policy']==policy]
                assert sum(r['success'] and not ref[r['model'],r['seed']] for r in selected)==v['gains']
                assert sum(not r['success'] and ref[r['model'],r['seed']] for r in selected)==v['losses']
    page=Page();page.feed((public/'curriculum.html').read_text(encoding='utf-8'));assert len(page.ids)==len(set(page.ids))
    for link in page.links:
        parsed=urlsplit(link)
        if not parsed.scheme and parsed.path:assert (public/unquote(parsed.path).lstrip('/')).exists(),link
    text=(public/'curriculum-evidence/conclusion.json').read_text(encoding='utf-8')
    assert ':\\' not in text and '/Users/' not in text and '.pth' not in text
    index=read(public/'training-data/index.json');correction=next(r for r in index['runs'] if r['id']=='bc-approach-correction')
    assert correction['status']=='completed' and len(correction['models'])==12 and len(correction['curves'])==60
    assert evidence['dataset']['train_families']==36 and evidence['dataset']['validation_families']==9
    if (public.parent/'.git').exists():
        original=json.loads(subprocess.check_output(['git','show','HEAD:public/training-data/index.json'],cwd=public.parent))
        assert {r['id']:r for r in original['runs'] if not r['id'].startswith('bc-')}=={r['id']:r for r in index['runs'] if not r['id'].startswith('bc-')}
    print('OK: 1050 rollouts, per-seed counts, paired gains/losses, initial-state equality, page links/IDs, 12 components, 60 loss points, 36/9 accepted families, public-data scope and unrelated training records.')


if __name__=='__main__':main()
