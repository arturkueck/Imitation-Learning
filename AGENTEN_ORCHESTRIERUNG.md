# Agenten-Orchestrierung: Claude Code und Codex in unbeaufsichtigten Läufen

Gültig ab 19.11.2026 für alle künftigen Nacht- und Tagesläufe. Ergänzt
[AGENTS.md](AGENTS.md) und [Agend.md](Agend.md). Bei einem Widerspruch gelten deren
Forschungs-, Freigabe- und Monitoringregeln. Diese Datei regelt nur, **wer** eine
Aufgabe bearbeitet und **wie viel Agentenkontingent** dafür eingesetzt wird.

## 1. Rollen

| Rolle | Wer | Aufgabe |
|---|---|---|
| Steuerung | `experiments/critic/three_cube_transfer_v1/night_agent.py`, gestartet von der Windows-Aufgabe | Einzige Instanz, die Agenten startet, Anbieter wählt, Kontingent bucht und committet. Eine Sperre verhindert parallele Steuerungen. |
| Agent | je Aufgabe genau ein Claude-Code- oder Codex-Prozess | Bearbeitet genau die zugewiesene Aufgaben-ID und übergibt strukturiert (Dateien, Commitnachricht). Startet keine weiteren Agenten. |
| Supervisor | Prozess eines langen Laufs | Setzt Cutoff und Deadline unabhängig vom Agenten und vom Kontingent durch. |
| Nutzer | Artur | Erteilt Freigaben im NACHTPLAN, hebt eine Gesamtpause auf, ändert Aufgabenliste und Kontingentregeln. |

## 2. Aufgabenliste

- Maschinenlesbar in `experiments/critic/three_cube_transfer_v1/tasks.json`: ID, Abhängigkeiten,
  Freigabehäkchen (`gate`), erlaubte Anbieter in Vorzugsreihenfolge, Art, `light` für kurze
  Aufgaben und `not_before` als frühester Start.
- `STATUS.md` muss genau dieselben IDs enthalten, sonst hält die Steuerung an.
- Neue Aufgaben werden gleichzeitig in der NACHTPLAN-Tabelle, in `tasks.json` und als Zeile in
  `STATUS.md` angelegt. Das tut der Nutzer oder eine vom Nutzer beauftragte Planungssitzung,
  nie ein Nachtagent. Agenten ändern weder `tasks.json`, `orchestration.json`, den NACHTPLAN
  noch die Steuerung.

## 3. Zuordnung der Anbieter

Die Reihenfolge in `providers` ist die Vorzugsreihenfolge. Ist der bevorzugte Anbieter
nicht verfügbar, übernimmt der nächste erlaubte. Grundzuordnung:

| Art der Aufgabe | Bevorzugt | Begründung |
|---|---|---|
| Simulation mit eingefrorenen Modellen, Vorwärtsdiagnosen, Monitorprüfungen (`D1a`, `D1b`, `N2-4`, `N3-2`) | Codex | kurze, technische Schritte |
| Freigegebene Läufe mit Optimizerupdates (`N2-1b`, `N2-2b`, `N2-3v2`, `N3-1`, `N4-4`) | Claude | entspricht der bisherigen Freigabe „für Claude Code“, Codex als Rückfall |
| Analyse, Protokoll, Berichte, Abbildungen (`B-1` … `B-4`, `N4-1` … `N4-3`) | Claude | Text und Begründung |

**Freigaben gelten anbieterunabhängig.** Ein abgehaktes Freigabehäkchen im NACHTPLAN erlaubt
die Aufgabe für Claude und Codex. Jeder Agent prüft das Häkchen unmittelbar vor dem Start eines
Laufs mit Optimizerupdates selbst. Will der Nutzer eine Aufgabe auf einen Anbieter beschränken,
steht in `tasks.json` nur dieser Anbieter.

## 4. Kontingent dynamisch berücksichtigen

Die Steuerung führt je Nacht ein Verbrauchsbuch
`%LOCALAPPDATA%\Codex\three-cube-night\usage_<JJJJMMTT>.json`: Agentenläufe, Ausgabetokens,
Kosten, letzter Kontingentstand und Pausen je Anbieter. Vor jeder Zuweisung wählt sie den
ersten Anbieter, für den alles Folgende gilt:

1. **Keine Limitpause.** Meldet ein Anbieter ein erschöpftes Kontingent („usage limit“,
   „rate limit“, 429 und Ähnliches), wird er bis zum gemeldeten Rücksetzzeitpunkt pausiert,
   ohne Angabe für `default_cooldown_minutes`. Die Aufgabe bleibt vorgemerkt und geht an den
   anderen erlaubten Anbieter oder wartet. **Ein Limit ist kein Fehlschlag** der Aufgabe und
   zählt nicht als Reparaturversuch nach AGENTS.md §5.
2. **Gemeldeter Stand.** Codex läuft mit `--json`, die Steuerung liest daraus `used_percent`
   und die Rücksetzzeit. Ab `defer_heavy_above_used_percent` (80 %) bekommt Codex nur noch
   kurze Aufgaben und Monitorprüfungen, ab `stop_above_used_percent` (95 %) nichts mehr bis
   zum Rücksetzen. Claude meldet Tokens und Kosten je Lauf, aber keinen Restbestand. Für
   Claude gelten deshalb die Grenzen aus Punkt 3 und die Limitpause aus Punkt 1.
3. **Eigene Obergrenzen** aus `orchestration.json`: Agentenläufe und Ausgabetokens je Nacht,
   optional Kosten. Eine Reserve (`reserve_runs_for_handover`) bleibt für die Morgenübergabe frei.
4. **Wiederholte Fehler.** Nach `max_consecutive_failures_per_task` (2) Fehlschlägen einer Aufgabe
   in einer Nacht teilt die Steuerung sie nicht erneut zu, um kein Kontingent zu verbrennen.

Ist für keine bereite Aufgabe ein Anbieter verfügbar, endet die Steuerung mit einem
Logeintrag. Der nächste Termin im Zeitplan prüft erneut.

**Laufende Simulationen sind vom Kontingent unabhängig.** Ein Limit führt nie zum Anhalten,
Abbrechen oder Neustarten eines Laufs. Supervisor und Deadline wirken ohne Agent.

## 5. Kontingentschonendes Arbeiten der Agenten

- Ein Agent je Aufgabe. Langen Lauf unter Supervisor starten, Prozessidentität und
  Monitorbefehl dokumentieren, dann **enden**. Kein Warten oder Abfragen im Agenten, die
  nächste Prüfung übernimmt der Zeitplan.
- Monitorprüfungen kurz halten: Monitorbefehl ausführen und bei gesundem Stand sofort enden
  (AGENTS.md §5).
- Nur nötige Dateien lesen. Keine großen Logs, Rohdaten, Gewichte oder `praxis/results/`
  vollständig in den Kontext laden. Zusammenfassungen und Monitore verwenden.
- Analysen als Skript schreiben und ausführen, nicht im Agentendialog rechnen.
- Bei Kontingentwarnung in der Ausgabe die Arbeit sauber übergeben, statt sie abzubrechen.

## 6. Ablauf einer Nacht

| Zeit (Berlin) | Schritt |
|---|---|
| 22:00, 01:00, 04:00, 07:00 | Steuerung: zuerst laufende Aufgaben über ihren Monitor prüfen, dann bereite Aufgaben nach `tasks.json` mit verfügbarem Anbieter zuweisen. Abbildungen nach Meilensteinen nur mit Claude-Kontingent. |
| ab 07:30 | keine neuen Läufe |
| 07:30, 08:30 | Morgenübergabe mit beliebigem verfügbarem Anbieter. Der Nachtbericht nennt unter „Integrität“ den Kontingentstand je Anbieter, zurückgestellte Aufgaben und Limitpausen. |
| 09:00 | harte Deadline der Supervisoren |

## 7. Künftige Nächte einrichten

Die bestehende Windows-Aufgabe deckt die Nächte ab 18.11.2026 bis zur Übergabe am 22.11.2026
um 09:00 ab. Für weitere Nächte die Aufgabe deaktivieren und neu registrieren, etwa:

```powershell
Disable-ScheduledTask -TaskName 'Codex - Dreierturm Nachtagenten'
Unregister-ScheduledTask -TaskName 'Codex - Dreierturm Nachtagenten' -Confirm:$false
./experiments/critic/three_cube_transfer_v1/install_night_agent.ps1 -FirstNight 2026-11-18 -Nights 10
```

Kontingentgrenzen ändert der Nutzer in `orchestration.json`. Sie werden bei jedem Start neu
gelesen, ein Neustart ist nicht nötig.

## 8. Grenzen

Den Restbestand eines Claude-Abonnements kann die Steuerung nicht abfragen. Sie reagiert auf
Limitmeldungen und hält sich an die eigenen Obergrenzen. Die Codex-Angaben hängen davon ab,
dass die installierte Codex-Version `--json` mit Kontingentereignissen ausgibt. Fehlen sie,
gelten dieselben Regeln wie für Claude.
