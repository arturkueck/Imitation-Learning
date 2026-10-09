# Vollständige partielle Aktionsantwort: vorab bestimmter Vergleich bestanden

Status COMPLETE; physische Zustände und primäre Berechnung unabhängig VERIFIED. Null Trainingsupdates. Eingefrorener finaler B0-Checkpoint nach 2.000 Updates. Vier neue Demos, von allen früheren Diagnose-/Kalibrierungsdemos getrennt: demo_59/demo_152 ausschließlich Identifikation, demo_187/demo_104 Gegenprüfung. Je drei vorab fixierte frühe Anker, insgesamt zwölf. Alle Zustands-, Controller-, Hilfsfeld-, Wiederholungs- und Kontaktgates bestanden; 408 vollständige gespeicherte Zweige. Rank der Aktionsanregung sieben. A/B und Kontroll-B_xyz ausschließlich auf dem Identifikationsanteil angepasst.

## Primärer Projektbefund

Auf 36 vollständigen Policyreaktionen der sechs Gegenprüfungsanker:

| Vorhersage | Median absoluter Ratiofehler | p90 | Falsche Entwarnungen / Strafen bei Ratio 0,99 |
|---|---:|---:|---:|
| I / Expert-OLS-K_xyz | 0,002163 | 0,009529 | 1 / 0 |
| I / vorheriges K_partial_xyz | 0,004557 | 0,006292 | 0 / 12 |
| A / neu identifiziertes B_xyz | 0,004812 | 0,006231 | 0 / 12 |
| A / neu identifiziertes B_7×3 | 0,000389 | 0,001362 | 0 / 0 |

Der vorher festgelegte Vergleich A/B_xyz gegen A/B_7 verringert den medianen Ratiofehler um **91,9%**, verbessert alle **6/6** Gegenprüfungsanker und besteht damit die Regel ≥20% geringerer Fehler plus Verbesserung an ≥4/6 Ankern. B_xyz entspricht numerisch den ersten drei Zeilen von B_7: der Vergleich isoliert hier zusätzliche Aktionskomponenten bei gleichem A und gleicher Translationskalibrierung. Die Beobachtung betrifft lokale Modellvorhersagen; sie ist kein Gewinn von 91,9% Taskerfolg, Konvergenz oder Robustheit. Die 36 Perturbationen stammen aus nur zwei Gegenprüfungsdemos und einem eingefrorenen Entwicklungscheckpoint.

## Welcher ausgelassene Anteil wichtig ist

Isolierte partielle Antworten bestehen bei den drei Translations- und drei Rotationskomponenten jeweils 6/6 Gegenprüfungen. Die medianen relativen Fehler der Rotationsantworten betragen 4,11% / 2,12% / 4,65%, der Translationsantworten 0,66% / 0,90% / 0,72%. Der Gripper bewirkt an allen sechs freien Gegenprüfungsankern eine degenerierte, hier exakt null gemessene EEF-Antwort: **0/6 bestanden, 6/6 degeneriert**, ausdrücklich im Nenner. Gesamt daher 36/42 bestandene isolierte Antworten; 36/36 nichtdegenerierte. Keine behauptete Gültigkeit des Grippergains nach Kontakt.

Die Aktionsinterventionen belegen eine lokale EEF-Translationswirkung von Rotationskommandos. Eine ergänzende, als explorativ markierte Zerlegung der vollständigen Policyvorhersage ergibt median 0,0294 mm modellierten Rotationsbeitrag, 0 mm Gripperbeitrag. Die vormals pauschale offene Frage „Rotation/Gripper“ ist hier präzisiert: **Rotation erklärt den nachgewiesenen ausgelassenen Anteil; der Gripper ist in dieser frühen kontaktfreien Domain uninformativ.** Die reine Translationskalibrierung genügt deshalb dem vollständigen Policy-Loss nicht.

A=I bleibt an diesen neuen freien Ankern kompatibel: medianer relativer Fehler 0,1608%, p90 0,3446%. Das beweist keine Identität oder lokale Linearität in anderen Phasen. Sättigung/Asymmetrie der Gripperproben und tatsächliche geclippte Aktionen sind gespeichert. Kein allgemeines Robustheitsversprechen aus dem kleinen lokalen Modell.

## Wissenschaftliche Entscheidung

Die Hypothese, dass die ausgelassenen Rotationsaktionen die fehlerhafte Lossbewertung verursachen können, ist in dieser Domain durch eine vorab bestimmte Gegenprüfung gestützt. Ein bloßer Austausch von K_xyz ist keine hinreichende Korrektur. Ein konkreter Methodenkandidat ist die vollständige finite Differenz `delta_next ≈ delta@A + (pi(o_delta)-pi(o))@B_7`, statt Beschränkung auf die ersten drei Aktionskomponenten. Das ist eine konkret begründete Änderung am bestehenden BC-Regularisierer, noch keine trainierte oder robust verbesserte BC-Methode.

Die nächste minimale Diskrimination prüft **aus diesem Modell berechnete Korrekturaktionen tatsächlich im Simulator** auf neu reservierten Demos. Alle Arme korrigieren nur Translation, um zusätzliche Freiheitsgrade als Erklärung zu vermeiden. Ein solcher Oracle-Mechanismustest prüft die Korrekturwirkung; danach bleiben Domainabdeckung und effektive Gradientenskala als Trainingsgates offen. [Festgelegter Folgeauftrag](../NEXT_CORRECTION_PROBE.md).

Die allgemeine Modellierung lokaler Fehlerdynamik ist durch [Stable-BC, inspizierter Primärvolltext](https://arxiv.org/html/2408.06246v1) motiviert; korrigierende modellbasierte Labels und Gültigkeitsbegrenzung existieren in [CCIL, Primärvolltext](https://arxiv.org/html/2310.12972v2). Weder ein B_7-Fit noch die allgemeine Korrekturidee werden als neue Erfindung beansprucht. Eigene Evidenz hier: reproduzierbare Diagnose des ausgelassenen Aktionsanteils und seine konkrete Wirkung auf die lokale Lossbewertung. Hauptaussage unverändert: noch kein robuster neuer Trainingsalgorithmus nachgewiesen.

## Kosten und Provenienz

235,53 s Workerzeit, 238,21 s inklusive Prozessaufsicht. 408 reset_to-/XML-/Präfixrekonstruktionen, 1.666 Präfixaktionen, 408 Prüfaktionen, 51.850 Physiksteps, 432 IK-Iterationen, 156 Policyaufrufe. Physiksteps exakt 25 × (Präfix- plus Prüfaktionen). Erfasster Runtimepfad lite_physics=false; Instrumentierung unterstützt zusätzlich step1/step2. Kein technischer Ersatzlauf dieses Folgeversuchs. Eigener Worker und Watchdog beendet; Sessionaufsicht/Heartbeat bleiben bis 15:11:19 Berlin aktiv.

Auswahl und Quellen wurden vor Launch gehasht; selection.json/source_hashes.json, result.json, verification.json und prediction_verification.json erlauben Daten-/Checkpoint-, Zustands-, Fit-/Gegenprüfungs- und primäre Ergebnisprüfung. Physischer Endschritt-Kontakt zusätzlich nach letztem Integrationsschritt geprüft. Kein Training, keine Änderung historischer Artefakte oder Gates.
