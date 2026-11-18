# Agent-Regeln und Git-Branch-Struktur

Die verbindlichen Forschungs-, Reproduzierbarkeits- und Monitoringregeln stehen
in [AGENTS.md](AGENTS.md). Diese Datei ergänzt sie um die verbindliche
Git-Branch-Struktur des Projekts. Bei einem Widerspruch gilt `AGENTS.md`.

## Zielbild

Das Repository verwendet zwei dauerhafte Branches und kurzlebige, fachlich
abgegrenzte Seitenbranches:

```text
main
  └── dev
       ├── frontend_display
       ├── rl_actor_critic
       ├── vision_object_recognition
       ├── curriculum_learning
       ├── data_pipeline
       ├── experiment_<kurzer_name>
       └── docs_<kurzer_name>
```

Der normale Änderungsfluss lautet:

```text
Seitenbranch  →  dev  →  main
```

`main` enthält ausschließlich zusammengeführte, geprüfte und nachvollziehbare
Projektstände. `dev` bündelt abgeschlossene Seitenbranches für gemeinsame Tests.
Neue Arbeit beginnt grundsätzlich auf einem Seitenbranch, der von aktuellem
`dev` abzweigt.

## Aufgaben der Branches

| Branch | Aufgabe | Lebensdauer |
|---|---|---|
| `main` | Stabiler, reproduzierbarer Stand für Berichte, Releases und nach außen referenzierte Ergebnisse | dauerhaft |
| `dev` | Gemeinsamer Integrationsstand für bereits einzeln geprüfte Änderungen | dauerhaft |
| `frontend_display` | Research Atlas, Navigation, Darstellung und Dashboard | bis zur Integration in `dev` |
| `rl_actor_critic` | Actor-Critic-, RL- und Critic-Warmstart-Arbeit | bis zur Integration in `dev` |
| `vision_object_recognition` | Objekterkennung, Kamera- und Vision-Methoden | bis zur Integration in `dev` |
| `curriculum_learning` | BC-, Curriculum- und Korrekturmethoden | bis zur Integration in `dev` |
| `data_pipeline` | Datenverträge, Exporte, Provenienz und Aufbereitung | bis zur Integration in `dev` |
| `experiment_<kurzer_name>` | Eine vorab dokumentierte wissenschaftliche Methodenfrage | bis zum Abschluss oder zur Archivierung |
| `docs_<kurzer_name>` | Zusammenhängende Dokumentations- oder Ausarbeitungsänderung | bis zur Integration in `dev` |

Weitere Seitenbranches sind erlaubt, wenn ihr Name den fachlichen Zweck klar
beschreibt. Namen verwenden kleine Buchstaben, Ziffern und Unterstriche. Ein
Branch soll genau ein zusammenhängendes Thema tragen. Allgemeine Namen wie
`test`, `new` oder `changes` sind zu vermeiden.

## Verbindlicher Arbeitsablauf

1. Vor Beginn `dev` aktualisieren und den Seitenbranch von `dev` erstellen.
2. Nur Änderungen des benannten Themas auf diesem Branch committen.
3. Kleine, fachlich geschlossene Commits mit verständlicher Beschreibung bilden.
4. Die für den Bereich vorgeschriebenen Tests, Hashprüfungen und Builds ausführen.
5. Den Seitenbranch in `dev` zusammenführen. Der Seitenbranch bleibt erhalten,
   solange seine Versuchshistorie oder ein Vergleich ihn noch benötigt.
6. Den kombinierten Stand auf `dev` prüfen.
7. `dev` erst nach erfolgreicher Integrationsprüfung in `main` zusammenführen.

Beispiel zum Start einer Frontend-Änderung:

```powershell
git switch dev
git pull --ff-only origin dev
git switch -c frontend_display
```

Vor dem Zusammenführen wird der Seitenbranch mit dem aktuellen `dev` abgeglichen.
Geteilte Branches werden dabei nicht durch erzwungenes Umschreiben ihrer Historie
verändert. Die Zusammenführung in `dev` und von `dev` in `main` erfolgt mit
einem Merge-Commit, damit der Git-Graph die fachliche Herkunft sichtbar behält.

## Wissenschaftliche Versuche

Ein Experiment-Branch ersetzt kein Versuchsprotokoll. Vor wissenschaftlichem
Training müssen Methodenfrage, Vergleichsarme, Seeds, Splits, Budgets,
Erfolgskriterien und vorgesehene Auswertung gemäß `AGENTS.md` dokumentiert sein.
Datierte oder versiegelte Versuchsfamilien bleiben unverändert. Neue Fragen
erhalten einen neuen Branch und ein neues Versuchsverzeichnis.

Checkpoints, Datensätze, Logs, Laufordner und andere große lokale Artefakte
werden weiterhin nach [GIT_ARTIFACTS.md](GIT_ARTIFACTS.md) behandelt. Ein Merge
ändert weder die wissenschaftliche Freigabe noch die Aussagegrenzen eines
Experiments.

## Schutzregeln für `main` und `dev`

- Keine direkte Feature-Entwicklung auf `main` oder `dev`.
- Kein Force-Push auf `main`, `dev` oder gemeinsam verwendete Seitenbranches.
- Vor einem Merge muss der Arbeitsbaum sauber sein.
- Konflikte werden auf dem Seitenbranch gelöst und dort erneut geprüft.
- `main` wird nur aktualisiert, wenn `dev` vollständig geprüft ist.
- Veröffentlichungen, Deployments und neue Trainingsläufe benötigen weiterhin
  die jeweils in `AGENTS.md` festgelegte Freigabe.

## Bestehende Branches

Die vorhandenen Branches `self-IL` und `vision-object-recog` bleiben als
historische beziehungsweise laufende Fachbranches erhalten. Sie werden nicht
allein wegen dieser neuen Struktur umbenannt oder gelöscht. Neue Änderungen
verwenden die Namen aus dem Zielbild. Wenn bestehende Arbeit übernommen wird,
wird sie nachvollziehbar nach `dev` gemergt und anschließend gemeinsam geprüft.

## Einführung

Da `dev` derzeit noch nicht vorhanden ist, wird er einmalig vom aktuellen,
geprüften `main` erstellt und veröffentlicht:

```powershell
git switch main
git pull --ff-only origin main
git switch -c dev
git push -u origin dev
```

Danach gilt für reguläre Arbeit ausschließlich der Fluss
`Seitenbranch → dev → main`.
