# BC-Gradientenaudit ohne Training

**COMPLETE und unabhängig VERIFIED.** Bei gleichem diagnostischem lambda=1 verändert die kalibrierte volle Aktionsantwort die Stärke und Richtung des Regularisierergradienten. Die Änderung ist abschnittsabhängig; ein späterer Leistungsgewinn könnte ohne entsprechende Kontrolle auch von einer anders starken Regularisierung stammen. Das Audit belegt keine Trainingseffektivität.

| Aufgezeichnete Frames | Median gepaarte Norm B_7/OLS | Median gepaarte Norm B_7/B_xyz | Median ||g_B7||/||g_BC|| | Aktive B_7-Perturbationen |
|---|---:|---:|---:|---:|
| Train, frühe 5/10/15% | 1,059 | 1,401 | 0,309 | 97/144 |
| Train, spätere 50/85% | 4,075 | 2,154 | 0,331 | 64/96 |
| Valid, frühe 5/10/15% | 1,093 | 1,256 | 0,450 | 48/72 |
| Valid, spätere 50/85% | 2,769 | 2,142 | 0,594 | 32/48 |

Tabellenwerte sind Mediane **gepaarter Quotienten**, keine Quotienten aggregierter Normmediane. Die späteren Abschnitte sind anhand der Demozeit definiert; ihre Kontakt-/Taskphase wurde hier nicht physisch bestimmt.

Alle 60 Frames haben positive BC- und Regularisierergradientennormen; keine undefinierten Normquotienten. B_7 überschreitet den BC-Gradienten nicht um Faktor 10; zwei von 60 Frames liegen unter Faktor 0,1. Die anderen Lossvarianten sind ebenfalls unterschiedlich aktiv. B_7-Gradienten haben einen negativen Kosinus zum BC-Gradienten auf 41/60 Frames (Train früh 19/24, Train später 9/16, Valid früh 7/12, Valid später 6/8). Das zeigt einen lokalen Zielkonflikt der Ableitungen an diesem Checkpoint, **keinen Nachweis einer schädlichen Methode** oder schlechterer Aufgabenleistung.

Ein rein deskriptiver globaler Ausgleich aus allen 40 Trainframes wäre lambda_B7≈0,659 relativ zur alten OLS-Variante beziehungsweise ≈0,665 relativ zu B_xyz. Nur Trainframes bestimmen diese Werte; Valid dient zur Gegenbeschreibung. Ein einzelner Faktor gleicht die abschnittsabhängigen Unterschiede nicht aus: mit 0,659 bleibt das mediane B_7/OLS-Verhältnis später etwa 2,69 auf Train und 1,83 auf Valid, früh etwa 0,70/0,72. **Keine Trainingsparameter wurden daraus ausgewählt.** Ein späterer BC-Vergleich benötigt eine explizite Kontrollbedingung für Regularisierungsstärke und muss deren Kosten/Definition offenlegen; Normgleichheit allein gleicht die Richtungen oder ReLU-Aktivierungen nicht an.

## Fixiertes Verfahren und Nachweise

[Protokoll](PROTOCOL.md) und [Auswahl](selection.json) vor Berechnung fixiert, Seed 4100405. Acht neue Train- und vier neue Valid-Demos; alle 24 zuvor verwendeten Diagnose-/Kalibrierdemos ausgeschlossen. Je fünf Frames, insgesamt 40 Train-/20 Validframes; sechs ±5-mm-Beobachtungsperturbationen je Frame und Lossvariante, insgesamt 360 je Variante. EEF und cube-minus-EEF-Merkmal konsistent verschoben. Es sind **aufgezeichnete Beobachtungen**, keine physisch rekonstruierten Zustände und keine neuen Expertlabels an gestörten Zuständen. Frühe B_7-Gültigkeit überträgt sich damit nicht automatisch auf spätere Frames.

Eingefrorener B0-Endcheckpoint; Architektur unverändert. Offizielle BC-Lossroutine mit l2=1, l1=0, cos=0; rho=0,99, diagnostisches lambda=w=1. Alte I/Expert-OLS-K_xyz-Formel gegen eingefrorenes A/B_xyz und A/B_7; kein Refitting. Beide Policyzweige bleiben im Autogradgraphen. Gesamte Parameterglobalnormen und Kosinus, keine Auswahl einzelner Schichten. Kein Optimizer konstruiert, kein optimizer.step, keine EMA, kein neuer Policycheckpoint.

[Unabhängige Prüfung](verification.json) reproduziert Auswahl/Split, Frameindices, Gradientenstatistiken aus gespeicherten schichtweisen Normen/Skalarprodukten und Aggregationen; Quellen-/Kalibrier-/Datensatzhashes unverändert. Bei der Rekonstruktion von sechs float32-Losswerten wird deren Rundung durch sechs float32-Maschinenepsilon begrenzt, nicht exakte float64-Gleichheit unterstellt. Zentrale Richtungsableitung auf genau einer vorab bestimmten Trainprobe, eigener float64-Netzklon: BC und alle drei Regularisierer **4/4 VERIFIED**, maximaler relativer Fehler 1,84e−9, kein ReLU-Grenzwechsel. Der Klon wird exakt restauriert; das Hauptmodell wird überhaupt nicht verändert. Diese lokale Ableitungsprüfung ist kein Test aller Frames oder aller Parameterkoordinaten.

72.711 Policyparameter. Vorher-/Nachherparameter-SHA256 identisch mit Pilot-Endstand: `6073d5be417959e6f544985fa2565044895ca8ec0c04a95a8583446d7610408b`; Checkpoint-SHA256 unverändert `27a38fc65415d419a060cd0fc529f8f30d82bc36cdf77d54cc79d7a3e52117fa`. Rohdatenhash `6a3562467a0184a945c7676cd01e36bca68f2740c0d23c311235d2abf1a07447`; alle Details in [result.json](result.json), source_hashes.json und verification.json.

Kosten: 2,828 s Worker, 6,012 s Supervisor, CPU mit zwei Torchthreads; keine Simulatorschritte, keine Kalibrierung, null Policyupdates. Worker und Watchdog beendet, Job geschlossen, keine eigene Wachhalteanforderung. Die sechs Stunden lange Aufsicht bleibt bis zur Originaldeadline aktiv.

## Fachliche Entscheidung

Eine konkrete vollständige lokale Antwortmodellierung ist jetzt sowohl physisch als auch hinsichtlich ihres Lossgradienten geprüft, allerdings in begrenzter Domain. Der nächste diskriminierende Schritt ist [eine vorab begrenzte phasengetrennte Domainprobe](../NEXT_DOMAIN_PROBE.md) mit eingefrorenem Modell. Keine Trainingsfreigabe durch dieses Offlineaudit. Das Hauptziel bleibt eine replizierte algorithmische BC-Verbesserung, nicht ein neuer trainierter Checkpoint.

Allgemeine lokale Fehlerdynamikregularisierung und gültigkeitsbegrenzte Korrekturen sind bekannte Forschung ([Stable-BC](https://arxiv.org/html/2408.06246v1), [CCIL](https://arxiv.org/html/2310.12972v2)). Unsere Tabelle ist ausschließlich Projektevidenz eines Checkpoints, keine Aussage dieser Arbeiten und kein Neuheits-/Stabilitätsbeweis.
