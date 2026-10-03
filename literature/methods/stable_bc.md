# Stable-BC

## 1. Vollständige bibliographische Angaben

Shaunak A. Mehta, Yusuf Umut Ciftci, Balamurugan Ramachandran, Somil Bansal, Dylan P. Losey (2025). *Stable-BC: Controlling Covariate Shift With Stable Behavior Cloning.* *IEEE Robotics and Automation Letters* 10(2), S. 1952–1959, Februar 2025, IEEE. DOI [10.1109/LRA.2025.3526439](https://doi.org/10.1109/LRA.2025.3526439). [Bibliographie mit verifizierten Metadaten und getrenntem Preprint-BibTeX](../BIBLIOGRAPHY.md#stable-bc--mehta2025stablebc--mehta2024stablebcpreprint).

## 2. Publikationsstatus und geprüfte Fassung

**Publikation peer-reviewed in RA-L 2025. Inhalt hier ausschließlich aus einem Preprint verifiziert:** arXiv:2408.06246v1, 12. August 2024, 8 Seiten, vollständig gelesen. [Versionierter Datensatz](https://arxiv.org/abs/2408.06246v1), [eingefrorenes PDF](../_research/stable_bc.pdf).

Das vorhandene lokale Paper ist byteidentisch mit v1. Verlags-Accepted-Manuscript nicht abrufbar (HTTP 418); Autoren-Paper-Link HTTP 404. **Übereinstimmung der Inhalte, Gleichungsnummern und Seiten mit RA-L ungeklärt.** Alle folgenden A-Aussagen beziehen sich auf v1 und tragen in CLAIMS.md `P-`. Keine Journal-Seiten aus Preprint-Seiten abgeleitet.

## 3. Forschungsproblem — A (Preprint)

Fehler zwischen einem aktuellen Systemzustand und demonstrierten Abläufen können sich aufschaukeln. Das Paper fragt, ob die lokale Dynamik dieser Abweichungen durch den Policy-Loss gestaltet werden kann, ohne die Trainingsdaten zu verändern. Robotereigener Fehler und Fehler in der Umgebung werden gekoppelt betrachtet. S. 1–3, [SBC-01–03](../CLAIMS.md#sbc-01).

## 4. Zentrale Hypothese / Motivation — A (Preprint)

BC soll robuster sein, wenn es nahe an bekannten demonstrierten Verhaltensabläufen bleibt. Die Autoren motivieren die Demos als lokale Attraktionsregion und untersuchen Bedingungen, unter denen abweichende Trajektorien sich demonstrierten Trajektorien annähern. Sie behaupten nicht, dass Stabilität allein das richtige Taskziel auswählt: BC-Imitation bleibt Teil des Losses. S. 1 und 3–4.

## 5. Methode — A (Preprint)

Roboterzustand `x` folgt bekannter Dynamik `ẋ=f(x,u)`; Umgebungszustand `y` folgt `ẏ=g(x,y,u)`. Die Policy ist `u=π_θ(x,y)`. Aus lokalen Fehlern `e_x=x′−x`, `e_y=y′−y` wird eine linearisierte Fehlerdynamik gebildet.

Modellbasiert: `f` **und** `g` sind bekannt; der Loss bestraft instabile Eigenwerte der gesamten gekoppelten Matrix `A`.

Modellfrei im Sprachgebrauch des Papers: `g` ist unbekannt, `f` bleibt bekannt. Die Autoren nehmen beschränkte Umgebungsabweichung an, stabilisieren nur den Roboterblock `A₁` und reduzieren die Kopplung `A₂` zur Umgebung. Der normale BC-Loss verhindert, dass allein ein stabiler, aber aufgabenuntauglicher Ablauf optimiert wird. S. 2–5, Algorithmus 1.

## 6. Relevante Gleichungen — A, ausdrücklich v1

**BC-Loss**, S. 2, Gl. (1):

\[
L_{BC}(\theta)=\sum_{(x,y,u)\in D}\|\pi_\theta(x,y)-u\|^2.
\]

**Linearisierte Fehlerdynamik**, S. 3, Gl. (4)–(6):

\[
\dot z=Az,\qquad z=\begin{bmatrix}e_x\\e_y\end{bmatrix},\qquad
A=\begin{bmatrix}
\nabla_xf+\nabla_uf\,\nabla_x\pi & \nabla_uf\,\nabla_y\pi\\
\nabla_xg+\nabla_ug\,\nabla_x\pi & \nabla_yg+\nabla_ug\,\nabla_y\pi
\end{bmatrix}.
\]

Ableitungen beziehen sich auf die jeweilige demonstrierte Umgebung. Für das lineare System sind strikt negative Realteile der Eigenwerte die Hurwitz-Bedingung; der Schluss für die nichtlineare Dynamik ist lokal.

**Modellbasierter Loss**, S. 4, Gl. (7):

\[
L(\theta)=\sum_{(x,y,u)\in D}
\left[\|u-\pi_\theta(x,y)\|^2+
\lambda\sum_{\sigma\in\operatorname{eig}(A)}\operatorname{ReLU}(\operatorname{Re}\sigma)\right].
\]

**Modellfreie Fehlerdynamik**, S. 4, Gl. (8), mit `A₁` und `A₂` aus der oberen Zeile von Gl. (6):

\[
\dot e_x=A_1e_x+A_2e_y,\qquad \|e_y\|\le\epsilon.
\]

**Bound**, S. 4, Gl. (9), hier in äquivalenter Spaltenvektorschreibweise:

\[
\|e_x(t)\|\le\|e^{A_1t}e_x(0)\|
+\|A_2\|\epsilon\int_0^t\|e^{A_1(t-\tau)}\|\,d\tau.
\]

**Modellfreier Loss**, S. 5, Gl. (11):

\[
L(\theta)=\sum_{(x,y,u)\in D}
\left[\|u-\pi_\theta(x,y)\|^2+\lambda_1\|A_2\|
+\lambda_2\sum_{\sigma\in\operatorname{eig}(A_1)}\operatorname{ReLU}(\operatorname{Re}\sigma)\right].
\]

**B, mathematische Prüfgrenzen, keine Autorenaussage:** Ein verschwindender ReLU-Term erlaubt auch Eigenwertrealteile **gleich null**; er erzwingt ohne Zusatzprüfung keine strikte Negativität. Hurwitz-Stabilität bedeutet außerdem nicht zwingend monotones Schrumpfen der euklidischen Norm in jedem Schritt. Ein Soft-Loss an Datenpunkten prüft keine vollständige Nachbarschaft.

**B, ungeklärte Textpunkte:** S. 4 definiert `A₁` einmal mit `∇_uπ`, während Gl. (6) den passenden Roboter-Jacobian `∇_xπ` enthält. Ob dies in RA-L korrigiert wurde, ist unbekannt. Gl. (10) verwendet `exp(‖A₁‖t)−1`: Diese angegebene Schranke wächst mit `t` und ist allein keine zeituniforme Schranke. Hier wird sie nicht zu einer globalen oder monotonen Kontraktionsgarantie umgedeutet. Siehe SBC-G2–G4.

## 7. Verwendete Daten / Tasks — A (Preprint)

| Setting | Daten und Dynamik | Evaluation |
|---|---|---|
| Interaktive Kreuzung | Zwei simulierte Experten steuern Fahrzeuge; eine Demo umfasst 20 Paare; `x,y∈R²`, `ẋ=u`, fremde Dynamik unbekannt | Nominal, geändertes Verhalten des anderen Fahrers, fremde Starts; 100 Tests pro Kurvenpunkt, SEM, Abb. 2 |
| Nichtlinearer Quadrotor | `x∈R⁶`, `u∈R³`; bekannte Dynamik, sieben fixe Hindernisse und fixes Ziel | Aktionsrauschen zur Testzeit; 10 Trainingsläufe × 100 Rollouts, Abb. 3 |
| Visueller Point Mass | 21×21-Pixel-Zielbild, Autoencoder auf 10-dimensionales Latent; Position in R² | Endabstand zum Ziel über 25 Tests, Abb. 4 |
| Reales Air Hockey | Franka 7-DoF, aber planar `x,u∈R²`; Puckhistorie `y∈R⁴`; 20 Hz; 10 Personen, je etwa 3000 Paare | 15/60/120 Sekunden je Person; 10 Policies × 10 Rollouts pro Datenmenge; gepoolte 1200 Sekunden als zusätzliche große Datenbedingung |

S. 5–8. Zahl der Demos je exaktem Punkt der Simulationskurven wurde nicht aus Plotpixeln rekonstruiert. Ein 7-DoF-Roboter bedeutet im Air-Hockey-Versuch nicht einen sieben-dimensionalen Aktionsraum.

## 8. Baselines — A (Preprint)

Kreuzung: BC, CCIL, Stable-BC, CCIL+Stable-BC. Quadrotor: BC, DART, modellbasiertes Stable-BC; BC und Stable-BC haben dieselben nominalen Demos, DART erhebt anders. Point Mass und Air Hockey: BC versus Stable-BC. S. 5–7. Ein zusätzlicher CQL-Vergleich auf der Autorenwebseite ist ausdrücklich zusätzliche Web-Evidenz und wird hier **nicht** als Experiment des gelesenen Papers übernommen.

## 9. Evaluationsmetriken — A (Preprint)

Kreuzung: kumulative Kosten aus Gl. (12); niedrig ist besser. Quadrotor: Anteil kollisionsfreier Zielerreichungen. Point Mass: Endzustandsfehler, niedrig ist besser. Air Hockey: aufeinanderfolgende Hits, gedeckelt bei 25, sowie Richtungswechsel über zehn Grad pro erfolgreichem Hit. SEM wird in Abbildungen verwendet. Air Hockey nutzt Repeated-Measures-ANOVA und Post-hoc-Tests, nicht dieselbe Replikationseinheit wie unsere Trainingsseedstudie. S. 6–8.

## 10. Zentrale Ergebnisse — A (Preprint)

In den Kreuzungstests berichten die Autoren niedrigere Kosten mit Stable-BC als mit BC/CCIL und geringe Unterschiede gegenüber CCIL+Stable-BC (S. 5–6). Im Quadrotor erreicht Stable-BC mit weniger nominalen Demos höhere Erfolgsrate als die Vergleichsbedingungen (S. 6). Im visuellen Proof of Concept ist der Endabstand geringer als bei BC (S. 7). Keine exakten Kurvenwerte erfunden.

Air Hockey: mehr Hits bei 15/60/120 Sekunden Daten, Autoren-Tests `p<0,05`; Algorithmuseffekt `F(1,9)=19,03`, Dateneffekt `F(2,18)=50,79` (S. 7). Weniger Richtungswechsel, Algorithmuseffekt `F(1,9)=59,65`, Dateneffekt `F(2,18)=9,62`; bei 1200 Sekunden `t(9)=4,681`, `p<0,05` (S. 7–8). Bei der großen gepoolten Datenmenge nähern sich die Hit-Leistungen von BC und Stable-BC an. Rohmittelwerte der Balken werden nicht als exakt ausgegeben.

## 11. Von Autoren genannte Limitationen — A (Preprint)

Kein eigener Limitationsabschnitt. Explizit genannt: lokale Linearisierung (S. 3); Stabilität allein kann Taskperformance verfehlen (S. 3–4); unbekanntes `g` verhindert allgemeine Aussage zur vollständigen Matrix (S. 4); die modellfreie Aussage ist schwächer und setzt begrenztes `e_y` voraus (S. 5). Zu kleine Umgebungskopplung ignoriert notwendige Umgebungsinformation (S. 4). Der visuelle Versuch ist ein Proof of Concept (S. 7).

## 12. Wichtige Annahmen — A und B getrennt

**A:** Beobachtbare Roboter-/Umgebungszustände, genaue Roboterdynamik `f`; für die modellbasierte Version zusätzlich `g`; lokal ableitbare Dynamik und Policy; für die modellfreie Version begrenzte Umgebungsabweichung. S. 2–5.

**B:** Die Übertragung auf hybrid schaltende Kontakte, diskrete Greiferereignisse, Gedächtniswrapper und mehrschrittige Ausführung verlangt eine neue Herleitung. Die lokale Dimension und Zustandsskala beeinflussen Jacobian und Normstrafe. Das sind Analysegrenzen, keine im Paper durchgeführten Stack-Ablationen.

## 13. Übertragbarkeit auf unser State-Stack-Problem — B/C

**B:** Die Kopplung von Roboterfehler und Objektzustand hilft, Stabilität gegenüber Aufgabenfortschritt begrifflich zu trennen. Die Quellenwarnung vor zu geringer Reaktion auf `y` passt als Diskussionsrahmen zu notwendigen Zielrichtungs- und Phasenwechseln. Das beweist keinen lokalen Mechanismus.

**C:** Unsere Direct-Policy gibt Chunks aus und führt zwei Aktionen aus einer Queue aus; die originale Analyse behandelt eine zustandsabhängige kontinuierliche Aktion. `StackTwo` hat Kontakte und Freigabe. In `contraction_bc.py` liegt eine finite-difference Lift-Erweiterung mit geschätztem 3×3-Dynamikmapping vor; sie verlangt einen zehn-dimensionalen Lift-Objektvektor. Sie ist **keine Umsetzung von Gl. (7)/(11)** und nicht unmittelbar mit dem sechs-dimensionalen Stack-Objektvektor kompatibel.

## 14. Nicht übertragbare Punkte — B/C

Keine Stable-BC-Garantie für die Lift-Erweiterung oder Direct-Stack-Policy, kein Beweis einer stabilen vollständigen Stack-Dynamik und kein erwarteter Erfolgsgewinn aus Air Hockey. Die geschätzte Lift-Ein-Schritt-Abbildung ist kein bekanntes Stack-`f`. Der große Datensatz aus zehn menschlichen Hockey-Supervisors ist keine Analogie zu 200 Demos eines programmierten StackExperts. Vor Journalabgleich werden selbst paperinterne Theoreme ausdrücklich nur als Preprint-Inhalt zitiert.

## Belegstellen mit Claim-IDs

Zehn relevante Stellen aus **Preprint arXiv:2408.06246v1, 2024; Journalinhalt nicht abgeglichen**. Jede Seite ist eine konkrete PDF-Seite der archivierten Fassung. Originalzitate sind bewusst auf einen kurzen Auszug pro Paper begrenzt; „—“ bedeutet, dass hier kein Originalzitat gespeichert wird. Paraphrasen sind A; Verwendungen sind B. Der Projektbezug C steht in Abschnitt 13–14.

### SBC-01 — PDF S. 1

- **Abschnitt:** §I; hervorgehobene Hypothese. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=1)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Autoren erwarten geringere Fehlerakkumulation, wenn Trajektorien nicht weiter aus der Datenregion driften, sondern zu dort demonstrierten Abläufen hingezogen werden. Das ist die Motivation des Stabilitätslosses, noch keine universelle Garantie.
- **Mögliche Verwendung (B):** Motivation: Stabilität als alternativer Mechanismus.
- **Claim-ID:** [SBC-01](../CLAIMS.md#sbc-01); Evidenzklasse P-H.

### SBC-02 — PDF S. 2

- **Abschnitt:** §III; Robot, Environment, Gl. (1). [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=2)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Policy π(x,y) imitiert Aktionen. Die Umgebung folgt g(x,y,u); g darf im sogenannten modellfreien Fall unbekannt sein. Die Annahme eines genauen f bleibt bestehen und ist nicht gleichbedeutend mit dynamikfreiem Lernen.
- **Mögliche Verwendung (B):** Methoden/Voraussetzungen: präzise Bedeutung von model-free.
- **Claim-ID:** [SBC-02](../CLAIMS.md#sbc-02); Evidenzklasse P-M.

### SBC-03 — PDF S. 3

- **Abschnitt:** §IV-A; Gl. (2)–(6). [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=3)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der gemeinsame Fehler z enthält Abweichungen in x und y. Sein Jacobian A umfasst Ableitungen von f, g und π. Die Analyse beschreibt lokale Trajektorienabweichungen, keine globale Rückkehrgarantie aus beliebigen Fehlerzuständen.
- **Mögliche Verwendung (B):** Theorie: lokale Linearisierung statt globaler Stabilitätsbehauptung.
- **Claim-ID:** [SBC-03](../CLAIMS.md#sbc-03); Evidenzklasse P-T.

### SBC-04 — PDF S. 4

- **Abschnitt:** §IV-B; Gl. (7). [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Instabile lokale Modi werden mit ReLU(Re(σ)) bestraft. Das BC-Ziel bleibt notwendig, weil reine Stabilisierung nach der Autorendiskussion keine richtige Aufgabenlösung sicherstellt.
- **Mögliche Verwendung (B):** Methoden: Stabilitätsregularisierung und Taskperformance trennen.
- **Claim-ID:** [SBC-04](../CLAIMS.md#sbc-04); Evidenzklasse P-M.

### SBC-05 — PDF S. 4

- **Abschnitt:** §IV-C; Bounded Stability, Gl. (8)–(10). [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=4)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Ohne g stabilisiert sie nicht die vollständige gekoppelte Matrix. Die Roboterdynamik erhält einen Störungseingang A₂e_y. Der im Text angegebene Bound hängt von A₂, der Umgebungsabweichung und der Zeitentwicklung des Robotersystems ab.
- **Mögliche Verwendung (B):** Theorie/Limitationen: zusätzliche Annahme über Umgebungsabweichungen.
- **Claim-ID:** [SBC-05](../CLAIMS.md#sbc-05); Evidenzklasse P-T.

### SBC-06 — PDF S. 5

- **Abschnitt:** §IV-C; Gl. (11) und erster Absatz danach. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** λ₁ gewichtet die Norm von A₂, λ₂ die positiven Eigenwertrealteile von A₁. Die Autoren nennen diese Aussage schwächer als die modellbasierte: nur Roboterfehler unter begrenztem Umgebungsfehler werden behandelt.
- **Mögliche Verwendung (B):** Methoden: Original-Loss und Geltungsbereich.
- **Claim-ID:** [SBC-06](../CLAIMS.md#sbc-06); Evidenzklasse P-M.

### SBC-07 — PDF S. 6

- **Abschnitt:** §V-B; Abb. 3 und Methods. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der Task hat bekannte nichtlineare Roboterdynamik, fixe Hindernisse und fixe Zielposition. Zehn getrennte Trainingsläufe werden jeweils mit hundert Rollouts getestet. Die Autoren berichten höhere Erfolgsrate bei weniger Demos, ohne hier Zahlen aus der Kurve zu interpolieren.
- **Mögliche Verwendung (B):** Verwandte Arbeiten/Evaluation: kontrollierter Test und Datenregime.
- **Claim-ID:** [SBC-07](../CLAIMS.md#sbc-07); Evidenzklasse P-E.

### SBC-08 — PDF S. 7

- **Abschnitt:** §VI; Training Data, Testing Procedure, Results. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=7)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Zehn Personen liefern getrennte Datensätze. Pro Datenmenge werden zehn personenspezifische Policies und je zehn Rollouts betrachtet; ein Rollout endet spätestens nach 25 Hits. Autoren-ANOVA und Post-hoc-Tests berichten p < 0,05; dies ist keine Signifikanzangabe für unsere Experimente.
- **Mögliche Verwendung (B):** Evaluation: Effekt mit Autorentest und klarer Replikationseinheit.
- **Claim-ID:** [SBC-08](../CLAIMS.md#sbc-08); Evidenzklasse P-E.

### SBC-09 — PDF S. 8

- **Abschnitt:** §VI; Ergebnisfortsetzung und Abb. 5. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Ein Richtungswechsel ist zuvor als Aktionsänderung über zehn Grad definiert. Die Autoren berichten Unterschiede bei allen Datenmengen und auch bei gepoolten 1200 Sekunden; bei großen Datenmengen nähern sich die Hit-Leistungen beider Verfahren an.
- **Mögliche Verwendung (B):** Evaluation: Bewegungsqualität von Aufgabenleistung unterscheiden.
- **Claim-ID:** [SBC-09](../CLAIMS.md#sbc-09); Evidenzklasse P-E.

### SBC-10 — PDF S. 4

- **Abschnitt:** §IV-C; Stability vs. Performance. [Fundstelle](https://arxiv.org/pdf/2408.06246v1#page=4)
- **Kurzes Originalzitat:** “Stability vs. Performance”
- **Genaue Paraphrase (A):** Geht die Umgebungskopplung gegen null, verliert die Policy ihre Abhängigkeit von y. Das hilft der Entkopplung der Fehler, kann aber Aufgaben wie das Verfolgen des Pucks verhindern. Die Autoren behandeln dies als Trade-off mit BC.
- **Mögliche Verwendung (B):** Diskussion: Robustheit und erforderliche Zustandsreaktion.
- **Claim-ID:** [SBC-10](../CLAIMS.md#sbc-10); Evidenzklasse P-L.
