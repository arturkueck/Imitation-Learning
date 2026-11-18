"""Export measured BC conclusion to project docs and selected Atlas assets only."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import re
from datetime import datetime,timezone

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[1]
RUNS=ROOT/'praxis/results/curriculum'
POLICIES=['baseline','replay','action','completion','combined']
LABELS=['Ursprüngliches B','Replay-Fortsetzung','Nur Aktionen','Nur Abschluss','Aktionen + Abschluss']


def read(path):return json.loads(path.read_text(encoding='utf-8'))
def dump(path,value):path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')


def repair_text(value):
    if isinstance(value,dict):return {k:repair_text(v) for k,v in value.items()}
    if isinstance(value,list):return [repair_text(v) for v in value]
    if not isinstance(value,str):return value
    for _ in range(3):
        if not any(token in value for token in ('Ã','Â','â€')):break
        for encoding in ('cp1252','latin1'):
            try:value=value.encode(encoding).decode('utf-8');break
            except (UnicodeError,ValueError):continue
        else:break
    return value


def measured():
    paths=dict(abc=RUNS/'abc_comparison_20261112/ready_001/result_summary.json',
        phase=RUNS/'phase_skill_audit_v1/run_001/summary.json',
        grasp=RUNS/'second_grasp_probe_v1/night_001/summary.json',
        ablation=RUNS/'grasp_phase_ablation_v1/ready_001/summary.json',
        correction=RUNS/'approach_bc_correction_v1/ready_001/summary.json',
        paired=RUNS/'approach_bc_correction_v1/ready_001/paired_changes.json',
        dataset=RUNS/'approach_bc_correction_v1/ready_001/dataset_manifest.json')
    values={k:read(v) for k,v in paths.items()}
    trainrun=paths['correction'].parent
    assert read(trainrun/'status.json')['state']=='COMPLETE'
    aggregate={panel:{policy:dict(n=sum(v[policy]['n'] for v in models.values()),successes=sum(v[policy]['successes'] for v in models.values())) for policy in POLICIES} for panel,models in values['correction'].items()}
    paired={panel:{comparator:{policy:{key:sum(v[comparator][policy][key] for v in models.values()) for key in ('gains','losses')} for policy in POLICIES} for comparator in ('baseline','replay')} for panel,models in values['paired'].items()}
    assert [aggregate['confirmation'][p]['successes'] for p in POLICIES]==[85,92,92,78,118]
    assert paired['confirmation']['baseline']['combined']==dict(gains=34,losses=1)
    for folder in trainrun.glob('mixed_*'):
        if folder.is_dir():assert read(folder/'loss.json')[-1]['update']==5000 and (folder/'latest.pth').exists()
    attempts=read(trainrun/'collection_attempts.json')
    import numpy as np
    families={}
    for split in ('train','validation'):
        path=trainrun/f'corrections_{split}.npz'
        assert hashlib.sha256(path.read_bytes()).hexdigest()==values['dataset']['hashes'][split]
        with np.load(path) as archive:families[split]=len(set(archive['family'].tolist()))
    evidence=dict(schema='bc-conclusion-v1',updated='2026-11-13',
        training=dict(summary=values['correction'],aggregate=aggregate,paired=paired,updates_per_component=5000,components=12,
            policies=dict(zip(POLICIES,LABELS)),confirmation_unique_scenes=50,training_model_seeds=3,
            execution_scope='Only second placement, phase 0, excluding retreat; other outputs remain B',
            architecture='Separate action and completion PhaseNet copies; no critic; no curriculum ordering experiment'),
        dataset=dict(attempts=values['dataset']['attempts'],accepted=values['dataset']['accepted'],train_frames=values['dataset']['train_frames'],validation_frames=values['dataset']['validation_frames'],
            attempted_train_families=40,attempted_validation_families=10,train_families=families['train'],validation_families=families['validation'],accepted_train=sum(a['accepted'] and a['split']=='train' for a in attempts),accepted_validation=sum(a['accepted'] and a['split']=='validation' for a in attempts),split_unit='whole initial scene family across all source controllers'),
        ablation=values['ablation'],grasp=values['grasp'],phase=values['phase'],abc=values['abc'],
        provenance={key:dict(source_id=f'{path.parent.parent.name}/{path.parent.name}/{path.name}',sha256=hashlib.sha256(path.read_bytes()).hexdigest()) for key,path in paths.items()},
        limits=['50 shared confirmation scenes across three model seeds, not 150 independent scenes',
            'Fixed update endpoint; simulator privileged low-dimensional state; fixed task coordinator',
            'Separate output components restricted to second approach; no single-network distillation tested',
            'No curriculum-ordering advantage, arbitrary tower heights, hardware or general data-problem solution established'])
    return evidence


def narrative(e):
    rows='\n'.join(f"| {label} | {e['training']['aggregate']['confirmation'][p]['successes']}/150 |" for p,label in zip(POLICIES,LABELS))
    return f'''# Abschlussstand: BC, Curriculum und zweites Anfahren · 13.11.2026

Ziel war, das Stapeln von drei Würfeln mit Behavior Cloning zu verbessern und
die beobachteten Schwächen durch kontrollierte Versuche einzugrenzen. Der
aktuelle Abschluss belegt eine gezielte BC-Verbesserung auf einem neuen
Bestätigungspanel. Ein Nutzen geordneter Curriculum-Präsentation ist nicht belegt.

## Vorgehen und Entscheidungskette

1. **A/B/C bei 30.000 Updates:** A zeigt vollständige phasenausgewogene Daten,
   B und C dieselben Batches in gemischter bzw. X→XY→XYZ-Reihenfolge. Auf dem
   gemeinsamen neuen Dreierturm-Panel: A 40/28/26, B 48/56/50, C 52/42/46
   Erfolge je 100 Szenen pro Modellseed. B ist durchgängig besser als A; die
   geordnete Reihenfolge C übertrifft B nur in einem von drei Seeds.
2. **Phasendiagnose, 220 Versuche ohne Training:** Expertenphasen werden exakt
   aus Controller und Demonstrationen rekonstruiert. Experten-Präfixe erzeugen
   echte Greif-/Kontaktzustände, ohne Teleportation. Isolierte Teilfertigkeiten
   werden von vollständigen BC-Abläufen getrennt. Travel/Open gelingen in den
   30 getesteten Expertenkontexten jeweils vollständig. Bei 15/48 erreichten
   zweiten Lift-Starts fehlt im Gesamtrollout ein Griff; alle 15 scheitern.
   Kleine Abweichungen von einer strengen Lift-Schwelle werden nicht automatisch
   als Ursache eines Gesamtfehlers interpretiert.
3. **Gepaarte Expertenübernahme des zweiten Greifens:** Nur Approach,
   Grasp-Descend und Close werden ersetzt, danach wieder B. Gleiche Historie
   bis zum Eingriff, historische Kontrolle reproduziert. 26/60 → 45/60
   Gesamterfolge; 19 Gewinne, keine Verluste. Kein Lernen in diesem Versuch.
4. **Einzelphasen, 300 Episoden:** BC 26/60; nur Approach 45/60; nur
   Grasp-Descend 35/60; nur Close 26/60; kompletter Greifablauf 45/60.
   Approach ist der stärkste Ansatzpunkt. Jeder Experteneingriff ersetzt Aktion
   und Abschlussregel gemeinsam; er isoliert nicht Bewegung von Übergang.
5. **Gezieltes BC-Korrekturtraining:** Neue Expertenkorrekturen werden vom
   tatsächlich durch B erreichten Beginn des zweiten Anfahrens gesammelt.
   Getrennte Aktions- und Abschlusskopien erlauben die funktionale Auswertung
   beider Komponenten einzeln und gemeinsam, während die übrige Ausführung B bleibt.

## Daten, Modell und Lernen

Die drei B-Ausgangsmodelle haben je sieben unabhängige PhaseNet-MLPs mit Breite
128: zehn privilegierte Simulationsmerkmale, Aktionen XYZ/Greifer und ein
Phasenabschluss-Logit. Rotationen bleiben wie bisher null. Der Abschluss ist
kein Critic. Die ursprünglichen Demonstrationen stammen aus Zweier-Stapelaufgaben.

Neue Sammlung: 40 Trainings- und 10 Validierungsfamilien, jeweils mit allen drei
B-Controllern. Von 150 Sammelversuchen werden 135 akzeptiert: 108 Training,
27 Validierung. Tatsächlich enthalten sind 36 Trainings- und neun
Validierungsfamilien. Daraus entstehen 2.069 Trainings- und 499 Validierungsframes.
Die 15 Abbrüche erreichen das zweite Anfahren nicht; sie werden dokumentiert,
nicht durch andere Starts ersetzt. Ganze Anfangsszenen bleiben über alle
Controller und Frames in genau einem Split. Neue Bestätigungsszenen werden
nicht als Korrekturdaten genutzt.

Pro B-Modell werden vier Kopien jeweils 5.000 Updates fortgesetzt:
Replay-Aktion, Replay-Abschluss, Korrektur-Aktion und Korrektur-Abschluss.
Alle starten aus den ursprünglichen Gewichten und dem vollständigen AdamW-Zustand.
Trainiert wird die gesamte Phase-0-MLP, einschließlich versteckter Schichten;
Phase 1–6 bleibt bitgleich. Aktions-MSE und 0,1 × gewichtete Abschluss-BCE werden
in getrennten Kopien optimiert. Korrekturbatches mischen 32 alte Phase-0-Frames
mit 32 neuen Frames; Replay nutzt 64 alte Frames. Samplingpläne sind festgelegt
und zwischen Aktions-/Abschlusskopie gleich. LR 1e-4, Decay 1e-6, Gradientengrenze 10.

Die fünf Ausführungen sind ursprüngliches B, fortgesetzte Replay-Komposition,
nur neue Aktionen, nur neuer Abschluss sowie beide neuen Komponenten gemeinsam.
Einzel- und kombinierte Ausführung verwenden exakt dieselben gelernten Kopien;
die Kombination erhält keine zusätzlichen Updates. Das ist ein zusammengesetztes
Diagnosesystem, keine neue Schicht und keine Verdichtung zu einer gemeinsamen MLP.

Die neuen Ausgaben werden ausschließlich bei Platzierung 2, Phase 0, außerhalb
des Rückzugs aktiviert. Erstes Anfahren, Rückzug und alle anderen Phasen behalten
B. Der Kontext wird vom vorhandenen Sequencer vorgegeben. Die 0,8-Schwelle,
finale Clock-Korrektur und strenge Erfolgsdefinition bleiben gleich.

## Ergebnis auf neuen Bestätigungsszenen

Fester Endpunkt 5.000 Updates je Komponente; kein Best-of-Test und keine
Schwellenanpassung. Gesamterfolg: vollständiger Dreierturm für 50 aufeinanderfolgende
strenge Gültigkeitsframes ohne Fingerkontakt, bei höchstens 1.000 Schritten.

| Ausführung | Erfolge auf 150 Modell-/Szenenpaaren |
|---|---:|
{rows}

Kombiniert: 78,7 % statt 56,7 % bei B, Unterschied +22,0 Prozentpunkte.
Gegen B: 34 gepaarte Gewinne, ein Verlust. Gegen Replay: 28 Gewinne, zwei Verluste.
Pro Modellseed steigt B 27/32/26 auf kombiniert 39/39/40 je 50 Starts; Replay
liegt bei 32/32/28. Beide neuen Komponenten gemeinsam übertreffen Replay bei
allen drei Modellseeds. Nur der neue Abschluss verschlechtert zwei Modelle.

Das bekannte Entwicklungspanel bleibt separat: B 26/60, Replay 30/60,
Aktion 27/60, Abschluss 23/60, kombiniert 45/60. Diese Werte werden nicht mit
der neuen Bestätigung zu einer Leistungskurve oder gemeinsamen Quote vermischt.

## Belastbare Aussage und Grenzen

Gezielte Expertenkorrekturen für das zweite Anfahren verbessern in diesem
Versuchsaufbau den vollständigen Stapelerfolg, wenn gelernte Aktionen und
gelernter Phasenabschluss gemeinsam eingesetzt werden. In der Auswertung
übernimmt kein Experte. Das Ergebnis betrifft trainierte Komponenten und
geht über den vorherigen Nachweis einer Expertenhilfe hinaus.

50 Bestätigungsszenen werden über drei Modellseeds geteilt: 150 Modell-/Szenenpaare
sind keine 150 unabhängigen Szenen. Es gibt keine breite Signifikanzbehauptung.
Die Bestätigung prüft neue Anfangszustände im selben Simulator, keine neue
Objektgeometrie, Hardware oder andere Aufgabe. Bestätigungsstarts gelten jetzt
als geöffnet und dürfen nicht still als neue Validierungs-/Trainingsquelle dienen.

Getrennte Aktions-/Abschlusskopien und der Kontext-Gate gehören zum Verfahren.
Eine einzelne gemeinsame MLP mit demselben Erfolg wurde nicht gezeigt.
Ein geordnetes Curriculum, autonomes Paarplanen, beliebige Turmhöhen und ein
allgemein gelöstes Datenproblem sind nicht belegt. Rückzug und langes Open
bleiben ohne neu demonstrierte vollständige Trainingsabdeckung. Die vorhandenen
Kontrollen geben keinen Anlass für einen zwingenden weiteren Trainingslauf,
um diesen gezielten BC-Befund als aktuellen Abschluss zu berichten.

## Reproduzierbarkeit, Modelle und Abschluss

Der Lauf ist COMPLETE und benötigte rund 68 Minuten. Zwölf Komponenten haben
je 5.000 zusätzliche Updates. Gespeichert sind die unveränderten B-Vorfahren,
Kompositionskarten, versionierte Zwischen-/Endcheckpoints, vollständige
Optimizerzustände, nächster Batchindex, feste Samplingpläne und RNG-Zustände.
Die Wiederaufnahme aller vier Komponententypen wurde technisch auf bitgleiche
Gewichte und Optimizerzustände geprüft. Nicht behauptet wird plattformübergreifende
Bitgleichheit. Originalmodelle wurden nicht überschrieben.

Protokoll, Eingangs-Hashes, Quellenkopien und Paket-/GPU-Umgebung liegen beim
Lauf. Sammelversuche, Splitfamilien, Datenhashes, Loss-/Validierungswerte sowie
vollständige Rollouts und gepaarte Veränderungen bleiben lokal erhalten.
Keine Checkpoint-Auswahl auf dem Bestätigungspanel. Keine automatischen
Folgeversuche, kein Herunterfahren; Schlafverhinderung wieder freigegeben.

Die Website erhält ausschließlich verdichtete Messwerte, Abbildungen, diese
Einordnung und Quellen-Hashes. Keine Modellgewichte, RNG-Zustände oder Rohdaten.
'''


def graph(e,public):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,axes=plt.subplots(1,2,figsize=(12,4.8),layout='constrained')
    for ax in axes:ax.spines[['top','right']].set_visible(False);ax.set_xlim(0,100);ax.set_xlabel('Vollständiger Dreierturm: Anteil (%)');ax.grid(axis='x',alpha=.2);ax.set_axisbelow(True)
    for ax,vals,title in [(axes[0],[26,45,35,26,45],'Ursachenprüfung · bekannte Entwicklung'),(axes[1],[e['training']['aggregate']['confirmation'][p]['successes'] for p in POLICIES],'BC-Training · neue Bestätigung')]:
        denominator=60 if ax is axes[0] else 150
        labels=['BC','Nur Anfahren','Nur Absenken','Nur Schließen','Gesamtes Greifen'] if ax is axes[0] else LABELS
        ax.barh(labels,[100*v/denominator for v in vals],color=['#6b7888','#378b8a','#6b7888','#6b7888','#28766d'])
        ax.invert_yaxis();ax.set_title(title,fontsize=11,pad=14)
        for y,v in enumerate(vals):ax.text(100*v/denominator+1,y,f'{v}/{denominator}',va='center',fontsize=10)
    fig.suptitle('Experteneingriff und gelerntes BC: getrennte Versuche',fontsize=14)
    fig.savefig(public/'curriculum-evidence/conclusion-comparison.png',dpi=170);plt.close(fig)
    fig,axes=plt.subplots(2,2,figsize=(11,7),layout='constrained')
    for row,kind in enumerate(('actor','completion')):
        for col,source in enumerate(('replay','correction')):
            ax=axes[row,col]
            for seed in (1,2,3):
                points=read(RUNS/f'approach_bc_correction_v1/ready_001/mixed_s{seed}_u30000_{source}_{kind}/loss.json')
                ax.plot([p['update'] for p in points],[p['loss'] for p in points],marker='o',label=f'Seed {seed}')
            ax.set_title(('Replay' if source=='replay' else 'Korrektur')+' · '+('Aktions-MSE' if kind=='actor' else '0,1 × gewichtete Abschluss-BCE'))
            ax.set_xlabel('Zusätzliche Komponentenupdates');ax.set_ylabel('Protokollierter Batch-Loss');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('Training: getrennte Loss-Terme und Achsenskalierungen',fontsize=13)
    fig.savefig(public/'curriculum-evidence/correction-loss.png',dpi=160);plt.close(fig)


def website(e,public,report):
    evidence=public/'curriculum-evidence';evidence.mkdir(exist_ok=True)
    dump(evidence/'conclusion.json',e);(evidence/'conclusion.md').write_text(report,encoding='utf-8');graph(e,public)
    rows=''.join(f'<tr><th>{label}</th><td>{e["training"]["aggregate"]["confirmation"][p]["successes"]}/150</td><td>{100*e["training"]["aggregate"]["confirmation"][p]["successes"]/150:.1f} %</td></tr>' for p,label in zip(POLICIES,LABELS))
    additions=f'''<section id="bc-correction" aria-labelledby="bc-result"><div class="section-heading"><div><p class="eyebrow">ABGESCHLOSSEN · GEZIELTES BC-TRAINING</p><h2 id="bc-result">Aktionen und Phasenabschluss gemeinsam verbessern</h2></div><span class="badge">Neue Bestätigung · feste 5.000 Updates</span></div>
<div class="stats"><article><strong>118 / 150</strong><span>vollständige Dreiertürme mit beiden trainierten Komponenten, gegenüber 85/150 bei B</span></article><article><strong>+34 / −1</strong><span>gepaarte Gewinne / Verluste gegenüber B; gegen Replay +28 / −2</span></article><article><strong>3 / 3</strong><span>Modellseeds verbessern sich gegenüber Replay: 39/39/40 statt 32/32/28 Erfolge je 50 Starts</span></article></div>
<div class="panel"><div class="table-wrap"><table><caption>Neue Bestätigung: 50 gemeinsame Szenen × drei Modellseeds</caption><thead><tr><th>Ausführung</th><th>Erfolge</th><th>Anteil</th></tr></thead><tbody>{rows}</tbody></table></div>
<p>Während der Auswertung übernimmt kein Experte. Die beiden Korrekturkomponenten wurden getrennt gelernt und werden beim zweiten Anfahren gemeinsam eingesetzt. Nur Aktionen helfen weniger; nur der neue Abschluss verschlechtert zwei Modelle.</p>
<p class="caveat">150 Modell-/Szenenpaare sind keine 150 unabhängigen Szenen. Die 50 Anfangsszenen werden über drei Modellseeds geteilt. Das bekannte Entwicklungspanel bleibt getrennt: B 26/60, kombiniert 45/60.</p>
<a class="text-link" href="curriculum-evidence/conclusion.json">Messwerte, gepaarte Veränderungen und Quellen-Hashes ↗</a> · <a href="curriculum-evidence/conclusion.md">Vollständige Vorgehens- und Ergebniseinordnung ↗</a></div></section>
<section aria-labelledby="chain"><p class="eyebrow">VORGEHEN · VON DER DIAGNOSE ZUM LERNVERSUCH</p><h2 id="chain">Den zweiten Anfahrprozess eingrenzen</h2>
<ol class="timeline"><li><span>01 / A–B–C</span><div><h3>Reihenfolge zeigt keinen konsistenten Zusatznutzen</h3><p>A 40/28/26, B 48/56/50, C 52/42/46 Erfolge je 100 neue Starts. B übertrifft A in allen Seeds; die X→XY→XYZ-Reihenfolge C übertrifft B nur in einem Seed.</p></div></li>
<li><span>02 / PHASEN</span><div><h3>Teilfertigkeit und Eingangszustand trennen</h3><p>220 Diagnoseversuche ohne Training. Exakte Expertenlabels und echte Experten-Präfixe statt Zustands-Teleportation. Travel und Open erreichen je 30/30 isolierte Ziele. Im Gesamtrollout fehlt bei 15/48 zweiten Lift-Starts ein Griff; alle 15 scheitern.</p></div></li>
<li><span>03 / EINGRIFF</span><div><h3>Expertenhilfe beim zweiten Greifen wirkt</h3><p>Nur Approach, Grasp-Descend und Close ersetzt; danach wieder B. 26/60 → 45/60 Gesamterfolge, 19 Gewinne ohne Verlust. Noch keine Verbesserung durch Lernen.</p></div></li>
<li><span>04 / EINZELPHASEN</span><div><h3>Anfahren ist der stärkste Ansatzpunkt</h3><p>300 Episoden: BC 26/60, nur Anfahren 45/60, nur Absenken 35/60, nur Schließen 26/60, gesamtes Greifen 45/60. Die Eingriffe ersetzen jeweils Aktion und Abschlussregel gemeinsam.</p></div></li>
<li><span>05 / BC</span><div><h3>Korrekturen aus tatsächlich erreichten Zuständen lernen</h3><p>Neue, getrennte Trainings-/Validierungsfamilien. Aktions- und Abschlusslernen einzeln und gemeinsam gegen ursprüngliches B und eine Replay-Fortsetzung auswerten. Fester Endpunkt, keine Best-of-Test-Auswahl.</p></div></li></ol>
<figure><a href="curriculum-evidence/conclusion-comparison.png"><img src="curriculum-evidence/conclusion-comparison.png" alt="Getrennte Panels: Expertenhilfe beim Anfahren erreicht 45/60 bekannte Entwicklungsfälle; gelerntes kombiniertes BC erreicht 118/150 neue Bestätigungspaare." loading="lazy"></a><figcaption>Links: Experteneingriff, null Updates, bekannte Entwicklungsszenen. Rechts: trainierte Komponenten, neue Bestätigung. Die Panels sind keine gemeinsame Lernkurve.</figcaption></figure></section>
<section class="panel" aria-labelledby="correction-method"><p class="eyebrow">DATEN · MODELL · AUSFÜHRUNG</p><h2 id="correction-method">Was genau trainiert wurde</h2>
<p>40 neue Trainings- und zehn Validierungsfamilien werden mit drei B-Ausgangscontrollern ausgeführt. Von 150 Sammelversuchen sind 135 akzeptiert: 108 Training, 27 Validierung. Tatsächlich enthalten sind 36 Trainings- und neun Validierungsfamilien mit 2.069 bzw. 499 Frames. Ganze Anfangsszenen bleiben über alle Controller und Frames in einem Split; 15 nicht erreichte Anfahrphasen werden protokolliert statt ersetzt.</p>
<p>Je Modell vier Komponenten mit je 5.000 Updates: Replay-Aktion, Replay-Abschluss, Korrektur-Aktion und Korrektur-Abschluss. Start aus B-Gewichten samt AdamW-Zustand. Nur die gesamte Phase-0-MLP wird trainiert; Phase 1–6 bleibt bitgleich. Batch 64; Korrekturbatches mischen 32 alte Phase-0-Frames mit 32 neuen Frames. Replay nutzt 64 alte Frames. LR 1e-4; Aktions-MSE bzw. 0,1 × gewichtete Abschluss-BCE.</p>
<p>Die versteckten Gewichte der ursprünglichen MLP beeinflussen Aktion und Abschluss gemeinsam. Getrennte Kopien erlauben deshalb funktional getrennte Ausgaben. Die kombinierte Ausführung nutzt exakt die separat gelernten Kopien und erhält keine weiteren Updates. Es handelt sich um ein zusammengesetztes Diagnosesystem, nicht um eine neue letzte Schicht.</p>
<p>Ein expliziter Sequencer-Kontext aktiviert neue Ausgaben nur bei Platzierung 2, Phase 0, außerhalb des Rückzugs. Erstes Anfahren und Rückzug bleiben bei B. Die Erfolgsdefinition verlangt 50 aufeinanderfolgende strenge stabile Frames ohne Fingerkontakt. Bestätigungsstarts werden nicht zum Training oder zur Auswahl des besten Checkpoints verwendet.</p>
<details><summary>Protokollierte Komponenten-Losswerte</summary><p>Je ein Trainingsbatch-Loss bei 1.000 bis 5.000 zusätzlichen Updates. Aktions-MSE und skalierte Abschluss-BCE haben getrennte Skalen; dies sind keine geglätteten Epochenmittel oder Validierungskurven.</p><a href="curriculum-evidence/correction-loss.png"><img src="curriculum-evidence/correction-loss.png" alt="Vier getrennte Diagramme zeigen Replay- und Korrekturtraining für Aktions-MSE und skalierte Abschluss-BCE über drei Modellseeds." loading="lazy"></a></details>
<p><a href="trainings.html?category=robot&amp;method=il&amp;run=bc-approach-correction">Trainingsliste mit Komponenten-Losswerten ↗</a></p></section>
<section class="panel limits" id="current-conclusion"><p class="eyebrow">AKTUELLER ABSCHLUSS · REICHWEITE DER AUSSAGE</p><h2>Gezielte BC-Verbesserung für das zweite Anfahren</h2>
<p>Expertenkorrekturen aus den erreichten Eingangszuständen verbessern in diesem Versuchsaufbau den vollständigen Stapelerfolg, wenn die gelernten Aktionen und der gelernte Abschluss gemeinsam verwendet werden. Das ist eine Verbesserung durch Training auf neuen Bestätigungsstarts im selben Simulator.</p>
<p>Der Befund umfasst getrennte Aktions-/Abschlusskopien, den vorgegebenen Ausführungskontext und privilegierte Zustandsmerkmale. Eine einzelne gemeinsame MLP mit demselben Erfolg, ein Vorteil geordneter Curriculum-Präsentation, beliebige Turmhöhen, autonomes Paarplanen oder reale Hardware sind nicht nachgewiesen. Die Datenabdeckung für Rückzug und langes Open bleibt begrenzt.</p>
<p>Für diesen gezielten Abschluss ist kein weiterer Trainingslauf zwingend. Ein Curriculum-Nachweis würde dieselben Beispiele in gemischter und geordneter Reihenfolge vergleichen. Eine Verdichtung der getrennten Kopien und Übertragung auf andere Aufgaben wären weitere, eigenständige Untersuchungen.</p></section>'''
    page=(public/'curriculum.html').read_text(encoding='utf-8')
    page=re.sub(r'<!-- bc-conclusion:start -->.*?<!-- bc-conclusion:end -->','',page,flags=re.S)
    page=re.sub(r'<meta name="description" content="[^"]*">','<meta name="description" content="Gezielte BC-Korrekturen für das zweite Anfahren: Vorgehen, 118/150 neue Bestätigungserfolge und Grenzen des Curriculum-Nachweises.">',page)
    page=re.sub(r'<section class="hero">.*?</section>', '<section class="hero"><p class="eyebrow">FORSCHUNGSSTAND · 13. NOVEMBER 2026</p><h1>BC-Korrekturen für<br>das zweite Anfahren</h1><p class="lead">Gezielte Expertenkorrekturen verbessern den vollständigen Dreierturm-Erfolg auf neuen Bestätigungsszenen. Am wirksamsten ist die gemeinsame Verwendung neu gelernter Aktionen und Phasenabschlüsse.</p><div class="pills"><span>Simulation · privilegierte Zustände</span><span>3 Modellseeds · 50 gemeinsame Bestätigungsszenen</span><span>Curriculum-Vorteil nicht belegt</span></div></section><!-- bc-conclusion:start -->'+additions+'<!-- bc-conclusion:end -->',page,count=1,flags=re.S)
    page=page.replace('VORBEREITET · NOCH KEIN NEUER HAUPTLAUF','ABGESCHLOSSEN · A/B/C BEI 30K').replace('3 neue Modelle · 6 vorhandene','A: neu trainiert · B/C: wiederverwendet').replace('Neu zu trainieren · Seeds 1 / 2 / 3','Abgeschlossen · 40 / 28 / 26 je 100').replace('30k-Checkpoints geprüft und vorhanden','Abgeschlossen · 48 / 56 / 50 je 100').replace('30k-Checkpoints geprüft und vorhanden','Abgeschlossen · 48 / 56 / 50 je 100').replace('Geordnete Beispiele: X-lastig, dann XY, dann der vollständige Bewegungsumfang.','Geordnete Beispiele: X-lastig, dann XY, dann der vollständige Bewegungsumfang. Ergebnis: 52 / 42 / 46 je 100.')
    page=page.replace('Hauptmaß: vollständiger stabiler Dreierturm auf 100 neuen gepaarten Starts je Modell.','Ergebnis: B übertrifft A in allen drei Seeds; C übertrifft B nur in einem Seed. Hauptmaß: vollständiger stabiler Dreierturm auf 100 neuen gepaarten Starts je Modell.')
    page=re.sub(r'(?:Ergebnis: B übertrifft A in allen drei Seeds; C übertrifft B nur in einem Seed\. )+','Ergebnis: B übertrifft A in allen drei Seeds; C übertrifft B nur in einem Seed. ',page)
    page=re.sub(r'(?:Ergebnis: 52 / 42 / 46 je 100\. ?)+','Ergebnis: 52 / 42 / 46 je 100.',page)
    page=re.sub(r'(<h3>Curriculum-BC</h3>.*?<small>).*?(</small>)',r'\g<1>Abgeschlossen · 52 / 42 / 46 je 100\2',page,flags=re.S)
    page=page.replace('Es gibt noch keine A-Losskurve und keine neue korrigierte B/C-Zwischenkurve.','Die abgeschlossenen A/B/C-Endergebnisse stehen oben; diese historischen Kurven zeigen weiterhin nur den ursprünglichen B/C-Versuch.')
    page=re.sub(r'<section class="panel limits"><p class="eyebrow">GRENZEN DER AUSSAGE</p>.*?</section>','',page,flags=re.S)
    page=page.replace('Research Atlas · Stand 12.11.2026','Research Atlas · Stand 13.11.2026')
    (public/'curriculum.html').write_text(page,encoding='utf-8')
    for name in ('index.html','findings.html','trainings.html'):
        file=public/name;text=file.read_text(encoding='utf-8');text=re.sub(r'<aside class="bc-news" id="bc-current-status">.*?</aside>','<aside class="bc-news" id="bc-current-status"><strong>BC-Korrekturtraining · Stand 13.11.2026</strong><span>118/150 neue Bestätigungserfolge statt 85/150 bei B. Aktionen und Phasenabschluss gemeinsam gelernt; Curriculum-Vorteil nicht belegt.</span><a href="curriculum.html#bc-correction">Vorgehen, Ergebnisse und Grenzen ↗</a></aside>',text,flags=re.S);file.write_text(text,encoding='utf-8')
        if name=='trainings.html':file.write_text(re.sub(r'src="trainings\.js(?:\?[^"]*)?"','src="trainings.js?v=bc-20261113"',text),encoding='utf-8')
    old=read(evidence/'results.json');old['abc']=dict(status='completed',models=e['abc']['models'],seeds=[1,2,3],updates=30000,primary_scenes_per_model=100,interpretation='B>A in all seeds; C>B in one seed only; no consistent ordering advantage');old['updated']='2026-11-13';dump(evidence/'results.json',old)
    dashboard=read(public/'training-data/index.json');template=copy.deepcopy(next(r for r in dashboard['runs'] if r['id']=='bc-abc-30k'))
    for r in dashboard['runs']:
        if r['id']=='bc-abc-30k':r.update(title='BC · A/B/C-Vergleich abgeschlossen',description='A 40/28/26, B 48/56/50, C 52/42/46 je 100 Dreiertürme. Kein konsistenter Reihenfolgevorteil.',status='completed',stage='complete',results=old['abc'])
    for id,title,description,result in [
        ('bc-second-grasp','BC · Zweites Greifen: Experteneingriff','26/60 → 45/60 auf bekannten Entwicklungsszenen; 19 Gewinne, keine Verluste. Null Optimizer-Updates.',e['grasp']),
        ('bc-grasp-ablation','BC · Einzelphasen des zweiten Greifens','Nur Anfahren erreicht 45/60, ebenso die vollständige Expertenhilfe; 300 Episoden, keine Updates.',e['ablation']),
        ('bc-approach-correction','BC · Korrekturtraining zweites Anfahren','Neue Bestätigung: B 85/150, Replay 92/150, kombiniert 118/150. Getrennte Aktions-/Abschlusskopien; kein Curriculum-Vergleich.',e['training'])]:
        r=copy.deepcopy(template);r.update(id=id,title=title,description=description,status='completed',stage='complete',results=result,models=[],curves=[],parameters=None if id.endswith('correction') else 129955)
        r['architecture']=[['Vorfahr','PhaseNet B · 7 Phasenköpfe · Breite 128'],['Ausführung','Neue Ausgaben nur zweites Anfahren; sonst B'],['Komponenten','Getrennte Aktions-/Abschlusskopien' if id.endswith('correction') else 'Feste B-Gewichte mit begrenztem Experteneingriff']]
        r['config'].update(optimizer_updates=5000 if id.endswith('correction') else 0,dataset='Neue Korrekturen: 2069 train / 499 valid Frames; Split nach ganzen Szenen' if id.endswith('correction') else 'Bekannte Entwicklungsszenen; keine neuen Trainingslabels')
        r['checkpointInfo']='Zwölf fortsetzbare Komponenten; vollständige AdamW-, RNG- und Samplingzustände; lokale Kompositionskarten' if id.endswith('correction') else 'Unveränderte lokale B-30k-Modelle'
        if not id.endswith('correction'):
            r['models']=[dict(seed=seed,variant='B · feste Gewichte',step=30000,train=None,validation=None,positionMm=None,countAccuracy=None,recall10mm=None,bestValidation=None) for seed in (1,2,3)]
            r['lastStep']=0
        if id.endswith('correction'):
            env=read(RUNS/'approach_bc_correction_v1/ready_001/environment.json');r['runtime']={k:env[k] for k in ('gpu','torch','cuda')}
            status=read(RUNS/'approach_bc_correction_v1/ready_001/status.json');r['heartbeat']=datetime.fromtimestamp(status['updated_unix'],timezone.utc).isoformat();r['lastStep']=5000
            r['config'].update(loss='Getrennte Aktions-MSE bzw. 0,1 × gewichtete Abschluss-BCE; Loss-Skalen nicht als gemeinsame Kurve interpretieren',components=12,updates_per_component=5000,execution_gate='placement 2, phase 0, excluding retreat')
            for seed in (1,2,3):
                for source in ('replay','correction'):
                    for kind in ('actor','completion'):
                        folder=RUNS/f'approach_bc_correction_v1/ready_001/mixed_s{seed}_u30000_{source}_{kind}';points=read(folder/'loss.json');valid=read(folder/'validation.json')
                        r['models'].append(dict(seed=seed,variant=f'{source}-{kind}',step=5000,train=points[-1]['loss'],validation=valid['action_mse'] if kind=='actor' else .1*valid['completion_bce'],positionMm=None,countAccuracy=None,recall10mm=None,bestValidation=None))
                        for point in points:
                            r['curves'].append(dict(seed=seed,variant=f'{source}-{kind}',step=point['update'],epoch=None,train=point['loss'],validation=None,probe=None))
        assets=public/'training-assets'/id;assets.mkdir(exist_ok=True);dump(assets/'results.json',result);(assets/'README.md').write_text(report if id.endswith('correction') else description+'\n\nEntwicklungsszenen, keine Verbesserung durch Training; siehe curriculum.html.\n',encoding='utf-8')
        r['artifacts']=[dict(name='results.json',label='Messwerte und Grenzen',kind='document',url=f'/training-assets/{id}/results.json'),dict(name='README.md',label='Vorgehen und Einordnung',kind='document',url=f'/training-assets/{id}/README.md')]
        dashboard['runs']=[existing for existing in dashboard['runs'] if existing['id']!=id];dashboard['runs'].append(r)
    abcassets=public/'training-assets/bc-abc-30k';dump(abcassets/'results.json',old['abc']);(abcassets/'README.md').write_text('Abgeschlossen: A 40/28/26, B 48/56/50, C 52/42/46 je 100 Dreiertürme. B übertrifft A in allen drei Modellseeds, C übertrifft B nur in einem. Kein konsistenter Vorteil der Reihenfolge.\n',encoding='utf-8')
    dashboard['runs']=[repair_text(r) if r['id'].startswith('bc-') else r for r in dashboard['runs']]
    dashboard['generatedAt']=datetime.fromtimestamp(read(RUNS/'approach_bc_correction_v1/ready_001/status.json')['updated_unix'],timezone.utc).isoformat()
    (public/'training-data/index.json').write_text(json.dumps(dashboard,ensure_ascii=False)+'\n',encoding='utf-8')
    script=(public/'trainings.js').read_text(encoding='utf-8')
    script=script.replace("const prepared=r.id==='bc-abc-30k';","const prepared=r.id==='bc-abc-30k'&&r.status==='planned';")
    script=script.replace('geplanter A/B/C-Vergleich','abgeschlossener A/B/C-Vergleich')
    script=re.sub(r'/\* bc-correction-view:start \*/.*?/\* bc-correction-view:end \*/','',script,flags=re.S)
    extra="""/* bc-correction-view:start */
 if(r.id==='bc-approach-correction'){
  const t=r.results;
  $('summary').innerHTML=[['B-Vorfahren','3'],['Trainierte Komponenten','12'],['Updates je Komponente','5.000'],['Neue Bestätigungsstarts','50 · gemeinsam']].map(([k,v])=>`<div class="stat"><small>${k}</small><strong>${v}</strong></div>`).join('');
  $('panel-model').innerHTML=`<div class="grid"><article class="card"><h3>Getrennte BC-Komponenten</h3>${pairs(r.architecture||[])}<p>Je B-Vorfahr vier fortgesetzte Kopien. Nur die gesamte Phase-0-MLP lernt; übrige Phasen bleiben bitgleich. Neue Ausgaben werden nur beim zweiten Anfahren außerhalb des Rückzugs aktiviert.</p><p>Aktions- und Abschlusskopie werden separat trainiert. Die kombinierte Ausführung nutzt exakt dieselben Kopien und erhält keine weiteren Updates. Es ist kein Critic.</p></article><article class="card"><h3>Daten und Endpunkt</h3><p>40 Trainings- und zehn Validierungsfamilien versucht; tatsächlich 36 bzw. neun Familien enthalten. Ganze Ausgangsszenen bleiben über Controller und Frames in einem Split. 2.069 Trainings- und 499 Validierungsframes; zusätzlich ursprüngliches Phase-0-Replay.</p><p>Zwölf Komponenten, je 5.000 zusätzliche Updates. Fester Endpunkt; keine Best-of-Test-Auswahl. Bestätigung: 50 neue gemeinsame Starts je drei Modellseeds.</p></article></div><article class="card"><h3>Gespeicherter Trainingsvertrag</h3><pre>${esc(JSON.stringify(cfg,null,2))}</pre><p><a href="curriculum.html#correction-method">Vorgehen und Grenzen ↗</a></p></article>`;
  $('model-table').innerHTML=`<div class="table-wrap"><table><thead><tr><th>Modellseed</th><th>Komponente</th><th>Zusätzliche Updates</th><th>Train-Loss</th><th>Val-Metrik</th></tr></thead><tbody>${r.models.map(m=>`<tr><td>${esc(m.seed)}</td><td>${esc(m.variant)}</td><td>${fmt(m.step)}</td><td>${fmt(m.train,7)}</td><td>${fmt(m.validation,7)}</td></tr>`).join('')}</tbody></table></div><p class="muted">Aktionskopie: MSE. Abschlusskopie: Training 0,1 × gewichtete BCE, Validierung 0,1 × ungewichtete BCE. Protokollierte Batch-Losses, keine Epochenmittel; nicht über verschiedene Terme hinweg vergleichen. Keine Auswahl nach minimalem Validierungsloss.</p>`;
  const labels={baseline:'Ursprüngliches B',replay:'Replay-Fortsetzung',action:'Nur Aktionen',completion:'Nur Abschluss',combined:'Aktionen + Abschluss'};
  $('panel-geometry').innerHTML=['confirmation','development'].map(panel=>`<div class="card"><h3>${panel==='confirmation'?'Neue Bestätigung':'Bekannte Entwicklungsszenen'}</h3><p>${panel==='confirmation'?'50':'20'} gemeinsame Szenen × drei Modellseeds; keine unabhängigen Szenen über Modellseeds. Vollständiger Dreierturm für 50 strenge stabile Frames ohne Fingerkontakt.</p><div class="table-wrap"><table><thead><tr><th>Ausführung</th><th>Erfolge</th><th>Gewinne / Verluste gegen B</th><th>Gegen Replay</th></tr></thead><tbody>${Object.entries(t.aggregate[panel]).map(([p,v])=>`<tr><td>${esc(labels[p])}</td><td>${v.successes}/${v.n}</td><td>${t.paired[panel].baseline[p].gains} / ${t.paired[panel].baseline[p].losses}</td><td>${t.paired[panel].replay[p].gains} / ${t.paired[panel].replay[p].losses}</td></tr>`).join('')}</tbody></table></div></div>`).join('')+'<p><a href="curriculum.html#bc-correction">Seedwerte, Methode, Quellen und Aussagegrenzen ↗</a></p>';
 }
 /* bc-correction-view:end */
"""
    script=script.replace(' drawGeometry(r);drawChart();selectTab(tab);',extra+' drawGeometry(r);drawChart();selectTab(tab);')
    (public/'trainings.js').write_text(script,encoding='utf-8')


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--public',type=Path,required=True);args=parser.parse_args();e=measured();report=narrative(e)
    (HERE/'CONCLUSION_20261113.md').write_text(report,encoding='utf-8');dump(HERE/'reporting/conclusion_20261113.json',e);website(e,args.public,report)
    print('Exported measured conclusion, source hashes, selected BC dashboard entries and curriculum page.')
