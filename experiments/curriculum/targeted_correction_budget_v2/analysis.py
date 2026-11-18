"""Prespecified paired analysis, conditional on the frozen parents/data blocks."""


def primary_analysis(rows, plan):
    import numpy as np
    scenes = list(range(plan['confirmation_seeds'][0], plan['confirmation_seeds'][1]+1))
    lookup = {}
    for row in rows:
        key = row['panel'], row['block'], row['model'], row['policy'], row['seed']
        if key in lookup:
            raise ValueError('Duplicate evaluation cell')
        lookup[key] = row
    expected = [(block, scene, policy) for block in plan['blocks'] for scene in scenes for policy in plan['policies']]
    missing = [(block['id'], scene, policy) for block, scene, policy in expected
               if ('confirmation', block['id'], block['heldout_model'], policy, scene) not in lookup]
    if missing:
        return dict(complete=False, missing_cells=len(missing), decision='INCOMPLETE_NO_PRIMARY_CLAIM')
    deltas = {control:[] for control in ('standard', 'replay', 'baseline')}
    per_block = []
    for block in plan['blocks']:
        model = block['heldout_model']
        local = {control:[] for control in deltas}
        counts = {}
        for scene in scenes:
            outcomes = {policy:lookup['confirmation', block['id'], model, policy, scene] for policy in plan['policies']}
            if len({r['initial_sha256'] for r in outcomes.values()}) != 1:
                raise ValueError('Unpaired primary initial states')
            for control in deltas:
                local[control].append(int(outcomes['targeted']['success'])-int(outcomes[control]['success']))
        for policy in plan['policies']:
            cases = [lookup['confirmation', block['id'], model, policy, scene] for scene in scenes]
            reached = [r for r in cases if r.get('second_lift') is not None]
            counts[policy] = dict(n=len(cases), successes=sum(r['success'] for r in cases),
                reached_second_lift=len(reached), grasped_at_second_lift=sum(bool(r['second_lift']['held']) for r in reached))
        for control in deltas:
            deltas[control].append(local[control])
        per_block.append(dict(block=block['id'], collector_heldout_parent=model, outcomes=counts,
            gains_percentage_points={c:100*float(np.mean(v)) for c,v in local.items()},
            paired_vs_standard=dict(gains=sum(v == 1 for v in local['standard']), losses=sum(v == -1 for v in local['standard']))))
    # Each bootstrap item is one scene with ALL block/parent contrasts intact.
    scene_differences = np.asarray(deltas['standard'], dtype=np.float64).mean(axis=0)
    rng = np.random.default_rng(plan['analysis']['bootstrap_seed'])
    indices = rng.integers(len(scenes), size=(plan['analysis']['bootstrap_resamples'], len(scenes)))
    boot = scene_differences[indices].mean(axis=1)*100
    alpha = (1-plan['analysis']['confidence_level'])/2
    low, high = np.quantile(boot, [alpha, 1-alpha]).tolist()
    means = {control:100*float(np.asarray(values, dtype=np.float64).mean()) for control, values in deltas.items()}
    gates = dict(practical_gain=means['standard'] >= plan['practical_gain_percentage_points'],
        scene_interval_excludes_zero=low > 0,
        every_heldout_block_positive=all(b['gains_percentage_points']['standard'] > 0 for b in per_block),
        no_mean_regression_vs_replay=means['replay'] >= 0,
        no_mean_regression_vs_original_B=means['baseline'] >= 0)
    decision = 'SUPPORTED_WITHIN_PRESPECIFIED_SCOPE' if all(gates.values()) else ('NEGATIVE_EFFECT_WITHIN_SCOPE' if high < 0 else 'NOT_DEMONSTRATED')
    if plan.get('technical_only'):
        decision = 'TECHNICAL_ONLY_NO_SCIENTIFIC_CLAIM'
    return dict(complete=True, primary_comparison='learner-prefix vs expert-prefix; collector-heldout parents only',
        unique_confirmation_scene_families=len(scenes), collector_heldout_pairs=len(plan['blocks']), per_block=per_block,
        mean_gains_percentage_points=means, paired_scene_bootstrap=dict(confidence_level=plan['analysis']['confidence_level'],
            interval_percentage_points=[low, high], resamples=plan['analysis']['bootstrap_resamples'], seed=plan['analysis']['bootstrap_seed'],
            sampling_unit='whole scene; all heldout block/parent outcomes kept together',
            scope='conditional on these frozen parent/data pairs; excludes training/data-population uncertainty'),
        gates=gates, decision=decision, secondary_comparisons_confirmatory=False,
        null_is_equivalence=False, general_robustness_or_novelty_claimed=False)
