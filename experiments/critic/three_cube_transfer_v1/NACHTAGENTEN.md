# Automatische Nachtübergabe

Die Windows-Aufgabe `Codex - Dreierturm Nachtagenten` arbeitet im separaten Worktree auf `experiment_three_cube_critic`. Der Fortschritt steht in [STATUS.md](STATUS.md). Der erste Abend ist der 18.11.2026, die letzte Übergabe am 22.11.2026 um 09:00 Uhr (Berlin). Die vier Kalendernächte bleiben auch dann fest, wenn eine Aufgabe länger dauert.

- **22:00, 01:00, 04:00, 07:00** – Fortschritt prüfen. Eine laufende Aufgabe zuerst über ihren Monitor prüfen. Bei freier Kapazität die nächste zulässige Aufgabe bearbeiten. Nach jeder erledigten Aufgabe Dokumentation lokal committen und im selben Durchgang einen frischen Codex-Prozess für die nächste bereite Aufgabe starten.
- **07:30, 08:30** – Morgenübergabe. Eine bereits abgeschlossene Übergabe wird übersprungen. Ab 07:30 keine neuen Läufe. Ein Versuchssupervisor muss die 09:00-Grenze auch unabhängig vom Agenten durchsetzen.
- **Freigabe** – Die drei Kontrollkästchen im [Nachtplan](NACHTPLAN.md) dieses Worktrees gelten. Ein Sofortstopp wird in `STATUS.md` als `Gesamtpause: ja` festgehalten. Nach Klärung dort die betroffenen Aufgaben und die Pause aktualisieren.
- **Berichte** – Pro Abend eine Datei unter `nights/`. Technische Startzeiten, Fehler und Agentenausgaben liegen unter `%LOCALAPPDATA%\Codex\three-cube-night\`. Nur geprüfte kleine Arbeitsdateien aus der Übergabe werden commit­tet. Laufdaten liegen unter `praxis/results/critic/three_cube_transfer_v1/`.
- **Betrieb** – Der Windows-Benutzer muss angemeldet sein. Die Aufgabenplanung darf den PC aufwecken, sofern die Energieeinstellungen es zulassen. Verpasste Aufrufe prüfen das aktuelle Zeitfenster. Überlappende Instanzen werden übersprungen.

Installation aus diesem Worktree mit `./experiments/critic/three_cube_transfer_v1/install_night_agent.ps1 -FirstNight 2026-11-18`. Eine vorhandene Aufgabe wird nicht überschrieben. Manueller Kontrollaufruf über `Start-ScheduledTask -TaskName 'Codex - Dreierturm Nachtagenten'`, Zeitplan deaktivieren über `Disable-ScheduledTask -TaskName 'Codex - Dreierturm Nachtagenten'`. Das Deaktivieren verhindert zukünftige Aufrufe. Einen aktiven Versuch über seinen Supervisor ordnungsgemäß übergeben.

## Tagesfortsetzung am 19.11.2026

Die zusätzliche Windows-Aufgabe `Codex - Dreierturm Tagesagenten 2026-11-19` prüft die Liste bis 15:00 Uhr (Berlin) spätestens im Abstand von zehn Minuten und startet nach einer geprüften Übergabe sofort die nächste zulässige Aufgabe. Nacht- und Tagessteuerung verwenden dieselbe Sperre und getrennte Übergabemarken. Der Tageslauf dokumentiert im bestehenden Nachtbericht. Ab 14:30 Uhr starten keine neuen Simulationen. Ab 14:45 Uhr dient die Zeit der Übergabe. Optimizerupdates bleiben an die Freigaben im Nachtplan gebunden.

Codex übernimmt Simulationen und technische Aufgaben. Claude Code erhält den Dokumentationsschritt N1-6 mit Dateitools und strukturierter Rückgabe. Scheitert die Claude-Übergabe, prüft Codex den vorhandenen Arbeitsstand beim nächsten Termin. Die Steuerung commit­tet geprüfte Übergabedateien lokal.

## Wissenschaftliche Abbildungen

Claude Code erstellt die Abbildungen dieses Vorhabens, auch bei späteren Einzelaufträgen. Der Dispatcher übergibt nach geprüften Ergebnissen N2-2, N2-3 und N4-1 automatisch an Claude. Lebende Läufe erhalten zuerst ihre Monitorkontrolle. Die Übergabe enthält die Abbildungen, den reproduzierbaren Matplotlib-Generator und die Datenquellen unter den jeweiligen `figures/`-Unterordnern. Loss, technische Stabilität und Erfolg auf unabhängigen Szenen werden getrennt dargestellt. Der vorhandene Zeitrahmen und die Laufregeln gelten. Bei einem fehlgeschlagenen Abbildungsauftrag übernimmt Claude die nächste Prüfung.
