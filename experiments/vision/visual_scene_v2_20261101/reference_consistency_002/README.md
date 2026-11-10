# Referenzbilder eingerichtet und bewertet

01.11.2026. Vollständiger Lauf mit 2.000 vorhandenen Validierungsszenen und jeweils drei Kameras. **Kein Training, keine Optimizer-Updates, keine neue neuronale Inferenz.** Vorhandene Daten, Gewichte und Vorhersagen bleiben unverändert. Laufzeit ungefähr 177 Sekunden.

## Was jetzt vorhanden ist

Im Ordner `observations`:

- `empty_reference.npy`: 6.000 objektfreie RGB-Referenzbilder mit passender Kamera, Roboterpose und Beleuchtung.
- `robot_mask.npy`: 6.000 bekannte Robotersilhouetten aus der objektfreien Simulation. Unbekannte Objekte bestimmen diese Masken nicht.
- `foreground_mask.npy`: allein aus RGB-Differenz und Robotermaske abgeleiteter Vordergrund.
- `camera_position.npy`, `camera_rotation.npy`, `K.npy`: vorhandene Simulationskalibrierung.
- `robot_qpos.npy`: sieben Arm- und zwei Greifergelenke; keine unbekannten Objektpositionen.
- `scene_indices.npy`: Zuordnung zum unveränderten ursprünglichen RGB-Datensatz.

Im getrennten Ordner `evaluation_only`:

- `object_ids.npy`: exakte sichtbare Objekt-IDs für die Qualitätsauswertung.
- `full_scene_qpos.npy`: vollständiger Szenenzustand für Reproduzierbarkeitsdiagnosen, vom Bildverfahren nicht gelesen.
- `pre_state_split_results.json`: ursprünglicher Bericht vor der nachträglichen Trennung des vollständigen Szenenzustands vom öffentlichen Roboterzustand. Diese Speichertrennung ändert keine Scores oder Messergebnisse.

Die implementierte Bildprüfung in `../reference_evidence.py` bekommt ausschließlich RGB, leere Referenzbilder, Robotermasken, bekannte Kamerakalibrierung und vorhergesagte Boxen. Exakte Objektmasken werden nur zur Offline-Auswahl der Differenzschwelle auf der Kalibrierungshälfte und zur Qualitätsmessung verwendet. Sie sind kein Eingang der späteren Maskenberechnung.

## Qualität der Vordergrundmasken

Schwelle 8 wurde unter den vorher festgelegten RGB-Normschwellen 8/16/24/32 auf 1.000 Kalibrierungsszenen gewählt. Folgende Werte stammen aus den anderen 1.000 Szenen, also 3.000 Ansichten:

| Messgröße | Ergebnis |
| --- | ---: |
| Mittlerer IoU auf nichtleeren Ansichten | **88,77 %** |
| Gepoolter IoU über alle Pixel | **90,52 %** |
| Pixel-Präzision | **90,70 %** |
| Pixel-Recall | **99,78 %** |
| Objektleere Ansichten mit falschem Vordergrund | **0 / 138** |
| Mittlerer IoU Handkamera | **91,81 %** |
| Mittlerer IoU bei Türmen, alle Kameras | **91,56 %** |

IoU ist Schnittfläche geteilt durch Vereinigungsfläche von geschätzter und echter sichtbarer Objektmaske. Pixel-Recall ist keine Objekt-Erkennungsrate und keine Aussage zur Positionsgenauigkeit. Roboterbereiche einschließlich Zwei-Pixel-Rand werden in beiden Masken identisch ausgespart. Über alle 2.000 Szenen betrifft dies 34.321 von 3.581.461 tatsächlichen Objektpixeln, also 0,96 %. Die Qualitätswerte beziehen sich auf die übrigen Pixel.

Es handelt sich um binären Vordergrund. Aneinander angrenzende Objekte oder Turmteile werden nicht automatisch als einzelne Instanzen getrennt. Schatten und Konturränder können zusätzliche Vordergrundpixel erzeugen. Das jetzige saubere, identisch beleuchtete Simulations-Referenzpaar enthält nicht die Bewegung, Belichtungsänderung und Sensorgeräusche eines realen Aufbaus.

## Nutzen für die Vision-Fehlererkennung

Die unveränderten Vorhersagen werden mit den neuen Bildbelegen geprüft. Bei Fest + Handkamera und exakt 10 % zurückgestellten Vorhersagegruppen ergibt sich:

| Verfahren | Erkannte Fehler | Anteil aller Fehler erkannt | Fehler unter beibehaltenen Gruppen |
| --- | ---: | ---: | ---: |
| Bisherige Seed-Streuung | **126 / 219** | **57,53 %** | **3,61 %** |
| Neue Referenz-Bildprüfung | 96 / 219 | 43,84 % | 4,78 % |
| Auf Kalibrierung gewählte Kombination | 122 / 219 | 55,71 % | 3,77 % |

Die Kombination verwendet wie im vorherigen Versuch 75 % Streuung und 25 % Bildsignal auf kalibrierten Perzentilrängen. Sie findet vier Fehler weniger als die Referenz. Differenz im erkannten Fehleranteil: -1,83 Prozentpunkte, gepaartes Szenen-Bootstrap-95%-Intervall -5,58 bis +2,26 Punkte. Ein Vorteil ist nicht belegt.

Bei separat auf 10 % begrenztem Turmbudget findet die Kombination 23 von 87 Fehlern, die Seed-Streuung 28 von 87. Von 19 gemeinsamen Fehlern mit drei Seeds und höchstens 3 mm Streuung markiert die reine Referenz-Bildprüfung bei global 10 % Budget einen, die Kombination keinen. Die vollständigen Zahlen für beide Kameravarianten stehen in `results.json`.

Das primäre Fehlerkriterium ist weiterhin Position mehr als 10 mm daneben oder falsche Zusatzdetektion. Größen- und Orientierungsfehler allein zählen nicht mit. Eine Vordergrundmaske kann gut mit der gesamten Szene übereinstimmen, während einzelne Boxen innerhalb eines Turms falsch zugeordnet oder platziert sind. Dies ist eine relevante verbleibende Grenze; ihr kausaler Anteil wurde nicht separat gemessen.

## Bewertung

Die Referenzaufnahme und Vordergrundextraktion sind als Grundlage eingerichtet und funktionieren unter diesen Simulationsbedingungen. Sie vermeiden die pauschale Gleichsetzung heller Objektflächen mit dem Tisch. **Die zusätzliche Heuristik ist dennoch keine nachgewiesene Verbesserung der Vision-Fehlererkennung und wird nicht als Entscheidungsregel aktiviert.**

Für den nächsten Entwicklungsschritt sollte die vorhandene bessere Vordergrundmaske objektweise mit den projizierten Boxen in mehreren Ansichten verglichen werden, einschließlich fehlendem Vordergrund außerhalb aller vorhergesagten Boxen. Eine Instanzzuordnung und die Bewertung von Größe/Orientierung wären zusätzliche Ziele. Dafür braucht es eine neue getrennte Entwicklungs-/Prüfaufteilung, statt die jetzige Hälfte wiederholt zu optimieren. Hier wurde nichts Weiteres gestartet.

Die bisherigen Validierungsdaten wurden zuvor zur Checkpoint-Auswahl und zur Diagnose genutzt. Das Ergebnis ist ein Entwicklungsvergleich, keine unabhängige Schlussprüfung. Masken liefern keinen Nachweis kollisionsfreien Raums und keine Hardwarefreigabe.

## Reproduzierbarkeit und Abbildungen

1.960 Szenen wurden RGB-bitgenau reproduziert. Bei 40 Szenen gab es ausschließlich einzelne Rundungsabweichungen: maximal ein Helligkeitswert pro Farbkanal und höchstens zwölf geänderte Kanäle pro Szene über alle drei Bilder. Die erlaubte Obergrenze war 32. Die alten RGB-Bilder blieben die Eingabe der Maskenprüfung und der gecachten Modellvorhersagen. Positionen, Größen, Kamerastrahlen und diskrete Eigenschaften waren exakt gleich; die größte Rotationsmatrix-Abweichung betrug 1,37e-14.

`rgb_pairing.csv` dokumentiert jede Szene. `results.json` enthält Daten-, Vorhersage-, Quellcode- und Artefakthashes. `capture_source.py` und `evidence_source.py` sind die tatsächlich ausgeführten Quellkopien. Die aktuelle Erfassungsfunktion wurde anschließend nur so geändert, dass sie direkt den Roboterzustand statt des vollständigen Szenenzustands im Eingabebereich speichert.

- `reference_examples.png`: RGB, leere Referenz, Robotermaske, abgeleiteter Vordergrund und Abweichungen zur echten Objektmaske. Bewusst ausgewählte Beispiele, keine Zufallsstichprobe.
- `fixed_wrist_comparison.png` und `fixed_comparison.png`: Fehlererkennung bei gleichen Budgets.
- `segmentation_views.csv`: Qualitätswerte je Ansicht.
- `fixed_objects.csv`, `fixed_wrist_objects.csv`: objektweise Diagnosesignale.

25 Tests bestanden. Das übergeordnete Dokument `../REFERENCE_IMAGES.md` enthält Ablauf, Grenzen und Befehle zur Reproduktion.
