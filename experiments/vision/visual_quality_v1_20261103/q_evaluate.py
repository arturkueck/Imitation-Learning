"""One fixed held-out evaluation, no checkpoint/threshold selection."""
from pathlib import Path
import numpy as np
from q_protocol import verify,read,save,sha
from q_data import load
from q_policy import ensemble,probabilities,choose,evaluate_selection
from q_calibration import wilson

def evaluate(run):
    run=Path(run);verify(run)
    if not read(run/'audit.json')['passed']:raise RuntimeError('Independent calibration audit failed; test must remain blind')
    if (run/'test_metrics.json').exists():raise RuntimeError('Test already evaluated; no repeated model selection')
    frozen=read(run/'policy_freeze.json');cal=read(run/'calibrator.json')
    if sha(run/'head_freeze.json')!=frozen['head_freeze_sha256'] or sha(run/'calibrator.json')!=frozen['calibrator_sha256']:raise RuntimeError('Policy changed before test')
    d=load(run,'reserved_test');logits,gains=ensemble(run,d);p=probabilities(logits,cal);selected=choose(d,p,gains,frozen['threshold']);metrics=evaluate_selection(run,'reserved_test',d,selected)
    m=d['eligible']&d['labelled'];pred=np.argmax(p[m],axis=1);y=d['classes'][m];matrix=np.zeros((3,3),int)
    for a,b in zip(y,pred):matrix[a,b]+=1
    save(run/'test_metrics.json',dict(policy=metrics,confusion_matrix=matrix.tolist(),labelled_eligible_examples=int(m.sum()),
        brier=float(np.mean(np.square(p[m]-np.eye(3)[y]).sum(1))) if m.any() else None,
        family_harm_wilson95=wilson(metrics['harm_count'],metrics['families']),model_selection_on_test=False))
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(10,4));bins=np.linspace(0,1,11);xs=[];ys=[]
    for lo,hi in zip(bins[:-1],bins[1:]):
        take=m&(p[:,0]>=lo)&(p[:,0]<=hi if hi==1 else p[:,0]<hi)
        if take.any():xs.append(float(p[take,0].mean()));ys.append(float((d['classes'][take]==0).mean()))
    axes[0].plot([0,1],[0,1],'--',color='gray');axes[0].plot(xs,ys,'o-');axes[0].set(xlabel='Vorhergesagtes Objektrisiko',ylabel='Beobachteter Anteil schädlicher Kandidaten',title='Kalibrierung auf blindem Test')
    axes[1].scatter([r['initial'] for r in metrics['rows']],[r['selected'] for r in metrics['rows']],s=12,alpha=.5);maximum=max([r['initial'] for r in metrics['rows']]+[r['selected'] for r in metrics['rows']]);axes[1].plot([0,maximum],[0,maximum],'--',color='gray');axes[1].set(xlabel='Anfangsfehler [mm-Äq.]',ylabel='Ausgewählte Geometrie [mm-Äq.]',title='Familien: Anfang versus Q1')
    fig.tight_layout();fig.savefig(run/'test_quality.png',dpi=140);plt.close(fig)
