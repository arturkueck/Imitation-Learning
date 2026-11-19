# Nachtplan: Zweier-BC → Dreierturm mit IL-informiertem Critic

Stand 18.11.2026. Aufgabenstapel für drei bis vier unbeaufsichtigte Nachtläufe.
Grundlage ist das Exposé
[proposal.tex](../../../latex/projektarbeit_proposal/v2/proposal.tex):
*Verbessert ein Critic, der auf den Ausgängen eigener Dreierversuche der
BC-Policy vortrainiert wurde, den Dreierturm auf unbekannten Starts, ohne
Dreier-Demonstrationen und ohne Experteneingriffe in Dreier-Situationen?*

Es gelten [AGENTS.md](../../../AGENTS.md), [Agend.md](../../../Agend.md) und
[experiments/AGENTS.md](../../AGENTS.md). Bei einem Widerspruch gehen diese vor.
Dieser Plan ersetzt kein Versuchsprotokoll. Das Protokoll entsteht in Nacht 1.

## Ablauf pro Nacht

1. Diesen Plan und `STATUS.md` in diesem Ordner lesen (anlegen, falls nicht vorhanden).
2. Die nächste offene Aufgabe wählen, deren Abhängigkeiten erledigt sind und
   deren Freigabe (siehe unten) erteilt ist. Die Reihenfolge innerhalb einer
   Nacht ist frei. Während Simulationen laufen, Schreib- und Analyseaufgaben erledigen.
3. Lange Läufe im Hintergrund mit Supervisor und inkrementellem `monitor.py`
   starten und knapp nach AGENTS.md §5 überwachen. Den Lauf in
   `monitor/training-runs.json` eintragen.
4. **Ab 07:30 Europe/Berlin keine neuen Läufe starten.** Bis 09:00 dokumentieren,
   committen und `STATUS.md` übergeben. Unfertige Läufe sauber anhalten und mit
   exakt belegbarem Fortsetzungspunkt (Checkpoint, RNG-, Sampler- und
   Optimizerzustand) übergeben. Nicht neu starten.

**Sofort anhalten, dokumentieren und auf den Nutzer warten**, wenn:

- eine Aufgabe eine Änderung am eingefrorenen Protokoll verlangen würde
  (Arme, Seeds, Splits, Budgets, Erfolgsdefinition, Reward, Beobachtung),
- Testfamilien gelesen, ausgewertet oder für Entscheidungen gebraucht würden,
- ein Reparaturversuch fehlgeschlagen ist (AGENTS.md §5, Punkt 6),
- der Actor zusammenbricht (siehe Abbruchkriterium in N2-3) und die Ursache
  nicht rein technisch ist.

Blockiert eine Aufgabe, mit einer anderen unabhängigen Aufgabe weitermachen.

## Freigaben

Simulation mit eingefrorenen Modellen, Analyse und Dokumentation sind
ohne Weiteres erlaubt. Aufgaben mit Optimizerupdates starten nur, wenn der
Nutzer sie hier abgehakt hat:

- [x] N2-2/N2-3: Critic-Vortraining und technischer Actor-Critic-Smoke
- [x] N3-1: wissenschaftlicher Drei-Seed-Pilot
- [x] N4-4: Training neuer unabhängiger Zweier-BC-Parents für den Hauptvergleich
- [x] N2-1b/N2-2b: Critic-Daten mit Explorationsrauschen und Vortraining des Critics IL-v2 nach [PROTOCOL_V2.md](PROTOCOL_V2.md#e-neu-critic-il-v2-mit-aktionsvariation-n2-1b-n2-2b)

Am 19.11.2026 hat der Nutzer das Pilotprotokoll und die oben markierten Arbeiten für **Claude Code** freigegeben. Claude übernimmt die Listenpunkte ab N2-1 nach ihren bestehenden Abhängigkeiten und Abbruchregeln. N4-4 setzt zusätzlich ein freigegebenes Hauptprotokoll mit begründeter Seedzahl voraus. Die Tagesfortsetzung endet am 19.11.2026 um 15:00 Uhr Europe/Berlin.

Am 19.11.2026 um 22:12 Uhr hat der Nutzer nach dem gescheiterten Smoke N2-3 **Plan B** gewählt: zuerst den Critic verbessern, Pilot frühestens in Nacht 3. Damit sind [PROTOCOL_V2.md](PROTOCOL_V2.md) freigegeben, die Gesamtpause aufgehoben und N2-1b/N2-2b freigegeben. **N2-4 und N3-1 starten nicht vor Nacht 3 (20./21.11.2026)**, auch wenn Nacht 2 früher fertig wird.

## Feste Rahmenbedingungen

- **Start-Policy:** die drei vorhandenen Standard-BC-Modelle **A** (nur
  Zweier-Demonstrationen, privilegierter Zustand), geladen über
  `experiments/curriculum/registry.py`. Modelle mit Expertenkorrekturen aus
  Dreier-Situationen (B/C-Korrekturen, `targeted_correction_budget_v2`,
  `approach_bc_correction_v1`) sind als Startpunkt ausgeschlossen.
- **Erfolg:** stabiler Dreierturm über 50 aufeinanderfolgende Frames
  (unveränderter Endpunkt). Reward 1 nur bei diesem Erfolg, sonst 0.
- **Code:** Ausgangsbasis ist `experiments/critic/base/`. Die bekannte
  Fehlerursache ist dokumentiert in
  `critic_warmstart_20261104/diagnosis_001/REPORT.md`: Actor-Drift nach der
  ersten Runde, Aufgabenerfolg bricht ein.
- **Ablage:** Code und Berichte in diesem Ordner. Laufdaten unter
  `praxis/results/critic/three_cube_transfer_v1/<lauf>/`.
- **Branch:** `experiment_three_cube_critic`, abgezweigt von `dev`, sobald dieser
  Plan dort enthalten ist; sonst vom Branch mit diesem Plan. Lokal committen.
  Kein Push und kein Merge ohne Nutzer.

## Aufgabenstapel

| ID | Aufgabe | Abhängig von | Fertig, wenn |
|---|---|---|---|
| N1-1 | Bisher verwendete Szenenseeds aus allen Sampleplänen sammeln; neuen, überschneidungsfreien Seedbereich festlegen | – | `used_scene_seeds.json` und begründeter neuer Bereich |
| N1-2 | Szenenfamilien und Splits festlegen: Kalibrierung, Critic-Daten, Validierung (normal und schwierig), Test (normal und schwierig), Zweier-Panel | N1-1 | `splits.json` mit Zweck, Fallzahl und Begründung je Split |
| N1-3 | Deterministisches Skript für Schwierigkeitsmerkmale aus dem Anfangszustand (Transportstrecke, Abstand zum Turm, Platzverhältnisse, Lage im Arbeitsraum; Einheiten) | – | `difficulty.py` mit Tests und Version `difficulty_v1` |
| N1-4 | Kalibrierungsrollouts: drei A-Parents, unverändert, nur auf Kalibrierungsfamilien; Durchsatz messen | N1-2, N1-3 | Rohergebnisse mit vollständigem Nenner, Episoden/Stunde |
| N1-5 | Grenzen leicht/mittel/schwer aus Kalibrierung festlegen und einfrieren; Validierungs- und Testfamilien zuordnen, **ohne sie auszurollen** | N1-4 | `CALIBRATION.md`, gehashte `difficulty_v1.json` |
| N1-6 | `PROTOCOL.md` entwerfen: Arme, Budgets aus Durchsatz, Critic-Akzeptanzkriterien, Constraint-Kandidaten, Checkpointregel, Analyse, Ausschlussregeln | N1-2…N1-5 | Entwurf mit Status `ZUR FREIGABE` |
| N2-1 | Critic-Daten: A-Parents auf Critic-Datenfamilien ausrollen, alle Ausgänge behalten, Übergänge nach Datenvertrag speichern | N1-6 | Datensatz, Manifest, Hash, Erfolgs-/Fehlerzahlen |
| N2-2 | Critic vortrainieren (Freigabe); auf Validierungsfamilien gegen gemessene Returns prüfen | N2-1 | `CRITIC_VALIDATION.md`: Kriterien aus N1-6 erfüllt oder nicht |
| N2-3 | Technischer Smoke des Actor-Critic-Loops mit AWAC-artiger Bindung an BC, beide Critic-Varianten, wenige Updates (Freigabe) | N2-2 | Smoke-Bericht mit Drift- und Erfolgsverlauf, ausdrücklich ohne Wirksamkeitsaussage |
| N2-4 | Pilotlauf vorbereiten: Supervisor, Monitor, eingefrorene Quellen per SHA, Fortsetzbarkeit getestet | N2-3 | `night.py prepare` erfolgreich, Start nur über `launch` |
| N3-1 | Drei-Seed-Pilot (Freigabe): BC, AC mit neuem Critic, AC mit IL-informiertem Critic; je A-Parent gepaart; gleiche Online-Budgets und Interaktionsszenen | N2-4 | Lauf beendet oder sauber angehalten, alle Seeds erfasst |
| N3-2 | Checkpoints nach fester Regel nur auf Validierung auswerten: normal, schwierig, Zweier-Panel getrennt | N3-1 | Rohpaare je Parent und Szene |
| N4-1 | Pilotbericht: Effekt je Parent, Streuung, Interaktionen bis zur vorab festgelegten Erfolgsschwelle, Kosten des Critic-Vortrainings getrennt | N3-2 | `PILOT_REPORT.md` |
| N4-2 | Seedzahl des Hauptvergleichs aus kleinstem relevanten Effekt, Pilotstreuung und Budget begründen (> 3, AGENTS.md §1) | N4-1 | Abschnitt im Pilotbericht |
| N4-3 | Protokoll des Hauptvergleichs entwerfen: gewählte Bindung, Seedzahl, neue BC-Parents, Testauswertung einmalig | N4-2 | `MAIN_PROTOCOL.md`, Status `ZUR FREIGABE` |
| N4-4 | Optional (Freigabe): neue unabhängige Zweier-BC-Parents mit unveränderter A-Rezeptur trainieren | N4-3 | Modelle im Katalog über `registry.py` |

Die Zuordnung zu Nächten ist ein Richtwert. Geht eine Nacht schneller,
die nächsten freigegebenen Aufgaben beginnen. Wird sie nicht fertig,
übernimmt die nächste Nacht die offenen Aufgaben.

## Aufgabenstapel Nacht 2 (19./20.11.2026, protocol_v2, Plan B)

| ID | Aufgabe | Abhängig von | Fertig, wenn |
|---|---|---|---|
| D1a | Aktionssensitivität des N2-2-Critics und der Zufallsinitialisierung messen, nur Vorwärtsdurchläufe (v2 §A) | – | Tabelle im Bericht `ACTION_SENSITIVITY.md`, berichtend |
| N2-1b | Critic-Daten mit Explorationsrauschen: A-Parents auf `critic_data_noisy` (300 Familien ab 2100003690), σ = 0,05 in Grenze δ_max = 0,20 (v2 §E) | – | `splits_v3.json`, Datensatz, Manifest, Hash, Erfolgs-/Fehlerzahlen, `CRITIC_DATA_NOISY.md` |
| N2-2b | Critic IL-v2 je Parent auf N2-1 + N2-1b vortrainieren, nach §6 auf gespeicherten N2-2-Validierungsrollouts prüfen | N2-1b | `CRITIC_VALIDATION_V2.md`: bestanden oder nicht |
| D1b | Aktionssensitivität von IL-v2, entscheidend (v2 §A) | N2-2b | Entscheidung in `ACTION_SENSITIVITY.md` |
| N2-3v2 | Smoke v2 mit IL-v2, standardisierten Vorteilen τ = 1 und Divergenzprüfung, Stufen 0,05 → 0,10 → 0,20 (v2 §B–§D) | D1b bestanden | `AC_SMOKE_V2.md` mit gewählter Stufe oder Gesamtpause |
| B-1 | Pilotauswertung vorab einfrieren: Analyseskript nach v1 §10 mit Tests auf synthetischen Daten, SHA im Protokoll | – | `pilot_analysis.py`, Tests grün, Hash dokumentiert, **ohne Pilotdaten** |
| B-2 | Fehlerphasen der A-Parents aus N1-4- und N2-1-Daten: Endphase, Stufe und Abstand der nötigen Korrektur zur Bindung δ_max | – | `FAILURE_PHASES.md` mit vollständigen Nennern, nur bereits erhobene Daten |
| B-3 | Werkzeug für N4-2: Seedzahl aus kleinstem relevantem Effekt, Streuung und Budget, mit Tests auf Beispielwerten | – | `seed_count.py` mit Tests, keine Pilotdaten |
| B-4 | Abbildungen und Dokumentation: Critic-Vergleich N2-2 gegen IL-v2, Smoke v1 gegen v2 (Loss, Stabilität und Erfolg getrennt), `experiments/critic/README.md`, Dashboard, Nachtbericht | jeweilige Ergebnisse | Abbildungen mit Generator, Nachtbericht `nights/NACHT_2_20261119.md` |

Reihenfolge: N2-1b als erster langer Lauf, D1a, B-1, B-2 und B-3 währenddessen. Danach N2-2b, D1b und N2-3v2. B-4 zum Schluss. Für Nacht 3 vorgemerkt: N2-4, N3-1 mit IL-v2, N3-2.

## Hinweise zu den einzelnen Nächten

**Nacht 1, Protokoll (Meilenstein M1).** Kein Training. Schwierigkeitsgrenzen
nur aus Kalibrierungsfamilien ableiten. Validierungs- und Testfamilien werden
nur über Anfangszustände eingeordnet. Größenvorschlag zum Begründen:
Kalibrierung etwa 3 × 100 Episoden. Validierung etwa 100 normale und
50 schwierige Familien. Test etwa 150 normale und 75 schwierige Familien.
Zweier-Panel etwa 100 Familien. Endgültige Zahlen aus dem gemessenen
Durchsatz. Die Critic-Akzeptanz vorab festlegen, bevor Daten vorliegen.
Mindestens: Vorhersage des Erfolgs aus Zuständen an festen Phasenpunkten
(AUC, Kalibrierungsfehler) gegen eine reine Phasen-Baseline
(Erfolgsquote je erreichter Phase). Der Critic muss mehr leisten als die
Phase zu kodieren.

**Nacht 2, Critic.** Das Critic-Vortraining ist Teil der Methode, kein Pilot.
Fällt die Critic-Validierung durch, kein Pilot. Dann Befund dokumentieren
und Ursachen getrennt nennen (Daten, Merkmale, Ziel). Abbruchkriterium für
den Smoke und später den Pilot vorab in `PROTOCOL.md` festlegen, etwa
Aktionsabweichung zur BC-Policy oder Validierungserfolg unter einer Schwelle
bei Zwischenprüfungen. Die Constraint-Stärke höchstens aus technischen
Stabilitätskriterien eingrenzen, nicht aus Erfolgsvergleichen der Arme.

**Nacht 3, Pilot (Meilenstein M2).** Erster wissenschaftlicher Lauf dieses
Vorhabens, daher genau drei Seeds je Arm (die drei A-Parents). Kein
Nachschieben weiterer Seeds. Test bleibt geschlossen. Passt das Budget nicht
in eine Nacht, nach Protokoll anhalten und in Nacht 4 exakt fortsetzen.

**Nacht 4, Auswertung und Hauptplanung.** Erst jetzt wird über die
Seedzahl des Hauptvergleichs entschieden. Neue BC-Parents sind nötig, weil
jeder unabhängige Trainingslauf eine eigene BC-Policy braucht. Die drei
A-Parents allein genügen nicht.

## Dokumentation

Pro Nacht eine Datei `nights/NACHT_<n>_<JJJJMMTT>.md`, höchstens etwa
eine Seite:

```markdown
# Nacht <n> · <Datum> · Status: COMPLETE | PARTIAL | BLOCKED | FAILED
## Erledigte Aufgaben     (IDs, je ein Satz)
## Ergebnisse             (vollständige Nenner, z. B. 41/150; geteilte Szenen benennen)
## Abweichungen vom Plan  (was, warum, Auswirkung; „keine“ ist eine gültige Angabe)
## Integrität             (Tests, SHA-Prüfungen, Optimizerupdates gezählt, Exitcodes)
## Offene Probleme        (mit Ursache, falls bekannt)
## Übergabe               (nächste Aufgabe, Fortsetzungspunkt, nötige Nutzerentscheidung)
```

Außerdem jeweils:

- `STATUS.md` aktualisieren: Tabelle mit ID, Status (offen / läuft /
  erledigt / blockiert), Datum, Verweis. Das ist die einzige Quelle für den
  Fortschritt.
- Große Daten nur unter `praxis/results/…`, nie im Git. Kleine Manifeste,
  Hashes und Berichte hier.
- Smoke-Ergebnisse ausdrücklich als technisch kennzeichnen. Validierungs-
  und Testergebnisse nie zusammenfassen.
- `experiments/critic/README.md` um einen Statussatz ergänzen.
- Fachlich geschlossene Commits auf dem Branch.

## Danach

1. Nutzer gibt `MAIN_PROTOCOL.md` frei, und neue BC-Parents sind trainiert.
2. Hauptvergleich mit begründeter Seedzahl, voraussichtlich über mehrere Nächte.
3. Modelle und Checkpointregel einfrieren (M3), danach Test einmalig öffnen (M4).
4. Nachrangig: exakter Würfelzustand durch Positionen der Vision-Pipeline
   ersetzen, danach Machbarkeitstest auf dem realen Roboter.
