# Technische Fortsetzung nach Prozessabbruch

Windows-Anwendungslog: CodexSandboxService.OpenAI.Codex Ereignis1000 um20:11:09 Berlin, unmittelbar beim letzten gespeicherten Evaluationsstart. Kein Rechnerneustart (Boot22.10.) und kein Pythontraceback gefunden. Zeitliche Korrelation ist kein Ursachenbeweis. Supervisor und Worker fehlten nachweislich.

Fortsetzung aus gemeinsamem Update3000 inklusive AdamW-Zustand und je Seed identischem NumPy-Samplerzustand. Keine neuen Daten, keine geänderte Lernrate, maximal Gesamtupdate10000. Vorherige Daten und Quellen bleiben gehasht. Neuer Code in separaten Dateien; Originale und Ausgaben bleiben erhalten.

Die gemeinsame3000er Entwicklungsrunde wurde nicht vollständig beendet. Sie wird für ALLE Modelle als Auswahlpanel ausgeschlossen. Gemeinsame Auswahlkandidaten bleiben Update0 und10000; keine Wiederholung des unterbrochenen Starts524007. Diese offen dokumentierte Protokolländerung ist rein technisch und nutzt keine Endtestergebnisse.

Originale Trainings-/Gesamtdeadline werden übernommen, nicht neu gestartet. Der neue Supervisor schreibt seinen Lebensstatus fortlaufend und wird über den Windows-Prozessdienst gestartet, dessen Elternprozess unabhängig vom Agenten ist. Vor echtem Training werden Prozess-Unabhängigkeit und echte Checkpointfortsetzung kurz technisch geprüft. Stündliche Agentkontrolle; kein permanentes Agentwarten.

## Gemessene Prozess-Isolation

Der venv-Pythonlauncher erzeugt im Probeprozess ein Jobobjekt, auch beim Start via WMI und Breakawayflag. Direkter Basis-Pythonstart via WMI mit CREATE_BREAKAWAY_FROM_JOB ergab dagegen query_ok=true, is_process_in_job=false, PID22700. Das ursprüngliche Python-Kind konnte damit nicht als unabhängig von seinem Launcher gelten. Ein Neustart des Codex-Sandboxservice ist um18:11:09UTC belegt; ein Kausalnachweis zum Prozessverlust fehlt weiterhin.

Fortsetzung über Basis-Python mit derselben venv-site-packages-Umgebung. Bootstrap prüft für Supervisor UND Worker die echte Windows-Jobzugehörigkeit und verweigert Training bei einer Jobbindung. Die Probe mit geladenem AdamW-/Samplerzustand führte alle sechs Modelle technisch von3000 auf3001; B0/B-Samplehashes stimmen überein. Echte Fortsetzung verwendet weiterhin ausschließlich die ursprünglichen3000er Checkpoints.
