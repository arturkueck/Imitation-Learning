# Fortsetzung nach dem abgeschlossenen v2-Nachtlauf

Stand 18.11.2026. Entscheidungsplan, keine Freigabe und kein Start eines
weiteren Trainings oder Simulatorversuchs. Historische Quellen, Checkpoints,
Analyse und Testergebnisse bleiben unverändert.

## 1. Ergebnis abschließen und Aussage eingrenzen

Der vorab festgelegte Hauptvergleich ist vollständig, seine Entscheidung
lautet NOT_DEMONSTRATED. Targeted erreicht 359/450, Standard 362/450,
Replay 245/450, ursprüngliches B 227/450. Das sind 150 gemeinsame Szenen
über drei sammlungsfremde Datenblock/Parent-Paare, nicht 450 unabhängige
Szenen oder neun unabhängige Initialisierungen.

Targeted minus Standard: −0,67 Prozentpunkte, bedingtes gepaartes
95%-Szenenintervall [−1,78; +0,22] Prozentpunkte. Der geplante Zusatznutzen
von mindestens +5 Prozentpunkten wurde in diesem Versuchsrahmen nicht
gezeigt. Nicht als globale Gleichwertigkeit der Methoden ausgeben.

Zusätzliche passende Expertenbeispiele verbessern hier beide neuen Datenarme
deutlich gegenüber Replay. Die speziell lernerbesuchte Herkunft liefert
keinen nachgewiesenen Genauigkeitsvorteil. Ein größerer Lauf allein zur
Suche nach einem positiven Ergebnis ist deshalb nicht die nächste Priorität.

## 2. Nächster Arbeitsschritt: Restfehler diagnostizieren, ohne Training

Aus den bereits geöffneten Haupttestfällen, jeweils im vollständigen Nenner:

| Fehlergruppe | Standard, 88 Fehlschläge | Targeted, 91 Fehlschläge |
|---|---:|---:|
| Korrigierter Kontext nie erreicht | 43 | 43 |
| Kontext erreicht, zweiter Lift nicht erreicht | 6 | 7 |
| Zweiter Lift mit Griff erreicht, Gesamtaufgabe später erfolglos | 39 | 41 |

Kein erreichter zweiter Lift dieser beiden Datenarme startet ohne erkannten
Griff. Die Anfahrkorrektur beseitigt damit nicht automatisch frühe oder
nachgelagerte Ausfälle. Das sind Ablaufkategorien, keine bewiesenen Ursachen.

Die Endphasen im Targeted-Haupttest verteilen sich auf erste Platzierung:
Grasp-Descend 22, Travel 13, Open 8; zweite Platzierung: Grasp-Descend 7,
Travel 19, Open 22. Eine Episode kann dort aufgrund einer vorherigen
Abweichung enden. Diese Zahlen dürfen nicht als kausale Phasenfehlerquote
oder automatisch als fehlende Datenabdeckung interpretiert werden.

Als nächstes ein kleines separates Diagnoseprotokoll vorbereiten:

- Auswahl der zu untersuchenden Fälle nach einer dokumentierten festen Regel
  aus diesen bereits geöffneten Entwicklungskategorien, nicht nach einem
  gewünschten Ergebnis. Passende erfolgreiche Kontrollen einschließen.
- Unveränderte eingefrorene Modelle; bei Bedarf begrenzte Replays und
  einzelne kontrollierte Phasen-/Abschlusseingriffe. Kein Optimizerupdate.
- Frühere Abweichung, Greifer-/Objektkontakt, Zeitmerkmal, Phasenabschluss,
  Startzustand und Datenabdeckung prüfen. Aktion versus Abschluss nur mit
  passenden getrennten Eingriffen unterscheiden.
- Budget und Endpunkte vor Ausführung festlegen. Alle untersuchten Fälle
  und Ausgänge berichten. Diese geöffneten Szenen nicht erneut als frischen
  Bestätigungstest verwenden.

Die nächste Trainingsintervention wird aus einem reproduzierbaren Befund
abgeleitet. Keine breite Nachschulung aller Phasen ohne diese Eingrenzung.

## 3. Szenenschwierigkeit und künftige Datensplits aufbauen

Vor einem weiteren wissenschaftlichen Training:

- Messbare Merkmale und Einheiten definieren, etwa EEF-Objekt-Abstand,
  Transportstrecke, Platz-/Turmabstand oder Arbeitsraumlage. Ihre Bedeutung
  und Machbarkeit auf separaten Pilot-/Kalibrierungsfamilien prüfen.
- Schwierigkeitsskala und Grenzen für leicht/mittel/schwer festlegen und
  versionieren. Keine Grenzen anhand der künftigen Testergebnisse optimieren.
- Ganze Szenenfamilien in Training, Validierung und Test trennen. Normale
  Zielverteilung und schwierige Panels getrennt ausweisen; nicht pauschal
  alle schweren Fälle ausschließlich in die Validierung verschieben.
- Ein bewusst leicht-zu-schwer geordnetes Training ist eine eigene
  Curriculum-Intervention. Bei seiner Prüfung denselben Datenpool und
  dieselbe Exposition auch in einer gemischten Kontrolle verwenden.

## 4. Vergleichsrahmen festigen, bevor der nächste Hauptlauf startet

Bestehende A/B/C-Modelle und Replay bleiben historische interne Referenzen.
Für eine neue Bestätigung frische gemeinsame Szenen und einen identischen
50-Frame-Geometrie-/Kontakt-/Geschwindigkeitsendpunkt verwenden. Der native
10-Frame-Erfolg ist dafür kein Ersatz.

Für BC-/Korrektur-Folgestudien mehr als drei unabhängige vollständige
Trainingsseeds gemäß AGENTS.md. Die Wiederverwendung derselben drei Parents
genügt nicht. Zehn neue unabhängige Modelllinien sind ein möglicher
Budgetansatz; die konkrete Zahl ist vorab mit Zielgröße, Präzision/Streuung
und Budget zu begründen. Kein Nachschieben bis zur Signifikanz.

Die vom Nutzer gewünschte reine RL-Referenz bleibt ein separates Vorhaben:
SAC aus zufälliger Initialisierung, ohne Demonstrationen oder BC-gelernte
Unterkomponenten. Zuerst gemeinsamer Zustands-/Aktions-/Rewardvertrag,
technische Validierung und Durchsatzmessung in einer getrennten Umgebung.
Erst dann ein explizit abgegrenzter erster wissenschaftlicher Drei-Seed-Pilot;
spätere RL-Vergleiche ebenfalls mit größerer begründeter Seedzahl. Eine
Curriculum-Referenz muss benennen, ob BC oder SAC der zugrunde liegende Lerner ist.

Siehe [Baselineaudit](../../baselines/comparison_audit_20261117/REPORT.md) und
[SAC-Originalarbeit](https://proceedings.mlr.press/v80/haarnoja18b.html).

## 5. Kostenbefund prüfen, nicht nachträglich zum Hauptnachweis machen

Über alle drei Erhebungsblöcke einschließlich Validierung wurden gezählt:

| Größe | Standard | Targeted |
|---|---:|---:|
| Experten-Controlleraufrufe | 93.435 | 7.973 |
| Gemessene Präfix-/Phasenzeit, ohne Modell-/Umgebungsaufbau | 348,9 s | 578,4 s |

Die Standardquelle zählt auch die Expertensteuerung ihres gesamten Präfixes.
Das sind keine gemessenen menschlichen Beschriftungskosten. Weniger Aufrufe
bei Targeted bedeuten außerdem nicht kürzere Gesamtrechenzeit. Vor einem
Effizienzvergleich müssten Ausführungsaktionen, tatsächlich angefragte Labels,
Wiederverwendung, verworfene Versuche, Simulations- und Menschenzeit sauber
abgegrenzt werden.

Ein Vergleich bei gleichen tatsächlichen Erhebungskosten wäre eine neue,
separat vorab formulierte Fragestellung. Er darf den nicht gezeigten
Genauigkeitsvorteil dieses Hauptversuchs nicht rückwirkend ersetzen.

## Entscheidungspunkt

Unmittelbar sinnvoll ist Diagnose plus Kalibrierungs-/Vergleichsprotokoll.
Danach eine konkrete Methodenänderung und ihre Kontrollen wählen und das
nächste Training mit größerer begründeter Seedzahl planen. RL-Baseline und
Schwierigkeitscurriculum werden transparent als eigene Vergleichsverfahren
behandelt. Kein neues Training wurde durch diesen Plan gestartet.
