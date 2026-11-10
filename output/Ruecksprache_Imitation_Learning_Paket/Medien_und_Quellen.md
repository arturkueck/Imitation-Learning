# Medienauswahl für die Rücksprache

Stand: 12. Oktober 2026. Die lokalen Dateien liegen gemeinsam im Unterordner `media` und können zusammen mit diesem Gesprächspaket kopiert werden. Die folgenden absoluten Links öffnen die Exemplare auf diesem PC.

## Kurze Vortragsregie

1. **Forschungsfrage erklären, etwa 30 Sekunden:** [Konzeptgrafik öffnen](../meeting_2026-10-12/media/01_sensor_vs_state.png). „Ein fehlerhafter Messwert sollte die Aktion möglichst wenig verändern. Eine echte Zustandsabweichung verlangt dagegen eine Korrektur. Ich möchte diese beiden Fälle experimentell trennen.“
2. **Unterscheidung zeigen, 10 Sekunden:** [Schemaanimation als MP4](../meeting_2026-10-12/media/02_sensor_vs_state.mp4) oder [GIF](../meeting_2026-10-12/media/02_sensor_vs_state.gif). Die Animation zeigt idealisierte Lernziele und ist durchgehend als „Schematische Illustration – keine Versuchsdaten“ gekennzeichnet. Sie demonstriert keinen bereits erreichten Trainingserfolg.
3. **Lokale Arbeitsfähigkeit anschaulich machen, optional etwa 30 Sekunden:** zuerst [Stack-Erfolgsbeispiel, 8,25 Sekunden](../meeting_2026-10-12/media/04_stack_erfolg.mp4), danach den Anfang und Schluss des [Stack-Misserfolgsbeispiels, 27 Sekunden](../meeting_2026-10-12/media/05_stack_misserfolg.mp4). „Das sind zwei ausgewählte lokale Replays derselben Modellklasse mit verschiedenen Startzuständen. Sie zeigen, warum wir systematisch über mehrere Seeds und Starts evaluieren müssen.“ Die Clips sind qualitative Beispiele, kein Benchmarkbeweis und kein Vergleich der vorgeschlagenen Methoden. Stack ist hier Anschauungsmaterial; der geplante Einstieg bleibt Lift.
4. **Vorarbeiten nur bei Nachfrage einordnen:** [Historische Lift-Grafik mit allen drei Trainingsseeds](../meeting_2026-10-12/media/03_historical_lift_seeds.png). „Die frühere Erweiterung ist im kleinen lokalen Vergleich besser. Ob der Unterschied wirklich durch einen sinnvollen Dynamikmechanismus entsteht, ist damit noch nicht geklärt.“ Das motiviert kontrollierte Ablationen; es bestätigt die neue Hypothese noch nicht.

## Herkunft der lokalen Replays

Beide MP4s sind byteidentische Kopien vorhandener Videos aus `experiments/stack_diagnostics/stack_replication_20261001/representative/`. Es wurde dafür weder ein Modell trainiert noch eine neue Policy-Evaluation gestartet. Laut ursprünglichem Manifest wurden gespeicherte Simulatorzustände erneut abgespielt. Die Videos wurden vollständig dekodiert; Anfang, Mitte und Ende wurden als Storyboard visuell geprüft.

| Lokale Kopie | Originaldatei | Trainingsseed / Start | Dauer; Dateigröße | Ergebnis laut gespeichertem Rollout |
|---|---|---|---|---|
| `media/04_stack_erfolg.mp4` | `direct_seed_3_start_46003.mp4` | 3 / 46003 | 8,25 s; 112.301 Bytes | `stack=true`, `sustained_success=true` |
| `media/05_stack_misserfolg.mp4` | `direct_seed_3_start_46005.mp4` | 3 / 46005 | 27,00 s; 368.966 Bytes | `grasp=false`, `stack=false`, `sustained_success=false` |

„Erfolg“ bezeichnet beim ersten Clip das vorhandene Stack-Erfolgskriterium. Derselbe Rollout wird in der zusätzlichen Phasendiagnose als `correct_lift=false` und `premature_transport=true` eingeordnet. Der Clip belegt deshalb keine vollständig korrekte Phasenfolge.

- [Quellmanifest mit Originalpfaden, SHA-256-Prüfsummen und Ergebnisfeldern](../meeting_2026-10-12/media/replay_manifest.json)
- [Ursprüngliches Replay-Manifest](../../experiments/stack_diagnostics/stack_replication_20261001/representative/manifest.json) und [gespeicherte Rollout-Ergebnisse](../../experiments/stack_diagnostics/stack_replication_20261001/direct/seed_3/rollouts/results.json)
- [Storyboard Erfolg](../meeting_2026-10-12/media/04_stack_erfolg_storyboard.png) und [Storyboard Misserfolg](../meeting_2026-10-12/media/05_stack_misserfolg_storyboard.png) als statische Alternative
- [Medienlegenden und Quelle der historischen Lift-Abbildung](../meeting_2026-10-12/media/README.md)

## Externe Referenzmedien

Diese beiden Autorenprojektseiten wurden am 12. Oktober 2026 direkt geöffnet und überprüft. Externe Medien wurden nicht heruntergeladen. Die Seiten selbst enthalten Video- und Bildbeispiele; ihr Inhalt darf als Literaturkontext vorgestellt werden, nicht als eigenes Ergebnis.

- [Stable-BC: Autorenprojektseite](https://collab.me.vt.edu/Stable-BC/): enthält Video, Algorithmusschema sowie Beispiele aus Simulation und robotischem Air Hockey. Im Gespräch geeignet, um die bereits vorhandene Forschung zu stabilitätsorientiertem Behavioral Cloning zu verorten. Anschließend auf den eigenen engeren Vergleich zwischen Sensorfehlern und realen Zustandsabweichungen überleiten.
- [robomimic: „What Matters in Learning from Offline Human Demonstrations for Robot Manipulation“](https://robomimic.github.io/study/): enthält Aufgabenbeispiele, Demonstrationsvarianten und Policy-Rollouts. Geeignet, um Lift und mögliche Folgeaufgaben anschaulich zu zeigen. Für einen kurzen Termin reicht ein ausgewähltes Aufgabenbeispiel; die ganze Videosammlung ist Hintergrundmaterial.
