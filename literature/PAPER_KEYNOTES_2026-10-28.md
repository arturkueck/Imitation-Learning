# Neue Paper: Quellenvermerke

Stand: 29.10.2026. Seiten ab erster PDF-Seite; Zeilen sind eigene nichtleere Layoutzeilen pro Seite. Formeln und Spalten können Extraktionsartefakte enthalten.


## Demo-SCORE

arXiv:2503.03707v2, 22.07.2025; 14 PDF-Seiten. Eigene seitenlokale Zeilen der eingefrorenen Layout-Lesefassung; bei zweispaltigem Text Spaltenangabe beachten.

https://arxiv.org/pdf/2503.03707v2


Projektbezug (eigene Einordnung): Eigene Einordnung: Ein Vergleich mit Demo-SCORE könnte prüfen, ob aus Rollout-Ergebnissen gelernte Auswahl nützlicher ist als unser handgesetzter Übergangsscore. Chunkfilter passen zur Nutzung guter Teilabschnitte. Das Paper belegt keinen Vorteil für unseren Stack-Datensatz und erzeugt keine neuen Expertenkorrekturen.


### DEMO_SCORE-K01 — Erfolg ist noch keine Zuverlässigkeit

Auch ausschließlich erfolgreiche Demonstrationen können Strategien enthalten, die eine gelernte Policy nur unzuverlässig reproduziert. Demo-SCORE nutzt deshalb Erfolge und Fehler eigener Rollouts zur Datenauswahl.

PDF S. 2, Z. 41–52, rechte Spalte, §III Preliminaries

PDF S. 3, Z. 11–20, linke Spalte, §IV Data Curation


### DEMO_SCORE-K02 — Klassifikator und Cross-Validation

Ein Zustandsklassifikator lernt binäre Rollout-Ergebnisse. Klassifikatoren aus früheren Checkpoints werden mit Rollouts eines späteren Checkpoints validiert, um Überanpassung an eine einzelne Rollout-Verteilung zu begrenzen.

PDF S. 3, Z. 14–22, rechte Spalte, §IV-A

PDF S. 3, Z. 38–43, rechte Spalte, §IV-A


### DEMO_SCORE-K03 — Filtern und erneut trainieren

Die mittlere vorhergesagte Erfolgswahrscheinlichkeit einer Episode wird mit einer aus Rollout-Daten bestimmten Schwelle verglichen. Anschließend wird auf gefilterten Demonstrationen und gefilterten erfolgreichen Rollouts trainiert oder feinabgestimmt.

PDF S. 4, Z. 16–35, linke Spalte, §IV-B

PDF S. 4, Z. 5–14, rechte Spalte, Fortsetzung §IV-B


### DEMO_SCORE-K04 — Empirischer Umfang

Untersucht werden Diffusion Policy in Robosuite sowie ACT in simuliertem und realem ALOHA. Die Hauptexperimente in Simulation verwenden 400 Rollouts zur Kuration; bewertet wird mit 256 Simulations- beziehungsweise 30 Realrollouts.

PDF S. 5, Z. 7–15, linke Spalte, §V-A Experimental Setup

PDF S. 5, Z. 28–36, linke Spalte, §V-A Comparisons


### DEMO_SCORE-K05 — Teilabschnitte statt ganzer Episoden

In der Square-Peg-Ablation erreicht Chunkfilterung eine ähnliche Leistung wie Episodenfilterung. Damit können brauchbare Abschnitte erhalten bleiben; dies ist kein allgemeiner Nachweis für beliebige lange Aufgaben.

PDF S. 8, Z. 32–43, rechte Spalte, §V-D(d) Filtering at the chunk level


### DEMO_SCORE-K06 — Grenzen des Erfolgssignals

Nicht repräsentative Rollouts, fehlende Ausgangserfolge und reduzierte Zustandsabdeckung können die Methode begrenzen. Die Autoren richten die Kuration auf abschließende Aufgabenleistung aus, nicht auf maximale Breite eines Vortrainingsdatensatzes.

PDF S. 9, Z. 15–36, linke Spalte, §VI Limitations


## CUPID

arXiv:2506.19121v2, 23.09.2025; 27 PDF-Seiten. Eigene seitenlokale Zeilen der eingefrorenen Layout-Lesefassung. Extraktion enthält fehlende Leerzeichen und Formelartefakte; Original-PDF ist maßgeblich.

https://arxiv.org/pdf/2506.19121v2


Projektbezug (eigene Einordnung): Eigene Einordnung: Besonders relevant für die Validierung unseres Qualitätsscores. Eine ruhige oder erfolgreiche Demonstration muss nicht die größte Lernhilfe sein. Vor einer aufwendigen Umsetzung wären Nutzen, benötigte Rollouts und Einflussberechnung gegen einfache Auswahlbaselines zu prüfen. Kein Stack-Ergebnis wird hieraus abgeleitet.


### CUPID-K01 — Ziel: Erfolg im Regelkreis

CUPID schätzt aus Policy-Rollouts den Einfluss einzelner Demonstrationen auf den erwarteten Return. Die Auswahl kann bestehende Daten entfernen oder aus einem weiteren Datenpool hilfreiche Beispiele hinzufügen.

PDF S. 2, Z. 4–17, einspaltig, §1 Introduction

PDF S. 4, Z. 8–20, einspaltig, §4 Problem Formulation


### CUPID-K02 — Approximierter Einfluss

Das Verfahren verwendet eine lineare Näherung der Leistungsänderung beim Hinzufügen oder Entfernen von Demonstrationen. Es berechnet somit eine geschätzte Wirkung, keinen exakten Erfolg nach jedem möglichen erneuten Training.

PDF S. 6, Z. 1–17, einspaltig, §5.2 Data Curation with Performance Influence


### CUPID-K03 — Versuchsaufbau und Rolloutkosten

Untersucht werden drei RoboMimic- und drei Franka-Aufgaben. Zur Kuration sind 100 Simulations- beziehungsweise 25 Realrollouts vorgesehen. Die Arbeit nutzt Diffusion Policies und untersucht zusätzlich die Anpassung von π0.

PDF S. 6, Z. 32–48, einspaltig, §6 Experiments und Evaluation


### CUPID-K04 — Qualität kann robuste Strategien aussortieren

Im TuckBox-Versuch macht eine veränderte Massenverteilung die dominante Schiebestrategie unzuverlässig. CUPID identifiziert alternative Demonstrationen trotz ausschließlich gescheiterter Ausgangsrollouts; Qualitätsheuristiken schneiden hier schlechter ab.

PDF S. 8, Z. 14–30, einspaltig, §6.2 TuckBox und Analyse


### CUPID-K05 — Weniger Daten ist nicht immer besser

Der Nutzen der Kuration hängt von Aufgabe und Daten ab. In den berichteten Versuchen hilft Filtern bei Transport MH, während das Entfernen fast jeder Demonstration bei Square MH Leistung kostet.

PDF S. 9, Z. 18–27, einspaltig, §7.1 Data and task properties


### CUPID-K06 — Grenzen und Aufwand

Die Auswahlmenge wird vorgegeben; Wechselwirkungen zwischen ausgewählten Demonstrationen bleiben unberücksichtigt. Vollständige Einflussberechnung kann ähnlich teuer wie Policytraining sein. Wenige Rollouts erhöhen zudem die Schätzvarianz.

PDF S. 11, Z. 1–4, einspaltig, §9 Curation tasks

PDF S. 11, Z. 10–22, einspaltig, §9 Selection methods, Larger datasets, Estimator variance


## Policy-Calibrated DAgger

arXiv:2609.30462v1, 24.09.2026, 8 PDF-Seiten; lokal eingefroren am 28.10.2026. Eigene seitenlokale Layoutzeilen, keine offiziellen Publikationszeilen.

https://arxiv.org/pdf/2609.30462v1


Projektbezug (eigene Einordnung): Eigene Einordnung: Für unsere Stack-Übergänge ist die Trennung zwischen Störzuständen und passenden Recovery-Aktionen wichtig. Dieses Verfahren erzeugt neue Aktionsziele und gewichtet nicht bloß vorhandene Erfolge. Die Gelenkpositions- und Simulationsannahmen lassen sich nicht ungeprüft auf unseren Actor übertragen.


### PCDAGGER-K01 — Unterschied zu DART

Die Störstatistik wird offline und in Simulation bestimmt. Anders als bei DART wird der Expertenregelkreis nicht verrauscht; saubere Interventionen werden nachträglich erweitert.

PDF S. 3, Z. 26–34, linke Spalte, §IV Policy-Calibrated DAgger


### PCDAGGER-K02 — Multimodale Aktionen

Partielles Denoising führt die Policy zur aufgezeichneten Expertenbahn; der bekannte Rauschplan dient zur Fehlerschätzung. Lineares Mischen zweier jeweils gültiger Ausweichaktionen kann dagegen eine Kollision erzeugen.

PDF S. 4, Z. 15–18, linke Spalte, §IV-B

PDF S. 4, Z. 29–37, linke Spalte, §IV-B: Hindernisbeispiel


### PCDAGGER-K03 — Woher die Korrekturaktionen kommen

Zusätzliche Zustands-Aktions-Paare entstehen um Experteninterventionen. Ein heuristischer Verbindungsalgorithmus und ein kritisch gedämpfter PD-Regler führen gestörte Gelenkzustände zurück zur Expertenbahn; Geschwindigkeit und Beschleunigung orientieren sich an Demonstrationen.

PDF S. 5, Z. 36–56, rechte Spalte, §IV-E Generating Corrective Labels


### PCDAGGER-K04 — Vergleichsbedingungen

Die Experimente verwenden zwei Simulatoren und ein privilegiertes, deterministisches RRT-Orakel statt menschlicher Korrekturen. Innerhalb einer Umgebung starten die verglichenen Varianten am selben BC-Checkpoint und erhalten gleich viele Trainingsschritte.

PDF S. 3, Z. 26–37, rechte Spalte, §IV-A: Interventionserhebung

PDF S. 6, Z. 19–39, rechte Spalte, §V: Simulationsumgebungen

PDF S. 7, Z. 5–15, linke Spalte, §V: gepaarter Vergleich


### PCDAGGER-K05 — Ergebnisse mit Nenner und Streuung

Im 2D-Reacher erreicht gepooltes kalibriertes Rauschen nach Runde 5 89,3 ± 0,5 % gegenüber 87,3 ± 1,0 % bei HG-DAgger (Mittelwert ± Standardfehler, fünf DAgger-Linien; 100 Szenarien mit je drei Auswertungen). In der 3D-Aufgabe erreicht es nach Runde 2 63,4 ± 4,8 % gegenüber 58,1 ± 4,0 % (drei Linien).

PDF S. 6, Z. 1–16, seitenbreite Tabelle I samt Legende

PDF S. 6, Z. 17–25, linke Spalte, Tabelle II samt Legende


### PCDAGGER-K06 — Grenzen der Übertragung

Interventionen kürzer als der Aktionshorizont werden verworfen. In der 3D-Aufgabe bleiben die ursprünglichen Bilder bei verrauschten Gelenkpositionslabels unverändert. Menschliche Interventionen und andere generative Modellfamilien werden als zukünftige Arbeit genannt.

PDF S. 4, Z. 28–38, rechte Spalte, §IV-C

PDF S. 7, Z. 26–31, linke Spalte, §V: Bildapproximation

PDF S. 7, Z. 17–23, rechte Spalte, §VI Conclusion


## Reward-DAgger

arXiv:2610.04054v1, 02.10.2026, 11 PDF-Seiten; lokal eingefroren am 28.10.2026. Eigene seitenlokale Layoutzeilen, keine offiziellen Publikationszeilen.

https://arxiv.org/pdf/2610.04054v1


Projektbezug (eigene Einordnung): Eigene Einordnung: Rückschritt und Stillstand sind getrennte Diagnosen für unsere Paarwechsel und festhängenden Phasen. Das Paper motiviert gezielte Korrekturerhebung, beweist aber weder, dass unser Turmerhaltscore ein geeignetes Fortschrittssignal ist, noch dass ein bereits einstürzender Turm rechtzeitig gerettet werden kann.


### REWARD-DAGGER-K01 — Zwei Fehlerarten

Ein kurzes Zeitfenster erkennt sinkenden Fortschritt, ein längeres ausbleibenden Fortschritt. Spearman-Korrelationen erfassen die Trends; beim kurzen Fenster muss zusätzlich ein Mindestabfall vorliegen.

PDF S. 3, Z. 8–35, linke Spalte, §III-A Gating Criterion

PDF S. 3, Z. 4–20, rechte Spalte, §III-A, Gl. (3)–(4)


### REWARD-DAGGER-K02 — Korrekturen statt Reward-Optimierung

Nach Auslösen des Gates übernimmt ein Experte. Seine Korrekturen werden mit dem vorhandenen Datensatz zusammengeführt und die Policy wird weitertrainiert. In den Experimenten behält der Experte die Kontrolle bis zum Episodenende; das Fortschrittssignal entscheidet über die Übernahme.

PDF S. 3, Z. 22–33, rechte Spalte, §III-B Reward-DAgger

PDF S. 6, Z. 11–17, linke Spalte, §IV/Q3: Sammlung und Replay


### REWARD-DAGGER-K03 — Modelle und Evaluationsumfang

Robometer-4B liefert das Fortschrittssignal. In Simulation lernt eine Diffusion Policy mit π0.5 als eingefrorenem Experten; vier LIBERO-Aufgaben wurden gewählt, auf denen dieser häufige Fehlerzustände korrigiert. Reale Versuche nutzen vier Franka-FR3-Aufgaben und menschliche Teleoperation.

PDF S. 4, Z. 26–57, linke Spalte, §IV: Reward Model, Simulation Setup und Real Robot Setup

PDF S. 4, Z. 1–2, rechte Spalte, Fortsetzung Real Robot Setup


### REWARD-DAGGER-K04 — Transfer ist nicht parameterfrei

Die Übertragung eines auf nur einer Aufgabe gewählten Gates ist nicht durchgehend zuverlässig. Gemeinsame Auswahl auf mehreren Quellaufgaben verbessert die Stabilität. Die abschließende Konfiguration wird auf LIBERO-Aufgaben 0, 1, 5 und 8 ausgewählt und anschließend unverändert eingesetzt.

PDF S. 5, Z. 29–50, rechte Spalte, §IV/Q2: Transferergebnisse

PDF S. 6, Z. 4–10, linke Spalte, §IV/Q3: feste Konfiguration


### REWARD-DAGGER-K05 — Stack-Ergebnis und Testgrenze

Beim realen Zweier-Stack steigt der autonome Erfolg von 65 % auf 80 % über zwei Lernrunden. Jeder reale Checkpoint wird mit 20 Rollouts bewertet. Stack, Pick und Put haben genaue oder ähnliche Beispiele im Trainingsbestand des Fortschrittsmodells; sie sind daher kein Nachweis vollständig ungesehener Aufgaben.

PDF S. 6, Z. 15–21, rechte Spalte, Tabelle III: Stack-Zeilen

PDF S. 7, Z. 2–13, linke Spalte, Real-robot Tasks: Datenüberlappung und Testumfang


### REWARD-DAGGER-K06 — Reaktive Erkennung und Messgrenze

Stillstand kann mehrere Sekunden bestehen, bevor das lange Gate auslöst. Das Verfahren reagiert auf erkennbare Fehler, statt sie vorab zu verhindern. Die gemessene Detektionslatenz nutzt außerdem die mittlere Auslösezeit als Ersatzmaß, nicht den Abstand zu einem exakt annotierten Fehlerbeginn.

PDF S. 8, Z. 42–57, linke Spalte, Limitations and Future Work

PDF S. 4, Z. 17–23, rechte Spalte, Q1: Latency


## DemoGen

arXiv:2502.16932v1, 24.02.2025, 18 PDF-Seiten. Seiten ab erster PDF-Seite; Zeilen aus eingefrorener Layout-Lesefassung, keine offiziellen Publikationszeilen.

https://arxiv.org/pdf/2502.16932v1


Projektbezug (eigene Einordnung): Eigene Einordnung: DemoGen motiviert einen kontrollierten Vergleich zusätzlicher räumlicher Zustandsabdeckung mit bloßem Weitertraining. Die Methode liefert jedoch strukturiert erzeugte Aktionsziele und Punktwolken; ihr Erfolg belegt weder die Wirksamkeit unserer Qualitätsgewichte noch eine direkte Übertragbarkeit auf den bisherigen 10D-Actor.


### DEMOGEN-K01 — Kontaktsegmente und freie Bewegung

DemoGen trennt kontaktbezogene Fertigkeitssegmente von freien Bewegungen. Erstere werden mit der neuen Objektkonfiguration transformiert; die verbindenden Bewegungen werden durch Bewegungsplanung neu erzeugt.

PDF S. 2, Z. 19–29, linke Spalte, Einleitung: Aktionsgenerierung


### DEMOGEN-K02 — Synthetische Beobachtungen

Die Beobachtungen entstehen durch 3D-Editing segmentierter Punktwolken. Objekt- und Greifercluster erhalten dieselben räumlichen Transformationen wie der Aktionsplan; während des Kontakts werden zusammengehörige Teile gemeinsam transformiert.

PDF S. 2, Z. 39–53, linke Spalte, Einleitung: Punktwolkengenerierung


### DEMOGEN-K03 — Was eine Ausgangsdemonstration bedeutet

Für reale Aufgaben wird eine menschliche Ausgangsbewegung zweimal abgespielt und erneut beobachtet. Damit stehen drei Punktwolkenverläufe mit unterschiedlichem Sensorrauschen zur Verfügung; die reale Versuchsbasis ist nicht nur eine einzelne Aufnahme.

PDF S. 9, Z. 16–29, linke Spalte, §VI-A, Generation strategy


### DEMOGEN-K04 — Realer Versuchsumfang und Ergebnis

Acht reale Aufgaben auf drei Plattformen werden untersucht. Tabelle III berichtet 530 Rollouts und fünf Wiederholungen je Konfiguration; der Aufgabenmittelwert steigt von 11,0 % mit Quelldaten auf 74,6 % mit DemoGen-Daten. Das ist kein Ergebnis für unsere Stapelpolicy.

PDF S. 8, Z. 8–13, linke Spalte, §VI: Versuchsübersicht

PDF S. 9, Z. 1–3, seitenbreit oben, Beschriftung Tabelle III

PDF S. 9, Z. 39–41, seitenbreite Tabelle III; Tabellenzeilen stehen in der Extraktion am Seitenende


### DEMOGEN-K05 — Reichweite der Generalisierungsaussage

Die synthetischen Objektkonfigurationen werden gezielt an den später evaluierten Positionen erzeugt und um kleine Positionsstörungen erweitert. Die Arbeit prüft damit räumliche Übertragung aus wenigen menschlichen Vorlagen, nicht einen Test ohne synthetische Abdeckung der Zielpositionen.

PDF S. 9, Z. 30–38, linke Spalte, §VI-A, Generation strategy


### DEMOGEN-K06 — Grenzen der Datengenerierung

Die Autoren nennen segmentierte Punktwolken als Voraussetzung, Grenzen in stark unstrukturierten Szenen und Abweichungen zwischen synthetischen und realen Ansichten. Aufgaben ohne Bedarf an räumlicher Generalisierung sind nicht der geeignete Einsatzbereich.

PDF S. 12, Z. 5–13, linke Spalte, Limitations


## PSD Data Quality

arXiv:2605.01544v2, 07.09.2026, 8 PDF-Seiten. Titelseite nennt drei Autoren. Seiten ab erster PDF-Seite; Zeilen aus eingefrorener Layout-Lesefassung.

https://arxiv.org/pdf/2605.01544v2


Projektbezug (eigene Einordnung): Eigene Einordnung: Der PSD-Score ist eine mögliche kostengünstige Vergleichsgröße für unseren Qualitätsscore. Er sollte gegen Turmerhalt und vollständigen Aufgabenerfolg validiert werden. Glatte Fehlbewegungen sowie notwendige Korrekturen dürfen nicht allein aufgrund ihrer Glätte bewertet werden; eine Überlegenheit auf unseren Übergängen ist nicht nachgewiesen.


### PSD-K01 — Eingangssignal und Score

Die Methode verwendet kartesische Endeffektorpositionen. Spektrale Leistungen werden über die drei Koordinaten und Frequenzen zum Trajektorienscore W summiert. Das Ranking benötigt weder Policytraining noch Interaktion mit der Umgebung.

PDF S. 4, Z. 24–26, linke Spalte, §IV: Offline-Berechnung

PDF S. 4, Z. 27–49, linke Spalte, §IV-A/B: Trajektoriendarstellung und Spektralzerlegung


### PSD-K02 — Filterregel

Kleinere W-Werte erhalten den besseren Rang. Ein frei festgelegter Anteil der Demonstrationen mit den höchsten Scores wird entfernt; die übrigen Daten bilden den neuen Trainingssatz. Dies ist eine Filterung ganzer Trajektorien, keine Gewichtung einzelner Übergänge.

PDF S. 4, Z. 1–15, rechte Spalte, §IV-C: Demonstration Ranking and Evaluation


### PSD-K03 — Vergleichsbedingungen

Can und Square werden mit RoboMimic-MH und Layman2 untersucht. Die Vergleichsverfahren verwenden dieselbe diffusionsbasierte Architektur und dieselben Trainingsparameter; Ergebnisse werden über drei Seeds berichtet. Die Haupttabelle entfernt 50 % der Demonstrationen.

PDF S. 4, Z. 39–55, rechte Spalte, §V-A: Datensätze

PDF S. 5, Z. 14–26, linke Spalte, §V-A: Filterung und Training

PDF S. 6, Z. 5–6, seitenbreit, Beschriftung Tabelle II


### PSD-K04 — Ergebnis mit Gegenbeispiel

Tabelle II berichtet über die acht Bedingungen einen Mittelwert von 0,74 gegenüber 0,58 ohne Filterung. Der Vorteil ist nicht universell: Bei bildbasiertem RoboMimic-Square beträgt der PSD-Wert 0,85 gegenüber 0,87 ungefiltert.

PDF S. 6, Z. 27–36, seitenbreite Tabelle II; Tabellenzeilen am Ende der Textextraktion


### PSD-K05 — Reale Studie und Umfang

Fünf ältere Erwachsene liefern Demonstrationen für eine Mikrowellenaufgabe. Nach π0.5-Finetuning und 20 Rollouts je untersuchter Einstellung steigt der Personenmittelwert von 15 % ungefiltert auf 38 % mit PSD-Filterung; dabei bleiben 60 % der Demonstrationen erhalten.

PDF S. 5, Z. 27–45, linke Spalte, §V-A.2: Nutzerstudie und Finetuning

PDF S. 6, Z. 20–26, linke Spalte: Auswertung; rechte Spalte: Tabelle IV


### PSD-K06 — Glätte ist keine Erfolgsgarantie

Die Autoren unterscheiden Bewegungsineffizienz von semantischem Aufgabenerfolg und räumen ausdrücklich glatte, aber erfolglose Demonstrationen ein. Der Score erfasst deshalb nicht direkt, ob eine Aufgabe korrekt abgeschlossen wurde.

PDF S. 7, Z. 1–15, linke Spalte, §VI-C: Discussion

PDF S. 4, Z. 7–20, linke Spalte, §IV: Definition und bewusste Abgrenzung des Scores