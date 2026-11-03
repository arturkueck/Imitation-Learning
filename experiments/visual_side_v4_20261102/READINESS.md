# Parallel-Update, 03.11.2026

Aktuelle Vorbereitung: prepared_004, vier Windows-spawn-Simulator-Worker. Keine Änderungen an Modell, Loss, Szenenzahlen, Familienzuordnung oder Kollisionskriterien.

26 Tests bestanden. Vollständige historische Hashprüfung bestanden. Acht neue Entwicklungsszenen parallel erzeugt: 94,59 Sekunden einschließlich Workerstart und Kamerabank-Initialisierung. Familien-/Historien-/Inhaltsüberschneidungen: jeweils null. Modell-Vorwärtslauf und 3D-Vorschauen bestanden, null Vision-Optimizer-Updates. Noch kein Trainingsbudget und kein Haupttraining gestartet.

Die kleine Stichprobe hat andere Familien als die vorherige serielle Prüfung und enthält Startkosten; sie belegt keinen exakten Beschleunigungsfaktor und keine garantierte Gesamtlaufzeit. Anleitung: [PIPELINE.md](PIPELINE.md).

---

Nachfolgend der erhaltene frühere Prüfstand von prepared_003:

# Pipeline-Prüfung, 03.11.2026

Aktuell eingefrorener Lauf: `prepared_003`. Anleitung und Versuchsaufbau: [PIPELINE.md](PIPELINE.md).

- 25 gezielte Tests bestanden: historische Rollen, Inhaltsduplikate, gleichzeitige Schreiber, transaktionale laufübergreifende Datenansprüche, Ausschluss zukünftiger Bilder, gemeinsame Ziele, räumlicher Kamera-Holdout, exakte Wiederaufnahme inklusive Teilgradienten und sechs Trainings-/Validierungsspuren mit winzigen synthetischen Modellen.
- Vollständige Hashprüfung sämtlicher über die vier V2-/V3-Train-/Validation-Manifeste eingebundener Arrays sowie der eingefrorenen Startgewichte bestanden: `pipeline_verify_003.log`.
- Acht neue Entwicklungsszenen erzeugt und unabhängig geprüft: keine Familien-, historische oder Inhaltsüberschneidung. Diese Szenen bleiben vom Haupttraining ausgeschlossen.
- Vorwärtslauf des unveränderten V3-Startmodells auf diesen Szenen bestanden. Diagnose-Loss 0,11172 ist kein V4-Trainingserfolg. Acht 3D-Vorschauen samt Originalbildern und interaktiven Szenen liegen unter `prepared_003/development_preview/geometry`.
- **Null Optimizer-Updates am Vision-Modell, keine V4-Checkpoints, kein gestartetes Zeitbudget.** Die Optimizer-Regressionen betreffen ausschließlich synthetische Testnetze.

Die vollständige Datenerzeugung benötigte in dieser kleinen Stichprobe 3,52–34,19 Sekunden pro Familie, Mittel 19,31 Sekunden. Das umfasst acht vorgesehene Kamerakontexte, geprüfte Routen und Nachzentrieren; 6–8 Kontexte je Familie waren verfügbar. Eine rein lineare Hochrechnung auf 20.000 neue Trainings-/Validierungsfamilien läge bei rund 107 Stunden allein für die Datenerzeugung. Acht Familien sind keine belastbare Laufzeitprognose, zeigen aber klar: Ein kompletter Lauf in zehn oder sechzehn Stunden ist mit dieser Konfiguration derzeit nicht belegt. Vor einer solchen Freigabe muss die Datenerzeugung beschleunigt oder ein ausdrücklich genehmigter kleinerer Pilot festgelegt werden. Es wurden dafür keine Datenzahlen oder wissenschaftlichen Parameter stillschweigend geändert.

Die Modellqualität nach Training, die Eignung zusätzlicher Seitenansichten und die aktive Aufnahmeentscheidung sind noch offen. Die gebauten Loss-/Geometrieberichte werden im echten Training automatisch geschrieben. Die Vorbereitung ist lokal im Monitor registriert; die Website wurde in diesem Schritt nicht veröffentlicht.
