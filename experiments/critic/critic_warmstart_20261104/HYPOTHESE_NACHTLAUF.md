# Erwartung vor dem Start, 04.11.2026

Diese Hypothese wurde vor dem wissenschaftlichen Hauptlauf festgehalten.
Sie ist eine Prognose, kein Ergebnis. Die vorbereitete Konfiguration und
Auswertung bleiben unverändert.

Ich erwarte eher den Erhalt der vorhandenen Dreierturmleistung oder einen
kleinen Gewinn als einen großen Leistungssprung. Erwartete Stabilitätsreihenfolge:
C (vorgewärmter Critic + RL + 0.01 BC), B (vorgewärmter Critic + RL),
A (zufälliger Critic + RL). Die Rangfolge ist unsicher, besonders B gegenüber A.

Begründung: Die Actors beherrschen die Aufgabe bereits; der geometrische
Rückzugscontroller beseitigt einen bekannten Fehler. Ein vorgewärmter Critic
kann zu Beginn brauchbarere Werte liefern. Seine Labels stammen aber von
beobachteten Parentaktionen und belegen keine korrekte Bewertung neuer Aktionen.
Der kleine BC-Term könnte Actor-Drift begrenzen. Sparse Gesamterfolgsrewards
und nur 20 eigene Episoden je Modell begrenzen die erwartete Verbesserung.

Prüfung nach Abschluss: feste Runde 4 gegenüber Runde 0 auf denselben
Entwicklungsstarts, getrennt für alle Arme und Parentseeds. Hauptzielgröße ist
die bestätigte vollständige Dreierturm-Erfolgsrate; kleine Critic-Losses allein
sind kein Erfolg. Als vorab definierte praktische Verbesserung gelten
mindestens fünf Prozentpunkte im Mittel der drei Parents. C soll seine
Ausgangsleistung erhalten und mindestens so gut wie A abschneiden. Ein klarer
Warmstart-Hinweis wäre B vor A, mit gleicher Richtung bei mindestens zwei
der drei Parentseeds. Gegenläufige Seeds und Gleichstände werden berichtet.
Dies sind deskriptive Kriterien, kein Signifikanztest oder unabhängiger Endtest.

Morgen nach der Arbeit erwarte ich bei bestandenem Daten- und Critic-Gate
neun finale Checkpoints und einen A/B/C-Vergleich einschließlich Lernverläufen,
Erfolgsraten, Interaktionszahlen und Laufzeiten. Ein großer und verlässlicher
Leistungssprung wird nicht vorausgesagt. Bei einem Gate-Abbruch gibt es einen
diagnostischen Bericht und erhaltene Teilresultate, keinen erzwungenen Abschluss.
Die reservierten Endtestfamilien bleiben unberührt.

Zeitfenster der gewünschten Kontrollen: bis 05.11.2026, 15:00 Europe/Berlin,
alle zwei Stunden. Der Hauptlauf wird erst nach dem Hypothesenschritt gestartet.
