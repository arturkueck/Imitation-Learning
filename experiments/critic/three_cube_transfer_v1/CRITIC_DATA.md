# N2-1 · Critic-Daten: Datenvertrag und Lauf

Umsetzung von [PROTOCOL.md §4](PROTOCOL.md#4-aufgabe-reward-und-datenvertrag) und §12 für die Datenerhebung mit den drei eingefrorenen A-Parents. Code: [critic_data.py](critic_data.py), Tests: [test_critic_data.py](test_critic_data.py). Laufdaten liegen unter `praxis/results/critic/three_cube_transfer_v1/critic_data_n2_1/` und nicht im Git.

## Umfang

- Szenen ausschließlich aus dem Split `critic_data` (2100000100–2100000399, 300 Familien). Das Skript prüft den Bereich gegen `splits.json` und `splits_v2.json`. Validierungs- und Testfamilien werden nicht berührt.
- Reihenfolge: Szene aufsteigend, je Szene Parent 1, 2, 3. Das ergibt 900 Episoden mit 0 Optimizerupdates und ohne Explorationsrauschen. Die ausgeführte Aktion ist die Parentaktion.
- Episodenablauf, Controller, Uhrkorrektur und Erfolgsdefinition entsprechen `calibration.py` (N1-4). Erfolg heißt 50 aufeinanderfolgende gültige Dreierframes, der Horizont liegt bei 1.000 Frames und der Rückzugs-Timeout bei 200 Aktionen.

## Gespeicherte Übergänge je Episode (`episodes/NNNN.npz`)

| Array | Form | Bedeutung |
|---|---|---|
| `frame` | (T) | Framenummer 0…T−1 |
| `stage`, `phase`, `retreat` | (T) | Platzierungsstufe (1/2), Policy-Phase (0–6), Rückzugsmodus des Sequencers |
| `phase_steps`, `retreat_actions` | (T) | rohe Phasenuhr der Policy, Zähler der Rückzugsaktionen |
| `critic_state` | (T, 40) | Critic-Eingabe vor der Aktion, Spalten siehe unten |
| `actor_input`, `actor_phase` | (T, 10), (T) | unveränderte Actor-Beobachtung des A-Parents (mit Uhrkorrektur) und Phaseneingabe |
| `executed_action`, `parent_action` | (T, 7) | `x, y, z, rot_x, rot_y, rot_z, gripper`; in N2-1 identisch |
| `next_critic_state` | (T, 40) | Folgezustand nach Aktion und Sequencer-Fortschritt |
| `reward` | (T) | 1 nur im letzten Frame einer erfolgreichen Episode |
| `terminal` | (T) | wahr nur im letzten Frame; alle Enden sind echte Aufgabenenden |
| `discounted_return` | (T) | beobachteter Return mit γ = 0,995, also γ^(T−1−t) bei Erfolg, sonst 0 |

**Spalten von `critic_state`** (Positionen relativ zur Tischmitte in m): 0–8 Würfelpositionen A/B/C (x, y, z), 9–20 Würfelquaternionen A/B/C (w, x, y, z), 21–23 Greiferposition, 24–27 Greiferquaternion (x, y, z, w), 28–29 Fingerstellung, 30 Stufe 2, 31–37 Phase one-hot, 38 Rückzugsmodus, 39 Restzeit (1.000 − t)/1.000. Die vollständige Liste steht in `config.json` unter `critic_columns`. Zukünftige Ereignisse sind keine Merkmale. Die Normierung bestimmt erst N2-2 aus diesen Frames.

Je Episode hält `episodes/NNNN.json` Szene, Parent, Startzustands- und Trajektorienhash, Ausgang, Endgrund (`success`, `retreat_timeout`, `horizon`, `simulator_instability`), erreichte Kombinationen aus Stufe, Phase und Rückzug, MuJoCo-Warnzähler und den SHA-256 der `.npz` fest. Eindeutige Simulatorinstabilität, also nicht endliche Zustände oder Beobachtungen, beendet die Episode als Fehlschlag. Andere Ausnahmen halten den Lauf an (§12).

## Prüfungen

- Synthetische Vertragstests prüfen Formen, Folgezustand, Reward und Return, Instabilität, Split und Dashboardeintrag.
- Einzelne technische Integrationsprüfung (§12): Kalibrierungsepisode 000 mit Szene 2100000000 und Parent 1 lieferte mit dem Erhebungscode denselben Startzustands- und Trajektorienhash, Ausgang, Endgrund und dieselbe Framezahl wie N1-4. Ergebnis in `critic_data_n2_1_integration/result.json`. Diese Episode zählt nicht zu den 900.
- Bei Abschluss gleicht der Monitor einmalig alle 900 Rohepisoden mit `summary.json` ab: Hash jeder Episode, Datenvertrag, Paarung, Zählungen und `dataset_sha256`.

## Bedienung (aus dem Repository-Stamm)

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_data.py monitor
# Fortsetzung nur nach PAUSED, beendeten Prozessen und ohne STOP-Datei:
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_data.py start resume --cutoff <ISO+01:00> --deadline <ISO+01:00>
```

Ein Halt erfolgt über die Datei `STOP` im Laufordner. Der Worker setzt dann `PAUSED` an einer Episodengrenze. Die nächste Episode ist der Index der ersten fehlenden `NNNN.json`. Jede Episode setzt ihre Seeds selbst, sodass Fortsetzungen exakt reproduzieren. `config.json` bindet die Quellen per SHA-256. Eine Fortsetzung mit geänderten Quellen bricht ab.
