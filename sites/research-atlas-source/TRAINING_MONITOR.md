# Modell-Trainings im Research Atlas

Unter Eigene Forschung führt **Modell-Trainings** zu `/trainings.html`.
Modellrolle und Lernverfahren sind getrennt: Robot / Vision / Placement Quality
gegenüber IL / RL / überwacht. Leere Kategorien enthalten keine erfundenen Läufe.

## Lokal – direkt aus Trainingsdateien

`npm start` startet den Atlas auf127.0.0.1:4173, ohne Build/Installation.
Der Browser fragt alle15s `/api/trainings` ab; bei verborgenem Tab ruht Polling.
Der lokale Server liest ausschließlich das Register `monitor/training-runs.json`
im übergeordneten Imitation-Learning-Workspace und die dort benannten Dateien.
Kein Modellaufruf, kein Laden von Gewichten, keine Trainingssteuerung.

Neue Läufe werden mit Kategorie, Lernverfahren, Konfiguration, Kurvenpfad und
freigegebenen Artefakten registriert. Die V1-Adapter verstehen sowohl update/arm
als auch updates/arm. Für neue IL-/RL-Metriken muss das vereinbarte Schema um
beispielsweise Return, Erfolgsrate oder Actor-/Critic-Loss erweitert werden;
die Kategorien-/Methodenauswahl ist bereits vorhanden. Es werden noch keine
historischen Robot-Läufe automatisch als einheitliche Monitoringläufe importiert.

Statuspriorität: expliziter Abbruch vor früheren Heartbeats; Fehler; Abschluss;
laufender Status nur mit frischem Heartbeat. Nach3min ist der Status als veraltet
gekennzeichnet. Ein frischer Dateistatus beweist allein keine Prozessgesundheit;
der Trainingssupervisor bleibt für Prozess-/Fehlerprüfung zuständig.

Trainings-/Validationkurven, Seed-/Kamerawahl, Positionsfehler und Logskala sind
interaktiv. Architektur, Optimierer, Konfiguration, Status, Hardware und
Checkpointbeschreibung werden angezeigt. V2 ist ein Entwurf; die Geometrie-
Illustration hat eine ausdrückliche Demo-Kennzeichnung. Der V1-Nachtlauf ist
abgebrochen; Snapshot und Kurven behaupten keine ausgeführten Endtests.

## Private gehostete Website – exportierter Snapshot

`npm run training:export` aktualisiert public/training-data/index.json und die
freigegebenen Artefakte. Die private Publikation enthält diesen Datenstand.
Die Anzeige benennt Datum und **keine Live-Verbindung zum Trainingsrechner**.
Ein Remote-Live-Sync ist damit nicht implementiert: Cloudflare kann keine lokalen
F:-Dateien lesen. Dafür wäre ein authentifizierter Uploader/Relay mit dauerhafter
Autorisierung nötig. Browserpolling einer statischen Datei ist kein Live-Training.

Das lokale `npm run dev` für die Paper-API besitzt keinen Dateisystem-Monitor;
dafür `npm start` verwenden. Vor dem Export/Publizieren kann jeder lokale Lauf
über das Register freigegeben werden. Lokale absolute Pfade und Credentialfelder
werden aus dem JSON entfernt; nur registrierte Artefakte sind zugänglich.
Die lokale API bindet an Loopback und prüft Host/HTTP-Methode. Es gibt weder
Stop-/Restart-Endpunkte noch Zugriff auf beliebige angefragte Dateipfade.

## Prüfung

`node --test scripts/training-monitor.test.mjs`

Die Tests prüfen Abbruchpriorität, überalterte Heartbeats, beschädigte Metriken,
Pfad-/Hostgrenzen und das Weglassen lokaler Credential-/Pfadfelder.
Browserprüfung: V2-Entwurf, V1-Abbruch mit24.900Updates und6Varianten, echte
Losskurven, Seedwahl, Logskala, leere Kategorien und Demo-Hinweis.
