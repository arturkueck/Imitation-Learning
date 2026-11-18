"""Matched new-label budget: expert-prefix versus learner-prefix BC corrections."""
from pathlib import Path
from datetime import datetime
from types import SimpleNamespace
import argparse
import copy
import ctypes
import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
spec = importlib.util.spec_from_file_location('matched_origin_existing_bc', HERE.parent/'approach_bc_correction_v1/pipeline.py')
bc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bc)
h = bc.h
analysis = h.module('matched_origin_v2_analysis', HERE/'analysis.py')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write(path, value):
    path = Path(path)
    temp = path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')
    for attempt in range(20):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(.1)


def span(pair):
    return list(range(pair[0], pair[1]+1))


def deadline_for(plan, started):
    return min(started+plan['maximum_seconds'], datetime.fromisoformat(plan['absolute_deadline']).timestamp())-plan['exit_reserve_seconds']


def validate(plan):
    groups = [set(span(plan[k])) for k in ('development_seeds', 'confirmation_seeds')]
    for block in plan['blocks']:
        groups.extend(set(span(block[k])) for k in ('train_seeds', 'validation_seeds'))
    if any(not group for group in groups) or any(a & b for i, a in enumerate(groups) for b in groups[i+1:]):
        raise ValueError('Overlapping/empty scientific scene families')
    technical = [set(span(block[k])) for block in plan['smoke_blocks'] for k in ('train_seeds', 'validation_seeds')]
    smoke = set.union(*technical)
    if smoke & set.union(*groups) or any(a & b for i,a in enumerate(technical) for b in technical[i+1:]):
        raise ValueError('Technical/scientific overlap')
    if plan['batch_size'] != 64 or plan['maximum_labels_per_pair'] < 2 or plan['updates'] < 1:
        raise ValueError('Invalid fixed label/update contract')
    if len(set(b['id'] for b in plan['blocks'])) != len(plan['blocks']):
        raise ValueError('Duplicate data block')
    heldout = []
    for block in plan['blocks']:
        heldout.append(block['heldout_model'])
        if block['heldout_model'] in block['collector_models'] or set(block['collector_models']) != set(plan['models'])-{block['heldout_model']}:
            raise ValueError('Collector-heldout parent leakage')
    if sorted(heldout) != sorted(plan['models']):
        raise ValueError('Each parent must be collector-heldout exactly once')
    if plan['analysis']['bootstrap_unit'] != 'scene family; all three heldout contrasts retained together':
        raise ValueError('Wrong inference unit')
    if plan['sources'] != ['replay', 'standard', 'targeted'] or plan['policies'] != ['baseline', 'replay', 'standard', 'targeted']:
        raise ValueError('Unexpected comparison arms')
    if datetime.fromisoformat(plan['absolute_deadline']).utcoffset() is None or plan['exit_reserve_seconds'] < 10:
        raise ValueError('Require absolute timezone and exit reserve')
    if plan['automatic_restart'] or plan['pc_shutdown']:
        raise ValueError('Restart/shutdown not allowed')


def namespace_audit(plan):
    """Check only bounded plan/config files, never logs, data or snapshots."""
    fresh = set(span(plan['confirmation_seeds']))
    for b in plan['blocks']:
        fresh.update(span(b['train_seeds']))
        fresh.update(span(b['validation_seeds']))
    checked = []
    paths = list(HERE.parent.glob('*/config.json')) + list((ROOT/'praxis/results/curriculum').glob('*/*/plan.json'))
    def seeds(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if 'seed' in key and isinstance(item, list) and len(item) == 2 and all(type(v) is int for v in item) and item[0] <= item[1] and item[1]-item[0] < 100000:
                    yield from range(item[0], item[1]+1)
                elif 'seed' in key and type(item) is int:
                    yield item
                else:
                    yield from seeds(item)
        elif isinstance(value, list):
            for item in value:
                yield from seeds(item)
    for path in paths:
        if path.resolve() == (HERE/'config.json').resolve():
            continue
        previous = read(path)
        if previous.get('technical_only'):
            continue
        if previous.get('schema') == plan['schema']:
            state = read(path.parent/'status.json') if (path.parent/'status.json').exists() else {}
            if state.get('state') == 'READY' and not (path.parent/'launch.json').exists():
                continue  # Another sealed, never-started preparation of this revision.
        overlap = fresh & set(seeds(previous))
        if overlap:
            raise ValueError('Previously assigned scientific family: '+str(path)+' '+str(sorted(overlap)[:3]))
        checked.append(str(path.relative_to(ROOT)))
    return dict(new_families=len(fresh), checked_plans=checked, overlap=0)


def status(out, **values):
    write(out/'status.json', dict(pid=os.getpid(), updated_unix=time.time(), **values))


def verify(out):
    base, _, _ = h.libraries()
    for name, digest in read(out/'provenance.json').items():
        if base.sha(ROOT/name) != digest:
            raise ValueError('Changed frozen input: '+name)


def prepare(out, smoke=False):
    plan = read(HERE/'config.json')
    validate(plan)
    audit = namespace_audit(plan)
    if out.exists() or not out.is_relative_to(ROOT):
        raise ValueError('Require a new workspace output directory')
    plan['technical_only'] = smoke
    if smoke:
        for block, fixture in zip(plan['blocks'], plan['smoke_blocks']):
            block.update(id='technical_'+block['id'], train_seeds=fixture['train_seeds'], validation_seeds=fixture['validation_seeds'])
        plan.update(updates=4, checkpoint_every=2, minimum_train_families=1, minimum_validation_families=1,
                    development_seeds=[2026113000, 2026113000], confirmation_seeds=[2026113002, 2026113002], maximum_seconds=1200, exit_reserve_seconds=30)
        plan['analysis']['minimum_coverage_fraction_each_collector'] = 0
    if deadline_for(plan, time.time()) <= time.time():
        raise ValueError('Absolute deadline has passed')
    base, torch, _ = h.libraries()
    base.backend()
    out.mkdir(parents=True)
    write(out/'plan.json', plan)
    write(out/'namespace_audit.json', audit)
    entries = read(HERE.parent/'models.json')['models']
    files = {Path(m.__file__).resolve() for m in list(sys.modules.values()) if getattr(m, '__file__', None) and str(m.__file__).endswith('.py') and Path(m.__file__).is_file() and Path(m.__file__).resolve().is_relative_to(ROOT) and (ROOT/'praxis/.venv') not in Path(m.__file__).resolve().parents}
    files.update(HERE.glob('*.py'))
    files.update([HERE/'config.json', HERE/'README.md', HERE/'start.ps1', HERE.parent/'models.json', base.ARRAYS, base.MANIFEST, out/'plan.json',
                  ROOT/'praxis/results/curriculum/phase_skill_audit_v1/run_001/full_rollouts.json'])
    used_models = set(plan['models']) | {m for block in plan['blocks'] for m in block['collector_models']}
    files.update(ROOT/entries[m]['checkpoint'] for m in used_models)
    write(out/'provenance.json', {str(path.relative_to(ROOT)):base.sha(path) for path in sorted(files)})
    for path in files:
        if path.suffix in ('.py', '.json', '.md', '.ps1'):
            target = out/'sources'/path.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(path.read_bytes())
    write(out/'environment.json', dict(python=sys.version, platform=platform.platform(), torch=torch.__version__, cuda=torch.version.cuda,
        gpu=torch.cuda.get_device_name(0), packages={d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name']}))
    status(out, state='READY', technical_only=smoke, deadline=plan['absolute_deadline'], scientific_worker_started=False)
    print(json.dumps(dict(state='READY', technical_only=smoke, output=str(out))))


def standard_one(env, seed, plan, out, deadline):
    base, _, np = h.libraries()
    from task_extensions.stack_expert import StackExpert
    obs, initial, _ = h.reset(env, seed)
    expert = StackExpert(SimpleNamespace(base_env=env))
    for frame in range(plan['prefix_horizon']):
        base.check_stop(out, deadline)
        if expert.cube_index == 2 and expert.phase == 0:
            break
        if expert.cube_index > 2:
            raise ValueError('Expert skipped phase')
        action = expert(obs)
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
    else:
        return [], dict(accepted=False, reason='expert_prefix_timeout', expert_calls=plan['prefix_horizon'])
    prefix_calls = frame
    anchor = env.sim.data.body_xpos[env.cube_ids[2]].copy()
    entry_hash = hashlib.sha256(env.sim.get_state().flatten().tobytes()).hexdigest()
    rows = []
    for step in range(plan['approach_horizon']):
        base.check_stop(out, deadline)
        x = base.backend().native.historical.vector(obs, anchor, step)
        action = expert(obs)
        done = expert.phase != 0
        rows.append((x, action[[0, 1, 2, 6]], float(done)))
        env.step(action)
        env.sim.forward()
        obs = env._get_observations(force_update=True)
        if done:
            return rows, dict(accepted=True, frames=len(rows), prefix_frames=prefix_calls, expert_calls=prefix_calls+len(rows),
                initial_sha256=hashlib.sha256(initial.tobytes()).hexdigest(), entry_state_sha256=entry_hash)
    return [], dict(accepted=False, reason='expert_approach_timeout', expert_calls=prefix_calls+plan['approach_horizon'])


def matched_indices(left_length, right_length, maximum):
    """Unique, evenly spaced nonterminal labels plus exactly one terminal label."""
    count = min(left_length, right_length, maximum)
    if count < 2:
        raise ValueError('Insufficient paired phase labels')
    def indices(length):
        return [i*(length-2)//(count-2) for i in range(count-1)]+[length-1] if count > 2 else [0, length-1]
    return indices(left_length), indices(right_length)


def check_rows(rows, np):
    if len(rows) < 2 or [float(row[2]) for row in rows] != [0.]*(len(rows)-1)+[1.]:
        raise ValueError('Expected one final expert phase-transition label')
    if not np.isfinite(np.asarray([r[0] for r in rows])).all() or not np.isfinite(np.asarray([r[1] for r in rows])).all():
        raise ValueError('Nonfinite expert features/actions')


def assignments(block, split, plan, np):
    """Balanced, outcome-independent collector and execution-order allocation."""
    starts = span(block[split+'_seeds'])
    models = block['collector_models']
    salt = sum(ord(c) for c in block['id'])+{'train':0, 'validation':1000}[split]
    rng = np.random.default_rng(202618+salt)
    allocation = [models[i % len(models)] for i in range(len(starts))]
    rng.shuffle(allocation)
    return {seed:dict(model=model, standard_first=bool(i % 2)) for i,(seed,model) in enumerate(zip(starts,allocation))}


def family_uniform_indices(families, shape, rng, np):
    groups = [np.flatnonzero(families == family) for family in np.unique(families)]
    chosen = rng.integers(len(groups), size=shape)
    positions = rng.random(shape)
    result = np.empty(shape, dtype=np.int32)
    for group_id, group in enumerate(groups):
        mask = chosen == group_id
        result[mask] = group[(positions[mask]*len(group)).astype(np.int64)]
    return result


def collect_block(out, folder, block, plan, deadline):
    base, _, np = h.libraries()
    folder.mkdir()
    attempts = []
    manifest = {}
    allocated = {split:assignments(block, split, plan, np) for split in ('train', 'validation')}
    write(folder/'assignments.json', allocated)
    for split in ('train', 'validation'):
        rows = {source:[] for source in ('standard', 'targeted')}
        families = []
        accepted_families = []
        for seed in span(block[split+'_seeds']):
            allocation = allocated[split][seed]
            model_id = allocation['model']
            if model_id == block['heldout_model']:
                raise ValueError('Heldout parent supplied collection state')
            status(out, state='COLLECTING', block=block['id'], split=split, seed=seed, model=model_id, completed_pairs=len(attempts))
            model = h.registry.restore(model_id, 'cuda')[0].eval()
            env = base.backend().native.historical.make_env(3)
            started = time.time()
            try:
                def target_call():
                    begin = time.time()
                    rows, info = bc.collect_one(env, model, seed, plan, out, deadline)
                    info['elapsed_seconds'] = time.time()-begin
                    return rows, info
                def standard_call():
                    begin = time.time()
                    rows, info = standard_one(env, seed, plan, out, deadline)
                    info['elapsed_seconds'] = time.time()-begin
                    return rows, info
                if allocation['standard_first']:
                    standard, si = standard_call()
                    target, ti = target_call()
                else:
                    target, ti = target_call()
                    standard, si = standard_call()
                ti['expert_calls'] = len(target) if ti['accepted'] else (plan['approach_horizon'] if ti['reason'] == 'expert_approach_timeout' else 0)
            finally:
                env.close()
            pair = dict(seed=seed, split=split, source_model=model_id, standard_first=allocation['standard_first'], targeted=ti, standard=si, elapsed_seconds=time.time()-started,
                accepted=bool(ti['accepted'] and si['accepted']))
            allowed_rejections = {'second_approach_not_reached', 'prefix_retreat_timeout', 'expert_approach_timeout', 'expert_prefix_timeout'}
            if any(not info['accepted'] and info.get('reason') not in allowed_rejections for info in (ti,si)):
                raise ValueError('Unregistered data rejection reason')
            if pair['accepted']:
                if ti['initial_sha256'] != si['initial_sha256']:
                    raise ValueError('Collection initial states differ')
                check_rows(target, np)
                check_rows(standard, np)
                a, b = matched_indices(len(standard), len(target), plan['maximum_labels_per_pair'])
                pair.update(used_labels_per_source=len(a), standard_indices=a, targeted_indices=b)
                for source, raw, indices in (('standard', standard, a), ('targeted', target, b)):
                    rows[source].extend(raw[i] for i in indices)
                    rawdir = folder/'raw_phases'
                    rawdir.mkdir(exist_ok=True)
                    np.savez_compressed(rawdir/f'{split}_{seed}_{source}.npz', x=np.asarray([r[0] for r in raw]), a=np.asarray([r[1] for r in raw]), y=np.asarray([r[2] for r in raw]))
                families.extend([seed]*len(a))
                accepted_families.append(seed)
            attempts.append(pair)
            write(folder/'collection_attempts.json', attempts)
        if len(accepted_families) < plan['minimum_'+split+'_families']:
            raise ValueError('Insufficient paired '+split+' coverage; no replacement collection')
        coverage = {model:dict(attempts=sum(p['split'] == split and p['source_model'] == model for p in attempts),
                              accepted=sum(p['split'] == split and p['source_model'] == model and p['accepted'] for p in attempts)) for model in block['collector_models']}
        write(folder/f'{split}_coverage.json', coverage)
        if any(v['accepted']/v['attempts'] < plan['analysis']['minimum_coverage_fraction_each_collector'] for v in coverage.values()):
            raise ValueError('Insufficient coverage of a prespecified collector; no replacement collection')
        for source in rows:
            values = rows[source]
            np.savez_compressed(folder/f'{source}_{split}.npz', x=np.asarray([r[0] for r in values], dtype=np.float32),
                a=np.asarray([r[1] for r in values], dtype=np.float32), y=np.asarray([r[2] for r in values], dtype=np.float32), family=np.asarray(families, dtype=np.int64))
        manifest[split] = dict(families=accepted_families, labels_per_source=len(families), positive_labels_per_source=len(accepted_families), collector_coverage=coverage)
    if set(manifest['train']['families']) & set(manifest['validation']['families']):
        raise ValueError('Family split leakage')
    manifest.update(attempts=len(attempts), accepted=sum(p['accepted'] for p in attempts),
        collector_heldout_parent=block['heldout_model'], source_controllers=block['collector_models'],
        used_label_budget_equal=True, same_acquisition_cost_claimed=False,
        expert_calls={s:sum(p[s]['expert_calls'] for p in attempts) for s in ('standard', 'targeted')},
        generated_phase_labels={s:sum(p[s].get('frames', 0) for p in attempts if p[s]['accepted']) for s in ('standard', 'targeted')},
        collection_seconds=sum(p['elapsed_seconds'] for p in attempts),
        origin_seconds={s:sum(p[s]['elapsed_seconds'] for p in attempts) for s in ('standard', 'targeted')},
        selected_data_sha256={path.name:base.sha(path) for path in folder.glob('*_train.npz')},
        validation_data_sha256={path.name:base.sha(path) for path in folder.glob('*_validation.npz')})
    write(folder/'dataset_manifest.json', manifest)
    return manifest


def freeze_components(out, plan):
    base, torch, _ = h.libraries()
    frozen = {}
    for block in plan['blocks']:
        for model in plan['models']:
            for source in plan['sources']:
                for kind in ('actor', 'completion'):
                    path = out/('block_'+block['id'])/'training'/source/f"{model}_{'replay' if source == 'replay' else 'correction'}_{kind}/latest.pth"
                    checkpoint = torch.load(path, map_location='cpu', weights_only=False)
                    if checkpoint['update'] != plan['updates'] or checkpoint['next_batch'] != plan['updates']:
                        raise ValueError('Incomplete component before confirmation')
                    if checkpoint['model_id'] != model or checkpoint['kind'] != kind or checkpoint['source'] != ('replay' if source == 'replay' else 'correction') or checkpoint['plan'] != plan:
                        raise ValueError('Wrong parent/component/plan before confirmation')
                    frozen[str(path.relative_to(ROOT))] = base.sha(path)
    write(out/'frozen_components.json', dict(components=frozen, frozen_unix=time.time(), endpoint=plan['updates'], confirmation_opened=False))


def verify_frozen(out):
    base, _, _ = h.libraries()
    for name, digest in read(out/'frozen_components.json')['components'].items():
        if base.sha(ROOT/name) != digest:
            raise ValueError('Component changed after frozen endpoint')


def load_pair(folder, source, np):
    result = {}
    for split in ('train', 'validation'):
        with np.load(folder/f'{source}_{split}.npz') as a:
            result[split] = tuple(a[k].copy() for k in ('x', 'a', 'y'))
    return result


def paired_summary(rows, plan):
    result = {}
    for panel in ('development', 'confirmation'):
        result[panel] = {}
        for block in plan['blocks']:
            block_id = block['id']
            result[panel][block_id] = {}
            for model in plan['models']:
                lookup = {(r['policy'], r['seed']):r for r in rows if r['panel'] == panel and r['block'] == block_id and r['model'] == model}
                arms = {}
                for policy in plan['policies']:
                    selected = [r for (p, _), r in lookup.items() if p == policy]
                    entry = dict(n=len(selected), successes=sum(r['success'] for r in selected))
                    for control in ('baseline', 'replay', 'standard'):
                        pairs = [(r, lookup[control, r['seed']]) for r in selected]
                        entry['versus_'+control] = dict(gains=sum(a['success'] and not b['success'] for a,b in pairs), losses=sum(not a['success'] and b['success'] for a,b in pairs))
                    arms[policy] = entry
                result[panel][block_id][model] = arms
    differences = []
    for block in plan['blocks']:
        per_model = result['confirmation'][block['id']]
        differences.append(sum((p['targeted']['successes']-p['standard']['successes'])/p['standard']['n'] for p in per_model.values())/len(per_model)*100)
    mean = sum(differences)/len(differences)
    result['primary'] = analysis.primary_analysis(rows, plan)
    result['interpretation'] = dict(primary=result['primary']['primary_comparison'], decision=result['primary']['decision'],
        secondary_all_parent_block_gains_percentage_points=differences, secondary_all_parent_mean_gain_percentage_points=mean,
        training_population_inference_claimed=False, independent_confirmation_scenes=len(span(plan['confirmation_seeds'])))
    return result


def artifacts(out, plan, summary):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    lines = ['# Herkunft zusätzlicher BC-Labels: Ergebnis', '', f"Technical only: {plan['technical_only']}. Fester Endpunkt: {plan['updates']} Updates je Komponente.", '',
             '| Datenblock | Parent | B | Replay | Standard | Targeted | Targeted vs Standard Gewinne/Verluste |', '|---|---|---:|---:|---:|---:|---:|']
    fig, axes = plt.subplots(1, len(plan['blocks']), figsize=(5*len(plan['blocks']), 4), squeeze=False)
    for axis, block in zip(axes[0], plan['blocks']):
        values = summary['confirmation'][block['id']]
        for model, p in values.items():
            counts = [f"{p[s]['successes']}/{p[s]['n']}" for s in plan['policies']]
            paired = p['targeted']['versus_standard']
            lines.append('| '+block['id']+' | '+model+' | '+' | '.join(counts)+f" | {paired['gains']}/{paired['losses']} |")
            axis.plot(plan['policies'], [100*p[s]['successes']/p[s]['n'] for s in plan['policies']], marker='o', label=model)
        axis.set(title=block['id'], ylabel='Stable three-cube success (%)', ylim=(0, 100))
        axis.tick_params(axis='x', rotation=20)
        axis.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out/'confirmation_success.png', dpi=150)
    plt.close(fig)
    lines += ['', json.dumps(summary['interpretation'], ensure_ascii=False), '', 'Gemeinsame Szenen und Parent-Seeds; keine neun unabhängigen Modellinitialisierungen. Entwicklung separat in summary.json. Keine Hardware-/OOD-/Curriculum-/Critic-Aussage.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
    fig, axes = plt.subplots(1, 2, figsize=(11, 4))
    for kind, ax in zip(('actor', 'completion'), axes):
        for source in plan['sources']:
            curves = [read(path) for path in out.glob(f'block_*/training/{source}/*_*/loss.json') if path.parent.name.endswith('_'+kind)]
            if curves:
                x = [v['update'] for v in curves[0]]
                ys = [[c[i]['loss'] for c in curves] for i in range(len(x))]
                ax.plot(x, [sum(v)/len(v) for v in ys], label=source)
        ax.set(title=kind+' training loss (mean across components)', xlabel='Additional optimizer updates', ylabel='Recorded minibatch loss')
        ax.legend()
    fig.tight_layout()
    fig.savefig(out/'training_loss.png', dpi=150)
    plt.close(fig)


def worker(out, deadline):
    base, torch, np = h.libraries()
    base.configure(1)
    plan = read(out/'plan.json')
    started = time.time()
    try:
        verify(out)
        for block in plan['blocks']:
            collect_block(out, out/('block_'+block['id']), block, plan, deadline)
        olddata = base.load_data()['train']
        mask = olddata[2] == 0
        old = olddata[0][mask], olddata[1][mask], olddata[3][mask]
        total = len(plan['blocks'])*len(plan['models'])*len(plan['sources'])*2
        completed = 0
        for bi, block in enumerate(plan['blocks']):
            folder = out/('block_'+block['id'])
            for source in plan['sources']:
                component = folder/'training'/source
                component.mkdir(parents=True)
                write(component/'plan.json', plan)
                # Replay has no new source; use standard validation for diagnostics only.
                dataset_source = 'standard' if source == 'replay' else source
                for split in ('train', 'validation'):
                    (component/f'corrections_{split}.npz').write_bytes((folder/f'{dataset_source}_{split}.npz').read_bytes())
            for mi, model_id in enumerate(plan['models']):
                rng = np.random.default_rng(171100+100*bi+mi)
                with np.load(folder/'standard_train.npz') as a, np.load(folder/'targeted_train.npz') as b:
                    if not np.array_equal(a['family'], b['family']) or not np.array_equal(a['y'], b['y']):
                        raise ValueError('Mismatched families/terminal-label budgets')
                    families = a['family'].copy()
                old_ids = rng.integers(len(old[0]), size=(plan['updates'], 64), dtype=np.int32)
                new_ids = family_uniform_indices(families, (plan['updates'], 32), rng, np)
                for source in plan['sources']:
                    component = folder/'training'/source
                    np.savez_compressed(component/f'schedule_{model_id}.npz', old=old_ids, new=new_ids)
                    data = load_pair(folder, 'standard' if source == 'replay' else source, np)
                    for kind in ('actor', 'completion'):
                        status(out, state='TRAINING', block=block['id'], model=model_id, source=source, kind=kind,
                               component_output=str(component.relative_to(out)), components_completed=completed, components_total=total)
                        bc.fit_branch(component, plan, model_id, kind, 'replay' if source == 'replay' else 'correction', data, old, deadline)
                        completed += 1
        # No new confirmation scene is opened before all components reach the fixed endpoint.
        verify(out)
        freeze_components(out, plan)
        status(out, state='FROZEN_FOR_EVALUATION', components_completed=completed, components_total=total)
        rows, baselines, initial, scene_identity = [], {}, {}, {}
        historical = {(r['model'], r['seed']):r for r in read(ROOT/'praxis/results/curriculum/phase_skill_audit_v1/run_001/full_rollouts.json')}
        compositions = {}
        tasks = [(block, block['heldout_model']) for block in plan['blocks']]
        tasks += [(block, model) for block in plan['blocks'] for model in plan['models'] if model != block['heldout_model']]
        for task_index, (block, model_id) in enumerate(tasks):
            folder = out/('block_'+block['id'])
            reference = h.registry.restore(model_id, 'cuda')[0].eval()
            policies = dict(baseline=reference)
            for source in plan['sources']:
                paths = [folder/'training'/source/f"{model_id}_{'replay' if source == 'replay' else 'correction'}_{kind}/latest.pth" for kind in ('actor', 'completion')]
                actor, completion = [bc.restore_branch(path)[0].eval() for path in paths]
                policies[source] = bc.compose(reference, actor, completion)
                compositions[block['id']+'/'+model_id+'/'+source] = dict(reference=model_id, actor=str(paths[0].relative_to(ROOT)), completion=str(paths[1].relative_to(ROOT)),
                    gate='placement 2, phase 0, outside retreat; evaluate_episode sets context')
            write(out/'composition.json', compositions)
            env = base.backend().native.historical.make_env(3)
            try:
                for panel in ('development', 'confirmation'):
                    if panel == 'confirmation' and not (out/'confirmation_opened.json').exists():
                        verify_frozen(out)
                        write(out/'confirmation_opened.json', dict(opened_unix=time.time(), technical_only=plan['technical_only'],
                            frozen_components_manifest_sha256=base.sha(out/'frozen_components.json')))
                    for offset, seed in enumerate(span(plan[panel+'_seeds'])):
                        rotation = (offset+task_index) % len(plan['policies'])
                        order = plan['policies'][rotation:]+plan['policies'][:rotation]
                        for policy_name in order:
                            model = policies[policy_name]
                            base.check_stop(out, deadline)
                            key = model_id, panel, seed
                            status(out, state='EVALUATING', block=block['id'], model=model_id, panel=panel, policy=policy_name, seed=seed, completed_evaluations=len(rows),
                                primary_complete=(out/'primary_result.json').exists())
                            cached = policy_name == 'baseline' and key in baselines
                            if cached:
                                row = copy.deepcopy(baselines[key])
                            else:
                                row = bc.evaluate_episode(env, model, seed, out, deadline, plan)
                                if policy_name == 'baseline':
                                    if panel == 'development':
                                        expected = historical[model_id, seed]
                                        if any(row[k] != expected[k] for k in ('success', 'frames', 'initial_sha256', 'final_stage', 'final_phase', 'retreat_timeout')):
                                            raise ValueError('Baseline regression against archived evaluator')
                                    baselines[key] = copy.deepcopy(row)
                            scene = panel, seed
                            state_key = panel, row['initial_sha256']
                            if state_key in scene_identity and scene_identity[state_key] != seed:
                                raise ValueError('Different scenario IDs produced identical initial states')
                            scene_identity[state_key] = seed
                            if scene in initial and initial[scene] != row['initial_sha256']:
                                raise ValueError('Evaluation initial-state mismatch')
                            initial[scene] = row['initial_sha256']
                            row.update(block=block['id'], model=model_id, panel=panel, policy=policy_name, baseline_reused=cached, evaluated_unix=time.time())
                            rows.append(row)
                            with (out/'rollouts.jsonl').open('a', encoding='utf-8') as stream:
                                stream.write(json.dumps(row)+'\n')
            finally:
                env.close()
            if not (out/'primary_result.json').exists():
                primary = analysis.primary_analysis(rows, plan)
                if primary['complete']:
                    verify_frozen(out)
                    write(out/'primary_result.json', primary)
                    write(out/'primary_completed.json', dict(completed_unix=time.time(), result_sha256=base.sha(out/'primary_result.json')))
                    (out/'PRIMARY_REPORT.md').write_text('# Prespecified primary comparison\n\n'+json.dumps(primary, indent=2)+'\n', encoding='utf-8')
        write(out/'composition.json', compositions)
        summary = paired_summary(rows, plan)
        if summary['primary'] != read(out/'primary_result.json'):
            raise ValueError('Primary result changed during secondary evaluation')
        write(out/'summary.json', summary)
        artifacts(out, plan, summary)
        verify(out)
        verify_frozen(out)
        status(out, state='COMPLETE', technical_only=plan['technical_only'], components_completed=completed,
            components_total=total, primary_complete=True, secondary_complete=True, evaluated_rows=len(rows), actual_simulation_episodes=sum(not r['baseline_reused'] for r in rows), elapsed_seconds=time.time()-started)
    except BaseException as exc:
        status(out, state='PARTIAL_TIME_CAP' if isinstance(exc, TimeoutError) else ('STOPPED' if isinstance(exc, InterruptedError) else 'FAILED'),
            error=repr(exc), traceback=traceback.format_exc(), technical_only=plan['technical_only'], primary_complete=(out/'primary_result.json').exists(), secondary_complete=False)
        raise


def run(out):
    if read(out/'status.json')['state'] != 'READY':
        raise ValueError('Require READY; no automatic restart')
    verify(out)
    plan = read(out/'plan.json')
    start = time.time()
    deadline = deadline_for(plan, start)
    if deadline <= start:
        raise ValueError('No remaining time before fixed deadline')
    with (out/'launch.json').open('x', encoding='utf-8') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=start), stream)
    watchdog = h.module('matched_budget_watchdog', HERE.parent/'grasp_phase_ablation_v1/pipeline.py')
    proc, awake = None, False
    import psutil
    state = dict(state='STARTING', pid=os.getpid(), process_created=psutil.Process().create_time(), started_unix=start, deadline=deadline,
                 absolute_deadline=plan['absolute_deadline'])
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000001))
        with (out/'worker.log').open('x', encoding='utf-8') as log:
            proc = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), 'worker', '--output', str(out), '--deadline', str(deadline)], cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
            state.update(state='RUNNING', worker_pid=proc.pid, worker_created=psutil.Process(proc.pid).create_time(), sleep_prevention_active=awake)
            while proc.poll() is None:
                state['heartbeat_unix'] = time.time()
                write(out/'supervisor_status.json', state)
                if time.time() >= deadline+5:
                    watchdog.stop_worker(proc)
                    status(out, state='PARTIAL_TIME_CAP', error='Supervisor enforced fixed deadline')
                    break
                if (out/'STOP').exists():
                    for component in out.glob('block_*/training/*'):
                        (component/'STOP').touch()
                    try:
                        proc.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        watchdog.stop_worker(proc)
                    status(out, state='STOPPED', error='Explicit STOP request')
                    break
                time.sleep(2)
            terminal = read(out/'status.json')
            if terminal['state'] not in ('COMPLETE', 'FAILED', 'STOPPED', 'PARTIAL_TIME_CAP'):
                status(out, state='FAILED', error='Worker exited without terminal status', returncode=proc.returncode)
            state.update(state=read(out/'status.json')['state'], worker_returncode=proc.returncode)
    except BaseException as exc:
        state.update(state='FAILED', error=repr(exc))
        raise
    finally:
        if proc is not None and proc.poll() is None:
            watchdog.stop_worker(proc)
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(), sleep_prevention_active=False)
        write(out/'supervisor_status.json', state)
    print(json.dumps(dict(state=state['state'], output=str(out))))
    if state['state'] != 'COMPLETE':
        raise SystemExit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('prepare', 'run', 'worker', 'verify'))
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--smoke', action='store_true')
    parser.add_argument('--deadline', type=float)
    args = parser.parse_args()
    output = args.output.resolve()
    if not output.is_relative_to(ROOT):
        parser.error('Output must be inside workspace')
    if args.command == 'prepare':
        prepare(output, args.smoke)
    elif args.command == 'run':
        run(output)
    elif args.command == 'worker':
        worker(output, args.deadline)
    else:
        verify(output)
        print('Frozen inputs verified')
