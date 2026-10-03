# Diffusion Policy

## 1. Vollständige bibliographische Angaben

Cheng Chi, Siyuan Feng, Yilun Du, Zhenjia Xu, Eric Cousineau, Benjamin Burchfiel, Shuran Song (2023). *Diffusion Policy: Visuomotor Policy Learning via Action Diffusion.* *Robotics: Science and Systems XIX*, Paper 026, Daegu, Republic of Korea, Juli 2023; Konferenz 10.–14. Juli. DOI [10.15607/RSS.2023.XIX.026](https://doi.org/10.15607/RSS.2023.XIX.026). [Offizielle Proceedings](https://www.roboticsproceedings.org/rss19/p026.html), [vollständige Bibliographie und spätere IJRR-Version](../BIBLIOGRAPHY.md#diffusion-policy--chi2023diffusionpolicy).

## 2. Publikationsstatus und geprüfte Fassung

**Peer-reviewed RSS-Originalpublikation**, [eingefrorenes PDF](../_research/diffusion_policy.pdf), 16 Seiten. Geprüft: Methoden, alle Experimentabschnitte, Limitations S. 11 und relevanter Appendix S. 14–16. Die spätere peer-reviewte IJRR-Fassung (online 2024, Heft 2025) wird nur bibliographisch abgegrenzt. Keine Inhalte/Seiten oder Autorenlisten verschiedener Fassungen vermischt.

## 3. Forschungsproblem — A

Aktionsimitation umfasst mehrere gültige Aktionen, zeitliche Kohärenz und hohe Präzisionsanforderungen. Einzelaktionregression bzw. beschränkte multimodale Parametrisierung kann diese Struktur schlecht abbilden. Energy-Based-Policies besitzen Ausdruckskraft, sind in den verglichenen Konfigurationen aber schwierig zu trainieren. Das Paper untersucht Aktionsdiffusion als alternative **Offline-BC-Policyrepräsentation**. S. 1–3/5.

## 4. Zentrale Hypothese / Motivation — A

Ein konditionierter Denoiser kann eine multimodale, hochdimensionale Aktionsfolge lernen, ohne den Normalisierer einer Energy-Based-Policy schätzen zu müssen. Receding-Horizon-Ausführung soll zwischen zeitlicher Konsistenz und Reaktionsfähigkeit vermitteln. Visuelle Konditionierung soll die Generierung zukünftiger Beobachtungen vermeiden. S. 1–3, §I–II.

## 5. Methode — A

Aus einer Beobachtungshistorie `O_t` wird während der Inferenz zunächst ein verrauschter Aktionschunk erzeugt. Ein trainiertes Netzwerk sagt bei jedem Diffusionsschritt Noise voraus, das iterativ entfernt wird. Die unmodifizierten Beobachtungen konditionieren den Denoiser. Erst die vollständige denoisierte Sequenz enthält ausführbare Aktionen; Diffusionsschritte sind keine realen Roboterschritte.

Es werden ein temporales 1D-CNN/UNet mit FiLM sowie ein Time-Series-Transformer verglichen. Der Roboter führt nur `T_a` Aktionen aus der `T_p` langen Vorhersage aus und plant mit neuem `O_t` erneut. Ein ResNet18-Encoder verarbeitet Bilder, sofern die Taskvariante visuell ist; Statevarianten benötigen diesen nicht. DDIM wird für reduzierte Echtzeitinferenz eingesetzt. S. 3–4/14–15.

## 6. Relevante Gleichungen — A

**Konditionierte Denoising-Rekursion**, S. 3, Gl. (4), in Papierschreibweise:

\[
A_t^{k-1}=\alpha\left(A_t^k-\gamma\epsilon_\theta(O_t,A_t^k,k)+\mathcal N(0,\sigma^2 I)\right).
\]

`k` ist Diffusionsiteration; `α,γ,σ` hängen vom Schedule ab. Diese vereinfachte Darstellung ist nicht ungeprüft der Updatecode eines konkreten DDIM-Schedulers.

**Epsilon-Trainingsziel**, S. 3, Gl. (5):

\[
L=\operatorname{MSE}\left(\epsilon^k,
\epsilon_\theta(O_t,A_t^0+\epsilon^k,k)\right).
\]

Das Paper schreibt das Vorwärtsrauschen schematisch additiv. **B, erklärende Standardnotation:** In einer DDPM-Implementierung kann `A^k=√ᾱ_k A^0+√(1−ᾱ_k)ε` verwendet werden. Dies ist hier keine zusätzliche nummerierte Gleichung aus dem Paper; dessen Schedule-/Scalingdetails sind in der jeweiligen Implementation zu prüfen. Epsilon-MSE und direkte Aktions-MSE sind unterschiedliche Lernziele.

**Score-/Normalisiererbeziehung**, S. 5, Gl. (6)–(8):

\[
p_\theta(a|o)=\frac{e^{-E_\theta(o,a)}}{Z(o,\theta)},\qquad
\nabla_a\log p_\theta(a|o)=-\nabla_aE_\theta(o,a),
\]

weil `∇_a log Z(o,θ)=0`. Die Zuordnung zu Noisevorhersage wird im Paper schematisch als `≈−ε_θ` geschrieben. Skalierung und Noiselevel dürfen in einer konkreten Implementierung nicht weggelassen werden. **B:** Trainingsstabilität über diese Repräsentation ist keine Hurwitz-Stabilitätsaussage wie bei Stable-BC.

**Horizonte**, S. 3: `T_o` Beobachtungen, `T_p` vorhergesagte Aktionen, `T_a` ausgeführte Aktionen bis zu neuem Feedback. Sie sind unabhängig zu dokumentieren.

**46,9%-Aggregation**, S. 15, Appendix G:

\[
r_i=\frac{\max\_ours_i-\max\_baseline_i}{\max\_baseline_i},\qquad
\bar r=\frac1N\sum_i r_i=0.46858\approx46.9\%.
\]

Verwendet werden Spalten aus Tabellen I, II und IV, ohne MH, mit Auswahl der jeweils leistungsfähigeren DP-Variante. Die Zahl ist ein Mittel **relativer** Verbesserungen, kein Prozentpunkteabstand und keine Vorhersage für ein neues Setup.

## 7. Verwendete Daten / Tasks — A

| Benchmark / Setting | Daten-/Taskdefinition |
|---|---|
| Robomimic | Lift, Can, Square, Transport, ToolHang; 200 PH-Demos pro Task; MH für die ersten vier mit 300 Demos; State- und RGB-Varianten |
| Simuliertes Push-T | 200 Demos; RGB oder neun 2D-Keypoints plus EEF-Propriozeption; präzises kontaktreiches Schieben |
| Block Push | 1000 geskriptete Episoden; zwei Blöcke/Targets, randomisierte Zuordnung und Reihenfolge |
| Franka Kitchen | Menschliche Multi-Task-Demos, vier Interaktionen in variabler Reihenfolge; widersprüchliche Demoanzahl, siehe DP-G2 |
| Reales Push-T | 136 Trainingsdemos, UR5; finaler IoU und anschließendes Wegfahren in Endzone |
| Mug Flip | Laut Tabelle III 250 Demos, Franka-Setup in Abb. 2; komplexe Grasp-/Push-Multimodalität |
| Sauce Pour / Spread | Laut Tabelle III jeweils 90 PH; Appendix I nennt jeweils 50 Demos, davon 90 % Training; ungeklärter Widerspruch |

S. 6–10/15–16. Insgesamt werden zwölf Tasks als Paperumfang angegeben; PH/MH- und Modalitätsvarianten erhöhen die Zahl der Bedingungen. **Kein Stack-Task** in der RSS-Tasktabelle. Ein gleicher Robomimic-Begriff bedeutet daher keine identische lokale Taskkonfiguration.

## 8. Baselines — A

LSTM-GMM (= BC-RNN im Robomimic-Kontext), IBC und BeT. LSTM-GMM wird reproduziert; andere Referenzwerte stammen nach §V-B aus den besten verfügbaren Original-/Reproduktionsquellen. Die visuelle Tabelle II enthält kein BeT; Block Push/Kitchen Tabelle IV enthält alle drei. Hardware Push-T: IBC und LSTM-GMM, jeweils verschiedene Aktionsräume, sowie DP-Backbone-/Encoderablationen. Weitere reale Tasks: LSTM-GMM. S. 6–10.

Hauptbenchmark vergleicht **die beste Aktionsraumwahl je Methode**: Position Control für DP, Velocity Control für Baselines (S. 7). Das ist kein nur im Loss variierender kontrollierter Architekturvergleich. Bei Mug Flip wird die LSTM-GMM-Policy laut S. 9 auf einer Teilmenge derselben Daten trainiert; deren Nullerfolg ist kein belegter Vergleich mit identischem Datensatzumfang.

## 9. Evaluationsmetriken — A

Simulation: Task-Success; Push-T Zielabdeckung; Block Push `p1,p2`; Kitchen Anzahl erfüllter Interaktionen `p1` bis `p4`. Tabellen I–II schreiben **bestes Checkpoint / Durchschnitt letzte zehn Checkpoints**. Drei Trainingsseeds, fünfzig Starts pro Seed; letzte zehn Checkpoints werden alle fünfzig Epochen gespeichert, sodass 1500 Ausführungen pro Tabellenbedingung zur Zehn-Checkpoint-Aggregation beitragen, ohne 1500 unabhängige Trainingsreplikate zu sein. S. 6–7.

Reales Push-T: Endzustands-IoU, Erfolg relativ zum minimalen Demo-IoU, Episodendauer; zwanzig gepaarte Starts. Dort festes Training von zwölf Stunden, letzter Checkpoint, außer IBC mit minimalem Train-Aktions-MSE (S. 15). Mug Flip: Erfolg über zwanzig Tests. Pour/Spread: IoU/Flächenabdeckung und daraus abgeleitete Erfolgsschwelle; Schlusscheckpoint nach 1000 Epochen, Abbruch bei Rückzug oder unsicherem Verhalten (S. 16). Kein universell identisches Erfolgskriterium über alle Tasks.

## 10. Zentrale Ergebnisse — A

**Konkreter Statevergleich, Square PH**, Tabelle I S. 6:

| Methode | Bester Checkpoint | Durchschnitt letzte zehn |
|---|---:|---:|
| LSTM-GMM | 0,95 | 0,73 |
| DP-C | 1,00 | 0,93 |
| DP-T | 1,00 | 0,89 |

Die Unterschiede zwischen Checkpointstatistiken sind Teil des Befunds, kein Rundungsfehler. Beispiel starker Backboneabhängigkeit: Block-Push-`p2` in Tabelle IV S. 7: DP-C 0,11, DP-T 0,94, BeT 0,71. Aus „Diffusion Policy“ folgt somit keine gleiche Performance beider Architekturen.

Reales Push-T mit End-to-End-CNN: 95 % Erfolg, IoU 0,80 gegenüber menschlich 0,84; beste LSTM-GMM-Bedingung 20 %, IBC 0 % (S. 8, Tabelle V). Mug Flip: DP 90 % über zwanzig Tests; Baselinevergleich mit Datenumfanggrenze oben. Sauce-Figure 11 S. 10: Pour 0,79 Success, Spread 1,00; die Zahl der Tests und das 0,79-Ergebnis dürfen ohne vollständige Rohdaten nicht zu einem vermeintlichen ganzzahligen Erfolgscount rekonstruiert werden.

Das Paper berichtet 46,9 % mittlere relative Benchmarkverbesserung; die genaue Definition steht oben. Separate Störungsepisode mit Kameraokklusion und verschobenem T-Block illustriert Recovery, liefert aber keine eigene statistische Robustheitsrate (S. 8–9).

## 11. Von Autoren genannte Limitationen — A

§VIII, S. 11: unzureichende Demonstrationen begrenzen BC weiterhin; höherer Rechenbedarf/Inferenzlatenz als z. B. LSTM-GMM; Sequenzvorhersage reicht möglicherweise nicht für besonders hochfrequente Regelung. §III-A, S. 3–4: CNN kann schnelle Aktionsänderungen übersmoothen; Transformer ist empfindlicher gegenüber Hyperparametern. §V-C, S. 7: lange Ausführungshorizonte verschlechtern Reaktionsfähigkeit. Keine Behauptung, dass expressive Verteilungen fehlende Recovery-Daten generell ersetzen.

## 12. Wichtige Annahmen — A und B getrennt

**A:** Geeignete Demonstrationen, zeitlich korrekte Beobachtungs-/Aktionsfenster, normierte Aktionsdimensionen, lernbarer konditionaler Aktionssupport, zum Regelungsbedarf passender Ausführungshorizont. Appendix A S. 14: überwiegend Min-Max-Aktionen in `[−1,1]`, besondere Behandlung nahezu konstanter/Rotationsdimensionen. Beobachtungsnormalisierung wird daraus nicht abgeleitet.

**B:** Rauschinferenz, Checkpointregel, Aktionsrepräsentation und Budget können Leistungsunterschiede beeinflussen. Das Paper testet keine allgemeine Garantie für nichtbeobachtbare Expertphasen; seine Fähigkeit zu Multimodalität ist keine Messung der Multimodalität unseres nominalen Datensatzes.

## 13. Übertragbarkeit auf unser State-Stack-Problem — B/C

**B:** `T_o/T_p/T_a`, Epsilon-Ziel und iterative Inferenz erlauben eine präzise Beschreibung der lokalen Diffusionpolicy. Die Backbone- und Aktionsraumunterschiede begrenzen kausale Aussagen. Quellenhinweise zu abrupten Aktionen sind eine mögliche Interpretation, nicht die verifizierte Ursache unserer Transportprobleme.

**C:** Lokal zwei Stateframes, 16×7 Chunk, Ausführung von Indizes 1/2, DDIM mit zehn Schritten, Batch 8 und 30000 Updates, unnormalisierte Rohobservations und bereits begrenzte Actions. Paper-Simulation nutzt typischerweise 100 Denoisingsteps, Statebatch 256 und 4500 Epochen; die meisten CNN-Tasks haben `T_a=8`, Positional Actions, deutlich größeres Modell. Unser eigener Task und programmierten Demos sind abweichende Bedingungen. Direct und Diffusion verändern zugleich Architektur und Lernziel.

## 14. Nicht übertragbare Punkte — B/C

Kein Widerspruch zwischen lokalen 0/120 stabilen Stacks und hohen anderen publizierten Benchmarkzahlen; sie betreffen andere Tasks/Protokolle. Keine generelle Widerlegung der Modellfamilie und keine Garantie auf Verbesserung aus der 46,9%-Zahl. Kein kausaler Beweis von Oversmoothing durch die lokale geringe Grenzreaktion. Die Paperlatenz auf einer RTX 3080 ist kein isolierter Benchmark unserer 12-GB-GPU. Die qualitative Recovery-Episode ist keine quantitative Evidenz für unsere Release-/Stabilitätskriterien.

## Belegstellen mit Claim-IDs

Zehn relevante Stellen aus **RSS 2023, Original-Proceedings**. Jede Seite ist eine konkrete PDF-Seite der archivierten Fassung. Originalzitate sind bewusst auf einen kurzen Auszug pro Paper begrenzt; „—“ bedeutet, dass hier kein Originalzitat gespeichert wird. Paraphrasen sind A; Verwendungen sind B. Der Projektbezug C steht in Abschnitt 13–14.

### DP-01 — PDF S. 3

- **Abschnitt:** §II-C; Gl. (4)–(5). [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Beobachtung ist eine Bedingung für die Rauschvorhersage und wird nicht selbst als zukünftiger Zustand generiert. Training lernt injiziertes Rauschen; Inferenz startet mit Gaußrauschen und verfeinert den gesamten Aktionschunk iterativ.
- **Mögliche Verwendung (B):** Methoden: Aktionsdiffusion versus gemeinsame Zustands-/Aktionsgenerierung.
- **Claim-ID:** [DP-01](../CLAIMS.md#dp-01); Evidenzklasse M.

### DP-02 — PDF S. 3

- **Abschnitt:** §II-C; Closed-loop action-sequence prediction. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** O_t enthält T_o Beobachtungen, der Generator erzeugt T_p Aktionen und der Roboter führt T_a davon vor erneutem Planen aus. Ein langer vorhergesagter Chunk bedeutet deshalb nicht, dass ebenso lange ohne neue Beobachtung gehandelt wird.
- **Mögliche Verwendung (B):** Methoden: getrennte Horizonte und Receding Horizon.
- **Claim-ID:** [DP-02](../CLAIMS.md#dp-02); Evidenzklasse M.

### DP-03 — PDF S. 3

- **Abschnitt:** §III-A; CNN-based Diffusion Policy. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=3)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Als mögliche Erklärung nennen sie eine Präferenz zeitlicher Faltungen für niedrige Frequenzen. Das ist eine modellbezogene Hypothese zu beobachtetem Verhalten, kein nachgewiesener Mechanismus für jeden UNet-Fehlschlag.
- **Mögliche Verwendung (B):** Diskussion: Architekturabhängigkeit und Grenze kausaler Erklärungen.
- **Claim-ID:** [DP-03](../CLAIMS.md#dp-03); Evidenzklasse L.

### DP-04 — PDF S. 5

- **Abschnitt:** §IV-D; Gl. (6)–(8). [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der Normalisierer Z(o,θ) hängt nicht von der Aktion ab und verschwindet bei der Ableitung nach a. Die Autoren nutzen dies zur Erklärung stabileren Trainings gegenüber IBC. Die Aussage betrifft Optimierung, nicht eine garantierte stabilisierte Roboterdynamik.
- **Mögliche Verwendung (B):** Methoden/Diskussion: Trainingsstabilität von Regelungsstabilität unterscheiden.
- **Claim-ID:** [DP-04](../CLAIMS.md#dp-04); Evidenzklasse M.

### DP-05 — PDF S. 6

- **Abschnitt:** §V; Tabelle I, State Policy. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die erste Zahl ist die Performance des besten Checkpoints, die zweite der Durchschnitt der letzten zehn Checkpoints; die Angaben sind über drei Trainingsseeds und fünfzig Starts je Seed gemittelt. Die Task-/Checkpointdefinition gehört zwingend zur Zahl.
- **Mögliche Verwendung (B):** Evaluation: konkreter State-Benchmark statt allgemeiner Überlegenheit.
- **Claim-ID:** [DP-05](../CLAIMS.md#dp-05); Evidenzklasse E.

### DP-06 — PDF S. 15

- **Abschnitt:** Appendix G; Performance Improvement Calculation. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=15)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Pro Tabellenspalte wird die beste Baseline mit der besten Diffusionvariante verglichen; MH wird ausgelassen. Die relativen Quotienten werden anschließend gemittelt. Das ist weder +46,9 Prozentpunkte noch eine einzelne lokale Taskrate.
- **Mögliche Verwendung (B):** Evaluation: Nenner, Variantenwahl und Aggregation der Gesamtzahl.
- **Claim-ID:** [DP-06](../CLAIMS.md#dp-06); Evidenzklasse M.

### DP-07 — PDF S. 7

- **Abschnitt:** §V-C; Tradeoff in action horizon, Abb. 6. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=7)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Mehr als eine ausgeführte Aktion hilft der Konsistenz, zu lange offene Ausführung verschlechtert die Reaktion. Acht Schritte sind in den meisten untersuchten Tasks günstig. Das ist keine allgemeine optimale Wahl für jede Frequenz und jede Datenquelle.
- **Mögliche Verwendung (B):** Diskussion: Replanning und Feedbackintervall.
- **Claim-ID:** [DP-07](../CLAIMS.md#dp-07); Evidenzklasse E.

### DP-08 — PDF S. 8

- **Abschnitt:** §VI-A; Robustness against perturbation. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Autoren zeigen Reaktionen auf Kameraokklusion und verschobene Blöcke. Sie formulieren dies als Hinweis auf neu kombinierbares Verhalten; daraus folgt keine Erfolgsrate über eine standardisierte Störungsverteilung.
- **Mögliche Verwendung (B):** Evaluation: qualitative Recovery von Robustheitsstatistik trennen.
- **Claim-ID:** [DP-08](../CLAIMS.md#dp-08); Evidenzklasse Q.

### DP-09 — PDF S. 14

- **Abschnitt:** Appendix A; Normalization. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=14)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Aktionsdimensionen werden überwiegend mit ihren Minima und Maxima auf [−1,1] skaliert, weil DDPM-Vorhersagen geclippt werden. Nahezu konstante und Rotationsdimensionen erhalten besondere Behandlung. Dies ist eine Aktionsregel, kein Beleg für beliebige Observation-Normalisierung.
- **Mögliche Verwendung (B):** Reproduzierbarkeit: Skalierung und Aktionssupport.
- **Claim-ID:** [DP-09](../CLAIMS.md#dp-09); Evidenzklasse M.

### DP-10 — PDF S. 11

- **Abschnitt:** §VIII; Limitations and Future Work. [Fundstelle](https://www.roboticsproceedings.org/rss19/p026.pdf#page=11)
- **Kurzes Originalzitat:** “higher computational costs”
- **Genaue Paraphrase (A):** Unzureichende Demos begrenzen die Performance; iterative Generierung kostet Rechenzeit und Latenz. Aktionssequenzen mildern den Aufwand nur teilweise, besonders bei hoher erforderlicher Regelungsrate. Die Autoren behaupten keine allgemeine Aufhebung von Covariate Shift.
- **Mögliche Verwendung (B):** Limitationen: Datenabhängigkeit und Rechenaufwand.
- **Claim-ID:** [DP-10](../CLAIMS.md#dp-10); Evidenzklasse L.
