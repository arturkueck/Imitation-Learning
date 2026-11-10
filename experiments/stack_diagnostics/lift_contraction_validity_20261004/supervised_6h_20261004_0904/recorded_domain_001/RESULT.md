# Statische Domaininformation an aufgezeichneten BC-Frames

**COMPLETE_STATIC_AUDIT, unabhängig STATIC_AUDIT_VERIFIED.** Alle **60/60** aufgezeichneten Auditframes bestehen die vorbestimmte geometrische Zuordnung; **49/60** sind statisch frei von Roboter-/Gripperkontakten. Ein Index (Demo, Frame) kann solche Annotationen technisch an BC-Batches binden. Das ist **keine hinreichende dynamische Gültigkeitsmaske w** und keine Trainingsverbesserung.

| Bekannter Auditsatz | Geometrisch passend | Statisch kontaktfrei | Mit Kontakt |
|---|---:|---:|---:|
| Train, frühe 5/10/15% | 24/24 | 24/24 | 0/24 |
| Train, spätere 50/85% | 16/16 | 9/16 | 7/16 |
| Valid, frühe 5/10/15% | 12/12 | 12/12 | 0/12 |
| Valid, spätere 50/85% | 8/8 | 4/8 | 4/8 |

Die elf Kontakte liegen in den späteren Frames; beobachtete Paare betreffen Cube/Finger/Hand und einmal Tabelle/Finger. Die Frames und Gradienten waren bereits bekannt, die statische Annotation wurde erst jetzt erhoben. Das ist ein Zuordnungs-/Verfügbarkeitsaudit, **kein unberührter Methodentest** und kein Fit eines Gültigkeitsklassifikators.

## Was die Verknüpfung mit den bestehenden Gradienten zeigt

Der ungewichtete B_7-Loss ist auch auf sämtlichen elf statischen Kontaktframes aktiv: 44/66 Perturbationen positiv. Median ||g_B7||/||g_BC|| an diesen Frames 0,220 Train (sieben Frames) bzw. 0,551 Valid (vier Frames). An statisch freien späteren Frames sind es 0,511 Train (neun Frames) und 0,594 Valid (vier Frames). Alle Werte kommen aus dem unveränderten früheren Gradientenaudit; keine neuen Optimizerupdates, keine Loss-/Filter-/Lambdaauswahl nach Aufgabenleistung.

Damit liegt ein Teil des Regularisierungssignals an Zuständen, für die unsere bisherige **kontaktfreie** Modellprüfung keinen Gültigkeitsnachweis bietet. Dies beweist weder, dass der Loss dort numerisch falsch ist, noch dass er Taskleistung schädigt. Statisches Filtern würde das Trainingsziel verändern; dieser Eingriff müsste als eigene abladierbare Algorithmuskomponente geprüft werden.

Die Live-Domainprobe enthält bereits das Gegenbeispiel demo_165 bei 85%: Start ohne Kontakt, Kontakt im nächsten BC-Prüfschritt. Auf deren zwölf bereits gesehenen Ankern akzeptiert eine reine Startkontaktregel neun Fälle, aber nur acht erfüllen die volle Domainprüfung. Dieses Gegenbeispiel verhindert, statische Kontaktfreiheit als hinreichendes dynamisches Trainingsgate auszugeben.

## Durchführung, Nachweise und Grenzen

[Protokoll](PROTOCOL.md) vor neuen statischen Antworten fixiert. Alle 60 zuvor festgelegten Frames aus gradient_audit_001, acht Train-/vier Valid-Demos, keine Ersetzung. Seed 4100407 dient der reproduzierbaren Initialisierung, keine neue zufällige Auswahl. Demo-XML und vollständiger states[t]-Vektor gesetzt, forward und native robomimic-Beobachtungsabfrage; keine Expertpräfixe und **keine env.step-Aufrufe**. Keine Policy/Optimizer konstruiert.

EEF-/Objektposition und relativer Vektor ≤1 µm, Quaternionorientierung bis auf Vorzeichen ≤1e−4 rad, Gripper-qpos ≤1e−9. Maximaler Positions-/Relativfehler 5,60e−16 m, Objektposition/Quaternionwinkel/Gripperabweichung null. Weitere vorhandene Gelenk-/Geschwindigkeitsmerkmale und State-Roundtripdiagnostik in Rohdaten erfasst. Daraus wird **keine Wiederherstellung der ursprünglichen Controller-/Solvergeschichte oder Expertfolgedynamik** behauptet; die älteren Replayabweichungen bleiben relevante dynamische Grenzen.

[Unabhängige Prüfung](analysis_verification.json) reproduziert HDF5-Frames/Indices/Quaternion-/Positions-/Grippergates, Source-/State-/XML-/Checkpoint-/Datensethashes, Annotationszähler und die deskriptive Gradientenverknüpfung. Kontaktmarken sind aus der gespeicherten, durch eingefrorenen Simulatorcode erhobenen Geometrieabfrage; kein zweiter Simulatorlauf und keine unabhängig rekonstruierte ursprüngliche Aufnahmedynamik.

Kosten: 60 XML-/Zustandsrekonstruktionen, 60 explizite forward-Aufrufe und 60 Kontaktabfragen; Worker 24,140 s, Supervisor 26,030 s, Rohdatenanalyse 0,056 s. Keine Aktionsrollouts und null Policyupdates/Fits. Worker und Watchdog beendet, Job geschlossen, kein eigener Wachhaltemodus. B0-Checkpoint unverändert.

Rohdaten-SHA256 `5affa636ee974fcf47cb113644e40aaf9dd438c91c1163adf3beb8cb3d1905b4`; vollständige Dateien in [result.json](result.json), selection.json, source_hashes.json und analysis_verification.json.

Nächster minimaler Schritt: [eingefrorene Antwortmodelle an echten aufgezeichneten Zuständen unter zwei ausdrücklich kontrollierten Controllergeschichten prüfen](../NEXT_RECORDED_RESPONSE.md). Statische Maskenzuordnung ist jetzt technisch möglich; dynamische Gültigkeit und Expert-Recoverylabels sind weiterhin offen. Hauptaussage zur fehlenden robusten BC-Verbesserung unverändert.
