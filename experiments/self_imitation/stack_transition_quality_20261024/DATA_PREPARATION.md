# Native Datenvorbereitung und Zustandstransfer

Diese Vorbereitung erzeugt Daten und Benchmarks, **keine Optimizerupdates**. Ein langer Trainingslauf benötigt weiterhin die abschließende Freigabe. Verbindliche Zahlen stehen im finalen `native_data_v1/manifest.json`; laufende Zwischenstände sind keine abgeschlossene Studie.

## Feste Herkunft und Revision

`native_data_v1/source_plan.json` ist die unveränderte Kopie des Plans vor Sammlung. Native Quellen: neue Dreierstarts510000–510199 und Viererstarts511000–511199; zyklischer Teacherindex `index % 3` aus den drei zuvor gehashten Parents. Splits wurden vor jedem Ergebnis festgelegt: Indizes0–159 Training,160–199 Validierung.

Nach gemessener technischer Laufzeit wurde **vor der Fortsetzung** eine kleinere feste Kohorte vereinbart: Indizes0–59 und160–199 je Höhe, also60Train+40Valid je Höhe, insgesamt200Versuche. `cohort_revision_v2.json` dokumentiert diese ausschließlich zeitlich begründete Revision. Seed-/Teacher-/Splitzuordnung, Extraktion, Qualitätsgewichtung und Mindestgates bleiben unverändert. Ursprünglicher Quellplan, Revisionshash und effektiver Datenregelhash bleiben nachvollziehbar. Die absolute30-Minuten-Grenze zählt ab dem ersten Vorbereitungsstart und wird bei Resume nicht zurückgesetzt.

## Pro Frame gemessene Informationen

- `pre_obs`, `x`, `anchor`, `phase_steps`, `p`, `stage`, `retreat` liegen **vor** der Aktion.
- `a` ist die tatsächlich ausgeführte Teacheraktion; Rotation bleibt in dieser unveränderten Policy null.
- `post_obs`, `post_state`, `held_post`, `fingers`, `prefix_valid`, `contacts`, `velocities`, `controller_event` liegen **nach** der Aktion.
- MuJoCo wird nach Reset und Step synchronisiert; Pre-/Postobservations referenzieren die gespeicherten Positionen. Native `held_post` benutzt `_check_grasp`; Fingerkontakte werden über die tatsächlichen Geometrien aller Gripperwerte bestimmt. Ein dict wird nicht mehr als Geometrienamensmenge missverstanden.
- `prefix_valid[k-2]` schützt die unteren k Würfel und schließt zusätzlich jeden expliziten Fingerkontakt aus. Die vollständige Turmdefinition wird nicht durch die Übergangsmetrik ersetzt.

Aktionsziele werden einzelbildweise aus den gehashten Teachermodellen reproduziert. Original-HDF5 und Rawquellen werden nicht geändert. Teilabschnitte bleiben in ihrer vorab zugewiesenen Familie; später gescheiterte Episoden können gültige frühere Abschnitte enthalten.

## Rückblickende Qualitätsmetadaten

Ein Abschnitt beginnt mit der ersten Aktion nach dem bestätigten Freigabeereignis. Die nächste Quelle muss mindestens30mm gegenüber ihrer Referenzhöhe ansteigen und über5Frames nativ gegriffen sein. Der geschützte Turm muss durchgehend gültig bleiben, einschließlich weiterer50Nachlaufframes. Der Nachlauf gehört nur zur Bewertung; das Aktionsfenster endet am bestätigten Pickup. Unvollständige Nachläufe und Berührungen des unteren Turms werden nicht umetikettiert.

Scorev1 ohne Clearance: `Q=.50+.25*Ruhe+.25*Zentrierung`, `raw_weight=.5+1.5*Q`. Erhalt ist bei akzeptierten strengen Abschnitten konstant. Ruhe/Zentrierung sind die einzigen variierenden Komponenten; keine Greiferabstände werden aus bloßen EEF-Positionen erfunden. Normalisierung wird ausschließlich auf Trainingsabschnitten bestimmt. Score, Zukunftsausgang und Validierungsstatistiken werden nie in die10D-Actorinputs aufgenommen.

## Vollständige Runtime-Snapshots

`state_replay.py` speichert am ersten Retreatframe nach Freigabe:

1. MuJoCo `mjSTATE_INTEGRATION`, einschließlich Steuersignalen und Solver-Warmstart.
2. Dynamische OSC-/Grippercontrollerwerte, Ziele, Interpolatorzustände und Roboterpuffer.
3. Beobachtungscaches, Zeitzähler, native RNG-Zustände.
4. Sequencerstage, Retreatflag, Phasenindex, Phasenzeit und Anker; Modellgewichte bleiben außerhalb des Snapshots.

Unveränderte Modell-/Controllerkonfiguration wird über den Modell-XML-Hash geprüft. Jeder gespeicherte Start wird vor Nutzung auf identische erste Aktion und identischen nächsten Integrations-/Beobachtungszustand geprüft. Rein geometrisches Teleportieren ersetzt diesen Nachweis nicht. Pickles werden nur aus intern erzeugten, SHA256-geprüften Dateien geladen.

## Vorbereitete Entwicklung und Bestätigung

Die ersten20Validfamilien pro Höhe definieren das Entwicklungspanel520000–520019 beziehungsweise521000–521019. Die letzten20 definieren das Bestätigungspanel525000–525019 beziehungsweise526000–526019. Diese Panel-IDs referenzieren ausdrücklich die native Quellfamilie; sie sind keine behaupteten neuen zufälligen Resetstarts.

Panelstart ist der freigegebene Zweierturm im Dreierumfeld oder Dreierturm im Viererumfeld vor Retreat. Erreicht ein Teacher diesen Zustand nicht, bleibt ein Datensatz mit `prepared=false` und Grund im Panel. Fehlende Starts verschwinden nicht aus dem Nenner. `prepared_starts.json` enthält Pfad, Hash, Panel, Quellfamilie, Frame, geschütztes Präfix und Reproduktionsnachweis. Reservierte Endtestkonstruktion ist hiervon getrennt und wird nicht als Trainingsquelle verwendet.

## CLI und Gates

Ohne `--collect` bleibt `production_data.py` im Dry-run. `--collect --probe` sammelt zuerst20Train+20Valid je Höhe; `--collect --resume --plan native_data_v1/source_plan.json` darf ausschließlich fehlende vorab festgelegte Kohortenstarts ergänzen. Vorhandene Episoden werden weder überschrieben noch anhand ihrer Qualität ersetzt. Originaldeadline und Quellen-/Planhashes gelten weiter.

Ein vollständig geschriebenes Dataset ist keine Trainingsfreigabe: Mindestzahlen, Familien-/Teacherdiversität, Scoredispersion, Ausgangsgradienten, gepaarte Samples, unabhängiger Onlinebenchmark und späterer Modellfreeze müssen zusätzlich bestehen. Nicht bestandene Gates bleiben nicht bestanden.
