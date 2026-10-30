# Paper-Keynotes mit Seiten- und Zeilenbelegen

Stand: 21.10.2026. 48 paraphrasierte Stichpunkte zu den acht Papern der Forschungsnotiz.

## So verwendest du die Fundstellen

**S.** ist die PDF-Seite, ab der ersten PDF-Seite mit 1 gezählt. **Z.** bezeichnet die selbst erzeugte, seitenlokale Nummer einer nichtleeren Textzeile in der verlinkten Lesefassung. Es sind **keine offiziellen Zeilennummern der Publikation**. Bei zweispaltigen PDFs kann eine Layoutzeile Text beider Spalten enthalten; deshalb steht die Spalte zusätzlich am Beleg. Absätze nicht spaltenübergreifend lesen. Die Nummerierung ist eingefroren und nicht mit Editorzeilen identisch.

Alle Stichpunkte sind Paraphrasen, keine wörtlichen Zitate. Einordnungen und Einschränkungen sind als solche formuliert. Für den wissenschaftlichen Text Autor/Jahr plus Seite und ggf. Abschnitt verwenden; die eigenen Zeilenangaben dienen als Suchhilfe. Beispiel: „… (Zhao et al., 2023, PDF-S. 5, Abschn. IV-A).“ Die Literaturfassung im Literaturverzeichnis muss zur verwendeten PDF passen.

Die PDF-Hashes, Quellen-URLs und Zeilenzahlen stehen im [Manifest](_research/keynote_sources/manifest.json). Die Extraktion erfolgte mit pypdf 6.10.0 im Layoutmodus, ohne Leerzeilen; Formeln können Extraktionsartefakte enthalten. Die zitierten Textbereiche wurden gelesen; acht kritische Seiten zusätzlich als Seitenbilder geprüft. Dies ist keine vollständige Replikation oder mathematische Prüfung aller Paper.

**Versionshinweise:** Stable-BC wird ausschließlich aus arXiv v1 belegt; Open X-Embodiment aus arXiv v5. Für UMI wird das RSS-PDF verwendet. Zahlen und Fundstellen nicht ungeprüft auf andere Fassungen übertragen.

**Korrektur zur älteren Literaturübersicht:** Das DAgger-PDF zeigt gedruckte Proceedings-Paginierung (z. B. PDF-S. 4 = gedruckte S. 630), die der Textextraktor teilweise auslässt. Hier wird durchgehend die eindeutige PDF-Seitenzählung verwendet.

## DAgger — Ross, Gordon und Bagnell (2011)

AISTATS/PMLR-Original, 9 PDF-Seiten.

[Originalquelle](https://proceedings.mlr.press/v15/ross11a/ross11a.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/dagger.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt>)

- **DAGGER-K01 — Problem:** Eigene Aktionen verändern die späteren Beobachtungen. Dadurch ist die i.i.d.-Annahme klassischen überwachten Lernens im Rollout verletzt. **Fundstelle:** [PDF-S. 1, Z. 14–30](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:17>), rechte Spalte, Einleitung.

- **DAGGER-K02 — BC-Lernziel:** Klassisches BC minimiert den Imitationsverlust auf Expertenzuständen; das eigentliche Imitationsziel bewertet dagegen die durch die Policy selbst erzeugte Zustandsverteilung. **Fundstelle:** [PDF-S. 2, Z. 13–25](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:64>), rechts, §2, Gl. (1); [PDF-S. 2, Z. 28–36](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:79>), rechts, §2.1, Gl. (2).

- **DAGGER-K03 — Fehlerakkumulation:** Theorem 2.1 liefert unter den genannten 0–1-Surrogatloss- und Kostenannahmen den Worst-Case-Term T²ε. Das ist keine allgemeine Vorhersage empirischer Fehlerkurven. **Fundstelle:** [PDF-S. 2, Z. 38–49](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:89>), rechts, Theorem 2.1.

- **DAGGER-K04 — Algorithmus:** DAgger sammelt Rollouts, lässt die besuchten Zustände vom Experten labeln und trainiert auf dem aggregierten Datensatz. Die Policy wird anhand von Validierung ausgewählt. **Fundstelle:** [PDF-S. 4, Z. 2–13](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:168>), links, Algorithmus 3.1.

- **DAGGER-K05 — Expertmischung:** Die Erhebung kann Expert- und Learneraktionen mischen; der mittlere Expertanteil soll gegen null gehen. Expertlabels bleiben Teil der Datenerhebung. **Fundstelle:** [PDF-S. 4, Z. 26–44](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:192>), links, §3; [PDF-S. 4, Z. 7–10](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:173>), links, Algorithmus 3.1.

- **DAGGER-K06 — Empirischer Umfang:** Die Originalarbeit untersucht SuperTuxKart, Super Mario und OCR. Ihre Experimente sind kein direkter Nachweis für robotisches Stack- oder Multitask-Lernen. **Fundstelle:** [PDF-S. 2, Z. 27–39](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dagger.numbered.txt:78>), links, Einleitung.


## DART — Laskey et al. (2017)

CoRL/PMLR-Original, 14 PDF-Seiten.

[Originalquelle](https://proceedings.mlr.press/v78/laskey17a/laskey17a.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/dart.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt>)

- **DART-K01 — Mechanismus:** Rauschen wird während der Expertenausführung injiziert. Der Expert demonstriert dadurch echte Korrekturen; anschließend wird auf diesen Demonstrationen überwacht gelernt. **Fundstelle:** [PDF-S. 4, Z. 23–35](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:182>), §4, links neben Abb. 1; [PDF-S. 4, Z. 43–47](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:202>), §4, Gl. (2).

- **DART-K02 — Rauschwahl:** Richtung und Größe des Rauschens sollen die Fehler der späteren Policy annähern. DART optimiert ein parametrisiertes Rauschmodell statt beliebiges Rauschen zu verwenden. **Fundstelle:** [PDF-S. 2, Z. 14–21](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:65>), §1.

- **DART-K03 — Daten:** Die reale HSR-Studie verwendet vier Demonstratoren. Pro untersuchter Bedingung wird die finale Policy mit 40 Demonstrationen trainiert: zehn anfänglichen und 30 zusätzlichen. **Fundstelle:** [PDF-S. 8, Z. 18–28](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:362>), §5.2.

- **DART-K04 — Ergebnis mit Erfolgskriterium:** Berichtet werden 79 % für DART α=3 gegenüber 49 % für BC. Erfolg betrifft Zielidentifikation und freien Greifpfad; danach folgt ein Open-loop-Greifplan. **Fundstelle:** [PDF-S. 8, Z. 29–37](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:373>), §5.2.

- **DART-K05 — Rauschstärke als Grenze:** DART α=6 erreicht 72 %. Die Autoren vermuten zu starkes Rauschen für den menschlichen Demonstrator; mehr Rauschen ist hier nicht automatisch besser. **Fundstelle:** [PDF-S. 8, Z. 33–37](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:377>), §5.2.

- **DART-K06 — Offener Kamerawiderspruch:** Abb. 3 beschreibt eine kopfmontierte RGB-D-Kamera, der Fließtext eine Eye-in-hand-Perspektive. Die Kameramontage deshalb nicht ohne Klärung eindeutig zitieren. **Fundstelle:** [PDF-S. 8, Z. 1–4](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:345>), Bildunterschrift Abb. 3; [PDF-S. 8, Z. 10–16](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/dart.numbered.txt:354>), §5.2.


## Stable-BC — Mehta et al. (Preprint 2024)

arXiv:2408.06246v1, 8 PDF-Seiten. RA-L 2025 ist bibliographisch bekannt; diese Fundstellen belegen ausschließlich v1, nicht die Journalfassung.

[Originalquelle](https://arxiv.org/pdf/2408.06246v1) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/stable_bc.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt>)

- **STABLE_BC-K01 — Intervention:** Stable-BC verändert das Lernverfahren über Stabilitätsbedingungen; der Trainingsdatensatz muss dafür nicht verändert werden. **Fundstelle:** [PDF-S. 2, Z. 7–12](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:69>), links, Beitragsübersicht.

- **STABLE_BC-K02 — Voraussetzungen:** Roboterzustand x und Umgebungszustand y werden getrennt. Ein genaues Modell der Roboterdynamik f wird vorausgesetzt; die Umgebungsdynamik g darf unbekannt sein. **Fundstelle:** [PDF-S. 2, Z. 25–44](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:87>), rechts, §III.

- **STABLE_BC-K03 — Lokale Analyse:** Die Arbeit linearisiert gekoppelte Fehlerdynamiken und untersucht die Eigenwerte der Matrix A. Der Bezug ist lokale Stabilität nahe demonstriertem Verhalten. **Fundstelle:** [PDF-S. 3, Z. 17–31](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:138>), rechts, §IV-A.

- **STABLE_BC-K04 — Loss und Parameter:** Im modellbasierten Fall ergänzt eine Strafe auf positive Realteile der Eigenwerte den BC-Loss. λ steuert das relative Gewicht. **Fundstelle:** [PDF-S. 4, Z. 2–21](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:183>), links, Gl. (7) und Erläuterung.

- **STABLE_BC-K05 — Stabilität ≠ Aufgabenerfolg:** Die Autoren erklären ausdrücklich, dass Stabilität allein keine korrekte Aufgabenausführung sicherstellt; eine Policy könnte lokal stehen bleiben. **Fundstelle:** [PDF-S. 3, Z. 45–58](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:166>), rechts, Stability vs. Performance.

- **STABLE_BC-K06 — Grenze von model-free:** Ohne g wird eine Schranke für die Abweichung des Umgebungszustands angenommen. Die Methode bleibt von f abhängig und liefert keine uneingeschränkte globale Taskgarantie. **Fundstelle:** [PDF-S. 4, Z. 22–45](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:203>), links, §IV-C; [PDF-S. 2, Z. 29–31](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/stable_bc.numbered.txt:91>), rechts, Robot.


## ACT — Zhao et al. (2023)

Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware, RSS-Original, 19 PDF-Seiten.

[Originalquelle](https://www.roboticsproceedings.org/rss19/p016.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/act.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt>)

- **ACT-K01 — Action Chunking:** ACT sagt Sequenzen von k Aktionen voraus. Die Autoren motivieren dies mit einem kürzeren effektiven Entscheidungshorizont und zeitlichen Abhängigkeiten menschlicher Demonstrationen. **Fundstelle:** [PDF-S. 5, Z. 35–45](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:233>), links, §IV-A; [PDF-S. 5, Z. 5–15](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:203>), rechts, Fortsetzung §IV-A.

- **ACT-K02 — Temporal Ensembling:** Bei jedem Zeitschritt neu vorhergesagte Chunks überlappen. Gemittelt werden Vorhersagen für denselben Ausführungszeitpunkt; dadurch entstehen zusätzliche Inferenzkosten. **Fundstelle:** [PDF-S. 5, Z. 16–37](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:214>), rechts, §IV-A.

- **ACT-K03 — Generatives Training:** ACT wird als CVAE trainiert. Zur Ausführung wird der Encoder verworfen und z auf null gesetzt; die beschriebene Decodierung ist damit deterministisch. **Fundstelle:** [PDF-S. 6, Z. 27–43](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:272>), links, §IV-B.

- **ACT-K04 — Eingaben und Aktionen:** Die beschriebene Policy nutzt vier RGB-Bilder mit 480×640 Pixeln und Gelenkpositionen. Ausgaben sind absolute Zielgelenkpositionen beider Arme, insgesamt 14 Dimensionen pro Schritt. **Fundstelle:** [PDF-S. 6, Z. 13–24](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:258>), rechts, §IV-C.

- **ACT-K05 — Trainingsbedingungen:** Die Autoren nennen ungefähr 80 Millionen Parameter, Training von Grund auf pro Aufgabe und etwa fünf Stunden auf einer RTX 2080 Ti. Diese Zahlen sind setupspezifisch. **Fundstelle:** [PDF-S. 6, Z. 46–50](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:291>), rechts, §IV-C.

- **ACT-K06 — Offene Loss-Diskrepanz:** Algorithmus 1 nennt MSE als Rekonstruktionsloss; der Implementierungsabschnitt nennt L1 statt L2. Die konkrete Losswahl nur mit dieser Versionsdiskrepanz wiedergeben. **Fundstelle:** [PDF-S. 6, Z. 11–13](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:256>), links, Algorithmus 1; [PDF-S. 6, Z. 39–44](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/act.numbered.txt:284>), rechts, §IV-C.


## Diffusion Policy — Chi et al. (2023)

RSS-Original, 16 PDF-Seiten; keine Übertragung der Belege auf die spätere IJRR-Erweiterung.

[Originalquelle](https://www.roboticsproceedings.org/rss19/p026.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/diffusion_policy.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt>)

- **DIFFUSION_POLICY-K01 — Grundidee:** Das Diffusionsmodell erzeugt Roboteraktionen durch einen auf Beobachtungen konditionierten Denoising-Prozess. **Fundstelle:** [PDF-S. 3, Z. 7–14](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:115>), links, §II-C.

- **DIFFUSION_POLICY-K02 — Ausführungshorizonte:** Aus To Beobachtungsschritten werden Tp Aktionen vorhergesagt; nur Ta davon werden vor erneuter Planung ausgeführt. Beobachtungs-, Vorhersage- und Ausführungshorizont sind verschiedene Parameter. **Fundstelle:** [PDF-S. 3, Z. 15–28](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:123>), links, §II-C.

- **DIFFUSION_POLICY-K03 — Backbone-Abwägung:** Die Autoren berichten für Transformer gute Ergebnisse bei komplexen oder schnell wechselnden Aktionen, aber höhere Hyperparametersensitivität. Sie schlagen CNN als ersten Versuch vor. **Fundstelle:** [PDF-S. 4, Z. 8–21](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:162>), links, §III-A.

- **DIFFUSION_POLICY-K04 — Kameraverarbeitung:** Unterschiedliche Ansichten erhalten separate Encoder. ResNet-18 wird ohne Vortraining gemeinsam mit der Policy trainiert; Spatial Softmax und GroupNorm ersetzen Standardkomponenten. **Fundstelle:** [PDF-S. 4, Z. 23–35](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:177>), links, §III-B.

- **DIFFUSION_POLICY-K05 — Multimodalität:** Stochastische Initialisierung und Sampling erlauben mehrere Aktionsmodi. Abb. 4 illustriert alternative Wege um ein Objekt; das ist ein konkretes Beispiel, keine universelle Generalisierungsgarantie. **Fundstelle:** [PDF-S. 4, Z. 6–25](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:160>), rechts, §IV-A; [PDF-S. 4, Z. 33–39](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:187>), rechts, Abb. 4.

- **DIFFUSION_POLICY-K06 — Inferenzkosten:** DDIM erlaubt weniger Denoising-Schritte bei der Inferenz. Berichtet werden 100 Trainings- gegenüber zehn Inferenzschritten und etwa 0,1 s Latenz auf einer RTX 3080. **Fundstelle:** [PDF-S. 4, Z. 46–56](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/diffusion_policy.numbered.txt:200>), links, §III-D.


## UMI — Chi et al. (2024)

RSS-Original p045, 14 PDF-Seiten; eigens aus den Proceedings geladen, nicht mit der vorhandenen unversionierten latex-Datei gleichgesetzt.

[Originalquelle](https://www.roboticsproceedings.org/rss20/p045.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt>)

- **UMI-K01 — Erhebung:** UMI verwendet einen handgeführten Parallelgreifer mit GoPro als Sensor und Aufnahmegerät; für bimanuale Demonstrationen kommt ein zweiter Greifer hinzu. **Fundstelle:** [PDF-S. 4, Z. 1–9](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:150>), links, §III-A.

- **UMI-K02 — Kameramontage:** UMI nutzt ausschließlich Wrist-Kameras. Bei Demonstration und Roboterausführung bleibt ihre Montage relativ zu den Greiferfingern gleich, um Beobachtungsunterschiede zu reduzieren. **Fundstelle:** [PDF-S. 4, Z. 18–29](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:167>), links, HD1.

- **UMI-K03 — Bildinformation:** Ein 155°-Fisheye erweitert den Kontext; Seitenspiegel liefern zusätzliche Perspektiven für implizite Tiefeninformation. **Fundstelle:** [PDF-S. 2, Z. 1–3](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:48>), Abb. 2; [PDF-S. 4, Z. 34–46](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:183>), rechts, HD3.

- **UMI-K04 — Zeit und Aktionen:** Beobachtungen werden zeitlich abgeglichen; veraltete Aktionen verworfen. Vorhergesagte Posen beziehen sich auf dieselbe aktuelle Endeffektorpose. **Fundstelle:** [PDF-S. 6, Z. 1–11](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:250>), links, PD1.1; [PDF-S. 6, Z. 22–42](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:271>), links, PD1.2/PD2.

- **UMI-K05 — Kameraablation:** Beim Cup Arrangement: 305 Demonstrationen, 20 Testfälle; UMI erreicht 20/20, die auf 69° entzerrte/beschnittene Bildvariante 11/20. Dies isoliert nicht allein die Kameraposition. **Fundstelle:** [PDF-S. 7, Z. 24–28](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:331>), links, Performance; [PDF-S. 7, Z. 14–25](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:321>), rechts, No Fisheye lens.

- **UMI-K06 — Generalisierungsziel:** Die Generalisierungsfrage betrifft unbekannte Umgebungen und Objekte. Die Capability-Tests verwenden vier Aufgaben mit randomisierten Starts in der Erhebungsumgebung. **Fundstelle:** [PDF-S. 6, Z. 33–40](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:282>), rechts, §IV; [PDF-S. 6, Z. 52–56](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/umi.numbered.txt:301>), rechts, §V.


## LIBERO — Liu et al. (2023)

NeurIPS Datasets and Benchmarks, offizielles Proceedings-PDF, 16 Seiten.

[Originalquelle](https://proceedings.neurips.cc/paper_files/paper/2023/file/8c3c666820ea055a77726d66fc7d447f-Paper-Datasets_and_Benchmarks.pdf) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt>)

- **LIBERO-K01 — Problemdefinition:** Eine aufgabenkonditionierte Policy lernt Aufgaben nacheinander. Frühere Aufgabendaten sind beim Lernen neuer Aufgaben nicht vollständig verfügbar. **Fundstelle:** [PDF-S. 3, Z. 13–24](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:108>), §2.2; [PDF-S. 3, Z. 25–40](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:120>), Lifelong Imitation Learning.

- **LIBERO-K02 — Benchmarkstruktur:** Spatial, Object und Goal enthalten jeweils zehn Aufgaben und variieren unterschiedliche Wissensaspekte. LIBERO-100 ergänzt 100 Aufgaben mit gemischten Anforderungen. **Fundstelle:** [PDF-S. 5, Z. 13–29](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:200>), §4.2.

- **LIBERO-K03 — Einfach → komplex:** LIBERO-100 wird in 90 kurze Vortrainingsaufgaben und zehn lange Aufgaben für nachfolgendes Lifelong Learning aufgeteilt. Das Protokoll ist kein reiner Zero-shot-Test. **Fundstelle:** [PDF-S. 5, Z. 30–33](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:217>), §4.2; [PDF-S. 3, Z. 25–40](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:120>), §2.2.

- **LIBERO-K04 — Datenherkunft:** Je Aufgabe werden 50 hochwertige Demonstrationen bereitgestellt, erhoben durch menschliche Teleoperation mit einer 3Dconnexion SpaceMouse. **Fundstelle:** [PDF-S. 6, Z. 11–15](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:251>), Ende §4.4.

- **LIBERO-K05 — Vergleichsmethoden:** Verglichen werden Experience Replay, EWC und PackNet sowie sequenzielles Fine-Tuning und Multitask-Lernen als Referenzen. **Fundstelle:** [PDF-S. 5, Z. 34–42](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:221>), §4.3.

- **LIBERO-K06 — Metriken:** Forward Transfer, negativer Backward Transfer und AUC beruhen auf Erfolgsraten. Sie erfassen Lernen neuer Aufgaben, Vergessen und Gesamtleistung; die Checkpointregel gehört zur Definition. **Fundstelle:** [PDF-S. 6, Z. 28–42](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:268>), §5.1; [PDF-S. 6, Z. 54–57](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/libero.numbered.txt:294>), Fußnote 5.


## Open X-Embodiment / RT-X — Collaboration (2024er Preprint)

arXiv:2310.08864v5 vom 21.03.2024, 12 PDF-Seiten. ICRA 2024 ist der Publikationsort; diese Belege gelten für v5. Der finale Verlagsvolltext wurde nicht abgeglichen.

[Originalquelle](https://arxiv.org/pdf/2310.08864v5) · [Lokales PDF](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.pdf>) · [Nummerierte Lesefassung](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt>)

- **OPEN_X-K01 — Datenumfang:** Die Fassung beschreibt über eine Million reale Trajektorien aus 60 Datensätzen und 22 Verkörperungen, vereinheitlicht im RLDS-Format. **Fundstelle:** [PDF-S. 3, Z. 13–27](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:130>), rechts, §III-A.

- **OPEN_X-K02 — Trainingsmenge unterscheiden:** Die experimentelle Trainingsmischung umfasst neun Verkörperungen. Die 22 Verkörperungen des Gesamtbestands dürfen nicht als Trainingsumfang dieser Experimente angegeben werden. **Fundstelle:** [PDF-S. 5, Z. 19–28](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:225>), links, Fortsetzung §IV-C.

- **OPEN_X-K03 — Modalitäten und Koordinaten:** Pro Datensatz wird eine Kameraansicht gewählt; Aktionen werden normalisiert und grob vereinheitlicht. Koordinatenrahmen sowie absolute/relative Positions- oder Geschwindigkeitssteuerung bleiben heterogen. **Fundstelle:** [PDF-S. 4, Z. 20–44](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:176>), links, §IV-A.

- **OPEN_X-K04 — Transferbefund:** In der Emergent-Skills-Evaluation erreicht RT-2-X 75,8 % gegenüber 27,3 % für RT-2. Die Fertigkeiten fehlen in den Google-Robot-Daten, sind aber in Bridge vorhanden. **Fundstelle:** [PDF-S. 6, Z. 1–10](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:260>), Tabelle II; [PDF-S. 6, Z. 19–33](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:278>), links, §V-B.

- **OPEN_X-K05 — Datenablation:** Ohne Bridge sinkt der entsprechende RT-2-X-Wert auf 42,8 %. Die Autoren deuten dies als Evidenz für Fertigkeitstransfer aus WidowX-Daten. **Fundstelle:** [PDF-S. 6, Z. 1–10](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:260>), Tabelle II; [PDF-S. 6, Z. 34–40](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:293>), links, §V-B.

- **OPEN_X-K06 — Übertragungsgrenze:** Die Experimente untersuchen keine Generalisierung auf neue Roboter und keine stark abweichenden Sensor-/Aktuatormodalitäten. **Fundstelle:** [PDF-S. 6, Z. 50–59](<F:/Desktop/Programmieren/IT/Imitation Learning/literature/_research/keynote_sources/open_x.numbered.txt:309>), rechts, §VI.


## Hinweise fürs Schreiben

Die Ergebnisse verschiedener Paper sind keine gemeinsame Rangliste. Bei Zahlen jeweils Aufgabe, Datenmenge, Metrik und Versuchsbedingungen nennen. DAgger/DART behandeln vor allem Zustandsverteilungen; Stable-BC lokale Stabilität; ACT/Diffusion Policy die Policyrepräsentation; UMI die Erhebungs- und Ausführungsschnittstelle; LIBERO und Open X-Embodiment liefern unterschiedliche Transferprotokolle. Diese Zuordnung ist eine redaktionelle Synthese der obigen Belege.

Bei ACT bleibt die Diskrepanz L1/MSE und bei DART die Kamerabeschreibung offen. Nicht stillschweigend eine Variante auswählen. Die neuen IDs mit „-K“ sind unabhängig vom älteren [Claim-Register](CLAIMS.md); dessen IDs bleiben unverändert.
