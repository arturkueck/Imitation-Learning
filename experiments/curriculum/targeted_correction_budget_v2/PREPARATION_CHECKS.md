# Methodikrevision v2 und Prüfung · 17.11.2026

**Wissenschaftlicher Lauf: READY, nicht gestartet.**
`praxis/results/curriculum/targeted_correction_budget_v2/night_20261117`.
Deadline unverändert 18.11.2026, 09:00 Europe/Berlin. Diese Revision entstand
auf den Auftrag, die Methodik vor dem Start zu verschärfen. V1 wird bewahrt;
ihr nie gestarteter Lauf wird als SUPERSEDED gegen versehentlichen Start gesperrt.

## Konkrete Verschärfungen gegenüber v1

1. **Ein Hauptkontrast:** Zustandsherkunft zusätzlicher Labels, ausschließlich
   auf den drei jeweils nicht zur Sammlung verwendeten Parents. Andere sechs
   Datenblock/Parent-Kombinationen sind zusätzliche beschreibende Analysen.
2. **Keine Sammelzustände des Zielparents:** Die beiden anderen Parents
   liefern nach vorab balancierter, zufälliger Zuteilung die Trainings- und
   Validierungszustände. Das vollständige 3×3-Gitter bleibt erhalten.
3. **Gleiche Lernbedingungen:** gemeinsame Szenen, passende Labelzahlen und
   Abschlusslabels, identische Batches und Updates. Familiengleiches Sampling
   verhindert die unbemerkte Bevorzugung längerer Phasen. Erhebungskosten
   bleiben separat; kein unzutreffender Anspruch gleicher Abfragekosten.
4. **Abdeckung und Abbrüche:** feste Sammelversuche und Ausfallkategorien,
   zusätzlich Mindestabdeckung jedes Collectors; keine Ersatzstarts.
5. **Ein vollständiger Endpunkt:** 150 neue Bestätigungsszenen, alle im
   Erfolgsnenner. Griffquoten werden mit bedingtem Nenner separat ausgewiesen.
6. **Gepaarte Unsicherheit:** Bootstrap über ganze Szenen mit allen drei
   Hauptpaaren zusammen. Bedingt auf die eingefrorenen Parents/Datensätze;
   weder 450 noch 1.350 unabhängige Szenen. Keine Populationsbehauptung aus
   nur drei Modellseeds. Fester +5pp-Schwellwert, Intervalluntergrenze > 0,
   positive Richtung in allen Hauptpaaren und kein mittlerer Rückschritt
   gegenüber Replay/B. Ein Nullbefund ist kein Gleichwertigkeitsnachweis.
7. **Tatsächliche Testsperre:** alle 54 Checkpoints müssen mit richtiger
   Parent-/Komponenten-ID, korrektem Plan und Update 5.000 eingefroren sein.
   Hashprüfung vor Öffnung und nach Auswertung. Primärergebnis vor sekundären
   Tests festschreiben; es darf durch deren Ergebnisse nicht verändert werden.
8. **Vorab geplanter Teilausgang:** nur ein vollständig abgeschlossener
   Haupttest bleibt berichtbar, wenn die Zusatztests die feste Deadline
   erreichen. Keine positive Aussage aus einem verkürzten Hauptpanel.

Der Präfixwechsel variiert mehrere Zustandsmerkmale gemeinsam. V2 isoliert
das Erhebungsprotokoll, nicht den einzelnen physikalischen Wirkmechanismus.
Die Wahl des zweiten Anfahrens ist bereits diagnostisch begründet und wird
hier nicht automatisch gelernt. Kein Critic-, Reihenfolge-Curriculum-,
Hardware-, OOD- oder Neuheitsnachweis wird daraus abgeleitet.

## Technische Nachweise

- **15 Tests bestanden:** darunter Collector-Ausschluss und balancierte
  Zuteilung, familiengleiches Sampling bei unterschiedlich langen Phasen,
  unverändert breites Szenenintervall bei künstlicher Wiederholung derselben
  Szenen, Unabhängigkeit des Hauptresultats von sekundären Resultaten,
  Zurückweisung fehlender/doppelter Haupttestzellen, technische Nicht-Evidenz,
  Checkpointmanipulation, Deadline und echtes Beenden eines eigenen Prozessbaums.
- **smoke_002 COMPLETE**, 287,6 Sekunden: drei getrennte technische
  Erhebungsblöcke, 54 Komponenten mit je vier Updates, alle neun Modell-/
  Datenkombinationen. 72 Zeilen aus **60 tatsächlichen** Episoden, einschließlich
  der Wiederverwendung unveränderter Baselines.
- Geeignete technische Trainingsfamilien je Block: 2/4/4, Validierung 3/3/3.
  Verwendete Labels je Datenquelle: Training 35/82/75, Validierung 56/61/62.
  Zwischen Standard/Targeted exakt gleiche Familien und Abschlusslabels.
  Technische Mindestabdeckung ist bewusst reduziert; wissenschaftliche
  Schwellen bleiben in der Vollkonfiguration unverändert.
- Tatsächlicher Collector-Ausschluss in allen drei Datenblöcken geprüft.
  Sämtliche 54 Checkpoints vor Testöffnung eingefroren. Das vollständige
  Hauptresultat wurde vor der ersten sekundären Episode geschrieben.
- Alle sechs Quell-/Komponententypen von Update 2 bis 4 bitgleich fortgesetzt:
  Modellgewichte und vollständiger Optimizerzustand; Phasen 1–6 unverändert.
  Die Samplepläne zwischen Datenarmen sind identisch.
- Technischer Analyseausgang ausdrücklich
  `TECHNICAL_ONLY_NO_SCIENTIFIC_CLAIM`. Wissenschaftliche Bestätigungsszenen
  wurden nicht geöffnet. Keine Erfolgsquote des Smokes wird als H1-Befund genutzt.
- Quelle und Umgebung sind mit SHA-256 erfasst. PowerShell-Startskript ist
  syntaktisch geprüft; sein Start bleibt auf READY und einmaligen Aufruf begrenzt.

`smoke_001` war ein früherer kleiner technischer Durchlauf der Revision.
Er bleibt erhalten. Freigaberelevant sind die finalen Quellen und die
vollständige Gitterprüfung in `smoke_002` samt Resume-Verifikation.

## Zeitbedarf und Bedienung

Vollplanung: 450 Sammelpaare, 270.000 Komponentenupdates und 5.100 tatsächliche
Auswertungsepisoden. Planungswert **circa 5–8 Stunden**, abgeleitet aus
technischem Durchsatz und dem vorherigen abgeschlossenen 5k-Korrekturlauf;
keine Laufzeit- oder Fertigstellungsgarantie. Der Haupttest hat feste Priorität,
keine wissenschaftliche Größe wird zur Ausschöpfung der Nacht nachträglich erhöht.

Start: `powershell -NoProfile -File experiments/curriculum/targeted_correction_budget_v2/start.ps1`.
Kontrolle: der in diesem Ordner vorhandene inkrementelle `monitor.py`.
Für verlässliche Windows-Prozessidentität sind gegebenenfalls Leserechte
außerhalb der eingeschränkten Codex-Sandbox erforderlich. Das ist eine reine
Kontrolle; bei fehlender Sichtbarkeit meldet der Monitor WARNING statt eines
falschen Trainingsabbruchs.
