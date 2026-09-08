# Plan A — Algorithmische Erweiterung von Behavioral Cloning in robomimic

## Kurzübersicht

Ziel ist es, zunächst die in **robomimic** vorhandenen Offline-IL-Verfahren und
Datensätze nachvollziehbar zu reproduzieren. Anschließend wird eine klar
abgegrenzte Erweiterung von Behavioral Cloning (BC) implementiert und gegen die
robomimic-Baselines getestet. Der aussichtsreichste, gut beherrschbare Fokus ist
die **Robustheit gegen Covariate Shift**: BC wird auf Demonstrationszuständen
trainiert, besucht bei der Ausführung aber auch unbekannte Zustände; kleine
Fehler können sich dadurch aufschaukeln.

Empfohlene Arbeitsfrage: *Verbessert eine stabilitäts- oder
störungsrobuste BC-Erweiterung gegenüber robomimic-BC die Erfolgsrate und
Robustheit auf manipulativem Benchmark-Task bei gleicher Demonstrationsmenge?*

**Praktisch sinnvolle Reihenfolge:** (1) robomimic-BC auf einem kleinen
Franka-/robosuite-Task reproduzieren, (2) die Erweiterung als eigene Policy bzw.
Loss-Komponente integrieren, (3) BC als Hauptbaseline und optional BC-RNN/BCQ
als weitere Baselines vergleichen, (4) mit mehreren Seeds Erfolgsrate,
Störungsrobustheit und Lernaufwand berichten. Diffusion Policy und ACT sind
wertvolle Vergleichs- bzw. Designreferenzen, aber als vollständige
Reimplementierung für eine Projektarbeit deutlich risikoreicher.

## Abnahmekriterien und Versuchsdesign

- Eine feste Umgebung, Beobachtungsmodalität, Demonstrationsmenge und ein
  transparentes Trainingsbudget definieren.
- BC unter identischen Bedingungen reproduzieren; mindestens drei Seeds und
  Erfolgsrate mit Streuung berichten.
- Die Erweiterung nur in einem Aspekt ändern und eine Ablation ohne diesen
  Bestandteil ausführen.
- Robustheit getrennt auf nominalen und gestörten Startzuständen/Objektlagen
  auswerten. Training Loss allein ist kein ausreichendes Ergebnis.
- Konfigurationen, Seeds und Checkpoints versionierbar dokumentieren.

## Kommentierte Literatur

Die Einträge **1–10** sind sämtliche in dem Themenvorschlag genannten
wissenschaftlichen Dokumente bzw. Projektquellen. Die Einträge **11–13** wurden
für ein umsetzbares, reproduzierbares Experiment ergänzt.

### Direkt im Themenvorschlag genannte Quellen

1. **Mandlekar et al. (2021), [What Matters in Learning from Offline Human
   Demonstrations for Robot Manipulation](https://arxiv.org/abs/2108.03298)**
   — Die robomimic-Studie vergleicht sechs Offline-Lernverfahren auf simulierten
   und realen Manipulationsaufgaben sowie unterschiedlich guten Demonstrationen.
   **Nutzen:** Primärreferenz für Framework, Datasets, Baselines und die Warnung,
   dass Designentscheidungen, Datenqualität und der gewählte Checkpoint die
   Resultate stark beeinflussen.

2. **Li et al. (2025), [Robotic Manipulation via Imitation Learning:
   Taxonomy, Evolution, Benchmark, and Challenges](https://arxiv.org/abs/2508.17449)**
   — Aktuelle Übersicht zu Methodenklassen, Benchmarks, Stärken und offenen
   Problemen der IL-Manipulation. **Nutzen:** Zur Einordnung der eigenen Methode
   und zum Ableiten eines präzisen Forschungs-Gaps. Als Survey dient sie zur
   Orientierung; zentrale Behauptungen sollten zusätzlich mit Primärquellen
   belegt werden.

3. **Wu et al. (2025), [RoboCopilot: Human-in-the-loop Interactive Imitation
   Learning for Robot Manipulation](https://arxiv.org/abs/2503.07771)**
   — Beschreibt ein System, das bei bimanueller Manipulation zwischen Mensch und
   Policy umschaltet und Korrekturen für interaktives Lernen sammelt. **Nutzen:**
   Kontrast zu reinem Offline-BC und mögliche spätere Erweiterung, falls
   Interventionsdaten verfügbar werden.

4. **An et al. (2025), [Dexterous Manipulation through Imitation Learning: A
   Survey](https://arxiv.org/abs/2504.03515)** — Übersicht speziell für
   mehrfingrige/dextere Manipulation, inklusive Daten-, Kontakt- und
   Generalisierungsproblemen. **Nutzen:** Hintergrund, falls der Task hohe
   Präzision oder komplexe Kontakte erfordert; für einen Franka-Greifer nur
   ergänzende Kontextquelle.

5. **Chi et al. (2024), [Universal Manipulation Interface (UMI)](https://arxiv.org/abs/2402.10329)**
   — UMI sammelt portable menschliche Demonstrationen mit Handgripper und nutzt
   eine latenzangepasste Policy-Schnittstelle sowie relative Trajektorien.
   **Nutzen:** Referenz für künftige Datenerhebung und Transfer, nicht die
   naheliegendste Algorithmus-Baseline für das reine Offline-Projekt.

6. **Zhao et al. (2023), [Learning Fine-Grained Bimanual Manipulation with
   Low-Cost Hardware (ACT)](https://arxiv.org/abs/2304.13705)** — Führt Action
   Chunking mit Transformers ein: die Policy erzeugt Sequenzen statt einzelner
   Aktionen. **Nutzen:** Vergleichspunkt dafür, wie zeitliche Kohärenz und
   Fehlerakkumulation adressiert werden können; hoher Integrationsaufwand in
   robomimic.

7. **Chi et al. (2023/2025), [Diffusion Policy: Visuomotor Policy Learning via
   Action Diffusion](https://arxiv.org/abs/2303.04137)** — Modelliert
   Aktionssequenzen als bedingten Denoising-Prozess und adressiert multimodale
   Aktionen sowie hochdimensionale Steuerung. **Nutzen:** Starke moderne
   Vergleichsreferenz; hilfreich für eine spätere Diffusionsvariante, aber durch
   iterative Inferenz und Architekturaufwand kein Minimalumfang.

8. **Mani et al. (2024), [DiffClone: Enhanced Behaviour Cloning in Robotics
   with Diffusion-Driven Policy Learning](https://arxiv.org/abs/2401.09243)**
   — Offline-BC-Variante mit konditionierter Diffusionspolicy, evaluiert im
   TOTO-Benchmark. **Nutzen:** Direkter thematischer Bezug zur Idee „BC mit
   Diffusion verbessern“; sorgfältig prüfen, ob Benchmark, Daten und
   Implementierung mit robomimic vergleichbar sind.

9. **Mehta et al. (2025), [Stable-BC: Controlling Covariate Shift with Stable
   Behavior Cloning](https://arxiv.org/abs/2408.06246)** — Leitet modellbasierte
   und modellfreie Stabilitätsbedingungen für BC aus Fehlerdynamiken ab und
   evaluiert eine robuste Erweiterung in Simulation und auf einem Roboter.
   **Nutzen:** Beste Kandidatin für eine realistische Erweiterung, da Problem,
   Mechanismus und Messgrößen exakt zu Plan A passen.

10. **Laskey et al. (2017), [DART: Noise Injection for Robust Imitation
    Learning](https://proceedings.mlr.press/v78/laskey17a.html)** — Fügt bei der
    Demonstration gezielt Störungen ein, damit Recovery-Zustände im Offline-Datensatz
    enthalten sind. **Nutzen:** Alternative bzw. ergänzende Robustheitsbaseline;
    macht klar, dass bessere Datenabdeckung eine andere Lösung als ein neuer
    Policy-Loss ist.

### Ergänzte Grundlagen für die Umsetzung

11. **Ross, Gordon & Bagnell (2011), [DAgger](https://proceedings.mlr.press/v15/ross11a.html)**
    — Aggregiert iterativ Zustände der aktuellen Policy mit Expertenaktionen und
    reduziert so die Verteilungsverschiebung. **Nutzen:** Theoretische Referenz
    für Covariate Shift und eine obere, interaktive Vergleichslinie; benötigt
    jedoch einen Experten/Oracle und geht damit über reines Offline-Lernen hinaus.

12. **Zhu et al. (2020), [robosuite: A Modular Simulation Framework and
    Benchmark for Robot Learning](https://arxiv.org/abs/2009.12293)** —
    MuJoCo-basierter, modularer Manipulationssimulator mit Benchmark-Tasks.
    **Nutzen:** Geeignete Simulationsbasis, eng mit dem robomimic-Ökosystem
    verbunden und hilfreich für reproduzierbare Störungstests.

13. **robomimic, [offizielle Projektseite und Dokumentation](https://robomimic.github.io/)**
    — Code, Datensätze, Konfigurationen und Dokumentation zum Framework.
    **Nutzen:** Praktische Startquelle; in der Arbeit die Studie aus Eintrag 1
    zitieren, die Dokumentation für konkrete Versions- und Nutzungsangaben.

## Nichtwissenschaftliche Hilfsmittel aus dem Themenvorschlag

[Connected Papers](https://www.connectedpapers.com/),
[ResearchRabbit](https://www.researchrabbit.ai/), [Zotero](https://www.zotero.org/)
und [Obsidian](https://obsidian.md/) sind Recherche- bzw. Organisationswerkzeuge,
keine zitierbaren Fachquellen. Sie können zum Literaturmanagement genutzt werden;
in die wissenschaftliche Bibliographie gehören die Originalpublikationen.
