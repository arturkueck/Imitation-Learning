# DART

## 1. Vollständige bibliographische Angaben

Michael Laskey, Jonathan Lee, Roy Fox, Anca Dragan, Ken Goldberg (2017). *DART: Noise Injection for Robust Imitation Learning.* CoRL 2017, PMLR 78, S. 143–156. Herausgeber Sergey Levine, Vincent Vanhoucke, Ken Goldberg; PMLR; Mountain View, USA, 13.–15. November 2017. Kein DOI in der offiziellen Referenz. [Proceedings](https://proceedings.mlr.press/v78/laskey17a.html), [vollständige Bibliographie/BibTeX](../BIBLIOGRAPHY.md#dart--laskey2017dart).

## 2. Publikationsstatus und geprüfte Fassung

**Peer-reviewed CoRL-Originalpublikation**, [eingefrorenes PDF](../_research/dart.pdf), 14 Seiten einschließlich Appendix. Methoden, Experimente, theoretische Diskussion und Supplement gelesen. Die PDF-Seiten tragen lokale Nummern 1–14; bibliographischer Umfang ist 143–156.

## 3. Forschungsproblem — A

Reines BC wird auf Supervisorausführung trainiert, während spätere Policyfehler andere Zustände erzeugen. Interaktive Learner-Rollouts können diesen Shift adressieren, verlangen aber vom Supervisor Korrekturen an schlechten Zuständen und verursachen zusätzlichen Erhebungs-/Trainingsaufwand. DART untersucht einen Datenerhebungsweg, der näher an der Expertpolicy bleibt. S. 1–4, [DART-01–02](../CLAIMS.md#dart-01).

## 4. Zentrale Hypothese / Motivation — A

Kleine, an typische Policyfehler angepasste Störungen der Expertenausführung sollen genau jene Zustände erzeugen, in denen der Expert Korrekturen zeigen muss. Die Erhebung soll dabei weniger stark von erfolgreichen Expertentrajektorien abweichen als frühe Learner-Ausführung. Richtung und Stärke des Rauschens sollen angepasst statt beliebig gewählt werden. S. 2, §1.

## 5. Methode — A

DART bedeutet *Disturbances for Augmenting Robot Trajectories*. Es fügt während der Demonstration Rauschen zu **ausgeführten Expert-Aktionen** hinzu. Der Expert beobachtet den so erreichten Zustand und liefert die nächste beabsichtigte Aktion; diese ungestörte Aktion ist die Supervision. Nach ersten Demos wird eine temporäre Policy trainiert, ihre Aktionsabweichung vom Experten geschätzt, die Noiseverteilung angepasst und die nächste Erhebungsrunde durchgeführt. Die finale BC-Policy trainiert auf aggregierten Demos. S. 4–6, Gl. (2)–(4), Algorithmus 1.

Die Kovarianz wird im Lokomotions-Supplement auf zurückgehaltenen Demos früherer Runden geschätzt (S. 13). **B:** Dieser Erhebungs-/Optimierungsablauf ist nicht identisch mit Gaussian Noise auf einem bereits bestehenden State-Datensatz.

## 6. Relevante Gleichungen — A

Notation: `ξ` = Trajektorie; `J(θ,θ*|ξ)` = Summe der Aktionssurrogatverluste; `ψ` = Noiseparameter. Die Policyparameter beeinflussen sowohl den Verlust als auch die Trajektorienverteilung.

**Eigentliches IL-Ziel**, S. 4, Gl. (1), und gestörtes BC-Ziel, Gl. (2):

\[
\min_\theta\mathbb E_{\xi\sim p(\cdot|\pi_\theta)}J(\theta,\theta^*|\xi),
\qquad
\theta_R=\arg\min_\theta\mathbb E_{\xi\sim p(\cdot|\pi_{\theta^*},\psi)}J(\theta,\theta^*|\xi).
\]

**Shift-Bound**, S. 5, Lemma 4.1; Beweis S. 10–11:

\[
|\mathbb E_{p(\cdot|\pi_{\theta^*},\psi)}J-\mathbb E_{p(\cdot|\pi_{\theta_R})}J|
\le T\sqrt{\tfrac12D_{KL}(p(\cdot|\pi_{\theta_R})\Vert p(\cdot|\pi_{\theta^*},\psi))}.
\]

Punktweiser Aktionsloss muss in `[0,1]` liegen; rohe beliebige MSE ist damit nicht automatisch abgedeckt. Der Bound motiviert KL-Anpassung, liefert keinen direkt berechenbaren Stack-Success-Bound.

**Noiseanpassung**, S. 5, Gl. (3):

\[
\hat\psi_{k+1}=\arg\min_\psi
\mathbb E_{\xi\sim p(\cdot|\pi_{\theta^*},\psi_k)}
\left[-\sum_{t=0}^{T-1}\log\pi_{\theta^*}(\pi_{\hat\theta}(x_t)|x_t,\psi)\right].
\]

**Gaußlösung**, S. 5; Herleitung S. 12–13, mit `δ_t = π_θ̂(x_t)−π_θ*(x_t)`:

\[
\hat\Sigma_{k+1}=\frac1T\mathbb E\sum_t\delta_t\delta_t^\top,
\qquad
\Sigma_{k+1}^{\alpha}=\frac{\alpha}{T\,\operatorname{tr}(\hat\Sigma_{k+1})}\hat\Sigma_{k+1}.
\]

`α` bezeichnet den vermuteten **kumulativen** Fehler der finalen Policy. Für Gaußrauschen und quadratischen Aktionsloss ist der erwartete Gesamtabstand `T tr(Σ)`. Die Formel benötigt nichtverschwindende Spur; Umgang mit degenerierter Schätzung ist für eine konkrete Implementation zu prüfen.

Proposition 4.1 (S. 6) vergleicht den Support gestörter versus deterministischer Expertentrajektorien; der Appendix (S. 11) argumentiert mit unendlichem versus endlichem KL. **B:** Dies ist ein bedingtes Support-Argument, kein Nachweis, dass jede Gaußstörung die endliche Taskleistung verbessert. Bei singulärer Kovarianz oder veränderten menschlichen Reaktionen sind zusätzliche Voraussetzungen zu prüfen.

## 7. Verwendete Daten / Tasks — A

MuJoCo Walker, Hopper, Half-Cheetah, Humanoid; Supervisor ist der deterministische Mittelwert einer TRPO-Policy, zwei Hidden Layers à 64. Die BC-Learner verwenden dieselbe Netzstruktur. Pro Demo werden 50 State-/Action-Paare subsampelt. Walker/Hopper/Half-Cheetah: 20 Erhebungsiterationen; Humanoid: 200. S. 6–7 und 13.

Realer Toyota HSR: Ziel-Mustard-Bottle hinter Haushaltsgegenständen freilegen/greifen. Vier Supervisors; zehn gemeinsame BC-Demos und dreißig zusätzliche Demos je Bedingung, final vierzig. Bedingungen BC, DART-3 und DART-6 werden innerhalb der Personen verglichen. S. 8, §5.2. Kamerabeschreibungen sind im Text uneinheitlich; siehe Gap DART-G2.

## 8. Baselines — A

MuJoCo: BC, DAgger mit vollem Neutraining nach jeder Demo, DAgger-B mit seltenerem Training, isotropes Gaußrauschen, DART. Zusatzversuch: zufällige Wishart-Kovarianzen bei verschiedener Spur. HSR: BC, DART-3 und DART-6; keine HSR-DAgger-Comparison in diesem Versuch. S. 7–8, 13–14. Die Rechenvorteile hängen daher auch am konkret verwendeten Updateplan.

## 9. Evaluationsmetriken — A

MuJoCo: kumulativer Reward über 500 Ausführungsschritte, Rechenzeit in Sekunden, Reward **während der Datenerhebung**, zusätzliche Loss-Differenz zwischen Supervisor- und Learner-Verteilungen. HSR: success, wenn Ziel erkannt und Greifpfad frei; anschließend Open-Loop-Greifen mit menschlich ausgelöstem Plan. Der Supervisor ist gegenüber der Policybedingung verblindet. Je Policy zwanzig Tests mit verschiedenen Starts. S. 7–8, 13–14. Die Ausgangsdefinition ist keine Stabilitäts-/Release-Prüfung für Stack.

## 10. Zentrale Ergebnisse — A

Im betrachteten Lokomotionsprotokoll erreicht DART ähnliche Performance wie DAgger; im Humanoid-Versuch ungefähr dreifach schnellere Rechnung und nur etwa 5 % Erhebungsrewardverlust gegenüber dem Supervisor; DAgger verliert dort über 80 %. Absolute Rewards werden hier nicht aus Abb. 2 interpoliert. S. 7.

HSR: DART-3 79 %, BC 49 %, DART-6 72 % (S. 8). **B, Rechenabgrenzung:** 79−49 = 30 Prozentpunkte. Die Autorenbezeichnung rund 62 % ist relative Verbesserung; aus den gerundeten Zahlen ergibt sich rund 61,2 %, nicht ein genauer Rohdatenwert. Keine eigenen Testzahlen rekonstruiert.

Zufällige, geeignet skalierte Kovarianzen können in den Appendix-Versuchen DART-Leistung erreichen (S. 13–14). Optimierte Kovarianzrichtung ist damit keine universell belegte Notwendigkeit. Das Störungsniveau bleibt entscheidend.

## 11. Von Autoren genannte Limitationen — A

Die ideale Noiseoptimierung benötigt die erst nach Datenerhebung bekannte finale Policyverteilung (S. 5). Die iterative Näherung kann langsam konvergieren. Die Theorie setzt voraus, dass der Supervisor durch Noise nicht grundsätzlich verändert wird; bei Menschen kann diese Annahme scheitern (S. 6). Perfekte Imitation mit ausreichenden Daten würde durch Noise keinen Zusatznutzen erhalten. DART-6 kann für Menschen zu stark stören (S. 8, ausdrücklich Hypothese). Die richtige Spur zufälliger Kovarianzen ist vorab meist unbekannt (S. 13).

## 12. Wichtige Annahmen — A und B getrennt

**A:** Markovsche stochastische Dynamik; bekannte State-/Action-Räume; Rolloutzugriff; kompetenter Supervisor, dessen Aktionen auch unter gestörter Ausführung aufgezeichnet werden können; begrenzter Loss für den KL-Bound; geeignete parametrisierte Störungsverteilung. Kein Reward während IL-Training erforderlich, obwohl Reward für die Lokomotionsevaluation verwendet wird. S. 3–6.

**B:** Eine praktizierte Störung muss dem Expert noch eine sinnvoll lösbare Korrektursituation lassen. Noise auf Gripperdiskretisierung oder Kontaktzuständen ist nicht durch die Lokomotionskovarianz validiert. Der programmierte Expert kann ebenso ungeeignete Korrekturen liefern wie ein überforderter Mensch.

## 13. Übertragbarkeit auf unser State-Stack-Problem — B/C

**B:** Das Konzept echter Korrekturlabels macht die Grenze der ausschließlich erfolgreichen nominalen Demos verständlich. Aktionsraumskalierung und tatsächlicher Erhebungspfad sind wesentliche Vergleichsmerkmale. Dies stützt die Diskussion der Datenabdeckung, ohne neue Versuche vorzuschlagen.

**C:** Die 200 erfolgreichen programmierten Stack-Demos sind keine unter DART gesammelten Trajektorien. Der Expert enthält Phasen-/Zielgedächtnis; seine Reaktion unter Störungen ist nicht durch den nominalen Datensatz validiert. Die vorhandenen Phasen- und Release-Diagnosen beschreiben spätere Fehler, liefern aber keine zusätzlichen Expert-Korrekturlabels.

## 14. Nicht übertragbare Punkte — B/C

Die +30 Prozentpunkte im HSR-Protokoll und die dreifache Humanoid-Rechenersparnis sind keine Erwartung für Stack. Keine Gleichsetzung von DART mit nachträglicher Observation-Noise, State-Translation oder Balancierung nominaler Fenster. Im HSR verbleibt eine menschliche Entscheidung im Erfolg-/Greifpfad; unsere stabile Stack-Bedingung prüft Kontakt, Freigabe und 40 zusätzliche Frames. Die Gaussian-Noise-Theorie ist keine allgemeine Sicherheitsgarantie für Kontaktmanipulation.

## Belegstellen mit Claim-IDs

Zehn relevante Stellen aus **CoRL 2017, Original-Proceedings**. Jede Seite ist eine konkrete PDF-Seite der archivierten Fassung. Originalzitate sind bewusst auf einen kurzen Auszug pro Paper begrenzt; „—“ bedeutet, dass hier kein Originalzitat gespeichert wird. Paraphrasen sind A; Verwendungen sind B. Der Projektbezug C steht in Abschnitt 13–14.

### DART-01 — PDF S. 4

- **Abschnitt:** §3; Zerlegung Shift/Loss. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Zur BC-Testabweichung wird der Verlust unter Expertentrajektorien addiert und subtrahiert. Der verbleibende Unterschied der Erwartungen beschreibt den Shift-Anteil. DART zielt auf diesen Teil, nicht ausschließlich auf kleineren Trainingsloss.
- **Mögliche Verwendung (B):** Grundlagen: Offline-Loss und Closed-Loop-Verhalten.
- **Claim-ID:** [DART-01](../CLAIMS.md#dart-01); Evidenzklasse M.

### DART-02 — PDF S. 4

- **Abschnitt:** §4; Gl. (2). [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Supervisorausführung erhält Rauschen; dadurch muss der Expert tatsächlich korrigieren. Supervision ist weiterhin die ungestörte Expertenaktion am erreichten Zustand. Das Verfahren erweitert reale Trajektorien und ist keine nachträgliche Eingabeaugmentation mit unveränderten Labels.
- **Mögliche Verwendung (B):** Methoden: genaue Stelle der Störung und Herkunft der Korrekturlabels.
- **Claim-ID:** [DART-02](../CLAIMS.md#dart-02); Evidenzklasse M.

### DART-03 — PDF S. 5

- **Abschnitt:** §4; Lemma 4.1. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der KL-Term vergleicht die Trajektorienverteilung der Lernpolicy mit der des gestörten Supervisors. Der Bound motiviert Verteilungsanpassung, misst aber nicht unmittelbar die Erfolgsrate eines Tasks.
- **Mögliche Verwendung (B):** Theorie: Rolle des KL-Bounds und beschränkten Loss.
- **Claim-ID:** [DART-03](../CLAIMS.md#dart-03); Evidenzklasse T.

### DART-04 — PDF S. 5

- **Abschnitt:** §4.1; Gl. (3)–(4) und Gauß-Lösung. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die äußeren Produkte von Policy-minus-Expert-Aktionsfehlern ergeben eine Kovarianzschätzung unter gestörter Supervisorausführung. Für Gaußrauschen wird sie mit α/(T tr(Σ̂)) multipliziert. Die Kovarianzrichtung und die Gesamtstärke sind getrennte Entscheidungen.
- **Mögliche Verwendung (B):** Methoden: adaptive Störungsverteilung statt beliebiger Noise-Stärke.
- **Claim-ID:** [DART-04](../CLAIMS.md#dart-04); Evidenzklasse M.

### DART-05 — PDF S. 6

- **Abschnitt:** §4.2; Proposition 4.1 und Diskussion. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Gaußrauschen erweitert den Aktionssupport gegenüber dem deterministischen Expert bei nichtverschwindendem Policyfehler. Die Autoren schränken ausdrücklich ein, dass menschliche Supervisors ihr Verhalten durch Rauschen ändern können; perfekte Expert-Repräsentation bietet keinen erwarteten Zusatznutzen.
- **Mögliche Verwendung (B):** Theorie/Limitationen: Support-Argument und menschlicher Supervisor.
- **Claim-ID:** [DART-05](../CLAIMS.md#dart-05); Evidenzklasse T.

### DART-06 — PDF S. 7

- **Abschnitt:** §5.1; Abb. 2 und Ergebnisabsatz. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=7)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Berichtet werden Walker, Hopper, Half-Cheetah und Humanoid. Im Humanoid-Beispiel ist DART ungefähr dreimal schneller; der Erhebungsreward liegt etwa 5 % unter dem Supervisor, bei DAgger über 80 % darunter. Dies gilt für die untersuchten Updatepläne und Hardware.
- **Mögliche Verwendung (B):** Verwandte Arbeiten: Aufwand und Qualität der Datenerhebung getrennt berichten.
- **Claim-ID:** [DART-06](../CLAIMS.md#dart-06); Evidenzklasse E.

### DART-07 — PDF S. 8

- **Abschnitt:** §5.2; Ergebnisabsatz und Abb. 3. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Vier Supervisors liefern je eine BC-Basis von zehn Demos und je dreißig weitere Demos pro Bedingung; die finale Policy nutzt vierzig. 79 gegenüber 49 sind 30 Prozentpunkte. Die berichtete ungefähr 62%ige Verbesserung ist relativ, keine Zunahme um 62 Prozentpunkte.
- **Mögliche Verwendung (B):** Evaluation: absolute und relative Effekte unterscheiden.
- **Claim-ID:** [DART-07](../CLAIMS.md#dart-07); Evidenzklasse E.

### DART-08 — PDF S. 14

- **Abschnitt:** Appendix §4.5; Robot Setup. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=14)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Ein gegenüber der getesteten Policy verblindeter Supervisor bestätigt die Ziel-/Pfadsituation und löst einen Plan zur festen Zielposition aus. Pro Policy werden zwanzig unterschiedlich initialisierte Tests genannt. Das ist kein vollständig autonomer Closed-Loop-Stack-Erfolgstest.
- **Mögliche Verwendung (B):** Evaluation: Erfolgskriterium und verbleibende menschliche Hilfe.
- **Claim-ID:** [DART-08](../CLAIMS.md#dart-08); Evidenzklasse M.

### DART-09 — PDF S. 8

- **Abschnitt:** §5.2; letzter Ergebnisabsatz. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=8)
- **Kurzes Originalzitat:** “potentially too high”
- **Genaue Paraphrase (A):** DART-6 liegt unter DART-3, aber über BC. Die Erklärung durch übermäßiges Rauschen wird als mögliche Deutung formuliert; der Versuch isoliert keine universelle optimale Rauschstärke.
- **Mögliche Verwendung (B):** Diskussion: beobachteter Effekt versus erklärende Hypothese.
- **Claim-ID:** [DART-09](../CLAIMS.md#dart-09); Evidenzklasse H.

### DART-10 — PDF S. 13

- **Abschnitt:** Appendix §4.4; Random Covariance Matrices. [Fundstelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf#page=13)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Autoren variieren die Spur von Wishart-gezogenen Kovarianzen. Angemessener simulierter Fehler reduziert Shift auch ohne DART-Kovarianzrichtung; sehr hohe oder niedrige Stärken verschlechtern den Loss. Die richtige Stärke ist vorab nicht allgemein bekannt.
- **Mögliche Verwendung (B):** Diskussion: keine universelle Überlegenheit optimierter Kovarianz behaupten.
- **Claim-ID:** [DART-10](../CLAIMS.md#dart-10); Evidenzklasse E.
