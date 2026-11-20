# Pilotauswertung der Selbstimitation vorab eingefroren (S-0)

**Stand 20.11.2026, 11:45 Uhr · Version `si_pilot_analysis_v1` · ohne Pilotdaten erstellt**

Dieses Dokument friert die Auswertung des Selbstimitationspilots nach [PROTOCOL_V3.md §7](PROTOCOL_V3.md#7-analyse-s-6) ein, bevor Pool-, Trainings- oder Validierungsdaten der Arme SI-E und SI-K existieren. Das Skript [si_pilot_analysis.py](si_pilot_analysis.py) wird in S-6 unverändert auf die Ergebnisdatei aus S-5 angewendet. Eine Änderung nach Sicht auf Pilotdaten braucht eine neue, begründete Version und die Freigabe des Nutzers.

**Übertragen statt unverändert genutzt.** [pilot_analysis.py](pilot_analysis.py) (B-1) kennt nur die Arme BC, AC-neu und AC-IL mit Prüfrunden 1–4. v3 hat andere Arme und einen festen Checkpoint ohne Runden. Deshalb gibt es ein neues Skript. Es importiert die eingefrorenen B-1-Bausteine (Panels, Testfamilienabweisung, Familienbootstrap, Perzentilintervall, diskordante Paare) und prüft vor jeder Rechnung, dass `pilot_analysis.py` noch den SHA-256 `ad7d6274…18a2` hat. B-1 selbst bleibt unverändert.

## Hash

| Datei | SHA-256 |
|---|---|
| [si_pilot_analysis.py](si_pilot_analysis.py) | `4ee3385b7d0be74fe5190f1c42fe7541d3c1021c751efb739a82f6282dce5855` |
| [test_si_pilot_analysis.py](test_si_pilot_analysis.py) | `f3ff3ccacf6c893f2f33cface18d92cae4de5b90bcd40d266862d2a1774e65bf` |
| [pilot_analysis.py](pilot_analysis.py) (B-1, übernommen) | `ad7d627422e99c2f19eb36c7214e3c1dd7b5fe0ccd1dd0d7bbbc6d15be0f18a2` |

Die Hashes der neuen Dateien stehen auch in [si_pilot_analysis.sha256](si_pilot_analysis.sha256). Prüfung: `praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/si_pilot_analysis.py hash`. Jede Auswertung schreibt `script_sha256`, `input_sha256` und den geprüften B-1-Hash (`inherited_from`) in ihr Ergebnis.

## Aufruf (erst in S-6)

```
praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/si_pilot_analysis.py analyze \
  --input <si_pilot_outcomes.json> --output <analysis.json> --markdown <analysis.md>
```

Das Skript lädt keine Modelle und startet keine Simulation. Panels liest es aus [splits_v3.json](splits_v3.json) und [difficulty_panels_v1.json](difficulty_panels_v1.json).

## Eingabevertrag `three_cube_transfer_v1.si_pilot_outcomes.v1`

S-5 schreibt eine JSON-Datei mit diesen Feldern:

- `schema`: `three_cube_transfer_v1.si_pilot_outcomes.v1`
- `evaluations`: je ausgewerteter Episode `{arm, parent, panel, scene_seed, success}`. `arm` ist `BC`, `SI-E` oder `SI-K`, `parent` 1, 2 oder 3, `panel` `validation_normal` (100), `validation_hard` (50) oder `two_cube_validation` (100). Alle neun Modelle brauchen alle drei Panels vollständig. BC auf der Validierung stammt aus N2-2, das BC-Zweierpanel aus S-5. Ein Feld `round` ist unzulässig.
- `runs`: je SI-Lauf `{arm, parent, status, updates, minibatch_seed, demo_fraction, checkpoint_sha256, selection_sha256, demo_frames, self_success_episodes, self_success_frames, prefix_episodes, prefix_families, prefix_frames, eval_episodes, update_runtime_s, eval_runtime_s}`. Die beiden Laufzeiten dürfen `null` sein.
- `bc_determinism`: je Parent genau 10 Einträge `{parent, panel, scene_seed, n2_2_success, rerun_success}` aus `validation_normal` oder `validation_hard`.
- `pool`: `{episodes, frames, runtime_s}` des Datenpools S-1.

**Vertragsprüfung vor jeder Rechnung.** Zuerst werden Testfamilien abgewiesen (`TestFamilyError`), in `evaluations` und in `bc_determinism`: Szenenseeds in `test_normal` (2100001500–2100001649) oder `test_hard` (2100001650–2100003149) und Panels `test_*`. Danach wird abgewiesen (`ContractError`):

- fehlende, doppelte oder fremde Familien in einer Zelle sowie eine fehlende Zelle,
- ein Lauf mit Status ungleich `complete`. v3 hat keinen Zwischencheckpoint, ein abgebrochener Lauf hat also keinen Auswertungsstand. Über ihn entscheidet der Nutzer (v3 §5), kein stiller Ausschluss,
- Updates ungleich 5.000, Minibatch-Seed ungleich `7700 + p`, Zweieranteil ungleich 0,5,
- Präfixe im Arm SI-E sowie unterschiedliche Erfolgsepisoden, Erfolgsframes oder Auswahlhash zwischen SI-E und SI-K desselben Parents (v3 §2: beide Arme nutzen denselben Pool und dieselben Erfolge),
- derselbe Checkpoint-Hash für SI-E und SI-K, ein Pool ungleich 1.200 Episoden,
- eine Determinismusprüfung mit anderer Familienzahl als 10 je Parent, mit Familien außerhalb der Validierung oder mit einem N2-2-Wert, der dem BC-Wert in `evaluations` widerspricht.

## Festlegungen

| Punkt | Festlegung | Quelle |
|---|---|---|
| Panels | `validation_normal` k/100, `validation_hard` k/50, `two_cube_validation` k/100, getrennt berichtet | v3 §5, §7 |
| Checkpoint | fest nach 5.000 Updates, keine Auswahl, keine Runden | v3 §2 |
| Primärer Kontrast (SI-005a) | SI-K − SI-E je Parent auf `validation_normal` als gepaarte Differenz über dieselben 100 Familien, Mittel über die drei Parents als Schätzung bei drei Seeds, Minimum, Maximum, Spannweite | v3 §7 |
| Sekundäre Kontraste | SI-E − BC (SI-005b) und SI-K − BC auf `validation_normal`. Getrennt auf `validation_hard`: SI-K − SI-E, SI-E − BC, SI-K − BC | v3 §1, §7 |
| Zweiererhalt | SI-E − BC und SI-K − BC auf `two_cube_validation`. Nebenbedingung „Abfall um **mehr als** 10 Prozentpunkte unter den BC-Parent“ ganzzahlig geprüft (`100·(k_BC − k_Arm) > 10·n`), nur berichtend | v3 §1 |
| Paarung | je Parent und Kontrast diskordante Familien (nur a, nur b), dazu beide und keiner | wie B-1 |
| Intervall | 95-%-Perzentilintervall, Familienbootstrap mit 2.000 Ziehungen und Seed 7300, eine Ziehung je Panel für alle Arme, Parents und Kontraste. Das Parentmittel wird über dieselben Familien gezogen, weil die Parents die Familien teilen. Bezeichnung „reine Szenenunsicherheit“ | v3 §7, wie B-1 |
| Datenmengen | je Arm und Parent Zweierframes, Erfolgsepisoden und -frames, Präfixepisoden, -familien und -frames, Selbstframes gesamt. Das Gate aus v3 §4 (≥ 1,10-fache Selbstframes, ≥ 10 Präfixfamilien) wird ganzzahlig nachgerechnet und nur berichtet. Entschieden hat es S-2 | v3 §4, §7 |
| Kosten | Pool (Episoden, Frames, Laufzeit), je Lauf Updates, Update- und Auswertungszeit, Summe der Updates | v3 §7 |
| BC-Determinismus | Übereinstimmungen k/10 je Parent und abweichende Familien. Nur berichtend. Bei einer Abweichung kennzeichnet das Ergebnis `all_match: false`, die Bewertung trifft der Nutzer | v3 §5 |
| Seedzahl | `seed_count_inputs`: Primärkontraste je Parent, mittlere Diskordanzrate, 100 Familien, δ = 0,05 (+5 Prozentpunkte) und der Aufruf von [seed_count.py](seed_count.py) (B-3, unverändert) über `--pilot-differences`. Kosten je Seed und Budget legt der Hauptvergleich fest. Die Ausgabe von `seed_count_v1` trägt fest die Beschriftung „AC-IL − AC-neu“. Maßgeblich ist der hier übergebene Kontrast | v3 §7 |
| Bewertung | keine Signifikanztests, keine p-Werte | AGENTS.md §1 |

**Auslegungen, vor Datensicht festgelegt:** „SI-E − BC, getrennt auf `validation_hard`“ aus v3 §7 wird als „alle drei Kontraste zusätzlich auf `validation_hard`, getrennt berichtet“ gelesen. SI-K − BC ist nicht ausdrücklich verlangt und wird nur berichtend mitgeführt. „Um mehr als 10 Prozentpunkte“ heißt strikt größer, ein Abfall von genau 10 Punkten verletzt die Nebenbedingung nicht.

## Nachweis

- 47/47 Tests grün auf synthetischen Daten: `praxis/.venv/Scripts/python.exe -m pytest -q -p no:cacheprovider experiments/critic/three_cube_transfer_v1/test_si_pilot_analysis.py` (20.11.2026, 11:40 Uhr, 0,59 s). Zusammen mit den unveränderten 27 B-1-Tests 74/74.
- Abgedeckt sind der eingefrorene B-1-Hash und die Abweisung einer veränderten Kopie, die Panelgrößen, k/n, der primäre Kontrast mit Mittel und Spannweite, diskordante Paare, die Nachrechnung des Bootstraps einschließlich gemeinsamer Ziehung für das Parentmittel, die Reproduzierbarkeit und die Nebenbedingung an der Grenze (genau 10 gegen 11 Punkte). Dazu kommen die Datenmengen mit Gate-Nachrechnung an der Grenze 1,10, die Kosten, die berichtende Determinismusprüfung, die Übergabe an `seed_count.plan` mit δ = 0,05, die Abweisung von Testfamilien (vier Bereichsgrenzen, Panelname, Determinismusfamilie) vor der Schemaprüfung, 26 Vertragsverletzungen, eine fehlende Zelle und die Kommandozeile mit Hashes.
- Keine Pilotdaten gelesen oder erzeugt. Der laufende Pool S-1 wurde nicht gelesen. 0 Rollouts, 0 Optimizerupdates, Testfamilien geschlossen.
- [PROTOCOL_V3.md](PROTOCOL_V3.md) wurde nicht verändert. Der Hash steht hier, in [si_pilot_analysis.sha256](si_pilot_analysis.sha256) und in [STATUS.md](STATUS.md), wie bei B-1. Ein Querverweis im freigegebenen Protokoll bleibt der Planungssitzung vorbehalten.
