"""Audit all new data against complete history and explicitly bind dataset seals."""
from pathlib import Path
import numpy as np
from .common import ROOT,read,save,sha,check_stop,event
from .protocol import verify_protocol,verify_imports
from .lineage import connect,assert_new_family,assert_replay,historical_duplicate
from .generate import content_db,register_content
from .samples import Store

def audit(run,main=True):
    run=Path(run);cfg=verify_protocol(run,full_sources=True)
    if main:verify_imports(cfg)
    history=connect(run/'history.sqlite',readonly=True)
    # Independent temporary audit database; never trust the collector's cache.
    db=content_db(':memory:');counts={};seals={};families=set()
    try:
        splits=['train','validation'] if main else ['development']
        for split in splits:
            folder=run/'data'/split;seal=read(folder/'seal.json')
            if main and (seal.get('smoke_only') or seal['count']!=cfg['splits'][split]['count'] or seal['seed']!=cfg['splits'][split]['seed']):raise RuntimeError('Development/partial data cannot enter main training')
            store=Store(run,split,verify=True);count=len(store.records)
            for i,r in enumerate(store.records):
                if i%128==0:
                    check_stop(run,15)
                    if main:event(run,'initializing',reason='lineage/content audit',split=split,checked=i,total=len(store.records),training_started=False)
                row=store[i];family=tuple(map(int,row['family']))
                if family in families:raise RuntimeError('Cross-split family overlap')
                families.add(family);assert_new_family(history,family)
                if family!=(seal['seed'],i):raise RuntimeError('Family moved from frozen seed/index assignment')
                duplicate=historical_duplicate(history,row)
                if duplicate:raise RuntimeError('Historical content reused in new split: '+str(duplicate))
                register_content(db,row,split)
            counts[split]=count;seals[split]=sha(folder/'seal.json')
        if main:
            source=np.load(ROOT/cfg['replay']['directory']/'family.npy',mmap_mode='r')
            for i,expected in zip(cfg['replay']['indices'],cfg['replay']['families']):
                if list(map(int,source[i]))!=expected:raise RuntimeError('Replay family mapping changed')
                assert_replay(history,source[i])
                if tuple(expected) in families:raise RuntimeError('Replay crossed into a fresh split')
        result=dict(passed=True,main_eligible=main,counts=counts,family_overlap=0,history_overlap=0,content_overlap=0,
            replay_count=cfg['replay']['count'] if main else 0,replay_role='historical_training_only',dataset_seals=seals,protocol_sha256=sha(run/'config.json'))
        save(run/('dataset_freeze.json' if main else 'development_audit.json'),result);return result
    finally:history.close();db.close()
