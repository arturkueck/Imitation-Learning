"""Plot diagnostic full-dataset losses; preserve original test results separately."""
from pathlib import Path
import importlib.util, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import torch

HERE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('pilot',HERE/'pilot.py')
pilot=importlib.util.module_from_spec(spec);spec.loader.exec_module(pilot)
out=HERE/'diagnostic_001'
curves=json.loads((out/'curves.json').read_text())
model=pilot.Model()
layers=[]
for name,layer in model.named_modules():
    if isinstance(layer,(torch.nn.Conv2d,torch.nn.Linear)):
        layers.append(dict(name=name,type=type(layer).__name__,description=str(layer),
                           parameters=sum(p.numel() for p in layer.parameters())))
metadata=dict(parameters=sum(p.numel() for p in model.parameters()),layers=layers,
    input_shape=['batch',3,3,64,64],output_shape=['batch',2,3],
    torch_version=torch.__version__,optimizer_defaults=torch.optim.AdamW(model.parameters(),lr=3e-4).defaults)
(HERE/'MODEL_METADATA.json').write_text(json.dumps(metadata,indent=2,default=str),encoding='utf-8')
plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(2,2,figsize=(11,7),sharex=True,sharey=True,layout='constrained')
summary=[]
for seed in (1,2):
    for col,arm in enumerate(('fixed','fixed_wrist')):
        ax=axes[seed-1,col]
        rows=[r for r in curves if r['seed']==seed and r['arm']==arm]
        assert len(rows)==25 and all(np.isfinite(r['train_mse']) and np.isfinite(r['validation_mse']) for r in rows)
        epochs=[r['data_pass_equivalents'] for r in rows]
        ax.plot(epochs,[r['train_mse'] for r in rows],label='Training: gesamter Datensatz',color='#2563eb')
        ax.plot(epochs,[r['validation_mse'] for r in rows],label='Validation: gesamter Datensatz',color='#ea580c')
        ax.set_yscale('log');ax.grid(alpha=.2,which='both')
        ax.set_title(f"{'2 feste Kameras' if arm=='fixed' else '2 feste + Handkamera'} | Seed {seed}")
        ax.set_xlabel('Trainingsdatenpass-Äquivalente (Updates × 32 / 512)')
        ax.set_ylabel('MSE der normierten XYZ-Koordinaten')
        ax.legend(fontsize=8)
        end=rows[-1]
        summary.append(dict(seed=seed,arm=arm,train_mse=end['train_mse'],validation_mse=end['validation_mse'],
                            val_train_ratio=end['validation_mse']/end['train_mse'],
                            minimum_validation_update=min(rows,key=lambda r:r['validation_mse'])['update']))
fig.suptitle('Würfel-Lokalisierung: vollständige Trainings- und Validation-Losses\nDiagnoselauf, 600 Updates; keine Quaderdaten für Modellwahl',fontsize=13)
fig.savefig(out/'training_validation_loss.png',dpi=170)
fig.savefig(out/'training_validation_loss.svg')
plt.close(fig)
fig,ax=plt.subplots(figsize=(9,4.5),layout='constrained')
for seed in (1,2):
    for arm in ('fixed','fixed_wrist'):
        rows=[r for r in curves if r['seed']==seed and r['arm']==arm]
        ax.plot([r['data_pass_equivalents'] for r in rows],
                [r['validation_mse']-r['train_mse'] for r in rows],
                label=f"{'Fest' if arm=='fixed' else 'Fest + Hand'} | Seed {seed}")
ax.axhline(0,color='black',linewidth=.7);ax.grid(alpha=.2)
ax.set_xlabel('Trainingsdatenpass-Äquivalente');ax.set_ylabel('Validation MSE − Training MSE')
ax.set_title('Generalisierungslücke auf Würfeln – allein kein Overfitting-Beweis')
ax.legend();fig.savefig(out/'generalization_gap.png',dpi=170);plt.close(fig)
(out/'loss_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
print(json.dumps(dict(metadata=metadata,loss_summary=summary),indent=2,default=str))
