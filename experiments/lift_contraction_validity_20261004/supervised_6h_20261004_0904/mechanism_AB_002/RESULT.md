# Verifizierte lokale A/B-Diagnose ohne Training

Status: COMPLETE und unabhängig VERIFIED. 12 vorab gewählte frühe Anker aus vier Demos; erste zwei nur Identifikation, letzte zwei Gegenprüfung. 312 Simulatorzweige. Echte ±5-mm-EEF-Zustände über Gelenk-IK bei erhaltener Orientierung/räumlicher Geschwindigkeit, Objekt/Gripper/Controllerhistorie und Solver-Warmstart. Vollständige numerische Zustände und Beobachtungen sind gespeichert. Alle Referenz-/Kontakt-/Herstellungsgates und die unabhängige Hilfsfeldprüfung bestanden. Worker und eigener Watchdog sind beendet; Sessionaufsicht/Agent-Heartbeat bleiben aktiv.

Diese technische Wiederholung verwendet dieselben vorab bestimmten Demos wie mechanism_AB_001, dessen unabhängige Prüfung den veränderten Solver-Warmstart entdeckt hatte. Der erste Versuch bleibt ungültige Mechanismusevidenz. Seine Antworten waren vor Korrektur bekannt; die Wiederholung ist kein zusätzlicher unberührter Bestätigungssatz. Kein Trainingsupdate in beiden Diagnosen.

## Was die Gegenprüfung feststellt

| Aktionsmodell B | Bestandene Gegenprüfungen | Median relativer Fehler | Median Vektorfehler |
|---|---:|---:|---:|
| Expert-OLS-K | 0/18 | 1,160 | 1,136 mm |
| Frühere partielle Kalibrierung | 18/18 | 0,0691 | 0,0655 mm |
| Neues B, nur auf zwei Identifikationsdemos fit | 18/18 | 0,0155 | 0,0155 mm |

Diese neuen Anker waren von sämtlichen früheren Diagnose-/Kalibrierungsdemos getrennt. Die Aussage betrifft die aktuelle partielle Simulatorantwort an diesen Zuständen, keine Reproduktion der aufgezeichneten Zwischenzustände, keine Policyverbesserung. Das stützt die Kritik am Expert-OLS-K als partiellem Aktionsgain. Der neue Fit hat denselben begrenzten Simulatordomainzugriff und bleibt ein kleines Entwicklungsmodell.

Für die offene Zustandsantwort hat die Identitätsvorhersage einen medianen relativen Fehler von 0,00175 (0,175%), p90 0,00299. A=I ist damit nach den vorab gesetzten Größenordnungskriterien **an diesen frühen kontaktfreien Ankern kompatibel**. Die vorher offene Möglichkeit eines großen A-Fehlers wird hier nicht unterstützt. Kein Nachweis für andere Phasen, Kontakt oder beliebige erreichbare Störungen.

Bei den 36 zurückgehaltenen translationsbeschränkten Policyreaktionen beträgt der mediane Vektorfehler 0,0290 mm mit I/K_OLS, 0,00907 mm mit I/K_partial und 0,00575 mm mit A_fit/B_fit. Alle erfüllen das grobe Modellgütegate. Die kleinen Policyaktionsänderungen machen Fehler im Aktionsgain bei einem großen 5-mm-Startdelta schwerer sichtbar als die isolierte Aktionsantwort. Ein bestandenes Vektorfehlergate allein bestätigt keine Entscheidung direkt an einer engen Kontraktionsschwelle.

## Explorative Loss-Diagnose, keine vorab bestätigte Hauptmetrik

Eine nachträgliche Auswertung der gespeicherten Antworten mit dem bestehenden Zielratio 0,99 steht in loss_mechanism.json. In der translationsbeschränkten Gegenprüfung liegt tatsächlich nur 1/36 Ratio unter 0,99; I/K_OLS sagt 12/36 voraus (11 falsche Entwarnungen), die partielle beziehungsweise A/B-Näherung jeweils 0/36 (eine falsche Strafe). Das macht einen konkreten Unterschied im Regularisierer sichtbar, ohne seine Trainingswirkung nachzuweisen.

Bei **vollständiger** neuer Policyaktion liegt die beobachtete Ratio dagegen bei 12/36 unter 0,99. I/K_OLS klassifiziert diese Fälle hier zufällig richtig; I/K_partial und A/B_xyz jeweils 0/36, also zwölf falsche Strafen. Die aktuelle 3×3-Näherung berücksichtigt nur Translationsaktionen; die Rotations-/Gripperänderungen sind in den Rohdaten ausdrücklich gespeichert. Eine genauere 3D-Matrix kann deshalb die vollständige Lossentscheidung nicht automatisch verbessern. Das ist eine wichtige Einschränkung eines bloßen K-Austauschs. Die Unterschiede dürfen nicht als allgemeiner Klassifikations- oder Policyvergleich ausgegeben werden: ein eingefrorener Entwicklungscheckpoint, zwei Gegenprüfungsdemos, ausgewählte frühe Anker, post-hoc Schwellenanalyse.

Der nächste minimale Versuch identifiziert die vollständige partielle Antwort auf alle sieben Aktionskomponenten und prüft vollständige Policyreaktionen auf getrennten neuen Demos. Zunächst kein Policytraining. [Vorab festgelegter nächster Auftrag](../NEXT_ACTION_RESPONSE.md).

## Aufwand, Provenienz und Grenzen

Gültige Diagnose: 165,49 s Workerzeit, 168,14 s einschließlich Prozessaufsicht. 312 reset_to-/XML-/Präfixrekonstruktionen, 1.508 Präfixaktionen, 312 Prüfaktionen, 45.500 Physiksteps, 432 IK-Iterationen, 156 Policyaufrufe. Gemeldete Fitzeit 0,0 s liegt unter der Uhr-Auflösung, nicht gleichbedeutend mit kostenlosem Fit. Die Physikstepzahl stimmt exakt mit 25 × (Präfix- plus Prüfaktionen) überein.

Zusätzlich ungültiger erster Versuch: 165,45 s Workerzeit und dieselben Simulationszahlen; zwei Runtimeinspektionen etwa zehn Sekunden ohne Aktionen/Training. Gesamtaufwand beider Diagnoseworker 330,94 s, 91.000 Physiksteps, 624 Rekonstruktionen. Die Mehrkosten der technischen Reparatur zählen ausdrücklich mit.

selection.json, source_hashes.json, repair.json, result.json, verification.json und Supervisorlogs enthalten Auswahl, Seed, Quellen/Protokollhashes, Daten-/Checkpointpin, tatsächliche Zustände und Prozessende. Synthetische IK-Zustände zeigen einen Ein-Schritt-Mechanismus, keinen durch äußere Stöße tatsächlich erreichbaren Recoveryverlauf und keinen stabilen Stack. Primärliteratur und frühere Trainingsbefunde bleiben separate Evidenz. Hauptaussage unverändert: noch keine robuste neue BC-Verbesserung.
