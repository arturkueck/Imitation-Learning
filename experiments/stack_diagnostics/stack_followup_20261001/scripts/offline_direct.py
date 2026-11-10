"""Deterministic chunks on the unchanged expert panel and all train/valid frames."""
import json
import numpy as np,torch
from direct_common import OUT,ROOT,DirectChunk,flatten,KEYS
from transport_data import demos,history,summary
from balance_common import event
torch.set_num_threads(4);torch.backends.cuda.matmul.allow_tf32=False;ck=torch.load(OUT/'model_final.pth',map_location='cpu',weights_only=False);model=DirectChunk().cuda().eval();model.load_state_dict(ck['ema'])
def infer(ob):
    x=flatten(ob);parts=[]
    with torch.no_grad():
        for i in range(0,len(x),128):parts.append(model(torch.tensor(x[i:i+128],device='cuda')).cpu().numpy())
    return np.concatenate(parts)
prior=ROOT/'experiments/stack_diagnostics/stack_switch_20261001';panel=np.load(prior/'panel.npz');chunks=infer({k:panel[k] for k in KEYS});np.savez_compressed(OUT/'offline_predictions.npz',chunks=chunks,expected=panel['expected'])
rows=[];refs=[];targets=[]
for d in sorted(demos(),key=lambda r:int(r['name'].split('_')[-1])):
    k=event(d)
    for i in range(len(d['actions'])):
        rows.append(history(d,i));refs.append(dict(demo=d['name'],split=d['split'],frame=i,offset=i-k,phase=int(d['phase'][i])));targets.append(d['actions'][np.clip(np.arange(i-1,i+15),0,len(d['actions'])-1)])
ob={k:np.stack([r[k] for r in rows]) for k in KEYS};pred=infer(ob);target=np.array(targets);np.savez_compressed(OUT/'all_expert_predictions.npz',chunks=pred,expected=target);(OUT/'all_expert_refs.json').write_text(json.dumps(refs));stats={}
for split in ('train','valid'):
    m=np.array([r['split']==split for r in refs]);stats[split]=dict(frames=int(m.sum()),chunk_mse=float(((pred[m]-target[m])**2).mean()),executed_first_xyz_mse=float(((pred[m,1,:3]-target[m,1,:3])**2).mean()))
(OUT/'offline_loss.json').write_text(json.dumps(stats,indent=2));print(json.dumps(stats,indent=2))
