"""Fail-closed B0/B preparation and paired optimizer smoke pilot.

Historical collection only; never reads rollout endtests. Source-lift is a
geometric proxy, NOT evidence of native grasp. Production is deliberately gated.
"""
from pathlib import Path
import argparse, hashlib, json, sys, time
import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
ACTIVE = [0, 1, 2, 6]
SOURCE = ROOT / 'experiments/self_imitation/stack_five_curriculum_20261023/datasets'
ARRAYS = ROOT / 'experiments/self_imitation/stack_phased_8h_20261023/training_arrays.npz'
ORIGINAL = ROOT / 'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'
EXPECTED_ORIGINAL = '5222cbf96dc6218389d491fe7b99449295dcfc9bceb3bab8f8776ffff19fe6f8'

def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(8 * 1024 * 1024), b''): h.update(b)
    return h.hexdigest()

def dump(path, obj):
    path=Path(path);temporary=path.with_name(path.name+'.tmp')
    temporary.write_text(json.dumps(obj, indent=2), encoding='utf-8')
    temporary.replace(path)

def load_episode(row):
    with np.load(row['path'], allow_pickle=False) as f:
        return {k: f[k].copy() for k in f.files}

def audit_arrays(a, count):
    n = len(a['x'])
    assert a['x'].shape == (n, 10) and a['a'].shape == (n, 7)
    assert all(np.isfinite(v).all() for v in a.values()), 'nonfinite'
    assert np.array_equal(a['post_obs'][:-1], a['pre_obs'][1:]), 'temporal chain'
    e = count * 3
    x = np.c_[(a['pre_obs'][:, e:e+3]-a['anchor'])/.1,
              a['pre_obs'][:, e+3:e+7], a['pre_obs'][:, e+7:e+9]/.04,
              np.minimum(a['phase_steps'], 100)/20].astype('float32')
    assert np.allclose(a['x'], x, atol=1e-6, rtol=1e-6), 'pre-action input'
    assert np.all((a['p'] >= 0) & (a['p'] <= 6))
    assert not a['a'][:, 3:6].any(), 'rotation action'
    assert np.max(np.abs(a['a'])) <= 1.000001, 'action bounds'

def audit_teacher(a, model, device):
    """All executed actions, single-frame inference as used during collection."""
    import torch
    with torch.no_grad():
        for j in range(len(a['x'])):
            pred, _ = model(torch.as_tensor(a['x'][j:j+1], device=device),
                            torch.as_tensor(a['p'][j:j+1], device=device))
            assert np.allclose(pred.cpu().numpy()[0], a['a'][j, ACTIVE],
                               atol=1e-5, rtol=1e-5), ('teacher action', j)

def split_audit(rows):
    families = {}; seeds = {}
    for row in rows:
        split = row['split']; family = row['initial_sha256']
        assert split in ('train', 'valid'), 'reserved or unknown split'
        assert families.setdefault(family, split) == split, 'family leakage'
        key = (row['count'], row['seed'])
        assert seeds.setdefault(key, split) == split, 'seed family leakage'
    return families

def extract(a, row, rejections=None, grasp=None):
    """Conservative proxy windows with ALL intervening lower-prefix frames valid.

    Fixed limits: next lift within 200 frames, 50 subsequent frames of unchanged
    pair and valid prefix; source rises >=30mm from pre-transition table pose.
    Native held is absent historically, so no section is a verified pickup.
    """
    n = len(a['x']); count = row['count']; windows = []
    if grasp is not None:
        assert grasp['held_post'].shape==(n,count) and grasp['held_known'].shape==(n,),'native grasp schema'
        assert row.get('native_collector',False),'historical lower-contact signals are unverified'
    def reject(start, reason):
        if rejections is not None: rejections.append(dict(source=row['path'],post_frame=int(start),reason=reason))
    for start in np.flatnonzero(a['controller_event'] == 1):
        old_stage = int(a['stage'][start]); prefix = old_stage + 1
        if prefix >= count: reject(start,'no_next_source');continue
        # All metrics use POST-step state at their explicitly indexed frames.
        ok = a['prefix_valid'][:, prefix-2].astype(bool)
        if start < 9 or not ok[start-9:start+1].all(): reject(start,'ten_valid_release_states_missing');continue
        if int(a['p'][start]) != 6: reject(start,'release_phase_missing');continue
        next_source = prefix
        switches = np.flatnonzero((a['controller_event'] == 2) &
                                  (np.arange(n) > start))
        if not len(switches): reject(start,'no_pair_switch');continue
        switch = int(switches[0])
        if switch > start+200: reject(start,'pair_switch_timeout');continue
        ref_source_z = float(a['pre_obs'][start, next_source*3+2])
        postpos = a['post_obs'][:, :count*3].reshape(n, count, 3)
        candidates = np.flatnonzero((np.arange(n) > switch) &
            (np.arange(n) <= start+200) & (a['stage'] == prefix) &
            (a['p'] >= 3) & (postpos[:, next_source, 2] >= ref_source_z+.03))
        # Contact-plus-lift for five post-action frames is still only a proxy.
        confirmed=[]
        for candidate in candidates:
            j=int(candidate);stop=j+5
            if stop>n: continue
            signal=(a['fingers'][j:stop,next_source] if grasp is None else
                    grasp['held_post'][j:stop,next_source] & grasp['held_known'][j:stop])
            if signal.all() and (postpos[j:stop,next_source,2]>=ref_source_z+.03).all(): confirmed.append(j+4)
        if not confirmed: reject(start,'five_frame_contact_lift_missing');continue
        lift = confirmed[0]; end = lift+50
        if end >= n or not (a['stage'][switch+1:end+1] == prefix).all(): reject(start,'confirmation_censored_or_pair_changed');continue
        if not ok[start:end+1].all(): reject(start,'lower_prefix_interrupted');continue
        if a['fingers'][start:end+1, :prefix].any(): reject(start,'lower_tower_finger_contact');continue
        lower = postpos[start:end+1, :prefix]
        displacement = float(np.linalg.norm(lower-lower[0], axis=-1).max())
        xy = float(np.linalg.norm(np.diff(lower[-50:, :, :2], axis=1), axis=-1).max())
        # Clearance is intentionally absent. Fixed physical scales, no valid fit.
        quality = .50 + .25*np.clip(1-displacement/.008, 0, 1) + .25*np.clip(1-xy/.009, 0, 1)
        windows.append(dict(episode_id=str(row['path']), initial_family_id=row['initial_sha256'],
            split=row['split'], count=count, prefix=prefix, start=int(start+1), end=lift+1,
            released_post_frame=int(start), next_pair_post_frame=switch,
            lifted_proxy_post_frame=lift, confirmed_post_frame=end,
            source=row['path'], source_sha256=sha(row['path']), teacher=row['teacher'],
            teacher_sha256=row['teacher_sha256'], seed=row['seed'],
            historical_finger_contact_reliable=bool(row.get('native_collector',False)),
            verified_grasp=grasp is not None, label=('native_grasp_lift_with_continuous_prefix_validity' if grasp is not None else 'source_contact_lift_proxy_with_continuous_prefix_validity'),
            max_lower_displacement_m=displacement, max_end_neighbor_xy_m=xy,
            quality=float(quality), raw_weight=float(.5+1.5*quality)))
    return windows

def prepare(output, verify_actions=False, device='cpu'):
    output = Path(output); output.mkdir(parents=True, exist_ok=False)
    rows = []
    for height in (3, 4):
        manifest = SOURCE/f'curriculum_n{height}_cycle0/manifest.json'
        data = json.loads(manifest.read_text()); assert data['complete']
        rows.extend(data['rows'])
    split_audit(rows)
    models = {}; sections = []; rejected = 0; rejection_rows=[]; source_hashes={}
    if verify_actions:
        import torch
        sys.path.insert(0, str(ROOT/'experiments/self_imitation/stack_phased_8h_20261023'))
        from method import PhaseNet
    for row in rows:
        assert Path(row['path']).resolve().parent in {
            (SOURCE/f'curriculum_n{h}_cycle0').resolve() for h in (3, 4)}, 'source whitelist'
        assert sha(row['teacher']) == row['teacher_sha256'], 'teacher hash'
        source_hashes[row['path']]=sha(row['path'])
        a = load_episode(row); audit_arrays(a, row['count'])
        if verify_actions:
            if row['teacher'] not in models:
                model = PhaseNet().to(device).eval()
                model.load_state_dict(torch.load(row['teacher'], map_location='cpu', weights_only=False)['model'])
                models[row['teacher']] = model
            audit_teacher(a, models[row['teacher']], device)
        new = extract(a, row,rejection_rows); sections.extend(new); rejected += not bool(new)
    train = [s for s in sections if s['split'] == 'train']
    # Descriptive train-only normalizer; loss additionally divides by batch sum.
    norm = float(np.mean([s['raw_weight'] for s in train])) if train else None
    for s in sections: s['weight'] = s['raw_weight']/norm if norm else None
    manifest = dict(schema=1, estimator='proxy_only', original_sha256=sha(ORIGINAL),
        action_audit_all_frames=verify_actions, train_only_normalizer=norm,
        episodes=len(rows), episodes_without_accepted_window=rejected,
        sections=sections, verified_grasp=False, source_hashes=source_hashes,
        score_version='strict_contact_lift_v1_no_clearance',
        score_coefficients=dict(continuous_preservation_constant=.50,quietness=.25,centering=.25),
        excluded_score_components=['clearance: not measured'],rejections=rejection_rows,
        production_state='REQUIRES_COLLECTION_AND_ONLINE_EVALUATOR',
        missing=['native source grasp at lift and during confirmation',
                 'historical fingers bool used gripper dict in check_contact; requires explicit gripper geometry remeasurement',
                 'online transition evaluator and development-only checkpoint selection'])
    assert manifest['original_sha256'] == EXPECTED_ORIGINAL
    dump(output/'manifest.json', manifest)
    return manifest

class Pool:
    """Stichprobe: Phase -> Episode -> Abschnitt -> Frame.

    Ein Abschnitt traegt ein festes Gewicht; alle seine Frames erhalten dieses
    Gewicht. Das Sampling ist phasenbalanciert und bildet daher weder einen
    uniformen Frame-Mittelwert noch einen uniformen Abschnitts-Mittelwert ab.
    Der Zeitmittelwert 1/H aus der Vorschlagsformel wird nicht explizit gebildet.
    """
    def __init__(self, sections):
        self.data = {}; self.groups = {}
        for s in sections:
            path = s['source']
            if path not in self.data: self.data[path] = load_episode({'path':path})
            a = self.data[path]
            for p in np.unique(a['p'][s['start']:s['end']]):
                ids = np.arange(s['start'], s['end'])[a['p'][s['start']:s['end']] == p]
                self.groups.setdefault(int(p), {}).setdefault(path, []).append((s, ids))
        assert self.groups, 'empty pool'
    def sample(self, rng, n):
        result = []; keys = sorted(self.groups)
        for _ in range(n):
            p = keys[int(rng.integers(len(keys)))]; episodes = self.groups[p]
            path = sorted(episodes)[int(rng.integers(len(episodes)))]; choices = episodes[path]
            s, ids = choices[int(rng.integers(len(choices)))]; j = int(rng.choice(ids)); a = self.data[path]
            result.append((a['x'][j], a['a'][j, ACTIVE], p, s.get('weight', 1.), path, j))
        return result

def weighted_loss(per_frame, weights):
    """Nachahmungsfehler mit auf den Batch normierten positiven Gewichten.

    Berechnet sum_i(u_i * e_i) / sum_i(u_i), aequivalent zu
    mean_i((u_i / mean_batch(u)) * e_i). Dies ist der gewichtete BC-Baustein
    des Self-Loss; e_i ist bereits der Fehler eines einzelnen Frames.

    Die Funktion berechnet weder einen Critic-Score S_phi noch f(S_phi).
    Aktuelle Aufrufer liefern feste Dataset-Gewichte ohne Gradienten. Anders
    als ein fester Normalisierer ueber D_self ist der Nenner batchabhaengig.
    """
    assert per_frame.ndim==1 and weights.ndim==1,'weighted loss requires 1D arrays'
    assert per_frame.shape==weights.shape and len(weights)>0,'weighted loss shape or empty input'
    # Support both NumPy validation tests and differentiable Torch tensors.
    if hasattr(per_frame,'detach'):
        import torch
        assert bool(torch.isfinite(per_frame).all()) and bool(torch.isfinite(weights).all()),'nonfinite weighted loss'
        assert bool((weights>0).all()),'weights must be strictly positive'
    else:
        assert np.isfinite(per_frame).all() and np.isfinite(weights).all(),'nonfinite weighted loss'
        assert (weights>0).all(),'weights must be strictly positive'
    return (per_frame*weights).sum()/weights.sum()

def smoke(manifest_path, output, steps=3, device='cpu'):
    import torch
    sys.path.insert(0, str(ROOT/'experiments/self_imitation/stack_phased_8h_20261023'))
    from method import PhaseNet
    torch.set_num_threads(4); torch.manual_seed(17)
    manifest = json.loads(Path(manifest_path).read_text())
    for path,expected in manifest.get('source_hashes',{}).items():assert sha(path)==expected,'changed source'
    assert steps <= 10, 'smoke only, no extended training'
    sections = [s for s in manifest['sections'] if s['split']=='train']; pool = Pool(sections)
    legacy = ROOT/'experiments/self_imitation/stack_self_imitation_20261023'
    replayrows = json.loads((legacy/'dataset_manifest.json').read_text())['rows']
    replay = Pool([dict(source=r['path'], start=0, end=r['frames'], weight=1.)
                   for r in replayrows if r['count']==3 and r['split']=='train' and r['success']])
    parent = legacy/'final_test/C_seed1.pth'; parent_hash = sha(parent)
    with np.load(ARRAYS) as f: original = {k:f['train_'+k].copy() for k in ('x','a','p','y')}
    models = {}; opts = {}; before = {}
    for arm in ('B0','B'):
        m = PhaseNet().to(device); m.load_state_dict(torch.load(parent,map_location='cpu',weights_only=False)['model'])
        models[arm] = m; opts[arm] = torch.optim.AdamW(m.parameters(),lr=3e-5,weight_decay=1e-6)
        before[arm] = {k:v.detach().clone() for k,v in m.state_dict().items()}
    groups = [np.flatnonzero(original['p']==p) for p in range(7)]
    posweights=torch.tensor([min(50.,max(1.,(1-original['y'][g]).sum()/max(original['y'][g].sum(),1))) for g in groups],device=device)
    rng = np.random.default_rng(17); curves = []
    for update in range(1, steps+1):
        ids = np.array([rng.choice(groups[p]) for p in rng.integers(7,size=32)])
        rr = replay.sample(rng,16); nn = pool.sample(rng,16)
        x = np.r_[original['x'][ids], np.stack([r[0] for r in rr+nn])].astype('float32')
        actions = np.r_[original['a'][ids], np.stack([r[1] for r in rr+nn])].astype('float32')
        phases = np.r_[original['p'][ids], [r[2] for r in rr+nn]]
        sample_hash = hashlib.sha256(ids.tobytes()+json.dumps([(r[4],r[5]) for r in rr+nn]).encode()).hexdigest()
        for arm in ('B0','B'):
            model = models[arm]; opt = opts[arm]
            pred, logits = model(torch.tensor(x,device=device),torch.tensor(phases,device=device))
            error = (pred-torch.tensor(actions,device=device)).square().mean(-1)
            weights = torch.tensor([1. if arm=='B0' else r[3] for r in nn],device=device)
            actor = .5*error[:32].mean()+.25*error[32:48].mean()+.25*weighted_loss(error[48:],weights)
            mask = torch.tensor(phases[:32]<6,device=device)
            bce = torch.nn.functional.binary_cross_entropy_with_logits(logits[:32][mask],torch.tensor(original['y'][ids],device=device)[mask],pos_weight=posweights[torch.tensor(phases[:32],device=device)][mask])
            loss = actor+.1*bce; assert torch.isfinite(loss)
            opt.zero_grad();loss.backward();torch.nn.utils.clip_grad_norm_(model.parameters(),10);opt.step()
            curves.append(dict(arm=arm,update=update,loss=float(loss.detach()),sample_sha256=sample_hash))
    output = Path(output);output.mkdir(parents=True,exist_ok=False)
    for arm in models:
        assert any(not torch.equal(before[arm][k],v) for k,v in models[arm].state_dict().items())
        checkpoint = dict(model=models[arm].state_dict(),optimizer=opts[arm].state_dict(),update=steps,
            parent_sha256=parent_hash,rng=rng.bit_generator.state,arm=arm,smoke_only=True)
        path=output/f'{arm}.pth';torch.save(checkpoint,path)
        loaded=torch.load(path,map_location='cpu',weights_only=False)
        assert loaded['update']==steps and loaded['parent_sha256']==parent_hash
    assert sha(parent)==parent_hash
    dump(output/'smoke.json',dict(curve=curves,finite=True,paired_samples=True,
        actual_updates_per_arm=steps,device=device,parent_sha256=parent_hash,
        limitation='optimizer and serialization smoke; no online efficacy validation'))

def main():
    p=argparse.ArgumentParser();p.add_argument('--extract',action='store_true');p.add_argument('--verify-actions',action='store_true')
    p.add_argument('--smoke',action='store_true');p.add_argument('--train',action='store_true')
    p.add_argument('--manifest',type=Path);p.add_argument('--output',type=Path);p.add_argument('--device',default='cpu');p.add_argument('--plan',type=Path)
    args=p.parse_args()
    if args.train:
        raise SystemExit('BLOCKED: native grasp evidence, frozen protocol, online development evaluator and checkpoint-selection integration required. No production training launched.')
    if args.extract:
        assert args.output; result=prepare(args.output,args.verify_actions,args.device)
        print(json.dumps({k:v for k,v in result.items() if k not in ('sections','source_hashes','rejections')}));return
    if args.smoke:
        assert args.manifest and args.output;smoke(args.manifest,args.output,device=args.device);return
    print(json.dumps(dict(mode='DRY_RUN',long_training_started=False,production_ready=False,
        commands=['--extract --verify-actions --output NEW_DIRECTORY', '--smoke --manifest MANIFEST --output NEW_DIRECTORY'],
        blocked='Full production gates not met; see IMPLEMENTATION_VALIDATION.md')))

if __name__=='__main__':main()
