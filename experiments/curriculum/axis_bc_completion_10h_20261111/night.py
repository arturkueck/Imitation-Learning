"""Paired completion intervention, trace diagnosis, and fixed-completion BC."""
from pathlib import Path
import argparse
import copy
import ctypes
import hashlib
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import time
import traceback

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXT = HERE.with_name('axis_bc_extension_20261110')
spec = importlib.util.spec_from_file_location('bc_continuation_runtime', EXT/'night.py')
runtime = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runtime)
read, write = runtime.read, runtime.write
original_restore, original_save = runtime.restore, runtime.save_member


def fixed_restore(checkpoint, cfg, device):
    from policy import FixedCompletion
    actor, optimizer = original_restore(checkpoint, cfg, device)
    reference = copy.deepcopy(actor)
    if 'completion_reference' in checkpoint:
        reference.load_state_dict(checkpoint['completion_reference'])
    return FixedCompletion(actor, reference), optimizer


def fixed_save(out, member, plan, cfg, technical):
    _, torch, _ = runtime.libraries()
    model = member['model']
    checkpoint = dict(model=model.actor.state_dict(), completion_reference=model.reference.state_dict(),
        optimizer=member['optimizer'].state_dict(), update=member['update'], config=cfg,
        extension_plan=plan, technical_only=technical, completion_frozen=True,
        seed=member['seed'], arm=member['arm'], parent=member['parent'],
        sampler_sha256=member['sampler_sha256'], next_batch=member['update']-plan['start_update'],
        torch_rng=torch.get_rng_state(), cuda_rng=torch.cuda.get_rng_state_all() if torch.cuda.is_available() else [])
    path = out/member['name']/'latest.pth'
    tmp = path.with_suffix('.tmp')
    torch.save(checkpoint, tmp)
    tmp.replace(path)


def prior_analysis(source):
    records = {}
    for arm in ('mixed', 'curriculum'):
        for seed in (1, 2, 3):
            name = f'{arm}_seed{seed}'
            records[name] = {}
            for update in (30000, 40000, 50000, 60000):
                metric = read(source/name/f'offline_u{update}.json')
                phases = metric['completion']['phases'].values()
                records[name][update] = dict(action_mse=metric['action_mse'],
                    completion_bce=metric['completion']['weighted_bce'],
                    total_loss=metric['total_validation_loss'],
                    tp=sum(p['tp'] for p in phases), fp=sum(p['fp'] for p in phases), fn=sum(p['fn'] for p in phases))
    return dict(models=records, conclusion='All six models have lower validation action MSE and completion BCE at 60k than 30k. This does not establish better online phase timing. Functional swap and frozen-training comparisons remain hypotheses.')


def validate(plan, cfg, source_plan):
    runtime.validate(plan, cfg)
    if not 0 < plan['shutdown_reserve_seconds'] < plan['wall_clock_cap_seconds'] <= 36000:
        raise ValueError('Shutdown reserve must stay inside the maximum ten-hour budget')
    if (plan['start_update'], plan['additional_updates'], plan['sampler_seed_offset']) != (
            source_plan['start_update'], source_plan['additional_updates'], source_plan['sampler_seed_offset']):
        raise ValueError('Frozen continuation must exactly match existing control budget and sampling')
    fresh = set(range(plan['confirmation_seeds'][0], plan['confirmation_seeds'][1]+1))
    used = set(range(source_plan['confirmation_seeds'][0], source_plan['confirmation_seeds'][1]+1))
    if fresh & used:
        raise ValueError('Confirmation overlaps previous night')


def prepare(out):
    base, torch, np = runtime.libraries()
    if out.exists():
        raise FileExistsError('Use a new directory')
    plan = read(HERE/'config.json')
    source = ROOT/plan['source']
    runtime.verify(source)
    if read(source/'status.json')['state'] != 'COMPLETE':
        raise ValueError('Previous run and confirmation must be complete')
    cfg = read(source/'base_config.json')
    validate(plan, cfg, read(source/'plan.json'))
    parents = read(source/'parents.json')
    prior_proof = read(source/'provenance.json')
    inputs = dict(prior_proof['input_hashes'])
    controls = {}
    frozen = read(source/'confirmation/frozen.json')
    training_data = base.load_data()['train']
    checked_seeds = set()
    for name, parent in parents.items():
        path = source/name/'latest.pth'
        digest = base.sha(path)
        if frozen[name+'_extended']['sha256'] != digest:
            raise ValueError('Control is no longer the frozen 60k model')
        ck = torch.load(path, map_location='cpu', weights_only=False)
        if ck['update'] != 60000 or ck['technical_only']:
            raise ValueError('Invalid control')
        controls[name] = dict(path=str(path.relative_to(ROOT)), sha256=digest)
        inputs[str(path.relative_to(ROOT))] = digest
        # Prove the regenerated plan is the SAME plan used by the existing control.
        with np.load(source/f'schedule_seed{parent["seed"]}.npz', allow_pickle=False) as archive:
            saved = archive['batches']
        if hashlib.sha256(saved.tobytes()).hexdigest() != ck['sampler_sha256']:
            raise ValueError('Historical batch plan does not match checkpoint')
        if parent['seed'] not in checked_seeds:
            generated = runtime.common_batches(training_data, plan['additional_updates'], cfg['batch_size'],
                                                parent['seed']+plan['sampler_seed_offset'])
            if not np.array_equal(saved, generated):
                raise ValueError('Reused control has different training batches')
            checked_seeds.add(parent['seed'])
        inputs[str((source/f'schedule_seed{parent["seed"]}.npz').relative_to(ROOT))] = base.sha(source/f'schedule_seed{parent["seed"]}.npz')
        for update in (30000, 40000, 50000, 60000):
            file = source/name/f'offline_u{update}.json'
            inputs[str(file.relative_to(ROOT))] = base.sha(file)
        for generation in ('parent', 'extended'):
            file = source/'confirmation'/f'{name}_{generation}_count3.json'
            inputs[str(file.relative_to(ROOT))] = base.sha(file)
    sources = list(HERE.glob('*.py'))+list(HERE.glob('*.ps1'))+[HERE/'config.json']
    inputs.update({str(p.relative_to(ROOT)): base.sha(p) for p in sources})
    out.mkdir(parents=True)
    for name, value in (('plan.json', plan), ('base_config.json', cfg), ('parents.json', parents), ('controls.json', controls)):
        write(out/name, value)
        inputs[str((out/name).relative_to(ROOT))] = base.sha(out/name)
    write(out/'prior_diagnosis.json', prior_analysis(source))
    for path in sources:
        target = out/'source_snapshot'/path.name
        target.parent.mkdir(exist_ok=True)
        shutil.copy2(path, target)
    write(out/'provenance.json', dict(input_hashes=inputs,
          library_source_hashes=prior_proof['library_source_hashes'], versions=prior_proof['versions'], prepared_unix=time.time()))
    write(out/'status.json', dict(state='READY', completed_round=30000, updated_unix=time.time(), training_started=False))
    print(json.dumps(dict(state='READY', parents=len(parents), reused_controls=len(controls), output=str(out))))


def load_model(path, cfg, device):
    _, torch, _ = runtime.libraries()
    checkpoint = torch.load(path, map_location='cpu', weights_only=False)
    model, _ = original_restore(checkpoint, cfg, device)
    return model


def diagnose(out, device, deadline, technical=False):
    from policy import FixedCompletion
    from replay import replay_selected
    base, _, _ = runtime.libraries()
    runtime.verify(out)
    plan, cfg = read(out/'plan.json'), read(out/'base_config.json')
    parents, controls = read(out/'parents.json'), read(out/'controls.json')
    if technical:
        parents = {next(iter(parents)): next(iter(parents.values()))}
    folder = out/('technical_diagnosis' if technical else 'diagnosis')
    folder.mkdir(exist_ok=False)
    hashes, results = {}, {}
    started = time.time()
    base.configure(1)
    for name, parent in parents.items():
        before = load_model(ROOT/parent['path'], cfg, device)
        after = load_model(ROOT/controls[name]['path'], cfg, device)
        for action_tag, actor in (('30k', before), ('60k', after)):
            for completion_tag, reference in (('30k', before), ('60k', after)):
                tag = f'{name}_a{action_tag}_c{completion_tag}'
                write(out/'diagnostic_status.json', dict(state='DIAGNOSING', pid=os.getpid(), started_unix=started,
                    evaluating=tag, updated_unix=time.time(), deadline=deadline))
                model = FixedCompletion(actor, reference)
                seeds = [plan['technical_seeds'][0]] if technical else range(cfg['development_seeds'][0], cfg['development_seeds'][1]+1)
                result = base.evaluate(model, cfg, 3, seeds, out, deadline, frame_cap=20 if technical else None)
                runtime.check_pairing(hashes, 3, result)
                write(folder/(tag+'.json'), result)
                results[tag] = {k: v for k, v in result.items() if k != 'rows'}
    write(folder/'crossover_summary.json', results)
    if not technical:
        replay_selected(out, cfg, plan, parents, controls, device, deadline)
    write(out/'diagnostic_status.json', dict(state='DIAGNOSIS_COMPLETE', updated_unix=time.time()))


def train_fixed(out, device, deadline=None, prepared=None):
    runtime.restore, runtime.save_member = fixed_restore, fixed_save
    try:
        runtime.run(out, device, deadline=deadline, prepared=prepared)
    finally:
        runtime.restore, runtime.save_member = original_restore, original_save


def confirmation(out, device, deadline):
    base, torch, _ = runtime.libraries()
    runtime.verify(out)
    if read(out/'status.json')['state'] != 'TRAINING_COMPLETE':
        raise ValueError('All frozen-completion models must finish first')
    plan, cfg = read(out/'plan.json'), read(out/'base_config.json')
    controls = read(out/'controls.json')
    folder = out/'confirmation'
    folder.mkdir(exist_ok=False)
    frozen = {}
    for name, control in controls.items():
        for condition, source in (('control', ROOT/control['path']), ('fixed', out/name/'latest.pth')):
            ck = torch.load(source, map_location='cpu', weights_only=False)
            if ck['update'] != 60000 or ck['technical_only']:
                raise ValueError('Incomplete or technical confirmation model')
            target = folder/f'{name}_{condition}.pth'
            shutil.copy2(source, target)
            frozen[f'{name}_{condition}'] = dict(path=str(target), sha256=base.sha(target), condition=condition)
    write(folder/'frozen.json', frozen)
    hashes, results = {}, {}
    seeds = range(plan['confirmation_seeds'][0], plan['confirmation_seeds'][1]+1)
    started = time.time()
    base.configure(1)
    for name, entry in frozen.items():
        if base.sha(entry['path']) != entry['sha256']:
            raise ValueError('Frozen model changed')
        ck = torch.load(entry['path'], map_location='cpu', weights_only=False)
        model, _ = fixed_restore(ck, cfg, device) if entry['condition'] == 'fixed' else original_restore(ck, cfg, device)
        results[name] = {}
        for count in (2, 3):
            write(out/'status.json', dict(state='FINAL_TEST', pid=os.getpid(), started_unix=started,
                completed_round=60000, evaluating=name, count=count, deadline=deadline, updated_unix=time.time()))
            result = base.evaluate(model, cfg, count, seeds, out, deadline)
            runtime.check_pairing(hashes, count, result)
            write(folder/f'{name}_count{count}.json', result)
            results[name][str(count)] = result
    write(folder/'results.json', results)
    summary = {name: {k: dict(successes=r['successes'], n=r['n']) for k, r in counts.items()}
               for name, counts in results.items()}
    paired = {}
    for name in controls:
        paired[name] = {}
        for count in ('2', '3'):
            control = results[name+'_control'][count]['rows']
            fixed = results[name+'_fixed'][count]['rows']
            paired[name][count] = dict(gains=sum(not a['success'] and b['success'] for a, b in zip(control, fixed)),
                                      losses=sum(a['success'] and not b['success'] for a, b in zip(control, fixed)))
    write(out/'result_summary.json', dict(models=summary, paired_fixed_vs_control=paired,
          interpretation='Frozen completion training and inference intervention; does not isolate completion from shared-representation gradient effects. Report each training seed.'))
    write(out/'status.json', dict(state='COMPLETE', completed_round=60000, updated_unix=time.time()))


def supervise(out, device):
    started = time.time()
    runtime.verify(out)
    if read(out/'status.json')['state'] != 'READY' or (out/'STOP').exists():
        raise ValueError('Expected fresh READY run without STOP')
    with (out/'supervisor_launch.json').open('x') as stream:
        json.dump(dict(pid=os.getpid(), started_unix=time.time()), stream)
    plan = read(out/'plan.json')
    hard_deadline = started+plan['wall_clock_cap_seconds']
    deadline = hard_deadline-plan['shutdown_reserve_seconds']
    state = dict(state='STARTING', pid=os.getpid(), started_unix=started, deadline=deadline, hard_deadline=hard_deadline)
    worker, awake = None, False
    try:
        if os.name == 'nt':
            awake = bool(ctypes.windll.kernel32.SetThreadExecutionState(0x80000003))
        for command in ('diagnose', 'run', 'test'):
            if command == 'test' and read(out/'status.json')['state'] != 'TRAINING_COMPLETE':
                state['state'] = 'INCOMPLETE'
                return
            if (out/'STOP').exists() or time.time() >= deadline:
                state['state'] = 'STOPPED_OR_TIME_CAP'
                return
            worker = subprocess.Popen([sys.executable, '-u', str(Path(__file__).resolve()), command,
                '--output', str(out), '--device', device, '--deadline', str(deadline)], cwd=ROOT)
            state.update(state=command.upper(), worker_pid=worker.pid, sleep_prevention_active=awake, updated_unix=time.time())
            write(out/'supervisor_status.json', state)
            try:
                code = worker.wait(timeout=max(.001, hard_deadline-time.time()))
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()
                raise TimeoutError('Hard total time cap exhausted; shutdown reserve was inside the budget')
            if code:
                raise RuntimeError(command+' failed with exit code '+str(code))
            if command == 'diagnose' and read(out/'diagnostic_status.json')['state'] != 'DIAGNOSIS_COMPLETE':
                state['state'] = 'INCOMPLETE'
                return
        state['state'] = read(out/'status.json')['state']
    except BaseException as exc:
        state.update(state='FAILED', reason=repr(exc), traceback=traceback.format_exc())
        raise
    finally:
        if worker is not None and worker.poll() is None:
            worker.kill()
            worker.wait()
        if awake:
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
        state.update(updated_unix=time.time(), sleep_prevention_active=False)
        write(out/'supervisor_status.json', state)


def status(out):
    # Reuse the incremental monitor and its process-identity checks. During the
    # initial diagnosis, display that phase from a separate monitor directory.
    if (out/'supervisor_status.json').exists() and read(out/'supervisor_status.json')['state'] == 'DIAGNOSE' and (out/'diagnostic_status.json').exists():
        monitor = out/'diagnostic_monitor'
        monitor.mkdir(exist_ok=True)
        state = read(out/'diagnostic_status.json')
        state['state'] = 'EVALUATING' if state['state'] == 'DIAGNOSING' else state['state']
        state['completed_round'] = 30000
        write(monitor/'status.json', state)
        shutil.copy2(out/'supervisor_status.json', monitor/'supervisor_status.json')
        runtime.status(monitor)
    else:
        runtime.status(out)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('command', choices=('prepare', 'preflight', 'diagnose', 'smoke', 'run', 'test', 'supervise', 'status'))
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prepared', type=Path)
    p.add_argument('--device', choices=('cpu', 'cuda'), default='cuda')
    p.add_argument('--deadline', type=float)
    p.add_argument('--technical', action='store_true')
    args = p.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT):
        p.error('Output must stay inside workspace')
    try:
        if args.command == 'prepare':
            prepare(out)
        elif args.command == 'preflight':
            runtime.verify(out)
            if read(out/'status.json')['state'] != 'READY' or any((out/x).exists() for x in ('STOP', 'launch.json', 'supervisor_launch.json')):
                raise ValueError('Not startable; no restart allowed')
            print(json.dumps(dict(state='READY', input_hashes_verified=True)))
        elif args.command == 'diagnose':
            diagnose(out, args.device, args.deadline or time.time()+600, args.technical)
        elif args.command == 'smoke':
            if args.prepared is None:
                p.error('--prepared required')
            train_fixed(out, args.device, prepared=args.prepared.resolve())
        elif args.command == 'run':
            train_fixed(out, args.device, deadline=args.deadline)
        elif args.command == 'test':
            if args.deadline is None:
                p.error('Use supervise for a shared deadline')
            confirmation(out, args.device, args.deadline)
        elif args.command == 'supervise':
            supervise(out, args.device)
        else:
            status(out)
    except (TimeoutError, InterruptedError) as exc:
        target = out/('diagnostic_status.json' if args.command == 'diagnose' else 'status.json')
        state = read(target) if target.exists() else {}
        state.update(state='PARTIAL_TIME_CAP' if isinstance(exc, TimeoutError) else 'STOPPED', reason=str(exc), updated_unix=time.time())
        write(target, state)


if __name__ == '__main__':
    main()
