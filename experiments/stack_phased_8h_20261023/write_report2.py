"""Reproducible tables/figure for the agent's final interpretation."""
import json,math
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from method import digest
P=Path(__file__).resolve().parent
def read(p):return json.loads(p.read_text())
def main():
    final=read(P/'final_test/status.json');assert final['state']=='COMPLETE'
    ab=read(P/'retreat_ablation/status.json');assert ab['state']=='COMPLETE'
    selected=read(P/'final_test/selection.json')['models'];stats=[read(P/b/'status.json') for b in ['block1','block2']]
    trace=read(P/'final_trace_analysis.json');onset=read(P/'final_lower_onset.json')
    intervals={}
    for seed in [1,2,3]:
        r=final['results'][str(seed)];assert r['n']==100 and r['complete'];k=r['successes'];z=1.96;n=100;p=k/n;d=1+z*z/n
        c=(p+z*z/(2*n))/d;e=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d;intervals[str(seed)]=[c-e,c+e]
        assert digest(selected[str(seed)]['path'])==selected[str(seed)]['sha256']
    fig,axes=plt.subplots(1,2,figsize=(11,4.5));xs=[1,2,3]
    axes[0].bar(xs,[final['results'][str(s)]['successes'] for s in xs],color=['#007a8a','#69aeb7','#a7cdd1'])
    axes[0].axhline(90,color='red',ls='--',label='90%-Ziel');axes[0].set(xticks=xs,xlabel='Trainingsseed',ylabel='Stabile Dreiertuerme / 100',ylim=(0,100),title='Unabhaengige Teststarts, eingefrorene Auswahl');axes[0].legend()
    for i,s in enumerate(xs):
        r=ab['results'][str(s)];axes[1].bar(i-.18,r['without_retreat']['successes'],.36,color='#888888',label='Ohne Rueckzug' if i==0 else None);axes[1].bar(i+.18,r['with_retreat'],.36,color='#007a8a',label='Mit Rueckzug' if i==0 else None)
    axes[1].set(xticks=[0,1,2],xticklabels=xs,xlabel='Trainingsseed',ylabel='Stabile Dreiertuerme / 10',ylim=(0,10),title='Gleiche Gewichte, gepaarte Entwicklungsstarts');axes[1].legend()
    fig.tight_layout();fig.savefig(P/'final_results.png',dpi=160);plt.close(fig)
    lines=['# Bericht 2: Zweiter Trainingsblock und Abschlussanalyse','',
    '**Das90%-Ziel ist verfehlt.** Die drei final ausgewaehlten Modelle erreichen62/100,48/100 und50/100 stabile vollstaendige Dreiertuerme auf den reservierten neuen Starts84000–84099. Alle300 Episoden sind vollstaendig. Die Modelle wurden vor dem ersten Test anhand der Entwicklung ausgewaehlt, kopiert und gehasht; nach Testbeginn keine Optimierung oder Modellauswahl. Die drei Modelle verwenden dieselben100 Szenen, also keine300 unabhaengigen Trainingsreplikate.',
    '', '![Ergebnisse](final_results.png)','',
    '| Seed | Ausgewaehlte kumulative Updates | Entwicklung | Neuer Test | Wilson95%-Intervall |',
    '|---|---:|---:|---:|---|']
    for s in xs:
        info=selected[str(s)]['selection'];lo,hi=intervals[str(s)];k=final['results'][str(s)]['successes'];lines.append(f"| {s} | {info['update']} | {round(info['dev3']*10)}/10 | {k}/100 | [{lo:.1%}, {hi:.1%}] |")
    lines+=['', '## Zwei Trainingsbloecke und Zeitbilanz','',
    '| Seed | Block1 Updates insgesamt | Block2 Ausgangscheckpoint | Zusaetzliche Block2 Updates | Kumulativ nach Block2 |',
    '|---|---:|---:|---:|---:|']
    for s in xs:
        init=read(P/'block2'/f'seed{s}'/'initialization.json')['initial_update'];end=stats[1]['updates'][str(s)];lines.append(f"| {s} | {stats[0]['updates'][str(s)]} | {init} | {end-init} | {end} |")
    lines+=['',
    f"Block1: {stats[0]['elapsed_seconds']/3600:.3f}h Prozesslaufzeit, {sum(stats[0]['train_seconds'].values())/60:.1f}min gemessene Optimierung insgesamt. Block2: {stats[1]['elapsed_seconds']/3600:.3f}h Prozesslaufzeit, {sum(stats[1]['train_seconds'].values())/60:.1f}min Optimierung insgesamt. Der Rest entfiel vorwiegend auf Simulation und Auswertung. Block2 lief rund2h56min statt voller3–4h: die verspaetete Zwischenanalyse kostete Zeit. Die urspruengliche Deadline16:19:19 Uhr Berliner Zeit wurde nicht verlaengert. Nicht alle in Block1 trainierten Updates liegen auf dem Elternpfad der ausgesuchten Block2-Modelle, weil fruehere best-Checkpoints statt latest fortgesetzt wurden.",
    '', 'Block1-Bestwerte:4/10,7/10,5/10. Block2-Bestwerte:6/10,8/10,7/10. Das sind ausgewaehlte Werte auf wiederholten Entwicklungsstarts, kein unverzerrter Nachweis einer allgemeinen Verbesserung. Fuer Block1 wurde kein gleich grosser unabhaengiger Endtest auf denselben reservierten Starts nachgeholt. Die Behauptung einer gesicherten Testverbesserung von Block1 zu Block2 waere deshalb nicht gedeckt.',
    '', '## Was bewirkt der eingefuegte Rueckzug?','',
    'Ausfuehrungsablation nach Abschluss aller Tests auf ausschliesslich alten Entwicklungsstarts: identische final eingefrorene Gewichte, identische zehn Initialzustand-Hashes, gleicher Erfolgstest und gleiche Schwelle. Einziger variierter Faktor ist die Wiederverwendung des gelernten offenen Anflugkopfes als zusaetzliche Rueckzugsphase. Es werden keine Testresultate fuer diese Diagnose zurueck ins Training gegeben.',
    '', '| Seed | Ohne Rueckzug | Mit Rueckzug | Gewonnene Starts | Verlorene Starts |','|---|---:|---:|---:|---:|']
    for s in xs:
        r=ab['results'][str(s)];lines.append(f"| {s} | {r['without_retreat']['successes']}/10 | {r['with_retreat']}/10 | {len(r['gained_with_retreat'])} | {len(r['lost_with_retreat'])} |")
    lines+=['',
    'Damit ist auf diesen Szenen ein positiver Ausfuehrungseffekt des Rueckzugs sichtbar (+2,+1,+4 Erfolge); bei Seed1 gehen zugleich zwei zuvor geloeste Starts verloren. Das ist ein lokaler gepaarter Entwicklungsbefund. Drei Seeds und zehn wiederverwendete Szenen erlauben keine breite Signifikanzbehauptung. Die zusaetzliche niedrigere Trainingslernrate wurde nicht separat randomisiert; der gesamte Blockvergleich isoliert ihren Einfluss nicht.',
    '', '## Verbleibender Fehlermechanismus','',
    '| Seed | Erste stabile Paarplatzierung | Zweite Fertigkeit begonnen | Fehlschlaege am Ende in zweiter Phase6 |',
    '|---|---:|---:|---:|']
    for s in xs:
        r=trace[str(s)];lines.append(f"| {s} | {r['first_stack']}/100 | {r['second_started']}/100 | {r.get('failed_end_stage2_phase6',0)} |")
    lines+=['',
    'Die erste Platzierung ist auf neuen Szenen mit98/100,98/100 und96/100 sehr zuverlaessig. Der Engpass ist weiterhin die Komposition nach der ersten Platzierung. Bei30/46/46 Fehlschlaegen steht die Policy am Ende in Phase6 des zweiten Paars; ein Endphasenlabel allein identifiziert jedoch nicht den Entstehungszeitpunkt.',
    '',
    'Alle300 Testzeitreihen wurden auf endliche Werte geprueft und der Erfolg aus mindestens50 durchgehenden valid3-Frames erneut berechnet. Fuer jeden fehlgeschlagenen Versuch mit erstem Stapel wurde der erste Verlust der unteren A/B-Geometrietoleranz nach dem Erfolg der ersten Paarplatzierung untersucht, einschliesslich Rueckzugszeit. Bei den Seeds1/2/3 liegt dieser erste Verlust in31/45/16 Faellen waehrend Phase0 des zweiten Paars, in2/2/6 waehrend Phase1, in0/1/14 waehrend Phase2 und in0/0/1 waehrend Phase6. Bei3/2/9 bleibt die untere Geometrie innerhalb der Toleranz. Fuer diese Zaehler ist eine kurzzeitige Verletzung hinreichend; sie beweist weder irreversiblen Kollaps noch eine konkrete Kontaktkraftursache.',
    '',
    'Der Rueckzug verbessert einzelne Uebergaenge, verhindert die Stoerung des unteren Turms bei der folgenden Anflug-/Greifbahn aber nicht verlaesslich. Es bleiben auch Fehler mit erhaltener unterer Geometrie, die Platzierung, Freigabe, Kontakt oder Stabilitaet des dritten Wuerfels betreffen. Die Hypothese eines ausschliesslichen Hoehenproblems ist deshalb zu eng; ebenso waere eine reine Loslasskorrektur unzureichend.',
    '', '## Was ist gelernt, was ist vorgegeben?','',
    'Trainiert wurden sieben aktions- und abschlussvorhersagende Koepfe ausschliesslich aus den180 Zwei-Wuerfel-Trainingsdemos;20 Demos blieben Validierung. XYZ-/Greiferaktionen sind gelernt. Fest vorgegeben sind Phasenreihenfolge, Wahl der Paare, die zusaetzliche Wiederholung von Kopf0 beim Rueckzug, Objektauswahl/Anker sowie ein physisches Stabilitaetsgate. Rotationsaktionen bleiben wie alle Trainingslabels null. Privilegierte Objektpositionen und Simulator-Kontaktchecks werden verwendet. Es ist keine autonome Planung und kein neu aus Daten erlernter Rueckzugspfad. Dieses Strukturwissen muss bei jeder IL-Generaliserungsaussage genannt werden.',
    '',
    'Die Ergebnisse zeigen reale, aber begrenzte Komposition gelernter Bewegungen zu drei Wuerfeln ohne Drei-Wuerfel-Trainingsdemos. Sie zeigen weder90% Zuverlaessigkeit noch weniger Epochen bis zu diesem Ziel. Mit phasenbalanciertem Sampling, Batch64 und teils frueheren Elterncheckpoints sind historische uniforme Batch8-Epochen nicht direkt vergleichbar.',
    '', '## Entscheidung und Artefakte','',
    'Beide autorisierten Trainingsbloecke und beide Berichte sind abgeschlossen. Kein dritter Trainingslauf. Als naechste wissenschaftliche Untersuchung bietet sich eine kontrollierte Anflugbahn-/Freiraumdiagnose an: Wo beruehren Roboter oder bewegter Wuerfel den bestehenden Turm, und hilft eine klar ausgewiesene Bahnstruktur? Erst danach eine gezielte neue Methode. Die hier bereits gesehenen84000er Teststarts gelten bei weiterer Entwicklung als verbraucht; ein spaeterer Endnachweis benoetigt neue reservierte Starts.',
    '',
    'Belege: REPORT_1.md, block1_trace_diagnosis.json, block2_trace_diagnosis.json, final_trace_analysis.json, final_lower_onset.json, final_test/selection.json und seed*_test3.json sowie saemtliche NPZ-Zeitreihen; retreat_ablation/results.json enthaelt die gewonnenen/verlorenen Starts. Hashes der drei finalen Modelle wurden erneut mit der vor Testbeginn gespeicherten Auswahl abgeglichen. Beide Trainingsprozesse endeten mit Returncode0. Prozessende des Coordinators und Freigabe seiner Wachhaltesperre werden im Abschlusscheck separat verifiziert.']
    (P/'REPORT_2.md').write_text('\n'.join(lines),encoding='utf-8')
    (P/'final_verification.json').write_text(json.dumps(dict(test_complete=True,episodes=300,success_recomputed=True,finite_traces=True,checkpoint_hashes_match=True,intervals=intervals),indent=2))
if __name__=='__main__':main()
