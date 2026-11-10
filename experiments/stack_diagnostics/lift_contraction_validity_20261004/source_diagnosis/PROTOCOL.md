# Lift: Machbarkeit einer gültigkeitsgewichteten BC-Regularisierung

Status: aktive Machbarkeitsprüfung, autorisiert am 04.10.2026. Der abgebrochene Diffusionslauf bleibt beendet.

## Forschungsfrage

Kann eine ausschließlich auf Trainingsdemos geschätzte Gültigkeitsgewichtung verhindern, dass der bestehende Kontraktionsloss eine falsche Aktionsantwort erzwingt? Robustheit ist das primäre Ziel; weniger Updates und weniger Rechenzeit sind getrennte sekundäre Fragen. Ein neues Policy-Netz ist nicht der Beitrag.

Vor neuen Policy-Trainings wird die zentrale Annahme geprüft: Der aus Experttrajektorien regressierte Zusammenhang `ΔEEF ≈ a_xyz @ K + b` muss auch kleine Änderungen der Aktion bei gleichem Zustand sinnvoll beschreiben. Hohe Vorhersagegüte entlang Experttrajektorien reicht dafür nicht aus.

## Eingefrorene Diagnose

- Offizieller Lift-PH-v1.5-Datensatz, unveränderter 180/20-Demo-Split; SHA256 und Splitnamen werden gespeichert.
- Fünf innere Folds, deterministisch mit Seed 41004 über die 180 Trainingsdemos permutiert. Keine Frames derselben Demo in Fit und innerer Prüfung. Die äußeren 20 Validierungsdemos werden lediglich zur unabhängigen Diagnose des vorhandenen Fits verwendet, nicht für Gewichte oder Schwellen.
- Gleiche lineare Regression wie bisher, mit Intercept. In-Sample-, Out-of-Fold- und äußere R² sowie Vektorfehler werden getrennt protokolliert.
- Simulatorprobe: zwölf vorab deterministisch ausgewählte Trainingsdemos, je drei Zeitpunkte bei 20%, 50%, 80% ihrer Länge. Zeitanteile sind keine bestätigten Kontaktphasen.
- Jede Variante lädt das Demo-XML und den initialen Simulationszustand neu, spielt den Expertpräfix ab und stellt den gespeicherten Ankerzustand wieder her. Dadurch wird Controller-/Gripperhistorie auf dieselbe Weise erzeugt. Vor jedem Schritt wird die Beobachtungsrekonstruktion geprüft.
- Pro Anker zwei identische Referenzschritte sowie ±0,1 Änderungen jeder der drei Translationsaktionskomponenten, auf [-1,1] begrenzt. Die tatsächlich ausgeführten Aktionsdifferenzen werden protokolliert. Vergleich: `(a_plus-a_minus) @ K` gegen `EEF_next_plus-EEF_next_minus`.
- Zusätzlich wird die Referenztransition mit der gespeicherten `next_obs` verglichen. Ein reproduzierbarer Reset allein beweist keine vollständige Rekonstruktion der Datenerhebung.
- Die nach innerer Vorhersagegüte niedrigste Fehlerhälfte wird nur als vorab definierter Diagnosevergleich genutzt. Diese Ergebnisse dürfen die Gewichtshypothese verwerfen; sie dienen noch nicht zur Hyperparameteroptimierung.

## Entscheidung vor Policy-Training

1. Rekonstruktion: maximaler EEF-Beobachtungsfehler vor Schritt ≤10 µm; identische Referenzzweige ≤1 µm voneinander. Referenz-Next-Obs-Abweichung wird mitberichtet; über 0,5 mm Median macht die Counterfactualprobe vorläufig ungültig und verlangt eine Replaykorrektur.
2. Aktionsantwort: in mindestens 80% der nichtdegenerierten Achsenproben Kosinus ≥0,8 und relativer Vektorfehler ≤0,5. Eine gemessene Antwort <10 µm gilt als degeneriert und wird getrennt gezählt; sie darf die Quote nicht erhöhen.
3. Für B3 muss die niedrige Out-of-Fold-Fehlerhälfte ebenfalls Gate 2 erfüllen. Vorhersagefehler auf Demos wird nicht als Beweis für kontrafaktische Gültigkeit bezeichnet.

Bei Nichterfüllung kein B3-Training mit diesem K und keine Suche nach günstigen Gates. Stattdessen den Fehler dokumentieren, die Dynamikannahme überarbeiten oder die einfachere Sensor-Augmentation als getrennte Hypothese prüfen. Ein negativer Gatebefund ist ein wissenschaftliches Ergebnis.

## Begrenzter Pilot bei bestandener Machbarkeit

B0 BC, B1 strukturierte Sensor-Augmentation, B2 bisheriger konstanter Kontraktionsloss, B3 eingefrorene Gültigkeitsgewichtung. Je ein gepaarter Pilotseed 41004, höchstens 2.000 Updates pro Arm, gleiche 256×256-MLP, Batch 100, Adam und Datenmaske wie bestehendes Lift-BC. λ=1, Radius 5 mm, Zielratio 0,99 aus der bestehenden Implementierung, keine Suche. Zusatz-RNG unabhängig; Initialparameter und Batchreihenfolge prüfen. Frische Verzeichnisse, keine Wiederaufnahme alter Checkpoints. Vor Start genaue Gewichtsdefinition und Evalfälle ergänzen und einfrieren.

Pilotlauf höchstens zwei Stunden inklusive Evaluation, tatsächliche Updates, Losses, Trainings-/Fit-/Evaluationszeit, Dataset-/Source-/Checkpoint-Hashes speichern; finale festgelegte Checkpoints evaluieren. Keine Best-Checkpoint-Auswahl, kein automatischer Retry. Erst dieser Pilot liefert die Aufwandsschätzung für einen späteren Vergleich mit mindestens drei gepaarten Seeds. Er kann allein keine robuste Verbesserung belegen.

## Überwachung

Auf Nutzerwunsch soll ein Heartbeat alle 30 Minuten aktive Diagnose-/Trainingsprozesse, Fortschritt und Fehlermeldungen prüfen, das Protokoll verfolgen und bei abgeschlossenem Lauf die Ergebnisse aufarbeiten. Fehler bleiben erhalten; fehlgeschlagene Jobs werden nicht automatisch neu gestartet. Ein Trigger kann Abstürze erkennen, aber nicht verhindern. Die lokale Prozessaufsicht begrenzt die Laufzeit unabhängig davon. Nach abgeschlossener begrenzter Arbeit wird der Trigger pausiert.
