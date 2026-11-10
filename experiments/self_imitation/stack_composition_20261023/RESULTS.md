# Nachtlauf: beobachtete Ergebnisse

Automatische Auswertung; fehlende oder unvollstaendige Tests sind keine Erfolge.

| Arm | Seed | Update | Datenpass-Aequivalent | Dev 2 | Dev 3 |
|---|---:|---:|---:|---:|---:|
| raw | 1 | 1000 | 0.293 | 0.0% | nicht gemessen |
| raw | 1 | 3000 | 0.878 | 0.0% | nicht gemessen |
| raw | 1 | 10000 | 2.928 | 10.0% | nicht gemessen |
| raw | 1 | 30000 | 8.784 | 50.0% | 0.0% |
| raw | 2 | 1000 | 0.293 | 0.0% | nicht gemessen |
| raw | 2 | 3000 | 0.878 | 0.0% | nicht gemessen |
| raw | 2 | 10000 | 2.928 | 5.0% | nicht gemessen |
| raw | 2 | 30000 | 8.784 | 60.0% | 0.0% |
| raw | 3 | 1000 | 0.293 | 0.0% | nicht gemessen |
| raw | 3 | 3000 | 0.878 | 0.0% | nicht gemessen |
| raw | 3 | 10000 | 2.928 | 35.0% | nicht gemessen |
| raw | 3 | 30000 | 8.784 | 65.0% | 0.0% |
| relative | 1 | 1000 | 0.293 | 0.0% | nicht gemessen |
| relative | 1 | 3000 | 0.878 | 10.0% | nicht gemessen |
| relative | 1 | 10000 | 2.928 | 0.0% | nicht gemessen |
| relative | 1 | 30000 | 8.784 | 80.0% | 0.0% |
| relative | 2 | 1000 | 0.293 | 0.0% | nicht gemessen |
| relative | 2 | 3000 | 0.878 | 0.0% | nicht gemessen |
| relative | 2 | 10000 | 2.928 | 85.0% | 0.0% |
| relative | 2 | 30000 | 8.784 | 85.0% | 0.0% |
| relative | 3 | 1000 | 0.293 | 0.0% | nicht gemessen |
| relative | 3 | 3000 | 0.878 | 5.0% | nicht gemessen |
| relative | 3 | 10000 | 2.928 | 5.0% | nicht gemessen |
| relative | 3 | 30000 | 8.784 | 70.0% | 0.0% |

## Separater Test: 100 neue Starts pro Trainingsseed

- relative_seed1: 0/100; Wilson 95% [0.0%, 3.7%]; vollstaendig: True.
- relative_seed2: 0/100; Wilson 95% [0.0%, 3.7%]; vollstaendig: True.

90%-Punktziel auf allen drei Trainingsseeds erreicht: {'raw': False, 'relative': False}.

90/100 ist eine Punktschaetzung, kein Beleg, dass die wahre Erfolgswahrscheinlichkeit mindestens 90% betraegt. Entwicklungsrollouts duerfen dafuer nicht als Test verwendet werden.

## Uebergangsdiagnose (Entwicklungsrollouts)

| Lauf / Checkpoint | Erste Paarplatzierung | Zweite Fertigkeit gestartet | Voller Turm |
|---|---:|---:|---:|
| raw_seed1/dev3_30000 | 2/5 | 2/5 | 0/5 |
| raw_seed2/dev3_30000 | 3/5 | 3/5 | 0/5 |
| raw_seed3/dev3_30000 | 5/5 | 5/5 | 0/5 |
| relative_seed1/dev3_30000 | 16/20 | 16/20 | 0/20 |
| relative_seed2/dev3_10000 | 17/20 | 17/20 | 0/20 |
| relative_seed2/dev3_30000 | 17/20 | 17/20 | 0/20 |
| relative_seed3/dev3_30000 | 4/5 | 4/5 | 0/5 |