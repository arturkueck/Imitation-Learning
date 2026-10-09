"""Exploratory train-demo / heldout-demo split of already collected paired responses."""
import hashlib
import json
from pathlib import Path
import time

import numpy as np

HERE=Path(__file__).resolve().parent


def main():
    started=time.monotonic();source=HERE/'intervention_live_prefix.json'
    r=json.loads(source.read_text());assert r['state']=='COMPLETE' and r['matched_live_start_gate']
    names=r['selected_train_demos'];fit_names=names[:2];held_names=names[2:]
    assert len(fit_names)==len(held_names)==2 and not set(fit_names)&set(held_names)
    split={}
    for label,demos in [('fit',fit_names),('heldout',held_names)]:
        probes=[a for row in r['rows'] if row['demo'] in demos for a in row['axes']]
        split[label]=(np.array([p['action_difference_xyz'] for p in probes]),np.array([p['observed_response_m'] for p in probes]))
    K=np.linalg.lstsq(*split['fit'],rcond=None)[0]
    old_K=np.array(json.loads((HERE/'offline.json').read_text())['dynamics_matrix'])
    def metrics(a,y,K):
        pred=a@K;norm=np.linalg.norm(y,axis=1);pnorm=np.linalg.norm(pred,axis=1)
        cosine=(y*pred).sum(1)/np.maximum(norm*pnorm,1e-15)
        rel=np.linalg.norm(y-pred,axis=1)/np.maximum(norm,1e-15)
        degenerate=norm<1e-5
        passed=(cosine>=.8)&(rel<=.5)&(~degenerate)
        return dict(axis_probes=len(a),passes=int(passed.sum()),degenerate=int(degenerate.sum()),
                    relative_error_median=float(np.median(rel)),cosine_median=float(np.median(cosine)),
                    mean_absolute_vector_error_m=float(np.linalg.norm(y-pred,axis=1).mean()))
    output=dict(state='COMPLETE',exploratory=True,policy_training_updates=0,additional_rollouts=0,
                fit_demos=fit_names,heldout_demos=held_names,dynamics_matrix=K.tolist(),expert_ols_matrix=old_K.tolist(),
                fit=metrics(*split['fit'],K),heldout=metrics(*split['heldout'],K),expert_ols_heldout=metrics(*split['heldout'],old_K),
                source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                protocol_sha256=hashlib.sha256((HERE/'CALIBRATION_PROTOCOL.md').read_bytes()).hexdigest(),
                already_collected_live_probe_seconds=r['elapsed_seconds'],
                elapsed_seconds=time.monotonic()-started,
                interpretation='Heldout-demo response check only; no proof of state contraction or task improvement; extra simulator access required')
    path=HERE/'partial_action_calibration.json';assert not path.exists()
    path.write_text(json.dumps(output,indent=2)+'\n',encoding='utf-8');print(json.dumps(output,indent=2))


if __name__=='__main__':main()
