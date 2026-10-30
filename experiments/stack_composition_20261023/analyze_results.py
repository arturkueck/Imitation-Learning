"""Post-run descriptive analysis; no training or checkpoint reselection."""
from pathlib import Path
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT=Path(__file__).resolve().parent
status=json.loads((OUT/'status.json').read_text())
curves={arm:[json.loads((OUT/f'{arm}_seed{s}/learning_curve.json').read_text()) for s in [1,2,3]] for arm in ['raw','relative']}
hashes={};episodes=0;diagnostics=[]
for f in sorted(OUT.glob('*_seed*/*.json')):
    if not (f.name.startswith('dev') or f.name=='test3.json'):continue
    d=json.loads(f.read_text());assert d['complete'] and d['n']==len(d['rows'])
    assert d['successes']==sum(r['success'] for r in d['rows'])
    episodes+=d['n']
    for r in d['rows']:
        key=(d['count'],r['seed']);assert hashes.setdefault(key,r['initial_sha256'])==r['initial_sha256']
    if d['count']==3:
        switched=[r for r in d['rows'] if r['second_skill_started']]
        diagnostics.append(dict(run=f.parent.name,evaluation=f.stem,n=d['n'],first_stack=len(switched),
            grasp_third_among_switched=sum(r['grasp'][2] for r in switched),lift_third_among_switched=sum(r['lift'][2] for r in switched),success=d['successes']))
train_seconds=sum(c[-1]['training_and_checkpoint_seconds'] for cs in curves.values() for c in cs)
result=dict(state=status['state'],wall_seconds=status['elapsed_seconds'],training_and_checkpoint_seconds=train_seconds,
    completed_evaluation_episodes=episodes,paired_initial_hashes_match=True,diagnostics=diagnostics,
    final_dev2={arm:[c[-1]['dev2'] for c in cs] for arm,cs in curves.items()})
(OUT/'analysis.json').write_text(json.dumps(result,indent=2))

fig,axes=plt.subplots(1,2,figsize=(12,4.5))
colors={'raw':'#777777','relative':'#007a8a'}
for arm,cs in curves.items():
    x=np.array([r['effective_epochs'] for r in cs[0]])
    ys=np.array([[r['dev2']*100 for r in c] for c in cs])
    for y in ys:axes[0].plot(x,y,color=colors[arm],alpha=.35,lw=1,marker='.')
    axes[0].plot(x,ys.mean(0),color=colors[arm],lw=2.5,marker='o',label=f'{arm}: Mittel aus 3 Trainingsseeds')
axes[0].axhline(90,color='#b53a40',ls='--',lw=1,label='90%-Ziel')
axes[0].set(xlabel='Datenpass-Aequivalente (Sampling mit Zuruecklegen)',ylabel='Stabile Zweierstapel [%]',ylim=(-3,103),title='Entwicklung: 20 identische Starts je Modell')
axes[0].legend(fontsize=8);axes[0].grid(alpha=.15)
test=[r for r in diagnostics if r['evaluation']=='test3']
labels=['Erster Stapel /\nzweite Fertigkeit','C gegriffen*','C angehoben*','Dreierturm stabil']
for i,r in enumerate(test):
    values=[r['first_stack'],r['grasp_third_among_switched'],r['lift_third_among_switched'],r['success']]
    bars=axes[1].bar(np.arange(4)+(i-.5)*.36,values,.36,label=r['run'],color=['#007a8a','#6cb4ba'][i])
    axes[1].bar_label(bars,padding=2,fontsize=9)
axes[1].set(xticks=np.arange(4),xticklabels=labels,ylim=(0,105),ylabel='Episoden von jeweils 100',title='Getrennter Dreier-Test: kein erfolgreicher Turm')
axes[1].legend(fontsize=8);axes[1].grid(axis='y',alpha=.15)
fig.text(.52,.015,'* Unter Episoden mit Paarwechsel; Ereignisse, keine kausalen Fehlerlabels.',fontsize=8)
fig.tight_layout(rect=(0,.045,1,1));fig.savefig(OUT/'evaluation_summary.png',dpi=160);plt.close(fig)

lines=['# Auswertung vom 23.10.2026','',
'**Das Ziel ist nicht erreicht.** Die relative Darstellung verbessert den beobachteten Zweier-Erfolg, aber keiner der ausgewerteten Versuche erzeugte einen stabilen Dreierturm.',
'',f"Der begrenzte Pilot wurde technisch erfolgreich nach {status['elapsed_seconds']/60:.2f} Minuten beendet (00:32 bis ca. 01:10:53 Uhr Europe/Berlin). Acht Stunden waren eine Obergrenze; der feste Versuchsplan war vorher abgearbeitet. Es fand keine achtstuendige iterative Methodensuche statt. Sechs Modelle wurden je 30.000 Updates trainiert, insgesamt 180.000 Updates. Training inklusive Checkpoints beanspruchte laut Instrumentierung {train_seconds/60:.2f} Minuten; der Rest der Gesamtzeit entfiel ueberwiegend auf Simulation, daneben Datenladen und Prozessaufwand.",
'','![Lernkurven und Testdiagnose](evaluation_summary.png)','',
'## Zweier-Erfolg bei 30.000 Updates','',
'Entwicklungsdaten: je 20 identische Starts, keine unabhaengigen abschliessenden Zweier-Tests.','',
'| Darstellung | Seed 1 | Seed 2 | Seed 3 | Mittel |',
'|---|---:|---:|---:|---:|',
'| Absolut (raw) | 50% | 60% | 65% | 58,3% |',
'| Relativ | 80% | 85% | 70% | 78,3% |','',
'Gepaarte Unterschiede: +30, +25, +5 Prozentpunkte, Mittel +20. Alle drei Seeds zeigen dieselbe Richtung. Das ist ein positives Entwicklungssignal, kein breiter statistischer Ueberlegenheitsnachweis. Die historische grosse Direct-Baseline ist wegen anderer Architektur, Skalierung, EMA und Erfolgskriterien nicht direkt vergleichbar.',
'','## Dreier-Test und Uebergang','',
'| Modell | Ausgewaehlte Updates | Erste Paarplatzierung / 100 | C gegriffen* | C angehoben* | Stabiler Dreierturm |',
'|---|---:|---:|---:|---:|---:|']
for r in test:
    updates=30000 if r['run'].endswith('1') else 10000
    lines.append(f"| {r['run']} | {updates} | {r['first_stack']} | {r['grasp_third_among_switched']} | {r['lift_third_among_switched']} | 0/100 |")
lines+=['',
'* Greif-/Lift-Ereignisse innerhalb der Episoden, die zur zweiten Fertigkeit wechselten. Die gespeicherten Flags sind episodische Ereignisse; sie zeigen keine detaillierte zeitliche Abfolge oder eindeutige Fehlerursache. Lift bedeutet C-z > 0,88 m.',
'',
'Pro getesteter Policy: Wilson-95%-Intervall fuer 0/100 etwa [0%, 3,7%]. Die beiden Modelle verwenden dieselben 100 Szenen, deshalb nicht als 200 unabhaengige Trainingsreplikate interpretieren. Fuer relative Seed 3 und alle raw-Seeds wurde das vorab definierte 80%-Zweiergate verfehlt; daher keine 100er-Testserie. Ihre kleinen abschliessenden Dreierdiagnosen waren ebenfalls ohne Erfolg. Fehlende Haupttests sind nicht mit gemessenen 0/100 gleichzusetzen.',
'',
'Bei relative Seed 2 waren alle Dreier-Entwicklungsraten null. Die festgelegte Gleichstandsregel waehlte deshalb den frueheren Checkpoint bei 10.000 Updates, obwohl die spaetere 30.000er-Policy im Entwicklungstest C oefter griff (15/20 statt 8/20). Diese Regel war reproduzierbar, aber bei durchgehend null Enderfolg wenig aussagekraeftig fuer Teilfortschritte. Keine nachtraegliche Neuauswahl anhand der Testdaten.',
'','## Was wir ueber Lerneffizienz sagen koennen','',
'30.000 Updates mit Batch 8 entsprechen 8,784 Datenpass-Aequivalenten. Relative Seed 2 erreicht bereits bei 10.000 Updates (2,928 Aequivalente) 85% Zweier-Erfolg; die anderen Seeds erreichen am Ende 80% und 70%. Kein Seed erreicht die 90%-Zweierschwelle, kein Modell die Dreierschwelle. Eine Einsparung von Epochen bis zu 90% Dreier-Erfolg ist deshalb nicht nachgewiesen. Der sinkende Validierungsloss allein waere eine irrefuehrende Erfolgsmeldung.',
'','## Fehlerinterpretation und naechster sinnvoller Versuch','',
'Die Modelle erreichen den Paarwechsel in 80 beziehungsweise 81 der 100 Dreierszenen. Die Fehler liegen somit nicht ausschliesslich vor dem ersten Stapel. Viele Episoden zeigen auch Greifen/Anheben des dritten Wuerfels. Ob danach die Hoehenextrapolation, der Transport, das Absenken, Loslassen, eine Kollision oder der Zerfall des unteren Stapels entscheidend ist, laesst sich aus den vorhandenen Endmetriken nicht kausal entscheiden. Es wurden keine vollstaendigen Rollout-Zeitreihen oder Videos dieses Nachtlaufs gespeichert.',
'',
'Prioritaet fuer eine Fortsetzung: feste Entwicklungsstarts mit den vorhandenen Checkpoints erneut abspielen und Positionen, Aktionen, Kontakte sowie Greiferstatus pro Schritt protokollieren. Dann den kontinuierlichen B→A→C-Ablauf gegen einen separat initialisierten Test der zweiten Platzierung auf einem vorgebauten Zweierstapel diagnostisch vergleichen. Der vorgebaute Stapel zaehlt niemals als vollstaendiger Taskerfolg und liefert keine Trainingslabels. Damit kann man Uebergangsprobleme und Hoehen-/Platzierungsprobleme besser trennen, bevor eine gezielte Architektur- oder Datenrepraesentationsaenderung getestet wird. Ein Training mit laengerer Historie ist eine pruefbare Hypothese fuer den Uebergang, keine belegte Loesung.',
'',
'Weiterhin nur Zwei-Wuerfel-Demos fuer Training verwenden. Neue Recovery- oder erhoehte Zieldemos waeren ein veraendertes Datenprotokoll und muessen separat ausgewiesen werden. Nicht einfach das Updatebudget erhoehen und daraus eine Generalisierungsloesung erwarten. Die bereits angesehenen 100 Teststarts gelten fuer spaetere Methodenentwicklung als verbraucht; fuer einen neuen Endnachweis neue, vorab fixierte Starts verwenden.',
'','## Nachpruefung','',
f'- {episodes} abgeschlossene Evaluationsrollouts aus den gespeicherten JSON-Dateien nachgezaehlt, Erfolgszaehler mit Einzelzeilen abgeglichen.',
'- Initialzustand-Hashes bei gleichen Aufgaben und Seeds ueber alle Modelle/Checkpoints identisch.',
'- Alle sechs Lernkurven enthalten die vier vorgesehenen Checkpoints bis 30.000 Updates.',
'- Auswertung fuehrt kein neues Training und keine Test-basierte Modellwahl durch.',
'- Detailzahlen: [analysis.json](analysis.json); urspruengliche automatische Tabelle: [RESULTS.md](RESULTS.md).']
(OUT/'AUSWERTUNG.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(result,indent=2))
