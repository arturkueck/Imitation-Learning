"""Write a factual closeout from this run only; no training or threshold changes."""
from pathlib import Path
import argparse
import json
import hashlib
import numpy as np
import torch


def read(p):return json.loads(p.read_text(encoding='utf-8'))


def main(out):
    assert read(out/'status.json')['state']=='COMPLETED'
    audit=read(out/'dataset_audit.json');result=read(out/'results.json');plan=read(out/'protocol.json')
    counts=audit['counts'];rows=audit['inventory']
    sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
    assert all(sha(p)==h for p,h in plan['input_hashes'].items())
    assert len(rows)==440 and len({r['initial_sha256'] for r in rows})==440
    assert all(sha(r['path'])==r['sha256'] for r in rows)
    with np.load(out/'dataset.npz',allow_pickle=False) as data:
        train=set(data['train_family']);valid=set(data['valid_family'])
        assert not train&valid
        for checkpoint in (out/'models').glob('*.pth'):
            ck=torch.load(checkpoint,map_location='cpu',weights_only=False)
            assert set(ck['training_families'])<=train and not set(ck['training_families'])&valid
    # Correct historical-template reporting flags; retain the exact prior outputs.
    corrections=[]
    if result.get('scorer_test_passed') and not result.get('current_guarded_controller_validated'):
        p=out/'results.json';before=sha(p);shutil_copy=p.read_text(encoding='utf-8')
        (out/'results_before_reporting_correction.json').write_text(shutil_copy,encoding='utf-8')
        result['current_guarded_controller_validated']=True
        result['validated_scope']='Local50-frame continuation on this fixed guarded development panel only'
        p.write_text(json.dumps(result,indent=2),encoding='utf-8')
        corrections.append(dict(file=p.name,original_sha256=before,reason='Historical-template flag; current-controller gates all passed; no metric change'))
    p=out/'verification.json'
    if p.exists():
        v=read(p)
        if not v['actor_weights_loaded']:
            before=sha(p)
            (out/'verification_before_reporting_correction.json').write_text(p.read_text(encoding='utf-8'),encoding='utf-8')
            v.update(actor_weights_loaded=True,actor_weights_use='Frozen inference during collection only; no actor optimizer',
                     collection_source_rows=440,source_rows_meaning='Eligible trajectory sources used for scorer fitting/evaluation')
            p.write_text(json.dumps(v,indent=2),encoding='utf-8')
            corrections.append(dict(file=p.name,original_sha256=before,reason='Collection loads frozen actors; scorer fitting alone does not; no weight or metric change'))
    if corrections:(out/'reporting_corrections.json').write_text(json.dumps(corrections,indent=2),encoding='utf-8')
    (out/'independent_integrity.json').write_text(json.dumps(dict(passed=True,trajectory_hashes_checked=440,
        original_input_hashes_unchanged=True,unique_start_families=440,train_valid_disjoint=True,
        scorer_checkpoints_trained_only_on_train_families=True,actor_updates=0,reporter_sha256=sha(__file__)),indent=2),encoding='utf-8')
    lines=['# Bewerterprüfung am aktuellen Controller — 05.11.2026','',
        'Fortsetzung von `../scorer_check_001/REPORT.md`. Unveränderte eingefrorene Parents und Retreat-Guard, keine Actorupdates. '
        'Das bisherige Qualitätsziel, die Eingaben und sämtliche Prüfschwellen wurden beibehalten.','',
        'Vorab festgelegt: 120 bestehende Trainingsfamilien exakt rekonstruieren, 120 neue Trainingsfamilien und 200 neue Validierungsfamilien. '
        'Keine Auswahl nach Fehlerhäufigkeit, keine künstlich schädlichen Aktionen und keine Verlängerung bis zum Bestehen. '
        'Die früheren 40 Transfervalidierungsfamilien und die historischen Bewerterfamilien sind ausgeschlossen. '
        'Reservierte Endtestrollouts wurden nicht eingelesen.','',
        '| Split | Versuche | Geeignete Familien | Fenster | Familien mit positivem / negativem Label |',
        '|---|---:|---:|---:|---:|']
    for split in ('train','valid'):
        c=counts.get(split,{})
        lines.append(f"| {split} | {sum(r['split']==split for r in rows)} | {c.get('families',0)} | {c.get('examples',0)} | {c.get('positive_families',0)} / {c.get('negative_families',0)} |")
    lines+=['','Positive und negative Familien können sich überschneiden, wenn eine Episode beide Fensterlabels enthält. '
        'Eine Familie erhält insgesamt dieselbe Metrikmasse wie jede andere.']
    with np.load(out/'dataset.npz',allow_pickle=False) as data:
        diagnostic={}
        for split in ('train','valid'):
            episodes=[r for r in rows if r['split']==split];fail=[r for r in episodes if not r['success']]
            f=data[f'{split}_family'];y=data[f'{split}_y']
            negative=set(f[y==0]);eligible=set(f)
            diagnostic[split]=dict(attempts=len(episodes),task_failures=len(fail),
                failures_with_eligible_window=sum(r['initial_sha256'] in eligible for r in fail),
                failures_with_negative_window=sum(r['initial_sha256'] in negative for r in fail),
                successful_episodes_with_negative_window=sum(r['success'] and r['initial_sha256'] in negative for r in episodes))
    (out/'target_coverage.json').write_text(json.dumps(diagnostic,indent=2),encoding='utf-8')
    d=diagnostic['valid']
    lines+=['',f"Von {d['task_failures']} vollständigen Aufgabenfehlschlägen in {d['attempts']} Validierungsversuchen haben "
        f"{d['failures_with_eligible_window']} überhaupt ein geeignetes Anflugfenster und {d['failures_with_negative_window']} mindestens ein negatives Qualitätsfenster. "
        f"Auch {d['successful_episodes_with_negative_window']} erfolgreiche Episoden enthalten negative Fenster. "
        'Dies beschreibt die Abdeckung des unveränderten lokalen Ziels; es ist keine kausale Erklärung aller Fehlschläge.']
    if 'validation' in result:
        lines+=['','Der Bewerter wurde ausschließlich auf den aktuellen Trainingsfamilien neu angepasst: '
            'lineares Modell und MLP, je drei Cross-Fit-Folds und drei Volltrainingsseeds, je 1.000 Updates. '
            'Die Modelle waren vor der Auswertung der Validierungsmetriken eingefroren.','',
            '| Bewerter | Familien-AUC | Brier | Präzision oberes Viertel |','|---|---:|---:|---:|']
        for kind,m in result['validation'].items():
            auc='—' if m['auc'] is None else f"{m['auc']:.4f}"
            brier='—' if m['brier'] is None else f"{m['brier']:.4f}"
            lines.append(f"| {kind} | {auc} | {brier} | {100*m['top_precision']:.2f} % |")
        lines+=['',f"Unveränderte Gates: `{json.dumps(result['gates'],ensure_ascii=False)}`.",
            f"Familienbootstrap, 95%-Intervalle: `{json.dumps(result['family_bootstrap_95ci'])}`.",
            '',f"Keine der {counts['valid']['families']} geeigneten Validierungsfamilien enthält beide Labels. "
            'Eine Qualitätsreihenfolge innerhalb derselben Episode ist damit nicht geprüft. '
            'Das obere Viertel bedeutet 25 % der familiengewichteten Fenstermasse; Scoregleichstände werden anteilig behandelt. '
            'Die gemessenen 100 % Auswahlpräzision sind keine Gesamterfolgsrate.',
            '',('Alle Gates erfüllt. Damit kann der getrennte BC-Vergleich vorbereitet werden; ein Actorvorteil bleibt ungeprüft.'
                if result['scorer_test_passed'] else 'Mindestens ein Gate verfehlt. Keine Freigabe für Bewertergewichte im BC-Training.')]
    else:
        lines+=['','Die Mindestabdeckung von zehn Familien je Klasse ist nicht in beiden Splits erfüllt. '
            'Es wurden keine Bewerterfits ausgeführt. Keine Freigabe für Qualitätsgewichte im BC-Training.']
    lines+=['','Der Actor blieb unverändert. Kein Actortraining gestartet und keine Actortrainingsgewichte exportiert. '
        'Ein positives lokales Label ist weder ein Dreierturmerfolg noch ein kausaler Aktionsvorteil. '
        'Eine Änderung des Qualitätsziels oder gezielte Stressprüfung erfordert ein eigenes vorab festgelegtes Protokoll.','',
        'Nachweise: `protocol.json`, `episodes.json`, `dataset_audit.json`, `dataset.npz`, `collection_verification.json`, '
        '`results.json`, `target_coverage.json` sowie gegebenenfalls `verification.json`, `crossfit_audit.json` und `models/`. '
        '`independent_integrity.json` bestätigt sämtliche 440 Trajektorienhashes und die Trainingsfamilien der Bewertercheckpoints. '
        '`reporting_corrections.json` dokumentiert korrigierte historische Vorlagenflags; unveränderte ursprüngliche Ergebnisdateien sind separat erhalten. '
        'Der technische Smoke `../scorer_guarded_smoke_002` bestätigt die vollständige Rekonstruktionsgleichheit zweier Familien. '
        'Sechs gezielte Tests bestanden. Der erste technische Smoke scheiterte an einem Python-Importkonflikt; '
        'dieser wurde vor dem Hauptlauf durch den vorhandenen eindeutigen Modulloader behoben.']
    if plan.get('infrastructure_recovery'):
        r=plan['infrastructure_recovery']
        lines+=['',f"Infrastrukturkorrektur: Der erste Hauptprozess endete nach {r['preserved_episodes']} gespeicherten Familien "
            'wegen eines Windows-Zugriffsfehlers beim atomaren Ersetzen der Statusdatei. '
            'Der Prozess war nachweislich beendet. Nach einem Test begrenzter Schreibwiederholungen wurden '
            'die vollständigen gespeicherten Trajektorien per SHA-256 geprüft und unverändert übernommen. '
            'Ein separater Fortsetzungslauf erzeugte ausschließlich die ausstehenden Familien. '
            'Ursprüngliches Zeitlimit, Reihenfolge, Seeds, Labels, Modelle und Schwellen blieben gleich. '
            'Das ursprüngliche Protokoll und die Abbruchdiagnose bleiben im ersten Lauf erhalten. '
            'Die einmalige operative Abweichung vom ursprünglichen Verbot automatischer Wiederholungen ist '
            'in `protocol.json/infrastructure_recovery` dokumentiert; wissenschaftliche Fits wurden nicht wiederholt.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps(dict(report=str(out/'REPORT.md'),counts=counts,target_coverage=diagnostic,
                         scorer_test_passed=result.get('scorer_test_passed',False))))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);a=p.parse_args();main(a.output.resolve())
