"""Freeze development-selected block2 models, one reserved test per seed."""
import json,time,shutil,os
import torch
from method import OUT,PhaseNet,evaluate,digest,write

def main():
    session=json.loads((OUT/'session.json').read_text())
    assert json.loads((OUT/'block2/status.json').read_text())['state']=='TRAINING_COMPLETE'
    folder=OUT/'final_test';folder.mkdir(exist_ok=False)
    deadline=session['deadline']-180
    selected={}
    # Freeze every model before observing any reserved test outcome.
    for seed in [1,2,3]:
        source=OUT/'block2'/f'seed{seed}'/'best.pth';target=folder/f'seed{seed}.pth';shutil.copy2(source,target)
        selected[str(seed)]=dict(path=str(target),sha256=digest(target),selection=json.loads(source.with_suffix('.json').read_text()))
    write(folder/'selection.json',dict(models=selected,seeds=list(range(84000,84100)),retreat=True,threshold=.8,deadline=deadline,selection_before_any_test=True))
    torch.set_num_threads(4);results={}
    for seed in [1,2,3]:
        if time.time()>=deadline:break
        model=PhaseNet().cuda().eval();ck=torch.load(selected[str(seed)]['path'],map_location='cpu',weights_only=False);model.load_state_dict(ck['model'])
        write(folder/'status.json',dict(state='EVALUATING',pid=os.getpid(),seed=seed,results=results))
        results[str(seed)]=evaluate(model,3,list(range(84000,84100)),folder/f'seed{seed}_test3.json',deadline,.8,True)
        assert digest(selected[str(seed)]['path'])==selected[str(seed)]['sha256']
    write(folder/'status.json',dict(state='COMPLETE' if len(results)==3 and all(r['complete'] for r in results.values()) else 'TIME_LIMIT_PARTIAL',pid=os.getpid(),results=results))

if __name__=='__main__':main()
