# Prüfung des Lernmaterials

Geprüft am **2. Oktober 2026, Europe/Berlin**. Die Prüfungen beziehen sich auf die Lehrmodelle; keine neue Evaluation wissenschaftlicher Algorithmen oder eures Roboters.

## Rechenprüfung

`node test_engine.cjs` prüft:

- skalare Fehlerrekurrenz gegen ihre geschlossene Lösung;
- Eigenwerte der 2×2-Kopplungsmatrix;
- RK4 gegen exakte exponentielle Lösung ohne Kopplung und gegen die analytische Produktlösung;
- vorübergehendes Normwachstum trotz stabiler Eigenwerte;
- tatsächliches Neufitten nach einer DAgger-Lehrrunde;
- Unterschied zwischen DART-Ausführungsaktion und unverrauschtem Expertlabel;
- analytischen Gaußmischungs-Score, endliche Samplerwerte und Seed-Reproduzierbarkeit;
- positive definite Beispielkovarianz und `T trΣ=α`;
- Unterschied im Feedback beim Zielwechsel und endliche Chunk-/Ensemblingausgaben.

Die Syntax beider JavaScript-Dateien wurde mit `node --check` geprüft. Die Rechnungen des Atlas und der Lösungen wurden zusätzlich redaktionell nachgerechnet.

## Browserprüfung

Headless Chromium über das installierte Chrome; Desktop 1200×1000, schmale Ansicht 390×844. Alle sechs Panels und ihre Interaktionen wurden geprüft: Parameteränderung, DAgger-Runde/Reset, lineare und Produktkopplung, deaktiviertes d in der Produktvariante, deaktiviertes T_a bei Ensembling, Sampleiteration/Seed/Reset. Keine JavaScript-Laufzeitfehler, keine externen Netzwerkanfragen, kein horizontaler Seitenüberlauf in der schmalen Ansicht.

Ergebnis: [_qa/browser_validation.json](_qa/browser_validation.json). Screenshots liegen ebenfalls in `_qa/`; Diagramme, Achsen und Lesbarkeit wurden in der Desktopansicht und anhand der schmalen/dunklen Kopplungsansicht visuell geprüft.

## Was diese Prüfung nicht belegt

Die Tests bestätigen die dokumentierten kleinen Rechenmodelle. Sie belegen keine Leistung von DAgger, DART, Stable-BC, ACT oder Diffusion Policy auf einer realen Aufgabe. Das Material ist eine Lernhilfe, kein neuer Primärbeleg. Die Nachvollziehbarkeit der Fachquellen bleibt über die existierende Wissensbasis erhalten.

## Erneut prüfen

Für die Rechenprüfung genügt Node.js:

```powershell
node test_engine.cjs
```

Der Browser-Test benötigt Playwright und Chrome und gehört zur Entwicklung, nicht zum Starten des Lernlabors. In der hier geprüften Umgebung:

```powershell
$env:LEARN_NODE_DEPS='C:/Users/artur/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules'
$env:LEARN_CHROME='C:/Program Files/Google/Chrome/Application/chrome.exe'
node test_browser.cjs
```

Die Simulationen selbst brauchen nur einen modernen Browser. Es wurde keine Software installiert.
