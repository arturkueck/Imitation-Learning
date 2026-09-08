# Plan B — Demonstrationsdaten, Fine-Tuning und Generalisierung in Simulation

## Kurzübersicht

Plan B ist der verlässlichere Weg, wenn sich keine überzeugende neue
Algorithmus-Erweiterung abgrenzen lässt. Es werden ein oder zwei
Manipulationsaufgaben in Simulation ausgewählt, geeignete Demonstrationsdaten
genutzt oder selbst gesammelt und eine bestehende Policy (z. B. robomimic-BC,
ACT oder Diffusion Policy) trainiert bzw. feinabgestimmt. Danach wird nicht nur
die nominale Erfolgsrate, sondern die **Generalisierung auf eine gezielt neue
Aufgabenvariation** getestet.

Empfohlene Arbeitsfrage: *Wie stark verbessert Fine-Tuning mit gezielt
variierten Demonstrationen die Generalisierung einer Imitation-Learning-Policy
auf neue Objektposen, Objektinstanzen oder visuelle Bedingungen?*

Eine gute, kleine Versuchskonfiguration ist ein Franka-Panda-Task in robosuite
(z. B. Lift, PickPlace oder Door) mit einer klaren Variation. Nur **eine**
Generalisierungsachse sollte Hauptgegenstand sein, etwa Objektpose. Weitere
Achsen können als Belastungstest dienen. Das verhindert, dass unklare
Fehlerursachen (Perzeption, Kontakt, Dynamik und Tasklogik) vermischt werden.

## Abnahmekriterien und Versuchsdesign

- Trainings- und Testverteilung strikt trennen: Testvariationen dürfen nicht
  unbemerkt schon in den Trainingsdemonstrationen enthalten sein.
- Eine Baseline ohne Fine-Tuning gegen dieselbe Policy nach Fine-Tuning und
  möglichst gegen BC trainiert auf allen verfügbaren Daten vergleichen.
- Erfolgsrate je Variation, Konfidenz-/Streuungsmaß über mehrere Seeds und
  mindestens eine Fehleranalyse berichten.
- Datenherkunft, Anzahl der Trajektorien, Teleoperations-/Oracle-Policy und
  Randomisierungen dokumentieren.
- Bei selbst gesammelten Daten zunächst einen kleinen Task end-to-end validieren,
  bevor ein zweiter Task ergänzt wird.

## Kommentierte Literatur

Einträge **1–10** decken sämtliche im Themenvorschlag erwähnten
wissenschaftlichen Quellen und Projektressourcen ab; **11–14** ergänzen
unmittelbar nützliche Grundlagen für Datenerhebung, Simulation und Evaluation.

### Direkt im Themenvorschlag genannte Quellen

1. **Mandlekar et al. (2021), [What Matters in Learning from Offline Human
   Demonstrations for Robot Manipulation](https://arxiv.org/abs/2108.03298)**
   — Systematische robomimic-Studie zu Offline-Lernen aus menschlichen
   Demonstrationen mit variierender Datenqualität. **Nutzen:** Begründet, warum
   Datenqualität und Evaluation für Plan B zentrale Variablen sind, und liefert
   direkt nutzbare Baselines/Datasets.

2. **Li et al. (2025), [Robotic Manipulation via Imitation Learning:
   Taxonomy, Evolution, Benchmark, and Challenges](https://arxiv.org/abs/2508.17449)**
   — Breiter Überblick über Methoden, Benchmarks und offene
   Generalisierungsprobleme. **Nutzen:** Hilfe bei der Wahl einer messbaren
   Generalisierungsachse; Primärquellen für finale Aussagen nachschlagen.

3. **Wu et al. (2025), [RoboCopilot](https://arxiv.org/abs/2503.07771)** —
   Interaktives menschliches Lehren mit nahtlosem Wechsel zwischen Mensch und
   Policy für bimanuelle Manipulation. **Nutzen:** Option, falls später
   Korrekturdemonstrationen statt reiner Offline-Daten gesammelt werden sollen.

4. **An et al. (2025), [Dexterous Manipulation through Imitation Learning: A
   Survey](https://arxiv.org/abs/2504.03515)** — Survey zu IL für dextere
   Manipulation und ihren Daten-/Kontaktproblemen. **Nutzen:** Kontext bei
   feinmotorischen Tasks, ansonsten nachrangig gegenüber robosuite/robomimic.

5. **Chi et al. (2024), [UMI](https://arxiv.org/abs/2402.10329)** —
   Datenaufnahme- und Policy-Framework für den Transfer von in-the-wild
   Menschendemonstrationen auf Roboter. **Nutzen:** Vorbild für vielfältige
   Demonstrationen und Latenzbehandlung; für Plan B vor allem bei späterem
   Hardwaretransfer relevant.

6. **Zhao et al. (2023), [ACT](https://arxiv.org/abs/2304.13705)** —
   Generative Policy über Aktionssequenzen für präzise, bimanuale Aufgaben.
   **Nutzen:** Sinnvolle Fine-Tuning-Referenz, wenn die Testaufgabe zeitlich
   kohärente oder kontaktreiche Aktionen erfordert.

7. **Chi et al. (2023/2025), [Diffusion Policy](https://arxiv.org/abs/2303.04137)**
   — Konditionierte Diffusion über Aktionssequenzen; besonders geeignet für
   multimodale, hochdimensionale visuomotorische Policies. **Nutzen:** Moderne
   Referenz für die Wahl einer Policy; der Rechen- und Implementierungsaufwand
   muss gegenüber einem BC-Baseline-Projekt abgewogen werden.

8. **Mani et al. (2024), [DiffClone](https://arxiv.org/abs/2401.09243)** —
   Diffusionsgestützte Offline-BC-Variante im TOTO-Benchmark. **Nutzen:**
   Vergleich, ob eine reichhaltigere Policy-Repräsentation bei Offline-Daten
   hilft; keine direkte Generalisierungsevidenz für robosuite ohne Replikation.

9. **Mehta et al. (2025), [Stable-BC](https://arxiv.org/abs/2408.06246)** —
   Stabilitätsbasierte BC-Erweiterung gegen Covariate Shift. **Nutzen:**
   Kontrollbaseline für die Frage, ob ein Robustheitsmechanismus die
   Out-of-Distribution-Testleistung auch ohne zusätzliche Daten verbessert.

10. **Laskey et al. (2017), [DART](https://proceedings.mlr.press/v78/laskey17a.html)**
    — Stört Demonstrationen bewusst, damit Recovery-Verhalten gelernt wird.
    **Nutzen:** Besonders relevant für Plan B: kontrolliert variierte Daten sind
    eine direkte Strategie gegen schlechte Testabdeckung.

### Ergänzte Grundlagen für die Umsetzung

11. **Ross, Gordon & Bagnell (2011), [DAgger](https://proceedings.mlr.press/v15/ross11a.html)**
    — Trainingsdaten werden um Zustände erweitert, die von der aktuellen Policy
    besucht werden, und vom Experten nachannotiert. **Nutzen:** Goldstandard zum
    Verständnis der Verteilungsverschiebung; nützlich, falls ein Simulations-Oracle
    für iterative Korrekturen verfügbar ist.

12. **Zhu et al. (2020), [robosuite](https://arxiv.org/abs/2009.12293)** —
    Modularer MuJoCo-Simulator und Manipulationsbenchmark. **Nutzen:** Liefert
    die kontrollierbare Umgebung für die train/test-Trennung und reproduzierbare
    Variationen von Objektlage, Szene und Robotik.

13. **Mandlekar et al. (2020), [Human-in-the-Loop Imitation Learning using
    Remote Teleoperation](https://arxiv.org/abs/2012.06733)** — Interventionsdaten
    von menschlichen Operatoren zur Lösung präziser Bottleneck-Situationen.
    **Nutzen:** Konkrete Referenz für eine Erweiterung von Plan B um selektive
    Korrekturen, statt viele vollständige neue Trajektorien aufzunehmen.

14. **robomimic, [Projektseite und Dokumentation](https://robomimic.github.io/)**
    — Implementierungen, Datensätze und Konfigurationsbeispiele. **Nutzen:**
    Praktischer Einstieg; die Studie in Eintrag 1 bleibt die wissenschaftliche
    Hauptzitation.

## Nichtwissenschaftliche Hilfsmittel aus dem Themenvorschlag

[Connected Papers](https://www.connectedpapers.com/),
[ResearchRabbit](https://www.researchrabbit.ai/), [Zotero](https://www.zotero.org/)
und [Obsidian](https://obsidian.md/) unterstützen Suche, Verwaltung und Notizen,
sind jedoch keine Fachliteratur. Für die Ausarbeitung werden die verlinkten
Originalartikel zitiert.
