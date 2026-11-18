"""Fixed paired outcomes, factorial contrasts and actual-input similarity."""
from pathlib import Path
import argparse
import hashlib
import json
import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def paired(groups, first, second):
    eligible = [g for g in groups if first in g['arms'] and second in g['arms']]
    gains = sum(g['arms'][second]['success'] and not g['arms'][first]['success'] for g in eligible)
    losses = sum(g['arms'][first]['success'] and not g['arms'][second]['success'] for g in eligible)
    return dict(n=len(eligible),first=first,second=second,gains=gains,losses=losses,
        difference_percentage_points=100*(gains-losses)/len(eligible) if eligible else None)


def similarity(samples, cfg):
    tolerance = np.asarray([cfg['eef_component_tolerance_m']/.1]*3+
        [cfg['quaternion_component_tolerance']]*4+[cfg['gripper_joint_component_tolerance_m']/.04]*2+
        [cfg['clock_tolerance_steps']/20])
    exact, near, disagree, qualified = 0,0,0,0
    family_pairs, examples = set(),[]
    for i,first in enumerate(samples):
        for second in samples[i+1:]:
            if (first['parent'],first['placement'],first['phase'])!=(second['parent'],second['placement'],second['phase']) or first['seed']==second['seed']:
                continue
            delta = np.abs(np.asarray(first['x'])-np.asarray(second['x']))
            exact += int(not delta.any())
            if not (delta<=tolerance).all():
                continue
            near += 1
            different = first['ready']!=second['ready']
            disagree += int(different)
            if not different or abs(first['xy_m']-second['xy_m'])<cfg['minimum_xy_error_difference_m']:
                continue
            qualified += 1
            family_pairs.add((first['parent'],first['placement'],first['phase'],*sorted([first['seed'],second['seed']])))
            examples.append(dict(first=first,second=second,maximum_tolerance_fraction=float(np.max(delta/tolerance))))
    return dict(sampled_frames=len(samples),exact_cross_family_feature_pairs=exact,near_frame_pairs=near,
        near_frame_pairs_readiness_disagrees=disagree,near_frame_pairs_readiness_disagrees_xy_diff_ge_5mm=qualified,
        distinct_parent_phase_family_pairs=[list(p) for p in sorted(family_pairs)],
        examples=sorted(examples,key=lambda e:e['maximum_tolerance_fraction'])[:10],
        scope='Sampled control frames only; approximate input equality is not exact aliasing or proof of learned feature benefit')


def analyze(out):
    plan = read(out/'plan.json')
    if read(out/'status.json')['state']!='COMPLETE':
        raise ValueError('Require complete run')
    groups = read(out/'groups.json')
    col = {name:i for i,name in enumerate(read(out/'trace_schema.json'))}
    panels, details, samples, panel_groups, families = {},[],[],{},{}
    for group in groups:
        case, arms = group['case'],group['arms']
        panel = 'calibration' if case['panel']=='calibration' else case['stratum']
        panel_groups.setdefault(panel,[]).append(group)
        ctrl = arms['control']
        if case['panel']=='calibration':
            families.setdefault(str(case['seed']),dict(initial_sha256=ctrl['initial_sha256'],features=ctrl['initial_features']))
        for arm,row in arms.items():
            bucket = panels.setdefault(panel,{}).setdefault(arm,dict(n=0,successes=0,gains=0,losses=0,
                by_parent={},actual_intervention_cases=0,action_frames=0,completion_frames=0,guard_blocked_frames=0,
                grasp_reached=0,grasp_exited=0,forced_cases=0,forced_without_readiness=0,release_reached=0))
            delta = dict(n=1,successes=int(row['success']),gains=int(row['success'] and not ctrl['success']),
                losses=int(ctrl['success'] and not row['success']))
            parent = bucket['by_parent'].setdefault(case['model'],dict(n=0,successes=0,gains=0,losses=0))
            for key,value in delta.items():
                bucket[key] += value
                parent[key] += value
            bucket['actual_intervention_cases'] += int(row['first_intervention'] is not None)
            bucket['action_frames'] += row['action_override_frames']
            bucket['completion_frames'] += row['completion_override_frames']
            bucket['guard_blocked_frames'] += row['guard_blocked_frames']
            with np.load(out/'traces'/f"{case['id']}_{arm}.npz") as archive:
                trace = archive['trace']
            grasp = (trace[:,col['placement']]==2)&(trace[:,col['phase']]==1)&(trace[:,col['retreat']]==0)
            release = (trace[:,col['placement']]==2)&(trace[:,col['phase']]==6)&(trace[:,col['retreat']]==0)
            bucket['grasp_reached'] += int(grasp.any())
            bucket['grasp_exited'] += int(bool((trace[grasp,col['phase_after_decision']]==2).any()))
            bucket['release_reached'] += int(release.any())
            forces = [event for event in row['events'] if event['forced']]
            bucket['forced_cases'] += int(bool(forces))
            bucket['forced_without_readiness'] += sum(not event['grasp_ready'] for event in forces)
            context = None
            if release.any():
                phase_trace = trace[release]
                first,last = phase_trace[0],phase_trace[-1]
                context = dict(entry_xy_m=float(first[col['pre_xy_m']]),entry_height_m=float(first[col['pre_height_m']]),
                    entry_ready=bool(first[col['pre_placement_ready']]),last_xy_m=float(last[col['post_xy_m']]),
                    maximum_post_xy_m=float(phase_trace[:,col['post_xy_m']].max()),
                    last_minus_entry_xy_m=float(last[col['post_xy_m']]-first[col['pre_xy_m']]),
                    maximum_strict_tail=int(trace[:,col['valid_tail']].max()))
            details.append(dict(case=case['id'],panel=panel,model=case['model'],seed=case['seed'],arm=arm,
                success=row['success'],gain=bool(delta['gains']),loss=bool(delta['losses']),
                final_stage=row['final_stage'],final_phase=row['final_phase'],first_intervention=row['first_intervention'],
                forced_events=forces,release_context=context))
            if case['panel']=='calibration' and arm=='control':
                for phase in (5,6):
                    indices = np.flatnonzero((trace[:,col['placement']]==2)&(trace[:,col['phase']]==phase)&(trace[:,col['retreat']]==0))
                    if not len(indices):
                        continue
                    indices = indices[np.unique(np.linspace(0,len(indices)-1,min(len(indices),plan['input_similarity']['maximum_samples_per_phase_episode'])).astype(int))]
                    for at in indices:
                        t = trace[at]
                        samples.append(dict(parent=case['model'],seed=case['seed'],placement=2,phase=phase,frame=int(t[col['frame']]),
                            x=[float(t[col[f'feature_{j}']]) for j in range(10)],xy_m=float(t[col['pre_xy_m']]),
                            ready=bool(t[col['pre_placement_ready']])))
    comparisons, interactions = {},{}
    for panel,selected in panel_groups.items():
        comparisons[panel] = [paired(selected,a,b) for a,b in (
            ('control','grasp_timeout'),('control','grasp_ready'),('grasp_timeout','grasp_ready'),
            ('control','release_hold'),('control','release_feedback'),('guarded_bc','guarded_hold'),
            ('guarded_bc','guarded_feedback'),('control','guarded_bc'),('release_hold','guarded_hold'),
            ('release_feedback','guarded_feedback'),('release_hold','release_feedback'),('guarded_hold','guarded_feedback'))
            if any(a in g['arms'] and b in g['arms'] for g in selected)]
        interactions[panel] = {}
        for motion in ('hold','feedback'):
            eligible = [g for g in selected if all(a in g['arms'] for a in ('control','guarded_bc','release_'+motion,'guarded_'+motion))]
            if eligible:
                values = [(int(g['arms']['guarded_'+motion]['success'])-int(g['arms']['guarded_bc']['success']))-
                    (int(g['arms']['release_'+motion]['success'])-int(g['arms']['control']['success'])) for g in eligible]
                interactions[panel][motion] = dict(n=len(values),difference_in_differences_pp=100*sum(values)/len(values))
    result = dict(technical_only=plan['technical_only'],optimizer_updates=0,panels=panels,paired_comparisons=comparisons,
        factorial_interactions=interactions,details=details,initial_families=families,
        input_similarity=similarity(samples,plan['input_similarity']),
        inputs_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('plan.json','groups.json','trace_schema.json','integrity.json')},
        scope='Frozen causal diagnosis; dependent parent/scenes; opened calibration, no independent training or blind-test efficacy estimate')
    (out/'analysis.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    lines = ['# Selektiver Abschluss und Freigabe: Ergebnisse','',
        f"Technical only: {plan['technical_only']}; optimizer updates: 0; episodes: {plan['episodes']}.",
        '', '| Panel | Arm | Paare | Vollstaendige Erfolge | Gewinne | Verluste | Tatsaechlich eingegriffen |',
        '|---|---|---:|---:|---:|---:|---:|']
    for panel,arms in panels.items():
        for arm,b in arms.items():
            lines.append(f"| {panel} | {arm} | {b['n']} | {b['successes']} | {b['gains']} | {b['losses']} | {b['actual_intervention_cases']} |")
    lines += ['', '## Lokaler Fortschritt und Exposition','',
        '| Panel | Arm | Griff erreicht / verlassen | Erzwungene Abschluesse | Davon ohne aktuelle Bereitschaft | Freigabe erreicht |',
        '|---|---|---:|---:|---:|---:|']
    for panel,arms in panels.items():
        for arm,b in arms.items():
            lines.append(f"| {panel} | {arm} | {b['grasp_reached']} / {b['grasp_exited']} | {b['forced_cases']} | {b['forced_without_readiness']} | {b['release_reached']} |")
    lines += ['', '## Gepaarte Kontraste','', '| Panel | Von | Zu | N | Gewinne | Verluste | Differenz [pp] |',
        '|---|---|---|---:|---:|---:|---:|']
    for panel,contrasts in comparisons.items():
        for c in contrasts:
            lines.append(f"| {panel} | {c['first']} | {c['second']} | {c['n']} | {c['gains']} | {c['losses']} | {c['difference_percentage_points']:.2f} |")
    lines += ['', '## Beobachtung und Grenzen','',
        json.dumps(result['input_similarity']|{'examples':'See analysis.json','distinct_parent_phase_family_pairs':len(result['input_similarity']['distinct_parent_phase_family_pairs'])},indent=2),
        '', 'Die Referenz der Feedbackcontroller unterscheidet sich. Objektfeedback hat zusaetzliche Simulatorinformationen; '
        'dies ist keine reine Featureablation eines neu trainierten Modells. Die externe Griffhysterese fuegt einen Zaehler hinzu.',
        '', 'Alle frischen Familien sind geoeffnete Kalibrierung. Bekannte Fehler und Kontrollen werden separat berichtet. '
        'Gleiche Szenen und geerbte Parents sind abhaengig. Keine Konfidenz-/Teststaerkeaussage fuer neues Training.',
        '', '50 strenge Gesamtframes, unveraenderter Horizont; nicht erreichte Phasen im vollen Nenner. '
        'Alle Einzelverlaeufe, Faktorenkontraste und Parameter-/Quellnachweise bleiben erhalten.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    analyze(parser.parse_args().output.resolve())
