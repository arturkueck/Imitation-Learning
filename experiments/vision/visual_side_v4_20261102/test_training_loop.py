"""Exercise the real six-track loop on tiny synthetic CPU nets, not V4 data."""
import sys,copy
from pathlib import Path
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parent))
from pipeline.common import save,sha,read
import pipeline.train as trainer

def test_six_tracks_validation_barriers_and_exact_update_counts(tmp_path,monkeypatch):
    run=tmp_path/'run';run.mkdir();(tmp_path/'parents').mkdir()
    class Tiny(torch.nn.Module):
        def __init__(self):super().__init__();self.weight=torch.nn.Parameter(torch.tensor(.1))
        def to(self,*a,**kw):return self
    parents=[]
    for seed in [1,2,3]:
        path=tmp_path/'parents'/f'{seed}.pth';torch.save(dict(model=Tiny().state_dict()),path)
        parents.append(dict(seed=seed,file=path.relative_to(tmp_path).as_posix()))
    cfg=dict(parents=parents,optimization=dict(maximum_epochs=2,early_stop_pair_patience=8))
    save(run/'config.json',cfg);save(run/'budget.json',dict(deadline_unix=10**12))
    seals={}
    for split in ['train','validation']:
        save(run/'data'/split/'seal.json',dict(synthetic=True));seals[split]=sha(run/'data'/split/'seal.json')
    def audit(*a,**kw):save(run/'dataset_freeze.json',dict(dataset_seals=seals))
    class FakeStore:
        def __init__(self,run,split,**kw):self.records=list(range(4))
        def __len__(self):return 4
        def __getitem__(self,index):return dict(index=index)
    def fake_pairs(rows,*args,**kw):return [dict(images=np.ones((len(rows),1),np.float32)) for _ in range(2)]
    def fake_forward(model,batch):return dict(x=model.weight.expand(len(batch['images']))),None
    def criterion(raw,*args):return (raw['x']-1).square().mean(),{},[]
    def evaluate(model,*a,**kw):
        value=float((model.weight.detach()-1).square())
        c=dict(loss=value,balanced_loss=value,after_set_error_mm=value,before_set_error_mm=value,assignment_position_mm=value,
            count_accuracy=1.,recall_at_10mm=1.,components=dict(position=value))
        return dict(loss=value,balanced_loss=value,contexts={k:copy.deepcopy(c) for k in ['initial','old','side']})
    monkeypatch.setattr(trainer,'ROOT',tmp_path);monkeypatch.setattr(trainer,'verify_protocol',lambda *a,**kw:cfg)
    monkeypatch.setattr(trainer,'audit',audit);monkeypatch.setattr(trainer,'Store',FakeStore);monkeypatch.setattr(trainer,'ScenePerception',Tiny)
    monkeypatch.setattr(trainer,'batch_pairs',fake_pairs);monkeypatch.setattr(trainer,'forward',fake_forward);monkeypatch.setattr(trainer,'paired_criterion',criterion)
    monkeypatch.setattr(trainer,'tensors',lambda x,*a:x);monkeypatch.setattr(trainer,'evaluate',evaluate)
    monkeypatch.setattr(trainer,'geometry',lambda *a,**kw:None);monkeypatch.setattr(trainer,'plots',lambda *a,**kw:None)
    original_load=torch.load
    monkeypatch.setattr(torch,'load',lambda path,**kw:original_load(path,map_location='cpu',weights_only=False))
    monkeypatch.setattr(torch.cuda,'is_available',lambda:True);monkeypatch.setattr(torch.cuda,'get_device_name',lambda:'synthetic CPU test')
    monkeypatch.setattr(torch.cuda,'get_rng_state_all',lambda:[]);monkeypatch.setattr(torch.cuda,'set_rng_state_all',lambda state:None)
    monkeypatch.setattr(torch.cuda,'is_current_stream_capturing',lambda:False)
    trainer.train(run)
    results=read(run/'results.json');assert set(results['optimizer_updates'].values())=={2}
    assert results['heldout_tests_used'] is False
    curves=read(run/'curves.json');assert len(curves)==18
    assert all(r['train_loss'] is None for r in curves if r['epoch']==0)
    assert {r['updates'] for r in curves if r['epoch']==1}=={1}
    assert {r['updates'] for r in curves if r['epoch']==2}=={2}
    assert len(read(run/'selection.json')['models'])==6
    assert read(run/'status.json')['stage']=='complete'
