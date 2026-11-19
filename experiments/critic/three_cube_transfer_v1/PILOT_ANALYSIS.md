# Pilotauswertung vorab eingefroren (B-1)

**Stand 19.11.2026, 22:55 Uhr · Version `pilot_analysis_v1` · ohne Pilotdaten erstellt**

Dieses Dokument friert die Auswertung des Drei-Seed-Pilots N3-1 nach [PROTOCOL.md §10](PROTOCOL.md#10-analyse-pilot-n4-1) ein, bevor Pilotdaten existieren. [PROTOCOL_V2.md](PROTOCOL_V2.md) lässt §10 unverändert. Das Skript [pilot_analysis.py](pilot_analysis.py) wird in N4-1 unverändert auf die Ergebnisdatei aus N3-1/N3-2 angewendet. Eine Änderung des Skripts nach Sicht auf Pilotdaten braucht eine neue, begründete Version und die Freigabe des Nutzers.

## Hash

| Datei | SHA-256 |
|---|---|
| [pilot_analysis.py](pilot_analysis.py) | `ad7d627422e99c2f19eb36c7214e3c1dd7b5fe0ccd1dd0d7bbbc6d15be0f18a2` |
| [test_pilot_analysis.py](test_pilot_analysis.py) | `a840761e263a05eb66b5a349bc3e80ad33b910ac2915d6fb07d20bab44e47246` |

Die Hashes stehen auch in [pilot_analysis.sha256](pilot_analysis.sha256). Unter `experiments/**` gilt `-text` (`.gitattributes`), die Bytes bleiben beim Auschecken also erhalten. Prüfung: `praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/pilot_analysis.py hash`. Jede Auswertung schreibt `script_sha256` und `input_sha256` in ihr Ergebnis.

## Aufruf (erst in N4-1)

```
praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/pilot_analysis.py analyze \
  --input <pilot_outcomes.json> --output <analysis.json> --markdown <analysis.md>
```

Das Skript lädt keine Modelle und startet keine Simulation. Panels liest es aus [splits_v3.json](splits_v3.json) und [difficulty_panels_v1.json](difficulty_panels_v1.json).

## Eingabevertrag `three_cube_transfer_v1.pilot_outcomes.v1`

N3-1/N3-2 schreiben eine JSON-Datei mit diesen Feldern:

- `schema`: `three_cube_transfer_v1.pilot_outcomes.v1`
- `evaluations`: je ausgewerteter Episode `{arm, parent, panel, round, scene_seed, success}`. `arm` ist einer von `BC`, `AC-neu`, `AC-IL`. `parent` ist 1, 2 oder 3. `panel` ist `validation_normal`, `validation_hard` oder `two_cube_validation`. `round` ist eine ganze Zahl, `success` ein Boolean.
  - BC: Runde 0 auf allen drei Panels. Die regulären und schwierigen Werte stammen aus N2-2, das Zweierpanel aus N3-2.
  - AC: `validation_normal` in den Runden 1–4, `validation_hard` und `two_cube_validation` in Runde 4 (§5, §8).
- `runs`: je AC-Lauf `{arm, parent, status, last_evaluated_round, rounds, pretrain_episodes, pretrain_frames, pretrain_updates, eval_episodes, runtime_s}`. `status` ist `complete` (dann `last_evaluated_round = 4`) oder `aborted`. Je abgeschlossener Runde enthält `rounds` die Felder `{round, online_episodes, online_frames, critic_updates, actor_updates}`.

**Vertragsprüfung vor jeder Rechnung.** Liegt ein Szenenseed in `test_normal` (2100001500–2100001649) oder `test_hard` (2100001650–2100003149), oder heißt ein Panel `test_*`, bricht das Skript mit `TestFamilyError` ab. Diese Prüfung läuft vor allen anderen. Abgewiesen werden außerdem fehlende, doppelte oder fremde Familien in einer Zelle, fehlende Läufe oder Endprüfungen, nicht vorgesehene Runden und falsche Typen. Es gibt keinen stillen Ausschluss (§9).

## Festlegungen

| Punkt | Festlegung | Quelle |
|---|---|---|
| Panels | `validation_normal` k/100, `validation_hard` k/50, `two_cube_validation` k/100, getrennt berichtet | §10 |
| Checkpoint | Runde 4. Ein abgebrochener Lauf geht mit seinem letzten ausgewerteten Prüfpunkt je Panel ein und wird gekennzeichnet (`aborted`, `checkpoint_round`). Gibt es auf einem Panel keine AC-Auswertung, gilt Runde 0 = BC desselben Parents (`round0_is_bc`). | §8, §9 |
| Primärer Kontrast | AC-IL − AC-neu je Parent auf `validation_normal`, Mittel über die drei Parents, Minimum, Maximum, Spannweite | §10 |
| Sekundäre Kontraste | AC-neu − BC und AC-IL − BC regulär und schwierig, AC-IL − AC-neu schwierig, Zweiererhalt AC-neu − BC und AC-IL − BC | §10 |
| Paarung | je Parent und Kontrast die diskordanten Familien (nur a, nur b), dazu beide und keiner | §10 |
| Intervall | 95-%-Perzentilintervall, Familienbootstrap mit 2.000 Ziehungen und Seed 7300 (`numpy.random.default_rng(7300).integers`). Die Ziehung wird je Panel einmal gebildet und von allen Armen, Parents und Kontrasten geteilt. Das Parentmittel wird gemeinsam über dieselben Familien gezogen, weil die Parents die Familien teilen. Die Bezeichnung lautet ausdrücklich „reine Szenenunsicherheit“. | §10, Zahl der Ziehungen aus §6 |
| Effizienz | Schwelle = Parentquote + 10 Prozentpunkte auf `validation_normal`. Gemeldet wird die erste Prüfrunde, deren Quote die Schwelle **erreicht** (≥), mit Onlineepisoden und Frames bis zum Ende dieser Runde. Wird die Schwelle nicht erreicht, steht dort „> 400“, bei Abbruch „> E (abgebrochen)“. AC-IL wird zusätzlich mit 300 Vortrainingsepisoden und deren Frames berichtet. Der Vergleich ist ganzzahlig, ohne Rundungsfehler. | §10 |
| Zusammenbruchsmarken | Runden 1–3 mit einer Quote von höchstens der halben Parentquote, nur berichtend. Über den Abbruch entscheidet N3-1 während des Laufs. | §8 |
| Kosten | Onlineepisoden, Frames, Critic- und Actorupdates, Vortrainingsepisoden, -frames und -updates, Auswertungsepisoden und Laufzeit je Lauf getrennt | §10 |
| Bewertung | keine Signifikanztests, keine p-Werte. Der kleinste relevante Effekt von 10 Prozentpunkten wird nur als Bezug für N4-2 ausgegeben. | §10, AGENTS.md §1 |

**Auslegung, vor Datensicht festgelegt:** §10 sagt „erste Prüfrunde über dieser Schwelle“ und „wird die Schwelle nicht erreicht“. Das Skript wertet „erreicht“ als ≥. Ein Wechsel auf > wäre vor Öffnung der Pilotdaten eine neue Skriptversion.

## Nachweis

- 27/27 Tests grün auf synthetischen Daten: `praxis/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider experiments/critic/three_cube_transfer_v1/test_pilot_analysis.py` (19.11.2026, 22:51 Uhr, 0,35 s).
- Abgedeckt sind die Panelgrößen aus den eingefrorenen Dateien und die Trennung von den Testbereichen, k/n, der primäre Kontrast mit Mittel und Spannweite, diskordante Paare, die Nachrechnung des Bootstraps einschließlich der gemeinsamen Ziehung für das Parentmittel, die Reproduzierbarkeit, die Abweisung von Testfamilien (vier Bereichsgrenzen und Panelname) und sieben Vertragsverletzungen. Dazu kommen abgebrochene Läufe, die Effizienzschwelle (erreicht, genau erreicht, nicht erreicht, unerreichbar), die Zusammenbruchsmarken, Runde 0 = BC, getrennte Kosten und die Kommandozeile mit Hash.
- Keine Pilotdaten gelesen oder erzeugt. 0 Rollouts, 0 Optimizerupdates, Testfamilien geschlossen.
