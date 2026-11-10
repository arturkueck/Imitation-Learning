from pathlib import Path
import json,math,datetime
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
out=Path(__file__).resolve().parent;a=json.loads((out/'final_analysis.json').read_text());prefix=json.loads((out/'five_cube_endtest_analysis.json').read_text())
# Restore per-teacher identity, including separate C_seed1/2/3 under the same folder.
for name in a['datasets']:
 rows=json.loads((out/'datasets'/name/'manifest.json').read_text())['rows'];teachers={}
 for r in rows:
  key=r['teacher']+' / '+r['split'];d=teachers.setdefault(key,dict(attempts=0,successes=0));d['attempts']+=1;d['successes']+=int(r['success'])
 a['datasets'][name]['teachers']=teachers
(out/'final_analysis.json').write_text(json.dumps(a,indent=2))
fig,axes=plt.subplots(1,2,figsize=(11,4.2),layout='constrained')
x=np.arange(3)
for offset,arm,color,label in [(-.18,'curriculum','#2b7a78','Curriculum: ausgewählte Dreiermodelle'),(.18,'direct','#de8f05','Unveränderte Parents')]:
 vals=[a['final'][f'{arm}_seed{i}_n5']['successes'] for i in [1,2,3]];axes[0].bar(x+offset,vals,width=.34,color=color,label=label)
 for xx,v in zip(x+offset,vals):axes[0].text(xx,v+.6,f'{v}/100',ha='center',fontsize=9)
axes[0].set(xticks=x,xticklabels=['Seed 1','Seed 2','Seed 3'],ylim=(0,100),ylabel='Vollständig stabile Fünfertürme (%)',title='Reservierter Endtest: kein erkennbarer Vorteil')
axes[0].axhline(90,color='#aa4444',ls='--',lw=1);axes[0].text(-.48,92,'90%-Ziel je Seed',fontsize=9,color='#aa4444');axes[0].legend(fontsize=7,loc='upper right')
for i,color in zip([1,2,3],['#216e68','#5ca891','#9bcbb0']):axes[1].plot([2,3,4,5],prefix[f'curriculum_seed{i}_n5']['ever_stable_prefix10'],'o-',color=color,label=f'Seed {i}')
axes[1].set(xticks=[2,3,4,5],ylim=(0,105),xlabel='Größe des Turmpräfixes im Fünfer-Rollout',ylabel='Mindestens 10 Frames jemals stabil /100',title='Fehler akkumulieren vor der letzten Platzierung');axes[1].legend(fontsize=8)
fig.suptitle('Gemessener Pilot · kein Fünfertraining gestartet · Präfixstabilität ist nicht Enderfolg',fontsize=11)
fig.savefig(out/'measured_results.png',dpi=180);fig.savefig(out/'measured_results.svg');plt.close(fig)
# Actual tables, avoiding unsupported pooled significance claims.
lines=['| Modell/Seed | 2 Würfel | 3 Würfel | 4 Würfel | 5 Würfel |','|---|---:|---:|---:|---:|']
for arm,label in [('curriculum','Curriculum'),('direct','Parent/Kontrolle')]:
 for i in [1,2,3]:lines.append('| '+f'{label} {i}'+' | '+' | '.join(f"{a['final'][f'{arm}_seed{i}_n{n}']['successes']}/{a['final'][f'{arm}_seed{i}_n{n}']['attempts']}" for n in [2,3,4,5])+' |')
table='\n'.join(lines)
phase=['| Seed | 2er-Präfix ≥10 Frames | 3er-Präfix | 4er-Präfix | 5er-Präfix | 5er-Enderfolg ≥50 Frames |','|---|---:|---:|---:|---:|---:|']
for i in [1,2,3]:d=prefix[f'curriculum_seed{i}_n5'];phase.append(f"| {i} | "+' | '.join(map(str,d['ever_stable_prefix10']))+f" | {d['successes']} |")
steps=sum(d['steps'] for d in a['cost'].values());episodes=sum(d['episodes'] for d in a['cost'].values())
updates=60000;eq=updates*64/27322;selectedeq=30000*64/27322
text=f'''# Fünferturm-Pilot: vertiefte Auswertung

Stand:24.10.2026, Agentanalyse nach vollständigem Prozessabschluss. **90%-Ziel klar verfehlt. Kein Vorteil des realisierten Curriculum-Pfads erkennbar.** Alle24 vorgesehenen Endtestreihen wurden vollständig ausgeführt, insgesamt1500 Episoden. Der geplante Vergleich zweier tatsächlich auf Fünfern trainierter Methoden kam wegen der vorab festgelegten Gates nicht zustande. Der Pilot ist abgeschlossen; dies ist kein erfolgreicher Abschluss des Fünfer-Lernziels.

## Gemessene Endergebnisse

{table}

![Gemessene Resultate](measured_results.png)

Die Bezeichnung Curriculum meint hier die eingefrorenen, nach zusätzlichem Dreiertraining ausgewählten Modelle. Alle Viererkandidaten wurden verworfen. Der Direktarm blieb wegen zu weniger erfolgreicher Fünferdaten bei seinen unveränderten Parentgewichten. Deshalb zeigt die Tabelle **Dreierfortsetzung gegen Parent**, keinen budgetgleichen Vergleich zweier Fünfertrainingsverfahren.

Auf denselben100 reservierten Fünferstarts pro Modellseed liegen die Differenzen bei−3,+1,−1 Prozentpunkten. Gepaarte unterschiedliche Ausgänge:Seed1 Curriculum-only0/Parent-only3;Seed2 2/1;Seed3 0/1. Die Initialzustandshashes stimmen jeweils paarweise überein. Deskriptiv20/300 gegenüber23/300 Erfolge; diese Poolzahl ist wegen gemeinsamer Starts und nur drei Lernreplikaten kein unabhängiger300-Seed-Nachweis. Auch auf Dreiern ist der im Entwicklungsset sichtbare Gewinn im Endtest nicht konsistent:−2,+1,+2 Erfolge je50. Kein Endtest wurde für neue Modellwahl oder Optimierung verwendet.

## Warum das Training früher endete

Ausgangs-Dreiergate:Seed1 34/50, Bestätigung29/50;Seed2 31/50, Bestätigung28/50;Seed3 27/50 ohne Bestätigungsversuch. Zunächst bestand kein Parent das doppelte60%-Gate.

Nach30.000 neuen Dreierupdates pro Seed:37/50 mit31/50 Bestätigung,33/50 mit29/50 Bestätigung,28/50 ohne Bestätigung. NurSeed1 durfte als Teacher zum Sammeln von Vierern dienen. Das Gate beweist nicht, dass alle drei Modelle60% schaffen; es war ein praktisches Sammelgate auf Entwicklung, kein Konfidenzbeweis.

Die Vierersammlung lieferte27/100 erfolgreiche Trainingsepisoden und8/20 erfolgreiche Validierungsepisoden, erfüllte also das Datengate. Nach weiteren30.000 Updates pro Seed erzielten die Kandidaten13/50,13/50,10/50. Ihre direkten Dreier-Parentgewichte erzielten15/50,13/50,12/50. Bei Gleichstand blieb ebenfalls der Parent. Damit wurden alle Viererkandidaten verworfen; ihre Updates und Kosten bleiben dennoch Teil der Bilanz. Die ausgewählten Modelle lagen auf Vierern bei15/50,13/50,12/50 und verfehlten das30/50-Gate deutlich. Die Curriculum-Fünfersammlung und das120.000-Update-Fünfertraining wurden deshalb nicht betreten.

Die direkte Fünfersammlung mit den ursprünglichen drei Parents ergab6/100 erfolgreiche Trainingsepisoden und3/20 erfolgreiche Validierungsepisoden. Das Minimum20 Trainingserfolge wurde verfehlt. Kein direkter180.000-Update-Trainingslauf wurde gestartet. Dies ist ein Datenverfügbarkeitsbefund; seine Erfolgsrate ist nicht0/100. Die spätere Parent-Endtestrate beträgt5er10/7/6 von100.

## Echte Updates, Auswahl und Lernkurven

Alle sechs Produktionsläufe haben tatsächlich30.000 Updates:je drei auf Dreier- und Viererdaten. Latest- und Best-Gewichte stimmen innerhalb eines Laufs überein; die Auswahl prüfte nur den abgeschlossenen Endcheckpoint gegen seinen Parent. Best bedeutet hier **kein** fortlaufend in Simulation gesuchtes Optimum. Die protokollierten10k-Zwischenpunkte enthalten nur Offlinevalidierung; ein früherer besserer Rolloutcheckpoint wurde nicht untersucht.

Optimizerzustände und endliche Gewichte wurden geprüft; maximale Adam-Schrittzahl jeweils30.000. Die L2-Änderungen gegenüber dem Parent liegen auf Dreiern bei1,677/1,610/2,328 und auf Vierern bei1,233/1,392/2,207: Es fanden echte Modellupdates statt. Alle aufgezeichneten Losses sind endlich. Kleine Action-MSE-Werte reichen nicht als Nachweis für lange stabile Türme. Insbesondere Seed3 besitzt weiterhin viele falsche Phasenabschlussvorhersagen im ursprünglichen Validierungsset; auch diese Offlinewerte erklären den Rollouterfolg nicht allein.

Pro Seed wurden60.000 zusätzliche Updates mit Batch64 bezahlt, entsprechend{eq:.2f} Originaldatenpass-Äquivalenten bei27.322 Originaltrainingsframes. Die ausgewählten Modelle enthalten nur die erste30.000-Update-Fortsetzung, entsprechend{selectedeq:.2f} Äquivalenten. Über alle Seeds180.000 Updates und11,52Mio verarbeitete Batchbeispiele. Bei50% Originalmasse beträgt die tatsächliche Originalexposition je Seed etwa70,27 Originaldatenpässe; die140,55-Zahl normiert dagegen sämtliche Mischbeispiele auf die Originalgröße. Keine dieser Zahlen ist eine klassische Epoche über den wachsenden gemischten Datensatz. Historische Vortrainingskosten sind zusätzlich und wurden hier nicht erneut bezahlt. Zwei5-Update-Techniksmokes werden separat geführt.

## Wo die Fünfer-Rollouts scheitern

Die vollständigen Ereigniszusammenfassungen aller100 Starts je Seed zeigen:

{chr(10).join(phase)}

Jede Präfixzahl bedeutet, dass das gesamte jeweilige untere Präfix irgendwann mindestens10 Frames gültig war. Das ist weder eine isolierte Platzierungsgenauigkeit noch garantierter späterer Turmerhalt. Trotz93–99 kurzzeitig gültiger Zweiertürme bleiben nur20–28 gültige Viererpräfixe und5–9 gültige Fünferpräfixe übrig. Der Verlust tritt also über mehrere Paarwechsel auf, nicht ausschließlich bei der fünften Freigabe. Beim Curriculum scheitern in der letzten aktiven Paarstufe2/3/4 jeweils33/38/21 Episoden fürSeed1,33/39/19 fürSeed2 und40/33/15 fürSeed3; zusätzlich1/1/7 in Stufe1. Das sind Endzustandskategorien, keine nachgewiesenen kausalen Fehlerursachen.

Nur die ersten zwei festgelegten Endtestepisoden pro Modell wurden als vollständige Zeitreihe archiviert. In allen sechs untersuchten Verläufen auf Start365000 verliert das untere Zweierpräfix innerhalb40 Schritten nach dem ersten Paarwechsel mindestens einmal die strenge Gültigkeit. Auf365001 treten bei mehreren Modellen zusätzliche Gültigkeitsverluste nach späteren Wechseln auf. Diese gepaarten12 gespeicherten Verläufe stützen eine Übergangsdiagnose, erlauben aber keine repräsentative Fehlerrate für alle600 Episoden. Gültigkeitsverlust kann Bewegung, Kontakt oder Geometrie bedeuten; er wird nicht automatisch als dauerhafter Einsturz bezeichnet.

Eine belastbare Millimeterverteilung der letzten Platzierung für alle erfolgreichen Endtests ist mit nur zwei gespeicherten Zeitreihen pro Modell nicht nachträglich rekonstruierbar. Das globale Kriterium verlangtXY≤9mm zwischen jedem Nachbarpaar sowie40mm±8mm Höhendifferenz, reale Kontakte, niedrige Geschwindigkeiten und keine Fingerkontakte über50 Frames. Erfolgsquoten sind vollständig gemessen, feinere Platzierungsverteilungen fehlen. Es wurden dafür keine reservierten Tests erneut abgespielt.

## Daten, Controller und Kosten

Neu gesammelt wurden360 feste Episoden mit450.331 Simulations-Steuerschritten. Entwicklung und Gates kosteten1250 Episoden/1.030.356 Schritte; reservierte Endtests1500 Episoden/1.765.223 Schritte. Zusammen{episodes} Episoden und{steps:,} Steuerschritte. Wiederholte Entwicklungs-/Gatestarts zählen als reale Kosten, jedoch nicht als zusätzliche unabhängige Starts. Die technische Episode399001 (685 Schritte) sowie vorbereitete reine Physiktests und historische Demos sind in dieser Hauptbilanz ausgeschlossen.

Sessionstart23.10.21:17:08UTC, Workerabschluss24.10.02:46:26UTC, Supervisorabschluss02:46:28UTC; Gesamtzeit einschließlich Vorbereitung etwa{a['elapsed_hours']:.2f}h. Die12h waren eine Obergrenze, kein Auftrag, nach negativen Gates weitere unlimitierte Versuche zu erzeugen. GPU-Kernzeit und Energie wurden nicht gemessen; die Angabe ist reale Sessiondauer einschließlich Simulation und Tests. Die Fristen07:17:08UTC für Training und09:17:08UTC gesamt wurden eingehalten.

Architektur und10 Eingaben blieben unverändert:EEF-Ankerdifferenz, Orientierung, Fingerpositionen und Phasenzeit. Sieben BC-Phasen erzeugen Aktionen und Abschlusswahrscheinlichkeit. Ein externer Sequencer wählt Quell-/Zielwürfel und wartet auf freigegebenes stabiles Präfix; ein gelernter Phase0-Rückzug wird zwischen Paaren wiederverwendet. Das System ist damit ein explizit komponierter Controller mit gelernten Teilaktionen. Der restliche Turm ist kein expliziter Policyinput. Alle Ergebnisse enthalten bereits erfolgreiche eigene Dreierdaten aus der Vorgängersession; kein Beleg für reine Zero-shot-Generalisation aus ausschließlich Zweiertraining.

Die Datensatzprüfung steht in DATASET_REPORT.md. Original-HDF5-SHA256:{a['original_sha256']}. Original, eingefrorene Quellen, Arrays, Parentmanifest und alle sechs ausgewählten Gewichte sind erneut hashgeprüft. Split-/Pre-action-Audits für alle360 Dateien wurden in den stündlichen Checks abgeschlossen. Supervisor und Worker sind beendet; keine Session-Pythonprozesse mehr vorhanden, Wachhaltesperre bestätigt freigegeben(process_closeout.json).

## Konsequenz für die Hypothese und nächsten Versuch

Die Idee, bei60% Gesamtleistung erfolgreiche eigene Daten zu sammeln, ist als Datenerzeugung plausibel, hat hier aber den Aufstieg nach vier Würfeln nicht ermöglicht. Die universelle Behauptung „pro Würfel kurz weitertrainieren, danach nur den Fünfer lange trainieren“ wird durch diesen Pilot nicht gestützt. Eine allgemeine Überlegenheit oder Untauglichkeit von Curricula ist damit ebenfalls nicht bewiesen: Es fehlt der realisierte trainierte Fünfervergleich, und der getestete Actor sieht den unteren Turm nicht explizit.

Ein nächster vorab registrierter Versuch sollte zuerst auf **Viererleistung und Erhalt des unteren Turms bei Paarwechseln** zielen. Getrennt vergleichen:unveränderter Actor mit gezielter Auswahl erfolgreicher höherer Übergänge gegen einen neuen Actor mit Turm-/Freirauminformation. Architekturwechsel wäre ein eigener Methodenfaktor und braucht eine neue Baseline. Für reine Self-Imitation bleibt die Erfolgsfilterung erhalten; seltene erfolgreiche Endepisoden liefern jedoch keine Abdeckung gescheiterter Wiederherstellung. Ohne neue Information oder zusätzliche erfolgreiche Zustandsabdeckung garantiert längeres Kopieren eigener Aktionen keinen Gewinn.

Completionfehler und Rückzugs-/Transportverhalten zunächst auf **neuen Entwicklungsstarts** mit vollständigen Zeitreihen untersuchen; danach kleinen budgetgleichen Trainingsvergleich und2/3/4-Regression, erst bei bestätigtem Vierergate erneut auf fünf aufsteigen. Die jetzt benutzten Endtestbereiche sind dauerhaft für Optimierung gesperrt. Ein strenger kausaler Curriculumvergleich braucht auf beiden Armen tatsächlich verfügbare Daten und angeglichene bezahlte Updates/Sammelschritte oder muss Blockaden explizit als Resultat ausweisen. Ein Vergleich mit RL ohneIL wurde nicht implementiert; eine Epochenersparnis gegenüberRL bleibt unbekannt.

Kein weiterer Lauf wurde gestartet. Maschinell prüfbare Details:final_analysis.json, five_cube_endtest_analysis.json, dataset_audit_*.json, source_hashes.json und agent_checks.jsonl. Der automatische Rohbericht ist unverändert als RESULTS_AUTOMATIC.md erhalten.
'''
(out/'RESULTS.md').write_text(text,encoding='utf-8')
lines=['# Datensatzbericht — abgeschlossen','', 'Alle drei vorab begrenzten Sammlungen vollständig, keine zusätzliche Curriculum-Fünfersammlung nach gescheitertem Vierergate. Nur stabile vollständige Episoden als Actorziele, keine neuen Skriptexpertenaktionen. Originalsplit180/20 Demos bleibt unverändert.','', '| Sammlung | Versuche Train/Valid | Erfolge Train/Valid | akzeptierte Frames Train/Valid |','|---|---:|---:|---:|']
for name,d in a['datasets'].items():lines.append(f"| {name} |100/20|{d['successes']['train']}/{d['successes']['valid']}|{d['frames']['train']}/{d['frames']['valid']}|")
lines+=['','## Herkunft und Auswahlbias','']
for name,d in a['datasets'].items():
 lines.append('### '+name)
 for key,v in d['teachers'].items():lines.append(f"- {key}: {v['successes']}/{v['attempts']} vollständig erfolgreich")
lines+=['','Alle Fehlschläge bleiben mit vollständigen Pre-action-Inputs archiviert; im Training werden ausschließlich erfolgreiche Episoden verwendet. Das bevorzugt leichtere Starts und erfolgreiche Aktionssequenzen. Zyklische Teacherzuordnung vor Ergebnissen, aber keine Gleichverteilung der akzeptierten erfolgreichen Teacherbeiträge garantiert. Vierer-Teacher ist ausschließlich das bestätigte neue DreiermodellSeed1; daraus folgt kein Gatebestehen der anderen Lernseeds. Die9 erfolgreichen direkten Fünferepisoden werden wegen nur6 Trainingserfolgen nicht für ein Training verwendet.','', '## Integrität, Splits und Labels','', 'Alle360 Episoden wurden im Collector auf exakte Einzelbild-Aktionsreproduktion des jeweiligen Teachers geprüft. Unabhängige Dateiaudits in den stündlichen Kontrollen prüften endliche Werte, genaue Post-/Pre-action-Verkettung, Rekonstruktion der10 Modelleingaben, Nullrotationen und Übereinstimmung von Erfolgsflag und mindestens50 durchgängigen stabilen Frames. Initialzustandshashes innerhalb jeder Höhe Train/Valid disjunkt. Technikepisode399001 und vorbereitete Türme sind keine Trainingsdaten.','', 'Neue Sammlung:3er215000–215099 Training,215100–215119 Validierung;4er220000–220099/220100–220119;direkte5er275000–275099/275100–275119. Entwicklung310000+1000*N+[0,49], Bestätigung320000+1000*N+[0,49], reservierte Tests360000+1000*N+[0,99] für5 bzw.[0,49] sonst. Keine alten84000/85000/125000/126000-Endtests als neue Trainingsdaten. Bereits vorhandener3er-Replay stammt aus der vorigen explizit freigegebenen Sammlung, deren Manifest ebenfalls eingefroren ist.','', 'Batch64 enthält32 Originalexpertframes,16 frühere Höhen und16 neue Höhe; phasen-/episodenbalanciert. Frühere Höhen werden zunächst gleichverteilt gewählt. Auf dieser Session wurden nur3er/4er-Optimierungen ausgeführt. Neue y-Abschlussflags sind Teacher-Pseudolabels zur Diagnose; BCE lernt ausschließlich Originalexpertlabels. Kein RL.','', '## Dateien und unveränderte Quellen','', 'NPZ enthält x,a,p,y,phase_steps,anchor,stage,retreat,pre_obs,post_obs,pre_state,initial,prob,valid2,valid,prefix_valid,velocities,contacts,fingers,controller_event. Manifest enthält Seed,Höhe,Split,Erfolg,Frames,Teacherpfad/-hash,Initialzustandshash und Pfad. Daten sind Zustands-/Aktionsdaten, keine neuen RGB-Demos. Alle vollständigen Sammlungen bleiben unter datasets/ mit model.xml und manifest.json.','', 'Original-HDF5-SHA256:'+a['original_sha256']+'. Quellen-/Arrays-/Parentmanifest-Hashes und Teacherhashes am Abschluss erneut geprüft. Detailaudits:dataset_audit_n3.json,dataset_audit_n4.json,dataset_audit_direct_n5.json; vollständige Herkunft und Kosten in final_analysis.json.','', 'Die ursprünglichen Zweiwürfeldaten und historischen Vortrainingskosten bleiben notwendig; der aktuelle Versuch enthält bereits eigene Dreierdaten und ist kein Nachweis ausschließlich aus Zweierdaten. Vollständige Endergebnisse und Grenzen stehen in RESULTS.md.']
(out/'DATASET_REPORT.md').write_text('\n\n'.join(lines),encoding='utf-8')
print(json.dumps(dict(reports=['RESULTS.md','DATASET_REPORT.md'],main_episodes=episodes,main_steps=steps,original_equivalents_paid_per_seed=eq)))
