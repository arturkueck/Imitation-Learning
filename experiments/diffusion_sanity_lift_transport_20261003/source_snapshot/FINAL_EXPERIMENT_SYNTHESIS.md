# Gesamtsynthese des Stack-Experiments

## 1. Executive Summary

Unter identischen Trainings-/Validierungsdaten und gleichem nominalem Update- und Batchbudget erzielt der untersuchte deterministische Direct-Chunk-Regressor in drei unabhängigen Trainingsinitialisierungen **28/40, 30/40 und 31/40 stabile Stacks**. Die drei finalen unnormalisierten Diffusionsmodelle erzielen jeweils **0/40**. Direct erreicht im Mittel **74,17% bei 3,82 Prozentpunkten Stichproben-Standardabweichung über Trainingsseeds**; Diffusion 0,00% bei 0,00 Prozentpunkten. Der Abstand besteht in allen drei Seeds. Daraus folgt keine Signifikanzbehauptung und keine allgemeine Überlegenheit einer Policy-Klasse. [S1/S2/S16]

Die anschließende Failure-Analyse untersucht unveränderte Gewichte anhand von **960 unterschiedlichen neuen Rollouts und 322.560 Diffusionschunks**. Weder Ausführung von 1/2/4 Aktionen bei DDIM-10 noch DDIM-5/10/50 bei zwei ausgeführten Aktionen erzeugt in irgendeinem Seed einen stabilen Stack oder erreicht den Release-Indikator. DDIM-20 ist ausschließlich offline geprüft. Dies ist eine begrenzte Inferenzstudie, kein vollständiger Kreuzvergleich. [S3/S9/S10]

Diffusion scheitert nicht an einem generell schwachen Chunkanfang oder am völligen Fehlen brauchbarer Samples. Auf den eingefrorenen Expert-Transportzuständen erfüllen nur etwa 28–32% der Samples gemeinsam die festgelegte Mindeststärke und Zielrichtung. Solche Samples existieren aber bei jeder untersuchten Transportobservation. Historisch fallen 167 von 206 nicht regelgerechten Grasp-Verlusten mit einem Öffnungskommando zusammen; 205 liegen mehr als 3 cm vom Ziel entfernt. Diese Beobachtungen stützen Ursachenhypothesen, beweisen keine isolierte Kausalität. [S3/S5–S8]

**Wissenschaftliche Kernaussage:** In der untersuchten simulierten Zwei-Würfel-Stack-Aufgabe liefert der konkrete deterministische Direktregressor unter gleichem nominalem Trainingsbudget konsistente Closed-loop-Erfolge über drei Trainingsseeds. Die drei finalen unnormalisierten Diffusionsmodelle erreichen trotz einzelner transportgeeigneter Aktionssamples und der geprüften Inferenzänderungen keine stabilen Stacks. Der Vergleich umfasst unterschiedliche Architekturen und Lernziele; er isoliert keinen generellen Effekt von Stochastik oder Diffusion.

Weitere Experimente sind für die bisherigen, unten präzisierten Forschungsfragen nicht zwingend notwendig. Für diese Synthese wurden **kein Training, keine neue Policy-Inferenz und keine Simulatorrollouts** durchgeführt. Bestehende Artefakte bleiben unverändert.

## 2. Experimental Setup

### Hauptvergleich und Kontrollen

Die Hauptanalyse umfasst sechs finale EMA-Checkpoints: Direct BC und Diffusion Policy mit Trainingsseeds 1–3. Seed 1 stammt aus dem bestehenden passenden Ausgangsversuch; Seeds 2/3 wurden unabhängig neu initialisiert. Ausschließlich finale Checkpoints werden betrachtet, ohne Auswahl eines besseren Zwischenstands. Verwendet werden dieselben 180 Trainings- und 20 Validierungsdemos des programmierten StackExperts. Eingaben sind zwei rohe State-Frames mit jeweils 15 Merkmalen; Ausgaben sind 16×7 Controllerkommandos. RGB-Bilder gehen nicht in diesen Vergleich ein. [S4/S16]

Je Modell wurden 30.000 Optimizer-Updates bei Batchgröße 8 durchgeführt, entsprechend 240.000 konsumierten Trainingsfenstern. Optimizer, Lernratenbudget und EMA sind nominal angeglichen. Direct verwendet einen Residual-MLP mit tanh-Ausgabe und Action-Chunk-MSE, Diffusion einen konditionierten zeitlichen UNet mit Epsilon-MSE und DDIM. Die Parameterzahlen betragen 67.467.376 beziehungsweise 65.648.903. Architektur und Lernziel unterscheiden sich gemeinsam. Gleiche Updatezahlen belegen weder gleiche FLOPs noch gleiche optimale Trainingsreife. [S4/S16]

**Samplingpräzisierung:** Ältere Berichte beschreiben beide Sampler als uniform mit Zurücklegen. Der spätere Quellcodeaudit dokumentiert für Direct Ziehungen mit Zurücklegen, für Diffusion einen gemischten DataLoader ohne Zurücklegen innerhalb des jeweils neu gestarteten Epoch-Iterators. Die Daten und die nominale Trainingsmenge sind gleich, exakte Indexfolgen und Ziehmechanismen sind nicht identisch. Dieser Beschreibungsunterschied wird ausdrücklich dokumentiert. [S15/S16]

### Evaluation

Alle Hauptrollouts verwenden dieselben 40 Startzustände 46000–46039 mit geprüften Zustands-Hashes. Die Messphase umfasst höchstens 500 Schritte bei 20 Hz. Ein stabiler Stack verlangt die native Success-Bedingung durchgehend über 40 zusätzliche Policy-Schritte, Würfelkontakt und keinen gehaltenen Würfel. Der native Aufgabenerfolg und die nachfolgende Stabilität werden von bloßen Teilindikatoren unterschieden. [S3/S16]

Baseline-Replanning führt Chunkindizes 1/2 aus: Index 0 entspricht der vergangenen Aktion, Index 1 ist die erste aktuell ausgeführte Aktion. Die Horizonte 1/2/4 verwenden die Slices [1:2], [1:3], [1:5]; der vorhergesagte Chunk bleibt unverändert. DDIM-Schrittzahlen werden bei h=2, Horizonte bei DDIM-10 verglichen. [S3/S4]

Offline werden 420 eingefrorene Zwei-Frame-Histories aus 20 Validierungsdemos bei Offsets −10…+10 um den Expert-Wechsel untersucht. Der Haupt-Transportbereich enthält 100 Histories bei +6…+10. Pro Diffusionsseed, Observation und DDIM-Schrittzahl 5/10/20/50 liegen 64 komplette Chunks mit gemeinsam gespeichertem Initialrauschen vor. Die native Policy führt ein einzelnes Sample aus; sie mittelt oder selektiert keine Samples. [S3/S5/S6]

Die unabhängigen Replikate sind die **drei Trainingsseeds je Klasse**. Starts sind gepaarte Aufgabenfälle innerhalb dieser Replikate; Histories derselben Demo und wiederholte Samples sind abhängig. Alle Vergleiche bleiben deskriptiv. Keine Signifikanztests oder Konfidenzintervalle werden aus gepoolten Rollouts oder Samples abgeleitet.

### Weitere vorhandene Versuche als Kontext

Die älteren Scheduler-, Balancierungs- und Dynamikfortsetzungsversuche besitzen andere Budgets, Checkpoints oder Diagnoseprotokolle. Sie gehören nicht zum replizierten Sechs-Modell-Vergleich. Sie zeigen Verbesserungen einzelner Offline-/Transportindikatoren ohne entsprechende Lösung der gesamten Aufgabe. Ihre damaligen Empfehlungen sind historische Vorschläge; die späteren Direct- und Seedvergleiche erfüllen bereits wesentliche Teile davon. [S11–S14]

Ein separater vorhandener Normalisierungsvergleich liefert in Trainingsseed 1 Direct 29/40, 29/40, 31/40 sowie Diffusion 0/40, **2/40**, 0/40 für Actions-only, Observations-only und beide Normalisierungen. Diese anders trainierten Modelle ersetzen keinen Hauptcheckpoint. Der Observations-only-Befund begrenzt die Aussage: „Diffusion erreicht in allen vorhandenen Experimenten null Erfolg“ wäre falsch. Eine robuste Lösung über Trainingsseeds ist dadurch nicht gezeigt. Die nicht replizierten Zusatzarme werden nicht nachträglich als bessere Hauptreferenz ausgewählt. [S15]

## 3. Research Questions

1. **RQ1 — Reproduzierbarkeit:** Bleibt der Closed-loop-Erfolgsunterschied der beiden finalen Policy-Konfigurationen über unabhängige Trainingsinitialisierungen bestehen?
2. **RQ2 — Expert-Timing:** Ist die exakte Reproduktion des abrupten Expert-Lift→Transport-Wechsels einschließlich voller Lifthöhe für einen stabilen Stack notwendig?
3. **RQ3 — Policy-Ausgaben:** Welche Unterschiede in Stärke, Zielrichtung und bedingter Streuung zeigen direkte Regression und Diffusionssampling auf identischen Expert-Transportbeobachtungen?
4. **RQ4 — Fehlermechanismen:** Welche beobachteten Defizite sind mit dem Diffusion-Scheitern vereinbar, und welche isolierte Ursache ist nachgewiesen?
5. **RQ5 — Inferenz:** Beheben Replanning-Horizonte 1/2/4 oder DDIM-Schrittzahlen 5/10/50 bei unveränderten finalen Diffusionsgewichten das Ausbleiben stabiler Stacks?

Die Fragen sind auf die durchgeführten Vergleiche zugeschnitten. RQ4 unterscheidet beobachtete Fehlerstruktur von noch offenen Mechanismen. Keine Frage verlangt eine universelle Rangfolge der Policy-Klassen.

## 4. Main Quantitative Results

### Originaler replizierter Closed-loop-Vergleich

| Modell | Seed 1 | Seed 2 | Seed 3 | Mittelwert ± Seed-SD |
| --- | --- | --- | --- | --- |
| Direct | 28/40 | 30/40 | 31/40 | 74,17% ± 3,82 Prozentpunkte |
| Diffusion | 0/40 | 0/40 | 0/40 | 0,00% ± 0,00 Prozentpunkte |

Quelle: S2, gegen historische Einzelstarttabellen S7 und Audit S10 geprüft. Die Seed-SD ist die Stichproben-SD mit Nenner n−1 über drei Erfolgsraten. Sie beschreibt Seedstreuung auf festen Starts, keine Unsicherheit einer unbekannten Erfolgswahrscheinlichkeit. Direct löst 23 Starts in allen drei Seeds, 12 seedabhängig und fünf in keinem Seed; Diffusion löst keinen dieser Starts. [S2]

### Offline-Transport und Expert-Grenze

Alle Dreierangaben folgen der Reihenfolge Trainingsseed 1 / 2 / 3. Normen sind dimensionslose Controllerkommandos.

| Relevante Offlinegröße | Direct | Diffusion | Quelle |
| --- | --- | --- | --- |
| XY-Norm, Mittel, erste ausgeführte Aktion | 0,529 / 0,549 / 0,546 | 0,303 / 0,291 / 0,290 | S5/S6 |
| Zielcosinus, Mittel | 0,998 / 0,994 / 0,997 | 0,496 / 0,481 / 0,477 | S5/S6 |
| XY/Expert, Median, ursprüngliches Panel | 76,01% / 81,46% / 77,59% | 28,68% / 25,80% / 25,36% | S2; Diffusion 8 Draws |
| Grenzreaktion / Expert-Sprung, Median | 1,65% / 1,97% / 1,71% | 0,62% / 0,43% / 0,58% | S2; Diffusion 32 gepaarte Draws |
| P(XY>0,25 und Zielcosinus>0,5) | — | 32,13% / 29,28% / 28,45% | S5; 64 Draws je Observation |
| Mittlere bedingte XY-Quantile Q10 / Q50 / Q90 | — | Seed 1: 0,041 / 0,179 / 0,767; Seed 2: 0,040 / 0,164 / 0,757; Seed 3: 0,041 / 0,163 / 0,754 | S5 |
| XY erste Aktion / Mittel der nächsten drei | 0,529/0,412; 0,549/0,434; 0,546/0,424 | 0,303/0,254; 0,291/0,251; 0,290/0,246 | S6 |

Zielcosinus misst offline die Richtung zur EEF→A-Richtung der eingefrorenen letzten Observation. Die historischen „Transport-Cosinus“-Werte aus S1/S2 messen dagegen die Richtung relativ zur Expert-Aktion; sie sind nicht exakt dieselbe Größe. Der Zielvergleich oben verwendet konsistente Zielmetriken aus S5/S6. Expert-Stärkeverhältnis und Grenzreaktion stammen ausdrücklich aus dem ursprünglichen Panel. Dessen acht beziehungsweise 32 Ziehungen werden nicht mit den 64-Sample-Diagnosen gleichgesetzt.

Die Grenzreaktion ist die Norm der Änderung der ersten ausgeführten XYZ-Aktion zwischen gepaarten Grenzframes geteilt durch den Expert-Sprung; Diffusion verwendet identisches Initialrauschen vor/nach dem Wechsel. Die Quantile sind Mittelwerte zustandsbedingter Quantile, keine Quantile einer Mischung verschiedener Zustände. Stärke-/Richtungsschwellen sind Diagnosen, keine Erfolgsgarantie.

### Kontrollierte Inferenztests auf unveränderten Gewichten

| Ausgeführte Aktionen h; DDIM-10 | Direct Stacks je Seed /40 | Diffusion Stacks je Seed /40 | Diffusion Transportindikator je Seed /40 |
| --- | --- | --- | --- |
| 1 | 27 / 29 / 29 | 0 / 0 / 0 | 5 / 2 / 3 |
| 2 | 28 / 30 / 31 | 0 / 0 / 0 | 15 / 10 / 7 |
| 4 | 31 / 28 / 33 | 0 / 0 / 0 | 12 / 12 / 11 |

| DDIM-Schritte; h=2 | Offline P(stark+Ziel), Seeds 1 / 2 / 3 | Closed-loop Stacks je Seed /40 | Transportindikator je Seed /40 |
| --- | --- | --- | --- |
| 5 | 33,55% / 30,28% / 28,13% | 0 / 0 / 0 | 9 / 5 / 4 |
| 10 | 32,13% / 29,28% / 28,45% | 0 / 0 / 0 | 15 / 10 / 7 |
| 20 | 33,00% / 29,34% / 29,55% | nur offline | — |
| 50 | 33,83% / 29,67% / 30,52% | 0 / 0 / 0 | 12 / 13 / 7 |

Quelle: S5/S9. Direct h=1 erzielt im Mittel 70,83% ±2,89 Prozentpunkte Seed-SD, h=4 76,67% ±6,29 Prozentpunkte; h=2 entspricht der Originalbaseline. Diffusion bleibt in sämtlichen geprüften Closed-loop-Bedingungen bei 0,00% ±0,00 Prozentpunkten. Dies ist keine Auswahl oder Empfehlung einer besseren Horizonvariante. Teilindikatoren reagieren auf die Eingriffe, ohne die Gesamtaufgabe konsistent zu retten.

DDIM-20 wurde nach der Offlineauswertung nicht zusätzlich closed-loop geprüft. DDIM-10/h=2 wird als Kontrolle in beiden Vergleichsgruppen wiederverwendet: 27 Tabellenzeilen mit je 40 Starts entsprechen 1.080 Startzeilen, aber nur **960 unterschiedlichen neuen Rollouts**: 360 Direct und 600 Diffusion. Zusätzlich liegen 240 historische Starts vor. Die 322.560 Offlinechunks sind Inferenzziehungen, keine zusätzlichen Trainingsreplikate. [S10]

### Grasp-Verluste und Timing-Gegenbeispiele

| Diagnose | Direct | Diffusion | Quelle |
| --- | --- | --- | --- |
| Historische Starts mit ≥1 nicht regelgerechtem Grasp-Verlust, Seeds 1/2/3 | 7 / 4 / 3 von je 40 | 29 / 26 / 25 von je 40 | S7 |
| Nicht regelgerechte historische Einzelereignisse | keine zusätzliche Hauptmetrik benötigt | 206; davon 205 >3 cm vom Ziel, 167 mit Öffnungskommando, 182 ≥3 Frames ohne Grasp | S7 |
| XY-Norm unmittelbar vor erstem solchen Verlust, seedweise bedingte Mediane | 0,050 / 0,025 / 0,051 | 0,020 / 0,024 / 0,022 | S7 |
| Zielabstand beim ersten solchen Verlust, seedweise Mediane | 1,61 / 1,40 / 1,98 cm | 12,90 / 13,20 / 12,20 cm | S7 |
| Erfolgreiche Starts ohne Expert-Vollhöhe | 19/28; 23/30; 26/31; insgesamt 68/89 | keine erfolgreichen Starts | S2/S3 |
| Erfolgreiche Starts mit frühem Transportindikator | 19/28; 24/30; 27/31; insgesamt 70/89 | keine erfolgreichen Starts | S2 |

Die letzten Summen sind deskriptive Gegenbeispiele, keine Analyse mit 89 unabhängigen Trainingsreplikaten. Verlustamplitude bezieht sich auf das Kommando direkt **vor** der Grasp-Transition, das Öffnungskommando auf den Ereignisschritt. Diese bedingten Rolloutzustände sind nicht identisch mit dem Expert-Transportpanel.

## 5. Failure Analysis

Die maßgebliche Ursachenanalyse ist S3. Ihre drei Hypothesen werden eingeordnet, ohne zusätzliche kausale Behauptungen einzuführen.

**H1 — unzuverlässiger bedingter Zieltransport, teilweise gestützt als Ursachenbeitrag.** Diffusion liefert auf eindeutigen Expert-Transportzuständen häufig zu schwache oder nicht ausreichend zielgerichtete Aktionen. Die gemeinsame Diagnoseschwelle erfüllt nur eine Minderheit der Samples. Bedingte Median-Normen liegen deutlich unter Q90; einzelne brauchbare Samples existieren bei jeder untersuchten Observation. Das Verteilungsdefizit ist belegt. Sein isolierter Beitrag zum Scheitern und seine Entstehung durch Architektur, Lernziel, Repräsentation oder Verteilungsverschiebung bleiben offen. [S3/S5/S6]

**H2 — Unterbrechung durch Neusampling, teilweise gestützt.** Chunks besitzen intern hohe Richtungskohärenz; Richtungsumkehrungen sind in geeigneten gehaltenen/gelifteten Aktionspaaren häufiger an Replanning-Grenzen als innerhalb eines Chunks. h=1 reduziert den Transportindikator gegenüber h=2 in allen Seeds. h=4 verbessert jedoch nicht alle Seeds und erreicht keinen Release. Das spricht für einen Beitrag zu Teilproblemen, nicht für eine hinreichende oder alleinige Erklärung der Nullrate. Die Horizon-Intervention verändert Reaktionslatenz und Zahl der Noiseziehungen gemeinsam. [S3/S9]

**H3 — instabiler Griff und unpassende Gripperwechsel, teilweise gestützt.** Nicht regelgerechte Grasp-Verluste, Öffnungskommandos und große Zielabstände stimmen häufig zeitlich und räumlich überein. Ein isolierter Gripper-Eingriff fehlt. Armbewegung, Kontaktgeometrie und veränderte Rolloutzustände können ebenfalls beitragen. Ein nativer Grasp-Prädikatwechsel bedeutet nicht automatisch einen physischen Fall. [S3/S7]

### Kompakte Failure Chain

**Observation → bedingte Aktionsverteilung → ausgeführtes Sample → Grasp/Lift → Transport → Positionierung → Absenken → Release → stabiler Stack**

Die Pfeile zeigen Regelkreis und Aufgabenabfolge, keine bewiesene Kausalkette. Phasen können wiederholt auftreten, etwa erneutes Greifen nach einem Verlust. Historische Erreichungsmatrix:

| Stufe | Direct, Seeds 1 / 2 / 3 | Diffusion, Seeds 1 / 2 / 3 |
| --- | --- | --- |
| Grasp | 37 / 37 / 35 | 31 / 26 / 27 |
| Lift | 37 / 37 / 34 | 24 / 18 / 19 |
| Transport gestartet | 37 / 37 / 34 | 15 / 8 / 9 |
| Nähe | 37 / 37 / 34 | 4 / 2 / 2 |
| Positionierung | 37 / 35 / 34 | 0 / 0 / 2 |
| Absenken | 36 / 34 / 34 | 0 / 0 / 0 |
| Release | 30 / 30 / 31 | 0 / 0 / 0 |
| Stabiler Stack | 28 / 30 / 31 | 0 / 0 / 0 |

Jeder Wert zählt Starts unter 40, keinen bedingten Übergangsanteil. Indikatoren sind nicht zwingend verschachtelt; ihre erste Nichterfüllung ist Lokalisierung, keine Ursache. [S2/S7]

| Stufe | Evidenz und Unterschied | Offene Kausalität |
| --- | --- | --- |
| Observation | Gleiche Expert-Histories offline, gleiche Initialzustände online. Diagnoseproben finden nutzbare Hinweise auf den Expert-Wechsel. | Gleiche Starts garantieren keine gleichen späteren Zustände. Vollständige Markov-Beobachtbarkeit und Rollout-Konditionierung sind nicht bewiesen. |
| Bedingte Verteilung | Direct deterministisch; Diffusion breit und phasenuneinheitlich, mit Lift-/Transportregimen bei identischen Inputs. | Ursprung des Defizits und allgemeine Zweimodalität nicht bewiesen. |
| Ausgeführtes Sample | Diffusion zieht beim Replanning neues Rauschen und führt einen Chunkausschnitt aus. Erste Aktion nicht systematisch schwächer. | Kein isolierter Eingriff in Samplepersistenz oder Auswahl; brauchbare Einzelaktionen garantieren keine kohärente Trajektorie. |
| Grasp/Lift | Direct greift/liftet häufiger; Diffusion zeigt zahlreiche frühe Verluste. | Öffnung, Armbewegung und Kontaktgeometrie nicht getrennt. |
| Transport | Klassenunterschiede bei Richtung/Stärke offline und Erreichung online; h=1 verschlechtert den Indikator. | Wirkung auf andere Rolloutzustände und Neusamplingmechanismus nicht isoliert. |
| Positionierung | Direct erreicht häufig präzise Positionierung; historische Diffusion nur selten. | Defizite können sich vorher akkumulieren; keine isolierte Positionierungsprobe. |
| Absenken | Direct häufig, historische Diffusion nie. In neuen h=4-Tests tritt der Indikator vereinzelt auf. | Eigenständiges Absenkdefizit nicht von ungeeigneten Eingangszuständen getrennt. |
| Release | Direct häufig mit korrekter Geometrie; alle neuen Diffusionsbedingungen ohne Release. | Frühes Öffnen fern vom Ziel ist keine regelgerechte Freigabe. Kein isolierter Release-Test. |
| Stabiler Stack | Direct 28/30/31; Haupt-Diffusionsbedingungen stets null. | Endergebnis identifiziert keine einzelne notwendige Fehlerursache. |

Die Indikatoren verwenden folgende Gates: Grasp = natives Prädikat; Lift = B-z>0,88 m; Transport = gehalten, B-z>0,98 m, XY-Geschwindigkeit>0,02 m/s und B→A-Cosinus>0,5 für drei Frames. Nähe = XY<3 cm bei B−A-z>3,2 cm; Position = XY<9 mm mit gleichem Höhengate; Absenken zusätzlich B−A-z=4 cm ±8 mm; Release zusätzlich Kontakt und kein Grasp. Expert-Vollhöhe wird separat mit B-z≥1,045 m und EEF-z≥1,049 m für drei Frames diagnostiziert und ist kein obligatorischer Aufgabenindikator. Online-B→A-Richtung und Offline-EEF→A-Richtung sind unterschiedliche Definitionen. [S3]

## 6. Evidence vs. Interpretation

### Empirisch beobachtet

- Der Erfolgsabstand der finalen unnormalisierten Konfigurationen besteht in allen drei Trainingsseeds. [S2]
- Beide Klassen bilden den abrupten Expert-Sprung lokal nur schwach ab. Direct startet offline in allen Validierungsdemos früh und löst dennoch viele Starts; volle Expert-Lifthöhe fehlt dabei häufig. [S2/S3]
- Direct produziert stärkere, konsistenter zielgerichtete Expert-Transportaktionen. Diffusion enthält brauchbare Einzelsamples, aber eine breite bedingte Verteilung mit geringer gemeinsamer Stärke-/Richtungszuverlässigkeit. [S5/S6]
- Ein allgemein schwächerer erster ausgeführter Chunkbefehl wird im stabilen Transport nicht beobachtet. [S6]
- Die geprüften Horizon-/DDIM-Änderungen verändern Teilmetriken, erzielen aber keine stabilen Stacks. [S9]
- Grasp-Verluste und Öffnungskommandos treten häufig gemeinsam fern vom Ziel auf. [S7]
- Eine allgemeine robuste Zweimodalität ist nicht nachgewiesen: eindimensionale Zielprojektion ohne über alle Bandbreiten stabile Mehrgipfligkeit; gemeinsame Zielprojektion/Z-Dichte mit stabil mehreren lokalen Gipfeln bei 12%/11%/11% der Transportobservations je Seed. Dies sind explorative Dichtekriterien. [S8]

### Plausible Interpretation

Ein Regelkreis benötigt zusammenhängende, zustandsangemessene Bewegung und passende Griffhaltung über mehrere Phasen. Eine gelegentlich brauchbare Aktion genügt dafür nicht. Die uneinheitliche Transportverteilung, erneute Noiseziehungen und frühen Grasp-Verluste sind gemeinsam mit dem Scheitern vereinbar. Ihr relatives Gewicht ist nicht bestimmt.

Direct kann hier einen kontinuierlicheren Lift→Transport-Verlauf nutzen, obwohl der Expert abrupt zwischen Zwischenzielen wechselt. Erfolgreiche niedrigere Lifts zeigen, dass Demonstrationsähnlichkeit an diesem Detail und Aufgabenerfolg unterschiedliche Bewertungsziele sind. Dies macht Timing nicht generell unwichtig; es begrenzt seine behauptete Notwendigkeit in dieser Aufgabe.

Eine unzureichend gelernte Nutzung kleiner zustandsrelevanter Änderungen ist mit früheren Diagnoseproben vereinbar. Balancierungs-/Dynamikversuche beeinflussen Teilindikatoren, identifizieren aber keine alleinige Ursache des Stack-Scheiterns. Der Normalisierungsversuch schwächt die Erklärung, dass einfache Skalierung allein eine robuste Lösung liefern müsse. Diese Interpretationen bleiben den drei Hypothesen untergeordnet. [S3/S11–S15]

### Nicht gezeigt

- **„Diffusion scheitert wegen Multimodalität.“ — nicht belegt / offen.** Koexistierende Aktionsregime sind keine allgemein robuste Zweimodalität; kein isolierter kausaler Test.
- **„Der Gripper verursacht das Scheitern.“ — nicht belegt / offen.** Zeitliche und räumliche Koinzidenz isolieren keinen Gripper-Effekt.
- **„Häufiges Replanning verursacht die 0%-Stackrate.“ — nicht belegt / offen.** h=4 bleibt erfolglos; die Intervention isoliert keinen Neusamplingmechanismus.
- **„Diffusion Policy ist generell schlechter als Direct BC.“ — nicht belegt / offen.** Untersucht sind konkrete Architekturen, Lernziele, ein Datensatz und eine Aufgabe.
- **„Mehr DDIM-Schritte können Diffusion grundsätzlich nicht verbessern.“ — nicht belegt / offen.** Null Stacks gelten für die getesteten Gewichte und Bedingungen; Teilmetriken verbessern sich teilweise.
- **„Alle Diffusionssamples sind schwach oder unbrauchbar.“ — durch die Paneldaten widerlegt.** Jede untersuchte Transportobservation enthält ein Sample oberhalb beider Diagnoseschwellen; das beweist noch keinen erfolgreichen vollständigen Chunk.
- **„Die native Policy scheitert, weil sie Samples mittelt.“ — nicht belegt.** Sie führt jeweils ein Sample aus; Mittelaktionen sind Diagnosen.
- **„Exaktes Expert-Timing oder volle Expert-Lifthöhe sind hier notwendig.“ — durch erfolgreiche Gegenbeispiele widerlegt.** Andere Aufgaben können andere Anforderungen besitzen.
- **„Fehlende State-Normalisierung erklärt allein das Scheitern.“ — nicht belegt / offen.** Der Zusatzversuch liefert bessere Teilmetriken, aber keine robuste replizierte Lösung.
- **„Längeres Training oder eine neue Architektur werden Diffusion retten.“ — nicht belegt / offen.** Die entsprechenden Verbesserungen sind nicht nachgewiesen.
- **„Die Eingaben enthalten prinzipiell keine ausreichende Wechselinformation.“ — nicht belegt / offen.** Trennbarkeitsproben finden nutzbare Hinweise; vollständige Markov-Beobachtbarkeit folgt daraus nicht.

## 7. Discussion

Für das Ziel **„Erweiterung und Evaluation von Behavioural-Cloning-Verfahren mit Robomimic“** zeigt der Versuch den Nutzen einer kontrollierten, kapazitätsmäßig vergleichbaren direkten Chunk-Baseline und einer Evaluation über unabhängige Trainingsinitialisierungen. Eine leistungsfähigere Verteilungsmodellierung ist eine Modellierungsmöglichkeit; sie ist kein empirischer Vorteil, solange die konkrete Implementierung die Aufgabenabfolge nicht zuverlässig ausführt.

Direct-MSE misst Aktionen, Diffusion-MSE die Rauschvorhersage. Ihre Zahlen bilden keine gemeinsame Qualitätsskala. Auch passende Einzelsamples, größere XY-Normen, bessere Timingdiagnosen oder erreichte Teilphasen belegen keine vollständige Stack-Policy. Closed-loop-Rollouts prüfen akkumulierte Zustandsabweichungen, Kontakte, Griffhaltung, Positionierung und Freigabe. Der Stabilitätstail unterscheidet nachhaltigen Erfolg von einem kurz gültigen Stackzustand. Offline-Diagnosen bleiben wertvoll zur Eingrenzung, ersetzen jedoch nicht das Endkriterium.

**Inferenz- und Rechenaufwand:** Direct berechnet einen Chunk mit einem Netzwerk-Forward-Pass. Diffusion benötigt initiales Gaußrauschen und bei d DDIM-Schritten d aufeinanderfolgende Noise-Predictor-Auswertungen plus Scheduleroperationen. Das ist im vorhandenen Sampler überprüfbar. DDIM-50 hat fünfmal so viele Denoiserauswertungen wie DDIM-10; damit ist keine exakt fünffache Gesamtlatenz nachgewiesen. Kürzere Ausführungshorizonte erhöhen bei beiden Klassen die Zahl der Chunkberechnungen. [S4/S17]

Historische Laufzeiten sind durch konkurrierende GPU-Prozesse und unterschiedliche Zeitgrenzen beeinflusst. Ein belastbarer allgemeiner Geschwindigkeitsfaktor wird nicht angegeben. Besonders Seed-1-Diffusion besitzt nur die Summe der Trainings-Epochenzeiten, keinen vergleichbaren vollständigen Prozesszeitraum. Gleiches Trainingsbudget bezeichnet Updates und Batchmenge, nicht identisches Zeit- oder FLOP-Budget. [S1/S15]

Die komplexere iterative Inferenz bietet in der Hauptkonfiguration keinen Erfolgsgewinn gegenüber Direct. Das rechtfertigt Direct als erfolgreiche Baseline der Projektarbeit und Diffusion als untersuchte Erweiterung mit dokumentiertem negativem Hauptbefund. Es rechtfertigt keine allgemeine Ablehnung von Diffusion Policy. Die separate normalisierte Variante mit vereinzeltem Erfolg unterstreicht die notwendige Begrenzung.

## 8. Limitations

- Nur drei unabhängige Trainingsreplikate je Hauptklasse. Starts und Inferenzsamples sind keine weiteren Trainingsreplikate.
- Ein Datensatz eines programmierten Experts und eine simulierte State-Aufgabe; keine Generalisierung auf Vision, reale Robotik oder andere Aufgaben.
- Wiederholt diagnostisch verwendetes Validierungspanel und feste Starts sind kein neuer unberührter Testdatensatz.
- Architektur, Lernziel und native Implementierungsdetails unterscheiden sich gemeinsam. Historische uniforme Sampler liefern keine nachgewiesen identischen Indexfolgen.
- Gleiches Update-/Batchbudget und vergleichbare Parameterzahlen bedeuten keine gleichen FLOPs, Walltimes oder optimalen Konfigurationen.
- Offlinepanel umfasst den Expert-Lift→Transport-Bereich, keine vollständige Greif-/Release-Verteilung und keine systematische Stichprobe aller erreichten Rolloutzustände.
- Phasenindikatoren sind nicht zwingend verschachtelt; Expert-Vollhöhe ist kein notwendiges Success-Kriterium.
- Grasp-Verlust bedeutet nativen Prädikatwechsel; wiederholte Ereignisse einer Episode sind abhängig und nicht automatisch physische Fälle.
- Numerische Replayabweichungen beeinflussen Diffusionstrajektorien. Bei 20 historischen Seed-1-Traces fehlen gespeicherte Tails; die Messphase ist vorhanden, neue Traces sind vollständig.
- DDIM-20 nur offline; Horizonte bei DDIM-10 und Schrittzahlen bei h=2, kein vollständiger Kreuzvergleich.
- Null beobachtete Erfolge und Null Seed-SD beweisen keine exakte Null-Erfolgswahrscheinlichkeit in einer Grundgesamtheit.
- KDE-Diagnosen hängen von Koordinaten, Schwellen und Bandbreiten ab; kein formaler allgemeiner Multimodalitätsnachweis.
- Normalisierungsvarianten und ältere Fortsetzungsversuche besitzen nur einen Trainingsseed und andere Bedingungen.
- Laufzeitaufzeichnungen sind keine isolierten Geschwindigkeitsbenchmarks.

### Dokumentierte Zahlen- und Definitionskonflikte

1. **Historische gegenüber frischer Diffusionsbaseline:** Historische Grasp/Lift/Transport-Zahlen sind 31/24/15, 26/18/8, 27/19/9 je Seed. Die frische h=2/DDIM-10-Baseline ergibt 31/24/15, 27/18/10, 25/21/7. Beide behalten 0/40 stabile Stacks. S3 dokumentiert numerische Replayabweichungen; Direct-Baseline-Replays sind bitgleich. Historische Zahlen dienen der historischen Failure-Analyse, frische Zahlen den Inferenzinterventionen. [S2/S3/S9]
2. **„Uniform mit Zurücklegen“:** S4 und das ursprüngliche Protokoll S16 beschreiben Diffusion pauschal so; S15 präzisiert anhand des Quellcodes das DataLoader-Verfahren. Eine Gleichheit exakter Ziehfolgen ist nicht nachgewiesen. Der ursprüngliche Bericht bleibt erhalten.
3. **Richtung und Ziehungsumfang:** Historischer Expert-Cosinus und späterer Zielcosinus, acht und 64 Draws sowie gepoolte gegenüber bedingten Quantilen sind unterschiedliche Größen. Ihre Abweichungen werden nicht stillschweigend als gleiche Metrik zusammengeführt.
4. **Ältere Stabilitätsdefinitionen:** S12 unterscheidet das damalige native Stackkriterium von der weiteren zweisekündigen Fortsetzung. Diese Zahlen werden nicht mit dem Hauptkriterium gepoolt.
5. **Normalisierung:** 2/40 aus S15 stammen von einem anderen trainierten Checkpoint. Das widerspricht keinem Befund der sechs unnormalisierten Modelle, begrenzt aber Aussagen über sämtliche vorhandenen Diffusionsversuche.
6. **Historische Ursacheformulierungen:** Ältere Berichte sprechen teils von „Mitursache“ oder „unzureichender Konditionierung“. Für das gesamte Scheitern folgt diese Synthese der vorsichtigeren maßgeblichen Analyse S3. Beobachtete Änderungen von Teilmetriken belegen keine isolierte Ursache der Stack-Nullrate.

## 9. Answers to Research Questions

**RQ1 — belegt.** Direct erreicht in allen drei Trainingsseeds stabile Stacks mit Erfolgsraten von 70,0–77,5%; Diffusion jeweils null. Der Abstand ist für diese Aufgabe, Starts und finalen Konfigurationen konsistent. Keine Signifikanz- oder allgemeine Policy-Rangfolge wird behauptet. [S2]

**RQ2 — belegt.** Die Notwendigkeit exakten Expert-Timings beziehungsweise voller Expert-Lifthöhe ist für diese Starts durch erfolgreiche Gegenbeispiele widerlegt. Direct bildet den lokalen Sprung schwach ab, startet offline früh und erzielt dennoch stabile Stacks; 68/89 Erfolge ohne Vollhöhe, 70/89 mit vorzeitigem Transport. Timing kann weiterhin Robustheit beeinflussen, ist aber nicht mit Aufgabenlösbarkeit gleichzusetzen. [S2/S3]

**RQ3 — belegt.** Die untersuchten Direct-Outputs sind stärker und konsistenter zielgerichtet. Diffusion ist zustandsbedingt breit, erfüllt nur selten gemeinsam die Stärke-/Richtungsschwellen, enthält jedoch bei jeder Panel-Transportobservation brauchbare Einzelsamples. Diese Aussage beschreibt trainierte Implementierungen. Ein isolierter Nachteil von Stochastik, Diffusionslernziel oder Architektur ist **nicht belegt / offen**. [S5/S6]

**RQ4 — teilweise gestützt.** Unzuverlässiger Zieltransport, häufige frühe Grasp-Verluste mit Öffnungskommandos und mögliche Unterbrechungen durch Neusampling sind mit dem Scheitern vereinbar. Die Defizite sind beobachtet; ihre isolierten kausalen Beiträge und Entstehungsursachen sind **nicht belegt / offen**. Keine allgemeine Zweimodalität oder alleinige Gripper-/Replanningursache wird behauptet. [S3/S7/S8]

**RQ5 — belegt.** Die konkret geprüften Horizonte und DDIM-Schrittzahlen beheben das Scheitern bei den finalen Gewichten nicht: jeder Seed bleibt bei 0/40 und ohne Release. Teilindikatoren ändern sich. DDIM-20 besitzt keinen Closed-loop-Test. Für ungetestete Konfigurationen oder neu trainierte Modelle bleibt die Wirkung **nicht belegt / offen**. [S5/S9/S10]

**Statuskonvention:** „Belegt“ bezeichnet die eng formulierte empirische Antwort im geprüften Geltungsbereich. „Teilweise gestützt“ bezeichnet vereinbare mechanistische Erklärungen ohne isolierten Kausalnachweis. „Nicht belegt / offen“ begrenzt stärkere Aussagen. Ein negativer Test innerhalb eines Bereichs ist kein universeller Unmöglichkeitsnachweis.

## 10. Recommended Next Step for the Project

**Zwingend notwendige weitere Experimente: keine für die bisherigen Forschungsfragen.** Ergebnis und Diskussion dürfen Mechanismen ausdrücklich offenlassen. Vollständige Ursachenidentifikation ist keine Voraussetzung, einen replizierten deskriptiven Vergleich abzuschließen.

| Möglicher Anschluss | Bewertung für bisherige Fragen | Begründung / neuer Erkenntniszweck |
| --- | --- | --- |
| Weitere DDIM-Schrittzahlen | nicht mehr sinnvoll als ungerichteter Sweep | 5/10/50 closed-loop, 20 offline beantworten die bestehende Frage. Nur eine neue begründete Samplerhypothese rechtfertigt Erweiterung. |
| Weitere Replanning-Horizonte | nicht mehr sinnvoll als ungerichteter Sweep | 1/2/4 sind geprüft. Neue Latenz-/Persistenzfragen müssten die Mechanismen getrennt kontrollieren. |
| Isoliertes Erzwingen geschlossenen Grippers | wissenschaftlich interessant, aber optional | Prüft Beitrag frühen Öffnens zur Griffhaltung und zum Transport; nicht notwendig für aktuelle Synthese. |
| Zusätzliche Trainingsseeds | wissenschaftlich interessant, aber optional | Erhöhen Präzision der Seedvariation; keine Voraussetzung für den deskriptiven Abstand der vorhandenen drei Seeds. |
| Längeres Training | wissenschaftlich interessant, aber optional | Neue Frage zur Budgetabhängigkeit; nur vorab definierte gepaarte Budgetstudie beider Klassen, kein Rettungsversuch allein wegen null Erfolg. |
| Neue Diffusionsarchitektur / neues Training | wissenschaftlich interessant, aber optional | Neue Methodenfrage. Nur bei präziser abgeleiteter Hypothese; für die jetzigen Antworten nicht erforderlich. |

Ein optionaler Grippertest müsste eine vorab definierte Haltephase beziehungsweise ein Freigabegate verwenden. Dauerhaftes Erzwingen „geschlossen“ verhindert Release und wäre kein sinnvoller Nachweis stabiler Stacks. Getrennte Griff-/Transport- und Enderfolgskriterien sowie unveränderte Gewichte, Armkommandos, Starts und Noise wären erforderlich. Dieser Test würde eine neue Kausalfrage beantworten und wurde hier nicht ausgeführt.

**Empfehlung:** Experimentkapitel jetzt abschließen: Direct als funktionierende replizierte Baseline, Diffusion als unter kontrollierten Bedingungen erfolglose Hauptkonfiguration, Failure-Analyse als Eingrenzung mit offenen Mechanismen. Originalvergleich, frische Inferenzmatrix und separate Zusatzexperimente getrennt darstellen. Keine Checkpoints ersetzen, keine nachträgliche Best-Run-Auswahl und kein weiteres Training für diese Synthese.

### Quellen und Nachvollziehbarkeit

Die Quellenkennungen beziehen sich auf bestehende lokale Artefakte. S3 ist die maßgebliche Ursachenanalyse. Die Begleit-JSON enthält genaue Kennzahlen, Evidenzkennungen, Geltungsbereiche und SHA-256 der zur Verifikation gelesenen Quellen. Kernzahlen wurden gegen JSON/CSV geprüft; Sampleabdeckung und Verluste zusätzlich aus Beobachtungs-/Ereigniszeilen rekonstruiert.

- **S1:** [ERGEBNISSE.md](ERGEBNISSE.md) — Hauptbericht der Seed-Replikation.
- **S2:** [analysis.json](analysis.json) — Originalbaseline, Seedaggregate, Startvariation und Expert-Timing.
- **S3:** [diffusion_failure_analysis.md](diffusion_failure_analysis.md) — maßgebliche Ursachenanalyse und Audits.
- **S4:** [Direct-Ergebnisbericht](../stack_direct_20261001/ERGEBNISSE.md) — Architektur und Ausgangsvergleich.
- **S5:** [sample_summary.json](failure_analysis/sample_summary.json) — bedingte Samplemetriken, transport_6_10.
- **S6:** [Chunkmetriken](failure_analysis/chunk_position_metrics.json), [erste Aktion](failure_analysis/chunk_first_vs_later.json), [Observationmetriken](failure_analysis/sample_observation_metrics.csv) — alle Positionen, Zielrichtung und Sampleabdeckung.
- **S7:** [Verlustereignisse](failure_analysis/baseline_events.json), [historische Einzelstarts](failure_analysis/baseline_failures.csv), [Verlustzusammenfassung](failure_analysis/loss_event_summary.json).
- **S8:** [gemeinsame Dichte](failure_analysis/conditional_joint_density_modes.json), [Zielprojektionsdichte](failure_analysis/conditional_density_modes.json) — explorative KDE.
- **S9:** [closed_loop_summary.json](failure_analysis/closed_loop_summary.json) — frische Horizon-/DDIM-Matrix.
- **S10:** [Evaluation-Audit](failure_analysis/final_evaluation_audit.json), [Input-Audit](failure_analysis/final_input_verification.json) — Mengen, Parität und unveränderte Quellen.
- **S11:** [Umschaltdiagnose](../stack_switch_20261001/DIAGNOSE.md), [Datenanalyse](../stack_switch_20261001/data_analysis.json).
- **S12:** [Balancierungsversuch](../stack_balance_20261001/ERGEBNISSE.md) — separater früherer Fortsetzungsversuch.
- **S13:** [Dynamikversuch](../stack_dynamics_20261001/ERGEBNISSE.md) — separater früherer Fortsetzungsversuch.
- **S14:** [Scheduler-Follow-up](../stack_followup_20261001/RESULTS.md) — historische andere Bedingungen.
- **S15:** [Normalisierungsbericht](../stack_normalization_20261001/results_normalization.md), [Normalisierungsdaten](../stack_normalization_20261001/results_normalization.json) — separater 2×2-Versuch und Samplerpräzisierung.
- **S16:** [protocol.json](protocol.json), [verification.json](verification.json) — Daten, Budget und Checkpointidentitäten.
- **S17:** [Graph-Sampler](failure_analysis/scripts/graph_sampler.py) — vorhandener DDIM-Loop, ein Denoiseraufruf je Schritt.
