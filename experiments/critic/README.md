# Critic und Aktionsbewertung

**Basiscode:** [base/run.py](base/run.py) und [zugehoerige Module](base/README.md).
Dieser editierbare Stand ist der Einstieg fuer weitere Codearbeit; die datierten Versuche bleiben als Historie erhalten.

Critic-Vortraining, Validierung und Prüfung von Aktionen bzw. Segmenten.

- [critic_warmstart_20261104](critic_warmstart_20261104/README.md): Critic vorwärmen, Actor durch RL verbessern.
- [il_action_feasibility_20261107](il_action_feasibility_20261107/README.md): Nachtversuch zur Machbarkeit critic-gestützter Imitation.
- Der Versuch zum Dreierturm untersucht den Transfer von Zweier-BC mit IL-informiertem Critic. N1-1 bis N1-6 sind abgeschlossen. Die Kalibrierung ergab 103 von 300 erfolgreichen Dreiertürmen auf 100 gemeinsamen Familien, und die Transportgrenzen sowie die Zuordnung der 375 Validierungs- und Testfamilien sind eingefroren. Das Pilotprotokoll ist seit dem 19.11.2026 freigegeben. N2-1 ist abgeschlossen. Auf 300 gemeinsamen Critic-Datenfamilien liegen 900/900 Episoden der drei A-Parents mit allen Ausgängen vor, erhoben ohne Optimizerupdates. Davon gelangen 325, je Parent 125, 92 und 108 von 300. Alle Fehlschläge endeten am Horizont. N2-2 ist abgeschlossen. Je Parent wurde ein Critic mit 20.000 Updates vortrainiert und auf 450 A-Rollouts der Validierung geprüft. Alle drei Critics erfüllen auf der regulären Validierung die vorab festgelegten Akzeptanzkriterien, mit gewichteter AUC innerhalb der Phasenpunkte von 0,82 bis 0,89, kleinerem Fehler als die Phasen-Baseline und ECE von 0,033 bis 0,040. Die schwierige Validierung wird getrennt berichtet. Dort verfehlt Parent 3 die Bedingung „besser als Phase“, was nach Protokoll nicht entscheidet. N2-3 läuft seit dem 19.11.2026 um 13:12 Uhr unter Supervisor. Der technische Smoke prüft die Bindung an BC in den Stufen δ_max 0,05, 0,10 und 0,20 mit beiden Critic-Varianten und allen drei Parents, ohne Wirksamkeitsaussage. [Actor-Critic-Smoke N2-3](three_cube_transfer_v1/AC_SMOKE.md) · [Critic-Vortraining N2-2](three_cube_transfer_v1/CRITIC_VALIDATION.md) · [Datenvertrag N2-1](three_cube_transfer_v1/CRITIC_DATA.md) · [Pilotprotokoll](three_cube_transfer_v1/PROTOCOL.md) · [Kalibrierung](three_cube_transfer_v1/CALIBRATION.md) · [Nachtplan](three_cube_transfer_v1/NACHTPLAN.md) · [Aufgabenstatus](three_cube_transfer_v1/STATUS.md) · [Nachtbericht](three_cube_transfer_v1/nights/NACHT_1_20261118.md)

Datierte Ordner sind getrennte Versuchsfamilien. Die jeweiligen READMEs verweisen auf Protokolle, Ergebnisse und bekannte Grenzen.

[Alle Themen](../README.md).
