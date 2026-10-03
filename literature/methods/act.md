# ACT — Action Chunking with Transformers

## 1. Vollständige bibliographische Angaben

Tony Z. Zhao, Vikash Kumar, Sergey Levine, Chelsea Finn (2023). *Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware.* *Robotics: Science and Systems XIX*, Paper 016, Daegu, Republic of Korea, Juli 2023. DOI [10.15607/RSS.2023.XIX.016](https://doi.org/10.15607/RSS.2023.XIX.016). Konferenz 10.–14. Juli. [Offizielle Proceedings](https://www.roboticsproceedings.org/rss19/p016.html), [Bibliographie/BibTeX](../BIBLIOGRAPHY.md#act--zhao2023act). Kein durchgehend paginierter Seitenbereich in der offiziellen Referenz; PDF 19 Seiten.

## 2. Publikationsstatus und geprüfte Fassung

**Peer-reviewed RSS-Originalbeitrag**, [Lesefassung](../_research/act.pdf). Geprüft: Haupttext S. 1–11 und relevante Architektur-/Experiment-/Limitationsappendices S. 15–19. Ergebnisse zu ALOHA-Teleoperation werden von Erfolgen autonom gelernter ACT-Policies getrennt. Tabelle I auf S. 4 zeigt menschliche Teleoperation und darf nicht als ACT-Ergebnis ausgegeben werden.

## 3. Forschungsproblem — A

Feine bimanuale Manipulation verlangt Präzision und Feedback. Kleine Imitationsfehler können die Policy aus dem Demoablauf bringen. Zusätzlich enthalten menschliche Demos unterschiedliche gültige Aktionsfolgen und nichtstationäre Pausen. Das Paper kombiniert einen kostengünstigen Teleoperationsaufbau ALOHA mit einer Lernmethode, die diese Daten nutzen soll. S. 1–2, §I.

## 4. Zentrale Hypothese / Motivation — A

Gemeinsame Vorhersage von Aktionsfolgen verkürzt den effektiven Entscheidungs-/Vorhersagehorizont und modelliert kurzfristig korrelierte Ausführung besser. Überlappende Chunks sollen durch Ensembling präzisere, glattere Aktionen liefern. Ein CVAE soll Variation menschlicher Demos erfassen. Diese drei Ideen werden separat abliert; sie sind nicht austauschbar. S. 5–6 und 10.

## 5. Methode — A

ACT ist eine transformerbasierte CVAE-Policy. Der Trainingsencoder verarbeitet propriozeptive Beobachtung und demonstrierten Chunk zu einer Gaußverteilung über den Style-Latent `z`. Der Decoder verarbeitet vier RGB-Ansichten, aktuellen Gelenkzustand und `z` und erzeugt `k×14` absolute Gelenkziele. Zur Inferenz entfällt der Trainingsencoder; `z=0` liefert deterministische Chunks.

Temporales Ensembling fragt die Policy **jedes Zeitschritt** neu ab und kombiniert Vorhersagen verschiedener Chunks für denselben aktuellen Zeitpunkt. Das ist eine andere Ausführung als das ungeprüfte Abarbeiten eines vollständigen Chunks. S. 5–6, Abb. 5–6, Algorithmen 1–2; Architekturdetails S. 15–16/18.

## 6. Relevante Gleichungen — A

**Chunkmodell**, S. 5, §IV-A:

\[
\pi_\theta(a_{t:t+k}\mid s_t)
\quad\text{anstelle von}\quad \pi_\theta(a_t\mid s_t).
\]

Die Papierschreibweise `t:t+k` bezeichnet den Chunk; der Text definiert seine Länge als `k`. Keine zusätzliche `k+1`-Ausgabe aus der Indexnotation ableiten.

**CVAE-Ziel**, S. 6, Algorithmus 1 und §IV-B/C, in zusammengefasster Notation:

\[
z\sim q_\phi(z\mid a_{t:t+k},\bar o_t),\qquad
L=L_{reconst}+\beta\,D_{KL}(q_\phi\Vert\mathcal N(0,I)).
\]

`ō_t` enthält keine Bilder. Der Decoder erhält vollständiges `o_t` und `z`. **Widerspruch in der Quelle:** Algorithmus 1 schreibt `L_reconst=MSE`; §IV-C schreibt ausdrücklich **L1 statt L2**. Hier ist L1 die berichtete konkrete Implementierungsentscheidung, MSE die abweichende Pseudocodeangabe. Exakte Auflösung ohne versionsgebundenen Codeabgleich **ungeklärt**. Keine Gleichheit der beiden Objectives behaupten.

**Temporales Ensembling**, S. 5–6, §IV-A und Algorithmus 2:

\[
a_t=\frac{\sum_i w_i\hat a_t^{(i)}}{\sum_iw_i},\qquad
w_i=\exp(-mi).
\]

Alle `â_t^(i)` sind für **t**, aus unterschiedlich alten Plänen. `i=0` bezeichnet laut Text den ältesten Plan; für positives `m` erhält dieser das größte Gewicht. Kleineres `m` lässt neue Beobachtungen schneller einfließen. Nicht stillschweigend zu „neueste Vorhersage erhält größte Gewichtung“ umformulieren.

**Testinferenz:** `z=0`, Mittelwert des Standardnormalpriors. S. 6 und 16. Generatives Training, deterministische beschriebene Testpolicy. Die k-fache Horizontverkürzung ist methodische Motivation, kein eigener DAgger-artiger Performancebound.

## 7. Verwendete Daten / Tasks — A

Sechs reale Tasks: Slide Ziploc, Slot Battery, Open Cup, Thread Velcro, Prep Tape, Put On Shoe. Zwei MuJoCo-Tasks: Cube Transfer und Bimanual Insertion, jeweils mit geskripteten und menschlichen Demos. Reale Demos: 50 je Task, Thread Velcro 100; Simulationsbedingungen je 50 erfolgreiche Demos. Demos dauern etwa 8–14 s bei 50 Hz. S. 8–9, §V-A/B.

ALOHA verwendet zwei steuernde und zwei ausführende Arme; ACT beobachtet vier RGB-Kameras und 14 Gelenk-/Greiferwerte. Absolute Zielgelenkpositionen werden vom internen schnellen PID verfolgt. Niedrige Ebene >1 kHz, Zielübertragung 50 Hz; die Kameras streamen laut Appendix mit 30 fps. Die Raten sind daher keine identische 50-Hz-Sensor-/Lernschleife. S. 3–6/15.

Weitere Lernversuche mit Candy-Unwrapping und kleinem flach liegendem Ziploc-Bag werden als Fehlversuche berichtet (S. 17); zusätzliche teleoperierte Demos sind nicht zusätzliche erfolgreiche autonome ACT-Tasks.

## 8. Baselines — A

BC-ConvMLP, BeT, RT-1, VINN. Für zwei Simulations- und zwei reale Tasks werden alle vier verglichen; für die verbleibenden vier realen Tasks nur BeT. S. 8–10. Die Tabellenunterschrift III sagt versehentlich „remaining 3“, enthält aber **vier** Tasks; die tatsächlichen Spalten wurden geprüft.

Baselines werden auf Cube Transfer getunt, Hyperparameter S. 16/19. Zusätzliche Ablationen ergänzen BC-ConvMLP und VINN um Chunks, entfernen Ensembling oder CVAE. Die Ensemblingvarianten werden separat getunt; der Effekt ist kein vollständig eingefrorener einzelner Wrappervergleich.

## 9. Evaluationsmetriken — A

Finale und Teilphasen-Erfolgsraten je Task. Simulation: drei Seeds, je fünfzig Tests. Hardware: ein Seed, fünfundzwanzig Tests. In Ablationen Mittel über zwei simulierte Tasks mit jeweils zwei Datenquellen. Teleoperations-Userstudy misst separat menschliche Abschlusszeit bei 5 versus 50 Hz und ist kein autonomer Policyerfolg. S. 8–11. Checkpoint laut S. 5: niedrigster Validation-Loss.

## 10. Zentrale Ergebnisse — A

| Finale ACT-Tasklösung | Erfolgsrate | Protokoll |
|---|---:|---|
| Cube Transfer, Script / Human | 86 % / 50 % | 3 Seeds × 50 Tests, Tabelle II S. 8 |
| Bimanual Insertion, Script / Human | 32 % / 20 % | Gleiches Protokoll |
| Slide Ziploc | 88 % | 1 Seed × 25 Tests |
| Slot Battery | 96 % | Gleiches Hardwareprotokoll |
| Open Cup | 84 % | Tabelle III S. 8 |
| Thread Velcro | 20 % | Gleiches Hardwareprotokoll |
| Prep Tape | 64 % | Finale Hang-Phase, nicht 72 % Handover |
| Put On Shoe | 92 % | Finale Secure-Phase |

Chunking ohne Ensembling: mittlere Leistung etwa 1 % bei `k=1`, 44 % bei `k=100`; bei `k=200/400` etwas geringer. Ensembling-Ablation: +3,3 Prozentpunkte für ACT, +4 für BC-ConvMLP, negativer Effekt für VINN. CVAE-Entfernung: bei menschlichen Demos 35,3 % auf 2 %, bei deterministischen Scriptdaten kaum Unterschied. S. 10, §VI. Nicht daraus folgern, dass CVAE bei jedem programmierten Expert zwingend nutzlos ist.

## 11. Von Autoren genannte Limitationen — A

Thread Velcro scheitert oft bei Mid-Air-Grasp und Insertion; geringe Kontraste und kleiner Bildanteil erschweren Positionsschätzung (S. 10). Sehr lange Chunks verlieren Reaktivität (S. 10). Appendix F, S. 17: geringe Motorleistung, Parallelgreifer statt multifingriger Hand, Aufgaben mit Nägeln; diese Hardwaregrenzen sind von Policygrenzen getrennt.

Bei Candy-Unwrapping nach 50 Demos: Pickup 10/10, Ziehen 8/10, Auspacken **0/10**; eine andere Evaluation mit zehn Versuchen pro Candy erreicht 3/5 Candies. Der zweite Nenner ist keine alternative einmalige Erfolgsrate. Small-Ziploc-Bag-Pickup gelingt, anschließende Mid-Air-Schritte misslingen. Autoren vermuten Perzeptions-/Datenprobleme. Kein garantierter Robustheitsmechanismus für diese Fälle.

## 12. Wichtige Annahmen — A und B getrennt

**A:** Zeitlich passende Chunks und Sensor-/Aktionszuordnung; current-state Konditionierung; nutzbare, erfolgreiche Demonstrationen; absolute Gelenkziele in der berichteten Architektur; latente Standardnormalprior und `z=0` für Evaluation; gemeinsame Ausrichtung überlappender Vorhersagen. S. 5–6.

**B:** Den Begriff ACT nur für das Gesamtverfahren verwenden; ein MLP mit Chunk-Ausgabe ist allein keine ACT-Reproduktion. Die Testperformance bei einem Seed ist keine Messung breiter Trainingsvarianz. Ein Chunk enthält nicht zwingend genug Information für Gedächtnis über seine gesamte Lebensdauer hinaus.

## 13. Übertragbarkeit auf unser State-Stack-Problem — B/C

**B:** Die Unterscheidung Chunking/Ensembling/CVAE bietet einen präzisen Beschreibungsrahmen. Die script-versus-human Ablation ist für die Interpretation programmierter Demos besonders relevant, beweist aber keinen lokalen Effekt. Ein- und mehrphasige Erfolgskriterien sollten auseinandergehalten werden.

**C:** Direct sagt bereits 16×7 Aktionen aus zwei Stateframes voraus. Es ist ein Residual-MLP mit MSE, ohne CVAE und ohne temporales Ensembling. Die Queue verwendet Chunkindizes 1 und 2; Index 0 ist bereits Vergangenheit. Daher ist die lokale Policy eine direkte Chunkregression und keine Original-ACT-Policy. Zwei Frames beweisen nicht die Beobachtbarkeit der internen Expertphase.

## 14. Nicht übertragbare Punkte — B/C

Vier RGB-Kameras, bimanuale absolute Gelenkziele, 50 Hz und ACT-`k=100` sind keine Eigenschaften unserer einarmigen State-/OSC-Konfiguration bei 20 Hz. Die 88–96%-Erfolge sind keine Stackrate. Die CVAE-Human-Ablation darf nicht als Nachweis einer Verbesserung bei einem deterministischen phasenabhängigen StackExpert übernommen werden. Der ursprüngliche Ensembling-Effekt ist nicht durch den vorhandenen Direct/Diffusion-Vergleich isoliert. Keine theoretische Garantie globaler Fehlervermeidung oder sicherer Release-Schritte.

## Belegstellen mit Claim-IDs

Zehn relevante Stellen aus **RSS 2023, Original-Proceedings**. Jede Seite ist eine konkrete PDF-Seite der archivierten Fassung. Originalzitate sind bewusst auf einen kurzen Auszug pro Paper begrenzt; „—“ bedeutet, dass hier kein Originalzitat gespeichert wird. Paraphrasen sind A; Verwendungen sind B. Der Projektbezug C steht in Abschnitt 13–14.

### ACT-01 — PDF S. 5

- **Abschnitt:** §IV-A; erster Methodenabsatz. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der Chunk wird aus einer aktuellen Beobachtung erzeugt. Die Autoren verbinden die Sequenzvorhersage mit geringerer Fehlerakkumulation und dem Modellieren zeitlich zusammenhängender Pausen innerhalb eines Chunks. Es ist keine neue globale Fehlergarantie bewiesen.
- **Mögliche Verwendung (B):** Methoden: Motivation und Reichweite von Chunking.
- **Claim-ID:** [ACT-01](../CLAIMS.md#act-01); Evidenzklasse M.

### ACT-02 — PDF S. 5

- **Abschnitt:** §IV-A; Temporal Ensemble. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=5)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Die Policy wird jedes Zeitschritt erneut abgefragt. Alle Vorhersagen für Zeitpunkt t werden exponentiell gewichtet gemittelt; im Paper ist i=0 ausdrücklich die älteste Vorhersage. Benachbarte Zeitpunkte werden nicht einfach zeitlich geglättet.
- **Mögliche Verwendung (B):** Methoden: exakte Ausrichtungs- und Gewichtungsregel.
- **Claim-ID:** [ACT-02](../CLAIMS.md#act-02); Evidenzklasse M.

### ACT-03 — PDF S. 6

- **Abschnitt:** §IV-B; CVAE-Beschreibung. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Der Encoder erhält propriozeptive Beobachtung und Zielchunk, erzeugt eine diagonale Gaußverteilung über z und wird nach dem Training verworfen. Die Testpolicy erhält aktuelle Beobachtungen sowie den Mittelwert des Priors; generatives Training bedeutet hier keine zufällige Testaktion.
- **Mögliche Verwendung (B):** Methoden: Training und Inferenz einer generativen Policy.
- **Claim-ID:** [ACT-03](../CLAIMS.md#act-03); Evidenzklasse M.

### ACT-04 — PDF S. 6

- **Abschnitt:** §IV-C; Implementing ACT, Algorithmus 1. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=6)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Pro Schritt werden vier 480×640-Bilder und vierzehn Gelenk-/Greiferwerte verarbeitet, pro Chunk k×14 Gelenkziele ausgegeben. Die Autoren nennen L1 im Implementierungstext; Algorithmus 1 nennt dagegen MSE. Diese Inkonsistenz wird nicht stillschweigend aufgelöst.
- **Mögliche Verwendung (B):** Methoden/Reproduzierbarkeit: Modalität, Steuerraum und Loss.
- **Claim-ID:** [ACT-04](../CLAIMS.md#act-04); Evidenzklasse M.

### ACT-05 — PDF S. 9

- **Abschnitt:** §V-B; Data Collection. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=9)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Bei 50 Hz dauern Demos ungefähr acht bis vierzehn Sekunden. Die Simulationsaufgaben werden jeweils mit fünfzig erfolgreichen geskripteten oder menschlichen Demos untersucht. Menschliche Daten sind laut Autoren auch bei einem einzigen Demonstrator stochastisch.
- **Mögliche Verwendung (B):** Evaluation: Datenherkunft und Menge.
- **Claim-ID:** [ACT-05](../CLAIMS.md#act-05); Evidenzklasse M.

### ACT-06 — PDF S. 8

- **Abschnitt:** §V; Tabelle II. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Cube Transfer: 86 % mit Scriptdaten und 50 % mit menschlichen Demos; Bimanual Insertion: 32 % beziehungsweise 20 %. Je Bedingung werden drei Trainingsseeds und fünfzig Tests pro Seed berichtet. Teilphasenerfolg darf nicht als voller Taskerfolg ausgegeben werden.
- **Mögliche Verwendung (B):** Evaluation: Datenquelle, Seeds und finale Taskmetrik.
- **Claim-ID:** [ACT-06](../CLAIMS.md#act-06); Evidenzklasse E.

### ACT-07 — PDF S. 8

- **Abschnitt:** §V; Tabellen II–III. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=8)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Slide Ziploc erreicht 88 %, Slot Battery 96 %, Open Cup 84 %, Thread Velcro 20 %, Prep Tape 64 % und Put On Shoe 92 %. Das Protokoll nennt einen Trainingsseed und fünfundzwanzig Tests. Die Kurzzusammenfassung 80–90 % beschreibt nicht alle Tasks.
- **Mögliche Verwendung (B):** Evaluation: Ergebnisse vollständig und ohne pauschale Erfolgsrate berichten.
- **Claim-ID:** [ACT-07](../CLAIMS.md#act-07); Evidenzklasse E.

### ACT-08 — PDF S. 10

- **Abschnitt:** §VI-A; Ablations, Abb. 9(a)–(b). [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=10)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Temporales Ensembling ist für diese k-Ablation ausgeschaltet; für längere, nahezu offene Chunks nimmt die Leistung wieder etwas ab. Die separate Ensembling-Ablation wird eigenständig getunt und berichtet +3,3 Prozentpunkte für ACT; VINN profitiert nicht.
- **Mögliche Verwendung (B):** Ablationen: Chunking und Ensembling als getrennte Faktoren.
- **Claim-ID:** [ACT-08](../CLAIMS.md#act-08); Evidenzklasse E.

### ACT-09 — PDF S. 10

- **Abschnitt:** §VI-B; Abb. 9(c). [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=10)
- **Kurzes Originalzitat:** —
- **Genaue Paraphrase (A):** Über zwei Simulationsaufgaben sinkt die gemittelte Leistung mit menschlichen Daten ohne CVAE von 35,3 % auf 2 %. Bei vollständig deterministischen Scriptdaten beschreiben die Autoren fast keinen Unterschied. Die Aussage ist ausdrücklich datenquellenabhängig.
- **Mögliche Verwendung (B):** Diskussion: generatives Ziel bei menschlichen versus programmierten Demos.
- **Claim-ID:** [ACT-09](../CLAIMS.md#act-09); Evidenzklasse E.

### ACT-10 — PDF S. 17

- **Abschnitt:** Appendix F; Policy Learning Limitations. [Fundstelle](https://www.roboticsproceedings.org/rss19/p016.pdf#page=17)
- **Kurzes Originalzitat:** “difficulty of perception and lack of data”
- **Genaue Paraphrase (A):** Bei Candy-Unwrapping nach fünfzig Demos gelingt das vollständige Auspacken zunächst in null von zehn Tests, obwohl Teilphasen gelingen. Die Autoren nennen Wahrnehmung und fehlende Daten als Erklärungen; Mehrfachversuche pro Candy sind ein anderes Erfolgsprotokoll.
- **Mögliche Verwendung (B):** Limitationen: Teilphasenerfolg, Perzeption und Datenmenge.
- **Claim-ID:** [ACT-10](../CLAIMS.md#act-10); Evidenzklasse L.
