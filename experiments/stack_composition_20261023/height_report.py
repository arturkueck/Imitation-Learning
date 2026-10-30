"""Descriptive paired height-ablation report."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from pathlib import Path

OUT=Path(__file__).resolve().parent
DEST=OUT/'height_ablation'

def main():
    data=json.loads((DEST/'results.json').read_text());status=json.loads((DEST/'status.json').read_text())
    assert status['state']=='COMPLETED' and len(data)==75
    cases=[('relative_seed1',30000),('relative_seed2',10000),('relative_seed2',30000)]
    heights=[0,1,2,3,4];groups=[];paired=[]
    for c,u in cases:
        baseline={r['seed']:r for r in data if (r['case'],r['update'],r['height_cm'])==(c,u,0)}
        for h in heights:
            rows=[r for r in data if (r['case'],r['update'],r['height_cm'])==(c,u,h)]
            assert len(rows)==5
            g=dict(case=c,update=u,height_cm=h,n=5)
            for k in ['success','grasp','lift','near','placed','release','target_displaced']:g[k]=sum(r[k] for r in rows)
            groups.append(g)
            p=dict(case=c,update=u,height_cm=h,lost=0,gained=0)
            for r in rows:
                assert r['paired_hash']==baseline[r['seed']]['paired_hash']
                p['lost']+=int(baseline[r['seed']]['success'] and not r['success'])
                p['gained']+=int(not baseline[r['seed']]['success'] and r['success'])
            paired.append(p)
    (DEST/'analysis.json').write_text(json.dumps(dict(groups=groups,paired_vs_zero=paired),indent=2))
    fig,axes=plt.subplots(1,2,figsize=(12,4.7))
    colors=['#007a8a','#d18b18','#7955a6']
    for (c,u),color in zip(cases,colors):
        gs=[g for g in groups if (g['case'],g['update'])==(c,u)]
        axes[0].plot(heights,[g['success']*20 for g in gs],marker='o',lw=2,color=color,label=f'{c}, {u//1000}k')
    axes[0].set(title='Stabile Platzierung je Checkpoint (5 Starts)',xlabel='Zusaetzliche Zielhoehe [cm]',ylabel='Erfolg [%]',ylim=(-5,105),xticks=heights)
    axes[0].legend(fontsize=8);axes[0].grid(alpha=.2)
    for key,label in [('grasp','Gegriffen'),('lift','Angehoben'),('near','XY <3 cm nach Lift'),('placed','Kontakt am Ziel'),('success','Stabil')]:
        axes[1].plot(heights,[sum(g[key] for g in groups if g['height_cm']==h) for h in heights],marker='o',label=label)
    axes[1].set(title='Diagnoseereignisse (15 Modell-Start-Kombinationen)',xlabel='Zusaetzliche Zielhoehe [cm]',ylabel='Anzahl',ylim=(-.5,15.7),xticks=heights)
    axes[1].legend(fontsize=8);axes[1].grid(alpha=.2)
    fig.tight_layout();fig.savefig(DEST/'height_results.png',dpi=160);plt.close(fig)
    lines=['# Kontrollierte Hoehenablation','',
    '23.10.2026. 75 abgeschlossene Policyrollouts: drei vorhandene Checkpoints, fuenf identische Entwicklungsstarts, fuenf Zielhoehen. Zusaetzlich zwei Experten-Positivkontrollen. Keine Trainingsupdates, keine neuen Demonstrationen fuer das Training.',
    '', '**Hauptbefund:** Bei +2, +3 und +4 cm gab es fuer keinen der drei Checkpoints einen stabilen Erfolg (je Hoehe 0/15 Modell-Start-Kombinationen). Bei 0 cm waren es 8/15, bei +1 cm 6/15. Alle acht bei 0 cm erfolgreichen Modell-Start-Kombinationen scheitern bei jeder der Hoehen ab +2 cm. Die Hoehenintervention reicht in diesen gepaarten Faellen aus, den Erfolg zu verlieren; ein vorausgehender Paarwechsel ist dafuer nicht erforderlich.',
    '', 'Das ist eine lokale experimentelle Beobachtung, keine universelle 2-cm-Grenze: Es wurden nur fuenf Startzustaende und drei Checkpoints aus zwei Trainingsseeds untersucht. Im Bereich zwischen +1 und +2 cm wurde keine feinere Schwelle gemessen. Der feste Sockel aendert seine exponierte Geometrie mit der Hoehe.',
    '', 'Der Einbruch beginnt nicht ausschliesslich beim Greifen. Bei +2 cm wird der bewegte Wuerfel noch in 10/15 Faellen angehoben und in 8/15 bis auf 3 cm an das Ziel gebracht, aber nur 2/15 erreichen kurz das definierte Kontakt-/Positionskriterium und keiner stabilisiert es. Bei +4 cm werden nur noch 6/15 angehoben. Eine Methode muss daher sowohl Zielpositionierung/Stabilisierung als auch die zunehmende Beeintraechtigung frueherer Phasen adressieren.',
    '', '![Hoehenkurven](height_results.png)',
    '', '## Stabile Platzierungen','',
    '| Checkpoint | +0 cm | +1 cm | +2 cm | +3 cm | +4 cm |',
    '|---|---:|---:|---:|---:|---:|']
    for c,u in cases:
        vals=[next(g['success'] for g in groups if (g['case'],g['update'],g['height_cm'])==(c,u,h)) for h in heights]
        lines.append(f'| {c}, {u} Updates | '+' | '.join(f'{v}/5' for v in vals)+' |')
    lines+=['','Die Checkpoints von Seed 2 sind keine unabhaengigen Trainingsreplikate. Fuenf Starts pro Modell und Hoehe sind eine Entwicklungsdiagnose; gepoolte Zaehler sind keine 15 unabhaengigen Modellreplikate.',
    '', '## Teilereignisse','',
    '| Hoehe | Gegriffen | Angehoben | XY <3 cm nach Lift | Kontakt am Ziel | Stabil |',
    '|---|---:|---:|---:|---:|---:|']
    for h in heights:
        vals=[sum(g[k] for g in groups if g['height_cm']==h) for k in ['grasp','lift','near','placed','success']]
        lines.append(f'| +{h} cm | '+' | '.join(f'{v}/15' for v in vals)+' |')
    lines+=['','## Gepaarter Vergleich gegen 0 cm','',
    '| Checkpoint | Hoehe | Bei 0 cm erfolgreich, jetzt Fehler | Bei 0 cm Fehler, jetzt erfolgreich |',
    '|---|---:|---:|---:|']
    for p in paired:
        if p['height_cm']:lines.append(f"| {p['case']} / {p['update']} | +{p['height_cm']} cm | {p['lost']} | {p['gained']} |")
    lines+=['','## Was wurde kontrolliert?','',
    'Eine Zwei-Wuerfel-Umgebung mit einem 4×4 cm breiten, kinematisch festen Sockel unter dem Ziel. Der Sockel reicht bei 0 cm bis zur Tischoberflaeche; bei groesseren Hoehen wird er zusammen mit dem Ziel nach oben verschoben. Beide Wuerfel bleiben dynamisch. Ziel und Quelle haben je 4 cm Kantenlaenge.',
    '', 'Jeder Start wird zunaechst bei 0 cm fuer 40 Schritte mit offenem, neutral angesteuertem Greifer beruhigt. Danach werden ausschliesslich Zielposition und Sockelhoehe veraendert. Alle anderen qpos/qvel sind bytegenau gleich (Hashvergleich), ebenso Objekt-XY, Quellhoehe und Zielorientierung. Vor dem ersten Policy-Schritt wird die Beobachtung aktualisiert. Es gibt keinen Paarwechsel und keine vorherige gelernte Platzierung.',
    '', 'Alle Bedingungen haben dasselbe Budget von 1.000 Steuerschritten bei 20 Hz. Erfolg erfordert 50 aufeinanderfolgende gueltige Frames: Ziel auf Sollhoehe, Wuerfelkontakt, XY <9 mm, vertikaler Abstand 40 mm ±8 mm, kein Grasp/Greiferkontakt, geringe Geschwindigkeiten und bei erhoehtem Ziel Kontakt zum Sockel. Diese Zielhoehen-erweiterte Metrik ist kein unveraenderter historischer Benchmarkscore.',
    '', 'Der programmierte Experte loeste je einen separaten Kontrollstart bei 0 und 4 cm. Dies prueft die grundsaetzliche Loesbarkeit an den Endpunkten, nicht eine garantierte Expertenrate fuer alle Szenen.',
    '', '## Grenzen und Einordnung','',
    'Der Vergleich kontrolliert die Ausgangspose deutlich strenger als der vorherige vorbereitete Dreierstapel. Zielhoehe und sichtbare/kollidierbare Sockelhoehe aendern sich jedoch gemeinsam. Der feste Sockel ist stabiler als ein frei gestapelter unterer Wuerfel. Deshalb ist das eine Intervention an der Zielhoehe samt physischer Unterstuetzung, kein Beweis eines rein neuronalen Hoehenfeatures und kein Dreier-Erfolgstest.',
    '', 'Die 0-cm-Bedingung hat einen beruhigten Roboterstart und einen Sockel unter dem Ziel. Ihr Score muss deshalb nicht dem urspruenglichen Zweier-Benchmark entsprechen. Nichtmonotone Ergebnisse oder einzelne erfolgreiche erhoehte Starts schliessen eine universelle scharfe Versagenshoehe aus.',
    '', 'Die Datenbasis enthaelt Ziel-minus-Quellhoehen bis ca. +0,89 cm, alle Demostarts liegen bei 0 cm Differenz. Bereits +1 cm verlaesst diesen beobachteten Bereich leicht. Eine nachtraeglich aus diesen fuenf Hoehen gewaehlt wirkende Schwelle muss als explorativ bezeichnet werden.',
    '', 'Artefakte: protocol.json (fixiertes Design und Spaltenschema), results.json (Einzelfaelle), analysis.json (gepaarte Zaehler), expert_checks.json, status.json und NPZ-Zeitreihen. Alle Checkpoint-Hashes vor/nach dem Lauf identisch. Bestehende Modelle und Trainingsdaten wurden nicht veraendert.']
    (DEST/'REPORT.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(groups,indent=2))

if __name__=='__main__':main()
