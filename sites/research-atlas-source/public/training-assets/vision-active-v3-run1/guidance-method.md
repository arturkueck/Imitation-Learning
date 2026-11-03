# Verbesserte Kameraführung – Simulation, keine Modelltrainierung

Gleiche 200 Entwicklungsfamilien wie pilot_002; **47 → 147 zusätzliche Ansichten**. Jede neue gültige Zielhaltung wurde danach tatsächlich gerendert und anhand der gespeicherten Kamerapose überprüft. Keine Optimizerupdates, keine neue aktive Produktionspolicy und kein unabhängiger Endtest.

| Blickwunsch | Vorher | Neue Führung |
| --- | ---: | ---: |
| Rechts | 12 / 40 | 28 / 40 |
| Links | 5 / 40 | 24 / 40 |
| Basis | 0 / 40 | 27 / 40 |
| Erhöht | 13 / 40 | 37 / 40 |
| Kontrollblick
(unscharf) | 17 / 40 | 31 / 40 |

## Änderung und Ursache

Die bisherige Bewegungsüberapproximation benutzte 32 Teilintervalle pro Gelenksegment. Eine vorab getrennte Diagnose mit 128 Teilintervallen und gleicher Bank ergab 107 statt 47 gültige Ansichten unter den alten Blickfeldregeln. Dies zeigt den wesentlichen Anteil zu grober Bewegungshüllen. Die neue Führung verwendet 128 Intervalle mit **unverändertem analytischem Bewegungsbound und unveränderten Abständen** (Umwelt 10 mm, Selbstkollision 2 mm). Es wurde keine Sparse-Sampling-Freigabe eingeführt.

Zusätzlich alle geeigneten erhaltenen Posen statt höchstens drei pro Richtung: 26 statisch zertifizierte Wege. Für Basisansichten wurden objektunabhängige Arbeitsbereichsanker, zusätzliche IK-Ausgangshaltungen und Kamerarollwinkel geprüft. Blockierte Ziele werden nicht durch eine andere Blickrichtung ersetzt.

Die Handkamera wird von der Bankhaltung aus auf die unsicherste aktuelle V3-Ensemble-Vorhersage ausgerichtet. Bei Bedarf löst der Planer eine kleine Zielkorrektur und prüft deren gesamten zusätzlichen Gelenkweg gegen die vollständige Referenzwelt. Die erreichte Position darf sich dabei höchstens 15 mm verschieben. Auch nach der Korrektur müssen Blickfeld, gewünschte Seite, mindestens 20 cm Kameraversatz, Blickhöhe und optische Zielabweichung bestehen. Grenzwert optische Abweichung: 3°; gemessen maximal 2.953°. 116 Ansichten wurden nachgeführt.

## Bewegung und Erfassung

Die statische Bank umfasst Selbst-/Umweltprüfung von Arm, Greifer und Kamerahalterungsproxy. Pro Szene werden sämtliche Objekte mit der konservativen analytischen Bewegungshülle geprüft. Die Nachführung erhält einen vollständigen separaten Edge-Check. Zusätzlich 17 unabhängige vollständige Weltprüfungen auf neu zugelassenen, nach Blickfamilie/Anordnung geschichteten Fällen; diese sind kein Ersatz für die übrigen Zertifikate. Alle 3447 gespeicherten Replay-Zustände wurden zusätzlich auf native Robot-Umwelt-Penetration geprüft: kein Fehler.

Alle 147 angenommenen Ansichten wurden tatsächlich aufgenommen. Maximum Pose-Abweichung zwischen Plan und gerendertem Zustand: 0.000000059 m. Rückprojektionsabweichung maximal 0.000043 Pixel. Aufnahmejournale trennen Wunsch, Plan, Ist-Pose und Bild. Der Wunsch für diesen Replay ist als frische auf das Ziel gerichtete Bankpose dokumentiert; er wird nicht als historisch geloggte ursprüngliche IK-Eingabe ausgegeben. Jede neue Wahrnehmungsschätzung bleibt diagnostisch `hold`.

Für den Replay werden die gespeicherten gesetzten Objektposen geladen, statt die Szene erneut physikalisch zu setteln. Die ursprüngliche Beleuchtung wurde nicht separat serialisiert; photometrisch identische Beleuchtung wird nicht behauptet. In einem früheren Wiederaufnahmeversuch wurde ein NumPy-Weg irrtümlich addiert statt verkettet. Die unabhängige native Kontaktprüfung stoppte diesen Versuch. Ungültige Resultate bleiben separat in guidance_001; sie werden hier nicht als Erfolg gezählt. 138 zuvor gültige und auf Anfangs-/Endpunkte geprüfte Datensätze wurden übernommen, die restlichen 62 mit Regressionstest und expliziter Verkettung ergänzt. Für alle tatsächlichen Aufnahmen wurde die Zielnachführung nochmals in der exakt gespeicherten Referenzszene zertifiziert.

## Grenzen und nächster Schritt

Dies ist **Simulatorreferenz**. Die rein visuelle Freiraumfreigabe wird dadurch nicht gelöst; unbekannter Raum bleibt blockiert. Keine reale Bewegung und keine Garantie, dass eine echte Kamera das Ziel richtig erkannt hat. Ziel und Richtungsbewertung stammen aus vorhandenen Bildern; echte Objektgeometrie wird nur für explizite Simulations-Kollisionsprüfung, Sichtlinienprüfung und Auswertung benutzt, nicht als Objektpose für die Blickausrichtung.

Das zuvor festgelegte Abdeckungsgate (mindestens 20 rechte/linke/erhöhte Ansichten je 40 Wünsche) ist **bestanden**. Dies ist eine Entwicklungsprüfung, kein Generalisierungsbeleg. Die 200 Familien dürfen nicht zum späteren Blindtest werden. Bessere Kameraführung ist noch kein Nachweis besserer Objekterkennung; das unveränderte V3-Modell kann die neuen Bilder weiterhin schlechter verrechnen. Die Animationen zeigen die ersten erfolgreichen Beispiele je Richtung, ohne Auswahl nach Erkennungsqualität, und bleiben als technische Diagnosen beschriftet.

Bankvorbereitung 5.3 min; Validierung 10.1 min; zusätzliche tatsächliche Bilderfassung 144.6 s. Testprotokoll: 21 fokussierte Kamera-/Seiten-/Armtests bestanden. Haupttraining wartet weiterhin auf Freigabe und die übrige V4-Implementierung.

Artefakte: bank.json, certificate_*.npz, families.jsonl, report.json, capture_audit.json, captures/, animations/, source/.
