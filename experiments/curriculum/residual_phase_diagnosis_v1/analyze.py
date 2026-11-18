"""Describe the completed, selected-case diagnosis without retraining or new rollouts."""
from pathlib import Path
import argparse
import hashlib
import json
import collections
import numpy as np


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def analyze(out):
    state = read(out/'status.json')
    if state['state'] != 'COMPLETE' or state['optimizer_updates'] != 0:
        raise ValueError('Require completed frozen diagnosis')
    groups = read(out/'groups.json')
    plan = read(out/'plan.json')
    columns = {name:i for i,name in enumerate(read(out/'trace_schema.json'))}
    aggregate, contexts = {}, []
    for group in groups:
        case, arms = group['case'],group['arms']
        key = str(case['placement'])+'/'+str(case['phase'])
        bucket = aggregate.setdefault(key,dict(failure_cases=0,success_controls=0,unexposed_cases=0,
            rescued={arm:0 for arm in arms if arm != 'control'},harmed={arm:0 for arm in arms if arm != 'control'},
            local_progress_on_failure_cases={arm:0 for arm in arms}))
        role = 'failure_cases' if case['role'] == 'failure' else 'success_controls'
        bucket[role] += 1
        control = arms['control']
        if control['entry'] is None:
            bucket['unexposed_cases'] += 1
        local_progress = {}
        for arm, row in arms.items():
            with np.load(out/'traces'/f"{case['id']}_{arm}.npz") as archive:
                arm_trace = archive['trace']
            same = arm_trace[:,columns['placement']] == case['placement']
            active = same & (arm_trace[:,columns['phase']] == case['phase']) & (arm_trace[:,columns['retreat']] == 0)
            if case['phase'] < 6:
                progressed = bool(((same & (arm_trace[:,columns['phase']] > case['phase'])) | (arm_trace[:,columns['placement']] > case['placement'])).any())
            elif case['placement'] == 1:
                progressed = bool((arm_trace[active,columns['sequencer_event']] == 1).any())
            else:
                progressed = bool(row['success'])
            if row['success'] and not progressed:
                raise ValueError('Successful task without expected phase progress')
            local_progress[arm] = dict(progressed=progressed,final_stage=row['final_stage'],final_phase=row['final_phase'],success=row['success'])
            if case['role'] == 'failure':
                bucket['local_progress_on_failure_cases'][arm] += int(progressed)
            if arm != 'control':
                bucket['rescued'][arm] += int(not control['success'] and row['success'])
                bucket['harmed'][arm] += int(control['success'] and not row['success'])
        if case['role'] != 'failure':
            continue
        if control['entry'] is None:
            contexts.append(dict(case=case['id'],classification='target_phase_not_executed',**{k:case[k] for k in ('model','seed','placement','phase')}))
            continue
        with np.load(out/'traces'/f"{case['id']}_control.npz") as archive:
            trace = archive['trace']
        at = control['entry']['frame']
        previous = trace[at-1] if at > 0 and int(trace[at-1,columns['placement']]) == case['placement'] else None
        scope = (trace[:,columns['placement']] == case['placement']) & (trace[:,columns['phase']] == case['phase']) & (trace[:,columns['retreat']] == 0)
        rows = trace[scope]
        context = dict(case=case['id'],**{k:case[k] for k in ('model','seed','placement','phase')},entry_frame=at,
            local_progress_by_arm=local_progress,
            remaining_frames_at_entry=plan['episode_horizon']-at,
            control_bc_probability_range=[float(rows[:,columns['bc_completion_probability']].min()),float(rows[:,columns['bc_completion_probability']].max())],
            control_teacher_ready_frames=int((rows[:,columns['teacher_ready']] == 1).sum()),
            control_completion_disagreement_frames=control['completion_disagreement_frames'])
        if previous is not None:
            context.update(held_before_entry=bool(previous[columns['held_post']]),
                xy_error_before_entry_m=float(previous[columns['xy_error_m']]),
                source_height_above_target_before_entry_m=float(previous[columns['height_above_target_m']]),
                pair_contact_before_entry=bool(previous[columns['pair_contact']]))
            velocity = np.asarray([previous[columns[f'cube_velocity_{case["placement"]*6+j}']] for j in range(6)])
            context.update(source_linear_speed_before_entry_m_s=float(np.linalg.norm(velocity[:3])),
                           source_angular_speed_before_entry_rad_s=float(np.linalg.norm(velocity[3:])))
        action = arms['action']['success']
        if case['phase'] == 6:
            context['classification'] = 'action_override_rescues' if action else 'action_override_does_not_rescue'
        else:
            completion,both = arms['completion']['success'],arms['both']['success']
            if both and action and completion:
                kind = 'either_single_override_rescues'
            elif both and action:
                kind = 'action_override_sufficient'
            elif both and completion:
                kind = 'completion_override_sufficient'
            elif both:
                kind = 'joint_override_required_among_tested_arms'
            elif action or completion:
                kind = 'nonmonotonic_intervention_response'
            else:
                kind = 'no_tested_override_rescues'
            context['classification'] = kind
        context['intervention_successes'] = {name:bool(row['success']) for name,row in arms.items()}
        contexts.append(context)
    result = dict(technical_only=plan['technical_only'],optimizer_updates=0,aggregate=aggregate,failure_contexts=contexts,
        classifications=dict(collections.Counter(row['classification'] for row in contexts)),
        inputs_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('plan.json','groups.json','integrity.json','trace_schema.json')},
        analyzer_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        limits=['Selected already-opened diagnostic cases, no fresh success-rate estimate.',
                'Selection by final phase emphasizes trajectories that remain there; earlier causes remain possible.',
                'An oracle override is a diagnostic intervention, not a learned-policy improvement.',
                'Context measurements and BC/oracle discrepancies alone do not prove a cause.'])
    (out/'analysis.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    lines = ['# Bewegung und Abschluss: Diagnoseauswertung','',
        f"Technical only: {plan['technical_only']}; Optimizerupdates: 0. Alle Fälle sind bereits geöffnete Diagnosefälle.",'',
        '| Platzierung/Phase | Fehlerfälle | Durch Aktion gerettet | Durch Abschluss gerettet | Durch beides gerettet | Verluste bei Erfolgskontrollen (Aktion / Abschluss / beides) |',
        '|---|---:|---:|---:|---:|---|']
    for key, bucket in sorted(aggregate.items()):
        rescued,harmed = bucket['rescued'],bucket['harmed']
        a,c,b = [str(rescued[name]) if name in rescued else 'n/a' for name in ('action','completion','both')]
        losses = ' / '.join(str(harmed[name]) if name in harmed else 'n/a' for name in ('action','completion','both'))
        lines.append(f"| {key} | {bucket['failure_cases']} | {a} | {c} | {b} | {losses} |")
    lines += ['', 'Phase 1 = Absenken zum Griff; Phase 4 = Transport; Phase 6 = Freigeben/Halten. Phase 6 hat keinen verwendeten gelernten Abschluss.',
              '', '## Lokaler Phasenfortschritt, getrennt vom Gesamterfolg','',
              '| Platzierung/Phase | Fehlerfälle | Control | Action | Completion | Both |',
              '|---|---:|---:|---:|---:|---:|']
    for key, bucket in sorted(aggregate.items()):
        values = bucket['local_progress_on_failure_cases']
        numbers = [str(values[name]) if name in values else 'n/a' for name in ('control','action','completion','both')]
        lines.append(f"| {key} | {bucket['failure_cases']} | "+' | '.join(numbers)+' |')
    lines += ['', 'Phasen 1/4: eine folgende Phase wird tatsächlich ausgeführt. Phase 6, Platzierung 1: unveränderter physikalischer Übergang zum Rückzug. Phase 6, Platzierung 2: unveränderter vollständiger Aufgabenerfolg. Lokaler Fortschritt allein ist keine gerettete Gesamtaufgabe.',
              '', '## Einzelne ausgewählte Fehlerfälle','',
              '| Fall | Parent | Szene | Platzierung/Phase | Diagnoseklassifikation | Griff vor Eintritt | Restframes |',
              '|---|---|---:|---|---|---|---:|']
    for row in contexts:
        lines.append(f"| {row['case']} | {row['model']} | {row['seed']} | {row['placement']}/{row['phase']} | {row['classification']} | {row.get('held_before_entry','n/a')} | {row.get('remaining_frames_at_entry','n/a')} |")
    lines += ['', '## Grenzen','', 'Die Zahlen zählen gerettete ausgewählte Fehlerfälle und verlorene ausgewählte Erfolgskontrollen. Sie sind keine allgemeine Erfolgsquote. Ein Eingriff kann über veränderte Folgezustände wirken; ein erfolgloser Eingriff schließt frühere oder zusätzliche Ursachen nicht aus. Alle Rohresultate stehen in REPORT.md/groups.json, die Kontextmessungen in analysis.json und den Traces. Es wurde weder trainiert noch das Erfolgskriterium geändert.']
    (out/'ANALYSIS.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(technical_only=plan['technical_only'],aggregate=aggregate,classifications=result['classifications']),indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    analyze(args.output.resolve())
