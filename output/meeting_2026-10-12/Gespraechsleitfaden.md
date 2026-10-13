# Erste Rücksprache: Projektarbeit zu Imitation Learning

**Vorbereitung für Artur | Recherchestand: 12. Oktober 2026 | Master-Projektarbeit, 3 Monate**

Planungsgrundlage: Arbeit zunächst am eigenen PC; Rechenzentrum möglicherweise ab der zweiten Hälfte. Der Kern der Arbeit soll ohne Rechenzentrum abschließbar sein. Diese Unterlage enthält einen Vorschlag, keine neu durchgeführten Trainings. Vorarbeiten und neue Hypothesen sind getrennt.

## 1. Meine Empfehlung für das Gespräch

**Arbeitstitel: Wann hilft dynamikbasierte Regularisierung beim Imitation Learning? Eine kontrollierte Robustheitsstudie mit robomimic.**

Die Arbeit untersucht, ob ein zusätzlicher Lernterm kleine reale Abweichungen besser korrigieren lässt, wenn die zugrunde liegende Dynamiknäherung zuvor auf ihre Gültigkeit geprüft wird. Der Kern ist eine begrenzte Erweiterung von Behavioral Cloning (BC), mit unveränderter Policyarchitektur und nachvollziehbaren Kontrollen.

**Haupt-Hypothese:** Bei gleichem Trainingsbudget erhöht eine anhand lokaler Modellgültigkeit gewichtete Kontraktionsregularisierung die Erfolgsrate nach echten Aktionsstörungen gegenüber derselben Regularisierung ohne diese Gewichtung, ohne die nominale Erfolgsrate wesentlich zu senken.

Warum sinnvoll: BC lernt Aktionen auf Expertenzuständen. In der Ausführung entstehen Abweichungen; daraus können weitere Fehler folgen. Ein Zusatzloss kann eine korrigierende Reaktion fördern, aber ein falsches Dynamikmodell kann auch eine falsche Reaktion belohnen. Hier liegt eine konkrete und überprüfbare Methodenfrage. Stable-BC und CCIL liefern die wissenschaftliche Grundlage [S3-S5].

**Beitrag:** robomimic-Implementation, Prüfung der Modellannahmen, kontrollierte Ablation und Kostenbilanz. Die Kombination ist ein zu prüfender Projektbeitrag; weltweite Neuheit oder eine Stabilitätsgarantie werden nicht behauptet. Modellgültigkeit und Fehlerfilter sind in der Literatur bereits bekannt.

**Machbarkeit:** Start auf dem offiziellen Lift-PH-Datensatz mit Zustandsmerkmalen und kleinem MLP. Zweite Aufgabe nur nach Abschluss des Kerntests; bevorzugt Can, alternativ Square bei zuverlässig reproduzierter Baseline. Das lokale StackTwo ist eine optionale Übertragung mit eigenen, programmierten Demonstrationen.

**Entscheidung nach Woche 3:** Ist die Dynamiknäherung nicht hinreichend prüfbar oder die aktive Abdeckung zu klein, wird der neue Regularisierer nicht groß trainiert. Dann wird die vorbereitete Alternative zur zeitlichen Struktur von Sensoraugmentation verfolgt. Die dokumentierte Gültigkeitsprüfung bleibt ein Ergebnis.

## 2. Was der Forschungsstand für die Themenwahl bedeutet

Die Suche ist eine gezielte Auswahl aus offiziellen Projekten, Proceedings und Originalarbeiten bis 12.10.2026, kein systematischer Vollständigkeitsnachweis. Sehr neue Preprints werden als solche behandelt.

| Arbeit / Stand | Belastbare Aussage und Bedeutung für die Arbeit |
|---|---|
| robomimic / Mandlekar et al., CoRL 2021, Proceedings 2022 [S1-S2] | Bietet Aufgaben, Demonstrationen, Baselines und Vergleichsprotokolle. Datenqualität, Beobachtungen und Training sind relevante Einflussfaktoren. Der geprüfte Stand enthält bereits BC-RNN, BC-Transformer und Diffusion Policy; deren bloße Verwendung ist kein neuer Methodenbeitrag. |
| Diffusion Policy, RSS 2023 [S6] | Lernt Verteilungen über Aktionsfolgen und führt sie mit erneutem Planen aus. Liefert eine wichtige moderne Referenz; eine umfassende Replikation wäre für diese begrenzte Robustheitsfrage zusätzlicher Aufwand. |
| Stable-BC, RA-L 2025 [S3] | Verbindet BC mit Bedingungen für lokale Fehlerdynamik. Seine Annahmen und Garantien dürfen nicht auf einen beliebigen empirischen Zusatzloss übertragen werden. |
| CCIL, ICLR 2024; Feinmanipulation, IROS 2024 [S4-S5] | Erzeugt korrigierende Labels mit lokalen Dynamikmodellen; die Qualität und Filterung dieser Labels sind entscheidend. Unser Vorschlag verändert einen Regularisierungsterm und erhebt keine neuen Expertenlabels. |
| Contractive Dynamical Imitation Policies, ICLR 2025; Contractive Diffusion Policies, ICLR 2026 [S9-S10] | Kontraktive IL-Ansätze sind bereits vorhanden. Kontraktion einer Policy-Dynamik, des Diffusionssamplers und des physischen Roboters sind unterschiedliche Aussagen. Unser Fokus bleibt die empirisch geprüfte physische Fehlerantwort. |
| Lazzati et al., 03.08.2026, Preprint [S7] | Untersucht Mechanismen von Action Chunking, darunter verzögerte Beobachtungen und implizites Ensembling. Begründet eine Alternative zur Ausführungsstrategie, nicht die Neuheit von Chunking. |
| Goyal, 01.10.2026, Preprint [S8] | Misst Fehlerausbreitung nach Aktionsstörungen und berichtet starke Abhängigkeit vom Messhorizont. Motiviert Messungen über mehrere Horizonte; ist noch keine gesicherte allgemeine Aussage über alle IL-Policies. |

**Abgeleitete Forschungsfrage:** Unter welchen empirisch überprüften Modellbedingungen bringt dynamikbasierte Regularisierung in diesem robomimic-Aufbau einen Zusatznutzen gegenüber einfacher Rauschaugmentation? Das ist eine Synthese und eine lokale Untersuchungslücke, kein belegter weltweiter Neuheitsnachweis.

Für den Einstieg zuerst [S1], [S3], [S4] und [S5] lesen. [S7-S10] dienen der aktuellen Abgrenzung. DAgger und DART [S11-S12] sind sinnvolle Bezugspunkte, verlangen aber zusätzliche Expertenkorrekturen beziehungsweise eine veränderte Datenerhebung; sie sind kein gleichwertiger Ersatz für nachträgliches Rauschen auf Beobachtungen.

## 3. Was die lokalen Vorarbeiten bereits zeigen

| Befund | Was im Gespräch daraus folgt |
|---|---|
| Historischer Lift-Vergleich nach 10.000 Updates: BC 44/60, bisheriger Zusatzloss 56/60 nominal. Drei Trainingsseeds, je 20 Rollouts. | Es gibt einen positiven lokalen Anlass zur Untersuchung. Die 60 Rollouts sind keine 60 unabhängigen Trainingsreplikate. |
| Pro Seed nominal: BC 16/20, 15/20, 13/20; Zusatzloss 18/20, 20/20, 18/20. | Alle Seedwerte zeigen; keine Signifikanz oder allgemeine Verbesserung aus dieser kleinen Studie ableiten. |
| Spätere Interventionstests zeigen Fehler der aus Expertendaten geschätzten Aktionsantwort. | Gute Vorhersage von Expertentrajektorien beweist keine korrekte Antwort auf veränderte Aktionen. Das ist die Motivation für die Modellprüfung. |
| Neue lokale und volle Dynamik-Lossreferenz vorhanden; empirische Fehlerhülle hat ihren unabhängigen Entwicklungstest nicht bestanden. | Der Entwurf ist rechnerisch geprüft, aber noch kein trainierter und validierter neuer Algorithmus. |
| Ein Sensorpilot mit einem Seed: nominal 4/10 gegen 3/10, bei beiden Biasrichtungen jeweils 3/10 gegen 4/10, Impuls 3/10 gegen 3/10. | Keine robuste Überlegenheit. Sensorunempfindlichkeit und physische Korrektur müssen getrennt geprüft werden. |

Quellen: [L1-L3]. Keine hypothetischen 300-Epochen-Kurven präsentieren. Die historische Lift-Erweiterung ist Stable-BC-inspiriert und nicht die Originalmethode. Die umfangreichen lokalen Diagnosen sind Vorarbeiten; für die Rücksprache genügen eine Grafik und diese drei Aussagen: positiver Pilotbefund, offener Mechanismus, kontrollierter nächster Test.

## 4. Hypothese und algorithmische Änderung

### Sensorfehler und echte Zustandsabweichung unterscheiden

Bei einem Sensorfehler bleibt der physische Zustand gleich, aber die Policy sieht eine verfälschte Beobachtung. Kleine Messfehler sollen möglichst wenig stören. Bei einer echten Zustandsabweichung befindet sich der Roboter an einer anderen Position; er kann eine andere, korrigierende Aktion benötigen. Beide Fälle mit denselben unveränderten Aktionslabels zu trainieren ist deshalb nicht automatisch richtig.

Konzeptioneller Loss in Spaltenvektorschreibweise:

```text
Delta_a = pi(o_delta) - pi(o)
e_hat_next = A(o) * delta + B(o) * Delta_a
L = L_BC + lambda * mean[ w(o) * max(0, ||e_hat_next||² / ||delta||² - rho²) ]
```

`delta` ist eine kleine physisch konsistente Zustandsabweichung; `A` beschreibt ihre offene Fortwirkung, `B` die Wirkung einer geänderten Aktion. `rho < 1` ist ein gewünschter lokaler Schrumpffaktor. `w` gewichtet nur dort, wo unabhängige Prüfungen die Näherung stützen. Die Gleichung erläutert das Konzept; sie ist keine Stabilitätsgarantie. Die lokale Code-Referenz verwendet Zeilenvektoren und berücksichtigt zusätzlich eine Fehlermarge.

Geometrisch abgeleitete Beobachtungen werden konsistent angepasst. Eine EEF-Verschiebung allein definiert noch keinen eindeutigen vollständigen Simulatorzustand: Orientierung, Geschwindigkeit, Gripper, Controllerzustand und Kontakte müssen kontrolliert werden. Modellidentifikation und Gegenprüfung verwenden verschiedene Interventionen. `A`, `B` und `w` werden vor dem Policytraining eingefroren; keine Testrollouts zur Anpassung.

**Zusätzlicher Trainingszugang:** Die lokale Kalibrierung benötigt Simulatorzustände und Interventionen. Sie ist damit simulationsgestütztes IL mit festem Demonstrationssatz, kein Verfahren mit ausschließlich passivem Offline-Datenzugang. Die Policy erhält bei Ausführung nur dieselben Beobachtungen wie BC. Simulatorabfragen und Kalibrierkosten werden mitgezählt.

**Zunächst zu klären:** lokales `A` gegen festes `A` bei identischem lokalem `B` auf bisher ungenutzten Trainingsdemos. Das knüpft an den jüngsten Befund an. Die gescheiterte Fehlermarge wird nicht nachträglich anhand der Prüffälle vergrößert. Ein neuer Schätzer benötigt neue Entwicklung und getrennte Gegenprüfung.

## 5. Konkreter Versuchsplan

### Stufe 1: Machbarkeit bis Ende Woche 3

Versionen, Dataset-Hash und vorhandenen 180/20-Demosplit einfrieren. Innerhalb der 180 Trainingsdemos werden Modellfit, Kalibrierung und Gegenprüfung demoweise getrennt. Bereits verwendete Demos sind Entwicklungsdaten. Wenn keine unberührten Demos mehr verfügbar sind, eine neue Aufteilung offen als Entwicklung deklarieren und eine weitere Gegenprüfung reservieren; niemals rückwirkend Unberührtheit behaupten.

Anfangs die kleine vorhandene A/B-Diagnose weiterführen, danach über zusätzliche Demos und Phasen prüfen. Vor den Gegenprüfungen fixe Kriterien festhalten: normierter Vektorfehler, falsche Kontraktionsfreigaben, aktive Abdeckung, tatsächliche Kontaktzustände, Anzahl und Kosten der Simulatorabfragen. Praktische Startwerte für die Entwicklungsentscheidung: mindestens 30% aktive Abdeckung im vorab festgelegten Arbeitsbereich und höchstens 10% falsche Freigaben unter den akzeptierten Prüffällen. Diese Schwellen sind Vorschläge, keine theoretischen Grenzen; Nenner und Unsicherheit werden berichtet. Wenige oder keine akzeptierten Fälle reichen nicht.

Aktionsbereiche während des Policytrainings weiter protokollieren: Ein an Expertenaktionen kalibriertes Modell muss für die neuen Policyaktionen nicht gültig bleiben. Bei Verlassen des identifizierten Bereichs den Loss maskieren; gleiche Maskenregel in C2-C4. Die effektive Abdeckung je Phase und über die Trainingszeit messen und vorab einen Mindestwert für die beanspruchte Domain festlegen. Obwohl die Gewichte eingefroren sind, kann sich die Policy-abhängige Aktionsmaske verändern. Eine nahezu überall inaktive Methode gilt nicht als bestandene Machbarkeit; kontaktfreie Abdeckung begründet keinen Mechanismusanspruch für Kontaktphasen.

### Stufe 2: Kontrollierter Vergleich auf Lift

| Arm | Methode | Welche Frage wird isoliert? |
|---|---|---|
| C0 | Unverändertes BC | Referenzleistung |
| C1 | BC + konsistente Sensoraugmentation | Reicht eine einfachere Methode? |
| C2 | BC + kalibrierter lokaler Zusatzloss, überall gleich gewichtet innerhalb desselben zulässigen Bereichs | Basis des neuen Losses |
| C3 | C2 + eingefrorene Gültigkeitsgewichtung | Hauptvergleich C3 minus C2: Nutzen der Gewichtung |
| C4 | C3 mit zufällig permutierten Gültigkeitsgewichten | Hilft die gezielte Auswahl gegenüber zufälliger Gewichtung gleicher Verteilung? |

C2/C3/C4 verwenden dieselben A-/B-Modelle, Perturbationen, zugelassenen Bereiche und Cacheeinträge. C4 permutiert die C3-Gewichte innerhalb jeder Trainingsbatch auf der gemeinsamen harten Domain mit einer unabhängigen, vorab festgelegten RNG. Anzahl positiver Gewichte und Gewichtsverteilung bleiben exakt gleich; die Zuordnung zu Modellgüte wird entfernt. Harte Sicherheits-/Definitionsmasken werden nicht permutiert. C3 gegen C4 prüft damit die Information in der Auswahl. Zusatzgradientennormen während des Trainings protokollieren; gleiche Gewichtsmassen garantieren keine identische Gradientenstärke. Eine skalare Stärkeablation bleibt bei auffälligen Normunterschieden eine begrenzte Zusatzanalyse. Der alte OLS-Loss bleibt eine historische Referenz; ein zusätzlicher neuer OLS-Arm ist für den Kernvergleich nicht erforderlich.

**Gleich halten:** Policyarchitektur (zunächst Lift-MLP 256×256), Demosplit, Initialgewichte innerhalb eines Seedpaares, Batchreihenfolge, Normalisierung, Optimizer, Evaluator, Datenbudget und Updatebudget. Separate Zufallsgeneratoren für Perturbationen. Kein bester Checkpoint anhand der finalen Teststarts; letzter Checkpoint bei festem Budget. Startvorschlag 10.000 Updates aus dem vorhandenen Lift-Aufbau; vor Haupttest auf Entwicklungsdaten festschreiben. Pro Arm identisch begrenztes Tuningbudget; die Gültigkeitsgewichte haben ein separat ausgewiesenes Entwicklungskontingent.

**Umfang:** Kleiner Entwicklungsvergleich zunächst mit 3 Seeds je Arm, also bis zu 15 Entwicklungsläufe; diese Ergebnisse werden nicht als finale Bestätigung verwendet. Hauptvergleich mit 5 neuen gepaarten Trainingsseeds und 50 neuen gemeinsamen Simulatorstarts pro Bedingung. Fünf Arme × fünf Seeds = 25 finale Trainingsläufe, mit vollem Pilot insgesamt 40. Machbarkeitsarbeit und zusätzliche technische Prüfungen kommen hinzu.

**Fünf Testbedingungen:** nominal; Sensorbias +5 mm und -5 mm auf der EEF-x-Messung; echter einmaliger Aktionsimpuls in +x und -x. Relative Beobachtungsmerkmale beim Sensorbias konsistent verändern. Haupttest: Eingriff zu einem für alle Policies gleichen, frühen festen Zeitschritt, mit gleicher Dauer und Kommandodosis. Zeitpunkt, Dosis, Clipping und Zeithorizont in Woche 2 auf separaten Entwicklungsfällen festlegen und sperren; tatsächliche physische Verschiebung loggen. Den Evaluator in allen Bedingungen bis über den Eingriffszeitpunkt weiterführen und Erfolg nur im gemeinsamen anschließenden Bewertungsfenster zählen. Ein Erfolg vor dem Eingriff allein zählt nicht. Dosis und Zeitpunkt sind noch offene Protokollentscheidungen, keine bereits validierten Werte.

Das ergibt **5 × 5 × 50 × 5 = 6.250 Evaluationsepisoden** für einen finalen Checkpoint. Weitere Aufgaben, Dosen oder Zwischencheckpoints vervielfachen diesen Aufwand. Keine komplette große Rasterstudie vorsehen.

### Hauptmetrik, Interpretation und Unsicherheit

Primär ist die über beide Impulsrichtungen gleich gewichtete vollständige Task-Erfolgsrate im gemeinsamen Bewertungsfenster nach dem festen Eingriffszeitpunkt. Alle vorab festgelegten Starts bleiben im Nenner; technische oder physische Abbrüche getrennt dokumentieren, nicht still entfernen. Dieselben Startzustände und Störungszuordnungen über Arme und Seeds verwenden. Ein optionaler phasenabhängiger Recoverytest bleibt sekundär: Triggerquote und bedingte Recoveryrate zusätzlich zeigen, da unterschiedliche Triggerquoten dann einen Effekt erklären können.

Als praktische Zielgröße für H1 werden **mindestens +10 Prozentpunkte C3 gegen C2** und **höchstens 5 Prozentpunkte nominaler Verlust** vorgeschlagen. Diese Grenzen vor dem Haupttest mit der Betreuerin festlegen. Je Seed gepaarte Differenzen zeigen; näherungsweise Konfidenzintervalle mit Resampling von Trainingsseed und gemeinsamem Start als gekreuzten Faktoren, Paarungen und beide Störungsrichtungen erhalten. Fünf Seeds bleiben eine kleine Zahl; die Intervallabdeckung kann unsicher sein. In Woche 6 die erreichbare Präzision anhand des Entwicklungspiloten abschätzen, gegebenenfalls vor dem Test mehr Seeds festlegen oder das Ergebnis als explorativ einordnen. Keine Signifikanzrechnung, die alle Rollouts als unabhängige Trainingsläufe behandelt.

Positive Evidenz: geschätzter Störungsgewinn erreicht die praktische Zielgröße, das 95%-Intervall des Gewinns liegt über null und die untere Grenze der nominalen Differenz über -5 Prozentpunkten. Andernfalls zwischen gegenteiliger Evidenz und noch unklarer Präzision unterscheiden; ein nicht signifikanter Unterschied beweist keine Gleichwertigkeit. Ein kleiner Entwicklungspilot dient der Varianz-/Aufwandsabschätzung, nicht dem nachträglichen Verschieben des Ziels.

Sekundär: C3 gegen C0/C1; C3 gegen C4; gemessene Fehlerfortpflanzung nach 1/5/10 Schritten; Phasenfehler, aktive Lossabdeckung und gesamte Rechenkosten. Geringerer Zusatzloss oder Ein-Schritt-Fehler ersetzt keinen Taskerfolg. Schnellere Konvergenz ist kein Hauptversprechen; dazu wären getrennte Leistung-gegen-Update- und Leistung-gegen-Gesamtzeit-Kurven nötig.

**Auch negative Ergebnisse sind auswertbar:** C1 gleich gut und billiger: Zusatzmodell nicht gerechtfertigt. C3 verbessert die Näherung, aber nicht Taskerfolg: Mechanismus reicht nicht. C4 erreicht denselben Effekt: eine Erklärung über gezielte Gültigkeitsauswahl ist nicht gestützt. Modellprüfung scheitert: Grenzen des angenommenen Losses statt unbelegtem Verbesserungsanspruch dokumentieren.

## 6. Zwölf Wochen, mit und ohne Rechenzentrum

| Wochen | Arbeit und konkretes Ergebnis |
|---|---|
| 1-2, zuhause | Literaturmatrix, abgegrenzte Hypothese, Umgebung/Daten pinnen, unverändertes Lift-BC reproduzieren, Sensor-/Impulsprotokoll und Laufzeitpilot. Ergebnis: reproduzierbares Ausgangsprotokoll. |
| 3, zuhause | Getrennte A/B-Gegenprüfung, Abdeckung und Kosten messen; Entscheidung für Regularisierung oder Sensoralternative. Ergebnis: begründeter Methodenentscheid. |
| 4-5, zuhause | Gewählte Änderung integrieren; Parität bei lambda=0, Geometrie und Gradienten prüfen; begrenzter Pilot mit 3 Seeds und Entwicklungsstarts. Ergebnis: technisch geprüfte Methode. |
| 6, zuhause | Hyperparameter, primäre Metrik, Stichprobe und Teststarts sperren; Hauptlauf vorbereiten; ersten Methodik-/Literaturentwurf schreiben. Ergebnis: eingefrorenes Experimentpaket. |
| 7-8 | Finaler Lift-Vergleich mit 5 neuen Seeds. Ohne Cluster seriell lokal; mit Cluster dieselben Läufe parallel. Ergebnis: Rohdaten, Kosten, Unsicherheit. |
| 9 | Genau eine Erweiterung nur bei abgeschlossenem Kern: zweite Aufgabe oder zusätzliche Störungsstärke. Sonst Fehleranalyse und Replikation technischer Probleme. |
| 10-11 | Auswertung, Ergebnis- und Diskussionsteil; Annahmen und negative Ergebnisse erklären. Abbildungen und ausgewählte Rolloutvideos erstellen. |
| 12 | Text, Code und Reproduzierbarkeit prüfen; Vortrag proben; Zeitpuffer. |

Lokaler Audit: RTX 5070 mit ca. 12 GB VRAM, vorhandene Umgebung und Lift-Daten. Das genügt als plausible Planungsbasis für kleine State-BC-Experimente; neue konkrete Laufzeiten sind erst zu messen. Kein großes visuelles VLA-Training einplanen.

**Kostenformel:** 25 × Trainingszeit je Lauf + 6.250 × mittlere Episodenzeit + Kalibrierung + Auswertung. Beispiel zur Planung, keine Messung: 4 Sekunden pro Episode ergeben ca. 6,9 Stunden reine Evaluation; 10 Sekunden ergeben ca. 17,4 Stunden. Entwicklungsläufe kommen hinzu. Simulator-CPU, Renderkosten, Speicher und Parallelisierbarkeit können wichtiger sein als GPU-Speicher. Historische Kurzläufe sind kein verlässlicher End-to-End-Benchmark.

Der Cluster vergrößert nur Replikation oder Aufgabenabdeckung. Falls er ausfällt, bleibt eine vollständig abgeschlossene Lift-Studie mit sauberer Methodik das Mindestziel. State-Inputs, begrenzte Checkpointzahl und wenige repräsentative Videos halten Kosten klein.

## 7. Zwei Alternativen, die du mitbringen kannst

**Alternative B, geringeres Implementierungsrisiko: Zeitlich strukturierte Sensoraugmentation.** Hypothese: Bei gleichem marginalem Rauschniveau verbessert über kurze Zeitfenster konstanter EEF-Messbias die Robustheit gegen anhaltenden Testbias stärker als unabhängig pro Frame gezogenes Rauschen, ohne vergleichbaren Vorteil bei echten Aktionsimpulsen. BC-RNN verwenden, um Zeitstruktur überhaupt untersuchen zu können; identische Architektur und Fensterlängen in allen Armen. Beim rein zustandslosen MLP kann bei gleicher Randverteilung derselbe erwartete Trainingsloss entstehen: Dafür wäre der Zeitvergleich schlecht begründet. Arme: BC-RNN ohne Augmentation, mit unabhängigem Rauschen, mit konstantem Fensterbias. Verteilung/RMS, Featurekonsistenz, Sequenzsampling und Rechenbudget gleich halten. Beiträge: robomimic-Augmentationsmodul und Trennung von Messfehlerrobustheit und Recovery. Keine ungeprüfte Neuheitsbehauptung.

**Alternative C, geringstes Trainingsbudget: Replanning versus temporales Ensembling.** Hypothese: Häufigeres Feedback nach Störungen bringt einen größeren Erfolgsgewinn als reine Mittelung über vorhergesagte Aktionsfolgen. Vorhandene identische Direct-Checkpoints vergleichen: Ausführung von zwei Aktionen; eine Aktion ohne Mittelung; eine Aktion mit Mittelung. Gripperaktion separat behandeln; Inferenzzeit und vollständigen Taskerfolg messen. Die vorhandenen Chunks sind zeitlich um eine vergangene Aktion versetzt: Indizes ausdrücklich testen. Beitrag ist eine Ausführungsablation, deren Zulässigkeit als Projektkern die Betreuerin klären sollte. ACT und die 2026-Analysen sind relevante Vorarbeiten [S7-S8,S13].

**Auswahl:** A, wenn eine eigene Lernverfahrenserweiterung und Modellprüfung gewünscht sind. B, wenn ein überschaubarer Trainingsbeitrag mit geringerem Modellrisiko wichtiger ist. C, wenn Ausführung und empirische Mechanismen als Kern genügen. Keine dieser Alternativen zusätzlich als zweites Vollprojekt durchführen.

## 8. So kannst du die Idee vorstellen

### Etwa 90 Sekunden

> Ich möchte untersuchen, wann ein zusätzlicher dynamikbasierter Lernterm Behavioral Cloning robuster macht. BC lernt aus Expertendemonstrationen, trifft in der Ausführung aber auf leicht abweichende Zustände. Ein solcher Zusatzterm soll korrigierende Aktionen fördern. Das funktioniert jedoch nur dann sinnvoll, wenn die angenommene lokale Dynamik stimmt.
>
> In meinen vorhandenen Lift-Vorarbeiten sehe ich einen positiven Vergleich zur BC-Baseline, aber spätere Prüfungen zeigen Fehler in der Dynamiknäherung. Deshalb möchte ich zuerst diese Annahmen prüfen und dann eine anhand der Modellgültigkeit gewichtete Variante mit derselben ungewichteten Methode, reinem BC und einfacher Sensoraugmentation vergleichen.
>
> Die Hauptmessung ist vollständiger Aufgabenerfolg nach echten Störungen; Messfehler prüfe ich getrennt. Ich starte auf Lift mit Zustandsmerkmalen auf meinem PC. Nach drei Wochen ist eine Entscheidung vorgesehen, ob die Dynamikvariante tragfähig ist. Falls nicht, untersuche ich die zeitliche Struktur von Sensoraugmentation. Der Kern braucht keinen Cluster; ab der zweiten Hälfte könnte ich dort zusätzliche Seeds oder eine zweite Aufgabe auswerten.

### Gesprächsablauf für ungefähr 15 Minuten

1. Zwei Minuten: Problem, Leitfrage und Hypothese.
2. Drei Minuten: Stand der Forschung und historische Lift-Grafik.
3. Vier Minuten: Kontrollarme, Sensor-/Störungsunterschied und Hauptmetrik.
4. Zwei Minuten: Zwölf-Wochen-Plan und Entscheidung nach Woche 3.
5. Vier Minuten: Beitrag, Umfang und Rahmen mit der Betreuerin vereinbaren.

### Diese Entscheidungen mitnehmen

- Genügt eine begründete Adaption mit sauberer Ablation, oder wird ein stärkerer methodischer Neuheitsbeitrag erwartet?
- Ist simulationsgestützte Dynamikidentifikation erlaubt, oder soll der Datenzugang strikt offline bleiben?
- Reicht eine gründliche Aufgabe als Mindestumfang? Welche zweite Aufgabe wäre fachlich sinnvoll?
- Ist ein klar begründetes negatives Ergebnis beziehungsweise der Wechsel zu Alternative B akzeptabel?
- Welche GPU-/CPU-Ressourcen, Laufzeitlimits und Softwareumgebung sind ab ungefähr Woche 7 tatsächlich verfügbar?
- Wann sollen Zwischenstand, Rohfassung und Abschlusspräsentation besprochen werden?

## 9. Grafiken und Videos richtig einsetzen

Die neuen Medien im Unterordner `media` erklären Sensorfehler versus echte Zustandsabweichung; die Animation ist ausdrücklich schematisch und enthält keine gemessenen Erfolge. Die historische Lift-Grafik zeigt echte Seedwerte aus [L2].

Die Datei `Medien_und_Quellen.md` enthält zusätzlich ausgewählte vorhandene Stack-Replays und externe Autoren-Demovideos. Lokale Stack-Replays zeigen eine andere Aufgabe mit programmierten Demos. Sie illustrieren Verhalten, belegen aber weder die neue Hypothese noch einen allgemeinen Vorteil von Direct gegenüber Diffusion. Ein Erfolgsvideo zusammen mit einem Misserfolg derselben Methode zeigen; die quantitativen Ergebnisse bleiben maßgeblich.

## 10. Quellen

### Originalarbeiten und offizielle Dokumentation

- **[S1]** Mandlekar et al. *What Matters in Learning from Offline Human Demonstrations for Robot Manipulation.* CoRL 2021, PMLR 164 (2022). https://proceedings.mlr.press/v164/mandlekar22a.html
- **[S2]** robomimic, offizielle Algorithmen- und Datensatzdokumentation, am 12.10.2026 geprüft. https://robomimic.github.io/docs/introduction/implemented_algorithms.html ; https://robomimic.github.io/docs/datasets/robomimic_v0.1.html ; https://github.com/ARISE-Initiative/robomimic
- **[S3]** Mehta et al. *Stable-BC: Controlling Covariate Shift with Stable Behavior Cloning.* IEEE RA-L, 2025; Preprint 2024. https://collab.me.vt.edu/Stable-BC/ ; https://arxiv.org/abs/2408.06246
- **[S4]** Ke et al. *CCIL: Continuity-based Data Augmentation for Corrective Imitation Learning.* ICLR 2024; Preprint 2023, aktualisiert 2024. https://arxiv.org/abs/2310.12972
- **[S5]** Deshpande et al. *Data Efficient Behavior Cloning for Fine Manipulation via Continuity-based Corrective Labels.* IROS 2024, laut Autorenangabe. https://arxiv.org/abs/2405.19307
- **[S6]** Chi et al. *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion.* RSS 2023. https://diffusion-policy.cs.columbia.edu/
- **[S7]** Lazzati et al. *Why Does Action Chunking Improve Behavioral Cloning Performance in Robotic Control?* Preprint, 03.08.2026. https://arxiv.org/abs/2608.02547
- **[S8]** Goyal. *Measuring the Stability Assumption Behind Action Chunking.* Preprint, 01.10.2026. https://arxiv.org/abs/2610.01626
- **[S9]** Abyaneh et al. *Contractive Dynamical Imitation Policies for Efficient Out-of-Sample Recovery.* ICLR 2025. https://arxiv.org/abs/2412.07544
- **[S10]** Abyaneh et al. *Contractive Diffusion Policies.* ICLR 2026. https://proceedings.iclr.cc/paper_files/paper/2026/hash/1dec73169509c223220744b2c9b2df37-Abstract-Conference.html
- **[S11]** Ross et al. *A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning.* AISTATS 2011. https://proceedings.mlr.press/v15/ross11a.html
- **[S12]** Laskey et al. *DART: Noise Injection for Robust Imitation Learning.* CoRL 2017. https://proceedings.mlr.press/v78/laskey17a.html
- **[S13]** Zhao et al. *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware.* RSS 2023 (ACT). https://www.roboticsproceedings.org/rss19/p016.html

### Lokale Evidenz, gelesen am 12.10.2026

- **[L1]** `FORSCHUNGSPLAN.md`, Stand 04.10.2026: Ziel, Vorarbeiten und priorisierte Fragestellungen.
- **[L2]** `praxis/reports/lift_ph_full_100ep_summary.json`: historische 10.000-Update-Lift-Ergebnisse mit drei Trainingsseeds.
- **[L3]** `experiments/lift_contraction_validity_20261004/supervised_6h_20261004_0904/SESSION_RESEARCH_REPORT.md`: Sensorpilot, Mechanismusprüfungen, gescheiterte Fehlerhülle und Status der untrainierten Lossreferenz.
- **[L4]** `experiments/stack_replication_20261001/ERGEBNISSE.md` und `representative/manifest.json`: Stack-Ergebnisse und Herkunft der Replays.

Die lokalen Vorarbeiten ersetzen keinen neuen eingefrorenen Bestätigungstest. Diese Vorbereitung hat keine bestehenden Forschungsdateien geändert und keine Trainings gestartet.
