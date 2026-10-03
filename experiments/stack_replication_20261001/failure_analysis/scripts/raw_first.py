"""Disambiguate literal first predicted position (past action) from first executed position."""
import numpy as np
from common import *
rows=[]
for kind in ('direct','diffusion'):
    for seed in (1,2,3):
        a=direct_chunks(seed)[:,None] if kind=='direct' else np.load(OUT/f'diffusion_seed{seed}_ddim10.npz')['chunks']
        xy,xyz,_=fields(a);x=xy.mean(1);z=xyz.mean(1)
        for group,mask in [('all_panel',np.ones(420,bool)),('transport_6_10',OFFSETS>=6)]:
            for tail in ([1,2,3],list(range(1,16))):
                delta=x[mask,0]-x[mask][:,tail].mean(1)
                rows.append(dict(model=kind,training_seed=seed,group=group,first_raw_index=0,position_1based=1,is_executed=False,comparison_indices=tail,first_xy_mean=float(x[mask,0].mean()),later_xy_mean=float(x[mask][:,tail].mean()),paired_xy_delta_mean=float(delta.mean()),fraction_first_weaker=float((delta<0).mean()),first_xyz_mean=float(z[mask,0].mean()),later_xyz_mean=float(z[mask][:,tail].mean())))
dump('raw_first_vs_later.json',rows);csvwrite('raw_first_vs_later.csv',rows)
print(json.dumps([r for r in rows if r['group']=='transport_6_10' and len(r['comparison_indices'])==3],indent=2))
