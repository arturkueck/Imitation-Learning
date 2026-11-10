"""Read-only verification of historical evidence; writes only beside this script."""
import hashlib, json
from pathlib import Path
import h5py, numpy as np

OUT = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):
    h = hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''): h.update(b)
    return h.hexdigest()

def main():
    norm = ROOT/'experiments/stack_diagnostics/stack_normalization_20261001'
    causal = ROOT/'experiments/stack_diagnostics/stack_causal_diagnosis_20261003'
    rep = ROOT/'experiments/stack_diagnostics/stack_replication_20261001'
    protocol = read(rep/'protocol.json')
    data = ROOT/'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'
    assert sha(data) == protocol['data_sha256']
    with h5py.File(data, 'r') as f:
        masks = {k: [x.decode() for x in f['mask/'+k][:]] for k in ('train','valid')}
        assert len(masks['train']) == 180 and len(masks['valid']) == 20
        assert not set(masks['train']) & set(masks['valid'])
        assert set(masks['train']+masks['valid']) == set(f['data'])
        train_frames = sum(len(f['data'][k]['actions']) for k in masks['train'])
        assert train_frames == 27322
    sealed = read(causal/'output_hashes.json')
    mismatches = [k for k,h in sealed.items() if sha(causal/k) != h]
    assert not mismatches, mismatches
    checkpoint_checks = []
    for r in read(norm/'verification.json')['records']:
        assert sha(r['checkpoint']) == r['checkpoint_sha256']
        checkpoint_checks.append({k:r[k] for k in ('variant','kind','seed','checkpoint_sha256')})
    phase = read(causal/'experiment_1_phases/results.json')
    base = read(causal/'experiment_0_baseline/results.json')
    assert len(phase) == 90 and len(base) == 40
    groups = {}; tails = 0; actions = 0; chunks = 0
    with h5py.File(data, 'r') as f:
        for r in phase:
            z = np.load(causal/'experiment_1_phases'/f"{r['demo']}_{r['phase']}_{r['model']}.npz")
            d = f['data'][r['demo']]; k = r['expert_frame']; t = z['trace']; m = int(z['measured'])
            assert np.array_equal(z['initial_state'], d['states'][k])
            h = hashlib.sha256(z['initial_state'].tobytes()).hexdigest()
            assert h == r['saved_state_sha256'] == r['replayed_state_sha256']
            groups.setdefault((r['demo'],r['phase']), []).append(h)
            for key in ('object','robot0_eef_pos','robot0_eef_quat','robot0_gripper_qpos'):
                assert np.array_equal(z[key][0], d['obs'][key][[max(0,k-1),k]])
            assert len(t[m:]) == 40 and np.isfinite(t).all() and abs(t[:,20:27]).max() <= 1.00001
            stable = bool(t[m-1,36]>0 and (t[m:,36]>0).all() and not t[m:,34].any() and (t[m:,35]>0).all())
            assert stable == r['sustained_success']; tails += 1; actions += len(t)
            if r['model'] == 'diffusion':
                for step in range(len(t)):
                    ci = int(np.searchsorted(z['chunk_start_steps'],step,side='right')-1)
                    slot = 1+step-int(z['chunk_start_steps'][ci]); assert slot in (1,2)
                    assert np.array_equal(t[step,20:27],z['chunks'][ci,slot])
                chunks += len(z['chunks'])
    assert len(groups)==30 and all(len(h)==3 and len(set(h))==1 for h in groups.values())
    counts = []
    # Historical A baselines live in the original replication locations.
    for kind in ('direct','diffusion'):
        for seed in (1,2,3):
            if seed == 1:
                p = ROOT/('experiments/stack_diagnostics/stack_direct_20261001/rollouts/results.json' if kind=='direct' else 'experiments/stack_diagnostics/stack_followup_20261001/state_scheduler_fixed/rollouts/results.json')
            else: p = rep/kind/f'seed_{seed}'/'rollouts/results.json'
            if not p.exists():
                # Normalization result file preserves the full original per-start rows.
                rows = read(norm/'results_normalization.json')['rollouts']
                rows = [r for r in rows if r['variant']=='A' and r['model_class']==kind and r['training_seed']==seed]
            else: rows = read(p)
            assert len(rows)==40, (kind,seed,p)
            counts.append(dict(kind=kind,seed=seed,n=40,stable_stacks=sum(bool(r['sustained_success']) for r in rows)))
    assert [r['stable_stacks'] for r in counts] == [28,30,31,0,0,0]
    for r in base:
        assert r['initial_state_sha256'] == protocol['fixed_start_hashes'][str(r['seed'])]
    result = dict(passed=True,training_or_simulation_executed=False,dataset_sha256=sha(data),
                  split=masks,train_frames=train_frames,sealed_causal_files_verified=len(sealed),
                  normalization_checkpoints_verified=checkpoint_checks,replication_counts=counts,
                  causal_baseline_counts={k:sum(bool(r[k]) for r in base) for k in ('grasp','lift','transport_started','position','lower','release','sustained_success')},
                  causal_phase_rows=90,paired_anchor_groups=30,exact_histories_verified=90,
                  stability_tails_verified=tails,finite_phase_actions=actions,executed_chunks_verified=chunks,
                  expert_controls_stable=sum(r['sustained_success'] for r in phase if r['model']=='expert'))
    (OUT/'existing_evidence_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='split'},indent=2))

if __name__=='__main__': main()
