# Monitoringdaten

Dieser Ordner enthält das Laufregister und lokalen Zustand für das Trainingsdashboard.

- [training-runs.json](training-runs.json): registrierte Läufe sowie Pfade zu Konfigurationen, Status, Kurven und freigegebenen Artefakten.
- `dashboard_process.json`: lokale Prozessinformation; eine PID allein beweist keinen laufenden Prozess.
- `vision-data-claims.sqlite` und `vision-namespace/`: lokaler Zustand der Vision-Datenverwaltung.

Implementierung und Statusregeln: [TRAINING_MONITOR.md](../sites/research-atlas-source/TRAINING_MONITOR.md). Lokal mit `npm start` im Repository-Stamm öffnen, danach `http://127.0.0.1:4173/trainings.html`.

Das Register startet kein Training. Dateistatus und Dashboard ersetzen keine Prüfung von Prozessidentität und Trainingsfortschritt. Die lokalen Zustandsdateien nicht während eines laufenden Versuchs zurücksetzen.
