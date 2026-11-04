"""Calibrated proposal selection. Labels/GT are never selection inputs."""
from pathlib import Path
import sys,numpy as np,torch
from q_protocol import ROOT,read,sha,verify
from q_model import QualityModel
from q_data import load

def ensemble(run,data):
    run=Path(run);verify(run);frozen=read(run/'head_freeze.json');scaler=read(run/'scaler.json')
    if sha(run/'scaler.json')!=frozen['scaler_sha256']:raise RuntimeError('Scaler changed')
    x=torch.tensor(np.clip((data['x']-scaler['mean'])/scaler['std'],-8,8),dtype=torch.float32);logits=[];gains=[]
    with torch.no_grad():
        for parent in frozen['models']:
            if sha(run/parent['file'])!=parent['sha256']:raise RuntimeError('Quality checkpoint changed')
            model=QualityModel().eval();model.load_state_dict(torch.load(run/parent['file'],map_location='cpu',weights_only=False)['model']);out=model(x);logits.append(out['logits'].numpy());gains.append(out['gain'].numpy())
    return np.mean(logits,axis=0),np.mean(gains,axis=0)

def probabilities(logits,calibration):
    z=logits/calibration['temperature']+np.array(calibration['bias']);z-=z.max(axis=1,keepdims=True);p=np.exp(z)
    return p/p.sum(1,keepdims=True)

def choose(data,probs,gains,threshold):
    selected={}
    for i in range(len(gains)):
        if not data['eligible'][i] or probs[i,0]>threshold or probs[i,2]<.5 or gains[i]<1.:continue
        key=(*map(int,data['family'][i]),int(data['object_index'][i]));old=selected.get(key)
        if old is None or gains[i]>gains[old]+1e-8 or abs(gains[i]-gains[old])<=1e-8 and data['stage'][i]<data['stage'][old]:selected[key]=i
    return selected

def evaluate_selection(run,split,data,selected):
    # GT enters only after selection has finished.
    sys.path.insert(0,str(ROOT/'experiments/visual_active_v3_20261101'))
    from run import evaluate
    run=Path(run);cfg=verify(run);seed=cfg['splits'][split]['seed'];count=cfg['splits'][split]['count'];rows=[]
    for index in range(count):
        folder=run/'raw'/split/'development'/f'scene_{index:04d}';result=read(folder/'result.json');boxes=list(result['initial']);updated=0
        for obj in range(len(boxes)):
            i=selected.get((seed,index,obj))
            if i is None:continue
            stage=int(data['stage'][i]);snapshot=read(folder/f'analysis_after_sweep_{stage}.json');boxes[obj]=snapshot['raw'][obj];updated+=1
        with np.load(folder/'sample.npz',allow_pickle=False) as z:truth={k:z[k] for k in z.files}
        a=evaluate(result['initial'],truth);b=evaluate([{k:np.asarray(v) for k,v in box.items()} for box in boxes],truth)
        rows.append(dict(index=index,initial=a['error_mm'],selected=b['error_mm'],updated=bool(updated),missing=b['missing'],extra=b['extra']))
    return dict(families=count,mean_initial=float(np.mean([r['initial'] for r in rows])),mean_selected=float(np.mean([r['selected'] for r in rows])),
        harm_count=sum(r['selected']>r['initial']+1 for r in rows),coverage=sum(r['updated'] for r in rows)/count,updated_families=sum(r['updated'] for r in rows),rows=rows)
