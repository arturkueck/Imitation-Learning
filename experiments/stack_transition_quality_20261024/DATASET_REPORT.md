# Datensatzbericht: Übergänge zum nächsten Griff

Stand 24.10.2026. Neue Simulationen und technische Kurztests sind abgeschlossen; der produktive Trainingslauf wurde nicht gestartet.

200 vorab zugewiesene Episoden: je 100 Drei-/Viererrollouts, pro Höhe 60 Training und 40 Validierung. Die Reduktion von ursprünglich 400 auf 200 ist in cohort_revision_v2.json dokumentiert; die Akzeptanzgates wurden nicht gelockert. Drei eingefrorene Teacher werden zyklisch zugewiesen. Fehlgeschlagene Vollrollouts bleiben im Inventar.

| Quelle | Vollerfolge / Versuche |
|---|---:|
| 3 Würfel, Teacher 1 | 19/33 |
| 3 Würfel, Teacher 2 | 20/34 |
| 3 Würfel, Teacher 3 | 14/33 |
| 4 Würfel, Teacher 1 | 7/33 |
| 4 Würfel, Teacher 2 | 12/34 |
| 4 Würfel, Teacher 3 | 6/33 |

Dies sind Sammelergebnisse, keine unabhängigen Endtests und kein Ergebnis des neuen Trainings.

| Split | Abschnitte | Familien | Präfix 2 / 3 |
|---|---:|---:|---:|
| train | 49 | 46 | 41 / 8 |
| valid | 32 | 30 | 26 / 6 |

Pre-action-Eingänge und Teacheraktionen sind zeitlich zugeordnet. Akzeptiert wird nur bestätigtes natives Greifen und Anheben bei durchgehend erhaltenem unteren Turm einschließlich 50 Nachlaufframes. Nachlauf ist Bewertungsinformation und kein zusätzlicher Actiontarget. Training und Validierung teilen keine Startfamilien. Alle Quell- und Teacherhashes wurden geprüft.

Qualität im Training: Mittel 0.8992, Standardabweichung 0.0577; effektive Abschnittszahl nach Gewichtung 48.89 von 49. Der Erhaltterm ist nach strenger Annahme konstant; nur Ruhe und Zentrierung variieren. Daher ist der Gewichtungskontrast klein.

## Vorbereitete Evaluationszustände

| Panel | Präfix | vorbereitet / 20 |
|---|---:|---:|
| development | 2 | 18/20 |
| development | 3 | 13/20 |
| confirmation | 2 | 19/20 |
| confirmation | 3 | 10/20 |

Fehlgeschlagene Vorbereitung bleibt im gemeinsamen Nenner; zusätzlich muss die bedingte Leistung auf vorbereiteten Zuständen berichtet werden. Die Bestätigungsabdeckung bei Präfix 3 beträgt nur 10/20 und begrenzt die Gesamtquote auf 50 %. Das ist kein 90-%-Benchmark. Die reservierte Schlussvorbereitung wird erst nach dem gemeinsamen Modellfreeze ausgeführt.

Frische Umgebungen reproduzierten in geprüften Drei- und Viererbeispielen erste Aktion, Folgezustand und Folgebeobachtung exakt (maximale gemessene Abweichung 0). Das umfasst Simulations-, Controller- und Sequencerzustand.

## Kosten und Grenzen

Der letzte Sammelaufruf meldet 932.6 Sekunden. Er enthält nicht die gesamte frühere Probe und Entwicklungsarbeit. Ein vollständiger End-to-End-Timer wurde im laufenden Prozess noch nicht gespeichert; deshalb wird dieser Wert nicht als Gesamtkosten ausgegeben. Alle 200 Episoden wurden beendet. Diese Vorbereitung wird separat von der erst nach Go beginnenden Achtstundengrenze berichtet.

Nur acht Trainingsabschnitte betreffen Präfix 3. Teacherbias, strenge Erfolgsselektion und fehlende explizite Turmgeometrie im Actor bleiben wissenschaftliche Grenzen. Kein Datensatzgate beweist eine spätere Erfolgssteigerung.

Öffentliche MimicGen-Daten wurden tatsächlich heruntergeladen und geprüft, wegen anderer Geometrie, Rotationsaktionen und fehlender kompatibler Phasenlabels aber nicht beigemischt. Siehe PUBLIC_DATASET_REVIEW.md.