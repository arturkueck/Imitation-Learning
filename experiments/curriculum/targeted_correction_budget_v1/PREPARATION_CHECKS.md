# Vorbereitung und technische Nachweise · 17.11.2026

**Vollversuch: READY, wissenschaftlich noch nicht gestartet.**
Laufordner: `praxis/results/curriculum/targeted_correction_budget_v1/night_20261117`.
Deadline: 18.11.2026, 09:00 Europe/Berlin; kooperatives Workerlimit 08:58,
anschließend eigener Prozessbaum mit hartem Limit. Keine automatische Fortsetzung.

## Bestandene Prüfungen

- Sieben Unit-/Integrationstests: absolute Deadline auch bei spätem Start,
  Trennung sämtlicher neuen Datenfamilien, eindeutige gepaarte Frameauswahl
  mit identischem Abschlusslabelbudget, vollständige Erfolgsnenner und
  Paarvergleiche, inkrementelle Logs einschließlich Teilzeilen/Rotation,
  Prozessidentität einschließlich Erstellungszeit, tatsächliches Beenden
  eines eigenen Testworkers samt Kindprozess.
- `smoke_002`: COMPLETE, sechs Komponenten mit je vier technischen Updates,
  sieben Sammelpaare und acht technische Auswertungsepisoden. Laufzeit
  56,6 Sekunden. Keine wissenschaftliche Bestätigungsszene geöffnet.
- Fünf gemeinsam geeignete Sammelpaare: zwei Trainings-/drei
  Validierungsfamilien. Je Datenarm 40 Trainings- und 55 Validierungslabels,
  identische Familien-/Abschlusslabels und disjunkte Splits. Ungeeignete
  Paare bleiben dokumentiert, keine Ersatzstarts.
- Das unveränderte B reproduziert die archivierte Entwicklungskontrolle
  einschließlich Erfolg, Framezahl, Anfangszustand, Endphase und Timeout.
- `smoke_002_resume_verification`: alle sechs Quell-/Komponententypen von
  Update 2 bis 4 fortgesetzt. Gewichte und vollständiger Optimizerzustand
  bitgleich zum ununterbrochenen Lauf; Phasen 1–6 bitgleich zum B-Vorfahren.
- PowerShell-Launcher syntaktisch geprüft. Sein tatsächlicher versteckter
  Prozessstart samt Argumenten mit Leerzeichen wurde mit einem reinen
  `verify`-Aufruf erfolgreich geprüft; kein Vollversuch gestartet.
- Vollversuch: Quellen-/Plan-/Eingangshashes geprüft, alle drei B-30k-Modelle
  mit Registry-Hash und Optimizer geladen. Alter Phase-0-Pool: 3.489 Frames,
  davon 180 Abschlusslabels. Kein `launch.json` vorhanden. Nachweis:
  `night_20261117/readiness.json`.

## Während der Vorbereitung korrigiert

In eingeschränkten Windows-Shells kann psutil einen fremden laufenden Prozess
als nicht vorhanden melden. Dies ließ sich mit einem eigenen kurzlebigen
Testprozess reproduzieren. Der Monitor verwendet nun direkte Windows-
Prozesshandles samt Erstellungszeit. Fehlende Leserechte erzeugen WARNING
statt einer falschen Abbruchmeldung. Mit den nötigen Windows-Leserechten
wurde derselbe Prozess korrekt erkannt; die aktive Smoke-Kontrolle lieferte
OK und null neue Fehler. Bei Codex-Aufrufen mit eingeschränkter Prozesssicht
ist diese reine Lesekontrolle entsprechend außerhalb der Sandbox auszuführen.

`smoke_001` bleibt als erster technischer Durchlauf erhalten. Danach wurde
der Monitor korrigiert und der vollständige technische Ablauf mit den finalen
Quellen als `smoke_002` wiederholt. Für die Freigabe gelten die geprüften
Hashes von `smoke_002`; alte Nachweise wurden nicht umgeschrieben.

## Budget und erwartete Aussage

Drei Erhebungsblöcke mit je 120 Trainings-/30 Validierungsszenen ergeben
450 Sammelpaare bzw. bis zu 900 Präfix-/Korrekturabläufe. Drei Parents,
drei trainierte Quellen und zwei Komponenten ergeben 54 Fortsetzungen mit
je 5.000 Updates. 4.320 Auswertungszeilen entstehen aus 3.600 tatsächlich
ausgeführten Episoden; identische B-Kontrollen werden über Datenblöcke
wiederverwendet. Die 100 Bestätigungsszenen sind über Modelle und Datenblöcke
geteilt und werden entsprechend nicht als 900 unabhängige Szenen bezeichnet.

Planungswert circa **4–7 Stunden** aus dem technischen Durchsatz und dem
abgeschlossenen Korrekturlauf; keine Laufzeitgarantie. Die Morgen-Deadline
verlängert weder Updatebudget noch Testpanel. Der Lauf endet bei Fertigstellung.

Zu erwarten ist eine belastbarere Antwort auf die Frage nach der Herkunft
zusätzlicher Labels. Eine Verbesserung wird nicht versprochen. Quellen-
Auswahlkosten werden separat gemessen; gleich viele verwendete Lernlabels
bedeuten hier nicht gleich viele Expertenaufrufe oder gleiche Sammelzeit.
Ein unvollständiger Lauf liefert einen Teilbericht, keinen nachträglich
verkürzten Bestätigungsversuch. Wissenschaftlicher Start erfolgt erst auf
Startauftrag; `start.ps1` ist vorbereitet und wurde nicht auf den Vollversuch
angewendet.
