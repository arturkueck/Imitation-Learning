# Geschlossener Handkameratest · 01.11.2026

**Abgeschlossen. Kein Training und keine neuronalen Optimizer-Updates.** Die vorhandenen drei Seeds jeder Kameravariante bleiben eingefroren; alle sechs Checkpoint-Hashes wurden vor und nach dem Versuch geprüft.

## Ergebnis

Die technische Kette funktioniert in der Referenzsimulation: Unsicherheit auslösen, Ziel aus den Vorhersagen wählen, eine erreichbare Kamerapose suchen, eine Ganzarmbahn prüfen, kinematisch fahren, neue Bilder mit aktueller Kamerakalibrierung aufnehmen und erneut inferieren.

**Eine zuverlässige Positionsverbesserung ist damit nicht erreicht.** Die neuen Bilder verschlechtern in diesem kleinen Pilot die zuordenbaren Zielschätzungen. Die Übernahmeregel verwirft sämtliche neuen Schätzungen; die ursprünglichen Positionen bleiben erhalten. Das ist eine funktionierende Zurückstellung in diesen Fällen, keine Garantie gegen zukünftige Fehlübernahmen.

| Umfang | Ergebnis |
| --- | ---: |
| Neue Szenenfamilien versucht | höchstens 80, Seed 9841101 |
| Geeignete Szenen mit mindestens zwei Objekten | 61 |
| Ausgelöste Fälle | 7 |
| Kamerabewegungen und neue Aufnahmen | 7 |
| Anfangsziele mit zugeordnetem Sollobjekt | 4 |
| Als falsche Zusatzdetektion gewertete Anfangsziele | 3 |
| Übernommene neue Schätzungen | 0 |
| Kinematische Wiedergabeschritte | 1.119 |
| Native Roboter-Umwelt-Durchdringungen bei Wiedergabe | 0 |

Es sollten maximal acht ausgelöste Fälle aufgenommen werden. Die vorher festgelegte Grenze von 80 Szenenfamilien wurde mit sieben Auslösern erreicht; der Versuch wurde nicht verlängert, um weitere oder günstigere Fälle zu suchen. Es gab keine blockierte Fahrt in den sieben ausgelösten Fällen. Die Aussage über Bewegungen gilt ausschließlich relativ zur verwendeten Simulationsgeometrie und den konfigurierten Kamera-/Halterungsproxies, nicht für reale Hardware oder einen nur visuell belegten Freiraum.

## Tatsächlicher Positionsfehler

Die vier Ziele mit Sollzuordnung vor und nach der Aufnahme:

| Szene | Vorher | Nach neuer Aufnahme | Übernommen |
| --- | ---: | ---: | --- |
| 18 · Turm | 3,80 mm | 38,91 mm | nein |
| 36 · verstreut | 8,77 mm | 16,46 mm | nein |
| 55 · Wand/Brücke | 12,93 mm | 40,81 mm | nein |
| 57 · gemischt | 34,10 mm | 55,04 mm | nein |
| **Mittelwert über diese vier Zielpaare** | **14,90 mm** | **37,81 mm** | **0 / 4** |

Keine der vier neuen Zielpositionen ist genauer; alle werden um mehr als 1 mm schlechter. Mit der getesteten Übernahmeregel bleibt der mittlere Fehler deshalb bei 14,90 mm. Die drei Zusatzdetektionen erhalten keinen erfundenen Positionsfehler. Es fehlen in diesem Lauf keine Zielzuordnungen nach der Aufnahme; der Code würde solche Fälle separat zählen, statt sie als Erfolg zu behandeln. Bei der räumlichen Zuordnung können nahe Vorhersagen verwechselt werden; es gibt noch keine verlässliche zeitliche Objektidentität.

## Kontrolle der festen Kameras

Alle drei Ansichten werden nach der Bewegung gleichzeitig neu aufgenommen. Die festen Kameras bleiben an derselben Pose, sehen aber gegebenenfalls andere Roboterglieder beziehungsweise Verdeckungen. Deshalb laufen zusätzlich die drei eingefrorenen Modelle ohne Handkamera als Kontrolle.

| Kameravariante · ausgelöste Fälle | Mittlerer Szenen-Recall ≤10 mm vorher | Nachher |
| --- | ---: | ---: |
| Zwei feste Kameras | 91,43 % | 47,14 % |
| Fest + Handkamera | 82,14 % | 3,57 % |

Das ist der pro Szene gemittelte Anteil der ursprünglich beobachtbaren Sollobjekte, die erkannt und höchstens 10 mm entfernt vorhergesagt werden. Der identische ursprüngliche Sollobjektsatz wird für beide Varianten beibehalten. Es ist weder eine neue Gesamtgenauigkeit auf allen 61 Szenen noch ein repräsentativer Vergleich des allgemeinen Nutzens einer Handkamera. Die Szenen wurden gerade wegen Unsicherheit des Fest-plus-Hand-Modells ausgewählt.

Auch die feste Variante verschlechtert sich erheblich. Das Ergebnis lässt sich deshalb nicht ausschließlich der neuen Handkameraperspektive zuschreiben. Veränderte Roboterverdeckungen, verändertes Roboterbild und neue Kameraperspektiven sind mögliche Einflussfaktoren; sie wurden hier nicht kausal getrennt.

Die Handkamera wird um ungefähr 132–213 mm versetzt. Das vorhandene Modell wurde mit kleinen Gelenkvariationen um die ursprüngliche Pose trainiert, nicht mit dem gesamten jetzt erreichbaren Blickraum. Eine Verteilungsverschiebung ist damit eine plausible Grenze, aber der Versuch isoliert deren Anteil am Fehler nicht.

## Vorab festgelegte Regeln

`locked_plan.json` wurde vor dem Durchlauf geschrieben und per SHA-256 gegen nachträgliche Änderungen geprüft. Die Szene- und Modellseeds, Auslöse-/Übernahmeregeln, Suchbudgets und bekannte Kollisionsquelle stehen dort.

- Auslösen bei weniger als drei zustimmenden Seeds oder Positionsstreuung über 15,5 mm. Die Schwelle stammt aus der abgeschlossenen Ensemble-Diagnose. Priorität: fehlende Seed-Unterstützung, danach größere Streuung. Gemeinsame Fehler mit kleiner Streuung können weiterhin unmarkiert bleiben.
- Zielzentrum und Zielradius stammen aus vorhergesagter Position/Größe/Streuung. Die Sollobjektgeometrie wird nicht zur Zielauswahl benutzt.
- Maximal 18 geometrische Blickvorschläge; die ersten drei Kandidaten werden mit begrenzter Bahnsuche auf Erreichbarkeit geprüft. Der erste erreichbare Kandidat wird verwendet. Keine Auswahl anhand des späteren Sollfehlers.
- Die neue Zielvorhersage wird räumlich innerhalb von 50 mm der ursprünglichen Vorhersage zugeordnet. Übernahme nur mit drei unterstützenden Seeds. Bei ursprünglich drei Seeds muss die Streuung um mindestens 20 % sinken; bei ursprünglich fehlender Unterstützung müssen danach alle drei zustimmen und die Streuung höchstens 15,5 mm betragen.
- Ein einzelner Seed hat rechnerisch Streuung null, gilt aber ausdrücklich nicht als sichere Übereinstimmung. In mehreren Nachaufnahmen tritt genau dieser Fall auf; er führt nicht zur Übernahme.

Die geometrische Unsicherheitsregel ist nicht kalibriert für beliebige neue Handkameraposen. Keine neue Schätzung wird anhand der Sollposition akzeptiert oder verworfen; Sollgeometrie dient nur zur Auswertung. Die Ergebnisse werden nicht in einen IL-Datensatz übernommen und nicht an echte Hardware ausgegeben.

## Bewegungsprüfung und Daten

Die Kollisionsprüfung nutzt ausdrücklich die simulierten Hindernisgeometrien. Das ist eine Referenzprüfung für diesen Pilot, keine heimliche Freigabe unbekannter visueller Bereiche. Der gesamte Arm einschließlich Greifer, Kameragehäuse und Halterung wird geprüft. Adaptive Bahnschranken prüfen die Verbindungen, nicht nur Wegpunkte. Zusätzlich werden native Roboter-Umwelt-Kontakte bei jedem Wiedergabeschritt auditiert. Die Wiedergabe ist kinematisch ohne Drehmoment-/Nachführfehler und ohne bewegte Hindernisse.

Vor der Bewegung wird eine zweite Aufnahme an derselben Pose auf RGB-Gleichheit geprüft. Nach der Bewegung werden RGB und kalibrierte Strahlen aus der tatsächlichen neuen Kamerapose erzeugt. Die Objektpositionen müssen innerhalb von 1e-7 m unverändert bleiben. Beobachtungen und Sollgeometrie werden getrennt gespeichert.

## Nächster sinnvoller Versuch

Vor einem neuen Training zunächst kleine, begrenzte Poseänderungen näher am Trainingsbereich testen und bei der Blickwahl die Sicht der festen Kameras auf die vermuteten Objektbereiche berücksichtigen. Anschließend kontrolliert vergleichen, welcher Anteil der Verschlechterung durch Perspektive und welcher durch Roboterverdeckung entsteht. Die jetzigen sieben Fälle als Diagnosedaten behandeln und für die nächste unverzerrte Prüfung neue Szenen verwenden.

Erst wenn diese Grenzen bekannt sind, über ein Training mit größerer Kamerapose-Abdeckung entscheiden. Hier wurde kein weiterer Versuch und kein Training gestartet.

## Artefakte

- `quality.png`: Vorher-/Nachher-Fehler, Übernahmeregel und feste Kamera-Kontrolle.
- `case_*/observations.npz`: RGB und Kamerastrahlen vorher/nachher.
- `case_*/evaluation_only.npz`: getrennte Sollgeometrie und anfängliche Sichtbarkeit.
- `case_*/predictions.json`, `case.json`, `trajectory.json`: Vorhersagen, Entscheidungen und Bahn.
- `case_00/motion.gif`, `case_01/motion.gif`: zwei Bewegungsbeispiele. Das erste Beispiel ist eine falsche Zusatzdetektion, kein demonstrierter Wahrnehmungserfolg.
- `results.json`: sämtliche Fälle, Screening, Quellen- und Checkpoint-Hashes.
- `source_used.py`: ausgeführte Quellkopie.

```powershell
& .\praxis\.venv\Scripts\python.exe -m pytest praxis/tests/test_active_camera.py praxis/tests/test_active_view.py praxis/tests/test_ensemble_uncertainty.py -q -p no:cacheprovider
& .\praxis\.venv\Scripts\python.exe experiments/vision/visual_scene_v2_20261101/active_camera_test.py --name active_camera_002
```

Bestehende Ergebnisordner werden nicht überschrieben. Sechs neue Tests bestanden: Auslösung, gemeinsam falsche Vorhersage, räumliche Zuordnung, Übernahmeregel, fehlende Nachvorhersage und aktualisierte Kamerastrahlen. Keine Hardwarefreigabe.
