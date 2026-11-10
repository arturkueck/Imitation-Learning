# Richtungsentscheidung: criticgestützte Selbstimitation

Am05.11.2026 hat der Nutzer den Schwerpunkt auf Nachahmungslernen mit
Bewertung beziehungsweise Gewichtung eigener Erfahrungen befürwortet.
Diese Entscheidung startet kein neues Training und ändert keine bestehenden
Versuche. Das Ziel bleibt wissenschaftliche Relevanz, keine vorgegebene
Verbesserungszahl oder nachträgliche Auswahl günstiger Checkpoints.

## Actor und Bewertungsmodul trennen

Der Actor lernt ausschließlich Aktionsnachahmung auf tatsächlich vorhandenen
Beispielen. Sein Bewegungs-Loss ist gewichteter Behavior-Cloning-Fehler:

`L_actor = mean(w_i * ||pi(x_i, phase_i) - a_i||²)`.

Es gibt keinen direkten `-Q(s,pi(s))`-Term und keinen Gradientenpfad vom
Bewertungsmodul in die frei gewählte Actoraktion. Die Beispiele können
Originaldemonstrationen und separat geprüfte eigene Erfahrungen enthalten.
Ein Bewertungsmodul liefert Auswahl/Qualitätsgewichte als abgetrennte Labels.
Ein auf Rewards/Returns trainierter Bewerter macht das Gesamtverfahren weiterhin
zu einer Verbindung von IL und RL; der Actorupdate ist dabei Nachahmungslernen.
Ein überwacht gelernter Abschnittsqualitätsbewerter ist nicht automatisch ein
Q-Critic. Diese Begriffe werden nach dem tatsächlich gewählten Lernziel benannt.

Die vorhandenen Critics aus den Actor-Critic-Pilots werden nicht ungeprüft als
Gewichtsgeber eingesetzt: Die Gegenfaktualprüfung hat Fehlbewertungen auch
innerhalb der zulässigen Actoraktionen nachgewiesen.

## Vorhandene Evidenz berücksichtigen

Im separaten älteren Partial-Self-Imitation-Pilot
`experiments/self_imitation/partial_self_imitation_20261104/run_001/RESULTS.md` ergibt die
Aggregation über drei Parents und je50 Starts:

| Variante | Erfolg /150 |
|---|---:|
| Unveränderte Parents | 90 |
| Originalexperten-BC, Arm A | 88 |
| Erfolgreiche eigene Episoden, Arm B | 93 |
| Zusätzlich bestätigte Fehlversuchabschnitte, Arm C | 92 |
| Exakt C-Samples mit handdefinierten Gewichten, Arm D | 90 |

Der damalige Pilot belegt keinen Vorteil der Qualitätsgewichtung. Er benutzt
andere Bedingungen als die jüngeren Actor-Critic-Pilots; absolute Erfolgszahlen
dürfen nicht als direkter Methodenvergleich gegeneinander gestellt werden.
Die damaligen Endtestfamilien werden nicht für die neue Auswahl oder neue
Checkpointbewertung wiederverwendet.

`diagnosis_004/REPORT.md` zeigt außerdem nur rund1.3 % akzeptierte
Fehlversuchbeispiele unter allen Actorbeispielen. Ein neuer Versuch muss die
tatsächliche Abdeckung, Phasenverteilung und effektiven Gewichtsanteile prüfen,
statt aus dem Vorhandensein weniger solcher Abschnitte eine starke Nutzung
der Idee abzuleiten. Qualitätsgates werden nicht nachträglich gelockert.

## Nächster abgegrenzter Schritt: Bewerterprüfung vor Actortraining

1. Einen festen Pool geeigneter Erfahrungen samt tatsächlicher Messlabels
   inventarisieren. Controller-/Datenversionen getrennt halten; vorhandene
   fehlgeschlagene RL-Policies nicht pauschal nachahmen. Anfangs können vollständig
   erfolgreiche Episoden verwendet werden. Partielle Fehlversuchabschnitte kommen
   erst nach unabhängiger Prüfung ihrer lokalen Gültigkeit dazu.
2. Das Qualitätsziel vorab festlegen: Welche gemessene Eigenschaft soll ein
   Gewicht ausdrücken und weshalb sollte deren Nachahmung die Aufgabe verbessern?
   Lokale geometrische Ruhe, zukünftiger Gesamterfolg und Episodenschwierigkeit
   sind unterschiedliche Größen. Sie dürfen nicht zu einem beliebigen Score
   vermischt werden. Ein lernbarer Proxy für bereits direkt verfügbare Messwerte
   benötigt eine Begründung gegenüber dem unmittelbaren Messscore.
3. Bewerter anhand gemessener Folgen trainieren und auf vollständig getrennten
   Startfamilien prüfen. Vor allem nachvollziehbare Qualitätsreihenfolgen und
   die Vermeidung hoher Gewichte für nachweislich schädliche Beispiele messen;
   gute Train-MSE alleine reicht nicht. Kein automatischer Anspruch, dass der
   derzeit vorhandene Q-Critic dafür geeignet ist.
4. Für Actor-Trainingsfamilien Gewichte familienweise außerhalb des jeweiligen
   Bewerter-Trainingsfolds berechnen (Cross-Fitting). Gewichte abtrennen,
   normieren, ihre Verteilung und den effektiven Einfluss je Phase dokumentieren.
   Validierungs-/Endtestdaten erzeugen keine Actortrainingsbeispiele oder -gewichte.

Erst bei einem informativen, vorab festgelegten Prüfergebnis wird ein neuer
Actorvergleich vorbereitet. Die Prüfung vom 05.11.2026 ist in
`scorer_check_001/REPORT.md` dokumentiert: historische Kriterien bestanden,
Übertragung auf den Controller mit Retreat-Guard wegen unzureichender negativer
Familien und verschlechterter Kalibrierung nicht freigegeben. Kein Actortraining
wurde gestartet. Bewerterprotokoll, Datenmanifest und feste Prüfschwellen liegen
in `scorer_check_001`; die eingefrorene Transferprüfung in `scorer_transfer_001`.

Die Folgeprüfung am aktuellen Controller ist inzwischen abgeschlossen:
`scorer_guarded_recovery_001/REPORT.md`. Auf 240 Trainings- und 200 getrennten
Validierungsversuchen wurden die unveränderten lokalen Prüfschwellen erfüllt
(190 geeignete Validierungsfamilien, davon 20 mit negativen Labels; MLP-AUC
0,9712, Brier 0,0510 gegenüber konstant 0,0953). Alle 440 Trajektorienhashes und
die Familientrennung wurden zusätzlich geprüft. Der historische Bewerter wurde
nicht nachträglich als übertragen erklärt; es handelt sich um einen neuen Fit
auf passenden Trainingsdaten. Kein Actortraining und kein Gewichtsexport.

Die lokale Bewertung erfasst nur einen Teil der Aufgabenfehlschläge: 12/40
Fehlschläge im neuen Validierungspanel enthalten ein negatives Anflugfenster.
Keine geeignete Validierungsfamilie hat beide Labels. Der folgende BC-Vergleich
muss deshalb sowohl die lokale Wirkung als auch die vollständige Aufgabenerfüllung
messen; eine Verbesserung der Actorgewichte bleibt eine offene Hypothese.

## Danach: kausal auswertbarer BC-Vergleich

| Arm | Actortraining |
|---|---|
| A | Originaldemonstrationen, gleiche Updatezahl |
| B | Originale plus festgelegter eigener Datenpool, gleich gewichtet |
| C | Exakt B-Samples, Gewichte aus direkt messbarem Referenzscore |
| D | Exakt B-Samples, Gewichte des geprüften gelernten Bewerters |

B/C/D erhalten dieselben Samples und denselben Samplerstrom. Damit wird
Gewichtung nicht mit einer anderen Datenauswahl verwechselt. Auswahl wäre
später ein eigener Faktor. Architektur, Controller, Phasenentscheidungen,
Optimizerbudget, Seeds und Evaluationsstarts bleiben zwischen den Armen
vergleichbar. Die Kosten der Datengewinnung und des Bewertertrainings werden
zusätzlich ausgewiesen. Ein unveränderter Parent bleibt als Referenz erhalten.

Gewinne werden auf frischen gepaarten Startfamilien mit mehreren Trainingsseeds
geprüft. Der erste Vergleich ist Entwicklung, eine spätere Bestätigung verwendet
weitere unberührte Familien. Änderungen an Gewichten oder Gates nach Betrachtung
der Endtests sind ausgeschlossen.

## Wissenschaftliche Frage

**Verbessert eine nachweislich zuverlässige gelernte Bewertung eigener
Demonstrationsabschnitte das Nachahmungslernen gegenüber denselben Daten ohne
Gewichtung und gegenüber direkt berechenbaren Gewichten?**

Eine Kombination bekannter Bausteine ist noch kein eigenständiger Beitrag.
Literaturabgrenzung, Ablationen und Grenzen der Übertragbarkeit müssen geprüft
werden, bevor Neuheit oder Wirksamkeit behauptet werden. Auch ein negatives
Ergebnis wird unverändert berichtet; der Ansatz wird nicht allein zur Erreichung
einer gewünschten Prozentzahl umbenannt oder nachjustiert.
