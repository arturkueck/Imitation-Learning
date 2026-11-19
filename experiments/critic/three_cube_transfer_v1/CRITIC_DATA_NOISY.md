# N2-1b · Critic-Daten mit Explorationsrauschen: Datenvertrag und Lauf

Umsetzung von [PROTOCOL_V2.md §E](PROTOCOL_V2.md#e-neu-critic-il-v2-mit-aktionsvariation-n2-1b-n2-2b), freigegeben am 19.11.2026 um 22:12 Uhr (Plan B, Häkchen N2-1b/N2-2b im [NACHTPLAN](NACHTPLAN.md#freigaben)). Code: [critic_data_noisy.py](critic_data_noisy.py), Tests: [test_critic_data_noisy.py](test_critic_data_noisy.py). Laufdaten liegen unter `praxis/results/critic/three_cube_transfer_v1/critic_data_noisy_n2_1b/` und nicht im Git. 0 Optimizerupdates.

## Umfang

- Szenen ausschließlich aus dem neuen Split `critic_data_noisy` (2100003690–2100003989, 300 Familien), versioniert in [splits_v3.json](splits_v3.json). Gegenüber `splits_v2.json` (SHA-256 `527fc3d9…52942`) kommt nur dieser Split hinzu. Der unvergebene Rest beginnt bei 2100003990. Das Skript prüft Bereich und Überschneidungsfreiheit. Validierungs- und Testfamilien werden nicht berührt.
- Reihenfolge: Szene aufsteigend, je Szene Parent 1, 2, 3. Das ergibt 900 Episoden. Alle Ausgänge werden behalten.
- Policy: die drei unveränderten A-Parents. Episodenablauf, Controller, Abschlusslogit, Sequencer, Rückzug, Uhrkorrektur und Erfolgsdefinition sind identisch mit N2-1, denn der Lauf ruft `critic_data.episode` auf. Nur das Modell ist durch einen Ausführer ersetzt, der die Parentaktion verrauscht.

## Rauschen und Grenze

- Auf XYZ wird ε ~ N(0; 0,05²) addiert, der Greifer bleibt ohne Rauschen.
- Die Projektion entspricht der Regel aus PROTOCOL.md §7 (`ac_smoke.make_bound`, dieselbe Funktion wie im Smoke) mit der weitesten Stufe δ_max = 0,20: `a = clip(a_p + b·tanh(ε/b), −1, 1)` mit `b_xyz = min(0,20; 0,5·|a_p,xyz|)` und `b_Greifer = 0,02`.
- Zufallsstrom: Wurzel 7600 + p nach §E, je Episode `numpy.random.default_rng([7600 + p, Szenenseed])`. Damit reproduziert jede Fortsetzung an der Episodengrenze exakt. Eine durchgehende Folge je Parent hätte bei einer Fortsetzung den Generatorzustand voraussetzen müssen. Das ist eine Umsetzungsentscheidung innerhalb von §E, keine Protokolländerung.

## Gespeicherte Übergänge je Episode (`episodes/NNNN.npz`)

Alle Arrays aus [CRITIC_DATA.md](CRITIC_DATA.md#gespeicherte-übergänge-je-episode-episodesnnnnnpz) mit denselben Formen, zusätzlich:

| Array | Form | Bedeutung |
|---|---|---|
| `parent_action` | (T, 7) | Ausgabe des unveränderten Parents (in N2-1 identisch mit der ausgeführten Aktion) |
| `executed_action` | (T, 7) | verrauschte, begrenzte Aktion, die tatsächlich ausgeführt wurde |
| `exploration_noise` | (T, 3) | gezogenes ε auf XYZ vor der Projektion |
| `action_bound` | (T, 4) | Grenze b für x, y, z, Greifer |

`discounted_return` ist der beobachtete Return der **verrauschten** Verhaltenspolicy (bekannte Grenze nach §E). Je Episode hält `episodes/NNNN.json` zusätzlich `max_deviation_xyz`, `mean_deviation_xyz` und `bound_violations` fest.

## Prüfungen

- Die Vertragsprüfung jeder Episode umfasst den vollständigen N2-1-Vertrag ohne die Gleichheitsbedingung, die Grenze aus der Parentaktion, 0 Grenzverletzungen, unveränderte Rotations- und Greiferspalten und die Rekonstruktion der ausgeführten Aktion aus Parentaktion und ε (Toleranz 10⁻⁶). Eine Verletzung hält den Lauf als `FAILED` an.
- 10 synthetische Tests bestehen, die 9 N2-1-Vertragstests bestehen weiterhin (19/19).
- Technische Integrationsprüfung vor dem Lauf, nicht Teil der 900 Episoden (`critic_data_noisy_n2_1b_integration/result.json`): (a) Mit σ = 0 reproduziert der neue Ausführungspfad N2-1-Episode 0000 (Szene 2100000100, Parent 1) mit identischem Startzustands- und Trajektorienhash, Ausgang, Endgrund und Framezahl. (b) Mit σ = 0,05 auf derselben Szene liegt die größte XYZ-Abweichung bei 0,118 bei 0 Grenzverletzungen. Beide bestanden.
- Vor jedem Start prüft das Skript das Freigabehäkchen im NACHTPLAN, `Gesamtpause: nein` und den Status `FREIGEGEBEN` von PROTOCOL_V2.md. `config.json` bindet die Quellen per SHA-256, darunter `critic_data.py`, `ac_smoke.py`, `splits_v3.json` und `PROTOCOL_V2.md`.
- Bei Abschluss gleicht der Monitor einmalig alle 900 Rohepisoden mit `summary.json` ab: Hash, Daten- und Rauschvertrag, Paarung, Zählungen und `dataset_sha256`.

## Bedienung (aus dem Repository-Stamm)

```powershell
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_data_noisy.py monitor
# Fortsetzung nur nach PAUSED, beendeten Prozessen und ohne STOP-Datei, vor 07:30:
& praxis/.venv/Scripts/python.exe experiments/critic/three_cube_transfer_v1/critic_data_noisy.py start resume --cutoff <ISO+01:00> --deadline <ISO+01:00>
```

Ein Halt erfolgt über die Datei `STOP` im Laufordner. Der Worker setzt dann `PAUSED` an einer Episodengrenze. Die nächste Episode ist der Index der ersten fehlenden `NNNN.json`. Jede Episode setzt Szenen- und Rauschseeds selbst, deshalb reproduzieren Fortsetzungen exakt.

## Lauf

Gestartet am 19.11.2026 um 22:41 Uhr als losgelöster Supervisor. Maßgebliche Prozessidentitäten laut `supervisor_status.json` und `status.json`: Supervisor `{"pid": 34664, "created_unix": 1795124497.3361793}`, Worker `{"pid": 37584, "created_unix": 1795124497.5885663}`. Der von `start` gemeldete Startprozess (PID 17652) ist der Startaufruf der venv. Erste Monitorprüfung um 22:42 Uhr: `OK`, 5/900 Episoden, 0 Grenzverletzungen, keine Fehlerzeilen. Startfenster bis 20.11.2026 07:30 Uhr, harte Deadline 09:00 Uhr (Worker 08:59). Erwartete Dauer nach §E etwa 1,0–1,3 h. Dashboardeintrag `three-cube-transfer-v1-critic-data-noisy` in `monitor/training-runs.json`.

Ergebnis, Manifest und Hashes folgen nach Abschluss und Monitorabgleich. Bis dahin liegen keine Erfolgs- oder Fehlerzahlen vor.
