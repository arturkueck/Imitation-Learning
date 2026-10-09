# Feste empirische Fehlermarge: frische Gegenprüfung

Stand 2026-10-04T14:21:03.656055+02:00. Seed4100412, vier neue Train-Demos demo_38, demo_76, demo_50, demo_150, unveränderter180/20-Split; zwölf H_reset-Anker bei10/50/85%, **336/336** geplante Zweige. Eingefrorener B0-Endcheckpoint/A, null Policyupdates. [Vorabprotokoll](PROTOCOL.md), [effektive Auswahl](selection.json), [fixierte Marge und Herkunft](margin_spec.json).

## Primärer Befund

Lokales B7 je gültigem Anker aus14 nominalen ±0,1-Aktionszweigen bestimmt; tatsächlich geklippte Differenzen und Rang geprüft. **8 lokale Fits** mit je21 Koeffizienten, kein Policytraining. Sechs getrennte physische ±5-mm-Pfull-Prüfzweige je Anker, keine lokale Identifikation aus diesen Policyantworten. Primär gleiches A/B_local und gleiche Rohantworten; geändert wird nur die Entscheidungsfehlermarge.

epsilon_train=**0.0021163913289946276**, vor neuen Daten als maximales normiertes Vektorresiduum aus48 alten gültigen Trainprüfungen festgelegt. Die neue Regel verlangt r_hat+epsilon_train<0,99 statt r_hat<0,99. Tatsächliche Gegenprüfung r_observed<0,99. Technische Herstellung **12/12**, dynamische kontaktfreie Domain **8/12**. **48/72** geplante Policyprüfungen numerisch gültig bewertet, 24 wegen Domain nicht numerisch bewertet; keine ersetzten Frames. Alle tatsächlichen Selbstkontakte bleiben im Label.

| Regel auf gültigen Prüffällen | Richtig freigegeben | Falsch freigegeben | Unnötig verworfen | Richtig verworfen |
|---|---:|---:|---:|---:|
| Ungesicherte lokale Vorhersage | 10 | 2 | 0 | 36 |
| Vorhersage + feste Fehlermarge | 4 | 0 | 6 | 38 |

**10** Fälle überschreiten die alte empirische Vektorfehlergrenze; Maximum neuer normierter Vektorfehler **0.01014000876830819**. Wissenschaftlicher Margenstatus **EMPIRICAL_MARGIN_DEVELOPMENT_GATE_FAILED**, physischer Rohstatus **DOMAIN_GATE_FAILED**. Die vorab fixierte Entwicklungsregel ist **nicht erfüllt**. Fehlergrenzenverletzungen, falsche Freigaben und Abdeckung bleiben getrennte Kriterien. Die Marge wird nicht aus diesen Gegenprüfungsdaten vergrößert; kein Retry oder Seed-/Schwellensweep.

| Phase | Gültige / geplante Prüfungen | Grenze verletzt | Falsche Freigaben roh | Falsche Freigaben mit Marge | Richtig frei mit Marge | Unnötig verworfen mit Marge |
|---|---:|---:|---:|---:|---:|---:|
| 0.1 | 24/24 | 6 | 0 | 0 | 0 | 4 |
| 0.5 | 24/24 | 4 | 2 | 0 | 4 | 2 |
| 0.85 | 0/24 | 0 | 0 | 0 | 0 | 0 |

Die Dreiecksungleichung liefert eine obere Ratio nur unter einer tatsächlich geltenden Vektorfehlergrenze. Ein Maximum auf endlichen älteren Trainfällen ist keine solche allgemeine Grenze. Insbesondere kann die Entscheidung zufällig korrekt bleiben, obwohl die Fehlergrenze nicht übertragen wird; umgekehrt ist Nullfehler bei Nullabdeckung keine nützliche Regel. Das ist ein Mechanismustest einer eingefrorenen Policy, kein neuer Trainingseed oder Taskgewinn.

- demo_76, Frame 4, Achse 2 plus: normierter Vektorfehler 0.01014000877, beobachtete Ratio 0.9916494381, Vorhersage 0.9907832369, Vorhersage+Marge 0.9928996282.
- demo_76, Frame 4, Achse 2 minus: normierter Vektorfehler 0.009695598328, beobachtete Ratio 0.9913985451, Vorhersage 0.9905564494, Vorhersage+Marge 0.9926728407.
- demo_76, Frame 4, Achse 0 minus: normierter Vektorfehler 0.005984443144, beobachtete Ratio 1.000645973, Vorhersage 0.9996464654, Vorhersage+Marge 1.001762857.

## Sekundäre Masken und praktische Grenzen

Unveränderte vor Antwortaktionen berechnete M0/M2 separat, ohne Auswahl eines günstigeren Primärsubsets: M0 9/12 akzeptiert, 1 dynamische Fehlannahmen, 0 unnötige Verwerfungen; M2 7/12 akzeptiert, 0 dynamische Fehlannahmen, 1 unnötige Verwerfungen. [Vollständige phasengetrennte Zahlen](analysis_repair_001/margin_analysis.json). Keine daraus gewählte neue Maske/Schwelle.

Simulatoridentifikation und feste Controllerersatzgeschichte sind privilegierte Zusatzinformationen. Ein Cache muss korrekt mit Datasetframes/Policyfeatures verbunden werden; eine weiter trainierte Policy kann die um B0 identifizierte Aktionsregion verlassen. Gewichtung, Fehlermarge und volle Aktionsantwort dürfen außerdem den Vergleich nicht durch unkontrollierte Gradientenskalenänderung entscheiden. Diese praktischen Gates und der replizierte Task-/Robustheitsvergleich bleiben offen. Historische Taskgewinne/Literatur/Sensorpilot bleiben getrennte Evidenz; Hauptaussage unverändert, noch keine robuste neue BC-Algorithmusverbesserung.

## Quellen, Verifikation und Kosten

Vor Primärlaunch Auswahl/Marge/Code eingefroren, [source_hashes.json](source_hashes.json), Dataset-/Checkpoint-/Kalibrierhashes in Auswahl und margin_spec. [Physischer Audit](analysis_verification.json) prüft alle gespeicherten Zustände/History/Geometrie/Gates und Quellhashes. [Lokale Identifikation](local_identification.json), [Marginanalyse](analysis_repair_001/margin_analysis.json); unabhängige direkte lineare Lösung statt lstsq und Rohzustands-/Norm-/Fehlerrechnung reproduziert **8 Fits/48 Entscheidungen**, maximaler Matrixunterschied 0, Ratiounterschied 0, Fehlerunterschied 0, [Nachweis](analysis_repair_001/margin_verification.json). Gelenkgrenzen kommen aus eingefrorenen Workerassertionen; andere ausgewiesene Gates werden aus Rohzuständen nachgerechnet. Ein reiner Metadatenfehler wiederholte zunächst den globalen geplanten Nenner72 in jeder Phase; [frische Reparatur](analysis_repair_001/REPAIR.json) korrigiert nur diese drei Angaben auf24. Primäre/sekundäre Zählungen, sämtliche Fallentscheidungen, Formel, Marge und Quellen vor Primärlaunch bleiben exakt gleich, Originalanalysen bleiben erhalten. Kein erneut ausgeführter Simulatorzweig oder Training.

Primärworker **197.344 s**, Supervisor **200.175 s**. Zähler {"resets": 336, "prefix_actions": 0, "probe_actions": 336, "physics_steps": 8400, "ik_iterations": 288, "policy_calls": 84}, zwölf explizite Queryforwards zusätzlich, weitere Setupforwards nicht vollständig instrumentiert. Vorprüfung 4.750 s Worker/6.012 s Supervisor: sechs bekannte Boxcases und alter Frame, sieben Query-/sechs originale synthetische Forwards, eine Rekonstruktion, keine Antwortaktionen/Integration. Unabhängige Queryneuherstellung 10.468 s Worker/12.018 s Supervisor, zwölf Rekonstruktionen/Queryforwards, exakt gleiche Masken/Kontaktlisten und nominale Zustände, [Nachweis](query_verification_001/result.json); keine Policyantworten/Integration. Analysen erzeugen keine weiteren Physiksteps.

Alle drei Worker und Supervisoren anhand PID/Erzeugungszeit beendet, Jobs geschlossen. Sessioncoordinator/Heartbeat ACTIVE bis unverändert15:11:19 Berlin. [Nächster konkreter Schritt](../NEXT_METHOD_REFERENCE.md): isolierte Lossreferenz und Cache-/Aktionsregion-/Gradientenaudit ohne Policyupdates; keine Integration als angeblich validierter Trainingsalgorithmus.

SHA-256 Rohdaten `1f6908fb63f6a10baac22ecc9bde47809bccd7ad8b96760c5b083bac3610be9c`; physischer Audit `f7b790573487f0dda998780b4782ef43edef493c3bfef5e4908a610c752827c5`; korrigierte Marginanalyse `4597f5d457d41d9b0370d9448695236e15fd489e1a4a25967a59569d602c31b4`; unabhängige korrigierte Rechnung `49669e233a9fabea4989b71653fe45b9e859d38eac7483498b5211e564838ebe`. Endcheckpoint/Dataset unverändert.
