# Nächster minimaler diskriminierender Versuch

Die sinnvolle nächste Hypothese lautet: **Der bestehende Loss verwendet nicht nur einen unbestätigten AktionsgainK, sondern setzt die offene Zustandsantwort unbemerkt auf Identität.** Er schätzt`δ_next≈δ+Δa@K`. Eine genauere partielle Aktionsantwort ist nur die Hälfte dieser Approximation; die allgemeine lokale Form lautet`δ_next≈δ@A+Δa@B`.

## Zunächst ohne Policy-Training

Ein vorhandener BC-Checkpoint wird eingefroren. Kleine, frei bewegliche und überprüft kontaktfreie Lift-Anker werden in vollständigen reproduzierbaren Simulatorverläufen erzeugt. Zwei identische Referenzzweige, gleiche Controller-/Gripperhistorie und vollständige Startzustände sind Voraussetzung. Die neu reservierten Anker dürfen nicht die bereits zur Kalibrierung verwendeten Anker sein. Auswahlregel, Anzahl, Seeds und Toleranzen werden vor Ausführung festgelegt.

Pro Anker drei Vergleiche:

1. **Aktionsantwort B:** gleicher vollständiger Zustand, ±0,1 Translationsaktionsänderungen. Prüft die explorativ kalibrierte Matrix außerhalb ihrer bisherigen Demos/Anker.
2. **Zustandsantwort A:** echte kleine EEF-Verschiebung von ±5 mm bei gleicher Aktion, konsistent über Gelenkpositionen hergestellt; Orientierung, Geschwindigkeiten, Objekt und Controllerzustand kontrollieren und alle tatsächlich erreichten Werte speichern. Eine bloße Änderung des Observationvektors ist dafür ungeeignet. Wenn die Zustandsherstellung oder Kontaktfreiheit nicht verifizierbar ist, abbrechen statt die Probe als physischen Recoverytest auszugeben.
3. **Policy-Reaktion:** gleiche physische Anfangsabweichung, die eingefrorene Policy erhält die konsistente veränderte Beobachtung. Tatsächlich gemessenen Folgezustandsfehler gegen die Vorhersagen mit `I,K_OLS`, mit `I,K_partial` und mit separater A/B-Näherung vergleichen. Gleiche Aktion in Vergleich 2 isoliert die offene Reaktion des Systems von der Policyantwort. Das misst einen Ein-Schritt-Mechanismus, noch keinen Taskerfolg.

Eine Simulatormatrix darf nur auf dem ausdrücklich zugewiesenen Identifikationsanteil angepasst werden; die Gegenprüfung bleibt getrennt. Simulatorzugriff, Präfixwiederholungen, IK-Zustandsherstellung und Fitkosten vollständig bilanzieren. Bei fehlendem Gültigkeitsnachweis keine kontraktionsbasierte Policyoptimierung. Im kontaktreichen Bereich lässt sich daraus keine Garantie ableiten.

## Danach erst ein kontrollierter Methodenpilot

Wenn die neue lokale Vorhersagegüte trägt, sind BC, bisheriger Loss und der **konkret überarbeitete** Loss die minimale Methodenablation. Die Sensor-Augmentation bleibt eine separate einfachere Kontrolle. Kontrollieren, ob ein Gewinn nur durch eine geänderte effektive Regularisierungsstärke entsteht; gleiche λ allein gleicht unterschiedliche Gradientenskalen nicht aus. Exakte Zielfunktion, Gewichtsvalidität, Normen, Sampling und Zusatzkosten vor Start festlegen, dann begrenzter Pilot und erst anschließend mindestens drei gepaarte Seeds mit Robustheits-/Update-/Zeitmessungen.

Die allgemeine lokale Dynamiklinearisation ist bereits aus Stable-BC motiviert; eine neue wissenschaftliche Eigenleistung müsste die konkrete verifizierte Approximation/Validitätsentscheidung, ihren praktischen Vorteil und ihren Kosten-Nutzen-Vergleich zeigen. Eine neue K-Datei oder ein erfolgreicher Einzelcheckpoint reicht nicht.

**Aktueller Ausführungsstatus:** Die physische A/B-Zustandsdiagnose wurde im aktiven Sechs-Stunden-Fenster [abgeschlossen und unabhängig verifiziert](supervised_6h_20261004_0904/mechanism_AB_002/RESULT.md). A≈I ist an frühen kontaktfreien Ankern kompatibel. Expert-OLS-K bleibt als partielle Aktionsantwort unpassend; kalibriertes B_xyz erfasst die volle Rotations-/Gripperreaktion nicht vollständig. Nächster minimaler Versuch ist [die vollständige 7D-Aktionsantwort](supervised_6h_20261004_0904/NEXT_ACTION_RESPONSE.md), ohne weiteres Training. Gates für andere Phasen/Kontakt und effektive Regularisierungsstärke bleiben offen. [Aktive Session und Agentauftrag](supervised_6h_20261004_0904/PILOT_INTERPRETATION.md).

**Weitere Gegenprüfung abgeschlossen:** Die [7D-Probe](supervised_6h_20261004_0904/mechanism_action7_001/RESULT.md) bestätigt bessere lokale Ratio-Vorhersage auf neuen Demos, insbesondere durch zuvor ausgelassene Rotationsaktionen. Gripperwirkung hier degeneriert, keine Kontaktaussage. Der nächste Schritt ist nun [die tatsächliche Ausführung berechneter Korrekturaktionen](supervised_6h_20261004_0904/NEXT_CORRECTION_PROBE.md), vor jeder neuen Policyoptimierung. Die Verbesserung der Vorhersage ist von einer Verbesserung des BC-Trainings klar getrennt.
