# Research Atlas

Die Projektwebsite verbindet Literatur, Versuchsdokumentation, Visualisierungen und Trainingsübersichten.

Der maßgebliche Quellordner dieses Repositorys ist [research-atlas-source/](research-atlas-source/README.md). Startanleitung: [LOCAL_START.md](research-atlas-source/LOCAL_START.md).

```powershell
# Im Repository-Stamm oder in diesem Ordner:
npm start
```

Danach `http://127.0.0.1:4173` öffnen. Dieser Lesemodus benötigt keinen Build und keine Installation der Website-Abhängigkeiten.

Lokale Editor-/Deploymentkopien können zusätzlich vorhanden sein. Sie sind kein Nachweis für den veröffentlichten Stand. Details zu Serverbetrieb und Exporten stehen im Quellordner.

## BC / Curriculum, Stand 12.11.2026

Die Seite [curriculum.html](research-atlas-source/public/curriculum.html)
ordnet 30k-Reihenfolge, 60k-Fortsetzung, feste Abschlussfunktion und die frische
Zeitkorrekturprüfung getrennt ein. Sie zeigt den vorbereiteten A/B/C-Vergleich
ausdrücklich noch ohne neue Trainingsresultate. Der lokale Trainingsmonitor
enthält fünf passende Robot-/IL-Einträge. Die statische Veröffentlichung ist
ein datierter Snapshot, kein Livezugriff auf den Trainingsrechner.

Lokale Protokolle und Modellablage: [experiments/curriculum/README.md](../experiments/curriculum/README.md).
