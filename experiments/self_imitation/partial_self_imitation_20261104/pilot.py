"""Fixed-data four-arm pilot. Existing inputs stay read-only; no online RL."""
from pathlib import Path
import argparse
import collections
import hashlib
import json
import os
import random
import shutil
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = Path(__file__).resolve().parents[3]
os.environ.setdefault('NUMBA_CACHE_DIR', str(HERE / 'runtime' / 'numba_cache'))
os.environ.setdefault('CUBLAS_WORKSPACE_CONFIG', ':4096:8')
sys.path.insert(0, str(ROOT / 'praxis/src'))
sys.path.insert(0, str(ROOT / 'experiments/self_imitation/stack_transition_quality_20261024'))
import numpy as np
import torch
from transition_pilot import Pool, audit_arrays, audit_teacher, dump, extract, sha, split_audit, weighted_loss
import native_collector as native
from online_evaluation import evaluate_full

MANIFEST = ROOT / 'experiments/self_imitation/stack_transition_quality_20261024/native_data_v1/manifest.json'
ARRAYS = ROOT / 'experiments/self_imitation/stack_phased_8h_20261023/training_arrays.npz'
ORIGINAL = ROOT / 'experiments/baselines/additional_tasks/stack_two/data/image_demonstrations.hdf5'
ARMS = ('A', 'B', 'C', 'D')


def quality(a, start, stop, prefix):
    """Festes geometrisches Abschnittsgewicht, kein gelernter Critic-Score.

    Ruhige und ausgerichtete Wuerfel ergeben Werte zwischen 0.5 und 1.0.
    Hier werden nachtraegliche Outcome-Messungen fuer die Datengewichtung
    benutzt; sie gehen nicht als Beobachtungen in die trainierte Policy ein.
    Dies ersetzt noch nicht das geplante f(S_phi(tau)) aus dem Vorschlag.
    """
    pos = a['post_obs'][start:stop, :a['fingers'].shape[1]*3].reshape(stop-start, -1, 3)[:, :prefix]
    displacement = float(np.linalg.norm(pos-pos[0], axis=-1).max())
    alignment = float(np.linalg.norm(np.diff(pos[:, :, :2], axis=1), axis=-1).max())
    return float(.5 + .25*np.clip(1-displacement/.008, 0, 1) + .25*np.clip(1-alignment/.009, 0, 1))


def partial_sections(a, row):
    """First placement and verified later pickup; confirmation is never an input."""
    assert row['count'] == 3 and row['native_collector']
    result = []
    for release in np.flatnonzero(a['controller_event'] == 1):
        release = int(release)
        if a['stage'][release] != 1 or release < 9 or release+50 >= len(a['x']):
            continue
        # Ten release states and fifty subsequent outcome states all contact-free.
        lo, hi = release-9, release+51
        if not a['prefix_valid'][lo:hi, 0].all() or a['fingers'][lo:hi, :2].any():
            continue
        if not (a['stage'][:release+1] == 1).all() or a['retreat'][:release+1].any():
            continue
        result.append(dict(source=row['path'], start=0, end=release+1,
                           kind='confirmed_first_pair', confirmed_post_frame=release+50,
                           weight=quality(a, release+1, release+51, 2)))
        break
    for s in extract(a, row, grasp=dict(held_post=a['held_post'], held_known=a['held_known'])):
        stop = s['confirmed_post_frame']+1
        result.append(dict(source=row['path'], start=s['start'], end=s['end'],
                           kind='verified_next_pickup', confirmed_post_frame=stop-1,
                           weight=quality(a, stop-50, stop, s['prefix'])))
    for s in result:
        s.update(split=row['split'], family=row['initial_sha256'], teacher_sha256=row['teacher_sha256'])
    return result


def check_stop(out, deadline):
    if time.time() >= deadline or (out/'STOP').exists():
        raise TimeoutError('Fixed wall-clock cap or experiment STOP')


def collect_fixed(out, plan, deadline):
    """Fixed cohort decided before outcomes; no retry-until-success."""
    folder=out/'input';folder.mkdir()
    rows=[];env=native.historical.make_env(3)
    models=[native.historical.load(p['path']) for p in plan['parents']]
    try:
        (folder/'model.xml').write_text(env.model.get_xml(),encoding='utf-8')
        for index in range(plan['additional_collection']['attempts']):
            check_stop(out,deadline)
            seed=plan['additional_collection']['seed_start']+index
            split='train' if index<180 else 'valid'
            ti=index%3;parent=plan['parents'][ti]
            dump(out/'status.json',dict(state='COLLECTING',attempt=index+1,total=240,seed=seed,
                updated_unix=time.time(),pid=os.getpid()))
            a,r=native.collect(env,models[ti],3,seed,1000,deadline)
            audit_teacher(a,models[ti],'cuda')
            path=folder/f'{seed}.npz';np.savez_compressed(path,**a)
            r.update(path=str(path.resolve()),sha256=sha(path),split=split,native_collector=True,
                teacher=parent['path'],teacher_sha256=parent['sha256'],success=r['complete_success'],
                initial_sha256=hashlib.sha256(a['initial'].tobytes()).hexdigest(),
                initial_family_id=f'partial-self-imitation-v1:n3:seed{seed}')
            rows.append(r)
            dump(folder/'manifest.json',dict(complete=len(rows)==240,rows=rows,
                predetermined_attempts=240,train_attempts=180,valid_attempts=60,no_outcome_based_retries=True))
    finally:env.close()
    return rows


def prepare(out, extra_rows=None, technical=False):
    m = json.loads(MANIFEST.read_text())
    assert m['complete'] and m['schema'] == 'native_transition_dataset_v3'
    assert sha(ORIGINAL) == m['original_sha256']
    rows = [r for r in m['rows'] if r['count'] == 3]+(extra_rows or [])
    split_audit(rows)
    successful, failed, sources = [], [], {}
    initial_hashes = set()
    for r in rows:
        assert r['collector_schema'] == 'native_v2_forward_synchronized'
        assert r['native_grasp_measured'] and r['restored_contacts_and_grasp_verified']
        assert sha(r['path']) == r['sha256']
        assert sha(r['teacher']) == r['teacher_sha256']
        sources[r['path']] = r['sha256']
        with np.load(r['path'], allow_pickle=False) as f:
            a = {k:f[k].copy() for k in f.files}
        audit_arrays(a, 3)
        assert np.array_equal(a['post_state'][:-1], a['pre_state'][1:])
        assert len(a['x']) == r['frames']
        run = maximum = 0
        for valid in a['valid']:
            run = run+1 if valid else 0
            maximum = max(maximum, run)
        assert (maximum >= 50) == r['success']
        assert hashlib.sha256(a['initial'].tobytes()).hexdigest() == r['initial_sha256']
        initial_hashes.add(r['initial_sha256'])
        if r['success']:
            successful.append(dict(source=r['path'], start=0, end=len(a['x']),
                weight=quality(a, len(a['x'])-50, len(a['x']), 3),
                split=r['split'], family=r['initial_sha256'], kind='successful_episode'))
        else:
            failed.extend(partial_sections(a, r))
    train_success = [s for s in successful if s['split'] == 'train']
    train_failed = [s for s in failed if s['split'] == 'train']
    info = dict(source_manifest_sha256=sha(MANIFEST), sources=sources,
        original_sha256=sha(ORIGINAL), arrays_sha256=sha(ARRAYS),
        row_counts={str(k):v for k,v in collections.Counter((r['split'],r['success']) for r in rows).items()},
        partial_counts={str(k):v for k,v in collections.Counter((s['split'],s['kind']) for s in failed).items()},
        train_failed_families=len({s['source'] for s in train_failed}),
        successful_sections=successful, failed_sections=failed,
        source_initial_hashes=sorted(initial_hashes),
        limitation='Fixed data are pooled outputs from three teachers; not exact single-policy self-copy. Privileged low-dimensional simulation inputs; no visual-policy or RL claim.')
    dump(out/'dataset_audit.json', info)
    if not technical:
        assert len(train_success) >= 20 and len({s['source'] for s in train_failed}) >= 5, 'Insufficient fixed-data pilot support'
    return info, train_success, train_failed


def batch(original, groups, pool, seed, update):
    """Liefere Originaldemos und optional gespeicherte eigene Aktionen.

    x entspricht x_t, a dem gespeicherten Ziel a_t, p der Bewegungsphase.
    Mit Pool: 48 Originalframes + 16 eigene Frames, deren Abschnittsgewichte
    in w stehen. Das Gewicht stammt aus quality(), nicht aus einem Critic.
    Identische Zufallsstroeme machen die Vergleiche zwischen Armen gepaart.
    """
    # Independent deterministic streams retain identical original examples in all arms.
    rng = np.random.default_rng(np.random.SeedSequence([seed, update, 0]))
    ids = np.array([rng.choice(groups[p]) for p in rng.integers(7, size=64)])
    if pool is None:
        return original['x'][ids], original['a'][ids], original['p'][ids], ids, np.ones(64), sha_bytes(ids.tobytes())
    rr = pool.sample(np.random.default_rng(np.random.SeedSequence([seed, update, 1])), 16)
    x = np.r_[original['x'][ids[:48]], np.stack([r[0] for r in rr])].astype('float32')
    a = np.r_[original['a'][ids[:48]], np.stack([r[1] for r in rr])].astype('float32')
    p = np.r_[original['p'][ids[:48]], [r[2] for r in rr]]
    w = np.r_[np.ones(48), [r[3] for r in rr]].astype('float32')
    fingerprint = sha_bytes(ids.tobytes()+json.dumps([(r[4],r[5]) for r in rr]).encode())
    return x, a, p, ids, w, fingerprint


def sha_bytes(data):
    return hashlib.sha256(data).hexdigest()


def save_checkpoint(path, model, opt, update, parent, arm, seed):
    tmp = path.with_suffix('.tmp')
    torch.save(dict(model=model.state_dict(), optimizer=opt.state_dict(), update=update,
                    parent=parent, arm=arm, seed=seed, torch_rng=torch.get_rng_state(),
                    cuda_rng=torch.cuda.get_rng_state_all()), tmp)
    tmp.replace(path)


def evaluate(model, seeds, folder, deadline, source_hashes):
    """Save paired-start identities and compact native traces, no training reuse."""
    folder.mkdir(parents=True, exist_ok=False)
    env=native.historical.make_env(3)
    rows=[]
    try:
        for seed in seeds:
            check_stop(folder.parents[1],deadline)
            dump(folder/'progress.json',dict(state='RUNNING',completed=len(rows),planned=len(seeds),
                in_progress_seed=seed,updated_unix=time.time()))
            a,r=native.collect(env,model,3,seed,1000,deadline)
            h=hashlib.sha256(a['initial'].tobytes()).hexdigest()
            assert h not in source_hashes,'Test initial state leakage'
            assert not r['censored']
            r.update(initial_sha256=h,success=bool(r['complete_success']))
            rows.append(r)
            np.savez_compressed(folder/f'{seed}.npz',**{k:a[k] for k in
                ('initial','x','a','p','pre_obs','post_obs','stage','retreat','valid','prefix_valid','fingers','held_post','controller_event')})
            dump(folder/'results.json',dict(complete=len(rows)==len(seeds),rows=rows,
                successes=sum(r['success'] for r in rows),planned=len(seeds)))
    finally:env.close()
    dump(folder/'progress.json',dict(state='COMPLETED',completed=len(rows),planned=len(seeds),updated_unix=time.time()))
    return dict(complete=len(rows)==len(seeds),successes=sum(r['success'] for r in rows),rows=rows)


def train(out, plan, success, failed, deadline, smoke=False):
    from method import PhaseNet
    with np.load(ARRAYS, allow_pickle=False) as f:
        original = {k:f['train_'+k].copy() for k in ('x','a','p','y')}
        valid = {k:f['valid_'+k].copy() for k in ('x','a','p','y')}
    groups = [np.flatnonzero(original['p'] == p) for p in range(7)]
    pw = torch.tensor([min(50., max(1., (1-original['y'][g]).sum()/max(original['y'][g].sum(),1))) for g in groups], device='cuda')
    pools = {'A':None, 'B':Pool(success), 'C':Pool(success+failed)}
    pools['D'] = pools['C']
    steps = 5 if smoke else plan['updates']
    selected = {}
    curve = []
    for parent in plan['parents'][:1] if smoke else plan['parents']:
        seed = parent['seed']
        models, optimizers = {}, {}
        for arm in ARMS:
            torch.manual_seed(seed)
            model = PhaseNet().cuda()
            model.load_state_dict(torch.load(parent['path'], map_location='cpu', weights_only=False)['model'])
            models[arm] = model
            optimizers[arm] = torch.optim.AdamW(model.parameters(), lr=3e-5, weight_decay=1e-6)
            (out/'training'/f'{arm}_seed{seed}').mkdir(parents=True, exist_ok=False)
        for u in range(1, steps+1):
            check_stop(out, deadline)
            last_cd = None
            for arm in ARMS:
                x,a,p,ids,w,fingerprint = batch(original, groups, pools[arm], seed, u)
                if arm == 'C': last_cd = fingerprint
                if arm == 'D': assert last_cd == fingerprint
                model, opt = models[arm], optimizers[arm]
                pred,z = model(torch.as_tensor(x, device='cuda'), torch.as_tensor(p, device='cuda'))
                # pred = pi_theta(x_t); a = gespeicherte Zielaktion (nicht
                # Critic-Vorschlag). mean(-1) mittelt ueber m=4 Komponenten:
                # e_t = ||pi_theta(x_t)-a_t||_2^2 / m. Die Bildformel summiert
                # dagegen ueber Komponenten; der Code skaliert also mit 1/m.
                errors = (pred-torch.as_tensor(a, device='cuda')).square().mean(-1)
                if arm == 'A': actor = errors.mean()
                # Arm D ist die naechste vorhandene Entsprechung zu
                # (1-lambda)*L_BC + lambda*L_self mit lambda=0.25:
                # Originaldemos [:48], eigene Frames [48:], feste Gewichte.
                # Die Critic->Gewicht-Verbindung und explizite 1/H-Mittelung
                # ganzer Abschnitte sind hier noch nicht implementiert.
                elif arm == 'D': actor = .75*errors[:48].mean()+.25*weighted_loss(errors[48:], torch.as_tensor(w[48:], device='cuda'))
                else: actor = .75*errors[:48].mean()+.25*errors[48:].mean()
                # Identical original-only completion examples and coefficient in all arms.
                mask = original['p'][ids[:48]] < 6
                labels = torch.as_tensor(original['y'][ids[:48]][mask], device='cuda')
                bce = torch.nn.functional.binary_cross_entropy_with_logits(z[:48][mask], labels,
                    pos_weight=pw[torch.as_tensor(original['p'][ids[:48]][mask], device='cuda')])
                # Zusaetzlicher Lernauftrag: Abschluss einer Bewegungsphase
                # aus Originaldemos vorhersagen. Dieser BCE-Term steht nicht
                # in der abgebildeten reinen Aktions-Loss-Formel.
                loss = actor+.1*bce
                assert torch.isfinite(loss)
                opt.zero_grad(set_to_none=True)
                loss.backward()
                norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 10.)
                assert torch.isfinite(norm)
                opt.step()
                if u == 1 or u % 100 == 0 or u == steps:
                    curve.append(dict(arm=arm, seed=seed, update=u, loss=float(loss.detach()),
                        actor_loss=float(actor.detach()), completion_loss=float(bce.detach()),
                        gradient_norm=float(norm), sample_sha256=fingerprint))
                if u % 1000 == 0 or u == steps:
                    save_checkpoint(out/'training'/f'{arm}_seed{seed}'/'latest.pth', model,opt,u,parent,arm,seed)
            if u == 1 or u % 100 == 0 or u == steps:
                dump(out/'learning_curve.json', curve)
                dump(out/'status.json', dict(state='TRAINING', seed=seed, step=u, steps=steps,
                    loss=curve[-1]['loss'], completed_models=len(selected), updated_unix=time.time(), pid=os.getpid()))
            if smoke and u == steps:
                c = models['C'].state_dict(); d = models['D'].state_dict()
                assert any(not torch.equal(c[k], d[k]) for k in c), 'Quality weights have no optimizer effect'
                before = torch.load(parent['path'], map_location='cpu', weights_only=False)['model']
                for arm in ARMS:
                    assert any(not torch.equal(models[arm].state_dict()[k].cpu(), before[k]) for k in before)
        for arm in ARMS:
            model=models[arm].eval()
            with torch.no_grad():
                errors=[]
                for j in range(0,len(valid['x']),512):
                    pred,_=model(torch.as_tensor(valid['x'][j:j+512],device='cuda'),torch.as_tensor(valid['p'][j:j+512],device='cuda'))
                    errors.append((pred-torch.as_tensor(valid['a'][j:j+512],device='cuda')).square().sum().item())
            path=out/'training'/f'{arm}_seed{seed}'/'latest.pth'
            selected[f'{arm}_seed{seed}']=dict(path=str(path.resolve()),sha256=sha(path),update=steps,
                original_valid_mse=sum(errors)/(len(valid['x'])*4))
        dump(out/'trained.json', selected)
    return selected


def run(out, smoke=False):
    out.mkdir(parents=True, exist_ok=False)
    start=time.time(); deadline=start+(600 if smoke else 10800)
    dump(out/'status.json', dict(state='PREPARING', pid=os.getpid(), updated_unix=start))
    torch.set_num_threads(4)
    torch.backends.cuda.matmul.allow_tf32=False
    torch.backends.cudnn.allow_tf32=False
    torch.use_deterministic_algorithms(True)
    parents=[]
    for seed in (1,2,3):
        p=ROOT/f'experiments/self_imitation/stack_self_imitation_20261023/final_test/C_seed{seed}.pth'
        parents.append(dict(seed=seed,path=str(p),sha256=sha(p)))
    plan=dict(schema='partial-self-imitation-v1', created_unix=start, deadline=deadline,
        user_authorization='2026-11-04: Kannst du diesen Versuch direkt starten?',
        updates=5000,batch=64,lr=3e-5,weight_decay=1e-6,parents=parents,
        arms={'A':'100% original actor data', 'B':'75% original +25% successful own episodes',
              'C':'75% original +25% union of successful episodes and confirmed failed-episode sections',
              'D':'Same exact samples as C; normalized outcome-quality weights within 25% own-data component'},
        completion='Same 48 original examples in all arms; coefficient0.1',
        sampling='Own data: phase, episode, section, frame balanced. C/D identical draws.',
        quality='0.5+0.25*clip(1-displacement/8mm)+0.25*clip(1-alignment/9mm), same outcome-window rule for all own data',
        partial_rule='First pair:10 release frames+50 continuously valid contact-free outcome frames; next pickup:existing strict native extractor',
        selection='Fixed final update5000, no test-based checkpoint selection',
        test_seeds=[2026110500,2026110549], technical_seed=2026110490,
        additional_collection=dict(attempts=240,train=180,valid=60,seed_start=2026100000,
            teacher_assignment='cyclic index modulo3 fixed before outcomes',reason='Existing corpus has only3 verified failed train families; retain strict gates'),
        scope='Fixed-data low-dimensional simulation pilot; not RL, visual-policy training or real hardware',
        wall_clock_cap_seconds=10800,automatic_restart=False,
        software=dict(python=sys.version,torch=torch.__version__,numpy=np.__version__,gpu=torch.cuda.get_device_name()))
    dump(out/'protocol.json', plan)
    sourcefiles=[Path(__file__).resolve(),Path(native.__file__),Path(native.historical.__file__),
        Path(sys.modules['transition_pilot'].__file__),Path(sys.modules['online_evaluation'].__file__),
        Path(sys.modules['method'].__file__),Path(native.historical.old.__file__)]
    snapshot=out/'source_snapshot';snapshot.mkdir()
    sourcehashes={}
    for i,p in enumerate(sourcefiles):
        target=snapshot/f'{i:02d}_{p.name}';shutil.copy2(p,target)
        sourcehashes[str(p)]=dict(sha256=sha(p),snapshot=target.name)
    dump(snapshot/'manifest.json',sourcehashes)
    extra=[] if smoke else collect_fixed(out,plan,deadline)
    info,success,failed=prepare(out,extra,technical=smoke)
    selected=train(out,plan,success,failed,deadline,smoke)
    frozen=out/'frozen';frozen.mkdir()
    for name,row in selected.items():
        target=frozen/f'{name}.pth';shutil.copy2(row['path'],target)
        row['path']=str(target.resolve());assert sha(target)==row['sha256']
    dump(out/'selection.json', selected)
    if smoke:
        model=native.historical.load(selected['C_seed1']['path'])
        ev=out/'technical_evaluation';ev.mkdir()
        result=evaluate_full(model,3,[plan['technical_seed']],deadline,progress_path=ev/'stack3.json')
        assert result['complete']
        # Same seed must instantiate an identical initial state in separate envs.
        first=evaluate(model,[plan['technical_seed']+1],ev/'paired_a',deadline,set())
        second=evaluate(model,[plan['technical_seed']+1],ev/'paired_b',deadline,set())
        assert first['rows'][0]['initial_sha256']==second['rows'][0]['initial_sha256']
        dump(out/'preflight.json',dict(passed=True,all_four_arms_updated=True,cd_identical_samples=True,
            weighting_changes_updates=True,native_rollout_complete=True,excluded_from_scientific_results=True))
    else:
        ev=out/'evaluation';ev.mkdir()
        all_models={f'parent_seed{p["seed"]}':p for p in parents}|selected
        results={}
        for name,row in all_models.items():
            check_stop(out,deadline)
            assert sha(row['path'])==row['sha256']
            dump(out/'status.json',dict(state='EVALUATING',model=name,completed=len(results),total=len(all_models),
                updated_unix=time.time(),pid=os.getpid()))
            model=native.historical.load(row['path'])
            result=evaluate(model,list(range(plan['test_seeds'][0],plan['test_seeds'][1]+1)),ev/name,deadline,set(info['source_initial_hashes']))
            assert result['complete']
            if results:
                reference=next(iter(results.values()))
                assert [(r['seed'],r['initial_sha256']) for r in result['rows']]==[(r['seed'],r['initial_sha256']) for r in reference['rows']], 'Unpaired simulator starts'
            results[name]=result;dump(out/'results.json',results)
        lines=['# Fixed-data partial self-imitation pilot','',
            'Fresh paired 50-start tests, fixed update5000; three parent checkpoints. No RL or vision-training claim.','',
            '| Model | Success /50 |','|---|---:|']
        for name,r in results.items():lines.append(f'| {name} | {r["successes"]} |')
        lines+=['','C/D use identical sampled examples. B/C compare a data-selection strategy, not an isolated effect of section provenance. Quality weighting uses a hand-defined outcome score.',
            '','Parent checkpoints originate from the earlier pilot. Fixed pooled teacher data do not demonstrate improvement from exact self-copy. Test results must not be reused for checkpoint selection.']
        (out/'RESULTS.md').write_text('\n'.join(lines),encoding='utf-8')
    for path,h in info['sources'].items():assert sha(path)==h
    assert sha(ORIGINAL)==info['original_sha256'] and sha(ARRAYS)==info['arrays_sha256']
    assert sha(MANIFEST)==info['source_manifest_sha256']
    for p in parents:assert sha(p['path'])==p['sha256']
    for p,info in sourcehashes.items():assert sha(p)==info['sha256'],'Scientific source changed during run'
    dump(out/'status.json',dict(state='COMPLETED',smoke=smoke,elapsed_seconds=time.time()-start,
        inputs_unchanged=True,updated_unix=time.time(),pid=os.getpid()))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True);parser.add_argument('--smoke',action='store_true')
    args=parser.parse_args()
    try:run(args.output.resolve(),args.smoke)
    except Exception:
        if args.output.exists():dump(args.output/'status.json',dict(state='ERROR',error=traceback.format_exc(),updated_unix=time.time(),pid=os.getpid()))
        raise
