# Vision V4: Seitenansichten-Pilot

Abgeschlossen am03.11.2026 um05:05 Uhr Berlin. A/B-Vergleich über drei Seeds, jeweils zehn Epochen und420 Optimizer-Updates: A trainiert bisherige Blickrichtungen, B zusätzliche Seitenansichten.1.000 neue Trainingsfamilien,333 historische Trainingsfamilien als festes Replay und256 strikt getrennte Validierungsfamilien. Kein Endtest zur Modellauswahl.

Das Seitenansicht-Training verbessert die Verarbeitung seitlicher Zusatzbilder gegenüber dem Kontrollarm: Szenenfehler31,43 →13,35 mm-äquivalent,57,5 % niedriger, Verbesserung in allen drei Seeds. Auf bisherigen Zusatzansichten steigt der Fehler nur leicht von12,22 auf12,59. Der ausgewogene Validierungsloss fällt von0,2255 (A) auf0,1764 (B).

**Die eigentliche aktive Nachkorrektur ist noch nicht gelöst:** Innerhalb B steigt der Szenenfehler durch die Seitenaufnahme von11,95 auf13,35 mm-äquivalent (+11,7 %). Zusätzliche Bilder werden besser verarbeitet als vor dem spezifischen Training, verbessern aber die eigene erste Schätzung im Mittel noch nicht. Aufnahmebedarf, Bildfusion und die Ablehnung schädlicher Updates bleiben nächste Untersuchungen.

Der Szenenfehler bewertet Objektzentren, Eckengeometrie sowie fehlende/zusätzliche Objekte und ist kein reiner Positions- oder Roboter-Platzierfehler. Ergebnisse stammen aus Pilotvalidierung in der Simulation. Kein Nachweis für reale visuelle Kollisionsfreiheit, beliebige unbekannte Formen oder eine fertige aktive Aufnahmepolitik.

Darzustellen: loss.png mit Train-/Validation-/Train-Probe-Loss für alle sechs Modelle, view_metrics.png sowie ausgewählte cyan/orange/grüne Überlagerungen und ihre Eingabebilder aus geometry/index.json. Checkpoints und Hashes sind geprüft; das B-Ensemble ist für weitere getrennte Untersuchungen eingefroren. Dieser Entwurf wurde nicht online veröffentlicht.
