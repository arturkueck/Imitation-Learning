"""Raw/transformed channel statistics on train and valid; fit stays train-only."""
import csv
from common import *
def main():
    ds=demos();rows=[]
    for variant in ('A','B','C','D'):
        n=Normalizer(variant) if variant!='A' else None
        for split in ('train','valid'):
            selected=[d for d in ds if d['split']==split]
            raw_ob={k:np.concatenate([d['obs'][k] for d in selected]) for k in KEYS}
            raw_a=np.concatenate([d['actions'] for d in selected])
            groups={'observation':(raw_ob,n.observations(raw_ob) if n else raw_ob),'action':({'actions':raw_a},{'actions':n.actions(raw_a) if n else raw_a})}
            for group,(raw,transformed) in groups.items():
                for domain,arrays in (('raw',raw),('transformed',transformed)):
                    for key,a in arrays.items():
                        a=np.asarray(a,dtype=np.float64)
                        for j in range(a.shape[1]):rows.append(dict(variant=variant,split=split,domain=domain,group=group,key=key,channel=j,n=len(a),min=float(a[:,j].min()),max=float(a[:,j].max()),mean=float(a[:,j].mean()),std=float(a[:,j].std())))
    write(OUT/'channel_distributions.json',dict(fit_split='train only',validation_used_for_fit=False,records=rows))
    with (OUT/'channel_distributions.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
if __name__=='__main__':main()
