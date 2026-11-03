# Gezielte Seitenansichten – technische Diagnose, 02.11.2026

Kamera nach Roboterrechts und zum Ziel nach links ausrichten; umgekehrt für Roboterlinks. Rechts/links beziehen sich auf die horizontale Richtung von Roboterbasis zum vorhergesagten Ziel. Die Kamera blickt entlang ihrer tatsächlichen MuJoCo-Achse −Z. Eine reine Kameradrehung oder ein großer Versatz allein genügen nicht.

Das Ziel ist die unsicherste vorhergesagte Objektgruppe (fehlende Ensemble-Unterstützung/Streuung), nicht die echte Objektposition. Kandidaten koppeln seitlichen Versatz und Ausrichtung auf dieses Ziel. Die Höhe wird auf eine flache Seitenansicht begrenzt. Start- und Zielblickstrahlen sowie der tatsächliche Kameraweg sind im interaktiven 3D-Abgleich einblendbar. Die Zwischenbewegung ist eine Gelenkbahn; ein dauerndes Nachführen der Blickachse während der Fahrt ist nicht nachgewiesen.

| Ansicht | Kameraversatz | Blickhöhe über Zielhorizontalen | Zielabweichung der optischen Achse | Satzfehler vor → nach (mm-äq.) |
| --- | --- | --- | --- | --- |
| Kamera rechts → Blick links | 48.6 cm | 15.9° | 0.17° | 12.43 → 18.23 |
| Kamera links → Blick rechts | 32.8 cm | 17.1° | 1.47° | 12.43 → 51.75 |

Der kombinierte Satzfehler berücksichtigt Position, Ecken und fehlende/zusätzliche Objekte. Beide Seitenbilder verschlechtern in dieser einen Diagnoseszene das eingefrorene Modell. Die aktualisierte Vorhersage wird deshalb nicht als Produktionskorrektur übernommen. Diese zwei Beispiele belegen keine Generalisierung. Drei unveränderte M2-Checkpoints mit geprüften Hashes werden ausgewertet; es gibt keine Optimizerupdates und kein neues Training.

## Basisansicht: blockiert

Die Kamera näher zur Basis und von dort zum Ziel ausgerichtet ist als eigener Kandidatenmodus implementiert. Die erste Suche fand keine gültige Haltung. Eine zweite diagnostische Suche mit sechs gültigen IK-Ausgangshaltungen und bis zu 40° Blickhöhe fand ebenfalls keine gültige Haltung (52 Kandidaten). Es wurde keine Basisfahrt ausgeführt und kein Basis-GIF erfunden. Dies beweist keine globale Unerreichbarkeit; der begrenzte Planer hat keine gültige Lösung gefunden.

## Bewegung und Sicherheitsgrenze

Beide ausgeführten Wege wurden einschließlich Arm, Greifer und Kameragehäuse gegen Gelenkgrenzen, Selbst- und Umweltkollisionen geprüft. Die Replay-Zustände wurden erneut geprüft; native Robot-Umwelt-Penetrationen: 0. Der rechte Weg enthält 920, der linke 898 vollständige Wegprüfungen. Dies nutzt ausdrücklich Simulatorreferenz und diskrete konservative Bahnprüfungen, keine formale Garantie für kontinuierliche Bewegung oder echte Hardware.

Die unabhängige rein visuelle Freigabe blockiert weiterhin mit `initial_arm_volume_unverified / unknown_space`. Nicht beobachteter Freiraum gilt nicht als frei. Die Demonstration umgeht diese Sperre nicht im visuellen Betrieb; Simulatorreferenz ist als eigener Diagnosemodus bezeichnet.

## Nächster fachlicher Schritt

Diese Blickfamilien mit tatsächlichen Kameraposen als Trainingsdaten abdecken und die Fusion/Übernahme zusätzlicher Bilder separat validieren. Verbesserung muss auf unabhängigen Szenen und einer Kalibrierungsmenge nachgewiesen werden. Bis dahin bleibt die gelernte aktive Produktionsentscheidung deaktiviert. Das ist Vorbereitung, kein gestarteter Trainingslauf.
