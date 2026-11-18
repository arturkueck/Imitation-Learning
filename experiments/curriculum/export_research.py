"""Generate auditable human reports and public, path-free BC research evidence."""
from pathlib import Path
import hashlib
import json
import shutil

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
PUBLIC=ROOT/'sites/research-atlas-source/public'


def read(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def dump(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False),encoding='utf-8')


def main():
    sources={
      'ordering30':HERE/'axis_bc_20261110/ready_001/result_summary.json',
      'continuation60':HERE/'axis_bc_extension_20261110/ready_001/result_summary.json',
      'fixedCompletion':HERE/'axis_bc_completion_10h_20261111/ready_001/result_summary.json',
      'clockConfirmation':HERE/'axis_bc_clock_validation_20261112/ready_001/result_summary.json'}
    evidence={key:read(path) for key,path in sources.items()}
    evidence['provenance']={key:dict(source_id=path.parent.parent.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for key,path in sources.items()}
    clock=evidence['clockConfirmation']
    primary=[(name,results['3']) for name,results in clock['models'].items()]
    evidence['clockHeadline']=dict(pairs=sum(r['n'] for _,r in primary),gains=sum(r['gains'] for _,r in primary),losses=sum(r['losses'] for _,r in primary),
        models_improved=sum(r['bounded_successes']>r['original_successes'] for _,r in primary),optimizer_updates=0,
        negative_pairs=sum(r['2']['n'] for r in clock['models'].values()),negative_identical=all(r['2']['negative_identical'] for r in clock['models'].values()))
    evidence['abc']=dict(status='prepared',new_models=3,reused_models=6,updates=30000,seeds=[1,2,3],primary_scenes_per_model=100,
        arms=[dict(id='A',label='Standard-BC',sampling='Vollständiger Datenpool ab Beginn; phasenausgewogen',state='Neu zu trainieren'),
              dict(id='B',label='Kontroll-BC',sampling='Exakt die Batches von C, durchmischte Reihenfolge',state='30k-Gewichte vorhanden; neue Auswertung offen'),
              dict(id='C',label='Curriculum-BC',sampling='X-lastig → XY → vollständiger Pool',state='30k-Gewichte vorhanden; neue Auswertung offen')],
        limitations='Training ausschließlich auf Zweier-Demonstrationen; Dreierturm mit vorgegebener Paarreihenfolge und privilegierten Zustandsmerkmalen.')
    evidence['updated']='2026-11-12'
    # Public evidence never contains local checkpoint filenames, absolute paths or RNG data.
    dump(PUBLIC/'curriculum-evidence/results.json',evidence)
    dump(HERE/'reporting/measured.json',evidence)
    image_sources={
       'loss-curves.png':HERE/'axis_bc_20261110/analysis_loss/loss_curves.png',
       'development-success.png':HERE/'axis_bc_20261110/analysis_loss/development_success.png',
       'release-clock.png':HERE/'axis_bc_release_diagnosis_20261112/probe_001/release_clock_probe.png'}
    for name,source in image_sources.items():shutil.copy2(source,PUBLIC/'curriculum-evidence'/name)
    rows='\n'.join(f"| {name} | {r['original_successes']}/{r['n']} | {r['bounded_successes']}/{r['n']} | +{r['gains']} / −{r['losses']} |" for name,r in primary)
    report=f'''# BC, Curriculum und Freigabephase: Stand 12.11.2026

## Belastbarer aktueller Befund

Die Begrenzung des Zeitmerkmals der letzten Freigabe verbessert alle sechs
unveränderten gewöhnlichen 60k-Modelle auf einem neuen gepaarten Panel.
600 Dreierturm-Modell/Szenenpaare: **60 zusätzliche Erfolge, kein verlorener
Erfolg**. Alle 120 Zweierturm-Kontrollpaare sind bitgenau identisch.
Null Optimizerupdates; dies ist eine Ausführungskorrektur, kein neu trainiertes Modell.

| Modell | Original | Zeit begrenzt | Gepaarte Gewinne / Verluste |
|---|---:|---:|---:|
{rows}

100 frische Szenen je Modell; gleiche Szenen über alle Seeds. Die Szenen sind
keine unabhängigen Trainingsreplikate. Der praktische Review-Schwellwert wurde
erreicht; daraus folgt keine allgemeine Garantie oder automatische Aktivierung.

## Was die vorherigen Vergleiche zeigten

1. **30k, B gegen C:** Durchmischte Batchreihenfolge 49/54/49, Curriculum
   47/40/41 Dreiertürme je 100 Starts im ursprünglichen Endpanel. Damals war
   das Zeitproblem noch vorhanden; das ist keine neue zeitkorrigierte A/B/C-Auswertung.
2. **30k → 60k:** Auf einem anderen frischen Panel durchmischt 51→49,
   56→50, 52→48; Curriculum 52→41, 47→62, 47→60. Mehr Updates halfen nicht einheitlich.
3. **Feste Abschlussfunktion:** Bei fünf der sechs Modelle niedrigere
   Dreierturmraten als mit gewöhnlicher Fortsetzung. Kein stabiler Vorteil.
4. **Diagnose:** Phase-6-Zeitwerte waren im Training nur bis Schritt 17 enthalten.
   Bei längerer Ausführung drifteten Aktionen im ausgewählten Fehlerfall nach
   unten und erneuter Fingerkontakt unterbrach die geforderten 50 stabilen Frames.
   Der kleine Vorversuch betraf ausgewählte historische Fälle, die anschließende
   Zeitkorrektur-Bestätigung hingegen 100 neue Starts je Modell.

Die genannten Panels verwenden verschiedene reservierte Szenenbereiche.
Ihre absoluten Prozentwerte dürfen nicht als durchgehende Leistungskurve
verkettet werden. Quellen und SHA-256 stehen in reporting/measured.json.

## Nächste Untersuchung: A/B/C

Vorbereitet, nicht gestartet: drei neue Standard-BC-Modelle A; die sechs
ursprünglichen B/C-30k-Modelle werden mit geprüften gleichen Ausgangsgewichten
und Einstellungen wiederverwendet. Alle neun Endpunkte erhalten dieselbe
Zeitbehandlung und frische gepaarte Zwei-/Dreierturmtests.

- A gegen B: Änderung der Datenexposition bei durchmischter Reihenfolge.
- B gegen C: Reihenfolge desselben Batch-Multisets.
- A gegen C: Gesamtnutzen dieses Curriculums.

Die vorhandenen besseren zeitkorrigierten 60k-Curriculumwerte belegen den
isolierten Curriculum-Nutzen bei 30k noch nicht. Es gibt weiterhin ausschließlich
Zweier-Demonstrationen; höhere Ablagen, Recovery und autonome Paarplanung sind
keine durch zusätzliche Trainingsdaten bereits gelösten Fragen.
'''
    (HERE/'RESULTS.md').write_text(report,encoding='utf-8')
    histories=[
      ('bc-curriculum-30k','axis_bc_20261110','BC · B/C-Reihenfolge · 30k','completed','Originaler B/C-Vergleich; Ausführung damals ohne spätere Zeitkorrektur.',evidence['ordering30']),
      ('bc-curriculum-60k','axis_bc_extension_20261110','BC · Fortsetzung 30k → 60k','completed','Weitertraining mit gleichen neuen Batches; Ergebnis je Seed uneinheitlich.',evidence['continuation60']),
      ('bc-fixed-completion-60k','axis_bc_completion_10h_20261111','BC · Feste Abschlussfunktion','completed','Feste 30k-Abschlussfunktion gegen gewöhnliche Fortsetzung; kein stabiler Vorteil.',evidence['fixedCompletion']),
      ('bc-clock-confirmation','axis_bc_clock_validation_20261112','BC · Zeitkorrektur bestätigt','completed','Auswertung unveränderter 60k-Gewichte: 60 zusätzliche gepaarte Dreiertürme, keine Verluste; null Trainingsupdates.',clock),
      ('bc-abc-30k','abc_comparison_20261112','BC · A/B/C-Vergleich vorbereitet','design','Nur A wird neu trainiert; B/C-30k-Gewichte vorhanden. Einheitliche Zeitbehandlung, frische Tests noch offen.',evidence['abc'])]
    entries=[]
    for run_id,family,title,kind,description,results in histories:
        folder=HERE/'reporting'/run_id
        cfg=dict(seeds=[1,2,3],batch=64,lr=.0001,weight_decay=.000001,
                 loss='MSE XYZ/Greifer + 0,1 Abschluss-BCE; angezeigte Kurven: Aktions-MSE',dataset='180 train / 20 validation whole two-cube trajectories',
                 optimizer_updates=0 if run_id=='bc-clock-confirmation' else 30000)
        dump(folder/'config.json',cfg)
        dump(folder/'status.json',dict(stage='complete' if kind=='completed' else 'planned'))
        dump(folder/'results.json',results)
        curves=[]
        run=HERE/family/'ready_001'
        if run_id in ('bc-curriculum-30k','bc-curriculum-60k','bc-fixed-completion-60k'):
            panels={}
            for file in run.glob('panel_u*.json'):
                panel=read(file);update=int(file.stem.split('u')[1]);panels[update]=panel
            metrics=run/'metrics.jsonl'
            if metrics.exists():
                for line in metrics.read_text().splitlines():
                    row=json.loads(line);name=row['model'];seed=int(name.rsplit('seed',1)[1])
                    curves.append(dict(seed=seed,arm=name.rsplit('_seed',1)[0],update=row['update'],train_mse=row['action_mse'],
                        validation_mse=panels.get(row['update'],{}).get(name,{}).get('action_mse')))
        dump(folder/'curves.json',curves)
        (folder/'README.md').write_text(f'# {title}\n\n{description}\n\nSiehe ../../RESULTS.md. Daten aus archivierten Messungen; kein neuer Trainingslauf durch Website-Export.\n',encoding='utf-8')
        entries.append(dict(id=run_id,category='robot',method='il',kind=kind,title=title,
            directory=str(folder.relative_to(ROOT)).replace('\\','/'),config='config.json',parameters=259910 if run_id=='bc-fixed-completion-60k' else 129955,
            description=description,checkpointInfo='Drei A-Modelle vorbereitet; sechs vollständige B/C-30k-Checkpoints vorhanden' if kind=='design' else 'Versionierte Modelle mit AdamW, RNG und Sampleplan im lokalen Modellkatalog',
            architecture=[['Policy','PhaseNet · 7 Phasenköpfe · Breite 128'],['Parameterumfang','129.955 trainierbar + 129.955 feste Referenz in der eingefrorenen Bedingung' if run_id=='bc-fixed-completion-60k' else '129.955 je Policy'],['Eingabe','10 privilegierte Zustandsmerkmale'],['Ausgabe','XYZ und Greifer; Abschluss-Logit'],['Ziel','Stabiler Dreierturm; Paarreihenfolge vorgegeben']],
            artifacts=[dict(name='results.json',file='results.json',kind='document',label='Messwerte und Grenzen'),dict(name='README.md',file='README.md',kind='document',label='Einordnung')]))
    registry=read(ROOT/'monitor/training-runs.json')
    ids={entry['id'] for entry in entries}
    registry['runs']=[entry for entry in registry['runs'] if entry['id'] not in ids]+entries
    dump(ROOT/'monitor/training-runs.json',registry)
    for _,family,title,kind,description,_ in histories:
        folder=HERE/family;file=folder/'README.md'
        content=file.read_text(encoding='utf-8') if file.exists() else f'# {title}\n'
        start='<!-- current-bc-status:start -->';end='<!-- current-bc-status:end -->'
        if start in content:content=content.split(end,1)[1].lstrip()
        banner=f'{start}\n> Stand 12.11.2026: **{"Vorbereitet" if kind=="design" else "Abgeschlossen"}**. {description} '
        banner+='[Gesamteinordnung](../RESULTS.md) · Laufdaten unter `praxis/results/curriculum/`.\n'+end+'\n\n'
        file.write_text(banner+content,encoding='utf-8')
    print(json.dumps(dict(public_evidence='curriculum-evidence/results.json',registered_runs=len(entries),clock_gains=evidence['clockHeadline']['gains'])))


if __name__=='__main__':main()
