# Thematisches Claim-Register

Alle Aussagen und Paraphrasen in den Einträgen sind **A: Quellenaussagen**. Kapitelpositionen sind **B: redaktionelle Verwendungsvorschläge**. **C: Projektbefunde** stehen getrennt in [relation_to_our_results.md](comparisons/relation_to_our_results.md). Klassen und Seitenkonvention: [INDEX.md](INDEX.md).

Primärquelle bedeutet hier die Originalautoren; bei `P-` stammt die geprüfte Evidenz ausschließlich aus einem Preprint. Keine Journal-Garantie aus diesen Stellen ableiten. Zahlen sind Autorenangaben, keine neu berechneten Projektergebnisse.

## Behavioural Cloning

<a id="dag-01"></a>
### DAG-01

- **ID:** `DAG-01`
- **Aussage (A):** Klassisches BC minimiert den Imitationsverlust unter der Zustandsverteilung des Experten.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2) / [eingefrorenes PDF](_research/dagger.pdf#page=2)
- **Seite:** PDF S. 2; **Abschnitt:** §2.1; Gl. (2)
- **Evidenzklasse:** M
- **Paraphrase (A):** Das überwachte Lernziel gewichtet Zustände, die der Expert besucht. Die durch die gelernte Policy selbst erzeugte Zustandsverteilung steht nicht im BC-Ziel.
- **Mögliche Kapitelposition (B):** Grundlagen: BC-Lernziel und Unterschied zwischen Training und Ausführung.

<a id="dart-01"></a>
### DART-01

- **ID:** `DART-01`
- **Aussage (A):** DART trennt Ausführungsfehler in einen Verteilungsverschiebungsanteil und den Loss auf Expertendaten.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=4) / [eingefrorenes PDF](_research/dart.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §3; Zerlegung Shift/Loss
- **Evidenzklasse:** M
- **Paraphrase (A):** Zur BC-Testabweichung wird der Verlust unter Expertentrajektorien addiert und subtrahiert. Der verbleibende Unterschied der Erwartungen beschreibt den Shift-Anteil. DART zielt auf diesen Teil, nicht ausschließlich auf kleineren Trainingsloss.
- **Mögliche Kapitelposition (B):** Grundlagen: Offline-Loss und Closed-Loop-Verhalten.

<a id="sbc-02"></a>
### SBC-02

- **ID:** `SBC-02`
- **Aussage (A):** Stable-BC trennt beobachtbaren Roboterzustand x und Umgebungszustand y und setzt bekannte Roboterdynamik f voraus.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=2) / [eingefrorenes PDF](_research/stable_bc.pdf#page=2)
- **Seite:** PDF S. 2; **Abschnitt:** §III; Robot, Environment, Gl. (1)
- **Evidenzklasse:** P-M
- **Paraphrase (A):** Die Policy π(x,y) imitiert Aktionen. Die Umgebung folgt g(x,y,u); g darf im sogenannten modellfreien Fall unbekannt sein. Die Annahme eines genauen f bleibt bestehen und ist nicht gleichbedeutend mit dynamikfreiem Lernen.
- **Mögliche Kapitelposition (B):** Methoden/Voraussetzungen: präzise Bedeutung von model-free.

## Covariate Shift

<a id="dag-02"></a>
### DAG-02

- **ID:** `DAG-02`
- **Aussage (A):** Das eigentliche Imitationsziel verwendet die von der jeweiligen Policy induzierte Verteilung.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2) / [eingefrorenes PDF](_research/dagger.pdf#page=2)
- **Seite:** PDF S. 2; **Abschnitt:** §2; Gl. (1)
- **Evidenzklasse:** M
- **Paraphrase (A):** Die Policy beeinflusst durch ihre Aktionen die späteren Eingaben. Deshalb hängen Verlust und Zustandsverteilung gemeinsam von der Policy ab; auch bei konvexem punktweisem Loss ist das Gesamtziel nicht notwendig konvex.
- **Mögliche Kapitelposition (B):** Problemstellung: policyabhängige Zustandsverteilung.

<a id="dart-02"></a>
### DART-02

- **ID:** `DART-02`
- **Aussage (A):** DART stört ausgeführte Expertenaktionen während der Datenerhebung und lernt die Expertenreaktion in den so erreichten Zuständen.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=4) / [eingefrorenes PDF](_research/dart.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §4; Gl. (2)
- **Evidenzklasse:** M
- **Paraphrase (A):** Die Supervisorausführung erhält Rauschen; dadurch muss der Expert tatsächlich korrigieren. Supervision ist weiterhin die ungestörte Expertenaktion am erreichten Zustand. Das Verfahren erweitert reale Trajektorien und ist keine nachträgliche Eingabeaugmentation mit unveränderten Labels.
- **Mögliche Kapitelposition (B):** Methoden: genaue Stelle der Störung und Herkunft der Korrekturlabels.

<a id="dart-03"></a>
### DART-03

- **ID:** `DART-03`
- **Aussage (A):** Bei punktweisem Loss in [0,1] wird der Erwartungsunterschied durch T√(DKL/2) begrenzt.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=5) / [eingefrorenes PDF](_research/dart.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §4; Lemma 4.1
- **Evidenzklasse:** T
- **Paraphrase (A):** Der KL-Term vergleicht die Trajektorienverteilung der Lernpolicy mit der des gestörten Supervisors. Der Bound motiviert Verteilungsanpassung, misst aber nicht unmittelbar die Erfolgsrate eines Tasks.
- **Mögliche Kapitelposition (B):** Theorie: Rolle des KL-Bounds und beschränkten Loss.

<a id="sbc-05"></a>
### SBC-05

- **ID:** `SBC-05`
- **Aussage (A):** Die modellfreie Analyse nimmt eine Schranke ε für die Abweichung des Umgebungszustands an.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=4) / [eingefrorenes PDF](_research/stable_bc.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §IV-C; Bounded Stability, Gl. (8)–(10)
- **Evidenzklasse:** P-T
- **Paraphrase (A):** Ohne g stabilisiert sie nicht die vollständige gekoppelte Matrix. Die Roboterdynamik erhält einen Störungseingang A₂e_y. Der im Text angegebene Bound hängt von A₂, der Umgebungsabweichung und der Zeitentwicklung des Robotersystems ab.
- **Mögliche Kapitelposition (B):** Theorie/Limitationen: zusätzliche Annahme über Umgebungsabweichungen.

## Error Accumulation

<a id="dag-03"></a>
### DAG-03

- **ID:** `DAG-03`
- **Aussage (A):** Für einen geeigneten 0–1-Surrogatverlust und beschränkte Taskkosten gilt der Worst-Case-BC-Bound J(π) ≤ J(π*) + T²ε.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2) / [eingefrorenes PDF](_research/dagger.pdf#page=2)
- **Seite:** PDF S. 2; **Abschnitt:** §2.1; Theorem 2.1
- **Evidenzklasse:** T
- **Paraphrase (A):** Der Bound verwendet ε unter Expertenzuständen und Kosten in [0,1]. Die Autoren nennen ihn tight: geeignete Probleme können quadratischen zusätzlichen Aufwand zeigen. Er ist keine Vorhersage jeder empirischen Lernkurve.
- **Mögliche Kapitelposition (B):** Theorie: bedingter Worst-Case-Bound; keine direkte Umrechnung von MSE.

<a id="dag-04"></a>
### DAG-04

- **ID:** `DAG-04`
- **Aussage (A):** Kleiner Imitationsverlust unter der eigenen Zustandsverteilung erlaubt einen Bound mit uTε.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=3) / [eingefrorenes PDF](_research/dagger.pdf#page=3)
- **Seite:** PDF S. 3; **Abschnitt:** §2.2; Theorem 2.2
- **Evidenzklasse:** T
- **Paraphrase (A):** u begrenzt die zusätzliche Expert-Cost-to-go einer falschen Aktion. Der Taskkostenbound ist J(π) ≤ J(π*) + uTε. Die Autoren weisen darauf hin, dass u im Worst Case selbst O(T) sein kann.
- **Mögliche Kapitelposition (B):** Theorie: Voraussetzungen einer linear in T formulierten Aussage.

<a id="sbc-03"></a>
### SBC-03

- **ID:** `SBC-03`
- **Aussage (A):** Die kontinuierliche Fehlerdynamik wird um einen demonstrierten Zustand linearisiert.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=3) / [eingefrorenes PDF](_research/stable_bc.pdf#page=3)
- **Seite:** PDF S. 3; **Abschnitt:** §IV-A; Gl. (2)–(6)
- **Evidenzklasse:** P-T
- **Paraphrase (A):** Der gemeinsame Fehler z enthält Abweichungen in x und y. Sein Jacobian A umfasst Ableitungen von f, g und π. Die Analyse beschreibt lokale Trajektorienabweichungen, keine globale Rückkehrgarantie aus beliebigen Fehlerzuständen.
- **Mögliche Kapitelposition (B):** Theorie: lokale Linearisierung statt globaler Stabilitätsbehauptung.

## Robustness

<a id="dag-07"></a>
### DAG-07

- **ID:** `DAG-07`
- **Aussage (A):** Unter den Reduktionsannahmen existiert eine gute Policy in der erzeugten Kandidatenfolge.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4) / [eingefrorenes PDF](_research/dagger.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §3; Theoreme 3.1–3.2
- **Evidenzklasse:** T
- **Paraphrase (A):** Im unendlichen Stichprobenfall und unter stark konvexem, beschränktem Loss sowie geeigneter β-Abnahme findet sich bei genügend Runden ein Kandidat mit kleinem Loss unter seiner eigenen Verteilung. Die Aussage garantiert nicht automatisch den letzten Kandidaten.
- **Mögliche Kapitelposition (B):** Theorie/Diskussion: Geltungsbereich der DAgger-Garantie.

<a id="dart-04"></a>
### DART-04

- **ID:** `DART-04`
- **Aussage (A):** DART schätzt eine Aktionsfehlerkovarianz und skaliert sie über den erwarteten Gesamtfehler α.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=5) / [eingefrorenes PDF](_research/dart.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §4.1; Gl. (3)–(4) und Gauß-Lösung
- **Evidenzklasse:** M
- **Paraphrase (A):** Die äußeren Produkte von Policy-minus-Expert-Aktionsfehlern ergeben eine Kovarianzschätzung unter gestörter Supervisorausführung. Für Gaußrauschen wird sie mit α/(T tr(Σ̂)) multipliziert. Die Kovarianzrichtung und die Gesamtstärke sind getrennte Entscheidungen.
- **Mögliche Kapitelposition (B):** Methoden: adaptive Störungsverteilung statt beliebiger Noise-Stärke.

<a id="dart-05"></a>
### DART-05

- **ID:** `DART-05`
- **Aussage (A):** Die theoretische KL-Aussage setzt einen deterministischen, vom Rauschen unbeeinflussten Supervisor voraus.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=6) / [eingefrorenes PDF](_research/dart.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §4.2; Proposition 4.1 und Diskussion
- **Evidenzklasse:** T
- **Paraphrase (A):** Gaußrauschen erweitert den Aktionssupport gegenüber dem deterministischen Expert bei nichtverschwindendem Policyfehler. Die Autoren schränken ausdrücklich ein, dass menschliche Supervisors ihr Verhalten durch Rauschen ändern können; perfekte Expert-Repräsentation bietet keinen erwarteten Zusatznutzen.
- **Mögliche Kapitelposition (B):** Theorie/Limitationen: Support-Argument und menschlicher Supervisor.

<a id="dart-09"></a>
### DART-09

- **ID:** `DART-09`
- **Aussage (A):** Die Autoren vermuten bei DART-6 eine für den menschlichen Supervisor zu große Störung.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=8) / [eingefrorenes PDF](_research/dart.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §5.2; letzter Ergebnisabsatz
- **Evidenzklasse:** H
- **Paraphrase (A):** DART-6 liegt unter DART-3, aber über BC. Die Erklärung durch übermäßiges Rauschen wird als mögliche Deutung formuliert; der Versuch isoliert keine universelle optimale Rauschstärke.
- **Mögliche Kapitelposition (B):** Diskussion: beobachteter Effekt versus erklärende Hypothese.

<a id="dart-10"></a>
### DART-10

- **ID:** `DART-10`
- **Aussage (A):** Passend skalierte zufällige Kovarianzen können in den Zusatzversuchen ähnlich gut wie DART funktionieren.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=13) / [eingefrorenes PDF](_research/dart.pdf#page=13)
- **Seite:** PDF S. 13; **Abschnitt:** Appendix §4.4; Random Covariance Matrices
- **Evidenzklasse:** E
- **Paraphrase (A):** Die Autoren variieren die Spur von Wishart-gezogenen Kovarianzen. Angemessener simulierter Fehler reduziert Shift auch ohne DART-Kovarianzrichtung; sehr hohe oder niedrige Stärken verschlechtern den Loss. Die richtige Stärke ist vorab nicht allgemein bekannt.
- **Mögliche Kapitelposition (B):** Diskussion: keine universelle Überlegenheit optimierter Kovarianz behaupten.

<a id="sbc-01"></a>
### SBC-01

- **ID:** `SBC-01`
- **Aussage (A):** Stable-BC motiviert Robustheit durch lokale Nähe zu demonstrierten Verhaltensabläufen.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=1) / [eingefrorenes PDF](_research/stable_bc.pdf#page=1)
- **Seite:** PDF S. 1; **Abschnitt:** §I; hervorgehobene Hypothese
- **Evidenzklasse:** P-H
- **Paraphrase (A):** Die Autoren erwarten geringere Fehlerakkumulation, wenn Trajektorien nicht weiter aus der Datenregion driften, sondern zu dort demonstrierten Abläufen hingezogen werden. Das ist die Motivation des Stabilitätslosses, noch keine universelle Garantie.
- **Mögliche Kapitelposition (B):** Motivation: Stabilität als alternativer Mechanismus.

<a id="sbc-04"></a>
### SBC-04

- **ID:** `SBC-04`
- **Aussage (A):** Der modellbasierte Loss ergänzt Aktionsimitation um positive Realteile der Eigenwerte von A.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=4) / [eingefrorenes PDF](_research/stable_bc.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §IV-B; Gl. (7)
- **Evidenzklasse:** P-M
- **Paraphrase (A):** Instabile lokale Modi werden mit ReLU(Re(σ)) bestraft. Das BC-Ziel bleibt notwendig, weil reine Stabilisierung nach der Autorendiskussion keine richtige Aufgabenlösung sicherstellt.
- **Mögliche Kapitelposition (B):** Methoden: Stabilitätsregularisierung und Taskperformance trennen.

<a id="sbc-06"></a>
### SBC-06

- **ID:** `SBC-06`
- **Aussage (A):** Der modellfreie Loss kombiniert BC, kleine Umgebungskopplung und Stabilisierung des Roboterblocks A₁.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=5) / [eingefrorenes PDF](_research/stable_bc.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §IV-C; Gl. (11) und erster Absatz danach
- **Evidenzklasse:** P-M
- **Paraphrase (A):** λ₁ gewichtet die Norm von A₂, λ₂ die positiven Eigenwertrealteile von A₁. Die Autoren nennen diese Aussage schwächer als die modellbasierte: nur Roboterfehler unter begrenztem Umgebungsfehler werden behandelt.
- **Mögliche Kapitelposition (B):** Methoden: Original-Loss und Geltungsbereich.

<a id="sbc-10"></a>
### SBC-10

- **ID:** `SBC-10`
- **Aussage (A):** Die Reduktion von A₂ kann die notwendige Reaktion auf die Umgebung abschwächen.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=4) / [eingefrorenes PDF](_research/stable_bc.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §IV-C; Stability vs. Performance
- **Evidenzklasse:** P-L
- **Paraphrase (A):** Geht die Umgebungskopplung gegen null, verliert die Policy ihre Abhängigkeit von y. Das hilft der Entkopplung der Fehler, kann aber Aufgaben wie das Verfolgen des Pucks verhindern. Die Autoren behandeln dies als Trade-off mit BC.
- **Mögliche Kapitelposition (B):** Diskussion: Robustheit und erforderliche Zustandsreaktion.

<a id="act-10"></a>
### ACT-10

- **ID:** `ACT-10`
- **Aussage (A):** ACT scheitert in zusätzlich berichteten Versuchen an Candy-Unwrapping und mehreren Schritten eines kleinen Ziploc-Bags.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=17) / [eingefrorenes PDF](_research/act.pdf#page=17)
- **Seite:** PDF S. 17; **Abschnitt:** Appendix F; Policy Learning Limitations
- **Evidenzklasse:** L
- **Paraphrase (A):** Bei Candy-Unwrapping nach fünfzig Demos gelingt das vollständige Auspacken zunächst in null von zehn Tests, obwohl Teilphasen gelingen. Die Autoren nennen Wahrnehmung und fehlende Daten als Erklärungen; Mehrfachversuche pro Candy sind ein anderes Erfolgsprotokoll.
- **Mögliche Kapitelposition (B):** Limitationen: Teilphasenerfolg, Perzeption und Datenmenge.

<a id="dp-07"></a>
### DP-07

- **ID:** `DP-07`
- **Aussage (A):** Der Ausführungshorizont enthält einen empirischen Trade-off zwischen Konsistenz und Reaktionsfähigkeit.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=7) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=7)
- **Seite:** PDF S. 7; **Abschnitt:** §V-C; Tradeoff in action horizon, Abb. 6
- **Evidenzklasse:** E
- **Paraphrase (A):** Mehr als eine ausgeführte Aktion hilft der Konsistenz, zu lange offene Ausführung verschlechtert die Reaktion. Acht Schritte sind in den meisten untersuchten Tasks günstig. Das ist keine allgemeine optimale Wahl für jede Frequenz und jede Datenquelle.
- **Mögliche Kapitelposition (B):** Diskussion: Replanning und Feedbackintervall.

<a id="dp-08"></a>
### DP-08

- **ID:** `DP-08`
- **Aussage (A):** Die gezeigten Push-T-Störungsreaktionen wurden in einer separaten Episode außerhalb der quantitativen Haupttabelle untersucht.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=8) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §VI-A; Robustness against perturbation
- **Evidenzklasse:** Q
- **Paraphrase (A):** Die Autoren zeigen Reaktionen auf Kameraokklusion und verschobene Blöcke. Sie formulieren dies als Hinweis auf neu kombinierbares Verhalten; daraus folgt keine Erfolgsrate über eine standardisierte Störungsverteilung.
- **Mögliche Kapitelposition (B):** Evaluation: qualitative Recovery von Robustheitsstatistik trennen.

## Interactive Imitation Learning

<a id="dag-05"></a>
### DAG-05

- **ID:** `DAG-05`
- **Aussage (A):** DAgger aggregiert Expert-Labels für unter der aktuellen Ausführungspolicy besuchte Zustände.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4) / [eingefrorenes PDF](_research/dagger.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §3; Algorithmus 3.1
- **Evidenzklasse:** M
- **Paraphrase (A):** Jede Runde sammelt neue Trajektorien, annotiert deren Zustände mit Expertenaktionen, vereinigt alte und neue Daten und trainiert erneut. Der zurückgegebene Kandidat wird im Algorithmus anhand von Validation ausgewählt.
- **Mögliche Kapitelposition (B):** Methoden: Ablauf und Unterschied zu einem festen Offline-Datensatz.

<a id="dag-06"></a>
### DAG-06

- **ID:** `DAG-06`
- **Aussage (A):** Eine optionale Mischung mit dem Experten beeinflusst die Zustände der Datenerhebung.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4) / [eingefrorenes PDF](_research/dagger.pdf#page=4)
- **Seite:** PDF S. 4; **Abschnitt:** §3; Absatz zur Expert-Mischung
- **Evidenzklasse:** M
- **Paraphrase (A):** π_i = β_iπ* + (1−β_i)π̂_i verwendet den Experten nur für einen Anteil der ausgeführten Aktionen. Diese Mischung betrifft die Erhebung; Expert-Labels werden weiterhin für die besuchten Zustände benötigt. Der mittlere Expert-Anteil soll langfristig verschwinden.
- **Mögliche Kapitelposition (B):** Methoden: Ausführungspolicy und Label-Oracle getrennt erläutern.

<a id="dag-10"></a>
### DAG-10

- **ID:** `DAG-10`
- **Aussage (A):** Die Reduktion benötigt eine stärkere Lernannahme als bloße Verfügbarkeit eines Klassifikators.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=5) / [eingefrorenes PDF](_research/dagger.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §4.2; Absatz vor Finite Sample Case
- **Evidenzklasse:** L
- **Paraphrase (A):** Die Autoren verlangen ein No-Regret-Verfahren oder einen stark konvexen Surrogatverlust und grenzen dies von allgemeineren Klassifikationsreduktionen ab. Daraus folgt keine automatische theoretische Absicherung beliebigen neuronalen Trainings.
- **Mögliche Kapitelposition (B):** Limitationen: Lernannahmen und Abgrenzung zum Projekt.

## Action Chunking

<a id="act-01"></a>
### ACT-01

- **ID:** `ACT-01`
- **Aussage (A):** ACT sagt k zukünftige Aktionen gemeinsam voraus und motiviert dies durch einen k-fach verkürzten effektiven Entscheidungshorizont.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=5) / [eingefrorenes PDF](_research/act.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §IV-A; erster Methodenabsatz
- **Evidenzklasse:** M
- **Paraphrase (A):** Der Chunk wird aus einer aktuellen Beobachtung erzeugt. Die Autoren verbinden die Sequenzvorhersage mit geringerer Fehlerakkumulation und dem Modellieren zeitlich zusammenhängender Pausen innerhalb eines Chunks. Es ist keine neue globale Fehlergarantie bewiesen.
- **Mögliche Kapitelposition (B):** Methoden: Motivation und Reichweite von Chunking.

<a id="act-02"></a>
### ACT-02

- **ID:** `ACT-02`
- **Aussage (A):** ACT kombiniert überlappende Vorhersagen für denselben Ausführungszeitpunkt.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=5) / [eingefrorenes PDF](_research/act.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §IV-A; Temporal Ensemble
- **Evidenzklasse:** M
- **Paraphrase (A):** Die Policy wird jedes Zeitschritt erneut abgefragt. Alle Vorhersagen für Zeitpunkt t werden exponentiell gewichtet gemittelt; im Paper ist i=0 ausdrücklich die älteste Vorhersage. Benachbarte Zeitpunkte werden nicht einfach zeitlich geglättet.
- **Mögliche Kapitelposition (B):** Methoden: exakte Ausrichtungs- und Gewichtungsregel.

<a id="act-08"></a>
### ACT-08

- **ID:** `ACT-08`
- **Aussage (A):** In der Chunking-Ablation steigt die über vier Simulationsbedingungen gemittelte ACT-Leistung von 1 % bei k=1 auf 44 % bei k=100.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=10) / [eingefrorenes PDF](_research/act.pdf#page=10)
- **Seite:** PDF S. 10; **Abschnitt:** §VI-A; Ablations, Abb. 9(a)–(b)
- **Evidenzklasse:** E
- **Paraphrase (A):** Temporales Ensembling ist für diese k-Ablation ausgeschaltet; für längere, nahezu offene Chunks nimmt die Leistung wieder etwas ab. Die separate Ensembling-Ablation wird eigenständig getunt und berichtet +3,3 Prozentpunkte für ACT; VINN profitiert nicht.
- **Mögliche Kapitelposition (B):** Ablationen: Chunking und Ensembling als getrennte Faktoren.

<a id="dp-02"></a>
### DP-02

- **ID:** `DP-02`
- **Aussage (A):** Diffusion Policy unterscheidet Beobachtungs-, Vorhersage- und Ausführungshorizont.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=3)
- **Seite:** PDF S. 3; **Abschnitt:** §II-C; Closed-loop action-sequence prediction
- **Evidenzklasse:** M
- **Paraphrase (A):** O_t enthält T_o Beobachtungen, der Generator erzeugt T_p Aktionen und der Roboter führt T_a davon vor erneutem Planen aus. Ein langer vorhergesagter Chunk bedeutet deshalb nicht, dass ebenso lange ohne neue Beobachtung gehandelt wird.
- **Mögliche Kapitelposition (B):** Methoden: getrennte Horizonte und Receding Horizon.

## Generative Policies

<a id="act-03"></a>
### ACT-03

- **ID:** `ACT-03`
- **Aussage (A):** ACT nutzt ein CVAE-Trainingsziel, dekodiert im beschriebenen Testprotokoll aber deterministisch mit z=0.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=6) / [eingefrorenes PDF](_research/act.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §IV-B; CVAE-Beschreibung
- **Evidenzklasse:** M
- **Paraphrase (A):** Der Encoder erhält propriozeptive Beobachtung und Zielchunk, erzeugt eine diagonale Gaußverteilung über z und wird nach dem Training verworfen. Die Testpolicy erhält aktuelle Beobachtungen sowie den Mittelwert des Priors; generatives Training bedeutet hier keine zufällige Testaktion.
- **Mögliche Kapitelposition (B):** Methoden: Training und Inferenz einer generativen Policy.

<a id="act-04"></a>
### ACT-04

- **ID:** `ACT-04`
- **Aussage (A):** Die konkrete ACT-Beschreibung verwendet absolute Gelenkzielpositionen, vier RGB-Ansichten und L1-Rekonstruktion.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=6) / [eingefrorenes PDF](_research/act.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §IV-C; Implementing ACT, Algorithmus 1
- **Evidenzklasse:** M
- **Paraphrase (A):** Pro Schritt werden vier 480×640-Bilder und vierzehn Gelenk-/Greiferwerte verarbeitet, pro Chunk k×14 Gelenkziele ausgegeben. Die Autoren nennen L1 im Implementierungstext; Algorithmus 1 nennt dagegen MSE. Diese Inkonsistenz wird nicht stillschweigend aufgelöst.
- **Mögliche Kapitelposition (B):** Methoden/Reproduzierbarkeit: Modalität, Steuerraum und Loss.

<a id="act-09"></a>
### ACT-09

- **ID:** `ACT-09`
- **Aussage (A):** Das Entfernen des CVAE-Ziels wirkt in der ACT-Ablation bei menschlichen Daten stark, bei geskripteten Daten kaum.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=10) / [eingefrorenes PDF](_research/act.pdf#page=10)
- **Seite:** PDF S. 10; **Abschnitt:** §VI-B; Abb. 9(c)
- **Evidenzklasse:** E
- **Paraphrase (A):** Über zwei Simulationsaufgaben sinkt die gemittelte Leistung mit menschlichen Daten ohne CVAE von 35,3 % auf 2 %. Bei vollständig deterministischen Scriptdaten beschreiben die Autoren fast keinen Unterschied. Die Aussage ist ausdrücklich datenquellenabhängig.
- **Mögliche Kapitelposition (B):** Diskussion: generatives Ziel bei menschlichen versus programmierten Demos.

<a id="dp-01"></a>
### DP-01

- **ID:** `DP-01`
- **Aussage (A):** Diffusion Policy modelliert p(A_t|O_t) durch konditioniertes Denoising von Aktionssequenzen.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=3)
- **Seite:** PDF S. 3; **Abschnitt:** §II-C; Gl. (4)–(5)
- **Evidenzklasse:** M
- **Paraphrase (A):** Die Beobachtung ist eine Bedingung für die Rauschvorhersage und wird nicht selbst als zukünftiger Zustand generiert. Training lernt injiziertes Rauschen; Inferenz startet mit Gaußrauschen und verfeinert den gesamten Aktionschunk iterativ.
- **Mögliche Kapitelposition (B):** Methoden: Aktionsdiffusion versus gemeinsame Zustands-/Aktionsgenerierung.

<a id="dp-03"></a>
### DP-03

- **ID:** `DP-03`
- **Aussage (A):** Die Autoren berichten Schwierigkeiten des temporalen CNN bei abrupt und schnell wechselnden Aktionsfolgen.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=3)
- **Seite:** PDF S. 3; **Abschnitt:** §III-A; CNN-based Diffusion Policy
- **Evidenzklasse:** L
- **Paraphrase (A):** Als mögliche Erklärung nennen sie eine Präferenz zeitlicher Faltungen für niedrige Frequenzen. Das ist eine modellbezogene Hypothese zu beobachtetem Verhalten, kein nachgewiesener Mechanismus für jeden UNet-Fehlschlag.
- **Mögliche Kapitelposition (B):** Diskussion: Architekturabhängigkeit und Grenze kausaler Erklärungen.

<a id="dp-04"></a>
### DP-04

- **ID:** `DP-04`
- **Aussage (A):** Die Score-Modellierung vermeidet die Schätzung des Aktionsnormalisierers, die bei den verglichenen Energy-Based-Policies erforderlich ist.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=5) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=5)
- **Seite:** PDF S. 5; **Abschnitt:** §IV-D; Gl. (6)–(8)
- **Evidenzklasse:** M
- **Paraphrase (A):** Der Normalisierer Z(o,θ) hängt nicht von der Aktion ab und verschwindet bei der Ableitung nach a. Die Autoren nutzen dies zur Erklärung stabileren Trainings gegenüber IBC. Die Aussage betrifft Optimierung, nicht eine garantierte stabilisierte Roboterdynamik.
- **Mögliche Kapitelposition (B):** Methoden/Diskussion: Trainingsstabilität von Regelungsstabilität unterscheiden.

<a id="dp-10"></a>
### DP-10

- **ID:** `DP-10`
- **Aussage (A):** Diffusion Policy behält BC-Datengrenzen und verursacht höhere Inferenzkosten als einfachere Policies.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=11) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=11)
- **Seite:** PDF S. 11; **Abschnitt:** §VIII; Limitations and Future Work
- **Evidenzklasse:** L
- **Paraphrase (A):** Unzureichende Demos begrenzen die Performance; iterative Generierung kostet Rechenzeit und Latenz. Aktionssequenzen mildern den Aufwand nur teilweise, besonders bei hoher erforderlicher Regelungsrate. Die Autoren behaupten keine allgemeine Aufhebung von Covariate Shift.
- **Mögliche Kapitelposition (B):** Limitationen: Datenabhängigkeit und Rechenaufwand.

## Evaluation

<a id="dag-08"></a>
### DAG-08

- **ID:** `DAG-08`
- **Aussage (A):** Im SuperTuxKart-Versuch berichten die Autoren nach 15 DAgger-Runden eine Policy ohne Sturz von der Strecke.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=6) / [eingefrorenes PDF](_research/dagger.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §5.1; Abb. 2 und Ergebnisabsatz
- **Evidenzklasse:** E
- **Paraphrase (A):** Die gemessene Größe sind mittlere Stürze pro Runde auf Star Track. Pro Trainingsiteration wird etwa eine Runde mit rund 1000 Datenpunkten erhoben; insgesamt werden 20 Iterationen betrachtet. Das Ergebnis ist kein Manipulationsbenchmark.
- **Mögliche Kapitelposition (B):** Verwandte Arbeiten: ursprüngliche empirische Demonstration.

<a id="dag-09"></a>
### DAG-09

- **ID:** `DAG-09`
- **Aussage (A):** DAgger erzielt im OCR-Versuch 85,5 % Zeichenaccuracy gegenüber 83,6 % mit überwachtem Training mit korrektem Vorgängerlabel.
- **Primärquelle:** DAgger, AISTATS 2011, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=8) / [eingefrorenes PDF](_research/dagger.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §5.3; Ergebnisabsatz
- **Evidenzklasse:** E
- **Paraphrase (A):** Bei ungefähr 6600 Wörtern und über 52000 Zeichen werden neun von zehn Folds zum Training und einer zum Test genutzt. Die Accuracy betrifft Zeichen, nicht vollständige Wörter oder robotische Erfolgsraten.
- **Mögliche Kapitelposition (B):** Evaluation: unterschiedliche Zielmetriken kenntlich machen.

<a id="dart-06"></a>
### DART-06

- **ID:** `DART-06`
- **Aussage (A):** DART erreicht in vier MuJoCo-Lokomotionsdomänen ähnliche Performance wie DAgger bei im Humanoid-Versuch geringerem Rechenaufwand.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=7) / [eingefrorenes PDF](_research/dart.pdf#page=7)
- **Seite:** PDF S. 7; **Abschnitt:** §5.1; Abb. 2 und Ergebnisabsatz
- **Evidenzklasse:** E
- **Paraphrase (A):** Berichtet werden Walker, Hopper, Half-Cheetah und Humanoid. Im Humanoid-Beispiel ist DART ungefähr dreimal schneller; der Erhebungsreward liegt etwa 5 % unter dem Supervisor, bei DAgger über 80 % darunter. Dies gilt für die untersuchten Updatepläne und Hardware.
- **Mögliche Kapitelposition (B):** Verwandte Arbeiten: Aufwand und Qualität der Datenerhebung getrennt berichten.

<a id="dart-07"></a>
### DART-07

- **ID:** `DART-07`
- **Aussage (A):** Im HSR-Clutter-Versuch werden 79 % für DART-3, 72 % für DART-6 und 49 % für BC berichtet.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=8) / [eingefrorenes PDF](_research/dart.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §5.2; Ergebnisabsatz und Abb. 3
- **Evidenzklasse:** E
- **Paraphrase (A):** Vier Supervisors liefern je eine BC-Basis von zehn Demos und je dreißig weitere Demos pro Bedingung; die finale Policy nutzt vierzig. 79 gegenüber 49 sind 30 Prozentpunkte. Die berichtete ungefähr 62%ige Verbesserung ist relativ, keine Zunahme um 62 Prozentpunkte.
- **Mögliche Kapitelposition (B):** Evaluation: absolute und relative Effekte unterscheiden.

<a id="dart-08"></a>
### DART-08

- **ID:** `DART-08`
- **Aussage (A):** Der HSR-Erfolgstest enthält Objekterkennung, einen freien Pfad und eine menschlich ausgelöste Open-Loop-Greifausführung.
- **Primärquelle:** DART, CoRL 2017, Original-Proceedings; [Original-PDF](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=14) / [eingefrorenes PDF](_research/dart.pdf#page=14)
- **Seite:** PDF S. 14; **Abschnitt:** Appendix §4.5; Robot Setup
- **Evidenzklasse:** M
- **Paraphrase (A):** Ein gegenüber der getesteten Policy verblindeter Supervisor bestätigt die Ziel-/Pfadsituation und löst einen Plan zur festen Zielposition aus. Pro Policy werden zwanzig unterschiedlich initialisierte Tests genannt. Das ist kein vollständig autonomer Closed-Loop-Stack-Erfolgstest.
- **Mögliche Kapitelposition (B):** Evaluation: Erfolgskriterium und verbleibende menschliche Hilfe.

<a id="sbc-07"></a>
### SBC-07

- **ID:** `SBC-07`
- **Aussage (A):** Im Quadrotor-Versuch wird modellbasiertes Stable-BC gegen BC und DART unter Test-Aktionsrauschen geprüft.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=6) / [eingefrorenes PDF](_research/stable_bc.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §V-B; Abb. 3 und Methods
- **Evidenzklasse:** P-E
- **Paraphrase (A):** Der Task hat bekannte nichtlineare Roboterdynamik, fixe Hindernisse und fixe Zielposition. Zehn getrennte Trainingsläufe werden jeweils mit hundert Rollouts getestet. Die Autoren berichten höhere Erfolgsrate bei weniger Demos, ohne hier Zahlen aus der Kurve zu interpolieren.
- **Mögliche Kapitelposition (B):** Verwandte Arbeiten/Evaluation: kontrollierter Test und Datenregime.

<a id="sbc-08"></a>
### SBC-08

- **ID:** `SBC-08`
- **Aussage (A):** Im Air-Hockey-Versuch berichten die Autoren mehr erfolgreiche Hits mit Stable-BC bei 15, 60 und 120 Sekunden Trainingdaten.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=7) / [eingefrorenes PDF](_research/stable_bc.pdf#page=7)
- **Seite:** PDF S. 7; **Abschnitt:** §VI; Training Data, Testing Procedure, Results
- **Evidenzklasse:** P-E
- **Paraphrase (A):** Zehn Personen liefern getrennte Datensätze. Pro Datenmenge werden zehn personenspezifische Policies und je zehn Rollouts betrachtet; ein Rollout endet spätestens nach 25 Hits. Autoren-ANOVA und Post-hoc-Tests berichten p < 0,05; dies ist keine Signifikanzangabe für unsere Experimente.
- **Mögliche Kapitelposition (B):** Evaluation: Effekt mit Autorentest und klarer Replikationseinheit.

<a id="sbc-09"></a>
### SBC-09

- **ID:** `SBC-09`
- **Aussage (A):** Stable-BC produziert im Air-Hockey-Versuch weniger Richtungswechsel pro erfolgreichem Hit.
- **Primärquelle:** Stable-BC, Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen; [Original-PDF](https://arxiv.org/pdf/2408.06246v1#page=8) / [eingefrorenes PDF](_research/stable_bc.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §VI; Ergebnisfortsetzung und Abb. 5
- **Evidenzklasse:** P-E
- **Paraphrase (A):** Ein Richtungswechsel ist zuvor als Aktionsänderung über zehn Grad definiert. Die Autoren berichten Unterschiede bei allen Datenmengen und auch bei gepoolten 1200 Sekunden; bei großen Datenmengen nähern sich die Hit-Leistungen beider Verfahren an.
- **Mögliche Kapitelposition (B):** Evaluation: Bewegungsqualität von Aufgabenleistung unterscheiden.

<a id="act-05"></a>
### ACT-05

- **ID:** `ACT-05`
- **Aussage (A):** ACT verwendet für die realen Tasks überwiegend fünfzig menschliche Demonstrationen pro Task; Thread Velcro hat hundert.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=9) / [eingefrorenes PDF](_research/act.pdf#page=9)
- **Seite:** PDF S. 9; **Abschnitt:** §V-B; Data Collection
- **Evidenzklasse:** M
- **Paraphrase (A):** Bei 50 Hz dauern Demos ungefähr acht bis vierzehn Sekunden. Die Simulationsaufgaben werden jeweils mit fünfzig erfolgreichen geskripteten oder menschlichen Demos untersucht. Menschliche Daten sind laut Autoren auch bei einem einzigen Demonstrator stochastisch.
- **Mögliche Kapitelposition (B):** Evaluation: Datenherkunft und Menge.

<a id="act-06"></a>
### ACT-06

- **ID:** `ACT-06`
- **Aussage (A):** ACT erzielt in den Simulationsaufgaben je nach Datenquelle deutlich unterschiedliche finale Erfolgsraten.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=8) / [eingefrorenes PDF](_research/act.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §V; Tabelle II
- **Evidenzklasse:** E
- **Paraphrase (A):** Cube Transfer: 86 % mit Scriptdaten und 50 % mit menschlichen Demos; Bimanual Insertion: 32 % beziehungsweise 20 %. Je Bedingung werden drei Trainingsseeds und fünfzig Tests pro Seed berichtet. Teilphasenerfolg darf nicht als voller Taskerfolg ausgegeben werden.
- **Mögliche Kapitelposition (B):** Evaluation: Datenquelle, Seeds und finale Taskmetrik.

<a id="act-07"></a>
### ACT-07

- **ID:** `ACT-07`
- **Aussage (A):** Die sechs realen ACT-Tasks zeigen finale Erfolgsraten zwischen 20 % und 96 %.
- **Primärquelle:** ACT, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p016.pdf#page=8) / [eingefrorenes PDF](_research/act.pdf#page=8)
- **Seite:** PDF S. 8; **Abschnitt:** §V; Tabellen II–III
- **Evidenzklasse:** E
- **Paraphrase (A):** Slide Ziploc erreicht 88 %, Slot Battery 96 %, Open Cup 84 %, Thread Velcro 20 %, Prep Tape 64 % und Put On Shoe 92 %. Das Protokoll nennt einen Trainingsseed und fünfundzwanzig Tests. Die Kurzzusammenfassung 80–90 % beschreibt nicht alle Tasks.
- **Mögliche Kapitelposition (B):** Evaluation: Ergebnisse vollständig und ohne pauschale Erfolgsrate berichten.

<a id="dp-05"></a>
### DP-05

- **ID:** `DP-05`
- **Aussage (A):** Auf Square-PH-State berichten die Autoren DP-C mit 1,00/0,93 und DP-T mit 1,00/0,89 gegenüber LSTM-GMM mit 0,95/0,73.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=6) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=6)
- **Seite:** PDF S. 6; **Abschnitt:** §V; Tabelle I, State Policy
- **Evidenzklasse:** E
- **Paraphrase (A):** Die erste Zahl ist die Performance des besten Checkpoints, die zweite der Durchschnitt der letzten zehn Checkpoints; die Angaben sind über drei Trainingsseeds und fünfzig Starts je Seed gemittelt. Die Task-/Checkpointdefinition gehört zwingend zur Zahl.
- **Mögliche Kapitelposition (B):** Evaluation: konkreter State-Benchmark statt allgemeiner Überlegenheit.

<a id="dp-06"></a>
### DP-06

- **ID:** `DP-06`
- **Aussage (A):** Die oft genannte Verbesserung von 46,9 % ist ein Mittel relativer Benchmarkverbesserungen mit Variantenwahl.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=15) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=15)
- **Seite:** PDF S. 15; **Abschnitt:** Appendix G; Performance Improvement Calculation
- **Evidenzklasse:** M
- **Paraphrase (A):** Pro Tabellenspalte wird die beste Baseline mit der besten Diffusionvariante verglichen; MH wird ausgelassen. Die relativen Quotienten werden anschließend gemittelt. Das ist weder +46,9 Prozentpunkte noch eine einzelne lokale Taskrate.
- **Mögliche Kapitelposition (B):** Evaluation: Nenner, Variantenwahl und Aggregation der Gesamtzahl.

<a id="dp-09"></a>
### DP-09

- **ID:** `DP-09`
- **Aussage (A):** Die Autoren nennen korrekte Aktionsnormalisierung als wesentliche Implementierungsbedingung.
- **Primärquelle:** Diffusion Policy, RSS 2023, Original-Proceedings; [Original-PDF](https://www.roboticsproceedings.org/rss19/p026.pdf#page=14) / [eingefrorenes PDF](_research/diffusion_policy.pdf#page=14)
- **Seite:** PDF S. 14; **Abschnitt:** Appendix A; Normalization
- **Evidenzklasse:** M
- **Paraphrase (A):** Aktionsdimensionen werden überwiegend mit ihren Minima und Maxima auf [−1,1] skaliert, weil DDPM-Vorhersagen geclippt werden. Nahezu konstante und Rotationsdimensionen erhalten besondere Behandlung. Dies ist eine Aktionsregel, kein Beleg für beliebige Observation-Normalisierung.
- **Mögliche Kapitelposition (B):** Reproduzierbarkeit: Skalierung und Aktionssupport.
