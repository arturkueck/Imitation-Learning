# Imitation Learning

Forschungsprojekt zu Behavioural Cloning, Selbstimitation und visueller Wahrnehmung für simulierte Manipulationsaufgaben.

## Orientierung

| Bereich | Inhalt |
|---|---|
| [Experimente](experiments/README.md) | Versuchsfamilien, Protokolle, Ergebnisse und historische Quellstände |
| [Implementierung](praxis/README.md) | Python-Setup und Reproduktion des Lift-Vergleichs |
| [Quellcode](praxis/src/README.md) | BC-Erweiterungen, Simulationsaufgaben und Kameraplanung |
| [Literatur](literature/README.md) | Papers, belegte Aussagen und Methodenvergleiche |
| [Lernmaterial](lernmaterial/README.md) | Erklärungen, Übungen und interaktive Beispiele |
| [Ausarbeitung](latex/README.md) | Entwürfe, Projektvorschläge und Zeitplan |
| [Research Atlas](sites/README.md) | Lokale Projektwebsite und Visualisierungen |
| [Monitoring](monitor/README.md) | Laufregister und Dashboard-Daten |
| [Exporte](output/README.md) | PDFs und Besprechungsmedien |

## Wichtige Einstiege

- [Projektvorschlag: von Zweier-Demonstrationen zum Dreierturm](latex/projektarbeit_proposal/v2/README.md) mit Critic-Vortraining und separatem Gantt-Zeitplan.
- [Critic und Selbstimitation](experiments/critic/critic_warmstart_20261104/README.md).
- [Aktions- und Abschnittsprüfung](experiments/critic/il_action_feasibility_20261107/README.md).
- [Abgeschlossene BC-Session vom 04.10.2026](experiments/stack_diagnostics/lift_contraction_validity_20261004/supervised_6h_20261004_0904/README.md).
- [Datierter Forschungsplan](FORSCHUNGSPLAN.md) und [Plan-A-Ergebnisse](latex/plan_a/RESULTS.md).

Die verlinkten Berichte beschreiben ihren jeweiligen Versuchsstand. Eine validierte Bewertung, eine bessere Policy und erfolgreicher Aufgabenvollzug sind getrennte Aussagen.

## Lokal ansehen

```powershell
npm start
```

Öffnet den lokalen Research Atlas unter `http://127.0.0.1:4173`. Für das Training die separate [Python-Setupanleitung](praxis/README.md) verwenden.

Datensätze, Checkpoints und große Rohartefakte bleiben teilweise lokal. Welche Dateien versioniert werden und welche für eine Reproduktion zusätzlich nötig sind, steht in [GIT_ARTIFACTS.md](GIT_ARTIFACTS.md).
