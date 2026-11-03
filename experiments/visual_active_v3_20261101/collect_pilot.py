"""Bounded data throughput/coverage pilot; no model optimization."""
from pathlib import Path
from datetime import datetime
import json,time
import numpy as np
from data_v3 import PoseGenerator
HERE=Path(__file__).resolve().parent

def main():
    session=json.loads((HERE/'session.json').read_text());deadline=datetime.fromisoformat(session['deadline']).timestamp()
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--name',default='data_pilot_002');args=parser.parse_args()
    out=HERE/args.name;out.mkdir(exist_ok=False)
    g=PoseGenerator();start=time.time()
    try:
        bank=g.make_bank();(out/'pose_bank.json').write_text(json.dumps(bank,indent=2))
        counts=np.zeros(6,int);kinds=np.zeros(4,int);fractions=[]
        for i in range(1000):
            if time.time()>deadline-3600:raise TimeoutError('Not enough session time for perception after pilot')
            row=g.family(9363001,i,out/'families'/f'{i:06d}')
            if i<32:np.savez_compressed(out/f'sample_{i:03d}.npz',**row)
            counts[int(row['count'])]+=1;kinds[int(row['kind'])]+=1
            fractions.append(row['robot_fraction'].tolist())
            if i%25==0:
                status=dict(stage='render',families=i+1,total=1000,elapsed_seconds=time.time()-start,
                    seconds_per_family=(time.time()-start)/(i+1),rejections=g.rejections)
                (out/'progress.json').write_text(json.dumps(status,indent=2));print(json.dumps(status),flush=True)
        report=dict(passed=True,families=1000,elapsed_seconds=time.time()-start,counts=counts.tolist(),kinds=kinds.tolist(),
                    rejections=g.rejections,pose_bands={b:sum(x['band']==b for x in g.bank) for b in ['original','near','medium','oblique']},
                    seconds_per_family=(time.time()-start)/1000,source='sim_reference_collision_certificates',
                    optimizer_updates=0,seed=9363001,robot_fraction_mean=np.asarray(fractions).mean((0,1)).tolist(),
                    protocol='grey-bright shapes, disjoint camera holdout IDs, geometry OOD length .13..16m width .018..024m')
        (out/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
    finally:g.close()
if __name__=='__main__':main()
