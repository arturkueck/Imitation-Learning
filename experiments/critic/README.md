# Critic und Aktionsbewertung

**Basiscode:** [base/run.py](base/run.py) und [zugehoerige Module](base/README.md).
Dieser editierbare Stand ist der Einstieg fuer weitere Codearbeit; die datierten Versuche bleiben als Historie erhalten.

Critic-Vortraining, Validierung und Prüfung von Aktionen bzw. Segmenten.

- [critic_warmstart_20261104](critic_warmstart_20261104/README.md): Critic vorwärmen, Actor durch RL verbessern.
- [il_action_feasibility_20261107](il_action_feasibility_20261107/README.md): Nachtversuch zur Machbarkeit critic-gestützter Imitation.
- Der Versuch zum Dreierturm untersucht den Transfer von Zweier-BC mit IL-informiertem Critic. N1-1 bis N1-3 sind abgeschlossen. Sieben disjunkte Szenenbereiche sind für 875 Familien geplant. Die Geometriemerkmale der Starts sind implementiert und getestet. Die Zuordnung der schwierigen Familien folgt nach der Kalibrierung. [Nachtplan](three_cube_transfer_v1/NACHTPLAN.md) · [Seedinventar](three_cube_transfer_v1/used_scene_seeds.json) · [Splitmanifest](three_cube_transfer_v1/splits.json) · [Merkmale difficulty_v1](three_cube_transfer_v1/difficulty.py)

Datierte Ordner sind getrennte Versuchsfamilien. Die jeweiligen READMEs verweisen auf Protokolle, Ergebnisse und bekannte Grenzen.

[Alle Themen](../README.md).
