# Experimente nach Thema

Die Versuchsfamilien sind nach Forschungsfrage gegliedert. Die bisherigen Namen und Datumsangaben bleiben innerhalb der Themen erhalten.

| Thema | Inhalt |
|---|---|
| [Baselines und Aufgaben](baselines/README.md) | Grundlegende BC-/Diffusionsvergleiche, Square und zusätzliche Simulationsaufgaben. |
| [Stack-Diagnosen](stack_diagnostics/README.md) | Analysen von Transport, Phasenwechseln, Dynamikannahmen, Normalisierung und Robustheit. |
| [Selbstimitation und Curriculum](self_imitation/README.md) | Datensammlung aus eigenen Versuchen, Abschnittslernen, Curriculum und Übergangsqualität. |
| [BC-Curriculum und Freigabephase](curriculum/README.md) | Neue A/B/C-Untersuchung, geprüfte Zeitkorrektur, Abschlussdiagnosen und versionierte fortsetzbare Modelle. |
| [Critic und Aktionsbewertung](critic/README.md) | Critic-Vortraining, Validierung und Prüfung von Aktionen bzw. Segmenten. |
| [Visuelle Wahrnehmung](vision/README.md) | RGB-Wahrnehmung, zusätzliche Ansichten, geometrische Verfeinerung und Qualitätsauswahl. |
| [Kameraplanung](camera_planning/README.md) | Geometrische Planung und Prüfung von Handkameraansichten. |

## Basiscode je Thema

Die bisher eingerichteten `base/`-Ordner enthalten echte Skriptkopien, ein dokumentiertes Basisskript und ein Herkunftsmanifest. Diese Kopien dienen der weiteren Codearbeit; sie ersetzen keine eingefrorenen Versuchsversionen. Der neue BC-Curriculum-Bereich verwendet geprüfte gemeinsame Policy-Adapter und einen Modellkatalog; seine Abhängigkeiten stehen in `curriculum/README.md`.

## Einen Versuch nachvollziehen

README und Ergebnisbericht lesen, danach Protokoll, Konfiguration und Manifeste für Splits, Seeds und Budget prüfen. Datensätze und Checkpoints sind teilweise nur lokal vorhanden. Ein gespeicherter Status ist kein Nachweis eines aktuell laufenden Prozesses.

Bewertungsqualität, geometrische Genauigkeit und physischer Aufgabenerfolg sind getrennte Aussagen. Abgebrochene Läufe und technische Vorbereitungen nicht als abgeschlossene Evaluation behandeln.

## Umzug vom 10.11.2026

Die Zuordnung alter zu neuen Pfaden steht in [layout.json](layout.json). Aktueller Code, Laufregister und Arbeitsdokumentation verwenden die neue Struktur. Historische Run-Artefakte, eingefrorene Quellen und deren Manifeste behalten ihre ursprünglichen Bytes und gegebenenfalls alte Pfade. Exakte historische Reproduktionen deshalb im zugehörigen Git-Stand vor dem Umzug durchführen; bestehende versiegelte Läufe nicht mit verändertem Arbeitscode fortsetzen. Neue Versuche benötigen neue Verzeichnisse und neue Quellcode-Siegel.

[Artefaktregeln](../GIT_ARTIFACTS.md) · [Robustheitsprotokoll](ROBUSTNESS.md) · [Projektübersicht](../README.md).
