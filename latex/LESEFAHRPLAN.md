# Lesefahrplan: alle 11 Papers

Stand: 9. Oktober 2026. Reihenfolge für dein BC-/Robustheitsprojekt.
**Alle Seitenangaben zählen ab der ersten PDF-Seite im Viewer**, einschließlich
Anhängen. Bei DAgger entspricht PDF-Seite 2 beispielsweise der gedruckten Seite 628.
Die Angaben gelten für die hier abgelegten Fassungen.

Lies bei jedem Paper zuerst Abstract und Fazit, dann die markierten Seiten.
Bei den langen Surveys genügt für den ersten Durchgang eine gezielte Lektüre;
Literaturverzeichnisse und vollständige Beweise kannst du anschließend nachschlagen.
Die elf PDFs umfassen zusammen 194 Seiten inklusive Referenzen und Anhängen.

| Reihenfolge / Datei | Besonders wichtige PDF-Seiten | Was du danach erklären und für dein Projekt beurteilen können solltest |
| --- | --- | --- |
| **1. [Robotic Manipulation: Taxonomy, Evolution, Benchmark, and Challenges](<Robotic Manipulation via Imitation Learning - Taxonomy, Evolution, Benchmark, and Challenges.pdf>)** (20 S.) | **2–4:** Taxonomie und Aktionsgenerierung. **12–14:** Benchmarks/Metriken. **16:** offene Probleme. | Deine Methode nach Eingaben, Aktionsmodell, Datenbedarf und Ziel einordnen. Generalisierung ist eine konkrete Testvariation; Erfolgsraten aus verschiedenen Benchmarks sind kein fairer Direktvergleich. Der Survey orientiert dich, zentrale Belege gehören aus den Originalpapers übernommen. |
| **2. [DAgger](<A Reduction of Imitation Learning and Structured Prediction to No-Regret Online Learning - DAgger.pdf>)** (9 S.) | **2:** Fehlerakkumulation, Theorem 2.1. **3–4:** Dataset Aggregation, Algorithmus 3.1 und Voraussetzungen. | Warum geringer Fehler auf Expertenzuständen keinen guten Rollout garantiert: Die Policy verändert ihre eigene Zustandsverteilung. DAgger sammelt Expertenaktionen auf besuchten Zuständen. Für deine Umsetzung brauchst du einen Experten/Oracle; die theoretischen Schranken gelten unter den angegebenen Annahmen. |
| **3. [DART](<DART - Noise Injection for Robust Imitation Learning.pdf>)** (14 S.) | **4–6:** Störungsmodell und Algorithmus 1. **7–8:** Simulation und Robotergreifen. | Warum gestörte Demonstrationen echte Recovery-Handlungen enthalten können. Entscheidend sind neue Zustände mit gültigen Expertenaktionen und ein passendes Störungsniveau. Das ist von nachträglichem Rauschen auf gespeicherten Beobachtungen bei unveränderten Aktionslabels zu unterscheiden. |
| **4. [Stable-BC](<Stable-BC - Controlling Covariate Shift with Stable Behavior Cloning.pdf>)** (8 S.) | **3–5:** Fehlerdynamik, Gleichungen 6, 7 und **11**, Algorithmus 1. **7–8:** Air Hockey und Fazit. | Den Unterschied zwischen lokaler Stabilität bei bekanntem Umgebungsmodell und dem schwächeren modellfreien Fall erklären. Auch Letzterer benötigt Roboterdynamik und Annahmen über Umgebungsabweichungen. Für deine Kontraktionsidee musst du Dynamik, Zustandsaufteilung und Gültigkeitsbereich prüfen; ähnliche Loss-Terme übernehmen nicht automatisch die Paper-Garantien. |
| **5. [ACT / ALOHA](<Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware - ACT.pdf>)** (19 S.) | **4–6:** Action Chunking, Temporal Ensembling, CVAE und Algorithmen. **9–11:** Policy-Ergebnisse, Ablationen, Grenzen. | Warum Aktionssequenzen und überlappende Vorhersagen zeitliche Kohärenz verbessern können; lange offene Sequenzen begrenzen zugleich die Reaktivität. Prüfe, welcher Bestandteil die Verbesserung erklärt. **Tabelle I auf S. 4 zeigt menschliche Teleoperation**, nicht autonome ACT-Erfolge. |
| **6. [Diffusion Policy](<Diffusion Policy - Visuomotor Policy Learning via Action Diffusion.pdf>)** (16 S.) | **2–5:** Denoising, Abbildung 3, Horizonte und Designentscheidungen. **6–7:** Benchmarks/Evaluationsprotokoll. **11:** Grenzen. | Wie eine bedingte Diffusionspolicy multimodale Aktionssequenzen erzeugt und mit Receding Horizon ausführt. Beobachtungs-, Vorhersage- und Ausführungshorizont unterscheiden. Für einen fairen Vergleich auch Aktionsraum, Checkpointauswahl, Trainingsbudget und Inferenzlatenz beachten. |
| **7. [Diffusion Model-Augmented Behavioral Cloning](<Diffusion Model-Augmented Behavioral Cloning.pdf>)** (25 S.) | **4–5:** Abbildung 2, Zusatzloss und Gleichung 6. **7–8:** Resultate/Generalisierung. Optional **12–13:** Algorithmus/Ablation. | DBC von Diffusion Policy unterscheiden: Ein zusätzliches Modell der gemeinsamen Zustands-Aktions-Verteilung liefert ein Trainingssignal für die BC-Policy. Beurteile, ob dieses Modell und sein Loss einen messbaren Zusatznutzen gegenüber BC bringen; seine Experimente ersetzen keinen eigenen robomimic-Vergleich. |
| **8. [DiffClone](<DiffClone - Enhanced Behaviour Cloning in Robotics with Diffusion-Driven Policy Learning.pdf>)** (13 S.) | **5–7:** Pipeline/Algorithmus. **8–9:** Architekturwahl, Hyperparameter und Tabellen **1–3**. | Einen Simulationsvorteil von erfolgreichem Hardwaretransfer unterscheiden. Hier sind die realen Pouring-/Scooping-Ergebnisse schwächer als die TOTO-Baseline. Daraus folgt eine konkrete Prüfaufgabe für dein Projekt: Latenz, Subsampling und Horizonte kontrollieren; „Diffusion ist besser“ wäre zu pauschal. |
| **9. [RoboCopilot](<RoboCopilot - Human-in-the-Loop Interactive Imitation Learning for Robot Manipulation.pdf>)** (20 S.) | **3–5:** Lernschleife, Kontrollwechsel und Teleoperation. **6–9:** Experimente; besonders Tabelle 3 und Grenzen auf **9**. | Wie menschliche Interventionen gezielt neue Korrekturdaten erzeugen und die Policy laufend verbessern. Das benötigt einen Operator und ein geeignetes Kontrollinterface. Vergleiche neben Erfolg auch Interventionsaufwand und Datenbudget; interaktives Lernen hat andere Ressourcen als dein reiner Offline-Versuch. |
| **10. [Universal Manipulation Interface / UMI](<Universal Manipulation Interface - In-The-Wild Robot Teaching Without In-The-Wild Robots.pdf>)** (18 S.) | **4–6:** Datenerhebung, relative Repräsentationen und Latenzkompensation. **10–11:** Generalisierung/Grenzen. Optional **15–17:** Protokolle. | Warum Demonstrations- und Roboterschnittstelle zusammenpassen müssen: Synchronisation, Latenz, relative Posen und kinematische Machbarkeit beeinflussen die Übertragung. UMI verbindet Datenerhebung mit Policy-Ausführung; beurteile, welche Teile bei deinen bestehenden Offline-Daten überhaupt anwendbar sind. |
| **11. [Dexterous Manipulation through Imitation Learning: A Survey](<Dexterous Manipulation through Imitation Learning - A Survey.pdf>)** (32 S.) | **5–6:** BC und Methodenvergleich, Tabelle I. **11–15:** Greifer/Sensorik. **19–24:** Benchmarks und Forschungsprobleme. | Warum Endeffektor, Kontakte, Sensorik und Datenabdeckung die Schwierigkeit verändern. Ordne deinen Panda-Zweifingergreifer gegenüber mehrfingriger Manipulation ein. Nutze den Survey für Kontext und Quellen; Resultate dexterer Hände lassen sich nicht unmittelbar auf Lift übertragen. |

## Drei Notizen nach jeder Datei

1. **Mechanismus:** Was wird tatsächlich verändert: Daten, Modell/Loss oder Steuerung?
2. **Evidenz:** Welche Baseline, Datenmenge und Testverteilung stützen die Aussage?
3. **Transfer:** Was übernehme ich für mein Projekt, und welche Voraussetzung fehlt noch?

**Ziel nach der Lektüre:** Datenabdeckung (DAgger/DART/RoboCopilot), lokale
Stabilitätsbedingungen (Stable-BC), Aktionsmodellierung (ACT/Diffusion Policy/
DiffClone), zusätzliches Trainingssignal (DBC) und Datenschnittstelle (UMI)
auseinanderhalten. Daraus eine konkrete Hypothese mit passender Kontrollgruppe
ableiten, statt Erfolgszahlen verschiedener Papers direkt gegeneinander zu stellen.

Die drei ergänzten PDFs wurden unverändert aus `literature/_research/` kopiert.
Die dortigen Lesefassungen bleiben als Ziele vorhandener Literaturverweise erhalten.
