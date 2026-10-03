# DAgger

## 1. Vollständige bibliographische Angaben

Stéphane Ross, Geoffrey J. Gordon, J. Andrew Bagnell (2011). *A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning.* AISTATS 2011, PMLR 15, S. 627–635. Herausgeber Geoffrey Gordon, David Dunson, Miroslav Dudík; PMLR; Fort Lauderdale, USA, 11.–13. April 2011. Kein DOI in der offiziellen Referenz. [Proceedings](https://proceedings.mlr.press/v15/ross11a.html). Vollständiger Datensatz/BibTeX: [Bibliographie](../BIBLIOGRAPHY.md#dagger--ross2011dagger).

## 2. Publikationsstatus und geprüfte Fassung

**Peer-reviewed AISTATS-Originalpublikation**, [eingefrorenes PDF](../_research/dagger.pdf), 9 Seiten. Gelesen: Haupttext einschließlich Theorie, finite-sample Analysis und Experimente S. 1–8. Fundstellen verwenden PDF-Seiten, nicht eine erfundene sichtbare Proceedings-Paginierung.

## 3. Forschungsproblem — A

Aktionen beeinflussen zukünftige Eingaben. Der Imitationsfehler auf Expertentrajektorien ist deshalb nicht automatisch der Fehler auf den von der Lernpolicy besuchten Zuständen. Die Autoren suchen eine stationäre deterministische Policy mit guter Leistung unter ihrer eigenen induzierten Zustandsverteilung. Der Anwendungsbereich umfasst Imitation Learning und strukturierte Vorhersage. [DAG-01–03](../CLAIMS.md#dag-01).

## 4. Zentrale Hypothese / Motivation — A

Wenn Trainingsdaten wiederholt die Zustände enthalten, die frühere Lernpolicies tatsächlich erzeugen, lässt sich ein Kandidat lernen, der auch unter seiner eigenen Verteilung wenig Imitationsfehler macht. Die Verbindung zu No-Regret-Online-Learning soll diese Intuition formal absichern. Im Gegensatz zu einer bloß größeren Expertensammlung verändert DAgger die Herkunft der Trainingszustände. S. 3–5, §3–4.

## 5. Methode — A

1. Policy initialisieren; in der üblichen ersten Runde den Experten ausführen.
2. Eine Erhebungspolicy `π_i = β_iπ* + (1−β_i)π̂_i` ausführen. Die Mischung ist optional.
3. An **allen erfassten Zuständen** Expertaktionen `π*(s)` als Labels erhalten.
4. `D_i` mit dem bisherigen Datensatz vereinigen und auf der Gesamtheit trainieren.
5. Wiederholen; Algorithmus 3.1 gibt den besten Kandidaten gemäß Validation zurück.

Die Auswahl eines Expertbefehls zur tatsächlichen Ausführung und die Anfrage eines Expertlabels sind verschiedene Operationen. Expertmischung kann frühe, besonders schlechte Lernpolicyzustände vermeiden; die Datenaggregation bleibt zentral. `β_1=1`, danach `β_i=0` ist eine beschriebene einfache Variante. S. 4, [DAG-05–07](../CLAIMS.md#dag-05).

## 6. Relevante Gleichungen — A, mit Geltungsbedingungen

Notation: `T` = endlicher Horizont; `d_π = (1/T) Σ_t d_π^t`; `J(π)` = kumulative Taskkosten; `ℓ` = Imitationssurrogat. Nicht jedes `ℓ` ist automatisch eine Taskkostenmetrik.

**Ziel und BC-Ziel**, S. 2, Gl. (1)–(2):

\[
\hat\pi=\arg\min_{\pi\in\Pi}\mathbb E_{s\sim d_\pi}[\ell(s,\pi)],\qquad
\hat\pi_{sup}=\arg\min_{\pi\in\Pi}\mathbb E_{s\sim d_{\pi^*}}[\ell(s,\pi)].
\]

**Worst-Case-BC-Bound**, S. 2, Theorem 2.1:

\[
J(\pi)\le J(\pi^*)+T^2\epsilon.
\]

Vorausgesetzt sind Taskkosten in `[0,1]` und ein Surrogat, das den 0–1-Imitationsfehler begrenzt. `ε` wird unter `d_π*` gemessen. Das DAgger-Paper schreibt diesen BC-Satz ausdrücklich Ross und Bagnell (2010) zu; er wird hier als darin wiedergegebene Grundlage, nicht als neue Entdeckung von 2011 geführt. **B:** Ein kontinuierlicher Aktions-MSE darf ohne zusätzliche Ableitung nicht anstelle dieses `ε` eingesetzt werden.

**Bound unter eigener Verteilung**, S. 3, Theorem 2.2:

\[
\mathbb E_{s\sim d_\pi}\ell(s,\pi)=\epsilon
\quad\Longrightarrow\quad
J(\pi)\le J(\pi^*)+uT\epsilon.
\]

`u` begrenzt den zusätzlichen Cost-to-go einer Abweichung mit anschließender Expertfortsetzung. Die Autoren sagen ausdrücklich, dass `u` selbst im Worst Case `O(T)` sein kann. Die Formel allein ist deshalb keine uneingeschränkte lineare Taskfehlergarantie.

**No-Regret-Bedingung**, S. 5, Gl. (3):

\[
\frac1N\sum_{i=1}^N\ell_i(\pi_i)
-\min_{\pi\in\Pi}\frac1N\sum_{i=1}^N\ell_i(\pi)
\le\gamma_N,\qquad \gamma_N\to0.
\]

**DAgger-Ergebnis**, S. 4, Theorem 3.1: im unendlichen Stichprobenfall, bei stark konvexem beschränktem Loss, entsprechend abnehmender Expertmischung und `N` der Ordnung `T` bis auf logarithmische Faktoren **existiert** ein Kandidat mit `E_{d_π̂} ℓ ≤ ε_N + O(1/T)`. Theorem 3.2 ergänzt die Kostenreduktion mit `u`. Finite Daten benötigen zusätzlich den Stichprobenfehler, S. 4–6, Theoreme 3.3–3.4/4.2. Kein gleichwertiger Satz für das lokale MLP-Training nachgewiesen.

## 7. Verwendete Daten / Tasks — A

| Task | Daten und Eingaben | Lernkomponente |
|---|---|---|
| SuperTuxKart / Star Track | Bilder, menschliche Lenkwinkel; etwa 1000 Datenpunkte pro Trainingsrunde, 20 Runden; 5 Hz | Linearer Regressor auf LAB-Bildmerkmalen |
| Super Mario Bros. | Zufällige Level Schwierigkeit 1, near-optimaler Planner mit vollem Simulatorzustand; 5000 Punkte pro Runde, 20 Runden | Vier binäre SVMs; Bildhistorie, Aktionshistorie und Mariozustand |
| OCR / Taskar-Datensatz | Etwa 6600 Wörter, mehr als 52000 Zeichen; 10-Fold-Teilung, neun Folds Training, einer Test | Greedy links-nach-rechts, SVM mit vorangegangenem Label |

S. 6–8, §5. Eine zustandsabhängige Policy in der Theorie verbietet keine Historienmerkmale in der praktischen Eingabe; die Mario-Eingaben enthalten tatsächlich Historie.

## 8. Baselines — A

SuperTuxKart: rein überwachte Expertentrajektorien und SMILe. Mario: überwachte Baseline, SMILe, SEARN; verschiedene Expertmischungen für DAgger und Mischparameter für SEARN. OCR: unabhängige Zeichenklassifikation, überwachtes Training mit korrektem Vorgängerlabel, SMILe und SEARN. Es werden lineare Modelle verglichen, keine modernen Robomimic-Policies. S. 6–8, §5.

## 9. Evaluationsmetriken — A

Star Track: mittlere Stürze pro Runde und Konfidenzintervalle in Abb. 2. Mario: mittlere zurückgelegte Distanz pro Level vor Tod/Timeout/Abschluss, rund 4200–4300 maximal typische Distanz; 60 Sekunden Limit. OCR: Zeichenaccuracy auf Testfolds. Trainingsdatenmenge und Iteration werden in Lernkurven getrennt abgebildet. S. 6–8.

## 10. Zentrale Ergebnisse — A

Die Autoren berichten eine Star-Track-Policy ohne Sturz nach 15 DAgger-Iterationen; die reine Expertensammlung stagniert. Bei Mario erzielt die Mischung `β_i=0.5^(i−1)` eine berichtete Distanz von 3030 gegenüber 2980 für Expert nur in Runde 1; langsamer abnehmende Mischung konvergiert langsamer. Bei OCR erreichen unabhängige SVMs 82 %, supervised mit korrektem Vorgänger 83,6 %, DAgger 85,5 % Zeichenaccuracy. S. 6–8, §5. Diese Zahlen werden nicht in erwartete Stack-Erfolge umgerechnet.

## 11. Von Autoren genannte Limitationen — A

Kein eigener Limitationsabschnitt. Explizite Einschränkungen stehen in Theorie und Experimentdiskussion: stärkere Lernannahme als reine Klassifikationsreduktion (S. 5); `u` kann `O(T)` sein (S. 3); zu langsam abnehmende Expertmischung kann nach 20 Mario-Runden noch nicht konvergiert sein (S. 7). Greedy One-Pass-OCR wird bewusst als einfache Demonstration gewählt, anspruchsvollere Decodingverfahren bleiben Future Work (S. 8). Risiken menschlicher Annotation sind hier keine eigene systematische Human-Robotics-Studie.

## 12. Wichtige Annahmen — A und B getrennt

**A:** Zugriff auf Systemrollouts und Expertlabels auf besuchten Zuständen; begrenzter Loss und geeignete Reduktionsannahmen für die Sätze; No-Regret-Basisverfahren; genug Iterationen/Stichproben; geeignete Expertmischung. Taskkostenreduktion benötigt zusätzlich die Beziehung zwischen Imitationssurrogat und Taskkosten.

**B:** In neuronalen Manipulationssystemen sind Expertenkompetenz an Fehlzuständen, ausreichende Informationen in der Policyeingabe und die Behandlung unlösbarer Zustände Voraussetzungen einer sinnvollen Übertragung. Das Paper beweist nicht, dass beliebige Deep-BC-Optimierung No-Regret ist.

## 13. Übertragbarkeit auf unser State-Stack-Problem — B/C

**B:** Die Unterscheidung `d_π*`/`d_π` erklärt, weshalb ein niedriger Offline-Loss auf erfolgreichen Demos Recovery nicht belegt. Sie ist auf kontinuierliche Manipulation als Problemstruktur übertragbar. Die konkrete Theorie erlaubt ohne weitere Ableitung keine Aussage über lokale MSE oder stabile Stackrate.

**C, Codebefund:** `StackExpert` speichert Phase, Phasendauer und Ziel. Ein fremder Rolloutzustand liefert durch Neuinitialisierung des Experts kein geprüftes Korrekturlabel. Das Projekt hat zwei Beobachtungsframes und 16 Aktionspositionen pro Chunk. Ein einzelnes DAgger-Aktionslabel ist noch kein korrektes Expertchunk für folgende, eventuell anders verlaufende Zustände. [Projektbezug](../comparisons/relation_to_our_results.md#c-projektbefunde).

## 14. Nicht übertragbare Punkte — B/C

Keine Übernahme der Spiel-/OCR-Zahlen, der linearen Lernergarantie oder der Behauptung eines sicheren Erhebungsprozesses. Die vorhandenen 200 Demos bilden keine abgeschlossene DAgger-Erhebung. Der Replikationsvergleich Direct/Diffusion enthält keine Expert-Nachannotation und ist daher keine DAgger-Evaluation. Die bisherige Abweichung vom Expert-Timing beweist weder das Vorliegen noch die kausale Wirkung von Covariate Shift.

## Belegstellen mit Claim-IDs

Zehn relevante Stellen aus **AISTATS 2011, Original-Proceedings**. Jede Seite ist eine konkrete PDF-Seite der archivierten Fassung. Originalzitate sind bewusst auf einen kurzen Auszug pro Paper begrenzt; „—“ bedeutet, dass hier kein Originalzitat gespeichert wird. Paraphrasen sind A; Verwendungen sind B. Der Projektbezug C steht in Abschnitt 13–14.

### DAG-01 — PDF S. 2

- **Abschnitt:** §2.1; Gl. (2). [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Das überwachte Lernziel gewichtet Zustände, die der Expert besucht. Die durch die gelernte Policy selbst erzeugte Zustandsverteilung steht nicht im BC-Ziel.
- **Mögliche Verwendung (B):** Grundlagen: BC-Lernziel und Unterschied zwischen Training und Ausführung.
- **Claim-ID:** [DAG-01](../CLAIMS.md#dag-01); Evidenzklasse M.

### DAG-02 — PDF S. 2

- **Abschnitt:** §2; Gl. (1). [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Policy beeinflusst durch ihre Aktionen die späteren Eingaben. Deshalb hängen Verlust und Zustandsverteilung gemeinsam von der Policy ab; auch bei konvexem punktweisem Loss ist das Gesamtziel nicht notwendig konvex.
- **Mögliche Verwendung (B):** Problemstellung: policyabhängige Zustandsverteilung.
- **Claim-ID:** [DAG-02](../CLAIMS.md#dag-02); Evidenzklasse M.

### DAG-03 — PDF S. 2

- **Abschnitt:** §2.1; Theorem 2.1. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=2)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der Bound verwendet ε unter Expertenzuständen und Kosten in [0,1]. Die Autoren nennen ihn tight: geeignete Probleme können quadratischen zusätzlichen Aufwand zeigen. Er ist keine Vorhersage jeder empirischen Lernkurve.
- **Mögliche Verwendung (B):** Theorie: bedingter Worst-Case-Bound; keine direkte Umrechnung von MSE.
- **Claim-ID:** [DAG-03](../CLAIMS.md#dag-03); Evidenzklasse T.

### DAG-04 — PDF S. 3

- **Abschnitt:** §2.2; Theorem 2.2. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=3)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** u begrenzt die zusätzliche Expert-Cost-to-go einer falschen Aktion. Der Taskkostenbound ist J(π) ≤ J(π*) + uTε. Die Autoren weisen darauf hin, dass u im Worst Case selbst O(T) sein kann.
- **Mögliche Verwendung (B):** Theorie: Voraussetzungen einer linear in T formulierten Aussage.
- **Claim-ID:** [DAG-04](../CLAIMS.md#dag-04); Evidenzklasse T.

### DAG-05 — PDF S. 4

- **Abschnitt:** §3; Algorithmus 3.1. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Jede Runde sammelt neue Trajektorien, annotiert deren Zustände mit Expertenaktionen, vereinigt alte und neue Daten und trainiert erneut. Der zurückgegebene Kandidat wird im Algorithmus anhand von Validation ausgewählt.
- **Mögliche Verwendung (B):** Methoden: Ablauf und Unterschied zu einem festen Offline-Datensatz.
- **Claim-ID:** [DAG-05](../CLAIMS.md#dag-05); Evidenzklasse M.

### DAG-06 — PDF S. 4

- **Abschnitt:** §3; Absatz zur Expert-Mischung. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** π_i = β_iπ* + (1−β_i)π̂_i verwendet den Experten nur für einen Anteil der ausgeführten Aktionen. Diese Mischung betrifft die Erhebung; Expert-Labels werden weiterhin für die besuchten Zustände benötigt. Der mittlere Expert-Anteil soll langfristig verschwinden.
- **Mögliche Verwendung (B):** Methoden: Ausführungspolicy und Label-Oracle getrennt erläutern.
- **Claim-ID:** [DAG-06](../CLAIMS.md#dag-06); Evidenzklasse M.

### DAG-07 — PDF S. 4

- **Abschnitt:** §3; Theoreme 3.1–3.2. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Im unendlichen Stichprobenfall und unter stark konvexem, beschränktem Loss sowie geeigneter β-Abnahme findet sich bei genügend Runden ein Kandidat mit kleinem Loss unter seiner eigenen Verteilung. Die Aussage garantiert nicht automatisch den letzten Kandidaten.
- **Mögliche Verwendung (B):** Theorie/Diskussion: Geltungsbereich der DAgger-Garantie.
- **Claim-ID:** [DAG-07](../CLAIMS.md#dag-07); Evidenzklasse T.

### DAG-08 — PDF S. 6

- **Abschnitt:** §5.1; Abb. 2 und Ergebnisabsatz. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die gemessene Größe sind mittlere Stürze pro Runde auf Star Track. Pro Trainingsiteration wird etwa eine Runde mit rund 1000 Datenpunkten erhoben; insgesamt werden 20 Iterationen betrachtet. Das Ergebnis ist kein Manipulationsbenchmark.
- **Mögliche Verwendung (B):** Verwandte Arbeiten: ursprüngliche empirische Demonstration.
- **Claim-ID:** [DAG-08](../CLAIMS.md#dag-08); Evidenzklasse E.

### DAG-09 — PDF S. 8

- **Abschnitt:** §5.3; Ergebnisabsatz. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Bei ungefähr 6600 Wörtern und über 52000 Zeichen werden neun von zehn Folds zum Training und einer zum Test genutzt. Die Accuracy betrifft Zeichen, nicht vollständige Wörter oder robotische Erfolgsraten.
- **Mögliche Verwendung (B):** Evaluation: unterschiedliche Zielmetriken kenntlich machen.
- **Claim-ID:** [DAG-09](../CLAIMS.md#dag-09); Evidenzklasse E.

### DAG-10 — PDF S. 5

- **Abschnitt:** §4.2; Absatz vor Finite Sample Case. [Fundstelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf#page=5)
- **Kurzes Originalzitat:** “a stronger (albeit common) assumption”
- **Genaue Paraphrase (A):** Die Autoren verlangen ein No-Regret-Verfahren oder einen stark konvexen Surrogatverlust und grenzen dies von allgemeineren Klassifikationsreduktionen ab. Daraus folgt keine automatische theoretische Absicherung beliebigen neuronalen Trainings.
- **Mögliche Verwendung (B):** Limitationen: Lernannahmen und Abgrenzung zum Projekt.
- **Claim-ID:** [DAG-10](../CLAIMS.md#dag-10); Evidenzklasse L.
