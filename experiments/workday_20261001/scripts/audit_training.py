"""Summarize all existing training logs and model readiness."""
import json, re
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
EXP=ROOT/'experiments/workday_20261001'
rows=[]
for folder in ('square','square_overnight','additional_tasks/stack_four'):
    for path in (ROOT/'experiments'/folder/'logs').glob('*training.log'):
        text=path.read_text(errors='replace')
        row=dict(log=str(path))
        for kind in ('Train','Validation'):
            points=[(int(e),json.loads(v).get('Loss')) for e,v in
                re.findall(kind+r' Epoch (\d+)\s*(\{.*?\})',text,re.S)]
            points=[p for p in points if p[1] is not None]
            if points: row[kind.lower()]=dict(last=points[-1],best=min(points,key=lambda p:p[1]))
        if len(row)>1: rows.append(row)
(EXP/'prior_training_losses.json').write_text(json.dumps(rows,indent=2))
lines=['# Prüfung der bisherigen Trainings','',
    '- Square BC: 0/20 Erfolge nach 50 Epochen. Als historische Referenz erneut auswerten, unverändertes Training aussetzen.',
    '- Square RNN: 8/20 nach 300 Epochen; stärkster bisheriger Kandidat. Als Referenz auf neue Seeds prüfen und gezielt mit einem neu trainierten GMM-Aktionsmodell vergleichen.',
    '- Square Transformer: bester bisher gemessener Zwischenstand 4/20 bei Epoche 200, zuletzt 2/20 bei Epoche 300. Früheren besseren Checkpoint erneut prüfen; keine unveränderte Fortsetzung.',
    '- StackFour RNN und Transformer: je 0/50 bei Epoche 1000. Validierungsverlust zuletzt deutlich höher als Train-Loss und höher als bei früheren Minima. Beste Validierungs-Checkpoints bei Epochen 454/497 nachprüfen; neues Training auf StackTwo reduzieren.',
    '- CubeHandover: Szene und Konfiguration vorhanden, aber kein Demonstrationsdatensatz. Noch kein trainiertes Modell vorhanden. Ein validierter Demonstrator ist der nächste notwendige Schritt, keine zusätzliche Trainingszeit.',
    '- Frühere Preview- und Robustheits-Smokes sind technische Tests und werden nicht als unabhängige Trainingserfolge gewertet.','',
    'Rohdaten: `prior_results_audit.json` und `prior_training_losses.json`. Der bestehende Vierer-Stapel-Diagnosebericht liefert die überprüften Fehlerszenarien.',
    'Neue Checkpoints werden anhand von Entwicklungsepisoden ausgewählt; der unabhängige Testsplit wird nicht zur Checkpointauswahl genutzt.','',
    '| Trainingslog | Letzte Epoche | Train-Loss | Validierungs-Loss |',
    '|---|---:|---:|---:|']
for row in rows:
    t=row.get('train',{}).get('last',[None,None]); v=row.get('validation',{}).get('last',[None,None])
    fmt=lambda x: f'{x:.5f}' if x is not None else '–'
    lines.append(f"| {Path(row['log']).name} | {t[0]} | {fmt(t[1])} | {fmt(v[1])} |")
(EXP/'TRAINING_REVIEW.md').write_text('\n'.join(lines),encoding='utf-8')
print('AUDIT_COMPLETED',len(rows),'training logs')
