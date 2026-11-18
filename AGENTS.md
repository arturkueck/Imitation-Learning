# Codex – Forschungsregeln und effizientes Trainingsmonitoring

Diese Vorgaben gelten für das gesamte Repository. Wissenschaftliche
Trainingsversuche müssen eine vorab dokumentierte Methodenfrage prüfen.
Fallender Loss allein ist kein Nachweis besseren Aufgabenerfolgs,
besserer Robustheit oder höherer Lerneffizienz.

## 0. Orientierung für Agenten

Rein navigatorisch; ändert keine der Regeln in Abschnitt 1–5. Weitere
`AGENTS.md` liegen in `experiments/`, `experiments/curriculum/`, `praxis/`
und `sites/` und gelten zusätzlich für ihren Teilbaum.

**Karte.** Menschliche Einstiege: `README.md` → Bereichs-READMEs.

| Ort | Rolle |
|---|---|
| `experiments/<thema>/<familie>/` | Versuchscode, Protokolle, Berichte; datierte Familien sind eingefroren |
| `experiments/<thema>/base/` | editierbare Basiskopien für neue Arbeit |
| `praxis/src/` | gemeinsame Bibliothek (`robomimic_ext`, `task_extensions`, `active_view`) |
| `praxis/tests/` | Regressionstests der Bibliothek |
| `praxis/results/` | große lokale Laufdaten, Checkpoints, Junctions |
| `sites/research-atlas-source/` | einzige maßgebliche Website-Quelle |
| `monitor/training-runs.json` | Laufregister für das Dashboard |
| `literature/`, `lernmaterial/`, `latex/` | Wissensbasis, Lernmaterial, Ausarbeitung |

**Aktueller Forschungsstand:** `experiments/curriculum/README.md` (Abschnitt
„Aktueller Stand“) und `experiments/curriculum/targeted_correction_budget_v2/NEXT_STEPS_20261118.md`.
`FORSCHUNGSPLAN.md`, `next_research_direction.md` und `RESEARCH_NOTIZEN_*.md`
sind datierte Hintergrunddokumente, nicht der aktuelle Stand.

**Nicht durchsuchen oder lesen** (groß, generiert oder fremd):
`praxis/.venv/`, `praxis/upstream/`, `praxis/.cache/`, `praxis/data/`,
`praxis/results/`, `**/node_modules/`, `**/__pycache__/`, `sites/*.tar.gz`,
`sites/research-*-editor/`, `sites/research-atlas-editorial/`,
`sites/research-atlas-update/`, `sites/research-workspace/`, `output/`, `tmp/`,
`tubs-latex-cd-lite-main/`, `*.log`, `*.hdf5`, `*.npz`, `*.pth`. Suchen auf
`experiments/`, `praxis/src/`, `praxis/tests/` und `sites/research-atlas-source/`
beschränken, dort `run_*/`, `smoke_*/` und ähnliche Ausgabeordner ausschließen.

**Umgebung.** Windows, PowerShell, Befehle aus dem Repository-Stamm.
Python immer über `praxis/.venv/Scripts/python.exe`; für Importe aus
`praxis/src` vorher `$env:PYTHONPATH=(Resolve-Path praxis/src).Path`.
Website lokal: `npm start` → `http://127.0.0.1:4173`. Lange Pfade:
`git config --local core.longpaths true`.

**Sprache.** Dokumentation überwiegend Deutsch, ältere Dateien teils Englisch
oder mit `ae/oe/ue` statt Umlauten; bei Suchen beide Schreibweisen prüfen.
Neue Dokumentation auf Deutsch.

## 1. Verbindliche Seedregel für neue wissenschaftliche Versuche

- Nur der **erste wissenschaftliche Pilotlauf eines vorab klar beschriebenen
  Versuchsvorhabens** wird mit **genau drei unabhängigen Trainingsseeds pro
  Methode beziehungsweise Vergleichsarm** durchgeführt. Er dient der ersten
  Prüfung von Machbarkeit, Effekt und Streuung.
- **Jeder nachfolgende wissenschaftliche Trainingslauf dieses Vorhabens muss
  mehr als drei unabhängige Trainingsseeds pro Methode beziehungsweise Arm
  verwenden.** Wiederholungen, Erweiterungen, Hyperparameteränderungen oder
  neue Laufnamen setzen die Pilotregel nicht zurück. Eine tatsächlich neue
  Methodenfrage ist vorab zu begründen und abzugrenzen.
- Die konkrete größere Seedzahl wird vor dem Lauf festgelegt und anhand
  des kleinsten relevanten Effekts, der erwarteten Streuung, gewünschter
  Präzision beziehungsweise Teststärke und des Budgets begründet. Zehn Seeds
  sind ein möglicher Planungsansatz, keine allgemeine Garantie ausreichender
  Evidenz. Bei knappen Ressourcen den Umfang vorab begründet planen, nicht
  stillschweigend wieder auf drei Seeds reduzieren.
- Ein Trainingsseed bezeichnet einen unabhängigen vollständigen Lernverlauf
  einschließlich der Initialisierung. Neue Testszenen, mehrere Checkpoints,
  Aktions-/Abschlusskopien, Feinabstimmungen desselben Parents oder zusätzliche
  Datenerhebungen sind **kein Ersatz** für weitere unabhängige Trainingsseeds.
  Die Zahl der unabhängigen Parent-Initialisierungen ist separat auszuweisen.
- Methoden werden soweit sinnvoll pro Trainingsseed gepaart verglichen:
  gleiche Ausgangsbedingungen, Datenverträge, Budgets und Teststarts. Alle
  vorab vorgesehenen Seeds und ihre Ausgänge berichten; keine Auswahl nur
  günstig konvergierender Seeds und kein Nachschieben bis zum positiven Befund.
- Technische Smoke-Tests sind von wissenschaftlichen Pilot-/Hauptläufen klar
  zu trennen. Sie liefern keinen wissenschaftlichen Wirksamkeitsnachweis und
  begründen keinen erneuten Drei-Seed-Pilotlauf für dieselbe Methodenfrage.

## 2. Schwierigkeit der Szenen muss bewertbar sein

- Trainings-/Initialisierungsseeds, Datenerhebungsseeds und Szenen-/Testseeds
  ausdrücklich unterscheiden. Eine Seednummer ist eine Kennung zur
  Reproduzierbarkeit; ihr Zahlenwert besitzt keine Schwierigkeitsskala.
- Für die durch Szenen-Seeds erzeugten Situationen vorab eine nachvollziehbare,
  reproduzierbare Schwierigkeitsbewertung definieren. Dokumentieren:
  verwendete Merkmale, Berechnung, Einheiten, Grenzen für leicht/mittel/schwer,
  Annahmen, Versionsstand und Zuordnung der Szenen zu den Gruppen.
- Mögliche Merkmale sind etwa Transportstrecke, Abstand zum vorhandenen Turm,
  Platzverhältnisse oder Lage im Arbeitsraum. Ihre tatsächliche Beziehung zur
  Schwierigkeit ist mit separaten Pilot-/Kalibrierungsdaten zu prüfen;
  vermeintlich plausible Geometrie ist noch kein validierter Schwierigkeitsgrad.
- Eine Referenzpolicy darf zur vorab dokumentierten Kalibrierung auf separaten
  Pilotdaten verwendet werden. Schwellen und Gruppen nicht anhand späterer
  Testresultate der zu vergleichenden Methoden auswählen oder verändern.
- Ein Curriculum beginnt gegebenenfalls einfacher und steigert anschließend
  Schwierigkeit und Vielfalt. Seine Regeln und Stufen werden vorab festgelegt.
  Kontrollarme behalten die für ihre Fragestellung nötigen Bedingungen; nicht
  stillschweigend allen Armen ein Curriculum hinzufügen.
- Normale neue Szenen, gezielt schwierige Fälle innerhalb des bisherigen
  Bereichs und veränderte Bedingungen außerhalb dieses Bereichs getrennt
  kennzeichnen. Schwieriger oder unbekannt bedeutet nicht automatisch OOD.

## 3. Angemessene Trennung von Training, Validierung und Test

- Vor jeder neuen Studie Zweck, Umfang, Szenenfamilien, Schwierigkeitsverteilung
  und gegebenenfalls Datenerhebung für **Train**, **Validation** und **Test**
  schriftlich festlegen. Die Aufteilung und ausreichende Fallzahlen begründen;
  ein pauschales Prozentverhältnis ersetzt diese Planung nicht.
- Ganze ursprüngliche Episoden beziehungsweise Anfangsszenenfamilien trennen.
  Frames, Ausschnitte, Varianten, Augmentationen und verschiedene Controller-
  Ausführungen derselben Familie dürfen nicht über die Splits verteilt werden.
  Zugehörigkeiten, Seeds und Eingangszustände nachvollziehbar protokollieren.
- Training muss die zum Forschungsziel nötigen Fertigkeiten und die geplante
  Variation abdecken. Bei einem Curriculum zunächst einfachere, später auch
  anspruchsvollere Trainingssituationen einbeziehen.
- Validierung unterstützt Methoden-/Hyperparameterwahl und muss zum
  behaupteten Einsatzbereich passen. Zusätzlich ein vorab definiertes
  schwieriges Validierungspanel verwenden, wenn Transfer oder Robustheit
  untersucht werden soll. Normale und schwierige Ergebnisse getrennt berichten;
  Validierung muss nicht grundsätzlich ausschließlich schwieriger sein.
- Der abschließende Test verwendet unabhängige, bis zur Festlegung von Methode,
  Checkpointregel und Analyse nicht ausgewertete Familien. Normale und gezielt
  schwierige Testpanels vorab definieren und getrennt ausweisen. Alle Methoden
  auf denselben gepaarten Szenen und nach derselben Erfolgsdefinition vergleichen.
- Testdaten nicht für Normalisierung, Schwierigkeitskalibrierung, Curriculum,
  Datenauswahl, Checkpoint-/Schwellenwahl oder Hyperparameteroptimierung nutzen.
  Geöffnete Testpanels bleiben als geöffnet gekennzeichnet und werden nicht
  später erneut als unabhängiger Blindtest ausgegeben.
- Ausschlussregeln und Umgang mit nicht erreichten Phasen vorher festlegen.
  Kein stilles Entfernen schwieriger Fehlschläge oder Ersetzen erfolgloser Starts.
  Vollständigen Aufgabenerfolg mit vollständigem Nenner berichten; bedingte
  Phasenquoten erhalten eigene ausdrücklich benannte Nenner.
- Unsicherheit über Testszenen, Datenerhebungen und Trainingsseeds getrennt
  behandeln. Geteilte Szenen und verwandte Modelle sind keine unabhängigen
  Wiederholungen. Ein nur über Szenen berechnetes Intervall deckt nicht die
  Streuung bei neuem Training ab.

## 4. Explizite Ausnahme für den bereits laufenden Versuch

Der vom Nutzer freigegebene Nachtlauf
`praxis/results/curriculum/targeted_correction_budget_v2/night_20261117`
darf nach seinem bestehenden eingefrorenen Drei-Seed-Protokoll abgeschlossen
werden. Seine Methoden, Seeds, Datensplits, Schwierigkeitsverteilung,
Lern-/Testbudgets, Checkpoint-/Analyseentscheidungen und absolute Deadline
**18.11.2026, 09:00 Europe/Berlin** werden durch diese neuen Regeln nicht
geändert. Keine zusätzliche Seedrunde zur nachträglichen Erfüllung hinzufügen.
Die Aussagegrenzen des vorhandenen Protokolls bleiben bestehen.

Die bereits autorisierte technische Fehlerbehebung und exakt belegbare
Fortsetzung bleibt innerhalb der bestehenden operativen Freigabe zulässig;
sie ist keine Freigabe für eine wissenschaftliche Protokolländerung oder
einen erneuten kompletten Versuch. Neue nachfolgende Studien richten sich
nach den Regeln oben.

## 5. Effizientes Trainingsmonitoring

### Ziel und Prioritäten

Laufende Trainings zuverlässig, ressourcenschonend und mit minimalem
Tokenverbrauch überwachen. Regelmäßige Aufrufe bleiben kurz; vertiefte
Analyse nur bei tatsächlichen Problemen.

1. Fehler und Trainingsabbrüche zuverlässig erkennen.
2. Unnötige Modellaufrufe und Kontextverarbeitung vermeiden.
3. Laufende Experimente nicht unnötig unterbrechen.
4. Probleme möglichst eigenständig und nachvollziehbar beheben.
5. Reproduzierbarkeit und wissenschaftliche Vergleichbarkeit erhalten.

### Minimaler Prüfaufwand

- Zuerst das vorhandene deterministische Monitoringwerkzeug verwenden.
- Erwarteten Trainingsprozess prüfen, danach Fortschritt seit der letzten
  erfolgreichen Kontrolle und ausschließlich neue Logeinträge lesen.
- Nur relevante Fehler, Warnungen und Metriken extrahieren. Keine vollständigen
  Logausgaben, umfassenden Repository-Suchen oder wiederholten unveränderten Reads.
- Für Routineprüfungen einfache Shell-/Python-Befehle verwenden. Quellcode
  ausschließlich bei konkreten Fehlerhinweisen untersuchen.
- Fehlende Windows-Prozesssicht ist kein Beweis für einen Abbruch; Identität
  und Erstellungszeit mit geeigneten Leserechten prüfen.

### Persistenter Überwachungsstatus

Vorhandene kleine Statusdateien, etwa `monitor/state.json` oder den lokalen
`monitor_state.json`, weiterverwenden. Zeitpunkt der letzten erfolgreichen
Kontrolle, Logoffset, letzten Schritt/Epoche, relevante Metriken, Prozessstatus
und erkannte/behandelte Probleme festhalten. Logrotation und Prozessneustarts
berücksichtigen. Ohne bisherigen Zustand aus dem aktuellen Stand initialisieren,
ohne unnötig die gesamte Historie einzulesen.

### Normalbetrieb

Bei aktivem Prozess, Fortschritt und ohne kritischen Fehler sofort beenden.
Keine Hyperparameter, wissenschaftlichen Dateien oder Experimente verändern;
keine zusätzlichen Trainings starten und keine umfassenden Analysen durchführen.
Nur erforderlichen Monitoringzustand aktualisieren.

Maximal eine kurze Statuszeile, zum Beispiel:

`OK | Training aktiv | Step: X | Loss: Y | Neue Fehler: 0 | Aktion: keine`

### WARNING und ERROR

**WARNING:** fehlender Fortschritt, wiederkehrende Warnungen, stagnierende
Metriken oder ungewöhnliche Ressourcennutzung. Zuerst nur unmittelbar relevante
Informationen prüfen; geplante Validierung und Checkpoints berücksichtigen.

**ERROR:** unerwartetes Ende, CUDA-OOM, NaN/Inf, beschädigte Daten,
unlesbare Checkpoints oder nicht abgefangene Exceptions. Fehlermeldung mit
relevantem Kontext isolieren und gezielt die Ursache untersuchen.

### Technische Fehlerbehebung und Neustarts

1. Fehler und Kontext isolieren, wahrscheinliche Ursache bestimmen.
2. Kleine risikoarme technische Lösung prüfen und nur notwendige Änderungen machen.
3. Geeigneten ressourcenschonenden Test durchführen und Ergebnis dokumentieren.
4. Keine Architektur, Loss-Funktion, Daten, Seeds, zentralen Hyperparameter,
   Splits, Erfolgskriterien oder wissenschaftlichen Budgets ohne spezifische
   Freigabe verändern. Reparatur von experimenteller Optimierung trennen.
5. Neustart/Fortsetzung nur innerhalb vorhandener Autorisierung, bei nachweislich
   beendetem Originalprozess, behobener Ursache und ohne Gefährdung vorhandener
   Checkpoints oder Ergebnisse. Optimizer-, RNG-, Sampler-, Update- und
   Schleifenzustände müssen zur behaupteten Fortsetzung passen.
6. Keine unbegrenzten Neustartversuche. Nach einem fehlgeschlagenen automatischen
   Reparaturversuch eskalieren. Engere laufbezogene Grenzen zusätzlich beachten.
7. Keine Gewichte, großen Checkpoints oder Datensätze in den Modellkontext laden.
   Bestehende Artefakte erhalten; keine Ergebnisse zur Bereinigung löschen.

### Berichte bei Problemen

Status, kurze Ursache, Maßnahme, Ergebnis und Trainingszustand angeben.
Ausführliche Berichte nur bei komplexen Problemen oder auf ausdrücklichen Wunsch.
Gesunde Routinekontrollen unmittelbar nach erfolgreicher Prüfung beenden.

**Grundprinzip: So wenig Analyse wie möglich, so viel wie nötig.**
