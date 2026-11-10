# 100 neue Entwicklungsszenen: Auswertung abgeschlossen

Lauf: `benchmark_001`. Keine neuen Modellgewichte, keine Endtestauswertung. Alle100 vorab zugeordneten Familien wurden vollständig bearbeitet und geprüft. Vier Szenen waren leer; in allen96 nichtleeren Szenen konnten beide zentrierten Seitenfahrten aufgenommen werden. Die100 Hauptszenen sind von der Vier-Szenen-Vorprüfung und sämtlichen bisherigen Trainings-/Validierungsfamilien getrennt. Ensemble: die drei eingefrorenen V4-B-Checkpoints.

## Hauptergebnis

Mehr Ansichten verbessern die mittlere Geometrie, aber die Übernahmeprüfung schützt gute Schätzungen noch nicht zuverlässig. Die gegenwärtige adaptive Regel spart fast keine zweite Seite. Ein bloßes Weitertrainieren des bisherigen Vision-Modells ist deshalb nicht der gezielte nächste Schritt.

Alle100 Szenen, einschließlich vier leerer Szenen:

| Verfahren | Mittlerer Szenenfehler | Median |95. Perzentil | Um >1 mm-äquivalent schlechter als Anfang |
|---|---:|---:|---:|---:|
| Erste Schätzung |8,862|5,337|20,929|–|
| Geometrie nach einer Seite |8,404|4,708|22,111|13/100|
| Geometrie nach beiden Seiten |8,112|4,045|25,211|19/100|
| Adaptive Geometrie |8,117|4,045|25,211|19/100|
| Neuronale Fusion der Endbilder |9,354|7,298|23,469|60/100|

Szenenfehler in mm-Äquivalenten: kombiniert Zentren, Eckengeometrie und fehlende/zusätzliche Objekte; keine reale Platziergenauigkeit. Die neuronale Vergleichsfusion nutzt die ursprünglich vorgesehenen Endbilder, die Geometrie hingegen Hinweg-Bildfolgen. Kein Vergleich bei identischer Bildanzahl. Detaillierte nichtleere/stratifizierte/gleich verfügbare Teilmengen in summary.json.

Beide Seiten verbessern den Mittelwert gegenüber dem Anfang um8,47 %, verschlechtern aber das95. Perzentil um20,46 %.53 Szenen verbessern sich um mehr als1 mm-äquivalent;19 verschlechtern sich um mehr als1 mm-äquivalent. Insgesamt25 Szenen verschlechtern sich um irgendeinen Betrag oberhalb der vorab festgelegten numerischen Toleranz. Die vier leeren Szenen bleiben korrekt leer und unverändert.

## Bringt die zweite Seite tatsächlich mehr?

Unter den96 Szenen mit beiden Seiten hilft die zweite gegenüber der ersten in30 Fällen um mehr als1 mm-äquivalent, schadet in14 und ändert52 nur innerhalb±1 mm-äquivalent. Der mittlere Zusatzgewinn beträgt0,304 mm-äquivalent. Damit ist weder „immer beide Seiten“ noch „immer nur eine“ aus diesen Entwicklungsdaten gerechtfertigt.

Die Anfangsregel fordert90-mal zwei Seiten,6-mal eine und4-mal keine an. Nach der ersten Aufnahme wählt sie insgesamt94-mal zwei Seiten, nur2-mal eine und4-mal keine. Bei den nichtleeren Szenen nutzt sie in97,9 % beide Seiten. Das ist praktisch noch keine wirksame Auswahl nach erwartetem Zusatznutzen.

## Wo die Qualitätsentscheidung versagt

Auf festen anfänglichen Objektzuordnungen wurden548 Objekt-Updates geprüft.357 Kandidaten wurden übernommen. Davon sind76 nach der nachträglichen GT-Auswertung um mehr als1 mm-äquivalent schädlich:21,3 % der übernommenen Kandidaten.174 angenommene Kandidaten sind um mehr als1 mm-äquivalent nützlich,107 liegen dazwischen. Von191 verworfenen Kandidaten wären24 nützlich gewesen.

Diese lokale Update-Diagnose nutzt unbeschnittenen Positionsfehler +0,25×Eck-RMSE auf festgehaltenen GT-Zuordnungen und ist nicht mit dem oben aggregierten Szenenmaß gleichzusetzen. Nicht zugeordnete Erkennungen bleiben im Szenenmaß, aber außerhalb dieses lokalen Nenners.

45 adaptive Ergebnisse erfüllen den regelbasierten geometrischen Unterstützungstest; drei davon verschlechtern dennoch den Anfang um mehr als1 mm-äquivalent. Der Unterstützungstest ist folglich keine kalibrierte Erfolgswahrscheinlichkeit. „Weiterhin unsicher“ muss eine verbindliche Sperre für die Verwendung zur Platzierung bleiben; auch ein bestandener RGB-Konsistenztest beweist noch keine korrekte Geometrie.

## Unterschiede zwischen Szenen

Die Stichprobe enthält Objektzahlen0/1/2/3/4/5 mit4/22/19/21/18/16 Szenen sowie22 gemischte,28 verstreute,35 Turm- und15 Wand-Anordnungen.18 Szenen enthalten lange/dünne Quader,82 reguläre Geometrien.

- Reguläre Geometrien: mittlerer Szenenfehler5,577 →4,490 nach beiden Seiten.
- Lange/dünne Quader:23,830 →24,612 durch die Geometrie, aber17,622 durch die neuronalen Endbilder. Hier ist das Verhalten anders; Ergebnisse dürfen nicht nur über alle Formen gemittelt werden.
- Gemischte Anordnungen und Türme profitieren im Mittel von der Geometrie. Bei Wänden steigt der Mittelwert4,732 →5,702.

Diese Untergruppen sind klein und teilweise gekoppelt (lange Quader werden ausschließlich verstreut erzeugt). Daraus folgt keine isolierte kausale Aussage über Form oder Anordnung. Es sind Entwicklungsbefunde zur gezielten nächsten Untersuchung, keine Endtestbelege.

## Empfehlung für den nächsten Schritt

1. Vision-Ensemble zunächst einfrieren und die Bewertung/Übernahme einer Korrektur gezielt verbessern. Schädliche Änderungen und die beste frühere Zwischenlösung sind dafür die relevanten Ziele, nicht nur ein kleinerer Bildkantenfehler.
2. Anschließend ein kleines Qualitäts-/Zusatznutzen-Modell für Aufnahme- und Übernahmeentscheidungen konzipieren. Es braucht frische, getrennte Trainings-/Validierungs-/Kalibrierungsfamilien; diese100 Entwicklungsfamilien dürfen dafür nicht in den Trainingssplit wandern. Eingaben dürfen nur bereits beobachtete Bilder, Vorhersagen, Kameraposen und Trackingqualität enthalten.
3. Ein späteres Vision-Training gezielt auf die neue zentrierte Kameraführung, Bildfusion und schwierige Geometrien ausrichten. Nicht allein die Epochzahl des bisherigen Laufs erhöhen. Die jetzige Evaluation trennt mögliche Ursachen, beweist aber nicht, welche Trainingsänderung sie beheben wird.

Kein Anschluss-Training, keine Schwellenanpassung und keine Veröffentlichung wurden automatisch gestartet.

## Prüfung und Laufzeit

15 Tests sowie parallele Vier-Szenen-Vorprüfung bestanden. Nach einem dokumentierten Speicherfehler mit vier Workern erfolgte genau eine technische Wiederaufnahme mit zwei Workern, unveränderten100 Familien-IDs und identischen erhaltenen Anfangssamples. Die Ausführung mit zwei Workern dauerte949,85 Sekunden (15min50s), ohne ursprüngliche Vorbereitung und Fehlstart.

Abschlussprüfung:100 eindeutige neue Entwicklungsfamilien, alle1.006 registrierten Szenendateien, Quellcodesiegel und drei unveränderte Modellcheckpoints geprüft.192 Analysepräfixe ohne spätere/Prüf-/Rückweg-Bilder im Fit und192 exakte Rückkehrmanöver verifiziert. Größte gemessene Zielabweichung0,5383°, vorhergesagte Gruppe in den aktiven Bildern im Sichtfeld. Null neuronale Optimizer-Updates. Technischer Wiederaufnahmebericht und unveränderte Datensiegel bleiben erhalten.

Artefakte unter `benchmark_001`: REPORT.md, summary.json, scenes.csv, object_updates.json, benchmark.png, benchmark_de.png, verification.json, evaluation_config.json und Rohdaten/Zwischenstände pro Szene. Die ersten sechs vorab festgelegten Szenen haben GIF-/3D-Ausgaben. Diese Dokumentation kann als Grundlage für einen späteren Website-Eintrag dienen; die Website wurde nicht verändert.
