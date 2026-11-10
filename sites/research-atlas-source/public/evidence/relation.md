# Literaturbezug zu unseren State-Stack-Ergebnissen

Stand: 1. Oktober 2026. **Keine neue Methode, kein Training und keine neue Evaluation.** A bezeichnet Primärliteratur; B unsere analytische Interpretation; C die dokumentierten Projektbefunde. Literaturzahlen werden nicht als Erwartungen für das Projekt behandelt.

## C: Projektbefunde

Die Basis ist die [Trainingsseed-Replikation](../../experiments/stack_diagnostics/stack_replication_20261001/ERGEBNISSE.md), ihr [Protokoll](../../experiments/stack_diagnostics/stack_replication_20261001/protocol.json) und der in [next_research_direction.md](../../next_research_direction.md) zusammengefasste Stand. Rahmenziel: [Projektbeschreibung](../../Projektarbeit%20Themenvorschlag%20--%20Artur.md). Die Berichte sind Projektevidenz und keine peer-reviewten Literaturquellen. Es wurde kein unabhängiger erneuter Simulator-/Checkpointlauf vorgenommen.

| Projekt-ID | Dokumentierter Befund C | Primärer lokaler Beleg |
|---|---|---|
| OUR-01 | Lokales `StackTwo`, zwei 4-cm-Würfel, eigener Success-/Stabilitätscheck; kein unveränderter offizieller Robomimic-Stack-Score | Replikationsbericht, Aufgaben-/Kriteriendefinition; `praxis/src/task_extensions/environments.py` |
| OUR-02 | 200 erfolgreiche programmierte Demos; 180 Training, 20 Validation; 27322 Trainingsanker | Protokoll: `train_demos`, `valid_demos`, `training_frames`; keine menschlichen PH-Demos |
| OUR-03 | Zwei Stateframes, je 15 Merkmale; absolute A-/B-Positionen, EEF-Position, Quaternion und Gripperpositionen | Projektstand; `direct_common.py`, `ORDER`/`flatten` |
| OUR-04 | Direct: Residual-MLP, acht Blöcke, Breite 2048, Output 16×7 mit Tanh; Aktions-MSE. Diffusion: UNet, Epsilon-Ziel, zehn DDIM-Schritte | Direct-Code; Protokoll und Replikationsbericht; finale Konfigurationen |
| OUR-05 | Chunkindex 0 entspricht t−1; Indizes 1 und 2 werden ausgeführt, danach Replanning. Diffusion wird vor der Evaluation auf zwei Aktionen gesetzt | `balance_common.py`, Fensterbildung; `direct_common.py`, `chunk[1:3]`; [evaluate_replication.py](../../experiments/stack_diagnostics/stack_followup_20261001/scripts/evaluate_replication.py), Laufzeitoverride; Protokoll `executed_action_slice` |
| OUR-06 | Gleiche 30000 Updates, Batch 8, 240000 Trainingsfenster je Modell; Rohobservations unnormalisiert | Eingefrorenes Protokoll; Replikationsbericht Trainingskontrolle |
| OUR-07 | Direct: 28/40, 30/40, 31/40 stabile Stacks; Mittel 74,2 %, Stichproben-SD 3,8 Prozentpunkte über drei Trainingsseeds | Replikationsbericht Ergebnis je Trainingsseed |
| OUR-08 | Diffusion: 0/40 je Trainingsseed, 0/120 insgesamt; drei Trainingsreplikate mit denselben vierzig Starts | Replikationsbericht; keine 120 unabhängigen Trainingsreplikate |
| OUR-09 | 70/89 erfolgreiche Direct-Rollouts transportieren nach der lokalen Frühdefinition vorzeitig; 68/89 erreichen keine Expert-Vollhöhe | Replikationsbericht, Forschungsfrage 2; Phasenkriterien beibehalten |
| OUR-10 | Fünf Starts scheitern bei allen drei Direct-Seeds; die ersten nicht erfüllten Indikatoren betreffen u. a. Grasp, Release und Absenken | Replikationsbericht Variation der Startzustände; Beschreibung, keine kausale Fehlerklasse |
| OUR-11 | Gepoolte Offline/Success-Korrelationen über sechs Modelle sind durch Modellklasse konfundierbar; innerhalb Direct nur drei Modelle | Replikationsbericht Offline ↔ Closed Loop |
| OUR-12 | `StackExpert` besitzt `phase`, `phase_steps` und gespeichertes `target` | [stack_expert.py](../../praxis/src/task_extensions/stack_expert.py), `__init__`/`__call__` |
| OUR-13 | Die lokale Lift-Kontraktion nutzt finite differences und geschätztes K; sie erwartet Lift-Objektvektor der Länge 10 | [contraction_bc.py](../../praxis/src/robomimic_ext/contraction_bc.py), Shapeprüfung und Lossberechnung |

Für OUR-04: Parameterzahlen laut Replikationsbericht Direct 67467376, Diffusion 65648903. Nahe Parameterzahl bedeutet keine identische Architektur. Direct ist strukturell einfacher, aber kein kleines Netz.

Für OUR-05: Die gespeicherte [Diffusionskonfiguration für Seed 2](../../experiments/stack_diagnostics/stack_replication_20261001/diffusion/seed_2/config.json) enthält `action_horizon: 8`. Der Evaluationscode überschreibt dieses Feld im geladenen Checkpoint auf `2`, bevor die Policy erzeugt wird. Der Vergleich verwendet deshalb zwei ausgeführte Aktionen, obwohl die unveränderte Konfigurationsdatei acht nennt. Gespeicherte Konfiguration und Laufzeitverhalten sind hier getrennte Belege.

Unser stabiler Stack verlangt die ursprüngliche Success-Bedingung mit Kontakt und freigegebenem Würfel über zusätzliche 40 Frames / 2 Sekunden bei 20 Hz. Expert-ähnliche Vollhöhe und Grenzreaktion sind Diagnosen, keine notwendigen Endbedingungen. Die einzelnen Phasenindikatoren sind nicht zwingend ein verschachtelter Funnel.

**Zusatzkontext mit begrenztem Status:** [diffusion_failure_analysis.md](../../experiments/stack_diagnostics/stack_replication_20261001/diffusion_failure_analysis.md) bezeichnet sich beim Lesen als Zwischenstand mit noch nicht vollständig abgeschlossener Closed-Loop-Matrix. Seine schwache/uneinheitlich gerichtete Transportverteilung wird hier nicht als abgeschlossene kausale Erklärung oder neue finale Erfolgsstudie übernommen.

## A/B/C: Konkrete Literaturverknüpfungen

| Literatur A | Projekt C | Eigene Einordnung B | Nicht zulässiger Schluss |
|---|---|---|---|
| DAG-01–04: Expert-Loss und eigener Rollout-Loss unterscheiden sich; Worst-Case-Bounds sind bedingt | OUR-07–11: Offline-Diagnosen sind nicht identisch mit stabiler Tasklösung | Die Primärquelle begründet die konzeptionelle Trennung von Offline-Imitation und Closed Loop | „Unsere MSE impliziert T² Fehler“ oder „Covariate Shift ist die gemessene Hauptursache“ |
| DAG-05–07: Expertlabels auf aktuell besuchten Zuständen | OUR-02/12: ausschließlich vorhandene nominale Demos; Expert mit internem Gedächtnis | Der verfügbare Datensatz ist kein DAgger-Datensatz; Oraclekompetenz an fremden Zuständen bleibt offen | „Expert neu starten liefert korrekte DAgger-Labels“ |
| DART-02/04: gestörte Ausführung erzeugt neue Expertenreaktionen | OUR-02/06: gleicher nominaler Datensatz in Replikation | Datenaugmentation, Sampling und gestörte Datenerhebung sind getrennte Eingriffe | „Nachträgliches State-Noise wäre bereits DART“ |
| DART-07–08: HSR-Kriterium enthält Objekterkennung/freien Pfad und menschlich ausgelöstes Greifen | OUR-01/07: autonomer stabiler Stack mit Kontakt/Freigabe | Die Erfolgsraten beider Settings haben verschiedene Aufgaben- und Hilfeanteile | „DART sollte auch bei uns +30 Prozentpunkte erzielen“ |
| SBC-03–06/10: lokale Fehlerdynamik, bekannte f, Umgebungskopplung; geprüfte Fassung nur Preprint | OUR-04/05/13: Chunkqueue und finite-difference Lift-Modul | Der Zusammenhang ist eine Inspirations-/Interpretationsebene; keine Originalimplementation | „Der lokale Kontraktionsloss erbt Stable-BC-Stabilität“ |
| ACT-01–04: Chunking, CVAE und Ensembling sind getrennte Bestandteile | OUR-04/05: Direct hat bereits Chunking, keine CVAE/TE | Die lokale Baseline ist direkte Chunkregression | „Direct ist ACT“ oder „ACT führt erstmals Chunking ein“ |
| ACT-09: CVAE-Ablation ist bei Human-/Scriptdaten unterschiedlich | OUR-02/12: programmierter Expert mit Gedächtnis | Datenherkunft muss bei der Literaturinterpretation genannt werden; deterministischer Code garantiert keine beobachtungsbedingte Eindeutigkeit | „Menschlicher CVAE-Gewinn gilt für unser Script“ oder „Scriptdaten sind immer unimodal“ |
| DP-01–02: Aktionsdiffusion und drei Horizonte | OUR-04–06: lokale UNet-/DDIM-/Chunkparameter | Die lokale Policy nutzt diesen Grundmechanismus bei verändertem Ausführungs-/Trainingsbudget | „Unsere Konfiguration reproduziert Tabelle I“ |
| DP-03/05/07: Backbone, Aktionsraum und Replanning beeinflussen Ergebnisse | OUR-07/08: Direct erfolgreich, Diffusion hier erfolglos | Die Diskrepanz begrenzt Allgemeinaussagen; Architektur und Objective sind gemeinsam verändert | „Diffusion als Familie ist widerlegt“ oder „UNet-Oversmoothing ist kausal nachgewiesen“ |
| DP-08/10: Recovery-Beispiel ist qualitativ; BC-Datengrenzen bleiben | OUR-10: verbleibende Direct-Fehler u. a. Release/Absenken | Ein fremder Push-T-Recoveryclip erklärt noch keinen lokalen Stackfehler | „Publizierte Recovery garantiert Stack-Release-Robustheit“ |

## B: Belastbare Formulierungen für den späteren Bericht

„Der Vergleich zeigt unter den dokumentierten lokalen Bedingungen einen reproduzierten Abstand zwischen direkter Chunkregression und der untersuchten UNet-Diffusionskonfiguration. Da Architektur und Lernziel gemeinsam variieren, isoliert er nicht den Effekt der Diffusionsformulierung.“ Grundlage C: OUR-04/07/08; Literaturrahmen A: DP-03/05/10.

„Die meisten erfolgreichen Direct-Rollouts erfüllen nicht das zusätzliche Expert-Vollhöhenkriterium. Expert-Trajektorienähnlichkeit und Aufgabenlösung sind in diesen Starts verschiedene Messgrößen.“ Grundlage C: OUR-09. Eine allgemeine Theorie über sicheres frühes Transportieren folgt daraus nicht.

„Die Literatur beschreibt unterschiedliche Wege, Fehlerakkumulation zu adressieren: neue Korrektursupervision, lokale Dynamikregularisierung und zeitliche/generative Aktionsrepräsentation. Die vorliegenden Experimente unterscheiden diese Mechanismen nicht einzeln.“ Grundlage A: DAG-05, DART-02, SBC-04/06, ACT-01–03, DP-01–02; B: die Vergleichsinterpretation.

## B/C: Aussagen, die weiterhin offen sind

Nicht isoliert nachgewiesen sind die kausale Rolle von Covariate Shift, bedingter Multimodalität, versteckter Expertphase, UNet-Frequenzbias, Normalisierung, Sampleauswahl oder dem Gripperkommando. Die drei Direct-Seeds validieren keinen allgemeinen Offline-Prädiktor. Die vorhandenen Starthashes erlauben gepaarte lokale Vergleiche, machen die Rollouts aber nicht zu unabhängigen Trainingsreplikaten. Diese Grenzen sind Teil der Wissensbasis, kein Auftrag für neue Methoden oder Experimente.
