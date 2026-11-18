# Agentenhinweise · praxis/

Gemeinsame Python-Bibliothek, Umgebung und lokale Laufdaten. Ergänzt die
Root-`AGENTS.md`.

## Was ist Quelle, was nicht

| Ort | Status |
|---|---|
| `src/` | gepflegter Bibliothekscode, siehe `src/README.md` |
| `tests/` | Regressionstests zu `src/` |
| `configs/` | Plan-A-Lift-Konfigurationen (historisch, nicht überschreiben) |
| `reports/`, `LOSS_FORMEL.md` | Zusammenfassungen, Formel-zu-Code-Zuordnung |
| `upstream/robomimic`, `upstream/robosuite` | gepinnte Fremd-Checkouts, **nicht ändern, nicht durchsuchen** |
| `.venv/`, `.cache/` | Umgebung/Caches, nicht durchsuchen |
| `data/`, `results/` | große lokale Daten und Checkpoints, nur gezielt per Pfad lesen |

`results/` enthält Junctions (siehe `results/curriculum/README.md`):
keine rekursiven Lösch- oder Verschiebeoperationen.

## Umgebung (PowerShell, aus dem Repository-Stamm)

```powershell
$env:PYTHONPATH=(Resolve-Path praxis/src).Path
$env:MPLCONFIGDIR=(Join-Path (Resolve-Path praxis).Path '.cache/matplotlib')
$env:HF_HOME=(Join-Path (Resolve-Path praxis).Path '.cache/huggingface')
& praxis/.venv/Scripts/python.exe -m pytest -q praxis/tests
```

Einzelne Tests: `praxis/tests/README.md`. Einige Tests brauchen
robosuite/MuJoCo; ein Importfehler dort ist zuerst ein Umgebungs-, kein
Codeproblem. Installations-Pins und Windows-Workarounds (MuJoCo 3.2.3,
DLL-Kopie) stehen in `README.md`. Keine Pakete aktualisieren.

## Ändern

- Änderungen an `src/` wirken auf alle neuen Versuche, nicht auf eingefrorene
  Kopien in `experiments/`. Laufende oder versiegelte Läufe nicht mit
  geändertem `src/` fortsetzen.
- Nach Änderungen die passenden Tests in `praxis/tests/` ausführen.
