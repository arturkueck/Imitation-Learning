# Nächste Schritte zur Auswahl

Alle folgenden Schritte sind vorbereitet, aber nicht gestartet. Die Diagnoseausgaben sind nicht mit einer Roboterfreigabe verbunden. Insbesondere wird kein Training ohne neue ausdrückliche Anweisung gestartet.

## A – Gemeinsame Fehler durch Bildkonsistenz aufdecken (Empfehlung)

**Ziel:** Fehler finden, bei denen sich alle drei Modelle einig sind, insbesondere bei Türmen.

**Arbeit:** Vorhergesagte Boxen mit der bekannten Kamerakalibrierung in die ursprünglichen Bilder projizieren. Silhouetten-/Kantenkonsistenz, Sichtbarkeit und Widersprüche zwischen Perspektiven prüfen. Robotermasken und verdeckte Flächen berücksichtigen; fehlende Bildbelege als unbekannt behandeln. Zunächst auf bisherigen Validierungsdaten gegen tatsächliche Fehler testen. RGB-Kanten sind keine verlässlichen Objektmasken; diese Grenze muss getrennt gemessen werden. Größen-/Eckenstreuung als zusätzliche Baselines vergleichen.

**Lieferumfang:** Zusätzliche objektweise Widerspruchssignale, Fehler-Erkennungsplots und Vergleich mit der jetzigen Ensemble-Regel bei gleichem Anteil zurückgestellter Vorhersagen. Stratifizierung nach Türmen und Verdeckung.

**Training:** keines. Keine Armbewegung erforderlich. Noch keine Aussage über Montagegenauigkeit.

## B – Unabhängige Prüfung und belastbarere Schwellen

**Ziel:** Prüfen, ob die jetzt gewählten Schwellen auf frischen Szenen funktionieren.

**Arbeit:** Regel und Checkpoints einfrieren, einen neuen separaten Diagnose-Datensatz mit intakten RGB-/Sichtbarkeitsdaten erzeugen. Türme, Verdeckungen und andere Quaderabmessungen getrennt prüfen. Vorhandene reservierte Schlussprüfungen bleiben erhalten. Unsicherheit der Fehlerquoten per Szenen-/Familien-Bootstrap statt unabhängiger Objektannahme ausweisen. Bei einer späteren Neukalibrierung wiederum neue Kalibrierungs- und Prüffamilien trennen.

**Lieferumfang:** Unabhängiger Diagnosebericht einschließlich gemeinsam übersehener Objekte und Ausfallrate je Anordnung. Kein Nachjustieren auf dem neuen Prüfsplit.

**Training:** keines; benötigt neue Simulationsbilder. Sinnvoll vor jeder Aktivierung einer Entscheidungsregel.

## C – Unsicherheitsanzeige und gezielte Handkamera-Aufnahmen

**Ziel:** Für ein unsicheres Objekt nachvollziehbar ein weiteres Bild anfordern.

**Arbeit:** Im Frontend Seed-Unterstützung, Positionsstreuung und geometrische Widersprüche anzeigen. Keine ungeprüften Prozentangaben für Positionszuverlässigkeit. Anschließend Zielbereiche an den vorhandenen Blickplaner übergeben. Zuerst den bislang unbekannten Bewegungskorridor um die Roboterbasis kalibriert erfassen. Zusätzlich prüfen, ob das aktuelle Vision-Modell mit veränderten Handkameraposen umgehen kann: Kalibrierte Strahlen allein belegen keine Generalisierung auf neue Posen. Neue Aufnahmen zunächst separat mit zwei festen Ansichten inferieren; zeitliche Fusion erst danach untersuchen.

**Lieferumfang:** Objektbezogene Anzeige plus begrenzter Simulationsvergleich vor/nach zusätzlichem Bild, mit gemessenem tatsächlichem Fehler und Unsicherheitsänderung. Bewegungen bleiben gesperrt, solange die Ganzarmbahn nicht freigegeben werden kann.

**Training:** zunächst keines. Eine veränderte Perspektive kann auch zu einer schlechteren Schätzung führen; das wird mitgemessen. Für den ersten Versuch nach A/B geeignet.

## D – Direkte Unsicherheitsausgabe und flexiblere Bildanzahl

**Ziel:** Beobachtungsmehrdeutigkeit direkt modellieren und mehrere Handkameraaufnahmen nutzen.

**Arbeit:** Architekturvorschlag mit Positionsmittelwert und positiver Streuung pro Achse; probabilistische Loss mit Schutz vor degenerierter Streuung. Kamera-/Zeit-Token für wechselnde Ansichten, Maskierung variabler Bildanzahl. Vergleich gegen die unveränderte Architektur bei festen Daten, Seeds und Auswahlregeln. Neue Kameraposen und gezielte Verdeckungen müssen im Datendesign berücksichtigt werden.

**Lieferumfang zunächst:** Architektur-, Daten-, Ressourcen- und Evaluationsplan mit erwarteten Ausgabedimensionen, Parametern, Loss-Gewichten sowie Kalibrierungsplots. Ein späteres Training wäre ein gesonderter Auftrag.

**Training:** für die spätere Umsetzung erforderlich, jetzt ausdrücklich nicht gestartet. Direkte Unsicherheit ersetzt weder die Ensemble-Diagnose noch die Kollisionsprüfung.

## Empfohlene Reihenfolge

A, danach B; anschließend C. D erst anhand dieser Ergebnisse entscheiden. Die jetzigen Daten sprechen dafür, zuerst gemeinsame geometrische Fehler zu erkennen, statt lediglich die Positionsstreuung als endgültiges Unsicherheitsmaß einzusetzen.
