"""Cross-tabulate the fixed readiness criterion against complete task outcomes."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import numpy as np


def audit(out):
    def read(name):
        return json.loads((out/name).read_text(encoding='utf-8'))
    if read('status.json')['state']!='COMPLETE':
        raise ValueError('Require complete run')
    cols = {name:i for i,name in enumerate(read('trace_schema.json'))}
    aggregate, rows = {}, []
    groups = read('groups.json')
    for group in groups:
        case = group['case']
        for arm,result in group['arms'].items():
            with np.load(out/'traces'/f"{case['id']}_{arm}.npz") as archive:
                trace = archive['trace']
            for event in result['events']:
                if event['phase']!=5:
                    continue
                key = f"{case['panel']}/{arm}/{event['placement']}"
                counts = aggregate.setdefault(key,dict(exits=0,pre_ready_success=0,pre_ready_failure=0,
                    pre_unready_success=0,pre_unready_failure=0,entry_ready_success=0,entry_ready_failure=0,
                    entry_unready_success=0,entry_unready_failure=0,eef_within_6mm_pre_unready=0))
                counts['exits'] += 1
                outcome = 'success' if result['success'] else 'failure'
                counts[('pre_ready_' if event['pre_placement_ready'] else 'pre_unready_')+outcome] += 1
                counts[('entry_ready_' if event['release_entry_ready'] else 'entry_unready_')+outcome] += 1
                at = int(event['frame'])
                if int(trace[at,cols['frame']])!=at:
                    raise ValueError('Frame indexing changed')
                distance = float(trace[at,cols['oracle_distance_pre_m']])
                counts['eef_within_6mm_pre_unready'] += int(distance<.006 and not event['pre_placement_ready'])
                xy,height,contact,speed,angular,lower = event['pre_placement_features']
                rows.append(dict(case=case['id'],panel=case['panel'],parent=case['model'],seed=case['seed'],arm=arm,
                    placement=event['placement'],complete_success=result['success'],frame=at,
                    eef_oracle_goal_distance_m=distance,xy_m=xy,height_m=height,pair_contact=contact,
                    source_linear_m_s=speed,source_angular_rad_s=angular,lower_prefix_valid=lower,
                    pre_ready=event['pre_placement_ready'],release_entry_ready=event['release_entry_ready']))
    proof = dict(aggregate=aggregate,rows=rows,
        inputs_sha256={name:hashlib.sha256((out/name).read_bytes()).hexdigest() for name in ('plan.json','groups.json','trace_schema.json')},
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        scope='Descriptive joint outcomes using the unchanged fixed criterion. Whole-task failure may occur later for another reason; dependent repeated scenes are not independent trials.')
    (out/'readiness_audit.json').write_text(json.dumps(proof,indent=2,allow_nan=False),encoding='utf-8')
    with (out/'placement_exits.csv').open('w',encoding='utf-8',newline='') as stream:
        writer = csv.DictWriter(stream,fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    lines = ['# Festes Ablagekriterium und spaeterer Gesamtaufgabenerfolg','',
        '| Panel/Arm/Platzierung | Austritte | Bereit: Erfolg / Fehlschlag | Nicht bereit: Erfolg / Fehlschlag | EEF <6mm trotz nicht bereit |',
        '|---|---:|---:|---:|---:|']
    for key,c in aggregate.items():
        lines.append(f"| {key} | {c['exits']} | {c['pre_ready_success']} / {c['pre_ready_failure']} | "+
            f"{c['pre_unready_success']} / {c['pre_unready_failure']} | {c['eef_within_6mm_pre_unready']} |")
    lines += ['', 'Nicht bereit beim Austritt ist kein alleiniger Fehlernachweis: Der Wuerfel kann nach dem Oeffnen korrekt absinken und beruhigen. '
        'Ein spaeterer Gesamtfehlschlag kann wiederum eine andere Ursache haben. Die kontrollierten Eingriffsarme liefern den engeren kausalen Vergleich.',
        '', 'Das EEF-Merkmal misst den Abstand zum am Phaseneintritt gespeicherten Expertenziel. '
        'Die 6-mm-Grenze ist die bestehende Expertenbedingung, keine nachtraeglich angepasste Klassifikationsschwelle.',
        '', 'CSV und JSON enthalten alle Austritte mit Parent, Familienkennung, Platzierung, Geometrie, Dynamik und vollstaendigem Ausgang. '
        'Keine Aenderung des vorab festgelegten Endpunkts oder des Ablagekriteriums.']
    (out/'READINESS_AUDIT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    audit(parser.parse_args().output.resolve())
