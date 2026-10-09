# Vorab fixierte A/B-Mechanismusdiagnose

Technische Wiederholung des vorab fixierten Versuchs mechanism_AB_001 nach unabhängigem PHYSICAL_AUDIT_FAILED: qacc_warmstart wird jetzt nach dem letzten IK-/Controllerrefresh auf den Ausgangswert zurückgesetzt und explizit geprüft. Die Kriterien werden nicht gelockert. Frühere Antworten wurden bereits inspiziert; dies ist kein neuer unabhängiger Bestätigungssatz. Alte Source/Rohdaten bleiben erhalten; repair.json dokumentiert die konkrete Korrektur und Zusatzkosten des ersten Versuchs.

04.10.2026, nach abgeschlossenem Sensor-Pilot, vor Simulatorantworten dieser Diagnose. Kein Policytraining, keine Checkpointauswahl. Instrument: endgültiger BC-Checkpoint B0 aus attempt_002 nach 2.000 Updates. Seed 4100402. Diese kleine Entwicklungsdiagnose prüft eine Modellannahme; sie kann keine robuste Policyverbesserung oder Stabilitätsgarantie begründen.

## Unbenutzte Anker und Kosten

Aus den 180 Trainingsdemos alle in intervention.json/intervention_teacher_forced.json/intervention_live_prefix.json verwendeten Demos ausschließen. Mit numpy.default_rng(4100402) vier verbleibende Demos ohne Zurücklegen wählen, Auswahl vor Ausführung in selection.json sichern. Erste zwei ausschließlich A/B-Identifikation, letzte zwei Gegenprüfung. Pro Demo die Indizes floor(0,05/0,10/0,15 * (L−1)), zwölf Anker. Keine Ersatzanker bei verfehltem physischem Gate, keine Auswahl nach Antwortgüte. Zwei technische Runtime-Inspektionen vorher: je ein Environmentreset, keine Simulatoraktionen/Updates, zusammen etwa zehn Sekunden; die erste Ausgabe scheiterte nur an numpy-JSON-Serialisierung.

Jeder Zweig beginnt mit gleichem Seed, vollständigem aufgenommenem Anfangszustand/XML und initialer Controller-Gelenkreferenz. Expertenaktionen bis zum Anker werden live wiederholt; kein Ankerreset. Dies erzeugt reproduzierbare aktuelle Simulatorzustände, nicht zwangsläufig die aufgenommenen Zwischenzustände. Präfixaktionen, Physiksteps, Resets, IK-Iterationen, Policyaufrufe, Fit- und Gesamtzeit getrennt zählen. Zwanzig Minuten maximale Laufzeit ab Launch, zusätzlich begrenzt durch die ursprüngliche Sessiondeadline 15:11:19 Berlin. Eigenständiger Windows-Job-Watchdog beendet Worker und sich selbst; keine erneute Wachhalteanforderung, die Sessionaufsicht ist bereits aktiv.

## Physischer Aufbau und Gates

Zwei identische Referenzzweige verwenden dieselbe eingefrorene vollständige BC-Aktion. Vollständige numerische Simulatorzustände (einschließlich qpos, qvel, qacc_warmstart, act, ctrl, Mocap, angewandte Kräfte, userdata, Zeit), Controllerzustände und Gripperaktionsspeicher sichern. Referenzstartabweichung höchstens 1e−9, Referenzfolgezustand EEF höchstens 1e−6 m. Robot-/Gripperkontakt mit beliebigem Kollisionsgeom ist vor und während jedem Prüfstep unzulässig; Objekt-Tischkontakt ist erlaubt. Verfehlte Gates bleiben im Nenner und werden dokumentiert; kein Fit/Mechanismusbefund aus ungültigen Ankern. Nur bei allen zwölf gültigen Ankern erfolgt die geplante Fit-/Gegenprüfung.

Echte ±5-mm-EEF-Verschiebungen auf den drei Weltachsen werden durch maximal 30 gedämpfte Jacobian-IK-Iterationen an den sieben Armgelenken hergestellt, bei fixierter Orientierung. Gelenkinkrement höchstens 0,05 rad pro Iteration, Gelenklimits prüfen. Dämpfung 1e−6; Positionsfehler höchstens 0,05 mm, Orientierungsfehler höchstens 1e−4 rad. Keine Dynamiksteps in der IK. Armgelenkgeschwindigkeiten werden mit minimaler Jacobian-Korrektur so angepasst, dass ursprüngliche räumliche EEF-Geschwindigkeit erhalten bleibt (linear 1e−5 m/s, angular 1e−4 rad/s). Nicht-Armgelenke, Gripper, Objekt, externe Kräfte und Controller-Ziel-/Nullraumhistorie bleiben gleich (1e−9 numerische Toleranz); Controller-Kinematik wird nach Änderung aufgefrischt. Gelenkgeschwindigkeitskorrektur und erreichte Zustände werden gespeichert. Die Intervention ist ein synthetisch hergestellter Simulatorzustand, kein Nachweis einer durch äußeren Stoß erreichbaren Störung.

## Drei getrennte Antworten

1. B: gleicher Zustand, vollständige Referenzaktion, jeweils ±0,1 in einer Translationskomponente, tatsächlich geclippte Differenz speichern. Referenz-/B-/A-Schritte stets gleicher gripper-/rotationsanteil.
2. A: echte ±5-mm-Zustände, gleiche vollständige Referenzaktion. Zentraldifferenzen der tatsächlich erreichten Start-EEF und nächsten EEF; Identifikationsfit delta_next = delta @ A auf ersten zwei Demos, B aus Aktionszentraldifferenzen. OLS ohne Intercept, Zeilenvektorkonvention. Kein Kontaktbereich und kein universelles Dynamikmodell.
3. Policyreaktion an denselben realen Zuständen: (a) nur neue Translationskomponenten der Policy, restliche Aktionsanteile wie Referenz; (b) vollständige neue Policyaktion als getrennte Sekundärprobe. Drei vorher bestimmte Vorhersagen vergleichen: delta + da_xyz @ K_OLS; delta + da_xyz @ K_partial (bereits explorativ kalibriert); delta @ A_fit + da_xyz @ B_fit. Beim vollständigen Policyzweig den ausgelassenen Rotations-/Gripperanteil explizit speichern; die 3×3-Näherung modelliert ihn nicht.

## Festgelegte Auswertung

Held-out B: nichtdegenerierte Antwortnorm ≥1e−5 m, Kosinus ≥0,8 und relativer Fehler ≤0,5; Anteil mit allen Kriterien für K_OLS, altes K_partial und neues B berichten. Alle Achsen im Nenner.

Offene A-Antwort: relativer Fehler der Identitätsvorhersage gegen beobachtete Zentraldifferenz, Median und p90. Identität gilt hier nur als größenordnungsmäßig kompatibel, wenn Median ≤0,10 und p90 ≤0,20; sonst wird A=I in diesen kontrollierten Zuständen nicht unterstützt. Das ist keine Gleichheitsprüfung mit statistischer Absicherung.

Held-out translationsbeschränkte Policyantwort: Fehler in Metern, relativer Fehler, Kosinus sowie beobachtetes/vorhergesagtes Ein-Schritt-Verhältnis. Eine A/B-Näherung ist für diese Diagnose vorläufig brauchbar bei ≥80% bestandenen Antworten (Kosinus ≥0,8, relativer Fehler ≤0,5, Norm ≥1e−5 m). Auch dann kein automatisches Training: lokale Extrapolation, Mehrkosten, Rotationsanteile und kontaktreiche Taskphasen bleiben offene Gates. Negative Ergebnisse ändern weder Kriterien noch Budgets. Keine erneute Untersuchung derselben Anker als angeblich frische Bestätigung.
