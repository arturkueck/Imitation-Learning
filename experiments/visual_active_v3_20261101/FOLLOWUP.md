# V3: Folgeagent nach abgeschlossenem Training

Stand: 02.11.2026. Go ist erteilt; der tatsächliche Lauf wird in monitor_state.json registriert. Die Automation bezieht sich ausschließlich auf diesen V3-Lauf, nicht auf beliebige ältere Trainings. Produktionsstatus siehe dessen status.json.

## Übergabe und Abschluss

Der künftige V3-Runner legt im neuen Laufverzeichnis `handoff_result.json` atomar an. `completion_gate.py arm --run <relativer Laufpfad>` registriert diesen Lauf vor dem Start. Dies startet keinen Prozess. Der Runner muss vor seinem Ende alle Worker in `workers` mit PID und `create_time` (psutil) verzeichnen. Alle Dateien und der Laufpfad liegen unter diesem Experimentverzeichnis.

Abschlussvertrag:

```json
{
  "schema_version": 1,
  "run_id": "run_001",
  "status": "completed",
  "training_complete": true,
  "validation_complete": true,
  "workers": [{"pid": 1234, "create_time": 1793574000.0}],
  "artifacts": {
    "metrics": {"path": "metrics.json", "sha256": "..."},
    "curves": {"path": "loss.png", "sha256": "..."},
    "checkpoint_manifest": {"path": "checkpoint_hashes.json", "sha256": "..."}
  }
}
```

Dies ist ein Schnittstellenbeispiel, kein vorhandenes Resultat. Fehlende/fehlerhafte Ergebnisse, aktive Worker und ein bloß beendeter Prozess lösen keine Erfolgsübergabe aus. Der Gate prüft kleine Ergebnisdateien und Artefakthashes, lädt keine Gewichte. Der Folgeagent prüft zusätzlich die tatsächlichen Checkpointhashes im Manifest. `status=failed` wird als Fehler behandelt. Teilstände `running`, `validating`, `checkpointing` bleiben in Beobachtung. `monitor_state.json` hält genau den registrierten Lauf und später den einmaligen Claim fest. Bei einem abgestürzten Folgeagenten Claim nicht blind löschen: erst Agent und Arbeitsstand prüfen.

## Auftrag des Folgeagenten

Nach erfolgreichem Gate zuerst atomar `completion_gate.py claim` ausführen und genau einen Subagenten über die Kollaboration starten. Kein separater Nutzerchat erforderlich. Entscheidungs- und Ergebnisbericht in `<run>/FOLLOWUP_REVIEW.md`; Übergabestatus mit `completion_gate.py finish --outcome <Wert>` sichern.

1. Vollständigkeit der drei Seeds, Datenfamilien-/Splittrennung, tatsächliche Epochen/Updates, Best-/Final-Checkpoints, Train-/Validation-/Probe-Loss und 3D-Abgleiche prüfen. Fehler, Overfitting und Leistungsrückschritt von Untertraining unterscheiden. Keine Entscheidung allein aus niedrigem Training-Loss.
2. Nur bei noch sinkendem Validation-Loss, fehlender Konvergenz und ohne Overfitting fortsetzen. Höchstens **eine** zusätzliche Fortsetzung, maximal **20 Epochen und 3 Stunden insgesamt**, früheres Limit gilt. Unveränderte Daten, Seeds, Architektur, Loss und zentrale Optimizerparameter; vollständigen Optimizer-/Scheduler-/RNG-Resume nur verwenden, wenn verifiziert. Neue Ergebnisse in neuem Verzeichnis mit Parent-Hashes. Bei fehlendem Resume keine vorgetäuschte Fortsetzung; konkrete Grenze berichten. Keine Endtestdaten zur Entscheidung oder Nachschulung benutzen.
3. Bei ausreichender Wahrnehmung das Training/Validieren der Aufnahmebedarf- und Blicknutzenköpfe nach PLAN.md durchführen; Wahrnehmungsmodell vorher einfrieren, separate Anfragefamilien und Kalibrierung verwenden. Maximal 30 Epochen je geplantem Kopf-Lauf und **6 Stunden Gesamtbudget für diese Anschlussphase**, mit vorab gespeicherter Deadline; bei Budgetende Checkpoints erhalten und Teilstand berichten. Wenn noch Implementierung fehlt, diese innerhalb desselben Budgets zuerst erstellen und testen. Keine Forschungsparameter spontan ändern, um Gates zu erreichen.
4. Danach automatische Zusatzbilder in der **Simulation** prüfen: feste Kameras als Kontrolle, zusätzliches Armkamera-Bild, getrennte Wunsch-/Plan-/Ist-Pose. Vor jeder Aufnahme IK, Gelenkgrenzen, Selbstkollision, Kamera-/Greifergehäuse, Roboter–Umwelt-Kollisionen sowie gesamten Pfad prüfen. Ein gültiger Endpunkt genügt nicht. Keine erreichbare sichere Bahn: `blocked`, kein Bildauftrag an einen realen Roboter. Bei geänderter Szene neu planen. Unsichtbarer/unbestätigter Raum ist nicht automatisch frei. Simulatorreferenz-Geometrie als solche kennzeichnen; visuelle Karte separat auswerten. Keine Behauptung realer kamerabasierter Sicherheitsgarantie.
5. Maximal zwei Zusatzbilder pro Szene; bisherige Bilder erhalten. Nutzen und Verschlechterungen, falsche Zusatzobjekte, fehlende Objekte, Posefehler, blockierte/unerreichbare Ziele, Kollisionsbefunde und Zeit auswerten. Train-/Validation-Loss und regelmäßige Cyan/Orange-3D-Abgleiche speichern. Fehlgeschlagene Kandidaten behalten. Keine GT-Geometrie oder zukünftigen Bilder als Netzeingabe.
6. Erst danach in diesen Chat zurückmelden: Entscheidung, tatsächliche Updates, Seeds, Budgets, Erfolg/Grenzen und Artefakte. Technische Blockade konkret melden; keine unbegrenzten Neustarts oder Trainingsschleifen. Nur ein technischer Reparaturversuch nach nachweislichem Prozessende. Keine realen Bewegungen, Deployments, Git-Pushes oder neue kostenpflichtige Dienste.

Mögliche Endwerte: `review_only`, `continued_then_reviewed`, `active_view_validated`, `blocked`, `failed`. Ein Endwert ist keine wissenschaftliche Erfolgsgarantie.

## Betrieb

Go erteilt am 02.11.2026 um 00:31:20 Berlin. Verbindliche session.json: Ende **02.11.2026 16:31:20 Berlin**, kein neues 16-Stunden-Fenster bei Folgeagenten. Der konkrete V3-Runner und die Datenerzeugung sind nun in train_v3.py/data_v3.py implementiert; Status und tatsächliche Updates stehen im registrierten Lauf, nicht im ursprünglichen Entwurfs-JSON. PREPARATION_NOTES.md erklärt die vor dem Training festgelegten Kamera-/Geometrie-Holdouts.

Die unabhängige deadline_guard.py überwacht die gemeinsame Frist ohne Modellaufrufe. Jeder zusätzliche Worker/Supervisor der Anschlussphase muss sofort mit `deadline_guard.py register --pid <PID> --role <Rolle> --run <absoluter V3-Laufpfad>` registriert werden. PID und Prozessstartzeit werden geprüft. Drei Minuten vor Ende STOP_REQUESTED, bei Deadline Ende nur der registrierten Prozesse. Die Folgephase muss STOP_REQUESTED beachten und rechtzeitig Checkpoints schreiben. Keine neue Deadline anlegen. Neue Agentenprüfung: `monitor_check.py` liest Prozessabschluss und ausschließlich neue Logbytes mit persistentem Offset. Nach komplettem Folgeabschluss beendet sich der Guard, sobald alle registrierten Prozesse gestoppt sind.

Der Runner veröffentlicht den Ergebnisvertrag schon während des Laufs atomar mit `status=running`, `validating` oder `checkpointing` und vollständigen Workeridentitäten. Fehlender Fortschritt wird zusätzlich anhand neuer Logeinträge geprüft. Ein fehlender Ergebnisvertrag bedeutet lediglich `waiting_for_result`; ohne diese Runner-Anbindung ist eine zuverlässige Absturzerkennung noch nicht gegeben. Alle registrierten Worker beendet, aber weiterhin laufender Status: Fehler statt Abschluss.

Eingerichtete Chat-Automation: `vision-v3-folgeagent-nach-trainingsabschluss`, mit dem Produktionsstart aktiviert, Prüfintervall **zwei Stunden**. Nach Abschluss des Folgeauftrags pausieren. Der Folgeagent startet erst nach verifiziertem Wahrnehmungsabschluss.

Die Chat-Automation prüft nach Aktivierung höchstens alle zwei Stunden ausschließlich `monitor_check.py`. Solange kein Lauf registriert ist oder der Lauf regulär arbeitet, keine neue Analyse, keinen Subagenten und keine Experimente starten. Bei Fehlern gezielt neue Logs nach Dateioffset prüfen und AGENTS-Vorgaben beachten. Nach dem einmaligen Folgeauftrag die Automation pausieren. Rechner und Codex-App müssen für lokale Aufgaben laufen. train_v3.py ist der implementierte Wahrnehmungstrainer; die gelernten Aufnahmeköpfe und der geschlossene Folgeversuch sind noch Anschlussarbeit.

## Gesamtzeitfenster ab Go

Das tatsächliche Go-Zeitfenster ist in session.json eingefroren: **02.11.2026 00:31:20 bis 16:31:20 Europe/Berlin**. Sämtliche Implementierung, Datenvorbereitung, Trainings, Validierung und Folgeagenten gehören in diese gemeinsamen 16 Stunden. Frühere 3-/6-Stunden-Teilbudgets dürfen das Gesamtfenster nicht verlängern. Ein Neustart setzt die Deadline nicht zurück. Der unabhängige lokale deadline_guard.py setzt diese Grenze durch; zweistündliche Agentenprüfungen allein reichen dafür nicht.

Für Anschlussarbeiten: data_v3.py liefert sechs Posen/Familie, model_v3.py baut maskierte Präfix-Kontexte. Auswahl M1/M2 über den Mittelwert der drei Seed-Modelle auf Modellvalidierung; nicht den besten Seed als Methodenbeleg wählen. M1 ersetzt eine Handansicht, M2 kann alte Handbilder derselben Szene behalten. Beim Kandidatenwechsel beide aktuellen festen Kameras verwenden und den reinen Feste-Kameras-Effekt getrennt kontrollieren. Die tatsächlichen Verdeckungsanteile `robot_fraction` aus Objekt-Segmentierung sind Diagnoselabels, kein zulässiges zukünftiges Kandidatenmerkmal. Erwartete Roboterverdeckung muss aus bekannter Robotik/Kalibrierung ohne unbekannte Objekte berechnet werden. Alle request/test-Familien mit den in config.json reservierten Seeds getrennt erzeugen. `test_camera_ood` verwendet camera_ood=True; Posen 1..5 separat auswerten. Es handelt sich um zurückgehaltene Gitterposen, kein Nachweis eines beliebigen neuen Kameradomänen-Transfers. `test_geometry_ood` verwendet ood=True und wird ausschließlich mit verstreuter IID-Kontrolle verglichen.
