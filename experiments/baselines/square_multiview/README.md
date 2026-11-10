# Vier-Perspektiven-Videos

Neue Aufnahmen enthalten standardmaessig zwei Sekunden echten Simulationsnachlauf.
Die Policy steuert weiter; Messwerte enden vor diesem Nachlauf.
`--post-roll-seconds 0` deaktiviert ihn. Der gepruefte erfolgreiche Beispielclip
liegt unter `videos/bc_rnn_success_plus2s/rollout_00.mp4`.

2 x 2 Collage, synchronisierte Ansichten desselben Rollouts:

1. Oben links: bisherige agentview-Kamera, unveraendert.
2. Oben rechts: vorne, weiter entfernt.
3. Unten links: rechts, weiter entfernt.
4. Unten rechts: diagonal von oben, ganzer Roboter samt Tisch.

768 x 768 MP4, vier beschriftete 384 x 384 Ansichten. Die neuen Kameras
aendern weder die Kameraeingaben der Policy noch die Aufgabe.
Die Videos werden mit gespeicherten Modellen durch neue Simulation-Rollouts
erzeugt; vorhandene Einzelansicht-Videos bleiben erhalten.

`videos/bc_rnn/` und `videos/bc_transformer/` enthalten zusaetzliche Videos der
300-Epochen-Modelle. Einzelmetriken und Seeds stehen unter `evaluation/`.
`bc_rnn_preview` ist nur der technische Kurztest mit drei Simulationsschritten.

Weitere 50 Videos je Modell aufnehmen (PowerShell im Projektordner):

```powershell
& .\experiments\baselines\square_multiview\record_more.ps1 -Episodes 50
```

Dieser Befehl aktualisiert die Videos in den genannten Modellunterordnern.
Fuer kuenftige Nachtlaeufe zeichnet die Pipeline jetzt 50 Rollouts je
Zwischenstand als Collage auf. Der fertige alte Lauf bleibt unveraendert.
Der gemeinsame Evaluator akzeptiert auch `--layout single`, `--episodes` und
`--seed`, wenn gezielt andere Aufnahmen gewuenscht sind.
