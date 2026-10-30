# Research Atlas lokal starten

Im Website-Ordner ausführen:

```powershell
cd 'F:\Desktop\Programmieren\IT\Imitation Learning\sites\research-atlas-source'
npm start
```

Dann http://127.0.0.1:4173 öffnen. Node.js genügt; für diesen lokalen Lesemodus sind weder npm install noch ein Build notwendig. Startseite: eigene Trainingsresultate. Die Paperbibliothek ist über die Navigation erreichbar. Diagramme, Quellen und Videos werden lokal ausgeliefert. Die Messdaten sind ein geprüfter Stand vom 25.10.2026, kein automatischer Live-Monitor.

Beenden: Strg+C. Bei belegtem Port in PowerShell `$env:PORT=4175` setzen und erneut `npm start` ausführen.

Für serverseitigen Paperimport und die Research-API: Abhängigkeiten installieren und `npm run dev` verwenden. `npm run start:server` erhält den bisherigen Wrangler-Start für einen vorhandenen Produktionsbuild. Lokale API-Speicherung ist von der veröffentlichten privaten Website getrennt.

Alternativ funktioniert `npm start` auch direkt im Repository-Stamm oder im Ordner `sites`. Beide leiten auf denselben lokalen Research Atlas weiter; `npm install` ist dafür nicht erforderlich.
