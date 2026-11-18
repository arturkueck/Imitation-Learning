# Technische Vorbereitung und Prüfungen

Der wissenschaftliche Lauf ist noch nicht gestartet. `ready_001` enthält
den eingefrorenen Plan für 300 Episoden; Start nur nach Freigabe.

## Bestandene Prüfungen

- Vier Unit-Tests: Begrenzung auf die richtige zweite Phase ohne Retreat;
  korrekte Nenner bei nicht erreichten Phasen; Ablehnung einer abweichenden
  Vorgeschichte; hartes Beenden eines eigenen Worker-Prozessbaums einschließlich
  Windows-Venv-Unterprozess.
- `smoke_003`: COMPLETE, drei technische Szenengruppen und fünf Arme,
  insgesamt 15 Simulatorepisoden. Ein Modell; bekannte Szenen 2026113000,
  2026113002 und 2026113003. Erfolgs-, Fehlgriff- und früher Abbruchfall.
- Bei jedem Arm stimmen Zustand und vollständige Historie bis zum ersten
  jeweiligen Eingriff mit der BC-Kontrolle überein. Fehlende Exposition bleibt
  erfolglos im Nenner statt ausgesondert zu werden.
- BC-Kontrolle und vollständige Expertenhilfe reproduzieren die historischen
  Ergebnisse einschließlich Dauer, Abschlusszustand und Lift-Griffmessung.
- Die im Smoke-Plan erfassten Eingangshashes wurden vor und nach Ausführung
  geprüft. Originalmodelle wurden nicht verändert. Supervisor regulär beendet;
  Schlafverhinderung wieder freigegeben.

## Während der Vorbereitung behobenes Problem

Die Vorbereitungen `smoke_001` und `smoke_002` brachen vor Simulationsbeginn
ab: Eine Bibliothek führt für dynamisch generierten Code einen synthetischen
`__file__`-Namen `_classes.py`. Die Provenienzerfassung versuchte diese nicht
existierende Datei zu lesen. Sie berücksichtigt jetzt nur tatsächlich
existierende Quelldateien; installierte Bibliotheksversionen werden separat
im Umgebungsmanifest erfasst. Keine wissenschaftlichen Kriterien geändert.
Die beiden unvollständigen Vorbereitungen bleiben erhalten.

Keine Smoke-Erfolgsquote wird als neues wissenschaftliches Ergebnis berichtet.
Ein vollständiger Vergleich umfasst drei Modellseeds und 20 gemeinsame
Entwicklungsszenen. Frische Bestätigung und BC-Training sind separate spätere
Untersuchungen.
