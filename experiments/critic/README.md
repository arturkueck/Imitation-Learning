# Critic und Aktionsbewertung

**Basiscode:** [base/run.py](base/run.py) und [zugehoerige Module](base/README.md).
Dieser editierbare Stand ist der Einstieg fuer weitere Codearbeit; die datierten Versuche bleiben als Historie erhalten.

Critic-Vortraining, Validierung und Prüfung von Aktionen bzw. Segmenten.

- [critic_warmstart_20261104](critic_warmstart_20261104/README.md): Critic vorwärmen, Actor durch RL verbessern.
- [il_action_feasibility_20261107](il_action_feasibility_20261107/README.md): Nachtversuch zur Machbarkeit critic-gestützter Imitation.
- Der Versuch zum Dreierturm untersucht den Transfer von Zweier-BC mit IL-informiertem Critic. N1-1 bis N1-6 sind abgeschlossen. Die Kalibrierung ergab 103 von 300 erfolgreichen Dreiertürmen auf 100 gemeinsamen Familien, und die Transportgrenzen sowie die Zuordnung der 375 Validierungs- und Testfamilien sind eingefroren. Das Pilotprotokoll ist seit dem 19.11.2026 freigegeben. N2-1 ist abgeschlossen. Auf 300 gemeinsamen Critic-Datenfamilien liegen 900/900 Episoden der drei A-Parents mit allen Ausgängen vor, erhoben ohne Optimizerupdates. Davon gelangen 325, je Parent 125, 92 und 108 von 300. Alle Fehlschläge endeten am Horizont. N2-2 läuft seit dem 19.11.2026 um 12:29 Uhr unter Supervisor. Je Parent wird ein Critic mit 20.000 Updates vortrainiert, anschließend folgen 450 A-Rollouts auf der Validierung und die Prüfung nach den vorab festgelegten Akzeptanzkriterien. Ein Ergebnis liegt noch nicht vor. [Critic-Vortraining N2-2](three_cube_transfer_v1/CRITIC_VALIDATION.md) · [Datenvertrag N2-1](three_cube_transfer_v1/CRITIC_DATA.md) · [Pilotprotokoll](three_cube_transfer_v1/PROTOCOL.md) · [Kalibrierung](three_cube_transfer_v1/CALIBRATION.md) · [Nachtplan](three_cube_transfer_v1/NACHTPLAN.md) · [Aufgabenstatus](three_cube_transfer_v1/STATUS.md) · [Nachtbericht](three_cube_transfer_v1/nights/NACHT_1_20261118.md)

Datierte Ordner sind getrennte Versuchsfamilien. Die jeweiligen READMEs verweisen auf Protokolle, Ergebnisse und bekannte Grenzen.

[Alle Themen](../README.md).
