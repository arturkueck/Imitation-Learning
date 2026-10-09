# Begrenzter Sensorrobustheits-Pilot, vor Trainingsstart festgelegt

Die ursprünglichen Diagnosegates bleiben unverändert. `intervention.json` ergibt 0/108 bestandene Aktionsantworten, auch 0/66 in der niedrigen inneren Fehlerhälfte. Die Rekonstruktionsprüfung scheitert mit 0,654 mm medianer Referenzabweichung an 0,5 mm. Damit ist B3 **nicht freigegeben**. Der bestehende Fit ist als kausale Aktionsantwort unbestätigt. Eine Replaykorrektur und eine separate Aktionsidentifikation bleiben fachliche Folgearbeiten.

Dieser Pilot prüft nur die im Forschungsplan vorgesehene einfachere Sensor-Hypothese: Kann ein konsistenter EEF-Messfehler im Training die Empfindlichkeit gegenüber demselben Sensortyp reduzieren, ohne die Nominalleistung wesentlich zu verlieren? Kein Beleg physischer Stabilität, keine neue Modellarchitektur, kein beanspruchter neuer allgemeiner Augmentationsalgorithmus.

## Zwei gepaarte Arme

- B0: robomimic deterministisches BC, bestehende Lift-BC-Konfiguration.
- B1: gleicher Actor/Optimizer, `bc_sensor`: `(1-mix)*L_BC(clean,a_expert) + mix*L_BC(sensor_noisy,a_expert)`, mix=0,5. Pro Trainingssample zentrierter isotroper EEF-Messbias mit fester Norm 5 mm. EEF += bias, abgeleitetes Objektmerkmal cube-minus-EEF -= bias; physische Cube-Koordinaten, Gripper und Aktion unverändert. Die Labels sind für den unveränderten physischen Zustand, nicht für eine physisch versetzte EEF gültig.
- Eigene Torch-Noise-RNG mit Seed 4100401; sie verändert weder die globale RNG noch Validierungssampling. Validation misst in beiden Armen sauberes BC.
- Ein gepaarter Trainingsseed 41004, je genau 2.000 Updates; bestehender 180/20-Demo-Split, Batch100, Feedforward256×256, Adam1e-4, keine Obs-/Aktionsnormalisierung, keine EMA (bestehendes Lift-BC verwendet keine), 100 Updates/Epoche. Keine neuen Expertlabels. Die Modifikation verursacht einen zusätzlichen Policy-Forward pro Trainingsbatch und wird zeitlich mitgemessen.
- Checkpoints bei 500, 1.000, 2.000 Updates; der abschließende Hauptvergleich nutzt ausschließlich den finalen 2.000-Update-Checkpoint. Zwischenstände dienen der Lernkurve, nicht der Auswahl.
- Identische Initialparameter und kumulative Hashes **jedes** verarbeiteten Trainingsbatches prüfen. Gleiches Updatebudget; keine Laufzeitverlängerung für schlechte Ergebnisse.

## Evaluation

Lift-Nativerfolg `env.is_success()['task']`, erste Erfolgsmeldung, maximal400Steps; kein Stack-Erfolgskriterium. Starts mit Seed714000…714009, pro Arm identisch. Die bislang nicht in der Methodenauswahl verwendeten Starts sind hier ausdrücklich ein kleiner Entwicklungs-Pilot und werden nicht als finaler unabhängiger Test bezeichnet.

1. Nominal: bei500/1.000Updates die ersten6Starts, bei final2.000 alle10.
2. Sensor_y_plus5mm und Sensor_y_minus5mm: je10Starts, konstant über die Episode; EEF-Messposition und cube-minus-EEF konsistent gestört, Simulatorzustand unverändert. Nur finaler Checkpoint. Primärer Pilotwert: Summe beider Sensorbedingungen /20.
3. Action_impulse_x_plus0.5:10Starts, zusätzliche auf[-1,1] geclippte x-Aktion beiStep20. Ausgelöste Impulse und tatsächlich ausgeführte Zusatzaktion mitberichten; wenn die Episode früher endet bleibt sie im Nenner. Explorative physische Störung, keine Sensorrobustheitsmetrik.

Paare müssen dieselben initialen Cube-Qpos und EEF-Positionen erhalten. Episodeweise Rohdaten und Teilresultate sichern. Lernkurve verwendet dieselben ersten6Nominalstarts an allen drei Messpunkten. Explorative Leistungsschwelle4/6, nachhaltig an zwei aufeinanderfolgenden Punkten; bei Nichterreichen zensieren. Trainingszeit bis zu beiden Punkten sowie Vorberechnung und Evaluation getrennt berichten. Die wenigen Messpunkte/Starts/der einzelne Trainingsseed begrenzen jede Konvergenzaussage.

Pilotentscheidung zur weiteren Prüfung: Sensorgewinn mindestens2 zusätzliche Erfolge /20 und Nominalverlust höchstens1/10. Dies ist eine vorab gewählte praktische Pilotregel, kein Signifikanztest. Bei Nichtbestehen kein Sweep oder automatisches längeres Training; Ergebnis und möglichen nächsten diskriminierenden Versuch dokumentieren. Eine positive Regel allein autorisiert keine Aussage robuster Verbesserung.

## Ausführung und Ende

Frischer Ordner `sensor_pilot/B0` und `sensor_pilot/B1`, nie Resume/Overwrite alter Ergebnisse. Gesamter Pilot einschließlich Evaluation maximal2Stunden ab Launch. Windows-Job mit kill-on-close und unabhängigem Watchdog; Safe-Stop90Sekunden vor Deadline, dann hartes Ende. Wachhalteanforderung nur während der aktive Worker läuft; Watchdog beendet sich danach. Finale Teilgewichte bei sicheren Fehler-/Stop-Grenzen atomar speichern. Ausfall eines Arms beendet den Pilot, ohne automatischen Ersatzlauf. Dataset-, Source-, Config-, Split-, Initialparameter-, Batch- und Checkpointhashes, Updates, Losses, Zeiten, Workerstatus speichern.

Der 30-Minuten-Heartbeat überwacht diesen begrenzten Pilot und arbeitet nach dessen Ende Bericht und nächste fachliche Entscheidung aus. Er verhindert keine Abstürze und ersetzt den lokalen Watchdog nicht.
