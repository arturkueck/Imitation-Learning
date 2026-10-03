# Vergleich der fünf Methoden

Dieser Vergleich dient der präzisen Einordnung, **nicht der Auswahl einer neuen Methode**. A beschreibt Quelleninhalt; B vergleicht ihn. C steht separat in [relation_to_our_results.md](relation_to_our_results.md). Alle Seiten beziehen sich auf die in [INDEX.md](../INDEX.md) fixierten Fassungen.

## A: Was die Quellen jeweils verändern

| Dimension | DAgger | DART | Stable-BC | ACT | Diffusion Policy |
|---|---|---|---|---|---|
| Primärer Eingriff | Expertlabels auf Zuständen der Erhebungspolicy, iterative Aggregation | Gestörte Expertenausführung und neue Korrekturdemos | BC-Loss plus lokale Stabilitäts-/Kopplungsstrafe | Sequenzrepräsentation, CVAE und überlappendes Ensembling | Konditionierte generative Aktionssequenz und Receding Horizon |
| Stateverteilung der Erhebung | Learner/Expert-Mischung | Noisy Supervisor | Unveränderter Offline-Datensatz | Menschliche oder geskriptete Offline-Demos | Vorhandene Offline-Demos |
| Neue Expertinteraktion Teil der Methode? | Ja | Ja | Nein für den beschriebenen Loss | Nein während Policytraining/-evaluation | Nein während Policytraining/-evaluation |
| Policyfamilie | Metaalgorithmus mit austauschbarem Supervised Learner | Datenerhebung mit anschließendem Supervised Learner | Differenzierbare Policy mit Dynamikableitungen | Transformer-CVAE | CNN/UNet oder Transformer-Denoiser |
| Temporalstruktur | Originallabels pro besuchtem Zustand; Kandidaten über Runden | Originallabels pro gestörter Demo; Kovarianzanpassung über Runden | Kontinuierliche lokale Zustandsfehlerdynamik | k Aktionen aus aktuellem Zustand, erneute Abfrage je Schritt mit Ensembling | T_p Aktionen aus T_o Observations; T_a Aktionen vor Replanning |
| Teststochastik | Stationäre deterministische Policy als Ziel; Erhebung kann mischen | Finales BC ohne erforderliche Teststörung | Kein Zufall als zentraler Policymechanismus verlangt | Im Original `z=0`, deterministische Dekodierung | Generierung beginnt mit Gaußrauschen; Sampling-/Solverabhängigkeit |
| Theorie | No-Regret-Reduktion, Loss-/Kostenbounds unter Annahmen | KL-/Supportargument mit beschränktem Loss und Supervisorannahme | Lokale linearisierte Stabilität; nur Preprintinhalt hier geprüft | Keine neue allgemeine globale Taskfehlergarantie | Keine allgemeine Closed-Loop-Stabilitäts-/Covariate-Shift-Garantie |
| Dynamikmodell | Kein bekanntes Modell erforderlich; Rollouts nötig | Kein bekanntes Modell erforderlich; Ausführung nötig | `f` bekannt; modellbasiert zusätzlich `g` | Kein explizites Modell erforderlich | Kein explizites Modell erforderlich |
| Kernbelege | DAG-01–07/10 | DART-01–05 | SBC-02–06/10 (Preprint) | ACT-01–04/08–09 | DP-01–04/07/09–10 |

Die Temporalstruktur bei DAgger/DART ist eine Beschreibung der ursprünglichen Methoden, keine Aussage, dass spätere Chunkvarianten prinzipiell unmöglich wären. Solche Varianten sind hier nicht gelesen oder geprüft.

## A: Experimente und Messgrößen

| Quelle | Hauptevidenz | Metrik und zentrale Vergleichsgrenze | Beleg |
|---|---|---|---|
| DAgger | Spiele und OCR; Expert-/Learner-Distribution | Stürze/Runde, Distanz/Level, Zeichenaccuracy; lineare Lerner, kein Robot-Stack | PDF S. 6–8; DAG-08–09 |
| DART | Vier Lokomotionstasks und HSR-Clutter | Reward, Rechenzeit, Erhebungsreward, Erfolg mit menschlich ausgelöstem Greifplan; konkrete Updatepläne | PDF S. 7–8/13–14; DART-06–10 |
| Stable-BC | Kreuzung, Quadrotor, visueller Point Mass, Air Hockey | Kosten, Goal-Success, Endabstand, Hits, Richtungswechsel; bekannte Roboterdynamik, v1 | Preprint PDF S. 5–8; SBC-07–09 |
| ACT | Zwei Simulationstasks × zwei Datenquellen, sechs reale Tasks | Finale und Teilphasen-Success; Simulation 3 Seeds, Hardware 1 Seed; Human/Script unterschiedlich | PDF S. 8–10/17; ACT-05–10 |
| Diffusion Policy | Robomimic, Push-T, Block Push, Kitchen, reale Tasks | Success/IoU/Subgoals; verschiedene Checkpointregeln, Aktionsräume und Backbones | PDF S. 6–10/14–16; DP-05–09 |

Die Erfolgsmetriken haben unterschiedliche Nenner und Endbedingungen. Kein paperübergreifendes Mittel, kein gemeinsames Ranking und keine bereinigte Metaanalyse wurden berechnet.

## B: Mechanismen, die auseinanderzuhalten sind

**Datenabdeckung versus Policyrepräsentation:** DAgger und DART erzeugen neue Zustands-/Aktionssupervision. Stable-BC verändert Ableitungseigenschaften der Policy auf dem vorhandenen Datensatz. ACT und Diffusion Policy erweitern die Aktionsrepräsentation und zeitliche Ausführung. Das sind unterschiedliche Eingriffe; hohe Ausdruckskraft beweist keine korrekten Aktionen außerhalb der Demos.

**Covariate Shift versus Partial Observability:** Die Verteilungsverschiebung zwischen Erhebung und Policyrollout ist nicht dasselbe wie fehlende Information über Expertgedächtnis. Wenn dieselbe beobachtete Eingabe verschiedene phasenabhängige Expertenaktionen zulässt, beseitigt die Sammlung weiterer identischer Eingabeformen diese Mehrdeutigkeit nicht automatisch. Die fünf Papers messen diesen lokalen Stack-Fall nicht.

**Error Accumulation versus eine konkrete Taskabweichung:** Der DAgger-Worst-Case-Bound kann Fehlerakkumulation erklären, sagt aber nicht, dass jede Abweichung vom Expert-Timing schadet. ACTs Horizontargument und DPs Konsistenzargument können gleichfalls nur mit ihren Versuchsbedingungen verwendet werden. Eine abweichende, erfolgreiche Transportbahn ist nicht allein wegen ihrer Abweichung ein Taskfehler.

**Robustheit hat mehrere Bedeutungen:** DART nutzt Korrekturdaten; Stable-BC behandelt lokale Fehlerdynamik; ACT bewertet glattere Ausgabe und empfindliche Teilphasen; DP zeigt außerdem qualitative Perturbationsreaktionen und Latenzablationen. Nominaler Taskerfolg, lokale dynamische Stabilität, Trainingsstabilität, Messrauschenrobustheit und Recovery nach physischer Störung sind unterschiedliche Claims.

**Chunking versus Original-ACT:** Sowohl ACT als auch DP erzeugen Aktionsfolgen. ACT kombiniert verschiedene Pläne für denselben Zeitpunkt, DP führt einen begrenzten Teil eines neu generierten Plans aus. Ein deterministischer Chunk-Regressor kann Chunking implementieren, ohne Transformer, CVAE oder Ensembling zu enthalten. Die Modelle dürfen daher nicht allein anhand der Chunklänge benannt werden.

**Generativ ist nicht automatisch stochastisch im Test:** ACT trainiert generativ, verwendet aber im beschriebenen Protokoll einen festen Latent. DP sampelt eine initiale Rauschfolge. Beide brauchen Daten, aus denen eine sinnvolle konditionale Verteilung gelernt werden kann; aus ihrer Familie folgt nicht die tatsächliche Zahl relevanter Modi unseres Datensatzes.

## B: Bedingungen für zitierfähige Vergleiche

Für eine Aussage über einen Effekt gehören Datenquelle und -menge, Modalität, Aktionsraum, Architektur, Ausführungshorizont, Budget, Checkpointauswahl und Evaluationseinheit zur Aussage. Diese Bedingungen sind im Methodendossier hinterlegt; fehlende oder widersprüchliche Angaben stehen in [GAPS_AND_QUESTIONS.md](../GAPS_AND_QUESTIONS.md).

Die fünf Primärarbeiten bieten **keinen** isolierten gemeinsamen Versuch, der bei identischem State-Stack-Setup alle Methoden gegeneinander prüft. Auch der lokale Vergleich isoliert nicht jeweils nur eines der theoretischen Konzepte. Ein späterer Bericht darf ihre Mechanismen vergleichen, muss quantitative Effektgrößen jedoch an die jeweilige Originalbedingung binden.
