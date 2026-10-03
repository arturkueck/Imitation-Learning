# Lernpfad: Imitation Learning verstehen

Für Artur · begonnen am 1., fertiggestellt am 2. Oktober 2026 · vorbereitet für deine Lernsitzung am **2. Oktober 2026**.

Dieser Ordner ist deine Lernunterlage. Die wissenschaftliche Wissensbasis in `literature/` bleibt unverändert. Hier werden ihre Inhalte erklärt; vereinfachte Rechenbeispiele und Simulationen sind **eigene didaktische Modelle**, keine Ergebnisse der Papers oder eures Roboters.

## Wo du anfängst

1. [Kurzer Einstieg](01_einstieg.md): in etwa fünf Minuten die Grundidee verstehen.
2. [Mathematische Werkzeuge](02_mathematische_werkzeuge.md): Symbole lesen, Ableitungen und Wahrscheinlichkeiten verstehen.
3. [Idee und Umsetzung der Algorithmen](03_algorithmen.md): BC, DAgger, DART, Stable-BC, ACT und Diffusion Policy.
4. [Gleichungsatlas](04_gleichungsatlas.md): die zentralen Gleichungen der fünf Dossiers, Variablen und durchgerechnete Beispiele. Dies ist ein Nachschlagewerk, keine Pflichtlektüre am Stück.
5. [Simulationen und Lernaufträge](05_simulationen.md): erst eine Vorhersage machen, dann ausprobieren, dann erklären.
6. [Übungen](06_uebungen.md), anschließend [Lösungen](07_loesungen.md).

**Simulationen starten:** [simulationen/index.html](simulationen/index.html) im normalen Browser öffnen, zum Beispiel im Explorer doppelklicken. Alles läuft lokal und offline; keine Installation, GPU oder Robomimic nötig. Falls Codex nur den Quelltext zeigt, die Datei über den Explorer im Browser öffnen. Die Simulationen sind bereits fertig für morgen; es ist kein geplanter Hintergrundlauf nötig.

## Ein überschaubarer Plan für deine Lernsitzung

| Zeitrahmen | Tätigkeit | Lernziel |
|---|---|---|
| 0–10 min | Einstieg lesen; anschließend ohne Text erklären, was Zustand, Aktion und Policy sind | Grundmodell im eigenen Kopf aufbauen |
| 10–25 min | Werkzeuge bis einschließlich Ableitungen; Atlas G1–G3 | Eine BC-Gleichung selbst lesen |
| 25–45 min | Algorithmustext zu DAgger/DART; Labore 1, 2 und 6 | Datenfehler, Zustandsverteilung und Korrekturlabel unterscheiden |
| 45–50 min | Pause | Neue Begriffe verarbeiten |
| 50–75 min | Stable-BC; Atlas S1–S6; Labor 3 | Kopplung verstehen, ohne jede Matrixformel auswendig zu lernen |
| 75–95 min | ACT/Diffusion; Atlas A1–A3 und P1–P3; Labore 4–5 | Aktionsfolgen und generatives Lernen unterscheiden |
| 95–110 min | Übungen 1–8 ohne Unterlagen; Lösungen erst danach | Verständnis prüfen statt nur wiedererkennen |

Die Zeiten sind Orientierung. Wenn Ableitungen neu sind, teile den Plan auf zwei Sitzungen auf. Die Vertiefungsformeln D3–D4, R2–R3, S5, A2 und P4–P5 kannst du später nachlesen.

## So ist das Material didaktisch aufgebaut

**Konkretes Beispiel → Begriff → Formel → Anwendung.** Eine mathematische Zeile kommt erst nach der Frage, die sie beantwortet. Die Rechenbeispiele sind vollständig gelöst; in den Übungen wird diese Hilfe schrittweise entfernt. Kleine Selbstchecks machen Fehlvorstellungen sichtbar. Bei jeder Simulation steht: Was verändere ich? Was bleibt gleich? Was darf ich daraus schließen?

**Aktiv abrufen:** Nach jeder Methode den Text schließen und drei Sätze schreiben: Problem, Eingriff, Grenze. Ein sicher klingendes Wiedererkennen beim Lesen ist noch kein Erklärenkönnen.

**Vergleichen:** DAgger und DART gemeinsam lernen; danach Stable-BC danebenstellen. ACT und Diffusion gemeinsam vergleichen. So erkennst du die Unterschiede der Mechanismen.

**Wiederholen:** Am Abend nach der ersten Lernsitzung die acht Kernfragen ohne Unterlagen beantworten; zwei bis drei Tage später nochmals. Bei einer falschen Antwort nur die passende Stelle nachlesen und ein neues Zahlenbeispiel rechnen. Der Zeitplan ist ein Lernvorschlag, keine empirisch validierte individuelle Lernstrategie.

## Quellen und Kennzeichnung

Die fachliche Basis sind die fünf vorhandenen [Methodendossiers](../literature/INDEX.md). Quellenverweise im Atlas nennen deren Claim-IDs und konkrete PDF-Seiten. Stable-BC-Inhalt ist weiterhin als **Preprint v1** gekennzeichnet; der Journalinhalt wurde nicht abgeglichen.

Alle Beispiele mit einem eindimensionalen Roboter, einer Zweizustandsmatrix, zwei Aktionsmodi oder künstlichen Störungen sind Lernkonstruktionen. Sie dürfen nicht als Literatur- oder Projektergebnisse zitiert werden. Einziger Projektabschnitt ist ausdrücklich als solcher markiert.

Zu den Simulationen gehören [Modellbeschreibung](simulationen/MODELLE.md) und [Prüfprotokoll](simulationen/PRUEFUNG.md). Rechenkerne und Oberfläche sind getrennt, damit die Gleichungen nachvollziehbar bleiben.
