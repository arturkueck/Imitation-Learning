# Forschungsskizze: Robustheit von Behavioral Cloning in robomimic

*Arbeitsstand: 30. September 2026. Die Implementierung und die geplanten
Lift-Versuche sind durchgeführt; Messwerte und Grenzen stehen in
[`RESULTS.md`](RESULTS.md).*

## 1. Idee in einem Satz

Eine stabilitätsregularisierte BC-Policy in **robomimic** integrieren und prüfen,
ob sie bei gleicher Demonstrationsmenge nach kleinen Abweichungen vom
Demonstrationsverlauf häufiger zum Ziel kommt als die vorhandene BC-Baseline.

**Arbeitstitel:** *Stability-Regularized Behavioral Cloning for Robust Robot
Manipulation in robomimic*.

## 2. Beobachtung und Forschungslücke

Die deterministische BC-Implementierung minimiert eine gewichtete Kombination
aus Aktionsfehlern (MSE, Smooth L1, Richtungskosinus). Sie lernt damit vor
allem, welche Aktion zu einer **beobachteten Demonstrationssituation** passt.
Während eines Rollouts verändert jedoch bereits ein kleiner Aktionsfehler die
nächste Beobachtung. Wiederholte Fehler können die Policy aus dem Bereich der
Trainingsdaten führen (*covariate shift*). Das ist eine bekannte Grenze von
Offline-BC und kein robomimic-spezifischer Programmfehler [1, 2].

robomimic bietet bereits BC-RNN, BC-Transformer und Diffusion Policy [1]. Eine
weitere Aktionsarchitektur allein ist daher kein klarer Beitrag. Der
untersuchte Zusatz soll stattdessen die **lokale Reaktion der Policy auf
Abweichungen** beeinflussen und deren Nutzen in robomimic-Manipulationsaufgaben
systematisch messen. Stable-BC [3] liefert dafür einen Ausgangspunkt: Es
kombiniert den Imitationsverlust mit einer Bedingung an die lokalen
Fehlerdynamiken.

## 3. Forschungsfrage und Hypothesen

**Forschungsfrage:** Verbessert eine an robomimic angepasste
Stabilitätsregularisierung die geschlossene Regelkreisleistung einer
Offline-BC-Policy auf einem Manipulationstask, insbesondere bei moderat
verschobenen Startzuständen, ohne die nominale Erfolgsrate stark zu senken?

- **H1:** Die erweiterte Policy erreicht bei gestörten Startzuständen eine
  höhere Erfolgsrate als BC bei gleichem Datensatz und Trainingsbudget.
- **H2:** Der Abstand der Rollout-Zustände zu vergleichbaren
  Demonstrationszuständen wächst nach einer Störung langsamer.
- **H3:** Zu starke Regularisierung verschlechtert Imitationsfehler oder
  nominale Erfolgsrate. Die Stärke des Zusatzterms muss daher untersucht
  werden.

H1–H3 sind zu prüfende Hypothesen, keine erwarteten Garantien. Die lokalen
Stabilitätsaussagen aus [3] lassen sich nicht ohne Prüfung der dortigen
Annahmen auf einen kontaktreichen robosuite-Task übertragen.

## 4. Vorgeschlagene Methode

### 4.1 Minimaler Startpunkt

Verwendet wird der offizielle Lift-PH-Low-Dim-Datensatz für einen Panda/Franka-
Roboter mit OSC_POSE-Controller. Die Baseline ist **deterministisches BC**, damit
die neue Loss-Komponente möglichst isoliert geprüft wird. Umgebung, Aktionen,
Erfolgsindikator und reproduzierbare Rollouts wurden lokal verifiziert.

### 4.2 Stabilitätszusatz

Die Policy bleibt zunächst die robomimic-BC-ActorNetwork. Der Trainingsverlust
wird zu

```text
L_total = L_BC + λ · L_stability
```

erweitert. `L_BC` entspricht dem bestehenden robomimic-Verlust. Die nun
implementierte Variante ist **von Stable-BC [3] inspiriert, aber nicht dessen
Gleichung 11**: Eine kleine, zufällige Abweichung `δ` der Greiferposition wird
in der Beobachtung erzeugt. Das relative Merkmal `Objektposition -
Greiferposition` wird dazu konsistent aktualisiert. Die Policy wird an beiden
Beobachtungen ausgewertet. Mit einer nur auf Trainingsdaten geschätzten Matrix
`K` für `ΔGreiferposition ≈ ΔAktion @ K` wird der nächste Fehler angenähert:

```text
e_next = δ + (π(obs_perturbed)[:3] - π(obs)[:3]) @ K
L_stability = mean(max(0, ||e_next||² / ||δ||² - ρ²))
```

`ρ < 1` ist die gewünschte lokale Kontraktion. Dieser finite-difference
Verlust vermeidet zweite Ableitungen und ist für den kleinen Low-Dim-Versuch
praktisch. Die Matrix `K` beschreibt nur eine **mittlere lokale Antwort** des
Lift-Controllers; sie ist kein vollständiges Roboterdynamikmodell. Der Verlust
liefert deshalb keine Stabilitätsgarantie bei Kontakt, großen Abweichungen
oder anderen Tasks. Der wissenschaftliche Beitrag wäre die Integration und
kontrollierte Prüfung dieser *Approximation* gegen Standard-BC, nicht eine
Reproduktion der theoretischen Stable-BC-Aussagen.

**Machbarkeitsgrenze:** Die Methode setzt einen sinnvoll perturbierbaren
Greiferzustand, konsistente relative Beobachtungen und eine hinreichend
brauchbare lokale Aktionsantwort voraus. Für reine Bilder oder ein anderes
Aktionsformat muss sie neu definiert und geprüft werden.

### 4.3 Kleine, getrennte Codeverbesserung

Der Datensatz kann Sequenzen am Ende einer Demonstration auffüllen und dafür
eine `pad_mask` liefern [4]. BC-RNN mittelt seinen Aktionsverlust über alle
Sequenzpositionen [1]. Ein **maskierter Sequenzverlust** wäre eine kleine,
direkt überprüfbare Implementierung: nur echte Zeitschritte zählen, der
Nenner ist die Anzahl gültiger Schritte. Er gehört in eine separate Ablation
mit BC-RNN; sein möglicher Effekt darf nicht als Wirkung der
Stabilitätsregularisierung ausgegeben werden. Für das deterministische BC mit
Sequenzlänge 1 ist dieser Punkt kein Kernproblem.

## 5. Arbeitsplan

| Phase | Arbeit | Prüfergebnis |
| --- | --- | --- |
| 1. Setup | robomimic-Version festhalten; einen Task, Datensatz und Low-Dim-Beobachtungen auswählen; Datenformat und Rollout-Skript prüfen | Ein unveränderter BC-Trainingslauf und mehrere Rollouts funktionieren |
| 2. Baseline | BC mit festen Splits, mindestens drei Trainings-Seeds und gleichem Budget trainieren | Nominale Erfolgsrate und Streuung dokumentiert |
| 3. Machbarkeit | Greifer-, Objekt- und Aktionsmerkmale definieren; lokale Aktionsantwort auf Trainingsdaten schätzen; Loss an kleinen Beispielen auf Dimensionen und Gradienten testen | Finite-difference-Näherung ist für den Task fachlich und technisch plausibel |
| 4. Integration | Neue Konfiguration und Loss im robomimic-Algorithmus ergänzen; `λ = 0` gegen unverändertes BC abgleichen | Baseline-Verhalten bei ausgeschaltetem Zusatzterm reproduziert |
| 5. Experimente | Regularisierungsstärken trainieren; nominale und gestörte Rollouts ausführen | Vergleich bei gleichen Daten, Seeds, Schritten und Evaluationszuständen |
| 6. Analyse | Erfolgsrate, Rückkehrverhalten, Imitationsfehler, Trainingszeit und Fehlermuster auswerten | Hypothesen werden angenommen, eingeschränkt oder verworfen |

Ein erster enger Meilenstein ist: **ein nominaler BC-Lauf plus ein definierter
Störungstest**. Erst wenn diese Messstrecke verlässlich ist, lohnt die
Integration der neuen Loss-Funktion.

## 6. Versuchsdesign

**Kontrollierte Bedingungen:** identischer Datensatz und Train/Validation-Split,
gleiche Beobachtungen, Policy-Architektur, Aktionsnormalisierung,
Trainingsschritte, Checkpoint-Regel und Rollout-Samen. Mindestens drei
Trainings-Seeds; pro Seed genügend Rollouts, sodass die Unsicherheit der
Erfolgsrate sichtbar wird. Die genaue Zahl wird nach Laufzeitmessung
festgelegt und vor dem finalen Vergleich fixiert.

**Vergleiche:**

1. robomimic-BC ohne Zusatzterm;
2. dieselbe Policy mit Stabilitätsregularisierung bei mehreren `λ`-Werten;
3. Ablation `λ = 0`, um Integrationsänderungen aufzudecken;
4. optional BC-RNN mit und ohne Padding-Maske, als getrennte technische Frage.

**Evaluation:**

- Nominale Startzustände aus der üblichen Task-Verteilung.
- Moderat verschobene, reproduzierbar erzeugte Startzustände oder Objektlagen.
  Störungen nur innerhalb physikalisch gültiger Zustände und nach Schwierigkeit
  gestaffelt.
- Primärmetrik: Erfolgsrate je Bedingung mit Unsicherheitsintervall.
- Sekundär: Zeit bis Erfolg, Fehlerarten, Aktionsglattheit, Abstand zu
  Demonstrationszuständen und Trainings-/Inferenzaufwand. Zustandsabstand nur
  für semantisch vergleichbare Zeitpunkte oder Phasen interpretieren.

Offline-Validation-Loss ist ergänzend; die Forschungsfrage betrifft das
Verhalten im **geschlossenen Regelkreis**. Ein negativer Befund ist ebenfalls
wertvoll, wenn die Bedingungen fair und die Grenzen des Stabilitätsansatzes
nachvollziehbar beschrieben sind.

## 7. Risiken und Entscheidungspunkte

| Risiko | Umgang damit |
| --- | --- |
| Zustandsaufteilung oder Dynamik passt nicht zum Task | Vor Implementierung prüfen; Task anpassen oder die Stable-BC-Adaption verwerfen |
| Regularisierung unterdrückt nötige Reaktion auf Objekte | Mehrere Stärken vergleichen; BC-Verlust und nominale Erfolgsrate mitberichten |
| Störung ist zu schwer oder unrealistisch | Validität und Stärke vorab definieren; nominal, leicht und moderat getrennt zeigen |
| Erfolg schwankt stark zwischen Seeds | Gleiche Seeds und Rollout-Zustände paarweise vergleichen; Streuung berichten |
| Rechenbudget reicht nicht für große Modelle | Low-Dim-Task und eine Policy-Architektur zuerst; optionale Baselines erst danach |

## 8. Erwarteter Beitrag und Umfang

Der realistische Beitrag ist eine **reproduzierbare robomimic-Integration und
kontrollierte Evaluation** einer stabilitätsbasierten BC-Erweiterung für einen
Manipulationstask. Eine Verbesserung ist möglich, aber nicht vorausgesetzt.
Der maskierte BC-RNN-Verlust ist ein nützlicher separater Fix, jedoch allein
eine deutlich kleinere Forschungsfrage. Diffusion Policy und ACT bleiben
Literatur- oder spätere Vergleichspunkte, da robomimic Diffusion Policy bereits
enthält [5].

## Quellen und Code-Anker

1. [robomimic: BC-Implementierung](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/algo/bc.py) und [implementierte Algorithmen](https://github.com/ARISE-Initiative/robomimic/blob/master/docs/introduction/implemented_algorithms.md).
2. [Mandlekar et al., *What Matters in Learning from Offline Human Demonstrations for Robot Manipulation*](https://arxiv.org/abs/2108.03298).
3. [Mehta et al., *Stable-BC: Controlling Covariate Shift with Stable Behavior Cloning*, Abschnitt IV-C](https://arxiv.org/html/2408.06246v1).
4. [robomimic: SequenceDataset und Padding-Maske](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/utils/dataset.py) sowie [Basis-Konfiguration](https://github.com/ARISE-Initiative/robomimic/blob/master/robomimic/config/base_config.py).
5. [robomimic: Algorithmusübersicht mit Diffusion Policy](https://github.com/ARISE-Initiative/robomimic/blob/master/docs/introduction/implemented_algorithms.md).

