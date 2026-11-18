# Präregistriertes Protokoll v2: Zustandsherkunft zusätzlicher BC-Labels

Revision vom 17.11.2026 auf Nutzerauftrag, **vor jedem wissenschaftlichen Start**.
V1 bleibt erhalten und wird durch diese Vorbereitung ersetzt. V2 verwendet
neue wissenschaftliche Szenenbereiche. Technische Fixtures sind als solche
bekannt; ihre Ergebnisse werden niemals als Forschungsbefund verwendet.

Deadline bleibt **18.11.2026, 09:00 Europe/Berlin**; Workerlimit 08:58,
anschließend harter Abbruch des eigenen Prozessbaums. Kein automatischer
Neustart, keine Budgetverlängerung, keine PC-Abschaltung. Fertigstellung
beendet den Lauf auch früher. Vorbereitung ist kein wissenschaftlicher Start.

## 1. Abgegrenzte Methodenfrage

**Verbessert BC aus Expertenlabels an lernerbesuchten Zuständen die vollständige
Aufgabe stärker als aus neuen Expertenlabels nach Expertenabläufen, wenn
verwendete Labels, Updates und Ausführung kontrolliert sind? Überträgt sich
dies auf einen Parent, der keine Sammelzustände geliefert hat?**

Die untersuchte Intervention ist ausschließlich die Herkunft der neuen
Zustände. Phase 0 der zweiten Platzierung ist aufgrund der bereits
abgeschlossenen Diagnose festgelegt. Ihre Auswahl wird hier nicht neu gelernt.
`targeted` bedeutet in diesem Code **Lerner-Präfix**, nicht automatische
Auswahl der schwierigsten Fehler. `standard` bedeutet **Experten-Präfix**.
Damit wird weder eine neue allgemeine Engpassauswahl noch ein Curriculum-
Reihenfolgevorteil, Critic-Nutzen oder wissenschaftliche Neuheit nachgewiesen.

**H1:** Die Anpassung mit Lerner-Präfix-Daten erhöht den vollständigen stabilen
Dreierturm-Erfolg gegenüber Experten-Präfix-Daten auch beim jeweils nicht
zur Sammlung verwendeten Parent. Fallender Offline-Loss erfüllt H1 nicht.

| Arm | Zusätzliche Updates/Daten | Aktion und Abschluss im Zielkontext |
|---|---|---|
| baseline | keine | ursprüngliches B |
| replay | alte Phase-0-Beispiele | fortgesetzte getrennte Kopien |
| standard | neue Experten-Präfix-Beispiele plus alte Beispiele | fortgesetzte getrennte Kopien |
| targeted | neue Lerner-Präfix-Beispiele plus alte Beispiele | fortgesetzte getrennte Kopien |

Einziger konfirmatorischer Kontrast: **targeted minus standard auf den drei
sammlungsfremden Parents**. Replay und B dienen zusätzlichen Regressions-
Kontrollen. Die anderen sechs Datenblock/Parent-Kombinationen sind deskriptiv;
sie dürfen einen verfehlten Hauptnachweis nicht ersetzen.

## 2. Sammlung ohne Daten des jeweiligen Zielcontrollers

| Datenblock | Gesperrt für Sammlung; Parent des Haupttests | Sammelcontroller |
|---|---|---|
| data_1 | B-Seed 1 | B-Seeds 2 und 3 |
| data_2 | B-Seed 2 | B-Seeds 1 und 3 |
| data_3 | B-Seed 3 | B-Seeds 1 und 2 |

Je Block: 120 neue Trainings- und 30 neue Validierungsfamilien. Ein Collector
pro Familie wird vor Datenerhebung balanciert und deterministisch zufällig
zugeteilt: je 60 Trainings-/15 Validierungsversuche pro Collector. Der
Zielparent liefert auch keine neuen Validierungszustände. Ganze Szenenfamilien
bleiben mit sämtlichen Frames und Quellen in genau einem Split. Alle drei
Trainingsparents sehen innerhalb eines Blocks denselben neuen Datenpool.
Die Parents teilen ihre ursprünglichen Demonstrationen; sie sind keine
neuen Aufgaben oder völlig unbekannten Modellarchitekturen.

Jede Familie erzeugt zwei echte Abläufe aus identischem Anfangszustand:
Targeted beginnt mit dem zugeteilten BC-Collector und übernimmt beim zweiten
Anfahren den unveränderten Experten; Standard verwendet den Experten auch
im Präfix bis zur selben Phase. Danach gilt dieselbe Expertenregel. Kein
Teleportieren, Eingriff in Kontakte oder künstliches Erfolgslabel. Die
Reihenfolge der beiden Abläufe wird vorab ausbalanciert.
Der Präfixwechsel verändert gemeinsam Pose, Kontaktkontext, Dauer und
gegebenenfalls Guard-Nutzung. Ein Effekt dieses Erhebungsprotokolls isoliert
keines dieser Merkmale als alleinigen Wirkmechanismus.

## 3. Eignung, Ausfälle und Budget

Gemeinsame Aufnahme ausschließlich bei regulär erreichter und abgeschlossener
Zielphase in beiden Quellen. Die Aufnahme hängt nicht vom späteren
Dreierturm-Erfolg ab. Zulässige Ausfälle: zweites Anfahren nicht erreicht,
Präfix-/Rückzugs-Timeout oder Expertenphasen-Timeout. Unbekannte Fehler
brechen ab. Keine Ersatzfamilien und kein Nachsammeln bis zum Bestehen.

Je Paar werden min(32, beide Phasenlängen) unterschiedliche Frames benutzt:
ein terminales Abschlusslabel und gleichmäßig verteilte nichtterminale
Frames. Beide Arme besitzen damit dieselben Familien, Labelzahlen und
Abschlusslabelquoten. Die spätere Zufallsauswahl ist **familiengleich**:
zuerst eine Familie gleichverteilt, dann eines ihrer ausgewählten Frames.
Längere Phasen gewinnen keine zusätzliche Samplingmasse. Dieselben
Familien-/Framepositionen gelten für Standard und Targeted sowie für
Aktions- und Abschlusskopie.

Abdeckung vor Training: mindestens 60/120 Trainings- und 15/30
Validierungsfamilien je Block; zusätzlich mindestens 40 % gemeinsam geeignete
Familien von jedem Collector in jedem Split. Sonst Abbruch statt veränderter
Stichprobe. Alle Versuche, Ausschlussgründe und Quoten je Collector werden
berichtet. Dieses Training untersucht damit ausdrücklich die gemeinsame
geeignete Teilpopulation; es löst keine vorangegangenen Präfixfehler.

**Gleiches Budget verwendeter Lernlabels ist keine gleiche Zahl abgefragter
Expertenaktionen.** Vollständige Phasen und Experten-Präfixe benötigen mehr
Abfragen als die verwendete Teilmenge. Erzeugte Labels, Expertenaufrufe,
Kosten der verworfenen Versuche und Zeit je Quelle werden getrennt erfasst.
Quellenzeiten schließen Modell-/Umgebungsaufbau aus; die gesamte Workerzeit
enthält diese Zusatzkosten. Es folgt kein Nachweis besserer Effizienz pro
Expertenabfrage oder Rechenzeit.

## 4. Konstant gehaltene Lern- und Ausführungsbedingungen

3 Datenblöcke × 3 B-Parents × 3 trainierte Quellen × Aktion/Abschluss =
54 Komponenten, jeweils genau 5.000 zusätzliche Updates. Alle starten mit
den ursprünglichen B-30k-Gewichten und vollständigem AdamW-Zustand.
Architektur, LR 1e-4, Decay 1e-6, Gradientengrenze 10, BCE-Koeffizient 0,1
und 0,8-Abschlussschwelle bleiben gleich. Nur Phase 0 wird trainiert;
Phasen 1–6 müssen bitgleich bleiben. Die Positivgewichte der neuen BCE
stimmen wegen der identischen Labelzahlen zwischen den Datenarmen überein.

Batch 64: dieselben 32 alten Beispiele plus 32 neue; Replay verwendet auch
in der zweiten Hälfte alte Beispiele. Alle Samplepläne sind gespeichert.
Es werden die geprüften Trainings-/Kompositionsfunktionen des früheren
Korrekturversuchs wiederverwendet. Aktions- und Abschlusskopien haben
getrennte versteckte Gewichte; eine einzelne gemeinsame MLP ist nicht gezeigt.

Alle fortgesetzten Arme werden ausschließlich bei Platzierung 2 / Phase 0 /
außerhalb des Rückzugs aktiviert. Sonst bleibt B. Sequencer, Guard,
Clock-Korrektur, privilegierte Merkmale und Erfolgsauswertung bleiben gleich.
Eine bloße Anpassung des Gates oder der Abschlussschwelle ist ausgeschlossen.

## 5. Ein Hauptendpunkt und eine Zähleinheit

Primär: vollständiger Dreierturm über 50 strenge Gültigkeitsframes ohne
Fingerkontakt, maximal 1.000 Schritte. **Alle 150 neuen Bestätigungsszenen
bleiben im Nenner**, auch wenn der Zielkontext nicht erreicht wird.
Entwicklung: 20 bereits geöffnete Szenen, getrennt, keine Modellselektion.

Für jede neue Szene i wird die gepaarte Erfolgsdifferenz zuerst über die
drei sammlungsfremden Datenblock/Parent-Paare gemittelt. Der Hauptschätzer
Delta ist das Mittel dieser 150 Szenendifferenzen. Dadurch erhält weder ein
Datenblock noch eine erfolgreich erreichte Teilphase mehr Gewicht.

Ein deterministischer gepaarter Szenenbootstrap zieht 10.000-mal jeweils
150 vollständige Szenenfamilien mit Zurücklegen. Sämtliche drei Hauptpaare
und ihre Kontrollausgänge bleiben beim Ziehen einer Szene zusammen.
Berichtet wird das zweiseitige 95%-Perzentilintervall für Delta. Seed und
Analysecode sind vorab fixiert. Das Intervall ist **bedingt auf diese
eingefrorenen Parents und Erhebungsblöcke**; Unsicherheit über eine neue
Trainingsseed-/Datenerhebungspopulation ist damit nicht abgedeckt.

Ein positiver Hauptbefund erfordert gemeinsam:

1. mittlerer Vorteil Targeted gegen Standard mindestens **+5 Prozentpunkte**;
2. untere Grenze des gepaarten Szenenintervalls **größer als null**;
3. positive Targeted–Standard-Differenz in **allen drei** Hauptpaaren;
4. im Mittel keine Verschlechterung gegenüber Replay und ursprünglichem B.

Sonst wird der Nutzen als nicht nachgewiesen berichtet; bei einem vollständig
negativen Intervall als negativer Effekt innerhalb dieses Versuchsrahmens.
Ein Nullbefund belegt keine Gleichwertigkeit. Der Umfang garantiert keine
bestimmte Teststärke für kleine Effekte. Keine neuen Varianten, Testvergrößerung
oder Schwellenänderung nach Einsicht. Weitere Kontraste bleiben deskriptiv.

150 Szenen werden über alle Modell-/Datenkombinationen geteilt. Weder 450
Haupttestpaare noch 1.350 Targeted-Paare des gesamten Gitters sind so viele
unabhängige Szenen. Drei Parents bleiben drei Modellseeds; drei Blöcke werden
nicht als neun unabhängige Initialisierungen ausgegeben. Griffstatus nennt
die erreichten Lift-Starts separat; er ersetzt den Gesamtendpunkt nicht.

## 6. Sperre vor Testöffnung und fester Umgang mit der Deadline

Alle 54 Komponenten müssen Update 5.000 erreicht haben. Ihre tatsächlichen
Checkpointbytes und Updatezähler werden vor dem ersten Bestätigungstest in
`frozen_components.json` festgehalten. Erst danach wird die Testöffnung mit
Zeit und Manifesthash dokumentiert. Unvollständige oder veränderte Komponenten
brechen ab. Vor und nach Auswertung werden die Hashes erneut geprüft.

Zuerst werden sämtliche drei Hauptpaare vollständig ausgewertet und der
unveränderliche `primary_result.json` geschrieben; danach die sechs sekundären
Kombinationen. Innerhalb einer Szene rotiert die Reihenfolge der vier Arme.
Kein Training findet während oder nach diesen Tests statt. Die ursprünglichen
B-Kontrollen werden nur einmal je Parent/Szene ausgeführt und später referenziert.

**Vorab definierter Teilausgang:** Ein vollständig abgeschlossener und
integritätsgeprüfter Haupttest bleibt berichtbar, falls nur die sekundäre
Auswertung an der Deadline endet. Fehlt eine einzige Haupttestzelle, gibt es
keinen positiven Hauptnachweis und keine Ersetzung fehlender Fälle. Es wird
kein nachträglich verkürztes Testpanel ausgewertet. Völlige Fertigstellung
umfasst 6.120 Zeilen aus 5.100 tatsächlich ausgeführten Episoden.

Quellen, Paket-/GPU-Umgebung, alte und neue Datenhashes, Controllerzuteilung,
Rohphasen, Auswahlindizes, Samplepläne, Optimizer/RNG, alle Einzelversuche,
Paarvergleiche, Loss und Grafiken bleiben nachvollziehbar erhalten. Keine
Website-Veröffentlichung, Hardware-/OOD-/beliebige-Turmhöhen-Behauptung oder
nachträgliche Wiederverwendung geöffneter Bestätigungsszenen fürs Training.

## 7. Start und technische Prüfung

```powershell
praxis/.venv/Scripts/python.exe -m unittest discover -s experiments/curriculum/targeted_correction_budget_v2 -p test_pipeline.py
praxis/.venv/Scripts/python.exe experiments/curriculum/targeted_correction_budget_v2/pipeline.py prepare --output praxis/results/curriculum/targeted_correction_budget_v2/night_20261117
# Wissenschaftlicher Start erst auf Startauftrag:
powershell -NoProfile -File experiments/curriculum/targeted_correction_budget_v2/start.ps1
praxis/.venv/Scripts/python.exe experiments/curriculum/targeted_correction_budget_v2/monitor.py --output praxis/results/curriculum/targeted_correction_budget_v2/night_20261117
```

Technischer Smoke: separater Ordner, `prepare --smoke`, dann `run`. Das volle
3×3-Gitter wird mit drei kleinen getrennten Erhebungsblöcken und vier Updates
je Komponente geprüft: 54 Komponenten, 72 Zeilen aus 60 echten technischen
Auswertungsabläufen. Jeder Zielparent liefert im Hauptblock selbst keine
Sammelzustände. Es werden bekannte technische Auswertungsszenen verwendet. Die
Analyse erzwingt `TECHNICAL_ONLY_NO_SCIENTIFIC_CLAIM`. Proben dienen ausschließlich
der technischen Prüfung. Geschätzte Vollzeit und konkrete Nachweise stehen
nach dem Probelauf in `PREPARATION_CHECKS.md`.
