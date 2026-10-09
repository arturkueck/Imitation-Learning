# Einstieg: abgeschlossene BC-Forschung vom 4. Oktober 2026

**Aktualisiert 2026-10-04T15:44:38.849592+02:00 / 2026-10-04T13:44:38.849592+00:00.** Sechs-Stunden-Fenster 09:11:19–15:11:19 Berlin abgeschlossen. Training und Diagnoseprozesse beendet, Wachhalteanforderung freigegeben, Automation PAUSED. Kein Anschlussversuch gestartet. Dieser Index ordnet vorhandene Evidenz; er verändert keine früheren Messungen.

## Aktuell lesen

1. [Gesamtbericht](SESSION_RESEARCH_REPORT.md): Literatur, historische Projektergebnisse, einzelner Sensorpilot, Mechanismustests, Hypothesenledger, Kosten und Grenzen.
2. [Datierte Bewertung und nächstes Vorgehen](REVIEW_20261004.md): eine letzte begrenzte Zustandsantwortdiagnose, Abbruchentscheidung, danach gegebenenfalls replizierter Trainingsvergleich.
3. [Algorithmusreferenz](method_reference_001/RESULT.md): Implementierung geprüft, kein damit erzielter Policygewinn.
4. [Endprüfung](final_verification_1791119630.json) und [Automationsabschluss](automation_closeout.json).
5. [Projektziel und Forschungsplan](../../../FORSCHUNGSPLAN.md).

**Fazit:** Konkrete Mängel der bisherigen Dynamiknäherung identifiziert; voller und lokaler Aktionsansatz verbessert einige Vorhersagen. Die empirische Fehlerhülle überträgt sich nicht zuverlässig. Noch keine robuste neue BC-Verbesserung oder schnellere Lernkonvergenz. Lift-Erfolg ist kein stabiler Stack.

## Datierung der Primärjobs

Alle Zeiten **04.10.2026, Europe/Berlin (UTC+02:00)**. Start aus launch.json, Ende aus supervisor_result.json; dies datiert die Ausführung des Primärjobs, nicht den späteren Bericht oder seine Reparatur. Der technische Rückgabecode allein entscheidet nicht über wissenschaftliche Gültigkeit. Beispielsweise hat mechanism_AB_001 physikalisch ungültige Daten; mechanism_correction_001 ist nach vollständiger Datenerhebung technisch gescheitert und separat analyserepariert. Details jeweils im Bericht. Manche frühen RESULT.md enthalten selbst keine Zeitzeile; die unveränderten Maschinenzeitquellen werden deshalb hier explizit verlinkt.

| Diagnosebericht | Primärjob Berlin | Unveränderte Zeitquelle |
|---|---|---|
| [clearance_filter_001](clearance_filter_001/RESULT.md) | 13:18:58–13:22:16 | [Zeitquelle](clearance_filter_001/supervisor_result.json) |
| [error_margin_001](error_margin_001/RESULT.md) | 14:13:23–14:16:43 | [Zeitquelle](error_margin_001/supervisor_result.json) |
| [external_proxy_001](external_proxy_001/RESULT.md) | 13:40:36–13:43:54 | [Zeitquelle](external_proxy_001/supervisor_result.json) |
| [gradient_audit_001](gradient_audit_001/RESULT.md) | 11:12:45–11:12:51 | [Zeitquelle](gradient_audit_001/supervisor_result.json) |
| [local_response_001](local_response_001/RESULT.md) | 12:41:14–12:44:28 | [Zeitquelle](local_response_001/supervisor_result.json) |
| [mechanism_AB_001](mechanism_AB_001/RESULT.md) | 09:46:30–09:49:19 | [Zeitquelle](mechanism_AB_001/supervisor_result.json) |
| [mechanism_AB_002](mechanism_AB_002/RESULT.md) | 09:51:40–09:54:29 | [Zeitquelle](mechanism_AB_002/supervisor_result.json) |
| [mechanism_action7_001](mechanism_action7_001/RESULT.md) | 10:11:39–10:15:38 | [Zeitquelle](mechanism_action7_001/supervisor_result.json) |
| [mechanism_correction_001](mechanism_correction_001/RESULT.md) | 10:41:26–10:44:16 | [Zeitquelle](mechanism_correction_001/supervisor_result.json) |
| [mechanism_domain_001](mechanism_domain_001/RESULT.md) | 11:40:19–11:43:49 | [Zeitquelle](mechanism_domain_001/supervisor_result.json) |
| [method_reference_001](method_reference_001/RESULT.md) | 14:47:32–14:47:38 | [Zeitquelle](method_reference_001/supervisor_result.json) |
| [recorded_domain_001](recorded_domain_001/RESULT.md) | 11:53:36–11:54:02 | [Zeitquelle](recorded_domain_001/supervisor_result.json) |
| [recorded_response_001](recorded_response_001/RESULT.md) | 12:17:43–12:27:13 | [Zeitquelle](recorded_response_001/supervisor_result.json) |

Der Sensorpilot ist separat in [RESULT.md](RESULT.md) und [run_result.json](attempts/attempt_002/run_result.json) dokumentiert. Seed 41004, 2.000 Updates je Arm, 104 vollständige Episoden einschließlich Lernkurve. Abschlusszeit aus der Run-Zeitquelle; [Agentprüfungen](agent_checks.jsonl) und [lokale Aufsicht](monitor_checks.jsonl) sind getrennt. Zusammenfassungen sind keine weiteren Trainingsreplikate.

## Historie und Aufbewahrung

[PILOT_INTERPRETATION.md](PILOT_INTERPRETATION.md), [früherer Forschungsstatus](../RESEARCH_STATUS.md), [ursprünglicher Anschlussplan](../NEXT_EXPERIMENT.md), alle NEXT_*.md/NEXT_*.json sowie SESSION_CLOSEOUT.md und FINAL_CHECK_COMMANDS.md sind historische Sessionanweisungen, keine aktuellen Startaufträge. Der aktuelle Vorschlag steht ausschließlich in REVIEW_20261004.md/FORSCHUNGSPLAN.md; seine Ausführung ist hier nicht angeordnet.

Alle Diagnoseordner einschließlich gescheiterter Vorprüfungen/Versuche und Analyse-Reparaturen bleiben vollständig erhalten. Historischer Diffusionsabbruch und andere Experimentserien werden nicht bereinigt. Die Session enthält vor dieser Ordnung rund 308 MB (294 MiB); die größten Dateien sind wissenschaftliche Rohdaten, kein entbehrlicher Cache. Archivierung der Hilfsskripte ordnet den Arbeitsbereich und spart keinen Speicher.

[Archiv dieser Dokumentationspflege](archive/documentation_20261004T134438Z/README.md): vier nicht referenzierte Hilfsskripte und bytegetreue Originale der ergänzten Navigation. Manifest mit Originalpfad, Archivpfad, SHA256, Zeit und Wiederherstellungshinweisen. Keine Löschung.
