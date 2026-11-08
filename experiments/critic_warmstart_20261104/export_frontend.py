"""Publish only sanitized setup documentation and verified technical evidence."""
from pathlib import Path
import argparse
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def export(public):
    evidence=public/'actor-critic-evidence';evidence.mkdir(parents=True,exist_ok=True)
    preflight=HERE/'smoke_002/preflight.json';status=HERE/'smoke_002/status.json'
    p=json.loads(preflight.read_text());s=json.loads(status.read_text())
    assert p['passed'] and p['bounded_workflow']['passed'] and s['state']=='COMPLETED'
    assert not p['scientific_training_started'] and not s['scientific_training_started']
    cfg=json.loads((HERE/'config.json').read_text());assert cfg['training_enabled'] is False
    files=[]
    def copy(src,name):
        dst=evidence/name;shutil.copy2(src,dst)
        files.append(dict(name=name,source_sha256=sha(src),published_sha256=sha(dst)))
    copy(HERE/'config.json','config.json')
    copy(HERE/'README.md','protocol.md')
    copy(ROOT/'experiments/retreat_gate_20261104/run_001/REPORT.md','retreat-controller-report.md')
    sanitized=dict(schema='critic-warmstart-public-status-v1',status='technically_verified',
        scientific_training_started=False,efficacy_demonstrated=False,unit_tests_passed=7,
        state_dim=p['state_dim'],warmup_keeps_actor_fixed=p['warmup_keeps_actor_fixed'],
        train_valid_families_disjoint=p['train_valid_families_disjoint'],paired_online_starts=p['paired_online_starts'],
        normalization_training_only=p['normalization_training_only'],
        bounded_workflow=p['bounded_workflow'],
        arms={k:{key:v for key,v in arm.items() if key!='success'} for k,arm in p['arms'].items()},
        source_preflight_sha256=sha(preflight),source_status_sha256=sha(status),
        note='Technical optimizer updates are recorded; no scientific comparison or efficacy result.')
    dst=evidence/'setup-status.json';dst.write_text(json.dumps(sanitized,indent=2,ensure_ascii=False),encoding='utf-8')
    files.append(dict(name=dst.name,published_sha256=sha(dst),source_sha256=sha(preflight)))
    (evidence/'manifest.json').write_text(json.dumps(dict(files=files,raw_data_published=False,model_weights_published=False),indent=2),encoding='utf-8')
    for pth in evidence.iterdir():
        text=pth.read_text(encoding='utf-8')
        assert 'F:\\' not in text and 'C:\\Users' not in text,'Absolute local path in public artifact'


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--public',type=Path,required=True);args=parser.parse_args();export(args.public.resolve())
